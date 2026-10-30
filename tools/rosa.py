"""Signal Hill - deterministic contract for Priya's repair job (job 3), three scenes.

Data only. Since the multi-scene redesign (docs/LEVEL_REDESIGN.md §2 Job 3) the
job is a journey over three scenes, reached from Hiroshi's porch once his house
is powered. Five lines in one grid chain must be repaired before Priya's router
comes back on (Blackout Grid: she can work and study online again):

    edge -> feeder -> west -> middle -> east -> house box

  3A ``signal_hill`` (64x18, entry): up the hill. Lines 1-2 and pole 3; Priya's
     own free-standing live arc on the floor, the upper walk doubling the floor.
     Carry 3 leaves through the summit exit (62, 3).
  3B ``signal_gully`` (20x36, down): the new idea. Every deck is rock slab plus
     one-way timber across the full width, so the only way down is a Down+A
     drop-through tap (B-07: one shelf per tap) with the cable in hand. T3 on
     deck 9, pole 4 on deck 15, T4 on deck 27, pole 5 on the floor; carry 5
     leaves through the bottom-right exit (19, 30).
  3C ``signal_porch`` (40x18): the end of carry 5 across the creek bed (span
     arc, board, floor whip, gust on the rock), T5, Priya, her workstation,
     door and the gated exit to Emil's work order.

Lines are global, actors are local (grid_chain "Multi-scene jobs"): each line
names its ``pole_scene`` / ``box_scene``. The chain refresh, HUD and the chain
palettes are global; a carried cable (var 6) survives the scene switch.

The module-level geometry without a prefix is 3A's (``MAP_W``, ``SOLID_BLOCKS``,
``LEDGES``, ``START`` ...); 3B's is ``GULLY_*`` and 3C's ``PORCH_*``. Priya's
house constants (``ROSA``, ``WORKSTATION``, ``HOUSE_*``, ``DOOR_TRIGGER``,
``PORCH_ROW``) are 3C tiles. Per-scene data is in ``LAYOUTS[folder]``; the
helpers take a ``folder`` argument that defaults to 3A.

Every generator for this job reads this module: ``make_rosa_art.py`` (the three
backgrounds), ``make_rosa_sprites.py`` (Priya, her workstation and the live
arc), ``make_rosa_scene.py`` (3A and 3C) and ``make_gully_scene.py`` (3B).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row). Collision bytes follow GB Studio PLATFORM semantics: solid=0x0F,
top/one-way=0x01, empty=0x00.
"""

from __future__ import annotations

import uuid as _uuid

import climb
import grid_chain
import hazards
import ridge
import scene_links
import shaft
import transformer_art

TILE = 8
JOB = 3
HILL, GULLY, PORCH = "signal_hill", "signal_gully", "signal_porch"
SCENE_ORDER = (HILL, GULLY, PORCH)
SCENE_AXES = {HILL: "x", GULLY: "down", PORCH: "x"}

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player.
MAX_SCENE_ACTORS = 20
MAX_ACTIVE_ACTORS = 11

# ---------------------------------------------------------------------------
# Variables (project-global). Var 6 (carrying cable) holds which line's cable
# (1-5) and survives a switch between the job's scenes.
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
# 3A signal_hill (64x18): floor 15, rocks 12, plateau/catwalks 9, summit 6.
# Every rise is one short A tap (three rows).
#
#   1 feeder  rock A pole 1 -> catwalk C1 (board on the landing; Priya's live
#             arc on the floor below) -> plateau B, T1
#   2 west    plateau B pole 2 -> the upper walk U (whip) or the floor (span
#             arc 1, hidden cable) -> rock C, T2
#   3 middle  rock C pole 3 -> catwalk D1 (board, gust) -> the summit block,
#             whip before the exit; the cable goes on into the gully
# ---------------------------------------------------------------------------
MAP_W, MAP_H = 64, 18
GROUND_ROW = 15
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # one tap up: rocks A and C
SURFACE_HIGH = GROUND_ROW - 6     # plateau B and the catwalks
SURFACE_TOP = GROUND_ROW - 9      # the summit block

