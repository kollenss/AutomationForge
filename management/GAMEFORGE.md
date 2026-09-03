# GameForge – Platform Documentation

## Vision

GameForge är en generisk webbplattform för att designa och kontrollera fysiska spel (escape rooms, puzzle boxes, interaktiva installationer) med DIY-elektronikkomponenter kopplade till en Raspberry Pi.

Målet är att en "game designer" utan djup kodkunskap ska kunna:
- Bygga upp ett projekt med fysiska scener
- Dra in hårdvarukomponenter från ett bibliotek till en canvas
- Konfigurera varje komponent (GPIO-pinnar, lösenord, tröskelvärden)
- Testa hårdvaran live direkt från webgränssnittet
- Spara konfigurationen som ett projekt

**Det är inte kopplat till något specifikt spel.** Diamond Heist är det första projektet som byggs *i* GameForge.

---

## User Stories (MVP)

| Story | Status |
|-------|--------|
| Som game designer vill jag skapa/ladda ett projekt | ✅ |
| Som game designer vill jag lägga till en scen i projektet | ✅ |
| Som designer vill jag dra en komponent från biblioteket till canvas | ✅ |
| Som designer vill jag klicka ett kort och konfigurera dess parametrar | ✅ |
| Som designer vill jag ta bort ett kort från canvas | ✅ |
| Som designer vill jag länka outputs till inputs (visuellt) | ✅ |
| Som designer vill jag se live-status på reläkortet | ✅ |
| Som designer vill jag slå på/av enskilda reläkanaler | ✅ |
| Som designer vill jag att komponentbiblioteket speglar ansluten hårdvara | ✅ |
| Som designer vill jag att kortens status uppdateras i realtid utan polling | ✅ |
| Som designer vill jag att canvasen exekveras av en server-side engine | ✅ |

---

## Arkitektur

```
AutomationForge/
├── modules/                      Hårdvarumoduler — en undermapp per enhetstyp
│   ├── hardware_service.py       Flask REST API (port 5101) — äger all hårdvara
│   ├── relay_trigger/relay_trigger.py
│   ├── rotary_encoder/
│   ├── rfid/rfid.py
│   ├── servo/, max7219_display/, dfplayer/, ws2812b/, usb_device_detector/, text_input/
│   └── generate_sounds.py        Deterministisk SFX-generator (sinusvågor)
│
└── management/
    ├── app.py                    Flask + Socket.IO (port 5000)
    ├── engine.py                 GameEngine — server-side grafexekverare
    ├── component_library.json    Statiska Logic-komponenter
    ├── data/
    │   └── projects/             En JSON-fil per projekt (UUID.json) — gitignorerad
    ├── static/                   Byggd React-app (serveras av Flask)
    └── frontend/                 React-källkod (byggs med Vite)
        └── src/
            ├── socket.js         Socket.IO singleton (delar anslutning i hela appen)
            ├── api.js
            ├── pages/
            │   ├── ProjectsPage.jsx
            │   └── SceneEditorPage.jsx
            └── components/
                ├── ComponentLibrary.jsx
                ├── ComponentNode.jsx   (live-status + simulering på kortet)
                ├── NodeModal.jsx
                └── NodeModal.css
```

> **Detaljerad kodnavigation (var varje sak finns, hur man lägger till en ny komponenttyp/executor/live-status) hålls löpande uppdaterad i [`management/CLAUDE.md`](CLAUDE.md) — den är auktoritativ källa för kodstruktur.** Den här filen fokuserar på vision, REST-kontrakt och backlog och länkar dit istället för att duplicera detaljer som annars tenderar att bli inaktuella.

---

## Hardware Service (`modules/hardware_service.py`)

En enda Flask-tjänst på port 5101 som **äger all hårdvara**. Både GameForge och externa Web App Bridges (t.ex. en framtida Floor 2-terminalapp, se längre ner) pratar med denna tjänst istället för att hålla hårdvara direkt.

**Modulupptäckt vid start:** Scannar `modules/` efter `.py`-filer som innehåller `MANIFEST` och `Device`. Filer utan dessa ignoreras (test-scripts, utilities).

