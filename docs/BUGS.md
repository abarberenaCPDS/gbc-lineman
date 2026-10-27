# 🐞 Bug log

Bugs found in play, newest first. Each fixed bug names its cause, the exact ROM
that showed it, and the regression test that guards it. Feature requests live in
`docs/HANDOFF.md` / `docs/PROJECT_PLAN.md`, not here.

## Open

| # | Found | Where | Bug | Notes |
|---|---|---|---|---|
| B-11 | 2026-10-26, Abe on cart | Climb, Wind Ridge, Pine Hollow | Falling rocks don't fit a line crew's job. | **Built, awaiting Abe's play:** cracked boards + hidden cables replace every rock (`tools/hazards.py`, release `2625c15d…`). |
| B-08 | 2026-10-26 | Pine Hollow | Dead end after Kiko's house is powered. | **Built, awaiting play:** Emil's porch exit → storm report → title (`tools/tickets.py`, release `2625c15d…`). |
| B-06 | 2026-10-26 | Pine Hollow | Junction box needs the hero right next to it (B at x243 does nothing, x≈253 works). | Minor; widen the interaction or add a hint. |

## Fixed

| # | Found | Bug | Cause | Fix and guard |
|---|---|---|---|---|
| B-07 | 2026-10-25 (known) | Holding Down+A dropped through every one-way shelf below; even a single press dropped two climb shelves. | Input mode `DOWN_JUMP_HOLD` re-armed the engine's drop timer every falling frame; and the timer (`DROP_FRAMES_MAX` 15 frames, ~52 px at default gravity) outlasts the 24 px between climb shelves. | Tap mode (`make_engine_fields.py`) plus a generated engine overlay with `DROP_FRAMES_MAX` 7 (~12 px; `make_engine_patch.py`, Abe's choice over slower falling). `test_engine_fields`, `test_engine_patch` (overlay = vendor file + one line; drop distance between 8 px and the smallest shelf gap). Test ROM `00e8d8f3…`: Down+A held 90 frames from shelf 18 lands on 21 and stays; a second press lands on 24; A still jumps. Released in v0.10.3; Abe on stream: "v0.10.3 looks good". Not flashed to the cart. |
| B-12 | 2026-10-26, Abe | "We are missing the dialogs from the intro too." | Never reproduced natively; the cart likely still ran an older ROM. | Abe on the v0.10.1 cart (`31110ef7…`): **"dialogs are back, good job!"** Closed. |
| B-14 | 2026-10-26, native (`454403…`) | Pine Hollow's entry box said "No power at Kiko's house!": the rename missed one caption. | The line was a literal in `make_kiko_scene.py`, not `voices.name()`. | Caption uses `voices.name("kiko")`; `test_voices.test_no_player_text_uses_a_code_key_name` scans every scene script for Marta/Tomás/Rosa/Kiko. Release `a3f5bba4…`. |
| B-15 | 2026-10-26, contract check | Pine Hollow's hidden cable (x11–12) left only 2 standing tiles before the gust (x15–17); the 12 px hero box had a ~4 px safe window. | `hazards.HIDDEN_CABLES` was placed outside `kiko.py`'s three-tile gap check. | Gust moved to x16–18 (mesa's right end); `kiko._self_check` now includes hidden cables in the gap rule. Native test ROM `45440321…`: hero parked at x≈107 px survived 600 frames of gust + cable cycles; safe window x 102–113 px. |
| B-13 | 2026-10-26, Abe on cart (`63c67828…`) | "I don't see the cable": the climb's cable end was invisible and B did nothing, so the junction box only said "No cable yet" and the game was stuck. | The storm pole actor shares the cable end's tile. Actors draw in descending index order (higher index = lower OAM = on top) and the pole was appended last, so it covered the cable. Its 16x32 box also caught the B probe and it has no script. | In all four jobs the pole comes before the cable end and starts with collisions off (`make_*_scene.py`); `test_poles`. Verified on test ROM `8fa0d9e0…`: cable visible in front of the pole, B gives "Got the cable!" and var 6 = 1. Release `8d3f295e…`. |
| B-10 | 2026-10-26, Abe on cart | Characters looked small next to the 24px hero. | Neighbour sprites were 16x16. | 16x32 canvases: Amara/Hiroshi/Priya 24px, Emil 20px (`make_opening_characters.py`, `make_{tomas,rosa,kiko}_sprites.py`); sprite tests assert canvas, bounds and tile-y layout. Release `63c67828…`; cart verdict pending. |
| B-09 | 2026-10-26, Abe on cart | Dialogue didn't say who was speaking. | Boxes had no speaker. | `voices.py`: name line + per-character blip, narrator blip restored; `test_voices`. Release `63c67828…`; cart verdict pending. |
| B-05 | 2026-10-26, Abe on cart (ROM `6bfec7b4…`) | After Tomás's house nothing led to Signal Hill, so Pine Hollow could not be tested. | At the right wall the hero's box overlaps both the door trigger (x35–37) and the porch exit (x38); the platform engine fires only the first matching trigger, the door. | Exits sort before doors on Tomás's and Rosa's porches (`make_ridge_scene.py`, `make_rosa_scene.py`); `test_kiko.PorchExitPriorityTests`. Verified on test ROM `bd8d0559…`; flashed `9c776c6d…`. A first guess (solid porch props) was wrong and reverted. |
| B-04 | 2026-10-26, native (`23b2fc03…`) | Intro hero, pole and bolt drew with their top and bottom halves swapped. | GB Studio sprite tile `y` counts up from the canvas bottom; the intro sprite generator counted from the top. 16px sprites hid it. | `make_intro_sprites.py`; `test_intro_sprites.test_tile_y_counts_up_from_the_canvas_bottom` (checked against `opening_worker24`). |
| B-03 | 2026-10-26, native (`04c6c4a4…`) | A/START could not skip the intro; START did nothing on the title. | Scene start scripts run VM-locked; button scripts only fire after the start script ends, and the timeline/blink loop never ended. | Timelines run in `EVENT_THREAD_START`; `test_intro` thread tests. |
| B-02 | 2026-10-26, native (`ba3a3c63…`) | The last story caption stayed on screen over the title. | The overlay window survives a scene switch. | Overlay hidden on every story exit and at title start; `test_intro` overlay tests. |
| B-01 | 2026-10-26, native (`a8e4f0ad…`) | Story captions corrupted the sky and houses. | Text drawn in a LOGO-type scene overwrites background tiles. | Story and title are TOPDOWN scenes; title text is baked art with a palette-swap blink; `test_intro.test_text_only_outside_logo_scenes`. |

**Process lesson (2026-10-26):** two "fixes" this session were wrong before being
corrected: an actor-offset conversion (the MCP OAM view already reports screen
pixels) and the "worker24 is upside down" theory (it was the overlay hiding the
lower half). Measure pixels or memory before concluding; see `MCP_TOOLKIT.md` §5.

**Caught before a build (2026-10-26):** the intro pole and the live arc both baked OBJ
slot 3 into their tiles, so Signal Hill and Pine Hollow could not show both. GB Studio
ignores an actor's palette field; the slot lives in the sprite's tiles. Fixed by moving the
pole to slot 7 everywhere (`intro.SPRITE_SLOTS`); see `MCP_TOOLKIT.md` §5.