# (x0, x1, row0, row1) inclusive solid rectangles in addition to the floor.
SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                    # left cliff wall
    (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1),    # right cliff wall beside the exit
    (3, 5, SURFACE_STEP, GROUND_ROW - 1),         # rock A: pole 1 (feeder)
    (13, 18, SURFACE_HIGH, GROUND_ROW - 1),       # plateau B: T1, pole 2
    (33, 38, SURFACE_STEP, GROUND_ROW - 1),       # rock C: T2, pole 3
    (50, MAP_W - 1, SURFACE_TOP, GROUND_ROW - 1),  # summit block: the way into the gully
]
ROCK_A, PLATEAU_B, ROCK_C, SUMMIT_D = SOLID_BLOCKS[2:]
# One-way timber catwalks (row, x0, x1), each one tap above where it is reached from.
LEDGES: list[tuple[int, int, int]] = [
    (SURFACE_HIGH, 7, 12),     # C1: rock A -> plateau B (board on the landing, live arc below)
    (SURFACE_HIGH, 19, 30),    # U: plateau B -> rock C, the upper walk (whip)
    (SURFACE_HIGH, 39, 49),    # D1: rock C -> summit (board, gust)
]
C1, U, D1 = LEDGES
START = (2, GROUND_ROW - 1)    # entry from Hiroshi's porch (work order), facing right
HILL_EXIT = (62, 3, 1, 3)      # summit exit into the gully (scene_links)

# ---------------------------------------------------------------------------
# 3B signal_gully (20x36): the climb's shaft decks (shaft.py), all one-way walks.
# ---------------------------------------------------------------------------
GULLY_W, GULLY_H = shaft.MAP_W, shaft.MAP_H
GULLY_DECK_ROWS = list(shaft.DECK_ROWS)           # 27, 21, 15, 9: slabs + a one-way walk
GULLY_ARRIVAL = (5, 1, 9)                         # the arrival shelf under the top-left exit
GULLY_PLATFORMS: list[tuple[int, int, int]] = [
    GULLY_ARRIVAL,
    *[(row, *shaft.DECK_WALK) for row in GULLY_DECK_ROWS],
    (12, 6, 12), (18, 7, 13), (24, 6, 12), (30, 7, 13),   # ledges between the decks
    (shaft.DECK0_ROW, 1, GULLY_W - 2),                    # the floor: timber over bedrock
]
GULLY_LEDGES = [GULLY_ARRIVAL, (12, 6, 12), (18, 7, 13), (24, 6, 12), (30, 7, 13)]
GULLY_SOLID_BLOCKS: list[tuple[int, int, int, int]] = [
    (0, GULLY_W - 1, 34, 35),        # bedrock
    (0, 0, 0, 1),                    # left wall above the entry
    (0, 0, 5, 35),                   # left wall below the entry (open rows 2-4)
    (GULLY_W - 1, GULLY_W - 1, 0, 29),   # right wall above the floor exit
    (GULLY_W - 1, GULLY_W - 1, 33, 35),  # (open rows 30-32)
    *shaft.deck_solid_blocks(GULLY_DECK_ROWS),
]
GULLY_START = (2, 4)            # entry from the hill's summit exit, facing right
GULLY_FLOOR = shaft.DECK0_ROW

# ---------------------------------------------------------------------------
# 3C signal_porch (40x18): creek bed floor 15, the porch rock 12, a catwalk 9.
# ---------------------------------------------------------------------------
PORCH_W, PORCH_H = 40, 18
PORCH_SOLID_BLOCKS = [
    (0, 0, 2, GROUND_ROW - 1),                        # left cliff wall
    (PORCH_W - 1, PORCH_W - 1, 2, GROUND_ROW - 1),    # right wall behind the exit
    (18, PORCH_W - 1, SURFACE_STEP, GROUND_ROW - 1),  # Priya's porch rock
]
PORCH_ROCK = PORCH_SOLID_BLOCKS[2]
PORCH_LEDGES: list[tuple[int, int, int]] = [(SURFACE_HIGH, 8, 16)]   # the creek catwalk (board)
PORCH_START = (2, GROUND_ROW - 1)    # entry from the gully's floor exit
PORCH_ROW = SURFACE_STEP - 1          # porch actors stand on row 11
ROSA = (32, PORCH_ROW)               # four tiles clear of the house box, left of her door
HOUSE_DOOR = (33, PORCH_ROW)         # doorway column of Priya's house (art)
WORKSTATION = (34, PORCH_ROW)        # computer + router on the porch table: Off -> On
HOUSE_RECT = (32, 35, PORCH_ROW - 6, PORCH_ROW)    # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(32, PORCH_ROW - 3), (35, PORCH_ROW - 3)]
# Door checkpoint trigger: top row of a 24px hero standing on the porch.
DOOR_TRIGGER = (32, PORCH_ROW - 2, 3, 1)

