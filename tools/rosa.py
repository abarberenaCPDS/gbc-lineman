"""Signal Hill - deterministic contract for Priya's repair job (job 3).

Data only for a 100x18-tile PLATFORM scene reached from Hiroshi's porch once his
house is powered. Five lines in one grid chain must be repaired before Priya's
router comes back on (Blackout Grid: she can work and study online again):

    edge -> feeder -> west -> middle -> east -> house box

Live cable arcs are the featured hazard: a downed wire sparks as a warning, then
arcs (hits) and rests, like a gust lane. Since 0.18 the hill carries the whole
kit (live arc, cracked boards, hidden cables, whips, gusts, fallen-span arcs) on
climb-style tiers, tighter than Wind Ridge. The boxes are background
transformers (``transformer_art.py``), as on Wind Ridge.

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
import transformer_art

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
# 0.18 redesign (Abe, 0.17 playtest: "reorganize the layout because it's too
# easy, have all of our obstacles there too ... same as Hiroshi's"). Wind Ridge's
# climb-style tiers on an 18-row map that never scrolls vertically: floor 15,
# rocks 12, plateaus and catwalks 9, the summit 6. Every rise is one short A tap
# (three rows); every carry crosses hazards sitting on the route, and the combos
# are tighter than Wind Ridge (a board right into a gust right into a whip).
#
#   1 feeder  rock A pole 1 -> tap onto catwalk C1 (cracked board on the landing,
#             whip 1 on the floor below) -> plateau B, T1
#   2 west    plateau B pole 2 -> drop to the floor: live arc, fallen span 1, then
#             a hidden cable right before the tap onto rock C, T2
#   3 middle  rock C pole 3 -> catwalk D1: cracked board, gust 1, then whip 2
#             guarding the tap onto the summit D, T3
#   4 east    summit pole 4 -> drop to catwalk E1 (whip 3 on the landing; the
#             step S climbs out of the pit below) -> plateau E, T4
#   5 house   plateau E pole 5 -> catwalk F (cracked board, hidden cable 2) or the
#             floor under it (fallen span 2, gust 2) -> Priya's porch: house box
# ---------------------------------------------------------------------------
GROUND_ROW = 15
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # one tap up: rocks A, C, step S and the porch
SURFACE_HIGH = GROUND_ROW - 6     # plateaus B, E and the catwalks
SURFACE_TOP = GROUND_ROW - 9      # summit D

# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                    # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1),    # right cliff wall behind the house
    (3, 5, SURFACE_STEP, GROUND_ROW - 1),         # rock A: pole 1 (feeder)
    (14, 18, SURFACE_HIGH, GROUND_ROW - 1),       # plateau B: T1, pole 2
    (36, 41, SURFACE_STEP, GROUND_ROW - 1),       # rock C: T2, pole 3
    (55, 60, SURFACE_TOP, GROUND_ROW - 1),        # summit D: T3, pole 4
    (61, 62, SURFACE_STEP, GROUND_ROW - 1),       # step S: the way out of the pit under E1
    (70, 74, SURFACE_HIGH, GROUND_ROW - 1),       # plateau E: T4, pole 5
    (88, 98, SURFACE_STEP, GROUND_ROW - 1),       # Priya's porch (box sits 4 tiles clear of her)
]
ROCK_A, PLATEAU_B, ROCK_C, SUMMIT_D, STEP_S, PLATEAU_E, PORCH = SOLID_BLOCKS[2:]
# One-way timber catwalks (row, x0, x1), each one tap above where it is reached from.
LEDGES: list[tuple[int, int, int]] = [
    (SURFACE_HIGH, 8, 12),     # C1: rock A -> plateau B (board on the landing, whip 1 below)
    (SURFACE_HIGH, 42, 54),    # D1: rock C -> summit (board, gust 1, whip 2)
    (SURFACE_HIGH, 63, 69),    # E1: summit -> plateau E (whip 3)
    (SURFACE_HIGH, 76, 86),    # F: plateau E -> porch (board, hidden cable 2; span 2 and gust 2 below)
]
C1, D1, E1, F = LEDGES
PORCH_ROW = SURFACE_STEP - 1      # porch actors stand on row 11, above every floor lane

START = (2, GROUND_ROW - 1)  # entry from Hiroshi's porch, facing right
ROSA = (95, PORCH_ROW)       # clear of the box's two columns, left of her door
WORKSTATION = (97, PORCH_ROW)    # computer + router on the porch table: Off -> On
HOUSE_DOOR = (96, PORCH_ROW)     # doorway column of Priya's house (art)
HOUSE_RECT = (95, 98, PORCH_ROW - 6, PORCH_ROW)    # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(95, PORCH_ROW - 3), (98, PORCH_ROW - 3)]
# Door checkpoint trigger: top row of a 24px hero standing on the porch.
DOOR_TRIGGER = (95, PORCH_ROW - 2, 3, 1)

# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is the feet tile of the background transformer the cable
# plugs into (transformer_art.py, 16x24 on two columns); "checkpoint" is the
# respawn once the line is repaired.
LINES = [
    {"key": "feeder", "pole": (4, SURFACE_STEP - 1), "box": (14, SURFACE_HIGH - 1),
     "box_kind": "transformer", "checkpoint": (16, SURFACE_HIGH - 1), "live_var": VAR_FEEDER_LIVE},
    {"key": "west", "pole": (18, SURFACE_HIGH - 1), "box": (36, SURFACE_STEP - 1),
     "box_kind": "transformer", "checkpoint": (38, SURFACE_STEP - 1), "live_var": VAR_WEST_LIVE},
    {"key": "middle", "pole": (40, SURFACE_STEP - 1), "box": (56, SURFACE_TOP - 1),
     "box_kind": "transformer", "checkpoint": (58, SURFACE_TOP - 1), "live_var": VAR_MIDDLE_LIVE},
    {"key": "east", "pole": (59, SURFACE_TOP - 1), "box": (70, SURFACE_HIGH - 1),
     "box_kind": "transformer", "checkpoint": (72, SURFACE_HIGH - 1), "live_var": VAR_EAST_LIVE},
    {"key": "house", "pole": (74, SURFACE_HIGH - 1), "box": (89, PORCH_ROW),
     "box_kind": "transformer", "checkpoint": (88, PORCH_ROW), "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
LINE_COUNT = len(LINES)

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the chest row of the surface
# they cross: row 13 on the floor, row 7 on a catwalk. Cracked boards and
# hidden cables are placed by hazards.py (its "signal_hill" keys).
# ---------------------------------------------------------------------------
CHEST_LOW = SURFACE_LOW - 2
CHEST_HIGH = SURFACE_HIGH - 2

# The live arc (Signal Hill's own hazard): a downed wire on two posts that
# sparks, arcs and rests. ARC_* timings are also the lab's and the climb's.
ARC_LANES = [
    (CHEST_LOW, 23, 24),
]
ARC_START_DELAYS = [0]
ARC_WARNING_FRAMES = 48     # sparks: safe, telegraphs the arc
ARC_ACTIVE_FRAMES = 24      # arc: hits (collision group 1)
ARC_REST_FRAMES = 80        # dark wire: safe

GUST_LANES: list[tuple[int, int, int]] = [(CHEST_HIGH, 46, 48), (CHEST_LOW, 84, 86)]   # D1, floor under F
GUST_START_DELAYS: list[int] = [24, 12]
# Tighter than Wind Ridge's 48/22/70, still telegraphed for 0.73 s.
GUST_WARNING_FRAMES = 44
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 62
# Arcs in this job (the live arc and the span arcs): sparks 0.67 s, arc 0.4 s,
# 0.87 s dark (Wind Ridge: 42/24/60). ARC_* above stay for the lab and the climb.
JOB_ARC_WARNING_FRAMES = 40
JOB_ARC_ACTIVE_FRAMES = 24
JOB_ARC_REST_FRAMES = 52

# Fallen spans: floor columns of the wire lying on the ground, the line whose
# repair makes it live (with every line above it), and its live_arc lanes.
FALLEN_SPANS: list[dict] = [
    {"columns": (26, 32), "live_after": 1, "arcs": [(CHEST_LOW, 28, 29)], "delays": [30]},
    {"columns": (77, 82), "live_after": 4, "arcs": [(CHEST_LOW, 79, 80)], "delays": [0]},
]

# Whipping live wire: hangs sparking, sways (warning, safe), then whips across
# the chest row (hits). Whip 1 hangs from catwalk C1 over the floor, whips 2
# and 3 from crossarms over catwalks D1 and E1.
WHIP_LANES = [(CHEST_LOW, 10, 11), (CHEST_HIGH, 52, 53), (CHEST_HIGH, 65, 66)]
WHIP_START_DELAYS = [0, 40, 24]
WHIP_SWAY_FRAMES = 36      # sparks and sways, safe: 0.6 s of warning (Wind Ridge: 40/22/62)
WHIP_SWING_FRAMES = 22
WHIP_HANG_FRAMES = 54
WHIP_SPRITE_ID = ridge.WHIP_SPRITE_ID
WHIP_PALETTE_ID = ridge.WHIP_PALETTE_ID
WHIP_SPRITE_PALETTE_SLOT = ridge.WHIP_SPRITE_PALETTE_SLOT

# Background transformers (transformer_art.py), as on Wind Ridge: no box actors,
# the wire palette lights them. The can is painted in the stone slot, its four
# colours mapped to the art's codes ('.' stays index 0, the dark behind the can).
BACKGROUND_BOXES = True
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)


# ---------------------------------------------------------------------------
# Wires (background art). Slots 5 (stages 1-3) and 6 (stages 4-5) hold wire pixels.
# Routes are polylines of tile cells; a pole's top is (x, y - 3), a box's
# hookup is the left tile of its transformer's top row.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]        # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    """A pole's top tile (its 32px canvas)."""
    return (cell[0], cell[1] - 3)


