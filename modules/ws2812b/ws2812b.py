#!/usr/bin/env python3
"""
WS2812B Addressable LED Strip — GameForge hardware module.

All strip access runs in a single dedicated worker thread (init + instant
commands). Looping animations (rainbow, pulse) run in their own daemon
threads so the worker stays free to process new commands like 'off'.

Wiring:
    GPIO21 (Pin 40) — DIN
    5V              — VCC
    GND             — GND
"""

import queue
import threading
import time

try:
    from rpi_ws281x import PixelStrip, Color
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False
    print('[ws2812b] rpi_ws281x not installed — stub mode')

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
    f = brightness / 255.0
    return (int(rgb[0] * f), int(rgb[1] * f), int(rgb[2] * f))

def _wheel(pos):
    pos = pos % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)

# ── GameForge component definition ────────────────────────────────────────────

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
            {'key': 'set_color', 'label': 'Set Color',    'description': 'Static colour'},
            {'key': 'blink',     'label': 'Blink',        'description': 'Blink N times then restore'},
            {'key': 'pulse',     'label': 'Pulse',        'description': 'Breathing animation — runs until Off'},
            {'key': 'chase',     'label': 'Chase',        'description': 'Fill LEDs one by one left→right'},
            {'key': 'rainbow',   'label': 'Rainbow',      'description': 'Rainbow cycle — runs until Off'},
            {'key': 'off',       'label': 'Off',          'description': 'Turn off all LEDs in this zone'},
        ],
        'outputs': [
            {'key': 'done', 'label': 'Done', 'description': 'Fires when command or animation completes'},
        ],
    }]

# ── Device ─────────────────────────────────────────────────────────────────────

