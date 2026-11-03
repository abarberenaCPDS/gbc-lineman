# Session handoff: Lineman (2026-11-02): 0.19.0-dev review on `main`

Start a new session in `/Users/abe/src/modretro-chromatic/gb-mr-cfe` with:
**"Read docs/HANDOFF.md and continue."**
`docs/PROJECT_PLAN.md` is the long-term record (progress log, newest rows near line 685).

The former feature worktree is gone; its branch was merged into `main`.
Abe accepted this round for commit on 2026-11-03: "very good, let's commit this version."
VERSION remains `0.19.0-dev`; its existing tag stays on the earlier merge.
Leave local `opencode.jsonc` uncommitted. No cartridge flash requested.

## Current round (2026-11-02)

- Abe accepted the intro sync and WP5 art: **"accepted, all good."** He requested a
  frontier gameplay review, implementation, remaining native checks, and preview recovery.
  **Accepted for commit on 2026-11-03.** No version bump, tag change or flash.
- Frontier GPT-6 Astra reviewed all ten job routes and implemented four fairness fixes:
  crest and saddle arrivals now have solid recovery steps below one-way timber, so two
  short jumps regain the upstream exit; Wind Ridge and Pine Hollow return catwalks extend
  one tile to support both columns of the hero. Obstacle mix/timings and tutorial unchanged.
  A smaller independent worker checked art/collision linkage and hazard clearance.
- New route checks cover recovery from every reachable standing tile and safe full-width
  arrivals across all ten scenes. **490 tests pass** after all profiles regenerated.
  Also fixed empty abandoned scene directories confusing registry tests and the ticket-art
  preview's hardcoded old session path (now `build/ticket-art/`).
- Native checks (unrecorded, original recordings preserved):
  - Cable 5: pole pickup -> crest preserves var 6 = 5; hidden-cable hit clears it to 0,
    line 5 remains dead; return to the original pole permits pickup again (var 6 = 5).
    Baseline test ROM `c48d9bd5…`, frames 180–1080; gameplay state handling unchanged.
  - Gully with cable 4: feet row 14 -> 17 -> 20, var 6 stays 4. Holding Down+A for
    90 frames on the second drop stays at row 20. ROM `2e8bb960…`, frames 546–763.
  - Saddle floor -> step (feet 11) -> timber (feet 8), two 6-frame A taps:
    `68c13b62…`, frames 276–346. Crest recovery plus return to Storm Climb:
    `a447c763…`, frames 360–543. Original maps were not proven runtime softlocks;
    these improve short-tap recovery rather than maximum-jump capability.
  - Internal music continuity: `fd78cb98…`, frames 180–276, climb -> crest. hUGE row
    16 -> 33, order 0 unchanged, counter 99 -> 202; track bank 3/pointer 0x79df unchanged.
    A temporary generator wrapper (`build/review-music-fixture.py`) seeds playback at a
    summit test start; transition scripts are production code. Fixture and test start restored.
    Normal-flow climb -> opening also continues: `9c228c5d…`, frames 3070–3138, row 21 -> 33.
  - Sampled OAM: climb ascent peaks at 9/line; gully at 6; ladder ascent feet 32 -> 8
    (`935e133d…`, frames 495–770) peaks at 7. Zero over-limit scanlines in these samples.
    These are sampled routes, not every hazard phase/camera position or a full-game verdict.
- All ten scenes analyzed: 84–198 effective BG tiles. Whole-map static OAM warnings remain
  conservative: horizontal rows include off-screen actors; shafts depend on culling.
- Final logo-start ROM: `build/rom/lineman-review.gbc`, 524288 B, SHA256
  `e850ee012246d173c7b99d45b90e70a91652ec94551aaa0274d86979702ef7ef`, header valid;
  native source debug confirms Abe's Games Logo at frame 120.
- **Current web preview**, stable while Abe tests:
  `http://127.0.0.1:62832/868951b201c95dc1d8411acbfa4b3a760283132af437193bc22b46537ea9bf59/`
  serves `build/web-review`, ROM `1936436b…`. Listener open; no old unresolved closure in
  this plugin session, so no restart required. Built-in browser host unavailable: the agent
  could not open its tab. URL supplied to Abe; don't replace/reload this export during play.

The sections below retain the previous round's implementation history; the current round
and current URL above take precedence.

## Read first

