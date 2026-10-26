"""Storm Climb - deterministic geometry source for the vertical-climb slice.

This is data only for a 20x36-tile PLATFORM scene.  The existing storm-night
background supplies the mountain art; these values describe walkable ledges,
rock collision, timed debris columns, and wind-gust respawn lanes.

Units are 8x8-pixel tiles.  Collision bytes follow GB Studio's PLATFORM
semantics: solid=15 (0x0F), top/one-way=1 (0x01), and empty=0 (0x00).
"""

from __future__ import annotations

TILE = 8
MAP_W, MAP_H = 20, 36

# Collision bytes used by GB Studio PLATFORM scenes.
COL_EMPTY = 0x00
COL_TOP = 0x01  # one-way surface: land from above, jump through from below
COL_SOLID = 0x0F

# ---------------------------------------------------------------------------
# Mountain route, bottom to summit
#
# Platforms are (row, x_start, x_end), inclusive.  The alternating, overlapping
# shelves keep the route legible while allowing a straight-up option at every
# transition.  Every rise is exactly three tiles (24 px), matching the proven
# jump cadence in level.py.  The bottom shelf is the substation deck; the top
# shelf is House A's checkpoint ledge.
# ---------------------------------------------------------------------------
PLATFORMS = [
    (33, 0, 7),
    (30, 3, 16),  # room to steer around the lower debris before the next jump
    (27, 9, 18),
    (24, 5, 15),  # two-tile supported landing right of the row-25 hazard
    (21, 1, 10), # preserve a two-tile corridor clear of the next falling rock
    (18, 6, 15),
    (15, 11, 19),
    (12, 7, 15),
    (9, 2, 10),
    (6, 7, 16),
]

# Rows occupied by the valley deck structure: its one-way top and two solid
# foundation rows.  The staggered edge buttresses make the lower mountain feel
# enclosed without closing any of the overlapping central ascent routes.
DECK_ROWS = [33, 34, 35]
SOLID_BLOCKS = [
    (0, MAP_W - 1, 34, 35),  # continuous valley bedrock
    (18, 19, 28, 29),       # right-side rock buttress
    (0, 1, 25, 26),         # left-side rock buttress
    (18, 19, 22, 23),
    (0, 1, 19, 20),
    (18, 19, 16, 17),
    (0, 1, 13, 14),
    (18, 19, 10, 11),
]

# ---------------------------------------------------------------------------
# Storm hazards
#
# Gust lanes are (row, x_start, x_end), inclusive. They mark future wind zones
# between shelves; lane 1 has an actor-owned timed collision, while the other
# seven trigger resources are inert until their routes are proven in play.
# Their staggered placement leaves a climbable corridor through every gap.
# Debris entries are timed actor-drop columns, with inclusive row bounds.
# They can cross one-way shelves (but never solid rock); landing columns stay
# within the overlap and away from platform edges. Runtime fairness needs play.
# ---------------------------------------------------------------------------
GUST_LANES = [
    (31, 9, 11),
    (28, 14, 16),
    (25, 10, 12),
    (22, 2, 4),
    (19, 12, 14),
    (16, 1, 3),
    (13, 8, 10),
    (10, 3, 5),
]

# First timed gust proves the hazard language in the lower playable slice.
# Remaining lanes are still static instant-reset triggers until reviewed.
TIMED_GUST_LANE_INDICES = (0,)
GUST_WARNING_FRAMES = 54
GUST_ACTIVE_FRAMES = 20
GUST_REST_FRAMES = 90

HAZARD_DEBRIS = [
    {"row_top": 29, "x": 6, "row_bottom": 32},  # clear the 24px worker's first-jump corridor
    {"row_top": 25, "x": 15, "row_bottom": 29},
    {"row_top": 17, "x": 7, "row_bottom": 20},
    {"row_top": 8, "x": 8, "row_bottom": 11},
]

# Frames are authored explicitly so warnings can be tuned without script edits.
DEBRIS_WARNING_FRAMES = 60
DEBRIS_REST_FRAMES = 90
DEBRIS_STEP_PIXELS = 2
DEBRIS_STEP_FRAMES = 2

# The checkpoint tile is immediately above the summit shelf, with open
# headroom.  The last hazard lane is below row 10, leaving the house safe.
HOUSE_A = {"x": 11, "y": 5}

# The base substation and player begin on the wide bottom deck.  START is the
# empty tile occupied by the player; the one-way deck surface is directly
# beneath it, as in level.py's spawn convention.
SUBSTATION = {"x": 1, "y": 32}
START = (2, 32)
# Walking off the bottom deck's left edge returns to the service opening.
# (x, y, width, height) in tiles: column 0 over the 24px hero's rows 30-32,
# clear of START so a respawn never re-fires it.
STREET_EXIT = (0, 30, 1, 3)

