"""text_input — mobile web UI for sending text to the engine.

Serves a mobile-friendly page on a configurable port (default 5200).
When the user submits text, a `text_received` event is fired into the engine.
"""
import json
import threading
from pathlib import Path

_DIR = Path(__file__).parent

# ── Config ────────────────────────────────────────────────────────────────────
def _cfg():
    try:
        return json.loads((_DIR / 'config.json').read_text())
    except Exception:
        return {}

MANIFEST = {
    'type':  'text_input',
    'label': 'Mobile Text Input',
}


def get_components():
    cfg = _cfg()
    port = cfg.get('port', 5200)
    return [{
        'type':          'text_input',
        'label':         'Mobile Text Input',
        'subtitle':      f'Mobile UI on port {port}',
        'category':      'input',
        'color':         '#06b6d4',
        'icon':          '📱',
        'display_param': 'name',
        'params': [
            {'key': 'name',       'label': 'Label',       'type': 'text',   'default': 'text input'},
            {'key': 'input_id',   'label': 'Input ID',    'type': 'text',   'default': '1',
             'description': 'Unique ID — allows multiple text inputs on different ports'},
        ],
        'inputs':  [],
        'outputs': [
            {
                'key':         'text_received',
                'label':       'Text Received',
                'description': 'Fires with the submitted text value',
            }
        ],
    }]


# ── Device ────────────────────────────────────────────────────────────────────
class Device:
    def __init__(self):
        self._callback = None
        self._last_text = {}
        cfg = _cfg()
        self._port = int(cfg.get('port', 5200))
        self._title = cfg.get('title', 'Send Text')
        self._placeholder = cfg.get('placeholder', 'Type something...')

        t = threading.Thread(target=self._serve, daemon=True, name='text-input-web')
        t.start()
        print(f'[text_input] mobile UI on http://0.0.0.0:{self._port}')

    # ── Web server ─────────────────────────────────────────────────────────────
    def _serve(self):
        from flask import Flask, request, jsonify, Response
        srv = Flask('text_input')
        srv.logger.disabled = True
        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        html = (_DIR / 'mobile.html').read_text(encoding='utf-8')

        @srv.route('/')
        def index():
            page = (html
                    .replace('{{TITLE}}', self._title)
                    .replace('{{PLACEHOLDER}}', self._placeholder))
            return Response(page, mimetype='text/html')

        @srv.route('/submit', methods=['POST'])
        def submit():
            data = request.get_json(silent=True) or {}
            text = str(data.get('text', '')).strip()
            input_id = str(data.get('input_id', '1'))
            if text:
                self._last_text[input_id] = text
                if self._callback:
                    self._callback('text_received', {'input_id': input_id, 'text': text})
            return jsonify({'ok': True})

        srv.run(host='0.0.0.0', port=self._port, debug=False, use_reloader=False)

    # ── Hardware service contract ──────────────────────────────────────────────
    def get_state(self):
        return {'last_text': self._last_text, 'port': self._port}

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate':
            text = str(kwargs.get('text', 'hello')).strip()
            input_id = str(kwargs.get('input_id', '1'))
            self._last_text[input_id] = text
            if self._callback:
                self._callback('text_received', {'input_id': input_id, 'text': text})
            return {'input_id': input_id, 'text': text}
        raise ValueError(f'Unknown command: {cmd}')

    def set_event_callback(self, fn):
        self._callback = fn
