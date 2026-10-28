# Session handoff: Mister CFE (2026-10-28) — 0.14.0-dev on `feat/wind-ridge-lines`

Start a new session in the worktree `../gb-mr-cfe-wind-ridge` with:
**"Read docs/HANDOFF.md and start phase 2."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its newest log rows, `docs/BUGS.md`,
`docs/MCP_TOOLKIT.md` §5 (engine facts, OBJ palette slot map) and §8 (budget, worker rules). Load the
`chromatic-budget-playtest` skill before emulator work or spawning workers. Local-only repo; one-line Conventional
Commits, no AI attribution. `project/settings.gbsres` starts at the logo (`8f0deaff…`); never commit a `--test-start`.

## State

- Branch `feat/wind-ridge-lines`, VERSION **0.14.0-dev** (`272e6ed`), not merged; main is v0.10.3 = `stable`.
  `.mcp.json` is copied into the worktree (gitignored); `project_select` the worktree's `mr-cfe.gbsproj` first.
  If the MCP is missing, Abe runs `/mcp` to reconnect.
- **Versioning (Abe):** bump VERSION per landed phase: phase 2 → `0.15.0-dev`, phase 3 → `0.16.0-dev`, fixes → patch.
  Bump in its own `chore(release)` commit, regenerate every profile (HUD label + title tag read VERSION), before any
  build/stream for Abe.
- Cart: v0.10.2. Streams to Abe's Chromatic go through MCP `play` (rom_inspect → device list_devices → play,
  `saveMode: none`); no stop command exists (kill the `chromatic-cli live-demo` pid if Abe says cancel).
- Names: Amara/Hiroshi/Priya/Emil on screen; code keys stay `marta`/`tomas`/`rosa`/`kiko`.

## Abe's direction for this round (2026-10-27/28, verbatim where quoted)

"our goal is to improve the gameplay with the elements we have so far."
- "lines should not be connected by just colliding with them, there should be an action" — **done (phase 1)**
- "if picked up the wrong cable, pressing a button should allow you drop the cable" — **done** (B away from zones)
- "we can remove the 16px worker"; "service opening: Select button doesn't really make sense" — **done**
- "let's improve all levels: introduce more obstacles and lines broken to be connected" — phase 3
- "scenes need re-work to be improved" — phase 3
- "levels should consistently have the obstacles we've designed" — phase 3
- "we can increase the number lines to connect, difficulty, etc" — Abe chose **go past 3 lines** → phase 2 + 3
- Extras (carried-cable HUD, result card, jump-rule tests): "no extras at this time".

## How the game works now (phase 1, `723e66f`)

