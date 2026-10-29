# Session handoff: Mister CFE (2026-10-28) — 0.15.0-dev on `feat/wind-ridge-lines`

Start a new session in the worktree `../gb-mr-cfe-wind-ridge` with:
**"Read docs/HANDOFF.md and start phase 3."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its newest log rows, `docs/BUGS.md`,
`docs/MCP_TOOLKIT.md` §5 (engine facts, OBJ palette slot map) and §8 (budget, worker rules). Load the
`chromatic-budget-playtest` skill before emulator work or spawning workers. Local-only repo; one-line Conventional
Commits, no AI attribution. `project/settings.gbsres` starts at the logo (`8f0deaff…`); never commit a `--test-start`.

## State

- **Phase 3 resumed, uncommitted:** five lines and 20 actors per horizontal job, full obstacle kit,
  dual wire slots, widened 100-tile maps, updated work orders/exits. All profiles regenerated;
  474 tests now pass. VERSION is now `0.16.0-dev` in the working tree; the paused accepted preview
  still serves `0.15.0-dev`. Terra artwork and two Luna scene/test workers completed their first
  pass. Background analysis after a strong refresh: 267/81/174 effective tiles (Ridge/Hill/Pine),
  all within 384; no authored graphics diagnostics. This is not runtime OAM verification.
- **Build/runtime blockers found:** first debug build failed BankPack (`script_input_3.o`
  16438 > 16384). Splitting box scripts made debug ROM `build/rom/phase3-ridge.gbc` build
  (524288 bytes, SHA256 `af32e5a5168e185fbd70e55f2423f5e116bd714f585ed2d8285f3b954ccf7325`).
  However, native B at the feeder box did nothing: carrying var6=1, near27=101, feeder17=0
  remained unchanged. Managed GB Studio's deprecated `EVENT_ACTOR_INVOKE` resolves its call
  using `scene.actors[this.actorIndex]`, despite the player occupying index0; the target is
  shifted. **Authored fix now built:** 15 supported synchronous custom-script resources in
  `project/scripts/`, called with the five box actor bindings plus that line's pole. No actor-invoke
  events remain in the new dispatcher. Managed CLI fallback built the logo-start ROM
  `build/rom/phase3-custom-scripts.gbc`, 524288 bytes, SHA256
  `474657afb2d0b4e4a72fcc75181e22ed9332edd96c975c1113914d23d147556f`; header checksum valid.
  All eight profiles regenerated and all 474 tests pass. This exact fixed ROM has **not** been
  run or previewed; B-17 remains pending runtime verification.
  Do not compensate by passing a previous actor or patching vendor/engine code.
- **MCP disconnected during native testing:** Chromatic tools disappeared from the catalog;
  Abe needs `/mcp` to reconnect before further MCP gameplay/preview work. Last native session
  paused at frame1252 with B held. No new preview was installed. Launch settings restored to
  logo after the attempt. Recording quota refused; native checks were unrecorded (no old
  recordings removed). Confirmed pickup (var6=1), gust contact clears cable/respawns, and one
  sampled OAM peak7 / zero over-limit scanlines; not a full route or sustained OAM verdict.
- Neighbours now stand at x95, clear of box x93–94 and appliance x97–98; test talk from x96.
  Full five-column box reach must remain intact. NPC talk uses the native actor-distance
  predicate after box/pole priority, without another NPC trigger (13 triggers per scene).
- Labs now own `lab_pine_reference.png`, a fixed 40×18 crop, rather than referencing the widened
  Pine Hollow map directly. Reference scenery remains cosmetic/not collision-aligned.

### Immediate next steps after reconnecting MCP

1. Select this worktree project again and rediscover signatures. Preserve the accepted preview
   and old recordings. Inspect existing emulator/preview status before changing anything.
