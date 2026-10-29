"""Pine Hollow - deterministic contract for Emil's family's repair job (job 4).

Data only for a 40x18-tile PLATFORM scene reached from Priya's porch once her
house is powered. The job mixes the hazards learned so far: a hidden cable lane
on a long rock mesa (the feeder pole and transformer stand up there), then a
live cable arc on the floor below. Two lines make one grid chain: the feeder
line from the pole on the mesa to the transformer beside it, then the house
line from a second pole on the floor to the porch's junction box.
Repairing both lights the family's window and switches on their electric
stove so dinner can cook (Blackout Grid).

Every generator for this job reads this module: ``make_kiko_art.py`` (art +
collision-aligned background), ``make_kiko_sprites.py`` (Emil and the stove)
and ``make_kiko_scene.py`` (scene, actors, triggers, scripts). The live arc
reuses ``live_arc`` from Priya's job; the transformer reuses Wind Ridge's
sprite.

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row). Collision bytes follow GB Studio PLATFORM semantics:
solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import grid_chain
import hazards as _hazards
import ridge
import rosa

TILE = 8
MAP_W, MAP_H = 40, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player, 12 active.
MAX_SCENE_ACTORS = 20

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
    (7, 18, 9, 14),                 # the mesa (top surface row 9); feeder pole stands on it
    (31, 38, 12, 14),               # the family's porch step (top surface row 12)
]
STEP, MESA, PORCH = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
MESA_ROW = 8                        # feet row on the mesa
PORCH_ROW = 11
LEDGES: list[tuple[int, int, int]] = []

START = (2, 14)            # entry from Priya's porch, facing right
DAMAGED_POLE = (9, 8)      # feeder pole on the mesa: its cable end is picked up here
FEEDER_BOX = (16, 8)       # transformer T1 on the mesa, past the feeder pole and the hidden cable
HOUSE_POLE = (24, 14)      # house pole on the floor, before the arc and the porch
JUNCTION_BOX = (33, 11)    # house junction box on the porch: plug-in point
KIKO = (34, 11)            # Emil waits outside, left of the door
STOVE = (37, 11)           # electric stove with a pot, on the porch: Off -> On
HOUSE_DOOR = (36, 11)
HOUSE_RECT = (35, 38, 5, 11)
HOUSE_WINDOWS = [(35, 8), (38, 8)]
DOOR_TRIGGER = (35, 9, 3, 1)
FEEDER_CHECKPOINT = (14, 8)    # respawn once the feeder line is repaired: on the mesa, past the hidden cable
HOUSE_CHECKPOINT = (31, 11)    # respawn once the house line is repaired: the porch step

# ---------------------------------------------------------------------------
# Hazards
#
# Lanes are (row, x0, x1) inclusive on the walking hero's chest row: row 7 on
# the mesa, row 13 on the floor. Arcs are 2 wide. The mesa's hidden cable
# (hazards.HIDDEN_CABLES["pine_hollow"]) is placed by hazards.py; the falling
# debris column is retired. The mesa gust is retired too: with a 16px hero the
# mesa's chest row only has room for the transformer and the hidden cable.
# ---------------------------------------------------------------------------

GUST_LANES: list[tuple[int, int, int]] = []

# On the floor between the house pole and the porch: the house line's carry path.
ARC_LANES = [(GROUND_ROW - 2, 27, 28)]
ARC_START_DELAYS = [0]
ARC_WARNING_FRAMES = rosa.ARC_WARNING_FRAMES
ARC_ACTIVE_FRAMES = rosa.ARC_ACTIVE_FRAMES
ARC_REST_FRAMES = rosa.ARC_REST_FRAMES
ARC_SPRITE_ID = rosa.ARC_SPRITE_ID

# ---------------------------------------------------------------------------
# Variables
#
# 6 is shared with the climb: it holds the number of the line whose cable Emil
# carries (0 = none). 12 and 13 keep their meaning: 12 is the house line live
# (line 2), 13 is Emil's home powered. 24-26 are this job's chain variables;
# 21-23 are reserved for Signal Hill.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "12"       # house line (line 2)
VAR_HOME_POWERED = "13"    # Emil's checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "24"     # feeder line (line 1)
VAR_LINES_LIVE = "25"      # HUD count, 0-2
VAR_CHAIN_LIVE = "26"      # how many leading lines are repaired: how far power reaches (0-2)
VARIABLES = [
    (VAR_LINE_LIVE, "Hollow Line Live", "var_hollow_line_live"),
    (VAR_HOME_POWERED, "Kiko Home Powered", "var_kiko_home_powered"),
    (VAR_FEEDER_LIVE, "Hollow Feeder Live", "var_hollow_feeder_live"),
    (VAR_LINES_LIVE, "Hollow Lines Live", "var_hollow_lines_live"),
    (VAR_CHAIN_LIVE, "Hollow Chain Live", "var_hollow_chain_live"),
]
LINE_COUNT = 2
HUD_TEXT = f"LINES %D1${VAR_LINES_LIVE}$/{LINE_COUNT} HOME %D1$13$/1"

# The grid chain, upstream first (grid_chain.GridChain).
LINES = [
    {"key": "feeder", "pole": DAMAGED_POLE, "box": FEEDER_BOX, "box_kind": "transformer",
     "checkpoint": FEEDER_CHECKPOINT, "live_var": VAR_FEEDER_LIVE},
    {"key": "house", "pole": HOUSE_POLE, "box": JUNCTION_BOX, "box_kind": "junction",
     "checkpoint": HOUSE_CHECKPOINT, "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it

# Entry from Signal Hill: the right end of Priya's porch, past her door, gated on
# her checkpoint (var 11). Text-only refusal, never a nudge (see rosa.py).
HILL_EXIT = (38, 9, 1, 3)
HILL_EXIT_GATE_VAR = rosa.VAR_HOME_POWERED     # "11"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots: 0 worker, 1 Emil, 2 grid sprites (cable ends, boxes, transformer,
# stove), 3 live arc, 4 unused (the retired debris slot), 5 unused (the retired gust).
KIKO_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = rosa.ARC_SPRITE_PALETTE_SLOT
# Hardware colours, index 0 transparent: skin, mustard-yellow jacket, dark.
KIKO_SPRITE_HARDWARE = ["000000", "D9A97E", "E0A82E", "2B2420"]
ARC_SPRITE_HARDWARE = rosa.ARC_SPRITE_HARDWARE
WINDOW_BG_SLOT = 3

KIKO_STATES = ["Waiting", "Relieved"]
STOVE_STATES = ["Off", "On"]

# ---------------------------------------------------------------------------
# Wires (background art), drawn in BG slot LINE_BG_SLOT (metal) only. Two
# colour indices, one per chain stage, so two palettes light the chain as far
# as it is continuous. The metal slot holds nothing but wire: posts use the
# stone slot.
#
#   stage 1 (index 1): live once the feeder line is repaired - edge -> feeder
#                      pole, feeder line (pole -> T1), T1 -> house pole
#   stage 2 (index 3): live once the house line is repaired - house line (pole
#                      -> junction box) and the junction -> house
#
# Routes are polylines of tile cells; a pole's or box's top is (x, y - 3).
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3]        # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0], cell[1] - 3)


_F, _H = (line["pole"] for line in LINES)
_T1, _J = (line["box"] for line in LINES)
OVERHEAD = 4                      # sky row above the pine tops
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD), (_F[0], OVERHEAD), _top(_F)]),                        # edge -> feeder pole
    (1, [_top(_F), (_F[0], OVERHEAD), (_T1[0], OVERHEAD), _top(_T1)]),        # feeder line
    (1, [(_T1[0], OVERHEAD), (_H[0], OVERHEAD), _top(_H)]),                   # T1 -> house pole
    # The house line leaves the pole one column over, so it never shares a
    # pixel column with the stage-1 wire that arrives at the pole's top.
    (2, [_top(_H), (_H[0] + 1, _top(_H)[1]), (_H[0] + 1, OVERHEAD),
         (_J[0], OVERHEAD), (_J[0], _J[1] - 1)]),                             # house line
    (2, [(_J[0], OVERHEAD), (HOUSE_RECT[0], OVERHEAD)]),                      # junction -> house
]
STAGE_COUNT = len(STAGE_COLOR_INDEX)
# {stages_live: metal colours} for the background wire slot (grid_chain.chain_palette).
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# Chain dialogue (grid_chain.GridChain text keys); the scene validates the lengths.
CHAIN_TEXT = {
    "pickup": "Got the cable!\nTo the box ahead.",
    "hands_full": "Hands full!\nOne cable a trip.",
    "already": "Line is live.",
    "all_live": "Both lines live!\nGo see Emil.",
    "lit": "Power flows on!\nOne more line.",
    "dark": "Fixed. No power\nfrom upstream.",
    "no_cable": "No cable yet.\nCheck the pole.",
    "wrong_cable": "Wrong cable\nfor this box.",
}

_KIKO_NAMESPACE = _uuid.UUID("d27a4e1c-3b95-5c08-8f6e-1a9c2b7d4e53")


def resource_id(key: str) -> str:
    """Stable IDs for every resource this job generates."""
    return str(_uuid.uuid5(_KIKO_NAMESPACE, "mr-cfe:kiko:" + key))


SCENE_ID = resource_id("scene:pine-hollow")
BACKGROUND_ID = resource_id("background:pine-hollow")
KIKO_SPRITE_ID = resource_id("sprite:kiko")
STOVE_SPRITE_ID = resource_id("sprite:kiko_stove")
# Wind Ridge's transformer sprite (Dead/Live states, grid sprite slot).
TRANSFORMER_SPRITE_ID = ridge.TRANSFORMER_SPRITE_ID


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


def actor_count() -> int:
    """Emil, the stove, two per line (pole, box), arcs and hidden cables."""
    return (2 + 2 * len(LINES) + len(ARC_LANES)
            + len(_hazards.HIDDEN_CABLES["pine_hollow"]))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, KIKO, STOVE, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    hazard_cells = _hazard_cells()
    assert all(r >= HUD_ROWS for r, _ in hazard_cells), "hazards under the HUD"
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
    for row, x0, x1 in ARC_LANES:
        assert x1 - x0 == 1, "arc lanes match the 16px arc sprite"
    # Standing gaps of three tiles between every hazard lane, hidden cables included.
    columns = sorted([(x0, x1) for _, x0, x1 in [*hazard_lanes(), *_hazards.HIDDEN_CABLES["pine_hollow"]]])
    for (_, a1), (b0, _) in zip(columns, columns[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Walking off the mesa lands clear of every floor lane.
    for row, x0, _ in ARC_LANES:
        assert x0 - MESA[1] >= 9, "mesa landing too close to a floor lane"
    assert PORCH[0] - ARC_LANES[-1][2] >= 2, "need a takeoff tile before the porch"
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert KIKO[0] == JUNCTION_BOX[0] + 1 and STOVE[0] > HOUSE_DOOR[0]
    # The chain runs left to right: feeder pole < T1 < house pole < junction < door.
    grid_chain.check_chain_order(LINES)
    assert START[0] < DAMAGED_POLE[0] and JUNCTION_BOX[0] < HOUSE_DOOR[0]
    # Each box's zone: its two columns plus the three tiles before it, on open air the hero walks through.
    for line in LINES:
        rx, ry, rw, rh = grid_chain.reach_rect(line["box"])
        bx, by = line["box"]
        assert rx + rw == bx + 2 and rw == 5, "box zone covers the box's two columns and three tiles before it"
        assert all(0 < x < MAP_W - 1 and HUD_ROWS <= y < GROUND_ROW
                   for x in range(rx, rx + rw) for y in range(ry, ry + rh))
        assert all(grid[y][x] == COL_EMPTY for y in range(ry, ry + rh) for x in range(bx - 1, bx + 2)), \
            "box zone on open air"
        assert grid[by][bx - 1] == COL_EMPTY and grid[by + 1][bx - 1] != COL_EMPTY
    # The feeder transformer stands on the mesa; its reach zone stays clear of the hidden cable.
    assert LINES[0]["box"][1] == MESA_ROW
    frx, _, frw, _ = grid_chain.reach_rect(LINES[0]["box"])
    assert all(x1 < frx or x0 >= frx + frw for _, x0, x1 in _hazards.HIDDEN_CABLES["pine_hollow"]), \
        "feeder reach zone clear of the hidden cable"
    # Wires: every route stays on the map and below the HUD; the chain is continuous.
    grid_chain.check_wire_routes(WIRE_ROUTES, STAGE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    assert len({tuple(c) for c in CHAIN_PALETTES.values()}) == STAGE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, KIKO_SPRITE_ID, STOVE_SPRITE_ID}
    assert len(ids) == 4, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({str(n) for n in range(12)})
    assert {line["live_var"] for line in LINES} == {VAR_FEEDER_LIVE, VAR_LINE_LIVE}
    # Entry from Signal Hill: right end of Priya's porch, clear of her door trigger.
    ex, ey, ew, eh = HILL_EXIT
    rtx, rty, rtw, _ = rosa.DOOR_TRIGGER
    assert ex >= rtx + rtw and ey + eh - 1 == rosa.PORCH_ROW and ex < rosa.MAP_W - 1


_self_check()
