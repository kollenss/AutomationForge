# Relay Board

**Module file:** `modules/relay_trigger.py`  
**Device type:** `relay_board` (manifest) / `relay_channel` (canvas component)  
**Category:** Output

## What it does

The relay board module controls a USB 4-channel relay board that connects to the Pi via USB. Each relay channel can independently switch an external circuit on or off — typical uses include triggering door locks (solenoids), turning on lights, or activating props.

The board is identified by its FTDI serial number (`DAE000iW` in the current configuration). Communication uses the `pylibftdi` library in bit-bang mode; no GPIO pins are used.

## Wiring

Connect the USB relay board to any USB port on the Pi. No other wiring to the Pi is needed. Each relay channel has three screw terminals: **COM** (common), **NO** (normally open), and **NC** (normally closed).

For most prop applications:

- Wire your load between **COM** and **NO**.
- When the relay is ON, COM–NO is closed (circuit active).
- When the relay is OFF, COM–NO is open (circuit inactive).

## Canvas component: Relay Channel

Each relay channel is a separate canvas component. You can place up to four Relay Channel cards on the canvas, one per channel.

### Parameters

| Key | Label | Type | Default | Description |
|---|---|---|---|---|
| `channel` | Channel | select | 1 | Which relay channel (1–4) this node controls |
| `name` | Label | text | `solenoid` | Display label shown on the canvas card header |

### Input handles

| Handle | Label | Description |
|---|---|---|
| `trigger_on` | Turn ON | Closes the relay channel, activating the connected circuit |
| `trigger_off` | Turn OFF | Opens the relay channel, deactivating the circuit |

### Output handles

| Handle | Label | Description |
|---|---|---|
| `state` | Current State | Fires with the updated state dict (`{"1": true, "2": false, …}`) after each change |

## Commands (REST API)

```bash
# Activate channel 2
curl -X POST http://<pi-hostname>:5101/hardware/relay_board/on \
     -H 'Content-Type: application/json' \
     -d '{"channel": 2}'

# Deactivate channel 2
curl -X POST http://<pi-hostname>:5101/hardware/relay_board/off \
     -H 'Content-Type: application/json' \
     -d '{"channel": 2}'

# Get current state of all channels
curl http://<pi-hostname>:5101/hardware/relay_board/state
```

Response from `/state`:

```json
{"1": false, "2": true, "3": false, "4": false}
```

## Bit mapping

The FTDI chip operates in bit-bang mode. The port byte maps relay channels to specific bits:

| Channel | Bit mask |
|---|---|
| 1 | `0x02` |
| 2 | `0x08` |
| 3 | `0x20` |
| 4 | `0x80` |

All four channels are set atomically in a single write, so activating channel 2 does not disturb channels 1, 3, or 4.

!!! warning "No simulate command"
    The relay board is output-only. There is no simulate command because output devices respond to explicit commands — you can test them by sending `on`/`off` REST calls directly.
