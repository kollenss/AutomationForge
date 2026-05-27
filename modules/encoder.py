#!/usr/bin/env python3
"""Rotary encoder module — KY-040 via pigpio.

FALLING_EDGE på CLK + tidsbaserad debounce.

KY-040 är konstruerad så att DT alltid hinner sätta sig innan CLK faller,
vilket ger riktningen:
  CLK faller, DT=1 → medsols   (+1)
  CLK faller, DT=0 → motsols   (-1)

Debounce (default 3 ms) filtrerar CLK-studsar utan att tappa sanna hack.

CW-sekvens:  11 → 01 (CLK faller, DT=1 → +1) → 00 → 10 → 11
CCW-sekvens: 11 → 10 → 00 (CLK faller, DT=0 → -1) → 01 → 11

Usage:
    from encoder import RotaryEncoder
    enc = RotaryEncoder(pi, clk_pin=17, dt_pin=27, callback=on_step)
    enc.cancel()
"""

import time
import pigpio


class RotaryEncoder:
    def __init__(self, pi, clk_pin: int, dt_pin: int, callback,
                 debounce_ms: float = 3.0):
        """
        pi          — pigpio.pi() instance
        clk_pin     — KY-040 CLK  (Rad-pos 6 · Pin 11 · GPIO 17)
        dt_pin      — KY-040 DT   (Rad-pos 7 · Pin 13 · GPIO 27)
        callback    — anropas med +1 (medsols) eller -1 (motsols) per hack
        debounce_ms — minsta tid (ms) mellan två accepterade CLK-kanter
        """
        self._pi       = pi
        self._clk      = clk_pin
        self._dt       = dt_pin
        self._cb       = callback
        self._debounce = debounce_ms / 1000.0
        self._last_t   = 0.0

        pi.set_mode(clk_pin, pigpio.INPUT)
        pi.set_mode(dt_pin,  pigpio.INPUT)
        pi.set_pull_up_down(clk_pin, pigpio.PUD_UP)
        pi.set_pull_up_down(dt_pin,  pigpio.PUD_UP)

        # Endast FALLING_EDGE på CLK — DT behöver ingen callback
        self._clk_cb = pi.callback(clk_pin, pigpio.FALLING_EDGE, self._on_edge)

    def _on_edge(self, gpio, level, tick):
        now = time.monotonic()
        if now - self._last_t < self._debounce:
            return              # CLK-studs, ignorera
        self._last_t = now
        dt = self._pi.read(self._dt)
        self._cb(+1 if dt else -1)

    def cancel(self):
        self._clk_cb.cancel()
