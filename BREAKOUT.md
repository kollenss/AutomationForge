# Diamond Heist — Breakout Board Layout

## Kortspecifikation
- **Storlek:** 14 rader (1–14) × 20 kolumner (A–T)
- **Origo:** A1 = längst ned till vänster
- **Pi-header:** Rad 13–14, kolumn A–T (2×20 flatkabel)
- **Yt-pads:** 7 st per kortsida (LP1–LP7 vänster, RP1–RP7 höger)

---

## Layout

```
      A    B    C    D    E    F    G    H    I    J    K    L    M    N    O    P    Q    R    S    T
 14  [3V3][IO2][IO3][IO4][GND][G17][G27][G22][3V3][MOS][MIS][SCK][GND][IO0][IO5][IO6][G13][G19][G26][GND]  Pi udda pins
 13  [ 5V][ 5V][GND][G14][G15][G18][GND][G23][G24][GND][G25][ G8][ G7][ G1][GND][G12][GND][G16][G20][G21]  Pi jämna pins
 12  [════════════════════════════════ 3.3V buss ═════════════════════════════════════════════════════════]
 11  [════════════════════════════════  GND buss ═════════════════════════════════════════════════════════]
 10  [════════════════════════════════   5V buss ═════════════════════════════════════════════════════════]
  9  [   ][   ][   ][   ][GND][CLK][ DT][ SW][3V3][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ]  KY-040
  8  [   ][   ][   ][   ][   ][   ][   ][   ][   ][MOS][MIS][SCK][ CS][RST][3V3][GND][   ][   ][   ][   ]  RC522 Valvet
  7  [   ][   ][   ][   ][   ][   ][   ][   ][   ][MOS][MIS][SCK][ CS][RST][3V3][GND][   ][   ][   ][   ]  RC522 Lobby
  6  [   ][   ][   ][   ][   ][   ][   ][   ][   ][MOS][MIS][SCK][ CS][RST][3V3][GND][   ][   ][   ][   ]  RC522 Wraith
  5  [   ][   ][   ][   ][   ][   ][   ][   ][   ][MOS][MIS][SCK][ CS][RST][3V3][GND][   ][   ][   ][   ]  RC522 Circuit
  4  [   ][   ][   ][   ][   ][   ][   ][   ][ 5V][DIN][GND][CLK][ CS][   ][   ][   ][   ][   ][   ][   ]  MAX7219
  3  [   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][   ][GND][SIG][ 5V][GND][ 5V][DAT]  Servo + WS2812B
  2   spare
  1   spare
```

---

## Pi-header pinmappning

| Kolumn | Rad 14 (udda) | Rad 13 (jämna) |
|--------|---------------|----------------|
| A | Pin 1 — 3.3V | Pin 2 — 5V |
| B | Pin 3 — GPIO2 | Pin 4 — 5V |
| C | Pin 5 — GPIO3 | Pin 6 — GND |
| D | Pin 7 — GPIO4 | Pin 8 — GPIO14 |
| E | Pin 9 — GND | Pin 10 — GPIO15 |
| F | Pin 11 — **GPIO17** (KY-040 CLK) | Pin 12 — GPIO18 |
| G | Pin 13 — **GPIO27** (KY-040 DT) | Pin 14 — GND |
| H | Pin 15 — **GPIO22** (KY-040 SW) | Pin 16 — GPIO23 |
| I | Pin 17 — 3.3V | Pin 18 — GPIO24 |
| J | Pin 19 — **GPIO10** (MOSI) | Pin 20 — GND |
| K | Pin 21 — **GPIO9** (MISO) | Pin 22 — **GPIO25** (RST Valvet) |
| L | Pin 23 — **GPIO11** (SCLK) | Pin 24 — **GPIO8** (CS Valvet) |
| M | Pin 25 — GND | Pin 26 — **GPIO7** (MAX7219 CS) |
| N | Pin 27 — GPIO0 | Pin 28 — GPIO1 |
| O | Pin 29 — **GPIO5** (CS Lobby) | Pin 30 — GND |
| P | Pin 31 — **GPIO6** (CS Wraith) | Pin 32 — **GPIO12** (Servo) |
| Q | Pin 33 — GPIO13 | Pin 34 — GND |
| R | Pin 35 — GPIO19 | Pin 36 — **GPIO16** (CS Circuit) |
| S | Pin 37 — **GPIO26** (RST V1 delad) | Pin 38 — GPIO20 |
| T | Pin 39 — GND | Pin 40 — **GPIO21** (WS2812B) |

---

## Komponentplacering

### KY-040 Rotary Encoder — Rad 9

| Pad | Signal | Källa |
|-----|--------|-------|
| E9 | GND | Rad 11 (GND buss) |
| F9 | CLK | F14 — GPIO17 |
| G9 | DT | G14 — GPIO27 |
| H9 | SW | H14 — GPIO22 |
| I9 | VCC | Rad 12 (3.3V buss) |

### RC522 Valvet — Rad 8, kolumn J–P