# ---------------------------------------------------------------------------
# Lines, upstream first. "pole" is the cable-end pickup (the pole stands on the
# same tile); "box" is the feet tile of the background transformer the cable
# plugs into (transformer_art.py, 16x24 on two columns); "checkpoint" is the
# respawn once the line is repaired (in the box's scene).
# ---------------------------------------------------------------------------
LINES = [
    {"key": "feeder", "pole": (4, 11), "box": (14, 8), "checkpoint": (16, 8),
     "box_kind": "transformer", "live_var": VAR_FEEDER_LIVE, "pole_scene": HILL, "box_scene": HILL},
    {"key": "west", "pole": (18, 8), "box": (34, 11), "checkpoint": (36, 11),
     "box_kind": "transformer", "live_var": VAR_WEST_LIVE, "pole_scene": HILL, "box_scene": HILL},
    {"key": "middle", "pole": (38, 11), "box": (16, 8), "checkpoint": (14, 8),
     "box_kind": "transformer", "live_var": VAR_MIDDLE_LIVE, "pole_scene": HILL, "box_scene": GULLY},
    {"key": "east", "pole": (2, 14), "box": (16, 26), "checkpoint": (14, 26),
     "box_kind": "transformer", "live_var": VAR_EAST_LIVE, "pole_scene": GULLY, "box_scene": GULLY},
    {"key": "house", "pole": (3, 32), "box": (26, 11), "checkpoint": (28, 11),
     "box_kind": "transformer", "live_var": VAR_LINE_LIVE, "pole_scene": GULLY, "box_scene": PORCH},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
LINE_COUNT = len(LINES)

# ---------------------------------------------------------------------------
# Hazard timings (spec §1, Priya's tier: tighter than Wind Ridge).
# ---------------------------------------------------------------------------
# ARC_* are also the lab's and the climb's (Amara's tier); keep them.
ARC_WARNING_FRAMES = 48     # sparks: safe, telegraphs the arc
ARC_ACTIVE_FRAMES = 24      # arc: hits (collision group 1)
ARC_REST_FRAMES = 80        # dark wire: safe
# Arcs in this job (the live arc and the span arcs): 40/24/52 (Wind Ridge 42/24/60).
JOB_ARC_WARNING_FRAMES = 40
JOB_ARC_ACTIVE_FRAMES = 24
JOB_ARC_REST_FRAMES = 52
GUST_WARNING_FRAMES = 44    # 44/22/62 (Wind Ridge 48/22/70)
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 62
WHIP_SWAY_FRAMES = 36       # 36/22/54 (Wind Ridge 40/22/62)
WHIP_SWING_FRAMES = 22
WHIP_HANG_FRAMES = 54
CABLE_TIMINGS = hazards.CABLE_TIMINGS["rosa"]     # hidden cables: 140/20/24
WHIP_SPRITE_ID = ridge.WHIP_SPRITE_ID
WHIP_PALETTE_ID = ridge.WHIP_PALETTE_ID
WHIP_SPRITE_PALETTE_SLOT = ridge.WHIP_SPRITE_PALETTE_SLOT

# Lanes are (chest row, x0, x1): the hero's chest row, two above the surface.
CHEST_LOW = SURFACE_LOW - 2
CHEST_HIGH = SURFACE_HIGH - 2

# Per-scene hazards (boards and hidden cables: hazards.placement(folder, redesign=True)).
#   arcs   the free-standing live arc (Priya's own hazard, 3A only)
#   gusts, whips, spans (fallen spans: the wire on the ground goes live after
#   ``live_after`` leading lines; "columns" is the drawn wire on the surface)
LAYOUTS: dict[str, dict] = {
    HILL: {
        "arcs": [(CHEST_LOW, 10, 11)], "arc_delays": [0],
        "gusts": [(CHEST_HIGH, 45, 47)], "gust_delays": [24],
        "whips": [(CHEST_HIGH, 26, 27), (4, 55, 56)], "whip_delays": [0, 40],
        "spans": [{"columns": (22, 27), "live_after": 1, "arcs": [(CHEST_LOW, 24, 25)], "delays": [30]}],
    },
    GULLY: {
        "arcs": [], "arc_delays": [],
        "gusts": [(16, 9, 11), (31, 12, 14)], "gust_delays": [12, 36],
        "whips": [(10, 8, 9), (28, 7, 8)], "whip_delays": [0, 24],
        "spans": [{"columns": (6, 10), "live_after": 3, "arcs": [(19, 7, 8)], "delays": [20]}],
    },
    PORCH: {
        "arcs": [], "arc_delays": [],
        "gusts": [(10, 21, 23)], "gust_delays": [12],
        "whips": [(CHEST_LOW, 14, 15)], "whip_delays": [36],
        "spans": [{"columns": (5, 10), "live_after": 4, "arcs": [(CHEST_LOW, 7, 8)], "delays": [0]}],
    },
}
for _folder, _layout in LAYOUTS.items():
    _layout["boards"], _layout["cables"], _layout["cable_delays"] = hazards.placement(_folder, redesign=True)
LAYOUTS[HILL].update(width=MAP_W, height=MAP_H, platforms=LEDGES, ledges=LEDGES, start=START,
                     solid=SOLID_BLOCKS, floor=GROUND_ROW, vertical=False)
LAYOUTS[GULLY].update(width=GULLY_W, height=GULLY_H, platforms=GULLY_PLATFORMS, ledges=GULLY_LEDGES,
                      start=GULLY_START, solid=GULLY_SOLID_BLOCKS, floor=None, vertical=True)
LAYOUTS[PORCH].update(width=PORCH_W, height=PORCH_H, platforms=PORCH_LEDGES, ledges=PORCH_LEDGES,
                      start=PORCH_START, solid=PORCH_SOLID_BLOCKS, floor=GROUND_ROW, vertical=False)

# Legacy names (3A): the lab, the climb and other jobs read some of these.
ARC_LANES = LAYOUTS[HILL]["arcs"]
ARC_START_DELAYS = LAYOUTS[HILL]["arc_delays"]
GUST_LANES = LAYOUTS[HILL]["gusts"]
GUST_START_DELAYS = LAYOUTS[HILL]["gust_delays"]
WHIP_LANES = LAYOUTS[HILL]["whips"]
WHIP_START_DELAYS = LAYOUTS[HILL]["whip_delays"]
FALLEN_SPANS = LAYOUTS[HILL]["spans"]
ALL_FALLEN_SPANS = [span for folder in SCENE_ORDER for span in LAYOUTS[folder]["spans"]]

# Background transformers (transformer_art.py): no box actors, the wire palette
# lights them. The can is painted in the stone slot.
BACKGROUND_BOXES = True
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)


