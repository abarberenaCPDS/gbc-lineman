# ModRetro Chromatic MCP toolkit

Reusable workflows for combining model design/coding with native game tools.
Keep project plans, gameplay specifications and acceptance logs separate.

**Audit date:** 2026-10-25. **Catalog:** 81 tools discovered, not 81 tools tested.
Rediscover tools and their exact signatures in future sessions or plugin versions.
This guide grants no project, browser, device or filesystem authorization.
Other repositories may optionally link to or copy it; apply their own rules.

## 1. Responsibility and evidence

- **Model:** composition, pixel grids, animation poses, dialogue, game design,
  source/generator code, test scenarios and interpretation of returned evidence.
- **MCP:** inspect actual resources, validate supported constraints, perform bounded
  native edits, build, execute supported runtimes and retain evidence.
- **Human/hardware:** artistic approval, movement feel, listening, browser UX,
  physical readability, cartridge boot and real-device behavior.
- Successful generation or compilation is not proof of fun, polish or hardware play.
- Tool applicability depends on project layout, asset metadata, editor/engine
  version and supported event formats. Inspect results and limitations first.

Evidence labels used below:

- **D — discovered:** description/signature inspected; operation not tested here.
- **I — invoked:** bounded read-only call completed in this audit.
- **P — prior runtime evidence:** earlier project records describe a specific
  successful use; not newly tested here and not a universal compatibility claim.

| Capability | Evidence | What is established / not established |
| --- | --- | --- |
| `project_inventory`, `asset_inspect` | I | Native resources resolved; no fresh authoritative refresh performed |
| `sprite_inspect` | I | States, animation counts, bounds and optional frame metadata read |
| `dialogue_analyze` | I | Font-aware measurements returned; result confidence can be conservative |
| `collision_inspect` | I | Bounded actual collision bytes decoded; no reachability proof |
| `world_dependencies` | I | Relationships and coverage returned; bounded page is not the entire graph |
| `graphics_analyze_scene` | I | Authored tile/palette analysis and explicitly qualified static estimates |
| Tilemap, import, palette and native edit operations | D | Contracts inspected; mutations and dry-runs not exercised here |
| Sprite/dialogue/scene preview writers | D | Static output contracts only; no preview files created here |
| ROM build, source debugging, stepping, OAM, retained review | D + P | Prior scoped build/gameplay evidence; no runtime operations in this audit |
| Browser export/preview | D + P | Prior export and human browser use; agent control not established |
| Device discovery, play, flash, physical capture | D | No USB discovery, device access, capture or write attempted |

## 2. Discover and bind context

Code Mode discovery goes inside `execute`:

```js
return search({namespace:'modretro-chromatic',limit:100});
```

Follow pagination if `remaining` is nonzero. Read each returned description and
signature; do not guess tool names, argument shapes or revision requirements.
Then call the exact bracket path, also inside `execute`, for example:

```js
return await tools["modretro-chromatic"].project_inspect();
```

1. Use `session_status` to inspect existing selection before changing context.
2. For an authorized existing native project, `project_select` its native project
   file, not a ROM and not an unrelated bundled starter. Workers use main's
   selection; never select a competing project behind an active session.
3. Use `project_inspect` and filtered `project_inventory` to identify stable IDs,
   paths, settings and health. Follow `nextCursor` with the same query filters.
4. Use `world_dependencies` before shared-asset changes or scene expansion.
   Check coverage, limitations and both reference/coverage pagination.
5. `project_refresh` is an explicit authoritative verification operation, not a
   routine worker probe. A read-only audit must respect any prohibition on it.

Selection and runtime context are shared. Main serializes selection, writes,
builds, emulator controls and browser updates. Independent workers can inspect
within their authorized scope; do not infer mutation permission from access.

## 3. Model art + native asset checks

Design a native-size composition, value hierarchy, material vocabulary and
character silhouettes before scaling content. Produce reproducible pixel grids,
PNG generators and native sprite metadata rather than relying on tool names to
imply an image-generation service.

- `asset_inspect`: check the actual PNG and native sidecar identity/dimensions.
- `sprite_inspect`: verify canvas, bounds, states, animation slots and frames.
- `sprite_preview` / `sprite_contact_sheet`: write labeled authored-frame views
  for pose/silhouette comparison. These are not emulator framebuffers.
