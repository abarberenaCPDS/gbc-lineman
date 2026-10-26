# Session handoff: Mister CFE (2026-10-26) — build the title + intro

Start a new session with: **"Read docs/HANDOFF.md and continue."**
Replace or delete this file once the intro ships. `PROJECT_PLAN.md` is the long-term record.

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its progress log (newest
first), `docs/MCP_TOOLKIT.md`. VERSION is `0.8.0-dev`; the intro is a feature, so bump to
`0.9.0-dev`. Local-only repo: never add a remote. One-line Conventional Commits, no AI
attribution.

## Where the game is

- Four repair jobs, each verified in the emulator and approved by Abe in the browser
  (Kiko's is pending his verdict):
  - Opening → Storm Climb (Marta, var0)
  - → Wind Ridge (Tomás, `tools/ridge.py`, vars 8/9)
  - → Signal Hill (Rosa, `tools/rosa.py`, vars 10/11)
  - → Pine Hollow (Kiko, `tools/kiko.py`, vars 12/13)

  Each has a contract module and a `tools/make_project.py <profile> --verify` profile
  (climb, ridge, rosa, kiko, opening). 285 tests pass.
- Release ROM `build/rom/mr-cfe.gbc` `15e1c3ed…`. The web preview serves `build/web-kiko`.
  If a preview gets stuck, Abe runs `/mcp` reconnect, then `project_select` the absolute
  `.gbsproj` path.
- Abe's verdicts so far:
  - Tomás's job, browser: "works awesome"
  - Tomás's job, Chromatic stream: "gameplay is awesome"
  - Rosa's job, browser: "all plays amazingly"
  - Kiko's job: pending
- Flashing is deferred; it needs Abe's explicit consent at the time.

## Task: title + animated intro (Abe approved the draft)

Flow: **logo → intro cinematic (A/START skips) → title → Service Opening**.
The game's start scene (`project/settings.gbsres`) becomes the logo scene. It must stay
generator-owned: the intro generator sets it, and the opening generator must not.

1. **Logo:** "ABE'S GAMES / PRESENT" on a night background, about 2 s, then fade out.
2. **Intro: one 20×18 LOGO-type scene.** Captions sit in a bottom overlay. Each line is
   ≤17 chars (≤18 is the hard limit at x=1). Each shot runs 3–4 s.

   | # | Shot | Caption |
   |---|---|---|
   | 1 | Village at dusk, warm windows | "A quiet evening\non the hill..." |
   | 2 | Sky darkens, rain starts | "Then a tropical\nstorm rolled in." |
   | 3 | Lightning flash, thunder, shake | "Thunder. Lightning.\nFerocious winds." (trim: 19 chars) |
   | 4 | Pole snaps and sparks, windows go dark one by one | "Poles snapped.\nThe lines fell." |
   | 5 | Grey morning, rain stops, all houses dark | "The storm passed.\nThe power didn't." |
   | 6 | Dark windows | "No fridge. No air.\nNo net. No stove." |
   | 7 | Mr CFE walks in (worker24 sprite) | "One electrician.\nOne mission:" |
   | 8 | He looks up the hill, cut to the title | "Bring the power\nback home." |

3. **Title:**
   - "ABE'S GAMES PRESENT" (small), a big pixel logotype "MR CFE", and "After the Storm".
   - The SemVer tag is read from `VERSION` at generation time, e.g. "v0.9.0-dev", drawn
     with `EVENT_TEXT_DRAW` on the background.
   - "PRESS START" blinks. START fades out and switches to the opening at `opening.START`
     (1,15), facing right.

Suggested split, using the same pattern as the jobs:
- **Main:** writes `tools/intro.py` (IDs via uuid5, scene list, timings, captions, actor
  positions, palette slots, version reader, start-scene ownership) and a `make_project.py`
  `intro` profile.
- **Three parallel workers** (prefer GPT-6 Luna; fall back to Agent `model: "haiku"`):
  - art: `make_intro_art.py`, three backgrounds;
  - sprites: `make_intro_sprites.py` with rain (loop), lightning bolt and pole
    (Standing/Snapped with sparks);
  - scenes: `make_intro_scene.py` with scripts, sky/flash/morning BG palettes and the
    settings start scene.
- **Then:** native check on the release ROM (OAM peak ≤10 per line), web preview,
  Abe's verdict, docs, commit.

## Engine facts already checked (GB Studio 4.3.2 CLI; event defs in the vendored `src/lib/events`)

- **Scene type:** `LOGO` is enabled; its state code builds. Its default player sprite id
  `581d34d0…` may not exist, so hide the player with `EVENT_ACTOR_HIDE` "player" and
  check that the build is clean.
- **Text:**
  - `EVENT_TEXT_DRAW` `{text, x 0–19, y 0–17, location: "background"|"overlay"}` is
    non-modal; use it for captions and the version tag.
  - The overlay comes from `EVENT_OVERLAY_SHOW {color, x, y}` (tiles). Use y=14 for a
    bottom caption band. `EVENT_OVERLAY_HIDE` removes it.
- **Camera shake:** `EVENT_CAMERA_SHAKE` `{units "time"|"frames", time|frames,
  shakeDirection "horizontal"…, magnitude {type number}}`.
- **Fades:** `EVENT_FADE_OUT` / `EVENT_FADE_IN` `{speed: "2"}`.
- **Skip input:** `EVENT_SET_INPUT_SCRIPT` (file `eventInputScriptSet.js`)
  `{input: ["a","start"], override: true, true: [events]}`; remove it with
  `EVENT_REMOVE_INPUT_SCRIPT`. Also available: `EVENT_INPUT_AWAIT`, `EVENT_LOOP`,
  `EVENT_THREAD_START`.
- **Thunder:** `EVENT_SOUND_PLAY_EFFECT` `type: "crash"` (built-in noise). Project sounds:
  connect, cut, death, jump, pickup, place, sparkle, victory.
- **Actor moves:** `EVENT_ACTOR_MOVE_TO` `{actorId, x, y (value objects), moveType,
  collideWith}`.
- **Hero sprite:** `opening_worker24` is `9cb46fea…`, with states `Default`/`Repair`.
- **Palettes:**
  - Window palettes come from `opening.resource_id("palette:bg:window"|"…:powered_window")`.
  - BG slot 7 is UI and is reserved.
  - Swap palettes with `EVENT_PALETTE_SET_BACKGROUND` (pattern: `background_palette_event`
    in `tools/make_rosa_scene.py`).

## Gotchas learned

- **Sprites per scanline:** ≤10 OBJs per line. Props stay off hazard rows; test it the
  way `test_kiko.py` does.
- **Trigger refusals:** never nudge the hero in a trigger refusal (the text loops); show
  text only.
- **Landing margin:** walking off a 3-tile step can carry the hero ~42px. Keep hazards
  ≥9 tiles past the edge.
- **Hardcoded art pixels drift:** derive drawing coordinates from contract tiles. Signal
  Hill's pole was clipped away until fixed.
- **Temporary test start scene:** edit `project/settings.gbsres` for test ROMs, then
  `git checkout project/settings.gbsres` before the release build. The intro will own this
  file, so give it a test-start override instead.
- **Recording quota:** emulator recordings are refused even after archiving. Use
  unrecorded native runs and note that in the docs.
- **Text tokens:** HUD text needs two-digit variable tokens; in-play text goes through
  `say()` (it lifts the HUD cutoff).
