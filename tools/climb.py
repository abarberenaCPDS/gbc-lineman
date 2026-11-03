"""Storm Climb - deterministic contract for Amara's repair job (job 1, two scenes).

Data only. Job 1 is two PLATFORM scenes (docs/LEVEL_REDESIGN.md §2, Job 1):
1A ``storm_climb`` (20x36, the shaft Abe loved, unchanged up to pole 5) and 1B
``climb_crest`` (56x18, the CREST section below: the end of carry 5, Amara's
house and transformer 5). Power flows bottom -> top: the base substation feeds
pole 1 on the bottom deck, and five lines climb the mountain in one continuous
grid chain (Abe, 2026-10-29: "the hero must connect 5 lines"; "lines must show
continuity"). Line 5 is the game's first cross-scene carry: its pole stands on
the L8 deck of 1A, its transformer on the crest's porch. Amara's door (the
checkpoint, var 0) only completes once all five are live.

    deck 0 (row 33)  substation -> pole 1 (left)
    L1 ledge         carry 1 up the middle
    L2 deck (27)     transformer 1 (left) ......... pole 2 (right)
    L3 ledge         carry 2
    L4 deck (21)     pole 3 (left) .......... transformer 2 (right)
    L5 ledge         carry 3
    L6 deck (15)     transformer 3 (left) ......... pole 4 (right)
    L7 ledge         carry 4
    L8 deck (9)      pole 5 (left) .......... transformer 4 (right)
    summit (5)       exit (top right) up to the crest; line 5's wire leaves there
    1B climb_crest   carry 5 across the crest to transformer 5, Amara's porch

Every deck has rock slabs at both ends (the poles and transformers stand on
them) and a one-way timber walk in the middle, so a full-height jump at a deck
end bonks the slab above: carries go up the middle ledges and their hazards.
The wire serpentine (``WIRE_ROUTES``) lights stage by stage as the chain repairs.

Transformers are background art, not actors (``TRANSFORMERS``): GB Studio keeps
actors active ~6 rows above and ~8 rows below the screen and every active
actor uses OAM even off screen, so ten 16x32 pole/box sprites plus hazards in a
36-row map overflow the 40-sprite OAM. The background transformer's bushing
tile sits in its stage's wire slot and lights with the wire. A culling thread
(``CULL_*``, make_climb_scene) deactivates actors outside the camera window.

Lines are global, actors are local (spec §3): each line names its
``pole_scene`` / ``box_scene``; ``ROUTE_SCENES`` (test_routes.py) gives both
scenes as route data.

Units are 8x8-pixel tiles. Actor positions are the tile the actor stands in
(feet row). Collision bytes follow GB Studio PLATFORM semantics: solid=0x0F,
top/one-way=0x01, empty=0x00. Cracked boards and hidden cables are placed by
``hazards.py`` (its ``storm_climb`` keys).
"""

from __future__ import annotations

import uuid as _uuid

import shaft
import transformer_art
# The shaft template (shaft.py) owns the deck geometry, collision bytes and the
# culling thread; these names are re-exported unchanged.
from shaft import (COL_EMPTY, COL_SOLID, COL_TOP, DECK0_ROW, DECK_ROWS, DECK_WALK, LEDGE_ROWS,  # noqa: F401
                   SLAB_LEFT, SLAB_RIGHT, CAMERA_ROWS, CAMERA_DEADZONE_ROWS, CULL_ABOVE, CULL_BELOW,
                   CULL_WAIT_FRAMES, OAM_LIMIT, HERO_OBJ, HERO_COLUMNS, VAR_CULL_X, VAR_CULL_Y,
                   VAR_CULL_CAM, VAR_CULL_TOP)

TILE = 8
MAP_W, MAP_H = shaft.MAP_W, shaft.MAP_H

# Rows 0-1 sit under the 16px HUD when the camera is at the top.
HUD_ROWS = 2
MAX_SCENE_ACTORS = 20

# ---------------------------------------------------------------------------
# Mountain route, bottom to summit. Rises are three rows (one short A tap)
# except the last, four-row leap to the summit.
# ---------------------------------------------------------------------------
# DECK0_ROW 33; DECK_ROWS 27/21/15/9 (L2, L4, L6, L8: slabs + middle walk);
# LEDGE_ROWS 30/24/18/12 (L1, L3, L5, L7); SLAB_LEFT, SLAB_RIGHT, DECK_WALK: shaft.py.
SUMMIT_ROW = 5

# Platforms are (row, x_start, x_end), inclusive one-way surfaces.
PLATFORMS = [
    (DECK0_ROW, 0, 18),
    (30, 7, 13),
    (27, *DECK_WALK),
    (24, 6, 12),
    (21, *DECK_WALK),
    (18, 7, 13),
    (15, *DECK_WALK),
    (12, 6, 12),
    (9, *DECK_WALK),
    (SUMMIT_ROW, 7, 16),
]
LEDGES = [platform for platform in PLATFORMS if platform[0] in LEDGE_ROWS]

# (x0, x1, row0, row1) inclusive solid rectangles.
SOLID_BLOCKS = [
    (0, MAP_W - 1, 34, 35),        # valley bedrock
    (0, 0, 0, 29),                 # left cliff wall (open at the street exit, rows 30-32)
    (MAP_W - 1, MAP_W - 1, 0, 33),  # right cliff wall
]
SOLID_BLOCKS += shaft.deck_solid_blocks(DECK_ROWS)

