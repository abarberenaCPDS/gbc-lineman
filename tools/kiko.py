"""Pine Hollow - deterministic contract for Emil's repair job (job 4, the hardest).

Three PLATFORM scenes (docs/LEVEL_REDESIGN.md §2, Job 4), one grid chain of
five lines:

  4A ``pine_hollow`` (64x18, entry)  lines 1-2 and pole 3; line 3's cable leaves
                                     through the right-hand exit
  4B ``pine_ladder`` (20x36, up)     a climb-style shaft: box 3, line 4, pole 5;
                                     line 5's cable rises two decks and leaves
                                     through the top-right exit (culling thread)
  4C ``pine_rim`` (56x18)            box 5 on Emil's porch, Emil, the stove, his
                                     door and the storm-report exit

Lines are global, actors are local (grid_chain "Multi-scene jobs"): each line
names the scene of its pole and box. Repairing all five lights Emil's window
and switches on his electric stove so dinner can cook.

Every generator for this job reads this module: ``make_kiko_art.py`` (the three
backgrounds), ``make_kiko_sprites.py`` (Emil and the stove),
``make_kiko_scene.py`` (4A and 4C) and ``make_ladder_scene.py`` (4B). The live
arc reuses Priya's ``live_arc``; boxes are background transformers
(``transformer_art.py``). Cracked boards and hidden cables are placed by
``hazards.py`` (``placement(folder, redesign=True)``); links come from
``scene_links.py``.

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
import scene_links
import shaft
import transformer_art

TILE = 8
COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID

HUD_ROWS = 2
JOB = 4
MAX_SCENE_ACTORS = 20
MAX_SCENE_TRIGGERS = 30

HOLLOW, LADDER, RIM = "pine_hollow", "pine_ladder", "pine_rim"
SCENE_ORDER = (HOLLOW, LADDER, RIM)
SCENE_AXES = {HOLLOW: "x", LADDER: "up", RIM: "x"}

# ---------------------------------------------------------------------------
# Hazard timings: the hardest tier (spec §1). Warnings and rests are never
# longer than Priya's, active windows never shorter (test_kiko asserts it).
# ---------------------------------------------------------------------------
GUST_WARNING_FRAMES = 44
GUST_ACTIVE_FRAMES = 24
GUST_REST_FRAMES = 58
ARC_WARNING_FRAMES = 36     # span arcs: sparks 0.6 s
ARC_ACTIVE_FRAMES = 26
ARC_REST_FRAMES = 48
WHIP_SWAY_FRAMES = 36       # sparks and sways, safe: 0.6 s of warning
WHIP_SWING_FRAMES = 24
WHIP_HANG_FRAMES = 46
CABLE_TIMINGS = _hazards.CABLE_TIMINGS["kiko"]     # hidden cables: dark 120, warning 20, arc 26

ARC_SPRITE_ID = rosa.ARC_SPRITE_ID
WHIP_SPRITE_ID = ridge.WHIP_SPRITE_ID
WHIP_PALETTE_ID = ridge.WHIP_PALETTE_ID
WHIP_SPRITE_PALETTE_SLOT = ridge.WHIP_SPRITE_PALETTE_SLOT
WHIP_COLUMNS = ridge.WHIP_CANVAS[0] // TILE


# ---------------------------------------------------------------------------
# Scene geometry. Run scenes: floor row 15 (feet 14), step 12 (11), high 9 (8),
# top 6 (5). The shaft reuses the climb's decks (shaft.py).
# ---------------------------------------------------------------------------
class Scene:
    """One scene of the job: geometry, hazards and wires (rows top-down, inclusive ranges)."""

    def __init__(self, *, folder: str, size: tuple[int, int], solid_blocks: list, platforms: list,
                 start: tuple[int, int], gusts: list, gust_delays: list, whips: list, whip_delays: list,
                 spans: list, wire_routes: list, edge_ports: dict, shaft_scene: bool = False,
                 house: dict | None = None) -> None:
        self.folder = folder
        self.map_w, self.map_h = size
        self.solid_blocks = solid_blocks
        self.platforms = platforms
        self.start = start
        self.gust_lanes = gusts
        self.gust_delays = gust_delays
        self.whip_lanes = whips
        self.whip_delays = whip_delays
        self.spans = spans
        self.wire_routes = wire_routes
        self.edge_ports = edge_ports          # {stage: (x, y) map-edge cell of its wire}
        self.shaft = shaft_scene
        self.house = house
        self.boards, self.cables, self.cable_delays = _hazards.placement(folder, redesign=True)

    # -- data views -----------------------------------------------------------
    def collision_grid(self) -> list[list[int]]:
        return shaft.collision_grid(self.map_w, self.map_h, self.platforms, self.solid_blocks)

    def span_arc_lanes(self) -> list[tuple[int, int, int]]:
        return [lane for span in self.spans for lane in span["arcs"]]

    def hazard_lanes(self) -> list[tuple[int, int, int]]:
        """Lanes with background warning art (gusts, span arcs, whips), by row then column."""
        return sorted([*self.gust_lanes, *self.span_arc_lanes(), *self.whip_lanes], key=lambda lane: (lane[0], lane[1]))

    def all_lanes(self) -> list[tuple[int, int, int]]:
        return sorted([*self.hazard_lanes(), *self.cables], key=lambda lane: (lane[0], lane[1]))

    def kinded_lanes(self) -> list[tuple[str, int, int, int]]:
        """[(kind, chest row, x0, x1)] for test_routes."""
        return ([("gust", *lane) for lane in self.gust_lanes] + [("whip", *lane) for lane in self.whip_lanes]
                + [("arc", *lane) for lane in self.span_arc_lanes()] + [("cable", *lane) for lane in self.cables])

    def hazard_cells(self) -> set[tuple[int, int]]:
        return {(row, x) for row, x0, x1 in self.all_lanes() for x in range(x0, x1 + 1)}

    def board_cells(self) -> set[tuple[int, int]]:
        """(row, x) of each cracked board's standing row (its trigger)."""
        return {(row - 1, x) for row, x0, x1 in self.boards for x in range(x0, x1 + 1)}

    def lines(self) -> list[dict]:
        """This scene's parts of the job's lines (grid_chain.scene_lines)."""
        return grid_chain.scene_lines(LINES, self.folder)

    def pole_lines(self) -> list[dict]:
        return [line for line in LINES if line["pole_scene"] == self.folder]

    def box_lines(self) -> list[dict]:
        return [line for line in LINES if line["box_scene"] == self.folder]

    def stages(self) -> list[int]:
        return sorted({stage for stage, _ in self.wire_routes})

    def links(self) -> list:
        """Every link out of this scene (scene_links' redesign rows, table order)."""
        return scene_links.from_scene(self.folder, scene_links.table("redesign"))

    def entries(self) -> list[tuple[int, int]]:
        arrivals = [link.entry for link in scene_links.into_scene(self.folder, scene_links.table("redesign"))]
        return [self.start] + [tile for tile in arrivals if tile != self.start]

    def downstream_exit(self) -> tuple[int, int, int, int]:
        """The exit that carries the job forwards (the last link out of the scene)."""
        return self.links()[-1].rect

    def actor_count(self) -> int:
        npcs = 2 if self.house else 0           # Emil and the stove
        return (npcs + len(self.pole_lines()) + len(self.gust_lanes) + len(self.whip_lanes)
                + len(self.span_arc_lanes()) + len(self.cables) + len(self.boards))

    def trigger_count(self) -> int:
        door = 1 if self.house else 0
        return (len(self.links()) + door + len(self.boards) + len(self.box_lines()) + len(self.pole_lines()))

    def route_scene(self) -> dict:
        """test_routes.ROUTE_SCENES schema."""
        house = self.house or {}
        return {
            "folder": self.folder, "grid": self.collision_grid(), "start": self.start,
            "entries": self.entries(), "lines": self.lines(), "lanes": self.kinded_lanes(),
            "boards": list(self.boards), "exit": self.downstream_exit(),
            "exits": [link.rect for link in self.links()],
            "npcs": [house["npc"]] if house else [], "devices": [house["device"]] if house else [],
            "max_rise": 4 if self.shaft else 3, "culled": self.shaft,
        }


