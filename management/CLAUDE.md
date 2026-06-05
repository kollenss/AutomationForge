# GameForge — Claude Instructions

## Sessionstart — läs alltid dessa filer först

Innan du skriver en enda rad kod eller föreslår en lösning, läs:
1. `Z:\management\GAMEFORGE.md` — arkitektur, konventioner, recept
2. `Z:\PIN_MAP.md` — GPIO-tilldelningar

---

## Källkod & filåtkomst

Källkoden redigeras **lokalt på Windows-klienten** via Samba-share:

- **Windows-sökväg:** `Z:\management\` (rooten för detta projekt)
- **Samma katalog på Pi:** `/home/pi/management/`
- `Z:` är en nätverksdisk monterad mot Pi:ns `/home/pi/management/`

**Använd alltid `Z:\management\...` som sökväg** när du läser eller redigerar filer.  
Git-kommandon (`git push` etc.) körs via **Bash-verktyget** direkt på Windows-klienten: `cd /z && git push`.  
Z:-shatten är monterad på Windows-maskinen — Bash-verktyget kör där och har tillgång till den.  
**Använd aldrig SSH MCP för git push.**  
Bygge (`npm run build`) och `systemctl restart` körs via **SSH MCP** på Pi:n.

## Serveråtkomst

Projektet körs på en Raspberry Pi 3B. Använd **SSH MCP** (`mcp__mcprouter__ssh_run`) för att köra kommandon på servern.

- **Host:** `diamond.local` (IP: 192.168.68.53)
- **OS:** Raspbian GNU/Linux 12 (Bookworm)
- **Källkod på Pi:** `/home/pi/management/`
- **Hårdvarumoduler:** `/home/pi/modules/`

## Tjänster (systemd)

Alla tjänster startar automatiskt vid Pi-boot. Starta/stoppa/status manuellt:

```bash
sudo systemctl start|stop|restart pigpiod
sudo systemctl start|stop|restart hardware-service
sudo systemctl start|stop|restart gameforge
```

Startordning: **pigpiod → hardware-service → gameforge** (hanteras av systemd via `Requires=`)

Floor 2 terminal startas fortfarande manuellt:
```bash
nohup python3 /home/pi/floor2_terminal/terminal_web.py > /tmp/terminal_web.log 2>&1 &
```

Verifiera portar:
```bash
ss -tlnp | grep -E '5000|5101|8080'
```

## Bygga frontend

```bash
cd /home/pi/management/frontend && npm run build
```

Output hamnar i `../static/` (serveras direkt av Flask). Kör alltid på Pi via SSH — npm fungerar inte på Samba-shatten (EPERM på nätverksdisk).

Efter build: `sudo systemctl restart gameforge`

## Loggar

```bash
journalctl -u hardware-service -f
journalctl -u gameforge -f
journalctl -u pigpiod -n 20 --no-pager
tail -f /tmp/terminal_web.log
```

## Språk

All GUI-text ska vara på **engelska** — knappar, labels, statusar, felmeddelanden, placeholders etc.
Kod, kommentarer och konversation med användaren är på svenska.

## Stack

- **pigpiod:** systemd-daemon — GPIO-åtkomst för pigpio (KY-040 encoder etc.)
- **hardware-service:** Flask, port 5101 — äger all hårdvara, `/home/pi/modules/`
- **gameforge:** Flask + Socket.IO, port 5000 — REST API + GameEngine + frontend
- **GameForge frontend:** React 18 + Vite + @xyflow/react v12 + socket.io-client
- **Floor 2 terminal:** Flask, port 8080 — anropar hardware_service för relästyrning
- **Data:** JSON-filer i `/home/pi/management/data/`
- **Git repo:** https://github.com/kollenss/AutomationForge

---

## Kod-navigation

Läs detta innan du söker igenom koden — det sparar tid.

### Var saker finns

| Vad | Fil |
|-----|-----|
| Logic-komponentdefinitioner (inputs/outputs/params) | `Z:\management\component_library.json` |
| Hårdvarukomponentdefinitioner | `get_components()` i `/home/pi/modules/<modul>.py` |
| Engine-exekverare (spellogik per komponenttyp) | `Z:\management\engine.py` — `_exec_<type>()` + `_EXECUTORS`-dict |
| Hårdvaruevent-mottagning & Socket.IO-emit | `Z:\management\app.py` — `api_engine_hardware_event()` |
| Canvas-kortrendering (handles + live-status) | `Z:\management\frontend\src\components\ComponentNode.jsx` |
| Signal flow-visualisering (Debug mode + Log) | `Z:\management\frontend\src\pages\SceneEditorPage.jsx` |
| Projektsparning | `Z:\management\data\projects\<uuid>.json` |
| Djup arkitekturdokumentation | `Z:\management\GAMEFORGE.md` |
| GPIO-pinntilldelning (alla 40 pinnar, status, komponent) | `Z:\PIN_MAP.md` |
| Strategisk vision, roadmap, kommersiella vinklar | `memory/strategy_gameforge.md` (i Claude memory-mappen) |

### Hårdvaruevent-flöde

```
HW-modul callback (ex. knapp trycks)
  → hardware_service.py anropar event_cb('click', {'encoder_id': 1})
  → POST /engine/hardware_event  { device_type, event, value }
  → app.py → engine.process_hardware_event()
      matchar noder på componentType (+ params-matchning om value är dict)
      anropar executor med handle=event, scalar value
  → executor propagerar till nästa nod via propagate('output_handle', value)
  → engine.process_event() emittar node_pulse + edge_pulse per traverserad kant
  → Socket.IO push till frontend (separat, inte i den tidskritiska kedjan)

