---
name: chromatic-budget-playtest
description: Token-efficient recipe for ModRetro Chromatic MCP work in mr-cfe. Use before native emulator verification (emulator_run/step/inspect), before spawning art or plumbing workers for a new scene or repair job, and when choosing models or effort for those workers.
---

# Budget-aware Chromatic playtest and asset work

Images returned into the conversation (frames, contact sheets, crops) are the
most expensive thing in this project. Code, even art code, costs far less. Verify
with text first and look with images only when judging appearance.

## 1. Pick models before spawning workers

| Work | Model | Effort |
|---|---|---|
| Contract (`tools/<job>.py`), reviewing workers, catching design defects | main session (strong model) | default or higher |
| Visual art players see first: logo, title, characters, backgrounds | Agent `model: "sonnet"` | higher |
| Plumbing: scene scripts, events, triggers, palettes, tests | GPT-6 Luna, else Agent `model: "haiku"` | default |

- Run up to 5 workers in parallel, each owning its own files. Main owns builds,
  emulator, preview and commits.
- Give art workers a tight brief:
  - mood and palette slots;
  - references in `assets/backgrounds/samples/`;
  - what to avoid: faint 2–4 px effects, visor-like faces, hardcoded pixel coordinates.
    Derive coordinates from contract tiles.
- Each art worker renders one preview sheet, reviews it once and reports. No render
  loops.

## 2. Native verification: text first

1. Build once with `rom_build` (`captureDebugArtifacts: true`). For a test start scene,
   edit `project/settings.gbsres` temporarily and restore it before the release build.
2. Run `emulator_run` with `debugMode: "source"`. If the recording quota is refused,
   run unrecorded and say so in the docs.
3. Drive play with `emulator_step` using `sampleCount: 1` and larger frame chunks.
   Decide timing from text reads, not pictures:
   - `emulator_inspect` memory, WRAM offset 4639. Actors are 56 bytes each:
     `[flags, x u16, y u16]`; pixels = value >> 5; flag `0x08` = collision on.
   - `emulator_debug` `variableIds` for game state, e.g. line live / home powered.
   - `emulator_inspect` view `oam` with `includeScanlineSummary: true` for the
     10-sprites-per-line budget (`overLimitScanlines` must be 0).
4. Take a screenshot only to judge a look: the payoff, a new sprite, a text box. Crop
   and zoom just that region with the managed Python Pillow. Use contact sheets only
   for side-by-side comparisons.
5. For a scripted scene (intro, cutscene), do one run with one sample per shot.

## 3. Hand off and stop

- Abe's browser pass in the MCP web preview is the final judge of look and feel.
  Record his words verbatim as "human browser".
- Use one fresh session per task, started from `docs/HANDOFF.md`, and update it before
  ending. Long sessions re-send their whole history every turn.

Full rationale: `docs/MCP_TOOLKIT.md` §8.
