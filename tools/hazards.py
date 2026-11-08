#!/usr/bin/env python3
"""Field-crew hazards that replace the falling rocks (HANDOFF item 6, Abe's pick:
"do #2", the recommended mix in docs/DESIGN_OPTIONS.md).

Two hazards, both delivered through each scene's existing group-1 contact reset
(``playerHit1Script`` respawns the hero), so neither freezes the player:

* **Cracked board**: a plank sprite on a shelf. A trigger over the plank sets
  ``VAR_ON_BOARD`` as an advisory body-overlap flag (its leave script clears
  it). Each board measures actual foot contact with actor-local position and
  timer variables; after ``CREAK_FRAMES`` continuous contacts it gives way: Break state plus
  a few frames of group-1 collision, which respawns the hero. Collision tiles
  never change at runtime (GB Studio can't), so the plank "breaks" by animation
  and respawn. Keep moving and it is safe.
* **Hidden cable**: the live-arc actor (``live_arc`` sprite, OBJ slot 3) with no
  wire drawn in the background, a long dark phase and a short, bright warning:
  the spark trail is the only clue where the buried line runs.

Placement replaces every debris column (see ``BOARDS`` / ``HIDDEN_CABLES``).
Each scene generator builds its actors with the ``board_*`` / ``cable_*``
helpers below, passing its own ``event`` and ``wait`` builders so event IDs
stay in that scene's namespace.

Multi-scene redesign (docs/LEVEL_REDESIGN.md §2; job workers never edit this file):

* The six new scenes (``climb_crest``, ``ridge_saddle``, ``signal_gully``,
  ``signal_porch``, ``pine_ladder``, ``pine_rim``) are ordinary keys of
  ``BOARDS`` / ``HIDDEN_CABLES`` / ``CABLE_START_DELAYS``.
* The entry scenes keep their keys. ``storm_climb``'s placement is unchanged by
  the redesign. ``wind_ridge``, ``signal_hill`` and ``pine_hollow`` keep
  today's (100-column) placement until their job migrates: the 64x18 layout is
  in ``REDESIGN_ENTRY`` and ``placement(scene, redesign=True)`` returns it.
  Once WP2-WP4 have switched, main folds ``REDESIGN_ENTRY`` into the tables.
* ``placement(scene, redesign=...)`` -> (boards, hidden cables, start delays)
  is the one accessor job generators should use.
* Per-job hidden-cable timings: ``CABLE_TIMINGS[job]`` (dark, warning, arc) and
  ``cable_timings(scene)`` via ``SCENE_JOB``. ``cable_update_script(...,
  timings=...)`` takes them; omitted, it keeps the module constants (150/20/24),
  so existing scenes stay byte-identical.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any, Callable

import climb

_HAZARD_NAMESPACE = _uuid.UUID("8c3e51d2-7f0a-5b64-9e1d-2a6f4c8b0e37")


def resource_id(key: str) -> str:
    """Stable UUIDv5 for shared hazard resources (sprite, palette, variable)."""
    return str(_uuid.uuid5(_HAZARD_NAMESPACE, "mr-cfe:hazards:" + key))


# ---------------------------------------------------------------------------
# Shared resources
# ---------------------------------------------------------------------------
VAR_ON_BOARD = "15"
VARIABLES = [(VAR_ON_BOARD, "On Cracked Board", "var_on_cracked_board")]

BOARD_SPRITE_NAME = "cracked_board"          # assets/sprites/cracked_board.png
BOARD_SPRITE_ID = resource_id("sprite:cracked_board")
BOARD_STATES = ["Idle", "Creak", "Break"]    # Idle 1 frame, Creak 2 (shake), Break 2 (split)
BOARD_CANVAS = (24, 16)                      # three 8x16 OBJs; plank in the bottom 8 px
# Collision box (GB Studio bounds, relative to the canvas bottom-left tile): the
# 8 px row above the plank, where the standing hero's feet are.
BOARD_BOUNDS = (0, -8, 24, 8)
BOARD_SPRITE_PALETTE_SLOT = 4                # the debris slot, free once rocks are gone
BOARD_PALETTE_ID = resource_id("palette:sprite:board")
BOARD_SPRITE_HARDWARE = ["000000", "E8C890", "9A6A3A", "3A2418"]  # pale wood, mid, dark crack

ARC_SPRITE_PALETTE_SLOT = 3                  # live_arc tiles carry slot 3 (rosa contract)

CREAK_FRAMES = 50       # ~0.8 s standing still before it gives way
BREAK_FRAMES = 8        # group-1 collision on: the hit
BOARD_REST_FRAMES = 60  # shows Break, then mends back to Idle

CABLE_DARK_FRAMES = 150     # invisible: safe
CABLE_WARNING_FRAMES = 20   # brief spark trail: safe, shows where it runs
CABLE_ARC_FRAMES = 24       # arc: hits (group 1)

# ---------------------------------------------------------------------------
# Placement. Boards: (shelf_row, x0, x1) — the plank lies on the one-way/solid
# surface row; the hero stands on row shelf_row - 1. Cables: (chest_row, x0, x1)
# exactly like rosa.ARC_LANES (two tiles, hero's chest row = surface row - 2).
# ---------------------------------------------------------------------------
BOARDS = {
    "storm_climb": [(27, 7, 9), (15, 9, 11), (9, 11, 13)],
    "wind_ridge": [(21, 9, 11), (21, 64, 66), (21, 83, 85)],   # C1, E1, F catwalks
    "signal_hill": [(9, 8, 10), (9, 43, 45), (9, 77, 79)],     # C1, D1, F catwalks
    "pine_hollow": [(9, 8, 10), (9, 62, 64), (9, 81, 83)],   # C1, E1, F catwalk landings
    # LAB_Hazard Gallery (make_lab_scene.py): one board on a one-tile shelf.
    "lab_hazard_gallery": [(12, 6, 8)],
    "lab_movement_room": [],
}
HIDDEN_CABLES = {
    "storm_climb": [(28, 9, 10)],
    "wind_ridge": [(25, 30, 31)],
    "signal_hill": [(13, 33, 34), (7, 83, 84)],     # floor before rock C, catwalk F
    "pine_hollow": [(7, 14, 15), (7, 86, 87)],               # C1 before the mesa, F before the porch
    "lab_hazard_gallery": [(13, 14, 15)],
    "lab_movement_room": [],
}
CABLE_START_DELAYS = {
    "storm_climb": [40],
    "wind_ridge": [60],
    "signal_hill": [50, 100],
    "pine_hollow": [90, 30],
    "lab_hazard_gallery": [40],
    "lab_movement_room": [],
}

# ---------------------------------------------------------------------------
# Redesign placements (docs/LEVEL_REDESIGN.md §2), same conventions as above:
# boards (plank row, x0, x1), cables (chest row, x0, x1), one delay per cable.
# Listed in route order (upstream entry first).
# ---------------------------------------------------------------------------
_NEW_SCENES = {
    # 1B: hidden cable before rock B, board on catwalk C's landing.
    "climb_crest": {"boards": [(9, 26, 28)], "cables": [(13, 16, 17)], "delays": [60]},
    # 2B: cable at the foot of the arrival drop; boards on catwalks C and E.
    "ridge_saddle": {"boards": [(9, 21, 23), (9, 38, 40)], "cables": [(13, 9, 10)], "delays": [40]},
    # 3B: boards on decks 15 and 27, cable on the deck-21 ledge.
    "signal_gully": {"boards": [(15, 8, 10), (27, 9, 11)], "cables": [(22, 10, 11)], "delays": [50]},
    # 3C: one board on the first catwalk, no hidden cable.
    "signal_porch": {"boards": [(9, 9, 11)], "cables": [], "delays": []},
    # 4B: two hidden cables in one shaft (bottom ledge and the arrival shelf), three boards.
    "pine_ladder": {"boards": [(27, 7, 9), (15, 9, 11), (9, 11, 13)], "cables": [(28, 8, 9), (3, 11, 12)],
                    "delays": [30, 90]},
    # 4C: board on the first catwalk, cable before the gust.
    "pine_rim": {"boards": [(9, 9, 11)], "cables": [(7, 15, 16)], "delays": [45]},
}
for _scene, _layout in _NEW_SCENES.items():
    BOARDS[_scene] = _layout["boards"]
    HIDDEN_CABLES[_scene] = _layout["cables"]
    CABLE_START_DELAYS[_scene] = _layout["delays"]
NEW_SCENES = tuple(_NEW_SCENES)

# Entry scenes whose placement changes when their job migrates to 64x18
# (storm_climb's redesign placement equals today's and needs no entry here).
REDESIGN_ENTRY = {
    # 2A: boards on catwalks C1 and the F approach; cables on the floor before rock C and on catwalk D.
    "wind_ridge": {"boards": [(9, 9, 11), (9, 58, 60)], "cables": [(13, 31, 32), (7, 42, 43)],
                   "delays": [60, 20]},
    # 3A: boards on C1 and D1; cable on the floor before rock C.
    "signal_hill": {"boards": [(9, 7, 9), (9, 40, 42)], "cables": [(13, 29, 30)], "delays": [50]},
    # 4A: boards on C1 and the low catwalk F; cable on C1 before the mesa.
    "pine_hollow": {"boards": [(9, 8, 10), (12, 58, 60)], "cables": [(7, 13, 14)], "delays": [90]},
}
# Every game scene of the redesign, in play order.
REDESIGN_SCENES = ("storm_climb", "climb_crest", "wind_ridge", "ridge_saddle", "signal_hill",
                   "signal_gully", "signal_porch", "pine_hollow", "pine_ladder", "pine_rim")

# Hidden-cable (dark, warning, arc) frames per job (spec §1 timing tiers). The
# contracts own the gust/arc/whip tiers; this table owns the hidden cables.
CABLE_TIMINGS = {
    "climb": (150, 20, 24),
    "ridge": (150, 20, 24),
    "rosa": (140, 20, 24),
    "kiko": (120, 20, 26),
}
SCENE_JOB = {
    "storm_climb": "climb", "climb_crest": "climb",
    "wind_ridge": "ridge", "ridge_saddle": "ridge",
    "signal_hill": "rosa", "signal_gully": "rosa", "signal_porch": "rosa",
    "pine_hollow": "kiko", "pine_ladder": "kiko", "pine_rim": "kiko",
}


def placement(scene: str, *, redesign: bool = False
              ) -> tuple[list[tuple[int, int, int]], list[tuple[int, int, int]], list[int]]:
    """(boards, hidden cables, cable start delays) for ``scene``.

    ``redesign=True`` returns the 64x18 layout for an entry scene listed in
    ``REDESIGN_ENTRY``; every other scene has one placement either way.
    """
    if redesign and scene in REDESIGN_ENTRY:
        layout = REDESIGN_ENTRY[scene]
        return list(layout["boards"]), list(layout["cables"]), list(layout["delays"])
    return list(BOARDS[scene]), list(HIDDEN_CABLES[scene]), list(CABLE_START_DELAYS[scene])


def cable_timings(scene: str) -> tuple[int, int, int]:
    """(dark, warning, arc) frames of the hidden cables in ``scene``'s job."""
    return CABLE_TIMINGS[SCENE_JOB[scene]]


