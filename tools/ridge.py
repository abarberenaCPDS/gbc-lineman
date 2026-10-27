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
#   edge -> pole A -[line 1]-> transformer T1 -> pole B -[line 2]-> transformer T2
#        -> pole C -[line 3]-> house box -> Hiroshi's house
#
# Each line is repaired by carrying its pole's dangling cable end to its box
# (one cable a trip). A stretch of wire is live only when every line upstream of
# it is repaired; a repaired line downstream of a break stays dark. Each break
# also left a fallen span on the ground between the next pole and its box: the
# span is live (its arcs fire) as soon as every line upstream of it is. So
# working downstream first keeps the spans dead; energizing upstream first makes
# the later carries cross live arcs. Any order finishes. No hints (Abe).
#
# Left to right, ground floor surface row 27 (hero rows 24-26):
#   start | rock A, pole A | gust 1 | T1 | cracked board | steps up to plateau B,
#   pole B (surface 21) | catwalk (row 21, one-way) over fallen span 2 (arcs);
#   whip 1 on the catwalk | T2 | gust 2 | rock C, pole C | whip 2 | fallen span 3
#   (arc) | porch: house box, Hiroshi, door
# ---------------------------------------------------------------------------
GROUND_ROW = 27
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # one tap up (rocks, steps, porch)
SURFACE_HIGH = GROUND_ROW - 6     # plateau B and the catwalk

# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                    # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1),    # right cliff wall behind the house
    (6, 10, SURFACE_STEP, GROUND_ROW - 1),        # rock A: pole A
    (31, 33, SURFACE_STEP, GROUND_ROW - 1),       # step up to plateau B
    (34, 41, SURFACE_HIGH, GROUND_ROW - 1),       # plateau B: pole B
    (70, 73, SURFACE_STEP, GROUND_ROW - 1),       # rock C: pole C
    (92, 98, SURFACE_STEP, GROUND_ROW - 1),       # Hiroshi's porch step
]
ROCK_A, STEP_B, PLATEAU_B, ROCK_C, PORCH = SOLID_BLOCKS[2:]
# One-way catwalk at plateau height over fallen span 2: (row, x0, x1).
LEDGES = [(SURFACE_HIGH, 42, 58)]
CATWALK = LEDGES[0]
PORCH_ROW = SURFACE_STEP - 1      # porch actors stand on row 23, above every floor lane

START = (2, GROUND_ROW - 1)       # entry from Amara's summit, facing right

# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is where that cable plugs in; "checkpoint" is the respawn
# once the line is repaired. "live_var" is project-global; var 8 keeps its old
# meaning (the house line), var 17 is still line 1.
LINES = [
    {"key": "feeder", "pole": (8, SURFACE_STEP - 1), "box": (22, GROUND_ROW - 1),
     "box_kind": "transformer", "checkpoint": (23, GROUND_ROW - 1), "live_var": "17"},
    # T2 sits left of x62 so it is off screen from pole C (11 OBJs on row 23 otherwise).
    {"key": "middle", "pole": (38, SURFACE_HIGH - 1), "box": (59, GROUND_ROW - 1),
     "box_kind": "transformer", "checkpoint": (60, GROUND_ROW - 1), "live_var": "19"},
    {"key": "house", "pole": (72, SURFACE_STEP - 1), "box": (93, PORCH_ROW),
     "box_kind": "junction", "checkpoint": (92, PORCH_ROW), "live_var": "8"},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it

TOMAS = (94, PORCH_ROW)           # Hiroshi waits outside, left of his door
CONCENTRATOR = (97, PORCH_ROW)    # oxygen concentrator on the porch: Off -> On
HOUSE_DOOR = (96, PORCH_ROW)      # doorway column of Hiroshi's house (art)
HOUSE_RECT = (95, 98, PORCH_ROW - 6, PORCH_ROW)   # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(95, PORCH_ROW - 3), (98, PORCH_ROW - 3)]
DOOR_TRIGGER = (95, PORCH_ROW - 2, 3, 1)

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) inclusive on the chest row of the surface
# they cross: row 25 on the floor, row 19 on the catwalk.
# ---------------------------------------------------------------------------
CHEST_LOW = SURFACE_LOW - 2
CHEST_HIGH = SURFACE_HIGH - 2

GUST_LANES = [(CHEST_LOW, 16, 18), (CHEST_LOW, 65, 67)]   # three wide (climb_gust)
GUST_START_DELAYS = [0, 70]
GUST_WARNING_FRAMES = climb.GUST_WARNING_FRAMES
GUST_ACTIVE_FRAMES = climb.GUST_ACTIVE_FRAMES
GUST_REST_FRAMES = climb.GUST_REST_FRAMES

