"""Pine Hollow - deterministic contract for Emil's family's repair job (job 4).

Data only for a 40x18-tile PLATFORM scene reached from Priya's porch once her
house is powered. The job mixes the hazards learned so far: a wind gust on top
of a long rock mesa (the pole stands up there), a hidden cable lane on the mesa,
then a live cable arc on the floor below. Powering the line lights the family's window and
switches on their electric stove so dinner can cook (Blackout Grid).

Every generator for this job reads this module: ``make_kiko_art.py`` (art +
collision-aligned background), ``make_kiko_sprites.py`` (Emil and the stove)
and ``make_kiko_scene.py`` (scene, actors, triggers, scripts). The live arc
reuses ``live_arc`` from Priya's job; the gust reuses the climb sprites.

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row). Collision bytes follow GB Studio PLATFORM semantics:
solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import rosa

TILE = 8
MAP_W, MAP_H = 40, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

HUD_ROWS = 2

# ---------------------------------------------------------------------------
# Terrain, left to right
#
# Floor from GROUND_ROW down; the 24px hero stands in rows 12-14 on the floor
# and rows 6-8 on the mesa. A one-tap step leads onto a long mesa (top surface
# row 9). Walking off the mesa's right edge can carry the hero ~42px past it
# (exact ROMs 3dd78a6e/c2aeecad), so the first floor lane sits >= 9 tiles on.
# Props stand on the porch (row 11), above every hazard row.
# ---------------------------------------------------------------------------
GROUND_ROW = 15
SOLID_BLOCKS = [
    (0, 0, 2, 14),                  # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (5, 6, 12, 14),                 # step up to the mesa (top surface row 12)
    (7, 18, 9, 14),                 # the mesa (top surface row 9); pole stands on it
    (31, 38, 12, 14),               # the family's porch step (top surface row 12)
]
STEP, MESA, PORCH = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
MESA_ROW = 8                        # feet row on the mesa
PORCH_ROW = 11
LEDGES: list[tuple[int, int, int]] = []

START = (2, 14)            # entry from Priya's porch, facing right
DAMAGED_POLE = (9, 8)      # cable-end pickup on the mesa
JUNCTION_BOX = (33, 11)    # plug-in point on the porch
KIKO = (34, 11)            # Emil waits outside, left of the door
STOVE = (37, 11)           # electric stove with a pot, on the porch: Off -> On
HOUSE_DOOR = (36, 11)
HOUSE_RECT = (35, 38, 5, 11)
HOUSE_WINDOWS = [(35, 8), (38, 8)]
DOOR_TRIGGER = (35, 9, 3, 1)

# ---------------------------------------------------------------------------
# Hazards
#
# Lanes are (row, x0, x1) inclusive on the walking hero's chest row: row 7 on
# the mesa, row 13 on the floor. Gust lanes are 3 wide (climb_gust), arcs 2.
# The mesa's hidden cable (hazards.HIDDEN_CABLES["pine_hollow"]) is placed by
# hazards.py; the falling debris column is retired.
# ---------------------------------------------------------------------------

GUST_LANES = [(MESA_ROW - 1, 15, 17)]
GUST_START_DELAYS = [40]
GUST_WARNING_FRAMES = climb.GUST_WARNING_FRAMES
GUST_ACTIVE_FRAMES = climb.GUST_ACTIVE_FRAMES
GUST_REST_FRAMES = climb.GUST_REST_FRAMES

ARC_LANES = [(GROUND_ROW - 2, 27, 28)]
ARC_START_DELAYS = [0]
ARC_WARNING_FRAMES = rosa.ARC_WARNING_FRAMES
ARC_ACTIVE_FRAMES = rosa.ARC_ACTIVE_FRAMES
ARC_REST_FRAMES = rosa.ARC_REST_FRAMES
ARC_SPRITE_ID = rosa.ARC_SPRITE_ID

# ---------------------------------------------------------------------------
# Cable route (background art), as in rosa.py: one palette swap lights it.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
CABLE_ROUTE = [(9, 5), (9, 4), (33, 4), (33, 10), (33, 4), (35, 4)]

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "12"
VAR_HOME_POWERED = "13"    # Emil's checkpoint; moves respawn to the door
VARIABLES = [
    (VAR_LINE_LIVE, "Hollow Line Live", "var_hollow_line_live"),
    (VAR_HOME_POWERED, "Kiko Home Powered", "var_kiko_home_powered"),
]
HUD_TEXT = "LINE %D1$12$/1 HOME %D1$13$/1"

# Entry from Signal Hill: the right end of Priya's porch, past her door, gated on
# her checkpoint (var 11). Text-only refusal, never a nudge (see rosa.py).
HILL_EXIT = (38, 9, 1, 3)
HILL_EXIT_GATE_VAR = rosa.VAR_HOME_POWERED     # "11"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots: 0 worker, 1 Emil, 2 grid sprites (cable end, junction box, stove),
# 3 live arc, 4 unused (the retired debris slot), 5 gust.
KIKO_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = rosa.ARC_SPRITE_PALETTE_SLOT
GUST_SPRITE_PALETTE_SLOT = 5
# Hardware colours, index 0 transparent: skin, mustard-yellow jacket, dark.
KIKO_SPRITE_HARDWARE = ["000000", "D9A97E", "E0A82E", "2B2420"]
ARC_SPRITE_HARDWARE = rosa.ARC_SPRITE_HARDWARE
WINDOW_BG_SLOT = 3

KIKO_STATES = ["Waiting", "Relieved"]
STOVE_STATES = ["Off", "On"]

_KIKO_NAMESPACE = _uuid.UUID("d27a4e1c-3b95-5c08-8f6e-1a9c2b7d4e53")


def resource_id(key: str) -> str:
    """Stable IDs for every resource this job generates."""
    return str(_uuid.uuid5(_KIKO_NAMESPACE, "mr-cfe:kiko:" + key))


SCENE_ID = resource_id("scene:pine-hollow")
BACKGROUND_ID = resource_id("background:pine-hollow")
KIKO_SPRITE_ID = resource_id("sprite:kiko")
STOVE_SPRITE_ID = resource_id("sprite:kiko_stove")


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
    """Gust and arc lanes, left to right."""
    return sorted([*GUST_LANES, *ARC_LANES], key=lambda lane: lane[1])


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in hazard_lanes() for x in range(x0, x1 + 1)}


def _stands(grid: list[list[int]], x: int, y: int) -> bool:
    """A 24px actor at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (COL_TOP, COL_SOLID))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = (START, DAMAGED_POLE, JUNCTION_BOX, KIKO, STOVE, HOUSE_DOOR)
    for x, y in props:
        assert 0 < x < MAP_W - 1 and HUD_ROWS + 2 <= y < MAP_H - 1, f"bounds {(x, y)}"
        assert _stands(grid, x, y), f"actor tile {(x, y)} must stand clear on support"
    hazards = _hazard_cells()
    assert all(r >= HUD_ROWS for r, _ in hazards), "hazards under the HUD"
    for x, y in props:
        assert all(abs(x - hx) > 1 or abs(y - hy) > 2 for hy, hx in hazards), (
            f"prop {(x, y)} too close to a hazard"
        )
    # Steps are one tap (three tiles) above what they stand on.
    assert GROUND_ROW - STEP[2] == 3 and STEP[3] == GROUND_ROW - 1
    assert STEP[2] - MESA[2] == 3 and STEP[1] + 1 == MESA[0], "step leads onto the mesa"
    assert MESA[2] - 1 == MESA_ROW and MESA[3] == GROUND_ROW - 1
    assert GROUND_ROW - PORCH[2] == 3 and PORCH[2] - 1 == PORCH_ROW
    # Lanes sit on the chest row of whatever surface they cross.
    for row, x0, x1 in hazard_lanes():
        surface = MESA[2] if MESA[0] <= x0 and x1 <= MESA[1] else GROUND_ROW
        assert row == surface - 2, f"lane {(row, x0, x1)} not on the chest row"
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[surface][x] == COL_SOLID for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in ARC_LANES:
        assert x1 - x0 == 1, "arc lanes match the 16px arc sprite"
    # Standing gaps of three tiles between every hazard lane on the mesa.
    columns = sorted([(x0, x1) for _, x0, x1 in hazard_lanes()])
    for (_, a1), (b0, _) in zip(columns, columns[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Walking off the mesa lands clear of every floor lane.
    for row, x0, _ in ARC_LANES:
        assert x0 - MESA[1] >= 9, "mesa landing too close to a floor lane"
    assert PORCH[0] - ARC_LANES[-1][2] >= 2, "need a takeoff tile before the porch"
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert KIKO[0] == JUNCTION_BOX[0] + 1 and STOVE[0] > HOUSE_DOOR[0]
    xs = [p[0] for p in CABLE_ROUTE]
    assert xs[0] == DAMAGED_POLE[0] and JUNCTION_BOX[0] in xs and HOUSE_RECT[0] in xs
    assert CABLE_ROUTE[0] == (DAMAGED_POLE[0], DAMAGED_POLE[1] - 3), "cable leaves the pole top"
    assert all(HUD_ROWS <= y < GROUND_ROW and 0 <= x < MAP_W for x, y in CABLE_ROUTE)
    assert START[0] < DAMAGED_POLE[0] < JUNCTION_BOX[0] < HOUSE_DOOR[0]
    # Entry from Signal Hill: right end of Priya's porch, clear of her door trigger.
    ex, ey, ew, eh = HILL_EXIT
    rtx, rty, rtw, _ = rosa.DOOR_TRIGGER
    assert ex >= rtx + rtw and ey + eh - 1 == rosa.PORCH_ROW and ex < rosa.MAP_W - 1
    ids = {SCENE_ID, BACKGROUND_ID, KIKO_SPRITE_ID, STOVE_SPRITE_ID}
    assert len(ids) == 4, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({str(n) for n in range(12)})


_self_check()
