# 🔍 GBC asset hardware audit

Audit performed with the ModRetro Chromatic MCP `graphics_analyze` and
`graphics_analyze_scene` tools against local baseline `149135c` on 2026-10-22.
The sample images below are reference material, not assets assigned to the
playable scene.

## ✅ Playable-scene assets

| Asset | Size | GBC result |
| --- | ---: | --- |
| `assets/backgrounds/storm_night.png` | 160×288 (20×36 tiles) | Valid; 93 flipped unique tiles / 384 |
| `assets/backgrounds/village.png` | 256×256 (32×32 tiles) | Valid; 112 flipped unique tiles / 384 |
| `assets/sprites/player_platform.png` | 160×16 | Valid; 24 authored 8×16 tiles |
| `assets/sprites/houses.png` | 160×16 | Valid; 13 authored 8×16 tiles |
| `assets/sprites/locals.png` | 48×16 | Valid; 8 authored 8×16 tiles |
| `assets/sprites/cable.png` | 48×16 | Valid; 12 authored 8×16 tiles |
| `assets/sprites/hazard.png` | 32×16 | Valid; 8 authored 8×16 tiles |
| `assets/sprites/substation.png` | 16×16 | Valid; 4 authored 8×16 tiles |
| `assets/sprites/village_player.png` | 192×16 | Valid; 36 authored 8×16 tiles |
| `assets/sprites/village_folk.png` | 80×16 | Valid; 16 authored 8×16 tiles |
| `assets/sprites/village_props.png` | 64×16 | Valid; 16 authored 8×16 tiles |

The original `Storm Night` scene's authored static budget was 93/384 background
tiles, an estimated 47/192 sprite tiles, 19/20 actors, and 40/40 static OAM
objects (8 maximum objects on a scanline). These are source estimates; an
emulator observation is still required to prove runtime visibility/flicker.

## ⚠️ Supplied reference images

The files in `assets/backgrounds/samples/` are visually useful, but are not
build-ready GBC backgrounds. Analysis found these issues:

- `sample_001.png`: dimensions not divisible by 8, over the 384-tile budget,
  more than four colors per tile, and 155 analyzer violations.
- `sample_002.png`: 2692×2160 exceeds the analyzer's 4,194,304-pixel safety
  limit; the project validator also reports a sidecar-dimension mismatch.
- `sample_003.png`: over the tile budget and per-tile color limits; the
  validator reports a sidecar-dimension mismatch.
- `sample_004.png`–`sample_008.png`: dimensions not divisible by 8 and many
  per-tile color violations; most also exceed the 384-tile budget.

They are deliberately preserved as references. No playable scene references
them, and the official 128 KiB GBC-only ROM build succeeds without them. If one
is ever selected for a game scene, first create a purpose-built, quantized,
8×8-aligned replacement rather than repairing or importing the reference PNG
in place.

## 🧪 Recheck

Use MCP `graphics_analyze` on each new/changed PNG and
`graphics_analyze_scene` on the active scene before building. The active
platformer conversion should be re-audited after its art and player-sprite
passes land; this report records the baseline, not those pending changes.
