# Amara: pine steps and the cabin walkway

The first household route follows the selected lakeside baseline. The original
pine ascent and four work decks lead to a lower shoreline trail and a broken
walkway. The last cable crosses both scenes and reaches the transformer beside
Amara's cabin. Map sizes, scene links, entry and respawn tiles, repair order and
accepted jump physics stay the same.

| Beat | Route | What to watch in play |
| --- | --- | --- |
| Pine service steps | Four offset shelves connect the existing work decks. The first pickup approaches the lower shelf at x7–8, beside the hidden cable. | A short tap lands on each shelf; repair pads support a full stop. |
| Preview and cross the wire | Crest arrival at (3,8) overlooks the lower trail. Two severed cable ends mark the cycling arc at x11–12. Stone at x7–10 and x13–19 gives room on both sides. | The warning is visible before the first step into range. Waiting for calm or jumping over it both work. |
| Walkway approach | Granite x20–24 at row12 leads onto timber x23–34 at row9. The cracked boards are at x24–26; the hanging wire is at x29–30. | The player can wait at x27–28 between hazards, then use four clear launch tiles at x31–34. The crest's redundant gust and hidden cable are gone. |
| Carry across the break | Missing boards at x35–37 separate the elevated walkway from the lower granite porch at x38. The trail below catches a missed jump at row15. | The direct jump should be quicker. The catch basin can be exited toward the porch without another hazard or losing the cable; a reverse route reaches the summit exit. |
| Repair and payoff | Box at (39,11), B zone x38–40 and checkpoint at (41,11). The porch extends to Amara and the dark cabin windows. | Repair 5 clears the earlier span; visiting Amara's door lights the windows and closes the job. The far exit uses the existing return flow. |

The rendered art uses the existing palette slots. Water and pine silhouettes
stay behind the walkable surfaces; cracked boards and splintered timber align
with collision edges, and only the cabin windows swap to the powered palette.
`build/review/amara-lakeside.png` is an RGB source review sheet without sprites
or the HUD. The compiler uses the generator's separate grayscale index proxies.
Source checks measured 107 effective background tiles on the steps and 166 on
the walkway. The crest's static scanline estimate is 9 columns including the
hero.

The standing tile graph checks both directions from the catch basin; it does
not model the actual jump arc or collision timing. Native validation should
enter with cable 5, cross the wire and walkway normally, deliberately fall into
the notch and recover, then verify the cabin connection, safe-span reentry and
return. A second pass should deliberately lose cable 5 and retrieve it from the
summit. Human review should assess whether the wire warning and jump landing
read at a normal approach speed.

## Integrated native evidence

See [the route playtest report](../LAKESIDE_ROUTE_PLAYTEST.md) for the completed
focused checks, failures and retries, exact ROM identities, and remaining human
and full-campaign gates. The prospective play notes above describe review goals;
the report records what has actually been verified.
