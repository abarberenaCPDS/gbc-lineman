"""Wind Ridge - deterministic contract for Hiroshi's repair job (job 2).

Data only for a 100x30-tile PLATFORM scene: a five-screen traverse with a
ground route and an upper catwalk, reached from Amara's summit once her line is
live. Three lines in one continuous grid chain must be repaired before
Hiroshi's oxygen concentrator comes back on.

Every generator for this job reads this module: ``make_ridge_art.py`` (art +
collision-aligned background), ``make_tomas_sprites.py`` (Hiroshi and the
concentrator), ``make_whip_sprite.py``, ``make_transformer_sprite.py`` and
``make_ridge_scene.py`` (scene, actors, triggers, scripts).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching climb.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import grid_chain
import transformer_art

TILE = 8
MAP_W, MAP_H = 100, 30

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player, 12 active.
MAX_SCENE_ACTORS = 20
MAX_ACTIVE_ACTORS = 11

# ---------------------------------------------------------------------------
# The grid chain (Abe, 2026-10-27): "the electrician fixes the grid by restoring
# the lines, posts and transformers. There should be continuity on the grid as
# in real life." Power enters at the left edge and flows downstream:
#
#   edge -> pole 1 -[line 1]-> T1 -> pole 2 -[line 2]-> T2 -> ... -> pole 5
#        -[line 5]-> house box -> Hiroshi's house
#
# Each line is repaired by carrying its pole's dangling cable end to its box
# (one cable a trip). A stretch of wire is live only when every line upstream of
# it is repaired; a repaired line downstream of a break stays dark. Each fallen
# span lies on the floor of a later carry and is live (its arcs fire) as soon
# as every line upstream of it is. Any order finishes. No hints (Abe).
#
# 0.18 redesign (Abe, 0.17 playtest: "reorganize the layout because it's too
# easy. Have all of our obstacles there too"), modelled on the climb he liked:
# three tiers (floor 27, rocks 24, plateaus and catwalks 21, the summit rock 18),
# short-A-tap rises of three rows, every carry crosses at least one hazard sitting
# on the route, and the gusts and whips guard the jumps. Left to right:
#
#   1 feeder  rock A pole 1 -> tap onto catwalk C1 (cracked board on the landing;
#             the floor below has whip 1) -> plateau B, T1
#   2 west    plateau B pole 2 -> drop to the floor: fallen span 1 arcs, then a
#             hidden cable right before the tap onto rock C, T2
#   3 middle  rock C pole 3 -> catwalk D1: gust 1, then whip 3 guarding the tap
#             onto the summit rock D, T3
#   4 east    rock D pole 4 -> drop to catwalk E1: whip 2, cracked board right
#             behind it -> floor: fallen span 2 arcs -> tap onto rock E, T4
#   5 house   rock E pole 5 -> catwalk F (cracked board) or the floor under it
#             (gust 2) -> Hiroshi's porch: house box, Hiroshi, door, exit
# ---------------------------------------------------------------------------
GROUND_ROW = 27
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # one tap up: rocks A, C, E and the porch
SURFACE_HIGH = GROUND_ROW - 6     # plateau B and the catwalks
SURFACE_TOP = GROUND_ROW - 9      # summit rock D

# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                    # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1),    # right cliff wall behind the house
    (5, 7, SURFACE_STEP, GROUND_ROW - 1),         # rock A: pole 1 (feeder)
    (15, 20, SURFACE_HIGH, GROUND_ROW - 1),       # plateau B: T1, pole 2
    (33, 38, SURFACE_STEP, GROUND_ROW - 1),       # rock C: T2, pole 3
    (52, 57, SURFACE_TOP, GROUND_ROW - 1),        # summit rock D: T3, pole 4
    (75, 80, SURFACE_STEP, GROUND_ROW - 1),       # rock E: T4, pole 5
    (89, 98, SURFACE_STEP, GROUND_ROW - 1),       # Hiroshi's porch (box sits 4 tiles clear of him)
]
ROCK_A, PLATEAU_B, ROCK_C, ROCK_D, ROCK_E, PORCH = SOLID_BLOCKS[2:]
# One-way timber catwalks (row, x0, x1), each three rows above where it is reached from.
LEDGES = [
    (SURFACE_HIGH, 9, 14),     # C1: rock A -> plateau B (board on the landing, whip 1 below)
    (SURFACE_HIGH, 40, 51),    # D1: rock C -> rock D (gust 1, whip 3)
    (SURFACE_HIGH, 59, 67),    # E1: rock D -> floor (whip 2, then a board)
    (SURFACE_HIGH, 82, 86),    # F: rock E -> porch (board; gust 2 on the floor below)
]
C1, D1, E1, F = LEDGES
PORCH_ROW = SURFACE_STEP - 1      # porch actors stand on row 23, above every floor lane

START = (2, GROUND_ROW - 1)       # entry from Amara's summit, facing right

# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is the feet tile of the background transformer the cable
# plugs into (transformer_art.py, 16x24 on two columns); "checkpoint" is the
# respawn once the line is repaired. "live_var" is project-global; var 8 keeps
# its old meaning (the house line), var 17 is still line 1.
LINES = [
    {"key": "feeder", "pole": (6, SURFACE_STEP - 1), "box": (15, SURFACE_HIGH - 1),
     "box_kind": "transformer", "checkpoint": (17, SURFACE_HIGH - 1), "live_var": "17"},
    {"key": "west", "pole": (19, SURFACE_HIGH - 1), "box": (34, SURFACE_STEP - 1),
     "box_kind": "transformer", "checkpoint": (36, SURFACE_STEP - 1), "live_var": "28"},
    {"key": "middle", "pole": (37, SURFACE_STEP - 1), "box": (53, SURFACE_TOP - 1),
     "box_kind": "transformer", "checkpoint": (55, SURFACE_TOP - 1), "live_var": "19"},
    {"key": "east", "pole": (56, SURFACE_TOP - 1), "box": (76, SURFACE_STEP - 1),
     "box_kind": "transformer", "checkpoint": (78, SURFACE_STEP - 1), "live_var": "29"},
    {"key": "house", "pole": (79, SURFACE_STEP - 1), "box": (89, PORCH_ROW),
     "box_kind": "transformer", "checkpoint": (91, PORCH_ROW), "live_var": "8"},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it

TOMAS = (95, PORCH_ROW)           # clear of the box's two columns; B talks from the door side
CONCENTRATOR = (97, PORCH_ROW)    # oxygen concentrator on the porch: Off -> On
HOUSE_DOOR = (96, PORCH_ROW)      # doorway column of Hiroshi's house (art)
HOUSE_RECT = (95, 98, PORCH_ROW - 6, PORCH_ROW)   # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(95, PORCH_ROW - 3), (98, PORCH_ROW - 3)]
DOOR_TRIGGER = (95, PORCH_ROW - 2, 3, 1)

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the chest row of the surface
# they cross: row 25 on the floor, row 19 on a catwalk. Cracked boards and
# hidden cables are placed by hazards.py (its "wind_ridge" keys).
# ---------------------------------------------------------------------------
CHEST_LOW = SURFACE_LOW - 2
CHEST_HIGH = SURFACE_HIGH - 2

GUST_LANES = [(CHEST_HIGH, 42, 44), (CHEST_LOW, 85, 87)]   # D1, floor under F
GUST_START_DELAYS = [30, 0]
# Harder than the climb's 54/20/90, still telegraphed for 0.8 s.
GUST_WARNING_FRAMES = 48
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 70
# Span arcs (shared sprite): sparks 0.7 s, arc 0.4 s, 1 s dark.
JOB_ARC_WARNING_FRAMES = 42
JOB_ARC_ACTIVE_FRAMES = 24
JOB_ARC_REST_FRAMES = 60

# Fallen spans: floor columns of the wire lying on the ground, the line whose
# repair makes it live (with every line above it), and its live_arc lanes
# (two wide).
FALLEN_SPANS = [
    {"columns": (22, 28), "live_after": 1, "arcs": [(CHEST_LOW, 25, 26)], "delays": [0]},
    {"columns": (69, 74), "live_after": 3, "arcs": [(CHEST_LOW, 72, 73)], "delays": [40]},
]

# Whipping live wire (Abe: "broken cables moved by the wind with sparks"): hangs
# sparking, sways (warning, safe), then whips across the chest row (hits).
# Placed with its 16x32 canvas bottom on the surface row above the lane; whip 1
# hangs from catwalk C1 over the floor, whips 2 and 3 from crossarms over a catwalk.
WHIP_LANES = [(CHEST_LOW, 12, 13), (CHEST_HIGH, 48, 49), (CHEST_HIGH, 62, 63)]
WHIP_START_DELAYS = [0, 50, 20]
WHIP_SWAY_FRAMES = 40    # sways (safe, sparking): 0.67 s of warning
WHIP_SWING_FRAMES = 22
WHIP_HANG_FRAMES = 62
WHIP_STATES = ["Hang", "Sway", "Swing"]
WHIP_CANVAS = (16, 32)
WHIP_SPRITE_PALETTE_SLOT = 6
WHIP_SPRITE_HARDWARE = ["000000", "FFF4A8", "8A97A6", "1B2028"]  # spark, sheath, dark

# The job transformer sprite (make_transformer_sprite.py; Signal Hill and Pine
# Hollow still place it as actors). Wind Ridge's boxes are its background
# version (transformer_art.py): no box actors, the wire palette lights them.
TRANSFORMER_CANVAS = (16, 32)
TRANSFORMER_STATES = ["Dead", "Live"]
BACKGROUND_BOXES = True
# Background hardware for the transformer cans: the stone slot, its four colours
# mapped to the art's codes ('.' stays index 0, the dark behind the can).
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)

# ---------------------------------------------------------------------------
# Wires (background art), drawn in BG slots LINE_BG_SLOT (5, stages 1-3) and
# LINE_BG_SLOT_2 (6, stages 4-5).
# Routes are polylines of tile cells; a pole's top is (x, y - 3).
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]     # chain stage -> metal colour index (1..3 per slot)


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    """A pole's top tile (its 32px canvas)."""
    return (cell[0], cell[1] - 3)


