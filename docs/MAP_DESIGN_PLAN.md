## Lakeside baseline selected — November 8, 2026

Abe selected variant 1 for the entire game. Implementation order: intro mission,
walkable lakeside town, then mission routes. Preserve jump physics. Increase map
sizes selectively, only where meaningful gameplay requires room. Parallel agent
and economical-model directives are recorded in AGENTS.md. Start the next session
with [LAKESIDE_IMPLEMENTATION_HANDOFF.md](LAKESIDE_IMPLEMENTATION_HANDOFF.md).
No gameplay changes made in this planning/handoff pass.

---

# Terrain and mission design review

November 8, 2026. Planning only; no new terrain implementation approved here.

## Whole-game scope clarified — November 8

[Three mountain-community variants](terrain/WORLD_VARIANTS.md) now cover the
entire campaign, the walkable town and a proposed learn-by-doing Service Opening.
Recommend the lakeside neighborhood; no variant selected yet. Keep jump physics.
Choose world structure before implementing local route changes.

## Earlier local study

[Annotated Saddle comparison](terrain/SADDLE_OPTIONS.md) shows the current route
and two open-air proposals. Candidate B relocates the existing fourth repair to
a service island; five repairs and jump physics remain unchanged. Await terrain
feedback before gameplay implementation. Work continues on `feat/terrain-design`.
The walkable neighborhood hub remains pending after this route-design pass.

## Decision and scope

Abe wants harder, well-placed hazards and missions with purpose. He likes the
jump physics. Preserve jump height, variable hold, air control, acceleration,
braking, collision bounds and camera behavior as the initial design envelope.
Changing terrain to suppress the useful jump arc is not an acceptable substitute
for designing a good crossing.

The Wind Ridge and Hiroshi low rock ceilings are explicitly rejected. Keep the
revision 3 fixture as historical evidence, not a candidate for integration.
Its staircase terrain and increased height are unapproved experiments, not an
accepted visual or terrain direction. The full campaign build uses production
geometry, without those experimental roofs, stairs or enlarged Ridge scenes.

Priya's descent and Emil's overall layout are positive references. Priya's empty
lower pocket and Emil's ascent/next-scene transitions need review. The attached
screenshot documents a quiet lower area under a long catwalk, not proof that
adding an enemy there is the right solution. No scene identity is asserted from
that screenshot alone.

## Consultant review

Two parallel agents contributed read-only reviews:

- Terrain and route consultant (`route_audit`): route topology, recovery floors,
  hazard relevance, scene dimensions and boundary continuity.
- Mission pacing consultant (`payoff_audit`): meaningful mission beats, length,
  difficulty progression, resident payoff and human evaluation.

Both used the parent model; no model override was requested for this review.
Main reconciles their findings with Abe's feedback and owns builds/playtesting.
Source review supports the existence of cheap upper/lower bypasses. The latest
native runs establish completion and stopping margins, not enjoyable placement.

## Agree on the terrain before building another route

Prepare one annotated overview for the first proposed crossing, showing the
existing terrain and two candidate arrangements. Mark the current jump envelope,
walking route, cable pickup, repair destination, hazard warning view, landing,
waiting area, fall recovery and return route. Show the easiest route as well as
the intended one. Keep accepted artwork and physics.

Choose whether the setting reads as an exposed ridge with ledges, a service
catwalk crossing, or another coherent environment before adding structural rock.
In open-air ridge sections, do not introduce low roofs solely to force a wait.
Terrain should make the destination and route legible while allowing skilled
jumping. A valid jump over a hazard is mastery, not automatically a bypass defect.
An entire hazard group that never affects any meaningful route is a design issue.

Classify each quiet space as approach, rest, recovery, scenic payoff or unused
travel. Preserve useful quiet space; shorten purposeless travel. Consider moving
or removing a hazard before adding one. Avoid turning every recovery floor into
a penalty zone.

## Proposed experiments, in order

| Experiment | Preserve | Proposed change | Evaluate |
| --- | --- | --- | --- |
| Wind Ridge / Hiroshi final carry | Jump arc, cable loop, readable warnings, medical-home payoff | First sketch an open-air pickup → visible crossing → broad landing/repair sequence. Relocate one existing timed hazard to a meaningful landing or route rejoin; remove a redundant threat. | Full-held jump, cautious approach, short hops, fall recovery and reverse retrieval. Is the fastest route interesting without a forced crouched passage? |
| Priya descent and porch | The liked descending section | Review one mandatory repair crossing. Compare a shorter lower recovery walk with a clear return step under the catwalk. | Does the quiet area save a mistake, offer a real alternate route, or merely delay the player? Does a proposed hazard create a decision? |
| Emil ascent and scene transitions | The favored level layout | Align exit and arrival elevation, wire direction and landmarks across Hollow → Ladder → Rim. Provide a readable landing/decision point at each seam. | Cable 3 and cable 5 delivery and loss/return; both directions; held movement at a scene boundary; no blind required jump immediately after a transition. |