**Endpoints:**
```
GET  /hardware              → lista laddade enheter + manifest + connected-status
GET  /components            → komponentdefinitioner från alla moduler (för GameForge)
GET  /hardware/:type/state  → enhetens nuvarande tillstånd
POST /hardware/:type/:cmd   → kör kommando (JSON-body med parametrar)
```

### Modulkontrakt

En modul registreras om den har:

```python
MANIFEST = {
    'type': 'relay_board',      # Unikt enhets-ID
    'label': 'USB Relay Board',
    'channels': 4,              # Enhetsspecifika fält
}

def get_components():
    """Returnerar komponentdefinitioner för GameForge-biblioteket."""
    return [{ 'type': 'relay_channel', ... }]

class Device:
    def get_state(self): ...                    # → dict
    def execute(self, cmd, **kwargs): ...       # → dict

    # Valfritt — för input-moduler som genererar events:
    def set_event_callback(self, fn): ...       # fn(event, value) anropas vid förändring
```

**Input-moduler** (KY-040, RFID etc.) implementerar `set_event_callback`. hardware_service anropar denna med en funktion som POSTar till GameForge:

```python
# hardware_service.py sätter automatiskt callback vid load:
device.set_event_callback(
    lambda event, value, t=hw_type: _post_engine(t, event, value)
)
# → POST http://localhost:5000/engine/hardware_event
#   { device_type, event, value }
```

---

## Backend – GameForge (`management/app.py`)

Ren REST API. Ingen spellogik, ingen hårdkodad hårdvarureferens.

**Komponentbibliotek:**
```
GET  /api/components    → mergar hardware_service /components med component_library.json
```
Hardware-kategorier (Input/Output) kommer dynamiskt från anslutna moduler.
Logic-kategorin kommer från den statiska `component_library.json`.

**Projekt-endpoints:**
```
GET    /api/projects
POST   /api/projects
GET    /api/projects/:id
PUT    /api/projects/:id
DELETE /api/projects/:id
POST   /api/projects/:id/scenes
PUT    /api/projects/:id/scenes/:sid
DELETE /api/projects/:id/scenes/:sid
GET    /api/projects/export          → ladda ner alla projekt som JSON-bundle (runtime-state strippat)
POST   /api/projects/import          → återställ/seeda projekt { projects, mode: skip|overwrite|duplicate }
GET    /api/settings/autostart       → vilket projekt+scen som auto-aktiveras vid boot
PUT    /api/settings/autostart       → sätt/rensa autostart ({ project_id: null } rensar)
```

### Projektlagring, backup & autostart

- **Lagring:** ett projekt = en JSON-fil i `management/data/projects/<uuid>.json`. `<uuid>_unlock.json` = runtime-state. `management/data/` är **gitignorerad** → projekt följer inte med i git; en ny Pi (fresh bootstrap) startar tom.
- **Källa till sanning = den centrala Pi:n.** Alla klienter ansluter till `http://ninja.local:5000` och delar samma data. Frontenden cachar inga projekt (bara `gf_layout`/`gf_debug` i localStorage).
- **Backup/migrering = Export/Import** (knappar i ProjectsPage). Export laddar ner alla projekt som en JSON-bundle med scenens `active`-flagga strippad; Import återställer (skip/overwrite/duplicate). Använd detta regelbundet som backup av `management/data/` (se `Z:\CLAUDE.md` → Backup) och för att seeda en ny Pi eller flytta arbete.
- **Autostart:** `data/settings.json` (per-instans, gitignorerad) `{ "autostart": { "project_id", "scene_id" } }`. Vid boot laddar `_autoload_engine()` det projektet och aktiverar exakt den scenen (kör `on_scene_start`, som Activate-knappen). Ej satt → fallback: senast ändrade projekt med sparade scen-states. Ställs in via 🚀 "Start on launch"-knappen per scenkort (ett projekt + en scen).

**Hårdvara (proxy till hardware_service):**
```
GET  /api/hardware/relay               → state {1: bool, 2: bool, ...}
POST /api/hardware/relay/:ch/:action   → slå på/av kanal (action: on|off)
GET  /api/hardware/status              → hardware_service-anslutning + laddade moduler
POST /api/hardware/restart             → startar om hardware-service (för att pröva nyinkopplad hårdvara)
```
Liknande proxy-endpoints finns per modul (`/api/hardware/text_input`, `/api/hardware/ws2812b/<cmd>`, `/api/hardware/servo/<cmd>`, …) — se `app.py` för den fullständiga, aktuella listan istället för att lita på en handskriven kopia här.

