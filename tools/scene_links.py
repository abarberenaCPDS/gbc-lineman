"""Every link between game scenes, in one table (docs/LEVEL_REDESIGN.md §3 rule 7). Stdlib only.

A link is one exit trigger: (from folder, trigger rect, to folder, entry tile,
facing, gate var), plus the work order it opens on the way (``ticket``). Scene
generators build their exits from here instead of importing each other's exit
constants (``ridge.CLIMB_SUMMIT_EXIT``, ``rosa.RIDGE_EXIT``, ``kiko.HILL_EXIT``,
``tickets.REPORT_EXIT``); test_scene_links.py checks symmetry, standable entries,
spacing and gates, and that the generated triggers match the table.

This module imports no contract (they will import it), so values are literals;
the tests compare them with the contracts.

Two tables, one per layout:

* ``TODAY``: today's game exactly (single-scene jobs).
* ``REDESIGN``: the multi-scene layout of §2 (internal links ungated, both ways;
  each job's last scene opens the next work order with today's gate).

``links()`` picks, per job, the redesign rows once that job has migrated (all of
its new scene folders are generated, ``migrated(job)``), else today's rows. A
work-order link's entry is the destination job's current start (``job_start``),
so one job can migrate before the next. A job worker therefore adds nothing
here: generating its new folders switches its rows.

Link fields:

  source, rect     the exit trigger: scene folder and (x, y, w, h) in tiles
  target, entry    destination folder and the hero's feet tile there
  facing           hero direction on arrival ("left" / "right" / "down")
  gate             variable that must be 1 to pass (None: ungated); a refusal
                   says why (text only; the climb summit also nudges back)
  ticket           work order number opened on the way (tickets.to_work_order),
                   or None for a direct switch
  fade             EVENT_SWITCH_SCENE fadeSpeed; every link fades (Abe: keep the fade)

``switch_args(link)`` gives the EVENT_SWITCH_SCENE args of a direct link and
``exit_events(link, key, event=..., set_value=..., number=...)`` the switch (or the
work-order hop) the trigger runs once its gate passes. Exits stay first in a
scene's trigger order and lift the HUD cutoff / hide the overlay before calling these.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable

import scenes

FADE_SPEED = "2"
VAR_TICKET = "16"                   # tickets.VAR_TICKET (literal: tickets imports the contracts)
WORK_ORDER = "work_order"
REPORT = "storm_report"
WORK_ORDER_POSITION = (0, 0)        # tickets.HERO_POSITION: the card scene hides the hero


@dataclass(frozen=True)
class Link:
    source: str
    rect: tuple[int, int, int, int]
    target: str
    entry: tuple[int, int]
    facing: str
    gate: str | None = None
    ticket: int | None = None
    fade: str = FADE_SPEED

    @property
    def internal(self) -> bool:
        """Between two scenes of one job: ungated, both directions."""
        return job_of(self.source) is not None and job_of(self.source) == job_of(self.target)


# The job's scenes, entry first; 0 is the opening (scenes.JOB_SCENES has jobs 1-4).
JOB_SCENES = {0: ("service_opening",), **scenes.JOB_SCENES}


def job_of(folder: str) -> int | None:
    for job, folders in JOB_SCENES.items():
        if folder in folders:
            return job
    return None


# ---------------------------------------------------------------------------
# Job starts (the work order card switches there): tickets.TICKETS[n]["start"]
# ---------------------------------------------------------------------------
TODAY_START = {1: (2, 32), 2: (2, 26), 3: (2, 14), 4: (2, 14)}
REDESIGN_START = {1: (2, 32), 2: (2, 14), 3: (2, 14), 4: (2, 14)}

# ---------------------------------------------------------------------------
# Today's game. Per job: the links whose source is one of that job's scenes.
# ---------------------------------------------------------------------------
TODAY: dict[int, tuple[Link, ...]] = {
    0: (Link("service_opening", (18, 6, 2, 4), "storm_climb", TODAY_START[1], "right", gate="4", ticket=1),),
    1: (Link("storm_climb", (0, 30, 1, 3), "service_opening", (16, 9), "left"),
        Link("storm_climb", (17, 3, 1, 3), "wind_ridge", TODAY_START[2], "right", gate="0", ticket=2)),
    2: (Link("wind_ridge", (98, 21, 1, 3), "signal_hill", TODAY_START[3], "right", gate="9", ticket=3),),
    3: (Link("signal_hill", (98, 9, 1, 3), "pine_hollow", TODAY_START[4], "right", gate="11", ticket=4),),
    4: (Link("pine_hollow", (98, 9, 1, 3), REPORT, WORK_ORDER_POSITION, "down", gate="13"),),
}

# ---------------------------------------------------------------------------
# The redesign (§2 maps). "e" tiles: where a back link lands, two columns
# inside the map and clear of the exits and boards there.
# ---------------------------------------------------------------------------
REDESIGN: dict[int, tuple[Link, ...]] = {
    0: TODAY[0],
    1: (Link("storm_climb", (0, 30, 1, 3), "service_opening", (16, 9), "left"),
        Link("storm_climb", (17, 2, 1, 3), "climb_crest", (3, 8), "right"),
        Link("climb_crest", (1, 6, 1, 3), "storm_climb", (14, 4), "left"),
        Link("climb_crest", (54, 9, 1, 3), "wind_ridge", REDESIGN_START[2], "right", gate="0", ticket=2)),
    2: (Link("wind_ridge", (62, 6, 1, 3), "ridge_saddle", (2, 8), "right"),
        Link("ridge_saddle", (1, 6, 1, 3), "wind_ridge", (56, 8), "left"),
        Link("ridge_saddle", (62, 9, 1, 3), "signal_hill", REDESIGN_START[3], "right", gate="9", ticket=3)),
    3: (Link("signal_hill", (62, 3, 1, 3), "signal_gully", (2, 4), "right"),
        Link("signal_gully", (0, 2, 1, 3), "signal_hill", (59, 5), "left"),
        Link("signal_gully", (19, 30, 1, 3), "signal_porch", (2, 14), "right"),
        Link("signal_porch", (1, 12, 1, 3), "signal_gully", (17, 32), "left"),
        Link("signal_porch", (38, 9, 1, 3), "pine_hollow", REDESIGN_START[4], "right", gate="11", ticket=4)),
    4: (Link("pine_hollow", (62, 9, 1, 3), "pine_ladder", (2, 32), "right"),
        Link("pine_ladder", (0, 30, 1, 3), "pine_hollow", (55, 8), "left"),
        Link("pine_ladder", (17, 2, 1, 3), "pine_rim", (3, 8), "right"),
        Link("pine_rim", (1, 6, 1, 3), "pine_ladder", (15, 4), "left"),
        Link("pine_rim", (54, 9, 1, 3), REPORT, WORK_ORDER_POSITION, "down", gate="13")),
}


def migrated(job: int) -> bool:
    """A job uses its REDESIGN rows once every one of its new scene folders is generated."""
    new = JOB_SCENES[job][1:]
    return bool(new) and all(scenes.present(folder) for folder in new)


def job_start(job: int, layout: str | None = None) -> tuple[int, int]:
    """Entry tile of a job's entry scene: "today", "redesign", or (None) its current layout."""
    if layout is None:
        layout = "redesign" if migrated(job) else "today"
    return (REDESIGN_START if layout == "redesign" else TODAY_START)[job]


