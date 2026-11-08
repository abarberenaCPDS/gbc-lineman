# Lineman — archived vertical-slice design

> Historical design for the retired Storm Night slice. Its splice loop and five-house layout are superseded; see [README](../README.md) and [PROJECT_PLAN](PROJECT_PLAN.md) for current Lineman gameplay.

## Player-facing concept

After a tropical storm cuts power to a lonely mountain, climb the slope,
reconnect five homes from the substation upward, and check in with the locals.
The game has no score. Dangerous storm water and live wires cause a respawn;
lives are unlimited.

## Decisions from the design review

- **Level:** one vertical-scrolling PLATFORM scene, 20×36 tiles. Five houses sit
  along the climb; the connection order is bottom-up.
- **Controls:** D-pad moves, A jumps, B interacts. GB Studio's platform run
  feature is disabled and B is assigned to interaction.
- **Fail state:** hazards respawn the player at the substation. Retries are
  unlimited; there is no countdown or permanent game-over state.
- **Art direction:** use the samples as composition references, not source
  pixels. Sample 003's opening composition calls for an ALPINE van, substation,
  timber house, `B: PULL CABLE`, and a `0/5 houses` HUD. The climb should read
  as sample 002's dark cavern with suspended bright-edged platforms and glowing
  cable links; include sample 005's airborne worker/tether moment where the
  refined player art supports it, and use samples 004/006/008 for spikes, gaps,
  and bridges.
- **Audio:** village stage 1 starts with play, stage 2 begins at two repairs,
  stage 3 at four repairs, and the win cue plays on the fifth. Jump, death,
  pickup, place, sparkle, connect, cut, and victory effects support the loop.

## Current slice and remaining review

The active start is the 20×36 Storm Night PLATFORM scene. The separate 32×32
top-down village remains available but is inactive. The platform scene has
five house actors, a substation, six hazard zones, four loose splice pickups,
ordered connect/cut progression, visible cable spans, powered-house lighting,
and respawn triggers. The player starts with one splice; four more are
collected in the level, and repairs consume them while cutting refunds one.
The three former standalone local actors were repurposed as pickups; residents
remain represented in the named house interactions, but are not separate
on-level NPCs. Cable runs are fixed vertical spans, not a free-form rope/tether.

The provided sample PNGs are visual references only and remain untouched. No
scene references a sample background; their high-color pixels are not copied
or used as gameplay backgrounds. Their 1/10 splice motif is adapted to a
truthful 1/5 inventory for this five-home game. B picks up splices and pulls,
connects or cuts the fixed cable runs.

The slot-4 Moss ramp is now the lime platform-edge ramp
`0B1710, 1A3520, 347A36, 7BE35B`, selected for clear platform readability
against the dark cave. The full five-home run and manual/browser review of the
splice collection/refund loop, hazard respawn, physical Chromatic readability,
and human audio taste still need a dedicated play session. PyBoy has confirmed
the first pickup, repair consumption, and cut/refund state changes.
