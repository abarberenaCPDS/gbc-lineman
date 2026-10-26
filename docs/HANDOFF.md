# Session handoff: Mister CFE (2026-10-26) — after the cart-feedback burst

Start a new session with: **"Read docs/HANDOFF.md and continue."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its progress log,
`docs/MCP_TOOLKIT.md` §5 (engine facts, including the new OBJ palette slot map and the
stale MCP index) and §8 (budget, worker rules). Load the `chromatic-budget-playtest` skill
before emulator work or spawning workers. VERSION `0.10.0-dev`. Local-only repo; one-line
Conventional Commits, no AI attribution. Bugs: `docs/BUGS.md`.

## State

- **Committed:** speaker names + voices, 24px neighbours, animated storm poles, renamed
  neighbours, docs (see `git log`). `project/settings.gbsres` starts at the logo
  (`8f0deaff…`); never commit a `--test-start` override.
- **Release ROM** `build/rom/mr-cfe.gbc` `8d3f295e…` (v0.10.0-dev + B-13 cable fix), **flashed** 2026-10-26. Previous flash `63c67828…`: Abe "game launched fine", then got stuck (B-13, fixed). Flashing:
  later writes to that device need no new data-loss consent (given 2026-10-26), but
  always bind the exact ROM via `rom_inspect` and confirm Abe isn't mid-play.
- **Names:** Marta → **Amara** (Nigeria), Tomás → **Hiroshi** (Japan), Rosa → **Priya**
  (India), Kiko → **Emil** (Denmark). Code keys keep the old names on purpose.

## Done this burst (HANDOFF items 2–5)

2. Speaker names: `tools/voices.py`; `say(lines, key, speaker)` in each job generator.
3. Per-character voice pitch (Amara 660, Hiroshi 440, Priya 990, Emil 1320 Hz; narrator 880).
4. The intro pole sprite is each job's broken pole: Snapped → Standing when the line goes live (OBJ slot 7).
5. Bigger characters: three adults 24px, Emil 20px (a kid; easy to make 24 if Abe prefers).

## Open, in suggested order

0. **Abe asked to build #2 + #3** (recommended hazards mix + work-order tickets, and the look fixes). Contracts are drafted and uncommitted: `tools/hazards.py` (boards + hidden cables, placement, timings, event builders) and `tools/tickets.py` (work-order/report scenes, ticket text, flow). Restart the five workers from these (board sprite, ticket card art, look fixes: Sonnet; hazard wiring, ticket scenes: Haiku), then main integrates exits/closing stamps and moves the cable end one tile right of the pole only if still cluttered.

1. **B-12: Abe reported "we are missing the dialogs from the intro".** Not reproduced:
   all nine story captions render on `634ecdb6…`. Ask Abe where he saw it (cart still on
   `9c776c6d…`? browser? in-game boxes rather than story captions?). If it's on the cart,
   check whether the caption overlay color (`intro.CAPTION_OVERLAY_COLOR`, "verify in
   build") behaves differently on hardware.
2. **Flash `63c67828…`** when Abe wants it, then gather his cart verdict on names, voices,
   sizes and poles.
3. **Hazards (item 6) and tickets (item 7):** options and three questions are in
   `docs/DESIGN_OPTIONS.md`. Build only after Abe picks.
4. Look items for Abe's pass: Emil's raised bowl is thin; Priya lost her glasses, so her
   only props now are long hair and a phone; Hiroshi's tube doubles as his cane. The
   storm pole's dangling wire overlaps the cable-end sprite on the same tile.
5. Known minors: B-06 junction reach, B-07 Down+A multi-drop.

Use parallel workers per the skill (art: Sonnet; plumbing: Haiku). Main selects the
project **before** spawning workers, gives plumbing workers the OBJ slot map, and
regenerates every profile + runs the full suite after they finish.
