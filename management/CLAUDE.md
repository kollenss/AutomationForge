# GameForge — Claude Instructions

## Serveråtkomst

Projektet körs på en Raspberry Pi 3B. Använd **SSH MCP** (`mcp__mcprouter__ssh_run`) för att köra kommandon på servern.

- **Host:** `diamond.local` (IP: 192.168.68.53)
- **OS:** Raspbian GNU/Linux 12 (Bookworm)
- **Källkod på Pi:** `/home/pi/management/`

## Bygga frontend

```bash
cd /home/pi/management/frontend && npm run build
```

Output hamnar i `../static/` (serveras direkt av Flask).

## Starta Flask-servern

```bash
setsid bash -c 'cd /home/pi/management && python app.py >> /tmp/gameforge.log 2>&1' &
```

SSH-anslutningen kan timeouta vid start — det är normalt. Verifiera med:

```bash
ss -tlnp | grep 5000
```

## Loggar

```bash
tail -50 /tmp/gameforge.log
```

## Stack

- **Backend:** Flask REST API, port 5000
- **Frontend:** React 18 + Vite + @xyflow/react v12
- **Data:** JSON-filer i `/home/pi/management/data/`
