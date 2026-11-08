# Campaign investigation — first implementation burst

November 7, 2026 · `feat/campaign-polish` · VERSION `0.20.1-dev`.
Baseline: annotated tag `v0.20.0-dev` at `0804abb`.

## Status

Step 1 is **in progress**. The normal recorded run reached Amara's first two
repairs and repeated carry-3 failures. It did **not** finish Amara, the four
households, or the ending. The focused fixtures below are seeded diagnostics,
not uninterrupted campaign completion. Map work has not started.

## Changes

1. **Cracked boards measure footing rather than body-trigger overlap.** The
   24px worker could overlap a board trigger during an ascent from below. The
   old timer waited 50 frames, then accepted a subsequently rearmed trigger as
   continuous standing. A following jump could therefore land on an almost
   expired board. The shared board helper now checks player pixel position and
   counts consecutive foot-contact updates. Leaving resets the warning; board
   timers use independent actor-local variables. All job and lab generators use
   the helper; stable actor/trigger IDs, geometry, collision bounds and the
   nominal 50-frame warning remain intact. Native visible warning measured
   approximately 51 frames. The first candidate doubled that interval through
   redundant WAITs; it was rejected and corrected before finalization.
2. **Amara dispatch runs once per campaign.** Flag 54 records dispatch separately
   from repaired-line count. First entry still shows WO-0412 and initializes the
   job. A street round-trip returns directly to the climb even with zero lines
   repaired, preserving progress and skipping the card and climb briefing.
   Service Opening's own controls page still appears on street entry.
3. **Title START begins a fresh campaign.** It clears real household, line,
   service, carry, dispatch, checkpoint and feedback state before entering the
   opening. Intro theme 14 and thread temporaries are preserved. Title idle
   replay does not reset gameplay state.

Contracts/generators own every production change. VERSION and its generated
HUD/title labels are updated to `0.20.1-dev`; intro sequence/art selection,
music, household payoffs, movement settings and hardware remain unchanged.

## Verification

- **528 tests pass** with managed Python: `-m unittest discover -s tools`.
- Repeat generation matches all **647 tracked asset/resource files** byte for
  byte. Production launch remains the logo.
- Final production ROM builds, has valid checksums, and boots logo → story →
  title → Service Opening. Native B repair sets service variable 4 to 1; household
  and pending-job state remains zero. This is a boot/tutorial check, not a full run.
- Exact before/after board comparison uses identical controls: neutral boot to
  frame 300, A8, neutral20, left42, neutral100. Other hazards are disabled only
  in these isolated fixture copies. Before: cable 6 becomes 0 and player returns
  to checkpoint 2. After: cable 6 stays 3, player reaches box-3 zone 103, no reset.
- Corrected standing fixture: neutral180 below the board stays safe; A8 +
  neutral20 lands on it; continued standing produces Break/Shock and the expected
  checkpoint/cable reset. Retained frames show creak around frame333 and break
  around384. Moving off instead preserves the cable through frame470.
- Seeded new-run fixture: at title, homes 0/9/11/13 are 1, chain44=5,
  carry6=5, ticket16=4, service4=1, dispatch54=1 and feedback50=1.
  START120 reaches opening with these all 0, while theme14 remains 2.
- Seeded street fixture: service4=1, dispatch54=1, chain44=0, ticket16=0.
  After dismissing opening controls and moving right, frame386 is Storm Climb
  with gameplay HUD visible, no work-order/briefing, and unchanged zero progress.
- Sampled fixture OAM peaks at 7 objects per scanline, none over 10. This does
  not establish sustained whole-campaign performance or physical-device behavior.

Tests exercise leaving/relanding, from-below overlap, independent board timers,
first dispatch versus repeated zero/one/five-line reentry, and new-game versus
attract-loop reset behavior. Existing hazard/route checks remain enabled.

## Exact ROMs and recordings

