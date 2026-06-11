import json
import queue
import threading
import time
import urllib.request as _req

# ── Combo Lock debug log ────────────────────────────────────────────────────
# Written to /tmp/combo_debug.log while the engine is running.
# _log() is safe to call from any thread — no file I/O, only a queue put.

_LOG_FILE   = '/tmp/combo_debug.log'
_log_q      = queue.Queue()
_log_t0     = time.time()


def _log(node_id, event, **kw):
    """Queue a log entry. Non-blocking — safe to call inside the engine lock."""
    t = time.time() - _log_t0
    _log_q.put((t, node_id, event, kw))


def _log_worker():
    with open(_LOG_FILE, 'w', buffering=1) as f:
        f.write(f"{'t(s)':>8}  {'node':<10}  {'event':<14}  details\n")
        f.write('-' * 70 + '\n')
        while True:
            item = _log_q.get()
            if item is None:
                break
            t, node_id, event, kw = item
            detail = '  '.join(f'{k}={v}' for k, v in kw.items())
            short_id = str(node_id)[-8:]   # last 8 chars of UUID is enough
            f.write(f'{t:8.3f}  {short_id:<10}  {event:<14}  {detail}\n')


threading.Thread(target=_log_worker, daemon=True, name='combo-log').start()

HW_SERVICE = 'http://localhost:5101'


