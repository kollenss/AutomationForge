#!/usr/bin/env python3
"""Unified hardware service — discovers and hosts all shared/ hardware modules."""
import importlib.util
import json
import sys
from pathlib import Path
from flask import Flask, jsonify, request

SHARED_DIR = Path(__file__).parent
sys.path.insert(0, str(SHARED_DIR))

app = Flask(__name__)
_devices = {}  # type -> {'manifest': dict, 'device': Device|None, 'error': str|None}


def _load_modules():
    for path in sorted(SHARED_DIR.glob('*.py')):
        if path.name.startswith('_') or path.name == 'hardware_service.py':
            continue
        # Fast pre-check: skip files that don't declare MANIFEST (avoids executing side-effectful scripts)
        try:
            source = path.read_text()
        except Exception:
            continue
        if 'MANIFEST' not in source or 'Device' not in source:
            continue
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            print(f'[HW] import error {path.name}: {e}')
            continue
        if not (hasattr(mod, 'MANIFEST') and hasattr(mod, 'Device')):
            continue
        manifest = mod.MANIFEST
        hw_type = manifest.get('type')
        if not hw_type:
            continue
        try:
            device = mod.Device()
            _devices[hw_type] = {'manifest': manifest, 'device': device, 'error': None}
            print(f'[HW] loaded: {hw_type}')
        except Exception as e:
            _devices[hw_type] = {'manifest': manifest, 'device': None, 'error': str(e)}
            print(f'[HW] {hw_type} unavailable: {e}')


_load_modules()


@app.route('/hardware')
def hw_list():
    result = []
    for hw_type, info in _devices.items():
        entry = dict(info['manifest'])
        entry['connected'] = info['device'] is not None
        if info['error']:
            entry['error'] = info['error']
        result.append(entry)
    return jsonify(result)


@app.route('/hardware/<hw_type>/state')
def hw_state(hw_type):
    info = _devices.get(hw_type)
    if not info:
        return jsonify({'error': 'Unknown device'}), 404
    if not info['device']:
        return jsonify({'error': info.get('error') or 'Not connected'}), 503
    try:
        return jsonify(info['device'].get_state())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/hardware/<hw_type>/<cmd>', methods=['POST'])
def hw_execute(hw_type, cmd):
    info = _devices.get(hw_type)
    if not info:
        return jsonify({'error': 'Unknown device'}), 404
    if not info['device']:
        return jsonify({'error': info.get('error') or 'Not connected'}), 503
    try:
        kwargs = request.get_json(silent=True) or {}
        result = info['device'].execute(cmd, **kwargs)
        return jsonify({'ok': True, 'state': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5101, debug=False)
