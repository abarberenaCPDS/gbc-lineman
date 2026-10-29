"""Signal Hill - deterministic contract for Priya's repair job (job 3).

Data only for a 100x18-tile PLATFORM scene reached from Hiroshi's porch once his
house is powered. Five lines in one grid chain must be repaired before Priya's
router comes back on (Blackout Grid: she can work and study online again):

    edge -> feeder -> west -> middle -> east -> house box

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
MAP_W, MAP_H = 100, 18

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
# and reset by every scene init; here it holds which line's cable (1-5).
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "10"       # line 5, the house line (unchanged meaning)
VAR_HOME_POWERED = "11"    # Priya checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "21"     # line 1
VAR_LINES_LIVE = "22"      # HUD count of repaired lines, 0-5
VAR_CHAIN_LIVE = "23"      # how many leading lines are repaired: how far power reaches (0-5)
VAR_WEST_LIVE = "30"       # line 2
VAR_MIDDLE_LIVE = "31"     # line 3
VAR_EAST_LIVE = "32"       # line 4
VARIABLES = [
    (VAR_LINE_LIVE, "Hill Line Live", "var_hill_line_live"),
    (VAR_HOME_POWERED, "Rosa Home Powered", "var_rosa_home_powered"),
    (VAR_FEEDER_LIVE, "Hill Feeder Live", "var_hill_feeder_live"),
    (VAR_LINES_LIVE, "Hill Lines Live", "var_hill_lines_live"),
    (VAR_CHAIN_LIVE, "Hill Chain Live", "var_hill_chain_live"),
    (VAR_WEST_LIVE, "Hill West Live", "var_hill_west_live"),
    (VAR_MIDDLE_LIVE, "Hill Middle Live", "var_hill_middle_live"),
    (VAR_EAST_LIVE, "Hill East Live", "var_hill_east_live"),
]
HUD_TEXT = f"LINES %D1${VAR_LINES_LIVE}$/5 HOME %D1${VAR_HOME_POWERED}$/1"

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
    (87, 98, 12, 14),               # Priya's porch step (top surface row 12); box 4 tiles clear of her
    (11, 12, 12, 14),               # pole 2's rock (top surface row 12); keeps its sprite off the hero's rows
    (28, 29, 12, 14),               # step up to mesa B
    (30, 38, 9, 14),                # mesa B (top surface row 9): pole 3 and hidden cable
    (51, 52, 12, 14),               # step up to mesa C
    (53, 57, 9, 14),                # mesa C (top surface row 9): T3
    (58, 59, 12, 14),               # rock D (top surface row 12): pole 4
    (67, 68, 12, 14),               # step up to mesa E
    (69, 73, 9, 14),                # mesa E (top surface row 9): T4 and pole 5
]
PORCH_ROW = 11
MESA_ROW = 8
# (row, x0, x1) one-way timber ledges. B-16: the T1 pit (x9-10) is exactly the
# hero's width, so he cannot climb its 3-tile walls; this step on the pit's right
# side splits the way out into a 2-tile tap (pit floor -> ledge) and a 1-tile hop (ledge -> rock).
LEDGES: list[tuple[int, int, int]] = [(13, 10, 10)]

START = (2, 14)            # entry from Hiroshi's porch, facing right
ROSA = (95, 11)            # clear of the box's two columns, left of her door
WORKSTATION = (97, 11)     # computer + router on the porch table: Off -> On
HOUSE_DOOR = (96, 11)      # doorway column of Priya's house (art)
HOUSE_RECT = (95, 98, 5, 11)    # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(95, 8), (98, 8)]
# Door checkpoint trigger: top row of a 24px hero standing on the porch.
DOOR_TRIGGER = (95, 9, 3, 1)

# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is where that cable plugs in; "checkpoint" is the respawn
# once the line is repaired.
LINES = [
    # T1 sits in the two-tile pit between the step and the storm-pole rock, so its
    # reach trigger is the pit itself (the tiles before it are rock).
    {"key": "feeder", "pole": (7, 8), "box": (9, 14), "box_kind": "transformer",
     "checkpoint": (14, 14), "live_var": VAR_FEEDER_LIVE, "reach": (9, 12, 2, 3)},
    {"key": "west", "pole": (12, 11), "box": (26, 14), "box_kind": "transformer",
     "checkpoint": (27, 14), "live_var": VAR_WEST_LIVE},
    {"key": "middle", "pole": (31, 8), "box": (55, 8), "box_kind": "transformer",
     "checkpoint": (56, 8), "live_var": VAR_MIDDLE_LIVE},
    {"key": "east", "pole": (59, 11), "box": (70, 8), "box_kind": "transformer",
     "checkpoint": (71, 8), "live_var": VAR_EAST_LIVE},
    {"key": "house", "pole": (73, 8), "box": (89, 11), "box_kind": "transformer",
     "checkpoint": (88, 11), "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
LINE_COUNT = len(LINES)

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the hero's chest row.
# ---------------------------------------------------------------------------
ARC_LANES = [
    (13, 17, 18),
]
ARC_START_DELAYS = [0]
ARC_WARNING_FRAMES = 48     # sparks: safe, telegraphs the arc
ARC_ACTIVE_FRAMES = 24      # arc: hits (collision group 1)
ARC_REST_FRAMES = 80        # dark wire: safe

# The gust became a whip (Abe: more swinging cut cables; the T1/board/T2 view also
# caps the first room at the 10-OBJ scanline limit).
GUST_LANES: list[tuple[int, int, int]] = []
GUST_START_DELAYS: list[int] = []
# Harder than the climb's 54/20/90 (0.8 s of warning).
GUST_WARNING_FRAMES = 48
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 70
# Span arcs in this job: sparks 0.7 s, arc 0.4 s, 0.9 s dark (ARC_* above stay for the lab).
JOB_ARC_WARNING_FRAMES = 42
JOB_ARC_ACTIVE_FRAMES = 24
JOB_ARC_REST_FRAMES = 54

FALLEN_SPANS: list[dict] = [
    {"columns": (42, 45), "live_after": 2, "arcs": [(13, 43, 44)], "delays": [0]},
    {"columns": (81, 86), "live_after": 4, "arcs": [(13, 83, 84)], "delays": [75]},
]

WHIP_LANES = [(13, 48, 49), (13, 64, 65), (13, 78, 79)]
WHIP_START_DELAYS = [0, 50, 20]
WHIP_SWAY_FRAMES = 38      # sparks and sways, safe: 0.63 s of warning
WHIP_SWING_FRAMES = 22
WHIP_HANG_FRAMES = 56
WHIP_SPRITE_ID = ridge.WHIP_SPRITE_ID
WHIP_PALETTE_ID = ridge.WHIP_PALETTE_ID
WHIP_SPRITE_PALETTE_SLOT = ridge.WHIP_SPRITE_PALETTE_SLOT

# ---------------------------------------------------------------------------
# Wires (background art). Slots 5 (stages 1-3) and 6 (stages 4-5) hold wire pixels.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]        # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0], cell[1] - 3)


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _BOX = (line["box"] for line in LINES)
OVERHEAD = 4                      # stage 1 runs above the feeder pole, and the house wire above the porch
POLE_ROW = _top(_P2)[1]           # row 8
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD), (_P1[0], OVERHEAD), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], OVERHEAD), (_T1[0], OVERHEAD), _top(_T1)]),
    (1, [_top(_T1), (_T1[0], POLE_ROW), _top(_P2)]),
    (2, [_top(_P2), (_T2[0], POLE_ROW), _top(_T2)]),
    (2, [_top(_T2), (_T2[0], OVERHEAD), (_P3[0], OVERHEAD), _top(_P3)]),
    (3, [_top(_P3), (_P3[0], OVERHEAD), (_T3[0], OVERHEAD), _top(_T3)]),
    (3, [_top(_T3), (_T3[0], POLE_ROW), _top(_P4)]),
    (4, [_top(_P4), (_P4[0], 3), (_T4[0], 3), _top(_T4)]),
    (4, [_top(_T4), (_T4[0], 3), (_P5[0], 3), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, OVERHEAD),
         (_BOX[0], OVERHEAD), (_BOX[0], _top(_BOX)[1]),
         (_BOX[0], OVERHEAD), (HOUSE_RECT[0], OVERHEAD)]),
]
SPAN_STAGE = [span["live_after"] for span in FALLEN_SPANS]
# {stages_live: {slot: metal colours}} for the background wire slots.
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
    """All floor/placard lanes, left to right."""
    return sorted([*ARC_LANES, *GUST_LANES, *span_arc_lanes(), *WHIP_LANES], key=lambda lane: lane[1])


def _all_hazard_lanes() -> list[tuple[int, int, int]]:
    import hazards
    return sorted([*hazard_lanes(), *hazards.HIDDEN_CABLES["signal_hill"]],
                  key=lambda lane: (lane[0], lane[1]))


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Priya, her workstation, two per line (pole, box), hazards, hidden cables, boards."""
    import hazards
    return (2 + 2 * LINE_COUNT + len(ARC_LANES) + len(GUST_LANES) + len(span_arc_lanes())
            + len(WHIP_LANES) + len(hazards.HIDDEN_CABLES["signal_hill"])
            + len(hazards.BOARDS["signal_hill"]))


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
    for row, x0, x1 in (*ARC_LANES, *span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes match the 16px width"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between lanes"
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Rock steps are one tap (three tiles) above whatever they stand on.
    lower, upper, porch = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
    assert GROUND_ROW - lower[2] == 3 and lower[3] == GROUND_ROW - 1
    assert lower[2] - upper[2] == 3 and upper[3] == lower[2] - 1
    assert lower[0] < upper[0] and upper[1] <= lower[1], "upper step sits on the lower"
    assert GROUND_ROW - porch[2] == 3 and porch[2] - 1 == PORCH_ROW
    # Walking off the upper step lands clear of every lane.
    assert all(x0 - upper[1] >= 9 for _, x0, _ in lanes), "step landing too close to a lane"
    pole_rock = SOLID_BLOCKS[5]
    assert GROUND_ROW - pole_rock[2] == 3 and pole_rock[3] == GROUND_ROW - 1, "one tap high"
    for block in (pole_rock, SOLID_BLOCKS[7], SOLID_BLOCKS[9], SOLID_BLOCKS[10], SOLID_BLOCKS[12]):
        assert all(x0 - block[1] >= 5 for _, x0, _ in lanes if x0 > block[1]), "rock landing"
    # The last lane leaves a tile to hop from onto the porch.
    assert porch[0] - lanes[-1][2] >= 2, "need a takeoff tile before the porch"
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
    assert lanes[0][1] < LINES[-1]["box"][0] < HOUSE_DOOR[0]
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert ROSA[0] - (_BOX[0] + 2) == 4 and WORKSTATION[0] > HOUSE_DOOR[0]
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    # Wires: every route stays on the map below the HUD; the chain is continuous.
    grid_chain.check_wire_routes(WIRE_ROUTES, LINE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == LINE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, ROSA_SPRITE_ID, WORKSTATION_SPRITE_ID, ARC_SPRITE_ID}
    assert len(ids) == 5, "resource ids collide"
    owned = {v for v, _, _ in VARIABLES}
    assert owned == {
        VAR_LINE_LIVE, VAR_HOME_POWERED, VAR_FEEDER_LIVE, VAR_LINES_LIVE, VAR_CHAIN_LIVE,
        VAR_WEST_LIVE, VAR_MIDDLE_LIVE, VAR_EAST_LIVE,
    }
    assert owned.isdisjoint({"0", "4", "5", "6", "7", "8", "9", "24", "25", "26"}), "reserved variables"
    assert {line["live_var"] for line in LINES} <= owned
    assert VAR_CARRYING_CABLE not in owned


_self_check()