2. Strong refresh. Build a fresh debug test-start ROM for Wind Ridge (2,26) with the custom-script
   fix. Verify B pickup, then B plug-in (var17=1, var18=1, var20=1, var6=0). The deprecated invoke
   attempt failed here despite passing unit tests, so do not infer runtime success from build.
3. Check all-five completion gate, neighbour talk from x96, hazard respawn/checkpoints and native
   OAM on the routes, then test Signal Hill and Pine Hollow. Recording quota is full: use
   unrecorded checks unless Abe authorizes archival; do not remove old evidence.
4. Restore logo start, rerun full tests, then safely update the owned preview for Abe. No Phase 3
   changes have been committed and no new preview has been installed.
- Branch `feat/wind-ridge-lines`, VERSION **0.15.0-dev** (`a26d8cb`), not merged; main is v0.10.3 = `stable`.
  `.mcp.json` is copied into the worktree (gitignored); `project_select` the worktree's `mr-cfe.gbsproj` first.
  If the MCP is missing, Abe runs `/mcp` to reconnect.
- **Versioning (Abe):** bump VERSION per landed phase: phase 2 (`0.15.0-dev`, landed), phase 3 → `0.16.0-dev`, fixes → patch.
  Bump in its own `chore(release)` commit, regenerate every profile (HUD label + title tag read VERSION), before any
  build/stream for Abe.
- Cart: v0.10.2. Streams to Abe's Chromatic go through MCP `play` (`device` `list_devices` → `play`,
  `saveMode: none`); no stop command exists (kill the `chromatic-cli live-demo` pid if Abe says cancel).
- Names: Amara/Hiroshi/Priya/Emil on screen; code keys stay `marta`/`tomas`/`rosa`/`kiko`.

## Abe's direction for this round (2026-10-27/28, verbatim where quoted)

"our goal is to improve the gameplay with the elements we have so far."
- "lines should not be connected by just colliding with them, there should be an action" — **done (phase 1)**
- "if picked up the wrong cable, pressing a button should allow you drop the cable" — **done (phase 1)** (B away from zones)
- "we can remove the 16px worker"; "service opening: Select button doesn't really make sense" — **done (phase 1)**
- **Phase 2 (`0.15.0-dev`, done):** `grid_chain` supports 1..6 lines across two BG wire slots (`LINE_BG_SLOT_1` = 5 for stages 1..3, `LINE_BG_SLOT_2` = 6 for stages 4..6) and 2-actor lines (cable end folded into `intro_pole` states `Standing` / `Snapped+Cable` / `Snapped`; separate `cable_end` actors retired from all four job scenes). 495 tests pass.
- **Abe's verdict on 0.15.0-dev stream + web preview (2026-10-28, verbatim):**
  - **"awesome, the gameplay has improved. commit this version."**
  - **"Feedback, I like the obstacles, let's add more lines so the hero has to connect 5 before the scene is complete, have the obstacles in all scenes but the first one, increase the level of difficulty a bit."**
  - **"use subagents. balance the model the use by delegating artwork and creativity to better models and assign inexpensive models to coding-only or testing-only subagents. tokenomics is important for me. we need to have a good balance."**

## Phase 3 — rebuild the levels with 5 lines & full obstacle kit (target `0.16.0-dev`)

