# First Project: Button → Relay

This walkthrough creates the simplest possible PropForge project: a USB relay channel that activates when a signal arrives. If you have a relay board connected, the relay will physically click. If you don't, you can use a simulated trigger to test the graph.

By the end of this guide you will understand how to create a project, add a scene, place components, configure their parameters, wire them together, and fire a test signal.

## Step 1 — Create a project

1. Open `http://<pi-hostname>:5000` in your browser.
2. On the Projects page, click **New Project**.
3. Give the project a name, e.g. `Hello World`, and click **Create**.

The project opens to an empty scene.

## Step 2 — Add a scene

A fresh project has no scenes. Click **Add Scene** in the left panel and name it `Main`. The canvas editor opens for that scene.

## Step 3 — Open the component library

The left-hand panel shows all available components, grouped by category:

- **Input** (green) — hardware that generates events: RFID readers, encoders, USB detectors.
- **Output** (amber) — hardware that receives commands: relay channels, audio players, servos.
- **Logic** (purple) — software components: RFID Auth gate, Combo Lock, Timer.

Components that are not physically connected to the Pi are shown with a faded border but can still be placed on the canvas and triggered via simulate commands.

## Step 4 — Place a Relay Channel

Find **Relay Channel** in the Output section and drag it onto the canvas. A card appears with two input handles on the left:

- **Turn ON** — activates the relay channel.
- **Turn OFF** — deactivates it.

And one output handle on the right:

- **Current State** — fires with the updated on/off value whenever the relay changes.

Click the card to open its parameter panel. Set **Channel** to `1` and give it a label like `door lock`. Click **Save**.

## Step 5 — Test the relay directly

With no wiring needed, you can already test the relay. With the relay board connected:

1. Visit `http://<pi-hostname>:5101/hardware/relay_board/state` to see current channel states.
2. Send a command manually:

```bash
curl -X POST http://<pi-hostname>:5101/hardware/relay_board/on \
     -H 'Content-Type: application/json' \
     -d '{"channel": 1}'
```

The relay should click. This confirms hardware-service is working.

## Step 6 — Add a trigger source (optional wiring demo)

To wire a signal source to the relay, drag a **USB Device Detector** component from the Input section onto the canvas. This component fires events when a YubiKey or USB memory stick is inserted.

You will see four output handles on the right side of the USB Device Detector card:

- YubiKey Inserted
- YubiKey Removed
- USB Memory Inserted
- USB Memory Removed

## Step 7 — Wire them together

Click and drag from the **YubiKey Inserted** output handle on the USB Device Detector to the **Turn ON** input handle on the Relay Channel card. A line (edge) appears connecting them.

Do the same for **YubiKey Removed** → **Turn OFF**.

!!! tip "Connecting handles"
    Output handles are on the right side of a card; input handles are on the left. You can only connect an output to an input — the canvas will not allow you to connect two outputs or two inputs together.

## Step 8 — Save the project

Click **Save** (or press `Ctrl+S`). The engine reloads the graph immediately. You will see a brief confirmation in the browser.

## Step 9 — Test without a YubiKey

If you do not have a YubiKey, you can simulate the insertion event:

```bash
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_yubikey_insert \
     -H 'Content-Type: application/json' \
     -d '{}'
```

The engine receives a `yubikey_inserted` event, traverses the edge to the Relay Channel node, and fires `POST /hardware/relay_board/on` with `{"channel": 1}`. In the browser, enable Debug Mode (the bug icon in the scene editor header) to watch the signal flow animate along the edge in real time.

## What you have built

```
[USB Device Detector]
  yubikey_inserted ──────► trigger_on  [Relay Channel ch.1]
  yubikey_removed  ──────► trigger_off [Relay Channel ch.1]
```

Every time a YubiKey is inserted, channel 1 closes. Every time it is removed, channel 1 opens. This is the foundation for more complex puzzles: add an RFID Auth gate to only allow certain cards, or chain a DFPlayer to play a sound when the relay fires.
