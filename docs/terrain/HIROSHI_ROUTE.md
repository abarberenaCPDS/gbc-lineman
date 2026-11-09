# Hiroshi: from Wind Ridge to the lakeside porch

Variant 1 uses both existing 64×18 scenes. It keeps the five line IDs, repair
variables, cross-scene cable, arrival and exit coordinates, and porch payoff.
There are no low ceilings. The player can clear a timed hazard with a good
jump; short jumps and missed landings have nearby places to recover.

| Carry | Approach and crossing | Repair, rest, or recovery |
| --- | --- | --- |
| 1, feeder | Pole at (6,11); jump to the timber span, where boards 9–11 can creak. | T1 at (16,8) on a broad ledge. Below the bridge, return to the first rock to climb back. |
| 2, west | Pole at (20,8); step down through columns 23–26 and see the fallen line before its live arc at 31–32. | Clear floor on either side of the arc; one rise to T2 at (36,11). |
| 3, middle | Pole at (40,11); cross the pennant-marked gust at 47–49. A fall at 43–45 leaves a one-step climb to either bank. | Lee at 50–53, then the wide shelf into Saddle. Carry survives the seam. Saddle's high landing matches the outgoing tier; the step at 7–8 restores that height on a reverse trip. The hidden cable at 13–14 precedes T3 at (17,11). |
| 4, east | Pole at (21,11); cracked timber at 24–26 leads to a gap and a gust at the island lip, 31–33. | Clear floor at 28–30. T4 at (36,11) has a B reach zone wholly past the gust; the checkpoint at (38,11) sits between T4 and the next pickup. |
| 5, house | Pole at (39,11); a short gap separates the island and porch. The porch lip has a gust at 47–49; floor 44–46 is outside it. | T5 at (52,11), checkpoint (56,11), then Hiroshi and the concentrator. The porch opens over the lake; two cabin windows keep their existing warm palette swap. |

Hazards dropped from 16 to seven by removing overlapping upper and lower
lanes. This leaves one exposed crossing per approach, with a pause to do
actual work between the two Saddle gusts. Each gust keeps its existing
warning, burst and calm timings. Pennants mark its extent even when the
actor is hidden. The sheltered floor pockets have granite rises at their
edges; they serve as recovery and cautious approaches, not separate errands.
The moon, shoreline roofs and dock sit behind the route without changing
collision or claiming the live-wire palettes.

The generator writes manual-palette index proxies; the RGB source review
sheet is `build/review/hiroshi-lakeside.png`. It shows no runtime sprites or
HUD. Source checks counted 224/249 indexed tiles in Wind Ridge and 243/260
in Saddle, and 6 and 8 authored actors respectively. Both maps pass the
coarse movement, seam recovery and sprite budget checks. The archived
64×36 roof pilot pins its own coordinates and legacy art so its tests do
not inherit this redesign.

Exact-ROM checks: carry the third cable through both sides of the seam,
retrieve it from Wind after a missed Saddle crossing, try a short and held
jump over each gust, wait on the island through a full cycle, and take the
porch route to the warm windows and town return. Check the carried sprite
against the HUD on a held jump from the highest shelf. Static checks cannot
establish warning readability, native stopping distance, or player feel.

## Integrated native evidence

See [the route playtest report](../LAKESIDE_ROUTE_PLAYTEST.md) for the completed
focused checks, failures and retries, exact ROM identities, and remaining human
and full-campaign gates. The prospective play notes above describe review goals;
the report records what has actually been verified.
