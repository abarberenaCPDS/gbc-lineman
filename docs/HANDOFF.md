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

Done 2026-10-27 (later): Pine Hollow fits 10 OBJs per line (mesa gust dropped, T1 on the mesa; strict test passes, porch
measured 10 in OAM); gallery whip; `AGENTS.md` docs. Native: Pine house line pickup, Carry pose on/off, B-06 auto-plug
from a porch jump, chain gating (house first stays dark). Source-debug note: keep the `--test-start` settings in place
while `emulator_debug` runs (it rechecks live sources), then restore.

Native 2026-10-27 (`pine-feeder` `e29941fe…`, start = feeder pole (9,8)): feeder pickup on the mesa, walk right past the
hidden cable (inactive at that moment), T1 reach trigger auto-plugs: var 24 = 1, var 25 = 1, var 26 = 1, "Power flows
on…", stage-1 wire lit. Combined with the earlier house-line run, both Pine lines work in isolation.

1. **Native playtest, remaining:** Pine with both lines in one run, then the door (needs var 25 = 2); Signal Hill chain
   in both orders; lab rooms (gallery hazards incl. whip, movement room). Recipe: `make_intro_scene.py --test-start
   <folder> X Y right`, `rom_build` with `captureDebugArtifacts`, `emulator_run` source mode, keep the override while
   `emulator_debug` runs, restore with a plain `make_intro_scene.py`. Each scene opens with 2-3 dialogue boxes (A + ~80
   frames each). Build logs are ~15k tokens each: budget about 6 builds per session.
2. Look check on the cart: Priya's glasses, Emil's bowl, Hiroshi's hose, carry pose.
3. **Merge to main only after Abe's OK**; then release (drop `-dev`), tag, move `stable` if he approves on the cart.
   B-07 (one-shelf drop) is still not flashed; Abe should feel-test it on the cart.
Not yet played natively: Wind Ridge lines 2-3 with power, the catwalk route, the door, every span live at once.
Worktree note: the session guard rejects `cd` and `$PY` in compound commands; use small wrapper scripts with absolute paths.

Use parallel workers per the skill (art: Sonnet; plumbing: Haiku). Main selects the
project **before** spawning workers, gives plumbing workers the OBJ slot map, and
regenerates every profile + runs the full suite after they finish.
