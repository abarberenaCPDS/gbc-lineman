# Campaign playtest and first fixes

November 7, 2026 · `feat/campaign-polish` · VERSION `0.20.1-dev`.
Baseline: annotated tag `v0.20.0-dev` at `0804abb`.

## Current status

Step 1 route investigation is **complete with acceptance limits**. The recorded
campaign reaches all four household payoffs, all20 repairs, the report, title,
idle story replay and a real next START. Human feel, listening and final-cartridge
whole-route acceptance remain open. The [one-state map prototype](DISPATCH_MAP_PROTOTYPE.md) is ready for playable review.

The completed campaign route uses the earlier candidate ROM `de0b3594...`; the
final board implementation below was then checked separately in native fixtures
and a fresh production boot. Do not describe that combination as a complete
campaign on the final ROM, or seeded fixtures as uninterrupted play.

## Changes

1. **Boards start their warning from foot contact.** A tall hero could overlap a
   body trigger from below; an earlier warning could expire after a following
   jump rearmed that trigger. Each board now checks full player pixel X/Y before
   arming and again before breaking. Its body-trigger enter/leave scripts use
   official `EVENT_ACTOR_STOP_UPDATE` / `EVENT_ACTOR_START_UPDATE` events to cancel
   the old wait and start a fresh update on reentry. Warning uses the native
   50-frame wait; Break8 and uninterrupted Rest60 remain. No polling timer or
   new global variable is needed. Ordinary jumps leaving the body trigger cancel
   the warning; this is not a mathematical claim about every subpixel foot motion.
2. **Amara dispatch runs once per campaign.** Flag54 records dispatch separately
   from line progress. First entry still shows WO-0412 and initializes the job.
   Street reentry returns directly to the climb even before the first repair,
   preserving progress and skipping the card and climb briefing. Service Opening's
   own controls page still appears on street entry.
3. **Title START begins a fresh campaign.** It clears real household, line,
   service, carry, dispatch, checkpoint and feedback state before entering the
   opening. Intro theme14 and temporary thread values are preserved; idle story
   replay does not reset progress.

Edit the generators/contracts, not generated resources. All20 boards share the
helper; actor/trigger IDs, palettes, geometry, movement and hero bounds remain.
Only VERSION's generated HUD/title labels change art. Existing music, opening
sequence, household effects and physical hardware are unchanged.

## Verification

- **533 tests pass** with managed Python: `-m unittest discover -s tools`.
- All **647 tracked asset/resource files** reproduce byte-for-byte on repeat
  generation. Production starts at the logo. MCP health: **0 errors/warnings/info**.
- Final production ROM builds with valid cartridge checksums and boots
  logo→story→title→Service Opening; B repair sets service4=1 at frame2824 while
  all household flags and pending ticket remain0. This is a boot/tutorial check.
- Final board fixture: wait below, jump up, short-hop off and back before the old
  deadline. Cable6 remains3 at frame457; deliberate standing then produces the
  expected Shock, cable loss and checkpoint reset by527. This verifies native
  stop/start cancellation and successful restart, not just authored event shapes.
- Identical escape controls: boot neutral to300, A8, neutral20, left42, neutral100.
  The original board loses the cable and resets. Final board keeps cable3 and
  reaches box-3 zone103 at470. Other hazards are disabled only in this fixture.
- Seeded title START: homes0/9/11/13=1, chain44=5, carry6=5, ticket16=4,
  service4=1, dispatch54=1 and feedback50=1 become0; theme14 stays2.
- Seeded zero-line street reentry: service4=1, dispatch54=1, chain44=0, ticket16=0.
  At386 the player is in Storm Climb with gameplay HUD and unchanged zero progress,
  without the work-order or climb briefing.
- Sampled fixture OAM peaks at7 objects/scanline, none above10. This is not a
  sustained whole-campaign, listening, browser or hardware acceptance claim.

Tests cover body overlap from below, body departure/reentry, restart after a
single-frame trigger visit, fresh full-coordinate deadline checks, stale flags,
scene/culling restart, safe initialization, board ownership/visibility, first-only
street dispatch and new-campaign versus attract-loop state reset.

## Native performance checks

The first per-frame footing implementation slowed the game and was replaced.
The final implementation uses ordinary engine waits and only checks coordinates
at arm/deadline (with a cheap candidate check while approaching a board).

These are completed engine updates per120 native emulator frames, in three
neutral-input windows, using each exact ROM's captured `_game_time` symbol:

