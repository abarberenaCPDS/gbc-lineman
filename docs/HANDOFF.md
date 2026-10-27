# Session handoff: Mister CFE (2026-10-27) — 0.13.0-dev on `feat/wind-ridge-lines`

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

## Branch `feat/wind-ridge-lines` (VERSION `0.13.0-dev`, not merged)

Worktree `../gb-mr-cfe-wind-ridge`; main is still v0.10.3 = `stable`. `project_select` the worktree's `mr-cfe.gbsproj`
before MCP work (`.mcp.json` is copied in, gitignored). Abe on the 0.12.0-dev stream (`54e5d273…`): "good".

Done on the branch (2026-10-27, see the progress log): scene registry `tools/scenes.py` (game/lab/legacy) +
`make_release.py` (release copy without lab/legacy scenes); lab scenes `LAB_Hazard Gallery` and `LAB_Movement Room`
(`lab` profile, `--test-start <folder>`); `tools/grid_chain.py`; two-line chains on Signal Hill (vars 21-23) and Pine
Hollow (vars 24-26); B-06 box reach triggers (auto-plug on entry with the right cable); hero `Carry` pose; Priya's
glasses, Emil's bowl, Hiroshi's hose, shorter pole wire; `climb_debris` retired.

## Next, in suggested order

1. **Pine Hollow scanline budget** (`test_kiko.py` strict test is `expectedFailure`): porch 13, floor 11, mesa 12 OBJs
   per row (limit 10). Proposed: move the mesa gust so both posts fit on the mesa; then remove the `expectedFailure`.
2. **Native playtest** (MCP emulator, text-first per the skill) of the new work: both chains in both repair orders, HUD
   counts, door gating, reach triggers (B-06 from x=243), carry pose on/off, lab rooms.
3. **Whip in the hazard gallery** (skipped: its builder was mid-refactor; now reusable from `make_ridge_scene.py`).
4. **Docs:** `AGENTS.md` should mention the `lab` profile, `scenes.py` and `make_release.py`.
5. Look check on the cart: Priya's glasses, Emil's bowl, Hiroshi's hose, carry pose.
6. **Merge to main only after Abe's OK**; then release (drop `-dev`), tag, move `stable` if he approves on the cart.
   B-07 (one-shelf drop) is still not flashed; Abe should feel-test it on the cart.
Not yet played natively: Wind Ridge lines 2-3 with power, the catwalk route, the door, every span live at once.
Worktree note: the session guard rejects `cd` and `$PY` in compound commands; use small wrapper scripts with absolute paths.

Use parallel workers per the skill (art: Sonnet; plumbing: Haiku). Main selects the
project **before** spawning workers, gives plumbing workers the OBJ slot map, and
regenerates every profile + runs the full suite after they finish.
