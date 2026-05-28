READERS = [
    {'id': 1, 'ce': 0, 'rst': 25},
]

MANIFEST = {
    'type': 'rfid_reader',
    'label': 'RFID Reader RC522',
    'readers': len(READERS),
}


def get_components():
    return [{
        'type': 'rfid_reader',
        'label': 'RFID Reader',
        'subtitle': MANIFEST['label'],
        'category': 'input',
        'color': '#22c55e',
        'icon': '📡',
        'display_param': 'reader_id',
        'params': [
            {
                'key': 'reader_id',
                'label': 'Reader',
                'type': 'select',
                'default': READERS[0]['id'],
                'options': [{'value': r['id'], 'label': f'Reader {r["id"]}'} for r in READERS],
            },
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'card reader'},
        ],
        'inputs':  [],
        'outputs': [{'key': 'card_read', 'label': 'Card Read (UID)'}],
    }]


class Device:
    def __init__(self):
        self._callback = None
        self._last = {}  # reader_id → last uid
        # Real RC522 implementation goes here (spidev / mfrc522 library).
        # Currently stub — use execute('simulate', reader_id=1, uid='AABBCCDD').
        print('[rfid] stub mode — no hardware connected')

    def get_state(self):
        return {'last': self._last}

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate':
            reader_id = int(kwargs.get('reader_id', READERS[0]['id']))
            uid = str(kwargs.get('uid', 'AABBCCDD')).upper()
            self._last[reader_id] = uid
            if self._callback:
                self._callback('card_read', {'reader_id': reader_id, 'uid': uid})
            return {'reader_id': reader_id, 'uid': uid}
        raise ValueError(f'Unknown command: {cmd}')

    def set_event_callback(self, fn):
        self._callback = fn
