import json
import threading
import time
from pathlib import Path
import RPi.GPIO as GPIO

_CONFIG_PATH = Path(__file__).parent / 'config.json'


def _load_readers():
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        readers = data.get('rfid_readers', [])
        if readers:
            return readers
    except Exception as e:
        print(f'[rfid] could not load config.json ({e}) — using default')
    # Fallback: single vault reader
    return [{'id': 1, 'label': 'Vault', 'ce_gpio': 8, 'rst_gpio': 25}]


READERS = _load_readers()

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
                'options': [{'value': r['id'], 'label': f"{r['id']} – {r['label']}"} for r in READERS],
            },
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'card reader'},
        ],
        'inputs':  [
            {
                'key': 'enable',
                'label': 'Enable',
                'description': 'Activates this reader — connect from If/Else Then or any trigger',
            },
            {
                'key': 'disable',
                'label': 'Disable',
                'description': 'Deactivates this reader until re-enabled',
            },
        ],
        'outputs': [
            {
                'key': 'card_read',
                'label': 'Card UID',
                'description': 'Fires with the card UID string each time a new card is scanned',
            }
        ],
    }]


def _enable_antenna(ce_gpio):
    """Manually enable the RC522 antenna — the mfrc522 library does not do this on init."""
    import spidev
    # Map GPIO CS pin to SPI device number (CE0=GPIO8, CE1=GPIO7)
    # For software CS pins we briefly open CE0 to reach the chip — the chip
    # is selected by pulling its CS low via GPIO which MFRC522.__init__ does.
    # We just need to write TxControlReg after init.
    device = 0 if ce_gpio == 8 else 1 if ce_gpio == 7 else 0
    _spi = spidev.SpiDev()
    _spi.open(0, device)
    _spi.max_speed_hz = 1000000
    _txctrl = _spi.xfer2([0x6E | 0x80, 0x00])[1]
    _spi.xfer2([0x28, _txctrl | 0x03])
    _spi.close()


class Device:
    def __init__(self):
        self._callback = None
        self._last = {}        # reader_id → last detected uid string
        self._readers = []     # list of (reader_cfg, MFRC522_instance)

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        try:
            from mfrc522 import MFRC522
            for r in READERS:
                try:
                    reader = MFRC522(bus=0, device=0, pin_rst=r['rst_gpio'], pin_mode=11)
                    # For software-CS readers, manually drive the CS pin
                    if r['ce_gpio'] not in (8, 7):  # not a hardware CE pin
                        GPIO.setup(r['ce_gpio'], GPIO.OUT)
                        GPIO.output(r['ce_gpio'], GPIO.HIGH)  # deselect by default
                    _enable_antenna(r['ce_gpio'])
                    self._readers.append((r, reader))
                    print(f"[rfid] reader {r['id']} ({r['label']}) started — CE GPIO{r['ce_gpio']}, RST GPIO{r['rst_gpio']}, antenna ON")
                except Exception as e:
                    print(f"[rfid] reader {r['id']} ({r['label']}) init failed: {e}")

            if self._readers:
                t = threading.Thread(target=self._poll_loop, daemon=True, name='rfid-poll')
                t.start()
        except Exception as e:
            print(f'[rfid] hardware init failed ({e}) — stub mode active')

    # ------------------------------------------------------------------
    # Polling loop — polls each reader in turn
    # ------------------------------------------------------------------

    def _poll_loop(self):
        prev_uids = {}  # reader_id → last uid string (None = no card)

        while True:
            for (r, reader) in self._readers:
                rid = r['id']
                try:
                    (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
                    if status == reader.MI_OK:
                        (status, raw_uid) = reader.MFRC522_Anticoll()
                        if status == reader.MI_OK:
                            uid_str = ''.join(f'{b:02X}' for b in raw_uid[:4])
                            if uid_str != prev_uids.get(rid):
                                prev_uids[rid] = uid_str
                                self._last[rid] = uid_str
                                if self._callback:
                                    self._callback('card_read', {'reader_id': rid, 'uid': uid_str})
                    else:
                        prev_uids[rid] = None
                except Exception:
                    prev_uids[rid] = None

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

