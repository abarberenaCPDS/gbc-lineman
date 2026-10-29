"""Signal Hill - deterministic contract for Priya's repair job (job 3).

Data only for a 40x18-tile PLATFORM scene reached from Hiroshi's porch once his
house is powered. Two lines in one grid chain must be repaired before Priya's
router comes back on (Blackout Grid: she can work and study online again):

    edge -> feeder pole -[line 1]-> transformer T1 -> storm pole -[line 2]-> porch box

Live cable arcs are the featured hazard: a downed wire sparks as a warning, then
arcs (hits) and rests, like a gust lane. One wind gust sits between the arcs.

Every generator for this job reads this module: ``make_rosa_art.py`` (art +
collision-aligned background), ``make_rosa_sprites.py`` (Priya, her
workstation and the live arc) and ``make_rosa_scene.py`` (scene, actors,
triggers, scripts). The grid chain itself is ``grid_chain.py``; this file
supplies only Signal Hill's geometry, IDs, variables and palettes.

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching ridge.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import grid_chain
import ridge

TILE = 8
MAP_W, MAP_H = 40, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player, 12 active.
MAX_SCENE_ACTORS = 20
MAX_ACTIVE_ACTORS = 11

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared with the climb
# and reset by every scene init; here it holds which line's cable (1-2).
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "10"       # line 2, the house line (unchanged meaning)
VAR_HOME_POWERED = "11"    # Priya checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "21"     # line 1
VAR_LINES_LIVE = "22"      # HUD count of repaired lines, 0-2
VAR_CHAIN_LIVE = "23"      # how many leading lines are repaired: how far power reaches (0-2)
VARIABLES = [
    (VAR_LINE_LIVE, "Hill Line Live", "var_hill_line_live"),
    (VAR_HOME_POWERED, "Rosa Home Powered", "var_rosa_home_powered"),
    (VAR_FEEDER_LIVE, "Hill Feeder Live", "var_hill_feeder_live"),
    (VAR_LINES_LIVE, "Hill Lines Live", "var_hill_lines_live"),
    (VAR_CHAIN_LIVE, "Hill Chain Live", "var_hill_chain_live"),
]
HUD_TEXT = f"LINES %D1${VAR_LINES_LIVE}$/2 HOME %D1${VAR_HOME_POWERED}$/1"

# ---------------------------------------------------------------------------
# Terrain, left to right
#
# The floor is solid from GROUND_ROW down; the 24px hero stands in rows 12-14.
# A two-step rock holds the feeder pole on its upper step. Priya's porch repeats
# the Wind Ridge lesson: props stand on row 11, above every hazard row, so the
# 10-sprites-per-scanline limit holds.
# ---------------------------------------------------------------------------
GROUND_ROW = 15
# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, 14),                  # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (4, 8, 12, 14),                 # lower rock step (top surface row 12)
    (6, 8, 9, 11),                  # upper rock step (top surface row 9); feeder pole stands on it
    (32, 38, 12, 14),               # Priya's porch step (top surface row 12)
    (11, 12, 12, 14),               # storm pole's rock (top surface row 12); keeps its sprite off the hero's rows
]
PORCH_ROW = 11
# (row, x0, x1) one-way timber ledges. B-16: the T1 pit (x9-10) is exactly the
# hero's width, so he cannot climb its 3-tile walls; this step on the pit's right
# side splits the way out into a 2-tile tap (pit floor -> ledge) and a 1-tile hop (ledge -> rock).
LEDGES: list[tuple[int, int, int]] = [(13, 10, 10)]

START = (2, 14)            # entry from Hiroshi's porch, facing right
ROSA = (34, 11)            # Priya waits outside, left of her door
WORKSTATION = (37, 11)     # computer + router on the porch table: Off -> On
HOUSE_DOOR = (36, 11)      # doorway column of Priya's house (art)
HOUSE_RECT = (35, 38, 5, 11)    # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(35, 8), (38, 8)]
# Door checkpoint trigger: top row of a 24px hero standing on the porch.
DOOR_TRIGGER = (35, 9, 3, 1)

#
# The house line's storm pole (the original job's) moved off the upper step to
# the one-tap rock at x 11-12, so transformer T1 (x 9-10) sits between the poles.
# The rock keeps the pole's sprite (rows 8-11) off the hero's rows at the start
# view, where the scanline budget would otherwise be exceeded.
#
# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is where that cable plugs in; "checkpoint" is the respawn
# once the line is repaired.
LINES = [
    # T1 sits in the two-tile pit between the step and the storm-pole rock, so its
    # reach trigger is the pit itself (the tiles before it are rock).
    {"key": "feeder", "pole": (7, 8), "box": (9, 14), "box_kind": "transformer",
     "checkpoint": (14, 14), "live_var": VAR_FEEDER_LIVE, "reach": (9, 12, 2, 3)},
    {"key": "house", "pole": (12, 11), "box": (33, 11), "box_kind": "junction",
     "checkpoint": (32, 11), "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
LINE_COUNT = len(LINES)

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the hero's chest row. Arcs are
# two tiles wide (a 16px sprite, two 8x16 OBJs); the gust reuses the 24px
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

# No fallen span: the terrain has no floor stretch that keeps the three-tile
# standing gap on both sides of a two-tile arc, so the chain runs on the lines
# alone (grid_chain.check_spans accepts an empty list).
FALLEN_SPANS: list[dict] = []

# ---------------------------------------------------------------------------
# Wires (background art). The metal BG slot holds wire pixels only: stage k
# (line k repaired) takes colour index STAGE_COLOR_INDEX[k-1], so the scene can
# light the chain as far as it is continuous. Routes are polylines of tile cells;
# a pole's top is (x, y - 3), a transformer's top is (x, y - 3) too.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3]        # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0], cell[1] - 3)


_FEEDER, _HOUSE = LINES
_P1, _T1 = _FEEDER["pole"], _FEEDER["box"]
_P2, _BOX = _HOUSE["pole"], _HOUSE["box"]
OVERHEAD = 4                      # stage 1 runs above the feeder pole, and the house wire above the porch
POLE_ROW = _top(_P2)[1]           # the storm pole's top row: T1 -> pole 2 and line 2 run along it
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD), (_P1[0], OVERHEAD), _top(_P1)]),                         # edge -> feeder pole
    (1, [_top(_P1), (_P1[0], OVERHEAD), (_T1[0], OVERHEAD), _top(_T1)]),         # line 1 -> T1
    (1, [_top(_T1), (_T1[0], POLE_ROW), _top(_P2)]),                             # T1 -> storm pole
    (2, [_top(_P2), (_BOX[0], POLE_ROW), (_BOX[0], _BOX[1] - 1)]),               # line 2 -> house box
    (2, [(_BOX[0], _BOX[1] - 1), (_BOX[0], OVERHEAD), (HOUSE_RECT[0], OVERHEAD)]),  # box -> house
]
# {stages_live: metal colours} for the background wire slot (grid_chain.chain_palette).
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# Hardware colours, index 0 transparent placeholder.
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
TRANSFORMER_SPRITE_ID = ridge.TRANSFORMER_SPRITE_ID    # Wind Ridge's transformer asset, reused

# Entry from Wind Ridge: the right end of Hiroshi's porch, past his door. Gated
# on his checkpoint (ridge var 9). The refusal shows text only; it never
# nudges the hero, because a nudge plus leftover momentum re-enters the
# trigger and loops (exact ROM 147c23be, summit exit).
RIDGE_EXIT = (ridge.MAP_W - 2, ridge.PORCH_ROW - 2, 1, 3)   # right end of Hiroshi's porch
RIDGE_EXIT_GATE_VAR = ridge.VAR_HOME_POWERED   # "9"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots: 0 worker, 1 Priya, 2 grid sprites (cable end, junction box,
# transformer, workstation), 3 live arc, 5 gust - matching the climb/ridge layout.
ROSA_SPRITE_PALETTE_SLOT = 1
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


def span_arc_lanes() -> list[tuple[int, int, int]]:
    return [lane for span in FALLEN_SPANS for lane in span["arcs"]]


def hazard_lanes() -> list[tuple[int, int, int]]:
    """All lanes, left to right."""
    return sorted([*ARC_LANES, *GUST_LANES, *span_arc_lanes()], key=lambda lane: lane[1])


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Priya, her workstation, two per line (pole, box), hazards."""
    return (2 + 2 * LINE_COUNT + len(ARC_LANES) + len(GUST_LANES) + len(span_arc_lanes()))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, ROSA, WORKSTATION, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    lanes = hazard_lanes()
    for row, x0, x1 in lanes:
        assert row == GROUND_ROW - 2, "lanes sit on the walking hero's chest row"
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[GROUND_ROW][x] == COL_SOLID for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in ARC_LANES:
        assert x1 - x0 == 1, "arc lanes match the 16px arc sprite"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
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
    # The storm pole's rock: a one-tap step; the first lane past it is five tiles
    # clear of its edge (the carry-off landing, as on Wind Ridge).
    pole_rock = SOLID_BLOCKS[5]
    assert GROUND_ROW - pole_rock[2] == 3 and pole_rock[3] == GROUND_ROW - 1, "one tap high"
    assert all(x0 - pole_rock[1] >= 5 for _, x0, _ in lanes if x0 > pole_rock[1]), "rock landing"
    # The last lane leaves a tile to hop from onto the porch.
    assert porch[0] - lanes[-1][2] >= 2, "need a takeoff tile before the porch"
    # The chain runs left to right: the feeder pole on the upper step, T1 on the
    # floor, then the storm pole on its rock, then the lanes, then the porch box.
    grid_chain.check_chain_order(LINES)
    # Each box's reach trigger (B-06) lies on open air the hero walks or drops through.
    for line in LINES:
        rx, ry, rw, rh = line.get("reach") or grid_chain.reach_rect(line["box"])
        assert rx <= line["box"][0] <= rx + rw, "reach trigger reaches the box"
        assert all(grid[y][x] in (COL_EMPTY, COL_TOP) for y in range(ry, ry + rh) for x in range(rx, rx + rw)), \
            f"{line['key']} reach trigger in rock"
    # B-16: the pit ledge sits 2 tiles above the pit floor and 1 below the rock top.
    pit_ledge_row, _, _ = LEDGES[0]
    assert GROUND_ROW - pit_ledge_row == 2 and pit_ledge_row - pole_rock[2] == 1, "pit ledge: 2-tile then 1-tile rise"
    assert LINES[0]["pole"] == (upper[1] - 1, upper[2] - 1), "feeder pole stands on the upper step"
    assert LINES[1]["pole"] == (pole_rock[1], pole_rock[2] - 1), "storm pole stands on its rock"
    assert START[0] < LINES[0]["pole"][0] < LINES[0]["box"][0] < LINES[1]["pole"][0] < lanes[0][1]
    assert lanes[0][1] < LINES[1]["box"][0] < HOUSE_DOOR[0]
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert ROSA[0] == _BOX[0] + 1 and WORKSTATION[0] > HOUSE_DOOR[0]
    assert LINES[1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    # Wires: every route stays on the map below the HUD; the chain is continuous.
    grid_chain.check_wire_routes(WIRE_ROUTES, LINE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    assert len({tuple(c) for c in CHAIN_PALETTES.values()}) == LINE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, ROSA_SPRITE_ID, WORKSTATION_SPRITE_ID, ARC_SPRITE_ID}
    assert len(ids) == 5, "resource ids collide"
    owned = {v for v, _, _ in VARIABLES}
    assert owned == {VAR_LINE_LIVE, VAR_HOME_POWERED, VAR_FEEDER_LIVE, VAR_LINES_LIVE, VAR_CHAIN_LIVE}
    assert owned.isdisjoint({"0", "4", "5", "6", "7", "8", "9", "24", "25", "26"}), "reserved variables"
    assert {line["live_var"] for line in LINES} <= owned
    assert VAR_CARRYING_CABLE not in owned


_self_check()