def table(layout: str) -> tuple[Link, ...]:
    """Every link of one layout ("today" or "redesign"), as written."""
    rows = TODAY if layout == "today" else REDESIGN
    return tuple(link for job in sorted(rows) for link in rows[job])


def links() -> tuple[Link, ...]:
    """The links of the game as generated now (per job: redesign once migrated, else today)."""
    out = []
    for job in sorted(TODAY):
        for link in (REDESIGN if migrated(job) else TODAY)[job]:
            if link.ticket is not None:
                link = replace(link, entry=job_start(link.ticket))
            out.append(link)
    return tuple(out)


def from_scene(folder: str, all_links: tuple[Link, ...] | None = None) -> list[Link]:
    """Exits of ``folder``, in table order (back links before the onward exit)."""
    return [link for link in (all_links or links()) if link.source == folder]


def into_scene(folder: str, all_links: tuple[Link, ...] | None = None) -> list[Link]:
    return [link for link in (all_links or links()) if link.target == folder]


def link(source: str, target: str, all_links: tuple[Link, ...] | None = None) -> Link:
    """The one link from ``source`` to ``target`` (for a work-order hop, the job it leads to)."""
    found = [item for item in (all_links or links()) if item.source == source and item.target == target]
    if len(found) != 1:
        raise KeyError(f"{len(found)} links from {source} to {target}")
    return found[0]


def scene_id(folder: str) -> str:
    return scenes.REGISTRY[folder]["id"]


def switch_args(item: Link, number: Callable[[int], dict[str, Any]]) -> dict[str, Any]:
    """EVENT_SWITCH_SCENE args of a direct link (no work order)."""
    x, y = item.entry
    return {"x": number(x), "y": number(y), "direction": item.facing,
            "sceneId": scene_id(item.target), "fadeSpeed": item.fade}


def exit_events(item: Link, key: str, *, event: Callable[..., dict[str, Any]],
                set_value: Callable[..., dict[str, Any]],
                number: Callable[[int], dict[str, Any]]) -> list[dict[str, Any]]:
    """The switch a link's trigger runs once its gate passes (builders from the scene).

    A ticket link opens its work order exactly like tickets.to_work_order (the
    card then switches to the job's start); a direct link switches with a fade.
    """
    if item.ticket is not None:
        x, y = WORK_ORDER_POSITION
        return [
            set_value(VAR_TICKET, item.ticket, f"{key}:ticket"),
            event("EVENT_SWITCH_SCENE", {
                "x": number(x), "y": number(y), "direction": "down",
                "sceneId": scene_id(WORK_ORDER), "fadeSpeed": item.fade,
            }, f"{key}:to-work-order"),
        ]
    return [event("EVENT_SWITCH_SCENE", switch_args(item, number), f"{key}:switch")]
