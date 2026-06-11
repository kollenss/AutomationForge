# Installation

This guide walks through setting up PropForge on a Raspberry Pi running Raspbian Bookworm. All commands are run on the Pi via SSH unless otherwise noted.

## 1. Prepare the Pi

Enable SPI (needed for the RC522 RFID reader and MAX7219 display) and the serial port (needed for DFPlayer):

```bash
sudo raspi-config
# → Interface Options → SPI → Enable
# → Interface Options → Serial Port → Enable (disable login shell, enable hardware)
```

Reboot after making changes.

## 2. Install system dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git unzip
```

`pigpio` is not available as an apt package on Raspberry Pi OS Bookworm — build it from source:

```bash
wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip
cd pigpio-master
make
sudo make install
cd ..
```

If you plan to rebuild the frontend:

```bash
sudo apt install -y nodejs npm
```

## 3. Clone the repository

```bash
cd /home/pi
git clone https://github.com/kollenss/AutomationForge.git
# Files land in /home/pi/AutomationForge/
```

If you are working from a local Windows machine with the Pi share mounted as `Z:\`, the equivalent paths are:

- Pi: `/home/pi/modules/` → Windows: `Z:\modules\`
- Pi: `/home/pi/management/` → Windows: `Z:\management\`

## 4. Install Python dependencies

```bash
pip3 install flask flask-socketio pylibftdi mfrc522 RPi.GPIO pigpio
```

## 5. Configure systemd services

Create service unit files so that all three services start automatically on boot and restart if they crash.

### pigpiod

pigpiod ships with a unit file. Enable it:

```bash
sudo systemctl enable pigpiod
sudo systemctl start pigpiod
```

### hardware-service

Create `/etc/systemd/system/hardware-service.service`:

```ini
[Unit]
Description=PropForge Hardware Service
After=pigpiod.service
Requires=pigpiod.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/modules/hardware_service.py
WorkingDirectory=/home/pi/modules
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
```

### propforge

Create `/etc/systemd/system/propforge.service`:

```ini
[Unit]
Description=PropForge Engine
After=hardware-service.service
Requires=hardware-service.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/management/app.py
WorkingDirectory=/home/pi/management
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
```

Enable and start both:

```bash
sudo systemctl daemon-reload
sudo systemctl enable hardware-service propforge
sudo systemctl start hardware-service propforge
```

## 6. Verify services are running

Check that all three ports are listening:

```bash
ss -tlnp | grep -E '5000|5101'
```

Expected output:

```
LISTEN  0  5  0.0.0.0:5101  ...  python3 (hardware-service)
LISTEN  0  5  0.0.0.0:5000  ...  python3 (propforge)
```

Check service logs if something is not listening:

```bash
journalctl -u hardware-service -n 40 --no-pager
journalctl -u propforge -n 40 --no-pager
```

## 7. Open the interface

Navigate to `http://<pi-hostname>:5000` in a browser on the same network. You should see the PropForge projects page.

!!! tip "Finding the Pi's hostname"
    Run `hostname` on the Pi to see its hostname. On most home networks you can reach it at `http://raspberrypi.local:5000`. If mDNS does not work, use the IP address shown by `ip addr show wlan0`.

## Managing services

```bash
# Restart after code changes
sudo systemctl restart hardware-service
sudo systemctl restart propforge

# View live logs
journalctl -u propforge -f
journalctl -u hardware-service -f
```
