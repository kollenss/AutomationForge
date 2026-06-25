# Writing a Custom Hardware Module

A custom hardware module is a single Python file dropped into `/home/pi/modules/`. The hardware service discovers it automatically on next restart. This guide walks through writing a complete module from scratch, using a hypothetical magnetic door sensor as the example.

## File naming

Name the file after the device type, using underscores: `door_sensor.py`. The filename does not need to match the `type` key in `MANIFEST`, but keeping them consistent helps.

## Minimal skeleton

```python
# /home/pi/modules/door_sensor.py
import threading
import time

# ── Manifest ──────────────────────────────────────────────────────────────────

MANIFEST = {
    'type':  'door_sensor',    # unique identifier — used in URLs and node types
    'label': 'Door Sensor',   # shown in the /hardware endpoint listing
}

# ── Component definitions ─────────────────────────────────────────────────────

def get_components():
    return [{
        'type':          'door_sensor',
        'label':         'Door Sensor',
        'subtitle':      'Magnetic contact switch',
        'category':      'input',          # 'input' | 'output' | 'logic'
        'color':         '#06b6d4',
        'icon':          '🚪',
        'display_param': 'name',
        'params': [
            {
                'key':     'gpio_pin',
                'label':   'GPIO Pin (BCM)',
                'type':    'number',
                'default': 17,
            },
            {
                'key':     'name',
                'label':   'Label',
                'type':    'text',
                'default': 'door',
            },
        ],
        'inputs':  [],
        'outputs': [
            {
                'key':         'opened',
                'label':       'Door Opened',
                'description': 'Fires once when the door contact opens',
            },
            {
                'key':         'closed',
                'label':       'Door Closed',
                'description': 'Fires once when the door contact closes',
            },
        ],
    }]

# ── Device ────────────────────────────────────────────────────────────────────

class Device:
    def __init__(self):
        self._callback = None
        self._closed = True          # assume door starts closed
        self._stop = threading.Event()

        # Replace this with real GPIO initialisation:
        # import RPi.GPIO as GPIO
        # GPIO.setmode(GPIO.BCM)
        # GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

        t = threading.Thread(target=self._poll_loop, daemon=True, name='door-sensor-poll')
        t.start()
        print('[door_sensor] started')

    def _poll_loop(self):
        while not self._stop.is_set():
            self._check()
            time.sleep(0.1)

    def _check(self):
        # Replace with real GPIO read:
        # pin_high = GPIO.input(17)
        # now_closed = not pin_high   # active-low wiring
        now_closed = self._closed   # placeholder — no change

        if now_closed and not self._closed:
            self._closed = True
            self._fire('closed', {})
        elif not now_closed and self._closed:
            self._closed = False
            self._fire('opened', {})

    def _fire(self, event, value):
        if self._callback:
            self._callback(event, value)

    # ── Hardware service contract ──────────────────────────────────────────────

    def set_event_callback(self, fn):
        self._callback = fn

    def get_state(self):
        return {'closed': self._closed}

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate_open':
            if self._closed:
                self._closed = False
                self._fire('opened', {'simulated': True})
            return self.get_state()

        if cmd == 'simulate_close':
            if not self._closed:
                self._closed = True
                self._fire('closed', {'simulated': True})
            return self.get_state()

        raise ValueError(f'Unknown command: {cmd}')
```

## get_components() schema in full

The table below lists every key accepted in a component definition. All keys marked *required* must be present; the rest are optional.

| Key | Required | Type | Description |
|---|---|---|---|
| `type` | yes | string | Node `componentType` in the canvas. Must be unique. |
| `label` | yes | string | Displayed name of the component |
| `subtitle` | no | string | Second line on the canvas card (e.g. device model) |
| `category` | yes | `'input'` / `'output'` / `'logic'` | Determines panel group and colour |
| `color` | no | CSS colour string | Card accent colour. Defaults to category colour. |
| `icon` | no | string | Emoji or short text shown on the card |
| `display_param` | no | string or `null` | Param key whose value is shown in the card header |
| `params` | yes | array of param objects | Empty array `[]` if no params |
| `inputs` | yes | array of handle objects | Empty array `[]` for pure output devices |
| `outputs` | yes | array of handle objects | Empty array `[]` for pure input devices (rare) |

### Handle object

```json
{
  "key":         "opened",
  "label":       "Door Opened",
  "description": "Fires once when the door contact opens"
}
```

`description` is shown as a tooltip on the canvas card handle.

## Adding a corresponding executor

Placing the module in `/home/pi/modules/` is enough for the component to appear in the library. To make something happen when an event from this module reaches a downstream node, you also need an executor in `management/engine.py`:

```python
# In engine.py — add alongside the other _exec_* functions

def _exec_door_sensor(node_id, params, handle, value, emit, propagate, get_state):
    # This node is an input source — it only propagates its own events.
    # The engine calls this executor when another node is wired FROM door_sensor
    # and needs to respond. Most commonly, door_sensor events go to logic nodes.
    pass  # input-only nodes rarely need an executor

# Register it:
_EXECUTORS['door_sensor'] = _exec_door_sensor
```

Pure input hardware nodes typically do not need executors — their events travel directly to logic or output nodes via edges. You only need an executor for this type if it has input handles that the canvas can trigger.

## Deploy

```bash
# Copy file to Pi
scp door_sensor.py pi@ninja.local:/home/pi/AutomationForge/modules/

# Restart hardware-service to load the new module
sudo systemctl restart hardware-service

# Verify it loaded
curl http://ninja.local:5101/hardware
# Look for {"type": "door_sensor", "connected": true, ...}

# Restart propforge so the frontend gets the updated component list
sudo systemctl restart propforge
```

The component will now appear in the Input section of the canvas library.
