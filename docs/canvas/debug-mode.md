# Debug Mode

Debug Mode is a real-time signal flow visualisation tool built into the scene editor. When enabled, it shows exactly which nodes and edges are activated as hardware events travel through the canvas graph, making it easy to verify that wiring is correct and diagnose unexpected behaviour.

## Enabling Debug Mode

Click the **bug icon** (🐛) in the scene editor header. The button toggles between active (highlighted) and inactive. The setting is saved in `localStorage` per browser, so it persists across page reloads.

!!! note "Performance"
    Debug Mode adds Socket.IO listener overhead in the browser. For a finished production game with no active development, you can turn it off to keep the browser client lighter. The engine always emits `node_pulse` and `edge_pulse` events regardless of whether the browser has Debug Mode on — the setting only controls whether the frontend renders them.

## Signal flow animation

When an event travels through the graph, the engine emits two types of Socket.IO events:

| Event | Payload | Visual effect |
|---|---|---|
| `node_pulse` | `{ node_id }` | The node card briefly glows with a coloured outline |
| `edge_pulse` | `{ edge_id }` | The edge animates with a travelling pulse along the wire |

The animation plays in real time — for a fast event chain (RFID card → RFID Auth → Relay → DFPlayer), all four pulses fire within milliseconds and play back almost simultaneously.

## Signal Log

Below the canvas, the Signal Log panel records every `node_pulse` and `edge_pulse` event received while Debug Mode is active. Each entry shows:

- Timestamp (ms since page load)
- Event type (`node_pulse` or `edge_pulse`)
- Target ID

The log holds up to 500 entries. Older entries are dropped when the buffer is full.

## Slow-motion replay

The Signal Log has a **Replay** button. Clicking it plays back the recorded events in slow motion. You can choose a speed multiplier:

- `1×` — real time (fast, good for confirming a long chain)
- `0.3×` — slow (good for seeing individual node activations)
- `0.1×` — very slow (good for step-by-step debugging)

During replay, the canvas animates as if the events were happening live. This is especially useful for debugging Combo Lock phase transitions, where the event chain includes counter updates, digit-lock signals, and optional DFPlayer and display updates — all within a fraction of a second.

## What to look for

**Signal stops before expected:** The edge leading to the stuck node is not being pulsed. Check that the output handle on the upstream node exactly matches the edge's `sourceHandle`. Open the upstream node's executor logic (or its `get_components()` output list) to verify the handle key.

**Signal fires but hardware does not respond:** The node pulse fires on the output node, but the relay/audio/servo does not activate. This means the executor ran but the hardware-service call failed. Check `journalctl -u hardware-service -f` for errors.

**Signal fires multiple times:** You have multiple edges leaving the same source handle, or multiple canvas nodes with the same `componentType` and matching params. The engine sends the event to all matching nodes.

**Combo Lock "wrong" transitions:** The Signal Log lets you see whether `digit_locked` fired before a direction reversal, whether `failed` or `unlocked` was the final output, and exactly how many `current_value` events were emitted for each phase — without needing to read the debug log file at `/tmp/combo_debug.log`.
