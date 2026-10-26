# Session handoff: Mister CFE (2026-10-26) — Abe's cart feedback

Start a new session with: **"Read docs/HANDOFF.md and continue."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its progress log,
`docs/MCP_TOOLKIT.md` §5 (engine facts: VM lock + threads, LOGO text, overlay, OAM is
screen pixels, sprite tile y counts from the bottom, first-matching trigger wins) and §8
(budget, worker MCP checks). Load the `chromatic-budget-playtest` skill before emulator
work or spawning workers. VERSION `0.9.0-dev`. Local-only repo; one-line Conventional
Commits, no AI attribution.

Bugs (open and fixed, with causes and guards): `docs/BUGS.md`.

## State

- **Committed:** intro/title/music, the porch-exit fix and these docs (see `git log`).
  `project/settings.gbsres` must always start at the logo (`8f0deaff…`), never a
  `--test-start` override.
- **Release ROM** `build/rom/mr-cfe.gbc` `9c776c6d…` (porch-exit fix). The cartridge
  holds this ROM too (flashed after the fix) (flashed with Abe's consent; later writes to this device
  need no new data-loss consent, but always bind the exact ROM via `rom_inspect`).
- **Abe:** "the game booted fine" on the cart; he is playtesting. Intro theme B chosen.

## Abe's list (2026-10-26), in suggested order

1. ~~After Wind Ridge nothing leads to Signal Hill~~ **fixed** (exit before door,
   test). Flashed `9c776c6d…`; Abe to test Rosa → Kiko on the cart.
2. **Speaker names in dialogue** ("Marta:" etc.). In-play text goes through each
   job generator's `say()`; lines ≤ 17 chars, so the name likely needs its own line.
3. **Per-character voice pitch** (Abe: "later", but listed): `EVENT_TEXT_SET_SOUND_EFFECT`
   before each character's lines, back to the narrator blip (`intro.TEXT_SOUND`) after.
4. **Reuse the intro pole sprite** (`intro_pole`, Standing/Snapped) for each job's
   snapped pole: Snapped until the line is live, then Standing (payoff). Today the pole
   is background art; mind the 10-sprites-per-line budget.
5. **Bigger characters:** Marta, Tomás, Rosa, Kiko are 16px; make them 24px like the
   hero (Sonnet art workers, one per character, `sprite_inspect` on output).
6. **Hazards: replace falling rocks** with field-crew hazards Abe named (Spanish →
   English): *electrical shocks / arcing* (exists: live-wire arcs), *hidden cables*
   (buried/concealed live lines that only show briefly), *strong winds* (exists: gusts),
   *cracked wood, poles or platforms* (crumbling platforms that give way after a step).
   Debris is used in the climb, Wind Ridge and Pine Hollow. Needs a design pass with Abe.
7. **Winning as a service ticket / report:** each job starts from a ticket or work
   order (or a pre-storm prep plan) and ends with the ticket closed; a final storm report
   after Kiko (today Pine Hollow is a dead end). Needs a design pass with Abe.

Items 6–7 change the game's design: propose concrete options to Abe before building.
Items 2–5 are clear enough to build. Use parallel workers per the skill (art: Sonnet;
plumbing: Haiku), each verifying MCP access and running `graphics_analyze_scene` /
`sprite_inspect` on its own output; main owns builds, emulator, device.