All ROMs are 524,288 bytes. Recordings are stopped and retained beneath
`artifacts/playtests/`; no unknown recording was closed or restored.

| Evidence | Recording folder | Native ROM SHA-256 |
| --- | --- | --- |
| Normal baseline investigation, frames0–9808 | `campaign-baseline` | `15b7e2517ee04e976a16537d17ac8657d090085a21f82509fd5f16d34d1ad401` |
| Old board, identical escape inputs | `board-before-escape` | `a0b92ea8b6b291a47774c4a3af751d926c80143b0381609bb84eae1ac3318233` |
| Corrected board, escape succeeds | `board-escape` | `b9ced473fd338e118b1a00f2efd4c89808eb57ba796a9d928d8f2d42da040f8a` |
| Corrected board, deliberate standing failure | `board-footing-corrected` | `b9ced473fd338e118b1a00f2efd4c89808eb57ba796a9d928d8f2d42da040f8a` |
| Seeded title START reset | `new-campaign-reset` | `a441a5fad13437455b66432d251fe35c29521b67c3648fafdb4e714b6e054092` |
| Seeded zero-line street reentry | `street-reentry-verified` | `4636f8b76cab6924cb7eb0f4d87205be14aa6d72eb29bc5ee9390731984633fb` |
| Final production boot/tutorial, frames0–2824 | `campaign-polish-production` | `cf91ae1454f6783a3602c6d29b4e7bb1bfd7065567035bde845177f85eaec6de` |

Production ROM: `build/rom/lineman-campaign-polish.gbc`.
Diagnostic ROMs remain under their respective `build/diagnostics/*/build/rom/`
copies. They preceded the patch-version label regeneration; they establish the
specified logic only. The final production check uses the new version labels.
Baseline session `6303ec072899420190512adb14cdad32` includes a checkpoint at9808
(`checkpoint-b1bb1ea8977447bebdfab89997e4da69`); it is valid only with baseline ROM.
Reviewed board failure: actions1241–1252, frames9648–9727, on branch0001.

To reproduce isolated copies, run managed Python on
`tools/make_campaign_diagnostics.py`, select the desired copy's `.gbsproj`, then
build/debug through MCP. The utility delegates launch settings to the intro
owner and never alters production settings. For the old-board comparison,
copy the board fixture and replace only its `board_02.gbsres` with that resource
from tag `v0.20.0-dev`; keep other fixture inputs identical.

## Preview and acceptance

Web export `build/web-campaign-polish` uses a separate Binjgb ROM:
`af20b48f10e9d12554922c4d731f635fa10a305cf09925f3b65bdf4e3034fba7`.
Current listener, open with no attached players at final check:

<http://127.0.0.1:53104/a181cb4de94e9273b28a472d189a433c6f42a3b9041274b89266a37515d45194/>

Opening the built-in browser failed with “The browser access host is unavailable.”
Browser UI, human feel/listening and physical Chromatic acceptance remain open.
No external-browser fallback, release tag, merge, push, stream or flash occurred.

## Continue in order

1. Resume a fresh corrected production campaign and retain inputs. Finish Amara,
   Hiroshi, Priya, Emil and report; count deaths/return trips and check exits.
2. Probe cross-scene cable loss/backtracking, especially Priya's gully ascent,
   repeated gully hints, premature exit refusals and actual second-loop play.
3. Reassess the most consequential remaining frustrations after the full pass.
4. Only then prototype the map within existing `work_order`, using homes
   0/9/11/13 for lights and ticket16 only as a one-shot pending job. Request
   Abe's playable prototype review before expansion.

Source audit: three households already have device Off→On transformations;
Amara currently has fridge dialogue/window lighting but no visible fridge actor.
Avoid duplicating existing reactions and CLOSED pages. Full details remain in
NEXT_PHASE_PLAN.md. Two read-only/coding agents verified direct MCP status access
but had no selected project; main owned selection, builds, native checks and preview.