def _box_top(cell: tuple[int, int]) -> tuple[int, int]:
    """A background transformer's hookup tile: the left one of its stage-slot top row."""
    return transformer_art.tiles(cell)[0][0]


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _BOX = (line["box"] for line in LINES)
# Overhead rows per stage: above every pole top and box they reach, below the HUD,
# clear of the whip crossarms (rows 4-5 over D1 and E1).
OVERHEAD = [4, 3, 2, 3, 4]
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD[0]), (_P1[0], OVERHEAD[0]), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], OVERHEAD[0]), (_T1[0], OVERHEAD[0]), _box_top(_T1)]),
    (1, [_box_top(_T1), (_T1[0], OVERHEAD[0]), (_P2[0], OVERHEAD[0]), _top(_P2)]),
    (2, [_top(_P2), (_P2[0], OVERHEAD[1]), (_T2[0], OVERHEAD[1]), _box_top(_T2)]),
    (2, [_box_top(_T2), (_T2[0], OVERHEAD[1]), (_P3[0], OVERHEAD[1]), _top(_P3)]),
    (3, [_top(_P3), (_P3[0], OVERHEAD[2]), (_T3[0], OVERHEAD[2]), _box_top(_T3)]),
    (3, [_box_top(_T3), (_T3[0], OVERHEAD[2]), _top(_P4)]),      # the summit pole's top is row 2
    (4, [_top(_P4), (_P4[0] + 1, _top(_P4)[1]), (_P4[0] + 1, OVERHEAD[3]),
         (_T4[0], OVERHEAD[3]), _box_top(_T4)]),
    (4, [_box_top(_T4), (_T4[0], OVERHEAD[3]), (_P5[0], OVERHEAD[3]), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, OVERHEAD[4]),
         (_BOX[0], OVERHEAD[4]), _box_top(_BOX),
         (_BOX[0], OVERHEAD[4]), (HOUSE_RECT[0], OVERHEAD[4])]),
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
    """All lanes with background placards (live arc, gusts, span arcs, whips), by row then x."""
    return sorted([*ARC_LANES, *GUST_LANES, *span_arc_lanes(), *WHIP_LANES],
                  key=lambda lane: (lane[0], lane[1]))


