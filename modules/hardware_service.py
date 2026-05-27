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
_devices = {}  # type -> {'manifest', 'device', 'error', 'mod'}

CATEGORY_META = {
    'input':  {'label': 'Input',  'color': '#22c55e'},
    'output': {'label': 'Output', 'color': '#f59e0b'},
    'logic':  {'label': 'Logic',  'color': '#8b5cf6'},
}


def _load_modules():
    for path in sorted(SHARED_DIR.glob('*.py')):
        if path.name.startswith('_') or path.name == 'hardware_service.py':
            continue
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
            _devices[hw_type] = {'manifest': manifest, 'device': device, 'error': None, 'mod': mod}
            print(f'[HW] loaded: {hw_type}')
        except Exception as e:
            _devices[hw_type] = {'manifest': manifest, 'device': None, 'error': str(e), 'mod': mod}
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


@app.route('/components')
def hw_components():
    by_cat = {}
    for hw_type, info in _devices.items():
        mod = info.get('mod')
        if not (mod and hasattr(mod, 'get_components')):
            continue
        connected = info['device'] is not None
        for comp in mod.get_components():
            cat = comp.get('category', 'output')
            if cat not in by_cat:
                by_cat[cat] = []
            entry = {k: v for k, v in comp.items() if k != 'category'}
            entry['connected'] = connected
            by_cat[cat].append(entry)

    categories = []
    for cat_id, comps in by_cat.items():
        meta = CATEGORY_META.get(cat_id, {'label': cat_id.title(), 'color': '#6b7280'})
        categories.append({'id': cat_id, 'label': meta['label'],
                           'color': meta['color'], 'components': comps})
    return jsonify({'categories': categories})


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
