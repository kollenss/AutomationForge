# Diamond Heist — GPIO Pin Map
## Raspberry Pi 3B (EN Pi styr ALLT — Våning 1, 2 och 3)
### Senast uppdaterad: 2026-06

---

## Snabbreferens — I bruk

| GPIO (BCM) | Board Pin | Signal | Komponent | Modul |
|---|---|---|---|---|
| GPIO7  | Pin 26 | SPI0 CE1 | MAX7219 CS | `max7219_display.py` |
| GPIO8  | Pin 24 | SPI0 CE0 | RC522 CS (Valvet) | `rfid.py` |
| GPIO9  | Pin 21 | SPI0 MISO | RC522 MISO (delad SPI-buss) | — |
| GPIO10 | Pin 19 | SPI0 MOSI | MAX7219 DIN + RC522 MOSI (delad) | — |
| GPIO11 | Pin 23 | SPI0 SCLK | MAX7219 CLK + RC522 SCK (delad) | — |
| GPIO17 | Pin 11 | Digital IN | KY-040 CLK | `rotary_encoder.py` |
| GPIO22 | Pin 15 | Digital IN | KY-040 SW (knapp) | `rotary_encoder.py` |
| GPIO25 | Pin 22 | Digital OUT | RC522 RST (Valvet) | `rfid.py` |
| GPIO27 | Pin 13 | Digital IN | KY-040 DT | `rotary_encoder.py` |
| —      | USB   | `/dev/ttyUSB0` | Denkovi Relay Board (4 kanaler) | `relay_trigger.py` |
| —      | USB   | `/dev/ttyUSB1` | DFPlayer Mini (MP3) | `dfplayer.py` |

---

## Snabbreferens — Planerat (ej kopplat än)

| GPIO (BCM) | Board Pin | Signal | Komponent | Våning |
|---|---|---|---|---|
| GPIO5  | Pin 29 | Digital OUT | RC522 CS — Lobby (Ghost) | V1 |
| GPIO6  | Pin 31 | Digital OUT | RC522 CS — Säkerhetscentral (Wraith) | V1 |
| GPIO12 | Pin 32 | PWM0 (HW) | Servo SG90 | V3 |
| GPIO16 | Pin 36 | Digital OUT | RC522 CS — Serverrum (Circuit) | V1 |
| GPIO21 | Pin 40 | PCM/DMA | WS2812B LED strip, 10 LED (index 0–2: V1, 3–5: V2, 6–9: V3) | V1+V2+V3 |
| GPIO23 | Pin 16 | Digital OUT | Piezo buzzer | V3 |
| GPIO26 | Pin 37 | Digital OUT | RC522 RST — delad för alla V1-läsare | V1 |

---

## Fullständig 40-pinnstabell

```
Board  BCM    Funktion          Status         Komponent / Notering
─────  ─────  ────────────────  ─────────────  ────────────────────────────────────
Pin 1  3.3V   Strömförsörjning  I BRUK         KY-040 VCC
Pin 2  5V     Strömförsörjning  LEDIG          (extra ström till perifera)
Pin 3  GPIO2  I2C SDA1          LEDIG          ⟵ Reserverad för OLED / DS3231 RTC
Pin 4  5V     Strömförsörjning  LEDIG
Pin 5  GPIO3  I2C SCL1          LEDIG          ⟵ Reserverad för OLED / DS3231 RTC
Pin 6  GND    Jord              I BRUK         KY-040 GND
Pin 7  GPIO4  Generell          LEDIG
Pin 8  GPIO14 UART TXD          LEDIG          (DFPlayer kör USB, inte HW UART)
Pin 9  GND    Jord              LEDIG
Pin 10 GPIO15 UART RXD          LEDIG          (DFPlayer kör USB, inte HW UART)
Pin 11 GPIO17 Generell          I BRUK         KY-040 CLK
Pin 12 GPIO18 PWM0 / PCM        LEDIG          ⟵ Frigjord (NeoPixel flyttad till Pin 40)
Pin 13 GPIO27 Generell          I BRUK         KY-040 DT
Pin 14 GND    Jord              LEDIG
Pin 15 GPIO22 Generell          I BRUK         KY-040 SW (knapp)
Pin 16 GPIO23 Generell          PLANERAD       Piezo buzzer (V3)
Pin 17 3.3V   Strömförsörjning  LEDIG
Pin 18 GPIO24 Generell          LEDIG          ← Frigjord (röd LED ersatt av WS2812B index 0)
Pin 19 GPIO10 SPI0 MOSI         I BRUK         MAX7219 DIN + RC522 MOSI (delad)
Pin 20 GND    Jord              LEDIG
Pin 21 GPIO9  SPI0 MISO         I BRUK         RC522 MISO
Pin 22 GPIO25 Generell          I BRUK         RC522 RST (Valvet)
Pin 23 GPIO11 SPI0 SCLK         I BRUK         MAX7219 CLK + RC522 SCK (delad)
Pin 24 GPIO8  SPI0 CE0          I BRUK         RC522 CS (Valvet)
Pin 25 GND    Jord              LEDIG
Pin 26 GPIO7  SPI0 CE1          I BRUK         MAX7219 CS
Pin 27 GPIO0  ID_SD (EEPROM)    RESERVERAD     ⚠ Använd ej — HAT EEPROM
Pin 28 GPIO1  ID_SC (EEPROM)    RESERVERAD     ⚠ Använd ej — HAT EEPROM
Pin 29 GPIO5  Generell          PLANERAD       RC522 CS — Lobby/Ghost (V1)
Pin 30 GND    Jord              LEDIG
Pin 31 GPIO6  Generell          PLANERAD       RC522 CS — Säkerhetscentral/Wraith (V1)
Pin 32 GPIO12 PWM0 (HW)         PLANERAD       Servo SG90 — pigpio HW PWM (V3)
Pin 33 GPIO13 PWM1 (HW)         LEDIG          ⟵ Backup servo / andra servo
Pin 34 GND    Jord              LEDIG
Pin 35 GPIO19 PWM1 alt          LEDIG
Pin 36 GPIO16 Generell          PLANERAD       RC522 CS — Serverrum/Circuit (V1)
Pin 37 GPIO26 Generell          PLANERAD       RC522 RST delad — alla V1-läsare
Pin 38 GPIO20 SPI1 MOSI         LEDIG
Pin 39 GND    Jord              LEDIG
Pin 40 GPIO21 SPI1 SCLK/PCM     PLANERAD       WS2812B strip 10 LED — rpi_ws281x PCM-DMA (V1+V2+V3)
```

