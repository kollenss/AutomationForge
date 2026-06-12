import json
import threading
import time
from pathlib import Path
import RPi.GPIO as GPIO
import spidev

_CONFIG_PATH = Path(__file__).parent / 'config.json'


def _load_readers():
    try:
        data = json.loads(_CONFIG_PATH.read_text())
        readers = data.get('rfid_readers', [])
        if readers:
            return readers
    except Exception as e:
        print(f'[rfid] could not load config.json ({e}) — using default')
    return [{'id': 1, 'label': 'Vault', 'ce_gpio': 8, 'rst_gpio': 25}]


READERS = _load_readers()

MANIFEST = {
    'type': 'rfid_reader',
    'label': 'RFID Reader RC522',
    'readers': len(READERS),
}

_POLL_INTERVAL = 0.1   # seconds between full scan cycles

# ── RC522 register constants ───────────────────────────────────────────────────
_REG_COMMAND    = 0x01
_REG_COM_I_EN   = 0x02
_REG_COM_IRQ    = 0x04
_REG_ERROR      = 0x06
_REG_FIFO_DATA  = 0x09
_REG_FIFO_LEVEL = 0x0A
_REG_BIT_FRAMING= 0x0D
_REG_CONTROL    = 0x0C
_REG_TX_CONTROL = 0x14
_REG_VERSION    = 0x37

_CMD_IDLE       = 0x00
_CMD_TRANSCEIVE = 0x0C
_CMD_RESETPHASE = 0x0F

_PICC_REQIDL    = 0x26
_PICC_ANTICOLL  = 0x93

_MI_OK     = 0
_MI_NOTAG  = 1
_MI_ERR    = 2


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
        'inputs': [
            {'key': 'enable',  'label': 'Enable',  'description': 'Activates this reader'},
            {'key': 'disable', 'label': 'Disable', 'description': 'Deactivates this reader'},
        ],
        'outputs': [
            {'key': 'card_read', 'label': 'Card UID',
             'description': 'Fires with the card UID string each time a new card is scanned'},
        ],
    }]


# ── Low-level SPI + GPIO CS helpers ───────────────────────────────────────────

def _cs_select(cs):
    if cs not in (8, 7):
        GPIO.output(cs, GPIO.LOW)

def _cs_deselect(cs):
    if cs not in (8, 7):
        GPIO.output(cs, GPIO.HIGH)

def _read_reg(spi, cs, reg):
    _cs_select(cs)
    val = spi.xfer2([((reg << 1) & 0x7E) | 0x80, 0x00])[1]
    _cs_deselect(cs)
    return val

def _write_reg(spi, cs, reg, val):
    _cs_select(cs)
    spi.xfer2([(reg << 1) & 0x7E, val & 0xFF])
    _cs_deselect(cs)

def _set_bits(spi, cs, reg, mask):
    _write_reg(spi, cs, reg, _read_reg(spi, cs, reg) | mask)

def _clear_bits(spi, cs, reg, mask):
    _write_reg(spi, cs, reg, _read_reg(spi, cs, reg) & (~mask & 0xFF))

def _init_reader(spi, cs, rst):
    """Reset and configure one RC522."""
    GPIO.setup(rst, GPIO.OUT)
    GPIO.output(rst, GPIO.HIGH)
    time.sleep(0.05)
    _write_reg(spi, cs, _REG_COMMAND, _CMD_RESETPHASE)
    time.sleep(0.05)
    _write_reg(spi, cs, 0x2A, 0x8D)   # TModeReg
    _write_reg(spi, cs, 0x2B, 0x3E)   # TPrescalerReg
    _write_reg(spi, cs, 0x2D, 30)     # TReloadRegL
    _write_reg(spi, cs, 0x2C, 0)      # TReloadRegH
    _write_reg(spi, cs, 0x15, 0x40)   # TxASKReg
    _write_reg(spi, cs, 0x11, 0x3D)   # ModeReg
    # Antenna on
    tx = _read_reg(spi, cs, _REG_TX_CONTROL)
    if not (tx & 0x03):
        _set_bits(spi, cs, _REG_TX_CONTROL, 0x03)

