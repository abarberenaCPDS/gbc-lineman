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
- **Fail state:** a 90-count storm countdown. If it reaches zero, the storm
  wins and the lose track plays. The duration is a tuning value, not a fixed
  story fact.
- **Art:** storm-night colors inspired by the supplied samples, with brighter
  rock edges, warm powered-house windows, and a visible countdown for small
  screen readability.
- **Audio:** intro, main, win, and lose music; jump, death, connect, cut, and
  victory effects. The pickup effect is authored for a later connector-pickup
  pass.

## Deferred alternative — no permanent lose state

The other reviewed direction was to remove the storm timer: unlimited lives
would mean there is no game-over state, and the “losing” cue could instead be a
short sting on each death. Keep this as a future-stage option if the countdown
feels punitive or if the game should emphasize exploration over urgency.

## Current slice and remaining review

The current build has one authored scene, five house actors, three locals, a
substation, six hazard zones, ordered connect/cut progression, visible cable
spans, powered-house lighting, timer loss, and respawn triggers. Cable runs
are fixed vertical spans in this slice, not a freely drawn rope/path; a
carried-connector pickup/place interaction remains a follow-up.

The project validator reports zero errors. Its nine warnings are confined to
the supplied reference images under `assets/backgrounds/samples/`; do not
“fix” or replace those examples as part of the game slice. The full win path,
hazard respawn, physical Chromatic readability, and human audio taste review
still need a dedicated play session.