### 1. Level scope & line counts (per Abe's feedback above)
- **First scene (`service_opening`, M-V1):** untouched, **no obstacles** (1 terminal repair tutorial).
- **`storm_climb` (Amara, 20x36 vertical climb):** 1 line, already has obstacles (3 cracked boards, 1 hidden cable, 1 timed gust; keep `TIMED_GUST_LANE_INDICES = (0,)` per `AGENTS.md`, or add 1 more hidden cable on an upper shelf if scanlines allow).
- **Horizontal job scenes (`wind_ridge`, `signal_hill`, `pine_hollow`) — 5 lines each (`STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]`):**
  - **`wind_ridge` (100x30):** **5 lines** (`feeder`, `west`, `middle`, `east`, `house`), vars `17, 28, 19, 29, 8`. Full obstacle kit: 2 gusts, 2 fallen span arcs (`live_after` 2 and 4), 2 whip wires, 1 hidden cable, 1 cracked board = **20 actors** (2 props + 10 line actors + 8 hazard actors), **13 triggers**.
  - **`signal_hill` (widen to 100x18):** **5 lines** (`feeder`, `west`, `middle`, `east`, `house`), vars `21, 30, 31, 32, 10`. Keep B-16's feeder step/pit/ledge at `x=4..12` intact! Full obstacle kit: 2 live arcs, 1 gust, 2 fallen span arcs (`live_after` 2 and 4), 1 whip wire, 1 hidden cable, 1 cracked board = **20 actors**, **13 triggers**.
  - **`pine_hollow` (widen to 100x18):** **5 lines** (`feeder`, `west`, `middle`, `east`, `house`), vars `24, 33, 34, 35, 12`. Keep the opening mesa (`x=5..18`, pole 1 at `(9,8)`, hidden cable at `(7,11,12)`, T1 at `(16,8)`) intact! Full obstacle kit: 2 live arcs, 1 gust, 2 fallen span arcs (`live_after` 2 and 4), 1 whip wire, 1 hidden cable, 1 cracked board = **20 actors**, **13 triggers**.
- **Consistent OBJ palette slot map (0..7) across all 5-line job scenes:**
  - `0`: Hero (`opening_worker24`)
  - `1`: Neighbour (`tomas` / `rosa` / `kiko`)
  - `2`: Grid props (`grid_junction_box`, `transformer`, appliance)
  - `3`: Live arc, fallen span arc, hidden cable (`live_arc`)
  - `4`: Cracked board (`cracked_board`)
  - `5`: Gust (`climb_gust`)
  - `6`: Whipping wire (`whip_wire`)
  - `7`: Storm pole (`intro_pole`)
- **Dual wire BG palette slots (5 & 6) in `make_{ridge,rosa,kiko}_art.py`:**
  - Use `STONE` (slot 1) for all `COL_SOLID` rock tiles (including subterranean `ty > GROUND_ROW`) so BG slot 6 (`EARTH`) is freed to serve as `LINE_BG_SLOT_2 = 6` (wire stages 4–5, using `PALETTES[LINE]` ramp).
  - Stages 1–3 paint in slot 5 (`LINE_BG_SLOT = 5`, indices `[1, 3, 2]`); stages 4–5 paint in slot 6 (`LINE_BG_SLOT_2 = 6`, indices `[1, 3]`).
  - Scene generators initialize both slots via `CHAIN.chain_palette_ids(0)` in `background_palette_ids`.
- **Neighbour talk / B script rough edge:** route neighbour talk or ensure B in a box zone does not double-fire native talk (`override: True` or non-overlapping placement).

### 2. Proposed 5-line coordinates (historical planning data; contracts are authoritative)

The earlier "pre-verified" label overstated the evidence: exploratory variants were tested,
but the final set was not verified together. Recheck generated sprite/trigger budgets and
native routes. Current contracts differ below: plateau D starts at x69 so the x70 box has
supported approach space; Ridge's step is x68 only to stay clear of its gust. Signal/Pine
use step x67–68; Pine's gust is x64–66. Do not restore these historical coordinates blindly.

