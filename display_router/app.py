#!/usr/bin/env python3
"""Display Router — lets GameForge point the kiosk screen at any URL.

Serves one stable page (a full-viewport iframe) that the kiosk browser
loads once and never navigates away from. POST /show swaps what's
inside the iframe live via Server-Sent Events, so switching what the
physical screen shows never causes a top-level page reload/flicker.
"""
import json
import queue
import threading

from flask import Flask, Response, jsonify, request

app = Flask(__name__)

_lock = threading.Lock()
_current_url = 'about:blank'
_subscribers = []  # one queue.Queue per connected SSE client (the kiosk page)

_PAGE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>GameForge Display</title>
<style>
  html, body {{ margin: 0; padding: 0; background: #000; overflow: hidden; height: 100%; }}
  iframe {{ border: 0; width: 100vw; height: 100vh; display: block; }}
</style>
</head>
<body>
<iframe id="f" src="{initial_url}"></iframe>
<script>
  const f = document.getElementById('f');
  const es = new EventSource('/events');
  es.addEventListener('show', (e) => {{
    f.src = JSON.parse(e.data).url;
  }});
</script>
</body>
</html>"""


@app.route('/')
def index():
    with _lock:
        url = _current_url
    return _PAGE.format(initial_url=url)


@app.route('/events')
def events():
    q = queue.Queue()
    with _lock:
        _subscribers.append(q)

    def stream():
        try:
            while True:
                data = q.get()
                yield f'event: show\ndata: {json.dumps(data)}\n\n'
        finally:
            with _lock:
                if q in _subscribers:
                    _subscribers.remove(q)

    return Response(stream(), mimetype='text/event-stream')


@app.route('/show', methods=['POST'])
def show():
    global _current_url
    body = request.get_json(force=True) or {}
    url = str(body.get('url', '')).strip()
    if not url:
        return jsonify({'error': 'url is required'}), 400
    with _lock:
        _current_url = url
        subs = list(_subscribers)
    for q in subs:
        q.put({'url': url})
    return jsonify({'ok': True, 'url': url})


@app.route('/api/status')
def status():
    with _lock:
        return jsonify({'current_url': _current_url, 'subscribers': len(_subscribers)})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, threaded=True)
