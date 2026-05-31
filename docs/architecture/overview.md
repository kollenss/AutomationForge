# Architecture Overview

PropForge runs as three cooperating services on a single Raspberry Pi. Each service has a single responsibility; they communicate over localhost HTTP and Socket.IO.

## Services

| Service | Port | Language | Responsibility |
|---|---|---|---|
| **pigpiod** | — | C daemon | Low-level GPIO access (PWM, interrupts) |
| **hardware-service** | 5101 | Python / Flask | Owns all physical hardware; one REST endpoint per device |
| **PropForge engine** | 5000 | Python / Flask + Socket.IO | Graph executor, project storage, React frontend |

### Startup order

Services must start in dependency order. `systemd` handles this automatically via `Requires=` directives:

```
pigpiod  →  hardware-service  →  propforge (engine + frontend)
```

If `hardware-service` starts before `pigpiod`, hardware modules that require pigpio will fail to initialise and be marked as `connected: false`. The engine continues to work — it simply has no hardware backend for those modules.

## Data flow

```
┌─────────────────────────────────────────────┐
│               Raspberry Pi 3B               │
│                                             │
│  ┌──────────┐    interrupts / SPI / I2C     │
│  │  pigpiod │◄──────────────────────────── physical hardware
│  └──────────┘                               │  (buttons, RFID, encoders…)
│        ▲                                    │
│        │  pigpio Python lib                 │
│  ┌─────┴──────────────────┐                 │
│  │   hardware-service     │  port 5101      │
│  │   (Flask REST API)     │                 │
│  │                        │                 │
│  │  auto-discovers modules│                 │
│  │  in /home/pi/modules/  │                 │
│  └────────────┬───────────┘                 │
│               │                             │
│       POST /engine/hardware_event           │
│               │                             │
│  ┌────────────▼───────────┐                 │
│  │   PropForge engine     │  port 5000      │
│  │   (Flask + Socket.IO)  │                 │
│  │                        │                 │
│  │  GameEngine            │                 │
│  │  process_hardware_event│◄─── REST calls from floor apps
│  └────────────┬───────────┘                 │
│               │  Socket.IO                  │
│               │  node_pulse / edge_pulse    │
│  ┌────────────▼───────────┐                 │
│  │   React frontend       │                 │
│  │   (served by Flask)    │◄────────────── browser
│  └────────────────────────┘                 │
└─────────────────────────────────────────────┘
```

## Floor apps

Floor apps (e.g. `floor2_terminal`) are standalone Flask processes that run alongside the three core services. They do not talk to hardware directly. Instead they:

1. Call `hardware-service` to control outputs (e.g. open a relay via `POST /hardware/relay_board/on`).
2. Receive activation signals from the PropForge engine via Socket.IO or direct HTTP.

This keeps all hardware ownership in one place and avoids GPIO conflicts.

## Project storage

Projects are saved as JSON files in `/home/pi/management/data/projects/<uuid>.json`. Each file contains an array of scenes; each scene contains `nodes` (components with params) and `edges` (wires). The engine loads the active project on startup and reloads it whenever the designer saves from the browser.

## Frontend

The React frontend is built with Vite and `@xyflow/react` (React Flow v12). The built output is placed in `/home/pi/management/static/` and served directly by the Flask process on port 5000. No separate Node.js process is needed at runtime.