`AGENTS.md`, `CLAUDE.md`, the newest `docs/PROJECT_PLAN.md` log rows, `docs/LEVEL_REDESIGN.md`
(multi-scene spec, Abe's answers in §9), `docs/BUGS.md`, and `docs/MCP_TOOLKIT.md` §5 (engine facts, OBJ
palette slot map) and §8 (budget, worker rules). Load the `chromatic-budget-playtest` skill before
you do emulator work or spawn workers.
- Local-only repo. Commits are one-line Conventional Commits with no AI attribution.
- `project/settings.gbsres` must start at the logo. Never commit a `--test-start`; check with
  `git diff --quiet project/settings.gbsres`.
- Leave `opencode.jsonc` (Abe's local config) uncommitted.

## Done (all committed on this branch)

- **0.17.0-dev / 0.18.0-dev** (tagged): the gameplay round from `HANDOFF_FEEDBACK.md`, harder
  layouts for Hiroshi, Priya and Emil, carried-cable option C, and the Lineman rebrand with the
  new story, opening and work-order script.
- **0.19.0-dev multi-scene redesign** (not tagged yet): 10 job scenes from `LEVEL_REDESIGN.md`:
  - Amara: storm_climb + climb_crest.
  - Hiroshi: wind_ridge + ridge_saddle.
  - Priya: signal_hill + signal_gully + signal_porch.
  - Emil: pine_hollow + pine_ladder + pine_rim.

  Shared cross-scene infra lives in `scene_links.py`, `GridChain(scene=)` and `shaft.py`. Cart
  header and release file are now `LINEMAN` / `lineman-release.gbc`. Abe's cart was flashed with
  `ef36962`.
- **WP5 art polish:**
  - Scene-edge markers (arch, signpost, pine gate).
  - Puddles and branches kept off hazard lanes.
  - Gully rope lashings and runoff, radio masts.
  - Crest storm backdrop, ridge wind streaks, pine trunks in the ladder.
  - 84–200 BG tiles per scene.
- **Intro music sync:**
  - The story restarts theme B on shot 1 every pass, and the logo is silent.
  - Theme B has 9 sections, one per shot.
  - Every shot lasts `intro.SHOT_FRAMES` = 239 frames (4 bars at hUGE's 64 Hz).
  - The hero walk counts inside its shot, and the camera shakes run in their own threads.
  - A measured 5-frame per-shot script cost is subtracted (`SHOT_OVERHEAD_FRAMES`).
  - Native exact ROM `7dea5da0…`: the hero shot starts at story+1674 ±2 frames (target 1673).
- **Tests:** 487 pass.
- **Web preview:** the export `0c0c5a45…` (art polish + music sync) is served at the existing
  listener URL `http://127.0.0.1:55192/77361db4…/`. curl confirmed the served ROM hash.

## Left to do

1. **Abe's review of the geometry improvements**, especially recovery after a fall in the crest
   and saddle and the widened return landings. Prior intro/art review is accepted.
2. **Broader play coverage:** native evidence above covers the listed mechanisms and sampled
   ascent routes, not every cross-scene cable, hazard phase or horizontal camera window.
   Physical hardware acceptance of this round remains untested.
3. **Release bookkeeping:** after Abe accepts this round, tag `v0.19.0-dev`, or bump the patch
   first (the music sync is a fix: `0.19.1-dev`; bump in a `chore(release)` commit and regenerate
   every profile). If he asks, flash the cart without asking again: build the committed ROM with
   the logo start, then fresh device discovery, then `rom_inspect`. Never auto-retry an uncertain
   write.
4. Older open items stay in `docs/PROJECT_PLAN.md` and `docs/BUGS.md`; inactive climb gust
   trigger resources stay intentionally empty.

## Verification recipe (native)

1. Run `make_intro_scene.py --test-start <folder> X Y right`.
2. `rom_build` with `captureDebugArtifacts`.
3. `emulator_run` with `debugMode: source`.
4. Restore the start scene with a plain `make_intro_scene.py`.

Player/actor positions:
- The actor array starts at WRAM offset 4639. Each actor is 56 bytes, laid out
  `[flags, x u16, y u16]`; pixels = value >> 5.
- The story hero is runtime actor 13, at offset 5367.

Read text first and take screenshots only to judge looks. Each `rom_build` log is ~15k tokens.
Docker `uge-builder` needs Docker Desktop running (`open -a Docker`) for `--render`.