def _box_top(cell: tuple[int, int]) -> tuple[int, int]:
    """A background transformer's hookup tile: the left one of its stage-slot top row."""
    return transformer_art.tiles(cell)[0][0]


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _HOUSE_BOX = (line["box"] for line in LINES)
# Overhead rows per stage: above every pole and box they reach, clear of catwalks.
OVERHEAD = [15, 14, 12, 13, 16]
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD[0]), (_P1[0], OVERHEAD[0]), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], OVERHEAD[0]), (_T1[0], OVERHEAD[0]), _box_top(_T1)]),
    (1, [_box_top(_T1), (_T1[0], OVERHEAD[0]), (_P2[0], OVERHEAD[0]), _top(_P2)]),
    (2, [_top(_P2), (_P2[0], OVERHEAD[1]), (_T2[0], OVERHEAD[1]), _box_top(_T2)]),
    (2, [_box_top(_T2), (_T2[0], OVERHEAD[1]), (_P3[0], OVERHEAD[1]), _top(_P3)]),
    (3, [_top(_P3), (_P3[0], OVERHEAD[2]), (_T3[0], OVERHEAD[2]), _box_top(_T3)]),
    (3, [_box_top(_T3), (_T3[0], OVERHEAD[2]), (_P4[0], OVERHEAD[2]), _top(_P4)]),
    (4, [_top(_P4), (_P4[0] + 1, _top(_P4)[1]), (_P4[0] + 1, OVERHEAD[3]),
         (_T4[0], OVERHEAD[3]), _box_top(_T4)]),
    (4, [_box_top(_T4), (_T4[0], OVERHEAD[3]), (_P5[0], OVERHEAD[3]), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, OVERHEAD[4]),
         (_HOUSE_BOX[0], OVERHEAD[4]), _box_top(_HOUSE_BOX),
         (_HOUSE_BOX[0], OVERHEAD[4]), (HOUSE_RECT[0], OVERHEAD[4])]),
]
# Fallen span k is wired into stage k's colour: live as soon as it is.
SPAN_STAGE = [span["live_after"] for span in FALLEN_SPANS]