# ---------------------------------------------------------------------------
# Wires (background art). Slots 5 (stages 1-3) and 6 (stages 4-5) hold wire pixels.
# Routes are polylines of tile cells; a pole's top is (x, y - 3), a box's
# hookup is the left tile of its transformer's top row. A cell in a map-edge
# wall column is where the wire runs into the rock (not painted): power enters
# 3A through its left wall, and in the gully the wire passes the full-width
# decks inside the side walls.
#
# Wires cross scene edges (rule 5): stage 3 leaves 3A on row 3 through the
# summit exit and enters the gully on row 3 above its arrival shelf; stage 5
# leaves the gully on row 29 above its floor exit and enters 3C on row 4.
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
_T1, _T2, _T3, _T4, _T5 = (line["box"] for line in LINES)
EDGE_PORTS = {3: {HILL: 3, GULLY: 3}, 5: {GULLY: 29, PORCH: 4}}   # stage -> {folder: row}
WIRE_ROUTES_BY_SCENE: dict[str, list[tuple[int, list[tuple[int, int]]]]] = {
    HILL: [
        (1, [(0, 4), (_P1[0], 4), _top(_P1)]),
        (1, [_top(_P1), (_P1[0], 4), (_T1[0], 4), _box_top(_T1)]),
        (1, [_box_top(_T1), (_T1[0], 4), (_P2[0], 4), _top(_P2)]),
        (2, [_top(_P2), (_P2[0], 3), (_T2[0], 3), _box_top(_T2)]),
        (2, [_box_top(_T2), (_T2[0], 3), (_P3[0], 3), _top(_P3)]),
        (3, [_top(_P3), (_P3[0] + 1, _top(_P3)[1]), (_P3[0] + 1, EDGE_PORTS[3][HILL]),
             (MAP_W - 1, EDGE_PORTS[3][HILL])]),
    ],
    GULLY: [
        (3, [(0, EDGE_PORTS[3][GULLY]), (_T3[0], EDGE_PORTS[3][GULLY]), _box_top(_T3)]),
        (3, [_box_top(_T3), (GULLY_W - 1, _box_top(_T3)[1]), (GULLY_W - 1, _top(_P4)[1]), _top(_P4)]),
        (4, [_top(_P4), (0, _top(_P4)[1]), (0, 23), (_T4[0], 23), _box_top(_T4)]),
        (4, [_box_top(_T4), (_T4[0], 23), (0, 23), (0, _top(_P5)[1]), _top(_P5)]),
        (5, [_top(_P5), (GULLY_W - 1, EDGE_PORTS[5][GULLY])]),
    ],
    PORCH: [
        (5, [(0, EDGE_PORTS[5][PORCH]), (_T5[0], EDGE_PORTS[5][PORCH]), _box_top(_T5)]),
        (5, [_box_top(_T5), (_T5[0], EDGE_PORTS[5][PORCH]), (HOUSE_RECT[0], EDGE_PORTS[5][PORCH])]),
    ],
}
WIRE_ROUTES = WIRE_ROUTES_BY_SCENE[HILL]
SPAN_STAGE = [span["live_after"] for span in ALL_FALLEN_SPANS]
# {stages_live: {slot: metal colours}} for the background wire slots (one set for all three scenes).
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)

