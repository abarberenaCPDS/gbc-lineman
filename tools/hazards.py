#!/usr/bin/env python3
"""Field-crew hazards that replace the falling rocks (HANDOFF item 6, Abe's pick:
"do #2", the recommended mix in docs/DESIGN_OPTIONS.md).

Two hazards, both delivered through each scene's existing group-1 contact reset
(``playerHit1Script`` respawns the hero), so neither freezes the player:

* **Cracked board**: a plank sprite on a shelf. A trigger over the plank sets
  ``VAR_ON_BOARD`` to the board's number while the hero stands there (its leave
  script clears it). The board's own update loop sees its number, creaks for
  ``CREAK_FRAMES``, and if the hero is still on it, gives way: Break state plus
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
    "storm_climb": [(30, 5, 7), (27, 14, 16), (9, 8, 10)],
    "wind_ridge": [(27, 26, 28)],   # floor, between T1 and the step to plateau B
    "pine_hollow": [],
}
HIDDEN_CABLES = {
    "storm_climb": [(16, 11, 12)],
    "wind_ridge": [],
    "pine_hollow": [(7, 11, 12)],
}
CABLE_START_DELAYS = {"storm_climb": [40], "pine_hollow": [90]}


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


def board_update_script(number: int, key: str, event: Event, wait: Callable[[int, str], dict[str, Any]],
                        if_value: Callable[..., dict[str, Any]],
                        set_value: Callable[..., dict[str, Any]],
                        creak_sound: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Creak while the hero stands on it; give way if they are still there."""

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    give_way = [
        own("EVENT_ACTOR_SET_STATE", "break-state", spriteStateId="Break", loopAnim=False),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "break-hit"),
        wait(BREAK_FRAMES, f"{key}:break-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "break-safe"),
        # The respawn teleports the hero without a leave event; clear it here.
        set_value(VAR_ON_BOARD, 0, f"{key}:clear"),
        wait(BOARD_REST_FRAMES, f"{key}:rest-time"),
    ]
    creak = [
        own("EVENT_ACTOR_SET_STATE", "creak-state", spriteStateId="Creak", loopAnim=True),
        *([creak_sound] if creak_sound else []),
        wait(CREAK_FRAMES, f"{key}:creak-time"),
        if_value(VAR_ON_BOARD, number, f"{key}:still-on", give_way, []),
        own("EVENT_ACTOR_SET_STATE", "idle-state", spriteStateId="Idle", loopAnim=True),
    ]
    return [
        if_value(VAR_ON_BOARD, number, f"{key}:on-check", creak,
                 [wait(1, f"{key}:idle-tick")]),
    ]


def board_start_script(key: str, event: Event) -> list[dict[str, Any]]:
    return [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:init-safe"),
        event("EVENT_ACTOR_SET_STATE", {"actorId": "$self$", "spriteStateId": "Idle", "loopAnim": True},
              f"{key}:init-idle"),
    ]


def cable_update_script(key: str, start_delay: int, event: Event,
                        wait: Callable[[int, str], dict[str, Any]],
                        branch: Callable[..., dict[str, Any]]) -> list[dict[str, Any]]:
    """Hidden cable: dark (hidden, safe) -> spark warning -> arc (group 1).

    Same first-cycle trick as the rosa arcs: the actor starts facing down; the
    first pass waits ``start_delay`` once and turns it up. ``branch`` is the
    scene's ``branch_event(command, args, key, true_events)``.
    """

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
        wait(CABLE_DARK_FRAMES, f"{key}:dark-time"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait(CABLE_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait(CABLE_ARC_FRAMES, f"{key}:arc-time"),
    ]


def cable_start_script(key: str, event: Event) -> list[dict[str, Any]]:
    return [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:init-safe"),
        event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:init-hidden"),
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


check()
