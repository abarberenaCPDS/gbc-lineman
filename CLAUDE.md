# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

The canonical agent instructions live in `AGENTS.md` and apply in full:

@AGENTS.md

## Quick commands

All Pillow-dependent commands use the managed toolchain Python:

```sh
PY="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"

"$PY" tools/make_project.py opening --fixtures --verify   # regenerate + test M-V1 fixture
"$PY" tools/make_project.py climb --verify                # regenerate + test storm_climb
"$PY" tools/make_project.py climb --render-music --verify # also re-render climb UGE (Docker uge-builder)

# Tests are stdlib unittest files in tools/ (run from repo root; -s tools puts tools/ on sys.path)
"$PY" -m unittest discover -s tools -p 'test_climb*.py'
"$PY" -m unittest discover -s tools -p test_opening.py
# Single test:
cd tools && "$PY" -m unittest test_climb.ClimbTests.test_geometry_invariants
```

## Architecture in brief

- `tools/make_project.py` is the single entry point per profile (`opening`, `climb`). It runs that profile's generators in order, optionally renders music / preview fixtures, then runs the matching tests. It never builds the ROM, changes the launch scene, or runs legacy Storm Night generators; ROM build/playtest go through the ModRetro Chromatic MCP.
- Each profile has a **contract module** that is the source of truth (`tools/opening.py`, `tools/climb.py`: geometry, palettes, stable resource IDs) and **generators** (`make_*_art.py`, `make_*_sprites.py`/`make_opening_characters.py`, `make_*_scene.py`, `make_engine_fields.py`) that write PNGs and `project/**/*.gbsres` JSON from it. Edit the contract/generator, then regenerate; don't hand-edit generated output.
- Tests (`tools/test_*.py`) assert on both the contract invariants and the generated `.gbsres`/PNG output, so they must run after regeneration.
- Status, acceptance gaps and the progress log: `docs/PROJECT_PLAN.md`; MCP capabilities and color/proxy pitfalls: `docs/MCP_TOOLKIT.md`; commit rules: `docs/GIT_WORKFLOW.md`.
