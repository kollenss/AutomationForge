"""MAX7219 8-digit 7-segment display module for GameForge hardware_service.

Hardware connection (Raspberry Pi SPI0 CE1):
  VCC  → Pin 4  (5V)
  GND  → Pin 25 (GND)
  DIN  → Pin 19 (GPIO 10 / MOSI)
  CLK  → Pin 23 (GPIO 11 / SCLK)
  CS   → Pin 26 (GPIO 7  / CE1)   ← CE1, NOT CE0

Requires SPI enabled:  sudo raspi-config → Interfaces → SPI → Enable
Uses spidev directly (no external library needed).
"""

import time

SPI_BUS    = 0
SPI_DEVICE = 1        # CE1 (GPIO 7, pin 26)
BRIGHTNESS = 8        # 0-15

MANIFEST = {
    'type':  'max7219',
    'label': 'MAX7219 Display',
}

# MAX7219 register addresses
_REG_DECODE_MODE  = 0x09
_REG_INTENSITY    = 0x0A
_REG_SCAN_LIMIT   = 0x0B
_REG_SHUTDOWN     = 0x0C
_REG_DISPLAY_TEST = 0x0F
_BCD_BLANK        = 0x0F   # blank digit in BCD mode
_RAW_BLANK        = 0x00   # blank in raw segment mode

# Segment bits (no-decode): bit7=DP 6=A 5=B 4=C 3=D 2=E 1=F 0=G
_CHAR_MAP = {
    ' ': 0x00, '-': 0x01,
    '0': 0x7E, '1': 0x30, '2': 0x6D, '3': 0x79, '4': 0x33,
    '5': 0x5B, '6': 0x5F, '7': 0x70, '8': 0x7F, '9': 0x7B,
    'A': 0x77, 'B': 0x1F, 'C': 0x4E, 'D': 0x3D, 'E': 0x4F,
    'F': 0x47, 'G': 0x5F, 'H': 0x37, 'I': 0x30, 'J': 0x38,
    'L': 0x0E, 'N': 0x15, 'O': 0x7E, 'P': 0x67, 'R': 0x05,
    'S': 0x5B, 'T': 0x0F, 'U': 0x3E, 'Y': 0x3B,
}


def get_components():
    return [{
        'type':          'max7219',
        'label':         'MAX7219 Display',
        'subtitle':      '7-segment 8-digit',
        'category':      'output',
        'color':         '#f97316',
        'icon':          '📟',
        'display_param': 'name',
        'params': [
            {
                'key': 'pair', 'label': 'Digit pair (0=left … 3=right)',
                'type': 'select', 'default': 0,
                'options': [
                    {'value': 0, 'label': 'Pair 0 (digits 1-2)'},
                    {'value': 1, 'label': 'Pair 1 (digits 3-4)'},
                    {'value': 2, 'label': 'Pair 2 (digits 5-6)'},
                    {'value': 3, 'label': 'Pair 3 (digits 7-8)'},
                ],
            },
            {'key': 'intensity', 'label': 'Brightness (0-15)', 'type': 'number',
             'default': 8, 'min': 0, 'max': 15},
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'display'},
        ],
        'inputs': [
            {'key': 'value', 'label': 'Show Number'},
            {'key': 'text',  'label': 'Show Text (8 chars)'},
            {'key': 'clear', 'label': 'Clear'},
        ],
        'outputs': [],
    }]


class Device:
    def __init__(self):
        try:
            import spidev
            self._spi = spidev.SpiDev()
            self._spi.open(SPI_BUS, SPI_DEVICE)
            self._spi.max_speed_hz = 1_000_000
            self._spi.mode = 0
            self._stub = False
            self._bcd  = True
            self._write(_REG_SHUTDOWN,     0x01)
            self._write(_REG_DISPLAY_TEST, 0x00)
            self._write(_REG_DECODE_MODE,  0xFF)
            self._write(_REG_SCAN_LIMIT,   0x07)
            self._write(_REG_INTENSITY,    BRIGHTNESS)
            self._clear_bcd()
            print('[max7219] connected — SPI0 CE1')
        except Exception as e:
            self._stub = True
            print(f'[max7219] stub mode — {e}')

    # ── SPI protocol ───────────────────────────────────────────────────────

    def _write(self, reg, data):
        if self._stub:
            return
        self._spi.xfer2([reg, data])

    # ── Display helpers ────────────────────────────────────────────────────

    def _ensure_bcd(self):
        if not self._bcd:
            self._write(_REG_DECODE_MODE, 0xFF)
            self._bcd = True

    def _ensure_raw(self):
        if self._bcd:
            self._write(_REG_DECODE_MODE, 0x00)
            self._bcd = False

    def _clear_bcd(self):
        self._ensure_bcd()
        for reg in range(0x01, 0x09):
            self._write(reg, _BCD_BLANK)

    def _show_pair(self, value, pair):
        """Show 0–99 on a digit pair (pair 0 = leftmost)."""
        self._ensure_bcd()
        v        = max(0, min(99, int(value)))
        tens_reg = 0x08 - pair * 2
        ones_reg = 0x07 - pair * 2
        self._write(tens_reg, v // 10)
        self._write(ones_reg, v %  10)

    def _show_text(self, text):
        """Show up to 8 characters in raw segment mode."""
        self._ensure_raw()
        for pos in range(8):
            char = text[pos].upper() if pos < len(text) else ' '
            self._write(0x08 - pos, _CHAR_MAP.get(char, 0x00))

    # ── Device interface ───────────────────────────────────────────────────

    def get_state(self):
        return {'stub': self._stub}

    def execute(self, cmd, **kwargs):
        if cmd == 'show':
            raw   = kwargs.get('text', kwargs.get('value', ''))
            pair  = int(kwargs.get('pair', 0))
            if self._stub:
                print(f'[max7219] show pair={pair} value={raw!r}')
            try:
                self._show_pair(int(raw), pair)
                return {'showing': int(raw), 'pair': pair}
            except (ValueError, TypeError):
                text = str(raw)[:8]
                if self._stub:
                    print(f'[max7219] show_text {text!r}')
                else:
                    self._show_text(text)
                return {'showing': text}

        if cmd == 'text':
            text = str(kwargs.get('text', ''))[:8]
            if self._stub:
                print(f'[max7219] text {text!r}')
            else:
                self._show_text(text)
            return {'showing': text}

        if cmd == 'clear':
            if self._stub:
                print('[max7219] clear')
            else:
                self._clear_bcd()
            return {'cleared': True}

        if cmd == 'brightness':
            level = max(0, min(15, int(kwargs.get('level', 8))))
            self._write(_REG_INTENSITY, level)
            return {'intensity': level}

        raise ValueError(f'Unknown command: {cmd}')

    def close(self):
        if not self._stub:
            try:
                self._clear_bcd()
                self._write(_REG_SHUTDOWN, 0x00)
                self._spi.close()
            except Exception:
                pass
