# 🗺️ Mister CFE — Master Project Plan

> **Goal:** turn the vertical slice into a complete, fun, memorable GBC game —
> real characters, multi-scene structure, distinctive music, tight feel — and
> ship it physically on the ModRetro Chromatic.
>
> **Method:** everything is built with the existing deterministic generator
> pipeline (`tools/`) + the ModRetro Chromatic MCP (build, emulator, browser
> preview). No custom C, no engine forks. Every change is reproducible from
> source data.

---

## Status legend

| Marker | Meaning |
| --- | --- |
| ⬜ | Not started |
| 🔄 | In progress |
| ✅ | Done and verified |
| 🚧 | Blocked / needs decision |

**Last updated:** 2026-10-26 · **Cart feedback burst: speaker names + per-character voices, 24px neighbours (Emil 20px), animated storm pole per job, neighbours renamed Amara / Hiroshi / Priya / Emil; release `63c67828…` flashed, boots on the cart; hazards and tickets await Abe's choice (`docs/DESIGN_OPTIONS.md`); VERSION 0.10.0 tagged; hazards + work orders (release `f505db32…`)**

**Character names (2026-10-26, Abe: "use names from all different countries"):** Marta → **Amara** (Nigeria), Tomás → **Hiroshi** (Japan), Rosa → **Priya** (India), Kiko → **Emil** (Denmark). Only player-visible text changed; resource keys, file names, symbols and editor variable names keep the old names (`opening_marta`, `tomas.png`, `var_rosa_home_powered`…) so stable IDs hold. Older log entries below keep the names used at the time.

**Latest feedback:** Abe confirmed the Chrome preview and said the movement
prototype looks good for now. Holding Down+A can drop multiple levels; keep
this as a known defect for a later single-level descent pass. Better music is
requested **now**, not postponed to Phase 3. Telegraphed falling debris and a
new climb theme are implemented but not yet gameplay/listening accepted. Abe also
approved the visual approach below, not finished assets. M-V1 preview handoff is
now authorized and served; user permits interruptions for meaningful iteration
updates and explicitly discarded the previous movement-preview state.
On seeing the separate polished lower-climb preview he replied **“brilliant!”**
(2026-10-25). Treat this as positive browser feedback, not a timed-gust
fairness verdict, top-checkpoint completion or device approval.

**M-V1 browser feedback (2026-10-25):** Abe played the new preview and said
“wow! much better this time.” He selected the **24px electrician** as the
preferred in-game default; the 16px version remains a comparison fixture.
This is positive visual-direction feedback, **not** a report that the
entire climb or physical cartridge passed. Abe separately listened to the new
climb theme in the opening preview and said it **works well**. The 24px default
has since been verified in a fresh native ROM: size variable 0 maps to 24px,
1 to the 16px comparator;
fresh native boot displays seven objects and variable 5=0. SELECT toggles
5→7→5 visible objects / variable 1→0; B still restores power (variable 4=1).
Native ROM `build/rom/service-opening-default24.gbc` SHA-256
`fd632ba2fd3195685e81369cbb616207a288fccfd7c42cb53a97e3abbf60e360`;
all 25 focused tests pass. New browser export is separate; human re-check not yet
reported for this build.

---

## Historical baseline metrics (Phase 0, 2026-10-25 — not current Storm Climb)

| Metric | Value |
| --- | --- |
| Project health | 0 errors · 0 warnings · 0 info |
| Resource counts | 2 scenes · 39 actors · 6 triggers · 35 palettes · 52 assets · 4 variables |
| Start scene | Storm Night (PLATFORM), start `(2, 32)` |
| Build | GB Studio CLI 4.3.2 + GBDK 4.5.0, 12.2 s |
| ROM | `build/rom/mr-cfe.gbc` · 131,072 B (128 KiB; eight 16-KiB banks) · sha256 `f776e3a3…` |
| Header | Title `MRCFE`, **MBC5+RUMBLE+RAM+BATTERY**, 32 KB SRAM, GBC-only, checksums valid |
| Headless boot | PyBoy 2.7.0, CGB, frame 600 shows Storm Night start + "Move: D-pad" prompt ✓ |
| Browser preview | `http://127.0.0.1:57089/83863de94ecce88d9065f3504e2a1721eccad11af404a4fed92c36ad58e88e97/` (listening) |
| Note | Project/desktop version is 4.2.0 versus managed CLI 4.3.2; desktop app is user-managed. Keep this mismatch visible. Headless boot frame sha256 `2b8e13b3…` is our "before" reference. |

---

## How we work (standing rules)

- **Reusable MCP knowledge:** [MCP toolkit](MCP_TOOLKIT.md) documents the
  capability audit and model/tool combinations independently of this game's
  plan. Rediscover signatures in future sessions. Use it for graphics/palette,
  sprite, dialogue, collision/dependency and runtime checks—not just builds.
  Tilemap recipes are an isolated-fixture experiment before any adoption;
  never give recipes and generators ownership of the same outputs.
- **Current game acceptance:** [action-climb evidence matrix](action-climb-acceptance.md)
  replaces the superseded splice-loop test plan; keep authored, exact-ROM,
  human-browser and hardware results separate.
- **Pipeline only:** data in `tools/level.py` + sibling data modules →
  deterministic generators → `assets/` + `project/` → MCP build → headless
  emulator asserts → browser preview live check. No hand-edited generated
  artifacts.
- **MCP first:** main selects the `.gbsproj`; children use direct read-only MCP
  against that selection, with no competing project selection. Main owns shared
  build/emulator/preview operations. Browser preview stays open between iterations;
   User permits preview interruptions for meaningful updates. Still preserve
   saves/recordings and resolve unknown outcomes; interruption permission is
   not permission to discard arbitrary state or recordings.
- **Verify before building on it:** a feature is only "done" after a ROM build
  plus headless run plus a live preview check (or device capture in Phase 4).
- **Git:** local-only repo, one-line Conventional Commits
  (`feat(platformer): ...`), no AI attribution. Feature work stays in a
  worktree when it is risky or long-running (`git worktree add
  ../gb-mr-cfe-<topic> -b feat/<topic>`); merge back per
  [GIT_WORKFLOW](GIT_WORKFLOW.md). Each worktree is its own MCP project copy.
- **SemVer:** version lives in root `VERSION`. `0.x` = pre-1.0. Additive
  content → MINOR, fixes/polish → PATCH. Dev suffix stays until a release.
- **Subagents:** parallel subagents are mandatory for independent work (up to 5),
  coding tasks prefer GPT-6 Luna, falling back to Haiku 5.5; pick specialist models per
  task. Subagents must follow this plan doc and commit nothing themselves —
  review, verify, then commit.
  User requires **direct MCP** use by each child; check access first and report
  limitations honestly. Earlier children reported no bridge and remain file-only.
  All three recent improvement reviewers and both final auditors confirmed direct
  MCP use; this documentation child also used read-only `project_inspect`.
  Later access does not retroactively verify earlier children or authorize mutations.
- **User testing checkpoints:** at the end of each phase (and at any
  " playable milestone" marker), stop and hand a browser preview to the user.
  Keep the preview open; apply the user's interruption permission and report
  meaningful updates. Report progress after every work burst.

---

## Phase 0 — MCP onboarding & baseline ✅

Ground the pipeline in reality: select the project, verify toolchain, record
the starting numbers.

- ✅ `project_select` the `.gbsproj`, confirm workspace + revision
- ✅ `project_inspect`: zero-error baseline, start scene, actor/trigger counts
- ✅ `toolchain_prepare(["build", "emulator"])`
- ✅ Build ROM, open browser preview, confirm playable
- ✅ Baseline headless emulator run + retained snapshot ("before" evidence)
- ✅ Record baseline metrics (ROM size, OAM usage, warnings) below

**Playable milestone M0:** project selected, preview live, "before" snapshot
recorded.

**Exit criteria:** zero-error project, warm toolchain, preview open, baseline
documented in the progress log.

---

## Phase 1 — Gameplay redesign ✅ → prototype 🔄 *(user pivot 2026-10-25)*

User decisions (2026-10-25): **action platformer** on the kept storm/mountain/
villagers fiction, **friendly expert** difficulty, **prototype-first** process.
New verb requested and now engine-verified: **drop-through via D-pad down +
A jump** (`FEAT_PLATFORM_DROP_THROUGH`, input mode `DROP_THRU_INPUT_DOWN_JUMP_HOLD`)
— coyote time is enabled; run remains disabled (B must not gain an unreviewed role).
Full spec: [redesign-brief](redesign-brief.md).

