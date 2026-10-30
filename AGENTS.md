# AGENTS.md

Game Boy Color game "Mister CFE: After the Storm", built with GB Studio 4.2.0 (`mr-cfe.gbsproj`), currently mid-conversion to a 2D platformer. All data lives in GB Studio resource files (`project/**/*.gbsres`, JSON); there is no hand-written C/game code in this repo. The one engine change is a generated one-line overlay, `assets/engine/src/states/platform.c` (B-07 drop-through window, `tools/make_engine_patch.py`, climb profile); rerun it after a GB Studio upgrade, never edit it by hand.

## Authoring and building

- Prefer the **ModRetro Chromatic MCP** tools: `project_select` the `.gbsproj` (absolute path; use the worktree's copy when working in a worktree) before authoring/building. Main owns build/playtest/preview operations. User permits preview interruptions for meaningful updates; preserve saves/recordings and resolve uncertain operations before switching.
- Local CLI build (rare, MCP unavailable): the temporary build dir path **must not contain `src`** or the build breaks. Exact working command:

  ```sh
  CLI="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/vendor/gb-studio/out/cli/gb-studio-cli.js"
  TMPDIR="$(getconf DARWIN_USER_TEMP_DIR)gbsb-cfe" node "$CLI" -v make:rom ./mr-cfe.gbsproj build/rom/mr-cfe.gbc
  ```

## Generated content

Launch is the intro logo (`tools/intro.py` owns the settings start scene; only
`make_intro_scene.py` writes it, `--test-start` for test ROMs): logo → story →
title → `service_opening` (M-V1); after the B repair its awning exit enters
`storm_climb`, whose summit door is Amara's checkpoint. The neighbours are Amara,
Hiroshi, Priya and Emil on screen; code keys keep the old names (`marta`, `tomas`,
`rosa`, `kiko`) so resource IDs stay stable. `tools/voices.py` owns speaker names
and text blips; pass `speaker=` to a job's `say()`.
Its hero is the 24px lineman only (`opening_worker24`); the 16px comparator
and its SELECT swap were removed.
Managed-Python command: `tools/make_project.py opening --fixtures --verify`.
`tools/opening.py` owns its palette/geometry/ID contract; the scene generator
does not change launch settings. Compiler-facing background PNGs are indexed
proxies, not the authored RGB fixtures (color pitfalls: `docs/MCP_TOOLKIT.md`).

The active redesign is `storm_climb`: `tools/climb.py` owns its geometry;
regenerate with managed Python: `make_climb_art.py`, then `make_climb_scene.py`
and `make_engine_fields.py`. Music needs
`python3 tools/compose_climb.py --render` first (installed Docker `uge-builder`,
offline/no pull); the legacy `compose_music.py` writes JSON, not binary UGE.
See `docs/PROJECT_PLAN.md` for current acceptance gaps and the visual-quality gate.
The older `level.py`/`make_scene.py` pipeline describes Storm Night, not the
redesign. Its authored resources diverged from generators; do not blindly rerun it.

Climb route uses **short A taps** for one-shelf rises; holding A longer can
overshoot into higher hazards. Lane 1 is actor-owned timed wind; the other
seven gust trigger resources have empty scripts intentionally until route tests
make them safe to activate. Keep their stable IDs during regeneration.

`tools/level.py` supplies legacy geometry and shared palette definitions. Edit
source modules/generators rather than generated art or scene resources.

- Pillow-based generators (`make_art`, `make_sprites`, `make_village_bg`, `make_village_sprites`) must run under the managed toolchain Python: `"$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"`.
- `tools/make_sfx.py` refuses to overwrite existing sounds; do not delete targets blindly. Inspect the asset/sidecar and owning refinement generator first.
- Dialogue in generated scene scripts is validated to ≤ 17 chars per line (`MAX_DIALOGUE_CHARS`) and raises otherwise.

## Project gotchas

- Current fixture: `project/scenes/service_opening/` (PLATFORM, 20×18); gameplay prototype: `project/scenes/storm_climb/` (20×36). Storm Night and the topdown village are legacy references, not acceptance targets.
- `tools/scenes.py` is the scene registry: every scene folder is tagged `game`, `lab` or `legacy` with its id, editor position and owning generator; `test_scenes.py` fails if a folder is unregistered or a game scene switches into a lab/legacy scene. Register new scenes there first.
- Lab scenes (`LAB_` names, editor row y=1200; `tools/make_lab_scene.py`, profile `lab`): hazard gallery and movement room for test starts, e.g. `make_intro_scene.py --test-start lab_movement_room 2 14 right` (restore settings before committing).
- Release ROMs: `tools/make_release.py` copies the project to `build/release-project/` without lab and legacy scenes (refuses a `-dev` VERSION unless `--allow-dev`), then build that copy. Storm Night stays in the source tree: `make_climb_scene.py` uses it as a template.
- Job scenes share the grid chain in `tools/grid_chain.py` (lines, transformers, B-press pole/box zones via var 27 and one B input script, hero `Carry` pose; B away from zones drops a carried cable); each job's contract (`ridge.py`, `rosa.py`, `kiko.py`) owns coordinates and variables.
- `*.bak` files are GB Studio editor backups; `build/`, `artifacts/`, `save-states/`, `__pycache__/`, and `user_settings.gbsres` are gitignored generated/local state. Never force-add them.
- Project settings: sprite mode 8x16, music driver `huge`, color-only. Respawn coordinates/state handling are scene-specific; inspect scripts rather than assuming a scene reload.

## Git and versioning (docs/GIT_WORKFLOW.md)

- **Local-only repo: never add or change a remote.**
- One-line Conventional Commits, `type(scope): imperative summary`; no AI attribution trailers. Types in use: `feat`, `fix`, `art`, `audio`, `docs`, `build`, `test`, `chore`.
- Version is SemVer in root `VERSION`. One branch per worktree, never the same branch in two worktrees.

## Roadmap

The current phase, status, and progress log live in `docs/PROJECT_PLAN.md` —
read it first and update it (status markers + progress log) after every work
burst.
Independent work uses up to five parallel subagents; coding-only workers
prefer `openai/gpt-6-luna` and fall back to Haiku 5.5 (Agent `model: "haiku"`)
when Luna is not selectable in the current harness; visual-art workers (logo, title,
characters) use Agent `model: "sonnet"` instead. Token and image budgeting rules are in
`docs/MCP_TOOLKIT.md` §8. Each worker must verify direct MCP access (recent `general`
workers have it; earlier `explore` workers did not). Main serializes builds,
emulator controls, project selection and preview updates.
Reusable MCP capabilities, ownership rules and verification limits are in
`docs/MCP_TOOLKIT.md`; rediscover tool signatures before reuse in a new session.

## Verification

- Full visual/climb tests and generators need the managed Python (Pillow):
  `"$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" tools/make_project.py climb --verify`.
  Plain `python3` can run only the stdlib-only `test_climb.py` subset.
- ROM build success is not enough: headless gameplay evidence does not verify browser UI, human feel/audio taste, or physical hardware.
- `docs/platformer-test-plan.md` is superseded: the old splice loop was rejected. Current prototype status and manual checks live in `docs/PROJECT_PLAN.md`.
