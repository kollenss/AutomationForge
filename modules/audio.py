#!/usr/bin/env python3
"""
Central audio module — /home/pi/modules/audio.py

Använder DFPlayer Mini via FT232RL USB-seriell adapter.
Kräver: pip3 install pyserial

Koppling:
    FT232RL TX  → DFPlayer RX
    FT232RL GND → DFPlayer GND
    Pi 5V       → DFPlayer VCC
    DFPlayer SPK1/SPK2 → Högtalare

Ljudfiler på DFPlayer microSD (root-mapp):
    0001.wav = click
    0002.wav = card_ok
    0003.wav = card_wrong
    0004.wav = vault_open
    0005.wav = error

Usage:
    from audio import Audio
    a = Audio()
    a.play_effect('card_ok')
    a.play_voice('cardinal_intro.mp3')
"""

import json
import os
import subprocess
import time

import serial

STATE_FILE = '/home/pi/modules/state.json'
VOICE_DIR  = '/home/pi/audio'

TRACK_MAP = {
    'click':      1,
    'card_ok':    2,
    'card_wrong': 3,
    'vault_open': 4,
    'error':      5,
}


class Audio:
    def __init__(self, port: str = '/dev/ttyUSB0', volume: int = 25):
        """
        port   — seriell port för FT232RL (vanligtvis /dev/ttyUSB0)
        volume — DFPlayer-volym 0–30
        """
        self._ser = serial.Serial(port, 9600, timeout=1)
        time.sleep(1.5)  # DFPlayer behöver tid att starta
        self._send(0x06, volume)  # sätt volym
        print(f"[audio] DFPlayer redo på {port}, volym {volume}")

    # ── Public API ────────────────────────────────────────────────────────

    def play_effect(self, name: str):
        """Spela en ljudeffekt. Icke-blockerande."""
        track = TRACK_MAP.get(name)
        if track is None:
            print(f"[audio] Okänd effekt: {name}")
            return
        self._send(0x03, track)
        self._report(f'effect:{name}')

    def play_voice(self, filename: str):
        """Spela en Cardinals röst-MP3 via mpg123. Icke-blockerande."""
        path = os.path.join(VOICE_DIR, filename)
        if not os.path.exists(path):
            print(f"[audio] Röstfil saknas: {path}")
            return
        subprocess.Popen(
            ['mpg123', '-q', path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._report(f'voice:{filename}')

    def set_volume(self, volume: int):
        """Sätt volym 0–30."""
        self._send(0x06, max(0, min(30, volume)))

    def stop(self):
        """Stoppa uppspelning."""
        self._send(0x16, 0)

    def close(self):
        self._ser.close()

    # ── Internal ──────────────────────────────────────────────────────────

    def _send(self, cmd: int, param: int):
        msg = bytes([0x7E, 0xFF, 0x06, cmd, 0x00, 0x00, param, 0xEF])
        self._ser.write(msg)
        time.sleep(0.05)

    def _report(self, event: str):
        try:
            try:
                with open(STATE_FILE) as f:
                    state = json.load(f)
            except Exception:
                state = {}
            state.setdefault('audio', {}).update({
                'last_event': event,
                'ts': time.strftime('%H:%M:%S'),
            })
            tmp = STATE_FILE + '.tmp'
            with open(tmp, 'w') as f:
                json.dump(state, f, indent=2)
            os.replace(tmp, STATE_FILE)
        except Exception:
            pass