Signal flow-visualisering (Debug mode):
  node_pulse  { node_id }                                    — nod aktiverades
  edge_pulse  { edge_id, value, target_handle }             — kant traverserades, inkl. värde och målhandtag
  Frontend lyssnar endast när Debug ON (toggle i SceneEditor-headern, sparas i localStorage).
  Signal Log visar: tidsstämpel, kant/nod-label, target handle-label, signalvärde (trunkerat till 20 tecken).
  Signal Log spelar in events (max 500) och kan spelas upp i slow-motion (0.1×–1×).
```

### Engine-exekverare (nuläge)

| Komponenttyp | Funktion | Status |
|---|---|---|
| `relay_channel` | `_exec_relay` | ✅ implementerad |
| `rfid_auth` | `_exec_rfid_auth` | ✅ implementerad |
| `combo_lock` | `_exec_combo_lock` | ✅ implementerad |
| `dfplayer` | `_exec_dfplayer` | ✅ implementerad |
| `max7219` | `_exec_max7219` | ✅ implementerad |
| `servo` | `_exec_servo` | ✅ implementerad |
| `timer` | `_exec_timer` | ✅ implementerad |
| `set_value` | `_exec_set_value` | ✅ implementerad |
| `terminal_gate` | `_exec_terminal_gate` | ✅ implementerad (label: "Web App Bridge"; outputs: `success`, `failure`) |
| `led_zone`      | `_exec_led_zone`      | ✅ implementerad (WS2812B zone; inputs: set_color/blink/pulse/chase/rainbow/off; output: done) |
| `activate_scene`, `deactivate_scene` | inline i `process_event` | ✅ implementerad |
| `on_scene_start` | ingen executor (fires externt) | ✅ implementerad |
| `checklist`     | `_exec_checklist`     | ✅ implementerad (step_1–step_6 i ordning → complete / out_of_order) |
| `password_lock` | saknas | ⏳ finns i library, ej i engine |

### Executor-signatur

```python
def _exec_<type>(node_id, params, handle, value, emit, propagate, get_state):
    # handle       — vilket input som triggar (ex. 'enable', 'delta', 'test_code')
    # params       — komponentens konfigurerade parametrar (dict)
    # propagate(output_handle, value)  — skickar värde nedströms i grafen
    # get_state(defaults)              — mutable per-nod state dict (persisterar)
    # emit('socket_event', payload)    — Socket.IO push till frontend
