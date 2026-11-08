## Current direction — terrain review and full campaign (November 8)

Abe rejected the experimental low ceilings and requested a terrain/mission design
plan with consultant agents. Preserve jump physics. Priya descent and Emil layout
are positive references; unused areas and scene seams need review. See
[MAP_DESIGN_PLAN.md](MAP_DESIGN_PLAN.md) for the reconciled proposal and gates.
The route prototype is not accepted for integration. Hub follows this design work.

Full production campaign recompiled from the logo, without prototype geometry:
`build/rom/lineman-full-campaign-2026-11-08.gbc`, SHA-256
`2fd969ca59bd833cc0e19902371344b5648f7f4cd2704ccecfbb691974fd41e8`.
Header and native opening boot passed; full human play remains pending. Flash is
explicitly deferred until Abe says ready. Browser project switching hit UNKNOWN
again; current preview is not the full-game build. Details in the new plan.

---

## Preview connection restored — November 8

User restarted the MCP connection; fresh selection succeeded. Revision3 cached
web export opened successfully and its opening briefing was visibly verified in
Chrome (tab2125938238). Listener15a91173ce4e657ec61ba9b517f1c9a6 is open.
[Play revision3](http://127.0.0.1:55358/be7a6938267af796deffbe9339cb59396018cd10f9ddc2c8915505a8759028fc/). This supersedes the preview restart blocker below.
Human route acceptance remains pending; browser gameplay was not automated.

---

## Latest update — November 8, route revision 3

Widened the copied Saddle rest window from12px to36px without changing physics.
Native full-route regression completed five repairs/home and returned to Wind.
Forward and reverse240-frame rest checks passed; porch OAM peak6/10. Full Python
suite passes. Native ROM and separate official web export built; exact evidence
and remaining gates are in `RIDGE_ROUTE_PILOT.md`.

Abe authorized discarding the old preview. No old players remain connected, but
the MCP retains its UNKNOWN close state and offers no reset. Automated access to
Codex settings is denied. User was asked to reconnect `lineman-workspace`; after
reconnection select the normal route fixture and open cached `build/web-route-v3`.
Do not call an old URL revision3. Hub remains next after the route human pass.

---


# Lineman — campaign polish and neighborhood map plan

Approved direction: Abe accepted this plan and asked to resume implementation in
a new session. Implementation has begun in the campaign-polish worktree. Step 1 remains in
progress; see [campaign investigation](CAMPAIGN_PLAYTEST.md) for the three
fixes, restored board performance, exact-ROM evidence and outstanding full-route checks.

## Current progress

- 🔄 Step 1: automated full-route investigation is complete, but Abe's human
  playtest identifies upper/lower-lane bypasses and redundant hazards. Reopen
  route-quality design before further expansion; see [feedback](PLAYTEST_FEEDBACK.md).
- 🔄 Step 2: the one-state dispatch map was played. Abe suggests a top-down
  presentation; a small walkable hub is approved for isolated preparation after
  the route pilot. Integration and human acceptance remain pending.
- ⬜ Steps 3–5: restoration additions, ending map and hardware.
- Branch `feat/campaign-polish`, sibling `../gb-mr-cfe-campaign-polish`,
  VERSION `0.20.1-dev`. Baseline tag `v0.20.0-dev` is preserved.
- Recorded route reachability is complete; address the human route-quality
  feedback before integrating the walkable hub. The old copy-ready prompt
  below describes the original kickoff; reuse this existing worktree.

## Starting point (tagged baseline)

### November 8 implementation order

Abe confirmed the 64×36 route pilot and small walkable top-down hub, requested
parallel subagents, and specified route first, then validation/hub progression.
The route worker owns an isolated Wind Ridge generator; the hub worker prepares
an isolated map and directional hero derivative. Independent route review checks
the easiest bypasses, recovery and both travel directions. Main owns integration,
builds and runtime verification. Production stays unchanged until these pilots
are reviewed. Browser access now works, but the current MCP session is scoped to
the old dispatch-map fixture; configure its workspace before building the new
prototypes. Abe requested help with that configuration after source work is ready.

- Game: **Lineman: After the Storm**, VERSION `0.20.0-dev`.
- Hero implementation: `6aeb34f`; accepted by Abe. Storm Worker is used throughout
  active gameplay; Neighborhood Hero is the default intro actor and a separate
  reusable story asset. Classic intro art remains selectable.
- Experience feedback, safe repaired crest span and ending reprise are integrated.
- All completed changes are merged into `main` and published to
  `git@github.com:abarberenaCPDS/gbc-lineman.git` (`origin`). Branding cleanup:
  `ed13fb1`. Read current Git state before starting.
- Latest implementation evidence: 517 passing tests, 647 deterministic generated
  files, native intro/movement/repair/Carry/Shock checks. These are prior checks,
  not a full-campaign playtest or hardware acceptance of this build.
- Read [HERO_VARIANTS.md](HERO_VARIANTS.md), [PROJECT_PLAN.md](PROJECT_PLAN.md)
  and [GAME_EXPERIENCE_REVIEW.md](GAME_EXPERIENCE_REVIEW.md) for contracts,
  evidence and remaining acceptance gaps.

## Recommended sequence

### 1. Play the complete campaign and fix its biggest frustrations

Follow the actual route from logo to final report, through all four households.
Check instructions, route clarity, cable return trips, checkpoints, internal scene
transitions and repeated hazard failures. Retain inputs and exact-ROM evidence;
record where a player hesitates and why, alongside completion/death counts where
available. Distinguish seeded diagnostic tests from uninterrupted play.

Prioritize the three most consequential frustrations found. Make targeted fixes
and replay those sections before adding mechanics. Ask Abe to assess feel and
clarity through the current preview; automated success is not player acceptance.

**Exit:** all four jobs and the ending are reachable, major reproducible blockers
are fixed, and remaining feel/recognition concerns are documented.

### 2. Prototype a neighborhood map between jobs

This is the next feature priority. Use **Neighborhood Hero** on a simple dispatch
screen connecting Amara, Hiroshi, Priya and Emil. Identify the next work order
and show completed homes lighting up. Keep the first version small and readable;
reuse the campaign's actual progression variables rather than maintaining a
second set of completion flags.

Prototype one map state before producing all variants. Make the next action
obvious and keep advancement quick. Preserve the existing order of jobs; this
plan does not require free roaming, a new map-control system or a new level.
Decide whether to integrate with the work-order card or place the map beside it
based on pacing, avoiding redundant screens.

**Exit:** the player can identify the current job and restored households at
native size; entry, advancement and completion states match real campaign state;
Abe approves the playable prototype before expanding it.

### 3. Make household restoration more personal

Audit the device transformations and reactions already present, then strengthen
only what is missing or hard to notice:

- Amara: refrigerator running and food preserved.
- Hiroshi: oxygen concentrator operating again.
- Priya: workstation returning to use.
- Emil: stove warming and dinner possible.

Use a short device change and character reaction, coordinated with the existing
household completion cue. Avoid repeated dialogue, duplicated rewards or long
forced pauses. Respect once-only completion behavior and reentry persistence.

**Exit:** each household has a distinct readable payoff, plays only as intended,
and remains comfortable when the player returns later.

### 4. Give the ending a visible payoff

Revisit the neighborhood with all four homes illuminated, then show the final
report with the existing ending reprise. Reuse the map art and actual completion
state where practical. Preserve the title/attract-loop music handoff and the
existing nine-shot opening sequence.

**Exit:** the ending visibly reflects the player's work; report → title → idle
story replay remains correct, with no duplicated or abruptly restarted cues.

### 5. Polish on the physical Chromatic

Check Storm Worker's silhouette against every scene, foreground/background
separation, warning readability at 160×144, dialogue and map legibility, and
sprite flicker during busy sections. Listen to music and repeated shock,
pickup, repair and household cues through the device speaker.

Use the verified exact ROM and the deployment skill. Streaming/capture and
cartridge flashing are distinct actions; obtain any required device/write
approval in the new session. Do not treat old approvals as proof of new hardware
acceptance.

**Exit:** retain the tested ROM identity and Abe's device feedback; resolve or
explicitly document remaining visual/audio issues before a release tag.

## Implementation boundaries

- Keep Storm Worker for gameplay and Neighborhood Hero for story/map use.
- Preserve the existing intro sequence and classic-art option.
- Edit deterministic generators/contracts, not generated PNGs or scene JSON.
- Register new scenes before generation; preserve stable IDs, palette slots,
  collision rules and the current movement behavior unless a playtest justifies
  a targeted change.
- Inspect existing map/work-order/device/ending code before adding duplicates.
- Use separate owned tasks for independent work, up to five subagents within
  available harness capacity. Select appropriate available models; main alone
  owns project selection, builds, emulator and preview operations.
- Verify palette/tile limits, compiled behavior and sampled runtime OAM. Keep
  source, native, browser, listening and hardware evidence separate.
- Use a fresh sibling worktree and feature branch based on current `main`.
  Preserve local `opencode.jsonc`, the pre-merge review stash and prior recordings.
- Refresh the plan/handoff after each work burst. Apply SemVer based on actual
  changes; do not create a release tag or flash automatically.

## Handoff prompt — paste into the next session

```text
Continue Lineman: After the Storm from docs/NEXT_PHASE_PLAN.md.

First read AGENTS.md, docs/PROJECT_PLAN.md, docs/HANDOFF.md,
docs/NEXT_PHASE_PLAN.md, docs/HERO_VARIANTS.md and docs/MCP_TOOLKIT.md.
Inspect Git state and origin/main. Completed hero/experience changes are already
merged and pushed; create a fresh sibling worktree and feature branch from the
current main. Preserve opencode.jsonc, the pre-merge review stash and recordings.

Implement the approved plan in order: (1) full-campaign playtest and the three
biggest evidenced fixes, (2) a small neighborhood dispatch-map prototype using
Neighborhood Hero, (3) distinct household restoration reactions, (4) an all-lit
neighborhood ending leading into the report/reprise, (5) Chromatic visual/audio
review when the device is available. Audit existing features first and avoid
duplicating work-order screens or completion effects. Present the playable map
prototype for my review before expanding it.

Keep Storm Worker as the gameplay hero. Preserve the existing nine-shot intro,
its music/timing and the classic intro-art option. Use generators/contracts and
native GBC assets. Use parallel subagents for independent work, up to five within
the available capacity, with suitable available models and disjoint files. Main
owns all MCP selection/build/emulator/preview operations.

Verify the complete route and relevant regressions on the actual built ROM;
record evidence and separate automated results from human feel/listening and
hardware acceptance. Do not assume an old localhost preview URL is alive:
inspect current MCP preview status and safely recover/build as needed. Preserve
unknown operations and saved players; never retry an unresolved close blindly.

Proceed with authorized implementation without repeating routine permission
questions. Keep changes reviewable, update documentation and report concrete
limitations. Do not flash hardware or create a release tag without the required
explicit approval. Start with the full-campaign playtest, not a new feature.
```
