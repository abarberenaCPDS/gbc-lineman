# Session handoff: Mister CFE (2026-10-26) — v0.10.2 on the cart (attract loop)

Start a new session with: **"Read docs/HANDOFF.md and continue."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its progress log,
`docs/MCP_TOOLKIT.md` §5 (engine facts, including the new OBJ palette slot map and the
stale MCP index) and §8 (budget, worker rules). Load the `chromatic-budget-playtest` skill
before emulator work or spawning workers. VERSION `0.10.0` (tag `v0.10.0`). Local-only repo; one-line
Conventional Commits, no AI attribution. Bugs: `docs/BUGS.md`.

## State

- **Committed:** speaker names + voices, 24px neighbours, animated storm poles, renamed
  neighbours, docs (see `git log`). `project/settings.gbsres` starts at the logo
  (`8f0deaff…`); never commit a `--test-start` override.
- **Cart:** v0.10.2 `86d3d954…` flashed 2026-10-26 (attract loop + B-14/B-15 fixes + v0.10.0 hazards/tickets). Flashing:
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

0. **Cart verdict on v0.10.2:** Abe: "all looks fantastic" (overall; no per-item notes). If he reports specifics later, the open questions were board creak fairness (50 frames), hidden cables, work orders 1–4, CLOSED boxes, storm report → title. `climb_debris` sprite is unused and can be retired.
1. **Attract loop** shipped in v0.10.2 and covered by that verdict.
2. Names, sizes and poles: covered only by the overall verdict above.
3. Look items for Abe's pass: Emil's raised bowl is thin; Priya lost her glasses, so her
   only props now are long hair and a phone; Hiroshi's tube doubles as his cane. The
   storm pole's dangling wire overlaps the cable-end sprite on the same tile.
4. Known minors: B-06 junction reach, B-07 Down+A multi-drop.

Use parallel workers per the skill (art: Sonnet; plumbing: Haiku). Main selects the
project **before** spawning workers, gives plumbing workers the OBJ slot map, and
regenerates every profile + runs the full suite after they finish.
