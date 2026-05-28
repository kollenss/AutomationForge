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
#   CONFIRM_STEPS  — require N consecutive opposite steps before treating
#                    as a real reversal (avoids single-tick mechanical noise)
#   CLICK_GRACE_S  — ignore same-direction steps for 250 ms after hitting
#                    target (absorbs encoder burst after the click)
#   DEBOUNCE_S     — ignore opposite step if last same-dir step was < 15 ms
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

_CONFIRM_STEPS    = 2       # consecutive opposite steps to confirm reversal
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
    state['pending_dir']    = None
    state['pending_count']  = 0
    state['dir_confirmed']  = False
    state['click_time']     = 0.0
    state['last_same_time'] = 0.0
    state['last_step_time'] = 0.0
    state['count_frozen']   = False
    state['reset_time']     = time.time()   # lockout window starts now
    state['locked']         = [0, 0, 0, 0]
    if not keep_enabled:
        state['enabled'] = False


def _exec_combo_lock(node_id, params, handle, value, emit, propagate, get_state):
    state = get_state({
        'enabled':        False,
        'phase':          0,
        'count':          0,
        'at_target':      False,
        'last_direction': None,
        'pending_dir':    None,
        'pending_count':  0,
        'dir_confirmed':  False,
        'click_time':     0.0,
        'last_same_time': 0.0,
        'last_step_time': 0.0,
        'reset_time':     0.0,
        'locked':         [0, 0, 0, 0],
        'count_frozen':   False,
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

    # ── delta input ─────────────────────────────────────────────────────────
    if handle != 'delta' or not state['enabled']:
        return

    # Parse code
    raw = params.get('code', '10,20,30,40')
    try:
        code = [max(0, min(99, int(x.strip()))) for x in raw.split(',')]
    except (ValueError, AttributeError):
        return
    while len(code) < 4:
        code.append(1)
    code = code[:4]

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
        # Cancel any pending reversal detection (was mechanical noise)
        if state['dir_confirmed']:
            _log(node_id, 'FALSE_ALARM', phase=phase, count=state['count'],
                 back_to=direction)
        state['dir_confirmed']  = False
        state['pending_dir']    = None
        state['pending_count']  = 0
        state['last_same_time'] = now

        # If a reversal was being detected, freeze the count so encoder wobble
        # (same-direction bounce during direction change) can't shift the value.
        if state['count_frozen']:
            state['count_frozen'] = False
            _log(node_id, 'UNFREEZE', phase=phase, count=state['count'])
            return

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

        # Also block opposite steps during click grace — prevents spurious
        # PENDING entries from encoder jitter right after the click sound
        if state['at_target'] and (now - state['click_time'] < _CLICK_GRACE_S):
            _log(node_id, 'GRACE_OPP', phase=phase, count=state['count'],
                 grace_ms=round((now - state['click_time']) * 1000))
            return

        # Debounce: single spurious opposite tick within 15 ms → ignore
        gap = now - state['last_same_time']
        if gap < _DEBOUNCE_S:
            _log(node_id, 'DEBOUNCE', phase=phase, count=state['count'],
                 gap_ms=round(gap * 1000))
            return

        if state['dir_confirmed']:
            # Reversal confirmed — lock whatever count we're on and advance.
            # Locking at the wrong value means the final check will fail.
            state['dir_confirmed']  = False
            state['pending_dir']    = None
            state['pending_count']  = 0

            locked_val = state['count']
            state['locked'][phase]   = locked_val
            state['phase']          += 1
            state['count']           = 0
            state['at_target']       = False
            state['last_direction']  = None  # fresh start for next phase
            state['click_time']      = 0.0
            state['last_same_time']  = 0.0
            state['last_step_time']  = 0.0
            state['count_frozen']   = False
            state['reset_time']      = now   # lockout: drain burst after commit
            _log(node_id, 'LOCK', locked=locked_val, new_phase=state['phase'],
                 correct=(locked_val == code[phase]))
            propagate('display_8', _combo_display_str(state))

            if state['phase'] >= 4:
                # All four digits locked — validate entire combination
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

        else:
            # Accumulate opposite steps toward confirmation
            if state['pending_dir'] == direction:
                state['pending_count'] += 1
            else:
                state['pending_dir']   = direction
                state['pending_count'] = 1

            state['count_frozen'] = True   # freeze: prevent wobble from shifting count

            _log(node_id, 'PENDING', phase=phase, count=state['count'],
                 new_dir=direction, pcount=state['pending_count'],
                 need=_CONFIRM_STEPS)

            if state['pending_count'] >= _CONFIRM_STEPS:
                state['dir_confirmed']  = True
                state['pending_dir']    = None
                state['pending_count']  = 0
                _log(node_id, 'DETECTED', phase=phase, count=state['count'],
                     new_dir=direction, note='waiting_for_commit')


def _exec_dfplayer(node_id, params, handle, value, emit, propagate, get_state):
    h = (handle or 'trigger').lower()
    if h == 'stop':
        _hw_post('/hardware/dfplayer/stop', {})
        return
    # trigger / play / anything else → play configured track
    track  = max(1, min(255, int(params.get('track',  1))))
    volume = max(0, min(30,  int(params.get('volume', 20))))
    _hw_post('/hardware/dfplayer/play', {'track': track, 'volume': volume})


def _exec_max7219(node_id, params, handle, value, emit, propagate, get_state):
    h      = (handle or 'value').lower()
    digits = int(params.get('digits', 2))

    if h == 'clear':
        _hw_post('/hardware/max7219/clear', {})
        return

    if h == 'text':
        # Send full text string via /text endpoint → _show_text() writes all 8 digits
        text = str(value) if not isinstance(value, bool) else ('ERR' if value else '   ')
        _hw_post('/hardware/max7219/text', {'text': text})
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


# ---------------------------------------------------------------------------

_EXECUTORS = {
    'relay_channel': _exec_relay,
    'rfid_auth':     _exec_rfid_auth,
    'combo_lock':    _exec_combo_lock,
    'dfplayer':      _exec_dfplayer,
    'max7219':       _exec_max7219,
}


# ---------------------------------------------------------------------------

class GameEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._nodes = {}        # node_id → node dict
        self._edges = []
        self._emit = None       # set to socketio.emit by app.py
        self._node_state = {}   # node_id → state dict (stateful behavior nodes)

    def set_emit(self, fn):
        self._emit = fn

    def load_project(self, project):
        nodes, edges = {}, []
        for scene in project.get('scenes', []):
            for node in scene.get('nodes', []):
                nodes[node['id']] = node
            edges.extend(scene.get('edges', []))
        with self._lock:
            self._nodes = nodes
            self._edges = list(edges)
            self._node_state = {}
        return len(nodes), len(edges)

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
            ]
        results = []
        if isinstance(value, dict):
            scalar = value.get('delta', value.get('uid', value))
        else:
            scalar = value
        for node in source_nodes:
            results.extend(self.process_event(node['id'], h, scalar))
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
                (self._nodes.get(e['target']), e.get('targetHandle'))
                for e in self._edges
                if e.get('source') == node_id and (e.get('sourceHandle') or '').lower() == h
            ]

        results = []
        for node, target_handle in targets:
            if not node:
                continue
            comp_type = node['data']['componentType']
            executor  = _EXECUTORS.get(comp_type)
            if not executor:
                continue
            params    = node['data'].get('params', {})
            # nid=node['id'] captures correct id per iteration (avoids closure issue)
            propagate = lambda h, v, nid=node['id']: self.process_event(nid, h, v)
            get_state = lambda defaults=None, nid=node['id']: self.get_node_state(nid, defaults)
            executor(node['id'], params, target_handle, value, self._emit, propagate, get_state)
            results.append({'node_id': node['id'], 'type': comp_type})

        return results
