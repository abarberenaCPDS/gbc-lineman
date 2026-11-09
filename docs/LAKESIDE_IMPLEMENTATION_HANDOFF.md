## Training and town revision complete — November 8, 2026

✅ `0.23.0-dev` implements the cartridge feedback: richer lakeside town with
pier/boats, depot/workshop, planters, paved routes and paper work-order kiosks.
A reads the job; Accept job dispatches and Keep exploring leaves it intact.
Storm Worker now owns town side/front/back cels and intro story animation;
Neighborhood Hero stays available as an unused alternative illustration asset.
Repair animates only a valid cable connection; pickup shows Carry; Shock
explicitly resets frame/speed and restores normal animation. Training introduces
controls and optional B-at-Amara field guidance for arcs, wires, boards and gusts.
The tutorial pole stands after repair and on restored reentry; wind uses bump
recovery rather than electrical feedback. Carry pose is restored on street return.
Jump physics and household geometry remain unchanged.

✅ GB Studio canvas: opening flow across top, separate mission rows for each
household, labs beneath and legacy references last. All20 scene rectangles are
nonoverlapping. `tools/organize_world_canvas.py` applies registry positions by ID.
Legacy village motifs are reused; its old five-house mission structure and
16px player remain archived rather than reactivated. Storm Night stays as a
required generator template. No legacy scenes were deleted.

✅ Full suite564 passed, plus35 opening tests after the final Carry-reentry fix.
Official final ROM valid512KB GBC MBC5:
`build/rom/lineman-training-town-v0.23.0-dev.gbc`, SHA256
`e87bd20ee59c2c34d4e31be2ad545d86f3bfb992c306c8dfe7ac829cb5b774ed`.
Project health0/0/0. Exact final-ROM normal boot reaches Lineman Training.
The immediately preceding build (only lacking final reentry Carry restoration)
recorded real title→training→pickup→repair→field guide→town, cancel/accept→Amara.
Native isolated checks verify two Repair frames and line1 powered, and actual
arc-triggered flashing Shock frames309/319 followed by recovery. Evidence:
`build/playtests/training-town-v023`, `training-repair-check`,
`training-shock-visible`, `training-town-final-boot`. Seeded checks do not prove
an uninterrupted full campaign. No new hardware flash performed.

🔄 Final official web export: `build/web-training-town`, ROM SHA256
`70cb07dd46b7f16f8d654667f0d6dca7ba66c10256bad54fb89f8b4d0e14ebd2`.
Server runs, but Codex browser access host is unavailable; browser UI and human
acceptance of this revision remain pending. Current process-local URL:
http://127.0.0.1:63887/ccf1db1ef9ef8898e58c563705b87518ac6da303459dd872f1a68a00e6f8d52a/
Authored review sheet: `docs/review-assets/training-town/town-and-worker.png`.
Three GPT-6 Luna workers handled source audits/coding/tests; GPT-6.1 Sol handled
town art. Main integrated, reconciled editor saves, and serialized builds/play.

---

## Cartridge checkpoint — November 8, 2026

✅ User requested tag and cartridge flash. Local annotated tag `v0.22.0-dev`
points to implementation commit `710c6d3`. The exact validated ROM
`build/rom/lineman-lakeside-v0.22.0-dev.gbc` (524288 bytes, SHA256
`3eb0526113b0688a62600374195eba87f12e6115e3dfa4a64bb507541ee149cd`)
was flashed successfully to Chromatic Player 01, USB bus00/port1, using existing
explicit erase/write consent recorded in RELEASE_v0.21.0.md. Discovery had no
diagnostics. Original operation:
`baa633accebb4560b443da4c5517edbedbb651c0b791c68e88edba612905f8f4`.
Vendor reported success; write process exited0 and closed normally. Physical
boot, gameplay and audio remain unverified. Tag is local; nothing pushed.
This supersedes earlier "no flash requested" notes below.

---

## Intro/town implementation checkpoint — November 8, 2026

Resumed after the user's Wi-Fi pause. Intro/town implementation and native gates
are complete; human acceptance and final browser delivery remain open. No cloud
work, upload, push, or remote change was performed. The local-only directive
remains authoritative.