# The route the hero climbs, bottom to summit: (surface row, x0, x1).
ROUTE = [
    (DECK0_ROW, 0, 18), (30, 7, 13), (27, 1, 18), (24, 6, 12), (21, 1, 18),
    (18, 7, 13), (15, 1, 18), (12, 6, 12), (9, 1, 18), (SUMMIT_ROW, 7, 16),
]

# The base substation and player begin on the bottom deck. START is the empty
# tile the player stands in (feet row). Kept at (2, 32): the service opening
# and tickets switch into this tile.
START = (2, 32)
SUBSTATION = {"x": 1, "y": 32}         # background art, x1-3 rows 30-32
SUBSTATION_TILES = (1, 3, 30, 32)      # (x0, x1, row0, row1)
# Walking off the bottom deck's left edge returns to the service opening.
# (x, y, width, height) in tiles: column 0 over the 24px hero's rows 30-32.
STREET_EXIT = (0, 30, 1, 3)

# The summit exit (top right, rows 2-4) leads up to the crest (scene_links).
# Amara, her house, door and transformer 5 moved there (CREST section).
CLIMB_SCENE = "storm_climb"
CREST_SCENE = "climb_crest"
SCENE_ORDER = (CLIMB_SCENE, CREST_SCENE)
SUMMIT_EXIT = (17, 2, 1, 3)            # (x, y, w, h): to climb_crest (3, 8), ungated
SUMMIT_ARRIVAL = (14, 4)               # back from the crest: on the summit timber, facing left

# ---------------------------------------------------------------------------
# The grid chain: lines upstream (bottom) first. "pole" is the pole actor's
# feet tile (its Snapped+Cable state is the pickup); "box" the feet tile of the
# background transformer the cable plugs into; "reach" the B zone of the box
# (two box columns plus the walk side); "checkpoint" the respawn once repaired.
# Var 7 keeps its meaning: Amara's line (now the fifth) is live.
# ---------------------------------------------------------------------------
# Line 5 ("summit") is the cross-scene carry: pole on 1A's L8 deck, transformer 5
# and its checkpoint on the crest porch (box_scene; the checkpoint follows it).
LINES = [
    {"key": "base", "pole": (5, 32), "box": (2, 26), "reach": (2, 24, 4, 3),
     "checkpoint": (4, 26), "live_var": "40", "pole_scene": CLIMB_SCENE, "box_scene": CLIMB_SCENE},
    {"key": "lower", "pole": (16, 26), "box": (16, 20), "reach": (13, 18, 5, 3),
     "checkpoint": (14, 20), "live_var": "41", "pole_scene": CLIMB_SCENE, "box_scene": CLIMB_SCENE},
    {"key": "middle", "pole": (2, 20), "box": (2, 14), "reach": (2, 12, 4, 3),
     "checkpoint": (4, 14), "live_var": "42", "pole_scene": CLIMB_SCENE, "box_scene": CLIMB_SCENE},
    {"key": "upper", "pole": (16, 14), "box": (17, 8), "reach": (14, 6, 5, 3),
     "checkpoint": (15, 8), "live_var": "43", "pole_scene": CLIMB_SCENE, "box_scene": CLIMB_SCENE},
    {"key": "summit", "pole": (2, 8), "box": (39, 11), "reach": (36, 9, 5, 3),
     "checkpoint": (41, 11), "live_var": "7", "pole_scene": CLIMB_SCENE, "box_scene": CREST_SCENE},
]
for _number, _line in enumerate(LINES, start=1):
    _line["number"] = _number          # also the value of VAR_CARRYING_CABLE while carrying it
    _line["box_kind"] = "transformer"
LINE_COUNT = len(LINES)


def poles_in(scene: str) -> list[dict]:
    """Lines whose pole stands in ``scene``."""
    return [line for line in LINES if line["pole_scene"] == scene]


def boxes_in(scene: str) -> list[dict]:
    """Lines whose transformer (and checkpoint) stands in ``scene``."""
    return [line for line in LINES if line["box_scene"] == scene]

# Background transformers: the shared job transformer (transformer_art.py, 16x24,
# two columns, three rows) standing on the box tile. The top row is in the
# stage's wire slot (cap, bushing and lid light with the wire); the can and post
# rows are in the hardware slot.
TRANSFORMER_W, TRANSFORMER_H = transformer_art.W, transformer_art.H
TRANSFORMERS = [line["box"] for line in boxes_in(CLIMB_SCENE)]       # 1A's background transformers


