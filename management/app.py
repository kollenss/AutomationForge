import copy
import json
import os
import subprocess
import sys
import time
import uuid
import urllib.request as _urllib_req
import urllib.error as _urllib_err
from datetime import datetime
from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO
from engine import GameEngine

# Add the modules directory to sys.path for local development (no-op on Pi
# where the service already runs from that directory).
_MODULES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'modules')
if _MODULES_DIR not in sys.path:
    sys.path.insert(0, _MODULES_DIR)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data', 'projects')
STATIC_DIR = os.path.join(BASE_DIR, 'static')
LIBRARY_PATH = os.path.join(BASE_DIR, 'component_library.json')
SETTINGS_PATH = os.path.join(BASE_DIR, 'data', 'settings.json')  # per-instance config (gitignored)

os.makedirs(DATA_DIR, exist_ok=True)

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

engine = GameEngine()
engine.set_emit(socketio.emit)


def _persist_scene_state(scene_id, active, project_id=None):
    """Persist scene active-flag to JSON and push socket event. Used as engine callback."""
    pid = project_id or _active_project_id
    if not pid:
        return
    path = _project_path(pid)
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
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}


def _write_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def _project_path(project_id):
    return os.path.join(DATA_DIR, f'{project_id}.json')


def _read_settings():
    return _read_json(SETTINGS_PATH, {})


def _write_settings(settings):
    _write_json(SETTINGS_PATH, settings)


def _now():
    return datetime.utcnow().isoformat() + 'Z'


def _reload_engine(project):
    n, e = engine.load_project(project)
    print(f'[engine] loaded "{project.get("name")}" — {n} nodes, {e} edges')


def _autoload_engine():
    """On startup, load the configured autostart project and activate its chosen
    scene (firing on_scene_start, just like the Activate button). If no autostart
    is configured, fall back to the most-recently-updated project with its saved
    scene states. Configure via PUT /api/settings/autostart."""
    global _active_project_id

    auto = _read_settings().get('autostart') or {}
    pid, sid = auto.get('project_id'), auto.get('scene_id')

    project = None
    if pid:
        p = _read_json(_project_path(pid))
        if p and 'id' in p and 'name' in p:
            project = p
            if sid and not any(s.get('id') == sid for s in project.get('scenes', [])):
                sid = None                       # configured scene was deleted

    if project is not None:
        # Exactly the chosen scene starts active; persist so the UI matches.
        for scene in project.get('scenes', []):
            scene['active'] = (scene.get('id') == sid)
        _write_json(_project_path(project['id']), project)
        _active_project_id = project['id']
        _reload_engine(project)
        if sid:
            engine.activate_scene(sid)           # fire on_scene_start like the Activate button
            print(f'[autostart] "{project.get("name")}" → scene {sid} activated')
        return

    # Fallback: no autostart configured — load latest project, keep saved states.
    try:
        files = os.listdir(DATA_DIR)
    except Exception:
        files = []
    projects = [_read_json(os.path.join(DATA_DIR, f)) for f in files
                if f.endswith('.json') and not f.endswith('_unlock.json')]
    projects = [p for p in projects if p and 'id' in p and 'name' in p]
    if not projects:
        return
    latest = max(projects, key=lambda p: p.get('updated_at', ''))
    for scene in latest.get('scenes', []):
        scene.setdefault('active', True)
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
        if p and 'id' in p and 'name' in p:
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


def _strip_runtime(project):
    """Return a copy of a project with transient runtime state removed, so
    exports/imports carry only the design, not the live scene state."""
    p = copy.deepcopy(project)
    for scene in p.get('scenes', []):
        scene.pop('active', None)
    return p


def _all_projects():
    """Read every saved project definition (skips the *_unlock.json runtime files)."""
    out = []
    try:
        files = os.listdir(DATA_DIR)
    except Exception:
        files = []
    for fname in files:
        if not fname.endswith('.json') or fname.endswith('_unlock.json'):
            continue
        p = _read_json(os.path.join(DATA_DIR, fname))
        if p and 'id' in p and 'name' in p:
            out.append(p)
    return out


