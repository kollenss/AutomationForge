# Diamond Heist — Audio Script & Track List
## Operation: Le Cœur Bleu

All voice lines recorded as MP3, named `0001.mp3`–`XXXX.mp3` on the DFPlayer SD card.
Duration column filled in after recording.

---

## Generation Guide

### Recommended tools

| Tool | Use | Link |
|---|---|---|
| **ElevenLabs** | All voice lines — consistent voice per character, exports MP3 | elevenlabs.io (free tier ~10 000 chars/month) |
| **NotebookLM** | Track 0010 only — natural two-voice dialogue (Ghost + Guard) | notebooklm.google.com |
| **Audacity** | Post-processing — walkie-talkie filter for Cardinal, Wraith, Circuit | audacityteam.org (free) |

### Recommended ElevenLabs voices (starting point — adjust to taste)

| Character | Voice suggestion | Style notes |
|---|---|---|
| Cardinal | **Adam** or **Antoni** | Calm, authoritative, slight gravel. Test: *"Thirty years. Finally."* |
| Ghost | **Callum** or **Charlie** | Smooth, warm, confident |
| Wraith | **Lily** or **Sarah** | Flat, clipped, military — remove warmth |
| Circuit | **Marcus** or **George** | Quick, technical energy |
| Guard | **Daniel** or **Brian** | Neutral, polite, customer service |

### Walkie-talkie filter in Audacity (Cardinal, Wraith, Circuit)

1. Open the generated MP3 in Audacity
2. **Effect → Filter Curve EQ** — cut everything below 300 Hz and above 3 000 Hz
3. **Effect → Distortion** — type: Leveller, degree: Light
4. **Effect → Compressor** — threshold −12 dB, ratio 4:1
5. Optional: add short static burst at start — **Generate → Noise** (0.1 s, amplitude 0.3)
6. Export as MP3 (File → Export → Export as MP3)

### Punctuation = pacing — copy scripts exactly as written

ElevenLabs reads punctuation as pauses and rhythm.
- `.` — short stop
- `—` — longer beat, dramatic pause
- `...` — hesitation or trailing off
- `,` — brief breath

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

## Pre-Game (0006–0007) — ⚪ Skip if tight

> 0006 är atmosfärisk men spelet fungerar utan den.
> 0007 är bakgrunden — berätta den muntligt om du inte hinner spela in.

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

## Floor 1 — The Entrance (0008–0014) — 🔴 Must have

> Track 0008 plays on `denied` from all three RFID Auth cards.
> Track 0009 plays on `out_of_order` from the Checklist.

---

**0008 — Cardinal** | Wrong card on any reader | *walkie-talkie filter*
```
What are you doing over there? Get out of there — quickly — or you will ruin the whole operation.
```

---

**0009 — Cardinal** | Right card, wrong timing | *walkie-talkie filter*
```
Stop. Do not go there. They can see you — on the monitors — from the reception. Wait for Ghost to clear it.
```

---

**0010 — Ghost + Guard** | Ghost's card accepted in Reception | *clean, in-scene — use NotebookLM*
```
Ghost: Excuse me — I was hoping you could help me reschedule a meeting with Monsieur Beaumont?
Guard: Of course, sir. Let me just open his calendar right away.
```
> Ghost is warm and unhurried. The guard suspects absolutely nothing. Two voices — use NotebookLM for natural dialogue.

---

**0011 — Wraith** | Wraith's card accepted in Surveillance Room | *light radio static*
```
Wraith in position. Uploading still image to the elevator camera feed. Stand by.
```

---

**0012 — Wraith** | After LED blinks red | *light radio static*
```
Done.
```
> One word. Completely flat. No emotion — that is correct for Wraith.

---

**0013 — Wraith** | After LED turns green | *light radio static*
```
Trying to disable the server room lock... Lock's open.
```
> Pause on the `...` — she's working while she speaks. Brief silence before "Lock's open."

---

**0014 — Circuit** | Circuit's card accepted in Server Room | *light radio static*
```
All clear. I have the key. Everyone — move to the elevator.
```

---

## Floor 2 — The Terminal (0015–0017) — 🔴 Must have

**0015 — Cardinal** | YubiKey inserted — terminal activates | *walkie-talkie filter*
```
You're in. Find the alarm controls.
```

---

**0016 — Cardinal** | Wrong password entered | *walkie-talkie filter*
```
Circuit says you're looking at the right page — but the wrong line.
```

---

**0017 — Cardinal** | Correct password — alarm deactivated | *walkie-talkie filter*
```
Alarm deactivated. You have a window. Move.
```

---

## Floor 3 — The Vault (0018–0022) — 🔴 Must have

**0018 — Cardinal** | Wrong RFID card on vault reader | *walkie-talkie filter*
```
Who's trying to crack my vault? Get the right person in there.
```

---

**0019 — Cardinal** | SPECTRE card placed | *walkie-talkie filter*
```
The best in Europe. Prove it.
```

---

**0020 — Cardinal** | Wrong combination step | *walkie-talkie filter*
```
Focus. Listen to the lock.
```

---

**0021 — Cardinal** | Long pause — inactivity | *walkie-talkie filter*
```
Is the clock ticking — or is it just me?
```

---

**0022 — Cardinal** | Vault opens — diamond revealed | *walkie-talkie filter — slower, genuine*
```
Le Cœur Bleu. Your grandmother's heart. Take it home, Nova.
```
> This is the only line where Cardinal allows himself to mean it. Slower than usual. No sarcasm.

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

## Priority

| Priority | Tracks | Reason |
|---|---|---|
| 🔴 **Must have** | 0008–0022 | Triggered by game events — silence = broken puzzle |
| 🟡 **Nice to have** | 0006 | Briefcase opens — atmospheric but skippable |
| ⚪ **Skip if tight** | 0007 | Full briefing — tell it verbally if needed |

---

## Status

| Track | Script done | Recorded | On SD card |
|---|---|---|---|
| 0001–0005 | ✅ | ✅ | ✅ |
| 0006 | ✅ | ❌ | ❌ |
| 0007 | ✅ | ❌ | ❌ |
| 0008–0022 | ✅ | ❌ | ❌ |
