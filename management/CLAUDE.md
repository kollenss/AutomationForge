# GameForge — Claude Instructions

## Serveråtkomst

Projektet körs på en Raspberry Pi 3B. Använd **SSH MCP** (`mcp__mcprouter__ssh_run`) för att köra kommandon på servern.

- **Host:** `diamond.local` (IP: 192.168.68.53)
- **OS:** Raspbian GNU/Linux 12 (Bookworm)
- **Källkod på Pi:** `/home/pi/management/`
- **Hårdvarumoduler:** `/home/pi/modules/`

## Tjänster (systemd)

Alla tjänster startar automatiskt vid Pi-boot. Starta/stoppa/status manuellt:

```bash
sudo systemctl start|stop|restart pigpiod
sudo systemctl start|stop|restart hardware-service
sudo systemctl start|stop|restart gameforge
```

Startordning: **pigpiod → hardware-service → gameforge** (hanteras av systemd via `Requires=`)

Floor 2 terminal startas fortfarande manuellt:
```bash
nohup python3 /home/pi/floor2_terminal/terminal_web.py > /tmp/terminal_web.log 2>&1 &
```

Verifiera portar:
```bash
ss -tlnp | grep -E '5000|5101|8080'
```

## Bygga frontend

```bash
cd /home/pi/management/frontend && npm run build
```

Output hamnar i `../static/` (serveras direkt av Flask). Kör alltid på Pi via SSH — npm fungerar inte på Samba-shatten (EPERM på nätverksdisk).

Efter build: `sudo systemctl restart gameforge`

## Loggar

```bash
journalctl -u hardware-service -f
journalctl -u gameforge -f
journalctl -u pigpiod -n 20 --no-pager
tail -f /tmp/terminal_web.log
```

## Språk

All GUI-text ska vara på **engelska** — knappar, labels, statusar, felmeddelanden, placeholders etc.
Kod, kommentarer och konversation med användaren är på svenska.

## Stack

- **pigpiod:** systemd-daemon — GPIO-åtkomst för pigpio (KY-040 encoder etc.)
- **hardware-service:** Flask, port 5101 — äger all hårdvara, `/home/pi/modules/`
- **gameforge:** Flask + Socket.IO, port 5000 — REST API + GameEngine + frontend
- **GameForge frontend:** React 18 + Vite + @xyflow/react v12 + socket.io-client
- **Floor 2 terminal:** Flask, port 8080 — anropar hardware_service för relästyrning
- **Data:** JSON-filer i `/home/pi/management/data/`
- **Git repo:** https://github.com/kollenss/AutomationForge
