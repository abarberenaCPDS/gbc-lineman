# Current handoff — campaign polish

**Latest:** Abe played and supplied five screenshots. Route-quality revision is
now the priority: upper/lower bypasses and redundant hazards, plus a proposed
walkable top-down hub. See PLAYTEST_FEEDBACK.md. This was feedback/advice only;
no geometry or map-control expansion has been implemented or approved. Browser
inventory still reports unavailable host; desktop discovery works.

Worktree `/Users/abe/src/modretro-chromatic/gb-mr-cfe-campaign-polish`, branch
`feat/campaign-polish`, VERSION `0.20.1-dev`. Baseline tag `v0.20.0-dev` at
`0804abb` preserved. Main/local config/stash unchanged. Fixes `238f645`, `abd18b5`.

**537 tests** now pass;647 earlier campaign outputs plus7 new deterministic map
outputs. Production scenes/launch unchanged.
Recorded route now reaches all four homes,20 lines, report/title/idle replay and
actual next START. Cross-scene cable recovery and gully return ascent pass;
failed attempts retained. See CAMPAIGN_PLAYTEST.md for exact frames/checkpoints.

Campaign is on earlier candidate `de0b3594...`, ROM
`build/rom/lineman-campaign-polish-optimized.gbc`; its exact worker/checkpoints
must never be restored into a changed cartridge. Continuation recording
`artifacts/playtests/campaign-after-amara` stopped at29768 as needs-review.
Final source board uses event-driven native waits (`abd18b5`), independently
regressed/performance checked. Final production ROM SHA
`44c1eb40271257b35bc5ba8ff6d1b75f0f5db01b8e9c6dfacf140d240bff55f5`.
Full final-cartridge route and human difficulty/listening/hardware remain open.

Step2 one-state prototype is now ready: see DISPATCH_MAP_PROTOTYPE.md for the
live preview, exact ROMs and native capture. Selected project is the isolated
`build/diagnostics/dispatch-map/mr-cfe.gbsproj`, not the production root. It opens
WO-0413 with Amara lit and Neighborhood Hero; one A enters Hiroshi's existing
briefing. Final native SHA c38e235f...; all native recordings stopped/sessions
closed. The preview remains live with no player at last status. Browser host
still unavailable; human feel/listening/hardware remain open.

Wait for Abe's playable map approval before variants or household/ending expansion,
as NEXT_PHASE_PLAN.md explicitly requires. Do not mistake the fixture's seeded
household state/launch for campaign progress or production integration. Source
contracts/generator/tests and seven map resources are tracked; build outputs are
ignored. Keep0.20.1-dev until production integration merits a version decision.
No release tag/merge/push/flash.

---

## Previous handoff (historical)

# Session handoff: hero variants (November 7, 2026)

Continue in `/Users/abe/src/modretro-chromatic/gb-mr-cfe-experience`, branch
`feat/experience-feedback`, VERSION `0.20.0-dev`. Main checkout remains untouched.

Storm Worker is the active gameplay hero everywhere in the campaign/labs.
Neighborhood Hero is the default intro art and an independent reusable story
sprite. The original intro hero remains available with `--intro-hero classic`.
The nine-shot sequence, captions/music/timing and gameplay hitboxes are preserved.

**517 tests pass**, 647 deterministic generated files; native intro, title,
opening repair/movement, carried jump, Shock and respawn checks passed. Both
variant ROMs built. Production logo launch and Neighborhood default are restored.
See [HERO_VARIANTS.md](HERO_VARIANTS.md) for exact commands, hashes and captures.

Current preview:
<http://127.0.0.1:50913/398fbd351b218eff07550b104a16dfe9de07be63989710d25c07c14f5c2e0d9e/>.
It serves the new hero build; open listener, no players attached at final check.
Browser automation failed with “The browser access host is unavailable.”
Human motion/visual review and hardware checks remain open. All task-owned
native emulator sessions are closed; preview is left open.

The historical unresolved preview/save below belongs to its old owner. A fresh
MCP session had no live preview and created the new listener without retrying or
closing the old uncertain operation. Old export and saved-state files are kept.
No merge, tags, remotes or hardware flash were changed.