- `graphics_analyze`: analyze actual PNG colors, tile families, quantization,
  flip deduplication, viewport usage and supported hardware constraints.
- `graphics_analyze_scene`: inspect scene palette/tile usage and sprite estimates.
- `graphics_preview_scene`: static background projection, excluding actors/UI.
- `palette_inspect` / `palette_create` / `palette_update` / `palette_assign`:
  coordinate real four-color palettes; shared changes affect other users.
- `palette_paint`: native tile-color assignment, not pixel painting; use only on
  unbound backgrounds. Preserve the reserved UI slot unless explicitly intended.

For full generated animation metadata, `asset_import` with
`sprite.profile:"native_metadata"` accepts a project-local PNG/JSON pair.
It requires source and metadata SHA-256 pins plus a fresh whole-project revision;
use `dryRun` first. It creates new outputs and returns deterministic ID mappings.
Rebinding actors is separate. Never replay an import with an uncertain outcome.
`sprite_edit` tunes supported metadata; it is not an arbitrary pixel/frame editor.

Static projections do not prove animation selection, compiled allocation,
simultaneous visibility, runtime sprite pressure or performance.
`native_graphics_update` supports only the **wrecklight-title-v1** contract;
it is not a general renderer or a recommendation to add custom engine code.

### Native color pitfalls (verified with GB Studio 4.3.2)

- Manual-color backgrounds are indexed from source brightness before native
  palettes apply. Intended indices 0/1/2/3 can be encoded with source gray
  255/170/85/0. Writing dark painted RGB directly can render as bright index 3.
  Keep authored RGB fixtures separate from the compiler-facing proxy PNG.
- Sprite proxies differ: transparent green/alpha → 0; white → 1; gray 160 → 2;
  black → 3. Do not reuse the background indexer for sprite previews. If a
  generated sprite uses the keyed-green RGB convention, static graphics analysis
  may count that key as a fourth opaque color. Encoding keyed-green pixels with
  **alpha zero** in RGBA preserves native transparency and lets the static
  analyzer verify the three-opaque-color limit; test the generated PNG, not
  only its in-memory art data.
- The compiler's `getSpritePalette` expands editor colors as `[p0,p0,p1,p3]`.
  For three opaque colors light/mid/dark, serialize editor
  `[light,mid,dark,dark]`, not `[transparent,light,mid,dark]`.
- Inspect the installed quantizers/compiler before reusing these mappings in a
  different version. Verify an exact-ROM frame against intended colors; valid
  PNG budgets and attractive authored mockups alone missed both mistakes.

## 4. Optional tilemap recipes: one owner per output

Useful combination: model-designed motifs and surface semantics →
`tilemap_atlas_create` → `tilemap_create` → `tilemap_inspect` →
`tilemap_edit` → `tilemap_compile`.

- Atlases register opaque indexed 8×8 tiles and named sparse motifs under the
  project's tilemap area; motifs can include palette and collision semantics.
- Room recipes bind fixed-size native outputs, protected regions, reserved slots
  and tile budgets. Existing-room capture requires exact named atlas patterns:
  no approximate capture or automatic resize is promised.
- `tilemap_inspect` exposes verified identities, native hashes and cell preimages.
- Placement/fill/stamp respects protected cells. Exclusive `replace_cells` and
  `set_collision_cells` require exact preimages and synchronize their supported
  changes; protected-cell selection is deliberate, not a generic override.
- `tilemap_compile` rejects drifted atlas/native outputs and shared-background
  conflicts instead of silently overwriting newer work.
- `adopt_binding` is a guarded identity-adoption operation with six file preimages;
  it is not a bypass for failed validation or unsupported dependency coverage.

**Do not migrate immediately.** First use an isolated small fixture and available
dry-runs; check exact capture, deterministic regeneration and native/runtime output.
Adoption changes the source of truth for bound pixels, palettes and collisions.
Either generators emit reproducible recipe/atlas inputs, or explicitly stop them
from writing recipe-owned outputs. Never let recipe compilation and an existing
generator both own the same PNG, sidecar or collision grid. For bound outputs use
recipe-aware edits, not direct `palette_paint` or `collision_edit`.

## 5. Dialogue, events and revision-safe integration

