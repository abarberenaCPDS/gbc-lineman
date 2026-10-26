"""Wind Ridge - deterministic contract for Tomás's repair job (job 2).

Data only for a 40x18-tile PLATFORM scene: a two-screen horizontal traverse
reached from Marta's summit once her line is live. Timed gusts are the
featured hazard (step 2 of the hazard ladder in docs/redesign-brief.md), with
one falling-debris column. The Live Wire phase carries a snapped cable from a
pole to a junction box; powering the line switches on Tomás's oxygen
concentrator and warms his window (Blackout Grid).

Every generator for this job reads this module: ``make_ridge_art.py`` (art +
collision-aligned background), ``make_tomas_sprites.py`` (Tomás and the
concentrator) and ``make_ridge_scene.py`` (scene, actors, triggers, scripts).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching climb.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb

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
# The ridge floor is solid from GROUND_ROW down; the 24px hero stands in rows
# 12-14. A rock step plateau (three tiles high, one 8-frame tap) holds the
# pole and breaks the walk before the gust lanes.
# ---------------------------------------------------------------------------
GROUND_ROW = 15
# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, 14),        # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (13, 18, 12, 14),     # rock step plateau (top surface row 12); pole stands on it
    (32, 38, 12, 14),     # Tomás's porch step (top surface row 12): one tap up from the gusts
]
# Exact-ROM play showed the house props sharing the gusts' scanlines exceeded the
# 10-sprites-per-line limit (the concentrator lost its top half). On the porch,
# actors stand on row 11, above every gust row.
PORCH_ROW = 11
# One-way ledges (row, x0, x1) inclusive. None yet: a single jump rises three
# tiles, so a side route needs stepping stones (planned with the connector
# collectibles). Exact-ROM play showed a row-9 catwalk was unreachable.
LEDGES: list[tuple[int, int, int]] = []

START = (2, 14)            # entry from Marta's summit, facing right
DAMAGED_POLE = (16, 11)    # cable-end pickup on the step plateau (stands on row 12)
JUNCTION_BOX = (33, 11)    # plug-in point at the top of the porch step
TOMAS = (34, 11)           # Tomás waits outside, left of his door
CONCENTRATOR = (37, 11)    # oxygen concentrator on the porch: Off -> On
HOUSE_DOOR = (36, 11)      # doorway column of Tomás's house (art)
# House body in the background art, inclusive tile rectangle.
HOUSE_RECT = (35, 38, 5, 11)   # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(35, 8), (38, 8)]

# Door checkpoint trigger: top row of a 24px hero standing on the porch at the
# door columns, like Marta's arrival trigger. (x, y, width, height).
DOOR_TRIGGER = (35, 9, 3, 1)

# ---------------------------------------------------------------------------
# Hazards
#
# Gust lanes are (row, x0, x1) inclusive, three tiles wide to fit the authored
# 24x8 climb_gust sprite. Row 13 is the hero's chest on the floor; each gust
# can be timed (walk through during rest) or jumped (8-frame tap clears it).
# Each lane has its own start delay so two gusts never fire in lockstep.
# ---------------------------------------------------------------------------
GUST_LANES = [
    (13, 24, 26),
    (13, 29, 31),
]
GUST_START_DELAYS = [0, 82]        # frames before the first warning, per lane
GUST_WARNING_FRAMES = climb.GUST_WARNING_FRAMES
GUST_ACTIVE_FRAMES = climb.GUST_ACTIVE_FRAMES
GUST_REST_FRAMES = climb.GUST_REST_FRAMES

# One debris column between the pole plateau and the first gust. Exact-ROM play
# showed x21 is where the hero lands walking off the plateau; x22 keeps the
# landing (x19-21) clear so the rock can be timed from the floor.
HAZARD_DEBRIS = [
    {"row_top": 4, "x": 22, "row_bottom": 14},
]
DEBRIS_WARNING_FRAMES = climb.DEBRIS_WARNING_FRAMES
DEBRIS_REST_FRAMES = climb.DEBRIS_REST_FRAMES
DEBRIS_STEP_PIXELS = climb.DEBRIS_STEP_PIXELS
DEBRIS_STEP_FRAMES = climb.DEBRIS_STEP_FRAMES

# ---------------------------------------------------------------------------
# Cable route (background art). Drawn only with BG slot LINE_BG_SLOT colour
# index LINE_COLOR_INDEX, exactly as in the climb, so one palette swap lights
# it. Polyline of tile cells, pole top -> overhead span -> junction box ->
# house wall. The art generator draws a 1-2 px line through these cells.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
CABLE_ROUTE = [(16, 8), (16, 6), (33, 6), (33, 10), (33, 6), (35, 6)]

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared with the climb
# and reset by every scene init; vars 8/9 belong to this job.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "8"
VAR_HOME_POWERED = "9"     # Tomás checkpoint; moves respawn to the door
VARIABLES = [
    (VAR_LINE_LIVE, "Ridge Line Live", "var_ridge_line_live"),
    (VAR_HOME_POWERED, "Tomas Home Powered", "var_tomas_home_powered"),
]
HUD_TEXT = "LINE %D1$08$/1 HOME %D1$09$/1"

# Entry gate from the climb summit: only after Marta's checkpoint (climb var 0).
CLIMB_SUMMIT_EXIT = (17, 3, 1, 3)   # climb-scene trigger (x, y, w, h), right end of summit
CLIMB_EXIT_GATE_VAR = "0"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots in the ridge scene: 0 worker, 1 Tomás, 2 grid sprites (cable end,
# junction box, concentrator), 4 debris, 5 gust - matching the climb's layout.
TOMAS_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
# Hardware colours, index 0 transparent placeholder: warm cardigan, skin, dark.
TOMAS_SPRITE_HARDWARE = ["000000", "E8C39E", "4F7A5B", "1E2A2E"]
# BG slot 3 is the window family (opening palette "window" / "powered_window").
WINDOW_BG_SLOT = 3

TOMAS_STATES = ["Waiting", "Relieved"]
CONCENTRATOR_STATES = ["Off", "On"]

_RIDGE_NAMESPACE = _uuid.UUID("9c4d1a2e-7b3f-5e60-8a1d-2f3e4c5b6a70")


def resource_id(key: str) -> str:
    """Stable IDs for every resource this job generates."""
    return str(_uuid.uuid5(_RIDGE_NAMESPACE, "mr-cfe:ridge:" + key))


SCENE_ID = resource_id("scene:wind-ridge")
BACKGROUND_ID = resource_id("background:wind-ridge")
TOMAS_SPRITE_ID = resource_id("sprite:tomas")
CONCENTRATOR_SPRITE_ID = resource_id("sprite:oxygen_concentrator")


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


def _hazard_cells() -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for row, x0, x1 in GUST_LANES:
        cells.update((row, x) for x in range(x0, x1 + 1))
    for debris in HAZARD_DEBRIS:
        cells.update((row, debris["x"])
                     for row in range(debris["row_top"], debris["row_bottom"] + 1))
    return cells


def _stands(grid: list[list[int]], x: int, y: int) -> bool:
    """A 24px actor at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (COL_TOP, COL_SOLID))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    for x, y in (START, DAMAGED_POLE, JUNCTION_BOX, TOMAS, CONCENTRATOR, HOUSE_DOOR):
        assert 0 < x < MAP_W - 1 and HUD_ROWS + 2 <= y < MAP_H - 1, f"bounds {(x, y)}"
        assert _stands(grid, x, y), f"actor tile {(x, y)} must stand clear on support"
    hazards = _hazard_cells()
    assert all(r >= HUD_ROWS for r, _ in hazards), "hazards under the HUD"
    for x, y in (START, DAMAGED_POLE, JUNCTION_BOX, TOMAS, CONCENTRATOR, HOUSE_DOOR):
        assert all(abs(x - hx) > 1 or abs(y - hy) > 2 for hy, hx in hazards), (
            f"prop {(x, y)} too close to a hazard"
        )
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "gust in rock"
        assert all(grid[GROUND_ROW][x] == COL_SOLID for x in range(x0, x1 + 1)), (
            "gust lanes cross walkable floor"
        )
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(set(GUST_START_DELAYS)) == len(GUST_START_DELAYS), "gusts must not fire together"
    # Lanes are separated by walkable floor so the hero can wait between them.
    for (_, _, a1), (_, b0, _) in zip(GUST_LANES, GUST_LANES[1:]):
        assert b0 - a1 >= 3, "need a standing gap between gust lanes"
    for debris in HAZARD_DEBRIS:
        x = debris["x"]
        assert all(grid[r][x] == COL_EMPTY
                   for r in range(debris["row_top"], debris["row_bottom"] + 1)), "debris in rock"
        assert grid[debris["row_bottom"] + 1][x] == COL_SOLID, "debris lands on the floor"
    # Rock steps are one tap high (three tiles) from the floor.
    for x0, x1, row0, row1 in SOLID_BLOCKS[2:]:
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "steps are 3 tiles high"
    # Landing zone off the plateau stays hazard-free.
    plateau_end = SOLID_BLOCKS[2][1]
    assert all((r, x) not in hazards for r in range(GROUND_ROW - 3, GROUND_ROW)
               for x in range(plateau_end + 1, plateau_end + 4)), "plateau landing in a hazard"
    # Any ledge ends before the junction box and is one jump above the floor.
    for row, x0, x1 in LEDGES:
        assert x1 < JUNCTION_BOX[0] - 2, "high route must end before the box"
        assert GROUND_ROW - row == 3, "ledges must be one jump above the floor"
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw, (
        "door trigger covers only the standing hero's top row at the door"
    )
    assert not {(ty, x) for x in range(tx, tx + tw)} & hazards, "door trigger in a hazard"
    xs = [p[0] for p in CABLE_ROUTE]
    assert xs[0] == DAMAGED_POLE[0] and JUNCTION_BOX[0] in xs and HOUSE_RECT[0] in xs
    assert all(HUD_ROWS <= y < GROUND_ROW and 0 <= x < MAP_W for x, y in CABLE_ROUTE)
    assert START[0] < DAMAGED_POLE[0] < GUST_LANES[0][1] < JUNCTION_BOX[0] < HOUSE_DOOR[0], (
        "route order: start, pole, gusts, box, house"
    )
    ids = {SCENE_ID, BACKGROUND_ID, TOMAS_SPRITE_ID, CONCENTRATOR_SPRITE_ID}
    assert len(ids) == 4, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7"})


_self_check()