# Hardware colours, index 0 transparent placeholder.
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
TRANSFORMER_SPRITE_ID = ridge.TRANSFORMER_SPRITE_ID    # Wind Ridge's transformer asset, reused

# Entry from Wind Ridge: the right end of Hiroshi's porch (ridge's own contract
# until WP2 moves it to scene_links). Gated on his checkpoint (ridge var 9).
RIDGE_EXIT = (ridge.MAP_W - 2, ridge.PORCH_ROW - 2, 1, 3)
RIDGE_EXIT_GATE_VAR = ridge.VAR_HOME_POWERED   # "9"

# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
# OBJ slots: 0 worker, 1 Priya, 2 grid sprites (workstation), 3 live arc,
# 4 board, 5 gust, 6 whip, 7 pole - matching the climb/ridge layout.
ROSA_SPRITE_PALETTE_SLOT = 1
ARC_SPRITE_PALETTE_SLOT = 3
GUST_SPRITE_PALETTE_SLOT = 5
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
GULLY_SCENE_ID = resource_id(f"scene:{GULLY}")       # scenes.REGISTRY ids
PORCH_SCENE_ID = resource_id(f"scene:{PORCH}")
GULLY_BACKGROUND_ID = resource_id(f"background:{GULLY}")
PORCH_BACKGROUND_ID = resource_id(f"background:{PORCH}")
SCENE_IDS = {HILL: SCENE_ID, GULLY: GULLY_SCENE_ID, PORCH: PORCH_SCENE_ID}
BACKGROUND_IDS = {HILL: BACKGROUND_ID, GULLY: GULLY_BACKGROUND_ID, PORCH: PORCH_BACKGROUND_ID}
ROSA_SPRITE_ID = resource_id("sprite:rosa")
WORKSTATION_SPRITE_ID = resource_id("sprite:rosa_workstation")
ARC_SPRITE_ID = resource_id("sprite:live_arc")


# ---------------------------------------------------------------------------
# Per-scene helpers (``folder`` defaults to 3A)
# ---------------------------------------------------------------------------
def size(folder: str = HILL) -> tuple[int, int]:
    return LAYOUTS[folder]["width"], LAYOUTS[folder]["height"]


def collision_grid(folder: str = HILL) -> list[list[int]]:
    """Row-major PLATFORM collision bytes (height rows by width columns)."""
    layout = LAYOUTS[folder]
    width, height = size(folder)
    solid = list(layout["solid"])
    if layout["floor"] is not None:
        solid.insert(0, (0, width - 1, layout["floor"], height - 1))
    return shaft.collision_grid(width, height, layout["platforms"], solid)


def lines_here(folder: str = HILL) -> list[dict]:
    """The parts of LINES in ``folder`` (pole / box / checkpoint only where they stand)."""
    return grid_chain.scene_lines(LINES, folder)


def span_arc_lanes(folder: str = HILL) -> list[tuple[int, int, int]]:
    return [lane for span in LAYOUTS[folder]["spans"] for lane in span["arcs"]]


def hazard_lanes(folder: str = HILL) -> list[tuple[int, int, int]]:
    """All lanes with background placards (live arc, gusts, span arcs, whips), by row then x."""
    layout = LAYOUTS[folder]
    return sorted([*layout["arcs"], *layout["gusts"], *span_arc_lanes(folder), *layout["whips"]],
                  key=lambda lane: (lane[0], lane[1]))


def _all_hazard_lanes(folder: str = HILL) -> list[tuple[int, int, int]]:
    return sorted([*hazard_lanes(folder), *LAYOUTS[folder]["cables"]], key=lambda lane: (lane[0], lane[1]))


