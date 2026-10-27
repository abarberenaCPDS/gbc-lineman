"""Signal Hill - deterministic contract for Priya's repair job (job 3).

Data only for a 40x18-tile PLATFORM scene reached from Hiroshi's porch once his
house is powered. Live cable arcs are the featured hazard (step 3 of the hazard
ladder in docs/redesign-brief.md): a downed wire between two posts sparks as a
warning, then arcs (hits) and rests, like a gust lane. One wind gust from
Hiroshi's job sits between the two arcs. The Live Wire phase carries the snapped
cable from a pole on a two-step rock to a junction box on Priya's porch;
powering the line lights her window and switches on her computer and router
(Blackout Grid: she can work and study online again).

Every generator for this job reads this module: ``make_rosa_art.py`` (art +
collision-aligned background), ``make_rosa_sprites.py`` (Priya, her
workstation and the live arc) and ``make_rosa_scene.py`` (scene, actors,
triggers, scripts).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching ridge.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import ridge

TILE = 8
MAP_W, MAP_H = 40, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# ---------------------------------------------------------------------------
# Terrain, left to right
#
# The floor is solid from GROUND_ROW down; the 24px hero stands in rows 12-14.
# A two-step rock (each step one 8-frame tap, three tiles) holds the pole.
# Priya's porch repeats the Wind Ridge lesson: props stand on row 11, above
# every hazard row, so the 10-sprites-per-scanline limit holds.
# ---------------------------------------------------------------------------
GROUND_ROW = 15
# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, 14),                  # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (4, 8, 12, 14),                 # lower rock step (top surface row 12)
    (6, 8, 9, 11),                  # upper rock step (top surface row 9); pole stands on it
    (32, 38, 12, 14),               # Priya's porch step (top surface row 12)
]
PORCH_ROW = 11
LEDGES: list[tuple[int, int, int]] = []

START = (2, 14)            # entry from Hiroshi's porch, facing right
DAMAGED_POLE = (7, 8)     # cable-end pickup on the upper step (stands on row 9)
JUNCTION_BOX = (33, 11)    # plug-in point at the top of the porch step
ROSA = (34, 11)            # Priya waits outside, left of her door
WORKSTATION = (37, 11)     # computer + router on the porch table: Off -> On
HOUSE_DOOR = (36, 11)      # doorway column of Priya's house (art)
HOUSE_RECT = (35, 38, 5, 11)    # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(35, 8), (38, 8)]
# Door checkpoint trigger: top row of a 24px hero standing on the porch.
DOOR_TRIGGER = (35, 9, 3, 1)

# ---------------------------------------------------------------------------
# Hazards
#
# Lanes are (row, x0, x1) inclusive on the hero's chest row. Arcs are two
# tiles wide (a 16px sprite, two 8x16 OBJs); the gust reuses the 24px
# climb_gust sprite. Standing gaps of at least three tiles separate lanes.
# ---------------------------------------------------------------------------
ARC_LANES = [
    (13, 18, 19),
    (13, 29, 30),
]
ARC_START_DELAYS = [0, 70]
ARC_WARNING_FRAMES = 48     # sparks: safe, telegraphs the arc
ARC_ACTIVE_FRAMES = 24      # arc: hits (collision group 1)
ARC_REST_FRAMES = 80        # dark wire: safe

GUST_LANES = [(13, 23, 25)]
GUST_START_DELAYS = [35]
GUST_WARNING_FRAMES = climb.GUST_WARNING_FRAMES
GUST_ACTIVE_FRAMES = climb.GUST_ACTIVE_FRAMES
GUST_REST_FRAMES = climb.GUST_REST_FRAMES

# ---------------------------------------------------------------------------
# Cable route (background art), exactly like ridge.py: BG slot LINE_BG_SLOT
# colour index LINE_COLOR_INDEX, so one palette swap lights it. Pole top ->
# overhead span -> junction box -> house wall.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
CABLE_ROUTE = [(7, 5), (7, 4), (33, 4), (33, 10), (33, 4), (35, 4)]

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared and reset by
# every scene init; vars 10/11 belong to this job.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "10"
VAR_HOME_POWERED = "11"    # Priya checkpoint; moves respawn to the door
VARIABLES = [
    (VAR_LINE_LIVE, "Hill Line Live", "var_hill_line_live"),
    (VAR_HOME_POWERED, "Rosa Home Powered", "var_rosa_home_powered"),
]
HUD_TEXT = "LINE %D1$10$/1 HOME %D1$11$/1"

# Entry from Wind Ridge: the right end of Hiroshi's porch, past his door. Gated
# on his checkpoint (ridge var 9). The refusal shows text only; it never
# nudges the hero, because a nudge plus leftover momentum re-enters the
# trigger and loops (exact ROM 147c23be, summit exit).
RIDGE_EXIT = (ridge.MAP_W - 2, 9, 1, 3)   # right end of Hiroshi's porch
RIDGE_EXIT_GATE_VAR = ridge.VAR_HOME_POWERED   # "9"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots: 0 worker, 1 Priya, 2 grid sprites (cable end, junction box,
# workstation), 3 live arc, 5 gust - matching the climb/ridge layout.
ROSA_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = 3
GUST_SPRITE_PALETTE_SLOT = 5
# Hardware colours, index 0 transparent placeholder.
ROSA_SPRITE_HARDWARE = ["000000", "F0C8A8", "B04A6A", "2A1E2E"]   # skin, rose cardigan, dark
ARC_SPRITE_HARDWARE = ["000000", "FFF6B0", "F2C230", "3A6CF0"]    # white-hot, yellow, blue
WINDOW_BG_SLOT = 3

ROSA_STATES = ["Waiting", "Relieved"]
WORKSTATION_STATES = ["Off", "On"]
ARC_STATES = ["Warning", "Arc"]

_ROSA_NAMESPACE = _uuid.UUID("4b1e7c92-6d3a-5f81-9c2e-7a5d3b1f0e64")


def resource_id(key: str) -> str:
    """Stable IDs for every resource this job generates."""
    return str(_uuid.uuid5(_ROSA_NAMESPACE, "mr-cfe:rosa:" + key))


SCENE_ID = resource_id("scene:signal-hill")
BACKGROUND_ID = resource_id("background:signal-hill")
ROSA_SPRITE_ID = resource_id("sprite:rosa")
WORKSTATION_SPRITE_ID = resource_id("sprite:rosa_workstation")
ARC_SPRITE_ID = resource_id("sprite:live_arc")


def collision_grid() -> list[list[int]]:
    """Row-major PLATFORM collision bytes (MAP_H rows by MAP_W columns)."""
    grid = [[COL_EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
    for row in range(GROUND_ROW, MAP_H):
        for x in range(MAP_W):
            grid[row][x] = COL_SOLID
    for row, x0, x1 in LEDGES:
        for x in range(x0, x1 + 1):
            grid[row][x] = COL_TOP
    for x0, x1, row0, row1 in SOLID_BLOCKS:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_SOLID
    return grid


def hazard_lanes() -> list[tuple[int, int, int]]:
    """All lanes, left to right."""
    return sorted([*ARC_LANES, *GUST_LANES], key=lambda lane: lane[1])


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in hazard_lanes() for x in range(x0, x1 + 1)}


def _stands(grid: list[list[int]], x: int, y: int) -> bool:
    """A 24px actor at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (COL_TOP, COL_SOLID))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = (START, DAMAGED_POLE, JUNCTION_BOX, ROSA, WORKSTATION, HOUSE_DOOR)
    for x, y in props:
        assert 0 < x < MAP_W - 1 and HUD_ROWS + 2 <= y < MAP_H - 1, f"bounds {(x, y)}"
        assert _stands(grid, x, y), f"actor tile {(x, y)} must stand clear on support"
    hazards = _hazard_cells()
    for x, y in props:
        assert all(abs(x - hx) > 1 or abs(y - hy) > 2 for hy, hx in hazards), (
            f"prop {(x, y)} too close to a hazard"
        )
    for row, x0, x1 in ARC_LANES:
        assert x1 - x0 == 1, "arc lanes match the 16px arc sprite"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in hazard_lanes():
        assert row == GROUND_ROW - 2, "lanes sit on the walking hero's chest row"
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[GROUND_ROW][x] == COL_SOLID for x in range(x0, x1 + 1)), "lane floor"
    lanes = hazard_lanes()
    for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between lanes"
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    # Rock steps are one tap (three tiles) above whatever they stand on.
    lower, upper, porch = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
    assert GROUND_ROW - lower[2] == 3 and lower[3] == GROUND_ROW - 1
    assert lower[2] - upper[2] == 3 and upper[3] == lower[2] - 1
    assert lower[0] < upper[0] and upper[1] <= lower[1], "upper step sits on the lower"
    assert GROUND_ROW - porch[2] == 3 and porch[2] - 1 == PORCH_ROW
    # Walking off the upper step lands clear of every lane. Exact ROMs 3dd78a6e
    # and c2aeecad: holding right through the fall lands the hero up to 42px
    # past the step's edge, box 16px wider. Keep lanes nine tiles past the edge.
    assert all(x0 - upper[1] >= 9 for _, x0, _ in lanes), "step landing too close to a lane"
    # The last lane leaves a tile to hop from onto the porch.
    assert porch[0] - lanes[-1][2] >= 2, "need a takeoff tile before the porch"
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert ROSA[0] == JUNCTION_BOX[0] + 1 and WORKSTATION[0] > HOUSE_DOOR[0]
    xs = [p[0] for p in CABLE_ROUTE]
    assert xs[0] == DAMAGED_POLE[0] and JUNCTION_BOX[0] in xs and HOUSE_RECT[0] in xs
    assert all(HUD_ROWS <= y < GROUND_ROW and 0 <= x < MAP_W for x, y in CABLE_ROUTE)
    assert START[0] < DAMAGED_POLE[0] < lanes[0][1] < JUNCTION_BOX[0] < HOUSE_DOOR[0]
    # Ridge entry: the right end of Hiroshi's porch, clear of his door trigger.
    ex, ey, ew, eh = RIDGE_EXIT
    rtx, rty, rtw, _ = ridge.DOOR_TRIGGER
    assert ex >= rtx + rtw and ey + eh - 1 == ridge.PORCH_ROW and ex < ridge.MAP_W - 1
    ids = {SCENE_ID, BACKGROUND_ID, ROSA_SPRITE_ID, WORKSTATION_SPRITE_ID, ARC_SPRITE_ID}
    assert len(ids) == 5, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "8", "9"})


_self_check()
