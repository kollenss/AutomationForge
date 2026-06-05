# Diamond Heist — Audio Script & Track List
## Operation: Le Cœur Bleu

All voice lines recorded as MP3, named `0001.mp3`–`XXXX.mp3` on the DFPlayer SD card.
Duration column filled in after recording.

---

## Audio Style Guide

| Speaker | Voice character | Delivery | Filter |
|---|---|---|---|
| **Cardinal** | Calm, professional, dark sarcasm. Never raises his voice. | Measured, deliberate. Pauses carry weight. | Walkie-talkie / earpiece radio static |
| **Ghost** | Smooth, charming, completely in control. The perfect cover. | Warm, confident, unhurried. | Clean — in-scene |
| **Wraith** | Former military. Terse. Every word earns its place. | Short, flat, efficient. | Light radio static — field comm |
| **Circuit** | Technical, slightly nerdy, genuinely excited by systems. | Quick, under-breath energy. | Light radio static — field comm |
| **Guard** | Polite, professional, completely unsuspecting. | Neutral customer service. | Clean — in-scene |

---

## Existing Tracks (0001–0005) — Sound Effects

| Track | Type | Description | Duration |
|---|---|---|---|
| 0001 | Sound effect | Mechanical click — combination lock step | — |
| 0002 | Sound effect | Card accepted chime | — |
| 0003 | Sound effect | Card rejected buzz | — |
| 0004 | Sound effect | Vault opening mechanism | — |
| 0005 | Sound effect | Error tone | — |

---

## Pre-Game (0006–0007)

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0006 | Cardinal | Voice line | Briefcase lid opened | *"Thirty years. Finally."* | — |
| 0007 | Cardinal | Voice line — full briefing | Earpiece inserted / game starts | See full script below ↓ | ~2–3 min |

### 0007 — Cardinal's Briefing (full script)

