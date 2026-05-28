"""Rotary encoder module for GameForge hardware_service.

Define physical encoders in ENCODERS below — one entry per connected encoder.
Each canvas card selects an encoder by ID.
"""

import pigpio
from encoder import RotaryEncoder

# ── Physical encoder definitions ───────────────────────────────────────────
# Add one entry per connected KY-040. ID must be unique.
ENCODERS = [
    {'id': 1, 'clk': 17, 'dt': 27},
]

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
        'outputs': [{'key': 'delta', 'label': 'Delta (+1 / -1)'}],
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
                callback=lambda delta, eid=e['id']: self._on_step(eid, delta)
            )
            self._encoders[e['id']] = {'enc': enc, 'position': 0, 'last_delta': 0}

    def set_event_callback(self, fn):
        self._event_cb = fn

    def _on_step(self, encoder_id, delta):
        enc = self._encoders[encoder_id]
        enc['last_delta'] = delta
        enc['position']  += delta
        if self._event_cb:
            self._event_cb('delta', {'encoder_id': encoder_id, 'delta': delta})

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
