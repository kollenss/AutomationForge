# PropForge

!!! warning "Frozen snapshot — not actively maintained"
    This documentation site is a point-in-time snapshot and may be out of date.
    The current source of truth lives in the repository — see
    [`management/GAMEFORGE.md`](https://github.com/kollenss/AutomationForge/blob/main/management/GAMEFORGE.md)
    and [`CLAUDE.md`](https://github.com/kollenss/AutomationForge/blob/main/CLAUDE.md).

**PropForge** is a no-code platform for designing, wiring, and running physical escape room puzzles using a Raspberry Pi and DIY electronics. Instead of writing Python scripts to connect buttons to relays or RFID readers to solenoids, you drag hardware components onto a visual canvas and draw lines between their outputs and inputs. The platform takes care of the rest.

## What it does

At its core, PropForge is a browser-based graph editor backed by a server-side execution engine running on a Raspberry Pi. When a player taps an RFID card, presses a button, or inserts a USB key, the hardware module fires an event. That event travels through the canvas graph — triggering logic nodes, activating outputs, and pushing live feedback back to the designer's browser in real time.

The same platform that you use to design the game also runs it. There is no separate deploy step: save the project, and the engine immediately reflects the updated graph.

## Who it is for

- **Escape room designers** who want to build hardware-driven puzzles without writing GPIO code.
- **Makers and hobbyists** who want to wire sensors, relays, RFID readers, and audio players together through a visual interface.
- **Game masters** who need to monitor and manually trigger puzzle events from a control panel during a live game.

## Key concepts

| Concept | Description |
|---|---|
| **Project** | A named collection of scenes, saved as a JSON file on the Pi. |
| **Scene** | A single canvas — nodes and edges that define one puzzle or area. |
| **Component** | A draggable card on the canvas representing a hardware device or a logic gate. |
| **Handle** | An input or output connection point on a component card. |
| **Edge** | A wire drawn between an output handle and an input handle. |
| **Engine** | The server-side process that executes the graph when hardware events arrive. |

## Quick navigation

- [Architecture overview](architecture/overview.md) — how the services fit together.
- [Installation](getting-started/installation.md) — get PropForge running on your Pi.
- [First Project](getting-started/first-project.md) — wire a button to a relay in under 10 minutes.
- [Hardware Modules](hardware-modules/index.md) — supported sensors and actuators.

!!! tip "Diamond Heist"
    The Diamond Heist escape room is the first game built entirely inside PropForge. All three floors — including the RFID vault, the combo lock, and the USB challenge — are configured as PropForge projects running on a single Raspberry Pi 3B.
