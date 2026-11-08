# Hero designs and intro variants

Abe selected **Storm Worker** for gameplay and **Neighborhood Hero** for story use
on November 7, 2026. These are native interpretations of the approved concept
sheets in `review-assets/hero-variants/`, authored at Game Boy Color resolution.

## Gameplay: Storm Worker

`tools/make_opening_characters.py` owns the character. Its broad orange jacket,
cream reflective band, hard hat, pouch and heavier boots replace the previous
art in every Default, Repair, Carry and Shock frame. The stable asset name is
still `opening_worker24`; renaming it would unnecessarily break references.

All 13 active platform/lab scenes initialize this shared sprite. Its 16×32
canvas, 24px body, 12×24 collision bounds, foot anchor, animation types, frame
counts and speed remain unchanged. The existing overhead-plug Carry signal is
preserved. Neighbors, hazards, background art and music were not redesigned.
Historical Storm Night/topdown village assets remain archival references, not
part of the active campaign or release copy.

## Story: Neighborhood Hero

`tools/neighborhood_hero.py` contains editable native pixel grids. The hero has
a larger cream helmet, warmer face, orange rolled sleeves and gloves. Four
walk cels give the story actor a separate character from the gameplay worker.
The story sprite uses a 16×32 canvas, including a 31px-tall silhouette; it is a
non-colliding cinematic actor, not a change to the gameplay hitbox.

`tools/make_intro_sprites.py` generates:

- `intro_hero.png`: selected intro art, retaining its original stable ID and
  fixed Idle/Walk state contract.
- `neighborhood_hero.png`: independent reusable story asset, always Neighborhood
  Hero, with its own stable ID and existing worker OBJ palette slot 0. This is
  retained for a future map or other story scene; no map scene was invented.

The existing nine-shot sequence is preserved: dusk, storm, lightning, snapped
poles, morning, dark homes, lost services, hero entrance, mission. The new hero
enters during the existing “One lineman. One mission” beat. Scene/actor scripts,
caption wording, beat timing, music, title attract replay, skip controls and the
logo → story → title → Service Opening chain are unchanged.

The `classic` option preserves the original intro hero pixel-for-pixel in native
grids, independent of future gameplay sprite regeneration. Neighborhood Hero is
the default; classic remains a reproducible alternative.

## Generate and build

Use the managed Python (Pillow):

```sh
PYTHON="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"
"$PYTHON" tools/make_project.py opening --fixtures --verify
"$PYTHON" tools/make_project.py intro --intro-hero neighborhood --verify
```

For the preserved intro appearance:

```sh
"$PYTHON" tools/make_project.py intro --intro-hero classic --verify
```

Then build through the selected worktree's ModRetro MCP. Restore the default
with the neighborhood command before normal development. Neither variant changes
the gameplay worker. Never edit the generated PNGs or sidecars by hand.

## Verified evidence

Version `0.20.0-dev`, branch `feat/experience-feedback`, sibling worktree
`../gb-mr-cfe-experience`. Three parallel workers: Terra for each native character
track, Luna for active-scene integration; main serialized build/playtest/preview.
Each worker could call MCP status but its isolated session had no selected
project, so the project-specific MCP checks were performed by main.

- **517 tests pass**; every profile regenerated and 647 asset/resource files
  reproduced byte-for-byte on a second pass.
- Both variant verification commands pass. Classic source pixels match the
  pre-change intro sheet. Source snapshots confirm all existing project resources
  are unchanged except version labels; music, sounds and engine hashes match.
- Project health: zero errors/warnings/info; 20 scenes, 164 actors, 97 triggers,
  127 palettes, 97 assets, 50 variables. Gameplay hero metadata is 59 tile pairs
  and at most four hardware objects per frame. Metadata is not runtime proof.
- Production native ROM: `build/rom/storm-worker-neighborhood-intro.gbc`, 524288
  bytes, SHA-256 `ea139d78dc71281128e691dfb66c8c2dc2c1e946b95a2f9e51e320e9f8131a8a`.
- Classic native ROM: `build/rom/storm-worker-classic-intro.gbc`, SHA-256
  `940d99081866ee77f80b3aeb3c409c6914595dfbba37c29dee1c0858c3ba9de7`.
- Native production recording `artifacts/playtests/hero-redesign`, session
  `74300985f6824685b038150ca9635796`, frames 0–3068: intro hero at 2093,
  mission at 2332, title at 2571, opening at 2752, panel repair variable 4 = 1
  at 2954, walking and jumping through 3068. Classic intro visually checked at
  frame 2093 in its own ROM. Sampled OAM peaks: intro 8/scanline, opening 5,
  zero over-limit scanlines in those samples.
- Direct-start Storm Climb fixture `build/rom/storm-worker-carry-check.gbc`,
  SHA-256 `928442c3fe02ea1da3567d45010415a3afce46df580211947d5fbfaa82575182`.
  Recording `artifacts/playtests/storm-worker-carry`, session
  `504f28fe46394216ad2008c35ae777a7`, frames 0–521: real base-pole pickup
  var6=1 at 266, carried jump at 333/341, hidden-cable hit and Shock at 425/431,
  respawn with var6=0 at 521. Sampled OAM peak 4/scanline, none over limit.
  Only launch settings were overridden for this fixture; production launch and
  default variant were restored to the verified source hash afterward.
- Web export `build/web-storm-worker`, ROM SHA-256
  `341b9c50b68c141ffe189811532d4a521b03931c90d11315e17d4a933f6742d8`.
  Current listener is open, with no attached players at final status:
  <http://127.0.0.1:50913/398fbd351b218eff07550b104a16dfe9de07be63989710d25c07c14f5c2e0d9e/>.
  Browser opening failed with “The browser access host is unavailable.”

Native captures and source sheets are retained in `review-assets/hero-variants/`.
Builds and recordings remain ignored local artifacts. The only compiler warning
was the existing upstream Node DEP0190 deprecation. Native checks do not establish
human visual/motion acceptance, full-campaign completion or physical hardware
quality. The browser preview remains available for the user's review.