```

### Komponentdefinition — schema

Både `component_library.json` och `get_components()` på Pi använder samma schema:

```json
{
  "type": "my_component",
  "inputs":  [{"key": "enable", "label": "Activate", "description": "Kort hjälptext"}],
  "outputs": [{"key": "done",   "label": "Done",      "description": "Kort hjälptext"}]
}
```

`description` visas som tooltip på canvas-kortet (lagt till 2025-05).

---

## Vanliga ändringsrecept

### Ny output på ett hårdvarukort
1. `/home/pi/modules/<modul>.py` → `get_components()` outputs + `_on_<event>()` i Device-klassen
2. `Z:\management\engine.py` → hantera nytt handle i `_exec_<type>()`
3. Starta om: `sudo systemctl restart hardware-service gameforge`
4. Frontend visar den nya outputen automatiskt — bygg bara om canvas-kortet behöver ändras

### Ny input på ett logic-kort
1. `Z:\management\component_library.json` → lägg till i komponentens `inputs`-array
2. `Z:\management\engine.py` → lägg till `if handle == 'new_handle':` i `_exec_<type>()`
3. Bygg React + starta om: `npm run build && sudo systemctl restart gameforge`

### Ny komponenttyp (logic)
1. `component_library.json` → ny post med type, inputs, outputs, params
2. `engine.py` → skriv `_exec_<type>()` + registrera i `_EXECUTORS`-dict
3. Bygg React + starta om gameforge

### Ny komponenttyp (hårdvara)
1. Skapa `/home/pi/modules/<modul>.py` med `MANIFEST`, `get_components()`, `Device`
2. Skriv `_exec_<type>()` i `engine.py` + registrera i `_EXECUTORS`
3. Starta om hardware-service + gameforge (hårdvarumodulen laddas automatiskt)
4. Bygg React om live-status på kortet behövs (`ComponentNode.jsx`)

---

## Canvas-kort: live-status och simulering

### Live-status per komponenttyp

| Komponenttyp | Socket-event | Vad visas på kortet |
|---|---|---|
| `relay_channel` | `relay_state` | Grön/grå prick + ON/OFF |
| `ky040_encoder` | `encoder_state` | Position + riktningspil |
| `combo_lock` | `combo_state` | INACTIVE / PHASE X/4 / FAILED / UNLOCKED |
| `timer` | `timer_state` | Återstående sekunder, grön dot när aktiv |
| `max7219` | `max7219_state` | Displayinnehåll i 7-segment-stil (orange text på svart) |

Nya live-statuses läggs till i `ComponentNode.jsx`:
1. Skriv en React-komponent som lyssnar på relevant socket-event, filtrerar på `node_id`
2. Emita eventet från `_exec_<type>()` i `engine.py` med `emit('event_name', {'node_id': node_id, ...})`
3. Rendera komponenten i `ComponentNode` villkorligt på `data.componentType`
4. Lägg till CSS i `ComponentNode.css` (återanvänd `.cn-combo-status`-mönstret)

### Hårdvarusimulering (utan fysisk hårdvara)

Simuleringsknappar på canvas-kortet låter dig köra hela engine-kedjan utan inkopplad hårdvara. De POSTar till `/engine/hardware_event` — samma flöde som riktig hårdvara.

| Komponenttyp | Simuleringskontroller |
|---|---|
| `ky040_encoder` | ◀ (delta -1), ● (click), ▶ (delta +1) |
| `rfid_reader` | UID-textfält + Scan-knapp |
| `usb_device_detector` | Dropdown (YubiKey / USB Memory) + Insert + Remove |

**Viktigt:** Knappar i canvas-kort måste stoppa event-propagation på både `onMouseDown` och `onClick` för att inte öppna NodeModal:
```jsx
<button onMouseDown={e => e.stopPropagation()} onClick={e => { e.stopPropagation(); doSomething() }}>
```

Lägg till ny simulering:
1. Skriv en `<TypeSim>`-komponent i `ComponentNode.jsx`
2. Rendera den villkorligt på `data.componentType` i `ComponentNode`
3. POST-payload: `{ device_type, event, value: { ...params, ...eventData } }`

### Set Value — asynkron propagering
`_exec_set_value` propagerar med 50 ms fördröjning (`threading.Timer`) så att kortets pulse-animation hinner renderas innan nedströmsnoder aktiveras. Utan fördröjningen batchas React-uppdateringarna och kortet glöder inte.

### Scenaktivering

Scener har ett `active: bool`-fält i project JSON. Bara aktiva sceners noder exekveras — hardware events ignoreras för inaktiva scener.

```
POST /engine/activate_scene   { scene_id, project_id }
POST /engine/deactivate_scene { scene_id, project_id }
```

Socket.IO-event: `scene_state { scene_id, active }` — emittas vid förändring.  
ProjectsPage lyssnar på `scene_state` och uppdaterar grön/grå dot + Activate-knapp per scen i realtid.

**Nya param-typen `scene_select`** i `component_library.json`: renderas som dropdown med projektets scener. NodeModal tar emot `scenes`-prop från SceneEditorPage.

**Engine-metoder:** `activate_scene()`, `deactivate_scene()`, `get_scene_id_by_name()`, `set_activation_callback(fn)` — callback sätts av `app.py` (`_persist_scene_state`) för att spara till JSON + emittera socket-event.

### Web App Bridge — Terminal Interface (`/home/pi/floor2_terminal/terminal_web.py`)

Fristående Flask-app på port 8080. Implementerar Web App Bridge-kontraktet — styrs av GameForge via HTTP och rapporterar `success`/`failure` tillbaka. Startar alltid i `enabled: false`.

**Konfigureringsvariabler i toppen av filen (lätta att byta för ny implementation):**

| Variabel | Beskrivning |
|---|---|
| `GAMEFORGE_URL` | URL till GameForge-instansen |
| `DEVICE_TYPE` | Måste matcha nodens `type` i component_library.json (`terminal_gate`) |
| `CONFIG_PATH` | Sökväg till config.json med fallback-lösenord |
| `KEYBOARD_DEVICE` | evdev-sökväg till Pi:ns USB-tangentbord |

**Web App Bridge-kontrakt (endpoints):**

| Endpoint | Funktion |
|---|---|
| `POST /enable` | GameForge aktiverar bryggan; optional `{ password }` overridar config |
| `POST /disable` | GameForge deaktiverar bryggan, rensar state |
| `GET /api/status` | `{ enabled: bool }` |
| `POST /api/validate` | Validerar spelarens input; POSTar `success` eller `failure` till GameForge |
| `GET /api/keys` | SSE-stream av Pi-tangentbordstryckningar → telefonbrowser (terminal-specifik) |