class Device:
    """
    Worker thread owns all strip writes (thread-safety for rpi_ws281x).
    Looping animations (rainbow, pulse) run in separate daemon threads and
    check a cancel event — so 'off' or any new command stops them promptly.

    Key constraint: PixelStrip.begin() must be called from the main thread
    (rpi_ws281x uses DMA + signal handlers that break in daemon threads).
    __init__ therefore initializes the strip synchronously before starting
    the worker thread.
    """

    def __init__(self):
        self._strip       = None
        self._strip_lock  = threading.Lock()
        self._cmd_queue   = queue.Queue()
        self._cancel_ev   = {}
        self._cancel_lock = threading.Lock()
        self._zone_color  = {}

        # Init strip in calling thread (rpi_ws281x DMA requires main thread context)
        if _HW_AVAILABLE:
            try:
                self._strip = PixelStrip(MANIFEST['led_count'], MANIFEST['gpio_pin'])
                self._strip.begin()
                self._clear_all()
                print('[ws2812b] strip ready on GPIO', MANIFEST['gpio_pin'])
            except Exception as e:
                print(f'[ws2812b] strip init failed: {e}')

        threading.Thread(target=self._worker, daemon=True, name='ws2812b-worker').start()

    def _worker(self):
        while True:
            try:
                cmd, params = self._cmd_queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self._dispatch(cmd, params)
            except Exception as e:
                print(f'[ws2812b] error in {cmd}: {e}')

    def _dispatch(self, cmd, params):
        first, last, brightness, rgb = self._extract(params)
        zone = (first, last)
        self._stop_zone(zone)          # cancel any running animation first

        if cmd == 'off':
            self._set_zone(first, last, (0, 0, 0), 255)

        elif cmd == 'set_color':
            self._zone_color[zone] = rgb
            self._set_zone(first, last, rgb, brightness)

        elif cmd == 'blink':
            count   = max(1, int(params.get('count', 3)))
            on_s    = float(params.get('on_ms',  300)) / 1000
            off_s   = float(params.get('off_ms', 300)) / 1000
            restore = self._zone_color.get(zone, (0, 0, 0))
            for _ in range(count):
                self._set_zone(first, last, rgb, brightness)
                time.sleep(on_s)
                self._set_zone(first, last, (0, 0, 0), 255)
                time.sleep(off_s)
            if restore != (0, 0, 0):
                self._set_zone(first, last, restore, brightness)

        elif cmd == 'chase':
            delay = float(params.get('delay_ms', 80)) / 1000
            self._set_zone(first, last, (0, 0, 0), 255)
            if self._strip:
                r, g, b = _scale(rgb, brightness)
                c = Color(r, g, b)
                with self._strip_lock:
                    for i in range(first, last + 1):
                        self._strip.setPixelColor(i, c)
                        self._strip.show()
                        time.sleep(delay)
            self._zone_color[zone] = rgb

        elif cmd == 'pulse':
            cancel = self._new_cancel(zone)
            def _pulse(cancel=cancel, first=first, last=last, rgb=rgb, brightness=brightness):
                step = 6
                while not cancel.is_set():
                    for b in list(range(20, brightness, step)) + list(range(brightness, 20, -step)):
                        if cancel.is_set():
                            break
                        self._set_zone(first, last, rgb, b)
                        time.sleep(0.03)
                self._set_zone(first, last, (0, 0, 0), 255)
            threading.Thread(target=_pulse, daemon=True).start()

        elif cmd == 'rainbow':
            cancel = self._new_cancel(zone)
            def _rainbow(cancel=cancel, first=first, last=last, brightness=brightness):
                zone_size = max(1, last - first + 1)
                spread    = 256 // zone_size
                offset    = 0
                while not cancel.is_set():
                    if self._strip:
                        with self._strip_lock:
                            for i in range(first, last + 1):
                                pos = (offset + (i - first) * spread) % 256
                                r, g, b = _scale(_wheel(pos), brightness)
                                self._strip.setPixelColor(i, Color(r, g, b))
                            self._strip.show()
                    offset = (offset + 2) % 256
                    time.sleep(0.02)
                self._set_zone(first, last, (0, 0, 0), 255)
            threading.Thread(target=_rainbow, daemon=True).start()

    # ── Strip helpers ──────────────────────────────────────────────────────────

    def _clear_all(self):
        if not self._strip:
            return
        with self._strip_lock:
            for i in range(MANIFEST['led_count']):
                self._strip.setPixelColor(i, Color(0, 0, 0))
            self._strip.show()

    def _set_zone(self, first, last, rgb, brightness):
        if not self._strip:
            return
        r, g, b = _scale(rgb, brightness)
        c = Color(r, g, b)
        with self._strip_lock:
            for i in range(first, last + 1):
                self._strip.setPixelColor(i, c)
            self._strip.show()

    def _stop_zone(self, zone):
        with self._cancel_lock:
            ev = self._cancel_ev.pop(zone, None)
        if ev:
            ev.set()

    def _new_cancel(self, zone):
        ev = threading.Event()
        with self._cancel_lock:
            self._cancel_ev[zone] = ev
        return ev

    def _extract(self, params):
        first      = int(params.get('first_led', 0))
        last       = int(params.get('last_led',  0))
        brightness = int(params.get('brightness', 128))
        color_raw  = params.get('color') or params.get('default_color', 'white')
        rgb        = _parse_color(color_raw)
        return first, last, brightness, rgb

    # ── Public API ─────────────────────────────────────────────────────────────

    def _enqueue(self, cmd, params):
        self._cmd_queue.put((cmd, params))
        return {'ok': True}

    def set_color(self, params): return self._enqueue('set_color', params)
    def off(self,       params): return self._enqueue('off',       params)
    def blink(self,     params): return self._enqueue('blink',     params)
    def pulse(self,     params): return self._enqueue('pulse',     params)
    def chase(self,     params): return self._enqueue('chase',     params)
    def rainbow(self,   params): return self._enqueue('rainbow',   params)

    def execute(self, cmd, **kwargs):
        method = getattr(self, cmd, None)
        if method is None:
            raise ValueError(f'[ws2812b] unknown command: {cmd}')
        return method(kwargs)

    def get_state(self):
        return {
            'connected': _HW_AVAILABLE and self._strip is not None,
            'led_count': MANIFEST['led_count'],
            'gpio_pin':  MANIFEST['gpio_pin'],
        }
