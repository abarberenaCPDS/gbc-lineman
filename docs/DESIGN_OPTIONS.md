# Design options for Abe: hazards and service tickets (2026-10-26)

HANDOFF items 6 and 7 change how the game plays, so nothing here is built yet.
Pick one option per question (or mix); each lists what it reuses.

## 6. Replace falling rocks with field-crew hazards

Falling debris today: timed columns in the climb (`climb.HAZARD_DEBRIS`), Wind Ridge
and Pine Hollow. Live-wire arcs (Signal Hill) and wind gusts already exist.

| Hazard | How it plays | Built from |
|---|---|---|
| **A. Cracked boards** (recommended) | A plank or crossarm shows cracks. Stand on it and it creaks for ~0.7 s, then gives way: the hero drops back to the lane start, like a gust. Keep moving and it's safe. | A trigger over the plank plus the gust respawn. GB Studio can't change collision at runtime, so the plank "breaks" by animation and respawn rather than a real hole. |
| **B. Hidden cables** | A buried or hidden live line is invisible. Every few seconds a short spark trail shows where it runs, then it arcs. Learn the rhythm, cross while it's dark. | The live-arc actor and timings (`rosa.ARC_*`) with a longer dark phase and a brief, bright reveal in place of the always-visible wire. |
| **C. Snapped pole falls** | A leaning damaged pole sways (warning), then tips across the path for a moment. | The debris column timing with a pole sprite. It's still "something falls on you", just more on-theme. |

**Suggested mix:** the climb gets A (rotten boards on the shelves) and B on one
shelf. Wind Ridge gets A on the plateau, alongside its gusts. Pine Hollow gets B on
the mesa. Every scene then has its own hazard, and no rocks are left.

## 7. Each job as a service ticket, and a storm report at the end

| Option | Start of job | End of job | After Emil |
|---|---|---|---|
| **A. Work-order cards** (recommended) | A full-screen ticket: `TICKET #0412 · Amara · Fridge out · Fix: reconnect line`, A to start. | The same card stamped **CLOSED** with a jingle. | A **Storm report**: jobs closed 4/4, falls, a thank-you, credits, then back to the title. |
| **B. Dispatcher radio** | A radio call in the dialogue box ("Dispatch: Amara, fridge out, Calle 3"). | "Dispatch: ticket closed." | A short report box, then the title. |
| **C. Pre-storm prep plan** | At the title, a checklist of four homes; the HUD shows tickets left. | Ticks the list. | The checklist all ticked, then the storm report. |

A costs the most (four card scenes, or one shared card scene driven by a variable).
It reads best on the small screen, and the text-scene pattern already exists
(TOPDOWN, as in the intro story). B is the cheapest, since it is just
dialogue. C changes the HUD.

**Questions for Abe**
1. Hazards: A, B, C, or the suggested mix?
2. Tickets: A, B or C? Real-looking ticket numbers or playful ones?
3. Ending: should the storm report count falls (a light score) or only thank people?
