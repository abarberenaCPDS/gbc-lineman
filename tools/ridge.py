"""Hiroshi's lakeside ridge: job 2 (docs/terrain/HIROSHI_ROUTE.md).

Data only for two 64x18-tile PLATFORM scenes joined by an ungated edge:

  2A ``wind_ridge``   (entry scene; scene and background IDs kept from the 100x30 level)
  2B ``ridge_saddle`` (Hiroshi's porch and the hand-off to work order 3)

Five lines form one continuous grid chain. Lines 1-2 stand in 2A; line 3's pole
stands on the granite service pad in 2A and its transformer is in 2B, so its
cable is carried across the scene edge (the job's new idea). Lines 4-5 and the
house are in 2B. Lines are global, actors are local (§3 rule 3): each line names
the folder of its pole and box, and each scene builds its own
``grid_chain.GridChain(scene=...)`` from the same ``LINES``.

Every generator for this job reads this module: ``make_ridge_art.py`` (both
backgrounds), ``make_tomas_sprites.py`` (Hiroshi and the concentrator),
``make_whip_sprite.py``, ``make_transformer_sprite.py`` and
``make_ridge_scene.py`` (both scenes, actors, triggers, scripts).

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row), matching climb.py. Collision bytes follow GB Studio PLATFORM
semantics: solid=0x0F, top/one-way=0x01, empty=0x00. Per-scene data lives in
``LAYOUTS[folder]`` (a :class:`Layout`); the module-level names that other jobs
import (sprite IDs, timings, ``START``, ``PORCH_ROW``, ``SCENE_ID``) keep their
meaning.
"""

from __future__ import annotations

import uuid as _uuid
from typing import Any

import climb
import grid_chain
import hazards
import scene_links
import scenes
import transformer_art

TILE = 8
MAP_W, MAP_H = 64, 18            # both scenes

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

# Rows 0-1 sit under the 16px HUD window; keep gameplay below them.
HUD_ROWS = 2

# Engine limits (gbvm actor.h): 21 actors including the player, 12 active.
MAX_SCENE_ACTORS = 20
MAX_ACTIVE_ACTORS = 11

JOB = 2
RIDGE = "wind_ridge"
SADDLE = "ridge_saddle"
SCENE_ORDER = (RIDGE, SADDLE)
assert SCENE_ORDER == scenes.JOB_SCENES[JOB]

# ---------------------------------------------------------------------------
# Tiers: floor row 15 (feet 14), step 12 (11), and the high seam shelf 9 (8).
# ---------------------------------------------------------------------------
GROUND_ROW = 15
SURFACE_LOW = GROUND_ROW          # floor
SURFACE_STEP = GROUND_ROW - 3     # service pads, exposed crossings and porch
SURFACE_HIGH = GROUND_ROW - 6     # feeder catwalk and the inter-scene shelf
CHEST_LOW = SURFACE_LOW - 2
CHEST_STEP = SURFACE_STEP - 2
PORCH_ROW = SURFACE_STEP - 1      # Hiroshi's porch feet row (2B)
_WALLS = [(0, 0, 2, GROUND_ROW - 1), (MAP_W - 1, MAP_W - 1, 2, GROUND_ROW - 1)]

