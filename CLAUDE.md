# THE DIAMOND HEIST – Project Overview
## Operation: Le Cœur Bleu

This is a physical puzzle box built inside an aluminum briefcase. The player solves their way through three floors/layers to retrieve a blue diamond (Le Cœur Bleu) that was stolen from their grandmother in 1987.

---

## Project Status
- **Phase:** Design complete, building started
- **Target:** Wife's birthday gift
- **Style:** GTA 5 loading screen aesthetic – flat graphic, bold silhouettes, hard shadows
- **Color palette:** Black (#000000) · White (#FFFFFF) · Gold (#C9A84C)

---

## Key Documents

| File | Contents |
|------|----------|
| `STORY.md` | Full story bible, characters, Cardinal's briefing script |
| `GAMEPLAY.md` | All three acts, puzzle mechanics, game flow |
| `COMPONENTS.md` | Full component inventory with status |
| `diamond-heist-designdokument.md` | Image prompts (all 12), contract text, planning book text |

---

## Development Setup

**Pi is source of truth for all code.** Edit files directly via Samba share.

| | Path |
|---|---|
| Pi IP | `192.168.68.53` |
| Samba share | `\\192.168.68.53\diamond` → maps to `/home/pi/` |
| Windows drive | `Z:\` |
| SSH | `ssh pi@192.168.68.53` |

### Workflow

**Z:\ (Samba) — create and edit all files here.**
All file creation, editing, and reading goes through `Z:\`. Claude Code uses this drive directly. `Z:\` = `/home/pi/` on the Pi.

**SSH — run scripts, check logs, debug.**
Use SSH to execute scripts, tail logs, restart services, check hardware, etc. Never edit files over SSH.

### MCP Tools – Best Fit

| Task | Tool |
|------|------|
| Read/edit files on Z:\ | Claude Code built-in (Read/Edit/Glob) — snabbast, skickar bara diff |
| Run commands on Pi | MCP Router SSH (`ssh_run`) |
| Interact with GameForge UI, click/navigate, console errors | Playwright MCP (fristående browser, ingen session-konflikt) |
| Testa GameForge REST API-endpoints direkt | Fetch MCP |
| Flytta fönster, skärmdumpar, lokal PowerShell | Windows-MCP |
| **Undvik:** Windows-MCP FileSystem för Z:\ | Går via extra MCP-lager + Samba = onödigt långsamt |
| Inspektera befintlig Chrome-session | Claude in Chrome extension |

---

## Architecture

**Pi-only.** A single Raspberry Pi 3B handles all three floors. No ESP32s or other microcontrollers. All sensors, RFID readers, actuators and audio connect directly to Pi GPIO/SPI/UART.

### Modular Architecture

All hardware/sensors are implemented as shared modules with GPIO pin as parameter. Floor scripts import from `shared/`. Never hardcode pins inside modules.

```
shared/komponent.py      ← hardware module (pin as parameter)
shared/test_komponent.py ← isolated test, no other hardware needed
floor1_plan/floor1.py    ← imports from shared/
floor2_terminal/...      ← imports from shared/
floor3_vault/vault.py    ← imports from shared/
```

### File Structure on Pi (`/home/pi/`)

```
/home/pi/
├── floor1_plan/          ← TODO: floor1.py (not written yet)
├── floor2_terminal/
│   ├── terminal_tty.py   ← ACTIVE: curses UI, reads keyboard on Pi directly
│   ├── terminal_web.py   ← Flask app (port 8080) serving phone display
│   └── terminal.html     ← Phone browser UI (served by terminal_web.py)
├── floor3_vault/
│   └── vault.py          ← Pi implementation (needs audio.py integration + hardware test)
├── shared/
│   ├── relay_trigger.py  ← RelayBoard class (pylibftdi / BitBangDevice)
│   ├── actuators.py      ← SolenoidController wrapping RelayBoard
│   ├── audio.py          ← Audio module – DFPlayer Mini via FT232RL (/dev/ttyUSB0)
│   ├── generate_sounds.py← Generates MP3 sound effects → shared/sounds/
│   ├── test_audio.py     ← Isolated audio test
│   ├── sounds/           ← Generated MP3s (0001–0005) – copy to DFPlayer SD card
│   ├── config.json       ← Game config: password
│   └── state.json        ← Runtime state (floor2 state, relay states, audio events)
├── management/
│   ├── app.py            ← GameForge REST API (port 5000)
│   ├── component_library.json  ← Komponentdefinitioner
│   ├── GAMEFORGE.md      ← Plattformsdokumentation (vision, arkitektur, backlog)
│   ├── data/projects/    ← Projekt-JSON-filer
│   ├── static/           ← Byggd React-app (serveras av Flask)
│   └── frontend/         ← React + Vite källkod
└── audio/                ← Cardinal's voice MP3s (not recorded yet)
```

### Relay / Actuator Layer

```
relay_trigger.py   →  RelayBoard (pylibftdi, BitBangDevice 'DAE000iW')
                       CHANNEL_BITS: {1:0x02, 2:0x08, 3:0x20, 4:0x80}
actuators.py       →  SolenoidController(board, {'name': channel})
                       .trigger(name)   – open and stay open
                       .release(name)   – close
                       .pulse(name, s)  – open for s seconds then close
```

**Floor 2 uses channel 1** (`floor2_panel`). Floor 1 and Floor 3 will also use this layer.

---

## Hardware Summary

| Component | Role |
|-----------|------|
| Raspberry Pi 3B | Master controller – all three floors |
| RC522 RFID x5 | All on Pi SPI0 bus, different CS pins per reader |
| Mifare Classic cards x5 | Character cards (GHOST, WRAITH, CIRCUIT, SPECTRE + NOVA ID) |
| KY-040 Rotary encoder x3 | Safe combination dial (Floor 3) |
| SG90 servo x4 | Opens plexi cover over diamond (Floor 3) |
| WS2812B LED strip 10-LED | Addressable LEDs: index 0–2 Floor 1, 3–5 Floor 2, 6–9 Floor 3 (diamond illumination) |
| Micro solenoid K055 x3 | Release floor panels |
| Denkovi USB relay board | Pi solenoid control – pylibftdi, CHANNEL_BITS {1:0x02, 2:0x08, 3:0x20, 4:0x80} |
| Redmi 9A phone | Floor 2 display only – connects to terminal_web.py over WiFi (no touch, no keyboard) |
| USB keyboard | Connected to Pi USB – input for terminal_tty.py |
| YubiKey / USB security key | Floor 2 trigger – detected via lsusb count |
| DFPlayer Mini + FT232RL | Audio output – UART via /dev/ttyUSB0, built-in 3W amp |
| Speaker 8Ω | Driven by DFPlayer Mini – sound effects + Cardinal's voice |

---

## Three Floors

```
FLOOR 1 – The Plan  [Pi GPIO/SPI]
  4× RC522 readers on Pi SPI (Lobby, Security Control, Server Room, Vault room)
  Cards placed in correct order: GHOST → WRAITH → CIRCUIT → SPECTRE
  WhatsApp verification with Cardinal (code OP-0987)
  Red LED camera turns off (Pi GPIO)
  Solenoid releases panel → access to Floor 2

FLOOR 2 – The Terminal  [terminal_tty.py + terminal_web.py, port 8080]
  Player finds screwdriver, unscrews USB port cover on Pi
  Inserts YubiKey into Pi USB → terminal activates (lsusb count increases)
  terminal_tty.py runs on Pi: curses UI, keyboard on Pi, arrow key navigation
  terminal_web.py serves terminal.html to Redmi 9A over WiFi (display only, touch disabled)
  Navigate: ALARM CONTROL → Vault Corridor → enter override code
  Code stored in /home/pi/shared/config.json
  Solenoid channel 1 via actuators.py → Denkovi relay → release panel → Floor 3

FLOOR 3 – The Vault  [vault.py, pigpio]
  Place SPECTRE card on RC522 → audio confirmation via speaker
  Crack combination with stethoscope: R27 L14 R9
  Each correct position → click sound via audio.py (DFPlayer track 1)
  Combination digits hidden on back of character cards (Ghost SN-27, Wraith SN-14, Circuit SN-9)
  Plexi cover opens (4× SG90 servos via pigpio) → NeoPixel ring illuminates → take Le Cœur Bleu
```

---

## Current Progress

- ✅ Story bible complete
- ✅ All character designs defined
- ✅ Game flow documented
- ✅ All AI image/video prompts written
- ✅ RC522 RFID x5 arrived
- ✅ Mifare Classic cards x5 arrived (white, came with RC522 – used for character cards)
- ✅ NTAG215 NFC cards x10 arrived (black – reserved for future use)
- ✅ KY-040 Rotary encoder x3 arrived
- ✅ Micro solenoid K055 x3 arrived
- ✅ Denkovi USB relay board – WORKING (pylibftdi, correct bit mapping, udev rule for ftdi_sio)
- ✅ LogiLink AA0035 OTG cable – arrived
- ✅ Floor 2 terminal – COMPLETE & TESTED
  - terminal_tty.py: curses UI, arrow key navigation, keyboard on Pi
  - terminal_web.py + terminal.html: phone display over WiFi, touch disabled
  - Password read from /home/pi/shared/config.json
  - YubiKey detection via lsusb (Yubico vendor ID 1050)
  - Pi keyboard captured via evdev (grab), events streamed to phone via SSE /api/keys
  - Relay stays open after trigger (channel 1 via actuators.py → Denkovi board)
  - ACCESS GRANTED screen: green box, no blinking text
- ✅ vault.py – KOMPLETT med ny kombo-mekanik (display + 4 slumptal + grace-period + dir_confirmed)
- ✅ **GameForge** management platform running on port 5000 — React + React Flow + Flask
  - Projekt- och scenhantering med visuell canvas-editor
  - Komponentbibliotek (Input/Output/Logic) — drag-and-drop till canvas
  - Live-testning: Relay board (ON/OFF per kanal, status-polling)
  - Dokumentation: management/GAMEFORGE.md
- ✅ Samba share configured (Z:\ → /home/pi/)
- ✅ Audio module (shared/audio.py) – DFPlayer Mini via FT232RL, TESTED & WORKING
  - 5 sound effects: click(1), card_ok(2), card_wrong(3), vault_open(4), error(5)
  - MP3 files on DFPlayer SD card (0001–0005.mp3)
  - play_effect(name) + play_voice(filename) API
- ✅ Floor 2 keyboard auto-reconnect fixed (evdev thread retries on disconnect)
- ✅ shared/encoder.py – KY-040 via pigpio, FALLING_EDGE på CLK + 3ms tidsbaserad debounce
  - Pins: CLK=GPIO17 (Pin 11), DT=GPIO27 (Pin 13)
  - CLK faller → läs DT → riktning; debounce filtrerar CLK-studsar
  - Ersatte gray code (tappade steg vid state-skippar) — testat & stabilt
- ✅ shared/segment_display.py – MAX7219 8-digit 7-segment via SPI0 CE1 (GPIO7, Pin 26)
  - show_pair(val, pair), blank_pair(pair), show_text(str), blink_text(str), restore_bcd(), clear()
  - BCD-mode for digits, raw-segment mode for text (OPEN, TrYAGAIn etc.)
- ✅ floor3_vault/test_combo.py – kombination-testscript (encoder + display + audio), TESTAT & STABILT
  - 4 slumpade mål (5–99), sparas i /tmp/vault_code.txt
  - Räknar uppåt i aktiv riktning; klick vid rätt tal
  - 250ms grace-period efter klick absorberar encoder-burst
  - Riktningsbyte: CONFIRM_STEPS(2) pending → DETECTED → +1 bekräftelse → LOCK
  - 15ms debounce mot encoder-brus (motriktade hack)
  - last_dir=None efter lås: tvingar riktningsetablering → omöjligt låsa på 0
  - Debuglogg till /tmp/vault_debug.log
- ❌ ESP32-C3 SuperMini x10 – arrived but NOT USED (Pi-only architecture)
- ❌ Piezo – NOT USED (replaced by speaker + DFPlayer)
- ❌ Floor 1 code – not written yet (Pi-based, needs RC522 × 4 on SPI)
- ❌ Floor 3 hardware (RC522, servos, NeoPixel) – ej kopplad/testad
- ❌ Multi-RC522 SPI wiring not done yet
- ❌ Audio (Cardinal's voice MP3 files) – not recorded yet
- ❌ Management web app needs service/autostart (currently manual)
- ⚠️ Still needed: blue glass diamond, stethoscope, YubiKey for game
- ❌ 3D printing not started
- ❌ Physical construction not started

## Floor 3 – Kombinationslåset: Aktuell status & felsökning

### Mekanik (test_combo.py och vault.py – samma logik)
- Räknaren ökar +1 per encoder-hack i aktiv riktning
- Vid rätt tal → click-ljud, `click_time = time.time()` sätts
- 250 ms grace-period: alla hack i samma riktning ignoreras direkt efter klick
- Riktningsbyte bekräftas i två steg:
  1. CONFIRM_STEPS (=2) hack i ny riktning → `dir_confirmed = True`
  2. Ytterligare ett hack i ny riktning → LOCK (lås värdet, gå vidare)
  - Om nästa hack är tillbaka i gamla riktningen → falskt larm, räkna vidare

### Bugg fixad (2026-05-27)
KY-040 genererade burst av 2–3 snabba hack vid detentposition.
`skip_next` (enkelt steg-skip) räckte inte — `click_time` + 250 ms grace löser det.

## Next Step

Kombinationslåsmekaniken är klar och testad (23/33/26/74 — alla korrekta lås). Nästa fas: koppla hårdvara och kör vault.py.

1. **Koppla RC522 RFID** (SPI CE0, GPIO 8, Pin 24) — SPECTRE-kort-detektion
   - Om shared/test_rfid.py saknas: skriv det
2. **Koppla servos** (GPIO 5/6/13/19, Pin 29/31/33/35) — öppnar plexi-lock
3. **Koppla NeoPixel-ring** (GPIO 18, Pin 12) — belyser diamanten
4. **Kör vault.py end-to-end** med all hårdvara anslutet