| Matched pose | Original board wait loop | Rejected polling | Final event-driven wait |
| --- | --- | --- | --- |
| Quiet shaft, anchor14/20 | 116 / 118 / 118 | 60 / 60 / 60 | 116 / 118 / 118 |
| Standing on board2, anchor11/14 | 111 / 115 / 112 | 93 / 91 / 90 (four-frame polling) | 111 / 115 / 113 |

Standing fixtures extend only board warning waits to10000, keeping the player
alive and all other hazards active. This isolates script load. It is neither a
physical-device FPS measurement nor proof of every busy scene's performance.
Use `tools/diagnose_board_load.py` to generate matched copies, then select/build
through MCP; counters must use the matching captured symbol addresses.

## Exact cartridges and recordings

All native ROMs are524288 bytes. Recordings are retained under
`artifacts/playtests/`; all campaign recordings are stopped. Selected stopped intermediates were archived through MCP
when the reservation quota filled. Original-path mappings and all evidence bytes
remain intact. Use recording status/review/retrieve, or restore before making clips.

| Evidence | Recording folder | Native ROM SHA-256 |
| --- | --- | --- |
| Initial normal investigation,0–9808 | `campaign-baseline` | `15b7e2517ee04e976a16537d17ac8657d090085a21f82509fd5f16d34d1ad401` |
| Normal Amara completion,0–8179 | `campaign-optimized-run` | `de0b3594fbc5b7cbc14068965eebf969fe5629f6b2652e7b624d3b2f49ce6c93` |
| Earned-state continuation,8179–29768 | `campaign-after-amara` | `de0b3594fbc5b7cbc14068965eebf969fe5629f6b2652e7b624d3b2f49ce6c93` |
| Original board escape failure | `board-before-escape` | `a0b92ea8b6b291a47774c4a3af751d926c80143b0381609bb84eae1ac3318233` |
| Final board escape/reentry | `board-events-escape`, `board-events-reentry` | `e436343f441b29039c2de6433a91a9d3d7b8c480cabe14f8a1ada5765a79fb4f` |
| Final production boot/tutorial,0–2824 | `campaign-events-production` | `44c1eb40271257b35bc5ba8ff6d1b75f0f5db01b8e9c6dfacf140d240bff55f5` |
| Quiet final load fixture | `load-events` | `bf713b169c4bcd6187faa8c82518c66bff9e2a902deac17746598ac897c89e3f` |
| Standing final load fixture | `standing-load-events` | `60a978d484e0db943272d2222240b00b2fa2aa18ea649fbaa09b6e9de77f2cd1` |
| Seeded title START reset | `new-campaign-reset` | `a441a5fad13437455b66432d251fe35c29521b67c3648fafdb4e714b6e054092` |
| Seeded street reentry | `street-reentry-verified` | `4636f8b76cab6924cb7eb0f4d87205be14aa6d72eb29bc5ee9390731984633fb` |

Latest production: `build/rom/lineman-campaign-polish-events.gbc`. Earlier ROMs
and their debug artifacts remain; do not overwrite them or restore a checkpoint
into a different cartridge. Diagnostic cartridges are under `build/diagnostics/`.
`tools/make_campaign_diagnostics.py` regenerates board/reset/street copies using
the intro owner for launch settings, without changing production launch settings.

Normal Amara completion: home0=1/chain44=5 at7838; CLOSED then WO-0413 at8179,
with ticket16=2 and Hiroshi home9=0. Checkpoint
`checkpoint-f91d2087ab3b49d6a90c34d7c09a1eef` belongs to `de0b3594...` only.
The initial baseline checkpoint at9808 belongs to `15b7e251...` only. Reviewed
initial board failure: baseline session `6303ec072899420190512adb14cdad32`,
branch0001, actions1241–1252, frames9648–9727.

## Hiroshi continuation and cable recovery

The exact `de0b3594...` campaign continues from the earned frame8179 checkpoint
in `campaign-after-amara`, session `cc4f6244e81e43eea252e3fdf21d529a`, branch0002.
No campaign variables were seeded and no diagnostic checkpoint was restored.

- After two repairs, carried cable3 into Ridge Saddle, then deliberately lost it.
  At10712 carry6=0, chain20=2/lines18=2 remain, and the visible hint says
  "Cable at pole. / Back to / Wind Ridge." Local respawn is safe.
- Walked back into Wind Ridge, crossed the upper whip/gust/cable lanes in reverse,
  retrieved cable3 at its original pole and recrossed to Saddle by11751. No replay
  of the job introduction or loss of repaired lines occurred.
- Line3 repaired12154, line4 by12631, line5 by13066. The all-lines notice
  precedes Hiroshi's concentrator reaction; home9=1 at13372.
