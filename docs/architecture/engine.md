# PropForge Engine

The engine (`management/engine.py`, class `GameEngine`) is the server-side graph executor. It holds the active project in memory, receives hardware events from the hardware service, and walks the canvas graph to trigger component executors. It also pushes real-time visual feedback to the browser via Socket.IO.

## Graph representation

When a project is loaded, `GameEngine.load_project()` flattens all scenes into two in-memory structures:

- `_nodes` — a dict mapping node ID → node dict (type, params).
- `_edges` — a list of edge dicts (source node, source handle, target node, target handle).

```python
engine.load_project(project_json)
# result: _nodes populated from all scenes, _edges collected across all scenes
```

The engine reloads the graph every time the designer saves from the browser. Reloading clears `_node_state`, so stateful components (like Combo Lock) reset.

## Hardware event flow

When a player performs a physical action, the flow is:

```
hardware-service  →  POST /engine/hardware_event
                      { device_type, event, value }
                  →  engine.process_hardware_event(device_type, event, value)
                      find all canvas nodes with componentType == device_type
                      filter by params (encoder_id, reader_id, etc.)
                      emit node_pulse to browser for each matched node
                  →  engine.process_event(node_id, handle=event, value)
                      look up all edges leaving this node on the matching handle
                      for each edge:
                        emit edge_pulse  { edge_id }
                        emit node_pulse  { node_id: target }
                        call executor(target_node, target_handle, value)
                  →  executor propagates downstream via propagate(output_handle, value)
                      recurses back into process_event
```

The graph walk is depth-first and synchronous. All steps happen in the Flask request thread that received the `/engine/hardware_event` POST.

## Executor pattern

Each component type has one executor function registered in `_EXECUTORS`:

```python
_EXECUTORS = {
    'relay_channel': _exec_relay,
    'rfid_auth':     _exec_rfid_auth,
    'combo_lock':    _exec_combo_lock,
    'dfplayer':      _exec_dfplayer,
    'max7219':       _exec_max7219,
    'servo':         _exec_servo,
}
```

Every executor has the same signature:

```python
def _exec_<type>(node_id, params, handle, value, emit, propagate, get_state):
    ...
```

| Parameter | Type | Description |
|---|---|---|
| `node_id` | str | UUID of the canvas node being executed |
| `params` | dict | Configured parameter values (channel number, valid UIDs, etc.) |
| `handle` | str | Name of the input handle that was triggered |
| `value` | any | The scalar value carried by the signal |
| `emit` | callable | `socketio.emit(event, payload)` — push to browser |
| `propagate` | callable | `propagate(output_handle, value)` — fire a downstream output |
| `get_state` | callable | `get_state(defaults)` — retrieve mutable per-node state |

Executors that control hardware (relay, servo, DFPlayer) call `POST /hardware/<type>/<cmd>` on the hardware service. Executors that implement logic (RFID auth, combo lock) compute a result and call `propagate()` on the appropriate output handle.

## Per-node state

Stateful components — currently Combo Lock — need persistent state between calls (current phase, current count, timestamps for debounce). The engine stores this in `_node_state[node_id]`. Executors access it via `get_state(defaults)`:

```python
state = get_state({
    'phase': 0, 'count': 0, 'enabled': False, ...
})
# state is a mutable dict; changes are automatically persisted
```

## Socket.IO events

The engine pushes these events to all connected browser clients:

| Event | Payload | When |
|---|---|---|
| `node_pulse` | `{ node_id }` | A node is activated (source or target of an edge traversal) |
| `edge_pulse` | `{ edge_id }` | An edge is traversed during graph execution |
| `relay_state` | `{ "1": false, "2": true, … }` | Relay board state changes |
| `combo_state` | `{ node_id, phase, count, … }` | Combo lock phase/count updates |

The browser's Debug Mode uses `node_pulse` and `edge_pulse` to animate signal flow on the canvas (see [Debug Mode](../canvas/debug-mode.md)).

## Thread safety

`_nodes`, `_edges`, and `_node_state` are protected by `threading.Lock`. The lock is acquired for reads and writes. Flask runs with `async_mode='threading'`, so multiple hardware events can arrive concurrently; the lock ensures graph traversal is not interleaved with a project reload.
