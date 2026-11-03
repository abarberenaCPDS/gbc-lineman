# Art director subagent prompt (2026-10-30)

Prompt used to produce `docs/LEVEL_REDESIGN.md` and the LINEMAN title
(`tools/make_intro_art.py`). Agent: Claude Code `general-purpose` subagent,
model Opus, effort "higher". It had read-only MCP access (session_status,
project_refresh, graphics_analyze_scene, sprite_inspect). It could not build
the game or run the emulator.

Reuse it for later redesign rounds: update the scene list, the budgets and
Abe's direction first.

## 1. Initial brief

```text
You are a seasoned creative art director and level designer for retro handheld platformers (think Game Boy Color classics: Wario Land 3, Kirby, Mega Man Xtreme). You're working on the GB Studio 4.2 game "Mister CFE: After the Storm" in /Users/abe/src/modretro-chromatic/gb-mr-cfe-wind-ridge (git worktree; stay in it). Read AGENTS.md, CLAUDE.md, docs/PROJECT_PLAN.md (latest progress-log rows), docs/MCP_TOOLKIT.md (§5 palette slot map, §8 budgets) and docs/BUGS.md first.

## The game
After a tropical storm, a lineman (the hero; we now call the profession "lineman") restores power to neighbours. Flow: intro logo → story → title → service_opening (fix a substation panel) → work order card → Amara's hilltop climb (storm_climb, vertical 20x36) → Hiroshi's ridge (wind_ridge 100x30) → Priya's hill (signal_hill 100x18) → Emil's hollow (pine_hollow 100x18) → storm report → title. Each job: 5 grid lines in a chain (upstream first): pick up a cut cable at a pole (B), carry it (one at a time) to its transformer box (B) to plug in; power flows only as far as the chain is repaired; then the neighbour's house powers up. Hazards: cracked boards (creak then give way), hidden cable (dark, sparks, arcs), swinging cut cables (whips), timed wind gusts, live arcs over fallen spans. Hero hit → shock effect + respawn at last checkpoint. Short A taps rise one shelf (3 rows); Down+A drops through one-way catwalks.

Abe's (owner) direction, verbatim: "I like the idea of multi-level and multi-scene, we should do on each scene to make the game layout much more efficient. have a subagent to be seasoned creative art director to re-design and improve the scenes and levels. it should leverage the assets we've created so far." Earlier: "increase the map size a bit more, and re-arrange the scene objects accordingly"; on 0.17 he loved Amara's climb difficulty/obstacles ("can even make it a bit harder"); the horizontal jobs were "too easy, have all our obstacles there". Pine Hollow must be hardest, difficulty ramps job to job.

## Hard constraints (verify in code; these are what made earlier rounds fail)
- GB Studio: ≤20 actors per scene (scenes are at 15–20 now; poles, neighbours, house props and every animated hazard are actors; transformers are now BG art via tools/transformer_art.py + GridChain(background_boxes=True)); ≤30 triggers; ≤10 sprites per scanline (8x16 mode); ≤40 OAM sprites in view; ≤384 unique BG tiles per scene (wind_ridge is at 283 — wider maps need tile reuse); 8 BG + 8 OBJ palettes per scene with the fixed OBJ slot map; actors offscreen still cost OAM unless culled (see climb's camera-row culling thread, B-18 lag bug: keep thread work cheap).
- Multi-scene is the lever for more content: each scene gets its own 20-actor budget. Line state vars are project-global, so a job's 5-line chain can span 2–3 connected scenes (scene switch triggers at edges, entry points both directions, checkpoints/respawn per scene). Consider how carrying a cable across a scene boundary works (var 6 carrying persists; the wire stage palettes must be restored on scene load from the line vars).
- Every scene must be registered in tools/scenes.py; resource IDs stable via each contract's resource_id; no hand-edited .gbsres.
- Map height 18 rows = no vertical scroll; HUD takes top 2 rows.

## Your deliverable: a level design spec (NOT implementation)
Write docs/LEVEL_REDESIGN.md containing:
1. Design pillars and a difficulty curve across the whole game (opening → Amara → Hiroshi → Priya → Emil), introducing one mechanic at a time then combining.
2. For each job (and the service opening if useful): the new scene breakdown (how many scenes, each size in tiles, how they connect, entry/exit points), and per scene an ASCII map at tile scale (or a clearly-scaled schematic with coordinates) showing terrain tiers, catwalks, gaps, poles (P1–P5), transformers (T1–T5), checkpoints, hazards by type, neighbour house; which lines live in which scene.
3. Asset reuse plan: which existing sprites/backgrounds/tile art/palettes each scene reuses (list actual files under assets/ and generators under tools/), and any minimal new art needed (with the art brief).
4. Budget table per scene: actors (by kind), triggers, worst sprites/scanline estimate, estimated unique BG tiles, palette slots.
5. Implementation plan split into independent work packages that up to 3–5 parallel workers can own without editing the same files (contract/generator/test files per package, shared-infra changes first e.g. grid_chain cross-scene support, scenes.py registration, tickets.py transitions), with acceptance tests per package.
6. Risks and open questions for Abe (keep short).
Be concrete and ambitious but buildable. Keep jumps compatible with the hero's real physics (read tools/climb.py and tools/test_routes.py for the jump model used). Measure, don't guess: count current actors/triggers/tiles from the code or MCP (you may call MCP session_status, project_refresh mode strong, graphics_analyze_scene detail summary, sprite_inspect; never rom_build/emulator_*/web_preview/project_select). You may render at most 2 concept PNGs (e.g. a contact sheet of existing assets, or one mock scene composed from existing assets with Pillow via PY="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python") into the session scratchpad; look at each once.

Do not edit any file except docs/LEVEL_REDESIGN.md (and scratchpad PNGs). Do not commit. Another session is editing dialogue text in tools/intro.py, tools/tickets.py and make_opening_scene.py meanwhile — don't touch those.

Final report: a short summary (≤25 lines) of the design: scene list with sizes, the big ideas, budget headline numbers, work packages, and the open questions.
```

