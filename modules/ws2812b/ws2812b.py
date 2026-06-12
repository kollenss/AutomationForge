#!/usr/bin/env python3
"""
WS2812B Addressable LED Strip — GameForge hardware module.

Drives a WS2812B LED strip via rpi_ws281x (PCM-DMA, GPIO21).
Multiple canvas cards (LED Zone) can control independent zones of the
same physical strip by passing first_led / last_led per command.

Wiring:
    GPIO21 (Pin 40) — DIN   (data in, first LED in chain)
    5V  ────────── — VCC
    GND ────────── — GND
    DOUT of last LED is not connected (end of chain)

Zone layout (Diamond Heist default):
    Index 0–2  → Floor 1  (3 LEDs)
    Index 3–5  → Floor 2  (3 LEDs)
    Index 6–9  → Floor 3  (4 LEDs — diamond illumination)

To adapt for a different project:
    - Change MANIFEST['led_count'] and MANIFEST['gpio_pin'] if needed.
    - Redefine zones on the GameForge canvas — no code change required.
"""

import threading
import time

try:
    from rpi_ws281x import PixelStrip, Color
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False
    print('[ws2812b] rpi_ws281x not installed — running in stub mode')

MANIFEST = {
    'type':      'ws2812b',
    'label':     'WS2812B LED Strip',
    'led_count': 10,
    'gpio_pin':  21,
}


# ── Colour helpers ─────────────────────────────────────────────────────────────

_NAMED_COLORS = {
    'red':    (255,   0,   0),
    'green':  (  0, 255,   0),
    'blue':   (  0,   0, 255),
    'white':  (255, 255, 255),
    'yellow': (255, 220,   0),
    'orange': (255, 110,   0),
    'purple': (140,   0, 255),
    'cyan':   (  0, 255, 200),
    'pink':   (255,  20, 120),
    'off':    (  0,   0,   0),
}


def _parse_color(s):
    """Parse a colour string to an (r, g, b) tuple.

    Accepts named colours ('red', 'off', etc.), CSS hex ('#FF0000'), or
    bare hex ('FF0000'). Falls back to white on unrecognised input.
    """
    s = str(s).strip().lower()
    if s in _NAMED_COLORS:
        return _NAMED_COLORS[s]
    s = s.lstrip('#')
    if len(s) == 6:
        try:
            return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
        except ValueError:
            pass
    return (255, 255, 255)


def _scale(rgb, brightness):
    """Multiply each channel by brightness (0–255) and return a new tuple."""
    f = brightness / 255.0
    return (int(rgb[0] * f), int(rgb[1] * f), int(rgb[2] * f))


def _wheel(pos):
    """Map 0–255 position to a rainbow (r, g, b) colour."""
    pos = pos % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


# ── Component definition returned to GameForge ─────────────────────────────────

def get_components():
    return [{
        'type':          'led_zone',
        'label':         'LED Zone',
        'subtitle':      'WS2812B addressable',
        'color':         '#f59e0b',
        'icon':          '💡',
        'display_param': 'name',
        'params': [
            {'key': 'name',          'label': 'Zone Name',     'type': 'text',   'default': 'LEDs'},
            {'key': 'gpio_pin',      'label': 'GPIO Pin',      'type': 'number', 'default': 21},
            {'key': 'led_count',     'label': 'Total LEDs',    'type': 'number', 'default': 10},
            {'key': 'first_led',     'label': 'First Index',   'type': 'number', 'default': 0},
            {'key': 'last_led',      'label': 'Last Index',    'type': 'number', 'default': 2},
            {'key': 'default_color', 'label': 'Default Color', 'type': 'text',   'default': 'white'},
            {'key': 'brightness',    'label': 'Brightness',    'type': 'number', 'default': 128},
        ],
        'inputs': [
            {'key': 'set_color', 'label': 'Set Color',
             'description': 'Static colour — value string overrides Default Color param'},
            {'key': 'blink',     'label': 'Blink',
             'description': 'Blink N times then restore — value = count (default 3). Done fires when complete.'},
            {'key': 'pulse',     'label': 'Pulse',
             'description': 'Breathing animation — runs until Off. Done fires immediately on start.'},
            {'key': 'chase',     'label': 'Chase',
             'description': 'Fill LEDs one by one left→right. Done fires when last LED is lit.'},
            {'key': 'rainbow',   'label': 'Rainbow',
             'description': 'Rainbow cycle — runs until Off. Done fires immediately on start.'},
            {'key': 'off',       'label': 'Off',
             'description': 'Turn off all LEDs in this zone.'},
        ],
        'outputs': [
            {'key': 'done', 'label': 'Done',
             'description': 'Fires when the command or animation completes'},
        ],
    }]


# ── Strip singleton (one PixelStrip per GPIO pin) ──────────────────────────────

_strips      = {}
_strips_lock = threading.Lock()


def _get_strip(gpio_pin, led_count):
    """Return (or lazily create) the PixelStrip for this GPIO pin."""
    with _strips_lock:
        if gpio_pin not in _strips:
            if _HW_AVAILABLE:
                strip = PixelStrip(led_count, gpio_pin)
                strip.begin()
            else:
                strip = None
            _strips[gpio_pin] = strip
        return _strips[gpio_pin]


# ── Device ─────────────────────────────────────────────────────────────────────

