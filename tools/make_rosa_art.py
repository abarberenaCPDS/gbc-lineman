"""Generate the three Signal Hill job backgrounds from the ``rosa.py`` contract.

Scenes: 3A ``signal_hill`` (64x18, upper creek approach), 3B ``signal_gully``
(20x36, eroded banks and timber drops) and 3C ``signal_porch`` (40x18,
broken footbridges over the dry path to Priya's house).

The RGB image returned by :func:`make_background` is the artist-facing source;
the compiler-facing PNG is a grayscale index proxy that uses GB Studio's native
index thresholds. This generator owns only the three PNGs and their sidecars.

Both metal BG slots hold wire pixels and the transformers' stage rows only;
placards, whip crossarms and arc posts live in the stone slot. The boxes are
the shared background transformer (``transformer_art.py``): the top tile row in
its stage's wire slot, the can and post in the stone slot
(``rosa.TRANSFORMER_BODY_SLOT``). Cracked boards are drawn as cracked planks on
their timber; the board actor only shows while it creaks. A wire cell inside a
map-edge wall column is where the cable runs into the rock: it is not painted.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import opening
import rosa
import shaft_art
import transformer_art
from make_climb_scene import collision_rle

ROOT = Path(__file__).resolve().parent.parent
TILE = rosa.TILE
OUTPUTS = {folder: ROOT / f"assets/backgrounds/{folder}.png" for folder in rosa.SCENE_ORDER}
SIDECARS = {folder: Path(str(path) + ".gbsres") for folder, path in OUTPUTS.items()}
OUTPUT, SIDECAR = OUTPUTS[rosa.HILL], SIDECARS[rosa.HILL]
WIDTH, HEIGHT = rosa.MAP_W * TILE, rosa.MAP_H * TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
# Unique (slot, pattern) tiles before GB Studio's flip dedupe (CGB limit 384).
MAX_UNIQUE_TILES = 256

# BG palette families (opening.BG_PALETTES order). Slot 7 is the editor UI.
SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, WIRE_2 = range(7)
PALETTES[WIRE_2] = PALETTES[METAL][:]
LINE = climb.LINE_BG_SLOT
assert LINE == METAL, "wire slot must be the metal family"
assert rosa.WINDOW_BG_SLOT == WINDOW, "window slot must be the window family"
assert rosa.TRANSFORMER_BODY_SLOT == STONE, "transformer cans use the stone ramp"

# WP5: a signpost at every scene link ("the route continues here"), derived from scene_links.
MARKERS = {folder: shaft_art.exit_markers(folder, *rosa.size(folder)) for folder in rosa.SCENE_ORDER}
CLAIMED: dict[str, set[tuple[int, int]]] = {}

# Stars above the cable runs (pixel rows 16-27 only), run scenes and the gully.
STARS = [(24, 20), (64, 26), (120, 18), (176, 24), (226, 20), (262, 26), (330, 22), (410, 18), (470, 25)]
# Distant radio mast on the hill (3A), over the upper walk: below the stage-2
# wire (row 3), its foot behind the hill.
MAST_X = 22 * TILE + 4
MAST_TOP, MAST_BOTTOM = 34, 62


def size_px(folder: str) -> tuple[int, int]:
    width, height = rosa.size(folder)
    return width * TILE, height * TILE


def stage_slot(stage: int) -> int:
    return LINE if stage <= 3 else WIRE_2


# ---------------------------------------------------------------------------
# Derived cells per scene
# ---------------------------------------------------------------------------
@functools.lru_cache(maxsize=None)
def arc_post_tops(folder: str = rosa.HILL) -> tuple[tuple[int, int], ...]:
    """Downed-wire posts of the free live arc: one at each end, standing on the floor (two tiles tall)."""
    return tuple((tx, row) for row, x0, x1 in rosa.LAYOUTS[folder]["arcs"] for tx in (x0 - 1, x1 + 1))


@functools.lru_cache(maxsize=None)
def arc_post_tiles(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    return frozenset((tx, ty) for tx, top in arc_post_tops(folder) for ty in (top, top + 1))


@functools.lru_cache(maxsize=None)
def lane_cells(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    """(row, x) of every lane with a background placard."""
    return frozenset((row, x) for row, x0, x1 in rosa.hazard_lanes(folder) for x in range(x0, x1 + 1))


@functools.lru_cache(maxsize=None)
def bracket_cells(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    """(row, x) of each whip's crossarm: two rows over the whip, below the HUD, only in
    open air (a whip right under a deck or catwalk hangs from its timber instead)."""
    grid = rosa.collision_grid(folder)
    out = set()
    for row, x0, x1 in rosa.LAYOUTS[folder]["whips"]:
        columns = range(x0 - 1, x1 + 2)
        above = range(max(row - 3, rosa.HUD_ROWS), row)
        if any(grid[r][x] != rosa.COL_EMPTY for r in above for x in columns):
            continue
        out |= {(r, x) for r in (row - 3, row - 2) if r >= rosa.HUD_ROWS for x in columns}
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def placard_cells(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    return lane_cells(folder) | bracket_cells(folder)


PLACARD_CELLS = placard_cells(rosa.HILL)
LANE_CELLS = lane_cells(rosa.HILL)


@functools.lru_cache(maxsize=None)
def transformer_tiles(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    return frozenset(cell for line in rosa.box_lines(folder) for cell in transformer_art.all_tiles(line["box"]))


def _post_run(grid: list[list[int]], row: int, tx: int) -> list[tuple[int, int]]:
    """Tiles of a post under catwalk ``row`` at column ``tx`` down to the next surface."""
    out = []
    for ty in range(row + 1, len(grid)):
        if grid[ty][tx] != climb.COL_EMPTY:
            break
        out.append((tx, ty))
    return out


@functools.lru_cache(maxsize=None)
def post_tiles(folder: str = rosa.HILL) -> tuple[tuple[int, int], ...]:
    """Timber posts. Run scenes: under each catwalk's ends plus one inboard, down to
    the floor, clear of spans, hazard art and transformers. The gully: the shaft's
    short posts under each ledge end (shaft_art.post_tiles)."""
    grid = rosa.collision_grid(folder)
    blocked = {(x, y) for y, x in placard_cells(folder)} | set(transformer_tiles(folder)) | arc_post_tiles(folder)
    blocked |= {cell for cell in span_tiles(folder)}
    if rosa.LAYOUTS[folder]["vertical"]:
        lanes = rosa._hazard_cells(folder) | placard_cells(folder)
        posts = shaft_art.post_tiles(grid, rosa.LAYOUTS[folder]["ledges"], lanes, len(grid))
        return tuple(p for p in posts if p not in blocked and p not in wire_tiles(folder))
    spans = [s["columns"] for s in rosa.LAYOUTS[folder]["spans"]]
    out = []
    for row, x0, x1 in rosa.LAYOUTS[folder]["ledges"]:
        for x in (x0, x0 + 3, x1):
            if any(c0 <= x <= c1 for c0, c1 in spans):
                continue
            run = _post_run(grid, row, x)
            if any(tile in blocked for tile in run):
                continue
            if any(lrow > row and lx0 - 1 <= x <= lx1 + 1 for lrow, lx0, lx1 in rosa._all_hazard_lanes(folder)):
                continue          # no post right beside a lane below the catwalk
            out += run
    return tuple(out)


def _mask_pixels(draw, folder: str) -> frozenset[tuple[int, int]]:
    width, height = size_px(folder)
    mask = Image.new("1", (width + 2, height + 2), 0)
    draw(ImageDraw.Draw(mask))
    w = mask.width
    return frozenset((i % w, i // w) for i, v in enumerate(mask.get_flattened_data()) if v)


def _polyline_pixels(route, folder: str) -> frozenset[tuple[int, int]]:
    """2px-thick polyline through contract tile centres (inside the tile)."""
    pts = [(tx * TILE + 3, ty * TILE + 3) for tx, ty in route]

    def draw(d):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            d.line([(x + dx, y + dy) for x, y in pts], fill=1, width=1)
    return _mask_pixels(draw, folder)


def _span_pixels(span, folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    """The fallen span: a sagging wire on the feet row of its surface."""
    x0, x1 = span["columns"]
    y = (span["arcs"][0][0] + 1) * TILE
    pts = [(x, y + (3 if (x // 6) % 2 else 5)) for x in range(x0 * TILE + 1, (x1 + 1) * TILE - 1, 6)]
    pts.append(((x1 + 1) * TILE - 2, y + 4))

    def draw(d):
        d.line(pts, fill=1, width=2)
    return _mask_pixels(draw, folder)


@functools.lru_cache(maxsize=None)
def span_tiles(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    return frozenset((x // TILE, y // TILE) for span in rosa.LAYOUTS[folder]["spans"]
                     for x, y in _span_pixels(span, folder))


@functools.lru_cache(maxsize=None)
def stage_pixels(stage: int, folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    """Every pixel of ``folder`` that may carry the wire colour index of chain ``stage`` (1-based)."""
    out: set[tuple[int, int]] = set()
    for s, route in rosa.WIRE_ROUTES_BY_SCENE[folder]:
        if s == stage:
            out |= _polyline_pixels(route, folder)
    for span in rosa.LAYOUTS[folder]["spans"]:
        if span["live_after"] == stage:
            out |= _span_pixels(span, folder)
    # The transformer's cap, bushing, clamp, collar and lid light with its stage.
    line = rosa.LINES[stage - 1]
    if line["box_scene"] == folder:
        out |= transformer_art.stage_pixels(line["box"])
    return frozenset(out)


def stages(folder: str) -> list[int]:
    """The chain stages with pixels in ``folder`` (wire routes and spans)."""
    found = {stage for stage, _ in rosa.WIRE_ROUTES_BY_SCENE[folder]}
    found |= {span["live_after"] for span in rosa.LAYOUTS[folder]["spans"]}
    return sorted(found)


@functools.lru_cache(maxsize=None)
def wire_tiles(folder: str = rosa.HILL) -> frozenset[tuple[int, int]]:
    """(tx, ty) open-air tiles any wire route touches (not spans or transformer caps)."""
    grid = rosa.collision_grid(folder)
    out = set()
    for stage, route in rosa.WIRE_ROUTES_BY_SCENE[folder]:
        for x, y in _polyline_pixels(route, folder):
            tx, ty = x // TILE, y // TILE
            if ty < len(grid) and tx < len(grid[0]) and grid[ty][tx] == climb.COL_EMPTY:
                out.add((tx, ty))
    return frozenset(out)


def _edge_column(folder: str, tx: int) -> bool:
    return tx in (0, rosa.size(folder)[0] - 1)


# ---------------------------------------------------------------------------
# Palette map
# ---------------------------------------------------------------------------
def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int, y0: int, y1: int) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            slots[ty][tx] = slot


def _slots(grid: list[list[int]], folder: str = rosa.HILL) -> list[list[int]]:
    """Choose one palette family per tile, respecting the collision grid."""
    width, height = rosa.size(folder)
    slots = [[SKY] * width for _ in range(height)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = STONE
            elif cell == climb.COL_TOP:
                slots[ty][tx] = TIMBER

    posts = set(post_tiles(folder))
    for tx, ty in posts:
        slots[ty][tx] = TIMBER

    house: set[tuple[int, int]] = set()
    if folder == rosa.PORCH:
        # Priya's house: timber body on the porch, two windows, one door.
        x0, x1, y0, y1 = rosa.HOUSE_RECT
        house = {(tx, ty) for ty in range(y0, y1 + 1) for tx in range(x0, x1 + 1)}
        for tx, ty in house:
            if grid[ty][tx] != climb.COL_EMPTY:
                raise AssertionError(f"house overlaps collision at {tx},{ty}")
        _set_rect(slots, TIMBER, x0, x1, y0, y1)
        # Each window owns exactly one whole tile; no other tile uses this slot.
        for tx, ty in rosa.HOUSE_WINDOWS:
            slots[ty][tx] = WINDOW

    # Downed-wire posts: stone family, open air, never on a lane.
    for tx, ty in arc_post_tiles(folder):
        if (grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in lane_cells(folder)
                or (tx, ty) in transformer_tiles(folder)):
            raise AssertionError(f"arc post overlaps collision, a lane or a transformer at {tx},{ty}")
        slots[ty][tx] = STONE

    # Lanes get a stone hazard placard, whips a stone crossarm.
    for row, tx in sorted(placard_cells(folder)):
        if grid[row][tx] != climb.COL_EMPTY:
            raise AssertionError(f"{folder}: hazard placard overlaps collision at {tx},{row}")
        if (tx, row) in transformer_tiles(folder) or (tx, row) in posts:
            raise AssertionError(f"{folder}: hazard art overlaps a transformer or post at {tx},{row}")
        slots[row][tx] = STONE

    # Background transformers: the top row in the stage's wire slot, the can in stone.
    bodies = set()
    for line in rosa.box_lines(folder):
        top, body = transformer_art.tiles(line["box"])
        for tx, ty in top + body:
            if grid[ty][tx] != climb.COL_EMPTY or (tx, ty) in posts:
                raise AssertionError(f"transformer {line['key']} overlaps terrain at {tx},{ty}")
        for tx, ty in body:
            slots[ty][tx] = rosa.TRANSFORMER_BODY_SLOT
            bodies.add((tx, ty))
        for tx, ty in top:
            slots[ty][tx] = stage_slot(line["number"])

    # Wire tiles take the metal slot last; they may never hit collision (except where
    # the cable runs into an edge wall), a lane, the house, a post or a placard.
    for stage in stages(folder):
        for tx, ty in sorted({(x // TILE, y // TILE) for x, y in stage_pixels(stage, folder)}):
            if grid[ty][tx] != climb.COL_EMPTY:
                assert _edge_column(folder, tx), f"{folder}: wire tile {tx},{ty} inside collision"
                continue
            if ((ty, tx) in placard_cells(folder) or (tx, ty) in house or (tx, ty) in posts
                    or (tx, ty) in arc_post_tiles(folder) or (tx, ty) in bodies):
                raise AssertionError(f"{folder}: wire tile {tx},{ty} collides with other art")
            slots[ty][tx] = stage_slot(stage)

    CLAIMED[folder] = shaft_art.claim_markers(slots, grid, MARKERS[folder], TIMBER)
    assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
    return slots


# ---------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------
_Canvas = shaft_art.Canvas


def _hill_line(folder: str) -> list[tuple[int, int]]:
    width, _ = size_px(folder)
    return [(x, 63 + ((x // 24 * 7 + x // 96 * 3) % 5) * 4) for x in range(0, width + 1, 24)] + [(width, 70)]


def _draw_sky(c: _Canvas, folder: str) -> None:
    p = PALETTES[SKY]
    width, height = size_px(folder)
    vertical = rosa.LAYOUTS[folder]["vertical"]
    if not vertical:
        # Two night-family layers: a paler far ridge (rim-lit) and a dark hill mass in front,
        # so rock and timber still win wherever they overlap the sky tiles.
        far = [(x, 44 + (x // 32 * 5 + x // 128 * 3) % 4 * 4) for x in range(0, width + 1, 32)]
        c.polygon(SKY, far + [(width, height - 24), (0, height - 24)], p[1])
        c.line(SKY, far, p[2])
        line = _hill_line(folder)
        c.polygon(SKY, line + [(width, height - 24), (0, height - 24)], p[0])
        c.line(SKY, line, p[2])
    else:
        # Receding banks frame the spillway; keep contrast lower than the
        # rock edges and bridge lips in the foreground.
        west = [(0, 36), (31, 43), (64, 77), (52, 115), (38, 155), (18, 177), (0, 214)]
        east = [(width - 1, 58), (121, 69), (103, 102), (116, 138), (96, 166),
                (108, 197), (129, 226), (width - 1, 248)]
        c.polygon(SKY, west + [(0, 36)], p[1])
        c.polygon(SKY, east + [(width - 1, 58)], p[1])
    for x, y in STARS:
        if x < width:
            c.point(SKY, (x, y), p[2])
    # Priya's radio hill: lattice masts with lit beacons (below the stage-2 wire, feet behind the hill).
    if folder == rosa.HILL:
        shaft_art.mast(c, SKY, MAST_X, MAST_TOP, MAST_BOTTOM, p)
        shaft_art.mast(c, SKY, width - 15 * TILE, MAST_TOP + 6, MAST_BOTTOM + 8, p)
    elif folder == rosa.PORCH:
        shaft_art.mast(c, SKY, 17 * TILE + 4, MAST_TOP, MAST_BOTTOM + 6, p)
    else:
        shaft_art.mast(c, SKY, width - 5 * TILE - 4, 26, 118, p)


def _draw_creek(c: _Canvas, folder: str) -> None:
    """Distant runoff behind the route, using the quiet night ramp."""
    p = PALETTES[SKY]
    if folder == rosa.GULLY:
        path = [(106, 65), (82, 101), (86, 127), (67, 155), (57, 183), (68, 216),
                (101, 242), (151, 254)]
        bank = [(x + offset, y + 3) for (x, y), offset in zip(path, (4, 7, 9, 11, 11, 13, 15, 5))]
        c.polygon(SKY, path + bank[::-1], p[1])
        for x, y in ((82, 104), (67, 156), (59, 183), (89, 229), (121, 246)):
            c.line(SKY, [(x, y), (x + 5, y + 1)], p[2])
        return
    width, _ = size_px(folder)
    end = 32 if folder == rosa.PORCH else 54
    lip = [(0, 113), (24, 108), (56, 106), (88, 103),
           (121, 99), (width - end, 105)]
    c.polygon(SKY, lip + [(width - end, 119), (0, 119)], p[1])
    for x in range(15, width - end, 24):
        y = 111 + ((x // 24) % 3) * 2
        c.line(SKY, [(x, y), (x + 3, y)], p[2])
        c.line(SKY, [(x + 8, y + 3), (x + 12, y + 3)], p[0])


def _draw_rock(c: _Canvas, grid: list[list[int]]) -> None:
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != climb.COL_SOLID:
                continue
            ramp = PALETTES[STONE]
            x, y = tx * TILE, ty * TILE
            c.rect(STONE, (x, y, x + 7, y + 7), ramp[1])
            # Exposed rock gets a lit surface edge; the joint seams are diagonal.
            if ty == 0 or grid[ty - 1][tx] != climb.COL_SOLID:
                c.line(STONE, [(x, y), (x + 7, y)], ramp[3])
            if (tx + ty) % 3 == 0:
                c.polygon(STONE, [(x, y + 2), (x + 3, y), (x + 4, y + 2), (x + 2, y + 4)], ramp[0])
            else:
                c.line(STONE, [(x + 1, y + 1), (x + 3, y + 2), (x + 2, y + 4)], ramp[0])
            c.line(STONE, [(x + 5, y + 1), (x + 6, y + 3)], ramp[2])
            if (tx * 3 + ty) % 4 == 0:
                c.point(STONE, (x + 6, y + 6), ramp[3])


def _draw_ledges(c: _Canvas, folder: str) -> None:
    p = PALETTES[TIMBER]
    for row, x0, x1 in rosa.LAYOUTS[folder]["ledges"]:
        left, right, y = x0 * TILE, (x1 + 1) * TILE - 1, row * TILE
        c.line(TIMBER, [(left, y), (right, y)], p[3])
        c.rect(TIMBER, (left, y + 1, right, y + 4), p[1])
        c.line(TIMBER, [(left, y + 5), (right, y + 5)], p[0])


def _draw_split_bridge(c: _Canvas) -> None:
    """Fractured inner ends; the walkable lip remains visible end to end."""
    p = PALETTES[TIMBER]
    for (row, x0, x1), side in zip(rosa.PORCH_LEDGES, (-1, 1)):
        edge = x0 * TILE if side == 1 else (x1 + 1) * TILE - 1
        y = row * TILE
        c.polygon(TIMBER, [(edge, y + 2), (edge + 4 * side, y + 4), (edge, y + 6)], p[0])
        c.line(TIMBER, [(edge, y + 1), (edge + 4 * side, y + 3)], p[2])


def _draw_posts(c: _Canvas, folder: str) -> None:
    p = PALETTES[TIMBER]
    for tx, ty in post_tiles(folder):
        x, y = tx * TILE + 3, ty * TILE
        c.line(TIMBER, [(x, y), (x, y + 7)], p[0], 2)
        c.line(TIMBER, [(x + 2, y), (x + 2, y + 7)], p[2])


def _draw_storm_damage(c: _Canvas, grid: list[list[int]], folder: str) -> None:
    """Puddles on flat rock, snapped branches on the ground; clear of lanes, spans and their art."""
    keep = set(placard_cells(folder)) | {(row, x) for row, x in rosa._hazard_cells(folder)}
    for span in rosa.LAYOUTS[folder]["spans"]:
        keep |= {(row, x) for row, x0, x1 in span["arcs"] for x in range(x0, x1 + 1)}
    keep |= {(row, x + dx) for row, x in set(keep) for dx in (-2, -1, 1, 2)}
    seed = len(folder)
    shaft_art.puddles(c, grid, PALETTES[STONE], STONE, seed=seed)
    shaft_art.branches(c, shaft_art.ground_spots(grid, keep, seed=seed + 2, mod=8), PALETTES[SKY], SKY)


def _draw_boards(c: _Canvas, folder: str) -> None:
    """Cracked planks on their timber (the board actor only shows while it creaks)."""
    p = PALETTES[TIMBER]
    for row, x0, x1 in rosa.LAYOUTS[folder]["boards"]:
        y = row * TILE
        for tx in range(x0, x1 + 1):
            x = tx * TILE
            c.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
            c.point(TIMBER, (x + 6, y + 4), p[0])


def _draw_transformers(c: _Canvas, folder: str) -> None:
    body_rgb = {code: PALETTES[rosa.TRANSFORMER_BODY_SLOT][index]
                for code, index in rosa.TRANSFORMER_BODY_INDEX.items()}
    for line in rosa.box_lines(folder):
        stage = line["number"]
        transformer_art.paint(c.image.load(), line["box"],
                              stage_rgb=PALETTES[stage_slot(stage)][rosa.STAGE_COLOR_INDEX[stage - 1]],
                              body_rgb=body_rgb)


def _draw_cabin(c: _Canvas) -> None:
    p = PALETTES[TIMBER]
    x0, x1, y0, y1 = rosa.HOUSE_RECT
    left, right = x0 * TILE, x1 * TILE + 7
    top, bottom = y0 * TILE, y1 * TILE + 7
    # Board walls with a seam at every tile edge.
    c.rect(TIMBER, (left, top + 8, right, bottom), p[1])
    for x in range(left + 7, right, TILE):
        c.line(TIMBER, [(x, top + 8), (x, bottom)], p[0])
    # Pitched roof on the top tile row, with a lit eave.
    mid = (left + right) // 2
    c.polygon(TIMBER, [(left, top + 7), (mid, top), (right, top + 7)], p[2])
    c.line(TIMBER, [(left, top + 7), (right, top + 7)], p[3])
    # Doorway: a dark opening three tiles tall, framed in light timber.
    dx = rosa.HOUSE_DOOR[0] * TILE
    dy0 = (rosa.HOUSE_DOOR[1] - 2) * TILE
    c.rect(TIMBER, (dx, dy0, dx + 7, bottom), p[0])
    c.line(TIMBER, [(dx, dy0), (dx, bottom)], p[3])
    c.line(TIMBER, [(dx + 7, dy0), (dx + 7, bottom)], p[3])
    c.point(TIMBER, (dx + 5, dy0 + 12), p[3])


def _draw_windows(c: _Canvas) -> None:
    p = PALETTES[WINDOW]
    # Cold glass; the scene swaps this slot to warm when the line is live.
    for tx, ty in rosa.HOUSE_WINDOWS:
        x, y = tx * TILE, ty * TILE
        c.rect(WINDOW, (x, y, x + 7, y + 7), p[0])
        c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[1])
        c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[3])
        c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[2])
        c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[2])


def _draw_arc_posts(c: _Canvas, folder: str) -> None:
    p = PALETTES[STONE]
    for tx, top in arc_post_tops(folder):
        x = tx * TILE + 3
        y0, y1 = top * TILE + 2, (top + 2) * TILE - 1
        c.rect(STONE, (x, y0, x + 1, y1), p[0])
        c.line(STONE, [(x + 2, y0), (x + 2, y1)], p[2])
        c.rect(STONE, (x - 1, y0, x + 3, y0 + 1), p[3])


def _draw_warnings(c: _Canvas, folder: str) -> None:
    # Placards are stone (the metal slot is wire only).
    p = PALETTES[STONE]
    for row, x0, x1 in rosa.hazard_lanes(folder):
        left, right = x0 * TILE, x1 * TILE + 7
        y = row * TILE
        c.rect(STONE, (left + 2, y + 2, right - 2, y + 5), p[0])
        c.line(STONE, [(left + 4, y + 2), (right - 4, y + 5)], p[2])
        c.line(STONE, [(right - 4, y + 2), (left + 4, y + 5)], p[2])
        center = (left + right) // 2
        c.line(STONE, [(center - 2, y + 3), (center + 2, y + 3)], p[3])
        c.line(STONE, [(center, y + 1), (center, y + 6)], p[3])
    brackets = bracket_cells(folder)
    for row, x0, x1 in rosa.LAYOUTS[folder]["whips"]:
        if (row - 2, x0) not in brackets:
            continue
        left, right, y = (x0 - 1) * TILE + 1, (x1 + 2) * TILE - 2, (row - 3) * TILE
        c.rect(STONE, (left, y + 10, right, y + 13), p[2])
        c.line(STONE, [(left, y + 10), (right, y + 10)], p[3])
        for x in (left + 2, right - 3):
            c.rect(STONE, (x, max(y + 3, rosa.HUD_ROWS * TILE), x + 1, y + 9), p[2])


def _draw_cable(c: _Canvas, slots: list[list[int]], folder: str) -> None:
    """Paint each stage's wire pixels in its metal colour index, on its wire-slot tiles only."""
    px = c.image.load()
    width, height = size_px(folder)
    for stage in stages(folder):
        slot = stage_slot(stage)
        color = PALETTES[slot][rosa.STAGE_COLOR_INDEX[stage - 1]]
        for x, y in sorted(stage_pixels(stage, folder)):
            if x < width and y < height and slots[y // TILE][x // TILE] == slot:
                px[x, y] = color


def make_background(folder: str = rosa.HILL) -> tuple[Image.Image, list[list[int]]]:
    """Return authored art and the contract-sized tile-palette map of one scene."""
    grid = rosa.collision_grid(folder)
    slots = _slots(grid, folder)
    width, height = size_px(folder)
    image = Image.new("RGB", (width, height))
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            color = PALETTES[slot][0]
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    pixels[x, y] = color
    canvas = _Canvas(image, slots)
    _draw_sky(canvas, folder)
    _draw_creek(canvas, folder)
    if rosa.LAYOUTS[folder]["vertical"]:
        shaft_art.draw_stone(canvas, grid, PALETTES[STONE], STONE)
        shaft_art.runoff(canvas, grid, PALETTES[STONE], STONE, seed=3)
        shaft_art.draw_platforms(canvas, rosa.LAYOUTS[folder]["platforms"], PALETTES[TIMBER], TIMBER)
        shaft_art.rope_lashings(canvas, rosa.LAYOUTS[folder]["platforms"], PALETTES[TIMBER], TIMBER)
        shaft_art.draw_posts(canvas, post_tiles(folder), PALETTES[TIMBER], TIMBER)
    else:
        _draw_rock(canvas, grid)
        _draw_ledges(canvas, folder)
        if folder == rosa.PORCH:
            _draw_split_bridge(canvas)
        _draw_posts(canvas, folder)
    _draw_storm_damage(canvas, grid, folder)
    shaft_art.paint_markers(canvas, MARKERS[folder], CLAIMED[folder], "sign", PALETTES[TIMBER], TIMBER)
    if folder == rosa.PORCH:
        _draw_cabin(canvas)
        _draw_windows(canvas)
    _draw_arc_posts(canvas, folder)
    _draw_warnings(canvas, folder)
    _draw_boards(canvas, folder)
    _draw_transformers(canvas, folder)
    _draw_cable(canvas, slots, folder)

    allowed = [set(colors) for colors in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    if image.getpixel((x, y)) not in allowed[slot]:
                        raise AssertionError(f"{folder}: illegal palette color in tile {tx},{ty}")
    _check_geometry_art(image, grid, slots, folder)
    return image, slots


def _check_geometry_art(image: Image.Image, grid: list[list[int]], slots: list[list[int]], folder: str) -> None:
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                assert slots[ty][tx] == STONE, f"{folder}: solid not rock at {tx},{ty}"
    # Wire-slot pixels of each stage's index belong to that stage's wire only.
    for stage in stages(folder):
        wire_slot = stage_slot(stage)
        color = PALETTES[wire_slot][rosa.STAGE_COLOR_INDEX[stage - 1]]
        owner = stage_pixels(stage, folder)
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                if slot != wire_slot:
                    continue
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        if image.getpixel((x, y)) == color:
                            assert (x, y) in owner, f"{folder}: stray stage {stage} wire at {x},{y}"


def _gb_studio_native_index(green: int) -> int:
    if green < 65:
        return 3
    if green < 130:
        return 2
    if green < 205:
        return 1
    return 0


def encode_native_background(image: Image.Image, slots: list[list[int]],
                             folder: str = rosa.HILL) -> Image.Image:
    """Convert each authored ramp index to a canonical grayscale proxy."""
    width, height = rosa.size(folder)
    if image.mode != "RGB" or image.size != size_px(folder):
        raise ValueError(f"expected RGB {size_px(folder)} author image")
    if len(slots) != height or any(len(row) != width for row in slots):
        raise ValueError(f"expected {width}x{height} palette grid")
    palette_indices = [{color: index for index, color in enumerate(palette)} for palette in PALETTES]
    proxy = Image.new("RGB", image.size)
    src, dst = image.load(), proxy.load()
    for y in range(image.height):
        for x in range(image.width):
            slot = slots[y // TILE][x // TILE]
            try:
                intended = palette_indices[slot][src[x, y]]
            except (IndexError, KeyError) as exc:
                raise ValueError(f"invalid palette/color at {x},{y}") from exc
            gray = NATIVE_PROXY_BY_INDEX[intended]
            if _gb_studio_native_index(gray) != intended:
                raise AssertionError(f"proxy brightness mismatch at {x},{y}")
            dst[x, y] = (gray, gray, gray)
    return proxy


def _unique_indexed_tiles(image: Image.Image, slots: list[list[int]]) -> int:
    patterns = set()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            pixels = tuple(image.getpixel((tx * TILE + x, ty * TILE + y)) for y in range(TILE) for x in range(TILE))
            patterns.add((slot, pixels))
    return len(patterns)


def _check_owned_outputs(folder: str) -> None:
    expected_id = rosa.BACKGROUND_IDS[folder]
    sidecar, output = SIDECARS[folder], OUTPUTS[folder]
    if sidecar.exists():
        try:
            current = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"refusing to overwrite unreadable sidecar: {sidecar}") from exc
        if current.get("id") != expected_id:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {sidecar}")
    elif output.exists():
        raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {output}")


def write_background(folder: str) -> None:
    _check_owned_outputs(folder)
    author_image, slots = make_background(folder)
    proxy = encode_native_background(author_image, slots, folder)
    unique = _unique_indexed_tiles(proxy, slots)
    if unique > MAX_UNIQUE_TILES:
        raise AssertionError(f"{folder} uses {unique} unique indexed tiles (budget {MAX_UNIQUE_TILES})")
    output = OUTPUTS[folder]
    width, height = rosa.size(folder)
    output.parent.mkdir(parents=True, exist_ok=True)
    proxy.save(output, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": rosa.BACKGROUND_IDS[folder],
        "name": folder,
        "symbol": f"bg_{folder}",
        "filename": output.name,
        "width": width,
        "height": height,
        "imageWidth": proxy.width,
        "imageHeight": proxy.height,
        "autoColor": False,
        "tileColors": collision_rle(slots, width, height),
    }
    SIDECARS[folder].write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    slot_counts = {slot: sum(value == slot for row in slots for value in row) for slot in range(7)}
    print(f"generated {output.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
          f"{unique} unique indexed tiles (budget {MAX_UNIQUE_TILES}), palette tiles {slot_counts}")


def main() -> None:
    for folder in rosa.SCENE_ORDER:
        write_background(folder)


if __name__ == "__main__":
    main()