def _run_blocks(map_w: int, blocks: list) -> list[tuple[int, int, int, int]]:
    """Floor rows 15-17 plus a run scene's own rocks."""
    return [(0, map_w - 1, 15, 17), *blocks]


# --- 4A pine_hollow (64x18): the entry scene --------------------------------
MAP_W, MAP_H = 64, 18           # 4A keeps the old module names (tickets, test_scene_links)
GROUND_ROW = 15
SURFACE_LOW, SURFACE_STEP, SURFACE_HIGH = 15, 12, 9
CHEST_LOW, CHEST_HIGH = SURFACE_LOW - 2, SURFACE_HIGH - 2
ROCK_A = (4, 6, 12, 14)         # pole 1 (feeder)
MESA = (16, 22, 9, 14)          # T1, pole 2
ROCK_C = (36, 41, 12, 14)       # T2, pole 3
C1 = (9, 8, 15)                 # catwalk: rock A -> mesa (board on the landing, hidden cable)
D1 = (9, 43, 55)                # catwalk: rock C -> east (gust, whip)
F = (12, 57, 61)                # low catwalk to the ladder exit (board)
START = (2, 14)                 # entry from the work order card, facing right

HOLLOW_SCENE = Scene(
    folder=HOLLOW, size=(MAP_W, MAP_H),
    solid_blocks=_run_blocks(MAP_W, [(0, 0, 2, 14), (MAP_W - 1, MAP_W - 1, 2, 14), ROCK_A, MESA, ROCK_C]),
    platforms=[C1, D1, F], start=START,
    gusts=[(CHEST_HIGH, 44, 46), (CHEST_LOW, 47, 49)], gust_delays=[20, 0],
    whips=[(CHEST_LOW, 32, 33), (CHEST_HIGH, 51, 52)], whip_delays=[0, 45],
    spans=[
        {"columns": (25, 30), "row": CHEST_LOW + 1, "live_after": 1, "arcs": [(CHEST_LOW, 27, 28)], "delays": [0]},
        {"columns": (51, 56), "row": CHEST_LOW + 1, "live_after": 2, "arcs": [(CHEST_LOW, 53, 54)], "delays": [30]},
    ],
    # Overhead rows 3 and 2 alternate per stage, under the HUD; power enters through
    # the left wall and line 3 leaves through the right wall (edge cells are rock: a gap).
    wire_routes=[
        (1, [(0, 3), (5, 3), (5, 8)]),
        (1, [(5, 8), (5, 3), (18, 3), (18, 6)]),
        (1, [(18, 6), (18, 3), (22, 3), (22, 5)]),
        (2, [(22, 5), (22, 2), (37, 2), (37, 9)]),
        (2, [(37, 9), (37, 2), (41, 2), (41, 8)]),
        (3, [(41, 8), (41, 3), (MAP_W - 1, 3)]),
    ],
    edge_ports={3: (MAP_W - 1, 3)},
)

