# GameForge — Claude Instructions

## Serveråtkomst

Projektet körs på en Raspberry Pi 3B. Använd **SSH MCP** (`mcp__mcprouter__ssh_run`) för att köra kommandon på servern.

- **Host:** `diamond.local` (IP: 192.168.68.53)
- **OS:** Raspbian GNU/Linux 12 (Bookworm)
- **Källkod på Pi:** `/home/pi/management/`
- **Hårdvarumoduler:** `/home/pi/modules/`

## Starta tjänster

Starta alltid i denna ordning:

```bash
# 1. Hardware service (äger all hårdvara)
nohup python3 /home/pi/modules/hardware_service.py > /tmp/hardware_service.log 2>&1 &

# 2. GameForge
nohup python3 /home/pi/management/app.py > /tmp/gameforge.log 2>&1 &

# 3. Floor 2 terminal (Diamond Heist)
nohup python3 /home/pi/floor2_terminal/terminal_web.py > /tmp/terminal_web.log 2>&1 &
```

Verifiera med:
```bash
ss -tlnp | grep -E '5000|5101|8080'
```

## Bygga frontend

```bash
cd /home/pi/management/frontend && npm run build
```

Output hamnar i `../static/` (serveras direkt av Flask).

## Loggar

```bash
tail -50 /tmp/hardware_service.log
tail -50 /tmp/gameforge.log
tail -50 /tmp/terminal_web.log
```

## Stack

- **Hardware service:** Flask, port 5101 — äger all hårdvara, `/home/pi/modules/`
- **GameForge backend:** Flask REST API, port 5000 — proxar hårdvara via hardware_service
- **GameForge frontend:** React 18 + Vite + @xyflow/react v12
- **Floor 2 terminal:** Flask, port 8080 — anropar hardware_service för relästyrning
- **Data:** JSON-filer i `/home/pi/management/data/`
- **Git repo:** https://github.com/kollenss/AutomationForge
