# Diamond Heist — Design Docs

This folder holds the **story and game-design bible** for *Operation: Le Cœur Bleu*
("Diamond Heist"), the first game built on the GameForge platform. Moved here from
an orphaned local folder (`C:\Dev\Diamond heist.old`, no version control) on
2026-08-31.

**Scope — deliberately story/design only.** How the game *engine* (GameForge/
PropForge) actually runs floors, nodes, relays, RFID etc. is **not** documented
here on purpose, to avoid this bible drifting out of sync with the real
architecture. For that, see:

- [`Z:\CLAUDE.md`](../../CLAUDE.md) — current platform architecture, workflow, hardware map
- [`Z:\management\GAMEFORGE.md`](../../management/GAMEFORGE.md) — GameForge engine concepts (floor apps, web app bridges, nodes)
- [`Z:\PIN_MAP.md`](../../PIN_MAP.md) — physical wiring/pinout

## Files

| File | Contents |
|------|----------|
| `STORY.md` | Story bible: background, Cardinal, the team, briefing script, contract, planning book |
| `GAMEPLAY.md` | The three acts as the player experiences them — puzzle flow, what's on each floor, Cardinal's contextual lines |
| `VISUAL-STYLE.md` | Art direction, color palette, and all image-generation prompts (character cards, floor plan, props) |
| `COMPONENTS.md` | Physical hardware/prop inventory for building the briefcase — not GameForge engine config |

## What was left out on purpose

The original folder also had a combined design document and a `CLAUDE.md` full of
implementation status (Pi file structure, relay channel bit-mapping, per-floor state
machines, Python code snippets). That's real, but it's **engine/build status, not
game design** — and it was already stale relative to the actual platform docs above.
Only the story-bible and image-prompt content unique to that combined doc was folded
into `STORY.md` / `GAMEPLAY.md` / `VISUAL-STYLE.md` here; the technical sections were
dropped rather than carried forward, so they don't quietly go stale a second time.
