"""MAX7219 7-segment / LED matrix display module for GameForge hardware_service.

Hardware connection (Raspberry Pi SPI):
  MAX7219 VCC  → 5V (pin 2 or 4)
  MAX7219 GND  → GND (pin 6)
  MAX7219 DIN  → GPIO 10 / MOSI (pin 19)
  MAX7219 CS   → GPIO 8  / CE0  (pin 24)   [or CE1 on GPIO 7 / pin 26]
  MAX7219 CLK  → GPIO 11 / SCLK (pin 23)

Requires SPI enabled:  sudo raspi-config → Interfaces → SPI → Enable
Library:  pip3 install luma.led_matrix

Configurable:
  SPI_PORT   — SPI bus (0)
  SPI_DEVICE — chip select (0 = CE0, 1 = CE1)
  CASCADED   — number of MAX7219 modules daisy-chained
  DISPLAY_TYPE — 'sevensegment' (7-seg digits) or 'matrix' (8×8 pixels)
"""

SPI_PORT     = 0
SPI_DEVICE   = 0
CASCADED     = 1
DISPLAY_TYPE = 'matrix'   # 'matrix' (8×8 pixels) or 'sevensegment' (7-seg digits)

MANIFEST = {
    'type':  'max7219',
    'label': 'MAX7219 Display',
}


def get_components():
    return [{
        'type':          'max7219',
        'label':         'MAX7219 Display',
        'subtitle':      '7-segment / matrix',
        'category':      'output',
        'color':         '#f97316',
        'icon':          '📟',
        'display_param': 'name',
        'params': [
            {
                'key': 'digits', 'label': 'Digits', 'type': 'select', 'default': 2,
                'options': [
                    {'value': 2, 'label': '2 digits'},
                    {'value': 4, 'label': '4 digits'},
                    {'value': 8, 'label': '8 digits'},
                ],
            },
            {'key': 'intensity', 'label': 'Brightness (0-15)', 'type': 'number',
             'default': 8, 'min': 0, 'max': 15},
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'display'},
        ],
        'inputs': [
            {'key': 'value', 'label': 'Show Number'},
            {'key': 'text',  'label': 'Show Text'},
            {'key': 'clear', 'label': 'Clear'},
        ],
        'outputs': [],
    }]


def _make_device(intensity=8):
    from luma.core.interface.serial import spi, noop
    from luma.led_matrix.device import max7219
    serial_if = spi(port=SPI_PORT, device=SPI_DEVICE, gpio=noop())
    dev = max7219(serial_if, cascaded=CASCADED, block_orientation=0, rotate=0)
    dev.contrast(intensity * 16)    # luma uses 0-255; scale 0-15 → 0-240
    return dev


class Device:
    def __init__(self):
        self._intensity = 8
        try:
            self._dev  = _make_device(self._intensity)
            self._stub = False
            self._dev.text = '  '   # blank on startup
            print(f'[max7219] connected — {DISPLAY_TYPE}, {CASCADED} module(s)')
        except Exception as e:
            self._dev  = None
            self._stub = True
            print(f'[max7219] stub mode — {e}')

    # ── Helpers ────────────────────────────────────────────────────────────

    def _show(self, text):
        if self._stub:
            print(f'[max7219] show: {text!r}')
            return
        from luma.core.render import canvas
        from luma.core.legacy import text as draw_text
        from luma.core.legacy.font import proportional, TINY_FONT
        with canvas(self._dev) as draw:
            draw_text(draw, (0, 0), str(text), fill='white',
                      font=proportional(TINY_FONT))

    def _clear(self):
        if self._stub:
            print('[max7219] clear')
            return
        self._dev.clear()

    # ── Device interface ───────────────────────────────────────────────────

    def get_state(self):
        return {'stub': self._stub, 'intensity': self._intensity}

    def execute(self, cmd, **kwargs):
        if cmd == 'show':
            raw     = kwargs.get('text', kwargs.get('value', ''))
            digits  = int(kwargs.get('digits', 2))
            # If numeric, zero-pad to digits width; otherwise use as-is
            try:
                num = int(raw)
                text = str(num).zfill(digits)
            except (ValueError, TypeError):
                text = str(raw)
            # Right-align within 8-char field for 7-seg display
            self._show(text.rjust(CASCADED * 8))
            return {'showing': text}

        if cmd == 'clear':
            self._clear()
            return {'cleared': True}

        if cmd == 'brightness':
            level = max(0, min(15, int(kwargs.get('level', 8))))
            self._intensity = level
            if not self._stub:
                self._dev.contrast(level * 16)
            return {'intensity': level}

        raise ValueError(f'Unknown command: {cmd}')

    def close(self):
        if not self._stub and self._dev:
            try:
                self._clear()
            except Exception:
                pass
