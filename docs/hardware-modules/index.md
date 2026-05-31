# Hardware Modules

A hardware module is a self-contained Python file in `/home/pi/modules/` that wraps a single physical device. The hardware service loads every file that exports `MANIFEST` and `Device` — no registration or configuration file is needed.

## How modules auto-load

On startup, `hardware_service.py` scans the `modules/` directory alphabetically. For each `.py` file it finds both `MANIFEST` and `Device`, it:

1. Imports the module.
2. Calls `Device()` to instantiate it (which initialises the hardware).
3. If the device has `set_event_callback`, registers a callback that POSTs events to the PropForge engine.
4. Records the module as `connected: true`.

If `Device()` raises an exception (e.g. the USB relay board is not plugged in), the module is still registered but marked `connected: false`. Commands sent to it return HTTP 503. All other modules continue working.

You can see the current status of all loaded modules at:

```
GET http://<pi-hostname>:5101/hardware
```

## Simulate commands

Every input module should implement one or more `simulate_*` commands in its `Device.execute()` method. These let you trigger events from the command line or a test script without physical hardware.

```bash
# Simulate a YubiKey insertion
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_yubikey_insert \
     -H 'Content-Type: application/json' -d '{}'

# Simulate an RFID card scan
curl -X POST http://<pi-hostname>:5101/hardware/rfid_reader/simulate \
     -H 'Content-Type: application/json' -d '{"uid": "AABBCCDD"}'
```

The event is processed exactly as if real hardware fired it — the callback is called, the engine receives the POST, and the canvas graph is traversed.

## Included modules

| Module file | Device type | Category | Description |
|---|---|---|---|
| `relay_trigger.py` | `relay_board` / `relay_channel` | Output | USB 4-channel relay board via FTDI |
| `rfid.py` | `rfid_reader` | Input | RC522 RFID reader via SPI |
| `usb_device_detector.py` | `usb_device_detector` | Input | YubiKey and USB mass storage detection |
| `rotary_encoder.py` | `rotary_encoder` | Input | KY-040 rotary encoder via pigpiod interrupts |
| `servo.py` | `servo` | Output | Servo motor via pigpio PWM |
| `max7219_display.py` | `max7219` | Output | MAX7219 8-digit 7-segment display via SPI |
| `dfplayer.py` | `dfplayer` | Output | DFPlayer Mini audio module via UART |
| `audio.py` | `audio` | Output | Software audio playback via aplay/pygame |
| `actuators.py` | `actuators` | Output | Generic GPIO digital outputs |

See the individual module pages for wiring diagrams, param details, and simulate commands.

!!! note "Adding your own module"
    See [Custom Hardware Modules](../advanced/custom-modules.md) to learn how to write a new module. Any `.py` file you drop into `/home/pi/modules/` with the correct structure will appear in the component library automatically after restarting `hardware-service`.