# ---------------------------------------------------------------------------
# Amara's line (first repair job): a storm-snapped pole on shelf 21 leaves a
# dangling cable end. Carry it past debris 3 and up to the junction box on
# shelf 15; plugging it in energizes the line, which Amara's door requires.
# Positions are actor tiles (the tile the actor stands in).
# ---------------------------------------------------------------------------
DAMAGED_POLE = (3, 20)      # cable-end pickup, left end of shelf 21
JUNCTION_BOX = (17, 14)     # plug-in point, right end of shelf 15
VAR_CARRYING_CABLE = "6"
VAR_LINE_LIVE = "7"
# Grid sprites share OBJ palette slot 2 (free in the climb since the house icon
# was replaced by Amara; the opening's slot 2 is the terminal palette).
GRID_SPRITE_PALETTE_SLOT = 2
# BG slot 5 (metal) carries the drawn cable route. Only colour index 1 may be
# used by cable pixels anywhere in slot 5, so swapping index 1 to cyan lights
# the whole route without recolouring any other slot-5 pixel.
LINE_BG_SLOT = 5
LINE_COLOR_INDEX = 1
METAL_DEAD = ["17232E", "3D5364", "7791A3", "C7DCE1"]
METAL_LIVE = ["17232E", "38C8D8", "7791A3", "C7DCE1"]

import uuid as _uuid

_GRID_NAMESPACE = _uuid.UUID("5b0e7f1c-3c41-5f0e-9a8b-6c1d2e3f4a5b")


def grid_resource_id(key: str) -> str:
    """Stable IDs for grid-repair resources shared by several generators."""
    return str(_uuid.uuid5(_GRID_NAMESPACE, "mr-cfe:grid:" + key))