def _hazard_cells(folder: str = HILL) -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in _all_hazard_lanes(folder) for x in range(x0, x1 + 1)}


def route_lanes(folder: str = HILL) -> list[tuple[str, int, int, int]]:
    """[(kind, chest row, x0, x1)] for test_routes (span arcs and the live arc are "arc")."""
    layout = LAYOUTS[folder]
    lanes = [("arc", *lane) for lane in layout["arcs"]]
    lanes += [("gust", *lane) for lane in layout["gusts"]]
    lanes += [("arc", *lane) for lane in span_arc_lanes(folder)]
    lanes += [("whip", *lane) for lane in layout["whips"]]
    lanes += [("cable", *lane) for lane in layout["cables"]]
    return lanes


def npcs(folder: str = HILL) -> list[tuple[int, int]]:
    return [ROSA] if folder == PORCH else []


def devices(folder: str = HILL) -> list[tuple[int, int]]:
    return [WORKSTATION] if folder == PORCH else []


def actor_count(folder: str = HILL) -> int:
    """Poles here, Priya and her workstation (3C), and every hazard actor."""
    return len(npcs(folder)) + len(devices(folder)) + len(pole_lines(folder)) + hazard_count(folder)


def pole_lines(folder: str = HILL) -> list[dict]:
    return [line for line in LINES if line["pole_scene"] == folder]


def box_lines(folder: str = HILL) -> list[dict]:
    return [line for line in LINES if line["box_scene"] == folder]


def hazard_count(folder: str = HILL) -> int:
    layout = LAYOUTS[folder]
    return (len(layout["arcs"]) + len(layout["gusts"]) + len(span_arc_lanes(folder)) + len(layout["whips"])
            + len(layout["cables"]) + len(layout["boards"]))


def surfaces(folder: str = HILL) -> list[tuple[int, int, int]]:
    """Every raised walkable surface (surface row, x0, x1) of a run scene: block tops and catwalks."""
    walls = {(0, 0), (size(folder)[0] - 1, size(folder)[0] - 1)}
    out = [(row0, x0, x1) for x0, x1, row0, _ in LAYOUTS[folder]["solid"] if (x0, x1) not in walls]
    return sorted(out + list(LAYOUTS[folder]["ledges"]), key=lambda s: (s[1], s[0]))


def board_cells(folder: str = HILL) -> set[tuple[int, int]]:
    """(row, x) of each cracked board's standing row (its trigger)."""
    return {(row - 1, x) for row, x0, x1 in LAYOUTS[folder]["boards"] for x in range(x0, x1 + 1)}


def links(folder: str) -> list[scene_links.Link]:
    """This scene's exits as the redesign table writes them (this job generates all three folders)."""
    return [link for link in scene_links.table("redesign") if link.source == folder]


def entries(folder: str) -> list[tuple[int, int]]:
    """Every link entry tile into ``folder`` (the job start for the entry scene)."""
    out = [LAYOUTS[folder]["start"]]
    out += [link.entry for link in scene_links.table("redesign")
            if link.target == folder and link.ticket is None and link.entry not in out]
    return out


def downstream_exit(folder: str) -> tuple[int, int, int, int]:
    """The exit that carries the job on (not a back link)."""
    order = SCENE_ORDER.index(folder)
    for link in links(folder):
        if link.ticket is not None or (link.target in SCENE_ORDER and SCENE_ORDER.index(link.target) > order):
            return link.rect
    raise KeyError(folder)


def route_scene(folder: str) -> dict:
    """One test_routes route scene (docs/LEVEL_REDESIGN.md §7 shared validator schema)."""
    return {
        "folder": folder, "grid": collision_grid(folder), "start": LAYOUTS[folder]["start"],
        "entries": entries(folder), "lines": lines_here(folder), "lanes": route_lanes(folder),
        "boards": list(LAYOUTS[folder]["boards"]), "exit": downstream_exit(folder),
        "exits": [link.rect for link in links(folder)], "npcs": npcs(folder), "devices": devices(folder),
        "max_rise": 4 if LAYOUTS[folder]["vertical"] else 3, "culled": False,
    }


ROUTE_SCENES = [route_scene(folder) for folder in SCENE_ORDER]