def transformer_tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware-slot tiles) of a background transformer."""
    return transformer_art.tiles(box)


# ---------------------------------------------------------------------------
# Variables (project-global). 6, 7, 15 and 27 are shared with the other jobs;
# 40-48 are climb-only. Job 1 resets them (and var 0, Amara's door) once, when
# its work order starts the job (grid_chain.job_reset_events), not on every entry.
# ---------------------------------------------------------------------------
VAR_CARRYING_CABLE = "6"
VAR_LINE_LIVE = "7"        # line 5, Amara's line
VAR_NEAR = "27"
NEAR_VARIABLE = (VAR_NEAR, "Chain Near", "var_chain_near")
VAR_BASE_LIVE = "40"
VAR_LOWER_LIVE = "41"
VAR_MIDDLE_LIVE = "42"
VAR_UPPER_LIVE = "43"
VAR_CHAIN_LIVE = "44"      # how many leading lines are repaired (0-5): how far power climbs
VAR_LINES_LIVE = "45"      # HUD count of repaired lines (0-5)
# VAR_CULL_X/Y/CAM/TOP (46-49): the culling thread's scratch variables (shaft.py).
VARIABLES = [
    (VAR_BASE_LIVE, "Climb Base Live", "var_climb_base_live"),
    (VAR_LOWER_LIVE, "Climb Lower Live", "var_climb_lower_live"),
    (VAR_MIDDLE_LIVE, "Climb Middle Live", "var_climb_middle_live"),
    (VAR_UPPER_LIVE, "Climb Upper Live", "var_climb_upper_live"),
    (VAR_CHAIN_LIVE, "Climb Chain Live", "var_climb_chain_live"),
    (VAR_LINES_LIVE, "Climb Lines Live", "var_climb_lines_live"),
    (VAR_CULL_X, "Climb Cull X", "var_climb_cull_x"),
    (VAR_CULL_Y, "Climb Cull Y", "var_climb_cull_y"),
    (VAR_CULL_CAM, "Climb Cull Camera", "var_climb_cull_cam"),
    (VAR_CULL_TOP, "Climb Cull Top", "var_climb_cull_top"),
]
HUD_TEXT = f"LINE %D1${VAR_LINES_LIVE}$/{LINE_COUNT} HOME %D1$00$/1"

# Grid sprites share OBJ palette slot 2 (kept assigned; the transformers are now
# background art).
GRID_SPRITE_PALETTE_SLOT = 2

# ---------------------------------------------------------------------------
# Wires (background art). Stages 1-3 live in BG slot 5, stages 4-5 in slot 6;
# each stage owns one colour index in its slot, swapped dead -> live by the
# chain palettes. Routes are polylines of tile cells; a pole's top is (x, y-3),
# a transformer's top is its stage-slot row (x, y-2).
# ---------------------------------------------------------------------------
LINE_BG_SLOT = 5
LINE_BG_SLOT_2 = 6
LINE_COLOR_INDEX = 1
METAL_DEAD = ["17232E", "3D5364", "7791A3", "C7DCE1"]
METAL_LIVE = ["17232E", "38C8D8", "7791A3", "C7DCE1"]
# The climb's wire slots use the night sky as index 0, so wire tiles blend
# into the sky around them (the other jobs keep METAL_DEAD).
WIRE_SLOT_DEAD = ["0B101E", *METAL_DEAD[1:]]
WIRE_DEAD = METAL_DEAD[LINE_COLOR_INDEX]
WIRE_LIVE = METAL_LIVE[LINE_COLOR_INDEX]
STAGE_COLOR_INDEX = [1, 3, 2, 1, 3]    # chain stage -> colour index within its slot
# Stage 5 crosses the scene edge on this row in both scenes (spec §3 rule 5).
EDGE_PORT_ROW = 3
WIRE_ROUTES = [
    # stage 1: substation -> pole 1 -> up to transformer 1 -> across L2 to pole 2
    (1, [(2, 29), (5, 29), (5, 24), (2, 24)]),
    (1, [(2, 24), (2, 23), (16, 23)]),
    # stage 2: pole 2 -> right riser -> transformer 2 -> across L4 to pole 3
    (2, [(16, 23), (18, 23), (18, 18), (16, 18)]),
    (2, [(16, 18), (16, 17), (2, 17)]),
    # stage 3: pole 3 -> left riser -> transformer 3 -> across L6 to pole 4
    (3, [(2, 17), (1, 17), (1, 12), (2, 12)]),
    (3, [(2, 12), (2, 11), (16, 11)]),
    # stage 4: pole 4 -> up past the slab -> transformer 4 -> across L8 to pole 5
    (4, [(16, 11), (16, 6), (17, 6)]),
    (4, [(16, 6), (2, 6), (2, 5)]),
    # stage 5: pole 5 -> up over the summit -> out of the top right toward the crest
    # (EDGE_PORT_ROW; CREST_WIRE_ROUTES picks it up at the crest's left edge)
    (5, [(2, 5), (2, EDGE_PORT_ROW), (MAP_W - 2, EDGE_PORT_ROW)]),
]


def stage_slot(stage: int) -> int:
    return LINE_BG_SLOT if stage <= 3 else LINE_BG_SLOT_2


def chain_palettes() -> dict[int, dict[int, list[str]]]:
    """{stages_live: {slot: colours}} (grid_chain.chain_palettes, inlined to avoid a cycle)."""
    out = {}
    for live in range(LINE_COUNT + 1):
        slots = {}
        for slot, stages in ((LINE_BG_SLOT, range(1, 4)), (LINE_BG_SLOT_2, range(4, LINE_COUNT + 1))):
            colours = list(WIRE_SLOT_DEAD)
            for stage in stages:
                colours[STAGE_COLOR_INDEX[stage - 1]] = WIRE_LIVE if stage <= live else WIRE_DEAD
            slots[slot] = colours
        out[live] = slots
    return out


CHAIN_PALETTES = chain_palettes()

# Background hardware slot (transformer cans, substation): sky, light, grey, dark
# (the transformer sprite's look).
HARDWARE_BG_SLOT = 4
HARDWARE_COLORS = ["0B101E", "C7DCE1", "7791A3", "142332"]

# ---------------------------------------------------------------------------
# Hazards. Lanes are (row, x0, x1) on the chest row of the surface they cross
# (surface row - 2). Boards and hidden cables live in hazards.py.
# ---------------------------------------------------------------------------
# Timed gusts: lane 0 is the original gust_01 actor, lane 1 a second gust; the
# six remaining trigger resources keep their stable IDs as inert markers in the
# sky above the summit (row 0, out of play), ordered after every other trigger.
GUST_LANES = [
    (16, 8, 10),   # L5 ledge: carry 3
    (7, 8, 10),    # L8 walk: before pole 5 and on the final carry
    (0, 1, 3), (0, 4, 6), (0, 7, 9), (0, 10, 12), (0, 13, 15), (0, 16, 18),
]
TIMED_GUST_LANE_INDICES = (0, 1)
INERT_GUST_LANE_INDICES = tuple(i for i in range(len(GUST_LANES)) if i not in TIMED_GUST_LANE_INDICES)
# 0.18 (Abe: "can even make it a bit harder"): 0.8 s of warning (was 0.9), a
# slightly longer burst and a shorter rest (was 54/20/90). Wind Ridge is 48/22/70.
GUST_WARNING_FRAMES = 50
GUST_ACTIVE_FRAMES = 22
GUST_REST_FRAMES = 80

# Fallen span on the L4 walk: dark until power reaches transformer 2.
FALLEN_SPANS = [{"live_after": 2, "arcs": [(19, 7, 8)], "delays": [0]}]

# Whipping cut cables hang from the deck above and swing across a ledge.
# Placed with their 16x32 canvas bottom on the ledge's standing row (lane + 1).
WHIP_LANES = [(22, 9, 10), (10, 8, 9)]   # L3 ledge (carry 2), L7 ledge (carry 4)
WHIP_START_DELAYS = [0, 30]

# ---------------------------------------------------------------------------
# Culling thread (shaft.py): an actor is active only while the clamped camera
# top s = clamp(u, 0, 18) satisfies anchor - CULL_BELOW <= s <= anchor + CULL_ABOVE.
# ---------------------------------------------------------------------------
CAMERA_MAX_TOP = shaft.camera_max_top(MAP_H)


def cull_range(anchor_row: int) -> tuple[int, int]:
    """(lo, hi) of the unclamped camera estimate u for which the actor stays active."""
    return shaft.cull_range(anchor_row, CAMERA_MAX_TOP)


_GRID_NAMESPACE = _uuid.UUID("5b0e7f1c-3c41-5f0e-9a8b-6c1d2e3f4a5b")


def grid_resource_id(key: str) -> str:
    """Stable IDs for grid-repair resources shared by several generators."""
    return str(_uuid.uuid5(_GRID_NAMESPACE, "mr-cfe:grid:" + key))


def collision_grid() -> list[list[int]]:
    """Return the row-major PLATFORM collision bytes (MAP_H by MAP_W)."""
    return shaft.collision_grid(MAP_W, MAP_H, PLATFORMS, SOLID_BLOCKS)


def span_arc_lanes() -> list[tuple[int, int, int]]:
    return [lane for span in FALLEN_SPANS for lane in span["arcs"]]


def play_lanes() -> list[tuple[int, int, int]]:
    """Every hazard lane in play (timed gusts, span arcs, whips, hidden cables)."""
    import hazards
    lanes = [GUST_LANES[i] for i in TIMED_GUST_LANE_INDICES]
    lanes += span_arc_lanes() + WHIP_LANES + list(hazards.HIDDEN_CABLES["storm_climb"])
    return sorted(lanes)


def hazard_cells() -> set[tuple[int, int]]:
    """(row, x) cells of every lane in play."""
    return {(row, x) for row, x0, x1 in play_lanes() for x in range(x0, x1 + 1)}


def sprite_footprints() -> list[dict]:
    """Every actor as {name, x, anchor, cols, rows, obj, always}: the OBJ budget model.

    ``rows`` is the canvas height in tile rows above and including the anchor;
    ``obj`` the 8x16 OBJs it draws; ``always`` False for hazards that hide
    between cycles (gusts, arcs, hidden cables) and for boards, whose actor only
    shows while creaking (their idle plank is background art).
    """
    import hazards
    out = []
    for line in poles_in(CLIMB_SCENE):
        x, y = line["pole"]
        out.append({"name": f"pole:{line['key']}", "x": x, "anchor": y, "cols": 2, "rows": 4, "obj": 4,
                    "always": True})
    for i in TIMED_GUST_LANE_INDICES:
        row, x0, _ = GUST_LANES[i]
        out.append({"name": f"gust:{i + 1}", "x": x0, "anchor": row, "cols": 3, "rows": 2, "obj": 3,
                    "always": False})
    for number, (row, x0, _) in enumerate(span_arc_lanes(), start=1):
        out.append({"name": f"span-arc:{number}", "x": x0, "anchor": row, "cols": 2, "rows": 2, "obj": 2,
                    "always": False})
    for number, (row, x0, _) in enumerate(WHIP_LANES, start=1):
        out.append({"name": f"whip:{number}", "x": x0, "anchor": row + 1, "cols": 2, "rows": 4, "obj": 4,
                    "always": True})
    for number, (row, x0, _) in enumerate(hazards.HIDDEN_CABLES["storm_climb"], start=1):
        out.append({"name": f"hidden-cable:{number}", "x": x0, "anchor": row, "cols": 2, "rows": 2, "obj": 2,
                    "always": False})
    for number, (row, x0, _) in enumerate(hazards.BOARDS["storm_climb"], start=1):
        out.append({"name": f"board:{number}", "x": x0, "anchor": row, "cols": 3, "rows": 2, "obj": 3,
                    "always": False})
    return out


def scanline_load() -> dict[int, int]:
    """OBJ columns per tile row for every actor at once (the climb is exactly one screen wide)."""
    load: dict[int, int] = {}
    for sprite in sprite_footprints():
        for row in range(sprite["anchor"] - sprite["rows"] + 1, sprite["anchor"] + 1):
            load[row] = load.get(row, 0) + sprite["cols"]
    return load


def oam_load(camera_top: int, *, worst: bool) -> int:
    """OBJs drawn with the camera top at ``camera_top`` (thread-culled window, plus the hero).

    ``worst`` counts every timed hazard as visible at once plus one creaking
    board (the hero can stand on one at a time); otherwise only always-visible
    sprites, the hero and one creaking board.
    """
    total = HERO_OBJ
    boards = []
    for sprite in sprite_footprints():
        if not (sprite["anchor"] - CULL_BELOW <= camera_top <= sprite["anchor"] + CULL_ABOVE):
            continue
        if sprite["name"].startswith("board:"):
            boards.append(sprite["obj"])
        elif sprite["always"] or worst:
            total += sprite["obj"]
    return total + (max(boards) if boards else 0)


def actor_count() -> int:
    return len(sprite_footprints())


def _stands(grid: list[list[int]], x: int, y: int, width: int = 2) -> bool:
    """A 24px actor or 2-wide prop at feet tile (x, y): three clear rows, support below."""
    return all(grid[r][c] == COL_EMPTY for r in (y, y - 1, y - 2) for c in range(x, x + width)) and \
        all(grid[y + 1][c] in (COL_TOP, COL_SOLID) for c in range(x, x + width))


def _self_check() -> None:
    """Exhaustively check the geometry and fairness invariants at import time."""
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(row) == MAP_W for row in grid), "grid size"
    assert all(cell in (COL_EMPTY, COL_TOP, COL_SOLID) for row in grid for cell in row)

    # Route: each rise is a short tap (3) or the summit leap (4), with a
    # two-tile landing overlap on a one-way surface (jump through from below).
    for (low, lx0, lx1), (high, hx0, hx1) in zip(ROUTE, ROUTE[1:]):
        assert low - high in (3, 4), f"rise {low}->{high}"
        first = max(lx0, hx0, DECK_WALK[0] if high in DECK_ROWS else 0)
        last = min(lx1, hx1, DECK_WALK[1] if high in DECK_ROWS else MAP_W)
        assert last - first >= 1, f"no two-tile overlap {low}->{high}"
        assert all(grid[high][x] == COL_TOP for x in range(first, last + 1)), f"landing {high} not one-way"
    assert ROUTE[-1][0] - SUMMIT_ROW == 0 and ROUTE[-2][0] - SUMMIT_ROW == 4, "summit leap is four rows"
    # Slabs: a jump straight up from a deck end hits the slab of the deck above.
    for lower, upper in zip(DECK_ROWS, DECK_ROWS[1:]):
        for x in (*range(SLAB_LEFT[0], SLAB_LEFT[1] + 1), *range(SLAB_RIGHT[0], SLAB_RIGHT[1] + 1)):
            assert grid[upper + 1][x] == COL_SOLID and grid[lower][x] == COL_SOLID

    # Spawn, street exit and the summit exit up to the crest.
    sx, sy = START
    assert grid[sy][sx] == COL_EMPTY and grid[sy + 1][sx] == COL_TOP, "spawn"
    ex, ey, ew, eh = STREET_EXIT
    assert all(grid[y][ex] == COL_EMPTY for y in range(ey, ey + eh)), "street exit must be open"
    assert grid[ey + eh][ex] != COL_EMPTY, "street exit stands on the bottom deck"
    assert START[0] >= ex + ew + 1, "START keeps the hero clear of the street exit"
    x, y, w, h = SUMMIT_EXIT
    assert all(grid[r][x] == COL_EMPTY for r in range(y, y + h)), "summit exit must be open"
    assert grid[y + h][x - 1] == COL_TOP and y + h == SUMMIT_ROW, "the summit timber reaches the exit"
    assert y >= HUD_ROWS and x == MAP_W - 3
    assert _stands(grid, *SUMMIT_ARRIVAL) and SUMMIT_ARRIVAL[0] + 2 < x, "arrival clear of the exit"

    # Props: poles and transformers stand clear on support, away from hazard lanes.
    cells = hazard_cells()
    grids = {CLIMB_SCENE: grid, CREST_SCENE: crest_collision_grid()}
    crest_cells = crest_hazard_cells()
    for line in LINES:
        for point, field in ((line["pole"], "pole_scene"), (line["box"], "box_scene")):
            x, y = point
            near = cells if line[field] == CLIMB_SCENE else crest_cells
            assert _stands(grids[line[field]], x, y), f"prop {(x, y)} footing"
            assert all(abs(x - cx) > 2 or abs(y - cy) > 2 for cy, cx in near), f"prop {(x, y)} near hazard"
        box_grid = grids[line["box_scene"]]
        cx, cy = line["checkpoint"]
        assert box_grid[cy][cx] == COL_EMPTY and box_grid[cy + 1][cx] != COL_EMPTY, "checkpoint footing"
        rx, ry, rw, rh = line["reach"]
        bx, by = line["box"]
        assert rx <= bx and bx + 1 < rx + rw and ry == by - 2 and rh == 3, "reach covers the box"
    # Poles never stand under a platform: their 32px canvas stays in open air.
    for line in poles_in(CLIMB_SCENE):
        x, y = line["pole"]
        assert all(grid[y - 3][c] == COL_EMPTY for c in (x, x + 1)), "pole top clear"
    assert not poles_in(CREST_SCENE), "the crest has no pole: it ends carry 5"
    # Chain order: power climbs; each pole sits below (or level with) its box and
    # the next pole shares its box's deck. Line 5's box is up on the crest.
    for line, nxt in zip(LINES, LINES[1:]):
        assert line["box_scene"] == CLIMB_SCENE and nxt["pole_scene"] == CLIMB_SCENE
        assert line["pole"][1] > line["box"][1], "each line carries its cable upward"
        assert nxt["pole"][1] == line["box"][1], "the next pole stands on this box's deck"
    assert [line["box_scene"] for line in LINES] == [CLIMB_SCENE] * 4 + [CREST_SCENE]

    # Hazard lanes: open air, on a surface, two-tile ascent corridor kept.
    for row, x0, x1 in play_lanes():
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "lane in rock"
        assert all(grid[row + 2][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "lane floor"
    for row, x0, x1 in [GUST_LANES[i] for i in TIMED_GUST_LANE_INDICES]:
        assert x1 - x0 == 2, "gust lanes match the 24px gust sprite"
    for row, x0, x1 in (*span_arc_lanes(), *WHIP_LANES):
        assert x1 - x0 == 1, "arc and whip lanes are two tiles wide"
    for i in INERT_GUST_LANE_INDICES:
        row, x0, x1 = GUST_LANES[i]
        assert row < HUD_ROWS and all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1))
    for (low, lx0, lx1), (high, hx0, hx1) in zip(ROUTE, ROUTE[1:]):
        first, last = max(lx0, hx0), min(lx1, hx1)
        pairs = [x for x in range(first, last)
                 if all((r, c) not in cells for r in range(high - 2, low) for c in (x, x + 1))]
        assert pairs, f"no hazard-free two-tile ascent {low}->{high}"
    assert len(WHIP_START_DELAYS) == len(WHIP_LANES)

    # Wires: on the map, continuous, every stage used; transformers in place.
    for (_, a), (_, b) in zip(WIRE_ROUTES, WIRE_ROUTES[1:]):
        assert set(a) & set(b), "consecutive wire routes share a cell (continuity)"
    assert {stage for stage, _ in WIRE_ROUTES} == set(range(1, LINE_COUNT + 1))
    for stage, route in WIRE_ROUTES:
        assert all(0 <= x < MAP_W and HUD_ROWS <= y < MAP_H for x, y in route)
        for (x0, y0), (x1, y1) in zip(route, route[1:]):
            assert x0 == x1 or y0 == y1, "wire runs are orthogonal"
    for line in LINES:
        stage = line["number"]
        top, _ = transformer_tiles(line["box"])
        routes = WIRE_ROUTES if line["box_scene"] == CLIMB_SCENE else CREST_WIRE_ROUTES
        assert any(cell in route for s, route in routes if s == stage for cell in top), (
            f"stage {stage} wire reaches transformer {line['box']}")
        px, py = line["pole"]
        assert any((px, py - 3) in route for s, route in WIRE_ROUTES if s == stage), "wire reaches the pole top"
    # Stage 5 leaves 1A on the edge-port row at the right edge.
    assert WIRE_ROUTES[-1][1][-1] == (MAP_W - 2, EDGE_PORT_ROW)
    assert len({tuple(tuple(c) for _, c in sorted(p.items())) for p in CHAIN_PALETTES.values()}) == LINE_COUNT + 1

    # Budgets: actors, OBJs per scanline (hero two columns), OAM per camera window.
    assert actor_count() <= MAX_SCENE_ACTORS
    assert max(scanline_load().values()) + HERO_COLUMNS <= 10, "scanline sprite budget"
    for top in range(CAMERA_MAX_TOP + 1):
        assert oam_load(top, worst=False) <= OAM_LIMIT, f"always-visible OAM at camera row {top}"

    # Variables: new IDs only, one live variable per line.
    assert len({line["live_var"] for line in LINES}) == LINE_COUNT
    assert {v for v, _, _ in VARIABLES}.isdisjoint({"0", "4", "5", "6", "7", "15", "16", "27"})
    _crest_self_check()



# ===========================================================================
# CREST: 1B climb_crest (56x18), the end of carry 5 (docs/LEVEL_REDESIGN.md §2 1B)
#
# A short run scene above the summit exit. Run-scene rows: floor 15 (feet 14),
# rock B and the porch 12 (feet 11), catwalk C 9 (feet 8). The hero arrives on
# the ledge x0-6 (feet 8) under the back exit, drops to the floor, passes the
# fallen span (live once lines 1-4 are repaired, so it always arcs during carry
# 5) and a hidden cable, taps onto rock B under a gust, taps onto catwalk C
# (a cracked board on its landing, a whip at its end) and drops onto Amara's
# porch: transformer 5, Amara, her house and door, then the porch exit to work
# order 2 (gated on var 0, as the summit exit was).
# ===========================================================================
CREST_W, CREST_H = 56, 18
CREST_FLOOR_ROW = 15
CREST_PORCH_ROW = 12
CREST_CATWALK_ROW = 9
CREST_PLATFORMS = [
    (9, 1, 6),                         # arrival timber: jump back through from the step below
    (CREST_CATWALK_ROW, 25, 37),         # catwalk C, one-way timber
]
CREST_SOLID_BLOCKS = [
    (0, 0, HUD_ROWS, CREST_H - 1),                        # left cliff wall
    (CREST_W - 1, CREST_W - 1, HUD_ROWS, CREST_H - 1),    # right cliff wall
    (0, 6, 12, 14),                                       # recovery step below the arrival timber
    (0, CREST_W - 1, CREST_FLOOR_ROW, CREST_H - 1),       # floor and bedrock
    (20, 24, CREST_PORCH_ROW, 14),                        # rock B
    (38, CREST_W - 1, CREST_PORCH_ROW, 14),               # Amara's porch
]
CREST_START = (3, 8)                   # upstream entry "S" (from 1A's summit exit) and respawn fallback
CREST_BACK_EXIT = (1, 6, 1, 3)         # back down to 1A, landing on SUMMIT_ARRIVAL
CREST_PORCH_EXIT = (54, 9, 1, 3)       # on to work order 2 once Amara's door is reached (var 0)
CREST_EXIT_NUDGE_TILES = 3             # refused: step back three tiles, then explain (ROM 147c23be)
CREST_AMARA = (45, 11)
CREST_HOUSE_RECT = (46, 49, 5, 11)     # (x0, x1, row0, row1) background house at porch height
CREST_DOOR = (47, 11)                  # door tile: Amara's checkpoint (var 0)
CREST_WINDOW_TILES = ((46, 8), (49, 8))
CREST_DOOR_RECT = (CREST_DOOR[0], CREST_DOOR[1] - 2, 2, 3)   # arrival trigger at the door

# Hazards (boards and the hidden cable: hazards.py's climb_crest keys). Lanes are
# (chest row, x0, x1) as in 1A. 1B pushes a little harder than the shaft: the
# gust rests less between bursts (Abe: keep 1A, the crest may be harder).
CREST_GUST_LANES = [(10, 21, 23)]       # on rock B, guarding the tap onto catwalk C
CREST_GUST_TIMINGS = (GUST_WARNING_FRAMES, GUST_ACTIVE_FRAMES, 70)
CREST_WHIP_LANES = [(7, 33, 34)]        # at catwalk C's end, hanging from line 5's wire
CREST_WHIP_START_DELAYS = [20]
# R8 pilot: the fallen span goes live after lines 1-4, preserving the carry-5
# challenge; its crest-specific chain makes it stay safe once line 5 is repaired.
CREST_FALLEN_SPANS = [{"live_after": 4, "arcs": [(13, 11, 12)], "delays": [0]}]

# Stage 5's wire enters at the left edge on the edge-port row, runs over the
# crest (the whip hangs below it) to transformer 5's top tile, then to the roof.
CREST_WIRE_ROUTES = [
    (5, [(1, EDGE_PORT_ROW), (39, EDGE_PORT_ROW), (39, 9)]),
    (5, [(39, EDGE_PORT_ROW), (47, EDGE_PORT_ROW), (47, 4)]),
]
CREST_TRANSFORMERS = [line["box"] for line in boxes_in(CREST_SCENE)]


def crest_collision_grid() -> list[list[int]]:
    """Row-major PLATFORM collision bytes of the crest (CREST_H by CREST_W)."""
    return shaft.collision_grid(CREST_W, CREST_H, CREST_PLATFORMS, CREST_SOLID_BLOCKS)


def crest_span_arc_lanes() -> list[tuple[int, int, int]]:
    return [lane for span in CREST_FALLEN_SPANS for lane in span["arcs"]]


def crest_play_lanes() -> list[tuple[int, int, int]]:
    """Every crest hazard lane (gust, span arc, whip, hidden cable)."""
    import hazards
    _, cables, _ = hazards.placement(CREST_SCENE, redesign=True)
    return sorted(CREST_GUST_LANES + crest_span_arc_lanes() + CREST_WHIP_LANES + cables)


def crest_hazard_cells() -> set[tuple[int, int]]:
    return {(row, x) for row, x0, x1 in crest_play_lanes() for x in range(x0, x1 + 1)}


def crest_sprite_footprints() -> list[dict]:
    """The crest's actors in the climb's OBJ budget model (sprite_footprints)."""
    import hazards
    boards, cables, _ = hazards.placement(CREST_SCENE, redesign=True)
    x, y = CREST_AMARA
    out = [{"name": "amara", "x": x, "anchor": y, "cols": 2, "rows": 4, "obj": 4, "always": True}]
    out += [{"name": "gust", "x": x0, "anchor": row, "cols": 3, "rows": 2, "obj": 3, "always": False}
            for row, x0, _ in CREST_GUST_LANES]
    out += [{"name": "span-arc", "x": x0, "anchor": row, "cols": 2, "rows": 2, "obj": 2, "always": False}
            for row, x0, _ in crest_span_arc_lanes()]
    out += [{"name": "whip", "x": x0, "anchor": row + 1, "cols": 2, "rows": 4, "obj": 4, "always": True}
            for row, x0, _ in CREST_WHIP_LANES]
    out += [{"name": "hidden-cable", "x": x0, "anchor": row, "cols": 2, "rows": 2, "obj": 2, "always": False}
            for row, x0, _ in cables]
    out += [{"name": "board", "x": x0, "anchor": row, "cols": 3, "rows": 2, "obj": 3, "always": True}
            for row, x0, _ in boards]
    return out


def crest_actor_count() -> int:
    return len(crest_sprite_footprints())


def crest_scanline_worst() -> int:
    """Worst OBJ columns on one tile row of any 20-column screen, hero (2) included."""
    best = 0
    for left in range(CREST_W - 20 + 1):
        for row in range(CREST_H):
            best = max(best, sum(s["cols"] for s in crest_sprite_footprints()
                                 if s["x"] < left + 20 and s["x"] + s["cols"] > left
                                 and s["anchor"] - s["rows"] + 1 <= row <= s["anchor"]))
    return best + HERO_COLUMNS


def _crest_self_check() -> None:
    grid = crest_collision_grid()
    assert len(grid) == CREST_H and all(len(row) == CREST_W for row in grid)
    assert _stands(grid, *CREST_START, width=1), "crest entry"
    for x, y, w, h in (CREST_BACK_EXIT, CREST_PORCH_EXIT):
        assert all(grid[r][x] == COL_EMPTY for r in range(y, y + h)) and grid[y + h][x] != COL_EMPTY
    assert CREST_START[0] >= CREST_BACK_EXIT[0] + 2, "the entry keeps clear of the back exit"
    assert _stands(grid, *CREST_AMARA), "Amara stands on the porch"
    assert _stands(grid, *CREST_DOOR, width=1), "the door stands on the porch"
    hx0, hx1, hy0, hy1 = CREST_HOUSE_RECT
    assert hx0 <= CREST_DOOR[0] < hx1 and hy1 == CREST_DOOR[1] and grid[hy1 + 1][hx0] == COL_SOLID
    assert all(hx0 <= x <= hx1 and hy0 <= y <= hy1 for x, y in CREST_WINDOW_TILES)
    assert all(grid[y][x] == COL_EMPTY for x in range(hx0, hx1 + 1) for y in range(hy0, hy1 + 1))
    nx = CREST_PORCH_EXIT[0] - CREST_EXIT_NUDGE_TILES
    assert _stands(grid, nx, CREST_DOOR[1], width=1) and nx + 2 < CREST_PORCH_EXIT[0]
    for row, x0, x1 in crest_play_lanes():
        assert all(grid[row][x] == COL_EMPTY for x in range(x0, x1 + 1)), "crest lane in rock"
        assert all(grid[row + 2][x] in (COL_SOLID, COL_TOP) for x in range(x0, x1 + 1)), "crest lane floor"
    assert all(x1 - x0 == 2 for _, x0, x1 in CREST_GUST_LANES)
    assert all(x1 - x0 == 1 for _, x0, x1 in (*CREST_WHIP_LANES, *crest_span_arc_lanes()))
    assert len(CREST_WHIP_START_DELAYS) == len(CREST_WHIP_LANES)
    assert [span["live_after"] for span in CREST_FALLEN_SPANS] == [LINE_COUNT - 1], "live during carry 5"
    # Wires: continuous, orthogonal, below the HUD, entering on 1A's edge-port row.
    assert CREST_WIRE_ROUTES[0][1][0] == (1, EDGE_PORT_ROW)
    for (_, a), (_, b) in zip(CREST_WIRE_ROUTES, CREST_WIRE_ROUTES[1:]):
        assert set(a) & set(b)
    for stage, route in CREST_WIRE_ROUTES:
        assert stage == LINE_COUNT
        assert all(0 <= x < CREST_W and HUD_ROWS <= y < CREST_H for x, y in route)
        assert all(x0 == x1 or y0 == y1 for (x0, y0), (x1, y1) in zip(route, route[1:]))
    assert crest_actor_count() <= MAX_SCENE_ACTORS
    assert crest_scanline_worst() <= 10
    assert sum(s["obj"] for s in crest_sprite_footprints()) + HERO_OBJ <= OAM_LIMIT


# ---------------------------------------------------------------------------
# Route scenes (test_routes.py schema): both scenes of the job, from this contract.
# ---------------------------------------------------------------------------
def route_scenes() -> list[dict]:
    import grid_chain
    import hazards
    out = []
    boards, cables, _ = hazards.placement(CLIMB_SCENE, redesign=True)
    lanes = [("gust", *GUST_LANES[i]) for i in TIMED_GUST_LANE_INDICES]
    lanes += [("whip", *lane) for lane in WHIP_LANES] + [("arc", *lane) for lane in span_arc_lanes()]
    lanes += [("cable", *lane) for lane in cables]
    out.append({"folder": CLIMB_SCENE, "grid": collision_grid(), "start": START,
                "entries": [START, SUMMIT_ARRIVAL], "lines": grid_chain.scene_lines(LINES, CLIMB_SCENE),
                "lanes": lanes, "boards": boards, "exit": SUMMIT_EXIT, "exits": [STREET_EXIT, SUMMIT_EXIT],
                "npcs": [], "devices": [], "max_rise": 4, "culled": True})
    boards, cables, _ = hazards.placement(CREST_SCENE, redesign=True)
    lanes = [("gust", *lane) for lane in CREST_GUST_LANES] + [("whip", *lane) for lane in CREST_WHIP_LANES]
    lanes += [("arc", *lane) for lane in crest_span_arc_lanes()] + [("cable", *lane) for lane in cables]
    out.append({"folder": CREST_SCENE, "grid": crest_collision_grid(), "start": CREST_START,
                "entries": [CREST_START], "lines": grid_chain.scene_lines(LINES, CREST_SCENE),
                "lanes": lanes, "boards": boards, "exit": CREST_PORCH_EXIT,
                "exits": [CREST_BACK_EXIT, CREST_PORCH_EXIT], "npcs": [CREST_AMARA], "devices": []})
    return out


def __getattr__(name: str):
    # ROUTE_SCENES is built lazily: grid_chain and hazards import this module.
    if name == "ROUTE_SCENES":
        return route_scenes()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


_self_check()