def board_trigger_rect(board: tuple[int, int, int]) -> tuple[int, int, int, int]:
    """(x, y, width, height) tiles: the hero's feet row above the plank."""
    row, x0, x1 = board
    return (x0, row - 1, x1 - x0 + 1, 1)


def board_actor_position(board: tuple[int, int, int]) -> tuple[int, int]:
    """Actor tile: canvas bottom-left on the plank row."""
    row, x0, _ = board
    return (x0, row)


# ---------------------------------------------------------------------------
# Event builders. ``event(command, args, key)`` and ``wait(frames, key)`` come
# from the calling scene generator; ``set_value`` / ``if_value`` likewise.
# ---------------------------------------------------------------------------
Event = Callable[[str, dict[str, Any], str], dict[str, Any]]


def board_trigger_scripts(number: int, key: str, set_value: Callable[..., dict[str, Any]]
                          ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """(script, leaveScript) for the trigger over board ``number`` (1-based)."""
    return ([set_value(VAR_ON_BOARD, number, f"{key}:on")],
            [set_value(VAR_ON_BOARD, 0, f"{key}:off")])


# Actor-local storage: independent per board; never borrow shaft scratch 46..49.
BOARD_LOCAL_X, BOARD_LOCAL_Y, BOARD_LOCAL_TIMER = "L0", "L1", "L2"


def board_update_script(number: int, key: str, event: Event, wait: Callable[[int, str], dict[str, Any]],
                        if_value: Callable[..., dict[str, Any]],
                        set_value: Callable[..., dict[str, Any]],
                        board: tuple[int, int, int], *, hide_idle: bool = False,
                        creak_sound: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Count consecutive actual foot-contact polls, never the head/body trigger.

    The 24px worker's unchanged bounds are x=2..13, y=-16..7 relative to
    its actor anchor. At rest above shelf row R, the pixel y anchor is 8*(R-1).
    A jump can cross that y briefly, but any next non-contact poll resets the
    countdown. Actor update loops already yield once per pass; an explicit
    contact wait here would double the intended warning. VM scheduling can
    still lengthen the measured wall-clock interval slightly.
    """
    row, x0, x1 = board

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    def number_value(value: int) -> dict[str, Any]:
        return {"type": "number", "value": value}

    def variable(value: str) -> dict[str, Any]:
        return {"type": "variable", "value": value}

    def compare(operator: str, name: str, value: int) -> dict[str, Any]:
        return {"type": operator, "valueA": variable(name), "valueB": number_value(value)}

    def branch(condition: dict[str, Any], suffix: str, yes: list, no: list) -> dict[str, Any]:
        node = event("EVENT_IF", {"condition": condition}, f"{key}:{suffix}")
        node["children"] = {"true": yes, "false": no}
        return node

    def reset_idle(tag: str) -> list[dict[str, Any]]:
        return [
            set_value(BOARD_LOCAL_TIMER, 0, f"{key}:{tag}-timer"),
            own("EVENT_ACTOR_COLLISIONS_DISABLE", f"{tag}-safe"),
            own("EVENT_ACTOR_SET_STATE", f"{tag}-state", spriteStateId="Idle", loopAnim=True),
            *([own("EVENT_ACTOR_HIDE", f"{tag}-hidden")] if hide_idle else []),
        ]
    give_way = [
        own("EVENT_ACTOR_SET_STATE", "break-state", spriteStateId="Break", loopAnim=False),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "break-hit"),
        wait(BREAK_FRAMES, f"{key}:break-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "break-safe"),
        set_value(VAR_ON_BOARD, 0, f"{key}:clear"),
        wait(BOARD_REST_FRAMES, f"{key}:rest-time"),
        *reset_idle("after-break"),
    ]
    first_contact = [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "creak-safe"),
        own("EVENT_ACTOR_SET_STATE", "creak-state", spriteStateId="Creak", loopAnim=True),
        *([own("EVENT_ACTOR_SHOW", "creak-visible")] if hide_idle else []),
        *([creak_sound] if creak_sound else []),
    ]
    creak = [
        if_value(BOARD_LOCAL_TIMER, 0, f"{key}:first-contact", first_contact, []),
        branch(compare("gte", BOARD_LOCAL_TIMER, CREAK_FRAMES), "elapsed", give_way, [
            event("EVENT_SET_VALUE", {"variable": BOARD_LOCAL_TIMER, "value": {
                "type": "add", "valueA": variable(BOARD_LOCAL_TIMER), "valueB": number_value(1),
            }}, f"{key}:count-contact"),
        ]),
    ]
    contact = {"type": "and",
               "valueA": compare("eq", BOARD_LOCAL_Y, (row - 1) * 8),
               "valueB": {"type": "and",
                          "valueA": compare("gte", BOARD_LOCAL_X, x0 * 8 - 13),
                          "valueB": compare("lte", BOARD_LOCAL_X, (x1 + 1) * 8 - 3)}}
    return [
        event("EVENT_ACTOR_GET_POSITION", {"actorId": "player", "vectorX": BOARD_LOCAL_X,
              "vectorY": BOARD_LOCAL_Y, "units": "pixels"}, f"{key}:player-feet"),
        branch(contact, "foot-contact", creak, [
            # Idle boards need only a position read and comparisons. Restore
            # visual state once on departure, rather than every update frame.
            if_value(BOARD_LOCAL_TIMER, 0, f"{key}:already-idle", [], reset_idle("off")),
        ]),
    ]


def board_start_script(key: str, event: Event) -> list[dict[str, Any]]:
    return [
        event("EVENT_SET_VALUE", {"variable": BOARD_LOCAL_TIMER, "value": {"type": "number", "value": 0}},
              f"{key}:init-timer"),
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:init-safe"),
        event("EVENT_ACTOR_SET_STATE", {"actorId": "$self$", "spriteStateId": "Idle", "loopAnim": True},
              f"{key}:init-idle"),
    ]


def cable_update_script(key: str, start_delay: int, event: Event,
                        wait: Callable[[int, str], dict[str, Any]],
                        branch: Callable[..., dict[str, Any]],
                        timings: tuple[int, int, int] | None = None) -> list[dict[str, Any]]:
    """Hidden cable: dark (hidden, safe) -> spark warning -> arc (group 1).

    Same first-cycle trick as the rosa arcs: the actor starts facing down; the
    first pass waits ``start_delay`` once and turns it up. ``branch`` is the
    scene's ``branch_event(command, args, key, true_events)``. ``timings`` is
    (dark, warning, arc) frames, e.g. ``cable_timings(scene)``; None keeps
    CABLE_DARK_FRAMES / CABLE_WARNING_FRAMES / CABLE_ARC_FRAMES.
    """
    dark_frames, warning_frames, arc_frames = timings or (
        CABLE_DARK_FRAMES, CABLE_WARNING_FRAMES, CABLE_ARC_FRAMES)

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first = [
        own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
    ]
    if start_delay > 0:
        first.append(wait(start_delay, f"{key}:start-delay"))
    return [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "dark-safe"),
        own("EVENT_ACTOR_HIDE", "dark-hidden"),
        branch("EVENT_IF_ACTOR_DIRECTION",
               {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
               f"{key}:first-cycle", first),
        wait(dark_frames, f"{key}:dark-time"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait(warning_frames, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait(arc_frames, f"{key}:arc-time"),
    ]


def cable_start_script(key: str, event: Event) -> list[dict[str, Any]]:
    return [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:init-safe"),
        event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:init-hidden"),
    ]


def whip_start_script(key: str, event: Event) -> list[dict[str, Any]]:
    """The whip starts safe, hanging (its Hang state, always visible)."""
    return [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:initial-safe"),
        event("EVENT_ACTOR_SET_STATE", {"actorId": "$self$", "spriteStateId": "Hang", "loopAnim": True},
              f"{key}:initial-hang"),
    ]


def whip_update_script(key: str, start_delay: int, sway_frames: int, swing_frames: int, hang_frames: int,
                       event: Event, wait: Callable[[int, str], dict[str, Any]],
                       branch: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    """Whipping live wire: hangs sparking, sways (safe warning), whips (group 1), hangs.

    Same first-cycle trick as the cables: the actor starts facing down; the first
    pass optionally waits ``start_delay`` and turns it up, so later cycles skip it.
    """

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first_cycle_true = [
        own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
    ]
    if start_delay > 0:
        first_cycle_true.append(wait(start_delay, f"{key}:start-delay"))
    return [
        branch("EVENT_IF_ACTOR_DIRECTION",
               {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
               f"{key}:first-cycle", first_cycle_true),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "sway-safe"),
        own("EVENT_ACTOR_SET_STATE", "sway-state", spriteStateId="Sway", loopAnim=True),
        wait(sway_frames, f"{key}:sway-time"),
        own("EVENT_ACTOR_SET_STATE", "swing-state", spriteStateId="Swing", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "swing-active"),
        wait(swing_frames, f"{key}:swing-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "hang-safe"),
        own("EVENT_ACTOR_SET_STATE", "hang-state", spriteStateId="Hang", loopAnim=True),
        wait(hang_frames, f"{key}:hang-time"),
    ]


def check() -> None:
    assert set(BOARDS) == set(HIDDEN_CABLES)
    assert CABLE_WARNING_FRAMES < CREAK_FRAMES, "cable reveal is brief; the board warns longer"
    assert BREAK_FRAMES < BOARD_REST_FRAMES
    grids = {"storm_climb": climb.collision_grid()}
    for scene, boards in BOARDS.items():
        for row, x0, x1 in boards:
            assert x1 - x0 + 1 == BOARD_CANVAS[0] // 8, "a board is exactly the sprite width"
            if scene in grids:
                grid = grids[scene]
                assert all(grid[row][x] != climb.COL_EMPTY for x in range(x0, x1 + 1)), (
                    f"{scene} board {x0}..{x1} must lie on a shelf row {row}")
                assert all(grid[row - 1][x] == climb.COL_EMPTY for x in range(x0, x1 + 1))
        for row, x0, x1 in HIDDEN_CABLES[scene]:
            assert x1 - x0 == 1, "the live arc sprite is two tiles wide"
    for scene, delays in CABLE_START_DELAYS.items():
        assert len(delays) == len(HIDDEN_CABLES[scene])
    for scene, layout in REDESIGN_ENTRY.items():
        assert scene in BOARDS and len(layout["delays"]) == len(layout["cables"])
        assert all(x1 - x0 + 1 == BOARD_CANVAS[0] // 8 for _, x0, x1 in layout["boards"])
        assert all(x1 - x0 == 1 for _, x0, x1 in layout["cables"])
    assert set(SCENE_JOB) == set(REDESIGN_SCENES) and set(SCENE_JOB.values()) == set(CABLE_TIMINGS)
    assert all(scene in BOARDS for scene in REDESIGN_SCENES)
    assert (CABLE_TIMINGS["climb"] == (CABLE_DARK_FRAMES, CABLE_WARNING_FRAMES, CABLE_ARC_FRAMES)
            ), "job 1 keeps the module's hidden-cable timings"
    for dark, warning, arc in CABLE_TIMINGS.values():
        assert warning < CREAK_FRAMES and dark > warning + arc


check()
