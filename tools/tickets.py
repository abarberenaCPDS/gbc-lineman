#!/usr/bin/env python3
"""Work orders and the storm report (HANDOFF item 7, Abe's pick: "do #2",
option A in docs/DESIGN_OPTIONS.md).

Each job opens with a work-order card and ends with the ticket stamped CLOSED;
after Emil's house a storm report thanks everyone and returns to the title.

* ``work_order``: one TOPDOWN, screen-sized scene for every ticket. The exit
  that leads into a job sets ``VAR_TICKET`` to the job number (1-4) and switches
  here; the scene shows the clipboard card art, types that ticket as dispatch
  (narrator voice) and, on the last A, switches to the job's start.
* Closing: right after a house's power payoff, the job's own scene shows a
  CLOSED box (``closed_lines``) with the victory jingle. It stays in-scene:
  re-entering a job scene re-runs its init and would reset its variables.
* ``storm_report``: TOPDOWN, same card art. Pine Hollow's porch exit (gated on
  Emil's house) leads here; the report pages thank everyone, then the title.

TOPDOWN (not LOGO) because these scenes draw text (MCP_TOOLKIT §5). All lines
are <= 17 chars; card text is dialogue (``EVENT_TEXT``) over baked card art.
"""

from __future__ import annotations

import uuid as _uuid
from pathlib import Path

import climb
import intro
import kiko
import opening
import ridge
import rosa
import scenes

ROOT = Path(__file__).resolve().parent.parent
_TICKET_NAMESPACE = _uuid.UUID("3f9a6c21-5d7e-5b08-a4c3-9e1b7d2f6a40")
MAX_CHARS = 17


def resource_id(key: str) -> str:
    """Stable UUIDv5 for ticket/report resources."""
    return str(_uuid.uuid5(_TICKET_NAMESPACE, "mr-cfe:tickets:" + key))


VAR_TICKET = "16"
VARIABLES = [(VAR_TICKET, "Work Order", "var_work_order")]

MAP_W, MAP_H = 20, 18
WORK_ORDER_SCENE_ID = resource_id("scene:work-order")
REPORT_SCENE_ID = resource_id("scene:storm-report")
# (scene id, folder/symbol, name, background png stem, editor x, editor y)
SCENES = [
    (WORK_ORDER_SCENE_ID, "work_order", "Work Order", "ticket_card", *scenes.editor_position("work_order")),
    (REPORT_SCENE_ID, "storm_report", "Storm Report", "ticket_card", *scenes.editor_position("storm_report")),
]
BACKGROUND_NAME = "ticket_card"                 # assets/backgrounds/ticket_card.png
BACKGROUND_ID = resource_id("background:ticket_card")
# Card art occupies rows 0..11; the dialogue box (bottom, up to 6 rows) covers 12..17.
CARD_ROWS = 12
HERO_POSITION = (0, 0)   # TOPDOWN needs a player position; the hero sprite is hidden

# make_climb_scene.resource_id("scene:storm-climb"); a literal because the scene
# generators import this module (test_tickets checks it against the generator).
CLIMB_SCENE_ID = "e8778f37-44a7-5d3a-ad39-49d52fe4c5c7"

# ---------------------------------------------------------------------------
# Tickets: number, job scene, start tile, dispatch pages, closed pages.
# ---------------------------------------------------------------------------
TICKETS = {
    1: {
        "number": "WO-0412",
        "scene_id": CLIMB_SCENE_ID,
        "start": climb.START,
        "pages": ["WORK ORDER\nWO-0412", "Amara, hilltop:\nfridge is out.", "Fix: reconnect\nthe snapped line."],
    },
    2: {
        "number": "WO-0413",
        "scene_id": ridge.SCENE_ID,
        "start": ridge.START,
        "pages": ["WORK ORDER\nWO-0413", "Hiroshi, ridge:\noxygen machine\nhas no power.", "Fix: reconnect\nall five lines."],
    },
    3: {
        "number": "WO-0414",
        "scene_id": rosa.SCENE_ID,
        "start": rosa.START,
        "pages": ["WORK ORDER\nWO-0414", "Priya, hill:\nno internet,\nwork is due.", "Fix: five lines.\nMind live wires."],
    },
    4: {
        "number": "WO-0415",
        "scene_id": kiko.SCENE_ID,
        "start": kiko.START,
        "pages": ["WORK ORDER\nWO-0415", "Emil, hollow:\nstove is dead,\ndinner's cold.", "Fix: reconnect\nall five lines."],
    },
}
LAST_TICKET = 4


def closed_lines(ticket: int) -> list[str]:
    """In-scene CLOSED box shown right after the house's power payoff."""
    return [f"{TICKETS[ticket]['number']}\nCLOSED. Nice!"]


REPORT_PAGES = [
    "STORM REPORT",
    "Tickets closed:\n4 of 4.",
    "Lines fixed:\n20 of 20.",
    "Amara's food is\nsafe and cold.",
    "Hiroshi breathes\neasy again.",
    "Priya is back\nonline.",
    "Emil's soup is\nhot.",
    "Thank you,\nMister CFE!",
    "A game by\nAbe's Games",
]

# Pine Hollow porch exit to the report, gated on Emil's house (var 13).
# Same shape as Signal Hill's porch exit; it sorts before the door (BUGS B-05).
REPORT_EXIT = (kiko.MAP_W - 2, 9, 1, 3)
REPORT_EXIT_GATE_VAR = kiko.VAR_HOME_POWERED
TITLE_SCENE_ID = intro.TITLE_SCENE_ID


def to_work_order(ticket: int, key: str, event, set_value, number) -> list[dict]:
    """Events that open ticket ``ticket``: set VAR_TICKET, switch to the card scene.

    ``event(command, args, key)``, ``set_value(variable, value, key)`` and
    ``number(value)`` are the calling generator's own builders.
    """
    x, y = HERO_POSITION
    return [
        set_value(VAR_TICKET, ticket, f"{key}:ticket"),
        event("EVENT_SWITCH_SCENE", {
            "x": number(x), "y": number(y), "direction": "down",
            "sceneId": WORK_ORDER_SCENE_ID, "fadeSpeed": "2",
        }, f"{key}:to-work-order"),
    ]


def check() -> None:
    for number, ticket in TICKETS.items():
        assert ticket["scene_id"], f"ticket {number} has no destination scene"
        for page in [*ticket["pages"], *closed_lines(number)]:
            lines = page.split("\n")
            assert len(lines) <= 3, page
            assert all(len(line) <= MAX_CHARS for line in lines), page
    for page in REPORT_PAGES:
        assert all(len(line) <= MAX_CHARS for line in page.split("\n")), page
    assert sorted(TICKETS) == list(range(1, LAST_TICKET + 1))
    assert len({t["number"] for t in TICKETS.values()}) == LAST_TICKET
    assert opening  # opening's awning exit leads to ticket 1


check()
