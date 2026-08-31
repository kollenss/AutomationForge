# THE DIAMOND HEIST – Komponentinventering
## Operation: Le Cœur Bleu | Senast uppdaterad: Maj 2026

> **Scope:** Det här är en inventering av fysisk hårdvara för att bygga briefcase-proppen
> (vad du har/saknar/behöver köpa) — inte GameForge-motorns konfiguration. Se `README.md`
> i den här mappen för var den tekniska/engine-dokumentationen bor istället.
>
> **OBS, inaktuellt sedan uppdateringen:** enligt den senaste statusen (2026-08, se
> `Z:\CLAUDE.md`) pivoterade projektet till en **ren Raspberry Pi-arkitektur** —
> ESP32-C3 och DFPlayer Mini används inte längre, trots vad "Projekt-användning"-kolumnen
> nedan säger på några rader. Tabellen är kvar oredigerad som historisk inventering;
> lita på `Z:\CLAUDE.md` för vad som faktiskt används idag.

---

## Mikrokontrollers & Datorer

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| ESP32-C3 SuperMini | Mikrokontroller | 10 | ✅ Har | Valvet + Våning 1 + reserv + framtida projekt | Fler än beställt – bra! WiFi inbyggt, 3.3V logik, Arduino IDE | Levererad |
| ESP32-C3 Expansion boards | Tillbehör | 4 | ✅ Har | Underlättar prototyping | Breakout-kort för ESP32-C3 | Levererad |
| Raspberry Pi 3B | Dator | 1 | ✅ Har | Våning 2 – Terminal | Kör Python terminal-UI | Befintlig |
| Arduino UNO | Mikrokontroller | 1 | ✅ Har | Prototyping / backup | | Befintlig |
| Arduino Pro Micro (ATmega32U4) | Mikrokontroller | 2 | ✅ Har | HID-enhet / tangentbordsemulator | Kan simulera tangentbord mot Pi | Befintlig |
| Wemos D1 Mini (ESP8266) | Mikrokontroller | 1 | ✅ Har | Backup / extra WiFi-nod | | Befintlig |

---

## RFID

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| RC522 RFID-moduler | RFID | 5 | ✅ Har | 3 rum + valvet + reserv | Mix blå och svarta, standard storlek | Levererad |
| RFID-kort vita (Mifare Classic) | RFID | 5 | ✅ Har | Karaktärskort x5 – används i projektet | Följde med RC522-läsarna, standard Mifare Classic 1K | Levererad |
| NTAG215 NFC-kort svarta | RFID | 10 | ✅ Har | Reserv / framtida projekt | Ej Mifare – används inte i detta projekt | Levererad |

---

## Ljud

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| DFPlayer Mini V3.0 HW-247A | Ljudmodul | 1 | 🚫 Används ej | Ersatt av Pi audio | Pi hanterar allt ljud via WiFi | Levererad |
| MicroSD-kort | Lagring | 1 | ✅ Har | Ljudfiler på Pi:ns SD-kort | | Befintlig |
| Högtalare 8Ω 1W (från dammsugare) | Ljud | 1 | ✅ Har | Cardinals röst | I gummihölje, rött/svart kabel | Befintlig |
| Miniatyr-högtalare extra | Ljud | 2 | ✅ Har | Backup / annan våning | | Befintlig |
| Bluetooth-öronsnäcka | Ljud | 1 | ⚠️ Fixa | Earpiece för briefingen | Paras med gammal smartphone | Befintlig/köp |
| Piezo-element (mässing) | Sensor/Ljud | 1 | ✅ Har | Stetoskop-feedback valvet | Passivt piezo, analogsignal | Befintlig |
| Ljudsensor med potentiometer | Sensor | 2 | ✅ Har | Alternativ stetoskop-sensor | Inbyggd förstärkare, justerbar känslighet | Befintlig |

---

## Aktuatorer

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Micro solenoid K055 5V-6V | Aktuator | 3 | ✅ Har | Frigör plattor Våning 1 och 2 | 8x10mm push-pull, mycket kompakt | Levererad |
| SG90 micro servo | Aktuator | 4 | ✅ Har | Öppnar plexiglasskivan valvet | Tower Pro + NG30 | Befintlig |
| Stegmotorer 5V (28BYJ-48 typ) | Motor | 4 | ✅ Har | Mekaniskt lås – alternativ till solenoid | Exakt positionskontroll, håller läge | Befintlig |
| DC-motorer diverse | Motor | 8 | ✅ Har | Framtida projekt / mekanik | Olika storlekar och spänningar | Befintlig |
| Brushless motorer + ESC-kort | Motor | 4 | ✅ Har | Framtida projekt (drönare/robotik) | Med matchande ESC-kretskort | Befintlig |

---

