# Hardware Service

The hardware service (`modules/hardware_service.py`) is a Flask application running on port **5101**. Its single responsibility is to own all physical hardware on the Pi. Every other part of the system — the PropForge engine, floor apps, and the browser developer panel — talks to hardware exclusively through this service. No other process holds GPIO pins, opens SPI devices, or accesses USB peripherals directly.

## Why a separate service?

Having one owner for all hardware solves several practical problems:

- **No GPIO conflicts.** Only one process initialises each pin or SPI device. The rotary encoder interrupt fires once, in one place.
- **Floor apps stay simple.** `floor2_terminal` can open a magnetic lock by sending a POST request without knowing anything about relay board serial numbers or bit masks.
- **Module hot-reload.** Restarting `hardware-service` reloads all modules without touching the engine or the frontend.
- **Simulated hardware.** Modules can expose `simulate_*` commands on their `execute()` method, letting designers test the full graph without physical devices.

## Module auto-discovery

On startup, the hardware service scans every `.py` file in the `modules/` directory. A file is loaded as a hardware module if and only if it defines both a `MANIFEST` dict and a `Device` class. Files that lack either (test scripts, utilities, the service itself) are silently skipped.

```python
# Discovery logic in hardware_service.py
for path in sorted(SHARED_DIR.glob('*.py')):
    if 'MANIFEST' not in source or 'Device' not in source:
        continue   # not a module — skip
    # import, instantiate Device(), register event callback
```

After a module is loaded, the service calls `Device()` to instantiate it. If instantiation fails (e.g. the relay board is not connected), the module is recorded with `connected: false` and an error message, but the service continues running. The engine can still load and execute graphs; commands to the missing device will return a `503` error.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/hardware` | List all discovered modules with manifest and `connected` status |
| `GET` | `/components` | Component definitions from all loaded modules, grouped by category |
| `GET` | `/hardware/<type>/state` | Current state dict from `device.get_state()` |
| `POST` | `/hardware/<type>/<cmd>` | Execute a command on the device. Body is a JSON object of keyword arguments. |

The `/components` endpoint is called by the React frontend to populate the component library panel. It merges hardware-module components (from `get_components()`) with the static logic components in `component_library.json`.

## Event callback flow

Input hardware modules (buttons, RFID readers, USB detectors) need to push events upstream to the engine when something happens. They do this through a callback registered by the hardware service at load time:

```
1. hardware-service instantiates Device()
2. hardware-service calls device.set_event_callback(fn)
   where fn = lambda event, value: POST /engine/hardware_event
3. Device runs its polling thread or interrupt handler
4. When a physical event fires, Device calls self._callback(event, value)
5. hardware-service POSTs { device_type, event, value } to the engine
6. Engine looks up matching canvas nodes and propagates the signal
```

The callback is a plain Python function call; the HTTP POST to the engine happens synchronously in the same thread. If the engine is not running, the `urlopen` call times out after 2 seconds and the exception is silently swallowed — the hardware service keeps working.

!!! note "Output modules do not use callbacks"
    Relay boards, DFPlayer audio modules, and servo controllers have no `set_event_callback`. They only respond to commands. The engine calls `POST /hardware/<type>/<cmd>` when an output node is triggered.