- WO-0413 CLOSED is visible13505; onward work order WO-0414 at13811.
  Checkpoint `checkpoint-31a6b79b5c2341fc97bd28a295c1733e` at13631 retains
  the earned handoff state. It belongs only to the exact same ROM/runtime.

This is a checkpoint-linked campaign continuation, not one uninterrupted worker
session and not a full route on the final event-driven board cartridge. Hazard
phase observations used bounded read-only native actor flags; movement and
repairs used ordinary controller inputs. This proves reachability/recovery,
not unaided player recognition or subjective difficulty.

## Priya, Emil, report and actual next START

Same branch0002 continues without further checkpoint restores:

- Priya: line3 at16649; four controlled2-frame Down+A taps each land one shelf
  at17028/17072/17116/17160 (feet17/20/23/26). Line4 at17249. Optional
  return-ascent probes include failed hazard timings, followed by successful
  long-jump recovery26→20 at17830 and20→14 at17954. Progress remains four lines.
- Lower gully failures preserve that progress. Narrow safe columns, solid deck
  edges and premature inputs before landing complicate the final drops. A valid
  landing sequence at anchor79.1875 reaches feet29 at18880 and floor32 at18924;
  cable5 picked at18992 and carried into Signal Porch at19353. This is a
  reachability result, not a claim of comfortable unaided difficulty.
- Priya's line5 notice at19969; workstation/home reaction and home11=1 at20156;
  CLOSED at20284; WO-0415 at20547. Checkpoint
  `checkpoint-8323b00c742b47768fe1a3e83e09ee63` retains that earned handoff.
- Emil: line1 by21692, line2 by22247, cable3 carried into Pine Ladder22619;
  line3 by22979, line4 at23445. Final cable crosses the summit into Rim23950.
  Early entry jump falls to the floor; a normal long jump recovers the catwalk
  without cable loss. Line5 at24649; stove reaction/home13=1 at24827; CLOSED24955.
- Report entered25218; all four homes=1 and each job chain=5. Visible report:
  tickets4/4, lines20/20, all four named outcomes, thanks and credits. Title26460.
  Earned all-home checkpoint `checkpoint-ba74fc934eab476a83d3e5cb6a72172f`.
- Idle story replay at27960 retains all four homes and all four chain counts.
  Return to title29610; actual START opens Service Opening29768 and clears
  homes0/9/11/13, service4, carry6, ticket16, all chains/counts, feedback50–53
  and dispatch54. Theme14 remains1. This tests a real second start after a
  completed campaign, rather than only a seeded reset fixture.

Recording finalized `needs-review` at29768: session
`cc4f6244e81e43eea252e3fdf21d529a`, event digest
`7cbdc0c5a9cdce9f38185b54c9aac8c2fab4a2ee43b9015c486010b826749ee1`.
Final reset checkpoint `checkpoint-e015531047e14feb96ffd9870544647d`.
All checkpoints in this section belong only to `de0b3594...` and its recorded worker.

Remaining difficulty concerns: long versus short jumps, precise gully descent
columns, tall-body contact above shelves, and early rim jumps. Automated phase
reads aided traversal; failed attempts remain recorded. No additional geometry
or movement changes were made on this evidence alone. The event-driven board
fix separately removes the candidate's measured board slowdown.

## Preview and remaining gates

Latest web export: `build/web-campaign-events`; separate Binjgb ROM SHA-256
`c6970182614235a0b3c5e4e39a4b9fd3a276716bd3e954da9b5a5e575e7dfd0d`.

<http://127.0.0.1:53104/7f79e9980aed67b2a58e2fb2750d31b57f8494252c56d7651d08dbee59c7e2f7/>

The built-in browser still reports “The browser access host is unavailable.”
URL/state are retained; no external browser was used. Human feel/listening and
physical Chromatic acceptance remain open. No new release tag, merge, push,
stream or flash occurred.

Route, cross-scene cable recovery, gully return ascent and actual second START
are now covered on the candidate. Full final-ROM campaign, exit-refusal probes
and human difficulty review remain. Prototype within existing `work_order`,
using household flags0/9/11/13 for lights and ticket16 only as a pending dispatch.
Abe must review the playable map before expansion, per NEXT_PHASE_PLAN.md.

Source audit: three homes already have device transformations. Amara has fridge
dialogue/window lighting but no fridge actor. Avoid duplicate reactions/CLOSED
pages. Two workers verified direct MCP status; main owned project selection,
builds, native evidence, preview and recording maintenance throughout.