---

## USB-enheter (ej GPIO)

| Port | Enhet | Driver | Path |
|---|---|---|---|
| USB | Denkovi 4-relay board | pylibftdi (FT245RL) | `/dev/ttyUSB0` (via udev-regel) |
| USB | DFPlayer Mini (FT232RL) | pyserial | `/dev/ttyUSB1` |
| USB | SEM USB Keyboard (Floor 2 terminal) | evdev | `/dev/input/by-id/usb-SEM_USB_Keyboard-event-kbd` |
| USB | YubiKey / USB-minne | usb_device_detector.py | detekteras via `lsusb` + `findmnt` |

> **Notera:** udev-regel unbindar `ftdi_sio` för relay-boardet — annars kräver pylibftdi root.

---

## Viktiga noteringar

### SPI-bussen (GPIO9/10/11) är delad
MAX7219 och alla RC522-läsare delar samma SPI0-buss (MOSI/MISO/SCLK).
De separeras via individuella CS-pinnar. Det fungerar utan problem — de pratar aldrig samtidigt.

```
SPI0 MOSI (GPIO10) ─┬─► MAX7219 DIN    (CS via GPIO7/CE1)
                    ├─► RC522 Valvet    (CS via GPIO8/CE0)
                    ├─► RC522 V1 Lobby  (CS via GPIO5)
                    ├─► RC522 V1 Säkerh (CS via GPIO6)
                    └─► RC522 V1 Server (CS via GPIO16)
```

### PWM-kanaler
Pi 3B har två oberoende hardware PWM-kanaler:
- **PWM0:** GPIO12 (pin 32) och GPIO18 (pin 12) — samma kanal, kan EJ användas samtidigt
- **PWM1:** GPIO13 (pin 33) och GPIO19 (pin 35) — samma kanal, kan EJ användas samtidigt

**Vald plan:** Servo på GPIO12 (PWM0, pigpio HW PWM) + WS2812B strip på GPIO21 (PCM-DMA, rpi_ws281x).
✅ Ingen PWM-konflikt — WS2812B använder PCM-peripheraln, inte PWM. GPIO18 är frigjord.

### RC522 RST-strategi
- Valvet: individuell RST på GPIO25
- Våning 1 (3 läsare): delar RST på GPIO26 — ok, alla initieras samtidigt vid start

### Lediga GPIO-pinnar (bekräftat fria)
GPIO4, GPIO13, GPIO14, GPIO15, GPIO18, GPIO19, GPIO20 — tillgängliga för framtida expansion.

---

## Arkitekturnotering
Allt kör på EN Raspberry Pi 3B — ingen ESP32, ingen Arduino.
COMPONENTS.md nämner ESP32-C3 för valvet/Våning 1 men det är inaktuellt.
Beslut: Pi hanterar all hårdvara via hardware_service på port 5101.
