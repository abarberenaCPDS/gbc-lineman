# Session handoff: Lineman (2026-11-02): 0.19.0-dev on `feat/wind-ridge-lines`

Start a new session in the worktree `../gb-mr-cfe-wind-ridge` with:
**"Read docs/HANDOFF.md and continue."**
`docs/PROJECT_PLAN.md` is the long-term record (progress log, newest rows near line 685).

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

1. **Abe's feedback:** human listening of the intro sync (let the title loop back into the story),
   plus a browser pass on the WP5 art.
2. **Known art weak spots:** Priya's radio masts have low contrast, the gully lashings are faint,
   and the signpost reads like a mailbox.
3. **Native checks not done yet:**
   - Cross-scene carry, and a hit sending the cable home.
   - Gully Down+A drop-through descent.
   - Music continuity across scene edges.
   - OAM on the new routes beyond the ladder sample.
4. **Preview listener:** the MCP reports an unresolved closure ("Browser recording close
   acknowledgement is UNKNOWN"), so `web_preview` open/recover/close all refuse. The URL still
   serves `build/web`. Restart the ModRetro Chromatic plugin to clear it, then reopen the preview.
   Don't delete recordings.
5. **Release bookkeeping:** after Abe accepts this round, tag `v0.19.0-dev`, or bump the patch
   first (the music sync is a fix: `0.19.1-dev`; bump in a `chore(release)` commit and regenerate
   every profile). If he asks, flash the cart without asking again: build the committed ROM with
   the logo start, then fresh device discovery, then `rom_inspect`. Never auto-retry an uncertain
   write.
6. Older open items stay in `docs/PROJECT_PLAN.md` and `docs/BUGS.md` (the seven inactive climb gust
   triggers stay intentionally empty).

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
