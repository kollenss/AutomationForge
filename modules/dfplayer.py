"""DFPlayer Mini MP3 module for GameForge hardware_service.

Hardware connection (Raspberry Pi):
  DFPlayer TX  → Pi GPIO 15 / RX (pin 10)
  DFPlayer RX  → Pi GPIO 14 / TX (pin 8)  [via 1kΩ resistor recommended]
  DFPlayer VCC → 5V (pin 2 or 4)
  DFPlayer GND → GND (pin 6)
  DFPlayer SPK → speaker (8Ω)

SD card file layout:  /0001.mp3, /0002.mp3 … or /MP3/0001.mp3 etc.
Track numbers map directly to filenames.

Configurable:
  UART_PORT — serial device path
  UART_BAUD — baud rate (DFPlayer default: 9600)
"""

import time

UART_PORT = '/dev/ttyUSB1'   # USB-serial adapter; relay board claims ttyUSB0 via pylibftdi
UART_BAUD = 9600

MANIFEST = {
    'type':  'dfplayer',
    'label': 'DFPlayer Mini',
}


def get_components():
    return [{
        'type':          'dfplayer',
        'label':         'DFPlayer Mini',
        'subtitle':      'MP3 Player',
        'category':      'output',
        'color':         '#0ea5e9',
        'icon':          '🔊',
        'display_param': 'track',
        'params': [
            {'key': 'track',  'label': 'Track',        'type': 'number', 'default': 1,  'min': 1, 'max': 255},
            {'key': 'volume', 'label': 'Volume (0-30)', 'type': 'number', 'default': 20, 'min': 0, 'max': 30},
            {'key': 'name',   'label': 'Label',         'type': 'text',   'default': 'speaker'},
        ],
        'inputs': [
            {'key': 'trigger', 'label': 'Play Track', 'description': 'Plays the configured track at the configured volume'},
            {'key': 'stop',    'label': 'Stop', 'description': 'Stops playback immediately'},
        ],
        'outputs': [],
    }]


def _checksum(data):
    return (-sum(data)) & 0xFFFF


class Device:
    # DFPlayer serial command bytes
    _CMD_PLAY_TRACK = 0x03
    _CMD_SET_VOLUME = 0x06
    _CMD_STOP       = 0x16
    _CMD_PAUSE      = 0x0E
    _CMD_RESUME     = 0x0D
    _CMD_RESET      = 0x0C

    def __init__(self):
        self._volume = 20
        self._playing = None
        try:
            import serial
            self._ser = serial.Serial(UART_PORT, UART_BAUD, timeout=1)
            time.sleep(0.5)
            self._stub = False
            self._send(self._CMD_RESET)
            time.sleep(1.0)          # DFPlayer needs ~1 s after reset
            self._send(self._CMD_SET_VOLUME, 0, self._volume)
            print(f'[dfplayer] connected on {UART_PORT}')
        except Exception as e:
            self._stub = True
            print(f'[dfplayer] stub mode — {e}')

    # ── Serial protocol ────────────────────────────────────────────────────

    def _send(self, cmd, p1=0, p2=0):
        if self._stub:
            print(f'[dfplayer] CMD 0x{cmd:02X} p1={p1} p2={p2}')
            return
        cs = _checksum([0xFF, 0x06, cmd, 0x00, p1, p2])
        packet = bytes([
            0x7E, 0xFF, 0x06, cmd, 0x00,
            p1, p2,
            (cs >> 8) & 0xFF, cs & 0xFF,
            0xEF,
        ])
        self._ser.write(packet)
        time.sleep(0.05)

    # ── Device interface ───────────────────────────────────────────────────

    def get_state(self):
        return {'playing': self._playing, 'volume': self._volume, 'stub': self._stub}

    def execute(self, cmd, **kwargs):
        if cmd == 'play':
            track  = max(1, min(255, int(kwargs.get('track',  1))))
            volume = max(0, min(30,  int(kwargs.get('volume', self._volume))))
            if volume != self._volume:
                self._send(self._CMD_SET_VOLUME, 0, volume)
                self._volume = volume
            self._send(self._CMD_PLAY_TRACK, 0, track)
            self._playing = track
            return {'playing': track, 'volume': volume}

        if cmd == 'stop':
            self._send(self._CMD_STOP)
            self._playing = None
            return {'stopped': True}

        if cmd == 'pause':
            self._send(self._CMD_PAUSE)
            return {'paused': True}

        if cmd == 'resume':
            self._send(self._CMD_RESUME)
            return {'resumed': True}

        if cmd == 'volume':
            vol = max(0, min(30, int(kwargs.get('volume', 20))))
            self._send(self._CMD_SET_VOLUME, 0, vol)
            self._volume = vol
            return {'volume': vol}

        raise ValueError(f'Unknown command: {cmd}')

    def close(self):
        if not self._stub:
            try:
                self._send(self._CMD_STOP)
                time.sleep(0.1)
                self._ser.close()
            except Exception:
                pass
