"""Rotary encoder module for GameForge hardware_service.

Define physical encoders in ENCODERS below — one entry per connected encoder.
Each canvas card selects an encoder by ID.
"""

import pigpio
from encoder import RotaryEncoder

# ── Physical encoder definitions ───────────────────────────────────────────
# Add one entry per connected KY-040. ID must be unique.
# debounce_ms: ignore CLK falling edges within this window after each accepted
# edge. Default 3 ms catches fast electrical bounce; KY-040 mechanical bounce
# can extend to ~55 ms, so 60 ms gives one clean pulse per physical detent.
# sw: BCM pin for the push-button (SW). Set to None if not connected.
ENCODERS = [
    {'id': 1, 'clk': 17, 'dt': 27, 'sw': 22, 'debounce_ms': 60},
]

_SW_DEBOUNCE_US = 200_000  # 200 ms button debounce in pigpio microseconds

MANIFEST = {
    'type':  'ky040_encoder',
    'label': 'Rotary Encoder',
    'model': 'KY-040',
    'count': len(ENCODERS),
}


def get_components():
    options = [
        {'value': e['id'], 'label': f"Encoder {e['id']}  (CLK {e['clk']}, DT {e['dt']})"}
        for e in ENCODERS
    ]
    return [{
        'type':          'ky040_encoder',
        'label':         'Rotary Encoder',
        'subtitle':      MANIFEST['label'],
        'category':      'input',
        'color':         '#22c55e',
        'icon':          '🎛',
        'display_param': 'encoder_id',
        'params': [
            {'key': 'encoder_id', 'label': 'Encoder', 'type': 'select',
             'default': ENCODERS[0]['id'], 'options': options},
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'dial'},
        ],
        'inputs':  [],
        'outputs': [
            {'key': 'delta', 'label': 'Turn Step (+1 / -1)', 'description': 'Fires on each detent step — +1 for clockwise, -1 for counter-clockwise'},
            {'key': 'click', 'label': 'Button Click', 'description': 'Fires when the encoder shaft button is pressed'},
        ],
    }]


class Device:
    def __init__(self):
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError('pigpiod not running — start with: sudo pigpiod')
        self._event_cb = None
        self._encoders = {}
        for e in ENCODERS:
            enc = RotaryEncoder(
                self._pi, clk_pin=e['clk'], dt_pin=e['dt'],
                callback=lambda delta, eid=e['id']: self._on_step(eid, delta),
                debounce_ms=e.get('debounce_ms', 3.0)
            )
            self._encoders[e['id']] = {
                'enc': enc, 'position': 0, 'last_delta': 0, 'last_click_tick': 0,
            }
            sw_pin = e.get('sw')
            if sw_pin is not None:
                self._pi.set_mode(sw_pin, pigpio.INPUT)
                # KY-040 has onboard pull-up; internal PUD_UP is harmless extra safety
                self._pi.set_pull_up_down(sw_pin, pigpio.PUD_UP)
                cb = self._pi.callback(
                    sw_pin, pigpio.FALLING_EDGE,
                    lambda gpio, level, tick, eid=e['id']: self._on_click(eid, tick),
                )
                self._encoders[e['id']]['sw_cb'] = cb

    def set_event_callback(self, fn):
        self._event_cb = fn

    def _on_step(self, encoder_id, delta):
        enc = self._encoders[encoder_id]
        enc['last_delta'] = delta
        enc['position']  += delta
        if self._event_cb:
            self._event_cb('delta', {'encoder_id': encoder_id, 'delta': delta})

    def _on_click(self, encoder_id, tick):
        enc = self._encoders[encoder_id]
        # Software debounce: pigpio tick is uint32 µs, wraps ~72 min
        if (tick - enc['last_click_tick']) & 0xFFFFFFFF < _SW_DEBOUNCE_US:
            return
        enc['last_click_tick'] = tick
        if self._event_cb:
            self._event_cb('click', {'encoder_id': encoder_id})

    def get_state(self):
        return {
            eid: {'position': e['position'], 'last_delta': e['last_delta']}
            for eid, e in self._encoders.items()
        }

    def execute(self, cmd, **kwargs):
        if cmd == 'reset':
            eid = int(kwargs.get('encoder_id', list(self._encoders.keys())[0]))
            if eid in self._encoders:
                self._encoders[eid]['position']   = 0
                self._encoders[eid]['last_delta']  = 0
        return self.get_state()