# ---------------------------------------------------------------------------
# Self-check
# ---------------------------------------------------------------------------
def _check_scene(folder: str) -> None:
    layout = LAYOUTS[folder]
    width, height = size(folder)
    grid = collision_grid(folder)
    assert len(grid) == height and all(len(r) == width for r in grid), "grid size"
    here = lines_here(folder)
    props = [layout["start"], *npcs(folder), *devices(folder)]
    for line in here:
        props += [line[name] for name in ("pole", "box", "checkpoint") if name in line]
    grid_chain.check_props(grid, props, _hazard_cells(folder), HUD_ROWS)
    assert not {(y, x) for x, y in props} & board_cells(folder), "no prop or checkpoint on a cracked board"
    for row, x0, x1 in _all_hazard_lanes(folder):
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), f"{folder}: lane in rock"
        assert all(grid[row + 2][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), f"{folder}: lane floor"
        assert row - 1 > HUD_ROWS, "hazards stay below the HUD"
    for row, x0, x1 in layout["gusts"]:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*layout["arcs"], *span_arc_lanes(folder), *layout["whips"], *layout["cables"]):
        assert x1 - x0 == 1, "arc, cable and whip lanes are two tiles wide"
    for row in {lane[0] for lane in _all_hazard_lanes(folder)}:
        lanes = [lane for lane in _all_hazard_lanes(folder) if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(lanes, lanes[1:]):
            assert b0 - a1 >= 4, f"{folder}: need a three-tile standing gap between hazards"
    # Boards lie on one-way timber (their idle plank is background art), clear of every lane.
    for row, x0, x1 in layout["boards"]:
        assert all(grid[row][x] == COL_TOP and grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1)), \
            f"{folder}: board on a one-way walk"
    assert not board_cells(folder) & {(r + 1, x) for r, x0, x1 in _all_hazard_lanes(folder)
                                      for x in range(x0, x1 + 1)}
    for key in ("arc", "gust", "whip", "cable"):
        lanes, delays = (layout[f"{key}s"], layout[f"{key}_delays"])
        assert len(lanes) == len(delays), f"{folder}: one start delay per {key}"
    grid_chain.check_spans(layout["spans"], LINES)
    for span in layout["spans"]:
        row = span["arcs"][0][0] + 1
        c0, c1 = span["columns"]
        assert all(grid[row][x] == COL_EMPTY and grid[row + 1][x] != COL_EMPTY for x in range(c0, c1 + 1)), \
            f"{folder}: a fallen span lies on its surface"
    # Each box's reach zone (B-06) lies on open air the hero walks or drops through.
    for line in here:
        if "box" not in line:
            continue
        rx, ry, rw, rh = line.get("reach") or grid_chain.reach_rect(line["box"])
        assert all(grid[y][x] in (COL_EMPTY, COL_TOP) for y in range(ry, ry + rh) for x in range(rx, rx + rw)), \
            f"{line['key']} reach zone in rock"
    # Background transformers: open air on their two columns, support under both.
    reserved: set[tuple[int, int]] = set()
    for line in here:
        if "box" not in line:
            continue
        bx, by = line["box"]
        cells = transformer_art.all_tiles(line["box"])
        assert all(grid[ty][tx] == COL_EMPTY and ty >= HUD_ROWS for tx, ty in cells), \
            f"transformer {line['key']} in rock"
        assert all(grid[by + 1][x] != COL_EMPTY for x in (bx, bx + 1)), f"transformer {line['key']} footing"
        assert not reserved & set(cells), "transformers overlap"
        reserved |= set(cells)
        assert not {(y, x) for x, y in cells} & _hazard_cells(folder), "transformer over a lane"
    # Wires: every route stays on the map below the HUD and is continuous; only
    # this scene's stages; each pole top and transformer top here is on its stage.
    stages = {stage for stage, _ in WIRE_ROUTES_BY_SCENE[folder]}
    grid_chain.check_wire_routes(WIRE_ROUTES_BY_SCENE[folder], LINE_COUNT, width, HUD_ROWS, height - 1,
                                 stages=stages)
    for stage, route in WIRE_ROUTES_BY_SCENE[folder]:
        for (ax, ay), (bx, by) in zip(route, route[1:]):
            assert ax == bx or ay == by, "wire routes run straight between corners"
    for line in here:
        cells = {c for stage, route in WIRE_ROUTES_BY_SCENE[folder] if stage == line["number"] for c in route}
        if "pole" in line:
            assert _top(line["pole"]) in cells, f"{line['key']} wire reaches its pole"
        if "box" in line:
            assert _box_top(line["box"]) in cells, f"{line['key']} wire reaches its transformer"
    for stage, rows in EDGE_PORTS.items():
        if folder in rows:
            cells = {c for s, route in WIRE_ROUTES_BY_SCENE[folder] if s == stage for c in route}
            assert {(0, rows[folder]), (width - 1, rows[folder])} & cells, f"stage {stage} reaches the edge"
    # Entries stand, two columns inside the map; every exit is on an edge column.
    for x, y in entries(folder):
        assert grid_chain.stands(grid, x, y) and 2 <= x <= width - 3, f"{folder}: entry {(x, y)}"
    for x, y, w, h in [link.rect for link in links(folder)]:
        assert x in (0, 1, width - 2, width - 1) and w == 1 and h == 3
        assert all(grid[ty][x] == COL_EMPTY for ty in range(y, y + h)), f"{folder}: exit in rock"
    assert actor_count(folder) <= MAX_SCENE_ACTORS


