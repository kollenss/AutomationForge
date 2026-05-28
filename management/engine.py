import json
import threading
import urllib.request as _req

HW_SERVICE = 'http://localhost:5101'


def _hw_post(path, data=None):
    body = json.dumps(data or {}).encode()
    req = _req.Request(
        f'{HW_SERVICE}{path}', data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with _req.urlopen(req, timeout=2) as r:
            return json.loads(r.read())
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Executors — one per output component type.
# Signature: (params, handle, value, emit) → None
# Call emit('event_name', payload) to push state to frontend.

def _exec_relay(params, handle, value, emit):
    channel = int(params.get('channel', 1))
    if handle == 'trigger_on':
        action = 'on'
    elif handle == 'trigger_off':
        action = 'off'
    else:
        action = 'on' if value else 'off'
    resp = _hw_post(f'/hardware/relay_board/{action}', {'channel': channel})
    if emit and isinstance(resp.get('state'), dict):
        emit('relay_state', resp['state'])


_EXECUTORS = {
    'relay_channel': _exec_relay,
}


# ---------------------------------------------------------------------------

class GameEngine:
    def __init__(self):
        self._lock = threading.Lock()
        self._nodes = {}   # node_id → node dict
        self._edges = []
        self._emit = None  # set to socketio.emit by app.py

    def set_emit(self, fn):
        self._emit = fn

    def load_project(self, project):
        nodes, edges = {}, []
        for scene in project.get('scenes', []):
            for node in scene.get('nodes', []):
                nodes[node['id']] = node
            edges.extend(scene.get('edges', []))
        with self._lock:
            self._nodes = nodes
            self._edges = list(edges)
        return len(nodes), len(edges)

    def trigger_node(self, node_id, value):
        with self._lock:
            node = self._nodes.get(node_id)
        if not node:
            return None
        comp_type = node['data']['componentType']
        executor = _EXECUTORS.get(comp_type)
        if not executor:
            return None
        params = node['data'].get('params', {})
        executor(params, None, value, self._emit)
        return {'node_id': node_id, 'type': comp_type}

    def process_hardware_event(self, device_type, event, value):
        """Find matching canvas nodes and fire their outputs.

        value may be a plain scalar or a dict (e.g. {'encoder_id': 1, 'delta': 1}).
        For dict values, nodes are filtered on matching params where keys overlap.
        """
        h = event.lower()
        with self._lock:
            source_nodes = [
                node for node in self._nodes.values()
                if node['data']['componentType'] == device_type
                and self._params_match(node['data'].get('params', {}), value)
            ]
        results = []
        scalar = value.get('delta', value) if isinstance(value, dict) else value
        for node in source_nodes:
            results.extend(self.process_event(node['id'], h, scalar))
        return results

    @staticmethod
    def _params_match(params, value):
        """Return True if value is not a dict, or if all dict keys that exist
        as node params have matching values."""
        if not isinstance(value, dict):
            return True
        for k, v in value.items():
            if k in params and params[k] != v:
                return False
        return True

    def process_event(self, node_id, handle, value):
        h = handle.lower()
        with self._lock:
            targets = [
                (self._nodes.get(e['target']), e.get('targetHandle'))
                for e in self._edges
                if e.get('source') == node_id and (e.get('sourceHandle') or '').lower() == h
            ]

        results = []
        for node, target_handle in targets:
            if not node:
                continue
            comp_type = node['data']['componentType']
            executor = _EXECUTORS.get(comp_type)
            if not executor:
                continue
            params = node['data'].get('params', {})
            executor(params, target_handle, value, self._emit)
            results.append({'node_id': node['id'], 'type': comp_type})

        return results