def _all_hazard_lanes() -> list[tuple[int, int, int]]:
    import hazards
    return sorted([*hazard_lanes(), *hazards.HIDDEN_CABLES["signal_hill"]],
                  key=lambda lane: (lane[0], lane[1]))


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Priya, her workstation, one pole per line (the boxes are background art), hazards."""
    import hazards
    return (2 + LINE_COUNT + len(ARC_LANES) + len(GUST_LANES) + len(span_arc_lanes())
            + len(WHIP_LANES) + len(hazards.HIDDEN_CABLES["signal_hill"])
            + len(hazards.BOARDS["signal_hill"]))


def hazard_count() -> int:
    import hazards
    return actor_count() - 2 - LINE_COUNT


def surfaces() -> list[tuple[int, int, int]]:
    """Every raised walkable surface (surface row, x0, x1): solid block tops and catwalks."""
    out = [(row0, x0, x1) for x0, x1, row0, _ in SOLID_BLOCKS[2:]]
    return sorted(out + list(LEDGES), key=lambda s: (s[1], s[0]))


def board_cells() -> set[tuple[int, int]]:
    """(row, x) of each cracked board's standing row (its trigger)."""
    import hazards
    return {(row - 1, x) for row, x0, x1 in hazards.BOARDS["signal_hill"] for x in range(x0, x1 + 1)}


