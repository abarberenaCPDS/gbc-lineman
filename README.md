# 🎮 Mister CFE: After the Storm

[![Platform: Game Boy Color](https://img.shields.io/badge/platform-Game%20Boy%20Color-326b4f)](https://modretro.com/products/chromatic)
[![Engine: GB Studio](https://img.shields.io/badge/engine-GB%20Studio%204.2.0-4856a6)](https://www.gbstudio.dev/)
[![Version](https://img.shields.io/badge/version-0.2.0--dev-orange)](VERSION)

**Current work:** an isolated **Service Opening (M-V1)** visual candidate is
the configured start scene. It is not the full game. See the
[master plan](docs/PROJECT_PLAN.md) and [current redesign](docs/redesign-brief.md);
the original loop sketch below is historical, not the current acceptance target.
In the fixture, **B/X** repairs or talks; **SELECT/Shift** compares hero sizes
and returns to the starting spot.

## 🌧️ The game

A tropical storm has cut the power to a lonely mountain village. Climb the
mountain, recover loose cable connectors, restore the five homes in order, and
talk with the people waiting in the dark. There is no score; Mister CFE has
unlimited lives.

The project is being converted to a **2D PLATFORM game**. Its visual reference
is the supplied art in `assets/backgrounds/samples/`: dark cavern silhouettes,
clear green platform edges, wooden bridges, warm windows, and bright electric
cable against the night. Those PNGs are references, not game-ready assets.

## 🕹️ Controls

| Input | Action |
| --- | --- |
| D-pad | Move |
| A | Jump / close dialogue |
| B | Interact: pick up, talk, connect or cut |

## 🔌 Core loop

```text
        climb the mountain
               │
     find a loose connector
               │ B
   ┌───────────┴───────────┐
   │                       │
talk with a neighbor   link their home
                           │
             warm light + a fuller music arrangement
```

The intended repair chain is bottom-to-top: substation → five homes → the
mountain humming again. A failed jump or dangerous contact costs time, not a
life; hazards respawn the player without a permanent game-over state.

## 🗺️ World sketch

```text
                    [House E] ── ridge
               ledges / bridges / cable
          [House C]          [House D]
      trail and storm-damaged power poles
          [House B] ── stream crossing
              [House A]
           [Substation]
```

This is a design sketch, not a tile-accurate map. See the design notes for the
current authored level and any changes made during the platformer conversion.

## 🧱 Project layout

```text
mr-cfe.gbsproj       GB Studio project descriptor
assets/              Backgrounds, sprites, music and sound effects
project/             Scenes, actors, palettes, settings and variables
tools/               Deterministic art, audio and level generators
docs/                Design brief, decisions and production notes
build/               Local build output (ignored by Git)
```

## 🧰 Build and verification

Prefer the **ModRetro Chromatic MCP** for project inspection, ROM builds,
emulator playtests and the playable browser preview. Keep the preview open
between iterations; follow the interruption permission and save/recording guards
in [the project plan](docs/PROJECT_PLAN.md).

For local GB Studio CLI work, use the installed toolchain and a short temporary
build directory whose path does not contain `src`:

```sh
TS="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/vendor/gb-studio"
CLI="$TS/out/cli/gb-studio-cli.js"
TMPDIR="$(getconf DARWIN_USER_TEMP_DIR)gbsb-cfe" \
  node "$CLI" -v make:rom ./mr-cfe.gbsproj build/rom/mr-cfe.gbc
```

The source generators use the toolchain Python environment when Pillow is
required. Generated ROMs, browser exports, compiler symbols and emulator saves
are local and ignored by Git.

## 📚 Useful docs

- [Master project plan and progress status](docs/PROJECT_PLAN.md)
- [Reusable MCP toolkit and verification workflows](docs/MCP_TOOLKIT.md)
- [Original gameplay brief](docs/gameplay-instructions.md)
- [Design decisions and deferred alternatives](docs/game-design.md)
- [GBC background and sprite audit](docs/asset-hardware-audit.md)
- [Fast Pace reference analysis and CFE music notes](docs/music-notes.md)
- [Local Git, worktree and SemVer workflow](docs/GIT_WORKFLOW.md)

## 🏷️ Versioning and local collaboration

The project version is in [`VERSION`](VERSION) and follows SemVer. It is
`0.2.0-dev` while the platformer redesign is in development. Git history and
worktrees are local only; no remote is configured. Commit messages are one-line
Conventional Commits. See [GIT_WORKFLOW](docs/GIT_WORKFLOW.md).
