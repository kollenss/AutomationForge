# USB Device Detector

**Module file:** `modules/usb_device_detector.py`  
**Device type:** `usb_device_detector`  
**Category:** Input

## What it does

The USB Device Detector monitors the Pi's USB ports and fires events when specific devices are inserted or removed. It currently detects two device classes:

- **YubiKey** — any USB device with vendor ID `1050` (Yubico). Detected via `lsusb` polling.
- **USB mass storage** — any USB device that Linux mounts as a block device (flash drives, external HDDs). Detected via `lsblk` polling with mount-point tracking.

The detector runs a background thread that polls every 500 ms. Edge detection is done in software: the module compares the current state to the previous state and fires an event only on the transition.

## Canvas component

### Parameters

None — the detector monitors all USB ports automatically.

### Input handles

None.

### Output handles

| Handle | Label | Description |
|---|---|---|
| `yubikey_inserted` | YubiKey Inserted | Fires once when a YubiKey is connected |
| `yubikey_removed` | YubiKey Removed | Fires once when the YubiKey is disconnected |
| `usb_memory_inserted` | USB Memory Inserted | Fires once when a USB mass storage device is mounted. Value includes `mount_point`. |
| `usb_memory_removed` | USB Memory Removed | Fires once when a USB mass storage device is unmounted |

The value for `usb_memory_inserted` and `usb_memory_removed` is a dict: `{"mount_point": "/media/pi/USB"}`. Connect this to a logic node or relay to create puzzles that react to specific USB keys.

## Simulate commands

All four events can be simulated via REST:

```bash
# Simulate YubiKey insertion
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_yubikey_insert \
     -H 'Content-Type: application/json' -d '{}'

# Simulate YubiKey removal
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_yubikey_remove \
     -H 'Content-Type: application/json' -d '{}'

# Simulate USB memory insertion (specify a mount point)
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_memory_insert \
     -H 'Content-Type: application/json' \
     -d '{"mount_point": "/media/pi/EVIDENCE"}'

# Simulate USB memory removal
curl -X POST http://<pi-hostname>:5101/hardware/usb_device_detector/simulate_memory_remove \
     -H 'Content-Type: application/json' \
     -d '{"mount_point": "/media/pi/EVIDENCE"}'
```

Simulate commands update the internal state and fire the real callback, so the engine processes the event exactly as if physical hardware triggered it.

## Current state

```bash
curl http://<pi-hostname>:5101/hardware/usb_device_detector/state
```

```json
{
  "yubikey_present": false,
  "memory_mounts": ["/media/pi/USB"]
}
```

## Detection internals

**YubiKey:** The module runs `lsusb` and searches output lines for the string `1050:`. This matches all Yubico products (YubiKey 5, Security Key, YubiKey Bio).

**USB memory:** The module runs `lsblk --json -o NAME,TRAN,MOUNTPOINT` and collects mount points for all block devices with `tran == "usb"`. It checks both top-level devices and their children (partition entries). A device with no mount point (not yet mounted, or mounted without a user-visible path) is not reported.

!!! note "Mount timing"
    On Raspbian Bookworm, USB mass storage devices are auto-mounted by `udisks2` typically within 1–2 seconds of insertion. The detector will fire `usb_memory_inserted` on the first poll after the mount point appears, which may be 0.5–2.5 seconds after physical insertion.
