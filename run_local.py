#!/usr/bin/env python3
"""Start AutomationForge locally — no Raspberry Pi required.

Launches two services in parallel:
  • Hardware service  http://localhost:5101  (modules/)
  • Management app    http://localhost:5000  (management/)

All Pi-specific hardware modules (relay, RFID, servo, encoder, …) fall back
to stub mode automatically, so the management UI works fully without hardware.

Usage:
    python run_local.py

Stop with Ctrl-C.
"""

import os
import signal
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
MODULES_DIR    = os.path.join(BASE, 'modules')
MANAGEMENT_DIR = os.path.join(BASE, 'management')

# Use the same Python interpreter that is running this script.
PYTHON = sys.executable

SERVICES = [
    {
        'name': 'hardware-service',
        'cmd':  [PYTHON, 'hardware_service.py'],
        'cwd':  MODULES_DIR,
    },
    {
        'name': 'management-app',
        'cmd':  [PYTHON, 'app.py'],
        'cwd':  MANAGEMENT_DIR,
    },
]


def _prefix_output(name, stream, colour_code):
    """Read *stream* line by line and print each line with a coloured prefix."""
    prefix = f'\x1b[{colour_code}m[{name}]\x1b[0m '
    try:
        for line in stream:
            sys.stdout.write(prefix + line)
            sys.stdout.flush()
    except Exception:
        pass


def main():
    procs = []
    threads = []

    try:
        import threading

        colours = ['36', '33']  # cyan for hw-service, yellow for management
        for i, svc in enumerate(SERVICES):
            env = os.environ.copy()
            # Make sure the modules directory is on PYTHONPATH so imports work.
            env['PYTHONPATH'] = MODULES_DIR + os.pathsep + env.get('PYTHONPATH', '')

            proc = subprocess.Popen(
                svc['cmd'],
                cwd=svc['cwd'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
            )
            procs.append(proc)

            t = threading.Thread(
                target=_prefix_output,
                args=(svc['name'], proc.stdout, colours[i % len(colours)]),
                daemon=True,
            )
            t.start()
            threads.append(t)

            print(f'Started {svc["name"]} (pid {proc.pid})')
            time.sleep(0.5)   # slight stagger so hw-service is up before app

        print('\n  Management UI -> http://localhost:5000')
        print('  Hardware API  -> http://localhost:5101')
        print('\nPress Ctrl-C to stop both services.\n')

        # Wait for either process to exit unexpectedly.
        while True:
            for proc, svc in zip(procs, SERVICES):
                rc = proc.poll()
                if rc is not None:
                    print(f'\n{svc["name"]} exited with code {rc}. Stopping.')
                    return
            time.sleep(1)

    except KeyboardInterrupt:
        print('\nShutting down…')
    finally:
        for proc in procs:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


if __name__ == '__main__':
    main()
