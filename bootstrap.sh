#!/bin/bash
# GameForge bootstrap — kör detta på en färsk Pi med ett enda kommando:
#
#   bash <(curl -sSL https://raw.githubusercontent.com/kollenss/AutomationForge/main/bootstrap.sh)
#
# Kräver: internet via ethernet, användare pi, Raspberry Pi OS Bookworm Lite

set -e

REPO_URL="https://github.com/kollenss/AutomationForge.git"
REPO_DIR="/home/pi/AutomationForge"

echo ""
echo "======================================"
echo "  GameForge Bootstrap"
echo "======================================"
echo ""

# ---------------------------------------------------------------------------
# 1. Klona repot (eller uppdatera om det redan finns)
# ---------------------------------------------------------------------------
if [ -d "$REPO_DIR/.git" ]; then
    echo "==> Repo finns redan, uppdaterar..."
    git -C "$REPO_DIR" pull
else
    echo "==> Klonar GameForge..."
    git clone "$REPO_URL" "$REPO_DIR"
fi

# ---------------------------------------------------------------------------
# 2. Kör install.sh
# ---------------------------------------------------------------------------
echo "==> Startar installation..."
bash "$REPO_DIR/install.sh"

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
echo ""
echo "======================================"
echo "  Bootstrap klar — startar om Pi:n"
echo "======================================"
echo ""
sleep 3
sudo reboot
