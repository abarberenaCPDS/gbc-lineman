# Mister CFE — vertical-slice design

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
five house actors, three locals, a substation, six hazard zones, ordered
connect/cut progression, visible cable spans, powered-house lighting, and
respawn triggers. Cable runs are fixed vertical spans; B directly performs
the repair interaction rather than carrying a free-form connector.

The provided sample PNGs are visual references only and remain untouched. No
scene references a sample background; their high-color pixels are not copied
or used as gameplay backgrounds. The HUD shows houses linked;
sample 003's `1/10` loose-splice count is deferred until actual pickup sources and
collection logic exist, so it is not presented as a false counter. B is mapped
 to the existing platform-interact action and prompts `PULL CABLE` at the
 repair points.

The slot-4 Moss ramp is now the lime platform-edge ramp
`0B1710, 1A3520, 347A36, 7BE35B`, selected for clear platform readability
against the dark cave. The full win path, hazard respawn, physical Chromatic
readability, and human audio taste review still need a dedicated play session.