def _self_check() -> None:
    import hazards
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, ROSA, WORKSTATION, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    assert not {(y, x) for x, y in props} & board_cells(), "no prop or checkpoint on a cracked board"
    for row, x0, x1 in _all_hazard_lanes():
        surface = row + 2
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[surface][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
        assert row - 1 > HUD_ROWS, "hazards stay below the HUD"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*ARC_LANES, *span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes are two tiles wide"
    # Three standing tiles between lanes on the same row (the hero is two tiles wide).
    for row in {lane[0] for lane in _all_hazard_lanes()}:
        lanes = [lane for lane in _all_hazard_lanes() if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
            assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Boards lie on catwalks (their idle plank is background art), clear of every lane.
    for row, x0, x1 in hazards.BOARDS["signal_hill"]:
        assert any(lrow == row and lx0 <= x0 and x1 <= lx1 for lrow, lx0, lx1 in LEDGES), "board on a catwalk"
        assert all(grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1))
    assert not board_cells() & {(r + 1, x) for r, x0, x1 in _all_hazard_lanes() for x in range(x0, x1 + 1)}
    # Jumping or walking off a raised surface carries the hero ~5 tiles (Wind Ridge,
    # exact ROMs 3dd78a6e, c2aeecad, e1dd26e3): keep lower lanes to its right clear of the landing.
    for srow, _, sx1 in surfaces():
        for row, x0, _ in _all_hazard_lanes():
            if row + 2 > srow and x0 > sx1:
                assert x0 - sx1 >= 5, f"lane at {x0} in the landing off {sx1} (row {srow})"
    # Floor whips stay off screen from the porch (camera clamped at MAP_W - 20):
    # their 32px canvas reaches the porch actors' rows.
    assert all(x1 < MAP_W - 20 for row, _, x1 in WHIP_LANES if row == CHEST_LOW)
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    assert len(ARC_START_DELAYS) == len(ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Tiers: every raised surface is one tap (three rows) above the floor or the
    # surface it is reached from; catwalks have head room.
    assert {s[0] for s in surfaces()} <= {SURFACE_STEP, SURFACE_HIGH, SURFACE_TOP}
    for x0, x1, row0, row1 in (ROCK_A, ROCK_C, STEP_S, PORCH):
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "rocks are one tap high"
    for row, x0, x1 in LEDGES:
        assert all(grid[r][x] == COL_EMPTY for r in range(row - 3, row) for x in range(x0, x1 + 1)), \
            "head room over every catwalk"
    # Every pit has a way out: the floor under E1 climbs the step S.
    assert STEP_S[0] == SUMMIT_D[1] + 1 and E1[2] + 1 == PLATEAU_E[0]
    assert PORCH[2] - 1 == PORCH_ROW
    # The chain runs left to right: pole k < box k < pole k+1.
    grid_chain.check_chain_order(LINES)
    assert START[0] < LINES[0]["pole"][0] and LINES[-1]["box"][0] < HOUSE_DOOR[0]
    # Each box's reach trigger (B-06) lies on open air the hero walks or drops through.
    for line in LINES:
        rx, ry, rw, rh = line.get("reach") or grid_chain.reach_rect(line["box"])
        assert rx <= line["box"][0] <= rx + rw, "reach trigger reaches the box"
        assert all(grid[y][x] in (COL_EMPTY, COL_TOP) for y in range(ry, ry + rh) for x in range(rx, rx + rw)), \
            f"{line['key']} reach trigger in rock"
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
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert ROSA[0] - (_BOX[0] + 2) == 4 and WORKSTATION[0] > HOUSE_DOOR[0], \
        "four clear tiles between the house box and Priya"
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    # Wires: every route stays on the map below the HUD; the chain is continuous;
    # every stage reaches its pole top and its transformer's top row.
    grid_chain.check_wire_routes(WIRE_ROUTES, LINE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    assert WIRE_ROUTES[-1][1][-1][1] < HOUSE_RECT[2], "the house wire meets the roof from above"
    for line in LINES:
        cells = {c for stage, route in WIRE_ROUTES if stage == line["number"] for c in route}
        assert _top(line["pole"]) in cells and _box_top(line["box"]) in cells, line["key"]
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
    assert actor_count() <= MAX_SCENE_ACTORS


_self_check()
