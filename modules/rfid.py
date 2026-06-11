import threading
import time

READERS = [
    {'id': 1, 'ce': 0, 'rst': 25},
]

MANIFEST = {
    'type': 'rfid_reader',
    'label': 'RFID Reader RC522',
    'readers': len(READERS),
}

_POLL_INTERVAL = 0.1   # seconds between SPI polls


def get_components():
    return [{
        'type': 'rfid_reader',
        'label': 'RFID Reader',
        'subtitle': MANIFEST['label'],
        'category': 'input',
        'color': '#22c55e',
        'icon': '📡',
        'display_param': 'reader_id',
        'params': [
            {
                'key': 'reader_id',
                'label': 'Reader',
                'type': 'select',
                'default': READERS[0]['id'],
                'options': [{'value': r['id'], 'label': f'Reader {r["id"]}'} for r in READERS],
            },
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'card reader'},
        ],
        'inputs':  [],
        'outputs': [
            {
                'key': 'card_read',
                'label': 'Card UID',
                'description': 'Fires with the card UID string each time a new card is scanned',
            }
        ],
    }]


class Device:
    def __init__(self):
        self._callback = None
        self._last = {}   # reader_id → last detected uid string
        self._stop = threading.Event()
        self._reader = None

        try:
            import mfrc522, spidev
            self._reader = mfrc522.SimpleMFRC522()
            # mfrc522 library does not enable the antenna on init — do it manually
            _spi = spidev.SpiDev()
            _spi.open(0, 0)
            _spi.max_speed_hz = 1000000
            _txctrl = _spi.xfer2([0x6E | 0x80, 0x00])[1]  # read TxControlReg (0x14)
            _spi.xfer2([0x28, _txctrl | 0x03])              # write TxControlReg with TX1/TX2 on
            _spi.close()
            t = threading.Thread(target=self._poll_loop, daemon=True, name='rfid-poll')
            t.start()
            print('[rfid] RC522 started — CE0 (GPIO8), RST=GPIO25, antenna ON')
        except Exception as e:
            print(f'[rfid] hardware init failed ({e}) — stub mode active')

    # ------------------------------------------------------------------
    # Polling loop — runs in background thread
    # ------------------------------------------------------------------

    def _poll_loop(self):
        prev_uid = None   # tracks card presence: non-None = card is held against reader

        while not self._stop.is_set():
            try:
                uid_int = self._reader.read_id_no_block()

                if uid_int is not None:
                    # Format as 8-char uppercase hex, dropping the checksum byte
                    uid_str = format(uid_int >> 8, '08X')

                    if uid_str != prev_uid:
                        # New card placed (or different card) — fire event once
                        prev_uid = uid_str
                        self._last[1] = uid_str
                        if self._callback:
                            self._callback('card_read', {'reader_id': 1, 'uid': uid_str})
                else:
                    # No card present — reset so the same card can fire again on next placement
                    prev_uid = None

            except Exception:
                prev_uid = None

            time.sleep(_POLL_INTERVAL)

    # ------------------------------------------------------------------
    # Hardware service contract
    # ------------------------------------------------------------------

    def get_state(self):
        return {'last': self._last}

    def execute(self, cmd, **kwargs):
        if cmd == 'simulate':
            reader_id = int(kwargs.get('reader_id', READERS[0]['id']))
            uid = str(kwargs.get('uid', 'AABBCCDD')).upper()
            self._last[reader_id] = uid
            if self._callback:
                self._callback('card_read', {'reader_id': reader_id, 'uid': uid})
            return {'reader_id': reader_id, 'uid': uid}
        raise ValueError(f'Unknown command: {cmd}')

    def set_event_callback(self, fn):
        self._callback = fn