# --- 4B pine_ladder (20x36): the long climb out -------------------------------
LADDER_W, LADDER_H = shaft.MAP_W, shaft.MAP_H
LADDER_START = (2, 32)          # entry from the hollow, facing right
ARRIVAL_SHELF = (5, 7, 16)      # top shelf under the exit to the rim (hidden cable 2)
LADDER_SCENE = Scene(
    folder=LADDER, size=(LADDER_W, LADDER_H),
    solid_blocks=[
        (0, LADDER_W - 1, 34, 35),             # bedrock
        (0, 0, 0, 29), (0, 0, 33, 33),          # left wall, open at the hollow exit (rows 30-32)
        (LADDER_W - 1, LADDER_W - 1, 0, 33),    # right wall
        *shaft.deck_solid_blocks(shaft.DECK_ROWS),
    ],
    platforms=[(shaft.DECK0_ROW, 1, 18), (30, 7, 13), *[(row, *shaft.DECK_WALK) for row in shaft.DECK_ROWS],
               (24, 6, 12), (18, 7, 13), (12, 6, 12), ARRIVAL_SHELF],
    start=LADDER_START,
    gusts=[(16, 8, 10), (7, 8, 10)], gust_delays=[0, 30],
    whips=[(31, 12, 13), (22, 9, 10), (10, 8, 9)], whip_delays=[0, 40, 20],
    spans=[{"columns": (6, 11), "row": 20, "live_after": 3, "arcs": [(19, 7, 8)], "delays": [0]}],
    # Serpentine risers at the wall columns, as in the climb: where a riser crosses a
    # slab the wire passes behind the rock (a gap).
    wire_routes=[
        (3, [(0, 29), (1, 29), (1, 23), (2, 23), (2, 24)]),
        (3, [(2, 24), (2, 23), (16, 23)]),
        (4, [(16, 23), (18, 23), (18, 17), (1, 17), (1, 11), (2, 11), (2, 12)]),
        (4, [(2, 12), (2, 11), (16, 11)]),
        (5, [(16, 11), (18, 11), (18, 2), (LADDER_W - 1, 2)]),
    ],
    edge_ports={3: (0, 29), 5: (LADDER_W - 1, 2)},
    shaft_scene=True,
)

