import json
import threading
import time
from pathlib import Path

try:
    import RPi.GPIO as GPIO
    import spidev
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False
    print('[rfid] RPi.GPIO/spidev not available — stub mode (no hardware scanning)')

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
_REG_COMMAND     = 0x01
_REG_COM_I_EN    = 0x02
_REG_COM_IRQ     = 0x04
_REG_ERROR       = 0x06
_REG_FIFO_DATA   = 0x09
_REG_FIFO_LEVEL  = 0x0A
_REG_BIT_FRAMING = 0x0D
_REG_CONTROL     = 0x0C
_REG_TX_CONTROL  = 0x14
_REG_VERSION     = 0x37

_CMD_IDLE        = 0x00
_CMD_TRANSCEIVE  = 0x0C
_CMD_RESETPHASE  = 0x0F

_PICC_REQIDL     = 0x26
_PICC_ANTICOLL   = 0x93

_MI_OK    = 0
_MI_NOTAG = 1
_MI_ERR   = 2


_GPIO_TO_PIN = {2:3,3:5,4:7,5:29,6:31,7:26,8:24,9:21,10:19,11:23,12:32,13:33,14:8,15:22,16:36,17:11,18:12,19:35,20:38,21:40,22:15,23:16,24:18,25:22,26:37,27:13}

def _gpio_to_pin(gpio):
    return _GPIO_TO_PIN.get(gpio, '?')

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
                'options': [{'value': r['id'], 'label': f"{r['id']} – {r['label']} (GPIO{r['ce_gpio']} / pin {_gpio_to_pin(r['ce_gpio'])})"} for r in READERS],
                'description': 'Which physical RC522 reader this card represents (each reader has its own chip-select pin).',
            },
            {'key': 'name', 'label': 'Label', 'type': 'text', 'default': 'card reader',
             'description': 'Display name shown on the card. E.g. card reader.'},
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
    GPIO.setup(rst, GPIO.OUT)
    GPIO.output(rst, GPIO.HIGH)
    time.sleep(0.05)
    _write_reg(spi, cs, _REG_COMMAND, _CMD_RESETPHASE)
    time.sleep(0.05)
    _write_reg(spi, cs, 0x2A, 0x8D)
    _write_reg(spi, cs, 0x2B, 0x3E)
    _write_reg(spi, cs, 0x2D, 30)
    _write_reg(spi, cs, 0x2C, 0)
    _write_reg(spi, cs, 0x15, 0x40)
    _write_reg(spi, cs, 0x11, 0x3D)
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
        self._readers = []
        self._spi = None

        if not _HW_AVAILABLE:
            print('[rfid] stub mode — use "simulate" command to fire card events')
            return

        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)

        try:
            spi = spidev.SpiDev()
            spi.open(0, 0)
            spi.max_speed_hz = 1_000_000
            spi.mode = 0
            self._spi = spi

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
                except Exception:
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
