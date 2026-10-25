# 🌩️ Redesign brief — "Storm Climb" (action platformer)

> Supersedes the splice collect/connect/cut loop in `game-design.md` §"Decisions
> from the design review" for gameplay purposes. The fiction, characters, and
> visual direction are unchanged. Status of user decisions, 2026-10-25:

| Decision | Value |
| --- | --- |
| Core | **Action platformer** — the climbing and dodging IS the game |
| Fiction | **Keep** storm + mountain + five villagers + Mister CFE the electrician |
| Difficulty | **Friendly expert** — easy to learn, hazards grow teeth with altitude; no permanent fail state |
| Process | **Prototype-first** — playable slice each milestone, tested by Abe in the browser preview |

## Pitch

The storm is tearing the mountain apart while you climb it. Repair checkpoints
(the five homes) are your lifeline — power one and it becomes your respawn
point — but getting to each one means platforming through whatever the storm
has thrown across the dark mountain face: falling debris, wind gusts, live
cable. Higher = angrier. Unlimited retries; time pressure comes from the
mountain itself, not a clock.

## Player verbs (v1)

| Verb | Input | Notes |
| --- | --- | --- |
| Run | D-pad left/right | smooth, responsive; walk speed ≈ 1 px/frame baseline |
| Jump (up) | A | hold for height; through one-way platforms from below |
| **Descend (NEW)** | **D-pad down + A** | drop through the one-way platform you stand on (`FEAT_PLATFORM_DROP_THROUGH`) |
| Land safely | everything | one-way platforms mean falling back down a level is always survivable — the vertical world is honest |

Engine fields to enable (currently all off in `engine_field_values.gbsres`):
`FEAT_PLATFORM_DROP_THROUGH = 1`, `FEAT_PLATFORM_COYOTE_TIME = 1`,
`FEAT_PLATFORM_RUN = 1` (test in playtest; keep only if it feels good).

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

## Structure

Vertical climb in 2–3 linked PLATFORM scenes (level grows taller than one
CGB scene allows). Bottom → top: substation → House A → … → House E → mountain
summit finale. Homes are **checkpoints**: powering one moves the respawn point
(no dialogue-gated inventory loop). End of v1: powering all five = the storm
breaks at the summit (finale scene TBD after M-P2).

## M-P1 — first playable slice (current work target)

One scene, `storm_climb`, ~20×40 tiles: substation at the base, debris +
gust hazards along the climb, House A (Marta) at the top = the slice's
goal-checkpoint. New verbs verified headless (drop-through + coyote time +
jump). No HUD beyond checkpoint feedback. Success = Abe plays the climb in
the browser preview and says "yes, this feels fun" — the feel verdict is the
deliverable, the layout is disposable.

## Explicitly out of scope for M-P1

Title screen, NPCs/dialogue systems, new music (keep `cfe_village_1`), retored
splice inventory, ending scene.

## Non-negotiables

- All content via deterministic generators (`tools/`); no hand-edited
  `.gbsres`. The old scene's hand-edits are exactly the delegation this
  redesign must not repeat.
- Every feature verified by the proven loop: build → headless variable
  assertions → browser preview.