@app.route('/api/projects/export')
def api_export_projects():
    """Download all projects as a single JSON bundle (runtime state stripped).

    Lets you move work between machines or seed a fresh Pi: export here, then
    Import on the other instance.
    """
    bundle = {
        'version': 1,
        'exported_at': _now(),
        'projects': [_strip_runtime(p) for p in _all_projects()],
    }
    payload = json.dumps(bundle, indent=2, ensure_ascii=False)
    filename = f'gameforge-projects-{_now()[:10]}.json'
    return app.response_class(
        payload,
        mimetype='application/json',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@app.route('/api/projects/import', methods=['POST'])
def api_import_projects():
    """Restore projects from an exported bundle (or a single project object).

    Body: { "projects": [...], "mode": "skip" | "overwrite" | "duplicate" }
      skip       — keep existing projects with the same id, add only new ones (default)
      overwrite  — replace existing projects with the imported version
      duplicate  — import everything under fresh ids (never touches existing work)
    """
    body = request.json or {}
    incoming = body.get('projects')
    if incoming is None and isinstance(body.get('id'), str):
        incoming = [body]                      # accept a single bare project too
    if not isinstance(incoming, list):
        return jsonify({'error': 'Invalid bundle — expected {"projects": [...]}'}), 400

    mode = (body.get('mode') or 'skip').lower()
    if mode not in ('skip', 'overwrite', 'duplicate'):
        return jsonify({'error': f'Unknown mode "{mode}"'}), 400

    existing = {p['id'] for p in _all_projects()}
    added = overwritten = skipped = duplicated = 0

    for proj in incoming:
        if not (isinstance(proj, dict) and 'id' in proj and 'name' in proj):
            continue
        proj = _strip_runtime(proj)
        pid = proj['id']
        conflict = pid in existing

        if conflict and mode == 'skip':
            skipped += 1
            continue
        if conflict and mode == 'duplicate':
            pid = proj['id'] = str(uuid.uuid4())
            proj['name'] = f'{proj["name"]} (imported)'
            proj['created_at'] = _now()
            duplicated += 1
        elif conflict:                         # mode == 'overwrite'
            overwritten += 1
        else:
            added += 1

        proj.setdefault('created_at', _now())
        proj['updated_at'] = _now()
        _write_json(_project_path(pid), proj)
        existing.add(pid)

    return jsonify({
        'total': len(incoming),
        'added': added,
        'overwritten': overwritten,
        'skipped': skipped,
        'duplicated': duplicated,
    })


# ── Settings ─────────────────────────────────────────────────────────────────

@app.route('/api/settings/autostart')
def api_get_autostart():
    """Which project+scene activates automatically when GameForge starts."""
    auto = _read_settings().get('autostart') or {}
    return jsonify({'project_id': auto.get('project_id'), 'scene_id': auto.get('scene_id')})


@app.route('/api/settings/autostart', methods=['PUT'])
def api_set_autostart():
    """Set (or clear) the startup project+scene. Send {project_id: null} to clear."""
    body = request.json or {}
    pid = body.get('project_id')
    sid = body.get('scene_id')
    settings = _read_settings()
    if not pid:
        settings['autostart'] = None
    else:
        if not os.path.exists(_project_path(pid)):
            return jsonify({'error': 'Project not found'}), 404
        project = _read_json(_project_path(pid))
        if sid and not any(s.get('id') == sid for s in project.get('scenes', [])):
            return jsonify({'error': 'Scene not found in project'}), 404
        settings['autostart'] = {'project_id': pid, 'scene_id': sid}
    _write_settings(settings)
    auto = settings.get('autostart') or {}
    return jsonify({'project_id': auto.get('project_id'), 'scene_id': auto.get('scene_id')})


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


@app.route('/api/hardware/text_input')
def api_hw_text_input_state():
    data, status = _hw_get('/hardware/text_input/state')
    return jsonify(data), status


@app.route('/api/hardware/ws2812b/<cmd>', methods=['POST'])
def api_hw_ws2812b(cmd):
    allowed = ('set_color', 'blink', 'pulse', 'chase', 'rainbow', 'off')
    if cmd not in allowed:
        return jsonify({'error': 'Invalid command'}), 400
    body = request.get_json(force=True) or {}
    data, status = _hw_post(f'/hardware/ws2812b/{cmd}', body)
    return jsonify(data), status

@app.route('/api/hardware/servo/<cmd>', methods=['POST'])
def api_hw_servo(cmd):
    if cmd not in ('set_angle', 'release'):
        return jsonify({'error': 'Invalid command'}), 400
    body = request.get_json(force=True) or {}
    data, status = _hw_post(f'/hardware/servo/{cmd}', body)
    return jsonify(data), status

@app.route('/api/hardware/relay/<int:channel>/<action>', methods=['POST'])
def api_hw_relay_set(channel, action):
    if channel not in (1, 2, 3, 4) or action not in ('on', 'off'):
        return jsonify({'error': 'Invalid channel or action'}), 400
    data, status = _hw_post(f'/hardware/relay_board/{action}', {'channel': channel})
    if status == 200 and isinstance(data.get('state'), dict):
        socketio.emit('relay_state', data['state'])
    return jsonify(data), status


@app.route('/api/hardware/restart', methods=['POST'])
def api_hw_restart():
    """Restart the hardware service so it re-probes newly wired hardware.
    Hardware modules only initialise devices at startup — there is no hot
    re-probe — so a restart is the supported way to pick up new wiring."""
    try:
        subprocess.run(
            ['sudo', 'systemctl', 'restart', 'hardware-service'],
            check=True, capture_output=True, timeout=30,
        )
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or b'').decode(errors='replace').strip() or 'systemctl restart failed'
        return jsonify({'error': msg}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # The service serves /hardware only after _load_modules() has finished
    # initialising every device, so a successful GET is our readiness signal.
    deadline = time.time() + 12
    hw = None
    while time.time() < deadline:
        data, status = _hw_get('/hardware')
        if status == 200 and isinstance(data, list):
            hw = data
            break
        time.sleep(0.5)

    if hw is None:
        return jsonify({'ok': True, 'connected': [],
                        'warning': 'service restarted but not responding yet'}), 200

    connected = [{
        'type':      d.get('type'),
        'label':     d.get('label'),
        'connected': d.get('connected', False),
    } for d in hw]
    return jsonify({'ok': True, 'connected': connected}), 200


@app.route('/api/hardware/status')
def api_hw_status():
    """Lightweight health check for the hardware service — used by the UI to
    show whether it is up. Returns up + count of connected devices."""
    data, status = _hw_get('/hardware')
    up = status == 200 and isinstance(data, list)
    connected = sum(1 for d in data if d.get('connected')) if up else 0
    return jsonify({'up': up, 'connected': connected})


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
    # Ensure this project is loaded in the engine (covers the case where the
    # server restarted after the project was created, or a different project
    # was active before).
    if project_id != _active_project_id:
        _active_project_id = project_id
        _reload_engine(project)
    _persist_scene_state(scene_id, True, project_id=project_id)
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
    if project_id != _active_project_id:
        _active_project_id = project_id
        _reload_engine(project)
    _persist_scene_state(scene_id, False, project_id=project_id)
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
