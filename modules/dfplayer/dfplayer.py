"""DFPlayer Mini MP3 module for GameForge hardware_service.

Hardware connection (Raspberry Pi):
  The DFPlayer is driven over UART through an FT232R USB-serial adapter, which
  shows up as /dev/ttyUSB*. We address it via its stable /dev/serial/by-id
  symlink so it survives ttyUSB renumbering.
    FT232 TX  → DFPlayer RX   (commands; via 1kΩ resistor recommended)
    FT232 RX  → DFPlayer TX   (status/ACK — optional, fine if left unwired)
    DFPlayer VCC → 5V,  GND → common GND with the adapter
    DFPlayer SPK → speaker (8Ω)
  Note: keep VCC↔GND decoupling modest (a single ~470µF). Stacking several
  large electrolytics causes a big inrush surge at power-up that browns out the
  Pi → USB re-enumerates → playback dies.

SD card file layout:  /MP3/0001.mp3, /MP3/0002.mp3 …  (4-digit names inside a
folder named exactly "MP3"). Track N plays /MP3/NNNN.mp3 *by filename* via the
0x12 command — robust against SD copy order, unlike the old 0x03 "play index".

Self-healing: the serial handle is reopened automatically on write failure
(e.g. after a USB re-enumeration), so no hardware-service restart is needed when
the adapter is replugged or the box is rewired.

Configurable:
  UART_PORT — explicit serial device path override (default: auto-detect)
  UART_BAUD — baud rate (DFPlayer default: 9600)
"""

import glob
import time


def _find_port():
    """Locate the USB-serial adapter the DFPlayer is wired to.

    Prefer a stable /dev/serial/by-id symlink (survives ttyUSB renumbering);
    fall back to the first /dev/ttyUSB*. The Denkovi relay board uses pylibftdi
    and claims its FTDI chip directly, so it does not appear as a ttyUSB here.
    Set UART_PORT to an explicit path to override.
    """
    by_id = sorted(glob.glob('/dev/serial/by-id/*'))
    if by_id:
        return by_id[0]
    tty = sorted(glob.glob('/dev/ttyUSB*'))
    return tty[0] if tty else '/dev/ttyUSB0'


UART_PORT = None           # set to an explicit path to override auto-detection
UART_BAUD = 9600

MANIFEST = {
    'type':  'dfplayer',
    'label': 'DFPlayer Mini',
}


def _resolve_port():
    """Port to (re)open: explicit override if set, otherwise re-detect live."""
    return UART_PORT or _find_port()


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
            {'key': 'track',      'label': 'Track',         'type': 'number', 'default': 1,  'min': 1, 'max': 255,
             'description': 'Which MP3 to play, by filename on the SD card (/MP3/0001.mp3 … 0255.mp3). E.g. 1 plays 0001.mp3.'},
            {'key': 'volume',     'label': 'Volume (0-30)', 'type': 'number', 'default': 20, 'min': 0, 'max': 30,
             'description': 'Playback volume from 0 (silent) to 30 (max). E.g. 20.'},
            {'key': 'duration_s', 'label': 'Duration (s)',  'type': 'number', 'default': 0,
             'description': 'Clip length in seconds — the Done output fires after this. Set it to your audio file length. 0 = never fire Done.'},
            {'key': 'name',       'label': 'Label',         'type': 'text',   'default': 'speaker',
             'description': 'Display name shown on the card. E.g. speaker.'},
        ],
        'inputs': [
            {'key': 'trigger', 'label': 'Play Track', 'description': 'Plays the configured track at the configured volume'},
            {'key': 'stop',    'label': 'Stop',       'description': 'Stops playback immediately and cancels any pending Done'},
        ],
        'outputs': [
            {'key': 'done', 'label': 'Done', 'description': 'Fires after Duration seconds — set Duration to the length of your audio clip'},
        ],
    }]


def _checksum(data):
    return (-sum(data)) & 0xFFFF


class Device:
    # DFPlayer serial command bytes
    _CMD_PLAY_MP3   = 0x12   # play /MP3/NNNN.mp3 by filename (robust; not copy order)
    _CMD_SET_VOLUME = 0x06
    _CMD_STOP       = 0x16
    _CMD_PAUSE      = 0x0E
    _CMD_RESUME     = 0x0D
    _CMD_RESET      = 0x0C

    def __init__(self):
        self._volume = 20
        self._playing = None
        self._ser = None      # open serial handle, or None when disconnected
        self._stub = False    # True only when pyserial itself is unavailable
        try:
            import serial  # noqa: F401
        except Exception as e:
            self._stub = True
            print(f'[dfplayer] stub mode — pyserial not available ({e})')
            return
        # Try once now; if the device is absent it stays disconnected and the
        # first play command will reopen it. No hard failure at boot.
        self._open()

    # ── Serial protocol ────────────────────────────────────────────────────

    def _packet(self, cmd, p1=0, p2=0):
        cs = _checksum([0xFF, 0x06, cmd, 0x00, p1, p2])
        return bytes([
            0x7E, 0xFF, 0x06, cmd, 0x00,
            p1, p2,
            (cs >> 8) & 0xFF, cs & 0xFF,
            0xEF,
        ])

    def _open(self):
        """(Re)open the serial port via the live by-id path. Returns True on success."""
        if self._stub:
            return False
        import serial
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        port = _resolve_port()
        try:
            ser = serial.Serial(port, UART_BAUD, timeout=1)
            time.sleep(0.5)
            ser.write(self._packet(self._CMD_RESET))
            time.sleep(1.0)                                   # DFPlayer needs ~1 s after reset
            ser.write(self._packet(self._CMD_SET_VOLUME, 0, self._volume))
            time.sleep(0.05)
            self._ser = ser
            print(f'[dfplayer] connected on {port}')
            return True
        except Exception as e:
            self._ser = None
            print(f'[dfplayer] open failed on {port} — {e}')
            return False

    def _write(self, packet):
        """Write raw bytes; drop the handle on error so the next call reopens."""
        if self._ser is None:
            return False
        try:
            self._ser.write(packet)
            time.sleep(0.05)
            return True
        except Exception as e:
            print(f'[dfplayer] serial write error ({e}) — will reconnect')
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
            return False

    def _send(self, cmd, p1=0, p2=0):
        if self._stub:
            print(f'[dfplayer] CMD 0x{cmd:02X} p1={p1} p2={p2}')
            return
        packet = self._packet(cmd, p1, p2)
        # Ensure a handle exists (reopen if disconnected), then write with one
        # reconnect-and-retry on failure (covers USB re-enumeration mid-session).
        if self._ser is None:
            self._open()
        if self._write(packet):
            return
        if self._open() and self._write(packet):
            return
        print(f'[dfplayer] CMD 0x{cmd:02X} dropped — device unavailable')

    # ── Device interface ───────────────────────────────────────────────────

    def get_state(self):
        return {
            'playing':   self._playing,
            'volume':    self._volume,
            'stub':      self._stub,
            'connected': self._ser is not None,
        }

    def execute(self, cmd, **kwargs):
        if cmd == 'play':
            track  = max(1, min(255, int(kwargs.get('track',  1))))
            volume = max(0, min(30,  int(kwargs.get('volume', self._volume))))
            if volume != self._volume:
                self._send(self._CMD_SET_VOLUME, 0, volume)
                self._volume = volume
            self._send(self._CMD_PLAY_MP3, (track >> 8) & 0xFF, track & 0xFF)
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
        if self._ser is not None:
            try:
                self._ser.write(self._packet(self._CMD_STOP))
                time.sleep(0.1)
                self._ser.close()
            except Exception:
                pass
            self._ser = None
