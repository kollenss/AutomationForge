import json
import os
import sys
import uuid
import urllib.request as _urllib_req
import urllib.error as _urllib_err
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from engine import GameEngine

sys.path.insert(0, '/home/pi/modules')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'projects')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
LIBRARY_PATH = os.path.join(BASE_DIR, 'component_library.json')

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

engine = GameEngine()
engine.set_emit(socketio.emit)


def _persist_scene_state(scene_id, active):
    """Persist scene active-flag to JSON and push socket event. Used as engine callback."""
    if not _active_project_id:
        return
    path = _project_path(_active_project_id)
    if not os.path.exists(path):
        return
    project = _read_json(path)
    scene = next((s for s in project['scenes'] if s['id'] == scene_id), None)
    if not scene:
        return
    scene['active'] = active
    _write_json(path, project)
    socketio.emit('scene_state', {'scene_id': scene_id, 'active': active})

HW_SERVICE = 'http://localhost:5101'

_active_project_id = None
_encoder_positions = {}  # device_type → accumulated position


def _hw_get(path):
    try:
        with _urllib_req.urlopen(f'{HW_SERVICE}{path}', timeout=2) as r:
            return json.loads(r.read()), r.status
    except _urllib_err.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as e:
        return {'error': str(e)}, 503


def _hw_post(path, data=None):
    body = json.dumps(data or {}).encode()
    req = _urllib_req.Request(
        f'{HW_SERVICE}{path}', data=body,
        headers={'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with _urllib_req.urlopen(req, timeout=2) as r:
            return json.loads(r.read()), r.status
    except _urllib_err.HTTPError as e:
        return json.loads(e.read()), e.code
    except Exception as e:
        return {'error': str(e)}, 503


def _read_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _write_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _project_path(project_id):
    return os.path.join(DATA_DIR, f'{project_id}.json')


def _now():
    return datetime.utcnow().isoformat() + 'Z'


def _reload_engine(project):
    n, e = engine.load_project(project)
    print(f'[engine] loaded "{project.get("name")}" — {n} nodes, {e} edges')


def _autoload_engine():
    global _active_project_id
    try:
        files = os.listdir(DATA_DIR)
    except Exception:
        return
    projects = [_read_json(os.path.join(DATA_DIR, f)) for f in files if f.endswith('.json')]
    projects = [p for p in projects if p]
    if not projects:
        return
    latest = max(projects, key=lambda p: p.get('updated_at', ''))
    _active_project_id = latest['id']
    _reload_engine(latest)


engine.set_activation_callback(_persist_scene_state)
_autoload_engine()


# ── Serve React app ────────────────────────────────────────────────────────

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if path.startswith('api/') or path.startswith('engine/'):
        return jsonify({'error': 'Not found'}), 404
    file_path = os.path.join(STATIC_DIR, path)
    if path and os.path.exists(file_path) and os.path.isfile(file_path):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, 'index.html')


# ── Component Library ──────────────────────────────────────────────────────

_CATEGORY_META = {
    'input':  {'label': 'Input',  'color': '#22c55e'},
    'output': {'label': 'Output', 'color': '#f59e0b'},
    'logic':  {'label': 'Logic',  'color': '#8b5cf6'},
}

@app.route('/api/components')
def api_components():
    static = _read_json(LIBRARY_PATH, {'categories': []})
    hw_data, _ = _hw_get('/components')
    hw_cats = hw_data.get('categories', []) if isinstance(hw_data, dict) else []

    result = list(hw_cats)
    existing_ids = {c['id'] for c in result}
    for cat in static.get('categories', []):
        if cat['id'] not in existing_ids:
            result.append(cat)
    return jsonify({'categories': result})


# ── Projects ───────────────────────────────────────────────────────────────

@app.route('/api/projects')
def api_list_projects():
    projects = []
    try:
        files = os.listdir(DATA_DIR)
    except Exception:
        files = []
    for fname in files:
        if not fname.endswith('.json'):
            continue
        p = _read_json(os.path.join(DATA_DIR, fname))
        if p:
            projects.append({
                'id': p['id'],
                'name': p['name'],
                'description': p.get('description', ''),
                'created_at': p.get('created_at', ''),
                'updated_at': p.get('updated_at', ''),
                'scene_count': len(p.get('scenes', []))
            })
    projects.sort(key=lambda p: p.get('updated_at', ''), reverse=True)
    return jsonify(projects)


@app.route('/api/projects', methods=['POST'])
def api_create_project():
    body = request.json or {}
    name = body.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    project = {
        'id': str(uuid.uuid4()),
        'name': name,
        'description': body.get('description', ''),
        'created_at': _now(),
        'updated_at': _now(),
        'scenes': []
    }
    _write_json(_project_path(project['id']), project)
    return jsonify(project), 201


@app.route('/api/projects/<project_id>')
def api_get_project(project_id):
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    return jsonify(_read_json(path))


@app.route('/api/projects/<project_id>', methods=['PUT'])
def api_update_project(project_id):
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    project = _read_json(path)
    body = request.json or {}
    for field in ('name', 'description'):
        if field in body:
            project[field] = body[field]
    project['updated_at'] = _now()
    _write_json(path, project)
    return jsonify(project)


@app.route('/api/projects/<project_id>', methods=['DELETE'])
def api_delete_project(project_id):
    path = _project_path(project_id)
    if os.path.exists(path):
        os.remove(path)
    return jsonify({'ok': True})


# ── Scenes ─────────────────────────────────────────────────────────────────

@app.route('/api/projects/<project_id>/scenes', methods=['POST'])
def api_create_scene(project_id):
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    project = _read_json(path)
    body = request.json or {}
    name = body.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    scene = {
        'id': str(uuid.uuid4()),
        'name': name,
        'nodes': [],
        'edges': []
    }
    project['scenes'].append(scene)
    project['updated_at'] = _now()
    _write_json(path, project)
    return jsonify(scene), 201


@app.route('/api/projects/<project_id>/scenes/<scene_id>', methods=['PUT'])
def api_update_scene(project_id, scene_id):
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    project = _read_json(path)
    body = request.json or {}
    scene = next((s for s in project['scenes'] if s['id'] == scene_id), None)
    if not scene:
        return jsonify({'error': 'Scene not found'}), 404
    for field in ('name', 'nodes', 'edges'):
        if field in body:
            scene[field] = body[field]
    project['updated_at'] = _now()
    _write_json(path, project)

    global _active_project_id
    if project_id == _active_project_id:
        _reload_engine(project)

    return jsonify(scene)


@app.route('/api/projects/<project_id>/scenes/<scene_id>', methods=['DELETE'])
def api_delete_scene(project_id, scene_id):
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Not found'}), 404
    project = _read_json(path)
    project['scenes'] = [s for s in project['scenes'] if s['id'] != scene_id]
    project['updated_at'] = _now()
    _write_json(path, project)
    return jsonify({'ok': True})


# ── Hardware ───────────────────────────────────────────────────────────────

@app.route('/api/hardware/relay')
def api_hw_relay_state():
    data, status = _hw_get('/hardware/relay_board/state')
    return jsonify(data), status


@app.route('/api/hardware/relay/<int:channel>/<action>', methods=['POST'])
def api_hw_relay_set(channel, action):
    if channel not in (1, 2, 3, 4) or action not in ('on', 'off'):
        return jsonify({'error': 'Invalid channel or action'}), 400
    data, status = _hw_post(f'/hardware/relay_board/{action}', {'channel': channel})
    if status == 200 and isinstance(data.get('state'), dict):
        socketio.emit('relay_state', data['state'])
    return jsonify(data), status


# ── Engine ─────────────────────────────────────────────────────────────────

@app.route('/engine/hardware_event', methods=['POST'])
def api_engine_hardware_event():
    body = request.json or {}
    device_type = body.get('device_type')
    event       = body.get('event')
    value       = body.get('value')
    if not device_type or not event:
        return jsonify({'error': 'device_type and event required'}), 400
    results = engine.process_hardware_event(device_type, event, value)
    if isinstance(value, dict):
        eid = value.get('encoder_id', 1)
        if event == 'delta':
            delta_val = value.get('delta', 0)
            key = f'{device_type}_{eid}'
            _encoder_positions[key] = _encoder_positions.get(key, 0) + delta_val
            socketio.emit('encoder_state', {
                'device_type': device_type,
                'encoder_id':  eid,
                'position':    _encoder_positions[key],
                'delta':       delta_val,
            })
        elif event == 'click':
            socketio.emit('encoder_state', {
                'device_type': device_type,
                'encoder_id':  eid,
                'click':       True,
            })
        elif device_type == 'rfid_reader' and event == 'card_read':
            socketio.emit('rfid_state', {
                'reader_id': value.get('reader_id', 1),
                'uid':       value.get('uid', ''),
            })
        elif device_type == 'text_input' and event == 'text_received':
            socketio.emit('text_input_state', {
                'input_id': value.get('input_id', '1'),
                'text':     value.get('text', ''),
            })
    return jsonify({'results': results})


@app.route('/engine/activate', methods=['POST'])
def api_engine_activate():
    global _active_project_id
    body = request.json or {}
    pid = body.get('project_id')
    if not pid:
        return jsonify({'error': 'project_id required'}), 400
    path = _project_path(pid)
    if not os.path.exists(path):
        return jsonify({'error': 'Project not found'}), 404
    _active_project_id = pid
    project = _read_json(path)
    _reload_engine(project)
    return jsonify({'ok': True, 'project_id': pid})


@app.route('/engine/activate_scene', methods=['POST'])
def api_engine_activate_scene():
    global _active_project_id
    body = request.json or {}
    scene_id   = body.get('scene_id')
    project_id = body.get('project_id') or _active_project_id
    if not scene_id or not project_id:
        return jsonify({'error': 'scene_id and project_id required'}), 400
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Project not found'}), 404
    project = _read_json(path)
    if not any(s['id'] == scene_id for s in project.get('scenes', [])):
        return jsonify({'error': 'Scene not found'}), 404
    _persist_scene_state(scene_id, True)
    engine.activate_scene(scene_id)
    return jsonify({'ok': True, 'scene_id': scene_id, 'active': True})


@app.route('/engine/deactivate_scene', methods=['POST'])
def api_engine_deactivate_scene():
    global _active_project_id
    body = request.json or {}
    scene_id   = body.get('scene_id')
    project_id = body.get('project_id') or _active_project_id
    if not scene_id or not project_id:
        return jsonify({'error': 'scene_id and project_id required'}), 400
    path = _project_path(project_id)
    if not os.path.exists(path):
        return jsonify({'error': 'Project not found'}), 404
    project = _read_json(path)
    if not any(s['id'] == scene_id for s in project.get('scenes', [])):
        return jsonify({'error': 'Scene not found'}), 404
    _persist_scene_state(scene_id, False)
    engine.deactivate_scene(scene_id)
    return jsonify({'ok': True, 'scene_id': scene_id, 'active': False})


@app.route('/engine/trigger', methods=['POST'])
def api_engine_trigger():
    body    = request.json or {}
    node_id = body.get('node_id')
    value   = body.get('value', True)
    handle  = body.get('handle')   # optional: inject into a specific input handle
    if not node_id:
        return jsonify({'error': 'node_id required'}), 400
    result = engine.trigger_node(node_id, value, handle=handle)
    if result is None:
        return jsonify({'error': 'Node not found or no executor'}), 404
    return jsonify({'result': result})


@app.route('/engine/event', methods=['POST'])
def api_engine_event():
    body = request.json or {}
    node_id = body.get('node_id')
    handle  = body.get('handle')
    value   = body.get('value')
    if not node_id or not handle:
        return jsonify({'error': 'node_id and handle required'}), 400
    results = engine.process_event(node_id, handle, value)
    return jsonify({'results': results})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
