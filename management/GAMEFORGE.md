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
├── modules/                      Hårdvarumoduler (en fil per enhet)
│   ├── hardware_service.py       Flask REST API (port 5101) — äger all hårdvara
│   ├── relay_trigger.py          USB Relay Board (4 kanaler, trigger_on/trigger_off)
│   ├── rotary_encoder.py         KY-040 encoder(s) — interrupt-driven, delta-events
│   ├── encoder.py                RotaryEncoder-klass (återanvänds av rotary_encoder.py)
│   └── ...                       Framtida moduler (RFID, DFPlayer, etc.)
│
└── management/
    ├── app.py                    Flask + Socket.IO (port 5000)
    ├── engine.py                 GameEngine — server-side grafexekverare
    ├── component_library.json    Statiska Logic-komponenter
    ├── data/
    │   └── projects/             En JSON-fil per projekt (UUID.json)
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
                ├── ComponentNode.jsx   (RelayStatus + EncoderStatus live på kortet)
                ├── NodeModal.jsx
                └── NodeModal.css
```

---

## Hardware Service (`modules/hardware_service.py`)

En enda Flask-tjänst på port 5101 som **äger all hårdvara**. Både GameForge och Web App Bridges (t.ex. floor2_terminal) pratar med denna tjänst istället för att hålla hårdvara direkt.

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
- **Backup/migrering = Export/Import** (knappar i ProjectsPage). Export laddar ner alla projekt som en JSON-bundle med scenens `active`-flagga strippad; Import återställer (skip/overwrite/duplicate). Använd detta för att seeda en ny Pi eller flytta arbete — t.ex. innan lånade ninja lämnas tillbaka: Export på ninja → Import på egen Pi.
- **Autostart:** `data/settings.json` (per-instans, gitignorerad) `{ "autostart": { "project_id", "scene_id" } }`. Vid boot laddar `_autoload_engine()` det projektet och aktiverar exakt den scenen (kör `on_scene_start`, som Activate-knappen). Ej satt → fallback: senast ändrade projekt med sparade scen-states. Ställs in via 🚀 "Start on launch"-knappen per scenkort (ett projekt + en scen).

**Hårdvara (proxy till hardware_service):**
```
GET  /api/hardware/relay               → state {1: bool, 2: bool, ...}
POST /api/hardware/relay/:ch/on        → slå på kanal
POST /api/hardware/relay/:ch/off       → slå av kanal
```

---

## Frontend (React + React Flow)

- **React 18** + **@xyflow/react v12** + **React Router v6**
- **Vite** — output till `management/static/`
- SPA; Flask catch-all serverar `index.html` för alla icke-API-rutter
- **Drag-and-drop:** native DOM `dragover`/`drop`-lyssnare (React Flows egna events störde)
- **UUID:** `crypto.randomUUID()` kräver HTTPS — använder `Math.random()`-baserad `uid()`

---

## Komponentbiblioteket

`component_library.json` innehåller **bara Logic-komponenter** (Password Lock, Sequence Gate, Timer, Note). Hårdvarukomponenter (Input/Output) genereras dynamiskt av modulerna via hardware_service.

### Schema för en komponent

```json
{
  "type": "relay_channel",
  "label": "Relay Channel",
  "subtitle": "USB Relay Board",
  "color": "#f59e0b",
  "icon": "⚡",
  "display_param": "channel",        // Visas som badge på canvas-kortet
  "params": [
    {
      "key": "channel",
      "label": "Channel (1–4)",
      "type": "number",
      "default": 1,
      "min": 1,                      // Begränsar input i modalen
      "max": 4                       // Sätts dynamiskt från MANIFEST.channels
    },
    {
      "key": "name",
      "label": "Label",
      "type": "text",
      "default": "solenoid"          // Visas som subtitle på canvas-kortet
    }
  ],
  "inputs":  [{ "key": "trigger", "label": "Trigger" }],
  "outputs": [{ "key": "state",   "label": "State"   }]
}
```

**Param-typer:**
| Typ | Input | Kommentar |
|-----|-------|-----------|
| `text` | `<input type=text>` | Visas som subtitle på kortet om key=`name` |
| `number` | `<input type=number>` | Respekterar `min`/`max` |
| `password` | `<input type=password>` | |
| `select` | `<select>` | Kräver `options: [{value, label}]` |
| `boolean` | `<input type=checkbox>` | |
| `pin` | `<input type=number>` | Hint om fysiskt board-pinnummer |

**Canvas-kortet:**
- `display_param` → badge (t.ex. kanalnummer) i kortets header
- `params.name` → visas som subtitle (ersätter standard-subtitle)

---

## Live-status på canvas-kort

Komponenter visar live-status direkt på canvas-kortet via Socket.IO — **ingen polling**.

| Komponenttyp | Socket-event | Vad visas |
|---|---|---|
| `relay_channel` | `relay_state` | Grön/grå prick + ON/OFF |
| `ky040_encoder` | `encoder_state` | Position-räknare + riktningspil |
| `combo_lock` | `combo_state` | INACTIVE / PHASE X/4 / FAILED / UNLOCKED |
| `timer` | `timer_state` | Nedräkning i sekunder, grön dot när aktiv |
| `max7219` | `max7219_state` | Displaytext i 7-segment-stil på kortet |

Live-statuses filtreras på `node_id` (utom relay och encoder som filtrerar på kanal/encoder_id).

## Hårdvarusimulering på canvas-kort

Input-komponenter har simuleringskontroller direkt på kortet för att testa utan fysisk hårdvara. POSTar till `/engine/hardware_event` — identiskt med riktiga hårdvaru-events.

| Komponenttyp | Kontroller |
|---|---|
| `ky040_encoder` | ◀ (delta -1) · ● (click) · ▶ (delta +1) |
| `rfid_reader` | UID-textfält + Scan-knapp (Enter fungerar också) |

## Live-testning i NodeModal

`NodeModal.jsx` har ett `LIVE_COMPONENTS`-objekt som mappar komponenttyp → React-komponent:

```js
const LIVE_COMPONENTS = {
  relay_channel: ({ params }) => <RelayLive channel={params?.channel ?? 1} />,
}
```

### `RelayLive` (implementerad)

- Hämtar initial state via `GET /api/hardware/relay` vid mount
- Uppdateras via `relay_state` socket-event (ingen polling)
- ON/OFF-knappar — state uppdateras via socket efter toggle

Lägg till ny live-sektion:
1. Skriv React-komponent i `NodeModal.jsx`
2. Prenumerera på relevant socket-event (eller lägg till nytt i `app.py`)
3. Registrera i `LIVE_COMPONENTS`

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

```bash
# Bygga frontend (på Pi via SSH — kör INTE npm på Samba-share, ger EPERM):
cd /home/pi/AutomationForge/management/frontend && npm run build
# Output hamnar i ../static/ — efter build:
sudo systemctl restart propforge

