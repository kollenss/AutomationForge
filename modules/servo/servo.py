"""SG90 servo motor module for GameForge hardware_service.

Hardware connection (Raspberry Pi):
  Servo brown  → GND  (Pin 6  or any GND)
  Servo red    → 5V   (Pin 2  or Pin 4)
  Servo orange → GPIO (Pin 32 / GPIO12 default — hardware PWM0)

Uses pigpio hardware_PWM() instead of set_servo_pulsewidth() to avoid
DMA conflict with rpi_ws281x (NeoPixel) which also uses PWM0 via DMA.

Hardware PWM pins on Pi 3B: GPIO12, GPIO13, GPIO18, GPIO19.
  GPIO12 (Pin 32) — PWM0, assigned to servo
  GPIO13 (Pin 33) — PWM1, backup / second servo
"""

try:
    import pigpio
    _HW_AVAILABLE = True
except ImportError:
    _HW_AVAILABLE = False
    print('[servo] pigpio not available — stub mode (commands logged only)')

MANIFEST = {
    'type':  'servo',
    'label': 'Servo Motor',
    'model': 'SG90',
}

_HW_PWM_PINS = {12, 13, 18, 19}


def get_components():
    return [{
        'type':          'servo',
        'label':         'Servo Motor',
        'subtitle':      'SG90',
        'category':      'output',
        'color':         '#8b5cf6',
        'icon':          '⚙',
        'display_param': 'name',
        'params': [
            {'key': 'gpio_pin', 'label': 'GPIO Pin (BCM)', 'type': 'number', 'default': 12,
             'description': 'BCM GPIO number the servo signal wire connects to. E.g. 12. See PIN_MAP.md for assignments.'},
            {'key': 'name',     'label': 'Label',          'type': 'text',   'default': 'servo',
             'description': 'Display name shown on the card. E.g. servo.'},
        ],
        'inputs': [
            {'key': 'set_angle', 'label': 'Set Angle (0–180°)',
             'description': 'Moves the servo to the given angle in degrees (0–180)'},
            {'key': 'release',   'label': 'Release',
             'description': 'Cuts PWM signal — servo relaxes, no holding torque'},
        ],
        'outputs': [
            {'key': 'done', 'label': 'Done',
             'description': 'Fires after the move command is sent'},
        ],
    }]


def _angle_to_duty(angle):
    """0–180° → pigpio hardware_PWM duty cycle (0–1 000 000).

    SG90 pulse range: 500 µs (0°) … 2500 µs (180°) at 50 Hz (20 000 µs period).
    duty = pulse_us / 20000 * 1_000_000 = pulse_us * 50
    """
    pulse_us = 500.0 + (max(0.0, min(180.0, float(angle))) / 180.0) * 2000.0
    return int(pulse_us * 50)


class Device:
    def __init__(self):
        if not _HW_AVAILABLE:
            self._pi = None
            print('[servo] stub mode')
            return
        self._pi = pigpio.pi()
        if not self._pi.connected:
            raise RuntimeError('pigpiod not running — start with: sudo systemctl start pigpiod')

    def get_state(self):
        return {}

    def execute(self, cmd, **kwargs):
        pin = int(kwargs.get('gpio_pin', 12))
        if not _HW_AVAILABLE:
            print(f'[servo] stub execute: {cmd} gpio={pin} angle={kwargs.get("angle", "—")}')
            return self.get_state()
        if pin not in _HW_PWM_PINS:
            raise ValueError(
                f'GPIO{pin} does not support hardware PWM. '
                f'Use one of: {sorted(_HW_PWM_PINS)}'
            )
        if cmd == 'set_angle':
            duty = _angle_to_duty(kwargs.get('angle', 90))
            self._pi.hardware_PWM(pin, 50, duty)
        elif cmd == 'release':
            self._pi.hardware_PWM(pin, 0, 0)
        else:
            raise ValueError(f'Unknown command: {cmd}')
        return self.get_state()
