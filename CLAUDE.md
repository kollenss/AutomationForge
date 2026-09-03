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
| [`docs/diamond-heist/README.md`](docs/diamond-heist/README.md) | **Start here for story/game-design brainstorming.** Index of the story bible below — deliberately excludes engine/implementation details, which live in this file and `management/GAMEFORGE.md` instead. |
| `docs/diamond-heist/STORY.md` | Full story bible, characters, Cardinal's briefing script |
| `docs/diamond-heist/GAMEPLAY.md` | All three acts, puzzle mechanics, game flow |
| `docs/diamond-heist/VISUAL-STYLE.md` | Art direction, palette, and all image-generation prompts |
| `docs/diamond-heist/COMPONENTS.md` | Physical hardware/prop inventory with status |
| `PIN_MAP.md` | **Single source of truth for all GPIO/pin assignments.** This file does not duplicate pin numbers — always check PIN_MAP.md. |

---

## Development Setup

**GameForge** (working title) runs on Raspberry Pi. The setup now lives entirely on **ninja** after migrating off the deprecated diamond:

| Role | Host | IP | Notes |
|---|---|---|---|
| **Editing + runtime + debugging** | `ninja.local` | DHCP — use mDNS (was `.63`, now `.56`) | `Z:\` is Samba-mapped here (`Z:\` = `/home/pi/AutomationForge/`). SSH MCP points here. Services (`propforge`, `hardware-service`, `pigpiod`) run here. |
| **diamond.local** | — | — | **Deprecated** (WiFi broken). Reachable only via an SSH jump through ninja. No longer used for editing or runtime. |

> Migration done 2026-06-21: Samba share `\\ninja.local\forge` → `/home/pi/AutomationForge`, `Z:` remapped there. Editing and runtime are now the same machine — no more git round-trip between two Pis.

> **Always address ninja via `ninja.local` (mDNS), not a hardcoded IP** — its IP is DHCP and has already moved (`.63` → `.56`). Both Samba (`\\ninja.local\forge`) and the OpsRouter SSH plugin (`C:\Dev\OpsRouter\plugins\ssh\config.yaml`, `hostname: ninja.local`) point at the name. The MCP server caches its config at startup, so restart the client after changing it.

### Workflow

**Z:\ (Samba) — create and edit all files here.** Claude Code uses this drive directly. `Z:\` = ninja:`/home/pi/AutomationForge/`, so `Z:\management\` = `/home/pi/AutomationForge/management/`.

**SSH MCP (→ ninja) — run scripts, build frontend, tail logs, restart services, debug.** Never edit files over SSH.

**`Z:\` is the only working copy — GitHub (`kollenss/AutomationForge`) is the backup.** There is no local clone on the Windows machine; a `C:\Dev\GameForge` backup clone used to exist but was removed 2026-08-31 (it had drifted from `origin/main` and was never synced — see `C:\Dev\MIGRATION_STATUS.md`). Make and commit/push all changes from `Z:\` only.

**The systemd service is `propforge`**, not `gameforge`. GameForge is the product's working title.

### Backup — `management/data/` is gitignored

`management/data/` (project JSON — the actual node-graph designs built in the canvas, plus `settings.json`) is intentionally excluded from git and only exists on the Pi's SD card. **Use the Projects page's Export button** (downloads `gameforge-projects-<date>.json`, all projects in one file — Import restores them) to back it up periodically, and save the exported file **off the Pi** (Windows machine, cloud drive) — exporting to `Z:\` alone doesn't help if the SD card itself dies.

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

> **Superseded (kept for history):** earlier drafts of this file described each floor as a standalone script (`floor1_plan/floor1.py`, `floor2_terminal/terminal_tty.py`, `floor3_vault/vault.py`) importing shared hardware helpers from `shared/`. None of that exists on the Pi anymore — verified 2026-09-03. The project moved to the **GameForge node-graph engine** instead: hardware is exposed as modules, game logic per component type lives in one file, and each floor is a *scene* (a graph of connected component nodes) built in the canvas UI, not a bespoke Python script. The combo-lock mechanic described further down (debounce constants, grace-period, direction-confirm) was ported into `_exec_combo_lock` in `engine.py` — the tuning knowledge is still valid, the file it lived in is not.

Hardware modules take the GPIO pin as a parameter and never hardcode it. Never edit hardcoded pins into a module — read them from `PIN_MAP.md`/component params instead.

```
modules/<name>/<name>.py     ← hardware module: get_components() + Device class (pin as param)
management/component_library.json ← Logic-only component defs (Timer, Password Lock, ...)
management/engine.py         ← game logic per component type — one _exec_<type>() per type
management/data/projects/    ← the actual per-project node graphs (Floor 1/2/3 wiring) — see Backup below
```

### File Structure (`/home/pi/AutomationForge/` = `Z:\`)

```
Z:\
├── modules/              ← hardware wrappers, one folder per component type
│   ├── rfid/rfid.py             ← RC522 reader(s), SPI polling
│   ├── relay_trigger/relay_trigger.py  ← Denkovi relay board (pylibftdi)
│   ├── rotary_encoder/          ← KY-040 via pigpio
│   ├── servo/, max7219_display/, dfplayer/, ws2812b/, usb_device_detector/, text_input/
│   ├── hardware_service.py      ← Flask REST API (port 5101), owns all hardware
│   └── generate_sounds.py       ← deterministic sine-wave SFX generator
├── management/
│   ├── app.py            ← GameForge REST API (port 5000)
│   ├── engine.py          ← game logic per component type (_exec_<type> executors)
│   ├── component_library.json  ← Logic-component definitions
│   ├── GAMEFORGE.md       ← Plattformsdokumentation (vision, arkitektur, backlog)
│   ├── data/              ← Project JSON + settings.json — gitignored, see Backup below
│   ├── static/            ← Byggd React-app (serveras av Flask)
│   └── frontend/          ← React + Vite källkod
├── docs/diamond-heist/    ← story bible (see Key Documents)
└── PIN_MAP.md, install.sh, bootstrap.sh, run_local.py
```

`floor1_plan/`, `floor2_terminal/`, `floor3_vault/`, `shared/`, `audio/` at `/home/pi/` (outside `AutomationForge/`) do **not** exist — if you're looking for old logic under those paths, it's either gone or living in `engine.py` now (see note above).

### Relay / Actuator Layer

```
modules/relay_trigger/relay_trigger.py  →  RelayBoard (pylibftdi, BitBangDevice 'DAE000iW')
                                            CHANNEL_BITS: {1:0x02, 2:0x08, 3:0x20, 4:0x80}