# Tjänster hanteras av systemd (autostart vid boot):
sudo systemctl start|stop|restart pigpiod
sudo systemctl start|stop|restart hardware-service
sudo systemctl start|stop|restart propforge

# Startordning: pigpiod → hardware-service → propforge (hanteras av Requires=)
# OBS: huvudtjänsten heter propforge (inte gameforge).
```

---

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

### Socket.IO-events (engine → frontend)

| Event | Payload | Trigger |
|-------|---------|---------|
| `relay_state` | `{"1": bool, ...}` | Varje relay-kommando |
| `encoder_state` | `{device_type, encoder_id, position, delta}` | Varje encoder-steg |
| `combo_state` | `{node_id, enabled?, phase?, count?, unlocked?, failed?}` | Varje combo_lock-tillståndsändring |
| `timer_state` | `{node_id, remaining, running}` | Start, varje tick, reset |
| `max7219_state` | `{node_id, text, scrolling}` | Varje text/show/scroll/clear-kommando |
| `node_pulse` | `{node_id}` | Nod aktiverades (debug mode) |
| `edge_pulse` | `{edge_id, value, target_handle}` | Kant traverserades (debug mode) |
| `scene_state` | `{scene_id, active}` | Scen aktiverades eller deaktiverades |

### Executors (`engine.py`)

```python
_EXECUTORS = {
    'relay_channel': _exec_relay,  # Stöder trigger_on / trigger_off som separata handles
}
```

Lägg till ny executor för ny komponenttyp:
1. Skriv `_exec_<type>(params, handle, value, emit)` i `engine.py`
2. Registrera i `_EXECUTORS`

### Latenskritisk väg

| Faktor | Påverkan |
|--------|----------|
| GPIO-interrupt i hårdvarumodul | **Avgörande** — polling lägger till intervalltid |
| HTTP localhost (2 anrop) | 2–6 ms totalt — inte ett problem |
| Python-overhead i engine | < 1 ms för enkel graftraversering |
| `async_mode='threading'` i socketio | Hanterar concurrent requests korrekt |

---

## Nästa steg (backlog)

### Implementerat ✅

- [x] **`engine.py`** — server-sida grafexekverare i GameForge
- [x] **Socket.IO** (`flask-socketio`) — push till frontend utan polling
- [x] **Relay live-status** — direkt på canvas-kortet via `relay_state` socket-event
- [x] **Interrupt-driven input** — KY-040 encoder med GPIO-interrupt + callback
- [x] **KY-040 encoder-modul** — `rotary_encoder.py`, multi-encoder-stöd via ENCODERS-lista
- [x] **Encoder live-status** — position + riktningspil på canvas-kortet via `encoder_state`
- [x] **Systemd-services** — pigpiod + hardware-service + gameforge autostart vid boot
- [x] **Scenaktivering** — `active`-flagga per scen, engine filtrerar hårdvaru-events till aktiva scener
- [x] **on_scene_start** — Logic-kort som fires en gång när scenen aktiveras
- [x] **activate_scene / deactivate_scene** — Logic-kort med `scene_select`-dropdown
- [x] **Web App Bridge** — Logic-kort som integrerar extern webbapp via HTTP; skickar enable/disable, tar emot `success`/`failure`-events
- [x] **USB Device Detector-simulering** — dropdown YubiKey/USB Memory + Insert/Remove
- [x] **Scennamn inline-redigering** — klicka scennamn i ProjectsPage för att byta namn

### Hårdvarumoduler att lägga till

| Modul | Live-test i GameForge | Engine-event |
|-------|----------------------|-------------|
| NeoPixel Ring | Välj färg, tänd/släck | Output-only |

### Platform

- **Komponentbibliotek: disconnected-indikator** — visa om modul inte är ansluten

### Kända hårdvaruproblem (fixas senare)

- **WS2812B: sista LED flackar under pulse/rainbow.** Fast sken (`set_color`) är
  stabilt, men vid kontinuerliga uppdateringar flackar sista lampan på alla färger
  utom ren röd/grön. Inte ström (2 LED drar nästan inget; fast vitt sken är stabilt)
  och inte en latch-artefakt (ghost-pixel i slutet med `led_count+1` hjälpte inte).
  Det är signalintegritet på datalinjen. Åtgärder, billigast → definitiv:
  1. Verifiera gemensam, kort, grov GND mellan Pi och strippens 5V-källa.
  2. 330–470Ω serieresistor på DIN nära första LED + kort datakabel.
  3. Level shifter 3,3V→5V (74AHCT125 / 74HCT245) på DIN — definitiv fix.
  4. Ev. 1000µF över 5V/GND vid strippen (mest relevant med fulla strippen).
  Ej kritiskt för Diamond Heist nu; tas när hela 10-LED-strippen kopplas in.

---

## Web App Bridge — Terminal Interface

`/home/pi/floor2_terminal/terminal_web.py` — fristående Flask-app på port 8080.

En **Web App Bridge** är en extern webbapp som integreras med GameForge via HTTP. GameForge styr appen med enable/disable-kommandon och appen rapporterar `success`/`failure` tillbaka som events. Denna implementation är en hacker-terminal för Diamond Heist — men mönstret är generiskt och går att återanvända för vilken extern app som helst.

Startas manuellt vid boot (se CLAUDE.md). `floor2_terminal/` är gitignorerad.

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

Password priority: 1) Override code sent by GameForge on `/enable`, 2) `config.json`, 3) hardcoded fallback `DEFAULT_PASSWORD`.

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
