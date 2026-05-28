import time
from pylibftdi import BitBangDevice

CHANNEL_BITS = {1: 0x02, 2: 0x08, 3: 0x20, 4: 0x80}

MANIFEST = {
    'type': 'relay_board',
    'label': 'USB Relay Board',
    'serial': 'DAE000iW',
    'channels': 4,
}


def get_components():
    n = MANIFEST['channels']
    return [{
        'type': 'relay_channel',
        'label': 'Relay Channel',
        'subtitle': MANIFEST['label'],
        'category': 'output',
        'color': '#f59e0b',
        'icon': '⚡',
        'display_param': 'channel',
        'params': [
            {'key': 'channel', 'label': 'Channel', 'type': 'select',
             'default': 1, 'options': [{'value': i, 'label': f'Channel {i}'} for i in range(1, n + 1)]},
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'solenoid'},
        ],
        'inputs': [
            {'key': 'trigger_on',  'label': 'Trigger ON'},
            {'key': 'trigger_off', 'label': 'Trigger OFF'},
        ],
        'outputs': [{'key': 'state', 'label': 'State'}],
    }]


class RelayBoard:
    def __init__(self):
        self._bb = BitBangDevice('DAE000iW')
        self._bb.direction = 0xFF
        self._bb.port = 0x00

    def set_mask(self, mask):
        self._bb.port = mask & 0xFF

    def set(self, channel, on=True):
        bit = CHANNEL_BITS.get(channel, 0)
        if on:
            self._bb.port |= bit
        else:
            self._bb.port &= ~bit

    def all_off(self):
        self._bb.port = 0x00

    def get_mask(self):
        return self._bb.port

    def close(self):
        try:
            self._bb.port = 0x00
            self._bb.close()
        except Exception:
            pass


class Device:
    def __init__(self):
        self._board = RelayBoard()
        self._state = {1: False, 2: False, 3: False, 4: False}

    def get_state(self):
        return {str(k): v for k, v in self._state.items()}

    def execute(self, cmd, **kwargs):
        channel = int(kwargs.get('channel', 1))
        if cmd not in ('on', 'off'):
            raise ValueError(f'Unknown command: {cmd}')
        if channel not in CHANNEL_BITS:
            raise ValueError(f'Invalid channel: {channel}')
        self._state[channel] = (cmd == 'on')
        mask = sum(CHANNEL_BITS[ch] for ch, on in self._state.items() if on)
        self._board.set_mask(mask)
        return self.get_state()
