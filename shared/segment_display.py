#!/usr/bin/env python3
"""MAX7219 8-siffrig 7-segment display via SPI0 CE1 (GPIO 7, Pin 26).

Koppling:
    VCC  → Pin 4  (5V)
    GND  → Pin 25 (GND)
    DIN  → Pin 19 (GPIO 10 / MOSI)
    CLK  → Pin 23 (GPIO 11 / SCLK)
    CS   → Pin 26 (GPIO 7  / CE1)

Usage:
    from segment_display import SegmentDisplay
    d = SegmentDisplay()
    d.show_pair(33, pair=0)        # "33" på siffrorna 1–2
    d.show_text('  OPEN  ')        # råsegment-text, 8 tecken
    d.blink_text('  OPEN  ')       # blinka text
    d.restore_bcd()                # tillbaka till sifferläge
    d.clear()
    d.close()
"""

import time
import spidev

_REG_DECODE_MODE  = 0x09
_REG_INTENSITY    = 0x0A
_REG_SCAN_LIMIT   = 0x0B
_REG_SHUTDOWN     = 0x0C
_REG_DISPLAY_TEST = 0x0F
_BLANK_BCD        = 0x0F   # blank i BCD-läge
_BLANK_RAW        = 0x00   # blank i råläge

# Segment-bitar (no-decode mode): bit7=DP, 6=A(topp), 5=B(höger-övre),
# 4=C(höger-nedre), 3=D(botten), 2=E(vänster-nedre), 1=F(vänster-övre), 0=G(mitten)
_CHAR_MAP = {
    ' ': 0x00,
    '-': 0x01,   # G (mittstrecket)
    '0': 0x7E, '1': 0x30, '2': 0x6D, '3': 0x79, '4': 0x33,
    '5': 0x5B, '6': 0x5F, '7': 0x70, '8': 0x7F, '9': 0x7B,
    'A': 0x77,   # A,B,C,E,F,G
    'B': 0x1F,   # C,D,E,F,G  (lowercase b)
    'C': 0x4E,   # A,D,E,F
    'D': 0x3D,   # B,C,D,E,G  (lowercase d)
    'E': 0x4F,   # A,D,E,F,G
    'F': 0x47,   # A,E,F,G
    'G': 0x5F,   # A,C,D,E,F,G  (= 6)
    'H': 0x37,   # B,C,E,F,G
    'I': 0x30,   # B,C  (= 1)
    'J': 0x38,   # B,C,D
    'L': 0x0E,   # D,E,F
    'N': 0x15,   # C,E,G  (lowercase n)
    'O': 0x7E,   # A,B,C,D,E,F  (= 0)
    'P': 0x67,   # A,B,E,F,G
    'R': 0x05,   # E,G  (lowercase r)
    'S': 0x5B,   # A,C,D,F,G  (= 5)
    'T': 0x0F,   # D,E,F,G  (lowercase t)
    'U': 0x3E,   # B,C,D,E,F
    'Y': 0x3B,   # B,C,D,F,G
}


class SegmentDisplay:
    def __init__(self, bus: int = 0, device: int = 1, brightness: int = 8):
        self._spi  = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = 1_000_000
        self._spi.mode = 0
        self._bcd  = True   # aktuellt avkodningsläge

        self._write(_REG_SHUTDOWN,     0x01)
        self._write(_REG_DISPLAY_TEST, 0x00)
        self._write(_REG_DECODE_MODE,  0xFF)
        self._write(_REG_SCAN_LIMIT,   0x07)
        self._write(_REG_INTENSITY,    max(0, min(15, brightness)))
        self.clear()

    # ── Sifferläge (BCD) ───────────────────────────────────────────────────

    def show_pair(self, value: int, pair: int):
        """Visa 0–99 på ett sifferpar (pair 0 = längst till vänster)."""
        if not self._bcd:
            self.restore_bcd()
        v        = max(0, min(99, int(value)))
        tens_reg = 0x08 - pair * 2
        ones_reg = 0x07 - pair * 2
        self._write(tens_reg, v // 10)
        self._write(ones_reg, v % 10)

    def blank_pair(self, pair: int):
        if not self._bcd:
            self.restore_bcd()
        base = pair * 2
        self._write(0x08 - base,     _BLANK_BCD)
        self._write(0x08 - base - 1, _BLANK_BCD)

    def restore_bcd(self):
        """Återgå till BCD-sifferläge."""
        self._write(_REG_DECODE_MODE, 0xFF)
        self._bcd = True

    # ── Textläge (råsegment) ───────────────────────────────────────────────

    def show_text(self, text: str):
        """Visa upp till 8 tecken i råsegment-läge (position 0 = vänsterst)."""
        self._write(_REG_DECODE_MODE, 0x00)
        self._bcd = False
        for pos in range(8):
            char = text[pos].upper() if pos < len(text) else ' '
            seg  = _CHAR_MAP.get(char, 0x00)
            self._write(0x08 - pos, seg)

    def blink_text(self, text: str, times: int = 6, interval: float = 0.35):
        """Blinka text på displayen."""
        for _ in range(times):
            self.show_text(text)
            time.sleep(interval)
            self._write(_REG_SHUTDOWN, 0x00)   # stäng av display
            time.sleep(interval)
            self._write(_REG_SHUTDOWN, 0x01)   # tänd igen
        self.show_text(text)

    # ── Generellt ──────────────────────────────────────────────────────────

    def clear(self):
        if self._bcd:
            for reg in range(0x01, 0x09):
                self._write(reg, _BLANK_BCD)
        else:
            for reg in range(0x01, 0x09):
                self._write(reg, _BLANK_RAW)

    def close(self):
        self.clear()
        self._write(_REG_SHUTDOWN, 0x00)
        self._spi.close()

    def _write(self, reg: int, data: int):
        self._spi.xfer2([reg, data])