The original splice collect/connect/cut loop is **rejected by the user — the
gameplay must be redesigned**. The old `platformer-test-plan.md` no longer
represents an acceptance target. What carries over:

**Verified engine facts (from Phase 1 probing, 2026-10-25) — valid for any
redesign:**

- Headless verification loop works: scripted buttons → variable reads via
  debug-symbol build (`rom_build captureDebugArtifacts:true` +
  `emulator_debug`), plus screen checks. First splice pickup confirmed
  headless ("Splice +1", `Splices Held` 1→2).
- A advances help dialogue. Earlier walk-speed and interaction-radius estimates
  were rough probes, not calibrated engine limits; do not use them as assertions.
- Build size: 131,072 bytes (128 KiB). Header declares MBC5+RUMBLE+RAM+BATTERY;
  this does not establish physical cartridge capabilities or verified saves.
- Two coding agents ran in parallel. Main session performed MCP verification;
  the subagents themselves could not access MCP.

- 🔄 Movement/layout prototype generated and MCP-built. Jump and Down+A descent
  verified headlessly; Abe says movement looks good for now. Full route,
  checkpoint, coyote timing, and dynamic hazard fairness remain pending.
- ✅ Capture user redesign direction — done; decisions table in
  [redesign-brief](redesign-brief.md)
- ✅ Write the new design into docs — `docs/redesign-brief.md`
- 🔄 Replace the old test plan — banner added to `platformer-test-plan.md`;
  new plan written at M-P1 acceptance

**Exit criteria:** an acceptable new core loop, designed, documented, and
prototyped in the engine.

### Historical movement prototype handoff (not full M-P1 acceptance)

- Current start: `Storm Climb`, `(2,32)`; legacy scenes retained unchanged.
- Data/generators: `tools/climb.py`, `make_climb_art.py`,
  `make_climb_scene.py`, `make_engine_fields.py`.
- Regenerate using the managed Python in this order: `make_climb_art.py` →
  `make_climb_scene.py` → `make_engine_fields.py`. Start selection is an explicit
  MCP `settings_update`, not an implicit generator side effect.
- New background matches collisions. Cross-marked tiles are **static reset
  zones**, not timed wind. Falling debris was absent from this earlier build.
- MCP validation: zero errors/warnings before start switch; ROM build passed
  with only upstream Node DEP0190 warning. ROM SHA-256:
  `c6dff89a775215200f9f1565eaf24780daeac8fbca45dc536c44797d353717c5`.
- Four focused generator tests pass (`python3 -m unittest discover -s tools
  -p test_climb.py`); regeneration is byte-identical across 14 output files.
- Recorded headless jump/landing at frame 470; Down+A frames 482–497;
  released landing at frame 505. Recording:
  `/Users/abe/src/artifacts/playtests/storm-climb-movement`, session
  `f7f11bb5ed72451fbf4e2f99778d33d3`, branch `branch-0001`.
- Browser export updated on the existing preview URL (see baseline table).
  MCP status returned **no attached players**. Serving the preview is verified;
  opening a built-in browser tab and human/browser play are **not verified**.
- User check: arrows move, Z is A/jump, Down+Z drops through a shelf.
  Test movement/descending only; placeholder visuals are not final art direction.
- This handoff predates Abe's movement feedback and the debris/music iteration
  below; its ROM, tests and browser attachment state are historical evidence.

### Current debris/music iteration — verification in progress

- **Source:** `make_climb_scene.py` adds native debris update loops: 60-frame
  harmless warning, fall 2 px per 2 frames, rest `90 + 13 * index` frames;
  collision group 1 routes contacts to checkpoint-aware respawn. Static marked
  reset zones remain; timed gusts are still pending.
- **Source/audio:** `compose_climb.py` creates an original eight-section E-minor
  theme (~51.4 s), four channels / 32 patterns. Installed `uge-builder` renders
  offline; independent `uge_report` structural validation passed. Lead uses soft
  50% duty, bass half-volume, and reduced harmony/noise. Legacy tracks unchanged.
  Final B-major backing correction is source-audited; listening acceptance is pending.
  See [music notes](music-notes.md). This latest
  user request supersedes the brief's old “new music out of scope” statement.
- **Direct read-only MCP (documentation child):** `project_inspect` confirms
  project 4.2.0, PLATFORM start `(2,32)`, 3 scenes / 44 actors / 15 triggers /
  55 assets, zero health errors/warnings/info. This is authored-source evidence only.
- **Final direct child-MCP source audits:** music audit via
  `project_inspect` / `project_inventory` / `script_inspect` confirms native asset
  resolution, 840 events, 32 patterns, four orders and fixed B-major backing.
  Hazard audit via `project_inspect` / `scene_inspect` / `graphics_analyze_scene` /
  `script_inspect` validates four debris actors, harmless 60-frame warning,
  2 px / 2-frame fall, disabled hidden/rest state, valid name references and native
  update loop. Source checks do not establish gameplay fairness.
- **Final main-session build/test evidence:** 12 tests passed; regeneration of
  23 files, including the new UGE, is byte-identical. Successful ROM:
  `build/rom/storm-climb-review.gbc`, 131,072 bytes, SHA-256
  `6f9bdec3623ff7400022d153ac5a1b9cad150356810fe40f0aa52c75009fbcd5`.
  Final music SHA-256:
  `69ae51f2f5b0101a69fa0b9c295c4bbf5eaece9326f24866ca4f0d4fec942dcf`.
- **Headless (main session):** retained PyBoy recording
  `artifacts/playtests/storm-climb-review`, session
  `aee21094966949378e966ab27d751b89`, `branch-0001`, review actions 26–62,
  frames 348–414: warning → rock → contact → return to base (player OAM x=16 at
  frame 414); checkpoint variable 0 remains 0. This does **not** prove safe-warning
  contact, full route, checkpoint behavior, coyote timing, fairness or human music acceptance.
- **Browser:** Abe played the earlier Chrome movement preview and liked movement
  for now. Main-session MCP status sees unpaused remote player
  `0f1179d6-685e-477b-9c7a-fd0756e942bb`; remote input is unavailable. This is not
  evidence that an agent attached/controlled it or that the latest build was
  played. Latest web export is staged separately at `build/web-review`, ROM SHA-256
  `ff617bab548f9200b5bbd362aef75edb8433fab0d42d9c25ee1de04b60fdcc14`;
  it is not the final native ROM identity above. Old Chrome remains unpaused and
  untouched; no handoff yet. Do not replace/reload during human play.
- **Hardware:** no verification of this iteration.

**Known defect — multi-level drop:** holding Down+A can pass through several
shelves. User permits deferring a single-level descent fix; not resolved.

**Remaining M-P1 gates:** safe-warning contact and checkpoint tests,
full-route/coyote checks, timed gust implementation/verification, current
gameplay preview and human hazard-feel. The climb theme has positive browser
listening feedback; hardware audio remains untested. Movement approval alone
is not full slice acceptance.

### Visual-production lane — approved direction, M-V1 pending 🔄

**M-V1 acceptance gate:** one polished scene + a recognizable electrician animation
set + one distinct villager + one visible power-restoration transformation.
The user must approve this playable slice **in the browser before scaling up**;
direction approval, generator output or pixel counts alone do not pass the gate.

**Proposed first composition (reference review complete):** a 160×144 cliffside
substation opening, timber service terrace, one clear onward ledge, electrician
and Marta. Cold slate/blue-violet distance contrasts with a locally restored amber
window and panel lamp. Compare 16×16 and 16×24 hero fixtures in that same scene
before choosing size. Do not disguise every greybox shelf as a cliff: catwalks
must read as drop-through and solid rock must agree with solid collisions.
Reference basis: samples 003 (grounded opening), 002 (value/material hierarchy),
005 (worker silhouette). This is the next fixture target, not approved final art.

- **World/composition:** distinct storm village, wooded cliffs, infrastructure and
  summit identities; foreground framing and distant depth, restrained weather,
  cold night contrasted with warm windows. Build actual world terrain, not repeated
  green shelves. Purpose-built bridges, poles, cables, foliage and landmarks;
  compact, readable HUD that leaves room for the world.