- **Wind Ridge (`100x30`, `GROUND_ROW = 27`, `SURFACE_STEP = 24`, `SURFACE_HIGH = 21`, `PORCH_ROW = 23`):**
  - `SOLID_BLOCKS`: `(0,0,2,26)`, `(99,99,2,26)`, `ROCK_A=(5,7,24,26)`, `STEP_A=(25,26,24,26)`, `PLATEAU_A=(27,29,21,26)`, `STEP_B=(41,42,24,26)`, `PLATEAU_B=(43,46,21,26)`, `ROCK_C=(58,60,24,26)`, `STEP_D=(68,69,24,26)`, `PLATEAU_D=(70,73,21,26)`, `PORCH=(92,98,24,26)`
  - `LEDGES`: `[(21, 47, 54)]`
  - `LINES`:
    1. `feeder`: `pole=(6,23)`, `box=(18,26)`, `checkpoint=(19,26)`, `live_var="17"`
    2. `west`: `pole=(28,20)`, `box=(38,26)`, `checkpoint=(39,26)`, `live_var="28"`
    3. `middle`: `pole=(44,20)`, `box=(55,26)`, `checkpoint=(56,26)`, `live_var="19"`
    4. `east`: `pole=(59,23)`, `box=(70,20)`, `checkpoint=(71,20)`, `live_var="29"`
    5. `house`: `pole=(73,20)`, `box=(93,23)`, `checkpoint=(92,23)`, `live_var="8"`
  - Hazards: `GUST_LANES=[(25,12,14), (25,65,67)]`, `FALLEN_SPANS=[{"columns":(47,53),"live_after":2,"arcs":[(25,51,52)],"delays":[0]}, {"columns":(82,89),"live_after":4,"arcs":[(25,84,85)],"delays":[20]}]`, `WHIP_LANES=[(19,50,51), (25,78,79)]`, `HIDDEN_CABLES["wind_ridge"]=[(25,34,35)]`, `BOARDS["wind_ridge"]=[(27,21,23)]`

- **Signal Hill (`100x18`, `GROUND_ROW = 15`, `PORCH_ROW = 11`, `MESA_ROW = 8`):**
  - `SOLID_BLOCKS`: `(0,0,2,14)`, `(99,99,2,14)`, `(4,8,12,14)`, `(6,8,9,11)`, `(92,98,12,14)`, `(11,12,12,14)`, `(28,29,12,14)`, `(30,38,9,14)`, `(51,52,12,14)`, `(53,57,9,14)`, `(58,59,12,14)`, `(68,69,12,14)`, `(70,73,9,14)`
  - `LEDGES`: `[(13, 10, 10)]`
  - `LINES`:
    1. `feeder`: `pole=(7,8)`, `box=(9,14)`, `checkpoint=(14,14)`, `live_var="21"`, `reach=(9,12,2,3)`
    2. `west`: `pole=(12,11)`, `box=(26,14)`, `checkpoint=(27,14)`, `live_var="30"`
    3. `middle`: `pole=(31,8)`, `box=(55,8)`, `checkpoint=(56,8)`, `live_var="31"`
    4. `east`: `pole=(59,11)`, `box=(70,8)`, `checkpoint=(71,8)`, `live_var="32"`
    5. `house`: `pole=(73,8)`, `box=(93,11)`, `checkpoint=(92,11)`, `live_var="10"`
  - Hazards: `ARC_LANES=[(13,17,18), (13,48,49)]`, `GUST_LANES=[(13,64,66)]`, `FALLEN_SPANS=[{"columns":(42,45),"live_after":2,"arcs":[(13,43,44)],"delays":[0]}, {"columns":(84,89),"live_after":4,"arcs":[(13,85,86)],"delays":[35]}]`, `WHIP_LANES=[(13,78,79)]`, `HIDDEN_CABLES["signal_hill"]=[(7,35,36)]`, `BOARDS["signal_hill"]=[(15,20,22)]`