# {stages_live: {slot: metal colours}} for the background wire slots.
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared with the climb
# and reset by every scene init; here it holds which line's cable (1-5).
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "8"        # line 5, the house line (unchanged meaning)
VAR_HOME_POWERED = "9"     # Hiroshi checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "17"     # line 1
VAR_LINES_LIVE = "18"      # HUD count, 0-5
VAR_MIDDLE_LIVE = "19"     # line 3
VAR_CHAIN_LIVE = "20"      # how many leading lines are repaired: how far power reaches (0-5)
VAR_WEST_LIVE = "28"       # line 2
VAR_EAST_LIVE = "29"       # line 4
VARIABLES = [
    (VAR_LINE_LIVE, "Ridge Line Live", "var_ridge_line_live"),
    (VAR_HOME_POWERED, "Tomas Home Powered", "var_tomas_home_powered"),
    (VAR_FEEDER_LIVE, "Ridge Feeder Live", "var_ridge_feeder_live"),
    (VAR_LINES_LIVE, "Ridge Lines Live", "var_ridge_lines_live"),
    (VAR_MIDDLE_LIVE, "Ridge Middle Live", "var_ridge_middle_live"),
    (VAR_CHAIN_LIVE, "Ridge Chain Live", "var_ridge_chain_live"),
    (VAR_WEST_LIVE, "Ridge West Live", "var_ridge_west_live"),
    (VAR_EAST_LIVE, "Ridge East Live", "var_ridge_east_live"),
]
LINE_COUNT = len(LINES)
HUD_TEXT = f"LINE %D1${VAR_LINES_LIVE}$/{LINE_COUNT} HOME %D1$09$/1"