- **Characters:** helmet, workwear and tools read as an electrician in silhouette;
  idle/run/jump/fall/land/repair animation set. Villagers need distinct shapes,
  clothing and personalities, not just differently labelled houses.
- **References/reproducibility:** user samples are art-direction references, not
  copied pixel assets. Generators must reproduce the approved art; reproducibility
  does not substitute for artistic judgment or human review.
- **Hardware gates:** assess at native GBC 160×144; BG four colors per tile,
  sprites three opaque colors + transparency, 40 OAM objects / 10 per scanline.
  Static estimates do not establish compiled/runtime budgets: inspect compiled
  tile/palette usage and runtime OAM/scanline pressure before acceptance.

**Three parallel owned tracks** (mandatory independent subagent work, maximum five
subagents; coding only on GPT-6 Luna; each uses direct MCP):

| Track | Owned work / handoff |
| --- | --- |
| Environment | Reference/style investigation, scene composition and environment art generators; M-V1 scene and restoration states. |
| Character-animation | Electrician silhouette/animation and one distinct villager; character source/generators, not environment files. |
| Runtime-budget / integration | Readability and hardware-budget audit, integration requirements and compiled/runtime checks coordinated through main; no competing edits to the other tracks' sources. |

Main owns shared scene integration, project selection, build, emulator and preview;
resolve file ownership before edits and serialize shared-runtime checks.

**Next, in parallel:** **(A)** human debris/music review once a safe browser handoff
is possible; **(B)** reference/style investigation now, then M-V1 production.
Subsequent scene expansion is blocked on user approval of M-V1, not pixel count alone.

**M-V1 production status: candidate built/tested; human review pending.**

- Shared `tools/opening.py` owns geometry, palettes and stable IDs. Environment:
  160×144, 166 indexed tiles (157 flip-deduplicated by MCP). Three localized
  window/panel tiles use the power-swap slot. Both hero sizes, Marta, terminal,
  native repair/size-switch scripts and palette resources are integrated.
- Reproduce with managed Python:
  `tools/make_project.py opening --fixtures --verify`. Ten opening tests and
  twelve existing climb/music tests pass; all 25 opening resources regenerate
  byte-identically. Orchestrator does not change launch settings.
- Native debug ROM: `build/rom/service-opening-v2.gbc`, 131,072 bytes, SHA-256
  `713876e212352d86624c47d2e8f1d6d6b5229f01e046a0debe2ef428091e4724`.
  Initial build caught BG brightness indexing and OBJ editor-palette expansion
  bugs; both were corrected and checked in real native frames. Independent
  direct-MCP review confirmed source repairs, palette mapping and dialogue
  ≤128 px with the actual font. See reusable lessons in `MCP_TOOLKIT.md`.
- Retained recording: `artifacts/playtests/service-opening-v2`, session
  `38da1c8ae3614c7bb93f5d9a5eb8a5da`. Branch 1 actions 57–70 / frames 398–422
  cover tall-worker repair; branch 2 actions 88–101 / frames 448–472 cover small
  repair. `emulator_review` verified retained endpoints and input delivery.
- Headless verified: B changes `Service Restored` 0→1 with either hero size;
  repeat B preserves 1; SELECT toggles size and returns to the start while
  preserving restored state. Small worker walked past Marta and landed on the
  upper walk; airborne SELECT returned the tall worker safely to the floor.
  Sampled tall OAM: seven visible objects, peak five/scanline, none over limit.
  These samples do not establish whole-game performance.
- Native cold/warm frame comparison above actor height: exactly 128 window
  pixels changed, all in BG slot 3. Workwear orange is present in actual frames.
  Source repair poses now differ (18/24 pixels); an independent audit caught
  and regression tests prevent the original duplicate-pose error.
- Browser build staged separately at `build/web-opening`, ROM SHA-256
  `43aec1c44a974237177197db2da0832d434673ecffd2bbb4e1f6992677b33844`.
  User paused the old player and requested the switch. Cached export opened
  without recompilation at the new process-local URL:
  `http://127.0.0.1:57089/5c57abafec2b86fad79d4550ad2215b84dfcdbb4d7cba0f7e5cf1e8984135911/`.
  User then explicitly discarded the previous state; new preview `list_states`
  returns no saved states. No old state will be restored; unrelated recordings
  and stored project files were not deleted. Human art/music approval is pending.
- Preview controls: arrows move, A/Z jumps, B/X repairs or talks, SELECT/Shift
  compares hero size and returns home. Authored comparison (not gameplay):
  `artifacts/visual-opening/size_power_comparison.png`.
- Remaining gates: final art/interaction feel approval, actual scene
  re-entry/save persistence, broader collision/timing checks and hardware.
  Falling currently shares the jump pose; distinct fall/landing presentation
  is not implemented or claimed. The climb's multi-level drop remains deferred.

**Next playable checkpoint after 24px default:** a bounded lower-climb section,
not a full 20×36 makeover. Reuse the opening's seven-palette/night material
language without stretching its 20×18 art, and map the 24px worker into the
actual climb. Replace one lower static red-cross reset zone with a visibly
telegraphed, navigable encounter; test safe ascent/respawn plus actual OAM.
Leave eight-lane gust conversion, top checkpoint, complete route, coyote timing
and single-level drop as explicit later gates. Divide environment, character
integration and hazard/test generator ownership before parallel edits.
Do not add a service-opening → climb transition until the lower slice builds
and its entry route is tested; opening variable 4 (repair) and climb variable 0
(checkpoint) are independent authored state, not an implicit scene reload.
Initial read-only geometry audit (before correction): rows 27→24 and 21→18
had **no two-tile-wide hazard-free column supported by both shelves**. Even
after widening, test these landings in the exact ROM before claiming fairness.
First exact-ROM attempt with the tall hero exposed more overlap: the first
rock at x5 can hit even a nominal x3/4 takeoff, and the second rock at x10
blocked a jump from x9. The follow-up source widens shelves at rows 30/24/21,
shifts debris columns right (first x6, second x15) and asserts a fully supported,
two-tile hazard-free ascent in **every** gap. This correction still needs a
fresh native build/gameplay run; do not count the earlier 256-KiB ROM as proof.
Actual position trace also exposed an **unavoidable vertical squeeze** caused
by the seven un-timed instant-reset lanes: row-28 marks the right of the lower
shelf while row-25 catches the ascent near x11. Those seven trigger scripts
are now **inert**, retaining stable resources/visible storm marks for future
telegraphed versions. Only the first actor-owned gust and falling rocks cause
hazard resets in this interim climb; reactivating lanes without route tests
would regress fairness.

