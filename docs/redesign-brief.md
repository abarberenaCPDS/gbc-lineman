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

**Implementation status:** Abe accepted the initial movement preview for now.
Down+A descent is headless-tested but can skip multiple shelves (deferred defect).
Coyote time is enabled but timing untested; run remains off. Falling debris and
the new climb theme are implemented; recorded debris contact/respawn is verified.
Timed wind, full route/checkpoint tests, human music/hazard acceptance and visual
production remain pending. See `PROJECT_PLAN.md` for exact build/preview status.

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
| Move | D-pad left/right | acceleration and air control need feel review; no calibrated speed claim |
| Jump (up) | A | hold for height; through one-way platforms from below |
| **Descend (NEW)** | **D-pad down + A** | drop through the one-way platform you stand on (`FEAT_PLATFORM_DROP_THROUGH`) |
| Descend safely | release Down+A after dropping | intent: land on the next shelf when aligned; hazards and missing floor remain dangerous |

Current overrides: `FEAT_PLATFORM_DROP_THROUGH = 1`,
`FEAT_PLATFORM_COYOTE_TIME = 1`, `FEAT_PLATFORM_RUN = 0`.
Drop-through currently uses `DROP_THRU_INPUT_DOWN_JUMP_HOLD`; single-level
descent needs a later pass rather than being assumed solved by this toggle.

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

Vertical climb in 2–3 linked PLATFORM scenes for pacing and distinct areas,
not because the current scene reaches a hardware height limit.
Bottom → top: substation → House A → … → House E → mountain
summit finale. Homes are **checkpoints**: powering one moves the respawn point
(no dialogue-gated inventory loop). End of v1: powering all five = the storm
breaks at the summit (finale scene TBD after M-P2).

## M-P1 — first playable slice (current work target)

One scene, `storm_climb`, 20×36 tiles: substation at the base, debris +
gust hazards along the climb, House A (Marta) at the top = the slice's
goal-checkpoint. New verbs verified headless (drop-through + coyote time +
jump). No HUD beyond checkpoint feedback. Success = Abe plays the climb in
the browser preview and says "yes, this feels fun" — the feel verdict is the
deliverable, the layout is disposable.

## Explicitly out of scope for M-P1

Title screen, full NPC/dialogue systems, restored splice inventory, ending scene.
Music improvement is now explicitly in scope at the user's request:
`cfe_storm_climb` replaces the legacy village track for this scene.

## Visual production gate — M-V1 (approved direction)

The movement preview is a greybox, not the target art quality. Work in parallel
on environment composition, character animation, and hardware/runtime budgets.
Deliver **one polished scene + player animation set + one distinct villager +
one cold-to-warm repair transformation** for Abe's browser approval before
scaling production. Readable silhouettes, intentional palettes, environmental
storytelling and restrained effects matter more than adding decoration.
See `PROJECT_PLAN.md` for the tracked visual lane and acceptance criteria.

## Non-negotiables

- All content via deterministic generators (`tools/`); no hand-edited
  `.gbsres`. The old scene's hand-edits are exactly the source drift this
  redesign must not repeat.
- Every feature verified by the proven loop: build → headless variable
  assertions → browser preview.