def _self_check() -> None:
    for folder in SCENE_ORDER:
        _check_scene(folder)
    grid = collision_grid(HILL)
    # Run scenes: jumping or walking off a raised surface carries the hero ~5 tiles
    # (Wind Ridge, exact ROMs 3dd78a6e, c2aeecad, e1dd26e3): lower lanes to its right
    # stay clear of the landing.
    for folder in (HILL, PORCH):
        for srow, _, sx1 in surfaces(folder):
            for row, x0, _ in _all_hazard_lanes(folder):
                if row + 2 > srow and x0 > sx1:
                    assert x0 - sx1 >= 5, f"{folder}: lane at {x0} in the landing off {sx1} (row {srow})"
    # 3A tiers: every raised surface is one tap above the floor or the surface it is reached from.
    assert {s[0] for s in surfaces(HILL)} <= {SURFACE_STEP, SURFACE_HIGH, SURFACE_TOP}
    for x0, x1, row0, row1 in (ROCK_A, ROCK_C):
        assert row1 == GROUND_ROW - 1 and GROUND_ROW - row0 == 3, "rocks are one tap high"
    for row, x0, x1 in LEDGES:
        assert all(grid[r][x] == COL_EMPTY for r in range(row - 3, row) for x in range(x0, x1 + 1)), \
            "head room over every catwalk"
    # 3B: every deck is rock slab plus one-way timber wall to wall (Down+A is the only way down).
    gully = collision_grid(GULLY)
    for row in [*GULLY_DECK_ROWS, GULLY_FLOOR]:
        assert all(gully[row][x] != COL_EMPTY for x in range(1, GULLY_W - 1)), f"deck {row} spans the shaft"
        assert any(gully[row][x] == COL_TOP for x in range(1, GULLY_W - 1)), f"deck {row} has a walk"
    # Pole k < box k < pole k+1, by scene order, then x (runs) or rows (the gully, downwards).
    grid_chain.check_chain_order(LINES, scene_order=SCENE_ORDER, axes=SCENE_AXES)
    # 3C: Priya's porch (today's pattern): box, four clear tiles, Priya, door, workstation, exit.
    hx0, hx1, hy0, hy1 = HOUSE_RECT
    assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
    assert PORCH_ROCK[2] - 1 == PORCH_ROW
    tx, ty, tw, th = DOOR_TRIGGER
    assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
    assert ROSA[0] - (_T5[0] + 2) == 4 and WORKSTATION[0] > HOUSE_DOOR[0], \
        "four clear tiles between the house box and Priya"
    assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
    ex, ey, ew, eh = downstream_exit(PORCH)
    assert ex >= tx + tw and ey + eh - 1 == PORCH_ROW, "the work-order exit is past the door, on the porch"
    assert WIRE_ROUTES_BY_SCENE[PORCH][-1][1][-1] == (hx0, EDGE_PORTS[5][PORCH]) and EDGE_PORTS[5][PORCH] < hy0, \
        "the house wire meets the roof from above"
    # Floor whips stay off screen from the porch (camera clamped at width - 20).
    assert all(x1 < PORCH_W - 20 for row, _, x1 in LAYOUTS[PORCH]["whips"] if row == CHEST_LOW)
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == LINE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, GULLY_SCENE_ID, PORCH_SCENE_ID, GULLY_BACKGROUND_ID, PORCH_BACKGROUND_ID,
           ROSA_SPRITE_ID, WORKSTATION_SPRITE_ID, ARC_SPRITE_ID}
    assert len(ids) == 9, "resource ids collide"
    owned = {v for v, _, _ in VARIABLES}
    assert owned.isdisjoint({"0", "4", "5", "6", "7", "8", "9", "24", "25", "26"}), "reserved variables"
    assert {line["live_var"] for line in LINES} <= owned
    assert VAR_CARRYING_CABLE not in owned


_self_check()