def _hw_post(path, data=None):
    body = json.dumps(data or {}).encode()
    req = _req.Request(
        f'{HW_SERVICE}{path}', data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with _req.urlopen(req, timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Executors — one per component type.
# Signature: (node_id, params, handle, value, emit, propagate, get_state) → None
#
#   emit(event, payload)         — push socket event to frontend
#   propagate(handle, value)     — fire this node's output handle downstream
#   get_state(defaults=None)     — return mutable per-node state dict

def _exec_relay(node_id, params, handle, value, emit, propagate, get_state):
    channel = int(params.get('channel', 1))
    if handle == 'trigger_on':
        action = 'on'
    elif handle == 'trigger_off':
        action = 'off'
    else:
        action = 'on' if value else 'off'
    resp = _hw_post(f'/hardware/relay_board/{action}', {'channel': channel})
    if emit and isinstance(resp.get('state'), dict):
        emit('relay_state', resp['state'])


def _exec_rfid_auth(node_id, params, handle, value, emit, propagate, get_state):
    if handle and handle.lower() != 'card_read':
        return
    valid_uids = {u.strip().upper() for u in params.get('valid_uids', '').split(',') if u.strip()}
    uid = str(value).strip().upper()
    if uid in valid_uids:
        propagate('authorized', uid)
    else:
        propagate('denied', uid)


# ── Combo Lock ──────────────────────────────────────────────────────────────
# Models a 4-digit rotary combination lock.
#
# Params:
#   code  — "12,34,56,78"  (four numbers 0-99)
#   name  — display label
#
# Inputs:
#   enable — activates the lock (connect from RFID Auth authorized)
#   delta  — encoder step (+1 right / -1 left)
#
# Outputs:
#   current_value — current count (0-99) for display
#   digit_locked  — fires when a digit is confirmed (connect to DFPlayer click)
#   unlocked      — all 4 digits correct
#   failed        — wrong direction at wrong time
#
# Direction sequence: left → right → left → right
#   Phase 0 expects LEFT turns  (delta < 0)
#   Phase 1 expects RIGHT turns (delta > 0)
#   Phase 2 expects LEFT turns
#   Phase 3 expects RIGHT turns
#
# Mechanic: count increments each step in the expected direction (wraps 0-99).
# When count == code[phase]: fire digit_locked, set at_target + grace window.
# Overshooting is fine — click re-fires on the next lap around.
# When direction reverses (CONFIRM_STEPS opp-steps confirmed): lock current
# count and advance phase. The locked value doesn't have to be the target —
# wrong locks lead to a failed combination after all 4 phases are done.
#
# Noise rejection (ported from vault.py):
#   CLICK_GRACE_S  — ignore same-direction steps for 250 ms after hitting
#                    target (absorbs encoder burst after the click)
#   DEBOUNCE_S     — ignore opposite step if last same-dir step was < 150 ms
#                    ago (filters brief directional glitches)

_EXPECTED_DIRS = ['left', 'right', 'left', 'right']


def _combo_display_str(state):
    """Build an 8-char string for a MAX7219 8-digit display.
    Two digits per phase: locked phases show their locked value, the
    active phase shows the current count, future phases are blank.
    Example: phase 1 locked at 42, phase 2 active at 15 → '4215    '
    """
    out = ''
    for i in range(4):
        if i < state['phase']:
            out += f"{state['locked'][i]:02d}"
        elif i == state['phase']:
            out += f"{state['count']:02d}"
        else:
            out += '  '
    return out

_CLICK_GRACE_S    = 0.25   # seconds to ignore ALL steps after target hit
_DEBOUNCE_S       = 0.150  # seconds: ignore opp step if same-dir was this recent
                            # KY-040 generates ~9 spurious opp CLK edges per real step
                            # at ~10 ms intervals for up to 111 ms (observed in log).
                            # 150 ms filters the entire burst; deliberate reversals
                            # start ≥200 ms after the last step (safe margin: 50 ms).
_RESET_LOCKOUT_S  = 0.4    # seconds to ignore deltas after ENABLE / FAIL / LOCK
                            # absorbs queued encoder events after a state reset
_MIN_STEP_INTERVAL_S = 0.040  # 40 ms min between accepted same-dir steps
                               # KY-040 between-detent noise produces same-dir bursts
                               # at ~24-34 ms — this blocks the second pulse in each pair
                               # while still allowing deliberate turning (≥50 ms/step)


def _combo_reset(state, keep_enabled=False):
    state['phase']          = 0
    state['count']          = 0
    state['at_target']      = False
    state['last_direction'] = None
    state['click_time']     = 0.0
    state['last_same_time'] = 0.0
    state['last_step_time'] = 0.0
    state['reset_time']     = time.time()   # lockout window starts now
    state['locked']         = [0, 0, 0, 0]
    if not keep_enabled:
        state['enabled'] = False


def _combo_lock_phase(node_id, state, phase, code, now, emit, propagate):
    locked_val              = state['count']
    state['locked'][phase]  = locked_val
    state['phase']         += 1
    state['count']          = 0
    state['at_target']      = False
    state['last_direction'] = None
    state['click_time']     = 0.0
    state['last_same_time'] = 0.0
    state['last_step_time'] = 0.0
    state['reset_time']     = now
    _log(node_id, 'LOCK', locked=locked_val, new_phase=state['phase'],
         correct=(locked_val == code[phase]))
    propagate('display_8', _combo_display_str(state))

    if state['phase'] >= 4:
        if state['locked'] == code:
            _log(node_id, 'UNLOCK')
            if emit:
                emit('combo_state', {'node_id': node_id, 'unlocked': True})
            propagate('unlocked', True)
            _combo_reset(state, keep_enabled=False)
        else:
            _log(node_id, 'FAIL', locked=str(state['locked']), code=str(code))
            if emit:
                emit('combo_state', {'node_id': node_id, 'failed': True})
            propagate('failed', True)
            _combo_reset(state, keep_enabled=True)
    else:
        if emit:
            emit('combo_state', {
                'node_id': node_id,
                'phase':   state['phase'],
                'count':   0,
            })


def _exec_combo_lock(node_id, params, handle, value, emit, propagate, get_state):
    state = get_state({
        'enabled':        False,
        'phase':          0,
        'count':          0,
        'at_target':      False,
        'last_direction': None,
        'click_time':     0.0,
        'last_same_time': 0.0,
        'last_step_time': 0.0,
        'reset_time':     0.0,
        'locked':         [0, 0, 0, 0],
    })

    # ── enable input ────────────────────────────────────────────────────────
    if handle == 'enable':
        _combo_reset(state, keep_enabled=False)   # sets reset_time = now
        state['enabled'] = True
        _log(node_id, 'ENABLE', phase=0)
        if emit:
            emit('combo_state', {'node_id': node_id, 'enabled': True,
                                 'phase': 0, 'count': 0})
        propagate('display_8', '00      ')
        return

    if not state['enabled']:
        return

    # Parse code (needed by both test_code and delta)
    raw = params.get('code', '10,20,30,40')
    try:
        code = [max(0, min(99, int(x.strip()))) for x in raw.split(',')]
    except (ValueError, AttributeError):
        return
    while len(code) < 4:
        code.append(1)
    code = code[:4]

    # ── test_code input — same effect as a confirmed direction reversal ──────
    if handle == 'test_code':
        if state['last_direction'] is None:
            return
        now = time.time()
        lockout_remaining = _RESET_LOCKOUT_S - (now - state.get('reset_time', 0.0))
        if lockout_remaining > 0:
            return
        _combo_lock_phase(node_id, state, state['phase'], code, now, emit, propagate)
        return

    # ── delta input ─────────────────────────────────────────────────────────
    if handle != 'delta':
        return

    delta = int(value) if value else 0
    if delta == 0:
        return

    direction = 'left' if delta < 0 else 'right'
    phase     = state['phase']
    expected  = _EXPECTED_DIRS[phase]
    now       = time.time()

    # ── Post-reset lockout ─────────────────────────────────────────────────
    # Encoder events queue up in HTTP; after any reset (ENABLE/FAIL/LOCK)
    # ignore everything for _RESET_LOCKOUT_S to drain the backlog.
    lockout_remaining = _RESET_LOCKOUT_S - (now - state.get('reset_time', 0.0))
    if lockout_remaining > 0:
        _log(node_id, 'LOCKOUT', phase=phase, ms_left=round(lockout_remaining * 1000))
        return

    if direction == expected:
        # ── Correct direction ──────────────────────────────────────────────
        state['last_same_time'] = now

        # Grace window after hitting target — absorbs encoder burst noise
        if now - state['click_time'] < _CLICK_GRACE_S:
            _log(node_id, 'GRACE', phase=phase, count=state['count'],
                 grace_ms=round((now - state['click_time']) * 1000))
            return

        # Rate-limit same-direction steps — between-detent CLK noise produces
        # spurious steps in the same direction at ~24-34 ms intervals.
        step_gap = now - state['last_step_time']
        if step_gap < _MIN_STEP_INTERVAL_S:
            _log(node_id, 'RATELIMIT', phase=phase, count=state['count'],
                 gap_ms=round(step_gap * 1000))
            return
        state['last_step_time'] = now

        prev_count      = state['count']
        state['count']  = (state['count'] + 1) % 100
        state['last_direction'] = direction

        if state['count'] == 0:
            _log(node_id, 'WRAP', phase=phase, prev=prev_count)

        if state['count'] == code[phase]:
            state['at_target']  = True
            state['click_time'] = now
            _log(node_id, 'CLICK', phase=phase, count=state['count'],
                 target=code[phase])
            propagate('digit_locked', state['count'])
        else:
            if state['at_target']:
                # Overshot past target — clear flag so reversal now fails
                state['at_target'] = False
                _log(node_id, 'OVERSHOOT', phase=phase, count=state['count'],
                     target=code[phase])
            else:
                _log(node_id, 'COUNT', phase=phase, count=state['count'],
                     target=code[phase], dir=direction)

        if emit:
            emit('combo_state', {
                'node_id':   node_id,
                'phase':     phase,
                'count':     state['count'],
                'at_target': state['at_target'],
            })
        propagate('current_value', state['count'])
        propagate('display_8', _combo_display_str(state))

    else:
        # ── Opposite / wrong direction ─────────────────────────────────────
        # No direction established yet in this phase — ignore
        if state['last_direction'] is None:
            return

        # Block opposite steps during click grace — filters encoder jitter
        # right after the click sound fires
        if state['at_target'] and (now - state['click_time'] < _CLICK_GRACE_S):
            _log(node_id, 'GRACE_OPP', phase=phase, count=state['count'],
                 grace_ms=round((now - state['click_time']) * 1000))
            return

        # Debounce: spurious opposite tick within 150 ms → ignore
        gap = now - state['last_same_time']
        if gap < _DEBOUNCE_S:
            _log(node_id, 'DEBOUNCE', phase=phase, count=state['count'],
                 gap_ms=round(gap * 1000))
            return

        _combo_lock_phase(node_id, state, phase, code, now, emit, propagate)


def _exec_dfplayer(node_id, params, handle, value, emit, propagate, get_state):
    """Play or stop a DFPlayer Mini track.

    If 'duration_s' is set > 0 on the card, a Done signal fires after that
    many seconds — use this to chain audio → LED → audio sequences on canvas.
    Stop cancels any pending Done timer so it never fires after manual stop.
    """
    state = get_state({'timer': None})
    h = (handle or 'trigger').lower()

    if h == 'stop':
        t = state.get('timer')
        if t:
            t.cancel()
            state['timer'] = None
        _hw_post('/hardware/dfplayer/stop', {})
        return

    # trigger / play / anything else → play configured track
    track      = max(1, min(255, int(params.get('track',  1))))
    volume     = max(0, min(30,  int(params.get('volume', 20))))
    duration_s = float(params.get('duration_s', 0))

    _hw_post('/hardware/dfplayer/play', {'track': track, 'volume': volume})

    if duration_s > 0:
        t = state.get('timer')
        if t:
            t.cancel()

        def _done():
            state['timer'] = None
            propagate('done', value)

        timer = threading.Timer(duration_s, _done)
        timer.daemon = True
        timer.start()
        state['timer'] = timer


def _exec_servo(node_id, params, handle, value, emit, propagate, get_state):
    gpio_pin = int(params.get('gpio_pin', 12))
    if handle == 'set_angle':
        try:
            angle = max(0.0, min(180.0, float(value)))
        except (TypeError, ValueError):
            return
        _hw_post('/hardware/servo/set_angle', {'gpio_pin': gpio_pin, 'angle': angle})
        propagate('done', angle)
    elif handle == 'release':
        _hw_post('/hardware/servo/release', {'gpio_pin': gpio_pin})


def _exec_terminal_gate(node_id, params, handle, value, emit, propagate, get_state):
    if handle == 'success':
        propagate('success', value)
        return
    if handle == 'failure':
        propagate('failure', value)
        return
    if handle not in ('enable', 'disable'):
        return
    url = params.get('url', 'http://localhost:8080').rstrip('/')
    body = {}
    if handle == 'enable':
        pw = params.get('password', '').strip()
        if pw:
            body['password'] = pw
    try:
        req = _req.Request(f'{url}/{handle}', data=json.dumps(body).encode(),
                           headers={'Content-Type': 'application/json'}, method='POST')
        _req.urlopen(req, timeout=2)
    except Exception as e:
        print(f'[terminal_gate] {handle} failed: {e}')


def _exec_set_value(node_id, params, handle, value, emit, propagate, get_state):
    out = params.get('value', '')
    threading.Timer(0.05, propagate, args=('out', out)).start()


def _exec_timer(node_id, params, handle, value, emit, propagate, get_state):
    state = get_state({'running': False, 'cancel_event': None})
    duration = max(1, int(params.get('duration_s', 60)))

    def _cancel():
        ev = state.get('cancel_event')
        if ev:
            ev.set()
        state['running'] = False
        state['cancel_event'] = None

    if handle == 'reset':
        _cancel()
        if emit:
            emit('timer_state', {'node_id': node_id, 'remaining': duration, 'running': False})
        return

    if handle == 'start':
        _cancel()
        cancel_ev = threading.Event()
        state['running'] = True
        state['cancel_event'] = cancel_ev
        if emit:
            emit('timer_state', {'node_id': node_id, 'remaining': duration, 'running': True})

        def _run():
            remaining = duration
            while remaining > 0:
                if cancel_ev.wait(1.0):
                    return
                remaining -= 1
                propagate('tick', remaining)
                if emit:
                    emit('timer_state', {'node_id': node_id, 'remaining': remaining, 'running': remaining > 0})
            state['running'] = False
            propagate('expired', True)

        threading.Thread(target=_run, daemon=True,
                         name=f'timer-{str(node_id)[-8:]}').start()


def _exec_max7219(node_id, params, handle, value, emit, propagate, get_state):
    h      = (handle or 'value').lower()
    digits = int(params.get('digits', 2))

    def _emit_state(text, scrolling=False):
        if emit:
            emit('max7219_state', {'node_id': node_id, 'text': text, 'scrolling': scrolling})

    if h == 'clear':
        _hw_post('/hardware/max7219/clear', {})
        _emit_state('')
        return

    if h == 'scroll':
        text     = str(params.get('scroll_text', ''))
        speed_ms = max(50, min(1000, int(params.get('speed_ms', 150))))
        _hw_post('/hardware/max7219/scroll', {'text': text, 'speed_ms': speed_ms})
        _emit_state(text, scrolling=True)
        return

    if h == 'text':
        text = str(value) if not isinstance(value, bool) else ('ERR' if value else '   ')
        _hw_post('/hardware/max7219/text', {'text': text})
        _emit_state(text)
        return

    # Numeric / value mode: render as zero-padded number, show on a pair
    pair      = int(params.get('pair',      0))
    intensity = int(params.get('intensity', 8))
    if h in ('value', 'current_value'):
        try:
            text = str(int(value)).zfill(digits)
        except (ValueError, TypeError):
            text = str(value)
    else:
        text = str(value)

    _hw_post('/hardware/max7219/show', {'text': text, 'pair': pair, 'intensity': intensity})
    _emit_state(text)


def _exec_checklist(node_id, params, handle, value, emit, propagate, get_state):
    """Execute a Checklist step.

    Tracks which step is expected next using per-node state.
    Steps must arrive in order (step_1 → step_2 → ... → step_N).
    Out-of-order arrivals fire 'out_of_order' and reset the checklist
    if reset_on_fail is true.

    'length' controls how many steps count — inputs beyond that are ignored.
    """
    if not handle.startswith('step_'):
        return
    try:
        step_num = int(handle.split('_')[1])
    except (IndexError, ValueError):
        return

    length        = max(1, int(params.get('length', 3)))
    reset_on_fail = params.get('reset_on_fail', True)

    # Skip inputs that are beyond the configured length
    if step_num > length:
        return

    state    = get_state({'next_step': 1})
    expected = state['next_step']

    def _emit_status(current):
        emit('checklist_state', {
            'node_id': node_id,
            'step':    current,
            'total':   length,
        })

    if step_num == expected:
        if step_num == length:
            # Final step — checklist complete
            state['next_step'] = 1   # reset so it can be reused
            _emit_status(length)
            propagate('complete', value)
        else:
            # Correct step, advance
            state['next_step'] = expected + 1
            _emit_status(step_num)
    else:
        # Wrong order
        if reset_on_fail:
            state['next_step'] = 1
        _emit_status(-1)
        propagate('out_of_order', value)


def _exec_led_zone(node_id, params, handle, value, emit, propagate, get_state):
    """Execute a WS2812B LED Zone command.

    Instant commands (set_color, off, pulse, rainbow) fire Done immediately.
    Finite animations (blink, chase) run in a thread and fire Done on completion.
    """
    first      = int(params.get('first_led', 0))
    last       = int(params.get('last_led', 2))
    brightness = int(params.get('brightness', 128))
    default_color = params.get('default_color', 'white')

    payload = {
        'first_led':     first,
        'last_led':      last,
        'brightness':    brightness,
        'default_color': default_color,
    }

    if handle == 'set_color':
        payload['color'] = value if isinstance(value, str) and value else default_color
        _hw_post('/hardware/ws2812b/set_color', payload)
        propagate('done', value)

    elif handle == 'off':
        _hw_post('/hardware/ws2812b/off', payload)
        propagate('done', value)

    elif handle == 'pulse':
        _hw_post('/hardware/ws2812b/pulse', payload)
        propagate('done', value)

    elif handle == 'rainbow':
        _hw_post('/hardware/ws2812b/rainbow', payload)
        propagate('done', value)

    elif handle == 'blink':
        try:
            payload['count'] = int(value) if value else 3
        except (TypeError, ValueError):
            payload['count'] = 3

        def _run():
            try:
                _hw_post('/hardware/ws2812b/blink', payload)
            except Exception as e:
                print(f'[led_zone] blink failed: {e}')
            propagate('done', value)

        threading.Thread(target=_run, daemon=True).start()

    elif handle == 'chase':
        def _run():
            try:
                _hw_post('/hardware/ws2812b/chase', payload)
            except Exception as e:
                print(f'[led_zone] chase failed: {e}')
            propagate('done', value)

        threading.Thread(target=_run, daemon=True).start()


def _exec_if_else(node_id, params, handle, value, emit, propagate, get_state):
    """Compare the incoming value against a condition and route to then/else.

    Params:
        operator  — equals | contains | starts_with | ends_with | greater_than | less_than
        operand   — the value to compare against
        case_sensitive — '1' or '0' (default '0')
    """
    operator       = params.get('operator', 'equals')
    operand        = params.get('operand', '')
    case_sensitive = params.get('case_sensitive', '0') == '1'

    lhs = str(value).strip()
    rhs = operand.strip()

    if not case_sensitive:
        lhs_cmp = lhs.lower()
        rhs_cmp = rhs.lower()
    else:
        lhs_cmp = lhs
        rhs_cmp = rhs

    if operator == 'equals':
        result = lhs_cmp == rhs_cmp
    elif operator == 'contains':
        result = rhs_cmp in lhs_cmp
    elif operator == 'starts_with':
        result = lhs_cmp.startswith(rhs_cmp)
    elif operator == 'ends_with':
        result = lhs_cmp.endswith(rhs_cmp)
    elif operator == 'greater_than':
        try:
            result = float(lhs) > float(rhs)
        except ValueError:
            result = False
    elif operator == 'less_than':
        try:
            result = float(lhs) < float(rhs)
        except ValueError:
            result = False
    else:
        result = False

    if result:
        propagate('then', value)
    else:
        propagate('else', value)



def _exec_console_log(node_id, params, handle, value, emit, propagate, get_state):
    label = params.get('label', 'log')
    short_id = str(node_id)[-6:]
    print(f'[LOG {label} #{short_id}] {value}', flush=True)
    if emit:
        emit('console_log', {'node_id': node_id, 'label': label, 'value': str(value)})
    propagate('out', value)


# ---------------------------------------------------------------------------

_EXECUTORS = {
    'relay_channel': _exec_relay,
    'rfid_auth':     _exec_rfid_auth,
    'combo_lock':    _exec_combo_lock,
    'dfplayer':      _exec_dfplayer,
    'max7219':       _exec_max7219,
    'servo':         _exec_servo,
    'timer':         _exec_timer,
    'set_value':     _exec_set_value,
    'terminal_gate': _exec_terminal_gate,
    'checklist':     _exec_checklist,
    'led_zone':      _exec_led_zone,
    'if_else':       _exec_if_else,
    'console_log':   _exec_console_log,
}


# ---------------------------------------------------------------------------

class GameEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._nodes = {}            # node_id → node dict
        self._edges = []
        self._emit = None           # set to socketio.emit by app.py
        self._node_state = {}       # node_id → state dict (stateful behavior nodes)
        self._node_to_scene = {}    # node_id → scene_id
        self._scene_name_to_id = {} # scene name → scene_id
        self._active_scene_ids = set()
        self._on_scene_activation = None  # fn(scene_id, active: bool) — set by app.py for persistence
        self._if_else_gated = set() # node IDs that start disabled because they are wired from an if_else output
        self._unlocked = set()      # gated node IDs that have been unlocked this session

    def set_emit(self, fn):
        self._emit = fn

    def set_activation_callback(self, fn):
        """Called by app.py so canvas-triggered activation can persist + emit to clients."""
        self._on_scene_activation = fn

    def load_project(self, project):
        nodes, edges, node_to_scene, name_to_id, active_ids = {}, [], {}, {}, set()
        for scene in project.get('scenes', []):
            sid = scene['id']
            if scene.get('active', False):
                active_ids.add(sid)
            name_to_id[scene.get('name', '')] = sid
            for node in scene.get('nodes', []):
                nodes[node['id']] = node
                node_to_scene[node['id']] = sid
            edges.extend(scene.get('edges', []))
        # Nodes that have any incoming wire from an if_else output start disabled.
        # The if_else wire itself is what unlocks them — no param needed.
        gated = set()
        for edge in edges:
            src = nodes.get(edge.get('source'))
            if src and src['data']['componentType'] == 'if_else':
                src_handle = (edge.get('sourceHandle') or '').lower()
                if src_handle in ('then', 'else'):
                    gated.add(edge['target'])
        with self._lock:
            self._nodes = nodes
            self._edges = list(edges)
            self._node_state = {}
            self._node_to_scene = node_to_scene
            self._scene_name_to_id = name_to_id
            self._active_scene_ids = active_ids
            self._if_else_gated = gated
            self._unlocked = set()
        return len(nodes), len(edges)

    def activate_scene(self, scene_id, from_canvas=False):
        with self._lock:
            self._active_scene_ids.add(scene_id)
            # Re-lock any gated nodes in this scene so they start fresh
            scene_gated = {
                nid for nid in self._if_else_gated
                if self._node_to_scene.get(nid) == scene_id
            }
            self._unlocked -= scene_gated
            start_nodes = [
                nid for nid, sid in self._node_to_scene.items()
                if sid == scene_id
                and self._nodes.get(nid, {}).get('data', {}).get('componentType') == 'on_scene_start'
            ]
        for node_id in start_nodes:
            if self._emit:
                self._emit('node_pulse', {'node_id': node_id})
            self.process_event(node_id, 'signal', True)
        if from_canvas and self._on_scene_activation:
            self._on_scene_activation(scene_id, True)

    def deactivate_scene(self, scene_id, from_canvas=False):
        with self._lock:
            self._active_scene_ids.discard(scene_id)
        if from_canvas and self._on_scene_activation:
            self._on_scene_activation(scene_id, False)

    def is_scene_active(self, scene_id):
        with self._lock:
            return scene_id in self._active_scene_ids

    def get_scene_id_by_name(self, name):
        with self._lock:
            return self._scene_name_to_id.get(name)

    def get_node_state(self, node_id, defaults=None):
        """Return (and lazily initialise) per-node state dict for stateful behaviors."""
        with self._lock:
            if node_id not in self._node_state:
                self._node_state[node_id] = dict(defaults or {})
            return self._node_state[node_id]

    def trigger_node(self, node_id, value, handle=None):
        """Call a node's executor directly.

        handle — optional input-handle name (e.g. 'enable', 'delta').
                 Useful for injecting events into behavior nodes for testing.
        """
        with self._lock:
            node = self._nodes.get(node_id)
        if not node:
            return None
        comp_type = node['data']['componentType']
        executor = _EXECUTORS.get(comp_type)
        if not executor:
            return None
        params    = node['data'].get('params', {})
        propagate = lambda h, v: self.process_event(node_id, h, v)
        get_state = lambda defaults=None: self.get_node_state(node_id, defaults)
        executor(node_id, params, handle, value, self._emit, propagate, get_state)
        return {'node_id': node_id, 'type': comp_type}

    def process_hardware_event(self, device_type, event, value):
        """Find matching canvas nodes and fire their outputs.

        value may be a plain scalar or a dict (e.g. {'encoder_id': 1, 'delta': 1}).
        For dict values, nodes are filtered on matching params where keys overlap.
        """
        h = event.lower()
        with self._lock:
            source_nodes = [
                node for node in self._nodes.values()
                if node['data']['componentType'] == device_type
                and self._params_match(node['data'].get('params', {}), value)
                and self._node_to_scene.get(node['id']) in self._active_scene_ids
            ]
            gated   = self._if_else_gated
            unlocked = self._unlocked
        results = []
        if isinstance(value, dict):
            scalar = value.get('text', value.get('delta', value.get('uid', value)))
        else:
            scalar = value
        for node in source_nodes:
            nid = node['id']
            # If this source node is wired from an if_else output it starts
            # disabled — ignore hardware events until unlocked.
            if nid in gated and nid not in unlocked:
                continue
            if self._emit:
                self._emit('node_pulse', {'node_id': nid})
            results.extend(self.process_event(nid, h, scalar))
        return results

    @staticmethod
    def _params_match(params, value):
        """Return True if value is not a dict, or if all dict keys that exist
        as node params have matching values."""
        if not isinstance(value, dict):
            return True
        for k, v in value.items():
            if k in params and params[k] != v:
                return False
        return True

    def process_event(self, node_id, handle, value):
        h = handle.lower()
        with self._lock:
            targets = [
                (self._nodes.get(e['target']), e.get('targetHandle'), e.get('id'))
                for e in self._edges
                if e.get('source') == node_id and (e.get('sourceHandle') or '').lower() == h
            ]

        # Check if this propagation comes from an if_else output — if so, unlock targets
        source_node = self._nodes.get(node_id)
        is_if_else_output = (
            source_node is not None
            and source_node['data']['componentType'] == 'if_else'
            and h in ('then', 'else')
        )

        results = []
        for node, target_handle, edge_id in targets:
            if not node:
                continue

            # Topology-based gate: nodes wired from if_else start locked.
            # The if_else wire unlocks them; any other incoming wire is ignored until unlocked.
            nid = node['id']
            if is_if_else_output:
                with self._lock:
                    self._unlocked.add(nid)
                if self._emit:
                    self._emit('if_else_gate_state', {'node_id': nid, 'unlocked': True})
            elif nid in self._if_else_gated and nid not in self._unlocked:
                continue   # still locked — drop this event

            # Emit visual pulse events for the edge and target node
            if self._emit:
                if edge_id:
                    self._emit('edge_pulse', {'edge_id': edge_id, 'value': value, 'target_handle': target_handle})
                self._emit('node_pulse', {'node_id': nid})
            comp_type = node['data']['componentType']
            params    = node['data'].get('params', {})

            # Scene control components — handled inline, no executor needed
            if comp_type in ('activate_scene', 'deactivate_scene'):
                scene_name = params.get('scene_name', '').strip()
                sid = self.get_scene_id_by_name(scene_name)
                if sid:
                    if comp_type == 'activate_scene':
                        self.activate_scene(sid, from_canvas=True)
                    else:
                        self.deactivate_scene(sid, from_canvas=True)
                results.append({'node_id': nid, 'type': comp_type})
                continue

            executor  = _EXECUTORS.get(comp_type)
            if not executor:
                continue
            propagate = lambda h, v, _nid=nid: self.process_event(_nid, h, v)
            get_state = lambda defaults=None, _nid=nid: self.get_node_state(_nid, defaults)
            executor(nid, params, target_handle, value, self._emit, propagate, get_state)
            results.append({'node_id': nid, 'type': comp_type})

        return results
