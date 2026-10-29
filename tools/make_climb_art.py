"""Generate the authored, collision-aligned Storm Climb background from ``climb.py``.

The RGB image returned by :func:`make_background` is the artist-facing source.
The compiler-facing PNG is a grayscale index proxy, matching the native
GB Studio color-index thresholds. This generator owns only ``storm_climb.png``
and its background sidecar.

BG palette slots: 0 night sky, 1 stone (walls, deck slabs, bedrock), 2 timber
(walks, ledges, posts, Amara's house), 3 window (Amara's windows only; the
checkpoint swaps it), 4 hardware (transformer cans, substation), 5 wire stages
1-3, 6 wire stages 4-5, 7 UI. Wire tiles hold wire pixels and a transformer's
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
from make_climb_scene import collision_rle, resource_id


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/storm_climb.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
TILE = climb.TILE
WIDTH, HEIGHT = climb.MAP_W * TILE, climb.MAP_H * TILE
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
SUMMIT_WINDOW_TILES = climb.SUMMIT_WINDOW_TILES

# Background transformer, 16x24 on its two columns: the top row of tiles is in
# its stage's wire slot ("W" = the stage colour: bushings and lid glow when the
# stage is live), the can and post are hardware ("L" light, "G" grey, "D" dark).
# Modelled on the transformer sprite Abe picked (Signal Hill): dark outline,
# light can, banded body, short post.
TRANSFORMER_ART = [
    "................",
    "...WW......WW...",
    "...WW......WW...",
    "..WWWW....WWWW..",
    "...WW......WW...",
    "..WWWW....WWWW..",
    "...WW......WW...",
    ".WWWWWWWWWWWWWW.",
    ".DDDDDDDDDDDDDD.",
    ".DLLLLLLLLLLLLD.",
    ".DLLGGLLLLGGLLD.",
    ".DLLGGLLLLGGLLD.",
    ".DLLLLLLLLLLLLD.",
    ".DGGGGGGGGGGGGD.",
    ".DLLLLLLLLLLLLD.",
    ".DDDDDDDDDDDDDD.",
    "..DLLLLLLLLLLD..",
    "..DDDDDDDDDDDD..",
    "......DLLD......",
    "......DLLD......",
    "......DLLD......",
    "......DLLD......",
    "....DDDDDDDD....",
    "....DLLLLLLD....",
]
ART_INDEX = {"L": 1, "G": 2, "D": 3}
assert len(TRANSFORMER_ART) == climb.TRANSFORMER_H * TILE
assert all(len(row) == climb.TRANSFORMER_W * TILE for row in TRANSFORMER_ART)


def _mask_pixels(draw) -> frozenset[tuple[int, int]]:
    mask = Image.new("1", (WIDTH + 2, HEIGHT + 2), 0)
    draw(ImageDraw.Draw(mask))
    w = mask.width
    data = list(mask.get_flattened_data())
    return frozenset((i % w, i // w) for i, v in enumerate(data) if v)


def _polyline_pixels(route) -> frozenset[tuple[int, int]]:
    """2px-thick polyline through contract tile cells (offset 3 inside each tile)."""
    pts = [(tx * TILE + 3, ty * TILE + 3) for tx, ty in route]

    def draw(d):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            d.line([(x + dx, y + dy) for x, y in pts], fill=1, width=1)
    return _mask_pixels(draw)


@functools.lru_cache(maxsize=None)
def stage_pixels(stage: int) -> frozenset[tuple[int, int]]:
    """Every pixel that may carry the wire colour index of ``stage``."""
    out: set[tuple[int, int]] = set()
    for s, route in climb.WIRE_ROUTES:
        if s == stage:
            out |= _polyline_pixels(route)
    return frozenset((x, y) for x, y in out if x < WIDTH and y < HEIGHT)


def stage_color(stage: int) -> tuple[int, int, int]:
    return PALETTES[climb.stage_slot(stage)][climb.STAGE_COLOR_INDEX[stage - 1]]


def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int, y0: int, y1: int) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            slots[ty][tx] = slot


def _post_tiles(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Timber posts under each ledge end, down to the next occupied cell (at most three rows)."""
    lanes = climb.hazard_cells()
    posts = []
    for row, x0, x1 in climb.LEDGES:
        for tx in (x0, x1):
            for ty in range(row + 1, min(row + 4, climb.MAP_H)):
                if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in lanes:
                    break
                posts.append((tx, ty))
    return posts


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
    hx0, hx1, hy0, hy1 = climb.HOUSE_RECT
    _set_rect(slots, TIMBER, hx0, hx1, hy0, hy1)
    for tx, ty in SUMMIT_WINDOW_TILES:
        slots[ty][tx] = WINDOW
    sx0, sx1, sy0, sy1 = climb.SUBSTATION_TILES
    _set_rect(slots, HARDWARE, sx0, sx1, sy0, sy1)
    reserved = {(tx, ty) for ty in range(climb.MAP_H) for tx in range(climb.MAP_W) if slots[ty][tx] != SKY}
    bushings = set()
    for line in climb.LINES:
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
        for tx, ty in sorted({(x // TILE, y // TILE) for x, y in stage_pixels(stage)}):
            if grid[ty][tx] != climb.COL_EMPTY or (tx, ty) in bushings:
                continue
            if slots[ty][tx] in (SKY, WIRE_1, WIRE_2):
                slots[ty][tx] = climb.stage_slot(stage)
    assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
    return slots


class _Canvas:
    """Clip all painting to its tile's one assigned palette family."""

    def __init__(self, image: Image.Image, slots: list[list[int]]):
        self.image = image
        self.slots = slots

    def _apply(self, slot: int, painter) -> None:
        layer = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        painter(ImageDraw.Draw(layer))
        bounds = layer.getbbox()
        if not bounds:
            return
        px, over = self.image.load(), layer.load()
        left, top, right, bottom = bounds
        for y in range(top, bottom):
            for x in range(left, right):
                rgba = over[x, y]
                if rgba[3] and self.slots[y // TILE][x // TILE] == slot:
                    px[x, y] = rgba[:3]

    @staticmethod
    def _rgba(color):
        return tuple(color) + (255,)

    def rect(self, slot: int, box, color) -> None:
        fill = self._rgba(color)
        self._apply(slot, lambda d: d.rectangle(box, fill=fill))

    def line(self, slot: int, points, color, width=1) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.line(points, fill=rgba, width=width))

    def polygon(self, slot: int, points, color) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.polygon(points, fill=rgba))

    def point(self, slot: int, xy, color) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.point(xy, fill=rgba))


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


def _draw_stone(c: _Canvas, grid: list[list[int]]) -> None:
    ramp = PALETTES[STONE]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != climb.COL_SOLID:
                continue
            x, y = tx * TILE, ty * TILE
            c.rect(STONE, (x, y, x + 7, y + 7), ramp[1])
            if ty > 0 and grid[ty - 1][tx] == climb.COL_EMPTY:
                c.line(STONE, [(x, y), (x + 7, y)], ramp[3])   # walkable top edge
            if (tx + ty) % 3 == 0:
                c.polygon(STONE, [(x, y + 3), (x + 3, y + 1), (x + 4, y + 3), (x + 2, y + 5)], ramp[0])
            else:
                c.line(STONE, [(x + 1, y + 2), (x + 3, y + 3), (x + 2, y + 5)], ramp[0])
            c.line(STONE, [(x + 5, y + 2), (x + 6, y + 4)], ramp[2])


def _draw_platforms(c: _Canvas) -> None:
    p = PALETTES[TIMBER]
    for row, x0, x1 in climb.PLATFORMS:
        y = row * TILE
        left, right = x0 * TILE, x1 * TILE + 7
        # The light top edge is exactly the collision row's first pixel.
        c.line(TIMBER, [(left, y), (right, y)], p[3])
        c.line(TIMBER, [(left, y + 1), (right, y + 1)], p[2])
        c.rect(TIMBER, (left, y + 2, right, y + 4), p[1])
        c.line(TIMBER, [(left, y + 5), (right, y + 5)], p[0])
        c.line(TIMBER, [(left, y + 6), (right, y + 6)], p[0])
        for x in range(left + 10, right - 2, 16):
            c.line(TIMBER, [(x, y + 2), (x, y + 4)], p[0])
            c.point(TIMBER, (x + 3, y + 2), p[3])


def _draw_posts(c: _Canvas, grid: list[list[int]]) -> None:
    p = PALETTES[TIMBER]
    for tx, ty in _post_tiles(grid):
        x, y = tx * TILE + 3, ty * TILE
        c.line(TIMBER, [(x, y), (x, y + 7)], p[0], 2)
        c.line(TIMBER, [(x + 2, y), (x + 2, y + 7)], p[2])


def _draw_boards(c: _Canvas) -> None:
    """Cracked planks (the board actor only shows while it creaks)."""
    p = PALETTES[TIMBER]
    for row, x0, x1 in hazards.BOARDS["storm_climb"]:
        y = row * TILE
        for tx in range(x0, x1 + 1):
            x = tx * TILE
            c.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
            c.point(TIMBER, (x + 6, y + 4), p[0])


def _draw_house(c: _Canvas) -> None:
    p = PALETTES
    hx0, hx1, hy0, hy1 = climb.HOUSE_RECT
    left, right = hx0 * TILE, hx1 * TILE + 7
    top, bottom = hy0 * TILE, hy1 * TILE + 7
    mid = (left + right) // 2
    c.polygon(TIMBER, [(left - 2, top + 15), (mid, top), (right + 2, top + 15)], p[TIMBER][0])
    c.polygon(TIMBER, [(left + 2, top + 14), (mid, top + 3), (right - 2, top + 14)], p[TIMBER][2])
    c.rect(TIMBER, (left + 1, top + 15, right - 1, bottom), p[TIMBER][1])
    c.line(TIMBER, [(left + 1, top + 16), (left + 1, bottom)], p[TIMBER][3])
    c.line(TIMBER, [(right - 1, top + 16), (right - 1, bottom)], p[TIMBER][0])
    door_x = climb.HOUSE_A["x"] * TILE
    c.rect(TIMBER, (door_x + 2, bottom - 12, door_x + 13, bottom), p[TIMBER][0])
    c.point(TIMBER, (door_x + 11, bottom - 6), p[TIMBER][3])
    # Slot 3 is the selective power/window family: the checkpoint warms it.
    for tx, ty in SUMMIT_WINDOW_TILES:
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


def _draw_transformers(c: _Canvas) -> None:
    px = c.image.load()
    for line in climb.LINES:
        bx, by = line["box"]
        left, top = bx * TILE, (by - climb.TRANSFORMER_H + 1) * TILE
        stage_rgb = stage_color(line["number"])
        for dy, row in enumerate(TRANSFORMER_ART):
            for dx, code in enumerate(row):
                x, y = left + dx, top + dy
                slot = c.slots[y // TILE][x // TILE]
                if code == "W":
                    assert slot == climb.stage_slot(line["number"])
                    px[x, y] = stage_rgb
                elif code in ART_INDEX:
                    assert slot == HARDWARE
                    px[x, y] = PALETTES[HARDWARE][ART_INDEX[code]]


def _draw_wires(c: _Canvas) -> None:
    """Paint each stage's colour index on its own slot's tiles only."""
    px = c.image.load()
    for stage in range(1, climb.LINE_COUNT + 1):
        slot = climb.stage_slot(stage)
        color = stage_color(stage)
        for x, y in sorted(stage_pixels(stage)):
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
    _draw_platforms(canvas)
    _draw_posts(canvas, grid)
    _draw_boards(canvas)
    _draw_house(canvas)
    _draw_substation(canvas)
    _draw_transformers(canvas)
    _draw_wires(canvas)

    # Every material remains within its one tile palette's four native colors.
    allowed = [set(colors) for colors in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    if image.getpixel((x, y)) not in allowed[slot]:
                        raise AssertionError(f"illegal palette color in tile {tx},{ty}")
    _check_geometry_art(image, grid, slots)
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
    """Convert each authored ramp index to a canonical grayscale proxy."""
    if image.mode != "RGB" or image.size != (WIDTH, HEIGHT):
        raise ValueError(f"expected RGB {(WIDTH, HEIGHT)} author image")
    if len(slots) != climb.MAP_H or any(len(row) != climb.MAP_W for row in slots):
        raise ValueError(f"expected {climb.MAP_W}x{climb.MAP_H} palette grid")
    palette_indices = [{color: index for index, color in enumerate(palette)} for palette in PALETTES]
    proxy = Image.new("RGB", image.size)
    src, dst = image.load(), proxy.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
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
    # Only wire and bushing pixels use a stage's index; everything else in a wire
    # slot is the dark index 0, so the swap lights nothing but the route.
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


def _check_owned_outputs() -> None:
    expected_id = resource_id("background:storm-climb")
    if SIDECAR.exists():
        try:
            current = json.loads(SIDECAR.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"refusing to overwrite unreadable sidecar: {SIDECAR}") from exc
        if current.get("id") != expected_id:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {SIDECAR}")
    elif OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {OUTPUT}")


def main() -> None:
    _check_owned_outputs()
    author_image, slots = make_background()
    proxy = encode_native_background(author_image, slots)
    unique = unique_indexed_tiles(proxy, slots)
    if unique >= MAX_UNIQUE_TILES:
        raise AssertionError(f"storm_climb uses {unique} unique indexed tiles (target <{MAX_UNIQUE_TILES})")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    proxy.save(OUTPUT, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": resource_id("background:storm-climb"),
        "name": "storm_climb",
        "symbol": "bg_storm_climb",
        "filename": OUTPUT.name,
        "width": climb.MAP_W,
        "height": climb.MAP_H,
        "imageWidth": proxy.width,
        "imageHeight": proxy.height,
        "autoColor": False,
        "tileColors": collision_rle(slots, climb.MAP_W, climb.MAP_H),
    }
    SIDECAR.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    slot_counts = {slot: sum(value == slot for row in slots for value in row) for slot in range(7)}
    print(f"generated {OUTPUT.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
          f"{unique} unique indexed tiles (<{MAX_UNIQUE_TILES} target), palette tiles {slot_counts}")


if __name__ == "__main__":
    main()
