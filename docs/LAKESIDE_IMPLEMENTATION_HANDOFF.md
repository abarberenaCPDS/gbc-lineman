# Lakeside baseline implementation handoff

Updated November 8, 2026. Selected by Abe; proceed with implementation, not another
three-option design round. This handoff intentionally ends planning before source
changes so a fresh session can own the complete first playable increment.

## Copy/paste prompt for a new session

```text
Continue Lineman's approved lakeside baseline implementation in
/Users/abe/src/modretro-chromatic/gb-mr-cfe-campaign-polish
on feat/terrain-design. Read AGENTS.md and docs/LAKESIDE_IMPLEMENTATION_HANDOFF.md,
then the selected variant in docs/terrain/WORLD_VARIANTS.md.

Implement in order: (1) intro mission after Press Start, (2) walkable lakeside
hub, (3) redesign the household routes. Start with a small playable intro-and-town
increment and validate it before broad route changes. The lakeside neighborhood
is selected; do not reopen the world-variant choice. Preserve jump physics,
accepted hero/art direction, four households and five repairs per main job.
Expand scene sizes only where specific gameplay beats need room.

Use parallel subagents with disjoint work: a capable economical model for narrow
source/coding/testing tasks, frontier main for design/integration/hard debugging.
Follow the budget directive in AGENTS.md. Main alone controls builds/emulators/
previews. Inspect existing generators before replacing work. Use the ModRetro
plugin skills and verify the live connection. Build and playtest through the real
opening flow, then show me the playable increment. Keep implementation and
validation evidence distinct. Do not flash the cart unless I request it again.
```

## Selected world and scope

- Fictional mountain community inspired by Big Bear: lake, pine cabins, granite
  ridges, creek gullies and utility trails. Diagram:
  `terrain/world/01-lakeside-neighborhood.png`.
- Walkable top-down town connects platforming jobs in guided progression:
  Amara/pine cabins, Hiroshi/open ridge, Priya/creek descent, Emil/lookout climb.
- Brief returns show restoration; signed trailheads lead to homes, rather than
  duplicating the same resident's house in town and in their mission.
- Intro expands existing Service Opening. Teach walking and tap/hold A safely,
  B cable pickup, B repair and visible light payoff, then one gentle wind lesson
  with safe waiting/recovery. Enter town. Tutorial repair is separate from twenty
  main-job repairs. Introduce other hazards where they first matter in missions.
- Preserve jump height, hold behavior, acceleration, braking, air control and
  collision bounds. No low ceilings added to suppress the useful jump arc.
- Difficulty comes from meaningful crossings and work destinations. Jumping past
  a hazard can be mastery; bypassing an entire irrelevant group is poor placement.
- Quiet space needs a purpose: approach, rest, recovery or view. Shorten purposeless
  travel. Priya's descent and Emil's layout are positive references.

## Should levels grow?

Selectively, yes. No blanket dimension multiplier and no extra repairs in this
pass. Existing 64x18 horizontal and 20x36 vertical scenes are starting envelopes,
not mandatory limits. Keep the intro compact (proposed 2–3-minute first attempt)
and town travel brief. Expand a mission when its route sheet cannot fit warning,
approach, crossing, safe landing/work pad and recovery with unchanged physics.
A larger rectangle by itself does not solve wasted lower routes. Distinguish map
area from unique art/tile budgets. Measure first attempt and retry travel before
adding length. Set exact dimensions after route sheets, not in advance for all jobs.

## Bounded parallel work for the next session

1. Main: inspect current source and agree interface ownership; own campaign flow,
   integration, visual review and all project/build/preview/emulator calls.
2. Economical coding agent: intro changes in its owning opening modules/tests,
   after main assigns exact files. Preserve physics and launch ownership.
3. Economical coding agent: inspect/reuse isolated hub generator/tests, implement
   agreed town behavior in those files only. No shared registry/launch edits.
4. Optional short read-only review after integration: easiest route, tutorial
   clarity, duplicate houses, HUD visibility, job gating and return-state checks.

Do not run broad permanent consultant teams. Give workers acceptance criteria,
small context and output limits. Run focused checks first, required full checks
once after integration; repeat only for changed code or unresolved failures.

## Existing source and evidence

- `tools/intro.py` owns intro flow; current logo → story → title → Service Opening.
  `make_intro_scene.py` writes launch settings. Keep shipping starts out of labs.
- `tools/opening.py` owns Service Opening geometry/palette/IDs. Follow generators;
  do not hand-edit generated scene resources or backgrounds.
- `tools/make_dispatch_hub.py` and `tools/test_dispatch_hub.py`: prepared isolated
  32x32 walkable hub source, not yet runtime accepted. It emits a diagnostic fixture
  into build/diagnostics, clones work_order and seeds progress. Do not ship fixture
  resets/seeding. Production needs clean initialization and real return wiring.
  Existing layout places four homes together; adapt to signed district departures
  without duplicating destination homes. Gates use next-job variable 16 and
  completion flags 0/9/11/13; scratch 27 is also used by interactions. Check the
  campaign contract before sharing variables with intro/checkpoint state.
  Its top-down speed setting must not leak into platformer physics.
- `tools/scenes.py` owns scene registration; main owns shared campaign wiring.
- Route sources include `tools/climb.py`, `ridge.py`, `rosa.py`, `kiko.py`.
- Existing schematic generator: `docs/terrain/world/render_world_variants.py`.
- Current branch reuses the campaign-polish worktree. Main release/tag v0.21.0
  remains separate; baseline plan commit before this handoff is 8f994d4.
- v0.21.0 was flashed successfully to Player 01; physical gameplay acceptance is
  not implied. Exact artifact/evidence: `docs/RELEASE_v0.21.0.md`.
- Historical route prototype had rejected low ceilings and remains unaccepted.
  Do not integrate it just because its tests pass.

## Verification and operational cautions

Read relevant authoring/debugging skills before implementation. Discover live MCP
signatures and select the intended worktree project. lineman-workspace previously
had an UNKNOWN preview-close failure when switching projects; verify current state
rather than claiming it persists or retrying indefinitely. The old browser preview
is a rejected route fixture, not the released full campaign. A documented official
CLI fallback exists in AGENTS.md if MCP remains unavailable.

Acceptance for first increment: real title → intro → town → first job, successful
repair and recovery, short hub navigation, directional hero, correct job gating,
return/progress lights, no HUD occlusion, no physics drift, no broken save/return
state. Verify continuation to later jobs before replacing campaign dispatch.
Report source/tests, native runtime, browser play and human acceptance separately.
No need to flash hardware for this increment unless Abe requests it.

Keep the local-only repo local; no remote changes. Preserve main's local OpenCode
config, stash, worktrees and build evidence. Use Conventional Commits; no SemVer
bump for this handoff alone. Update this handoff with each completed increment.