### Final resumed validation

- Final production ROM: `build/rom/lineman-lakeside-v0.22.0-dev.gbc`, SHA256
  `3eb0526113b0688a62600374195eba87f12e6115e3dfa4a64bb507541ee149cd`.
  Official build succeeds; valid 512KB GBC-only MBC5 cartridge. Strong refresh:
  health 0 errors / 0 warnings / 0 info. Logo remains the production start.
- Exact final ROM recorded in `build/playtests/lakeside-final-resume`: normal
  logo/title -> cable pickup -> repair -> intentional gust recovery -> town at
  frame1482. Correct authored directional order and centered vertical hero views
  are included; side-facing frames remain unchanged.
- Seeded completed-porch fixtures verified town returns and next departures:
  `build/playtests/lakeside-return-2-resume` -> Hiroshi briefing at frame2336;
  `lakeside-return-3-resume` -> Priya briefing at1369;
  `lakeside-return-4-resume` -> Emil briefing at957. Completed district lamps
  reflect prior flags. These are gate/return checks, not an earned full campaign.
  Nested-fixture source-debug authentication was unavailable; these runs used
  ordinary ROM mode. Final root build used authenticated source mode.
- Official final web export compiled at `build/web-lakeside-final`, ROM SHA256
  `378797cb5ec2c5d6013cb82d83b85264371c90d35fc6b85e255baa99f23e66d3`.
  Opening it failed with **Browser recording close acknowledgement is UNKNOWN**.
  Do not claim the visible preview is final or replay uncertain close actions.
  Old browser game remains paused, visibly inspected and retained in IAB tab1.
  Latest old-build snapshot at frame36019:
  `aecdb354e58b60838a86424023669f2e9379ce73c64948d7712b6a786157dc90`.
- Next: resolve plugin preview closure/reconnect, select this root, open the
  verified `build/web-lakeside-final` export with cacheOnly (no rebuild needed),
  then human-play the increment before household route redesign. No hardware
  flash requested. Full uninterrupted final campaign and save/restore acceptance
  remain open.

### Working tree and implemented increment

- Worktree `/Users/abe/src/modretro-chromatic/gb-mr-cfe-campaign-polish`, branch
  `feat/terrain-design`, VERSION `0.22.0-dev`. Implementation is ready for a local Conventional Commit.
  Started from clean tree. Do not reset the worktree.
- Opening source: `opening.py`, `make_opening_scene.py`, `test_opening.py`.
  Start (8,15), existing panel (4,15), cable (14,12), gust (12,12).
  Movement to shelf precedes explicit B pickup; carry-gated B repair consumes
  tutorial cable and lights the existing windows/gate. Gust only after repair:
  40f warning / 20f active / 60f calm. Hit returns to panel without resetting
  service4. Reentry preserves carried cable6; controls/pickup gated unrepaired.
  Scene sprite palettes5/7 use existing rain/pole palettes. Shared jump engine
  fields, platform.c overlay and accepted platform hero remain untouched.
- `make_dispatch_hub.py` now writes production town via `write_production()`;
  `make_ticket_scene.py` integrates it as stable work_order scene ID. No fixture
  seeds in production. Four signed trails use ticket16 and completion0/9/11/13;
  A shows original ticket pages, clears its input override, enters original jobs.
  Return position (15,13) in tickets.py + scene_links.py. Existing main routes
  regenerated for these return coordinates and the automatic dev HUD version.
  All four jobs retain five repairs. Emil still ends at the existing report.
- Town32x32 has solid lake, four trailheads, flag-driven lamps, directional hero,
  pines, shoreline, textured paths, utility shed with matching solid footprint.
  Art151 unique tiles. Authored preview `build/lakeside-town-authored.png`.
- Agents: three GPT-6 Luna workers (intro, town, behavior tests); one
  GPT-6.1 Sol/medium worker for bounded town visual refinement. All finished.
  Main integration caught/fixed speed-vs-animation confusion, duplicate event IDs,
  palette argument aliasing, water collision, text font omissions, and sprite
  direction assumptions. Do not reintroduce those defects.

