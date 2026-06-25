# Writing a Custom Logic Component

Logic components live entirely on the software side: they receive signals, apply some rule, and route the result to one of their outputs. Unlike hardware modules, logic components do not interact with the GPIO or USB subsystems — they are defined in two places: `component_library.json` (the visual definition) and `engine.py` (the execution logic).

This guide walks through adding a new logic component called **Value Gate**, which passes a signal downstream only if its numeric value is above a configured threshold.

## Step 1 — Define the component in component_library.json

Open `Z:\management\component_library.json`. Add a new entry to the `components` array inside the `"logic"` category:

```json
{
  "type":    "value_gate",
  "label":   "Value Gate",
  "subtitle": "Threshold filter",
  "color":   "#8b5cf6",
  "icon":    "🔢",
  "display_param": "name",
  "params": [
    {
      "key":     "threshold",
      "label":   "Threshold",
      "type":    "number",
      "default": 50
    },
    {
      "key":     "name",
      "label":   "Label",
      "type":    "text",
      "default": "gate"
    }
  ],
  "inputs": [
    {
      "key":         "value",
      "label":       "Value Input",
      "description": "Receives a numeric value to compare against the threshold"
    }
  ],
  "outputs": [
    {
      "key":         "above",
      "label":       "Above Threshold",
      "description": "Fires when the input value is greater than or equal to the threshold"
    },
    {
      "key":         "below",
      "label":       "Below Threshold",
      "description": "Fires when the input value is less than the threshold"
    }
  ]
}
```

This is enough to make the component appear in the canvas library and be draggable. Save the file.

## Step 2 — Write the executor in engine.py

Open `Z:\management\engine.py`. Add the executor function alongside the existing `_exec_*` functions:

```python
def _exec_value_gate(node_id, params, handle, value, emit, propagate, get_state):
    """Pass the value downstream on 'above' or 'below' based on a threshold."""
    if handle != 'value':
        return  # only the 'value' input handle is handled

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return  # non-numeric input — ignore

    threshold = float(params.get('threshold', 50))

    if numeric >= threshold:
        propagate('above', numeric)
    else:
        propagate('below', numeric)
```

## Step 3 — Register the executor

In the same file, find the `_EXECUTORS` dict and add the new entry:

```python
_EXECUTORS = {
    'relay_channel': _exec_relay,
    'rfid_auth':     _exec_rfid_auth,
    'combo_lock':    _exec_combo_lock,
    'dfplayer':      _exec_dfplayer,
    'max7219':       _exec_max7219,
    'servo':         _exec_servo,
    'value_gate':    _exec_value_gate,   # ← add this line
}
```

## Step 4 — Deploy

```bash
# Rebuild the React frontend so the new component appears in the library
cd /home/pi/AutomationForge/management/frontend && npm run build

# Restart the engine to load the updated executor
sudo systemctl restart propforge
```

The Value Gate component will now appear under Logic in the canvas library. Drag it onto the canvas, set the threshold, wire a numeric output (e.g. a Rotary Encoder's `position` output or a Combo Lock's `current_value`) to its `value` input, and connect its `above` and `below` outputs to whatever you want to trigger.

## Executor design guidelines

**Use `handle` to distinguish inputs.** If your component has multiple input handles, branch on the `handle` parameter first:

```python
if handle == 'start':
    ...
elif handle == 'reset':
    ...
```

**Use `get_state` for stateful logic.** If the component needs to remember something between calls (a counter, a list of received steps, a timestamp), use `get_state(defaults)`:

```python
state = get_state({'count': 0, 'last_time': 0.0})
state['count'] += 1   # mutate — changes persist automatically
```

**Use `emit` for live UI feedback.** If you want the frontend to show live data (not just node/edge pulses), emit a Socket.IO event:

```python
if emit:
    emit('value_gate_state', {'node_id': node_id, 'value': numeric, 'passed': True})
```

The frontend can subscribe to this event to show a live display on the card (requires a `ComponentNode.jsx` update).

**Use `propagate` to continue the chain.** `propagate(output_handle, value)` fires the output handle and recursively processes all connected downstream nodes. Do not call it for outputs that should not fire — for example, if the value is below the threshold, only call `propagate('below', ...)`, not `propagate('above', ...)`.
