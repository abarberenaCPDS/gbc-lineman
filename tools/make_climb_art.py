"""Generate job 1's collision-aligned backgrounds from ``climb.py``: 1A
``storm_climb.png`` (20x36) and 1B ``climb_crest.png`` (56x18, the CREST section).

The RGB images returned by :func:`make_background` / :func:`make_crest_background`
are the artist-facing sources. The compiler-facing PNGs are grayscale index
proxies, matching the native GB Studio color-index thresholds. This generator
owns only those two PNGs and their background sidecars. The backdrop uses cool
pine and lake silhouettes; timber edges and the cabin stay warmer so collision
surfaces and the destination read in front of the scenery.

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
    # In the lower trail, trunks frame the service steps while a lake glimpse
    # between them foreshadows the view from the crest. Keep behind the play lane.
    _draw_lake(c, WIDTH, 146, 245)
    for x, bottom, size in ((28, 156, 3), (42, 172, 2), (128, 139, 3), (140, 160, 2),
                            (24, 252, 3), (40, 256, 2), (136, 254, 3)):
        _draw_pine(c, x, bottom, size)
    for x, y, color in [(20, 18, 2), (52, 22, 3), (126, 19, 2), (148, 66, 2), (28, 112, 2),
                        (100, 126, 2), (44, 182, 2), (140, 228, 2)]:
        c.point(SKY, (x, y), p[color])


def _draw_lake(c: _Canvas, width: int, shore: int, bottom: int) -> None:
    """Repeated native-size details in a quiet value range behind wires and sprites."""
    p = PALETTES[SKY]
    ridge = [(-1, shore - 9)]
    for i, x in enumerate(range(0, width + 32, 32)):
        ridge.append((x, shore - (10, 24, 17, 33, 25, 12)[i % 6]))
    c.polygon(SKY, ridge + [(width, shore - 1), (0, shore - 1)], p[1])
    c.line(SKY, ridge, p[2])
    c.rect(SKY, (0, shore + 2, width - 1, bottom), p[1])
    for x in range(0, width, 24):
        c.line(SKY, [(x, shore + 3), (x + 14, shore + 3)], p[2])
        for y in range(shore + 12, bottom, 16):
            c.line(SKY, [(x + 4, y), (x + 12, y)], p[0])
            c.line(SKY, [(x + 14, y + 2), (x + 21, y + 2)], p[2])


def _draw_pine(c: _Canvas, x: int, bottom: int, unit: int) -> None:
    p = PALETTES[SKY]
    c.line(SKY, [(x, bottom - 4 * unit), (x, bottom)], p[0], 2)
    for height, spread in ((11, 2), (9, 3), (7, 4)):
        tip = bottom - height * unit
        skirt = tip + 5 * unit
        c.polygon(SKY, [(x, tip), (x - spread * unit, skirt), (x, skirt - unit),
                        (x + spread * unit, skirt)], p[0])
        c.line(SKY, [(x, tip), (x - spread * unit + 1, skirt - 1)], p[2])


def _clear_cells(cells: set[tuple[int, int]]) -> set[tuple[int, int]]:
    """Hazard cells widened by one column each side, so debris never sits beside a hazard lane."""
    return cells | {(row, x + dx) for row, x in cells for dx in (-2, -1, 1, 2)}


def _draw_stone(c: _Canvas, grid: list[list[int]]) -> None:
    shaft_art.draw_stone(c, grid, PALETTES[STONE], STONE)


def _draw_platforms(c: _Canvas) -> None:
    shaft_art.draw_platforms(c, climb.PLATFORMS, PALETTES[TIMBER], TIMBER)


def _draw_posts(c: _Canvas, grid: list[list[int]]) -> None:
    shaft_art.draw_posts(c, _post_tiles(grid), PALETTES[TIMBER], TIMBER)


def _draw_boards(c: _Canvas, scene: str = climb.CLIMB_SCENE) -> None:
    """Cracked planks (the board actor only shows while it creaks)."""
    p = PALETTES[TIMBER]
    for row, x0, x1 in hazards.BOARDS[scene]:
        y = row * TILE
        for tx in range(x0, x1 + 1):
            x = tx * TILE
            c.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
            c.point(TIMBER, (x + 6, y + 4), p[0])


def _draw_house(c: _Canvas) -> None:
    """A lakeside log cabin with shingled gable, chimney and two powerable windows."""
    p = PALETTES
    hx0, hx1, hy0, hy1 = climb.CREST_HOUSE_RECT
    left, right = hx0 * TILE, hx1 * TILE + 7
    top, bottom = hy0 * TILE, hy1 * TILE + 7
    mid = (left + right) // 2
    bark = p[TIMBER]
    c.rect(TIMBER, (right - 10, top + 5, right - 5, top + 20), bark[1])
    c.line(TIMBER, [(right - 11, top + 5), (right - 4, top + 5)], bark[2], 2)
    c.rect(TIMBER, (left, top + 18, right, bottom), bark[1])
    for y in range(top + 21, bottom, 4):
        c.line(TIMBER, [(left, y), (right, y)], bark[2])
        c.point(TIMBER, (left + 2, y + 1), bark[3])
        c.point(TIMBER, (right - 2, y + 1), bark[3])
    c.polygon(TIMBER, [(left, top + 17), (mid, top), (right, top + 17)], bark[1])
    for offset in (6, 10, 14):
        c.line(TIMBER, [(mid - offset, top + offset), (mid + offset, top + offset)], bark[2])
    c.line(TIMBER, [(left, top + 17), (mid, top), (right, top + 17)], bark[3], 2)
    c.line(TIMBER, [(left, top + 18), (right, top + 18)], bark[0], 2)
    c.rect(TIMBER, (mid - 2, top + 9, mid + 3, top + 13), bark[0])
    door_x = climb.CREST_DOOR[0] * TILE
    c.rect(TIMBER, (door_x + 2, bottom - 19, door_x + 13, bottom), bark[0])
    c.line(TIMBER, [(door_x + 2, bottom), (door_x + 2, bottom - 19), (door_x + 13, bottom - 19)], bark[3])
    c.point(TIMBER, (door_x + 11, bottom - 8), bark[3])
    # Slot 3 is the selective power/window family: the checkpoint warms it.
    for tx, ty in CREST_WINDOW_TILES:
        x, y = tx * TILE, ty * TILE
        c.rect(WINDOW, (x, y, x + 7, y + 7), p[WINDOW][0])
        c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[WINDOW][2])
        c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[WINDOW][3])
        c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[WINDOW][1])
        c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[WINDOW][1])


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
    """Visible water, a low far shore, and dark pines around the cabin."""
    p = PALETTES[SKY]
    _draw_lake(c, CREST_WIDTH, 83, 118)
    for x, bottom, size in ((35, 105, 3), (51, 111, 2), (151, 117, 3),
                            (181, 115, 2), (205, 115, 3), (339, 110, 2),
                            (355, 111, 3), (427, 99, 3), (442, 96, 2)):
        _draw_pine(c, x, bottom, size)
    for x, y, color in ((20, 20, 2), (74, 42, 3), (116, 19, 2), (164, 41, 2),
                        (222, 21, 2), (280, 41, 3), (344, 23, 2), (414, 25, 2)):
        c.point(SKY, (x, y), p[color])
    for x, y in ((58, 40), (146, 44), (243, 39), (370, 24)):
        c.line(SKY, [(x, y), (x + 11, y), (x + 15, y + 1), (x + 31, y + 1)], p[1])


def _draw_crest_damage(c: _Canvas) -> None:
    # The static severed ends preview the arc even in its dark phase. The
    # break is aligned with the actual chest-height actor and clear of the
    # safe standing tiles beyond it. Its animation owns the brightest color.
    for row, x0, x1 in climb.crest_span_arc_lanes():
        x, y = x0 * TILE, row * TILE
        end = (x1 + 1) * TILE
        p = PALETTES[SKY]
        c.line(SKY, [(x - 13, y - 13), (x - 9, y - 8), (x - 7, y + 5),
                     (x - 2, y + 11), (x + 4, y + 11)], p[0], 3)
        c.line(SKY, [(x - 13, y - 13), (x - 9, y - 8), (x - 7, y + 5),
                     (x - 2, y + 11), (x + 4, y + 11)], p[2])
        c.line(SKY, [(end - 4, y + 11), (end + 4, y + 11),
                     (end + 10, y + 6), (end + 10, y + 2)], p[0], 3)
        c.line(SKY, [(end - 4, y + 11), (end + 4, y + 11),
                     (end + 10, y + 6), (end + 10, y + 2)], p[2])

    # Splinter pixels stay on their solid edge; there's no decorative
    # platform in the gap. The lower granite lip remains visible below it.
    gap_left = climb.CREST_GAP[0] * TILE
    deck_y = climb.CREST_CATWALK_ROW * TILE
    bark = PALETTES[TIMBER]
    c.line(TIMBER, [(gap_left - 7, deck_y + 4), (gap_left - 4, deck_y + 6),
                    (gap_left - 1, deck_y + 3)], bark[3])
    c.line(TIMBER, [(gap_left - 4, deck_y + 1), (gap_left - 2, deck_y + 3),
                    (gap_left - 1, deck_y + 5)], bark[0])

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
    _draw_boards(canvas, climb.CREST_SCENE)
    _draw_crest_damage(canvas)
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
