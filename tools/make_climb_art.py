"""Generate job 1's collision-aligned backgrounds from ``climb.py``: 1A
``storm_climb.png`` (20x36) and 1B ``climb_crest.png`` (56x18, the CREST section).

The RGB images returned by :func:`make_background` / :func:`make_crest_background`
are the artist-facing sources. The compiler-facing PNGs are grayscale index
proxies, matching the native GB Studio color-index thresholds. This generator
owns only those two PNGs and their background sidecars. The crest is functional
art from the climb's own pieces (sky, stone, timber, transformer, house); an
art pass may dress it later.

BG palette slots: 0 night sky, 1 stone (walls, deck slabs, bedrock), 2 timber
(walks, ledges, posts, Amara's house on the crest), 3 window (Amara's windows
only; her door swaps it), 4 hardware (transformer cans, substation), 5 wire
stages 1-3, 6 wire stages 4-5, 7 UI. Wire tiles hold wire pixels and a transformer's
bushings only, in their stage's colour index, so the chain palettes light the
route stage by stage (climb.CHAIN_PALETTES).
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import hazards
import opening
import shaft_art
import transformer_art
from make_climb_scene import collision_rle, resource_id


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/storm_climb.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
CREST_OUTPUT = ROOT / "assets/backgrounds/climb_crest.png"
CREST_SIDECAR = Path(str(CREST_OUTPUT) + ".gbsres")
TILE = climb.TILE
WIDTH, HEIGHT = climb.MAP_W * TILE, climb.MAP_H * TILE
CREST_WIDTH, CREST_HEIGHT = climb.CREST_W * TILE, climb.CREST_H * TILE
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
MAX_UNIQUE_TILES = 300

SKY, STONE, TIMBER, WINDOW, HARDWARE, WIRE_1, WIRE_2 = range(7)
assert climb.HARDWARE_BG_SLOT == HARDWARE and climb.LINE_BG_SLOT == WIRE_1 and climb.LINE_BG_SLOT_2 == WIRE_2


def _rgb(colors: list[str]) -> list[tuple[int, int, int]]:
    return [tuple(bytes.fromhex(color)) for color in colors]


PALETTES = [_rgb(colors) for _, colors in opening.BG_PALETTES]
PALETTES[HARDWARE] = _rgb(climb.HARDWARE_COLORS)
PALETTES[WIRE_1] = _rgb(climb.WIRE_SLOT_DEAD)
PALETTES[WIRE_2] = _rgb(climb.WIRE_SLOT_DEAD)
CREST_WINDOW_TILES = climb.CREST_WINDOW_TILES

# WP5: a timber arch at every scene link ("the route continues here"), derived from
# scene_links; the tiles it claims are open sky only (wires and terrain keep theirs).
MARKERS = {"storm_climb": shaft_art.exit_markers("storm_climb", climb.MAP_W, climb.MAP_H),
           "climb_crest": shaft_art.exit_markers("climb_crest", climb.CREST_W, climb.CREST_H)}
CLAIMED: dict[str, set[tuple[int, int]]] = {}

# Background transformer: the shared job transformer (transformer_art.py), a
# 16x24 condensation of the transformer sprite's Live frame. Its top tile row is
# in the stage's wire slot ("W": cap, bushing, clamp, collar and lid glow when
# the stage is live); the can and post are hardware ("L" light, "G" grey, "D" dark).
TRANSFORMER_ART = transformer_art.ART
ART_INDEX = {"L": 1, "G": 2, "D": 3}
assert len(TRANSFORMER_ART) == climb.TRANSFORMER_H * TILE
assert all(len(row) == climb.TRANSFORMER_W * TILE for row in TRANSFORMER_ART)


def _mask_pixels(draw, width: int = WIDTH, height: int = HEIGHT) -> frozenset[tuple[int, int]]:
    mask = Image.new("1", (width + 2, height + 2), 0)
    draw(ImageDraw.Draw(mask))
    w = mask.width
    data = list(mask.get_flattened_data())
    return frozenset((i % w, i // w) for i, v in enumerate(data) if v)


def _polyline_pixels(route, width: int = WIDTH, height: int = HEIGHT) -> frozenset[tuple[int, int]]:
    """2px-thick polyline through contract tile cells (offset 3 inside each tile)."""
    pts = [(tx * TILE + 3, ty * TILE + 3) for tx, ty in route]

    def draw(d):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            d.line([(x + dx, y + dy) for x, y in pts], fill=1, width=1)
    return _mask_pixels(draw, width, height)


@functools.lru_cache(maxsize=None)
def stage_pixels(stage: int) -> frozenset[tuple[int, int]]:
    """Every pixel that may carry the wire colour index of ``stage`` (1A)."""
    out: set[tuple[int, int]] = set()
    for s, route in climb.WIRE_ROUTES:
        if s == stage:
            out |= _polyline_pixels(route)
    return frozenset((x, y) for x, y in out if x < WIDTH and y < HEIGHT)


@functools.lru_cache(maxsize=None)
def crest_stage_pixels(stage: int) -> frozenset[tuple[int, int]]:
    """Every crest pixel that may carry the wire colour index of ``stage`` (only stage 5 runs there)."""
    out: set[tuple[int, int]] = set()
    for s, route in climb.CREST_WIRE_ROUTES:
        if s == stage:
            out |= _polyline_pixels(route, CREST_WIDTH, CREST_HEIGHT)
    return frozenset((x, y) for x, y in out if x < CREST_WIDTH and y < CREST_HEIGHT)


def stage_color(stage: int) -> tuple[int, int, int]:
    return PALETTES[climb.stage_slot(stage)][climb.STAGE_COLOR_INDEX[stage - 1]]


def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int, y0: int, y1: int) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            slots[ty][tx] = slot


def _post_tiles(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Timber posts under each ledge end, down to the next occupied cell (at most three rows)."""
    return shaft_art.post_tiles(grid, climb.LEDGES, climb.hazard_cells(), climb.MAP_H)