---

## Frontend (React + React Flow)

- **React 18** + **@xyflow/react v12** + **React Router v6**
- **Vite** — output till `management/static/`
- SPA; Flask catch-all serverar `index.html` för alla icke-API-rutter
- **Drag-and-drop:** native DOM `dragover`/`drop`-lyssnare (React Flows egna events störde)
- **UUID:** `crypto.randomUUID()` kräver HTTPS — använder `Math.random()`-baserad `uid()`

---

## Komponentbiblioteket

`component_library.json` innehåller **bara Logic-komponenter** (t.ex. Timer, Password Lock, Combo Lock, RFID Auth, Checklist, If/Else, Web App Bridge, Console Log, Note). Hårdvarukomponenter (Input/Output) genereras dynamiskt av modulerna via hardware_service.

Fullständigt schema (params, param-typer, canvas-kortets `display_param`/badge-konvention): se [`management/CLAUDE.md`](CLAUDE.md) → **"Komponentdefinition — schema"**.

---

## Live-status, simulering och live-testning

Canvas-korten visar live-status via Socket.IO (ingen polling), input-komponenter har simuleringskontroller direkt på kortet, och `NodeModal.jsx` har live-testkontroller för vissa typer (t.ex. relä ON/OFF).

Aktuell lista över vilka komponenttyper som har vad, och receptet för att lägga till fler: se [`management/CLAUDE.md`](CLAUDE.md) → **"Canvas-kort: live-status och simulering"**.

---

## Datamodell – Node i canvas

```json
{
  "id": "uuid",
  "type": "component",
  "position": { "x": 200, "y": 150 },
  "data": {
    "componentType": "relay_channel",
    "label": "Relay Channel",
    "subtitle": "USB Relay Board",
    "color": "#f59e0b",
    "icon": "⚡",
    "displayParam": "channel",
    "params": { "channel": 2, "name": "dörrlås" },
    "inputHandles":  [{ "key": "trigger", "label": "Trigger" }],
    "outputHandles": [{ "key": "state",   "label": "State" }]
  }
}
```

---

## Build & Deploy

Kort version — fullständiga steg (systemd, dependencies, lokal utveckling utan Pi) finns i `Z:\CLAUDE.md` → "GameForge — Installation på ny Pi" och `management/CLAUDE.md` → "Bygga frontend"/"Systemd-tjänster".

```bash
# Bygga frontend (på Pi via SSH — kör INTE npm på Samba-share, ger EPERM):
cd /home/pi/AutomationForge/management/frontend && npm run build
# Output hamnar i ../static/ — efter build:
sudo systemctl restart propforge   # huvudtjänsten heter propforge, inte gameforge
```

---

## GameEngine — Implementerad arkitektur

GameForge-frontend är **enbart en konfigurator**. All spellogik exekveras server-sida av `management/engine.py`.

### Princip

Canvas-grafen definierar kopplingar mellan noder. GameEngine håller grafen i minnet och exekverar den i realtid när events inkommer från hårdvaran.

```
Fysisk input (rotary dialer vrids)
  → hardware_service detekterar (GPIO-interrupt, ~0 ms)
  → POST /engine/hardware_event  →  GameEngine (localhost, 1–3 ms)
  → Engine traverserar grafen: rotary.out → relay.trigger_on
  → POST /hardware/relay_board/on  →  hardware_service (localhost, 1–3 ms)
  → Relä slår om
  ─────────────────────────────────────────
  Total latens: 3–8 ms  →  känns som direktkoppling
```

Frontend uppdateras via Socket.IO **efter** att fysisk output redan skett — den är inte i den tidskritiska kedjan.

### Engine-endpoints (i `management/app.py`)

