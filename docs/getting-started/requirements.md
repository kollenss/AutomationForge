# Requirements

## Hardware

| Item | Notes |
|---|---|
| **Raspberry Pi 3B or 3B+** | The platform is tested on the 3B. A 4 should also work but has not been tested. |
| **MicroSD card** | 16 GB minimum, Class 10 or better. |
| **USB relay board** | 4-channel FTDI-based board (e.g. the common CH340 / DAE000iW board). Connected via USB. |
| **RC522 RFID reader** | SPI, 3.3 V. Connects on the standard SPI0 pins + GPIO 25 for reset. |
| **KY-040 rotary encoder** | Used for the combo lock mechanic. Requires pigpiod for interrupt-driven decoding. |
| **DFPlayer Mini + speaker** | Serial audio module. Connects on UART. |
| **MAX7219 8-digit display** | SPI 7-segment display for showing combo lock digits. |
| **Network switch or router** | The Pi must be reachable from the designer's browser on the same network. |

!!! note "Minimum setup"
    You can run PropForge with no hardware at all. Modules that fail to initialise are marked `connected: false`, and you can use simulate commands to test your canvas graph. A USB relay board is the most useful first piece of hardware to connect.

## Operating system

- **Raspbian GNU/Linux 12 (Bookworm)** — 32-bit or 64-bit Lite image.
- Enable SPI and the serial port in `raspi-config` → Interface Options before installing.

## Software dependencies

### System packages

```bash
sudo apt install -y python3-pip python3-venv python3-setuptools git unzip nodejs npm
```

`pigpio` must be built from source on Bookworm (not available via apt — see [Installation](installation.md)). `nodejs` and `npm` are only needed if you want to rebuild the React frontend from source.

### Python packages

```bash
pip3 install flask flask-socketio pylibftdi mfrc522 RPi.GPIO pigpio
```

| Package | Used by |
|---|---|
| `flask` | hardware-service, engine |
| `flask-socketio` | engine (real-time browser updates) |
| `pylibftdi` | relay_trigger.py (USB relay board via FTDI) |
| `mfrc522` | rfid.py (RC522 reader over SPI) |
| `RPi.GPIO` | various modules |
| `pigpio` | rotary_encoder.py (KY-040 via pigpiod) |

### Frontend build (optional)

The repository ships with a pre-built frontend in `management/static/`. You only need Node.js if you modify the React source code.

```
Node.js 18+
npm 9+
```

!!! warning "Build on the Pi, not over Samba"
    If you access the Pi's filesystem via a Windows network share (Samba), do not run `npm install` or `npm run build` on that share. npm creates symlinks and hard links that fail on NTFS-over-Samba. Always run `npm` commands via SSH on the Pi directly.

## Network

The browser communicates with the Pi over HTTP and WebSocket. There are no cloud dependencies — everything runs locally.

- PropForge engine: `http://<pi-hostname>:5000`
- Hardware service: `http://<pi-hostname>:5101` (usually not accessed directly by the browser)

The Pi's hostname is typically `raspberrypi.local` on a fresh install. You can change it in `raspi-config`.