# Entry gate from the climb summit: only after Amara's checkpoint (climb var 0).
CLIMB_SUMMIT_EXIT = (17, 3, 1, 3)   # climb-scene trigger (x, y, w, h), right end of summit
CLIMB_EXIT_GATE_VAR = "0"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots in the ridge scene: 0 worker, 1 Hiroshi, 2 grid sprites (cable ends,
# boxes, transformers, concentrator), 3 live arcs (rosa's sprite bakes slot 3),
# 4 cracked board, 5 gust, 6 whipping wire, 7 storm poles.
TOMAS_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = 3
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
WHIP_SPRITE_ID = resource_id("sprite:whip_wire")
WHIP_PALETTE_ID = resource_id("palette:sprite:whip")
TRANSFORMER_SPRITE_ID = resource_id("sprite:transformer")


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
    return sorted([*GUST_LANES, *span_arc_lanes(), *WHIP_LANES], key=lambda lane: (lane[0], lane[1]))


def _all_hazard_lanes() -> list[tuple[int, int, int]]:
    import hazards
    return sorted([*hazard_lanes(), *hazards.HIDDEN_CABLES["wind_ridge"]],
                  key=lambda lane: (lane[0], lane[1]))


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Hiroshi, concentrator, one pole per line (the boxes are background art), hazards."""
    import hazards
    return (2 + len(LINES) + len(GUST_LANES) + len(span_arc_lanes()) + len(WHIP_LANES)
            + len(hazards.HIDDEN_CABLES["wind_ridge"]) + len(hazards.BOARDS["wind_ridge"]))


def surfaces() -> list[tuple[int, int, int]]:
    """Every raised walkable surface (surface row, x0, x1): solid block tops and catwalks."""
    out = [(row0, x0, x1) for x0, x1, row0, _ in SOLID_BLOCKS[2:]]
    return sorted(out + list(LEDGES), key=lambda s: (s[1], s[0]))


def board_cells() -> set[tuple[int, int]]:
    """(row, x) of each cracked board's standing row (its trigger)."""
    import hazards
    return {(row - 1, x) for row, x0, x1 in hazards.BOARDS["wind_ridge"] for x in range(x0, x1 + 1)}


def _self_check() -> None:
    import hazards
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, TOMAS, CONCENTRATOR, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    assert not {(y, x) for x, y in props} & board_cells(), "no prop or checkpoint on a cracked board"
    for row, x0, x1 in _all_hazard_lanes():
        surface = row + 2
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[surface][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes are two tiles wide"
    # Three standing tiles between lanes on the same surface (the hero is two tiles wide).
    for row in {lane[0] for lane in _all_hazard_lanes()}:
        lanes = [lane for lane in _all_hazard_lanes() if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
            assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Boards lie on catwalks (their idle plank is background art), clear of every lane.
    for row, x0, x1 in hazards.BOARDS["wind_ridge"]:
        assert any(lrow == row and lx0 <= x0 and x1 <= lx1 for lrow, lx0, lx1 in LEDGES), "board on a catwalk"
        assert all(grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1))
    assert not board_cells() & {(r + 1, x) for r, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}
    # Jumping or walking off a raised surface carries the hero ~5 tiles (exact ROMs
    # 3dd78a6e, c2aeecad, e1dd26e3): keep lower lanes to its right clear of the landing.
    for srow, _, sx1 in surfaces():
        for row, x0, _ in _all_hazard_lanes():
            if row + 2 > srow and x0 > sx1:
                assert x0 - sx1 >= 5, f"lane at {x0} in the landing off {sx1} (row {srow})"
    # Floor whips stay off screen from the porch (camera clamped at MAP_W - 20):
    # their 32px canvas reaches the porch actors' row and would make 11 OBJs.
    assert all(x1 < MAP_W - 20 for row, _, x1 in WHIP_LANES)
    # Span k lies between pole k and box k, so line k's carry crosses it.
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Tiers: every raised surface is one tap (three rows) above the floor or the
    # surface it is reached from; catwalks are never above a block.
    tiers = {SURFACE_STEP, SURFACE_HIGH, SURFACE_TOP}
    assert {s[0] for s in surfaces()} <= tiers
    for x0, x1, row0, row1 in (ROCK_A, ROCK_C, ROCK_E, PORCH):
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "rocks are one tap high"
    for row, x0, x1 in LEDGES:
        assert all(grid[r][x] == COL_EMPTY for r in range(row - 3, row) for x in range(x0, x1 + 1)), \
            "head room over every catwalk"
    # The chain runs left to right: pole k < box k < pole k+1.
    grid_chain.check_chain_order(LINES)
    # Background transformers: open air on their two columns, support under both.
    reserved: set[tuple[int, int]] = set()
    for line in LINES:
        bx, by = line["box"]
        cells = transformer_art.all_tiles(line["box"])
        assert all(grid[ty][tx] == COL_EMPTY for tx, ty in cells), f"transformer {line['key']} in rock"
        assert all(grid[by + 1][x] != COL_EMPTY for x in (bx, bx + 1)), f"transformer {line['key']} footing"
        assert not reserved & set(cells), "transformers overlap"
        reserved |= set(cells)
        assert not {(y, x) for x, y in cells} & _hazard_cells(), "transformer over a lane"
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    assert LINES[-1]["box"][0] + 1 + 4 < TOMAS[0] < HOUSE_DOOR[0] < CONCENTRATOR[0], \
        "four clear tiles between the house box and Hiroshi"
    # Wires: every route stays on the map and below the HUD; the chain is continuous;
    # every stage reaches its pole top and its transformer's top row.
    grid_chain.check_wire_routes(WIRE_ROUTES, len(LINES), MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    for line in LINES:
        cells = {c for stage, route in WIRE_ROUTES if stage == line["number"] for c in route}
        assert _top(line["pole"]) in cells and _box_top(line["box"]) in cells, line["key"]
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == len(LINES) + 1
    ids = {SCENE_ID, BACKGROUND_ID, TOMAS_SPRITE_ID, CONCENTRATOR_SPRITE_ID,
           WHIP_SPRITE_ID, WHIP_PALETTE_ID, TRANSFORMER_SPRITE_ID}
    assert len(ids) == 7, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "15", "16"})
    assert {line["live_var"] for line in LINES} == {
        VAR_FEEDER_LIVE, VAR_WEST_LIVE, VAR_MIDDLE_LIVE, VAR_EAST_LIVE, VAR_LINE_LIVE
    }
    assert actor_count() <= MAX_SCENE_ACTORS


_self_check()
