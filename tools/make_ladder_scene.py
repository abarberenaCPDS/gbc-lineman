"""Generate 4B ``pine_ladder`` (Emil's job): the long climb out, a 20x36 climb-style shaft.

Run with ``python3 tools/make_ladder_scene.py`` from any working directory.
Geometry, hazards and wires come from ``kiko.LADDER_SCENE`` (the climb's decks,
``shaft.py``); every builder is ``make_kiko_scene``'s, in this scene's
namespace (``ladder:`` event/actor keys, ``ladder_`` symbols).

Line 3's cable arrives from the hollow through the bottom-left exit and plugs
into transformer 3 on deck 27; line 4 rises two decks to transformer 4; line 5's
cable climbs two more shelves and the four-row leap and leaves through the
top-right exit to the rim.

The shaft's worst 30-row window holds 41+4 OBJs (spec §5), so it runs the
climb's culling thread (``shaft.cull_thread_event``; scratch vars 46-49 are
shared with the climb, one scene runs at a time). Every timed hazard starts
each live cycle safe, because the thread can deactivate an actor mid-cycle and
its update script restarts on reactivation; the span arc uses the climb's
``ClimbChain`` variant for that.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import climb  # noqa: E402  (culling scratch variable registrations)
import kiko  # noqa: E402  (Emil's job contract)
import make_kiko_scene as base  # noqa: E402  (the job's builders)
import shaft  # noqa: E402  (culling thread)

FOLDER = kiko.LADDER
CULL_VARIABLES = tuple(entry for entry in climb.VARIABLES
                       if entry[0] in (shaft.VAR_CULL_X, shaft.VAR_CULL_Y, shaft.VAR_CULL_CAM, shaft.VAR_CULL_TOP))


def cull_thread_event(actors: list[dict[str, Any]]) -> dict[str, Any]:
    """The shaft's culling thread over every actor of the scene (base builders, ladder namespace)."""
    with base.scene_scope(FOLDER):
        return shaft.cull_thread_event(actors, event=base.event, branch_event=base.branch_event,
                                       set_value=base.set_value, wait_event=base.wait_event,
                                       max_top=kiko.LADDER_CAMERA_MAX_TOP, key="cull")


def build_actors(sprite_ids: dict[str, str]) -> list[dict[str, Any]]:
    return base.build_actors(FOLDER, sprite_ids)


def build_scene(music_id: str, audio_ids: dict[str, str], actors: list[dict[str, Any]]) -> dict[str, Any]:
    return base.build_scene(FOLDER, music_id, audio_ids, [cull_thread_event(actors)])


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    return base.build_triggers(FOLDER, audio_ids)


def main() -> None:
    if len(CULL_VARIABLES) != 4:
        raise SystemExit("climb.VARIABLES must register the culling scratch variables 46-49")
    base.generate(FOLDER, extra_init=lambda actors: [cull_thread_event(actors)],
                  extra_variables=CULL_VARIABLES)


if __name__ == "__main__":
    main()