# --- 4C pine_rim (56x18): the rim run to Emil's porch -------------------------
RIM_W, RIM_H = 56, 18
RIM_START = (3, 8)              # entry from the ladder, facing right
PORCH_ROW = 11                  # porch actors stand on row 11 (surface 12)
RIM_HOUSE = {
    "rect": (47, 50, 5, PORCH_ROW),            # (x0, x1, row0, row1) background house
    "door": (48, PORCH_ROW),
    "windows": [(47, 8), (50, 8)],
    "door_trigger": (47, PORCH_ROW - 2, 3, 1),
    "npc": (47, PORCH_ROW),                     # Emil, left of his door
    "device": (49, PORCH_ROW),                  # the electric stove
}
RIM_SCENE = Scene(
    folder=RIM, size=(RIM_W, RIM_H),
    solid_blocks=_run_blocks(RIM_W, [(0, 0, 2, 14), (RIM_W - 1, RIM_W - 1, 2, 14), (0, 5, 9, 14),
                                     (21, 23, 12, 14),   # step out of the left pit (no softlock)
                                     (24, 28, 6, 14), (40, RIM_W - 1, 12, 14)]),
    platforms=[(9, 8, 22), (9, 29, 38)], start=RIM_START,
    gusts=[(7, 20, 22), (13, 34, 36)], gust_delays=[0, 25],
    whips=[(13, 18, 19), (7, 33, 34)], whip_delays=[10, 0],
    spans=[{"columns": (8, 14), "row": 14, "live_after": 4, "arcs": [(13, 11, 12)], "delays": [0]}],
    wire_routes=[
        (5, [(0, 2), (41, 2), (41, 9)]),
        (5, [(41, 9), (41, 2), (47, 2), (47, 4)]),
    ],
    edge_ports={5: (0, 2)},
    house=RIM_HOUSE,
)

SCENES = {HOLLOW: HOLLOW_SCENE, LADDER: LADDER_SCENE, RIM: RIM_SCENE}

