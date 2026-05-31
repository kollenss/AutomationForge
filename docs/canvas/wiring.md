# Wiring

Wiring is the act of connecting an output handle on one component to an input handle on another. A wire (called an *edge* in the underlying data) tells the engine: "when this output fires, deliver its value to that input."

## Drawing a connection

1. Hover over the source component until its output handles (right edge) become visible.
2. Click and drag from an output handle. A line follows your cursor.
3. Hover over the target component's input handle (left edge) until it highlights.
4. Release. The edge snaps into place.

The canvas only allows output → input connections. You cannot connect two outputs together or two inputs together, and you cannot connect a handle to itself.

## Multiple connections from one output

An output handle can connect to multiple input handles. When the output fires, the value is delivered to all connected inputs simultaneously. This is useful for triggering several things at once — for example, activating a relay and playing an audio track at the same moment.

## Multiple connections to one input

An input handle can receive connections from multiple output handles. Any incoming signal on any of those edges will trigger the input. There is no merging or sequencing — the first signal to arrive wins each time.

## What happens at runtime

When the engine traverses a graph, it:

1. Receives a signal on a source node's output handle.
2. Looks up all edges in the scene that have `source == node_id` and `sourceHandle == output_handle`.
3. For each matching edge, emits `edge_pulse` (for Debug Mode animation) and `node_pulse` on the target node.
4. Calls the target node's executor with `handle = targetHandle` and `value = signal_value`.
5. The executor may call `propagate(output_handle, value)`, which recursively repeats from step 2 for the target node.

This is a depth-first walk with no cycle detection. Avoid creating cycles (A → B → A) — they will cause infinite recursion.

## Deleting an edge

Click on any edge to select it, then press `Delete` or `Backspace`. Alternatively, right-click an edge for a context menu.

## Saving

Edges are saved as part of the project JSON when you click **Save**. The engine reloads the graph immediately; new edges are active for the next hardware event.

## Handle descriptions

Hover over any handle to see its description tooltip. Descriptions explain what value the handle carries and when it fires. For example:

- The RFID Reader's `card_read` output says: *"Fires with the card UID string each time a new card is scanned"*
- The Relay Channel's `trigger_on` input says: *"Activates the relay channel, connecting the circuit"*

Reading these tooltips is the fastest way to understand how two components should be wired together.

!!! warning "Handle name matching"
    The edge stores `sourceHandle` and `targetHandle` as string keys (e.g. `"card_read"`, `"trigger_on"`). These must match exactly what the module or component library defines. Handles defined in `get_components()` or `component_library.json` are always correct — issues arise only if you manually edit the project JSON file.