# ---------------------------------------------------------------------------
# The grid chain (Abe, 2026-10-27): "the electrician fixes the grid by restoring
# the lines, posts and transformers. There should be continuity on the grid as
# in real life." Power enters at 2A's left edge and flows downstream; each line is
# repaired by carrying its pole's dangling cable end to its transformer (one
# cable a trip). A stretch of wire is live only when every line upstream of it is
# repaired. Left to right:
#
#   2A 1 feeder  first rock -> cracked timber bridge -> T1 feeder pad
#      2 west    lower step -> visible fallen span -> T2 granite pad
#      3 middle  granite pad -> exposed gust shelf -> high seam
#   2B 3 middle  matched high landing -> hidden cable -> T3
#      4 east    cracked traverse -> island gust -> T4 sheltered work pad
#      5 house   island pole 5 -> final exposed landing -> T5 and lakeside cabin
# ---------------------------------------------------------------------------
LINES = [
    {"key": "feeder", "pole": (6, SURFACE_STEP - 1), "box": (16, SURFACE_HIGH - 1),
     "box_kind": "transformer", "checkpoint": (18, SURFACE_HIGH - 1), "live_var": "17",
     "pole_scene": RIDGE, "box_scene": RIDGE},
    {"key": "west", "pole": (20, SURFACE_HIGH - 1), "box": (36, SURFACE_STEP - 1),
     "box_kind": "transformer", "checkpoint": (38, SURFACE_STEP - 1), "live_var": "28",
     "pole_scene": RIDGE, "box_scene": RIDGE},
    {"key": "middle", "pole": (40, SURFACE_STEP - 1), "box": (17, SURFACE_STEP - 1),
     "box_kind": "transformer", "checkpoint": (19, SURFACE_STEP - 1), "live_var": "19",
     "pole_scene": RIDGE, "box_scene": SADDLE},
    {"key": "east", "pole": (21, SURFACE_STEP - 1), "box": (36, SURFACE_STEP - 1),
     # The wider default reach would start inside the island gust.
     "reach": (35, SURFACE_STEP - 3, 3, 3),
     "box_kind": "transformer", "checkpoint": (38, SURFACE_STEP - 1), "live_var": "29",
     "pole_scene": SADDLE, "box_scene": SADDLE},
    {"key": "house", "pole": (39, SURFACE_STEP - 1), "box": (52, PORCH_ROW),
     "box_kind": "transformer", "checkpoint": (56, PORCH_ROW), "live_var": "8",
     "pole_scene": SADDLE, "box_scene": SADDLE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
LINE_COUNT = len(LINES)
CROSS_LINE = LINES[2]              # line 3: carried across the 2A -> 2B edge

# Hiroshi's porch (2B): box E, four clear tiles, Hiroshi, door, concentrator, exit.
TOMAS = (58, PORCH_ROW)           # B talks from the box side
CONCENTRATOR = (60, PORCH_ROW)    # oxygen concentrator on the porch: Off -> On
HOUSE_DOOR = (59, PORCH_ROW)      # doorway column of Hiroshi's house (art)
HOUSE_RECT = (58, 61, PORCH_ROW - 6, PORCH_ROW)   # (x0, x1, row0, row1)
# Each window must use exactly one BG slot-3 tile so the slot swap warms it.
HOUSE_WINDOWS = [(58, PORCH_ROW - 3), (61, PORCH_ROW - 3)]
DOOR_TRIGGER = (58, PORCH_ROW - 2, 3, 1)

# ---------------------------------------------------------------------------
# Hazard timings (spec §1 tier: between Amara and Priya)
# ---------------------------------------------------------------------------
GUST_WARNING_FRAMES = 48
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 70
JOB_ARC_WARNING_FRAMES = 42
JOB_ARC_ACTIVE_FRAMES = 24
JOB_ARC_REST_FRAMES = 60
WHIP_SWAY_FRAMES = 40    # sways (safe, sparking): 0.67 s of warning
WHIP_SWING_FRAMES = 22
WHIP_HANG_FRAMES = 62
CABLE_TIMINGS = hazards.CABLE_TIMINGS["ridge"]     # hidden cables: (dark, warning, arc)

# Whipping live wire (Abe: "broken cables moved by the wind with sparks").
WHIP_STATES = ["Hang", "Sway", "Swing"]
WHIP_CANVAS = (16, 32)
WHIP_SPRITE_PALETTE_SLOT = 6
WHIP_SPRITE_HARDWARE = ["000000", "FFF4A8", "8A97A6", "1B2028"]  # spark, sheath, dark

# The job transformer sprite (make_transformer_sprite.py; other jobs may still
# place it as an actor). Ridge boxes are its background version (transformer_art.py).
TRANSFORMER_CANVAS = (16, 32)
TRANSFORMER_STATES = ["Dead", "Live"]
BACKGROUND_BOXES = True
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)


# ---------------------------------------------------------------------------
# Wires (background art), BG slots LINE_BG_SLOT (5, stages 1-3) and
# LINE_BG_SLOT_2 (6, stages 4-5). The chain palettes are one set for both scenes.
# ---------------------------------------------------------------------------
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[climb.LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[climb.LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]     # chain stage -> metal colour index (1..3 per slot)
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)
# Rule 5: a stage that crosses an edge runs on the same row on both sides (2A x63, 2B x0).
EDGE_PORTS = {CROSS_LINE["number"]: 3}


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    """A pole's top tile (its 32px canvas)."""
    return (cell[0], cell[1] - 3)


def _box_top(cell: tuple[int, int]) -> tuple[int, int]:
    """A background transformer's hookup tile: the left one of its stage-slot top row."""
    return transformer_art.tiles(cell)[0][0]


_P1, _P2, _P3, _P4, _P5 = (line["pole"] for line in LINES)
_T1, _T2, _T3, _T4, _HOUSE_BOX = (line["box"] for line in LINES)
_PORT = EDGE_PORTS[3]
# Overhead rows sit above the pole tops and transformer caps, below the HUD.
# A route leaving a pole top steps one column right, so stages never share a column.
RIDGE_ROUTES = [
    (1, [(0, 4), (_P1[0], 4), _top(_P1)]),
    (1, [_top(_P1), (_P1[0], 4), (_T1[0], 4), _box_top(_T1)]),
    (1, [_box_top(_T1), (_T1[0], 4), (_P2[0], 4), _top(_P2)]),
    (2, [_top(_P2), (_P2[0] + 1, _top(_P2)[1]), (_P2[0] + 1, 2), (_T2[0], 2), _box_top(_T2)]),
    (2, [_box_top(_T2), (_T2[0], 2), (_P3[0], 2), _top(_P3)]),
    (3, [_top(_P3), (_P3[0] + 1, _top(_P3)[1]), (_P3[0] + 1, _PORT), (MAP_W - 1, _PORT)]),
]
SADDLE_ROUTES = [
    (3, [(0, _PORT), (_T3[0], _PORT), _box_top(_T3)]),
    (3, [_box_top(_T3), (_T3[0], _PORT), (_P4[0], _PORT), _top(_P4)]),
    (4, [_top(_P4), (_P4[0] + 1, _top(_P4)[1]), (_P4[0] + 1, 4), (_T4[0], 4), _box_top(_T4)]),
    (4, [_box_top(_T4), (_T4[0], 4), (_P5[0], 4), _top(_P5)]),
    (5, [_top(_P5), (_P5[0] + 1, _top(_P5)[1]), (_P5[0] + 1, 3), (_HOUSE_BOX[0], 3),
         _box_top(_HOUSE_BOX), (_HOUSE_BOX[0], 3), (HOUSE_RECT[0], 3)]),
]

# ---------------------------------------------------------------------------
# Variables (project-global; meanings unchanged). Var 6 (carrying cable) survives
# a scene switch (§3 rule 2); only the job's fresh start clears it.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6"
VAR_LINE_LIVE = "8"        # line 5, the house line
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
HUD_TEXT = f"LINE %D1${VAR_LINES_LIVE}$/{LINE_COUNT} HOME %D1$09$/1"

# Entry gate from the climb summit (today's layout; scene_links.py owns the redesign's).
CLIMB_SUMMIT_EXIT = (17, 3, 1, 3)
CLIMB_EXIT_GATE_VAR = "0"

# ---------------------------------------------------------------------------
# Palettes. OBJ slots in both scenes: 0 worker, 1 Hiroshi, 2 grid sprites
# (concentrator), 3 live arcs, 4 cracked board, 5 gust, 6 whipping wire, 7 storm poles.
# ---------------------------------------------------------------------------
TOMAS_SPRITE_PALETTE_SLOT = 1
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT
ARC_SPRITE_PALETTE_SLOT = 3
TOMAS_SPRITE_HARDWARE = ["000000", "E8C39E", "4F7A5B", "1E2A2E"]
WINDOW_BG_SLOT = 3
TOMAS_STATES = ["Waiting", "Relieved"]
CONCENTRATOR_STATES = ["Off", "On"]

_RIDGE_NAMESPACE = _uuid.UUID("9c4d1a2e-7b3f-5e60-8a1d-2f3e4c5b6a70")


def resource_id(key: str) -> str:
    """Stable IDs for every resource this job generates."""
    return str(_uuid.uuid5(_RIDGE_NAMESPACE, "mr-cfe:ridge:" + key))


SCENE_ID = resource_id("scene:wind-ridge")
BACKGROUND_ID = resource_id("background:wind-ridge")
SADDLE_SCENE_ID = scenes.REGISTRY[SADDLE]["id"]
SADDLE_BACKGROUND_ID = resource_id("background:ridge-saddle")
TOMAS_SPRITE_ID = resource_id("sprite:tomas")
CONCENTRATOR_SPRITE_ID = resource_id("sprite:oxygen_concentrator")
WHIP_SPRITE_ID = resource_id("sprite:whip_wire")
WHIP_PALETTE_ID = resource_id("palette:sprite:whip")
TRANSFORMER_SPRITE_ID = resource_id("sprite:transformer")


# ---------------------------------------------------------------------------
# Per-scene layouts
# ---------------------------------------------------------------------------
class Layout:
    """One scene of the job: geometry, hazards, wires and links.

    It also serves as the per-scene "contract" the background checks read
    (``collision_grid()``, ``MAP_W``, ``LEDGES``, ``hazard_lanes()``...).
    """

    MAP_W, MAP_H, GROUND_ROW, HUD_ROWS = MAP_W, MAP_H, GROUND_ROW, HUD_ROWS
    STAGE_COLOR_INDEX, CHAIN_PALETTES = STAGE_COLOR_INDEX, CHAIN_PALETTES
    METAL_DEAD, WIRE_LIVE, WIRE_DEAD = METAL_DEAD, WIRE_LIVE, WIRE_DEAD
    LINE_COUNT = LINE_COUNT

    def __init__(self, folder: str, *, scene_id: str, background_id: str, name: str,
                 blocks: list[tuple[int, int, int, int]], ledges: list[tuple[int, int, int]],
                 gusts: list[tuple[int, int, int]], gust_delays: list[int],
                 whips: list[tuple[int, int, int]], whip_delays: list[int],
                 boards: list[tuple[int, int, int]], cables: list[tuple[int, int, int]],
                 cable_delays: list[int],
                 spans: list[dict[str, Any]], routes: list[tuple[int, list[tuple[int, int]]]],
                 house: bool, first_hazard: dict[str, int]) -> None:
        self.folder = folder
        self.SCENE_ID = scene_id
        self.BACKGROUND_ID = background_id
        self.NAME = name
        self.SOLID_BLOCKS = _WALLS + blocks
        self.BLOCKS = blocks               # raised blocks (walls excluded)
        self.LEDGES = ledges
        self.GUST_LANES = gusts
        self.GUST_START_DELAYS = gust_delays
        self.WHIP_LANES = whips
        self.WHIP_START_DELAYS = whip_delays
        self.FALLEN_SPANS = spans
        self.WIRE_ROUTES = routes
        self.STAGES = sorted({stage for stage, _ in routes})
        self.HOUSE = house
        self.LAKESIDE = True
        self.HOUSE_WINDOWS = HOUSE_WINDOWS if house else []
        # These placements move with our terrain; shared hazards.py still supplies the
        # scripts, timing constants and historical spec/legacy placements.
        self.BOARDS, self.HIDDEN_CABLES, self.CABLE_START_DELAYS = boards, cables, cable_delays
        # Job-wide hazard numbering (actor/trigger keys and board values stay unique per job).
        self.first_hazard = first_hazard
        self.LINES = grid_chain.scene_lines(LINES, folder)
        self.links = scene_links.from_scene(folder, scene_links.table("redesign"))
        self.arrivals = scene_links.into_scene(folder, scene_links.table("redesign"))
        rank = SCENE_ORDER.index(folder)
        # Upstream entry: the work order's job start, else the link from the previous scene.
        self.START = scene_links.REDESIGN_START[JOB] if rank == 0 else next(
            link.entry for link in self.arrivals if link.source == SCENE_ORDER[rank - 1])
        self.ENTRIES = [self.START] + sorted({link.entry for link in self.arrivals} - {self.START})
        exits = [link for link in self.links if link.target not in SCENE_ORDER or
                 SCENE_ORDER.index(link.target) > SCENE_ORDER.index(folder)]
        self.EXIT = exits[-1].rect
        self.EXITS = [link.rect for link in self.links]

    # -- geometry -----------------------------------------------------------
    def collision_grid(self) -> list[list[int]]:
        """Row-major PLATFORM collision bytes (MAP_H rows by MAP_W columns)."""
        grid = [[COL_EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]
        for row in range(GROUND_ROW, MAP_H):
            for x in range(MAP_W):
                grid[row][x] = COL_SOLID
        for row, x0, x1 in self.LEDGES:
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_TOP
        for x0, x1, row0, row1 in self.SOLID_BLOCKS:
            for row in range(row0, row1 + 1):
                for x in range(x0, x1 + 1):
                    grid[row][x] = COL_SOLID
        return grid

    def surfaces(self) -> list[tuple[int, int, int]]:
        """Every raised walkable surface (surface row, x0, x1): block tops and catwalks."""
        out = [(row0, x0, x1) for x0, x1, row0, _ in self.BLOCKS]
        return sorted(out + list(self.LEDGES), key=lambda s: (s[1], s[0]))

    def span_arc_lanes(self) -> list[tuple[int, int, int]]:
        return [lane for span in self.FALLEN_SPANS for lane in span["arcs"]]

    def hazard_lanes(self) -> list[tuple[int, int, int]]:
        """Drawn lanes (gust, span arc, whip): hidden cables have no background art."""
        return sorted([*self.GUST_LANES, *self.span_arc_lanes(), *self.WHIP_LANES],
                      key=lambda lane: (lane[0], lane[1]))

    def all_hazard_lanes(self) -> list[tuple[int, int, int]]:
        return sorted([*self.hazard_lanes(), *self.HIDDEN_CABLES], key=lambda lane: (lane[0], lane[1]))

    def hazard_cells(self) -> set[tuple[int, int]]:
        return {(row, x) for row, x0, x1 in self.all_hazard_lanes() for x in range(x0, x1 + 1)}

    def board_cells(self) -> set[tuple[int, int]]:
        """(row, x) of each cracked board's standing row (its trigger)."""
        return {(row - 1, x) for row, x0, x1 in self.BOARDS for x in range(x0, x1 + 1)}

    def pole_lines(self) -> list[dict[str, Any]]:
        return [line for line in LINES if line["pole_scene"] == self.folder]

    def box_lines(self) -> list[dict[str, Any]]:
        return [line for line in LINES if line["box_scene"] == self.folder]

    def hazard_count(self) -> int:
        return (len(self.GUST_LANES) + len(self.span_arc_lanes()) + len(self.WHIP_LANES)
                + len(self.HIDDEN_CABLES) + len(self.BOARDS))

    def actor_count(self) -> int:
        """Poles here (boxes are background art), Hiroshi and the concentrator, hazards."""
        return len(self.pole_lines()) + (2 if self.HOUSE else 0) + self.hazard_count()

    def trigger_count(self) -> int:
        """Exits, door, boards, box and pole zones (talk uses an actor-distance test)."""
        return (len(self.links) + (1 if self.HOUSE else 0) + len(self.BOARDS)
                + len(self.box_lines()) + len(self.pole_lines()))

    def lanes(self) -> list[tuple[str, int, int, int]]:
        """[(kind, chest row, x0, x1)] for test_routes."""
        out = [("gust", *lane) for lane in self.GUST_LANES]
        out += [("whip", *lane) for lane in self.WHIP_LANES]
        out += [("arc", *lane) for lane in self.span_arc_lanes()]
        out += [("cable", *lane) for lane in self.HIDDEN_CABLES]
        return out

    def route_scene(self) -> dict[str, Any]:
        """test_routes.py ROUTE_SCENES entry."""
        return {
            "folder": self.folder, "grid": self.collision_grid(), "start": self.START,
            "entries": list(self.ENTRIES), "lines": self.LINES, "lanes": self.lanes(),
            "boards": list(self.BOARDS), "exit": self.EXIT, "exits": list(self.EXITS),
            "npcs": [TOMAS] if self.HOUSE else [], "devices": [CONCENTRATOR] if self.HOUSE else [],
        }


LAYOUTS = {
    RIDGE: Layout(
        RIDGE, scene_id=SCENE_ID, background_id=BACKGROUND_ID, name="Wind Ridge",
        blocks=[(5, 7, SURFACE_STEP, GROUND_ROW - 1),       # pole 1
                (15, 22, SURFACE_HIGH, GROUND_ROW - 1),    # feeder pad: T1, pole 2
                (23, 26, SURFACE_STEP, GROUND_ROW - 1),    # descent/recovery step
                (36, 42, SURFACE_STEP, GROUND_ROW - 1),    # service island: T2, pole 3
                (46, 53, SURFACE_STEP, GROUND_ROW - 1),    # gust landing and lee
                (54, 62, SURFACE_HIGH, GROUND_ROW - 1)],   # level return entry and seam
        ledges=[(SURFACE_HIGH, 9, 14)],
        gusts=[(CHEST_STEP, 47, 49)], gust_delays=[30],
        whips=[], whip_delays=[],
        boards=[(SURFACE_HIGH, 9, 11)], cables=[], cable_delays=[],
        spans=[{"columns": (29, 33), "live_after": 1, "arcs": [(CHEST_LOW, 31, 32)], "delays": [0]}],
        routes=RIDGE_ROUTES, house=False,
        first_hazard={"gust": 1, "whip": 1, "span": 1, "cable": 1, "board": 1},
    ),
    SADDLE: Layout(
        SADDLE, scene_id=SADDLE_SCENE_ID, background_id=SADDLE_BACKGROUND_ID, name="Ridge Saddle",
        blocks=[(1, 6, SURFACE_HIGH, GROUND_ROW - 1),       # safe upper arrival
                (7, 8, SURFACE_STEP, GROUND_ROW - 1),      # reverse climb below seam
                (17, 22, SURFACE_STEP, GROUND_ROW - 1),    # T3 and pole 4
                (31, 43, SURFACE_STEP, GROUND_ROW - 1),    # gust, T4, pole 5
                (47, MAP_W - 2, SURFACE_STEP, GROUND_ROW - 1)],  # gust lip and Hiroshi's porch
        ledges=[(SURFACE_STEP, 24, 27)],
        gusts=[(CHEST_STEP, 31, 33), (CHEST_STEP, 47, 49)], gust_delays=[20, 0],
        whips=[], whip_delays=[],
        boards=[(SURFACE_STEP, 24, 26)], cables=[(CHEST_LOW, 13, 14)], cable_delays=[40],
        spans=[],
        routes=SADDLE_ROUTES, house=True,
        first_hazard={"gust": 2, "whip": 1, "span": 2, "cable": 1, "board": 2},
    ),
}
RIDGE_LAYOUT, SADDLE_LAYOUT = LAYOUTS[RIDGE], LAYOUTS[SADDLE]
START = RIDGE_LAYOUT.START        # tickets.TICKETS[2]["start"]: the work order card lands here
FALLEN_SPANS = [span for layout in LAYOUTS.values() for span in layout.FALLEN_SPANS]   # job-wide
WIRE_ROUTES = RIDGE_ROUTES + SADDLE_ROUTES
ROUTE_SCENES = [layout.route_scene() for layout in LAYOUTS.values()]


def collision_grid(folder: str = RIDGE) -> list[list[int]]:
    return LAYOUTS[folder].collision_grid()


def hazard_lanes(folder: str | None = None) -> list[tuple[int, int, int]]:
    folders = [folder] if folder else list(SCENE_ORDER)
    return [lane for f in folders for lane in LAYOUTS[f].hazard_lanes()]


def hazard_count() -> int:
    """Hazard actors in the whole job (spec §1: 16)."""
    return sum(layout.hazard_count() for layout in LAYOUTS.values())


def actor_count(folder: str | None = None) -> int:
    """Actors of one scene, or (None) of the whole job: poles, Hiroshi and the concentrator, hazards."""
    if folder is not None:
        return LAYOUTS[folder].actor_count()
    return sum(layout.actor_count() for layout in LAYOUTS.values())


def _self_check_layout(layout: Layout) -> None:
    grid = layout.collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"
    props = [layout.START, *layout.ENTRIES]
    if layout.HOUSE:
        props += [TOMAS, CONCENTRATOR, HOUSE_DOOR]
    for line in layout.LINES:
        props += [line[name] for name in ("pole", "box", "checkpoint") if name in line]
    grid_chain.check_props(grid, props, layout.hazard_cells(), HUD_ROWS)
    assert not {(y, x) for x, y in props} & layout.board_cells(), "no prop or checkpoint on a cracked board"
    lanes = layout.all_hazard_lanes()
    for row, x0, x1 in lanes:
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[row + 2][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
    assert all(x1 - x0 == 2 for _, x0, x1 in layout.GUST_LANES), "gust lanes match the 24px gust sprite"
    assert all(x1 - x0 == 1 for _, x0, x1 in (*layout.span_arc_lanes(), *layout.WHIP_LANES))
    for row in {lane[0] for lane in lanes}:
        same = [lane for lane in lanes if lane[0] == row]
        for (_, _, a1), (_, b0, _) in zip(same, same[1:]):
            assert b0 - a1 >= 4, "need a three-tile standing gap between hazards"
    for row, x0, x1 in layout.BOARDS:
        assert any(lrow == row and lx0 <= x0 and x1 <= lx1 for lrow, lx0, lx1 in layout.LEDGES), "board on a catwalk"
        assert all(grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1))
    assert not layout.board_cells() & {(r + 1, x) for r, x0, x1 in lanes for x in range(x0, x1 + 1)}
    # Jumping or walking off a raised surface carries the hero ~5 tiles: keep lower lanes
    # to its right clear of the landing.
    for srow, _, sx1 in layout.surfaces():
        for row, x0, _ in lanes:
            if row + 2 > srow and x0 > sx1:
                assert x0 - sx1 >= 5, f"{layout.folder}: lane at {x0} in the landing off {sx1} (row {srow})"
    for span in layout.FALLEN_SPANS:
        line = LINES[span["live_after"]]
        assert line["pole_scene"] == line["box_scene"] == layout.folder, "a span lies under a local carry"
    grid_chain.check_spans(layout.FALLEN_SPANS, LINES)
    assert len(layout.GUST_START_DELAYS) == len(layout.GUST_LANES)
    assert len(layout.WHIP_START_DELAYS) == len(layout.WHIP_LANES)
    assert len(layout.CABLE_START_DELAYS) == len(layout.HIDDEN_CABLES)
    assert {s[0] for s in layout.surfaces()} <= {SURFACE_STEP, SURFACE_HIGH}
    for row, x0, x1 in layout.LEDGES:
        assert all(grid[r][x] == COL_EMPTY for r in range(row - 3, row) for x in range(x0, x1 + 1)), \
            "head room over every catwalk"
    reserved: set[tuple[int, int]] = set()
    for line in layout.box_lines():
        bx, by = line["box"]
        cells = transformer_art.all_tiles(line["box"])
        assert all(grid[ty][tx] == COL_EMPTY for tx, ty in cells), f"transformer {line['key']} in rock"
        assert all(grid[by + 1][x] != COL_EMPTY for x in (bx, bx + 1)), f"transformer {line['key']} footing"
        assert not reserved & set(cells), "transformers overlap"
        reserved |= set(cells)
        assert not {(y, x) for x, y in cells} & layout.hazard_cells(), "transformer over a lane"
    # Wires: on the map, below the HUD, continuous; each local stage reaches its pole top / box top.
    grid_chain.check_wire_routes(layout.WIRE_ROUTES, LINE_COUNT, MAP_W, HUD_ROWS, GROUND_ROW,
                                 stages=layout.STAGES)
    for line in LINES:
        cells = {c for stage, route in layout.WIRE_ROUTES if stage == line["number"] for c in route}
        if line["pole_scene"] == layout.folder:
            assert _top(line["pole"]) in cells, line["key"]
        if line["box_scene"] == layout.folder:
            assert _box_top(line["box"]) in cells, line["key"]
    # Every carry crosses a hazard: from the pole (or the arrival) to the box (or the exit).
    for line in LINES:
        here = [line[f] == layout.folder for f in ("pole_scene", "box_scene")]
        if not any(here):
            continue
        start = line["pole"][0] if here[0] else layout.START[0]
        end = line["box"][0] if here[1] else layout.EXIT[0]
        spans = [(x0, x1) for _, x0, x1 in [*lanes, *layout.BOARDS]]
        assert any(start < x0 and x1 < end for x0, x1 in spans), f"{line['key']} carry crosses a hazard"
    # Exits and entries come from scene_links; entries are clear of every exit.
    for x, y in layout.ENTRIES:
        assert grid_chain.stands(grid, x, y) and 2 <= x <= MAP_W - 3
        hero = {(tx, ty) for tx in (x, x + 1) for ty in (y - 2, y - 1, y)}
        for ex, ey, ew, eh in layout.EXITS:
            rect = {(tx, ty) for tx in range(ex, ex + ew) for ty in range(ey, ey + eh)}
            assert not hero & rect, f"{layout.folder}: entry {(x, y)} inside exit {(ex, ey, ew, eh)}"
    if layout.HOUSE:
        hx0, hx1, hy0, hy1 = HOUSE_RECT
        assert all(grid[y][x] == COL_EMPTY for x in range(hx0, hx1 + 1) for y in range(hy0, hy1 + 1))
        assert hx0 <= HOUSE_DOOR[0] <= hx1 and hy1 == PORCH_ROW, "door inside house"
        assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in HOUSE_WINDOWS)
        tx, ty, tw, th = DOOR_TRIGGER
        assert ty == PORCH_ROW - 2 and th == 1 and tx <= HOUSE_DOOR[0] < tx + tw
        assert LINES[-1]["checkpoint"][0] < tx, "the house checkpoint stays off the door trigger"
        assert LINES[-1]["box"][0] + 1 + 4 < TOMAS[0] < HOUSE_DOOR[0] < CONCENTRATOR[0], \
            "four clear tiles between the house box and Hiroshi"
        assert all(tx + tw <= ex for ex, _, _, _ in layout.EXITS if ex > hx0), "the exit is past the door"
    assert layout.actor_count() <= MAX_SCENE_ACTORS
    grid_chain.check_scene_limits(layout.actor_count(), layout.trigger_count())


def _self_check() -> None:
    for layout in LAYOUTS.values():
        _self_check_layout(layout)
    assert [line["number"] for line in LINES] == list(range(1, LINE_COUNT + 1))
    grid_chain.check_chain_order(LINES, scene_order=SCENE_ORDER)
    # The cross-scene stage leaves 2A at its right edge and enters 2B at its left, on one row.
    ridge_end = RIDGE_ROUTES[-1][1][-1]
    saddle_start = SADDLE_ROUTES[0][1][0]
    assert RIDGE_ROUTES[-1][0] == SADDLE_ROUTES[0][0] == CROSS_LINE["number"]
    assert ridge_end == (MAP_W - 1, EDGE_PORTS[3]) and saddle_start == (0, EDGE_PORTS[3])
    assert CROSS_LINE["pole_scene"] == RIDGE and CROSS_LINE["box_scene"] == SADDLE
    assert {s for layout in LAYOUTS.values() for s in layout.STAGES} == set(range(1, LINE_COUNT + 1))
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == LINE_COUNT + 1
    ids = {SCENE_ID, BACKGROUND_ID, SADDLE_SCENE_ID, SADDLE_BACKGROUND_ID, TOMAS_SPRITE_ID,
           CONCENTRATOR_SPRITE_ID, WHIP_SPRITE_ID, WHIP_PALETTE_ID, TRANSFORMER_SPRITE_ID}
    assert len(ids) == 9, "resource ids collide"
    assert SCENE_ID == scenes.REGISTRY[RIDGE]["id"]
    assert SADDLE_SCENE_ID == resource_id(f"scene:{SADDLE}")
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "15", "16"})
    assert {line["live_var"] for line in LINES} == {
        VAR_FEEDER_LIVE, VAR_WEST_LIVE, VAR_MIDDLE_LIVE, VAR_EAST_LIVE, VAR_LINE_LIVE
    }
    # Hazard numbering is job-wide and contiguous (scene order).
    expected = {"gust": 1, "whip": 1, "span": 1, "cable": 1, "board": 1}
    for layout in LAYOUTS.values():
        assert layout.first_hazard == expected, layout.folder
        expected = {"gust": expected["gust"] + len(layout.GUST_LANES),
                    "whip": expected["whip"] + len(layout.WHIP_LANES),
                    "span": expected["span"] + len(layout.span_arc_lanes()),
                    "cable": expected["cable"] + len(layout.HIDDEN_CABLES),
                    "board": expected["board"] + len(layout.BOARDS)}


_self_check()