# Fallen spans: floor columns of the wire lying on the ground, the line whose
# repair makes it live (with every line above it), and its live_arc lanes
# (two wide, rosa.ARC_* timings).
FALLEN_SPANS = [
    # One arc on span 2: from T2 the gust, T2 and a second arc made 12 OBJs on rows 24-25.
    {"columns": (46, 57), "live_after": 1, "arcs": [(CHEST_LOW, 51, 52)], "delays": [0]},
    {"columns": (82, 89), "live_after": 2, "arcs": [(CHEST_LOW, 84, 85)], "delays": [20]},
]

# Whipping live wire (Abe: "broken cables moved by the wind with sparks"): hangs
# sparking, sways (warning, safe), then whips across the chest row (hits).
# Placed with its 16x32 canvas bottom on the surface row above the lane.
WHIP_LANES = [(CHEST_HIGH, 50, 51), (CHEST_LOW, 78, 79)]
WHIP_START_DELAYS = [30, 0]
WHIP_SWAY_FRAMES = climb.GUST_WARNING_FRAMES
WHIP_SWING_FRAMES = climb.GUST_ACTIVE_FRAMES
WHIP_HANG_FRAMES = climb.GUST_REST_FRAMES
WHIP_STATES = ["Hang", "Sway", "Swing"]
WHIP_CANVAS = (16, 32)
WHIP_SPRITE_PALETTE_SLOT = 6
WHIP_SPRITE_HARDWARE = ["000000", "FFF4A8", "8A97A6", "1B2028"]  # spark, sheath, dark

# The cracked board (hazards.BOARDS["wind_ridge"]) sits on the floor after T1.

# Transformers: a can on a short post, standing on the floor. Grid sprite slot.
TRANSFORMER_CANVAS = (16, 32)
TRANSFORMER_STATES = ["Dead", "Live"]

# ---------------------------------------------------------------------------
# Wires (background art), drawn only in BG slot LINE_BG_SLOT (metal). Three
# colour indices, one per chain stage, so four ridge-only palettes can light
# the chain as far as it is continuous. The metal slot holds nothing but wire:
# placards and brackets use the stone slot.
#
#   stage 1 (index 1): live once line 1 is repaired - edge -> pole A,
#                      line 1 (pole A -> T1), T1 -> pole B, fallen span 2
#   stage 2 (index 3): live once lines 1-2 are - line 2 (pole B -> T2),
#                      T2 -> pole C, fallen span 3
#   stage 3 (index 2): live once lines 1-3 are - line 3 (pole C -> house box -> house)
#
# Routes are polylines of tile cells; a pole's top is (x, y - 3).
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2]     # chain stage -> metal colour index


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    return (cell[0], cell[1] - 3)


_A, _B, _C = (line["pole"] for line in LINES)
_T1, _T2, _HOUSE_BOX = (line["box"] for line in LINES)
OVERHEAD = [_top(_A)[1] - 3, _top(_B)[1] - 3, _top(_C)[1] - 4]   # rows 17, 14, 16
WIRE_ROUTES = [
    # (stage, polyline)
    (1, [(0, OVERHEAD[0]), (_A[0], OVERHEAD[0]), _top(_A)]),                       # source -> pole A
    (1, [_top(_A), (_A[0], OVERHEAD[0]), (_T1[0], OVERHEAD[0]), (_T1[0], _T1[1] - 3)]),  # line 1
    (1, [(_T1[0], OVERHEAD[0]), (_B[0], OVERHEAD[0]), _top(_B)]),                  # T1 -> pole B
    (2, [_top(_B), (_B[0], OVERHEAD[1]), (_T2[0], OVERHEAD[1]), (_T2[0], _T2[1] - 3)]),  # line 2
    (2, [(_T2[0], OVERHEAD[1]), (_C[0], OVERHEAD[1]), _top(_C)]),                  # T2 -> pole C
    (3, [_top(_C), (_C[0], OVERHEAD[2]), (_HOUSE_BOX[0], OVERHEAD[2]),
         (_HOUSE_BOX[0], _HOUSE_BOX[1] - 1), (_HOUSE_BOX[0], OVERHEAD[2]),
         (HOUSE_RECT[0], OVERHEAD[2])]),                                            # line 3 -> house
]
# Fallen span k is wired into stage k-1's colour: live as soon as it is.
SPAN_STAGE = [span["live_after"] for span in FALLEN_SPANS]

