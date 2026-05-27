#!/usr/bin/env python3
"""Isolated encoder test — run on Pi to verify KY-040 wiring.

Usage:
    sudo python3 /home/pi/modules/test_encoder.py
    Vrid encoder. Ctrl+C för att avsluta.
"""

import sys, time
sys.path.insert(0, '/home/pi/modules')

import pigpio
from encoder import RotaryEncoder

CLK_PIN = 17
DT_PIN  = 27

position = [0]

def on_step(delta):
    position[0] += delta
    direction = 'R' if delta > 0 else 'L'
    print(f"{direction}  pos={position[0]:+d}")

pi = pigpio.pi()
if not pi.connected:
    sys.exit("pigpio daemon inte igång — kör: sudo pigpiod")

enc = RotaryEncoder(pi, CLK_PIN, DT_PIN, on_step)
print(f"KY-040 på CLK={CLK_PIN} DT={DT_PIN}. Vrid encoder. Ctrl+C för att avsluta.")

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    enc.cancel()
    pi.stop()
    print(f"\nSlutposition: {position[0]}")
