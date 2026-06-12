#!/usr/bin/env python3
"""
Standalone test for 4 RC522 RFID readers on shared SPI0 bus.
Each reader uses its own GPIO CS pin (software chip-select).

Wiring assumed (from config.json):
  Reader 1 (Vault):    CE=GPIO8  (SPI0 CE0, hardware), RST=GPIO25
  Reader 2 (Lobby):    CE=GPIO5  (software CS),         RST=GPIO26
  Reader 3 (Security): CE=GPIO6  (software CS),         RST=GPIO26
  Reader 4 (Server):   CE=GPIO16 (software CS),         RST=GPIO26

Run: python3 test_rfid_4.py
Hold a card against each reader when prompted.
Press Ctrl+C to skip a reader.
"""
import time
import RPi.GPIO as GPIO
import spidev

# ── Config ─────────────────────────────────────────────────────────────────
READERS = [
    {'id': 1, 'label': 'Vault',    'ce': 8,  'rst': 25},
    {'id': 2, 'label': 'Lobby',    'ce': 5,  'rst': 26},
    {'id': 3, 'label': 'Security', 'ce': 6,  'rst': 26},
    {'id': 4, 'label': 'Server',   'ce': 16, 'rst': 26},
]

SPI_BUS  = 0
SPI_FREQ = 1_000_000

# RC522 register addresses
REG_COMMAND    = 0x01
REG_TX_CONTROL = 0x14  # bit 0+1 = antenna pins
REG_VERSION    = 0x37

MI_OK  = 0
MI_NOTAG = 1
MI_ERR = 2
PICC_REQIDL = 0x26
PICC_ANTICOLL = 0x93
PCD_TRANSCEIVE = 0x0C
PCD_RESETPHASE = 0x0F
PCD_CALCCRC = 0x03

# ── Low-level SPI helpers ─────────────────────────────────────────────────────

ALL_CS = [r['ce'] for r in READERS]

def _setup_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    for pin in ALL_CS:
        if pin not in (8, 7):          # skip hardware CE pins
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.HIGH) # deselected

def _select(spi, cs_pin):
    if cs_pin not in (8, 7):
        GPIO.output(cs_pin, GPIO.LOW)

def _deselect(cs_pin):
    if cs_pin not in (8, 7):
        GPIO.output(cs_pin, GPIO.HIGH)

def _read_reg(spi, cs, reg):
    _select(spi, cs)
    val = spi.xfer2([((reg << 1) & 0x7E) | 0x80, 0x00])[1]
    _deselect(cs)
    return val

def _write_reg(spi, cs, reg, val):
    _select(spi, cs)
    spi.xfer2([(reg << 1) & 0x7E, val])
    _deselect(cs)

def _set_bits(spi, cs, reg, mask):
    _write_reg(spi, cs, reg, _read_reg(spi, cs, reg) | mask)

def _clear_bits(spi, cs, reg, mask):
    _write_reg(spi, cs, reg, _read_reg(spi, cs, reg) & (~mask))

# ── RC522 init ────────────────────────────────────────────────────────────────

def _reset(spi, cs, rst_pin):
    GPIO.setup(rst_pin, GPIO.OUT)
    GPIO.output(rst_pin, GPIO.HIGH)
    time.sleep(0.05)
    _write_reg(spi, cs, REG_COMMAND, PCD_RESETPHASE)
    time.sleep(0.05)
    # Timer: auto mode, prescaler
    _write_reg(spi, cs, 0x2A, 0x8D)
    _write_reg(spi, cs, 0x2B, 0x3E)
    _write_reg(spi, cs, 0x2D, 30)
    _write_reg(spi, cs, 0x2C, 0)
    _write_reg(spi, cs, 0x15, 0x40)
    _write_reg(spi, cs, 0x11, 0x3D)
    # Antenna on
    tx = _read_reg(spi, cs, REG_TX_CONTROL)
    if not (tx & 0x03):
        _set_bits(spi, cs, REG_TX_CONTROL, 0x03)

def _get_version(spi, cs):
    return _read_reg(spi, cs, REG_VERSION)

# ── PICC communication ────────────────────────────────────────────────────────