def collision_grid() -> list[list[int]]:
    """Return the row-major PLATFORM collision bytes (MAP_H by MAP_W)."""
    grid = [[COL_EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
    for row, x0, x1 in PLATFORMS:
        for x in range(x0, x1 + 1):
            grid[row][x] = COL_TOP
    for x0, x1, row0, row1 in SOLID_BLOCKS:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_SOLID
    return grid


def _hazard_cells() -> set[tuple[int, int]]:
    """Expand all gust and debris geometry into (row, x) cells."""
    cells: set[tuple[int, int]] = set()
    for row, x0, x1 in GUST_LANES:
        cells.update((row, x) for x in range(x0, x1 + 1))
    for debris in HAZARD_DEBRIS:
        cells.update(
            (row, debris["x"])
            for row in range(debris["row_top"], debris["row_bottom"] + 1)
        )
    return cells


def _self_check() -> None:
    """Exhaustively check the geometry and fairness invariants at import time."""
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(row) == MAP_W for row in grid), "grid size"
    assert all(cell in (COL_EMPTY, COL_TOP, COL_SOLID) for row in grid for cell in row), (
        "unexpected PLATFORM collision byte"
    )

    # All authored geometry stays within the scene, and every shelf has a
    # landing interval that overlaps the next one for a direct vertical route.
    for row, x0, x1 in PLATFORMS:
        assert 0 <= row < MAP_H and 0 <= x0 <= x1 < MAP_W, "platform bounds"
        assert all(grid[row][x] == COL_TOP for x in range(x0, x1 + 1)), (
            f"platform row {row} is not one-way throughout"
        )
    platform_rows = [row for row, _, _ in PLATFORMS]
    assert platform_rows == sorted(platform_rows, reverse=True), "platform order"
    for lower, upper in zip(PLATFORMS, PLATFORMS[1:]):
        lower_row, lower_x0, lower_x1 = lower
        upper_row, upper_x0, upper_x1 = upper
        rise = lower_row - upper_row
        assert rise == 3, f"platform rows {lower_row}->{upper_row} rise {rise}, expected 3"
        assert max(lower_x0, upper_x0) <= min(lower_x1, upper_x1), (
            f"platform rows {lower_row}->{upper_row} have no vertical landing overlap"
        )

    # The deck metadata agrees with the actual floor and lower landing shelf.
    assert DECK_ROWS == [33, 34, 35], "deck row definition"
    assert all(grid[34][x] == COL_SOLID and grid[35][x] == COL_SOLID for x in range(MAP_W)), (
        "valley bedrock must span the scene"
    )
    assert all(grid[33][x] == COL_TOP for x in range(8)), "bottom deck surface"

    # Spawn and substation occupy clear standing tiles with one-way ground.
    sx, sy = START
    assert 0 <= sx < MAP_W and 0 <= sy < MAP_H - 1, "spawn bounds"
    assert grid[sy][sx] == COL_EMPTY, "spawn blocked"
    assert grid[sy + 1][sx] == COL_TOP, "spawn floating"
    sub_x, sub_y = SUBSTATION["x"], SUBSTATION["y"]
    assert grid[sub_y][sub_x] == COL_EMPTY, "substation tile blocked"
    assert grid[sub_y + 1][sub_x] == COL_TOP, "substation floating"

    # Checkpoint tile and its two tiles of headroom are clear; its support is
    # the summit one-way shelf, and it is separated from every hazard.
    hx, hy = HOUSE_A["x"], HOUSE_A["y"]
    assert 0 <= hx < MAP_W and 2 <= hy < MAP_H - 1, "house bounds"
    assert grid[hy][hx] == COL_EMPTY, "house tile blocked"
    assert grid[hy - 1][hx] == COL_EMPTY and grid[hy - 2][hx] == COL_EMPTY, (
        "house needs two empty headroom tiles"
    )
    assert grid[hy + 1][hx] == COL_TOP, "house has no one-way standing surface"
    assert all(abs(row - hy) > 2 for row, _ in _hazard_cells()), "house too close to hazard"

    # Static reset lanes must occupy empty cells. Falling rocks may cross a
    # one-way shelf, but must never pass through solid rock.
    for row, x0, x1 in GUST_LANES:
        assert 0 <= row < MAP_H and 0 <= x0 <= x1 < MAP_W, "gust lane bounds"
        for x in range(x0, x1 + 1):
            assert grid[row][x] == COL_EMPTY, f"gust cell {x},{row} is not empty"
    assert len(GUST_LANES) >= 3, "need at least three gust lanes"
    assert TIMED_GUST_LANE_INDICES == tuple(sorted(set(TIMED_GUST_LANE_INDICES)))
    assert all(0 <= i < len(GUST_LANES) and GUST_LANES[i][2] - GUST_LANES[i][1] == 2
               for i in TIMED_GUST_LANE_INDICES), "timed gusts need three-tile lanes"
    assert len(HAZARD_DEBRIS) >= 2, "need at least two debris columns"
    for debris in HAZARD_DEBRIS:
        row_top, x, row_bottom = (
            debris["row_top"], debris["x"], debris["row_bottom"]
        )
        assert 0 <= row_top <= row_bottom < MAP_H and 0 <= x < MAP_W, (
            "debris column bounds"
        )
        assert all(grid[row][x] != COL_SOLID for row in range(row_top, row_bottom + 1)), (
            f"debris column x={x} intersects solid rock"
        )
        containing_gap = None
        for lower, upper in zip(PLATFORMS, PLATFORMS[1:]):
            lower_row, lower_x0, lower_x1 = lower
            upper_row, upper_x0, upper_x1 = upper
            if upper_row < row_bottom < lower_row:
                containing_gap = (lower_x0, lower_x1, upper_x0, upper_x1)
                break
        assert containing_gap is not None, "debris must end within an ascent gap"
        lower_x0, lower_x1, upper_x0, upper_x1 = containing_gap
        assert lower_x0 < x < lower_x1 and upper_x0 < x < upper_x1, (
            "debris must avoid both platform edges"
        )

    # For every three-row jump gap, a two-tile footprint remains free of all
    # gust/debris cells AND supported by both shelves. This conservative
    # corridor matches the approved 24px worker's 12px-wide collision bounds.
    hazards = _hazard_cells()
    for lower, upper in zip(PLATFORMS, PLATFORMS[1:]):
        lower_row, lower_x0, lower_x1 = lower
        upper_row, upper_x0, upper_x1 = upper
        first = max(lower_x0, upper_x0)
        last = min(lower_x1, upper_x1)
        clear_pairs = [
            (x, x + 1) for x in range(first, last)
            if all((row, column) not in hazards
                   for row in range(upper_row + 1, lower_row)
                   for column in (x, x + 1))
        ]
        assert clear_pairs, (
            f"platform rows {lower_row}->{upper_row} have no two-tile hazard-free ascent"
        )

    ex, ey, ew, eh = STREET_EXIT
    exit_tiles = {(y, x) for y in range(ey, ey + eh) for x in range(ex, ex + ew)}
    assert all(grid[y][x] == COL_EMPTY for y, x in exit_tiles), "street exit must be open"
    assert grid[ey + eh][ex] != COL_EMPTY, "street exit stands on the bottom deck"
    assert START[0] >= ex + ew + 1, "START keeps the 16px-wide hero clear of the street exit"
    assert not exit_tiles & hazards, "street exit inside a hazard"

    # Grid-repair props stand on shelves with 24px headroom, clear of hazards.
    for x, y in (DAMAGED_POLE, JUNCTION_BOX):
        assert grid[y][x] == COL_EMPTY and grid[y + 1][x] == COL_TOP, "grid prop footing"
        assert grid[y - 1][x] == COL_EMPTY and grid[y - 2][x] == COL_EMPTY, "grid prop headroom"
        assert (y, x) not in hazards, "grid prop inside a hazard"


_self_check()
