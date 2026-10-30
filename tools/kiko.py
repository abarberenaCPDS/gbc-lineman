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
import transformer_art

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
# 0.18 redesign (Abe, 0.17 playtest: "Emil's: same as Hiroshi's and Priya's",
# i.e. "reorganize the layout because it's too easy, have all of our obstacles
# there too"). The last and hardest job, modelled on the climb Abe liked: four
# tiers (floor 15, rocks 12, mesas and catwalks 9, the summit rock 6), short-A-tap
# rises of three rows, every carry crosses hazards sitting on the route, and the
# whips and gusts guard the jumps. The boxes are background transformers
# (transformer_art.py), which frees five actors for hazards. Left to right:
#
#   1 feeder  rock A pole 1 -> tap onto catwalk C1: cracked board on the landing,
#             then a hidden cable right before mesa M1, T1
#   2 west    mesa M1 pole 2 -> drop to the floor: fallen span 1 arcs, then whip 1
#             right before the tap onto rock C, T2
#   3 middle  rock C pole 3 -> catwalk D1: gust 1 on the landing, whip 2 guarding
#             the tap onto the summit rock D, T3
#   4 east    summit pole 4 -> drop to catwalk E1 (cracked board on the landing,
#             whip 3) or the floor under it (fallen span 2, two arcs) -> rock E, T4
#   5 house   rock E pole 5 -> catwalk F (cracked board on the landing, hidden
#             cable 2 at the drop onto the porch) or the floor under it (gust 2)
#             -> Emil's porch: house box, Emil, door, stove
# ---------------------------------------------------------------------------
GROUND_ROW = 15
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # one tap up: rocks A, C, E and the porch
SURFACE_HIGH = GROUND_ROW - 6     # mesa M1 and the catwalks
SURFACE_TOP = GROUND_ROW - 9      # summit rock D

# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                    # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1),    # right cliff wall behind the house
    (4, 6, SURFACE_STEP, GROUND_ROW - 1),         # rock A: pole 1 (feeder)
    (16, 23, SURFACE_HIGH, GROUND_ROW - 1),       # mesa M1: T1, pole 2
    (36, 41, SURFACE_STEP, GROUND_ROW - 1),       # rock C: T2, pole 3
    (54, 59, SURFACE_TOP, GROUND_ROW - 1),        # summit rock D: T3, pole 4
    (74, 79, SURFACE_STEP, GROUND_ROW - 1),       # rock E: T4, pole 5
    (88, 98, SURFACE_STEP, GROUND_ROW - 1),       # the family's porch (box 4 tiles clear of Emil)
]
ROCK_A, MESA, ROCK_C, ROCK_D, ROCK_E, PORCH = SOLID_BLOCKS[2:]
# One-way timber catwalks (row, x0, x1), each three rows above where it is reached from.
LEDGES: list[tuple[int, int, int]] = [
    (SURFACE_HIGH, 8, 15),     # C1: rock A -> mesa M1 (board on the landing, hidden cable 1)
    (SURFACE_HIGH, 43, 52),    # D1: rock C -> summit (gust 1 on the landing, whip 2)
    (SURFACE_HIGH, 61, 71),    # E1: summit -> rock E (board on the landing, whip 3; span 2 below)
    (SURFACE_HIGH, 81, 87),    # F: rock E -> porch (board on the landing, hidden cable 2; gust 2 below)
]
C1, D1, E1, F = LEDGES
MESA_ROW = SURFACE_HIGH - 1       # feet row on the mesa and the catwalks
PORCH_ROW = SURFACE_STEP - 1      # porch actors stand on row 11

START = (2, GROUND_ROW - 1)       # entry from Priya's porch, facing right
DAMAGED_POLE = (5, SURFACE_STEP - 1)    # feeder pole on rock A: its cable end is picked up here
FEEDER_BOX = (19, MESA_ROW)             # transformer T1 on mesa M1, past the board and hidden cable 1
HOUSE_POLE = (79, SURFACE_STEP - 1)     # house pole on rock E, before catwalk F and the porch
JUNCTION_BOX = (89, PORCH_ROW)          # house box on the porch: plug-in point (4 tiles from Emil)
KIKO = (95, PORCH_ROW)            # clear of the box's two columns, left of the door
STOVE = (97, PORCH_ROW)           # electric stove with a pot, on the porch: Off -> On
HOUSE_DOOR = (96, PORCH_ROW)
HOUSE_RECT = (95, 98, PORCH_ROW - 6, PORCH_ROW)
HOUSE_WINDOWS = [(95, PORCH_ROW - 3), (98, PORCH_ROW - 3)]
DOOR_TRIGGER = (95, PORCH_ROW - 2, 3, 1)
FEEDER_CHECKPOINT = (21, MESA_ROW)      # respawn once the feeder line is repaired: on M1, past T1
HOUSE_CHECKPOINT = (88, PORCH_ROW)      # respawn once the house line is repaired: the porch step

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the chest row of the surface
# they cross: row 13 on the floor, row 7 on a catwalk. Cracked boards and
# hidden cables are placed by hazards.py (its "pine_hollow" keys).
# ---------------------------------------------------------------------------
CHEST_LOW = SURFACE_LOW - 2
CHEST_HIGH = SURFACE_HIGH - 2

