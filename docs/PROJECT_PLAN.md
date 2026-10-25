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

**Last updated:** 2026-10-25 · **Phase 0 done · Phase 1 next**

---

## Baseline metrics (Phase 0, 2026-10-25)

| Metric | Value |
| --- | --- |
| Project health | 0 errors · 0 warnings · 0 info |
| Resource counts | 2 scenes · 39 actors · 6 triggers · 35 palettes · 52 assets · 4 variables |
| Start scene | Storm Night (PLATFORM), start `(2, 32)` |
| Build | GB Studio CLI 4.3.2 + GBDK 4.5.0, 12.2 s |
| ROM | `build/rom/mr-cfe.gbc` · 131,072 B (2 banks of 64 KB flat) · sha256 `f776e3a3…` |
| Header | Title `MRCFE`, **MBC5+RUMBLE+RAM+BATTERY**, 32 KB SRAM, GBC-only, checksums valid |
| Headless boot | PyBoy 2.7.0, CGB, frame 600 shows Storm Night start + "Move: D-pad" prompt ✓ |
| Browser preview | `http://127.0.0.1:57089/83863de94ecce88d9065f3504e2a1721eccad11af404a4fed92c36ad58e88e97/` (listening) |
| Note | GB Studio **desktop app** not managed by toolchain — user runs their own editor install; CLI-only pipeline unaffected. Headless boot frame sha256 `2b8e13b3…` is our "before" reference. |

---

## How we work (standing rules)

- **Pipeline only:** data in `tools/level.py` + sibling data modules →
  deterministic generators → `assets/` + `project/` → MCP build → headless
  emulator asserts → browser preview live check. No hand-edited generated
  artifacts.
- **MCP first:** `project_select` the `.gbsproj` before touching anything.
  Browser preview stays open between iterations; never rebuild/reload while a
  human is playing.
- **Verify before building on it:** a feature is only "done" after a ROM build
  plus headless run plus a live preview check (or device capture in Phase 4).
- **Git:** local-only repo, one-line Conventional Commits
  (`feat(platformer): ...`), no AI attribution. Feature work stays in a
  worktree when it is risky or long-running (`git worktree add
  ../gb-mr-cfe-<topic> -b feat/<topic>`); merge back per
  [GIT_WORKFLOW](GIT_WORKFLOW.md). Each worktree is its own MCP project copy.
- **SemVer:** version lives in root `VERSION`. `0.x` = pre-1.0. Additive
  content → MINOR, fixes/polish → PATCH. Dev suffix stays until a release.
- **Subagents:** parallelize independent work with subagents (up to 5),
  coding-only tasks to the dedicated coding model; pick specialist models per
  task. Subagents must follow this plan doc and commit nothing themselves —
  review, verify, then commit.
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

## Phase 1 — Verify the existing loop ⬜

Prove the current game works top-to-bottom before adding anything.

- ⬜ Scripted headless full run: all 4 pickups, all 5 repairs, one cut/refund
- ⬜ All 6 hazard trigger respawns confirmed headless
- ⬜ Clear every "Live test" item in [platformer-test-plan](platformer-test-plan.md)
  in the browser preview
- ⬜ Fix anything broken — through generators only — and re-verify

**Exit criteria:** test-plan fully green, updated snapshot recorded in the test
plan doc.

---

## Phase 2 — Pipeline hardening ⬜

Make every later feature fast to build and impossible to fork by accident.

- ⬜ Extract music data → `tools/melody.py` (data) consumed by `compose_music.py`
- ⬜ Extract character/sprite data → `tools/characters.py` consumed by
  `make_sprites.py`
- ⬜ Add `tools/make_project.py` orchestrator: one command regenerates
  art → sprites → scene(s) → music → sfx in dependency order
- ⬜ Byte-identical regen verified via fresh build + `project_refresh`

**Exit criteria:** single-command full regen, deterministic output confirmed,
iteration loop noticeably faster.

---

## Phase 3 — Full game content ⬜

Ordered by risk; each item ships independently and stays playable.

| # | Feature | Generator surface | Status |
| --- | --- | --- | --- |
| 3.1 | Title screen + storm intro vignette | `make_scene.py` new scenes, settings start switch | ⬜ |
| 3.2 | Resident NPCs on level, animated, power-gated dialogue | `characters.py` → `make_sprites.py` | ⬜ |
| 3.3 | Climb split into 2–3 linked areas | `level.py` areas support in `make_scene.py` | ⬜ |
| 3.4 | Ending scene: night→dawn, five homes lit, celebration | palettes via `make_art.py`, new scene | ⬜ |
| 3.5 | Feel & juice: coyote time, jump frames, sparkles, window glow | `level.py` tuning, sprite frames, palette flips | ⬜ |
| 3.6 | Memorable themes: title, village stages, character leitmotifs | `melody.py` → `compose_music.py` | ⬜ |

**Playable milestone M1** (after 3.1 + 3.2): user does a full browser playtest
of the new openings and NPCs.

**Playable milestone M2** (after 3.3 + 3.5): user plays the multi-area climb.

**Exit criteria:** title → intro → climb (multi-area) → ending complete in one
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
| 2026-10-25 | 0 | **Phase 0 complete.** `project_select` + `project_inspect` (0 errors, 0 warnings; 2 scenes · 39 actors · 6 triggers). Toolchain ready (CLI 4.3.2, GBDK 4.5.0, PyBoy 2.7.0). First MCP ROM build OK: 131,072 B, MBC5+RUMBLE+RAM+BATTERY, GBC-only, headers valid. Headless CGB boot verified (Storm Night, "Move: D-pad"). Browser preview opened and left running for the user. | Baseline table above · boot frame sha256 `2b8e13b3…` |
| 2026-10-25 | Pre-0 | Plan doc created from session decisions: pure GB Studio + generators, full-game scope, memorable themes. | docs/PROJECT_PLAN.md |
| — | — | — | — |
