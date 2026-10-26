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
| Opening → climb: exit only after repair | ✅ generator-owned awning exit (18,6 2×4), var4 gate + nudge; 19 opening tests | ✅ ROM `2274855c…`: repaired worker walked into exit → Storm Climb (2,32), var4=1; unrepaired branch not exercised natively | ⬜ | ⬜ |
| Upper climb 18→6 reachable with short taps | ✅ geometry asserts, read-only route audit | ✅ shelves 30→6 at y232…40 with 8-frame taps, no hazard contact (x72/x96/x72 takeoffs) | ⬜ feel | ⬜ |
| Marta checkpoint: visible reward at the door | ✅ doorway trigger (11,3 3×1), warm slot-3 windows, Marta Waiting→Powered, connect SFX, HUD `$00$` | ✅ var0 stays 0 through 12→9 and summit landing; door sets var0=1, windows warm, Marta Powered, HUD 1/1; OAM 6 visible, peak 4/scanline | ⬜ reward feels earned | ⬜ |
| Checkpoint respawn after hit | ✅ hit script: var0 ? House A : START | ✅ ROM `ef64f624…` (same respawn script): debris 4 hit on shelf 9 → reappeared on summit (y40) beside the door | ⬜ | ⬜ |
| Opening service gate opens with the repair | ✅ gate actor Closed/Open on var4 | ✅ ROM `a17ead01…`: Closed before B, Open after | ⬜ | ⬜ |
| Live Wire: pick up snapped cable, carry, plug in | ✅ vars 6/7, pole + box scripts, say() text | ✅ pickup var6=1, carried past falling debris 3, plug var7=1, HUD LINE 1/1 | ⬜ feel | ⬜ |
| Cable drops back to pole on a hit | ✅ drop block before respawn (tests) | ✅ ROM `b187d1e4…`: debris 3 hit while carrying → var6=0, respawn START (var0=0), HUD redrawn, cable sprite back at pole (OAM); re-pickup works; second drop also seen | ✅ "I like it so far" (web `6831f908…`) | ⬜ |
| Junction box texts: "No cable yet" / repeat "Line is live." | ✅ box script branches | ✅ ROM `b187d1e4…`: B with var6=0 → "No cable yet. / Check the pole."; second B after plugging → "Line is live." | ✅ "I like it so far" (web `6831f908…`) | ⬜ |
| Unpowered door: "Still no power", no checkpoint, reward later | ✅ door gated on var7 | ✅ ROM `b187d1e4…`: text shown, var0 stays 0 (debris-4 hit respawned at START); after plugging, door gives fridge payoff, var0=1, HUD 1/1 | ✅ "I like it so far" (web `6831f908…`) | ⬜ |
| 16px hero choice | ✅ climb forces 24px (Abe chose to keep this) | ✅ ROM `b187d1e4…`: SELECT → var5=1 16px in opening; climb plays 24px; var5 persists and opening restores 16px on return | ⬜ | ⬜ |
| Climb → opening → climb re-entry | ✅ street exit (0,30 1×3) → opening (16,9); exit lifts HUD cutoff + hides overlay; climb intro lifts cutoff | ✅ ROM `b187d1e4…` found invisible modal texts (frozen until A) after return; fixed; ROM `1769ebc6…`: texts visible, var4 kept, var0/6/7 reset, gate open, HUD LINE 0/1 HOME 0/1 | ✅ "I like it so far" (web `6831f908…`) | ⬜ |
| Line lights up; Marta's fridge payoff gated on power | ✅ slot-5 index-1 route + door gate | ✅ cyan route after plug; door text + var0=1, HOME 1/1, OAM peak 4/line | ⬜ reward feels earned | ⬜ |
| Full connected arc: repair → climb → checkpoint | ✅ 51 tests | ✅ one recorded deterministic pass, ROM `2274855c…`, frames 300–1584 | ⬜ preview served, human play pending | ⬜ |
| Summit exit → Wind Ridge only after Marta's checkpoint | ✅ trigger (17,3 1×3) gated on var0; refusal steps back 3 tiles, then explains | ✅ ROM `65d76ea8…` (summit-start test build): "Marta needs power first." shown once, hero back on the shelf, HUD restored (ROM `147c23be…` had looped the text: fixed + test); open branch not exercised natively | ⬜ | ⬜ |
| Tomás's job: carry cable past debris + 2 gusts, plug in, power the house | ✅ `tools/ridge.py` contract, 37 ridge + 21 sprite tests | ✅ ROM `e05b693c…`: pickup, carry past debris + gusts, box var8=1 (cyan route), repeat B "Line is live.", door var9=1, warm windows, HUD LINE 1/1 HOME 1/1; dead-line door "Still no power", Tomás dead-line talk; hit while carrying drops cable (ROM `ed6995c1…`, `816ef4ef…`) | ⬜ | ⬜ |
| Wind Ridge house view stays within 10 sprites/scanline | ✅ porch step (32–38, rows 12–14) lifts props off the gust rows; budget test | ✅ ROM `e05b693c…` showed the concentrator's top half dropped (13 OBJs/line); porch ROM `1f52dbdd…`: OAM peak 8, 0 lines over limit, concentrator whole; one-tap hop onto porch, box "No cable yet", porch door "Still no power" | ⬜ | ⬜ |

Evidence rules: project/graphics/static previews establish **authored** state,
not runtime behavior. Headless samples establish only the exact ROM and interval
recorded. Browser feedback establishes human perception, not physical-cart
execution. A valid cart header does not establish boot, save behavior or audio
on Chromatic. Retain recordings in ignored `artifacts/playtests/`; the current
ROM hashes and session IDs are in `PROJECT_PLAN.md`.