GUST_LANES: list[tuple[int, int, int]] = [(CHEST_HIGH, 44, 46), (CHEST_LOW, 84, 86)]   # D1, floor under F
GUST_START_DELAYS = [20, 0]
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

# Fallen spans: floor columns of the wire lying on the ground, the number of
# upstream lines whose repair makes it live, and its live_arc lanes (two wide).
FALLEN_SPANS: list[dict] = [
    {"columns": (25, 31), "live_after": 1, "arcs": [(CHEST_LOW, 28, 29)], "delays": [0]},
    {"columns": (62, 72), "live_after": 3, "arcs": [(CHEST_LOW, 64, 65), (CHEST_LOW, 69, 70)],
     "delays": [0, 55]},
]

# Whip 1 hangs over the floor before rock C; whips 2 and 3 from crossarms over a
# catwalk. None near the porch: its 32px canvas would join Emil, the house pole and
# a creaking board on one scanline.
WHIP_LANES = [(CHEST_LOW, 33, 34), (CHEST_HIGH, 50, 51), (CHEST_HIGH, 67, 68)]
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

# The grid chain, upstream first (grid_chain.GridChain). "box" is the feet tile
# of the background transformer the cable plugs into (transformer_art.py, 16x24
# on two columns); "checkpoint" is the respawn once the line is repaired.
LINES = [
    {"key": "feeder", "pole": DAMAGED_POLE, "box": FEEDER_BOX, "box_kind": "transformer",
     "checkpoint": FEEDER_CHECKPOINT, "live_var": VAR_FEEDER_LIVE},
    {"key": "west", "pole": (22, MESA_ROW), "box": (38, SURFACE_STEP - 1), "box_kind": "transformer",
     "checkpoint": (40, SURFACE_STEP - 1), "live_var": VAR_WEST_LIVE},
    {"key": "middle", "pole": (41, SURFACE_STEP - 1), "box": (55, SURFACE_TOP - 1), "box_kind": "transformer",
     "checkpoint": (57, SURFACE_TOP - 1), "live_var": VAR_MIDDLE_LIVE},
    {"key": "east", "pole": (58, SURFACE_TOP - 1), "box": (76, SURFACE_STEP - 1), "box_kind": "transformer",
     "checkpoint": (78, SURFACE_STEP - 1), "live_var": VAR_EAST_LIVE},
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
    """A pole's top tile (its 32px canvas)."""
    return (cell[0], cell[1] - 3)


def _box_top(cell: tuple[int, int]) -> tuple[int, int]:
    """A background transformer's hookup tile: the left one of its stage-slot top row."""
    return transformer_art.tiles(cell)[0][0]


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _J = (line["box"] for line in LINES)
# Overhead rows per stage, just under the HUD: above every catwalk, whip bracket
# and transformer; the summit pole's top (row 2) is itself overhead.
OVERHEAD = [3, 2, 3, 2, 3]
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD[0]), (_P1[0], OVERHEAD[0]), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], OVERHEAD[0]), (_T1[0], OVERHEAD[0]), _box_top(_T1)]),
    (1, [_box_top(_T1), (_T1[0], OVERHEAD[0]), (_P2[0], OVERHEAD[0]), _top(_P2)]),
    (2, [_top(_P2), (_P2[0], OVERHEAD[1]), (_T2[0], OVERHEAD[1]), _box_top(_T2)]),
    (2, [_box_top(_T2), (_T2[0], OVERHEAD[1]), (_P3[0], OVERHEAD[1]), _top(_P3)]),
    (3, [_top(_P3), (_P3[0], OVERHEAD[2]), (_T3[0], OVERHEAD[2]), _box_top(_T3)]),
    (3, [_box_top(_T3), (_T3[0], _top(_P4)[1]), _top(_P4)]),
    (4, [_top(_P4), (_T4[0], OVERHEAD[3]), _box_top(_T4)]),
    (4, [_box_top(_T4), (_T4[0], OVERHEAD[3]), (_P5[0], OVERHEAD[3]), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, OVERHEAD[4]),
         (_J[0], OVERHEAD[4]), _box_top(_J),
         (_J[0], OVERHEAD[4]), (HOUSE_RECT[0], OVERHEAD[4])]),
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
# The boxes are Wind Ridge's background transformer (transformer_art.py): no box
# actors, the wire palette lights them. The cans use the stone slot, its four
# colours mapped to the art's codes ('.' stays index 0, the dark behind the can).
BACKGROUND_BOXES = True
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)


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
    """All floor/catwalk lanes with art (gusts, arcs, whips), by row then column."""
    return sorted([*GUST_LANES, *ARC_LANES, *span_arc_lanes(), *WHIP_LANES], key=lambda lane: (lane[0], lane[1]))


