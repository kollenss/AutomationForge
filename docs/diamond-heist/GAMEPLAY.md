# GAMEPLAY – All Three Acts

*Puzzle flow and player experience only. For how the engine actually implements
this (state machines, wiring, code), see the platform docs linked in `README.md`.*

---

## PRE-GAME – The Briefing

*Before the briefcase is even opened.*

Player receives a sealed envelope containing:
1. **Fake ID card** with codename: NOVA – field coordinator
2. **The Contract** – the mission, rules, risks. At the bottom a seemingly unrelated reference code (the WhatsApp password): **OP-0987**
3. **Earpiece** – when she puts it in, Cardinal's briefing plays

*The clock starts when the briefing ends.*

---

## ACT 1 – The Entrance (Floor 1)

**Goal:** Place the team correctly and unlock the way to Floor 2.

### What the player sees
A floor plan from above with rooms and cameras marked. Five RFID readers in the form of rooms on the plan. A red LED representing the active camera. A panel covering the way down.

### The order (must be followed)

**Step 1 – GHOST in the Lobby**
Nothing visible happens. But under the Ghost card is a note:
*"CARDINAL not responding. Emergency protocol: send password to [number]"*
The password is in the contract from the briefing – a seemingly unrelated reference code.

**Step 2 – WhatsApp confirmation**
Player sends the code. You respond as Cardinal:
*"Identity verified. Welcome to the job, Nova."*
Now the system activates – RFID starts responding to next card.

**Step 3 – WRAITH in Security Control**
The red LED camera turns off.
Cardinal: *"Camera is blind. Move."*

**Step 4 – CIRCUIT in Server Room**
A hatch opens mechanically. USB drive can be retrieved.
Panel releases – way to Floor 2 is open.

### Cardinal lines Act 1

| Situation | Cardinal says |
|-----------|---------------|
| Briefcase opens | *"Thirty years. Finally."* |
| Wrong card in wrong room | *"Why is [name] in [room]? Read the plan again."* |
| Wraith placed before Ghost | *"Ghost hasn't secured the lobby. Wraith goes nowhere."* |
| Circuit placed before Wraith | *"Circuit is on camera. Is Wraith in position or not?"* |
| All cards correct | *"Camera is blind. Move."* |

---

## ACT 2 – The Server Room (Floor 2)

**Goal:** Log in to the terminal and disable the alarm to the vault.

### What the player sees
A Raspberry Pi 3B-driven terminal with small screen. A keyboard. A covered USB port with a screw. A tool must be used.

### Sequence
1. **Find the tool** – small screwdriver hidden physically in the briefcase
2. **Unscrew the cover** over the USB port
3. **Insert the USB drive** – terminal wakes up
4. **Enter the password** – found in planning book as a seemingly unrelated note: *"Circuit's old access code: BR-4471"*
5. **Select "Disable Alarm"** in terminal menu
6. Panel releases – way to vault is open

### Cardinal lines Act 2

| Situation | Cardinal says |
|-----------|---------------|
| Terminal activates | *"You're in. Find the alarm controls."* |
| Wrong password | *"Circuit says you're looking at the right page but wrong line."* |
| Correct password | *"Alarm deactivated. You have a window. Move."* |

---

## ACT 3 – The Vault (Floor 3)

**Goal:** Crack the combination lock and take Le Cœur Bleu.

### What the player sees
A 10×10 cm plexi cover in the middle of the panel. Under it – illuminated – lies the diamond. A safe dial. An RFID reader.

### Sequence
1. **Place SPECTRE card** on RFID reader – piezo activates
2. **Find the combination** – one digit per character card back (serial number part), must be combined:
   - Ghost card back: **SN-27**-4821 → 27
   - Wraith card back: SN-**14**-7763 → 14
   - Circuit card back: SN-9-**09**-2241 → 9
3. **Turn the dial** with stethoscope: **Right 27 → Left 14 → Right 9**
4. **Three correct positions** → plexi cover opens
5. **Take the diamond**

### Cardinal lines Act 3

| Situation | Cardinal says |
|-----------|---------------|
| Without SPECTRE card | *"Who's trying to crack my vault? Get the right person."* |
| SPECTRE card placed | *"The best in Europe. Prove it."* |
| Wrong combination | *"Focus. Listen to the lock."* |
| Long pause | *"Is the clock ticking or is it just me?"* |
| Vault opens | *"Le Cœur Bleu. Your grandmother's heart. Take it home, Nova."* |
