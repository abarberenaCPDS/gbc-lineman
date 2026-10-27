"""Wind Ridge - deterministic contract for Hiroshi's repair job (job 2).

Data only for a 60x18-tile PLATFORM scene: a three-screen horizontal traverse
reached from Amara's summit once her line is live. Timed gusts are the
featured hazard (step 2 of the hazard ladder in docs/redesign-brief.md), with
one cracked board from ``hazards.py`` on the floor. The Live Wire phase carries a snapped cable from a
pole to a junction box; powering the line switches on Hiroshi's oxygen
concentrator and warms his window (Blackout Grid).

Every generator for this job reads this module: ``make_ridge_art.py`` (art +
collision-aligned background), ``make_tomas_sprites.py`` (Hiroshi and the
concentrator) and ``make_ridge_scene.py`` (scene, actors, triggers, scripts).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching climb.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb

TILE = 8
MAP_W, MAP_H = 60, 18

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# ---------------------------------------------------------------------------
# Two lines (Abe, 2026-10-27: "include the number of lines in a scene, improving
# the puzzle and make the scenes a bit larger"). Left to right:
#
#   start | rock A, pole 1 | gust | feeder box J1 | cracked board | rock B, pole 2
#   | whipping wire | downed span: two arcs, live only once line 1 is | porch:
#   house box J2, Hiroshi, door
#
# The whip sits left of the span: its 32px canvas reaches the porch actors' row
# 11, and from the house box (camera clamped at x40) it must be off screen or
# row 11 carries 11 sprites.
#
# Line 1 (the feeder) runs pole 1 -> J1 and energizes the downed span. Line 2
# (the house line) runs pole 2 -> J2, so its cable is carried through the span.
# The puzzle is the order: line 2 first crosses a dead span; line 1 first means
# carrying cable 2 past live arcs (a hit drops it back on pole 2). The door
# needs both lines. Each live line moves the respawn to its box.
# ---------------------------------------------------------------------------
GROUND_ROW = 15
# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, 14),                  # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, 14),  # right cliff wall behind the house
    (6, 9, 12, 14),                 # rock A (top surface row 12): pole 1
    (28, 31, 12, 14),               # rock B (top surface row 12): pole 2
    (52, 58, 12, 14),               # Hiroshi's porch step (top surface row 12)
]
ROCK_A, ROCK_B, PORCH = SOLID_BLOCKS[2], SOLID_BLOCKS[3], SOLID_BLOCKS[4]
# Exact-ROM play showed the house props sharing the gusts' scanlines exceeded the
# 10-sprites-per-line limit (the concentrator lost its top half). On the porch,
# actors stand on row 11, above every hazard row.
PORCH_ROW = 11
LEDGES: list[tuple[int, int, int]] = []

START = (2, 14)            # entry from Amara's summit, facing right
# Line 1: the feeder.
FEEDER_POLE = (8, 11)      # cable-end pickup on rock A
FEEDER_BOX = (21, 14)      # J1 on the floor
FEEDER_CHECKPOINT = (22, 14)
# Line 2: the house line (the original job's pole -> box line; var 8).
DAMAGED_POLE = (30, 11)    # cable-end pickup on rock B
JUNCTION_BOX = (53, 11)    # J2, plug-in point at the top of the porch step
HOUSE_CHECKPOINT = (52, 11)
TOMAS = (54, 11)           # Hiroshi waits outside, left of his door
CONCENTRATOR = (57, 11)    # oxygen concentrator on the porch: Off -> On
HOUSE_DOOR = (56, 11)      # doorway column of Hiroshi's house (art)
HOUSE_RECT = (55, 58, 5, 11)   # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(55, 8), (58, 8)]
DOOR_TRIGGER = (55, 9, 3, 1)

# ---------------------------------------------------------------------------
# Hazards: lanes are (row, x0, x1) inclusive on the walking hero's chest row 13.
# ---------------------------------------------------------------------------
GUST_LANES = [(13, 15, 17)]          # three wide (climb_gust); between rock A and J1
GUST_START_DELAYS = [0]
GUST_WARNING_FRAMES = climb.GUST_WARNING_FRAMES
GUST_ACTIVE_FRAMES = climb.GUST_ACTIVE_FRAMES
GUST_REST_FRAMES = climb.GUST_REST_FRAMES

# The downed span: live_arc lanes (two wide, rosa.ARC_* timings) that stay
# dark and safe until line 1 is live. The art lays the fallen wire along the
# floor here in the line-1 colour, so it visibly lights with the feeder.
DOWNED_SPAN = (39, 49)               # floor columns of the fallen wire
SPAN_ARC_LANES = [(13, 41, 42), (13, 46, 47)]
SPAN_ARC_START_DELAYS = [0, 64]

# Whipping live wire (Abe: "broken cables moved by the wind with sparks"): a
# snapped line hangs from an overhead stub and sparks at its tip; on a wind
# cycle it sways (warning, safe) then whips across the chest row (hits).
WHIP_LANES = [(13, 36, 37)]          # two wide: the swing's reach on the chest row
WHIP_START_DELAYS = [30]
WHIP_SWAY_FRAMES = climb.GUST_WARNING_FRAMES
WHIP_SWING_FRAMES = climb.GUST_ACTIVE_FRAMES
WHIP_HANG_FRAMES = climb.GUST_REST_FRAMES
WHIP_STATES = ["Hang", "Sway", "Swing"]
WHIP_CANVAS = (16, 32)               # anchor at the top, tip sparks at chest height
WHIP_SPRITE_PALETTE_SLOT = 6         # the only OBJ slot still free in this scene
WHIP_SPRITE_HARDWARE = ["000000", "FFF4A8", "8A97A6", "1B2028"]  # spark, sheath, dark

# The cracked board (hazards.BOARDS["wind_ridge"]) sits on the floor before rock B.

# ---------------------------------------------------------------------------
# Cable routes (background art), drawn only in BG slot LINE_BG_SLOT (metal).
# Line 1 uses colour index LINE_COLOR_INDEX like every job; line 2 uses
# LINE2_COLOR_INDEX, unused by the metal slot's other art here. Four
# ridge-only metal palettes (LINE_PALETTES) light each line on its own.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
LINE2_COLOR_INDEX = 3
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
FEEDER_ROUTE = [(8, 8), (8, 6), (21, 6), (21, 12)]       # pole 1 top -> J1
CABLE_ROUTE = [(30, 8), (30, 4), (53, 4), (53, 10), (53, 4), (55, 4)]  # pole 2 -> J2 -> house


def line_palette(feeder_live: bool, house_live: bool) -> list[str]:
    """Metal slot colours for one combination of live lines."""
    colors = list(METAL_DEAD)
    colors[LINE_COLOR_INDEX] = (METAL_LIVE if feeder_live else METAL_DEAD)[LINE_COLOR_INDEX]
    colors[LINE2_COLOR_INDEX] = (METAL_LIVE[LINE_COLOR_INDEX] if house_live
                                 else METAL_DEAD[LINE_COLOR_INDEX])
    return colors


LINE_PALETTES = {(f, h): line_palette(f, h) for f in (False, True) for h in (False, True)}

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) is shared with the climb
# and reset by every scene init; here it holds which cable: 1 feeder, 2 house.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
CABLE_FEEDER, CABLE_HOUSE = 1, 2
VAR_LINE_LIVE = "8"        # line 2, the house line (unchanged meaning)
VAR_HOME_POWERED = "9"     # Hiroshi checkpoint; moves respawn to the door
VAR_FEEDER_LIVE = "17"     # line 1
VAR_LINES_LIVE = "18"      # HUD count, 0-2
VARIABLES = [
    (VAR_LINE_LIVE, "Ridge Line Live", "var_ridge_line_live"),
    (VAR_HOME_POWERED, "Tomas Home Powered", "var_tomas_home_powered"),
    (VAR_FEEDER_LIVE, "Ridge Feeder Live", "var_ridge_feeder_live"),
    (VAR_LINES_LIVE, "Ridge Lines Live", "var_ridge_lines_live"),
]
LINES = 2
HUD_TEXT = f"LINE %D1${VAR_LINES_LIVE}$/{LINES} HOME %D1$09$/1"

# Entry gate from the climb summit: only after Amara's checkpoint (climb var 0).
CLIMB_SUMMIT_EXIT = (17, 3, 1, 3)   # climb-scene trigger (x, y, w, h), right end of summit
CLIMB_EXIT_GATE_VAR = "0"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots in the ridge scene: 0 worker, 1 Hiroshi, 2 grid sprites (cable ends,
# junction boxes, concentrator), 3 live arcs (rosa's sprite bakes slot 3),
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
    return sorted([*GUST_LANES, *SPAN_ARC_LANES, *WHIP_LANES], key=lambda lane: lane[1])


def _hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in hazard_lanes() for x in range(x0, x1 + 1)}


def _stands(grid: list[list[int]], x: int, y: int) -> bool:
    """A 24px actor at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (COL_TOP, COL_SOLID))


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = (START, FEEDER_POLE, FEEDER_BOX, FEEDER_CHECKPOINT, DAMAGED_POLE, JUNCTION_BOX,
             HOUSE_CHECKPOINT, TOMAS, CONCENTRATOR, HOUSE_DOOR)
    hazards = _hazard_cells()
    for x, y in props:
        assert 0 < x < MAP_W - 1 and HUD_ROWS + 2 <= y < MAP_H - 1, f"bounds {(x, y)}"
        assert _stands(grid, x, y), f"actor tile {(x, y)} must stand clear on support"
        assert all(abs(x - hx) > 1 or abs(y - hy) > 2 for hy, hx in hazards), (
            f"prop {(x, y)} too close to a hazard")
    for row, x0, x1 in hazard_lanes():
        assert row == GROUND_ROW - 2, "lanes sit on the walking hero's chest row"
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[GROUND_ROW][x] == COL_SOLID for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in GUST_LANES:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*SPAN_ARC_LANES, *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes are two tiles wide"
    # Three standing tiles between every pair of hazard lanes.
    for (_, _, a1), (_, b0, _) in zip(hazard_lanes(), hazard_lanes()[1:]):
        assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    assert all(DOWNED_SPAN[0] <= x0 and x1 <= DOWNED_SPAN[1] for _, x0, x1 in SPAN_ARC_LANES)
    assert len(GUST_START_DELAYS) == len(GUST_LANES)
    assert len(SPAN_ARC_START_DELAYS) == len(SPAN_ARC_LANES)
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)
    # Rocks and porch are one tap high (three tiles) from the floor.
    for x0, x1, row0, row1 in SOLID_BLOCKS[2:]:
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "steps are 3 tiles high"
    # Jumping or walking off a rock carries the hero ~5 tiles (exact ROMs 3dd78a6e,
    # c2aeecad, and e1dd26e3 here, where a 2-tile gap landed in the gust).
    for rock in (ROCK_A, ROCK_B):
        assert all(x0 - rock[1] >= 5 for _, x0, _ in hazard_lanes() if x0 > rock[1]), (
            "rock landing in a hazard")
    # Route order: the house cable crosses the downed span and the whip; the feeder's does not.
    assert START[0] < FEEDER_POLE[0] < GUST_LANES[0][1] < FEEDER_BOX[0] < DAMAGED_POLE[0]
    assert DAMAGED_POLE[0] < WHIP_LANES[0][1] < DOWNED_SPAN[0] <= DOWNED_SPAN[1] < JUNCTION_BOX[0]
    # From the house box the camera is clamped at the right edge; the whip stays off screen.
    assert all(x1 < MAP_W - 20 for _, _, x1 in WHIP_LANES), "whip visible from the porch"
    assert FEEDER_BOX[0] < DOWNED_SPAN[0], "line 1's box sits before the span it energizes"
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw, (
        "door trigger covers only the standing hero's top row at the door")
    assert HOUSE_CHECKPOINT[0] < tx, "the house checkpoint stays off the door trigger"
    for route, pole, box in ((FEEDER_ROUTE, FEEDER_POLE, FEEDER_BOX),
                             (CABLE_ROUTE, DAMAGED_POLE, JUNCTION_BOX)):
        assert route[0] == (pole[0], pole[1] - 3), "cable leaves the pole top"
        assert box[0] in [x for x, _ in route]
        assert all(HUD_ROWS <= y < GROUND_ROW and 0 <= x < MAP_W for x, y in route)
    assert HOUSE_RECT[0] in [x for x, _ in CABLE_ROUTE]
    assert LINE2_COLOR_INDEX not in (0, LINE_COLOR_INDEX)
    assert LINE_PALETTES[(False, False)][LINE_COLOR_INDEX] == METAL_DEAD[LINE_COLOR_INDEX]
    assert len({tuple(c) for c in LINE_PALETTES.values()}) == 4, "each combination differs"
    ids = {SCENE_ID, BACKGROUND_ID, TOMAS_SPRITE_ID, CONCENTRATOR_SPRITE_ID,
           WHIP_SPRITE_ID, WHIP_PALETTE_ID}
    assert len(ids) == 6, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "15", "16"})


_self_check()
