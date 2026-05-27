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

---

## Arkitektur

```
AutomationForge/
├── modules/                      Hårdvarumoduler (en fil per enhet)
│   ├── hardware_service.py       Flask REST API (port 5101) — äger all hårdvara
│   ├── relay_trigger.py          USB Relay Board (MANIFEST + Device + get_components)
│   └── ...                       Framtida moduler (RFID, DFPlayer, etc.)
│
└── management/
    ├── app.py                    Flask REST API (port 5000)
    ├── component_library.json    Statiska Logic-komponenter
    ├── data/
    │   └── projects/             En JSON-fil per projekt (UUID.json)
    ├── static/                   Byggd React-app (serveras av Flask)
    └── frontend/                 React-källkod (byggs med Vite)
        └── src/
            ├── App.jsx
            ├── api.js
            ├── pages/
            │   ├── ProjectsPage.jsx
            │   └── SceneEditorPage.jsx
            └── components/
                ├── ComponentLibrary.jsx
                ├── ComponentNode.jsx
                ├── NodeModal.jsx
                └── NodeModal.css
```

---

## Hardware Service (`modules/hardware_service.py`)

En enda Flask-tjänst på port 5101 som **äger all hårdvara**. Både GameForge och spel-appar (floor2_terminal) pratar med denna tjänst istället för att hålla hårdvara direkt.

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
    n = MANIFEST['channels']
    return [{ 'type': 'relay_channel', ..., 'min': 1, 'max': n }]

class Device:
    def get_state(self): ...     # → dict
    def execute(self, cmd, **kwargs): ...  # → dict
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
```

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

## Live-testning per komponenttyp

`NodeModal.jsx` har ett `LIVE_COMPONENTS`-objekt som mappar komponenttyp → React-komponent:

```js
const LIVE_COMPONENTS = {
  relay_channel: ({ params }) => <RelayLive channel={params?.channel ?? 1} />,
  // rfid_rc522: ({ params }) => <RfidLive />,   ← kommande
}
```

### `RelayLive` (implementerad)

- Pollar `/api/hardware/relay` var 2:e sekund
- Visar ON/OFF-status per kanal med färgad dot
- ON/OFF-knappar — disabled när redan i det läget
- Mountas om med ny key när kanal ändras (säkerställer korrekt polling)

Lägg till ny live-sektion:
1. Skriv React-komponent i `NodeModal.jsx`
2. Lägg till Flask-proxy i `app.py` → hardware_service
3. Implementera `Device.execute()` i modulen
4. Registrera i `LIVE_COMPONENTS`

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
# Bygga frontend (på Pi via SSH):
cd /home/pi/management/frontend && npm run build

# Starta i rätt ordning:
nohup python3 /home/pi/modules/hardware_service.py > /tmp/hardware_service.log 2>&1 &
nohup python3 /home/pi/management/app.py > /tmp/gameforge.log 2>&1 &
```

---

## Nästa steg (backlog)

**Hårdvarumoduler att konvertera till ny service-arkitektur:**
| Modul | Live-test i GameForge |
|-------|----------------------|
| RFID RC522 | Visa senast läst kort-UID |
| KY-040 Encoder | Visa aktuellt värde |
| MAX7219 Display | Skicka text/nummer |
| DFPlayer Mini | Spela spår, volymkontroll |
| NeoPixel Ring | Välj färg, tänd/släck |
| Servo SG90 | Sätt vinkel |

**Platform:**
- **Export till Python-kod** — generera floor-script från canvas-konfiguration
- **Scene-dependencies** — definiera vad som triggar vad (utanför canvasen)
- **Systemd-services** — autostart av hardware_service + GameForge vid Pi-boot
- **Komponentbibliotek från manifest** — `ComponentLibrary`-panelen visar connected/disconnected per komponent