- Draft characterful concise text, then `dialogue_analyze` with the selected font,
  avatar and intended layout. Check pages, overflow, confidence and truncation.
- `dialogue_preview` writes static native-size cards; runtime timing/input still
  needs playtesting. Preserve any stricter generator dialogue rules.
- `script_inspect` reads the exact owner/nested branch before `dialogue_update`,
  `script_edit` or `script_transition`. Target exact event IDs where appropriate.
- `scene_apply` supports ordered bounded native edits and `dryRun`; distributed
  projects have best-effort rollback, not cross-file atomicity.
- `engine_field_inspect` / `engine_field_update` support bounded override tuning;
  preserve numeric checkbox values and verify engine-version compatibility.
- `script_transition` validates destination bounds, not collision passability.
  Inspect destination collisions separately and playtest the transition.

**Engine facts learned on the intro (GB Studio 4.3.2 CLI, exact ROMs noted in
`docs/PROJECT_PLAN.md`, 2026-10-26).** None of these showed up in a build or an
MCP static tool; each needed native play.
- **Scene start scripts are VM-locked.** Button scripts (`EVENT_SET_INPUT_SCRIPT`)
  never fire until the start script ends. Register the buttons, then put timelines
  and endless loops in `EVENT_THREAD_START`.
- **No text in LOGO scenes.** `EVENT_TEXT_DRAW` there overwrites background tiles.
  Scenes with text use TOPDOWN on a screen-sized map (the camera cannot move).
- **The overlay survives a scene switch.** Hide it (`EVENT_OVERLAY_HIDE`) on
  every exit path, or the next scene shows the last caption.
- **Read OAM as screen pixels.** `emulator_inspect` view `oam` already reports
  screen x/y (no hardware +8/+16 offset). Subtracting it again made actors look
  misplaced and led to a wrong "fix" (exact ROM c816d5e4 exposed it). An actor's
  tile is its canvas's bottom-left tile.
- **Sprite tile y counts up from the canvas bottom** in `.gbsres` sprite data
  (worker24: top slice at y=16). Measuring from the top swaps the halves of every
  32px sprite; 16px sprites hide the bug.
- **Overlapping triggers: the first one wins.** The platform state fires only the
  first trigger (by `_index`) whose tiles the hero's box overlaps. At a wall the
  hero can overlap two; put the one that must fire (an exit) first.
- **Sprites under the overlay are hidden.** A caption band hides any sprite rows
  below its top; keep actors above it.
- **Actors pick animation slots by facing** (down, right, up, left; +4 while
  moving). A `platform_player` sprite is laid out for the player state, so the
  intro uses a fixed-type sprite built from worker24's pixels instead.
- **Background text:** each draw re-renders through the dialogue engine (newlines
  return to the box margin). For static title text, bake it into the art and blink
  it by swapping its own BG palette slot.

**Learned on the cart-feedback burst (2026-10-26).**
- **A sprite's OBJ palette slot is baked into its tiles** (`paletteIndex` in the
  `.gbsres`). GB Studio never reads an actor's palette field, so a sprite shared
  across scenes needs the same slot free in every scene that uses it. Before reusing a
  sprite, list each target scene's `spritePaletteIds`. Job scenes: 0 hero, 1 neighbour,
  2 grid props, 3 live arc, 4 debris, 5 gust, 6 legacy, 7 intro pole.
- **The MCP index can be stale after generators write files.** `graphics_analyze_scene`
  reported 7 actors where 8 were on disk. Run `project_refresh` (mode `strong`) after
  regenerating and before any analysis.
- **Static per-line tests must model the screen.** Counting every actor on a row
  flagged a pole that sits 17 tiles away from the house view; count only actors within
  the 20-tile screen around the hero. The real check is still OAM `overLimitScanlines`.
- **Renames: change what players see, keep keys.** Resource IDs derive from keys and
  file names; variable registration refuses to rename existing variables. Edit display
  strings only. For non-ASCII text ("Tomás"), edit with Python, not `perl -CSD`: perl
  does not decode regex literals without `use utf8`, so the replace silently missed.

**Revision kinds differ:** whole-project revisions guard operations such as
`scene_apply`; script/actor/engine owner-resource revisions guard their respective
edits. They are not interchangeable. Follow each returned signature and revision.
Inspect before editing, reject stale preimages, and never overwrite unknown work.
If generators own resources, persist the accepted change in source as well;
otherwise regeneration will silently erase a successful native edit.

