#!/usr/bin/env python3
"""
Test för audio-modulen.
Kör: python3 /home/pi/modules/test_audio.py

Generera ljud först om sounds/-mappen saknas:
  python3 /home/pi/modules/generate_sounds.py
"""

import time
import sys
sys.path.insert(0, '/home/pi/modules')
from audio import Audio

a = Audio()

effects = ['click', 'card_ok', 'card_wrong', 'vault_open', 'error']

for name in effects:
    print(f"▶  {name}")
    a.play_effect(name)
    time.sleep(1.5)

print("✓  Klar – kolla management-sidan för events")