| Pad | Signal | Källa |
|-----|--------|-------|
| J8 | MOSI | J14 — GPIO10 |
| K8 | MISO | K14 — GPIO9 |
| L8 | SCLK | L14 — GPIO11 |
| M8 | CS | L13 — GPIO8 |
| N8 | RST | K13 — GPIO25 |
| O8 | 3.3V | Rad 12 (3.3V buss) |
| P8 | GND | Rad 11 (GND buss) |

### RC522 Lobby/Ghost — Rad 7, kolumn J–P

| Pad | Signal | Källa |
|-----|--------|-------|
| J7 | MOSI | SPI-buss kol J |
| K7 | MISO | SPI-buss kol K |
| L7 | SCLK | SPI-buss kol L |
| M7 | CS | O14 — GPIO5 |
| N7 | RST | S14 — GPIO26 (delad) |
| O7 | 3.3V | Rad 12 (3.3V buss) |
| P7 | GND | Rad 11 (GND buss) |

### RC522 Säkerhetscentral/Wraith — Rad 6, kolumn J–P

| Pad | Signal | Källa |
|-----|--------|-------|
| J6 | MOSI | SPI-buss kol J |
| K6 | MISO | SPI-buss kol K |
| L6 | SCLK | SPI-buss kol L |
| M6 | CS | P14 — GPIO6 |
| N6 | RST | N7 (delad RST-buss) |
| O6 | 3.3V | Rad 12 (3.3V buss) |
| P6 | GND | Rad 11 (GND buss) |

### RC522 Serverrum/Circuit — Rad 5, kolumn J–P

| Pad | Signal | Källa |
|-----|--------|-------|
| J5 | MOSI | SPI-buss kol J |
| K5 | MISO | SPI-buss kol K |
| L5 | SCLK | SPI-buss kol L |
| M5 | CS | R13 — GPIO16 |
| N5 | RST | N6 (delad RST-buss) |
| O5 | 3.3V | Rad 12 (3.3V buss) |
| P5 | GND | Rad 11 (GND buss) |

### MAX7219 Display — Rad 4, kolumn I–M

| Pad | Signal | Källa |
|-----|--------|-------|
| I4 | VCC | Rad 10 (5V buss) |
| J4 | DIN | SPI-buss kol J (MOSI) |
| K4 | GND | Rad 11 (GND buss) |
| L4 | CLK | SPI-buss kol L (SCLK) |
| M4 | CS | M13 — GPIO7 |

### Servo SG90 — Rad 3, kolumn O–Q

| Pad | Signal | Källa |
|-----|--------|-------|
| O3 | GND | Rad 11 (GND buss) |
| P3 | SIG | P13 — GPIO12 |
| Q3 | VCC | Rad 10 (5V buss) |

### WS2812B LED-strip — Rad 3, kolumn R–T

| Pad | Signal | Källa |
|-----|--------|-------|
| R3 | GND | Rad 11 (GND buss) |
| S3 | VCC | Rad 10 (5V buss) |
| T3 | DAT | T13 — GPIO21 |

---

## Undersidan — ledningsplan

### Raka vertikala ledningar (ingen routing krävs)

| Signal | Kolumn | Anslutna pads |
|--------|--------|---------------|
| MOSI/SPI-buss | J | J14 → J8 → J7 → J6 → J5 → J4 |
| MISO/SPI-buss | K | K14 → K8 → K7 → K6 → K5 |
| SCLK/SPI-buss | L | L14 → L8 → L7 → L6 → L5 → L4 |
| KY-040 CLK | F | F14 → F9 |
| KY-040 DT | G | G14 → G9 |
| KY-040 SW | H | H14 → H9 |
| MAX7219 CS | M | M13 → M4 |
| Servo SIG | P | P13 → P3 |
| WS2812B DAT | T | T13 → T3 |
| V1 RST delad | N | N7 → N6 → N5 (sedan trace till S14) |

### Korta diagonala ledningar

| Signal | Från | Till | Ungefärlig längd |
|--------|------|------|-----------------|
| Valvet CS | L13 (GPIO8) | M8 | 1 kol |
| Valvet RST | K13 (GPIO25) | N8 | 3 kol |
| Lobby CS | O14 (GPIO5) | M7 | 2 kol |
| Wraith CS | P14 (GPIO6) | M6 | 3 kol |
| Circuit CS | R13 (GPIO16) | M5 | 5 kol — kör som L (R13→R5→M5) |
| V1 RST | S14 (GPIO26) | N7 | 5 kol |
| 3.3V buss | A14 | A12 → rad 12 | kort |
| GND buss | E14 | E12 → rad 11 | kort |
| 5V buss | A13 | A10 → rad 10 | kort |

### Viktigt
- **CS-pinnarna M4–M8** är individuella signaler i samma kolumn — använd **isolerad tråd** så de inte kortar mot varandra.
- **Circuit CS** (längsta trace, 5 kol) — kör som L-form: rakt ned längs kol R från R13 till R5, sedan horisontellt vänster R5→M5.
- **V1 RST-bussen** (N5–N7): löd en vertikal tråd längs kol N rad 5–7, sedan en diagonal till S14.