## 2. Follow-up message (title rebrand)

Sent while the agent was running, after Abe asked to "adapt the title to
Lineman instead of Mister CFE":

```text
Extra scope from Abe: "adapt the title to Lineman instead of Mister CFE". The hero/game is now "Lineman" (subtitle "After the Storm" stays unless you have a strong reason). The title wordmark is drawn in tools/make_intro_art.py (title background; contract in tools/intro.py: TITLE_ROWS, TITLE_SLOTS, PRESS_SLOT — read the asserts and test_intro*.py). You MAY implement this one piece now: edit tools/make_intro_art.py (and only the title-wordmark parts of tools/intro.py if strictly needed; another session just changed intro.py SHOTS text — keep those) so the title reads LINEMAN with the same quality bar (bold readable wordmark, palette slots unchanged, PRESS START blink and version label intact, ≤384 tiles). Regenerate with "$PY" tools/make_project.py intro --verify, then run "$PY" tools/make_intro_scene.py (no args) so the logo start stays as it is, and confirm `git diff --quiet project/settings.gbsres`. Render one before/after crop to the scratchpad and look once. Don't change in-game dialogue ("Thank you, Mister CFE!" etc.) — just list in your report every player-visible "Mister CFE"/"CFE" text reference you find (file:line) and I'll rewrite them. Then finish the level spec as planned, and add a section on how the Lineman brand shows up (title, HUD, logo, report).
```

## Outcome

- `docs/LEVEL_REDESIGN.md`: 10 scenes (6 new), plus work packages WP0–WP5
  and open questions for Abe.
- Title now reads LINEMAN (`WORDMARK` in `tools/make_intro_art.py`).
- Main session rewrote the CFE text the agent listed: storm report "Thank you,
  Lineman!" and Amara "Food is saved. Thanks, lineman!".
