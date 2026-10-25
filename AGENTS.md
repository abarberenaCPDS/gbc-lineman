# AGENTS.md

Game Boy Color game "Mister CFE: After the Storm", built with GB Studio 4.2.0 (`mr-cfe.gbsproj`), currently mid-conversion to a 2D platformer. All data lives in GB Studio resource files (`project/**/*.gbsres`, JSON); there is no hand-written C/game code in this repo.

## Authoring and building

- Prefer the **ModRetro Chromatic MCP** tools: `project_select` the `.gbsproj` (absolute path; use the worktree's copy when working in a worktree) before inspecting, editing, or building. Build/playtest via MCP, keep the browser preview open between iterations, and never rebuild/reload it while a human is playing.
- Local CLI build (rare, MCP unavailable): the temporary build dir path **must not contain `src`** or the build breaks. Exact working command:

  ```sh
  CLI="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/vendor/gb-studio/out/cli/gb-studio-cli.js"
  TMPDIR="$(getconf DARWIN_USER_TEMP_DIR)gbsb-cfe" node "$CLI" -v make:rom ./mr-cfe.gbsproj build/rom/mr-cfe.gbc
  ```

## Generated content — tools/level.py rules everything

`tools/level.py` is the single source of truth for level geometry, palettes, and collision bytes. Art, sprites, and the scene resource are **derived from it** — never hand-edit `assets/backgrounds/`, sidecar `.gbsres` files, or `project/scenes/storm_night/` when a change belongs in `level.py`.

- Edit `level.py` → run the relevant generators (`tools/make_art.py`, `tools/make_scene.py`, `tools/make_sprites.py`, …). They use deterministic UUID5 namespaces, so reruns update only what they own, in place.
- Pillow-based generators (`make_art`, `make_sprites`, `make_village_bg`, `make_village_sprites`) must run under the managed toolchain Python: `"$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"`.
- `tools/make_sfx.py` **refuses to overwrite** existing sound assets — delete the target first if regenerating.
- Dialogue in generated scene scripts is validated to ≤ 17 chars per line (`MAX_DIALOGUE_CHARS`) and raises otherwise.

## Project gotchas

- The live scene is `project/scenes/storm_night/` (start scene, PLATFORM type, 20×36-tile map). `after_the_storm_-_village/` is legacy topdown leftovers and `after_the_storm_village/` is an empty husk — do not edit or assume they are wired up.
- `*.bak` files are GB Studio editor backups; `build/`, `artifacts/`, `save-states/`, `__pycache__/`, and `user_settings.gbsres` are gitignored generated/local state. Never force-add them.
- Project settings: sprite mode 8x16, music driver `huge`, color-only; hazard triggers teleport the player back to start `(2,32)` — there is no game-over state.

## Git and versioning (docs/GIT_WORKFLOW.md)

- **Local-only repo: never add or change a remote.**
- One-line Conventional Commits, `type(scope): imperative summary`; no AI attribution trailers. Types in use: `feat`, `fix`, `art`, `audio`, `docs`, `build`, `test`, `chore`.
- Version is SemVer in root `VERSION` (currently `0.1.0-dev`). One branch per worktree, never the same branch in two worktrees.

## Roadmap

The current phase, status, and progress log live in `docs/PROJECT_PLAN.md` —
read it first and update it (status markers + progress log) after every work
burst.

## Verification

- ROM build success is not enough: headless emulator checks confirm logic, but input/collision presentation/audio are only confirmed by live play (`docs/platformer-test-plan.md` holds the full playthrough checklist with per-behavior "Source-confirmed vs Live test" status).
- Playthrough order matters and is authored: splice pickups are gated per house (Marta 0 → Tomas 1 → Rosa 2 → Kiko 3 → Nuria 4), music changes at homes 2 and 4, win state at 5.
