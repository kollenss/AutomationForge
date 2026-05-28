MANIFEST = {
    'type': 'rfid_reader',
    'label': 'RFID Reader RC522',
}


def get_components():
    return [{
        'type': 'rfid_reader',
        'label': 'RFID Reader',
        'subtitle': MANIFEST['label'],
        'category': 'input',
        'color': '#22c55e',
        'icon': '📡',
        'display_param': 'name',
        'params': [
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'card reader'},
        ],
        'inputs':  [],
        'outputs': [{'key': 'card_read', 'label': 'Card Read (UID)'}],
    }]


class Device:
    def __init__(self):
        self._callback = None
        self._last_uid = None
        # Real RC522 implementation goes here (spidev / mfrc522 library).
        # Currently stub — use execute('simulate', uid='AABBCCDD') to fire events.
        print('[rfid] stub mode — no hardware connected')

    def get_state(self):
        return {'last_uid': self._last_uid}

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate':
            uid = str(kwargs.get('uid', 'AABBCCDD')).upper()
            self._last_uid = uid
            if self._callback:
                self._callback('card_read', uid)
            return {'uid': uid}
        raise ValueError(f'Unknown command: {cmd}')

    def set_event_callback(self, fn):
        self._callback = fn