> *[Sound: faint static, distant city sounds, chair scraping back. Cardinal's voice — close, calm.]*
>
> "You're listening. Good. That's a good first step.
>
> My name doesn't matter. You can call me Cardinal. Everyone does.
>
> I'm going to tell you a story. A short one — we don't have time for the long version.
>
> 1987. Paris. A woman named Marguerite lost everything she owned when a man named Viktor Beaumont decided her assets were worth more in his hands than hers. He used lawyers. He used contacts. He used systems built to protect men like him.
>
> Marguerite appealed. Nothing happened.
>
> The only thing she really wanted back was a diamond. Blue. Fourteen carats. Her mother's, before that. Her grandfather's, before that. Le Cœur Bleu — the heart's stone. The family called it that for generations.
>
> Beaumont sold it within a year. Laundered it through three fake auctions. It now hangs in a private museum in the seventh arrondissement. Beaumont's museum. Built on other people's losses.
>
> Viktor Beaumont died in 2019.
>
> Le Cœur Bleu still hangs there.
>
> Marguerite was your grandmother. And you're here to take back what was always yours.
>
> [pause]
>
> I've been working on this for three years. I have a team. I have a plan. What I didn't have — until now — was the right person on the ground.
>
> That's you. You are Nova.
>
> In the briefcase in front of you is everything you need. Your team is waiting. The planning book explains how we move through the building. Read it carefully — the order is not arbitrary.
>
> One more thing.
>
> Keep the order. Trust the team. Trust Cardinal.
>
> [pause]
>
> Your grandmother deserved better.
>
> Now let's take back what she never got.
>
> The clock starts when you close this message.
>
> Welcome to the job, Nova."
>
> *[Static fades. Silence.]*

---

## Floor 1 — The Entrance (0008–0014)

### Error lines

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0008 | Cardinal | Voice line | Wrong card on any reader (`denied`) | *"What are you doing over there? Get out of there — quickly — or you will ruin the whole operation."* | — |
| 0009 | Cardinal | Voice line | Right card, wrong timing — too early (`out_of_order`) | *"Stop. Do not go there. They can see you on the monitors from the reception. Wait for Ghost to clear it."* | — |

> **Note:** Track 0008 plays on `denied` from all three RFID Auth cards.
> Track 0009 plays on `out_of_order` from the Checklist (correct card placed before its step is unlocked).

---

### Step 1 — Reception (Ghost)

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0010 | Ghost + Guard | Voice line — dialogue | Ghost's card accepted in Reception | *[Ghost, smooth and confident]* "Excuse me — I was hoping you could help me reschedule a meeting with Monsieur Beaumont?" / *[Guard, polite, unhurried]* "Of course. Let me just open his calendar right away." | — |

> **Recording note:** Two voices needed. Can be same actor with slight shift in delivery.
> Ghost is completely calm — this is routine for him. The guard suspects nothing.

---

### Step 2 — Surveillance Room (Wraith) — three sequential tracks

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0011 | Wraith | Voice line | Wraith's card accepted in Surveillance Room | *"Wraith in position. Uploading still image to the elevator camera feed. Stand by."* | — |
| 0012 | Wraith | Voice line | After LED blinks red (LED Zone `done`) | *"Done."* | — |
| 0013 | Wraith | Voice line | After LED turns green (short pause) | *"Trying to disable the server room lock... Lock's open."* | — |

> **Playback chain:** 0011 → LED blinks red → 0012 → LED blinks green → LED solid green → 0013 → Server door LED green
> **Recording note:** Wraith is terse and military. "Done." is one word, no emotion. Flat is correct.

---

### Step 3 — Server Room (Circuit)

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0014 | Circuit | Voice line | Circuit's card accepted in Server Room | *"All clear. I have the key. Everyone — move to the elevator."* | — |

---

## Floor 2 — The Terminal (0015–0017)

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0015 | Cardinal | Voice line | YubiKey inserted (terminal activates) | *"You're in. Find the alarm controls."* | — |
| 0016 | Cardinal | Voice line | Wrong password entered | *"Circuit says you're looking at the right page — but the wrong line."* | — |
| 0017 | Cardinal | Voice line | Correct password — alarm deactivated | *"Alarm deactivated. You have a window. Move."* | — |

---

## Floor 3 — The Vault (0018–0022)

| Track | Speaker | Type | Trigger | Script | Duration |
|---|---|---|---|---|---|
| 0018 | Cardinal | Voice line | Wrong RFID card on vault reader | *"Who's trying to crack my vault? Get the right person in there."* | — |
| 0019 | Cardinal | Voice line | SPECTRE card placed on vault reader | *"The best in Europe. Prove it."* | — |
| 0020 | Cardinal | Voice line | Wrong combination step | *"Focus. Listen to the lock."* | — |
| 0021 | Cardinal | Voice line | Long pause / inactivity | *"Is the clock ticking — or is it just me?"* | — |
| 0022 | Cardinal | Voice line | Vault opens — diamond revealed | *"Le Cœur Bleu. Your grandmother's heart. Take it home, Nova."* | — |

---

## Track Summary

| Track | Floor | Speaker | One-liner |
|---|---|---|---|
| 0001 | All | SFX | Click — combo lock step |
| 0002 | All | SFX | Card accepted |
| 0003 | All | SFX | Card rejected |
| 0004 | All | SFX | Vault opens |
| 0005 | All | SFX | Error tone |
| 0006 | Pre-game | Cardinal | "Thirty years. Finally." |
| 0007 | Pre-game | Cardinal | Full briefing |
| 0008 | Floor 1 | Cardinal | "What are you doing over there?" |
| 0009 | Floor 1 | Cardinal | "Stop. Do not go there." |
| 0010 | Floor 1 | Ghost + Guard | Reception dialogue |
| 0011 | Floor 1 | Wraith | "Uploading still image. Stand by." |
| 0012 | Floor 1 | Wraith | "Done." |
| 0013 | Floor 1 | Wraith | "Server room lock is open." |
| 0014 | Floor 1 | Circuit | "I have the key. Move to elevator." |
| 0015 | Floor 2 | Cardinal | "You're in. Find the alarm controls." |
| 0016 | Floor 2 | Cardinal | "Right page, wrong line." |
| 0017 | Floor 2 | Cardinal | "Alarm deactivated. Move." |
| 0018 | Floor 3 | Cardinal | "Get the right person in there." |
| 0019 | Floor 3 | Cardinal | "The best in Europe. Prove it." |
| 0020 | Floor 3 | Cardinal | "Focus. Listen to the lock." |
| 0021 | Floor 3 | Cardinal | "Is the clock ticking?" |
| 0022 | Floor 3 | Cardinal | "Take it home, Nova." |

---

## Status

| Track | Script done | Recorded | On SD card |
|---|---|---|---|
| 0001–0005 | ✅ | ✅ | ✅ |
| 0006–0022 | ✅ | ❌ | ❌ |
