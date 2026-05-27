#!/usr/bin/env python3
"""Isolerat test för MAX7219 — räknar 0–99 på varje sifferpar i tur och ordning.

Usage:
    sudo python3 /home/pi/modules/test_segment_display.py
"""

import sys, time
sys.path.insert(0, '/home/pi/modules')
from segment_display import SegmentDisplay

d = SegmentDisplay()
print("Testar MAX7219. Ctrl+C för att avsluta.")

try:
    while True:
        for pair in range(4):
            for val in range(100):
                d.clear()
                d.show_pair(val, pair)
                print(f"\r  Par {pair+1}  val={val:02d}  ", end='', flush=True)
                time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    d.close()
    print("\nKlart.")
