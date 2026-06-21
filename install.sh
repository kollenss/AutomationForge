#!/bin/bash
# PropForge installer for Raspberry Pi OS Bookworm
# Run as the pi user: bash /home/pi/AutomationForge/install.sh

set -e

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOME_DIR="$(eval echo ~${SUDO_USER:-$USER})"
echo "==> PropForge install from: $REPO_DIR"

# ---------------------------------------------------------------------------
# 0. Remind user about raspi-config (must be done manually before running this)
# ---------------------------------------------------------------------------
echo "==> Enabling SPI and Serial via raspi-config..."
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_serial_cons 1

# ---------------------------------------------------------------------------
# 1. System packages
# ---------------------------------------------------------------------------
echo "==> Installing system packages..."
sudo apt update -y
sudo apt install -y python3-pip python3-venv python3-setuptools git unzip nodejs npm

# ---------------------------------------------------------------------------
# 2. pigpio (not in Bookworm apt repos — build from source)
# ---------------------------------------------------------------------------
if ! command -v pigpiod &> /dev/null; then
    echo "==> Building pigpio from source..."
    cd "$HOME_DIR"
    wget -q https://github.com/joan2937/pigpio/archive/master.zip
    unzip -q master.zip
    cd pigpio-master
    make -j4
    sudo make install
    cd "$HOME_DIR"
    rm -rf pigpio-master master.zip
else
    echo "==> pigpio already installed, skipping build."
fi

# ---------------------------------------------------------------------------
# 3. Python packages
# ---------------------------------------------------------------------------
echo "==> Installing Python packages..."
sudo pip3 install flask flask-socketio pylibftdi mfrc522 RPi.GPIO pigpio pyserial --break-system-packages

# ---------------------------------------------------------------------------
# 4. Build frontend
# ---------------------------------------------------------------------------
echo "==> Building frontend..."
cd "$REPO_DIR/management/frontend"
npm install --silent
npm run build

# ---------------------------------------------------------------------------
# 5. systemd unit: pigpiod
# ---------------------------------------------------------------------------
echo "==> Creating pigpiod.service..."
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

# ---------------------------------------------------------------------------
# 6. systemd unit: hardware-service
# ---------------------------------------------------------------------------
echo "==> Creating hardware-service.service..."
sudo tee /etc/systemd/system/hardware-service.service > /dev/null << EOF
[Unit]
Description=PropForge Hardware Service
After=pigpiod.service
Requires=pigpiod.service

[Service]
ExecStart=/usr/bin/python3 $REPO_DIR/modules/hardware_service.py
WorkingDirectory=$REPO_DIR/modules
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------------------
# 7. systemd unit: propforge
# ---------------------------------------------------------------------------
echo "==> Creating propforge.service..."
sudo tee /etc/systemd/system/propforge.service > /dev/null << EOF
[Unit]
Description=PropForge Engine
After=hardware-service.service
# Wants (inte Requires): omstart av hardware-service (t.ex. "Restart Hardware"-
# knappen i UI:t) får INTE cascade-stoppa propforge.
Wants=hardware-service.service

[Service]
ExecStart=/usr/bin/python3 $REPO_DIR/management/app.py
WorkingDirectory=$REPO_DIR/management
Restart=always
RestartSec=3
User=pi

[Install]
WantedBy=multi-user.target
EOF

# ---------------------------------------------------------------------------
# 8. udev rule for FTDI relay board
# ---------------------------------------------------------------------------
echo "==> Adding udev rule for FTDI relay board..."
echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="0403", MODE="0666"' | sudo tee /etc/udev/rules.d/99-ftdi.rules > /dev/null
sudo udevadm control --reload-rules && sudo udevadm trigger

# ---------------------------------------------------------------------------
# 9. Enable and start services
# ---------------------------------------------------------------------------
echo "==> Enabling and starting services..."
sudo systemctl daemon-reload
sudo systemctl enable pigpiod hardware-service propforge
sudo systemctl restart pigpiod hardware-service propforge

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "==> Install complete!"
echo "    UI: http://$(hostname -I | awk '{print $1}'):5000"
echo ""
sudo systemctl status pigpiod hardware-service propforge --no-pager