**Lower-climb native evidence (2026-10-25):** source regenerated with managed
Python, 23 focused climb-art/gust/source tests pass, project health 0/0.
GBC-only ROM `build/rom/lower-climb-timed-only.gbc` is 262,144 B, SHA-256
`73ef60d6b4ad9cf5249ae1d422495a47c222c6dd53124aed11a395cdcea72dbc`.
Headless PyBoy source-mode position reads (WRAM `_actors` decoded with the
installed engine's `PX_TO_SUBPX` scale) confirmed 24px worker landings at
world y232 (row30), y208 (row27), y184 (row24), y160 (row21), y136 (row18),
with explicit short A presses. An overlong jump can pass several shelves and
contact higher hazards—keep variable-height jump tuning on the feel backlog.
At world `(86.8,264)` the player remained inside gust lane 1 while its actor
collision flag was off at frames 489–534; at frame 549 the burst set collision
and the player returned to `(16,256)` (base). These native probes were not
recorded because the emulator reported retained-recording quota; preserve all
existing recordings, do not delete evidence merely to free quota. Earlier
failed attempts *are* retained under `artifacts/playtests/lower-climb-test`.
Full route, checkpoint, other gust lanes and browser/hardware feel are still
unverified. Project settings were restored to Service Opening `(1,15)` after
the temporary climb-start build/test.

**Playable lower-climb checkpoint:** user may test the separate browser export
at `http://127.0.0.1:57089/2b21374be4ac30b39a7d2e47fc92028ffc258b007bb88e0748fc2eb3580188bd/`
(process-local URL, can expire). Web ROM SHA-256 `c3370ce35214b67a3c99879560cca579c419f4f00685fc46a06ed49f3c7c08d2`,
262,144 B. The project's configured default start was then restored to the
service opening; the already-served lower-climb export remains independent.
Prompt: judge first five shelves, visibility and the first gust's warning/burst;
tap A briefly (~8 native frames), rather than holding to the upper hazards.
Remaining seven visible gust markers are harmless placeholders, not hidden
traps. Native scene analysis: 142/384 effective background tiles, four object
palette slots, static 11-OAM estimate; one boot frame observed peak 5/scanline.
The combined managed-Python suite passes **36 tests**, and all 23 climb-owned
resources regenerate byte-identically. Human browser/hardware approval pending.

### Connected arc: Service Opening → Storm Climb → Marta checkpoint 🔄

**Source (generator-owned):** `opening.py`/`make_opening_scene.py` add a
repair-gated awning exit (tiles 18–19, rows 6–9): with `Service Restored`
(var 4) = 1 it switches to Storm Climb at `(2,32)` facing right; otherwise
"No power yet. / Fix the panel." and a nudge back to (16,9).
`make_climb_scene.py` replaces the generic house icon with the M-V1 Marta
sprite (OBJ slot 1, Waiting → Powered), swaps BG slot 3 to `powered_window` at
the checkpoint (cold on every scene entry), plays `connect`, shows
"Made it, CFE! / Rest here." and redraws the HUD. `make_climb_art.py` now gives
each summit window exactly one slot-3 tile so the swap lights both windows.
Launch settings unchanged: Service Opening `(1,15)`.

**Exact-ROM defects found and fixed (native play, not source review):**
1. The first doorway trigger (rows 3–5) fired during an 8-frame jump from
   shelf 12 (head reached row 4). It is now row 3 only at the door columns
   11–13; regression test asserts an 8-frame shelf-12 apex cannot reach it.
   Residual: a ≥10-frame hold from shelf 12 at x≥75 could still touch it.
2. HUD text `%D1$0$` never read variable 0 (GB Studio strips a leading zero
   from single-digit ids); it showed `0 / 1` after checkpoint. Now `$00$`.

**Native evidence (PyBoy 2.7.0, source-debug, recorded):**
- ROM v1 `build/rom/opening-to-summit.gbc` SHA-256 `ef64f624…`, recording
  `artifacts/playtests/opening-to-summit` session `8a528f03…` (needs-review):
  found both defects; debris 4 hit on shelf 9 after checkpoint respawned the
  worker on the summit beside the door (actions 234–245, frames 1470–1516).
- ROM v2 `build/rom/opening-to-summit-v2.gbc` 262,144 B, SHA-256
  `2274855c201a177ae9ca6847d7ba271bbb74dd8985137cd6958cf15001ff8ebf`,
  recording `artifacts/playtests/opening-to-summit-v2` session `a41ba09c…`
  (passed), frames 300–1584: B repair (var4=1) → awning exit → climb entry
  (16,256) → shelves y232/208/184/160/136/112/88/64/40 with 8-frame A taps at
  x≈71/94/72 → var0 still 0 on summit at x72 → walking to door sets var0=1,
  warm windows, Marta Powered, HUD `CLIMBS 1 / 1`. OAM 6 visible, peak 4/line.
  Player position read from WRAM `_actors[0]` (0xD220, subpixel >> 5).
- One deterministic route only. Not covered natively: the unrepaired exit
  dialogue/nudge, the 16px comparator through the climb (the climb forces the
  24px sprite), re-entering the opening, lanes 2–8, coyote timing, Down+A.

**Browser:** separate export `build/web-opening-to-summit`, web ROM SHA-256
`36d3691e…`, served at a process-local URL (expires with the MCP process).
Not opened by an agent; human play/feel/audio pending. **Hardware:** none.

**Process note:** a stale ModRetro MCP server under a background
`opencode serve` held the emulator recording lease; with user approval only
that MCP child was SIGTERMed. Three parallel subagents (two Haiku 5.5 coding
workers with disjoint file ownership, one read-only route auditor) all used
direct read-only MCP; main owned selection, builds, emulator and preview.

### First repair job: Marta's line (Storm Run + Live Wire + Blackout Grid) 🔄

Game structure approved by Abe (2026-10-25): Mister CFE repairs the storm-
damaged grid household by household; each job = reach the damage, carry the
snapped cable to a junction box, power returns visibly (see
[redesign brief](redesign-brief.md) household/needs table).

**Source (generator-owned, five parallel Haiku 5.5 workers + main):**
`make_grid_sprites.py` (cable end, junction box, service gate; OBJ slot 2),
`make_climb_art.py` (snapped pole at shelf 21, cable route drawn only with
metal slot-5 colour index 1), `make_climb_scene.py` (vars 6 carrying / 7 line
live, pickup + plug scripts, hazard drop returns the cable to the pole, metal
slot 5 dead→live palette swap, door gated on the live line, fridge text,
HUD `LINE x/1 HOME x/1`), `make_opening_scene.py` (service gate Closed until
the panel repair). Shared contract in `climb.py` (DAMAGED_POLE, JUNCTION_BOX,
grid_resource_id). 82 tests; regeneration byte-identical.

**Exact-ROM defect found and fixed:** in-play dialogue was drawn behind the
16 px HUD window cutoff, so the pickup text was invisible and the script
waited for A — the game appeared frozen (`marta-line`, ROM `ac1b879f…`,
needs-review). Generator `say()` now lifts the cutoff to 150 and restores the
HUD; a regression test checks every in-play text.

**Native evidence:** ROM `build/rom/marta-line-v2.gbc`, 262,144 B, SHA-256
`a17ead019b292b9341843b4c30f6c7661bba1e0cb93e276e6b303cd1ab93c4b7`;
recording `artifacts/playtests/marta-line-v2` session `6a776744…` (passed),
frames 300–2032: gate Closed→Open on repair; B at pole sets var6=1 with
visible text; cable carried past debris 3 while its rock fell (worker at
x64.2, no contact); B at box sets var7=1, route lights cyan, HUD LINE 1/1;
summit door: "Power's back! / My fridge hums.", var0=1, HUD HOME 1/1; OAM 9
visible, peak 4/scanline. **Not exercised natively:** cable drop on a hazard
hit, "No cable yet" box text, "Still no power" door text, 16px hero, re-entry.

**Browser:** export `build/web-marta-line`, web ROM `0f4cb6ad…`, process-local
URL; human play pending. **Hardware:** none.

**Live Wire branches + re-entry (2026-10-26):** generator-owned street exit
added (`climb.STREET_EXIT` column 0, rows 30–32 → opening (16,9) facing left).
Native ROM `build/rom/live-wire-branches.gbc` SHA-256
`b187d1e4f8f7cf0446ea6f487ab196b770cf35774f0a5a9c5e7f7d89a85e57db`, recording
`artifacts/playtests/live-wire-branches` session `922212de…` (needs-review,
two branches): SELECT 16px in the opening, climb forces 24px (Abe: keep it);
debris 3 hit while carrying → var6=0, respawn START, HUD redrawn, cable back at
the pole (OAM), re-pickup works; box with no cable → "No cable yet."; door with
the line dead → "Still no power.", var0 stays 0 (debris-4 hit respawned at
START); plug → "Line is live!", second B → "Line is live."; door → fridge
payoff, var0=1, HUD 1/1; street exit → opening keeps var4/var5.
**Defect found:** the HUD's 16px scanline cutoff survived the scene switch, so
the opening's controls text and the climb's intro text on re-entry were
invisible modal boxes (input frozen until A). Fix in `make_climb_scene.py`:
the exit lifts the cutoff and hides the overlay; the intro lifts it first.
Regression tests added (84 total). Fixed ROM `build/rom/live-wire-reentry.gbc`
SHA-256 `1769ebc664a1f4ca7b041942bfcccf630d9f19ac0588e884b82f91788b24e069`,
recording `artifacts/playtests/live-wire-reentry` session `c205403e…` (passed):
texts visible both ways, re-entry resets var0/6/7, keeps var4, gate open, HUD
`LINE 0/1 HOME 0/1`. The branch checks ran on `b187d1e4…`; the fix touches only
the exit and the intro cutoff. **Browser:** `build/web-live-wire`, web ROM
`6831f908…`, process-local URL; human play pending. **Stream/hardware:** none.

---

### Second repair job: Tomás's Wind Ridge (Storm Run + Live Wire + Blackout Grid) 🔄

Contract `tools/ridge.py`; generators `make_ridge_art.py`, `make_tomas_sprites.py`,
`make_ridge_scene.py` (profile `tools/make_project.py ridge --verify`). Route:
Marta's checkpoint (var0=1) opens the summit exit (climb 17,3) → Wind Ridge
(40×18 PLATFORM) → hop the rock plateau, press B at the snapped pole → carry the
cable past one debris column and two timed gust lanes → hop onto Tomás's porch →
B at the junction box (var8, cyan route) → walk into the door (var9: warm
windows, Tomás Relieved, oxygen concentrator On, "Power's on! I can breathe.",
HUD `LINE 1/1 HOME 1/1`, respawn moves to the door). Built by three parallel
workers (art, sprites, scene) against main's contract.

**Native (exact ROM):** ridge-start test ROMs (temporary start scene, restored
afterwards). ROM `ed6995c1…`: plateau landing in the debris column and an
unreachable catwalk → debris moved to x22, catwalk removed. ROM `e05b693c…`
(recording `artifacts/playtests/wind-ridge-start-v2`, needs-review): the whole
loop passed (pickup, carry, dead-line door, Tomás talk, plug, repeat B, door
payoff). **Defect:** the concentrator lost its top half: house props, hero and
both 24px gusts shared scanlines (13 OBJs > 10). Fix: Tomás's porch step
(32–38, top row 12) lifts the props above the gust rows; budget test added.
Porch ROM `1f52dbdd…` (unrecorded: the recording quota was full even after
archiving superseded recordings): OAM peak 8/line, 0 over limit, concentrator
whole, one tap onto the porch, box and door texts correct. **Defect:** the
summit refusal looped (2-tile nudge + leftover momentum re-entered the
trigger); fixed with a 3-tile nudge before the text, test added, verified on
`65d76ea8…`. The open branch (var0=1 → ridge) is covered by tests, not by
native play. Full-arc ROM `build/rom/mr-cfe.gbc` `54570c84…`.

**Known limits:** gust start delays only offset first activation (actors run
their update scripts only on screen), so both gusts can show at once; the
debris column next to the plateau landing can catch a hero who walks off with
full momentum; no ridge→climb return exit. **Browser:** `build/web-tomas`, web
ROM `1996a02b…`; the preview server still holds the previous Live Wire view
with an unresolved browser-recording acknowledgement, so the new URL was not
opened. **Stream/hardware:** none.


---

### Third repair job: Rosa's Signal Hill (live-cable arcs) 🔄

Contract `tools/rosa.py`; generators `make_rosa_art.py`, `make_rosa_sprites.py`,
`make_rosa_scene.py` (profile `tools/make_project.py rosa --verify`), built by three
parallel workers. Route: Tomás powered (var9=1) opens the right end of his porch
(ridge trigger 38,9; text-only refusal, never a nudge) → Signal Hill (40×18) → two
one-tap rock steps to the snapped pole → carry past live wire 1, a gust, live wire 2
(arcs: 48f sparks warning, 24f arc hits, 80f rest) → porch → box (var10) → door
(var11: warm windows, Rosa Relieved, computer + router On, "Router's on! I'm online
again.", HUD `LINE 1/1 HOME 1/1`).

**Native:** hill-start test ROM `3dd78a6e…` (unrecorded; quota): full loop passed
(intro texts, both step taps, pickup, carry past wire/gust/wire, plug var10=1 with cyan
route, door payoff var11=1, OAM peak 8/line, 0 over limit). **Defect:** walking off the
upper step landed the hero over wire 1 (x138, box to x152 vs lane x144; holding right
lands up to 42px past the edge, `c2aeecad…`). Fix: steps and pole moved to x4–8 / x7, and the
contract now requires lanes ≥ 9 tiles past the upper step; verified on `089f7a44…`.
Release ROM `31fd2ac6…`; 212 tests. **Not native-verified:** the ridge→hill exit
(tests only), respawn after var11. **Art notes:** the wire's Warning sparks are faint
(few pixels); judge the telegraph in play. **Browser:** `build/web-rosa` (web ROM
`530b763a…`) on a local static server. **Stream/hardware:** none.


---

### Fourth repair job: Kiko's Pine Hollow (mixed hazards) 🔄

Contract `tools/kiko.py`; generators `make_kiko_art.py`, `make_kiko_sprites.py`,
`make_kiko_scene.py` (profile `tools/make_project.py kiko --verify`), three parallel
workers. Route: Rosa powered (var11=1) opens the right end of her porch (hill trigger
38,9; text-only refusal) → Pine Hollow (40×18) → one tap onto a long mesa with the pole
→ falling debris + a gust on the mesa → drop down → one live wire → porch → box (var12)
→ door (var13: warm windows, Kiko Relieved, stove On, "Stove's on! Soup is cooking!",
HUD `LINE 1/1 HOME 1/1`).

**Native:** hollow-start test ROM `96201faa…` (unrecorded; quota): full loop passed
(intro, step + mesa taps, pickup, debris/gust crossing, mesa drop clear of the wire,
plug var12=1 with cyan route, door var13=1, OAM peak 8/line, 0 over). The box needs the
hero right next to it (B at x243 did nothing, x≈253 worked). The worker's box script had
no empty-hands hint; added "No cable yet." for consistency. **Also fixed:** Signal Hill's
pole art was hardcoded at the old column 13 and clipped away after the pole moved; now
derived from the contract, with a pixel test (found by the Kiko art worker). Release ROM
`15e1c3ed…`; 285 tests. **Art notes:** Kiko and the stove are crude (blink frame reads
like a visor; stove steam faint). **Not native-verified:** Signal Hill→Pine Hollow exit
(tests only), respawn after var13. **Browser:** `build/web-kiko` (web ROM `72bf2761…`)
in the MCP web preview. **Stream/hardware:** none.


---

## Phase 2 — Pipeline hardening ⬜

Proposed hardening, not mandatory busywork before the next playable iteration.
Adopt extractions only where they reduce current duplication or iteration risk.

- ⬜ Consider extracting shared music data → `tools/melody.py` if useful;
  legacy `compose_music.py` emits JSON and needs external `uge-builder` to render
  UGE, not a pure-Python binary writer. Keep the new climb pipeline distinct.
- ⬜ Extract character/sprite data → `tools/characters.py` consumed by
  `make_sprites.py`
- ✅ Add `tools/make_project.py` with explicit `opening`/`climb` profiles;
  opening profile generation/fixtures/tests verified. Music rendering is an
  explicit offline `--render-music` option; legacy generators are excluded.
- ✅ Opening profile: 25 resources regenerate byte-identically; MCP refresh,
  ROM/web build and focused tests pass. This is not proof for every legacy asset.

**Proposed exit criteria:** agreed hardening scope, deterministic output and a
measurably faster iteration loop; a refactor alone is not a playable milestone.

---

## Phase 3 — Full game content ⬜

**Provisional backlog under the action-platformer redesign**, not frozen scope
or a required sequence. Re-scope generators, NPC/checkpoint roles, ending and
milestones after M-P1 acceptance; do not restore the rejected splice loop.
Climb music is already being improved in Phase 1, not gated on item 3.6.
Scene expansion additionally requires **M-V1 browser approval**; the distinct
village/cliffs/infrastructure/summit identities are direction, not a frozen scene count.

| # | Feature | Generator surface | Status |
| --- | --- | --- | --- |
| 3.1 | Title screen + storm intro vignette | `tools/intro.py` + `make_intro_{art,sprites,scene}.py`; owns the settings start scene | 🔄 native-verified, human verdict pending |
| 3.2 | Resident NPCs on level, animated, power-gated dialogue | `characters.py` → `make_sprites.py` | ⬜ |
| 3.3 | Climb split into 2–3 linked areas | `level.py` areas support in `make_scene.py` | ⬜ |
| 3.4 | Ending scene: night→dawn, five homes lit, celebration | palettes via `make_art.py`, new scene | ⬜ |
| 3.5 | Feel & juice: coyote time, jump frames, sparkles, window glow | `level.py` tuning, sprite frames, palette flips | ⬜ |
| 3.6 | Memorable themes: title, village stages, character leitmotifs | `melody.py` → `compose_music.py` | ⬜ |

**Provisional playable milestone M1** (after 3.1 + 3.2): user does a full browser playtest
of the new openings and NPCs.

**Provisional playable milestone M2** (after 3.3 + 3.5): user plays the multi-area climb.

**Proposed exit criteria:** title → intro → climb (multi-area) → ending complete in one
run; music changes with progression; every new fixture verified headless +
live.

---

## Phase 4 — Hardware readiness ⬜

- ⬜ `device_capture` session: real-screen readability, audio loudness/taste
- ⬜ Cart settings sanity (mbc5, battery), ROM budget check vs baseline
- ⬜ Full manual playthrough of final build against the (renamed) full-game
  test plan
- ⬜ Bump `VERSION`, Conventional-Commit release, local annotated tag per
  [GIT_WORKFLOW](GIT_WORKFLOW.md)

**Exit criteria:** master game you would hand to the Chromatic cart.

---

## Progress log

Keep entries newest-first, one per work burst, with build/test evidence.

| Date | Phase | Done | Evidence / notes |
| --- | --- | --- | --- |
| 2026-10-26 | Flash v0.10.2 | Abe: "flash". VERSION 0.10.2 (title tag), tag `v0.10.2`: the attract loop on the cart. | Release `86d3d954…`; 389 tests. Flashed (request `flash-mrcfe-86d3d954-2026-10-26-a`, vendor success in 24.5 s, process closed). Cart play pending. |
| 2026-10-26 | v0.10.1 flash + attract loop | Abe: "dialogs are back, good job!" (B-12 closed) and "let's flash the cart, so I can test voices, Hazards and tickets". VERSION 0.10.1 (title tag), tag `v0.10.1`, flashed. Then Abe: "the intro should 'loop' the storm cinematic": the title now blinks PRESS START 15 times (15 s) and, if START isn't pressed, fades back into the story, which returns to the title (`intro.TITLE_IDLE_BLINKS`, unrolled in the title thread). | Flashed `31110ef7…` (request `flash-mrcfe-31110ef7-2026-10-26-a`, vendor success in 26.7 s, process closed); cart play pending. Attract loop on test ROM `1584e27f…` (source debug): title at f3000 → story at f4000 with captions → title at f5760 → START → Service Opening. 389 tests. Loop not yet flashed; Abe confirmed the reading: "yes, idle replay". |
| 2026-10-26 | Pine Hollow gap + name fix | HANDOFF item 0 follow-up. Pine Hollow's gust moved from x15–17 to x16–18 so the hidden cable (x11–12) leaves the three standing tiles the contract asks for; the gap check now counts hidden cables. Native play found the entry caption still said "Kiko's house" (B-14); fixed with a scene-wide old-name guard test. VERSION unchanged (0.10.0); bump + title tag when Abe wants the next flash. | Test ROM `45440321…` (start = Pine Hollow mesa 9,8): gust at tile 16, cable at 11 (WRAM); hero at x≈107 px held for 600 frames, no respawn; overshoot to 17.5 tiles respawns as designed. 388 tests. Release `a3f5bba4…` (start = logo), not flashed. |
| 2026-10-26 | Release v0.10.0 | Abe streamed `2625c15d…` (300 s, Player 01, saves off), then asked: "tag, commit and flash". VERSION 0.10.0 (title tag regenerated), tag `v0.10.0`. | Release `f505db32…` (same sources as `2625c15d…` plus the title version tag); 387 tests. Stream `stream-mrcfe-2625c15d-2026-10-26-a` ran 300 s (1 audio underrun). Flashed `f505db32…` (request `flash-mrcfe-f505db32-2026-10-26-a`, vendor success in 28.0 s, process closed). Cart play pending. |
| 2026-10-26 | Hazards + work orders (#2, #3) | Abe: "do #2 and 3" (the recommended options). **Hazards** (`tools/hazards.py`): falling rocks are gone. Cracked boards (climb shelves 30/27/9, Wind Ridge floor) creak for 50 frames when stood on, then give way through the group-1 respawn; hidden cables (climb shelf 18, Pine Hollow mesa) stay dark 150 frames, spark 20, arc 24. **Work orders** (`tools/tickets.py`): every job exit sets var 16 and opens the clipboard card scene (WO-0412..0415), which switches to the job; each house payoff adds a CLOSED box; Emil's porch exit leads to the storm report, then the title. **Looks**: Emil's soup bowl, Priya's headset. Five workers (3 Sonnet art, 2 Haiku plumbing; ~830k tokens total, hazard plumbing 302k/76 calls); main wrote the contracts and the exit/CLOSED integration. | Test ROM `64a1724f…` (start = work order): card WO-0412 renders and switches to Storm Climb; on board 1 var 15 = 1, it splits, the hero respawns at (2,32), var 15 clears, the board mends. 387 tests. Release `2625c15d…`, not flashed. Not yet played: the other boards, both cables, tickets 2–4, the CLOSED boxes, the report. |
| 2026-10-26 | Cable fix flashed (B-13) | Abe on the cart: the storm poles "look better", but he was stuck in the climb: no visible cable, only "No cable yet". The pole covered the cable end and took the B press; fixed in all four jobs (pole before cable, collisions off). Flashed at Abe's request ("flash it"). Hazards/tickets work (#2, #3) paused: workers were cancelled when Abe reported the bug; contracts `tools/hazards.py`, `tools/tickets.py` are drafted, uncommitted. | Test ROM `8fa0d9e0…`: "Got the cable!", var 6 = 1. Release `8d3f295e…` flashed (request `flash-mrcfe-8d3f295e-2026-10-26-a`, vendor success in 28.2 s, process closed). 346 tests. Cart replay by Abe pending. |
| 2026-10-26 | Flash v0.10.0-dev | At Abe's request ("flash it"), flashed release `63c67828…` to the cartridge on Chromatic Player 01 (bus 00 port 1) with `write-homebrew`. Abe: **"game launched fine v0.10.0-dev"** (cart). Then asked to build the recommended hazards + work-order tickets (DESIGN_OPTIONS) and the look fixes ("do #2 and 3"). | Request `flash-mrcfe-63c67828-2026-10-26-a`, operation `ec319baa…`: vendor success in 24.3 s, process closed. |
| 2026-10-26 | Cart feedback: names, voices, sizes, poles | HANDOFF items 2–5 plus two mid-session requests. **Speakers:** `tools/voices.py` names each character's box on its own line ("Hiroshi:") and switches the typed-character blip to that character's pitch (Amara 660, Hiroshi 440, Priya 990, Emil 1320 Hz; narrator 880), restoring the narrator blip after. **Sizes:** four parallel Sonnet art workers grew Amara, Hiroshi and Priya to 24px and Emil (a kid) to 20px on 16x32 canvases; one revision made Hiroshi bald with a moustache because his outline read as Priya's long hair. **Poles:** every job's BG pole stub is gone; the intro's `intro_pole` actor shows Snapped (sparking) until the junction box makes the line live, then Standing. Its palette moved to OBJ slot 7 (the only slot free in every job scene); a Haiku worker did climb + ridge and stopped on the arc/pole slot-3 clash, main finished Signal Hill and Pine Hollow. **Rename:** Abe asked for names from different countries (see the note at the top). **Intro dialogue (Abe: "we are missing the dialogs from the intro too")**: all nine story captions render natively on `634ecdb6…` (frames 300–2420); not reproduced — see BUGS B-12. Design options for hazards (item 6) and tickets (item 7) written to `docs/DESIGN_OPTIONS.md`. VERSION 0.10.0-dev. | Test ROM `bf8bdb7c…` (Wind Ridge porch start): 24px Hiroshi beside the hero, narrator boxes intact, OAM peak 8/10, 0 over-limit lines. Release `63c67828…` (start = logo; same sources as the natively checked `634ecdb6…` plus the v0.10.0-dev title tag). 344 tests. `graphics_analyze_scene`: Signal Hill static max 7/line, OAM est. 23/40; Pine Hollow 7/line, 22/40. Worker tokens: Amara 92k, Emil 105k, Priya 109k, Hiroshi 119k (with revision), poles (Haiku) 268k / 69 tool calls. Not flashed; human/browser/cart verdicts pending. |
| 2026-10-26 | Cart test: porch-exit fix | Abe played the flashed cart: "the game booted fine". Bug: after Tomás's house, nothing led to Signal Hill (so Pine Hollow was untestable). Cause: at the right wall the hero overlaps both the door trigger (x35–37) and the porch exit (x38); the engine fires only the first trigger, the door. Fix: exits sort before doors on Tomás's and Rosa's porches; regression test. (A first guess, solid porch props, was wrong and reverted.) | Test ROM `bd8d0559…` (porch start, unrecorded): walking right now fires the exit ("Power Tomas's house first." while unpowered); powered branch unit-tested. Release `9c776c6d…`; 334 tests. Flashed to the cart (request `flash-mrcfe-9c776c6d-2026-10-26-a`, vendor success in 24.5 s, process closed); not committed. |
| 2026-10-26 | First cartridge flash | Third stream (`6bfec7b4…`, 300 s, vendor success): Abe: **"good!"** (Chromatic stream). Then, with Abe's explicit consent to cartridge data loss ("yes, flash it"), flashed ROM `6bfec7b4…` (256 KiB) to the cartridge on Chromatic Player 01 (bus 02 port 1) with `write-homebrew`. | Request `flash-mrcfe-6bfec7b4-2026-10-26-a`, operation `50a39acf…`: vendor success in 25.0 s, process closed. Manual boot/play on the cartridge not yet confirmed by Abe. Build not yet committed. |
| 2026-10-26 | Intro: theme B, poles, storm, copyright | Second stream (`b0ee52a6…`, 300 s, vendor success). Abe chose **theme B** (A and C kept on disk; audition off). Added: three power poles (one right of each house; all snap, struck pole first), a double lightning strike with heavier shake and five thunder claps (built-in crash, 0.5–1.5 s), a ninth caption shot "No WiFi or modem. / No internet!", and "©2026 ABE'S GAMES" on the title (title tile budget 256 of the CGB 384). Two of my earlier fixes were wrong and are reverted/corrected: the MCP OAM view reports screen pixels (no +8/+16), so the actor offset conversion was bogus and pushed actors under the caption band; and GB Studio sprite tile y counts up from the canvas bottom, so every 32 px intro sprite had swapped halves (now a regression test against worker24). | ROM `6bfec7b4…`: poles, bolt, hero render correctly in native frames; 333 tests. Device stream of this ROM pending. |
| 2026-10-26 | Intro music + dialogue voice | Chromatic stream of ROM `ef7badcf…` (180 s, Player 01, saves off; vendor success, process closed): Abe: **"amazing!"** (Chromatic stream, host-emulated). Then three intro-theme candidates (`tools/compose_intro.py`, offline uge-builder): A *Evening on the Hill* (D major → D minor storm, tpr 5), B *Storm Front* (driving D minor + drums, D major lift, tpr 4), C *Bring the Power Home* (C major march, A minor storm, tpr 5). The logo starts the default (A) and it plays through story and title; SELECT on the title auditions A→B→C (var 14) until Abe picks. Dialogue voice: `EVENT_TEXT_SET_SOUND_EFFECT` tone 880 Hz / 0.03 s per character, set once at boot. | ROM `b0ee52a6…`: flow intact, SELECT cycles var14 0→1→2 natively; 332 tests. Audio not judged headless: listening needs the stream or browser. |
| 2026-10-26 | Title + intro | `tools/intro.py` contract + 3 parallel workers (Sonnet art and sprites, Haiku scenes) and a read-only MCP probe worker. Flow logo → story → title → opening; the logo owns the start scene (`make_intro_scene.py --test-start` for test ROMs). Native play found and fixed five engine issues, each now a test or contract rule: text in LOGO scenes corrupts BG tiles (story → TOPDOWN); the bolt ended 24 px above the pole (moved down); the hero is a fixed-type `intro_hero` sprite from worker24's pixels (actors pick slots by facing); the caption overlay survives a scene switch (hidden on exit); title text is baked art with a palette-swap blink; scene start scripts are VM-locked, so A/START never fired until the timelines moved into `EVENT_THREAD_START`. VERSION 0.9.0-dev. | Final ROM `ef7badcf…`: logo, all 8 shots, title blink, START → opening at (1,15) (WRAM), skip → title, natural end → title; OAM peak 8/10. 44 intro + 25 opening tests; web export `4e31d517…` built, not yet served (old Kiko listener has an UNKNOWN recording close). Worker cost: art 117k, sprites 101k, scenes 201k, MCP probe 129k, docs 81k tokens. |
| 2026-10-26 | Kiko's job | Pine Hollow built by 3 parallel workers + main contract: mesa with debris + gust, floor live wire; Rosa porch exit gated on var11. Native full loop passed; Signal Hill pole art fix; junction hint added. Next requested by Abe: title ("Abe's Games Present / Mr CFE" + SemVer) and intro cinematic. VERSION 0.8.0-dev. | ROM `96201faa…` (loop); release `15e1c3ed…`; 285 tests; web `72bf2761…` served, human play pending. |
| 2026-10-26 | Rosa browser verdict | Abe played `build/web-rosa` (web ROM `530b763a…`) in the MCP web preview (after an MCP reconnect cleared the stuck listener): **"all plays amazingly."** Positive human-browser verdict on the full arc through Rosa's job; not a hazard-fairness or hardware verdict. | Human browser report. |
| 2026-10-26 | Rosa's job | Signal Hill built by 3 parallel workers + main contract; live-cable arcs (hazard step 3); ridge porch exit gated on var9 (text-only refusal). Native play passed the full loop; caught a step landing over wire 1 → steps moved left + contract rule. VERSION 0.7.0-dev. | ROMs `3dd78a6e…` (loop), `089f7a44…` (landing fix); release `31fd2ac6…`; 212 tests; web `530b763a…` served locally, human play pending. |
| 2026-10-26 | Tomás browser verdict | Abe played `build/web-tomas` (web ROM `1996a02b…`, local static server): **"works awesome."** Positive human-browser verdict on the full arc through Tomás's job; not a hazard-fairness or hardware verdict. Next: Rosa's job (Abe's choice). | Human browser report. |
| 2026-10-26 | Chromatic stream verdict | After the 120 s host-emulated stream to Player 01, Abe: **"gameplay is awesome."** Recorded as Chromatic stream (host-emulated) feedback, not a cartridge/hardware run. Old browser preview could not close (unresolved browser-recording acknowledgement), so `build/web-tomas` was served by a plain local server for his browser check. | Human report; hardware/cartridge untested. |
| 2026-10-26 | Chromatic stream (host-emulated) | At Abe's request, streamed release ROM `54570c84…` to Chromatic Player 01 (bus 00 port 1) for 120 s, saves off. Vendor-reported success and the process closed; ~7100 frames sent; device audio underruns 0. Host emulation only: not a cartridge run, nothing written; tools send no input and capture no frames, so readability/audio on the device are Abe's to judge. | Operation `9cad638f…`, request `stream-mrcfe-54570c84-2026-10-26-a`. Hardware/cartridge still untested. |
| 2026-10-26 | Tomás's job | Wind Ridge built by 3 parallel workers + main contract; summit exit gated on var0. Native play caught a sprite-per-scanline overflow (concentrator half-drawn) → porch step, and a looping summit refusal → 3-tile nudge first; both fixed with tests. VERSION 0.6.0-dev. | ROMs `e05b693c…` (full loop), `1f52dbdd…` (porch, OAM peak 8), `65d76ea8…` (refusal); release `54570c84…`; 134 tests; web `1996a02b…` built, human play pending. |
| 2026-10-26 | Live Wire browser verdict | Abe played `build/web-live-wire` (web ROM `6831f908…`): **"I like it so far."** Positive human-browser verdict on the branch/re-entry build; not a hazard-fairness or hardware verdict. Flash deferred by Abe ("will flash later"). Tomás's job (Wind Ridge) started; contract `tools/ridge.py`. | Human browser report. |
| 2026-10-26 | Live Wire branches | All untested Live Wire branches passed natively; added street exit for re-entry; exact-ROM play found a re-entry freeze (HUD cutoff hid modal text), fixed in generator + tests and re-verified. Abe kept the 24px-only climb. Browser export served. VERSION 0.5.0-dev. | ROMs `b187d1e4…` (branches) and `1769ebc6…` (fix, passed); 84 tests; web `6831f908…`; human play pending. |
| 2026-10-25 | Marta's line feedback | Abe on the first repair job: **"I love it."** Positive direction for the combined Storm Run + Live Wire + Blackout Grid structure; not a hazard-fairness, drop-on-hit or hardware verdict. | Human reaction after the `build/web-marta-line` handoff. |
| 2026-10-25 | Marta's line | Grid-repair structure approved; first job built by five parallel workers: powered opening gate, snapped pole + carried cable, junction box lights the route, door gated on power with fridge payoff, LINE/HOME HUD. Exact-ROM play caught invisible in-play dialogue (frozen game); fixed and re-verified. VERSION 0.4.0-dev. | ROM `a17ead01…` recorded pass frames 300–2032; 82 tests; web `0f4cb6ad…`; human play pending. |
| 2026-10-25 | Connected arc | Repair-gated opening exit, Marta summit reward (warm windows, powered Marta, HUD) and checkpoint respawn. Exact-ROM play caught an early-firing trigger and a dead HUD variable token; both fixed and re-verified. VERSION 0.3.0-dev. | ROM v2 `2274855c…` recorded pass frames 300–1584; v1 `ef64f624…` respawn evidence; 51 tests; web `36d3691e…` served, human play pending. |
| 2026-10-25 | Lower-climb feedback | Abe called the playable lower-climb preview “brilliant!” Positive direction; precise hazard-fairness and full-route acceptance remain open. | Human browser reaction to `build/web-lower-climb` export. |
| 2026-10-25 | Lower-climb preview | Staged separate 256-KiB browser build for human testing, then restored project start to Service Opening. 36 focused tests pass; 23 climb resources regenerate identically. | Web `c3370ce3…`; native `73ef60d6…`; static budget 142/384 BG; no human checkpoint feedback yet. |
| 2026-10-25 | Lower climb | Corrected unfair static-lane squeeze by inerting seven un-timed triggers; native 24px route reaches row18, and first gust warning is safe before its active burst resets the player. Opening start restored. | ROM `73ef60d6…` 256 KiB; exact WRAM/frame assertions in lower-climb evidence above. Human preview and top checkpoint pending. |
| 2026-10-25 | Lower climb | Parallel direct-MCP review identified narrow edge-supported landings at rows 27→24 and 21→18. Luna integrated the 24px sprite/opening palettes into the *climb generator*; a second Luna authored a 24px-wide Warning/Burst gust sprite. Main wired lane 1's timed actor and disabled its old trigger script in generator source. **Art generator and full ROM/playtest are pending**; only 16 focused stdlib source tests + 3 gust tests pass so far. | `tools/climb.py`, `make_climb_scene.py`, `make_climb_gust.py`; no native outcome claimed. |
| 2026-10-25 | M-V1 | 24px worker now defaults on fresh boot; SELECT retains 16px comparison, repair works after toggling back. Source from direct-MCP Luna review, main exact-ROM native test, new isolated web preview. | Native `fd632ba2…`, browser `59eb4a2d…` at `http://127.0.0.1:57089/ab353aa1e1049f7ba089a0ac87744636bc43696f8428b2b57e70688806728fd7/`; 25 tests pass. |
| 2026-10-25 | Audio | Abe listened to `cfe_storm_climb` in the opening browser preview and said it works well. This closes browser listening for the current track only; device audio remains untested. | Human browser report; UGE asset/version as above. |
| 2026-10-25 | M-V1 | User liked the new browser art direction and chose 24px electrician. Parallel direct-MCP workers assigned default-size implementation and next-climb integration review. | Fresh ROM/default-boot check and user music listening still pending. |
| 2026-10-25 | M-V1 handoff | User requested preview switch; old view was paused. Cached M-V1 export opened without a build. User permits preview interruptions and explicitly discarded the previous state; new session lists no saved states. | Current listener `e2b03c3e…`; web ROM `43aec1c4…`; human review pending. |
| 2026-10-25 | M-V1 | Three parallel direct-MCP workers delivered environment, characters and native integration guidance; follow-up audits caught/fixed duplicate repair poses and native color mappings. Isolated visual candidate builds, 22 tests pass, 25 resources regenerate identically. Native repair/size/movement and sampled OAM verified; web candidate staged without interrupting Chrome. | Native ROM `713876e2…`; web ROM `43aec1c4…`; human gate remains pending. |
| 2026-10-25 | Pipeline | Inspected all 81 MCP tools and audited useful model/tool combinations; reusable guide separated from game status. Debris/theme integration committed as `d65ea1a`. | Direct capability audit plus bounded sprite, dialogue, collision and dependency probes; recipe/import/device mutations were not exercised. |
| 2026-10-25 | 1 / visual | Final debris/music source audits and retained contact→base evidence recorded; visual approach approved, M-V1 browser gate and three parallel owned tracks added. Next: safe human debris/music handoff alongside reference/style work, then M-V1 production. | Main reports 12 tests, 23 byte-identical outputs, native ROM `6f9bdec3…`, PyBoy actions 26–62 / frames 348–414; exact identities and limits above. Three improvement reviewers + two final auditors confirmed direct MCP; earlier agents remain file-only. Documentation child directly inspected project health; no selection/build/preview operations. Human acceptance and scene scaling remain gated. |
| 2026-10-25 | 1 | Abe played Chrome movement preview: good for now; multi-level Down+A drop deferred. Debris loops and original climb theme implemented, not accepted. Music is current work, not deferred. Phase 2 extraction and Phase 3 backlog clarified as proposals. | Child read-only MCP: zero health errors/warnings, Storm Climb + four debris actors. Main-session evidence: eight tests, debug ROM 131,072 B sha `9078cd2e…`, PyBoy boot frame 348. Dynamic contacts/checkpoint/fairness, listening and latest browser/hardware checks pending; preserve unpaused Chrome player. |
| 2026-10-25 | 1 | Integrated both coding-agent outputs; corrected background/collision mismatch and arrival-trigger checkpoint. Movement prototype builds; jump and Down+A descent verified in recorded PyBoy frames. Browser export updated, but no browser players attached. `VERSION` now `0.2.0-dev`; Phase 1 remains in progress. | ROM `c6dff89a…`; recording review actions 71–78, frames 482–505; dynamic hazards and full route pending. |
| 2026-10-25 | 1 | **Redesign direction locked.** Action platformer, keep fiction, friendly expert, prototype-first, Down+A drop-through verb. Engine verified: `FEAT_PLATFORM_DROP_THROUGH` + `FEAT_PLATFORM_COYOTE_TIME` + `FEAT_PLATFORM_RUN` exist and are off; drop-through input modes include `DOWN_JUMP_HOLD` (GB Studio default is `DOWN_JUMP_TAP`). Brief written: `docs/redesign-brief.md`. M-P1 slice defined (storm_climb scene, checkpoints, debris+gust hazards). Coding work dispatched to parallel GPT-6 Luna subagents on tools/ generators; MCP stays in main session. Old test plan banner-superseded. | engine source grep: drop-through modes DOWN_HOLD/DOWN_TAP/DOWN_JUMP_HOLD/DOWN_JUMP_TAP · docs/redesign-brief.md |
| 2026-10-25 | 1 | **Pivot recorded: user rejected the splice collect/connect/cut gameplay — full redesign required.** Before the pivot, pipeline verification was proven end-to-end: first pickup scripted headless with variable-level assertion (`Splices Held` 1→2, "Splice +1" on-screen). Engine facts recorded (walk ≈1 px/frame, B-interact radius, multi-page dialogue). Old test plan de-scoped. | Baseline table above · debug-symbol ROM sha `49f2adce…` |
| 2026-10-25 | 0 | **Phase 0 complete.** `project_select` + `project_inspect` (0 errors, 0 warnings; 2 scenes · 39 actors · 6 triggers). Toolchain ready (CLI 4.3.2, GBDK 4.5.0, PyBoy 2.7.0). First MCP ROM build OK: 131,072 B, MBC5+RUMBLE+RAM+BATTERY, GBC-only, headers valid. Headless CGB boot verified (Storm Night, "Move: D-pad"). Browser preview opened and left running for the user. | Baseline table above · boot frame sha256 `2b8e13b3…` |
| 2026-10-25 | Pre-0 | Plan doc created from session decisions: pure GB Studio + generators, full-game scope, memorable themes. | docs/PROJECT_PLAN.md |
| — | — | — | — |
