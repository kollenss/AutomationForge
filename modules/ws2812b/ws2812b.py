#!/usr/bin/env python3
"""
WS2812B Addressable LED Strip — GameForge hardware module.

Drives a WS2812B LED strip via rpi_ws281x (PCM-DMA, GPIO21).
Multiple canvas cards (LED Zone) can control independent zones of the
same physical strip by giving each card a "LEDs in Zone" spec
(1-based, e.g. "1-2", "1,3", or combined "1-3,5").

Wiring:
    GPIO21 (Pin 40) — DIN   (data in, first LED in chain)
    5V  ────────── — VCC
    GND ────────── — GND
    DOUT of last LED is not connected (end of chain)

Zone layout (Diamond Heist default, 1-based as written on the card):
    LEDs 1–3   → Floor 1  (3 LEDs)
    LEDs 4–6   → Floor 2  (3 LEDs)
    LEDs 7–10  → Floor 3  (4 LEDs — diamond illumination)

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
    'led_count': 2,    # TILLFÄLLIGT: bara 2 LED inkopplade just nu (full build = 10)
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


def _parse_leds(spec, led_count):
    """Parse a 1-based LED spec into a sorted list of 0-based physical indices.

    Accepts comma-separated values and ranges, combinable:
        "1-2"  → [0, 1]
        "1,3"  → [0, 2]
        "1-3,5"→ [0, 1, 2, 4]
    Indices outside the strip (1..led_count) are silently dropped.
    """
    out = set()
    for part in str(spec).replace(' ', '').split(','):
        if not part:
            continue
        if '-' in part:
            a, _, b = part.partition('-')
            try:
                lo, hi = int(a), int(b)
            except ValueError:
                continue
            if lo > hi:
                lo, hi = hi, lo
            for n in range(lo, hi + 1):
                out.add(n - 1)
        else:
            try:
                out.add(int(part) - 1)
            except ValueError:
                continue
    return sorted(i for i in out if 0 <= i < led_count)


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
            {'key': 'leds',          'label': 'LEDs in Zone',  'type': 'text',   'default': '1-2'},
            {'key': 'default_color', 'label': 'Default Color', 'type': 'text',   'default': 'white'},
            {'key': 'brightness',    'label': 'Brightness',    'type': 'number', 'default': 128},
        ],
        'inputs': [
            {'key': 'set_color', 'label': 'Set Color',
             'description': 'Static colour — value string overrides Default Color param'},
            {'key': 'blink',     'label': 'Blink',
             'description': 'Blink then restore — numeric value = count (default 3), colour string = blink colour. Done fires when complete.'},
            {'key': 'pulse',     'label': 'Pulse',
             'description': 'Breathing animation — colour string sets the colour. Runs until Off. Done fires immediately on start.'},
            {'key': 'chase',     'label': 'Chase',
             'description': 'A single lit pixel sweeps back and forth through the zone (scanner). Runs until Off.'},
            {'key': 'fill',      'label': 'Fill',
             'description': 'Light the zone one LED at a time in order; each stays on. Done fires when the last LED is lit.'},
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
        # running animations keyed by zone: key → (cancel Event, Thread)
        self._anim       = {}
        self._anim_lock  = threading.Lock()
        # last static colour per zone — used by blink to restore after flashing
        self._zone_color = {}   # zone key → (r, g, b)
        # Clear strip on startup
        if self._strip:
            self._clear_all()

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _clear_all(self):
        for i in range(MANIFEST['led_count']):
            self._strip.setPixelColor(i, Color(0, 0, 0))
        self._strip.show()

    def _stop_zone(self, key):
        """Stop any running animation on this zone and wait for it to exit.

        Joining the animation thread before returning guarantees it won't
        write to the strip after the caller sets the zone's next state —
        otherwise a cancelled animation's final frame could clobber it.
        """
        with self._anim_lock:
            entry = self._anim.pop(key, None)
        if entry:
            cancel, thread = entry
            cancel.set()
            if thread.is_alive() and thread is not threading.current_thread():
                thread.join(timeout=1.0)

    def _start_anim(self, key, run):
        """Replace any animation on this zone with a new one.

        `run` is called as run(cancel) in a daemon thread and must return
        promptly once cancel is set. The thread does not turn the zone off
        on exit — the command that stops it owns the next state.
        """
        self._stop_zone(key)
        cancel = threading.Event()
        thread = threading.Thread(target=run, args=(cancel,), daemon=True)
        with self._anim_lock:
            self._anim[key] = (cancel, thread)
        thread.start()

    def _set_zone(self, leds, rgb, brightness):
        """Paint every pixel in `leds` with rgb scaled by brightness."""
        if not self._strip:
            return
        r, g, b = _scale(rgb, brightness)
        c = Color(r, g, b)
        for i in leds:
            self._strip.setPixelColor(i, c)
        self._strip.show()

    def _off_zone(self, leds):
        self._set_zone(leds, (0, 0, 0), 255)

    def _extract(self, params):
        """Pull zone + colour params from a command dict.

        Returns (leds, key, brightness, rgb) where `leds` is a list of
        0-based physical indices and `key` is a hashable zone identity.
        """
        spec = params.get('leds')
        if spec not in (None, ''):
            leds = _parse_leds(spec, MANIFEST['led_count'])
        else:
            # Legacy nodes saved before the 'leds' field — 0-based range.
            first = int(params.get('first_led', 0))
            last  = int(params.get('last_led', 1))
            leds  = [i for i in range(first, last + 1) if 0 <= i < MANIFEST['led_count']]
        brightness = int(params.get('brightness', 128))
        color_raw  = params.get('color') or params.get('default_color', 'white')
        rgb        = _parse_color(color_raw)
        return leds, tuple(leds), brightness, rgb

    # ── Commands (called by hardware_service via POST /hardware/ws2812b/<cmd>) ─

    def set_color(self, params):
        """Set zone to a static colour immediately."""
        leds, key, brightness, rgb = self._extract(params)
        self._stop_zone(key)
        self._zone_color[key] = rgb
        self._set_zone(leds, rgb, brightness)
        return {'ok': True}

    def off(self, params):
        """Turn off all LEDs in the zone."""
        leds, key, _, _ = self._extract(params)
        self._stop_zone(key)
        self._off_zone(leds)
        return {'ok': True}

    def blink(self, params):
        """Blink N times then restore the previous colour. Blocks until done."""
        leds, key, brightness, rgb = self._extract(params)
        count  = max(1, int(params.get('count', 3)))
        on_ms  = float(params.get('on_ms',  300)) / 1000
        off_ms = float(params.get('off_ms', 300)) / 1000
        self._stop_zone(key)
        restore = self._zone_color.get(key, (0, 0, 0))
        for _ in range(count):
            self._set_zone(leds, rgb, brightness)
            time.sleep(on_ms)
            self._off_zone(leds)
            time.sleep(off_ms)
        if restore != (0, 0, 0):
            self._set_zone(leds, restore, brightness)
        return {'ok': True}

    def pulse(self, params):
        """Start a breathing animation. Non-blocking — returns immediately."""
        leds, key, brightness, rgb = self._extract(params)
        step = 6

        def _run(cancel):
            while not cancel.is_set():
                for b in list(range(20, brightness, step)) + list(range(brightness, 20, -step)):
                    if cancel.is_set():
                        break
                    self._set_zone(leds, rgb, b)
                    time.sleep(0.03)

        self._start_anim(key, _run)
        return {'ok': True}

    def fill(self, params):
        """Light the zone one LED at a time in order; each stays on.

        Blocks until the last LED is lit (a progressive 'reveal' / loading fill).
        """
        leds, key, brightness, rgb = self._extract(params)
        delay = float(params.get('delay_ms', 80)) / 1000
        self._stop_zone(key)
        self._off_zone(leds)
        if self._strip:
            r, g, b = _scale(rgb, brightness)
            c = Color(r, g, b)
            for i in leds:
                self._strip.setPixelColor(i, c)
                self._strip.show()
                time.sleep(delay)
        self._zone_color[key] = rgb
        return {'ok': True}

    def chase(self, params):
        """Sweep a single lit pixel back and forth through the zone (scanner).

        Knight-Rider style. Non-blocking — runs until Off.
        """
        leds, key, brightness, rgb = self._extract(params)
        if not leds:
            self._stop_zone(key)
            return {'ok': True}
        delay = float(params.get('delay_ms', 80)) / 1000
        n     = len(leds)
        # ping-pong over zone positions: 0..n-1 then n-2..1, repeat
        seq = list(range(n)) + list(range(n - 2, 0, -1)) if n > 2 else list(range(n))

        def _run(cancel):
            r, g, b = _scale(rgb, brightness)
            c = Color(r, g, b)
            while not cancel.is_set():
                for pos in seq:
                    if cancel.is_set():
                        break
                    if self._strip:
                        for j, idx in enumerate(leds):
                            self._strip.setPixelColor(idx, c if j == pos else Color(0, 0, 0))
                        self._strip.show()
                    time.sleep(delay)

        self._start_anim(key, _run)
        return {'ok': True}

    def rainbow(self, params):
        """Start a rainbow cycle. Non-blocking — returns immediately."""
        leds, key, brightness, _ = self._extract(params)
        zone_size = max(1, len(leds))
        spread    = 256 // zone_size

        def _run(cancel):
            offset = 0
            while not cancel.is_set():
                if self._strip:
                    for n, i in enumerate(leds):
                        pos = (offset + n * spread) % 256
                        r, g, b = _scale(_wheel(pos), brightness)
                        self._strip.setPixelColor(i, Color(r, g, b))
                    self._strip.show()
                offset = (offset + 2) % 256
                time.sleep(0.02)

        self._start_anim(key, _run)
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