---

## Previous handoff (retained evidence)

# Session handoff: experience pilots (November 3, 2026)

Continue in `/Users/abe/src/modretro-chromatic/gb-mr-cfe-experience`, branch
`feat/experience-feedback`. Main checkout and its uncommitted review/local config
are preserved. VERSION `0.19.0-dev`; no tag, merge, remote or flash changes.

## Current implementation

- `32f3ba1`: R1–R4/R7 feedback prototype: named/need-specific rewards, once-per-job
  remote cable-return guidance, one shock cue, less routine modal text, short
  household-completion signature. See `SESSION_SUMMARY_2026-11-03.md`.
- Follow-up: **R8** crest span becomes persistently safe after line 5 repair;
  immediate cleanup and queued-phase guards; explicit arc actor binding through
  the final-box custom script. Only this span changes; first-pass waits unchanged.
- **R10** new separate 8s D-major ending reprise, report→title; title idle story
  replay still explicitly restarts Intro B, opening starts gameplay music.
- See `GAME_EXPERIENCE_REVIEW.md`, section “Continuation: R8 and R10 candidates,”
  for exact native recordings, scoped evidence, and remaining human gates.

## Verification

**512 tests pass**, all profiles regenerated, **645 files** unchanged on repeat
generation. New UGE binary decoded notes/instruments/effects/orders match source;
repeat render identical. All 38 existing music/engine/settings hashes unchanged.
MCP health 0 errors/warnings/info. Test starts restored; production boots logo.

- Native final: `build/rom/lineman-experience-pilots.gbc`, 524288 bytes, SHA-256
  `a61696cebd77482bea71cf8443133d9b9f0d4816830046e915ec5ffe2d216a83`.
  Source debug: Abe's Games Logo at frame 120.
- Web export: `build/web-experience-pilots`, SHA-256
  `98c45eae463a3702d2b218fe3ef4ff563317f1bf98a367db5f3a1bfde618372d`.
  Build succeeded; not installed into the live preview.
- Retained native evidence: `artifacts/playtests/experience-span-pilot` and
  `experience-ending-pilot`. Seeded fixtures and SELECT→production box dispatch
  are documented; they do not prove full-game, human taste or hardware acceptance.

Regenerate ending with managed Python:
`tools/make_project.py tickets --render-music --verify` (offline installed Docker
image). Other profiles retain their normal commands.

## Preview close unresolved — preserve before recovery

Saved old Chrome player at frame10600, state ID
`07c33040fc5e3b34c4a9a8d190abf6eb73d11368a0ba637eb6ea26a42139ea97`.
Exact old ROM is `3f53f857...`; keep old `build/web-experience` export for it.
Player is paused. Do not restore this state into the new ROM.

Attempt to show the successfully built new export returned:
**Browser recording close acknowledgement is UNKNOWN.**

Status confirms old listener remains open with unresolved closure. Do not replay
the uncertain close, force a replacement, kill its process, or erase recordings.
Resolve original close/plugin ownership before publishing the verified new export.
Chrome automation host unavailable; no browser or listening verdict claimed.

Old URL (serves R1–R4/R7, **not** R8/R10):
http://127.0.0.1:56988/aac254e162594eccf2a143c73c41faeb4d9e65a2a2865320c3fa0ff5085c6a2e/

## Next human checks

Compare crest before/after repair and reentry; audition report/reprise/title/idle
replay; review pickup/connection/hit comfort over full jobs and two gameplay loops.
R5/R6/R9 hazard/handoff/Carry/resident/device recognition remains evidence-led;
no extra audio warning, marker/art sweep, or lighter arrangement added. Human
listening and physical Chromatic acceptance remain open.

Continuation prompt: “Read docs/HANDOFF.md and the experience review continuation.
Preserve the captured old preview state and resolve its original UNKNOWN close
without replaying it. Review the verified R8/R10 candidates with Abe and keep native,
browser, listening and physical-device evidence separate.”
