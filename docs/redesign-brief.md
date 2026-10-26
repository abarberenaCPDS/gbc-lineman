# 🌩️ Redesign brief — "Storm Climb" (action platformer)

> Supersedes the splice collect/connect/cut loop in `game-design.md` §"Decisions
> from the design review" for gameplay purposes. The cast and visual direction
> are unchanged; the game structure below is the approved shape of 2026-10-25.
> Status of user decisions, 2026-10-25:

| Decision | Value |
| --- | --- |
| Core | **Action platformer** — the climbing and dodging IS the game; each repair is the payoff |
| Fiction | **Keep** storm + mountain + five households + Mister CFE the electrician |
| Difficulty | **Friendly expert** — easy to learn, hazards grow teeth with altitude; no permanent fail state |
| Process | **Prototype-first** — playable slice each milestone, tested by Abe in the browser preview |
| Structure | **Repair jobs** — one per household, 2–3 linked scenes, three phases (see Structure) |

**Implementation status (in progress, not verified):** the first slice
(Marta's neighborhood) is connected in the project: Service Opening → Storm
Climb → Marta's door. Down+A descent is implemented but can skip multiple
shelves (deferred defect). Coyote time is enabled but timing is unverified; run
remains off. Falling debris and the climb theme are implemented. Timed wind,
Live Wire, Blackout Grid, the other four households, and human music/hazard
acceptance are not verified. See `PROJECT_PLAN.md` for exact build/preview status.

## Pitch

The storm snapped poles and lines across the mountain, and the households on it
have gone dark. Mister CFE, the electrician, climbs out to repair the grid so
each home gets its power back. Electricity matters beyond appliances: food in
the fridge, Internet for work and study, home medical devices, cooking, and
heat and light at night. Each restored house is someone's life coming back on.
Higher = angrier. Urgency comes from the people waiting, not a clock.

## Structure

Each repair job is a **neighborhood** of 2–3 linked PLATFORM scenes, not one
crowded scene (GBC limits: ~20 actors, 8 BG palettes, tile memory). Every job
combines three phases:

1. **Reach the damage — Storm Run.** Precision climbing and dodging: falling
   debris, wind gusts, later live cable.
2. **Fix the line — Live Wire.** Pull the snapped cable end from a damaged pole
   and carry it to the junction box. A hazard hit drops it back at the pole.
   Cable routes are authored background tiles lit by palette swaps; no rope
   physics.
3. **Power returns — Blackout Grid.** The line glows cyan, powered gates and
   doors open, the house warms, and the citizen's need is visibly met.

Households, in order, and what their power restores:

| Household | Restored need | Notes |
| --- | --- | --- |
| Marta | Fridge and food saved | First slice; summit checkpoint |
| Tomás | Home medical device (oxygen concentrator) | Most urgent; placed early |
| Rosa | Working and studying online (computer + router lights) | |
| Kiko's family | Electric stove, dinner | |
| Nuria | Lights and heating for the night | Finale: the lit line runs back down the mountain |

Rules:

- Homes are **checkpoints**: powering one moves the respawn point. No
  dialogue-gated inventory loop.
- No fail timer and no permanent fail state. Urgency is narrative.
- Optional connectors (10 per area, shown like the sample HUD counters) are
  collectibles on harder side routes, not a gating inventory. The old splice
  loop stays rejected.
- HUD per job: `LINE x/1  HOME x/1` style. No other HUD beyond checkpoint
  feedback.
- Finale scene TBD after M-P2.

## First slice — Marta's neighborhood (in progress, not verified)

Service Opening (panel repair opens a powered service gate) → Storm Climb (pole
on shelf 21 → carry cable past falling debris → junction box on shelf 15 lights
the line) → Marta's door (fridge payoff, checkpoint).

Success = Abe plays the whole job in the browser preview and says whether it
feels fun and clear. The feel verdict is the deliverable; the layout is
disposable. Climb music (`cfe_storm_climb`) replaces the legacy village track
for this scene, at the user's request.

Out of scope for the slice: title screen, full NPC/dialogue systems, restored
splice inventory, ending scene.

## Player verbs (v1)

| Verb | Input | Notes |
| --- | --- | --- |
| Move | D-pad left/right | acceleration and air control need feel review; no calibrated speed claim |
| Jump (up) | A | hold for height; through one-way platforms from below |
| **Descend (NEW)** | **D-pad down + A** | drop through the one-way platform you stand on (`FEAT_PLATFORM_DROP_THROUGH`) |
| Descend safely | release Down+A after dropping | intent: land on the next shelf when aligned; hazards and missing floor remain dangerous |

Current overrides: `FEAT_PLATFORM_DROP_THROUGH = 1`,
`FEAT_PLATFORM_COYOTE_TIME = 1`, `FEAT_PLATFORM_RUN = 0`.
Drop-through uses `DROP_THRU_INPUT_DOWN_JUMP_TAP`: one Down+A press drops one
level (B-07; hold mode re-armed the drop timer every falling frame).

## Hazard ladder (friendly-expert ordering), lowest → highest

1. **Falling debris** — visibly telegraphed drops on fixed cycles. Dodge by
   rhythm, learnable in one attempt.
2. **Wind gusts** — surge along marked lanes (respawn if caught); telegraph by
   swaying vegetation/flags before firing.
3. **Live cable** — arcing hazards on the electrician theme; deceptively static
   looking positioned between jump lines.

House rules: hazards never spawn inside checkpoint houses' safe radius;
ascent in any column must remain possible with ≥1 column of clearance (a rule
the old level data already engineered successfully); every hazard must be
visible at least one arch/jump ahead.

## Visual production gate — M-V1 (approved direction)

The movement preview is a greybox, not the target art quality. Work in parallel
on environment composition, character animation, and hardware/runtime budgets.
Deliver **one polished scene + player animation set + one distinct villager +
one cold-to-warm repair transformation** for Abe's browser approval before
scaling production. Readable silhouettes, intentional palettes, environmental
storytelling and restrained effects matter more than adding decoration.
Art references: `assets/backgrounds/samples/` (dark mountain night, lit cabin
with cyan line, cable routes, `x/10` HUD counters).
See `PROJECT_PLAN.md` for the tracked visual lane and acceptance criteria.

The first playable service-opening candidate received positive browser feedback;
Abe selected the 24px electrician over the 16px comparison. The preference
changes the default for this fixture, not the original 16px asset or movement
collision tuning elsewhere. Music taste, climb integration, and physical-device
readability remain separate acceptance gates.

## Non-negotiables

- All content via deterministic generators (`tools/`); no hand-edited
  `.gbsres`. The old scene's hand-edits are exactly the source drift this
  redesign must not repeat.
- Every feature verified by the proven loop: build → headless variable
  assertions → browser preview.
