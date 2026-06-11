# Installation

This guide walks through setting up PropForge on a Raspberry Pi running Raspbian Bookworm. All commands are run on the Pi via SSH unless otherwise noted.

!!! tip "Automated install"
    A single-command install script is available at the root of the repo:
    ```bash
    bash /home/pi/AutomationForge/install.sh
    ```
    Follow the manual steps below if you prefer to understand each stage or need to troubleshoot.

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
sudo apt install -y python3-pip python3-venv python3-setuptools git unzip nodejs npm
```

!!! note "`distutils` missing on Python 3.12"
    Raspberry Pi OS Bookworm ships Python 3.12 which removed `distutils`. `python3-setuptools` restores it.

`pigpio` is not available as an apt package on Raspberry Pi OS Bookworm — build it from source:

```bash
cd /home/pi
wget https://github.com/joan2937/pigpio/archive/master.zip
unzip master.zip
cd pigpio-master
make
sudo make install
cd /home/pi
```

## 3. Clone the repository

```bash
cd /home/pi
git clone https://github.com/kollenss/AutomationForge.git
# Files land in /home/pi/AutomationForge/
```

If you are working from a local Windows machine with the Pi share mounted as `Z:\`, the equivalent paths are:

- Pi: `/home/pi/AutomationForge/modules/` → Windows: `Z:\AutomationForge\modules\`
- Pi: `/home/pi/AutomationForge/management/` → Windows: `Z:\AutomationForge\management\`

## 4. Install Python dependencies

```bash
sudo pip3 install flask flask-socketio pylibftdi mfrc522 RPi.GPIO pigpio --break-system-packages
```

!!! note "Bookworm requires `--break-system-packages`"
    Raspberry Pi OS Bookworm marks the system Python as externally managed. The `--break-system-packages` flag is required to install into the system site-packages so that systemd services can import them. Using `pip3` without `sudo` installs to `~/.local` which is not visible to services running as the `pi` user.

## 5. Build the frontend

The repository does not ship pre-built frontend assets. Build them on the Pi:

```bash
cd /home/pi/AutomationForge/management/frontend
npm install
npm run build
```

The build output is written to `management/static/assets/`. This step is required — without it the UI at port 5000 will load a blank page.

!!! warning "Do not run npm over a Samba share"
    If you access the Pi filesystem from Windows via a network share, always run `npm install` and `npm run build` via SSH on the Pi, not from the mounted drive. npm creates symlinks that fail on NTFS-over-Samba.

## 6. Configure systemd services

### pigpiod

Building pigpio from source does not install a systemd unit. Create one manually:

```bash
sudo tee /etc/systemd/system/pigpiod.service > /dev/null << 'EOF'
[Unit]
Description=Daemon required to control GPIO pins via pigpio
After=network.target

[Service]
ExecStart=/usr/local/bin/pigpiod -l
ExecStop=/bin/systemctl kill pigpiod
Type=forking

[Install]
WantedBy=multi-user.target
EOF
```

### hardware-service

```bash
sudo tee /etc/systemd/system/hardware-service.service > /dev/null << 'EOF'
[Unit]
Description=PropForge Hardware Service
After=pigpiod.service
Requires=pigpiod.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/AutomationForge/modules/hardware_service.py
WorkingDirectory=/home/pi/AutomationForge/modules
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
EOF
```

### propforge

```bash
sudo tee /etc/systemd/system/propforge.service > /dev/null << 'EOF'
[Unit]
Description=PropForge Engine
After=hardware-service.service
Requires=hardware-service.service

[Service]
ExecStart=/usr/bin/python3 /home/pi/AutomationForge/management/app.py
WorkingDirectory=/home/pi/AutomationForge/management
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
EOF
```

Enable and start all services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pigpiod hardware-service propforge
sudo systemctl start pigpiod hardware-service propforge
```

## 7. Add udev rule for the FTDI relay board

This allows the relay board to be accessed without root:

```bash
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ftdi.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

## 8. Verify services are running

```bash
sudo systemctl status pigpiod hardware-service propforge --no-pager
```

All three should show `active (running)`. Check logs if not:

```bash
journalctl -u hardware-service -n 40 --no-pager
journalctl -u propforge -n 40 --no-pager
```

## 9. Open the interface

Navigate to `http://<pi-ip>:5000` in a browser on the same network.

!!! note "Port 5101 returns 404 on `/`"
    This is normal. Port 5101 is the hardware service REST API used internally by the engine — it has no root page.

!!! tip "Finding the Pi's IP"
    Run `ip addr show wlan0` on the Pi, or check your router's DHCP table.

## Managing services

```bash
# Restart after code changes
sudo systemctl restart hardware-service
sudo systemctl restart propforge

# View live logs
journalctl -u propforge -f
journalctl -u hardware-service -f
```
