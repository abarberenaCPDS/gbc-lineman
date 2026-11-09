# Emil: from Pine Hollow to the lake rim

Emil still has three scenes and five repairs. The route starts below the tree
line, crosses a set of offset work shelves, and opens onto a view of the lake
before the last cable reaches the stove. Coordinates below are 8 px tiles.

| Beat | Route and recovery |
| --- | --- |
| Hollow work pads | Take cable 1 up to the timber crossing and the mesa transformer (18,8). After cable 2 pickup, drop to the floor or use the two raised steps along the fallen span. Both approaches reach the box on the second rock (37,11). |
| Pine trail | Take cable 3 on the second rock. The split high bridges give a view of the lower trail. The floor catches a short jump and offers another way to the final low catwalk, where two firm tiles follow the cracked boards. The trail pennant and rising ridge silhouette mark the entrance to the ascent. |
| West shelf to east pole | Enter at (2,32) on the bottom floor. Use the row 30 step to reach box 3 (2,26). Cross the west shelf, then rise onto the longer east shelf for cable 4 (16,23). Boards and the hanging wire mark the crossing; the floor catches a fall. |
| East shelf to west repair | Carry cable 4 back west across the offset ledges to box 4 (2,14). The open space between the ledges lets the player drop to an earlier shelf and retrace the route. The checkpoint stays beside the transformer. |
| Lake notch | Pick up cable 5 at the east approach (17,11). A short step at row 8 leads to the summit shelf at row 5. The pennant marks the seam before the switch; the same motif marks the return on the rim. Both entries retain their previous support and clearance. |
| Rim and home | Follow the broken timber approach or drop to the lower trail. The second catch runs from x13 to x18 at row 12. Walk along it to (17,11), then tap straight up into the pocket at (17,8) between the hidden cable and gust. Wait there for the gust's rest before crossing to the bluff. The lake, distant roofs, and pier sit behind the trail. The box at (41,11), checkpoint (43,11), and porch stay outside the hazard lanes. The existing powered exit opens the storm report. |

The route keeps the original bounds, scene links, checkpoints, repair IDs and
variables, hazards, hero, and jump physics. The ascent uses the existing actor
culling thread. Source checks cover short rises to the summit, two-way recovery,
link and work-pad clearance, and resource and sprite budgets. The rim recovery
test checks the vertical rise and upper pocket against the authored cable,
whip, and gust hitboxes.

Native checks still needed: carry through both seams, climb with short taps and
a held jump, recover after a fall or lost cable, restore the stove and reach the
report. Review the upper pennant and lake view at the actual camera positions.

## Integrated native evidence

See [the route playtest report](../LAKESIDE_ROUTE_PLAYTEST.md) for the completed
focused checks, failures and retries, exact ROM identities, and remaining human
and full-campaign gates. The prospective play notes above describe review goals;
the report records what has actually been verified.
