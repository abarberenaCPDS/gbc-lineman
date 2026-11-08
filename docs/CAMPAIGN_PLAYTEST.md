# Campaign playtest and first fixes

November 7, 2026 · `feat/campaign-polish` · VERSION `0.20.1-dev`.
Baseline: annotated tag `v0.20.0-dev` at `0804abb`.

## Current status

Step 1 is **in progress**. A normal recorded run completed all five Amara lines,
her household restoration, WO-0412 CLOSED and the handoff to WO-0413. Hiroshi,
Priya, Emil and the ending still need this campaign pass. Map work has not started.

The completed Amara route uses the earlier candidate ROM `de0b3594...`; the
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

All native ROMs are524288 bytes. Recordings are stopped and retained under
`artifacts/playtests/`; selected stopped intermediates were archived through MCP
when the reservation quota filled. Original-path mappings and all evidence bytes
remain intact. Use recording status/review/retrieve, or restore before making clips.

| Evidence | Recording folder | Native ROM SHA-256 |
| --- | --- | --- |
| Initial normal investigation,0–9808 | `campaign-baseline` | `15b7e2517ee04e976a16537d17ac8657d090085a21f82509fd5f16d34d1ad401` |
| Normal Amara completion,0–8179 | `campaign-optimized-run` | `de0b3594fbc5b7cbc14068965eebf969fe5629f6b2652e7b624d3b2f49ce6c93` |
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

## Preview and remaining gates

Latest web export: `build/web-campaign-events`; separate Binjgb ROM SHA-256
`c6970182614235a0b3c5e4e39a4b9fd3a276716bd3e954da9b5a5e575e7dfd0d`.

<http://127.0.0.1:53104/7f79e9980aed67b2a58e2fb2750d31b57f8494252c56d7651d08dbee59c7e2f7/>

The built-in browser still reports “The browser access host is unavailable.”
URL/state are retained; no external browser was used. Human feel/listening and
physical Chromatic acceptance remain open. No new release tag, merge, push,
stream or flash occurred.

Continue Hiroshi, Priya, Emil and report before the map prototype. Check cross-scene
cable loss/backtracking, Priya's gully return ascent, repeated gully hints, exit
refusals and a real second run. Then prototype within existing `work_order`,
using household flags0/9/11/13 for lights and ticket16 only as a pending dispatch.
Abe must review the playable map before expansion, per NEXT_PHASE_PLAN.md.

Source audit: three homes already have device transformations. Amara has fridge
dialogue/window lighting but no fridge actor. Avoid duplicate reactions/CLOSED
pages. Two workers verified direct MCP status; main owned project selection,
builds, native evidence, preview and recording maintenance throughout.
