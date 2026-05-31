# Hardware Module Contract

A hardware module is a single `.py` file in `/home/pi/modules/`. The hardware service discovers and loads every file that satisfies the contract: it must define a `MANIFEST` dict and a `Device` class. Everything else in the file is ignored by the service.

## MANIFEST

`MANIFEST` is a module-level dict that describes the hardware device. The `type` key is required; it acts as the unique identifier for the device across the whole system.

```python
MANIFEST = {
    'type': 'usb_device_detector',   # required — used as URL segment and node type
    'label': 'USB Device Detector',  # human-readable name shown in the hardware list
}
```

Additional keys (e.g. `serial`, `channels`, `readers`) are passed through to the `/hardware` endpoint and can carry device-specific metadata.

## get_components()

`get_components()` is a module-level function that returns a list of component definitions. Each definition describes one draggable card in the canvas component library. This is how hardware capabilities are exposed to the designer.

```python
def get_components():
    return [{
        'type':          'my_sensor',          # node componentType in the canvas
        'label':         'My Sensor',
        'subtitle':      'Short description',
        'category':      'input',              # 'input' | 'output' | 'logic'
        'color':         '#22c55e',
        'icon':          '🔌',
        'display_param': 'channel',            # param key shown on the card header
        'params': [
            # See param types below
        ],
        'inputs': [
            {'key': 'trigger', 'label': 'Trigger', 'description': 'Activates the device'},
        ],
        'outputs': [
            {'key': 'done', 'label': 'Done', 'description': 'Fires when the action completes'},
        ],
    }]
```

### Param types

| `type` | Description | Extra keys |
|---|---|---|
| `text` | Single-line text input | `default` |
| `number` | Numeric input | `default` |
| `boolean` | Checkbox | `default` |
| `password` | Masked text input | `default` |
| `select` | Dropdown | `default`, `options: [{value, label}]` |

`display_param` names the param key whose current value is shown in the node card header in the canvas. Set it to `null` if no param should be shown.

## Device class

`Device` is instantiated once at startup by the hardware service. It owns the physical hardware for its lifetime. The class must implement these methods:

### `get_state() → dict`

Returns the current observable state of the device as a plain JSON-serialisable dict. Called by `GET /hardware/<type>/state`.

```python
def get_state(self):
    return {'yubikey_present': self._yubikey_present}
```

### `execute(cmd: str, **kwargs) → dict`

Handles a command sent via `POST /hardware/<type>/<cmd>`. The body JSON keys become `**kwargs`. Should raise `ValueError` for unknown commands.

```python
def execute(self, cmd, **kwargs):
    if cmd == 'on':
        self._turn_on()
        return self.get_state()
    raise ValueError(f'Unknown command: {cmd}')
```

### `set_event_callback(fn)` *(input modules only)*

Called by the hardware service immediately after instantiation. `fn` has signature `fn(event: str, value: any)`. Input modules store this function and call it whenever a physical event occurs.

```python
def set_event_callback(self, fn):
    self._callback = fn

# later, in a polling thread or interrupt handler:
def _on_card_read(self, uid):
    if self._callback:
        self._callback('card_read', {'reader_id': 1, 'uid': uid})
```

Output-only modules (relays, audio, servos) do not need `set_event_callback`.

!!! tip "Simulate commands"
    Input modules should implement `simulate_*` commands in `execute()` so designers can test the full graph without physical hardware. For example, `POST /hardware/rfid_reader/simulate` with body `{"uid": "AABBCCDD"}` fires the `card_read` event as if a real card was scanned.