```
POST /engine/hardware_event   Tar emot { device_type, event, value } från hardware_service
POST /engine/event            Skjuter event från specifik nod: { node_id, handle, value }
POST /engine/trigger          Triggar nod direkt (utan graftraversering): { node_id, value }
POST /engine/activate         Sätt aktivt projekt: { project_id }
POST /engine/activate_scene   Aktivera scen: { scene_id, project_id }
POST /engine/deactivate_scene Deaktivera scen: { scene_id, project_id }
```

Engine laddas vid start enligt autostart-konfigurationen (`data/settings.json`) — valt projekt + scen aktiveras automatiskt; saknas konfig laddas senast uppdaterade projekt. Se "Projektlagring, backup & autostart". Om en scenes data sparas och scenen tillhör aktivt projekt laddas grafen om automatiskt.

### Eventflöde

```
hardware_service  ─POST /engine/hardware_event──►  GameEngine
                  ◄─POST /hardware/:type/:cmd────   GameEngine
                                                     │
                                             socketio.emit()
                                                     │
                                                    ▼
                                             Frontend (UI-display)
```

**Payload hardware_service → engine:**
```json
{ "device_type": "ky040_encoder", "event": "delta", "value": {"encoder_id": 1, "delta": 1} }
```

**Engine-respons:** hittar canvas-noder med matchande `componentType` (och matchande params vid dict-value), traverserar edges, anropar executor för varje mål-nod.

### Socket.IO-events (engine/app.py → frontend)

| Event | Payload | Trigger |
|-------|---------|---------|
| `relay_state` | `{"1": bool, ...}` | Varje relay-kommando |
| `encoder_state` | `{device_type, encoder_id, position, delta}` | Varje encoder-steg |
| `combo_state` | `{node_id, enabled?, phase?, count?, unlocked?, failed?}` | Varje combo_lock-tillståndsändring |
| `timer_state` | `{node_id, remaining, running}` | Start, varje tick, reset |
| `max7219_state` | `{node_id, text, scrolling}` | Varje text/show/scroll/clear-kommando |
| `checklist_state` | `{node_id, ...}` | Varje checklist-stegändring |
| `node_event` | `{node_id, label, ok?}` | Generisk kort-notis (RFID auth ✓/✗, dfplayer, servo, if_else, m.fl.) |
| `console_log` | `{node_id, ...}` | Console Log-nod skriver en rad |
| `if_else_gate_state` | `{node_id, ...}` | If/Else-nodens grindtillstånd ändras |
| `node_pulse` | `{node_id}` | Nod aktiverades (debug mode) |
| `edge_pulse` | `{edge_id, value, target_handle}` | Kant traverserades (debug mode) |
| `scene_state` | `{scene_id, active}` | Scen aktiverades eller deaktiverades (emittas från `app.py`, inte `engine.py`) |

### Executors (`engine.py`)

Aktuell, fullständig lista över `_exec_<type>`-funktioner och receptet för att lägga till en ny: se [`management/CLAUDE.md`](CLAUDE.md) → **"Engine-exekverare (nuläge)"** och **"Executor-signatur"**.

### Latenskritisk väg

| Faktor | Påverkan |
|--------|----------|
| GPIO-interrupt i hårdvarumodul | **Avgörande** — polling lägger till intervalltid |
| HTTP localhost (2 anrop) | 2–6 ms totalt — inte ett problem |
| Python-overhead i engine | < 1 ms för enkel graftraversering |
| `async_mode='threading'` i socketio | Hanterar concurrent requests korrekt |

---

## Nästa steg (backlog)

Vad som redan är implementerat (executors, live-status, simulering) står i `management/CLAUDE.md` och hålls där — listas inte igen här för att undvika att två listor glider isär.

**Kvarstående:**
- **`password_lock`-executor saknas** — komponenten finns definierad i `component_library.json` men har ingen `_exec_password_lock` i `engine.py` än.
- **Floor 2 Web App Bridge-appen behöver (åter)skrivas** — `terminal_gate`-noden och HTTP-kontraktet finns (se sektionen nedan), men själva telefon-/terminalappen finns inte på Pi:n just nu. Se `Z:\CLAUDE.md` → Next Step.
- **Komponentbibliotek: disconnected-indikator** — visa om en hårdvarumodul inte är ansluten.

### Kända hårdvaruproblem

