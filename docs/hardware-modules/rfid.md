# RFID Reader

**Module file:** `modules/rfid.py`  
**Device type:** `rfid_reader`  
**Category:** Input

## What it does

The RFID module reads 13.56 MHz MIFARE cards using an RC522 reader connected via SPI. When a card is held against the reader, the module fires a `card_read` event containing the card's UID. The same card held continuously does not re-fire — the event fires once per placement and resets when the card is removed.

In PropForge this component is almost always paired with an **RFID Auth** logic node, which checks the UID against a list of valid values and routes the signal to either an `authorized` or `denied` output.

## Wiring

Connect the RC522 to the Pi's SPI0 bus:

| RC522 pin | Pi pin (Board) | GPIO (BCM) |
|---|---|---|
| SDA (CS) | 24 | GPIO 8 (CE0) |
| SCK | 23 | GPIO 11 |
| MOSI | 19 | GPIO 10 |
| MISO | 21 | GPIO 9 |
| RST | 22 | GPIO 25 |
| GND | 6 | — |
| 3.3V | 1 | — |

Enable SPI in `raspi-config` before connecting.

## Canvas component: RFID Reader

### Parameters

| Key | Label | Type | Default | Description |
|---|---|---|---|---|
| `reader_id` | Reader | select | 1 | Which reader (if multiple are configured) |
| `name` | Label | text | `card reader` | Display label on the canvas card |

### Input handles

None — this is a pure input device.

### Output handles

| Handle | Label | Description |
|---|---|---|
| `card_read` | Card UID | Fires with the UID string each time a new card is scanned |

The value carried by `card_read` is a dict: `{"reader_id": 1, "uid": "AABBCCDD"}`. The engine extracts the `uid` scalar before passing it to downstream nodes.

## Simulate command

Test without a physical card:

```bash
curl -X POST http://<pi-hostname>:5101/hardware/rfid_reader/simulate \
     -H 'Content-Type: application/json' \
     -d '{"reader_id": 1, "uid": "AABBCCDD"}'
```

This fires the `card_read` event exactly as if a real card was scanned. The engine processes it normally — the RFID Auth node will check `AABBCCDD` against its configured valid UIDs.

## UID format

UIDs are formatted as 8-character uppercase hex strings (e.g. `A1B2C3D4`). The RC522 returns a 5-byte value where the last byte is a checksum; the module strips the checksum and formats the remaining 4 bytes.

When configuring an **RFID Auth** node, copy the UID from the browser's Signal Log (Debug Mode) or from the hardware service log while holding a real card against the reader:

```bash
journalctl -u hardware-service -f
# Look for: [rfid] card_read reader=1 uid=A1B2C3D4
```

## Adding more readers

The module supports multiple readers by extending the `READERS` list in `rfid.py`. Each reader needs its own CS pin. Only one SPI bus is available on the 3B (SPI0), so additional readers must use software CS via additional GPIO pins — this requires changes to the mfrc522 library initialisation.
