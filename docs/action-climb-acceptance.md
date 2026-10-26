# Action-climb acceptance (replaces the rejected splice-loop checklist)

This is an **evidence matrix**, not a prescribed button-by-button playthrough.
`PROJECT_PLAN.md` tracks phase status; this file tracks whether the *new* game
is enjoyable and works. Only mark a row complete with the named evidence.

| Slice / expectation | Authored + build | Headless exact-ROM | Human browser | Hardware |
| --- | --- | --- | --- | --- |
| Service opening: 24px worker is the default, 16px optional comparator | ✅ var5: 0→24px, 1→16px | ✅ fresh boot: 7 objects, peak 5/scanline; SELECT 5→7→5 | ✅ 24px preferred | ⬜ |
| Service opening: B repairs once; Marta reacts, only windows/panel warm | ✅ scene and palette analysis, 22 tests | ✅ both sizes repair, variable 4=1, repeat B leaves 1; 128 changed window pixels | 🔄 art direction liked; interaction feedback not explicit | ⬜ |
| Service opening: sprite/readability budget | ✅ 157 effective BG tiles, 7+UI palette slots | ✅ sampled 24px worker: 7 visible objects, peak 5/scanline | ✅ opening judged "much better" | ⬜ |
| Opening climb theme sounds right | ✅ UGE/source match, ROM event resolves | ✅ game boots with new track (audio quality not established) | ✅ Abe says music works well | ⬜ long loop and actual-device listening |
| Lower climb: accessible catwalks, clear next landing, no false footing | ✅ collision-aligned night/timber/stone lower art + two-tile route assertions; 256-KiB native build | 🔄 24px worker reaches shelves 30→27→24→21→18 using short A taps; full route not tested | ⬜ feel/readability | ⬜ |
| Falling debris: warning safe, fall hits, respawn retains progress | ✅ authored 60f warning + 2px/2f fall | 🔄 warning→fall→contact→base recorded; safe warning and checkpoint preservation untested | ⬜ telegraph feels fair | ⬜ |
| First timed gust: safe warning, active burst, avoidable crossing | ✅ lane 1 native actor; old marker trigger inert, valid 256-KiB ROM | ✅ player at world `(86.8,264)` stood safe during warning frames 489–534; burst reset to `(16,256)` by frame 549 | ⬜ rhythm feels fair | ⬜ |
| Other gust lanes: visible rhythm, avoidable while ascending | 🔄 seven old instant-reset scripts disabled after tall-collider route test; visible markers are inert placeholders | ⬜ re-author one by one | ⬜ | ⬜ |
| Down+A descends *one* shelf reliably | ✅ engine toggle | ⚠️ existing drop-through works, repeated hold may cross shelves | ⚠️ Abe observed multi-level drop; fix deferred | ⬜ |
| First checkpoint then full multi-area route | ⬜ source progression unfinished | ⬜ checkpoint/full route | ⬜ sustained play | ⬜ |

Evidence rules: project/graphics/static previews establish **authored** state,
not runtime behavior. Headless samples establish only the exact ROM and interval
recorded. Browser feedback establishes human perception, not physical-cart
execution. A valid cart header does not establish boot, save behavior or audio
on Chromatic. Retain recordings in ignored `artifacts/playtests/`; the current
ROM hashes and session IDs are in `PROJECT_PLAN.md`.
