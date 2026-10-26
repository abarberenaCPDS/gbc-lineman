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

**Last updated:** 2026-10-25 · **M-V1 candidate built and headless-tested; browser/art/music acceptance pending**

**Latest feedback:** Abe confirmed the Chrome preview and said the movement
prototype looks good for now. Holding Down+A can drop multiple levels; keep
this as a known defect for a later single-level descent pass. Better music is
requested **now**, not postponed to Phase 3. Telegraphed falling debris and a
new climb theme are implemented but not yet gameplay/listening accepted. Abe also
approved the visual approach below, not finished assets. Preserve the unpaused
Chrome preview: the latest web build is staged separately, with no safe handoff yet.

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
- **Pipeline only:** data in `tools/level.py` + sibling data modules →
  deterministic generators → `assets/` + `project/` → MCP build → headless
  emulator asserts → browser preview live check. No hand-edited generated
  artifacts.
- **MCP first:** main selects the `.gbsproj`; children use direct read-only MCP
  against that selection, with no competing project selection. Main owns shared
  build/emulator/preview operations. Browser preview stays open between iterations;
  never rebuild/reload while a human is playing.
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
  coding tasks to GPT-6 Luna only; pick specialist models per
  task. Subagents must follow this plan doc and commit nothing themselves —
  review, verify, then commit.
  User requires **direct MCP** use by each child; check access first and report
  limitations honestly. Earlier children reported no bridge and remain file-only.
  All three recent improvement reviewers and both final auditors confirmed direct
  MCP use; this documentation child also used read-only `project_inspect`.
  Later access does not retroactively verify earlier children or authorize mutations.
- **User testing checkpoints:** at the end of each phase (and at any
  " playable milestone" marker), stop and hand a browser preview to the user.
  Keep the preview open and untouched while they play. Report progress after
  every work burst.

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
full-route/coyote checks, timed gust implementation/verification, safe preview
handoff, human hazard-feel and music listening acceptance. Movement approval
alone is not full slice acceptance.

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
  Existing Chrome player remains unpaused on the old movement build; no reload
  or handoff performed. Human art/music approval is still pending.
- Preview controls: arrows move, A/Z jumps, B/X repairs or talks, SELECT/Shift
  compares hero size and returns home. Authored comparison (not gameplay):
  `artifacts/visual-opening/size_power_comparison.png`.
- Remaining gates: user art/size/feel approval, music listening, actual scene
  re-entry/save persistence, broader collision/timing checks and hardware.
  Falling currently shares the jump pose; distinct fall/landing presentation
  is not implemented or claimed. The climb's multi-level drop remains deferred.

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
| 3.1 | Title screen + storm intro vignette | `make_scene.py` new scenes, settings start switch | ⬜ |
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
