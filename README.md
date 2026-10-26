# 🎮 Mister CFE: After the Storm

[![Platform: Game Boy Color](https://img.shields.io/badge/platform-Game%20Boy%20Color-326b4f)](https://modretro.com/products/chromatic)
[![Engine: GB Studio](https://img.shields.io/badge/engine-GB%20Studio%204.2.0-4856a6)](https://www.gbstudio.dev/)
[![Version](https://img.shields.io/badge/version-0.10.3-orange)](VERSION)

A color-only Game Boy Color platformer, played on a ModRetro Chromatic
cartridge. The latest release Abe approved on the cart carries the git tag
`stable`. Status, open bugs and the progress log live in the
[master plan](docs/PROJECT_PLAN.md), [bug log](docs/BUGS.md) and
[session handoff](docs/HANDOFF.md).

## 🌧️ The game

A tropical storm has knocked out the power on the hill. Mister CFE, the
village electrician, takes one work order at a time: reach the broken pole,
pick up the dangling cable end, carry it to the house's junction box and make
the line live, then walk to the door.

| Work order | Scene | Neighbour | What the power brings back |
| --- | --- | --- | --- |
| 1 | Storm Climb | Amara (Nigeria) | Her fridge: "Food is saved." |
| 2 | Wind Ridge | Hiroshi (Japan) | His oxygen concentrator |
| 3 | Signal Hill | Priya (India) | Her home workstation |
| 4 | Pine Hollow | Emil (Denmark), a kid | Dinner on the electric stove |

Flow: logo → storm cinematic → title (left idle, it replays the cinematic) →
Service Opening → a work-order card before each job → the storm report → title.

Hazards respawn you at the scene start; there are no lives or game over.
Cracked boards creak and give way if you stand still on them, wind gusts and
live arcs fire on a timer, and hidden cables only show a brief spark before
they arc. Each neighbour speaks with their own name and voice pitch.

## 🕹️ Controls

| Input | Action |
| --- | --- |
| D-pad | Walk |
| A | Jump (short taps for one-shelf rises) / close dialogue |
| Down + A | Drop through one one-way shelf per press |
| B | Interact: pick up, connect, talk |
| START | Start from the title |
| A or START | Skip the cinematic |
| SELECT | Service Opening only: compare the 16px hero |

## 🧱 Project layout

```text
mr-cfe.gbsproj       GB Studio project descriptor
assets/              Backgrounds, sprites, music, sound effects
assets/engine/       Generated one-line engine overlay (B-07); never edit by hand
project/             Scenes, actors, palettes, settings, variables (generated JSON)
tools/               Contracts, generators and tests (the source of truth)
docs/                Plan, handoff, bug log, design and workflow notes
build/               Local build output (ignored by Git)
```

Everything under `project/` and the art in `assets/` is generated from the
contract modules in `tools/` (`climb.py`, `ridge.py`, `rosa.py`, `kiko.py`,
`intro.py`, `tickets.py`, `hazards.py`, `voices.py`, …). Edit the contract or
generator, regenerate, then run the tests; don't hand-edit generated output.
Code keys keep the neighbours' original names (`marta`, `tomas`, `rosa`,
`kiko`) so resource IDs stay stable.

## 🧰 Build and verification

Generators and tests use the managed toolchain Python (Pillow):

```sh
PY="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"
"$PY" tools/make_project.py climb --verify        # one profile: generate + its tests
"$PY" -m unittest discover -s tools -p 'test_*.py' # full suite
```

Profiles: `opening`, `climb`, `ridge`, `rosa`, `kiko`, `intro`, `tickets`.

Prefer the **ModRetro Chromatic MCP** for ROM builds, headless emulator checks,
the browser preview, streaming to the Chromatic and flashing the cartridge (see
[MCP toolkit](docs/MCP_TOOLKIT.md)). For a local CLI build, use a temporary
build directory whose path does not contain `src`:

```sh
TS="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/vendor/gb-studio"
CLI="$TS/out/cli/gb-studio-cli.js"
TMPDIR="$(getconf DARWIN_USER_TEMP_DIR)gbsb-cfe" \
  node "$CLI" -v make:rom ./mr-cfe.gbsproj build/rom/mr-cfe.gbc
```

Test ROMs that start in a specific scene use
`tools/make_intro_scene.py --test-start SCENE_ID X Y DIRECTION`; restore
`project/settings.gbsres` before a release build and never commit the override.

## 📚 Useful docs

- [Master project plan and progress log](docs/PROJECT_PLAN.md)
- [Session handoff: current state and next steps](docs/HANDOFF.md)
- [Bug log](docs/BUGS.md)
- [Design options awaiting decisions](docs/DESIGN_OPTIONS.md)
- [Reusable MCP toolkit and verification workflows](docs/MCP_TOOLKIT.md)
- [Platformer redesign brief](docs/redesign-brief.md)
- [Action-climb acceptance matrix](docs/action-climb-acceptance.md)
- [Local Git, SemVer and stable-tag workflow](docs/GIT_WORKFLOW.md)

## 🏷️ Versioning and local collaboration

The version is in [`VERSION`](VERSION) (SemVer, pre-1.0) and is baked into the
title screen. Each release gets a `vX.Y.Z` tag; `stable` marks the latest one
approved on the cart. Git is local only: no remote. Commit messages are
one-line Conventional Commits. See [GIT_WORKFLOW](docs/GIT_WORKFLOW.md).
