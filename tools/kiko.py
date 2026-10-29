"""Pine Hollow - deterministic contract for Emil's family's repair job (job 4).

Data only for a 100x18-tile PLATFORM scene reached from Priya's porch once her
house is powered. The job mixes the hazards learned so far: a hidden cable lane
on a long rock mesa (the feeder pole and transformer stand up there), then a
live cable arcs, wind, whipping wire and a cracked board along the route.
Five lines make one grid chain, from the feeder on the mesa through three
intermediate transformers to the porch's junction box.
Repairing all five lights the family's window and switches on their electric
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
MAP_W, MAP_H = 100, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player, 12 active.
MAX_SCENE_ACTORS = 20
MAX_ACTIVE_ACTORS = 11

# ---------------------------------------------------------------------------
# Terrain, left to right
# ---------------------------------------------------------------------------
GROUND_ROW = 15
SOLID_BLOCKS = [
    (0, 0, 2, 14),                  # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (5, 6, 12, 14),                 # step up to the mesa (top surface row 12)
    (7, 18, 9, 14),                 # the mesa (top surface row 9); feeder pole stands on it
    (87, 98, 12, 14),               # the family's porch step (top surface row 12); box 4 tiles clear of Emil
    (21, 23, 12, 14),               # rock 2 (top surface row 12): pole 2
    (38, 39, 12, 14),               # step up to mesa B
    (40, 44, 9, 14),                # mesa B (top surface row 9): pole 3
    (54, 55, 12, 14),               # step up to mesa C
    (56, 59, 9, 14),                # mesa C (top surface row 9): T3
    (60, 61, 12, 14),               # rock D (top surface row 12): pole 4
    (67, 68, 12, 14),               # step up to mesa E
    (69, 74, 9, 14),                # mesa E (top surface row 9): T4 and pole 5
]
STEP, MESA, PORCH = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
MESA_ROW = 8                        # feet row on the mesa
PORCH_ROW = 11
LEDGES: list[tuple[int, int, int]] = [(9, 45, 48)]

START = (2, 14)            # entry from Priya's porch, facing right
DAMAGED_POLE = (9, 8)      # feeder pole on the mesa: its cable end is picked up here
FEEDER_BOX = (16, 8)       # transformer T1 on the mesa, past the feeder pole and the hidden cable
HOUSE_POLE = (74, 8)       # house pole on mesa E, before the whip/span and the porch
JUNCTION_BOX = (89, 11)    # house box on the porch, a transformer like the rest: plug-in point (4 tiles from Emil)
KIKO = (95, 11)            # clear of the box's two columns, left of the door
STOVE = (97, 11)           # electric stove with a pot, on the porch: Off -> On
HOUSE_DOOR = (96, 11)
HOUSE_RECT = (95, 98, 5, 11)
HOUSE_WINDOWS = [(95, 8), (98, 8)]
DOOR_TRIGGER = (95, 9, 3, 1)
FEEDER_CHECKPOINT = (14, 8)    # respawn once the feeder line is repaired: on the mesa, past the hidden cable
HOUSE_CHECKPOINT = (88, 11)    # respawn once the house line is repaired: the porch step

# ---------------------------------------------------------------------------
# Hazards
# ---------------------------------------------------------------------------
GUST_LANES: list[tuple[int, int, int]] = [(13, 64, 66)]
GUST_START_DELAYS = [20]
# Pine Hollow is the hardest job: shortest rests, still 0.7 s of warning.
GUST_WARNING_FRAMES = 44
GUST_ACTIVE_FRAMES = 24
GUST_REST_FRAMES = 58

# Free-standing arcs became whips (more swinging cut cables); only span arcs remain.
ARC_LANES: list[tuple[int, int, int]] = []
ARC_START_DELAYS: list[int] = []
ARC_WARNING_FRAMES = 36     # span arcs: sparks 0.6 s
ARC_ACTIVE_FRAMES = 26
ARC_REST_FRAMES = 48
ARC_SPRITE_ID = rosa.ARC_SPRITE_ID

FALLEN_SPANS: list[dict] = [
    {"columns": (45, 48), "live_after": 2, "arcs": [(13, 46, 47)], "delays": [0]},
    {"columns": (81, 86), "live_after": 4, "arcs": [(13, 83, 84)], "delays": [60]},
]

WHIP_LANES = [(13, 28, 29), (13, 51, 52), (13, 78, 79)]
WHIP_START_DELAYS = [0, 45, 15]
WHIP_SWAY_FRAMES = 36      # sparks and sways, safe: 0.6 s of warning
WHIP_SWING_FRAMES = 24
WHIP_HANG_FRAMES = 46
WHIP_SPRITE_ID = ridge.WHIP_SPRITE_ID
WHIP_PALETTE_ID = ridge.WHIP_PALETTE_ID
WHIP_SPRITE_PALETTE_SLOT = ridge.WHIP_SPRITE_PALETTE_SLOT

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "12"       # house line (line 5)
VAR_HOME_POWERED = "13"    # Emil's checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "24"     # feeder line (line 1)
VAR_LINES_LIVE = "25"      # HUD count, 0-5
VAR_CHAIN_LIVE = "26"      # how many leading lines are repaired: how far power reaches (0-5)
VAR_WEST_LIVE = "33"       # line 2
VAR_MIDDLE_LIVE = "34"     # line 3
VAR_EAST_LIVE = "35"       # line 4
VARIABLES = [
    (VAR_LINE_LIVE, "Hollow Line Live", "var_hollow_line_live"),
    (VAR_HOME_POWERED, "Kiko Home Powered", "var_kiko_home_powered"),
    (VAR_FEEDER_LIVE, "Hollow Feeder Live", "var_hollow_feeder_live"),
    (VAR_LINES_LIVE, "Hollow Lines Live", "var_hollow_lines_live"),
    (VAR_CHAIN_LIVE, "Hollow Chain Live", "var_hollow_chain_live"),
    (VAR_WEST_LIVE, "Hollow West Live", "var_hollow_west_live"),
    (VAR_MIDDLE_LIVE, "Hollow Middle Live", "var_hollow_middle_live"),
    (VAR_EAST_LIVE, "Hollow East Live", "var_hollow_east_live"),
]
LINE_COUNT = 5
HUD_TEXT = f"LINES %D1${VAR_LINES_LIVE}$/{LINE_COUNT} HOME %D1$13$/1"

# The grid chain, upstream first (grid_chain.GridChain).
LINES = [
    {"key": "feeder", "pole": DAMAGED_POLE, "box": FEEDER_BOX, "box_kind": "transformer",
     "checkpoint": FEEDER_CHECKPOINT, "live_var": VAR_FEEDER_LIVE},
    {"key": "west", "pole": (22, 11), "box": (35, 14), "box_kind": "transformer",
     "checkpoint": (36, 14), "live_var": VAR_WEST_LIVE},
    {"key": "middle", "pole": (41, 8), "box": (57, 8), "box_kind": "transformer",
     "checkpoint": (58, 8), "live_var": VAR_MIDDLE_LIVE},
    {"key": "east", "pole": (61, 11), "box": (70, 8), "box_kind": "transformer",
     "checkpoint": (71, 8), "live_var": VAR_EAST_LIVE},
    {"key": "house", "pole": HOUSE_POLE, "box": JUNCTION_BOX, "box_kind": "transformer",
     "checkpoint": HOUSE_CHECKPOINT, "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it

# Entry from Signal Hill: the right end of Priya's porch, past her door, gated on
# her checkpoint (var 11). Text-only refusal, never a nudge (see rosa.py).
HILL_EXIT = (rosa.MAP_W - 2, 9, 1, 3)
HILL_EXIT_GATE_VAR = rosa.VAR_HOME_POWERED     # "11"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
KIKO_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = rosa.ARC_SPRITE_PALETTE_SLOT
GUST_SPRITE_PALETTE_SLOT = rosa.GUST_SPRITE_PALETTE_SLOT
# Hardware colours, index 0 transparent: skin, mustard-yellow jacket, dark.
KIKO_SPRITE_HARDWARE = ["000000", "D9A97E", "E0A82E", "2B2420"]
ARC_SPRITE_HARDWARE = rosa.ARC_SPRITE_HARDWARE
WINDOW_BG_SLOT = 3

KIKO_STATES = ["Waiting", "Relieved"]
STOVE_STATES = ["Off", "On"]

# ---------------------------------------------------------------------------
# Wires (background art), drawn in BG slots LINE_BG_SLOT (5) and LINE_BG_SLOT_2 (6).
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]        # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0], cell[1] - 3)


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _J = (line["box"] for line in LINES)
OVERHEAD = 4                      # sky row above the pine tops
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD), (_P1[0], OVERHEAD), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], OVERHEAD), (_T1[0], OVERHEAD), _top(_T1)]),
    (1, [_top(_T1), (_T1[0], 8), _top(_P2)]),
    (2, [_top(_P2), (_T2[0], 8), _top(_T2)]),
    (2, [_top(_T2), (_T2[0], OVERHEAD), (_P3[0], OVERHEAD), _top(_P3)]),
    (3, [_top(_P3), (_P3[0], OVERHEAD), (_T3[0], OVERHEAD), _top(_T3)]),
    (3, [_top(_T3), (_T3[0], 8), _top(_P4)]),
    (4, [_top(_P4), (_P4[0], 3), (_T4[0], 3), _top(_T4)]),
    (4, [_top(_T4), (_T4[0], 3), (_P5[0], 3), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, OVERHEAD),
         (_J[0], OVERHEAD), (_J[0], _top(_J)[1])]),
    (5, [(_J[0], OVERHEAD), (HOUSE_RECT[0], OVERHEAD)]),
]
SPAN_STAGE = [span["live_after"] for span in FALLEN_SPANS]
STAGE_COUNT = len(STAGE_COLOR_INDEX)
# {stages_live: {slot: metal colours}} for the background wire slots.
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# Chain dialogue (grid_chain.GridChain text keys); the scene validates the lengths.
CHAIN_TEXT = {
    "pickup": "Got the cable!\nTo the box ahead.",
    "hands_full": "Hands full!\nOne cable a trip.",
    "already": "Line is live.",
    "all_live": "All 5 lines live!\nGo see Emil.",
    "lit": "Power flows on!\nKeep going.",
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


def span_arc_lanes() -> list[tuple[int, int, int]]:
    return [lane for span in FALLEN_SPANS for lane in span["arcs"]]


def hazard_lanes() -> list[tuple[int, int, int]]:
    """All floor/placard lanes, left to right."""
    return sorted([*GUST_LANES, *ARC_LANES, *span_arc_lanes(), *WHIP_LANES], key=lambda lane: lane[1])


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in [*hazard_lanes(), *_hazards.HIDDEN_CABLES["pine_hollow"]]
            for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Emil, the stove, two per line (pole, box), hazards, hidden cables, boards."""
    return (2 + 2 * len(LINES) + len(ARC_LANES) + len(GUST_LANES) + len(span_arc_lanes())
            + len(WHIP_LANES) + len(_hazards.HIDDEN_CABLES["pine_hollow"])
            + len(_hazards.BOARDS["pine_hollow"]))


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
    for row, x0, x1 in (*ARC_LANES, *span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes match the 16px width"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    # Standing gaps of three tiles between every hazard lane, hidden cables included.
    columns = sorted([(x0, x1) for _, x0, x1 in [*hazard_lanes(), *_hazards.HIDDEN_CABLES["pine_hollow"]]])
    for (_, a1), (b0, _) in zip(columns, columns[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Walking off the mesa lands clear of every floor lane.
    for row, x0, _ in hazard_lanes():
        assert x0 - MESA[1] >= 9, "mesa landing too close to a floor lane"
    assert PORCH[0] - hazard_lanes()[-1][2] >= 2, "need a takeoff tile before the porch"
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert KIKO[0] - (JUNCTION_BOX[0] + 2) == 4 and STOVE[0] > HOUSE_DOOR[0]
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
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == STAGE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, KIKO_SPRITE_ID, STOVE_SPRITE_ID}
    assert len(ids) == 4, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({str(n) for n in range(12)})
    assert {line["live_var"] for line in LINES} == {
        VAR_FEEDER_LIVE, VAR_WEST_LIVE, VAR_MIDDLE_LIVE, VAR_EAST_LIVE, VAR_LINE_LIVE
    }
    # Entry from Signal Hill: right end of Priya's porch, clear of her door trigger.
    ex, ey, ew, eh = HILL_EXIT
    rtx, rty, rtw, _ = rosa.DOOR_TRIGGER
    assert ex >= rtx + rtw and ey + eh - 1 == rosa.PORCH_ROW and ex < rosa.MAP_W - 1


_self_check()