- **WS2812B — signalintegritet på datalinjen.** En äldre observation var att sista LED:n flackade under kontinuerliga uppdateringar (pulse/rainbow) medan fast sken var stabilt — matchar bristande signalintegritet, inte strömförsörjning. En senare, mer akut variant (slumpmässiga pixlar i fel färg) diagnostiserades och delvis åtgärdades 2026-08-29 (write-lock + `dma=5`) — se `Z:\CLAUDE.md` → **"WS2812B – Slumpmässiga färgblinkningar (2026-08-29)"** för aktuell status och den kvarstående accepterade risken. Den definitiva fixen för båda är sannolikt densamma: nivåomvandlare (74AHCT125/74HCT245) + seriemotstånd på DIN. Inte kritiskt för Diamond Heist i nuvarande version.

---

## Web App Bridge — Terminal Interface

En **Web App Bridge** är en extern webbapp som integreras med GameForge via HTTP: GameForge styr appen med enable/disable-kommandon och appen rapporterar `success`/`failure` tillbaka som events. `terminal_gate` (Floor 2:s hacker-terminal för Diamond Heist) är den avsedda första implementationen av mönstret, men mönstret i sig är generiskt och återanvändbart för vilken extern app som helst.

> **Status:** noden och kontraktet nedan är implementerade i GameForge (`_exec_terminal_gate` i `engine.py`), men den faktiska appen som ska svara på `/enable`/`/disable`/`/api/validate` — tänkt att köras som en fristående Flask-app på port 8080, t.ex. `terminal_web.py` — finns inte på Pi:n just nu (verifierat 2026-09-03). Kontraktet nedan är alltså specifikationen för vad den appen behöver implementera, inte en beskrivning av något som redan kör.

**Signalflöde:**
```
[USB Device Detector]  yubikey_inserted
        │
        ▼
[Web App Bridge]        params: App URL, Override Code
  enable ──────────────► POST /enable { password }
  disable ─────────────► POST /disable
  success ◄─────────────  POST /engine/hardware_event { device_type: terminal_gate, event: success }
  failure ◄─────────────  POST /engine/hardware_event { device_type: terminal_gate, event: failure }
        │
        ▼
[Activate Scene "Floor 3"]
```

**Endpoints (Web App Bridge contract):**

| Endpoint | Role |
|---|---|
| `POST /enable` | GameForge activates the bridge; optional `{ password }` overrides config |
| `POST /disable` | GameForge deactivates the bridge and resets state |
| `GET /api/status` | Returns `{ enabled: bool }` |
| `POST /api/validate` | Validates player input; fires `success` or `failure` to GameForge |
| `GET /api/keys` | SSE stream of Pi keyboard events → phone browser (terminal-specific) |

Password priority: 1) Override code sent by GameForge on `/enable`, 2) app's own config, 3) hardcoded fallback.

---

## Framtidsplan: USB File Pipeline

USB Device Detector skickar redan `mount_point` som del av `usb_memory_inserted`-eventet.
Det lägger grunden för en filläsningspipeline i canvas:

```
[USB Device Detector]
  usb_memory_inserted (mount_point: "/media/pi/USB")
        │
        ▼
[USB File Reader]          ← framtida modul
  params: filename         (ex. "code.txt")
  input:  mount_point
  output: file_content     (textsträng)
        │
        ▼
[Password Lock / Sequence Gate / ...]
```

**Att bygga när behovet uppstår:**

1. **`modules/usb_file_reader.py`** — ny hårdvarumodul (egentligen logic, men hanterar Pi-filsystem)
   - Input: `mount_point` (sträng från USB Device Detector)
   - Param: `filename` (fil att läsa, ex. `"code.txt"`)
   - Output: `file_content` (filens textinnehåll, trimmat)
   - `execute('read', mount_point=..., filename=...)` → `{'content': '...'}`

2. **`engine.py`** — executor för `usb_file_reader`
   - Vid `handle == 'mount_point'`: läs filen, propagera `file_content` nedströms

3. **Canvas-användning:** Dra in USB Device Detector → USB File Reader → Password Lock.
   Spelaren sätter in ett USB-minne med rätt fil → låset öppnas.