def _slots(grid: list[list[int]]) -> list[list[int]]:
    """Choose one palette family per tile, respecting the collision grid."""
    slots = [[SKY] * climb.MAP_W for _ in range(climb.MAP_H)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = STONE
            elif cell == climb.COL_TOP:
                slots[ty][tx] = TIMBER
    for tx, ty in _post_tiles(grid):
        slots[ty][tx] = TIMBER
    sx0, sx1, sy0, sy1 = climb.SUBSTATION_TILES
    _set_rect(slots, HARDWARE, sx0, sx1, sy0, sy1)
    _reserve_transformers_and_wires(slots, grid, climb.boxes_in(climb.CLIMB_SCENE), stage_pixels)
    CLAIMED["storm_climb"] = shaft_art.claim_markers(slots, grid, MARKERS["storm_climb"], TIMBER)
    return slots


def _reserve_transformers_and_wires(slots: list[list[int]], grid: list[list[int]], lines, pixels) -> None:
    """Transformer tiles (body hardware, top in the stage's wire slot), then wire tiles on open sky."""
    reserved = {(tx, ty) for ty, row in enumerate(slots) for tx, slot in enumerate(row) if slot != SKY}
    bushings = set()
    for line in lines:
        top, body = climb.transformer_tiles(line["box"])
        for tx, ty in body:
            assert (tx, ty) not in reserved, f"transformer body over {tx},{ty}"
            slots[ty][tx] = HARDWARE
        for tx, ty in top:
            assert (tx, ty) not in reserved, f"transformer top over {tx},{ty}"
            slots[ty][tx] = climb.stage_slot(line["number"])
            bushings.add((tx, ty))
    # Wire tiles take their stage's slot on open sky only, upstream first, so a
    # junction shared by two slots goes to the downstream stage. Platforms, rock,
    # posts, the house and hardware keep theirs: the wire passes behind as a gap.
    for stage in range(1, climb.LINE_COUNT + 1):
        for tx, ty in sorted({(x // TILE, y // TILE) for x, y in pixels(stage)}):
            if grid[ty][tx] != climb.COL_EMPTY or (tx, ty) in bushings:
                continue
            if slots[ty][tx] in (SKY, WIRE_1, WIRE_2):
                slots[ty][tx] = climb.stage_slot(stage)
    assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"


# Deck/ledge/slab/post drawing lives in shaft_art.py (shared with the other shafts).
_Canvas = shaft_art.Canvas


def _draw_sky(c: _Canvas) -> None:
    p = PALETTES[SKY]
    # Distant ranges in the night family stay low-contrast atmosphere behind the route.
    for base, color in ((52, 1), (130, 2), (210, 1)):
        pts = [(-2, base + 14)]
        for i, x in enumerate(range(0, WIDTH + 24, 24)):
            pts.append((x, base + (0, 10, 4, 14, 6)[i % 5]))
        pts += [(WIDTH + 2, base + 30), (-2, base + 30)]
        c.polygon(SKY, pts, p[color])
    for x, y, color in [(20, 18, 2), (52, 22, 3), (126, 14, 2), (148, 66, 3), (28, 112, 2),
                        (100, 126, 3), (44, 182, 2), (92, 204, 3), (140, 228, 2), (60, 252, 3)]:
        c.point(SKY, (x, y), p[color])
    for x, y in [(71, 30), (121, 78), (92, 110), (67, 158), (112, 190), (53, 236)]:
        c.line(SKY, [(x, y), (x - 2, y + 4)], p[1])


def _clear_cells(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Hazard cells widened by one column each side, so debris never sits beside a hazard lane."""
    return cells | {(row, x + dx) for row, x in cells for dx in (-2, -1, 1, 2)}


def _draw_stone(c: _Canvas, grid: list[list[int]]) -> None:
    shaft_art.draw_stone(c, grid, PALETTES[STONE], STONE)


def _draw_platforms(c: _Canvas) -> None:
    shaft_art.draw_platforms(c, climb.PLATFORMS, PALETTES[TIMBER], TIMBER)


def _draw_posts(c: _Canvas, grid: list[list[int]]) -> None:
    shaft_art.draw_posts(c, _post_tiles(grid), PALETTES[TIMBER], TIMBER)


def _draw_boards(c: _Canvas) -> None:
    """Cracked planks (the board actor only shows while it creaks)."""
    p = PALETTES[TIMBER]
    for row, x0, x1 in hazards.BOARDS["storm_climb"]:
        y = row * TILE
        for tx in range(x0, x1 + 1):
            x = tx * TILE
            c.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
            c.point(TIMBER, (x + 6, y + 4), p[0])


def _draw_house(c: _Canvas, house_rect: tuple[int, int, int, int] = climb.CREST_HOUSE_RECT,
                door: tuple[int, int] = climb.CREST_DOOR,
                window_tiles: tuple[tuple[int, int], ...] = CREST_WINDOW_TILES) -> None:
    """Amara's house (moved from the summit to the crest porch, same drawing)."""
    p = PALETTES
    hx0, hx1, hy0, hy1 = house_rect
    left, right = hx0 * TILE, hx1 * TILE + 7
    top, bottom = hy0 * TILE, hy1 * TILE + 7
    mid = (left + right) // 2
    c.polygon(TIMBER, [(left - 2, top + 15), (mid, top), (right + 2, top + 15)], p[TIMBER][0])
    c.polygon(TIMBER, [(left + 2, top + 14), (mid, top + 3), (right - 2, top + 14)], p[TIMBER][2])
    c.rect(TIMBER, (left + 1, top + 15, right - 1, bottom), p[TIMBER][1])
    c.line(TIMBER, [(left + 1, top + 16), (left + 1, bottom)], p[TIMBER][3])
    c.line(TIMBER, [(right - 1, top + 16), (right - 1, bottom)], p[TIMBER][0])
    door_x = door[0] * TILE
    c.rect(TIMBER, (door_x + 2, bottom - 12, door_x + 13, bottom), p[TIMBER][0])
    c.point(TIMBER, (door_x + 11, bottom - 6), p[TIMBER][3])
    # Slot 3 is the selective power/window family: the checkpoint warms it.
    for tx, ty in window_tiles:
        x, y = tx * TILE, ty * TILE
        c.rect(WINDOW, (x, y, x + 7, y + 7), p[WINDOW][0])
        c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[WINDOW][1])
        c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[WINDOW][3])
        c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[WINDOW][2])
        c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[WINDOW][2])


def _draw_substation(c: _Canvas) -> None:
    p = PALETTES[HARDWARE]
    x0, x1, y0, y1 = climb.SUBSTATION_TILES
    left, right, top, bottom = x0 * TILE, x1 * TILE + 7, y0 * TILE, y1 * TILE + 7
    c.rect(HARDWARE, (left + 1, top + 2, right - 1, bottom), p[3])
    c.rect(HARDWARE, (left + 2, top + 3, right - 2, bottom - 1), p[1])
    for y in range(top + 6, bottom - 2, 4):
        c.line(HARDWARE, [(left + 4, y), (right - 4, y)], p[2])
    c.rect(HARDWARE, (right - 7, top, right - 4, top + 2), p[3])


def _draw_transformers(c: _Canvas, lines=None) -> None:
    body_rgb = {code: PALETTES[HARDWARE][index] for code, index in ART_INDEX.items()}
    for line in climb.boxes_in(climb.CLIMB_SCENE) if lines is None else lines:
        top, body = climb.transformer_tiles(line["box"])
        assert all(c.slots[ty][tx] == climb.stage_slot(line["number"]) for tx, ty in top)
        assert all(c.slots[ty][tx] == HARDWARE for tx, ty in body)
        transformer_art.paint(c.image.load(), line["box"], stage_rgb=stage_color(line["number"]),
                              body_rgb=body_rgb)


def _draw_wires(c: _Canvas, pixels=stage_pixels) -> None:
    """Paint each stage's colour index on its own slot's tiles only."""
    px = c.image.load()
    for stage in range(1, climb.LINE_COUNT + 1):
        slot = climb.stage_slot(stage)
        color = stage_color(stage)
        for x, y in sorted(pixels(stage)):
            if c.slots[y // TILE][x // TILE] == slot:
                px[x, y] = color


def make_background() -> tuple[Image.Image, list[list[int]]]:
    """Return authored 160x288 RGB art and its 20x36 tile-palette map."""
    grid = climb.collision_grid()
    slots = _slots(grid)
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            color = PALETTES[slot][0]
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    pixels[x, y] = color
    canvas = _Canvas(image, slots)
    _draw_sky(canvas)
    _draw_stone(canvas, grid)
    shaft_art.puddles(canvas, grid, PALETTES[STONE], STONE)
    shaft_art.branches(canvas, shaft_art.ground_spots(grid, _clear_cells(climb.hazard_cells()), seed=2, mod=7),
                       PALETTES[SKY], SKY)
    _draw_platforms(canvas)
    _draw_posts(canvas, grid)
    _draw_boards(canvas)
    _draw_substation(canvas)
    shaft_art.paint_markers(canvas, MARKERS["storm_climb"], CLAIMED["storm_climb"], "arch", PALETTES[TIMBER], TIMBER)
    _draw_transformers(canvas)
    _draw_wires(canvas)

    _check_palette_colors(image, slots)
    _check_geometry_art(image, grid, slots)
    return image, slots


def _check_palette_colors(image: Image.Image, slots: list[list[int]]) -> None:
    """Every material remains within its one tile palette's four native colors."""
    allowed = [set(colors) for colors in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    if image.getpixel((x, y)) not in allowed[slot]:
                        raise AssertionError(f"illegal palette color in tile {tx},{ty}")


# ---------------------------------------------------------------------------
# 1B climb_crest (56x18): the climb's sky, stone, timber, transformer and house
# ---------------------------------------------------------------------------
def crest_post_tiles(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Timber posts under catwalk C's ends."""
    return shaft_art.post_tiles(grid, climb.CREST_PLATFORMS, climb.crest_hazard_cells(), climb.CREST_H)


def crest_slots(grid: list[list[int]]) -> list[list[int]]:
    slots = [[SKY] * climb.CREST_W for _ in range(climb.CREST_H)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = STONE
            elif cell == climb.COL_TOP:
                slots[ty][tx] = TIMBER
    for tx, ty in crest_post_tiles(grid):
        slots[ty][tx] = TIMBER
    hx0, hx1, hy0, hy1 = climb.CREST_HOUSE_RECT
    _set_rect(slots, TIMBER, hx0, hx1, hy0, hy1)
    for tx, ty in CREST_WINDOW_TILES:
        slots[ty][tx] = WINDOW
    _reserve_transformers_and_wires(slots, grid, climb.boxes_in(climb.CREST_SCENE), crest_stage_pixels)
    CLAIMED["climb_crest"] = shaft_art.claim_markers(slots, grid, MARKERS["climb_crest"], TIMBER)
    return slots


def _draw_crest_sky(c: _Canvas) -> None:
    """Night sky over the town, all in the night slot: receding storm cloud, a far range with
    two pylons on its crest, and a mostly dark town in the valley (a few windows still lit,
    the neighbours waiting on the power). Stars, rain streaks and the HUD rows stay clear."""
    p = PALETTES[SKY]
    base = 60
    for x0 in range(30, CREST_WIDTH - 40, 150):               # storm cloud banks (p1 slabs)
        y = 28 + (x0 // 150) % 2 * 10
        c.polygon(SKY, [(x0, y + 8), (x0 + 10, y + 2), (x0 + 30, y), (x0 + 52, y + 4), (x0 + 70, y + 9),
                        (x0 + 40, y + 12), (x0 + 12, y + 12)], p[1])
        c.line(SKY, [(x0 + 12, y + 3), (x0 + 30, y + 1), (x0 + 50, y + 5)], p[2])
    pts = [(-2, base + 14)]
    for i, x in enumerate(range(0, CREST_WIDTH + 24, 24)):
        pts.append((x, base + (0, 10, 4, 14, 6)[i % 5]))
    pts += [(CREST_WIDTH + 2, base + 60), (-2, base + 60)]
    c.polygon(SKY, pts, p[1])
    c.line(SKY, pts[:-2], p[2])
    for x in range(100, CREST_WIDTH - 40, 190):               # pylons on the range crest
        top = base - 6
        foot = base + 18
        c.line(SKY, [(x - 6, foot), (x, top), (x + 6, foot)], p[2], 2)
        c.line(SKY, [(x - 5, top + 9), (x + 5, top + 9)], p[2], 2)
        c.line(SKY, [(x - 8, top + 3), (x + 8, top + 3)], p[2], 2)
    for k, x in enumerate(range(6, CREST_WIDTH - 6, 14)):     # the dark town: roofs and lit windows
        h = 6 + (k * 5) % 7
        w = 7 + (k * 3) % 4
        y1 = base + 56
        y0 = y1 - h - (k % 3) * 3
        c.rect(SKY, (x, y0, x + w, y1), p[0])
        c.polygon(SKY, [(x - 1, y0), (x + w // 2, y0 - 4), (x + w + 1, y0)], p[0])
        if k % 3 == 1:                                         # a lit window in every third house
            c.rect(SKY, (x + 2, y0 + 3, x + 3, y0 + 4), p[3])
    for x, y, color in [(20, 26, 2), (76, 34, 3), (132, 22, 2), (188, 44, 3), (244, 28, 2),
                        (300, 40, 3), (356, 24, 2), (412, 36, 3)]:
        c.point(SKY, (x, y), p[color])
    for x, y in [(52, 60), (164, 52), (276, 64), (388, 56)]:
        c.line(SKY, [(x, y), (x - 2, y + 4)], p[1])


def make_crest_background() -> tuple[Image.Image, list[list[int]]]:
    """Return authored 448x144 RGB art and its 56x18 tile-palette map (climb_crest)."""
    grid = climb.crest_collision_grid()
    slots = crest_slots(grid)
    image = Image.new("RGB", (CREST_WIDTH, CREST_HEIGHT))
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            color = PALETTES[slot][0]
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    pixels[x, y] = color
    canvas = _Canvas(image, slots)
    _draw_crest_sky(canvas)
    shaft_art.draw_stone(canvas, grid, PALETTES[STONE], STONE)
    shaft_art.puddles(canvas, grid, PALETTES[STONE], STONE, seed=1)
    shaft_art.branches(canvas, shaft_art.ground_spots(grid, _clear_cells(climb.crest_hazard_cells()), seed=3, mod=9),
                       PALETTES[SKY], SKY)
    shaft_art.draw_platforms(canvas, climb.CREST_PLATFORMS, PALETTES[TIMBER], TIMBER)
    shaft_art.draw_posts(canvas, crest_post_tiles(grid), PALETTES[TIMBER], TIMBER)
    _draw_house(canvas)
    shaft_art.paint_markers(canvas, MARKERS["climb_crest"], CLAIMED["climb_crest"], "arch", PALETTES[TIMBER], TIMBER)
    _draw_transformers(canvas, climb.boxes_in(climb.CREST_SCENE))
    _draw_wires(canvas, crest_stage_pixels)
    _check_palette_colors(image, slots)
    _check_wire_slots(image, slots)
    for row, x0, x1 in climb.CREST_PLATFORMS:
        assert all(image.getpixel((x * TILE, row * TILE)) == PALETTES[TIMBER][3] for x in range(x0, x1 + 1))
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            assert cell != climb.COL_SOLID or slots[y][x] == STONE
    return image, slots


def _gb_studio_native_index(green: int) -> int:
    if green < 65:
        return 3
    if green < 130:
        return 2
    if green < 205:
        return 1
    return 0


def encode_native_background(image: Image.Image, slots: list[list[int]]) -> Image.Image:
    """Convert each authored ramp index to a canonical grayscale proxy (either scene's size)."""
    width, height = len(slots[0]) * TILE, len(slots) * TILE
    if image.mode != "RGB" or image.size != (width, height):
        raise ValueError(f"expected RGB {(width, height)} author image")
    if any(len(row) * TILE != width for row in slots):
        raise ValueError("ragged palette grid")
    palette_indices = [{color: index for index, color in enumerate(palette)} for palette in PALETTES]
    proxy = Image.new("RGB", image.size)
    src, dst = image.load(), proxy.load()
    for y in range(height):
        for x in range(width):
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


def unique_indexed_tiles(image: Image.Image, slots: list[list[int]]) -> int:
    patterns = set()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            pixels = tuple(image.getpixel((tx * TILE + x, ty * TILE + y)) for y in range(8) for x in range(8))
            patterns.add((slot, pixels))
    return len(patterns)


def _check_geometry_art(image: Image.Image, grid: list[list[int]], slots: list[list[int]]) -> None:
    for row, x0, x1 in climb.PLATFORMS:
        py = row * TILE
        for x in range(x0, x1 + 1):
            if grid[row][x] != climb.COL_TOP:
                continue
            assert image.getpixel((x * TILE, py)) == PALETTES[TIMBER][3], f"platform lip drift on row {row}"
    for x0, x1, row0, row1 in climb.SOLID_BLOCKS:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                assert slots[row][x] == STONE
    _check_wire_slots(image, slots)


def _check_wire_slots(image: Image.Image, slots: list[list[int]]) -> None:
    """Only wire and bushing pixels use a stage's index; everything else in a wire
    slot is the dark index 0, so the swap lights nothing but the route."""
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            if slot not in (WIRE_1, WIRE_2):
                continue
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    color = image.getpixel((x, y))
                    assert color == PALETTES[slot][0] or any(
                        color == stage_color(s) and climb.stage_slot(s) == slot
                        for s in range(1, climb.LINE_COUNT + 1)), f"stray colour in wire tile {tx},{ty}"


def _check_owned_output(output: Path, sidecar: Path, expected_id: str) -> None:
    if sidecar.exists():
        try:
            current = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"refusing to overwrite unreadable sidecar: {sidecar}") from exc
        if current.get("id") != expected_id:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {sidecar}")
    elif output.exists():
        raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {output}")


def _check_owned_outputs() -> None:
    _check_owned_output(OUTPUT, SIDECAR, resource_id("background:storm-climb"))
    _check_owned_output(CREST_OUTPUT, CREST_SIDECAR, resource_id("background:climb-crest"))


# (output, sidecar, background key, name, author-image builder) per job 1 scene.
BACKGROUNDS = (
    (OUTPUT, SIDECAR, "background:storm-climb", "storm_climb", lambda: make_background()),
    (CREST_OUTPUT, CREST_SIDECAR, "background:climb-crest", "climb_crest", lambda: make_crest_background()),
)


def main() -> None:
    _check_owned_outputs()
    for output, sidecar, key, name, build in BACKGROUNDS:
        author_image, slots = build()
        proxy = encode_native_background(author_image, slots)
        unique = unique_indexed_tiles(proxy, slots)
        if unique >= MAX_UNIQUE_TILES:
            raise AssertionError(f"{name} uses {unique} unique indexed tiles (target <{MAX_UNIQUE_TILES})")
        output.parent.mkdir(parents=True, exist_ok=True)
        proxy.save(output, format="PNG", optimize=False)
        width, height = len(slots[0]), len(slots)
        resource = {
            "_resourceType": "background",
            "id": resource_id(key),
            "name": name,
            "symbol": f"bg_{name}",
            "filename": output.name,
            "width": width,
            "height": height,
            "imageWidth": proxy.width,
            "imageHeight": proxy.height,
            "autoColor": False,
            "tileColors": collision_rle(slots, width, height),
        }
        sidecar.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
        slot_counts = {slot: sum(value == slot for row in slots for value in row) for slot in range(7)}
        print(f"generated {output.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
              f"{unique} unique indexed tiles (<{MAX_UNIQUE_TILES} target), palette tiles {slot_counts}")


if __name__ == "__main__":
    main()