management/engine.py  _exec_relay        →  POSTs on/off to hardware-service per channel;
                                            optional auto_off_s param auto-turns-off after N seconds
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

Game flow/story below is still accurate; the `[...]` implementation tags name the current GameForge node types (see `management/engine.py`), not standalone scripts.

```
FLOOR 1 – The Plan  [rfid_reader + rfid_auth nodes, Pi SPI]
  4× RC522 readers on Pi SPI (Lobby, Security Control, Server Room, Vault room)
  Cards placed in correct order: GHOST → WRAITH → CIRCUIT → SPECTRE
  WhatsApp verification with Cardinal (code OP-0987)
  Red LED camera turns off (Pi GPIO)
  Solenoid releases panel → access to Floor 2

FLOOR 2 – The Terminal  [terminal_gate node — "Web App Bridge", port 8080]
  Player finds screwdriver, unscrews USB port cover on Pi
  Inserts YubiKey into Pi USB → terminal activates (usb_device_detector node, lsusb count)
  Phone/terminal UI talks to GameForge over the Web App Bridge HTTP contract
  (enable/disable/validate — see management/CLAUDE.md); the app implementing that
  contract for this floor still needs to be (re)written, see Next Step
  Navigate: ALARM CONTROL → Vault Corridor → enter override code
  Solenoid channel 1 via relay_channel node → Denkovi relay → release panel → Floor 3

FLOOR 3 – The Vault  [combo_lock node in engine.py, ky040_encoder, pigpio]
  Place SPECTRE card on RC522 → audio confirmation via speaker (dfplayer node)
  Crack combination with stethoscope: R27 L14 R9
  Each correct position → click sound (DFPlayer track 1)
  Combination digits hidden on back of character cards (Ghost SN-27, Wraith SN-14, Circuit SN-9)
  Plexi cover opens (4× SG90 servos via pigpio) → NeoPixel ring illuminates → take Le Cœur Bleu
```

---

## Current Progress

> Entries below mentioning `shared/`, `floor2_terminal/`, `floor3_vault/` describe work done in the old per-floor-script architecture (see the superseded note under Architecture). None of those files exist anymore; where the logic survived, it was ported into `management/engine.py`. Kept here for the debugging history (e.g. the encoder debounce tuning) — don't go looking for the files.

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
  - CLK faller → läs DT → riktning; debounce filtrerar CLK-studsar
  - Ersatte gray code (tappade steg vid state-skippar) — testat & stabilt
