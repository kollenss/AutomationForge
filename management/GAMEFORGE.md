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
| Som designer vill jag länka outputs till inputs (visuellt) | ✅ |
| Som designer vill jag se live-status på reläkortet | ✅ |
| Som designer vill jag slå på/av enskilda reläkanaler | ✅ |

---

## Arkitektur

```
management/
├── app.py                    Flask REST API (port 5000)
├── component_library.json    Komponentdefinitioner
├── data/
│   └── projects/             En JSON-fil per projekt (UUID.json)
├── static/                   Byggd React-app (serveras av Flask)
└── frontend/                 React-källkod (byggs med Vite)
    ├── src/
    │   ├── App.jsx            Router
    │   ├── api.js             API-klient
    │   ├── pages/
    │   │   ├── ProjectsPage.jsx    Projektlista + scen-lista
    │   │   └── SceneEditorPage.jsx Canvas-editorn
    │   └── components/
    │       ├── ComponentLibrary.jsx  Höger panel – dra-och-släpp
    │       ├── ComponentNode.jsx     Custom React Flow node
    │       ├── NodeModal.jsx         Modal vid klick på nod
    │       └── NodeModal.css
    ├── package.json
    └── vite.config.js         Bygger till ../static/
```

### Backend (Flask)

Ren REST API. Ingen spellogik, ingen hårdkodad spelreferens.

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

**Komponentbibliotek:**
```
GET    /api/components         → returnerar component_library.json
```

**Hårdvara:**
```
GET    /api/hardware/relay               → state för alla 4 kanaler {1: bool, ...}
POST   /api/hardware/relay/:ch/on        → slå på kanal
POST   /api/hardware/relay/:ch/off       → slå av kanal
```

**Relay-singleton:** `RelayBoard` från `shared/relay_trigger.py` instansieras EN gång vid första anrop och hålls öppen. `close()` anropas aldrig (den nollställer utgångarna). State trackas i `_relay_state`-dict i minnet.

### Frontend (React + React Flow)

- **React 18** + **@xyflow/react v12** (React Flow) + **React Router v6**
- **Vite** som build tool — output till `management/static/`
- SPA med hash-less routing; Flask catch-all serverar `index.html` för alla icke-API-rutter
- **Drag-and-drop:** native DOM `dragover`/`drop`-lyssnare på canvas-wrapper (React Flows egna event-handlers störde, native DOM-listeners kringgår det)
- **UUID:** `crypto.randomUUID()` fungerar inte på HTTP (kräver HTTPS) — använder `Math.random()`-baserad UUID-funktion istället
- **`screenToFlowPosition`** från `useReactFlow()`-hooken (inte `onInit`-pattern)

---

## Komponentbiblioteket (`component_library.json`)

Komponentdefinitioner är statiska JSON. Tre kategorier: **Input**, **Output**, **Logic**.

### Schema för en komponent

```json
{
  "type": "relay_channel",          // Unikt ID, används som node-typ i canvas
  "label": "Relay Channel",         // Visningsnamn
  "subtitle": "USB Relay Board",    // Chip/modul-namn
  "color": "#f59e0b",               // Kategorifärg (syns på noden och i modalen)
  "icon": "⚡",                      // Emoji-ikon
  "params": [                       // Konfigurerbara parametrar
    {
      "key": "channel",             // Nyckel i node.data.params
      "label": "Channel (1–4)",
      "type": "number",             // text | number | password | select | boolean | pin
      "default": 1
    }
  ],
  "inputs":  [{ "key": "trigger", "label": "Trigger" }],   // Inkommande handles
  "outputs": [{ "key": "state",   "label": "State"   }]    // Utgående handles
}
```

**Param-typer:**
| Typ | Input-element | Kommentar |
|-----|--------------|-----------|
| `text` | `<input type=text>` | |
| `number` | `<input type=number>` | |
| `password` | `<input type=password>` | T.ex. lösenkod |
| `select` | `<select>` | Kräver `options: [{value, label}]` |
| `boolean` | `<input type=checkbox>` | |
| `pin` | `<input type=number>` | Visar hint om att det är fysiskt boardnummer |

---

## Live-testning per komponenttyp

Modalen (`NodeModal.jsx`) har ett `LIVE_COMPONENTS`-objekt som mappar komponenttyp → React-komponent:

```js
const LIVE_COMPONENTS = {
  relay_channel: (params) => <RelayLive channel={params?.channel ?? 1} />,
  // rfid_rc522: (params) => <RfidLive />,   ← kommande
  // encoder_ky040: ...
  // dfplayer: ...
}
```

Lägg till en ny live-sektion genom att:
1. Skriva en ny React-komponent (t.ex. `RfidLive`) i `NodeModal.jsx`
2. Lägga till Flask-endpoints under `/api/hardware/`
3. Registrera i `LIVE_COMPONENTS`-mappen

### `RelayLive` (implementerad)

- Pollar `/api/hardware/relay` var 2:e sekund
- Visar ON/OFF-status med färgad dot (grön/grå)
- ON/OFF-knappar — aktiv knapp dimmas (disabled när redan i det läget)
- Vid fel: "Board not connected"

---

## Datamodell – Projekt-JSON

```json
{
  "id": "uuid",
  "name": "The Diamond Heist",
  "description": "...",
  "created_at": "2026-05-27T21:00:00Z",
  "updated_at": "2026-05-27T22:00:00Z",
  "scenes": [
    {
      "id": "uuid",
      "name": "Floor 1 – The Plan",
      "nodes": [
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
            "params": { "channel": 1, "name": "panel_lock" },
            "inputHandles":  [{ "key": "trigger", "label": "Trigger" }],
            "outputHandles": [{ "key": "state",   "label": "State" }]
          }
        }
      ],
      "edges": [
        {
          "id": "uuid",
          "source": "node-id",
          "sourceHandle": "card_detected",
          "target": "node-id-2",
          "targetHandle": "trigger",
          "animated": true
        }
      ]
    }
  ]
}
```

---

## Build & Deploy

```bash
# På Pi (via SSH):
cd /home/pi/management/frontend
npm install      # Bara första gången
npm run build    # Bygger till /home/pi/management/static/

# Starta Flask:
cd /home/pi/management
python app.py    # Kör på port 5000
```

Flask serveras via `setsid bash -c '...' &` för att detacha från SSH-sessionen.

**OBS:** `crypto.randomUUID()` kräver HTTPS. Appen serveras på HTTP. Använd `uid()`-funktionen i frontend-koden (Math.random-baserad UUID v4).

---

## Nästa steg (backlog)

| Komponent | Live-test |
|-----------|-----------|
| RFID RC522 | Visa senast läst kort-UID |
| DFPlayer Mini | Spela spår, volymkontroll |
| KY-040 Encoder | Visa aktuellt värde |
| MAX7219 Display | Skicka text/nummer |
| NeoPixel Ring | Välj färg, tänd/släck |
| Servo SG90 | Sätt vinkel |

- **Export till Python-kod** — generera floor-script från canvas-konfiguration
- **Scene-dependencies** — definiera vad som triggar vad (utanför canvasen)
- **Systemd-service** — autostart av GameForge vid Pi-boot