- **B-press model** (`tools/grid_chain.py`, mirrored for storm_climb in `make_climb_scene.py`): var **27** "Chain
  Near" = 0 none, 1..N pole zone (line number), 100+N box zone. Zone triggers set it on enter and clear it on leave
  only if it still holds their value. One B input script per job scene (`EVENT_SET_INPUT_SCRIPT`, **override off** so
  neighbours' native B talk still works): box zone → plug logic (wrong cable / no cable / lit / dark texts), pole zone
  → pickup ("Hands full!" if carrying), else carrying → drop to its pole ("Cable dropped."). Cable/box/pole actors
  have no scripts. Carry pose on pickup, Default on plug/drop/hit.
- Zones: pole `(x-1, y-2, 3, 3)`; box = `reach_rect` **5x3** (3 tiles before + the box's 2 columns) or a line's own
  `reach` (Signal Hill T1 pit `(9,12,2,3)`). The engine counts only the **first listed trigger** overlapping the hero:
  order is exit, door, boards, box zones, pole zones. Tests (`first_hit`) assert standing on every box tile resolves
  to that box. Neighbour zones were removed (they shadowed boxes).
- **Open rough edge:** with override off, B next to Hiroshi/Priya/Emil while in a box zone can also start their native
  talk. Planned fix in phase 3: route neighbour talk through the B script (override on), one action per press.
- Lines today: Storm Climb 1, Wind Ridge 3 (100x30), Signal Hill 2 (40x18), Pine Hollow 2 (40x18).
- Variables used: 0-27 (17-20 ridge, 21-23 signal, 24-26 pine, 27 near; 5 is the retired opening size var, unused).

## Phase 2 — room for more lines (target `0.15.0-dev`)

Hard limits found so far:
- **Wire colours:** wires are background art in BG palette slot `LINE_BG_SLOT` = 5 (metal), colour indices 1..3 =
  one per stage (`grid_chain.MAX_STAGES = 3`, `chain_palettes()` swaps slot 5 as the chain lights). >3 lines needs a
  **second wire slot** (e.g. stages 4-6 on another BG slot's indices 1..3, swapped together by the chain refresh).
  Check which BG slots each job scene uses (`make_*_art.py` slot maps) before picking one.
- **Actors ≤ 20 per scene.** A line costs 3 actors (pole, cable end, box). Fold the cable end into the **pole actor
  states** (e.g. `Snapped+Cable` / `Snapped` / `Standing`) → 2 per line, so 5 lines = 10 actors + neighbour + props +
  hazards. Keep existing actor/resource IDs stable where possible (the cable-end IDs can be retired).
- **10 OBJs per scanline** in every 20-tile camera window (`grid_chain.scanline_load`; the hero counts 2 OBJ
  columns x 3 rows — measured in OAM). Posts are 2x4; place them so a window never stacks too many on one row.
- **Triggers ≤ 30 per scene** (now: ridge 10, rosa 7, kiko 7). Each line adds 2 zones.
- Variables: per scene, one "live" var per line + lines-count + chain-live; allocate from **28** up.
Deliverable: `grid_chain` supports 1..6 lines (two wire slots, 2-actor lines), Wind Ridge regenerates and still
passes, tests for the new limits. No level redesign yet.

## Phase 3 — rebuild the levels (target `0.16.0-dev`)

- Proposed line counts (Abe has not objected; confirm at start): **Storm Climb 1, Signal Hill 3, Pine Hollow 4,
  Wind Ridge 5.** Wider maps where needed (Ridge is already 100x30; Signal/Pine are 40x18).
- **Consistent hazard kit on every job level:** cracked boards, hidden cables, live arcs, timed gusts, whipping
  wires, live fallen spans (arcs that go live as upstream lines are fixed — Ridge's mechanic; makes repair order a
  puzzle). Mix grows level to level.
- Neighbour talk through the B script (see rough edge above).
- Lessons to design in from the start: a 2-tile-wide pit traps the hero (B-16); boxes need open tiles in front;
  the first-overlapping-trigger rule; scanline budget per camera window; keep hazards ≥ 5 tiles from landing spots.
- Lab: give the hazard gallery / movement room their own flat backgrounds (gallery reuses Pine's art, mismatch);
  use them for test starts.
- Workers: art (backgrounds, sprites) → Agent `model: "sonnet"`; plumbing → `model: "haiku"`; ≤5 in parallel,
  disjoint file ownership per worker; main regenerates every profile and runs the full suite after they finish.

## Verification recipe (native)

`make_intro_scene.py --test-start <folder> X Y right` → `rom_build` with `captureDebugArtifacts` → `emulator_run`
`debugMode: source` → keep the override while `emulator_debug` runs (it rechecks live sources) → restore with a plain
`make_intro_scene.py`. Each job scene opens with 2-3 dialogue boxes (A + ~80 frames each). Player position: WRAM
offset 4639, `[flags, x u16, y u16]`, pixels = value >> 5 (y = feet row x 8). Arcs show as OAM palette 3 objects.
Text-first; screenshots only for looks. Each `rom_build` log is ~15k tokens: budget ~6 builds per session.
Worktree note: the session guard rejects `cd` and `$PY` in compound commands; use wrapper scripts with absolute paths
(e.g. a `py.sh` that cds to the worktree and runs the managed Python).

## Not yet played natively

Signal Hill house line + door; Wind Ridge lines 2-3 with power, catwalk, door; gallery whip; movement room. Look
check on the cart: Priya's glasses, Emil's bowl, Hiroshi's hose, carry pose. B-07 not flashed.
**Merge to main only after Abe's OK**; then release (drop `-dev`), tag, move `stable` if he approves on the cart.