## 6. Real runtime evidence and protected browser handoff

1. Main builds with `rom_build`; request `captureDebugArtifacts:true` for source
   debugging. Inspect the exact returned cartridge with `rom_inspect`.
2. `emulator_run` takes that exact ROM; `debugMode:"source"` requires matching
   authenticated build artifacts. Recording options intentionally start a fresh
   bounded recorded boot; do not restart an existing attempt casually.
3. `emulator_step` applies the complete held-button set for exact native frames.
   Buttons persist; `buttons:[]` releases them. Nothing advances between calls.
4. `emulator_observe` reads the current real framebuffer without movement.
   `emulator_debug` reads supported source state; `emulator_inspect` reads bounded
   OAM/memory/VRAM, including current scanline-pressure summaries.
5. Save `emulator_checkpoint` only from a paused neutral sampled state; a one-frame
   neutral step is an action, not a read-only probe. Restore branches evidence.
6. Retain `recordingSpan` and use `emulator_review` for its exact input interval.
   Review reports samples, integrity and gaps, not automatic gameplay success.
7. Use `web_build` and the owned `web_preview` for human acceptance only after a
   safe handoff. Preserve ongoing play, paused saves and unresolved recordings.

Never replay inputs merely to recover a missing image. Resolve uncertain outcomes
using the original status/evidence. Static budgets and isolated OAM samples do not
prove full-game compiled allocation or sustained performance.
If the built-in browser is unavailable/locked, retain URL/state and report it;
never launch an external fallback. Continue exact-ROM gameplay headlessly when
authorized, while explicitly leaving browser UX unverified. Existing external
browser play does not imply agent control; inspect readiness and preserve that
player rather than assuming remote input is available.

## 7. Music and physical hardware boundaries

No standalone music composer or listening tool was exposed in this catalog.
Use model-authored composition data plus an authorized external composer/UGE
toolchain, integrate native playback events, build and obtain human listening
acceptance. Asset resolution and structural validation do not prove audio taste;
do not infer generative-audio capability from MCP build or playback tools.

- `device` discovery may access USB; even read-like device calls need appropriate
  scope. No device operations were invoked in this audit.
- `play` streams host-emulated video/audio to a selected Chromatic: **not cartridge
  execution**, no cartridge write, and no exposed remote controls or frame capture.
- `flash` is destructive: existing cartridge data is erased, saves may be lost,
  and no backup is made. Require an authorized homebrew/own-game ROM, fresh selected
  device token, exact `rom_inspect` path/size/hash and explicit informed consent.
- `device_capture` observes physical play, not the emulator; it cannot drive
  hardware. Platform access/audio support differs. Capture does not authenticate
  the cartridge ROM or establish game FPS. Use only the built-in browser.
- Recover uncertain device actions through the original operation/request status;
  timeout or failure never authorizes a replacement flash or replay.

Keep native ROM, browser export, host-stream demo and physical cartridge evidence
separate. Vendor success is not manual boot, gameplay, listening or save validation.

## 8. Token budget: models, effort and images

The step-by-step recipe ships as the project skill
`.claude/skills/chromatic-budget-playtest/` (loads on demand).

Learned on the repair jobs (2026-10-26). Our art is Python/Pillow code that draws
pixel grids, so writing it costs about the same as other code. **The real cost is
images returned into the conversation** (emulator frames, contact sheets, zoomed crops).
One full native run with screenshots costs far more than the code that built the scene.

**Models and effort**
- **Main session: a strong model.** Writes the contract, reviews worker output and
  catches design defects before a build. Examples it caught: the drifted pole art, the
  step-landing overlap and the sprite-per-line overflow.
- **Art / sprite-art workers: a mid-tier model** (Agent `model: "sonnet"`), higher effort.
  First-seen visuals (logo, title, characters) are where quality shows. Haiku's art was
  the weak spot: Kiko's blink read as a visor, the stove steam and the arc warning sparks
  were too faint.
- **Plumbing workers** (scene scripts, events, triggers, palettes, tests): coding-worker
  rule from `AGENTS.md` (GPT-6 Luna, else Haiku), default effort. They copy established
  patterns well.