class Device:
    """Manages all LED commands for one WS2812B strip.

    Zone boundaries (first_led, last_led) are passed per-command so that
    any number of canvas cards can control independent zones without any
    pre-registration — just configure on the canvas and wire it up.
    """

    def __init__(self):
        self._strip = _get_strip(MANIFEST['gpio_pin'], MANIFEST['led_count'])
        # cancel events keyed by (first_led, last_led) to stop running animations
        self._cancel      = {}
        self._cancel_lock = threading.Lock()
        # last static colour per zone — used by blink to restore after flashing
        self._zone_color  = {}   # (first, last) → (r, g, b)
        # Clear strip on startup
        if self._strip:
            self._clear_all()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _clear_all(self):
        for i in range(MANIFEST['led_count']):
            self._strip.setPixelColor(i, Color(0, 0, 0))
        self._strip.show()

    def _stop_zone(self, first, last):
        """Signal any running animation on this zone to stop."""
        with self._cancel_lock:
            ev = self._cancel.pop((first, last), None)
        if ev:
            ev.set()

    def _new_cancel(self, first, last):
        """Register a fresh cancel event for a new animation."""
        ev = threading.Event()
        with self._cancel_lock:
            self._cancel[(first, last)] = ev
        return ev

    def _set_zone(self, first, last, rgb, brightness):
        """Paint all pixels in [first, last] with rgb scaled by brightness."""
        if not self._strip:
            return
        r, g, b = _scale(rgb, brightness)
        c = Color(r, g, b)
        for i in range(first, last + 1):
            self._strip.setPixelColor(i, c)
        self._strip.show()

    def _off_zone(self, first, last):
        self._set_zone(first, last, (0, 0, 0), 255)

    def _extract(self, params):
        """Pull zone + colour params from a command dict."""
        first      = int(params.get('first_led', 0))
        last       = int(params.get('last_led', 2))
        brightness = int(params.get('brightness', 128))
        color_raw  = params.get('color') or params.get('default_color', 'white')
        rgb        = _parse_color(color_raw)
        return first, last, brightness, rgb

    # ── Commands (called by hardware_service via POST /hardware/ws2812b/<cmd>) ─

    def set_color(self, params):
        """Set zone to a static colour immediately."""
        first, last, brightness, rgb = self._extract(params)
        self._stop_zone(first, last)
        self._zone_color[(first, last)] = rgb
        self._set_zone(first, last, rgb, brightness)
        return {'ok': True}

    def off(self, params):
        """Turn off all LEDs in the zone."""
        first = int(params.get('first_led', 0))
        last  = int(params.get('last_led', 2))
        self._stop_zone(first, last)
        self._off_zone(first, last)
        return {'ok': True}

    def blink(self, params):
        """Blink N times then restore the previous colour. Blocks until done."""
        first, last, brightness, rgb = self._extract(params)
        count  = max(1, int(params.get('count', 3)))
        on_ms  = float(params.get('on_ms',  300)) / 1000
        off_ms = float(params.get('off_ms', 300)) / 1000
        self._stop_zone(first, last)
        restore = self._zone_color.get((first, last), (0, 0, 0))
        for _ in range(count):
            self._set_zone(first, last, rgb, brightness)
            time.sleep(on_ms)
            self._off_zone(first, last)
            time.sleep(off_ms)
        if restore != (0, 0, 0):
            self._set_zone(first, last, restore, brightness)
        return {'ok': True}

    def pulse(self, params):
        """Start a breathing animation. Non-blocking — returns immediately."""
        first, last, brightness, rgb = self._extract(params)
        self._stop_zone(first, last)
        cancel = self._new_cancel(first, last)
        step   = 6

        def _run():
            while not cancel.is_set():
                for b in list(range(20, brightness, step)) + list(range(brightness, 20, -step)):
                    if cancel.is_set():
                        break
                    self._set_zone(first, last, rgb, b)
                    time.sleep(0.03)
            self._off_zone(first, last)

        threading.Thread(target=_run, daemon=True).start()
        return {'ok': True}

    def chase(self, params):
        """Light LEDs one by one from first to last. Blocks until complete."""
        first, last, brightness, rgb = self._extract(params)
        delay = float(params.get('delay_ms', 80)) / 1000
        self._stop_zone(first, last)
        self._off_zone(first, last)
        if self._strip:
            r, g, b = _scale(rgb, brightness)
            c = Color(r, g, b)
            for i in range(first, last + 1):
                self._strip.setPixelColor(i, c)
                self._strip.show()
                time.sleep(delay)
        self._zone_color[(first, last)] = rgb
        return {'ok': True}

    def rainbow(self, params):
        """Start a rainbow cycle. Non-blocking — returns immediately."""
        first, last, brightness, _ = self._extract(params)
        self._stop_zone(first, last)
        cancel    = self._new_cancel(first, last)
        zone_size = max(1, last - first + 1)
        spread    = 256 // zone_size

        def _run():
            offset = 0
            while not cancel.is_set():
                if self._strip:
                    for i in range(first, last + 1):
                        pos = (offset + (i - first) * spread) % 256
                        r, g, b = _scale(_wheel(pos), brightness)
                        self._strip.setPixelColor(i, Color(r, g, b))
                    self._strip.show()
                offset = (offset + 2) % 256
                time.sleep(0.02)
            self._off_zone(first, last)

        threading.Thread(target=_run, daemon=True).start()
        return {'ok': True}

    def execute(self, cmd, **kwargs):
        """Dispatch hardware_service calls to the right method.

        hardware_service always calls device.execute(cmd, **body_kwargs).
        We forward to self.set_color(kwargs), self.blink(kwargs), etc.
        """
        method = getattr(self, cmd, None)
        if method is None:
            raise ValueError(f'[ws2812b] unknown command: {cmd}')
        return method(kwargs)

    def get_state(self):
        return {
            'connected': _HW_AVAILABLE,
            'led_count': MANIFEST['led_count'],
            'gpio_pin':  MANIFEST['gpio_pin'],
        }