def _to_card(spi, cs, command, send_data):
    _write_reg(spi, cs, _REG_COM_I_EN, 0x77 | 0x80)
    _clear_bits(spi, cs, _REG_COM_IRQ, 0x80)
    _set_bits(spi, cs, _REG_FIFO_LEVEL, 0x80)
    _write_reg(spi, cs, _REG_COMMAND, _CMD_IDLE)
    for b in send_data:
        _write_reg(spi, cs, _REG_FIFO_DATA, b)
    _write_reg(spi, cs, _REG_COMMAND, command)
    if command == _CMD_TRANSCEIVE:
        _set_bits(spi, cs, _REG_BIT_FRAMING, 0x80)
    wait_irq = 0x30 if command == _CMD_TRANSCEIVE else 0x10
    i = 2000
    while i > 0:
        n = _read_reg(spi, cs, _REG_COM_IRQ)
        if n & wait_irq:
            break
        if n & 0x01:
            return _MI_NOTAG, [], 0
        i -= 1
    _clear_bits(spi, cs, _REG_BIT_FRAMING, 0x80)
    if i == 0:
        return _MI_ERR, [], 0
    if _read_reg(spi, cs, _REG_ERROR) & 0x1B:
        return _MI_ERR, [], 0
    n = _read_reg(spi, cs, _REG_FIFO_LEVEL)
    last_bits = _read_reg(spi, cs, _REG_CONTROL) & 0x07
    back_len = (n - 1) * 8 + last_bits if last_bits else n * 8
    n = min(n, 16)
    back = [_read_reg(spi, cs, _REG_FIFO_DATA) for _ in range(n)]
    return _MI_OK, back, back_len

def _request(spi, cs):
    _write_reg(spi, cs, _REG_BIT_FRAMING, 0x07)
    status, _, _ = _to_card(spi, cs, _CMD_TRANSCEIVE, [_PICC_REQIDL])
    return status

def _anticoll(spi, cs):
    _write_reg(spi, cs, _REG_BIT_FRAMING, 0x00)
    status, back, _ = _to_card(spi, cs, _CMD_TRANSCEIVE, [_PICC_ANTICOLL, 0x20])
    if status == _MI_OK and len(back) == 5:
        chk = 0
        for b in back[:4]:
            chk ^= b
        if chk != back[4]:
            return _MI_ERR, []
    return status, back


# ── Device ─────────────────────────────────────────────────────────────────────

class Device:
    def __init__(self):
        self._callback = None
        self._last = {}
        self._readers = []   # list of (reader_cfg,) — spi is shared
        self._spi = None

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        try:
            spi = spidev.SpiDev()
            spi.open(0, 0)
            spi.max_speed_hz = 1_000_000
            spi.mode = 0
            self._spi = spi

            # All software CS pins start deselected
            for r in READERS:
                cs = r['ce_gpio']
                if cs not in (8, 7):
                    GPIO.setup(cs, GPIO.OUT)
                    GPIO.output(cs, GPIO.HIGH)

            for r in READERS:
                try:
                    _init_reader(spi, r['ce_gpio'], r['rst_gpio'])
                    ver = _read_reg(spi, r['ce_gpio'], _REG_VERSION)
                    self._readers.append(r)
                    print(f"[rfid] reader {r['id']} ({r['label']}) ready — "
                          f"CE GPIO{r['ce_gpio']}, RST GPIO{r['rst_gpio']}, version=0x{ver:02X}")
                except Exception as e:
                    print(f"[rfid] reader {r['id']} ({r['label']}) init failed: {e}")

            if self._readers:
                t = threading.Thread(target=self._poll_loop, daemon=True, name='rfid-poll')
                t.start()

        except Exception as e:
            print(f'[rfid] hardware init failed ({e}) — stub mode active')

    def _poll_loop(self):
        spi = self._spi
        prev_uids = {}

        while True:
            for r in self._readers:
                rid = r['id']
                cs  = r['ce_gpio']
                try:
                    if _request(spi, cs) == _MI_OK:
                        status, uid = _anticoll(spi, cs)
                        if status == _MI_OK and len(uid) >= 4:
                            uid_str = ''.join(f'{b:02X}' for b in uid[:4])
                            if uid_str != prev_uids.get(rid):
                                prev_uids[rid] = uid_str
                                self._last[rid] = uid_str
                                print(f'[rfid] reader {rid} ({r["label"]}) UID: {uid_str}')
                                if self._callback:
                                    self._callback('card_read', {'reader_id': rid, 'uid': uid_str})
                    else:
                        prev_uids[rid] = None
                except Exception as ex:
                    prev_uids[rid] = None

            time.sleep(_POLL_INTERVAL)

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

