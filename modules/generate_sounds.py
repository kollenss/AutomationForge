#!/usr/bin/env python3
"""
Genererar WAV-ljudeffekter till /home/pi/modules/sounds/
Kör: python3 /home/pi/modules/generate_sounds.py
"""

import math
import os
import struct
import wave

SAMPLE_RATE = 44100
OUT_DIR     = '/home/pi/modules/sounds'

# DFPlayer-namngivning: 0001.wav, 0002.wav osv.
TRACKS = [
    (1, 'click'),
    (2, 'card_ok'),
    (3, 'card_wrong'),
    (4, 'vault_open'),
    (5, 'error'),
]

os.makedirs(OUT_DIR, exist_ok=True)


def write_wav(filename, samples):
    path = os.path.join(OUT_DIR, filename)
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SAMPLE_RATE)
        f.writeframes(struct.pack(f'<{len(samples)}h', *samples))


def sine(freq, duration, amplitude=32000, decay=0.0):
    n = int(SAMPLE_RATE * duration)
    out = []
    for i in range(n):
        t   = i / SAMPLE_RATE
        env = math.exp(-decay * t)
        out.append(int(amplitude * env * math.sin(2 * math.pi * freq * t)))
    return out


def silence(duration):
    return [0] * int(SAMPLE_RATE * duration)


def fade_out(samples, ms=10):
    n = int(SAMPLE_RATE * ms / 1000)
    n = min(n, len(samples))
    out = list(samples)
    for i in range(n):
        out[-(i + 1)] = int(out[-(i + 1)] * (i / n))
    return out


print("Genererar ljud...")

sounds = {}

# ── 1: click — kombinationsklick (valvet) ─────────────────────────────────
s  = sine(900,  0.006, amplitude=32000, decay=200)
s += sine(400,  0.008, amplitude=16000, decay=300)
s += silence(0.01)
sounds['click'] = fade_out(s)

# ── 2: card_ok — kort placerat rätt (våning 1) ────────────────────────────
s  = sine(880,  0.08, amplitude=28000, decay=20)
s += silence(0.03)
s += sine(1320, 0.12, amplitude=28000, decay=15)
s += silence(0.05)
sounds['card_ok'] = fade_out(s)

# ── 3: card_wrong — fel kort ──────────────────────────────────────────────
s  = sine(350, 0.15, amplitude=28000, decay=8)
s += silence(0.03)
s += sine(250, 0.20, amplitude=28000, decay=6)
s += silence(0.05)
sounds['card_wrong'] = fade_out(s)

# ── 4: vault_open — valvet öppnas ─────────────────────────────────────────
s = []
for freq in [523, 659, 784, 1047]:
    s += sine(freq, 0.15, amplitude=28000, decay=12)
    s += silence(0.03)
s += silence(0.1)
sounds['vault_open'] = fade_out(s)

# ── 5: error — generellt fel ──────────────────────────────────────────────
s  = sine(300, 0.25, amplitude=28000, decay=5)
s += silence(0.04)
s += sine(220, 0.30, amplitude=28000, decay=4)
s += silence(0.05)
sounds['error'] = fade_out(s)

# ── Spara WAV temporärt och konvertera till MP3 ───────────────────────────
import subprocess, tempfile

for track_num, name in TRACKS:
    wav_path = os.path.join(OUT_DIR, f'{track_num:04d}.wav')
    mp3_path = os.path.join(OUT_DIR, f'{track_num:04d}.mp3')
    write_wav(wav_path, sounds[name])
    result = subprocess.run(
        ['lame', '--preset', 'standard', '--silent', wav_path, mp3_path],
        capture_output=True
    )
    os.remove(wav_path)
    print(f"  {track_num:04d}.mp3  ({name})")

print(f"\nKlar! Kopiera MP3-filerna i {OUT_DIR} till DFPlayer microSD-kortets root-mapp.")