def _all_hazard_lanes() -> list[tuple[int, int, int]]:
    return sorted([*hazard_lanes(), *_hazards.HIDDEN_CABLES["pine_hollow"]], key=lambda lane: (lane[0], lane[1]))


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Emil, the stove, one pole per line (the boxes are background art), hazards."""
    return (2 + len(LINES) + len(ARC_LANES) + len(GUST_LANES) + len(span_arc_lanes())
            + len(WHIP_LANES) + len(_hazards.HIDDEN_CABLES["pine_hollow"])
            + len(_hazards.BOARDS["pine_hollow"]))


def surfaces() -> list[tuple[int, int, int]]:
    """Every raised walkable surface (surface row, x0, x1): solid block tops and catwalks."""
    out = [(row0, x0, x1) for x0, x1, row0, _ in SOLID_BLOCKS[2:]]
    return sorted(out + list(LEDGES), key=lambda s: (s[1], s[0]))


def board_cells() -> set[tuple[int, int]]:
    """(row, x) of each cracked board's standing row (its trigger)."""
    return {(row - 1, x) for row, x0, x1 in _hazards.BOARDS["pine_hollow"] for x in range(x0, x1 + 1)}


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, KIKO, STOVE, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    assert not {(y, x) for x, y in props} & board_cells(), "no prop or checkpoint on a cracked board"
    assert all(r >= HUD_ROWS for r, _ in _hazard_cells()), "hazards under the HUD"
    # Lanes sit on the chest row of the surface they cross.
    for row, x0, x1 in _all_hazard_lanes():
        surface = row + 2
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[row + 1][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane feet row in rock"
        assert all(grid[surface][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in (*ARC_LANES, *span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes match the 16px width"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    # Whips hang from a bracket two and three rows above the chest row: open air, below the HUD.
    for row, x0, x1 in WHIP_LANES:
        assert row - 3 >= HUD_ROWS + 1
        assert all(grid[r][x] == COL_EMPTY for r in (row - 3, row - 2) for x in range(x0 - 1, x1 + 2))
    # Three standing tiles between lanes on the same surface (the hero is two tiles wide).
    for row in {lane[0] for lane in _all_hazard_lanes()}:
        lanes = [lane for lane in _all_hazard_lanes() if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
            assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Boards lie on catwalks (their idle plank is background art), clear of every lane.
    for row, x0, x1 in _hazards.BOARDS["pine_hollow"]:
        assert any(lrow == row and lx0 <= x0 and x1 <= lx1 for lrow, lx0, lx1 in LEDGES), "board on a catwalk"
        assert all(grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1))
    assert not board_cells() & {(r + 1, x) for r, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}
    # Jumping or walking off a raised surface carries the hero ~5 tiles (Wind Ridge,
    # exact ROMs): keep lower lanes to its right clear of the landing.
    for srow, _, sx1 in surfaces():
        for row, x0, _ in _all_hazard_lanes():
            if row + 2 > srow and x0 > sx1:
                assert x0 - sx1 >= 5, f"lane at {x0} in the landing off {sx1} (row {srow})"
    # Floor whips stay off screen from the porch (camera clamped at MAP_W - 20):
    # their 32px canvas reaches the porch actors' rows.
    assert all(x1 < MAP_W - 20 for row, _, x1 in WHIP_LANES if row == CHEST_LOW)
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Span k lies on the floor of line k+1's carry, so that carry crosses it.
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    assert all(row == CHEST_LOW for row, _, _ in span_arc_lanes()), "spans lie on the floor"
    # Tiers: every raised surface is one tap (three rows) above the floor or the
    # surface it is reached from; catwalks are never above a block.
    assert {s[0] for s in surfaces()} <= {SURFACE_STEP, SURFACE_HIGH, SURFACE_TOP}
    for x0, x1, row0, row1 in (ROCK_A, ROCK_C, ROCK_E, PORCH):
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "rocks are one tap high"
    for row, x0, x1 in LEDGES:
        assert all(grid[r][x] == COL_EMPTY for r in range(row - 3, row) for x in range(x0, x1 + 1)), \
            "head room over every catwalk"
    assert MESA[0] == C1[2] + 1 and MESA[2] == C1[0], "catwalk C1 runs onto the mesa"
    # Every carry crosses at least one hazard (lane or board) between its pole and box.
    spans = [(x0, x1) for _, x0, x1 in _all_hazard_lanes()]
    spans += [(x0, x1) for _, x0, x1 in _hazards.BOARDS["pine_hollow"]]
    for line in LINES:
        px, bx = line["pole"][0], line["box"][0]
        assert any(px < x0 and x1 < bx for x0, x1 in spans), f"{line['key']} carry crosses no hazard"
    # The chain runs left to right: pole k < box k < pole k+1.
    grid_chain.check_chain_order(LINES)
    assert START[0] < DAMAGED_POLE[0] and JUNCTION_BOX[0] < HOUSE_DOOR[0]
    # Background transformers: open air on their two columns, support under both.
    reserved: set[tuple[int, int]] = set()
    for line in LINES:
        bx, by = line["box"]
        cells = transformer_art.all_tiles(line["box"])
        assert all(grid[ty][tx] == COL_EMPTY and ty >= HUD_ROWS for tx, ty in cells), \
            f"transformer {line['key']} in rock"
        assert all(grid[by + 1][x] != COL_EMPTY for x in (bx, bx + 1)), f"transformer {line['key']} footing"
        assert not reserved & set(cells), "transformers overlap"
        reserved |= set(cells)
        assert not {(y, x) for x, y in cells} & _hazard_cells(), "transformer over a lane"
        assert line["checkpoint"] not in cells and line["pole"] not in cells
    # Each box's zone: its two columns plus the three tiles before it, on open air,
    # clear of every lane (B there never stands the hero in a hazard).
    for line in LINES:
        rx, ry, rw, rh = grid_chain.reach_rect(line["box"])
        bx, by = line["box"]
        assert rx + rw == bx + 2 and rw == 5, "box zone covers the box's two columns and three tiles before it"
        assert all(0 < x < MAP_W - 1 and HUD_ROWS <= y < GROUND_ROW
                   for x in range(rx, rx + rw) for y in range(ry, ry + rh))
        assert all(grid[y][x] == COL_EMPTY for y in range(ry, ry + rh) for x in range(bx - 1, bx + 2)), \
            "box zone on open air"
        assert grid[by][bx - 1] == COL_EMPTY and grid[by + 1][bx - 1] != COL_EMPTY
        assert not {(y, x) for x in range(rx, rx + rw) for y in range(ry, ry + rh)} & _hazard_cells(), \
            f"{line['key']} box zone over a lane"
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    assert KIKO[0] - (JUNCTION_BOX[0] + 2) == 4 and STOVE[0] > HOUSE_DOOR[0], \
        "four clear tiles between the house box and Emil"
    # Wires: every route stays on the map and below the HUD; the chain is continuous;
    # every stage reaches its pole top and its transformer's top row.
    grid_chain.check_wire_routes(WIRE_ROUTES, STAGE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    for line in LINES:
        cells = {c for stage, route in WIRE_ROUTES if stage == line["number"] for c in route}
        assert _top(line["pole"]) in cells and _box_top(line["box"]) in cells, line["key"]
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == STAGE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, KIKO_SPRITE_ID, STOVE_SPRITE_ID}
    assert len(ids) == 4, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({str(n) for n in range(12)})
    assert {line["live_var"] for line in LINES} == {
        VAR_FEEDER_LIVE, VAR_WEST_LIVE, VAR_MIDDLE_LIVE, VAR_EAST_LIVE, VAR_LINE_LIVE
    }
    assert actor_count() <= MAX_SCENE_ACTORS
    # Entry from Signal Hill: right end of Priya's porch, clear of her door trigger.
    ex, ey, ew, eh = HILL_EXIT
    rtx, rty, rtw, _ = rosa.DOOR_TRIGGER
    assert ex >= rtx + rtw and ey + eh - 1 == rosa.PORCH_ROW and ex < rosa.MAP_W - 1


_self_check()
