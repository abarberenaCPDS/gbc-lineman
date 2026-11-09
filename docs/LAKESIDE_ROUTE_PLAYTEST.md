# Lakeside route playtest evidence — November 9, 2026

The final production ROM used for the opening check is
`build/rom/lineman-lakeside-routes-v0.24.0-dev.gbc`, SHA-256
`1df0eb9e26109b42ac821fad996b8a396cfb0b0bd75d538a078525d0314e8eaf`.
The source suite passed **573 tests**. These results combine seeded native
fixtures and recorded checkpoints; they do not demonstrate an uninterrupted
campaign or player acceptance.

| Route | Native evidence | Follow-up evidence / human review |
| --- | --- | --- |
| Amara | `lakeside-amara-launch`: frame 456, fifth repair (`count5`). `lakeside-amara-notch`: frame 546, intentional fall recovery and fifth repair. | `lakeside-amara-ascent` starts with zero repairs: repairs 1–4 at frames 959/1609/3649/4211, fifth pickup 4641, crest seam 4848, notch recovery and repair 5 at 5439, cabin flag 0=1 and Town ticket 2 at 6200. Local complete route verified. |
| Hiroshi | `lakeside-hiroshi-route`: first two repairs and cable 3 carried forward across the Wind/Saddle seam. The initial reverse-loss result came from unconditional fixture reseeding, not a production route defect. `lakeside-saddle-once`: both-direction seam traversal preserves cable 3; repairs 3, 4 and 5; home flag 9=1; Town ticket 3 at frame 3089. | Try short and held jumps over each gust, wait through a full island gust cycle, and review porch/window approach and return. |
| Priya | `lakeside-priya-gully-safe`: repairs 3, 4 and 5; home flag 11=1 at frame 3398; Town ticket 4 at frame 3911. The run includes actual retries. | Review the deliberate and missed gully landings and recovery/backtracking on the exact ROM. |
| Emil | `lakeside-emil-hollow`: repairs 1 and 2 at frames 846/1524; after a failed upper crossing, cable 3 retrieved at 2220, lower recovery crossing at 2396 and forward seam to Pine Ascent at 2554 with cable 3 retained. `lakeside-emil-ladder`: repairs 3 and 4, cable 5 carried across the seam at frame 3255. The earlier Rim catch did not work; source was extended to x13–18 at row 12. `lakeside-emil-recovery`: vertical jump from (17,11) to (17,8), frame 228; safe 180-frame wait; crossings; repair 5 and home flag 13=1 at frame 1143. | Earlier frame 1715 was still at Rim; that stop note was incorrect. A new recorded run, `lakeside-emil-exit`, repeats the recovery and repair, then reaches the visible Storm Report at frame 1755. Local exit verified. |

Production ROM normal boot reached pickup at frame 1190, repair at 1393, and
Town at 1790. Canceling and accepting Amara dispatches to Storm Climb at frame
3258. The initial production ascent attempt lost the first cable. A subsequent focused
route run completed all five repairs and the cabin return, as recorded above. This is a partial opening check, separate from the seeded route
fixtures.

## Evidence boundaries and remaining gates

Generator/source review sheets establish authored terrain and static layout
budgets; they do not show runtime sprites, HUD, collision timing, or player
readability. Native emulator recordings establish the specific seeded state
transitions and route segments above, not an uninterrupted full campaign or
human judgment of pacing, feel, warning visibility, or audio. No browser UI,
human play acceptance, or physical hardware acceptance is established here.

The changed Pine Hollow approach and its forward seam now pass native play.
Priya's first scene retains its prior collision geometry; its source-art review is
separate from the gully and porch checks. The next campaign gate is to play all routes from the
opening through their returns, review route warnings and landing readability
with a person, and separately check browser and hardware behavior if those
targets are required. Do not treat the seeded fixture results as a full
campaign completion claim.

## Updated web export

Official export `build/web-lakeside-routes-v024` succeeded. Its web ROM SHA-256 is
`78ba326e8cde9a47d81c8e1bdc1fdf6ff79a9916cdff46085a1809e0aacaa26e`.
The process-local preview URL is:
http://127.0.0.1:51125/6b85c823c65beeb3e8f86f71e85dabe1c68565d2092762c28d566887597d89ab/

Codex browser host returned unavailable, so UI verification remains open. The
previous shoulder-coil preview save at frame 8862 is preserved as state
`97884c08982b7de465dec40df0c2221395afd0ebd1faf0450495f9ac4dadac5e`,
with its original export retained; it must not be restored into the new build.

The complete Amara route fixture ROM is `build/rom/lakeside-amara-ascent-check.gbc`,
SHA-256 `6a5057cf34b6a76b24b4b6ed4bb16d87d7f0a17907bdc1216d40b4e8c14f6d79`.
The Emil exit fixture ROM is `build/rom/lakeside-emil-recovery-check.gbc`, SHA-256
`226f205a339e9dc39674f603bd32019565d4bb34321f6db02c2a8ac8fba1f978`.
Source review sheets are retained in `docs/review-assets/lakeside-routes/`; they
are generator RGB renders, not emulator screenshots.

Pine Hollow fixture: `build/rom/lakeside-emil-hollow-check.gbc`, SHA-256
`166e042df99bc719b9ef6c44d4cfd99fb369c00f8c605ceb1607e88d933fc4ab`.
It seeds the fourth job with zero repairs once; subsequent progress and cable
retrieval are earned through normal game controls.

## Items 1 and 2 completion audit

| Requirement | Evidence and limit |
| --- | --- |
| Playtest revised training and town | Production normal boot reaches pickup, repair, town and cancel/accept dispatch. Earlier `route-baseline-guide` verifies optional field guidance; final wording is generated and builds. |
| Redesign all four household routes | Four owning source contracts/art generators and generated scenes, source RGB sheets, and focused native recordings above. Priya's first scene keeps its established geometry; redesign centers on its descent and porch. |
| Preserve accepted movement | No diff in `project/engine_field_values.gbsres` or `assets/engine/src/states/platform.c`; SHA-256 values below. Hero/collision assets and production start settings have no diff. |
| Four jobs, five repairs per job | Contract, chain and route tests in the 573-test suite; native evidence covers each changed repair route. |
| Work pads, crossings, recovery, returns | Amara full local run, Hiroshi both seams/home return, Priya descent/porch/home return, Emil Hollow recovery/ascent/rim/report. Seeded segments remain explicitly distinct from a full campaign. |
| Editor organization | Existing scene registry positions retained; canvas organization regenerated. Registry/layout checks passed in the suite; no new scene added. |
| Resource budgets and build | Focused tile/OAM/scanline tests and official 512KB GBC build passed. Source estimates do not guarantee every runtime scanline or human readability. |
| Preview and prior save | Official web export succeeds and listener is live. Old paused save retained. Browser host unavailable; UI/human review remains a later gate. |
| Parallel model-budget workflow | Bounded GPT-6 Luna audits; GPT-6.1 Sol route implementation; main serialized generation, builds and native controls. Final bounded review found no residual issue. |

Physics SHA-256:
- `project/engine_field_values.gbsres`: `fa83412757d818e45e05e3d27ded6740d3a02c3f6e64bff0af388a6e06138926`
- `assets/engine/src/states/platform.c`: `26feb227f341e995d6be1a3a557e621007fb6d9431935bdb44f7504b949e593b`

The next plan items are uninterrupted campaign play and player/hardware review.
The completed scope here is the training/town playtest and household route
increment; it is not a claim of final campaign or hardware acceptance.