# Legacy names for the porch (now in 4C).
HOUSE_RECT = RIM_HOUSE["rect"]
HOUSE_DOOR = RIM_HOUSE["door"]
HOUSE_WINDOWS = RIM_HOUSE["windows"]
DOOR_TRIGGER = RIM_HOUSE["door_trigger"]
KIKO = RIM_HOUSE["npc"]
STOVE = RIM_HOUSE["device"]

# ---------------------------------------------------------------------------
# Variables
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = climb.VAR_CARRYING_CABLE   # "6": survives the scene switch (rule 2)
VAR_LINE_LIVE = "12"       # house line (line 5)
VAR_HOME_POWERED = "13"    # Emil's checkpoint; moves respawn to the door, opens the report exit
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

# The grid chain, upstream first. "box" is the feet tile of the background
# transformer the cable plugs into; "checkpoint" the respawn once the line is
# repaired (in the box's scene); "reach" a box zone on the walk side where the
# tiles before the box are the shaft wall.
LINES = [
    {"key": "feeder", "pole": (5, 11), "box": (18, 8), "checkpoint": (20, 8),
     "pole_scene": HOLLOW, "box_scene": HOLLOW, "live_var": VAR_FEEDER_LIVE},
    {"key": "west", "pole": (22, 8), "box": (37, 11), "checkpoint": (39, 11),
     "pole_scene": HOLLOW, "box_scene": HOLLOW, "live_var": VAR_WEST_LIVE},
    {"key": "middle", "pole": (41, 11), "box": (2, 26), "reach": (2, 24, 4, 3), "checkpoint": (4, 26),
     "pole_scene": HOLLOW, "box_scene": LADDER, "live_var": VAR_MIDDLE_LIVE},
    {"key": "east", "pole": (16, 26), "box": (2, 14), "reach": (2, 12, 4, 3), "checkpoint": (4, 14),
     "pole_scene": LADDER, "box_scene": LADDER, "live_var": VAR_EAST_LIVE},
    {"key": "house", "pole": (16, 14), "box": (41, PORCH_ROW), "checkpoint": (43, PORCH_ROW),
     "pole_scene": LADDER, "box_scene": RIM, "live_var": VAR_LINE_LIVE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number      # also the value of VAR_CARRYING_CABLE while carrying it
    _line["box_kind"] = "transformer"
DAMAGED_POLE = LINES[0]["pole"]
HOUSE_POLE = LINES[-1]["pole"]
JUNCTION_BOX = LINES[-1]["box"]
FALLEN_SPANS = [span for scene in SCENES.values() for span in scene.spans]

# Legacy entry from Signal Hill (today's layout; scene_links owns the redesign's
# hand-off from 3C). Kept for the rosa generator until its job migrates.
HILL_EXIT = (rosa.MAP_W - 2, 9, 1, 3)
HILL_EXIT_GATE_VAR = rosa.VAR_HOME_POWERED     # "11"

ROUTE_SCENES = [scene.route_scene() for scene in SCENES.values()]

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

# Wires (background art), drawn in BG slots LINE_BG_SLOT (5, stages 1-3) and
# LINE_BG_SLOT_2 (6, stages 4-5). One set of chain palettes for all three scenes.
LINE_BG_SLOT = climb.LINE_BG_SLOT
LINE_BG_SLOT_2 = grid_chain.LINE_BG_SLOT_2
LINE_COLOR_INDEX = climb.LINE_COLOR_INDEX
METAL_DEAD = climb.METAL_DEAD
METAL_LIVE = climb.METAL_LIVE
WIRE_DEAD = METAL_DEAD[LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]        # chain stage -> metal colour index
STAGE_COUNT = len(STAGE_COLOR_INDEX)
CHAIN_PALETTES = grid_chain.chain_palettes(metal_dead=METAL_DEAD, wire_live=WIRE_LIVE,
                                           wire_dead=WIRE_DEAD, stage_color_index=STAGE_COLOR_INDEX)
WIRE_ROUTES = [route for scene in SCENES.values() for route in scene.wire_routes]

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
SCENE_IDS = {HOLLOW: SCENE_ID, LADDER: resource_id(f"scene:{LADDER}"), RIM: resource_id(f"scene:{RIM}")}
BACKGROUND_IDS = {HOLLOW: BACKGROUND_ID, LADDER: resource_id("background:pine-ladder"),
                  RIM: resource_id("background:pine-rim")}
KIKO_SPRITE_ID = resource_id("sprite:kiko")
STOVE_SPRITE_ID = resource_id("sprite:kiko_stove")
TRANSFORMER_SPRITE_ID = ridge.TRANSFORMER_SPRITE_ID
# The boxes are background transformers (transformer_art.py): no box actors, the
# wire palettes light them. The cans use the stone slot, its four colours mapped
# to the art's codes ('.' stays index 0, the dark behind the can).
BACKGROUND_BOXES = True
TRANSFORMER_BODY_SLOT = 1
TRANSFORMER_BODY_INDEX = {"L": 3, "G": 2, "D": 1}

# Culling thread (4B, shaft.py): the clamped camera top runs 0..18.
LADDER_CAMERA_MAX_TOP = shaft.camera_max_top(LADDER_H)


def collision_grid() -> list[list[int]]:
    """4A's PLATFORM collision bytes (the entry scene; see SCENES for the others)."""
    return HOLLOW_SCENE.collision_grid()


def hazard_lanes() -> list[tuple[int, int, int]]:
    return HOLLOW_SCENE.hazard_lanes()


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware tiles) of a background transformer (transformer_art)."""
    return transformer_art.tiles(box)


def _top(cell: tuple[int, int]) -> tuple[int, int]:
    """A pole's top tile (its 32px canvas)."""
    return (cell[0], cell[1] - 3)


def _box_top(cell: tuple[int, int]) -> tuple[int, int]:
    """A background transformer's hookup tile: the left one of its stage-slot top row."""
    return transformer_art.tiles(cell)[0][0]


def ladder_sprites() -> list[dict]:
    """4B's actors for the culling OAM model: anchor row, OBJ count, always visible or timed."""
    scene = LADDER_SCENE
    out = [{"name": f"pole:{line['key']}", "anchor": line["pole"][1], "obj": 4, "always": True}
           for line in scene.pole_lines()]
    out += [{"name": f"whip:{n}", "anchor": row + 1, "obj": 4, "always": True}
            for n, (row, _, _) in enumerate(scene.whip_lanes, start=1)]
    out += [{"name": f"gust:{n}", "anchor": row, "obj": 3, "always": False}
            for n, (row, _, _) in enumerate(scene.gust_lanes, start=1)]
    out += [{"name": f"span-arc:{n}", "anchor": row, "obj": 2, "always": False}
            for n, (row, _, _) in enumerate(scene.span_arc_lanes(), start=1)]
    out += [{"name": f"hidden-cable:{n}", "anchor": row, "obj": 2, "always": False}
            for n, (row, _, _) in enumerate(scene.cables, start=1)]
    out += [{"name": f"board:{n}", "anchor": row, "obj": 3, "always": False}
            for n, (row, _, _) in enumerate(scene.boards, start=1)]
    return out


def ladder_oam_load(camera_top: int, *, worst: bool = True) -> int:
    """OBJs drawn with the clamped camera top at ``camera_top`` under the culling thread, hero included.

    ``worst`` counts every timed hazard visible at once; boards are hidden until
    they creak and the hero stands on one at a time (climb.oam_load's model).
    """
    total = shaft.HERO_OBJ
    boards = []
    for sprite in ladder_sprites():
        lo, hi = shaft.cull_range(sprite["anchor"], LADDER_CAMERA_MAX_TOP)
        if not lo <= camera_top <= hi:
            continue
        if sprite["name"].startswith("board:"):
            boards.append(sprite["obj"])
        elif sprite["always"] or worst:
            total += sprite["obj"]
    return total + (max(boards) if boards else 0)


def _check_scene(scene: Scene) -> None:
    grid = scene.collision_grid()
    name = scene.folder
    assert len(grid) == scene.map_h and all(len(r) == scene.map_w for r in grid), f"{name} grid size"
    props = [scene.start]
    for line in scene.lines():
        props += [line[field] for field in ("pole", "box", "checkpoint") if field in line]
    if scene.house:
        props += [scene.house["npc"], scene.house["device"], scene.house["door"]]
    grid_chain.check_props(grid, props, scene.hazard_cells(), HUD_ROWS)
    assert not {(y, x) for x, y in props} & scene.board_cells(), f"{name}: prop on a cracked board"
    for row, x0, x1 in scene.all_lanes():
        assert row >= HUD_ROWS, "hazards under the HUD"
        assert all(grid[row][x] == COL_EMPTY and grid[row + 1][x] == COL_EMPTY for x in range(x0, x1 + 1)), \
            f"{name}: lane {row} {x0}-{x1} in rock"
        assert all(grid[row + 2][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), \
            f"{name}: lane {row} {x0}-{x1} has no floor"
    for row, x0, x1 in (*scene.span_arc_lanes(), *scene.whip_lanes, *scene.cables):
        assert x1 - x0 == 1, "arc, cable and whip lanes match the 16px width"
    for row, x0, x1 in scene.gust_lanes:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    if not scene.shaft:
        # Run whips hang from a bracket two and three rows above the chest row.
        for row, x0, x1 in scene.whip_lanes:
            assert row - 3 >= HUD_ROWS + 1
            assert all(grid[r][x] == COL_EMPTY for r in (row - 3, row - 2) for x in range(x0 - 1, x1 + 2))
    by_row: dict[int, list] = {}
    for lane in scene.all_lanes():
        by_row.setdefault(lane[0], []).append(lane)
    for row_lanes in by_row.values():
        for (_, _, a1), (_, b0, _) in zip(row_lanes, row_lanes[1:]):
            assert b0 - a1 >= 4, f"{name}: three standing tiles between hazards"
    for row, x0, x1 in scene.boards:
        assert all(grid[row][x] == COL_TOP for x in range(x0, x1 + 1)), f"{name}: board on timber"
        assert all(grid[row - 1][x] == COL_EMPTY for x in range(x0, x1 + 1))
    assert not scene.board_cells() & {(r + 1, x) for r, x0, x1 in scene.all_lanes() for x in range(x0, x1 + 1)}
    assert len(scene.gust_delays) == len(scene.gust_lanes) and len(scene.whip_delays) == len(scene.whip_lanes)
    # Spans lie on their line's carry and on a surface; the arcs inside their columns.
    for span in scene.spans:
        c0, c1 = span["columns"]
        assert all(c0 <= x0 and x1 <= c1 for _, x0, x1 in span["arcs"]) and len(span["delays"]) == len(span["arcs"])
        assert all(row + 1 == span["row"] for row, _, _ in span["arcs"])
        assert all(grid[span["row"] + 1][x] != COL_EMPTY and grid[span["row"]][x] == COL_EMPTY
                   for x in range(c0, c1 + 1)), f"{name}: span off its surface"
        assert span["live_after"] < LINE_COUNT
        line = LINES[span["live_after"]]          # the span lies on line live_after + 1's carry
        assert name in (line["pole_scene"], line["box_scene"]), f"{name}: span off its line's carry"
    # Background transformers: open air on their two columns, support under both.
    reserved: set[tuple[int, int]] = set()
    for line in scene.box_lines():
        bx, by = line["box"]
        cells = transformer_art.all_tiles(line["box"])
        assert all(grid[ty][tx] == COL_EMPTY and ty >= HUD_ROWS for tx, ty in cells), f"{line['key']} in rock"
        assert all(grid[by + 1][x] != COL_EMPTY for x in (bx, bx + 1)), f"{line['key']} footing"
        assert not reserved & set(cells)
        reserved |= set(cells)
        assert not {(y, x) for x, y in cells} & scene.hazard_cells(), "transformer over a lane"
        assert line["checkpoint"] not in cells and line["pole"] not in cells
        rx, ry, rw, rh = line.get("reach") or grid_chain.reach_rect(line["box"])
        assert rx <= bx and bx + 1 < rx + rw and ry + rh - 1 == by, "box zone covers the box's columns"
        assert all(0 < x < scene.map_w - 1 and grid[y][x] != COL_SOLID
                   for x in range(rx, rx + rw) for y in range(ry, ry + rh)), "box zone clear of rock"
        assert not {(y, x) for x in range(rx, rx + rw) for y in range(ry, ry + rh)} & scene.hazard_cells()
    # Wires: on the map, under the HUD, continuous, one stage per line here.
    grid_chain.check_wire_routes(scene.wire_routes, STAGE_COUNT, scene.map_w, HUD_ROWS, scene.map_h - 1,
                                 enters_left=scene.folder == HOLLOW, stages=scene.stages())
    for line in LINES:
        cells = {c for stage, route in scene.wire_routes if stage == line["number"] for c in route}
        if line["pole_scene"] == name:
            assert _top(line["pole"]) in cells, f"{line['key']} wire reaches its pole top"
        if line["box_scene"] == name:
            assert _box_top(line["box"]) in cells, f"{line['key']} wire reaches its transformer"
    for stage, (x, y) in scene.edge_ports.items():
        assert x in (0, scene.map_w - 1) and any((x, y) in route for s, route in scene.wire_routes if s == stage)
    # Links: exits are 1x3 edge triggers; the house and its door on the porch.
    assert all(rect[2:] == (1, 3) for rect in (link.rect for link in scene.links()))
    if scene.house:
        hx0, hx1, hy0, hy1 = scene.house["rect"]
        door = scene.house["door"]
        assert hx0 <= door[0] <= hx1 and hy1 == door[1], "door inside house"
        assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in scene.house["windows"])
        tx, ty, tw, th = scene.house["door_trigger"]
        assert ty == door[1] - 2 and th == 1 and tx <= door[0] < tx + tw
        assert all(line["checkpoint"][0] < tx for line in scene.box_lines())
    assert scene.actor_count() <= MAX_SCENE_ACTORS and scene.trigger_count() <= MAX_SCENE_TRIGGERS


def _self_check() -> None:
    for scene in SCENES.values():
        _check_scene(scene)
    grid_chain.check_chain_order(LINES, scene_order=SCENE_ORDER, axes=SCENE_AXES)
    assert all(line["pole_scene"] in SCENE_ORDER and line["box_scene"] in SCENE_ORDER for line in LINES)
    # Cross-scene carries leave through the edge their wire crosses (rule 5).
    for line in LINES:
        if line["pole_scene"] != line["box_scene"]:
            assert line["number"] in SCENES[line["pole_scene"]].edge_ports
            assert line["number"] in SCENES[line["box_scene"]].edge_ports
    assert len({tuple(tuple(v) for _, v in sorted(c.items())) for c in CHAIN_PALETTES.values()}) == STAGE_COUNT + 1
    ids = {*SCENE_IDS.values(), *BACKGROUND_IDS.values(), KIKO_SPRITE_ID, STOVE_SPRITE_ID}
    assert len(ids) == 8, "resource ids collide"
    assert {v for v, _, _ in VARIABLES}.isdisjoint({str(n) for n in range(12)})
    assert len({line["live_var"] for line in LINES}) == LINE_COUNT
    assert max(ladder_oam_load(top) for top in range(LADDER_CAMERA_MAX_TOP + 1)) <= shaft.OAM_LIMIT


_self_check()