def _to_card(spi, cs, command, send_data):
    back_data = []
    back_len  = 0
    status    = MI_ERR

    irq_en    = 0x77 if command == PCD_TRANSCEIVE else 0x12
    wait_irq  = 0x30 if command == PCD_TRANSCEIVE else 0x10

    _write_reg(spi, cs, 0x02, irq_en | 0x80)
    _clear_bits(spi, cs, 0x04, 0x80)
    _set_bits(spi, cs, 0x0A, 0x80)
    _write_reg(spi, cs, REG_COMMAND, 0x00)

    for b in send_data:
        _write_reg(spi, cs, 0x09, b)

    _write_reg(spi, cs, REG_COMMAND, command)
    if command == PCD_TRANSCEIVE:
        _set_bits(spi, cs, 0x0D, 0x80)

    i = 2000
    while True:
        n = _read_reg(spi, cs, 0x04)
        i -= 1
        if not (i != 0 and not (n & 0x01) and not (n & wait_irq)):
            break

    _clear_bits(spi, cs, 0x0D, 0x80)

    if i != 0:
        if (_read_reg(spi, cs, 0x06) & 0x1B) == 0x00:
            status = MI_OK
            if n & irq_en & 0x01:
                status = MI_NOTAG
            elif command == PCD_TRANSCEIVE:
                n = _read_reg(spi, cs, 0x0A)
                last_bits = _read_reg(spi, cs, 0x0C) & 0x07
                back_len = (n - 1) * 8 + last_bits if last_bits else n * 8
                n = min(n, 16)
                for _ in range(n):
                    back_data.append(_read_reg(spi, cs, 0x09))
        else:
            status = MI_ERR

    return (status, back_data, back_len)

def _request(spi, cs):
    _write_reg(spi, cs, 0x0D, 0x07)
    status, _, _ = _to_card(spi, cs, PCD_TRANSCEIVE, [PICC_REQIDL])
    return status

def _anticoll(spi, cs):
    _write_reg(spi, cs, 0x0D, 0x00)
    status, back, _ = _to_card(spi, cs, PCD_TRANSCEIVE, [PICC_ANTICOLL, 0x20])
    if status == MI_OK and len(back) == 5:
        check = 0
        for b in back[:4]:
            check ^= b
        if check != back[4]:
            return MI_ERR, []
    return status, back

# ── Main test ─────────────────────────────────────────────────────────────────

def test_reader(spi, reader, timeout=10):
    cs  = reader['ce']
    rst = reader['rst']
    rid = reader['id']
    lbl = reader['label']

    print(f"\n── Reader {rid} ({lbl}) — CE=GPIO{cs}, RST=GPIO{rst} ──")
    _reset(spi, cs, rst)
    ver = _get_version(spi, cs)
    if ver in (0x91, 0x92, 0x88, 0xB2):
        print(f"  ✓ RC522 found (version 0x{ver:02X}{' — clone variant' if ver not in (0x91,0x92) else ''})")
    elif ver in (0xEE,):
        print(f"  ✓ RC522 clone found (version 0x{ver:02X})")
    elif ver == 0x00 or ver == 0xFF:
        print(f"  ✗ No response (version=0x{ver:02X}) — check wiring or stop hardware-service first!")
        return False
    else:
        print(f"  ? Unexpected version 0x{ver:02X} — may still work")

    print(f"  Hold a card against reader {rid} ({lbl}) ... (Ctrl+C to skip)")
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            if _request(spi, cs) == MI_OK:
                status, uid = _anticoll(spi, cs)
                if status == MI_OK and len(uid) >= 4:
                    uid_str = ''.join(f'{b:02X}' for b in uid[:4])
                    print(f"  ✓ Card detected! UID: {uid_str}")
                    return True
            time.sleep(0.1)
        print(f"  ✗ Timeout — no card detected in {timeout}s")
        return False
    except KeyboardInterrupt:
        print("  (skipped)")
        return None


def main():
    print("=== RC522 4-Reader SPI Test ===")
    print("SPI0, shared MISO/MOSI/CLK, individual GPIO CS pins\n")

    # Warn if hardware-service is running — it holds the SPI bus for Reader 1
    try:
        import subprocess
        r = subprocess.run(['systemctl', 'is-active', 'hardware-service'],
                          capture_output=True, text=True)
        if r.stdout.strip() == 'active':
            print("⚠️  hardware-service is running — Reader 1 (CE0/GPIO8) may fail.")
            print("   Stop it first with: sudo systemctl stop hardware-service\n")
    except Exception:
        pass

    _setup_gpio()

    spi = spidev.SpiDev()
    spi.open(SPI_BUS, 0)   # open CE0 bus — CS is handled via GPIO
    spi.max_speed_hz = SPI_FREQ
    spi.mode = 0

    results = {}
    for r in READERS:
        results[r['id']] = test_reader(spi, r)

    spi.close()
    GPIO.cleanup()

    print("\n=== Summary ===")
    for rid, ok in results.items():
        lbl = next(r['label'] for r in READERS if r['id'] == rid)
        icon = '✓' if ok else ('—' if ok is None else '✗')
        print(f"  {icon}  Reader {rid} ({lbl})")


if __name__ == '__main__':
    main()