- **Pine Hollow (`100x18`, `GROUND_ROW = 15`, `PORCH_ROW = 11`, `MESA_ROW = 8`):**
  - `SOLID_BLOCKS`: `(0,0,2,14)`, `(99,99,2,14)`, `(5,6,12,14)`, `(7,18,9,14)`, `(91,98,12,14)`, `(21,23,12,14)`, `(38,39,12,14)`, `(40,44,9,14)`, `(54,55,12,14)`, `(56,59,9,14)`, `(60,61,12,14)`, `(68,69,12,14)`, `(70,74,9,14)`
  - `LEDGES`: `[(9, 45, 48)]`
  - `LINES`:
    1. `feeder`: `pole=(9,8)`, `box=(16,8)`, `checkpoint=(14,8)`, `live_var="24"`
    2. `west`: `pole=(22,11)`, `box=(35,14)`, `checkpoint=(36,14)`, `live_var="33"`
    3. `middle`: `pole=(41,8)`, `box=(57,8)`, `checkpoint=(58,8)`, `live_var="34"`
    4. `east`: `pole=(61,11)`, `box=(70,8)`, `checkpoint=(71,8)`, `live_var="35"`
    5. `house`: `pole=(74,8)`, `box=(93,11)`, `checkpoint=(91,11)`, `live_var="12"`
  - Hazards: `ARC_LANES=[(13,28,29), (13,51,52)]`, `GUST_LANES=[(13,66,68)]`, `FALLEN_SPANS=[{"columns":(45,48),"live_after":2,"arcs":[(13,46,47)],"delays":[0]}, {"columns":(84,89),"live_after":4,"arcs":[(13,85,86)],"delays":[25]}]`, `WHIP_LANES=[(13,78,79)]`, `HIDDEN_CABLES["pine_hollow"]=[(7,11,12)]`, `BOARDS["pine_hollow"]=[(9,45,47)]`
  - Note: update `tickets.REPORT_EXIT = (kiko.MAP_W - 2, 9, 1, 3)` (`x=98`) and `kiko.HILL_EXIT = (rosa.MAP_W - 2, 9, 1, 3)` (`x=98`)!

### 3. Subagent & tokenomics plan for Phase 3 (mandatory)
- **Main session** writes the deterministic contracts (`tools/hazards.py`, `tools/ridge.py`, `tools/rosa.py`, `tools/kiko.py`, `tools/tickets.py`) first and runs `_self_check()` so subagents never loop on geometry mistakes.
- **Current user cap: up to 3 parallel subagents**, balancing model pricing. Group the
  following original file assignments into one art worker and two coding/test workers:
  - **Artwork / background design subagents** → `model: "openai/gpt-6.1-terra"` ($1/$5 per 1M tokens — strong creative/visual model at half the cost of Sol/Argon):
    1. `tools/make_ridge_art.py` + `tools/test_ridge_background.py`
    2. `tools/make_rosa_art.py` + `tools/test_rosa_background.py`
    3. `tools/make_kiko_art.py` + `tools/test_kiko_background.py`
  - **Coding / scene plumbing & test subagents** → `model: "openai/gpt-6-luna"` ($0.10/$0.50 per 1M tokens — ultra-low-cost coding model):
    4. `tools/make_ridge_scene.py` + `tools/test_ridge.py`
    5. `tools/make_rosa_scene.py`, `tools/make_kiko_scene.py`, `tools/test_rosa.py`, `tools/test_kiko.py`, `tools/test_tickets.py`
- After workers finish, **main** bumps `VERSION` to `0.16.0-dev`, regenerates all profiles (`intro`, `tickets`, `ridge`, `rosa`, `kiko`, `climb`, `opening`, `lab`), runs the full test suite, and updates web preview / streams at Abe's request.

## Verification recipe (native)

`make_intro_scene.py --test-start <folder> X Y right` → `rom_build` with `captureDebugArtifacts` → `emulator_run`
`debugMode: source` → keep the override while `emulator_debug` runs (it rechecks live sources) → restore with a plain
`make_intro_scene.py`. Each job scene opens with 2-3 dialogue boxes (A + ~80 frames each). Player position: WRAM
offset 4639, `[flags, x u16, y u16]`, pixels = value >> 5 (y = feet row x 8). Arcs show as OAM palette 3 objects.
Text-first; screenshots only for looks. Each `rom_build` log is ~15k tokens: budget ~6 builds per session.