## Sensorer & Input

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Rotary encoder KY-040 | Sensor | 3 | ✅ Har | Vredet på valvet + reserv | CLK/DT/SW/VCC/GND pinout | Levererad |
| PIR-sensor HC-SR501 | Sensor | 1 | ✅ Har | Triggar Cardinal när hon närmar sig | "Jag ser dig, Nova" | Befintlig |
| HC-SR04 ultraljudssensor | Sensor | 1 | ✅ Har | Triggar Cardinal vid valvet | Detekterar närvaro utan kort | Befintlig |
| Reed switch (tungelement) | Sensor | 3 | ✅ Har | Detektera öppnade luckor/plattor | 1A och 50AT varianter | Befintlig |
| Hall-sensorer | Sensor | 2 | ✅ Har | Extra positionsdetektering | | Befintlig |
| IR cliff-sensorer (från dammsugare) | Sensor | 3 | ✅ Har | Proximity-trigger / platt-detektor | E314919, kort räckvidd 1–3cm, JST-kontakt, lila/vit kabel | Befintlig |
| Optiska hjulencoder-sensorer (från dammsugare) | Sensor | 4 | ✅ Har | Alternativ rotationsräknare för vredet | Fotointerruptor, röd/gul/svart/vit kabel, JST | Befintlig |

---

## Display & Input

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Raspberry Pi 3.5" SPI display Kedei | Display | 1 | ❌ Övergiven | — | **Defekt – visade bara scanlines/brus, ingen bild. Övergiven.** | Levererad |
| Redmi 9A telefon | Display | 1 | ✅ Används | Terminal Våning 2 – skärm | Pi HDMI → HDMI capture card → USB OTG → telefon | Befintlig |
| HDMI capture card (USB) | Display | 1 | ✅ Används | Terminal Våning 2 – bridge | Konverterar Pi HDMI till USB-video för telefonen | Befintlig |
| MAX7219 8-siffrig 7-segment display | Display | 1 | ✅ Har | Nedräkningstimer – bättre än OLED för detta | SPI, 5V, ser ut som riktig säkerhetstimer | Levererad |
| OLED-display 0.96" I2C | Display | 1 | ✅ Har | Extra display / valvet | VCC GND SCL SDA | Befintlig |
| Mini USB-tangentbord | Input | 1 | ✅ Har | Terminal Våning 2 | Svart, kompakt, USB-A | Levererad |

---

## Strömhantering

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Vapex NiMH 7.2V 4000mAh | Batteri | 1 | ✅ Har | Strömkälla valvet + våning 1 | Tamiya-kontakt, via LM2596 buck → 5V | Befintlig |
| BYD ICR18650 celler | Batteri | ~15 | ✅ Har | Strömkälla alla våningar | Lösa celler + 2-cells USB-laddare inkl. | Befintlig |
| 18650 nya batterier | Batteri | 4 | ✅ Har | Säker strömkälla | Gamla celler kan ha låg kapacitet | Levererad |
| 18650 Samsung ICR18650-22P | Batteri | 4+ | ⚠️ Kolla | Strömkälla per våning | Kontrollera kapacitet, köp nya vid behov | Befintlig |
| LiFePO4 batteripack 16.6V | Batteri | 1 | ✅ Har | Backup strömkälla | 4S pack med JST-kontakt | Befintlig |
| EMAX LiPo 7.6V 350mAh HV | Batteri | 2 | ⚠️ Liten kapacitet | Kortvarig strömkälla, ej primär | Kräver LiPo-laddare, begränsad drifttid | Befintlig |
| LM2596 DC-DC buck converter | Strömhantering | 10 | ✅ Har | Spänningsreglering per våning | Step-down, justerbar | Befintlig |
| LM1117T-3.3V regulator | Strömhantering | 10 | ✅ Har | 3.3V till ESP32-C3 | TO-220 package | Befintlig |
| TP4056 laddningsmodul | Strömhantering | 3 | ✅ Har | Laddar 18650-celler via USB | Mini-USB och micro-USB varianter | Befintlig |
| Powerbank-modul 5V/2.1A | Strömhantering | 1 | ✅ Har | Backup strömkälla | Från dammsugare | Befintlig |
| Breadboard strömförsörjning 5V/3.3V | Strömhantering | 2 | ✅ Har | Prototyping | USB-ingång, jumper 5V/3.3V | Befintlig |
| DC barrel jack-kablar | Kabel | 5 | ✅ Har | Strömkoppling per våning | Hane + hona | Befintlig |

---

## LED & Belysning

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| NeoPixel ring WS2812B 24-LED | RGB LED | 1 | ✅ Har | Lyser upp diamanten underifrån | Pulserar blått – animerad glöd | Befintlig |
| WS2812B LED-modul blå | RGB LED | 1 | ✅ Har | Statusindikator | JST-kontakt | Befintlig |
| LED-sortiment 3mm/5mm | LED | 30+ | ✅ Har | Röd kamera-LED + diverse | Röd, grön, blå, gul | Befintlig |
| SMD LED-kort (från dammsugare) | LED | 5+ | ✅ Har | Kan lödas loss eller användas direkt | WS2812B SMD | Befintlig |
| LED-panel stor SMD | LED | 1 | ✅ Har | Ambient-belysning / bakgrundsljus | Stor panel med många SMD-LEDs | Befintlig |