### Verified evidence (keep scopes distinct)

- Full managed-Python suite **560 passed**, log `build/lakeside-tests-final.log`.
  Earlier single stale title-start expectation fixed to intro.OPENING_START.
- After latest directional head-art correction, focused town tests **7 passed**;
  full suite predates that small correction. No need for broad repeated audits.
- Initial exact ROM `build/rom/lineman-lakeside-increment.gbc`, SHA256
  `51c3de56a894aee82ce34e092bb21762eabc0448e2a5dece900884c7153a1d87`.
  Native recording `build/playtests/lakeside-increment-first`, session
  `4c1727c8ac5343f0b1d5c663a8105455`, branch0001. Real logo/story/title -> opening,
  B pickup at frame891 (carry6=1), repair frame1085 (service4=1,carry6=0), gust
  recovery by1279 (service stays1), held jump exits to town1482 (ticket16=1).
  Town -> Amara Storm Climb2498; first household cable2893 and repair3457
  (line40=1, count44=1, carry6=0). Native session closed and evidence retained.
- Earlier polished ROM (same path, now superseded by final build above), SHA256
  `ca8cd3f97790ab366c3df5ce860b880226b2bf2b0467770ded60bbfd09186a8f`.
  Native final recording `build/playtests/lakeside-final` repeats exact opening
  inputs successfully to town1482. Session closed. This ROM **predates the last
  front/back hero correction** below and is not fully final.
- Official web export `build/web-lakeside` built and opened in visible Codex IAB
  tab1, marked deliverable. Genuine story scene visually observed in browser.
  Browser ROM SHA256 `8a6df138df390673891693ae8e8f8517df9afae2318fd37e151914620255f837`.
  URL at pause (process-local; check status on resume):
  `http://127.0.0.1:60294/b8204d02d55acd1815fae8ec1e11daf4d293cca03367d9d3b3426bba863d6adb/`
  listener `50df41c44087385807df550d5ba2e6f0`, view
  `5fec2dfc-818a-4c48-8ce8-24a16030cbce`. No video recording was active.
  Preview captured and paused at frame13701; saved state ID
  `54ceace494d809e4392a4afa38aeb25ab2689da0a7ab1921f30203e25d077f90`.
  This state belongs only to the exact old browser ROM above.
  The web export also predates latest hero correction. Human play acceptance,
  full final campaign, save/return runtime and hardware remain unverified.
- Physics hashes pinned by tools/test_lakeside_campaign.py:
  engine_field_values.gbsres `fa83412757d818e45e05e3d27ded6740d3a02c3f6e64bff0af388a6e06138926`;
  platform.c `26feb227f341e995d6be1a3a557e621007fb6d9431935bdb44f7504b949e593b`.

### Runtime details for continuation

- Official sprite authored slots are right,left,up,down; compiler toEngineOrder
  converts to down,right,up,left. Preserve this order and accepted side frames.
- Town trail triggers: Amara x4..7/y20..21, Hiroshi x24..27/y20..21,
  Priya x4..7/y25..26, Emil x24..27/y25..26. Trigger processing needs a settled
  frame before A. Route around solid signboards; wait for dialogue typing and
  release A between pages. A outside a zone shows the assignment hint.
- Seeded return fixtures remain under `build/diagnostics/lakeside-return-{2,3,4}`.
  All diagnostics and recordings stay gitignored. Main owns builds and previews.

### Exact successful opening native input sequence

Start emulator_run at frame180, normal logo boot, then (buttons:frames):
start:1, neutral:120, start:1, neutral:90, start:1, neutral:90,
[A:1,neutral:60] x3, A:1,neutral:40, right:22,right:30,A:2,neutral:28,
A:8,neutral:30,left:3,B:1,neutral:60,A:1,left:65,left:27,B:1,neutral:100,
A:1,right:65,A+right:8,neutral:120,right:55,A+right:18,neutral:20,
right:20,neutral:90. Arrives town frame1482. Includes intentional gust recovery.

---

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
