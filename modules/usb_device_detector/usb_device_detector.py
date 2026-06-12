import json
import subprocess
import threading
import time

YUBIKEY_VENDOR_ID = '1050'

MANIFEST = {
    'type': 'usb_device_detector',
    'label': 'USB Device Detector',
}

_POLL_INTERVAL = 2.0  # seconds — lsusb/lsblk are expensive on Pi 3B (~50-100ms each)


def get_components():
    return [{
        'type': 'usb_device_detector',
        'label': 'USB Device Detector',
        'subtitle': 'YubiKey · USB Memory',
        'category': 'input',
        'color': '#06b6d4',
        'icon': '🔌',
        'display_param': None,
        'params': [],
        'inputs': [],
        'outputs': [
            {
                'key': 'yubikey_inserted',
                'label': 'YubiKey Inserted',
                'description': 'Fires once when a YubiKey is connected to any USB port',
            },
            {
                'key': 'yubikey_removed',
                'label': 'YubiKey Removed',
                'description': 'Fires once when the YubiKey is disconnected',
            },
            {
                'key': 'usb_memory_inserted',
                'label': 'USB Memory Inserted',
                'description': 'Fires once when a USB mass storage device is mounted. '
                               'Value includes mount_point.',
            },
            {
                'key': 'usb_memory_removed',
                'label': 'USB Memory Removed',
                'description': 'Fires once when a USB mass storage device is unmounted.',
            },
        ],
    }]


# ── Detection helpers ──────────────────────────────────────────────────────────

def _yubikey_present():
    """Return True if a YubiKey (vendor 1050) is listed by lsusb."""
    try:
        r = subprocess.run(['lsusb'], capture_output=True, text=True, timeout=2)
        return any(f'{YUBIKEY_VENDOR_ID}:' in line for line in r.stdout.splitlines())
    except Exception:
        return False


def _usb_memory_mounts():
    """Return a set of mount points for currently mounted USB mass-storage devices."""
    try:
        r = subprocess.run(
            ['lsblk', '--json', '-o', 'NAME,TRAN,MOUNTPOINT'],
            capture_output=True, text=True, timeout=2,
        )
        data = json.loads(r.stdout)
        mounts = set()
        for dev in data.get('blockdevices', []):
            if dev.get('tran') != 'usb':
                continue
            mp = dev.get('mountpoint')
            if mp:
                mounts.add(mp)
            for child in dev.get('children') or []:
                cmp = child.get('mountpoint')
                if cmp:
                    mounts.add(cmp)
        return mounts
    except Exception:
        return set()


# ── Device ────────────────────────────────────────────────────────────────────

class Device:
    def __init__(self):
        self._callback = None

        self._yubikey_present = False
        self._memory_mounts: set = set()

        self._stop = threading.Event()
        t = threading.Thread(target=self._poll_loop, daemon=True, name='usb-detector-poll')
        t.start()
        print('[usb_device_detector] started — polling for YubiKey + USB memory')

    def _poll_loop(self):
        while not self._stop.is_set():
            self._check_yubikey()
            self._check_memory()
            time.sleep(_POLL_INTERVAL)

    # ── YubiKey ────────────────────────────────────────────────────────────────

    def _check_yubikey(self):
        now = _yubikey_present()
        if now and not self._yubikey_present:
            self._yubikey_present = True
            print('[usb_device_detector] YubiKey inserted')
            self._fire('yubikey_inserted', {'vendor_id': YUBIKEY_VENDOR_ID})
        elif not now and self._yubikey_present:
            self._yubikey_present = False
            print('[usb_device_detector] YubiKey removed')
            self._fire('yubikey_removed', {'vendor_id': YUBIKEY_VENDOR_ID})

    # ── USB Memory ─────────────────────────────────────────────────────────────

    def _check_memory(self):
        now = _usb_memory_mounts()
        inserted = now - self._memory_mounts
        removed  = self._memory_mounts - now
        self._memory_mounts = now

        for mp in inserted:
            print(f'[usb_device_detector] USB memory inserted → {mp}')
            self._fire('usb_memory_inserted', {'mount_point': mp})

        for mp in removed:
            print(f'[usb_device_detector] USB memory removed ← {mp}')
            self._fire('usb_memory_removed', {'mount_point': mp})

    # ── Internal ───────────────────────────────────────────────────────────────

    def _fire(self, event, value):
        if self._callback:
            self._callback(event, value)

    # ── Hardware service contract ──────────────────────────────────────────────

    def get_state(self):
        return {
            'yubikey_present': self._yubikey_present,
            'memory_mounts': list(self._memory_mounts),
        }

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate_yubikey_insert':
            if not self._yubikey_present:
                self._yubikey_present = True
                self._fire('yubikey_inserted', {'vendor_id': YUBIKEY_VENDOR_ID, 'simulated': True})
            return self.get_state()

        if cmd == 'simulate_yubikey_remove':
            if self._yubikey_present:
                self._yubikey_present = False
                self._fire('yubikey_removed', {'vendor_id': YUBIKEY_VENDOR_ID, 'simulated': True})
            return self.get_state()

        if cmd == 'simulate_memory_insert':
            mp = kwargs.get('mount_point', '/media/pi/USB')
            self._memory_mounts.add(mp)
            self._fire('usb_memory_inserted', {'mount_point': mp, 'simulated': True})
            return self.get_state()

        if cmd == 'simulate_memory_remove':
            mp = kwargs.get('mount_point', '/media/pi/USB')
            self._memory_mounts.discard(mp)
            self._fire('usb_memory_removed', {'mount_point': mp, 'simulated': True})
            return self.get_state()

        raise ValueError(f'Unknown command: {cmd}')

    def set_event_callback(self, fn):
        self._callback = fn
