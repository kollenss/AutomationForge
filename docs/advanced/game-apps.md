# Floor Apps

A floor app is a standalone Flask process that runs alongside the three core services to implement game-master UI, prop animations, or other game-specific behaviour that does not fit naturally into the PropForge canvas. The `floor2_terminal` application — a web-based terminal puzzle for floor 2 of the Diamond Heist — is the reference implementation.

## Responsibilities

Floor apps are responsible for their own user interface and game-specific logic. They are deliberately kept outside the PropForge engine so they can be iterated on independently without touching the shared canvas graph.

Typical floor app responsibilities:

- Rendering a game-specific UI in the browser (a fake computer terminal, a hacking minigame, a safe keypad).
- Sending commands to hardware-service to control outputs when a puzzle is solved.
- Receiving activation signals from the PropForge engine when a prerequisite has been completed.

## Communicating with hardware-service

Floor apps never hold GPIO pins or USB devices directly. They call the hardware-service REST API instead:

```python
import requests

def open_door(channel: int):
    """Activate a relay channel via hardware-service."""
    resp = requests.post(
        'http://localhost:5101/hardware/relay_board/on',
        json={'channel': channel},
        timeout=2,
    )
    resp.raise_for_status()
    return resp.json()
```

This keeps all hardware ownership in hardware-service and avoids device conflicts. If the floor app crashes, the relay state is preserved.

## Being activated by the PropForge engine

A common pattern is for the PropForge canvas to unlock a floor app when a prerequisite is satisfied. For example: the player solves the vault on floor 2, which triggers a Relay Channel (door opens) and simultaneously signals `floor2_terminal` to enable the next puzzle.

There are two integration options:

### Option A — HTTP callback endpoint

The floor app exposes an endpoint that the PropForge engine calls when an event fires:

```python
# In floor2_terminal/terminal_web.py
@app.route('/activate', methods=['POST'])
def activate():
    data = request.get_json()
    # Enable the terminal puzzle
    terminal_state['active'] = True
    return jsonify({'ok': True})
```

In the canvas, add a custom logic component (or use the engine's direct trigger) that calls this endpoint. Alternatively, add a call in `_exec_<type>` for the relevant component type:

```python
def _exec_relay(node_id, params, handle, value, emit, propagate, get_state):
    # ... existing relay logic ...
    # Notify floor app if channel 3 activates
    if int(params.get('channel', 1)) == 3 and handle == 'trigger_on':
        try:
            _req.urlopen('http://localhost:8080/activate', timeout=1)
        except Exception:
            pass
```

### Option B — Socket.IO

If the floor app is a real-time application, it can connect as a Socket.IO client to the PropForge engine and listen for specific events:

```javascript
// In the floor app's browser frontend
import { io } from 'socket.io-client';
const socket = io('http://raspberrypi.local:5000');

socket.on('relay_state', (state) => {
    if (state['3'] === true) {
        enableTerminalPuzzle();
    }
});
```

This avoids polling and gives sub-100 ms reaction time.

## Starting a floor app

Floor apps are currently started manually, not via systemd:

```bash
nohup python3 /home/pi/floor2_terminal/terminal_web.py > /tmp/terminal_web.log 2>&1 &
```

To view the log:

```bash
tail -f /tmp/terminal_web.log
```

To stop it:

```bash
pkill -f terminal_web.py
```

## Port conventions

| App | Port | Notes |
|---|---|---|
| PropForge engine | 5000 | Always running via systemd |
| hardware-service | 5101 | Always running via systemd |
| floor2_terminal | 8080 | Started manually for active game sessions |

!!! tip "Verify all ports are up"
    Before a game session starts, run `ss -tlnp | grep -E '5000|5101|8080'` to confirm all expected services are listening.
