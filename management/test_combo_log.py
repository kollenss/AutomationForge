#!/usr/bin/env python3
"""
Standalone test for combo_lock logging in engine.py.
Simulates a full 4-digit combination without a running server.

Run on the Pi:
    python3 /home/pi/management/test_combo_log.py
Then inspect:
    cat /tmp/combo_debug.log
"""

import time
import sys
sys.path.insert(0, '/home/pi/management')

from engine import _exec_combo_lock, _log_q

# ── Helpers ────────────────────────────────────────────────────────────────

_state_store = {}

def make_helpers(node_id):
    def emit(event, payload):
        print(f"  [socket] {event}: {payload}")
    def propagate(handle, value):
        print(f"  [output] {handle} = {value}")
    def get_state(defaults=None):
        if node_id not in _state_store:
            _state_store[node_id] = dict(defaults or {})
        return _state_store[node_id]
    return emit, propagate, get_state


def step(node_id, params, delta, emit, propagate, get_state, label=''):
    tag = f'  delta={delta:+d}  {label}'
    print(tag)
    _exec_combo_lock(node_id, params, 'delta', delta, emit, propagate, get_state)
    time.sleep(0.02)   # give log_worker time to flush


# ── Test ───────────────────────────────────────────────────────────────────

NODE   = 'test-node-0001'
# code: phase 0 → left to 5, phase 1 → right to 10, phase 2 → left to 3, phase 3 → right to 8
PARAMS = {'code': '5,10,3,8', 'name': 'test'}
emit, propagate, get_state = make_helpers(NODE)

print('=== Enable ===')
_exec_combo_lock(NODE, PARAMS, 'enable', True, emit, propagate, get_state)
time.sleep(0.02)

print('\n=== Phase 0: turn LEFT to 5 (delta=-1) ===')
for i in range(1, 6):
    step(NODE, PARAMS, -1, emit, propagate, get_state, f'count→{i}')

print('\n=== Lock phase 0: reverse RIGHT (2 steps to detect + 1 commit) ===')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 1')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 2 → DETECTED')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'commit → LOCK phase 0')

print('\n=== Phase 1: turn RIGHT to 10 (delta=+1) ===')
for i in range(1, 11):
    step(NODE, PARAMS, +1, emit, propagate, get_state, f'count→{i}')

print('\n=== Lock phase 1: reverse LEFT ===')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'pending 1')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'pending 2 → DETECTED')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'commit → LOCK phase 1')

print('\n=== Phase 2: turn LEFT to 3 (delta=-1) ===')
for i in range(1, 4):
    step(NODE, PARAMS, -1, emit, propagate, get_state, f'count→{i}')

print('\n=== Lock phase 2: reverse RIGHT ===')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 1')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 2 → DETECTED')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'commit → LOCK phase 2')

print('\n=== Phase 3: turn RIGHT to 8 (delta=+1) ===')
for i in range(1, 9):
    step(NODE, PARAMS, +1, emit, propagate, get_state, f'count→{i}')

print('\n=== Lock phase 3 (UNLOCK): reverse LEFT ===')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'pending 1')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'pending 2 → DETECTED')
step(NODE, PARAMS, -1, emit, propagate, get_state, 'commit → UNLOCK')

# Wait for log_worker to drain
_log_q.join()
time.sleep(0.1)

print(f'\nLog written to /tmp/combo_debug.log')
print('Run:  cat /tmp/combo_debug.log')

# ── Bonus: test FAIL and DEBOUNCE ──────────────────────────────────────────

print('\n=== Reset + test FAIL (reverse before target) ===')
_state_store.clear()
_exec_combo_lock(NODE, PARAMS, 'enable', True, emit, propagate, get_state)
time.sleep(0.02)

for i in range(1, 3):   # only 2 left-steps, target is 5
    step(NODE, PARAMS, -1, emit, propagate, get_state, f'count→{i}')

step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 1')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'pending 2 → DETECTED')
step(NODE, PARAMS, +1, emit, propagate, get_state, 'commit → FAIL (was at count=2, target=5)')

_log_q.join()
time.sleep(0.1)
print('Done. Check /tmp/combo_debug.log for all events.')