---

## Passiva Komponenter

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering |
|-----------|----------|-------|--------|--------------------|---------|
| Resistorer 330Ω | Resistor | 10 | ✅ Har | LED-resistorer för 3.3V | |
| Resistorer 1kΩ | Resistor | 10 | ✅ Har | Generell användning | |
| Resistorer 4.5kΩ | Resistor | 2 | ✅ Har | Pull-up/pull-down | |
| Resistorer 40kΩ | Resistor | 3 | ✅ Har | Signal-konditionering | |
| Resistorer 100kΩ | Resistor | 2 | ✅ Har | Signal-konditionering | |
| Keramiska kondensatorer | Kondensator | 30+ | ✅ Har | Avkoppling | Sortiment |
| Elektrolytkondensatorer 10µF | Kondensator | 10 | ✅ Har | Strömstabilisering | 50V |
| Elektrolytkondensatorer 1000µF | Kondensator | 8 | ✅ Har | Strömstabilisering vid solenoid | 63V stor + 16V |
| Trimpotentiometrar | Potentiometer | 4 | ✅ Har | Volymjustering etc. | |

---

## Övriga Komponenter

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Denkovi USB 4-relay board | Reläkort | 1 | ✅ Fungerar | USB-styrt från Raspberry Pi – solenoid Våning 2 | FT245RL, pylibftdi, CHANNEL_BITS: {1:0x02, 2:0x08, 3:0x20, 4:0x80}. udev-regel unbindar ftdi_sio. | Befintlig |
| ULN2003 stegmotordrivare | Motordrivare | 2 | ✅ Har | Driva solenoider från ESP32-C3 | | Befintlig |
| FT232RL USB-seriell adapter | Programmerare | 1 | ✅ Har | Programmera ESP32-C3 | Röd variant | Befintlig |
| DS3231 RTC-modul | Tidmodul | 1 | ✅ Har | Nedräkningstimer på terminalen | CR2032-hållare, I2C | Befintlig |
| Perfboard 4×6cm dubbelsidig | Kretskort | 5 | ✅ Har | Slutlig montering per våning | | Befintlig |
| Knappar sortiment | Input | 6+ | ✅ Har | Röda/gröna/blå caps + metallknapp | Metallknapp med LED = strömknapp | Befintlig |
| Transparent trycknapp med kabel | Input | 1 | ✅ Har | Startknapp för spelet | Lång kabel, Dupont-kontakt | Befintlig |
| Centrifugalfläkt med PCB | Fläkt | 1 | ✅ Har | Framtida projekt | Integrerad drivkrets | Befintlig |

---

## Props

| Komponent | Kategori | Antal | Status | Projekt-användning | Notering | Källa |
|-----------|----------|-------|--------|--------------------|----------|-------|
| Glasdiamant blå 4–6cm | Prop | 1 | ❌ Beställ | Le Cœur Bleu – slutmålet | Etsy eller Amazon | Beställ |
| Stetoskop | Prop | 1 | ❌ Beställ | Knäck kombinationslåset | Billigt plastexemplar räcker | Beställ |
| Plexiglasskiva 10×10cm 3mm | Material | 1 | ✅ Har | Täcker diamantutrymmet valvet | | Befintlig |
| USB-minne metallic-look | Prop | 1 | ⚠️ Fixa | Prop – sätts i terminalen | Välj ett som ser operativt ut | Befintlig/köp |
| Liten skruvmejsel | Prop | 1 | ⚠️ Fixa | Verktyget för USB-luckan | Finns hemma troligen | Befintlig |
| Bluetooth-öronsnäcka | Prop | 1 | ⚠️ Fixa | Earpiece för briefingen | Paras med gammal smartphone | Befintlig/köp |

---

## Återstår att köpa

| Komponent | Antal | Ca pris (kr) | Prioritet | Länk/Kommentar |
|-----------|-------|-------------|-----------|----------------|
| Glasdiamant blå 4–6cm | 1 | ~100 | 🟡 Medium | Etsy – "blue glass diamond" |
| Stetoskop | 1 | ~50 | 🟡 Medium | Kjell & Company eller AliExpress |
| USB-minne metallic-look | 1 | ~50 | 🟢 Låg | Välj ett som ser operativt ut |

---

## Viktiga tekniska noter

> **NTAG215 NFC-kort:** Korten som levererades är NTAG215 NFC, inte Mifare Classic. RC522 kan läsa dem men Arduino-koden behöver justeras för rätt protokoll.

> **Raspberry Pi-skärm:** Kedei SPI-displayen är övergiven (defekt). Ny lösning: Redmi 9A telefon som skärm via HDMI capture card + USB OTG. Pi kör pygame med SDL_VIDEODRIVER=kmsdrm, fullscreen 1920×1080.