- ✅ shared/segment_display.py – MAX7219 8-digit 7-segment via SPI0 CE1
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

## WS2812B – Slumpmässiga färgblinkningar (2026-08-29)

**Symptom:** enstaka pixlar blinkade till i fel färg (ofta blått), slumpmässigt, oberoende av vilken effekt (pulse, chase, set_color …) som kördes.

**Åtgärdat i två steg** (`modules/ws2812b/ws2812b.py`):
1. Lade till `Device._write_lock` runt alla `setPixelColor`+`show()`-sekvenser — flera zoners animationstrådar kunde tidigare skriva till samma `PixelStrip` samtidigt och korrumpera DMA-överföringen. Löste inte hela problemet ensamt.
2. Bytte `PixelStrip(..., dma=5)` istället för `rpi_ws281x`s default (`dma=10`) — detta minskade frekvensen drastiskt (från flera/minut till ~1/minut).

**Kvarstående, accepterad risk:** en enstaka blinkning kvarstår ibland (~1/minut). Trolig bakomliggande orsak (ej bekräftad): ingen nivåomvandlare/seriemotstånd/kondensator på datalinjen (GPIO21 → DIN, se `PIN_MAP.md`) i kombination med att ninja kör på WiFi (RF-störning är en känd källa till just den här typen av glitch på Pi + WS2812B). **Godkänt för nuvarande version av spelet** — om projektet någon gång serieproduceras bör nivåomvandlare + motstånd/kondensator läggas till för en robust lösning.

## Floor 3 – Kombinationslåset: Aktuell status & felsökning

### Mekanik (numera `_exec_combo_lock` i `management/engine.py`, samma logik som test_combo.py/vault.py hade)
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

Kombinationslåsmekaniken är klar och testad (23/33/26/74 — alla korrekta lås) — nu som `combo_lock`-noden i GameForge-motorn. Nästa fas: koppla hårdvara och testa Floor 3 end-to-end via en scen i canvasen.

> Alla pinnar: se `PIN_MAP.md`.

1. **Koppla RC522 RFID** — SPECTRE-kort-detektion (`rfid_reader`-nod)
2. **Koppla servos** — öppnar plexi-lock (`servo`-nod)
3. **Koppla NeoPixel-ring (WS2812B)** — belyser diamanten (`led_zone`-nod)
4. **Bygg Floor 3-scenen i canvasen** och kör den end-to-end med all hårdvara ansluten
5. **Floor 2 Web App Bridge** — `terminal_gate`-noden finns i engine.py, men själva telefon-/terminal-appen (`terminal_web.py`, Web App Bridge-kontraktet i `management/CLAUDE.md`) behöver skrivas om — den gamla filen finns inte kvar på Pi:n

---

## GameForge — Installation på ny Pi

### Ett kommando via SSH

```bash
bash <(curl -sSL https://raw.githubusercontent.com/kollenss/AutomationForge/main/bootstrap.sh)
```

Kör detta efter att Pi:n är uppe med SSH-access. Gör automatiskt:
1. Klonar repot till `/home/pi/AutomationForge`
2. Aktiverar SPI och Serial via raspi-config
3. Installerar systempaket (apt) och Python-paket (pip)
4. Bygger pigpio från källkod (finns inte i Bookworm apt)
5. Bygger React-frontend (`npm install && npm run build`)
6. Skapar och startar systemd-tjänsterna
7. Startar om Pi:n

Efter omstart: **http://\<hostname\>.local:5000**

### Dependencies

**Systempaket (apt):**
```
python3-pip python3-venv python3-setuptools git unzip nodejs npm
```

**Python (pip --break-system-packages):**
```
flask flask-socketio pylibftdi mfrc522 RPi.GPIO pigpio
```

**pigpio:** byggs från källkod — install.sh hanterar detta.

**Frontend:** `npm install && npm run build` i `management/frontend/` → output till `management/static/`.

### Systemd-tjänster

```
pigpiod           — GPIO-daemon (port -, startar först)
hardware-service  — Hårdvaru-REST-API (port 5101)
propforge         — Huvud-Flask-app (port 5000)
```

```bash
sudo systemctl status pigpiod hardware-service propforge
journalctl -u propforge -f
```

### Lokal utveckling (Windows, utan Pi)

```bash
pip install flask flask-socketio
python run_local.py
```

Alla hårdvarumoduler faller tillbaka till stub-läge utan fysisk hårdvara.