**Spend fewer image tokens (biggest lever)**
- Check state as text first: `emulator_inspect` memory/OAM (`includeScanlineSummary`),
  `emulator_debug` variables. Take a screenshot only to judge a look.
- `emulator_step` with `sampleCount: 1`. Use contact sheets only to compare frames side
  by side. Crop and zoom only the region in question.
- Scripted scenes (intro, cutscenes): one run with one sample per shot.
- Art workers render **one** preview sheet and review it once; no render loops.
- In gameplay, step in larger chunks between reads and let flags and positions (text)
  drive timing.

**Workflow**
- Give a tight visual brief before the art worker starts: mood, palette slots, references
  in `assets/backgrounds/samples/`, and what to avoid (faint 2-px effects, unreadable
  faces). A clear brief prevents paid redo loops.
- Reuse existing assets and palettes (worker24 hero, window/night palettes, climb hazard
  sprites).
- Abe's browser pass is the final judge of look and feel. One human pass beats the model
  polishing pixels on its own.
- One fresh session per task, started from `docs/HANDOFF.md`. Long sessions re-send their
  whole history every turn and eventually get summarized (lossy).

**Worker MCP checks (measured 2026-10-26)**

Context: intro and title work. Three generator workers ran without MCP (told not to).
A read-only probe worker then ran each candidate tool once against their output.

| Run | Model | Tokens | Notes |
|---|---|---|---|
| art | Sonnet | 117k | no MCP |
| sprites | Sonnet | 101k | no MCP |
| scene plumbing | Haiku | 201k | no MCP, 34 tool calls; much of it read vendored GB Studio event JS for argument formats |
| MCP probe | Haiku | 129k | 24 tool calls, about 2x the estimate |

- Workers do have direct MCP access: `session_status` worked from a Haiku subagent.
- Run these routinely in workers (small text responses):
  - `graphics_analyze_scene` (detail `summary`, `includeStaticOam`): tile counts,
    per-slot palette histogram and static OAM estimate in one call. Replaces hand-written
    budget checks. Does not count font/text VRAM.
  - `sprite_inspect`: real pixel bounds per sprite (e.g. pole -22..+8). Our tests check
    only canvas and frames. Its bounds found a real defect: the intro bolt ended ~24 px
    above the pole top (confirmed in emulator OAM).
- Marginal: `scene_inspect`; `script_inspect` (large, mostly repeats the generated JSON).
  Scene scripts are keyed `script`, not `startScript`. The schema does not say so.
- Not worth it for generator workers:
  - `dialogue_analyze`: GBS Mono is fixed width; char-count tests suffice.
  - `world_dependencies`: paged and large; first page uninformative.
  - `graphics_preview_scene`: "limited" confidence for every pixel; does not verify colours.
  - `sprite_contact_sheet`: one frame unless `stateIndex`/`includeFrames` are set; one call
    per state.
- No MCP tool flagged the defect that mattered. EVENT_TEXT_DRAW in a LOGO-type scene
  corrupts background tiles: font tiles overwrite BG VRAM. Seen in exact ROM a8e4f0ad as
  caption letters across the sky and houses. Fixed by making text scenes TOPDOWN on a
  screen-sized map (ROM 4992e3a4). Runtime glitches need the emulator; main owns that.

**Rule going forward**
- Workers verify MCP access, then run `graphics_analyze_scene` and `sprite_inspect` on
  their own output (text only).
- Workers add no preview beyond their one Pillow sheet.
- Main keeps builds, emulator, project selection and web preview. **Select the project
  before spawning workers**: without it, worker `sprite_inspect` and
  `graphics_analyze_scene` fail with `PROJECT_SELECTION_REQUIRED`.
- Parallel workers that run `make_project.py` regenerate shared scenes and see each
  other's half-edited files. Their failing tests are often a neighbour's in-progress work.
  Main regenerates every profile and runs the full suite once all workers are done.
- Give plumbing workers the scene's OBJ slot map (§5). The Haiku pole worker
  (268k tokens, 69 tool calls) stopped halfway on a slot clash that a one-line brief
  would have avoided. Sonnet art workers cost about 90–120k tokens each.
- A stage-2 rerun of a worker with tools was skipped: the probe's value did not justify
  ~200k tokens.
