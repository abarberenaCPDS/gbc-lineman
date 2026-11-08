# Human playtest feedback — route design and dispatch hub

November 7, 2026 · Abe played the dispatch-map prototype and its onward campaign.
This is human gameplay feedback, separate from earlier automated reachability.

## Findings from the five screenshots

| Image | Abe's observation | Assessment / proposed next pass |
| --- | --- | --- |
| 1 | Hanging wire below the catwalk can be jumped past; placement feels useless. | A jump can legitimately evade a platform hazard, but this wire mostly threatens the recovery floor while the preferred path avoids it. Audit its purpose; remove or move it to a meaningful crossing rather than penalize a fall. |
| 2 | Upper obstacles can be bypassed by walking below. | Confirmed structural pattern: one-way catwalks above a continuous floor. Alternative lanes need an explicit time/height/repair tradeoff. A source hazard count does not prove either lane is interesting. |
| 3 | No obstacles on the chosen lower route. | Treat as an unearned bypass or insufficiently signaled rest section. A quiet animation frame alone would not prove no timed hazard, but Abe's traversal is the relevant evidence. Place the next mandatory repair on the intended route and test both lanes. |
| 4 | Lower hazards are bypassed by staying above. | Alternate route only matters if it creates a distinct challenge or useful recovery. Keep safe recovery where intentional; remove redundant hazard actors or redesign the crossing. Do not solve this by filling both lanes with hazards. |
| 5 | Could the map be top-down? | It already has native TOPDOWN scene type, but the player is hidden and the hero is a fixed story actor. Recommendation: a small walkable top-down neighborhood hub, four homes and persistent lighting, with the next job still explicit. Not approved for expansion yet. |

Source examples: `ridge.py` Wind Ridge has catwalk9–14 over a floor whip12–13,
and upper/lower gust lanes around47–51. Ridge Saddle has catwalk20–31 over a
clear floor run, then upper38–47 and floor hazards42–49. These placements support
the reported bypass pattern. Some lower hazards are gated on repaired lines;
include outward and return trips in the next review instead of judging one pose.

## Reference inspection: ../gb-rom

Read the reference project and relevant level/art/quality docs without modifying
it. Actual sample platform scenes include:

- Path to Sample Town:161×18 tiles.
- Parallax Example:80×18 tiles.
- Deeper Underground:32×18 tiles.
- Sample Town:TOPDOWN,56×56 tiles.

Current Lineman horizontal job scenes are generally64×18; the shafts are20×36.
Larger maps are possible. Map cell count and unique art tile count are different:
the reference's161×18 path uses repeated art (the reference's background guide
reports62 unique tiles,53 with flips). More world cells do not require one new
stored art tile per cell, and extra size alone does not fix a bypass.

Recommendation: one revised route pilot before rebuilding all jobs. Preserve the
accepted hero/art/palettes. Use more vertical space where useful (candidate64×36),
place required pole/box endpoints so terrain guides a deliberate traversal, and
keep forgiving recovery/checkpoints. Give every hazard a stated purpose: required
timing, optional faster route, or meaningful return-trip change. Keep selected
rest areas; remove redundant hazards. Test the easiest bypass as well as the
intended path, followed by another human pass. Exact dimensions/geometry are a
proposal, not implemented or accepted.

## Browser automation check

Live CUA discovery still returns an empty browser inventory with:
`Browsers: Error: The browser access host is unavailable`.
Desktop app inventory does work. This is not evidence that localhost was denied,
that project filesystem permissions are insufficient, or that native rendering
failed. No browser settings or OS permissions were changed.

Official OpenAI documentation says the built-in browser is included automatically
in the ChatGPT desktop app. Use the desktop Codex experience, check
Settings > Browser > Agent permissions, and invoke @Browser. If this task is in
CLI/IDE, that surface does not supply the built-in browser. If already enabled,
updating/relaunching the desktop app is a reasonable diagnostic attempt, not a
confirmed repair for this particular host error. Full desktop control has separate
Computer Use setup and macOS permissions; it is not required merely to authorize
the game project filesystem.

Sources: <https://learn.chatgpt.com/docs/browser> and
<https://learn.chatgpt.com/docs/computer-use> (read this session).

## Status

- Automated route reachability remains established with its documented ROM limits.
- Human route-design acceptance has failed on the bypass examples above.
- The fixed dispatch map was reviewed; a walkable top-down hub is proposed.
- Reopen the route-quality pass before map/ending expansion. No geometry, art,
  movement, input controls, scene resources or browser permissions changed here.