Do not implement all three at once. Review the first annotated plan with Abe,
then build a small isolated experiment and compare it to the production route.
The walkable hub remains planned, but map/terrain direction comes first.

## Mission length: measure before expanding

The production campaign has five repairs per household, twenty overall.
Hiroshi spans two 64×18 scenes. Priya uses 64×18 → 20×36 descent → 40×18 porch.
Emil uses 64×18 → 20×36 ascent → 56×18 rim. Dimensions alone do not establish
whether a mission feels short or substantial.

During Abe's full-game pass, record per mission:

- Total time, pickup-to-repair time, empty travel and recovery/repeated travel.
- Meaningful route/timing decisions and sections skipped without a decision.
- Where the next repair or route is unclear; first-attempt versus repeated errors.
- Whether warnings are visible before commitment and stopping space feels natural.
- Whether each repair changes the route, reveals progress, or supports the payoff.

Proposed mission rhythm: safe orientation and visible goal → one clear traversal
skill → a repair/rest landmark → a new arrangement or combination of that skill
→ a satisfying final crossing → quiet household payoff. These are beats, not a
requirement for six scenes or extra repairs.

Expand a map only to support a distinct beat, route choice or environmental
reveal. Try redistributing current space first. Compare equal-objective layouts
before increasing repair count. Do not lengthen missions with repeated errands,
longer empty corridors, or forced backtracking. Set a target duration only after
the full-game timing and Abe's desired pace are known.

### Preserve a distinct identity for each household

- Amara: concise learning arc; establish carrying/repairing, then a readable
  ascent and a visible household destination.
- Hiroshi: exposed open-air crossings with landing choices and repair rests,
  ending in a quiet oxygen-restoration payoff.
- Priya: reveal the goal below, descend through planned landings, then approach
  the porch. Preserve the descent that Abe praised.
- Emil: foreshadow the uphill route from Hollow, vary the ascent, then give the
  rim a coherent final challenge and warm household payoff.

These use the existing five repairs. An additional middle beat or longer rim
approach is a hypothesis to compare after the baseline, not an approved increase
in map area, repair count, or duration. No percentage length target is adopted.

Boundary review starts with Hollow right exit `(62,9)` → Ladder `(2,32)` and
Ladder upper exit `(17,2)` → Rim `(3,8)`: source coordinates explain abrupt local
height changes, but do not prove the exact cause of Abe's reported oddness.
Sketch a continuous wire/material/landmark, foreshadow the destination in the
preceding scene, and check arrival feet/camera framing, safe landing and return.

## Validation and acceptance

1. Annotated terrain proposal reviewed before geometry implementation.
2. Generator changes remain isolated; verify production and physics unchanged.
3. Static route, tile and sprite checks; then build the exact native ROM.
4. Play likely easy routes, intended routes, failure/recovery and both scene seams.
   Preserve failed attempts. Sample full Carry artwork and HUD visibility.
5. Abe compares challenge, flow and usefulness of space. A reachability pass does
   not close this gate. Revise placement before adding density or restricting jumps.
6. Integrate only the accepted experiment, then review the next mission.

For Abe's current pass, three useful notes per mission are enough: the best
crossing, the most wasted stretch, and any confusing scene transition. Timings
are helpful but should not interrupt playing.

## Full campaign review build

- Version: 0.20.1-dev; branch `feat/campaign-polish`, base commit `1e28516`.
- ROM: `build/rom/lineman-full-campaign-2026-11-08.gbc`.
- SHA-256: `2fd969ca59bd833cc0e19902371344b5648f7f4cd2704ccecfbb691974fd41e8`.
- Official installed GB Studio CLI compiled the root production project, exit 0.
  The MCP project switch encountered its preview-close UNKNOWN bug, so the
  official compiler was invoked directly. Only the known Node DEP0190 warning.
- 524288 bytes, GBC-only, valid logo/header checksum. Native ROM-mode boot smoke
  observed the normal logo and opening story; no diagnostic progression seeds.
- Recording: `artifacts/playtests/full-campaign-2026-11-08-boot`, 300 frames,
  session `0336e129a39c4435aba10edcb2432792`.
- This is a fresh build and boot check, not a new uninterrupted campaign test.
- Browser still points to the rejected route experiment; do not identify it as
  the full campaign. Prototype browser states were captured before switching.
- No cartridge operation performed. Flash only after Abe explicitly says ready;
  re-inspect this exact ROM and identify the device at that time.