# {stages_live: metal colours} for the background wire slot (grid_chain.chain_palette).
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared with the climb
# and reset by every scene init; here it holds which line's cable (1-3).
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "8"        # line 3, the house line (unchanged meaning)
VAR_HOME_POWERED = "9"     # Hiroshi checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "17"     # line 1
VAR_LINES_LIVE = "18"      # HUD count, 0-3
VAR_MIDDLE_LIVE = "19"     # line 2
VAR_CHAIN_LIVE = "20"      # how many leading lines are repaired: how far power reaches (0-3)
VARIABLES = [
    (VAR_LINE_LIVE, "Ridge Line Live", "var_ridge_line_live"),
    (VAR_HOME_POWERED, "Tomas Home Powered", "var_tomas_home_powered"),
    (VAR_FEEDER_LIVE, "Ridge Feeder Live", "var_ridge_feeder_live"),
    (VAR_LINES_LIVE, "Ridge Lines Live", "var_ridge_lines_live"),
    (VAR_MIDDLE_LIVE, "Ridge Middle Live", "var_ridge_middle_live"),
    (VAR_CHAIN_LIVE, "Ridge Chain Live", "var_ridge_chain_live"),
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


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in hazard_lanes() for x in range(x0, x1 + 1)}


def actor_count() -> int:
    """Hiroshi, concentrator, three per line (pole, cable end, box), hazards, boards."""
    import hazards
    return (2 + 3 * len(LINES) + len(GUST_LANES) + len(span_arc_lanes()) + len(WHIP_LANES)
            + len(hazards.BOARDS["wind_ridge"]))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [START, TOMAS, CONCENTRATOR, HOUSE_DOOR]
    for line in LINES:
        props += [line["pole"], line["box"], line["checkpoint"]]
    grid_chain.check_props(grid, props, _hazard_cells(), HUD_ROWS)
    for row, x0, x1 in hazard_lanes():
        surface = row + 2
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[surface][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes are two tiles wide"
    # Three standing tiles between lanes on the same surface.
    for row in {lane[0] for lane in hazard_lanes()}:
        lanes = [lane for lane in hazard_lanes() if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
            assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    # Jumping or walking off a raised block carries the hero ~5 tiles (exact ROMs
    # 3dd78a6e, c2aeecad, e1dd26e3): keep floor lanes clear of each landing.
    for block in (ROCK_A, PLATEAU_B, ROCK_C):
        assert all(x0 - block[1] >= 5 for row, x0, _ in hazard_lanes()
                   if row == CHEST_LOW and x0 > block[1]), "landing in a hazard"
    # Floor whips stay off screen from the porch (camera clamped at MAP_W - 20):
    # their 32px canvas reaches the porch actors' row and would make 11 OBJs.
    assert all(x1 < MAP_W - 20 for row, _, x1 in WHIP_LANES if row == CHEST_LOW)
    # Span k lies between pole k and box k, so line k's carry crosses it.
    grid_chain.check_spans(FALLEN_SPANS, LINES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Raised blocks are one tap (three tiles) above whatever they stand on.
    for x0, x1, row0, row1 in (ROCK_A, STEP_B, ROCK_C, PORCH):
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "steps are 3 tiles high"
    assert PLATEAU_B[2] == SURFACE_HIGH and STEP_B[1] + 1 == PLATEAU_B[0], "plateau via its step"
    row, cx0, cx1 = CATWALK
    assert row == SURFACE_HIGH and cx0 == PLATEAU_B[1] + 1, "catwalk continues the plateau"
    # The chain runs left to right: pole k < box k < pole k+1.
    grid_chain.check_chain_order(LINES)
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    assert LINES[-1]["box"][0] < TOMAS[0] < HOUSE_DOOR[0] < CONCENTRATOR[0]
    # Wires: every route stays on the map and below the HUD; the chain is continuous.
    grid_chain.check_wire_routes(WIRE_ROUTES, len(LINES), MAP_W, HUD_ROWS, GROUND_ROW)
    assert WIRE_ROUTES[-1][1][-1][0] == HOUSE_RECT[0], "the chain ends at the house"
    assert len({tuple(c) for c in CHAIN_PALETTES.values()}) == len(LINES) + 1
    ids = {SCENE_ID, BACKGROUND_ID, TOMAS_SPRITE_ID, CONCENTRATOR_SPRITE_ID,
           WHIP_SPRITE_ID, WHIP_PALETTE_ID, TRANSFORMER_SPRITE_ID}
    assert len(ids) == 7, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "15", "16"})
    assert {line["live_var"] for line in LINES} == {VAR_FEEDER_LIVE, VAR_MIDDLE_LIVE, VAR_LINE_LIVE}


_self_check()
