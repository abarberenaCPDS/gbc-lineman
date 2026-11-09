# Priya: the creek and broken footbridges

The lakeside route uses the existing three scenes and five repairs. The first
two repairs and the hill-to-gully seam keep their established approach. The
descent and porch change shape within their original scene sizes. In the
diagrams below, coordinates are 8 px tiles and rows count down from the top.

| Beat | Route and decisions |
| --- | --- |
| Creek approach, Signal Hill | Follow the lower feeder trail or the upper timber walk. The visible runoff, radio mast and wire across the summit lead toward the descent. Deliver lines 1 and 2 at the usual pads; take cable 3 through the summit exit. |
| Head bridge, Signal Gully | The landing at (2,4) leaves room to see the gully. Drop off the arrival shelf, bring cable 3 to the right repair bench (16,8), then use Down+A on the intact timber span at row 9. This first deliberate drop is still required. |
| Eroded banks | Pick up cable 4 on the left bench (2,14). The broken right end of row 15 opens onto a wide catch shelf at row 18. The west bank opens below row 21 into another catch at row 24. The center keeps staged Down+A drops for controlled landings. Wait clear of the marked cable, gust and damaged boards. The transformer at (16,26) is visible on the lower east bench. |
| Dry spillway | A missed lower landing can drop to the dry floor. The recovery steps at row 30 lead back toward the lower bench and its repair. After line 4, take cable 5 at (3,32) along the dry floor to the right seam. The two former threats at the foot of the descent are gone, so picking up the cable and leaving no longer require another precisely timed drop. |
| Broken footbridge, Signal Porch | Bridge fragments at row 12, x5–10 and x14–17, leave a three-column gap. The first fragment has cracked boards; a hanging wire marks the second fragment. Below, the creek-bed path crosses the marked feeder arc and reaches the exposed rock step at x11–13. The step offers a way back to the right bank if a jump comes up short. Both routes reach the same dry porch pad. |
| Work and return | The porch bank starts at x18 and stays clear of active hazards through line 5, the workstation and Priya’s door. The line 5 box is at (26,11), with a checkpoint at (28,11). The existing powered home exit returns to town. Before the repair, backtracking across the creek bed and up the gully still reaches cable 5 or the hill. |

Scene dimensions, entry and return tiles, resource IDs for retained elements,
all line endpoints and progress variables, and the jump/drop-through physics
are preserved. Three redundant hazards were retired: the gully's bottom whip
and gust, and the gust on the porch work pad. The bridge board and porch whip
keep their IDs at the new crossing.

The source RGB render uses the established palette families. It shows the
background creek behind the dry tread; the water art does not add collision.
Static checks cover the first mandatory drop, open-air catch shelves, recovery
from the floor, a return ascent, the two routes to the porch pad and sprite
budgets. Native checks still need to verify deliberate and missed landings,
cable delivery through both seams, and return recovery on the actual ROM.

## Integrated native evidence

See [the route playtest report](../LAKESIDE_ROUTE_PLAYTEST.md) for the completed
focused checks, failures and retries, exact ROM identities, and remaining human
and full-campaign gates. The prospective play notes above describe review goals;
the report records what has actually been verified.
