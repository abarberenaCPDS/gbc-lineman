"""Generate the Wind Ridge background from the ``ridge.py`` contract.

Modelled on ``make_climb_art.py``: the RGB image returned by
:func:`make_background` is the artist-facing source, and the compiler-facing
PNG is a grayscale index proxy that uses GB Studio's native index thresholds.
This generator owns only ``wind_ridge.png`` and its background sidecar.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import opening
import ridge
from make_climb_scene import collision_rle


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/wind_ridge.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
TILE = ridge.TILE
WIDTH, HEIGHT = ridge.MAP_W * TILE, ridge.MAP_H * TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
MAX_UNIQUE_TILES = 192

# BG palette families (opening.BG_PALETTES order). Slot 7 is the editor UI.
SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, EARTH = range(7)
LINE = climb.LINE_BG_SLOT
LINE_INDEX = climb.LINE_COLOR_INDEX
assert LINE == METAL, "cable slot must be the metal family"
assert ridge.WINDOW_BG_SLOT == WINDOW, "window slot must be the window family"

# Pixel polyline of the distant ridge (sky tiles only). It stops at the floor
# top; rows 0-1 under the HUD stay clear of it.
RIDGE_LINE = [(0, 58), (14, 46), (28, 52), (42, 34), (56, 44), (72, 26),
              (88, 42), (104, 38), (118, 22), (134, 40), (150, 32), (166, 48),
              (182, 36), (198, 44), (214, 28), (230, 42), (246, 34), (262, 50),
              (278, 30), (294, 42), (308, 34), (320, 44), (336, 36), (352, 50),
              (368, 30), (384, 40), (400, 24), (414, 38), (430, 46), (446, 32),
              (462, 42), (480, 36)]
RIDGE_HIGHLIGHTS = [[(42, 34), (46, 40)], [(118, 22), (114, 28)],
                    [(214, 28), (210, 35)], [(278, 30), (274, 37)],
                    [(368, 30), (364, 38)], [(400, 24), (396, 31)], [(446, 32), (442, 39)]]
# Storm rain slashes and sparks, all above the ridge line.
RAIN_SLASHES = [(20, 30), (52, 24), (92, 28), (140, 26), (180, 26),
                (250, 24), (300, 26), (340, 28), (372, 24), (410, 30),
                (436, 22), (466, 28)]
SPARKS = [(64, 26, 3), (160, 20, 3), (236, 16, 2), (330, 22, 3), (392, 18, 3), (452, 24, 2)]
# Far-left pines (x, top, w, bottom) in pixels, behind the cliff wall. They sit
# clear of the cable route and the gust lanes.
PINES = [(9, 52, 12, 99), (25, 76, 10, 111), (132, 64, 10, 100),
         (205, 60, 10, 100), (336, 62, 10, 100)]

# The snapped utility pole (contract: ridge.DAMAGED_POLE) is the animated
# intro_pole actor (see make_ridge_scene); the background draws no pole. The
# cable starts at the top of that sprite (ridge.CABLE_ROUTE[0] == pole x, y-3).

# Route cells are converted to tile-centre pixels, so every polyline vertex
# lands in the middle of its contract cell.
LANE_CELLS = {(row, x) for row, x0, x1 in ridge.hazard_lanes()
              for x in range(x0, x1 + 1)}
# Overhead crossarm over each whip lane (the wire itself is a sprite whose
# canvas covers rows 11-14), rows 9-10, one tile wider than the lane each side.
BRACKET_ROWS = (9, 10)
BRACKET_CELLS = {(BRACKET_ROWS[i], x) for _, x0, x1 in ridge.WHIP_LANES
                 for x in range(x0 - 1, x1 + 2) for i in (0, 1)}


def _post_tiles(grid: list[list[int]]) -> list[tuple[int, int]]:
    """Catwalk posts: vertical timber under each ledge, in open air only."""
    posts: list[tuple[int, int]] = []
    for row, x0, x1 in ridge.LEDGES:
        for tx in sorted({x0, x1, *range(x0 + 3, x1, 4)}):
            for ty in range(row + 1, min(row + 4, ridge.MAP_H)):
                if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in LANE_CELLS:
                    break
                posts.append((tx, ty))
    return posts


def _polyline_pixels(route) -> frozenset[tuple[int, int]]:
    """Pixels of a 1px polyline through contract tile centres."""
    points = [(tx * TILE + TILE // 2, ty * TILE + TILE // 2) for tx, ty in route]
    mask = Image.new("1", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mask).line(points, fill=255, width=1)
    return frozenset((x, y) for y in range(HEIGHT) for x in range(WIDTH)
                     if mask.getpixel((x, y)))


def downed_wire_points() -> list[tuple[int, int]]:
    """Zigzag fallen wire on the floor across ridge.DOWNED_SPAN (row 14 only)."""
    y0 = (ridge.GROUND_ROW - 1) * TILE
    x0, x1 = ridge.DOWNED_SPAN[0] * TILE, (ridge.DOWNED_SPAN[1] + 1) * TILE - 1
    pts, x, k = [], x0, 0
    while x < x1:
        pts.append((x, y0 + (5, 3, 5, 4)[k % 4]))
        x += 7
        k += 1
    pts.append((x1, y0 + 5))
    return pts


@functools.lru_cache(maxsize=None)
def line1_pixels() -> frozenset[tuple[int, int]]:
    """Feeder route plus the fallen wire (colour index 1)."""
    pts = downed_wire_points()
    mask = Image.new("1", (WIDTH, HEIGHT), 0)
    d = ImageDraw.Draw(mask)
    d.line(pts, fill=255, width=1)
    d.line([(x, y + 1) for x, y in pts], fill=255, width=1)  # 2px thick
    wire = frozenset((x, y) for y in range(HEIGHT) for x in range(WIDTH) if mask.getpixel((x, y)))
    return _polyline_pixels(ridge.FEEDER_ROUTE) | wire


@functools.lru_cache(maxsize=None)
def line2_pixels() -> frozenset[tuple[int, int]]:
    return _polyline_pixels(ridge.CABLE_ROUTE) - line1_pixels()


def cable_pixels() -> frozenset[tuple[int, int]]:
    return line1_pixels() | line2_pixels()


@functools.lru_cache(maxsize=None)
def cable_route_tiles() -> frozenset[tuple[int, int]]:
    """(tx, ty) tiles either line passes through; some may be occluded."""
    return frozenset((x // TILE, y // TILE) for x, y in cable_pixels())


def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int,
              y0: int, y1: int) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            slots[ty][tx] = slot


def _slots(grid: list[list[int]]) -> list[list[int]]:
    """Choose one palette family per tile, respecting the collision grid."""
    slots = [[SKY] * ridge.MAP_W for _ in range(ridge.MAP_H)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = EARTH if ty > ridge.GROUND_ROW else STONE
            elif cell == climb.COL_TOP:
                slots[ty][tx] = TIMBER

    for x, top, w, bottom in PINES:
        for ty in range(top // TILE, (bottom - 1) // TILE + 1):
            for tx in range(x // TILE, (x + w - 1) // TILE + 1):
                if grid[ty][tx] == climb.COL_EMPTY and slots[ty][tx] == SKY:
                    slots[ty][tx] = FOLIAGE

    for tx, ty in _post_tiles(grid):
        slots[ty][tx] = TIMBER

    # Hiroshi's cabin: timber body over the floor, two lit windows, one door.
    x0, x1, y0, y1 = ridge.HOUSE_RECT
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if grid[ty][tx] != climb.COL_EMPTY:
                raise AssertionError(f"house overlaps collision at {tx},{ty}")
    _set_rect(slots, TIMBER, x0, x1, y0, y1)
    # Each window owns exactly one whole tile; no other tile uses this slot.
    for tx, ty in ridge.HOUSE_WINDOWS:
        slots[ty][tx] = WINDOW

    # Hazard lanes get a metal placard; the whip lane also gets an overhead
    # crossarm. Neither uses indices 1 or 3 (those belong to the two lines).
    for row, tx in sorted(LANE_CELLS | BRACKET_CELLS):
        if grid[row][tx] != climb.COL_EMPTY:
            raise AssertionError(f"hazard art overlaps collision at {tx},{row}")
        slots[row][tx] = METAL

    # Claim the cable's open-sky tiles for the metal line slot last. Cells on
    # the cabin, pole, posts or pines stay theirs, so the cable passes behind
    # them as a gap rather than a recolour.
    for tx, ty in sorted(cable_route_tiles()):
        if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in LANE_CELLS:
            continue
        if slots[ty][tx] == SKY:
            slots[ty][tx] = LINE
        assert slots[ty][tx] in (LINE, METAL), f"cable tile {tx},{ty} blocked by art"

    assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
    assert all(slots[ty][tx] == WINDOW for tx, ty in ridge.HOUSE_WINDOWS)
    return slots


class _Canvas:
    """Clip all painting to tiles whose assigned palette family matches."""

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
    # One flat night-family ridge mass behind the route. It is the same slot
    # as the sky, so rock and timber always win where they overlap.
    c.polygon(SKY, RIDGE_LINE + [(WIDTH, HEIGHT - 24), (0, HEIGHT - 24)], p[1])
    for points in RIDGE_HIGHLIGHTS:
        c.line(SKY, points, p[2])
    for x, y in RAIN_SLASHES:
        c.line(SKY, [(x, y), (x - 2, y + 4)], p[2])
    for x, y, index in SPARKS:
        c.point(SKY, (x, y), p[index])


def _draw_pines(c: _Canvas) -> None:
    p = PALETTES[FOLIAGE]
    for x, top, w, bottom in PINES:
        center = x + w // 2
        c.polygon(FOLIAGE, [(center, top), (x + 2, top + 11), (x + 5, top + 10),
                            (x, top + 20), (x + 5, top + 19), (x, bottom - 2),
                            (x + w, bottom - 2), (x + w - 5, top + 19),
                            (x + w, top + 20), (x + w - 5, top + 10),
                            (x + w - 2, top + 11)], p[1])
        c.line(FOLIAGE, [(center, top + 2), (center, bottom - 2)], p[0])
        c.line(FOLIAGE, [(center - 1, top + 7), (center - 3, top + 12)], p[2])


def _draw_rock(c: _Canvas, grid: list[list[int]]) -> None:
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != climb.COL_SOLID:
                continue
            slot = EARTH if ty > ridge.GROUND_ROW else STONE
            ramp = PALETTES[slot]
            x, y = tx * TILE, ty * TILE
            c.rect(slot, (x, y, x + 7, y + 7), ramp[1])
            # Exposed rock gets a lit surface edge; the joint seams are
            # diagonal, as in the climb rock.
            if ty == 0 or grid[ty - 1][tx] != climb.COL_SOLID:
                c.line(slot, [(x, y), (x + 7, y)], ramp[3])
            if (tx + ty) % 3 == 0:
                c.polygon(slot, [(x, y + 2), (x + 3, y), (x + 4, y + 2),
                                 (x + 2, y + 4)], ramp[0])
            else:
                c.line(slot, [(x + 1, y + 1), (x + 3, y + 2), (x + 2, y + 4)], ramp[0])
            c.line(slot, [(x + 5, y + 1), (x + 6, y + 3)], ramp[2])
            if (tx * 3 + ty) % 4 == 0:
                c.point(slot, (x + 6, y + 6), ramp[3])


def _draw_ledges(c: _Canvas) -> None:
    p = PALETTES[TIMBER]
    for row, x0, x1 in ridge.LEDGES:
        y = row * TILE
        left, right = x0 * TILE, x1 * TILE + 7
        # The light top edge is exactly the collision row's first pixel line.
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


def _draw_cabin(c: _Canvas) -> None:
    p = PALETTES[TIMBER]
    x0, x1, y0, y1 = ridge.HOUSE_RECT
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
    dx = ridge.HOUSE_DOOR[0] * TILE
    dy0 = (ridge.HOUSE_DOOR[1] - 2) * TILE
    c.rect(TIMBER, (dx, dy0, dx + 7, bottom), p[0])
    c.line(TIMBER, [(dx, dy0), (dx, bottom)], p[3])
    c.line(TIMBER, [(dx + 7, dy0), (dx + 7, bottom)], p[3])
    c.point(TIMBER, (dx + 5, dy0 + 12), p[3])


def _draw_windows(c: _Canvas) -> None:
    p = PALETTES[WINDOW]
    # Cold glass; the scene swaps this slot to warm when the line is live.
    for tx, ty in ridge.HOUSE_WINDOWS:
        x, y = tx * TILE, ty * TILE
        c.rect(WINDOW, (x, y, x + 7, y + 7), p[0])
        c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[1])
        c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[3])
        c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[2])
        c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[2])


def _draw_warnings(c: _Canvas) -> None:
    # Metal placards and brackets use indices 0 and 2 only; 1 and 3 are the lines'.
    p = PALETTES[METAL]
    for row, x0, x1 in ridge.hazard_lanes():
        left, right = x0 * TILE, x1 * TILE + 7
        y = row * TILE
        c.rect(METAL, (left + 2, y + 2, right - 2, y + 5), p[0])
        c.line(METAL, [(left + 4, y + 2), (right - 4, y + 5)], p[2])
        c.line(METAL, [(right - 4, y + 2), (left + 4, y + 5)], p[2])
    for _, x0, x1 in ridge.WHIP_LANES:
        left, right = (x0 - 1) * TILE + 1, (x1 + 2) * TILE - 2
        y = BRACKET_ROWS[0] * TILE
        c.rect(METAL, (left, y + 10, right, y + 13), p[2])       # crossarm
        c.line(METAL, [(left, y + 14), (right, y + 14)], p[0])
        for x in (left + 2, right - 3):                          # end brackets
            c.rect(METAL, (x, y + 4, x + 1, y + 9), p[2])


def _draw_cable(c: _Canvas, slots: list[list[int]]) -> None:
    """Paint line 1 (index 1) and line 2 (index 3) on claimed metal tiles only."""
    px = c.image.load()
    for pixels, index in ((line1_pixels(), ridge.LINE_COLOR_INDEX),
                          (line2_pixels(), ridge.LINE2_COLOR_INDEX)):
        color = PALETTES[LINE][index]
        for x, y in sorted(pixels):
            tx, ty = x // TILE, y // TILE
            if slots[ty][tx] == LINE and (ty, tx) not in LANE_CELLS:
                px[x, y] = color


def make_background() -> tuple[Image.Image, list[list[int]]]:
    """Return authored 480x144 RGB art and its 60x18 tile-palette map."""
    grid = ridge.collision_grid()
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
    _draw_pines(canvas)
    _draw_rock(canvas, grid)
    _draw_ledges(canvas)
    _draw_posts(canvas, grid)
    _draw_cabin(canvas)
    _draw_windows(canvas)
    _draw_warnings(canvas)
    _draw_cable(canvas, slots)

    allowed = [set(colors) for colors in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            for y in range(ty * TILE, ty * TILE + TILE):
                for x in range(tx * TILE, tx * TILE + TILE):
                    if image.getpixel((x, y)) not in allowed[slot]:
                        raise AssertionError(f"illegal palette color in tile {tx},{ty}")
    _check_geometry_art(image, grid, slots)
    return image, slots


def _check_geometry_art(image: Image.Image, grid: list[list[int]],
                        slots: list[list[int]]) -> None:
    for row, x0, x1 in ridge.LEDGES:
        py = row * TILE
        assert all(grid[row][x] == climb.COL_TOP for x in range(x0, x1 + 1))
        assert all(image.getpixel((x * TILE, py)) == PALETTES[TIMBER][3]
                   for x in range(x0, x1 + 1)), f"ledge lip drift on row {row}"
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                color = image.getpixel((tx * TILE + 3, ty * TILE + 3))
                assert color in PALETTES[slots[ty][tx]], f"rock miss at {tx},{ty}"
                assert slots[ty][tx] in (STONE, EARTH), f"solid not rock at {tx},{ty}"
    # Indices 1 and 3 in metal tiles are reserved for the two lines' pixels.
    for index, owner in ((ridge.LINE_COLOR_INDEX, line1_pixels()),
                         (ridge.LINE2_COLOR_INDEX, line2_pixels())):
        color = PALETTES[LINE][index]
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                if slot != LINE:
                    continue
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        if image.getpixel((x, y)) == color:
                            assert (x, y) in owner, f"stray line index {index} at {x},{y}"


def _gb_studio_native_index(green: int) -> int:
    if green < 65:
        return 3
    if green < 130:
        return 2
    if green < 205:
        return 1
    return 0


def encode_native_background(image: Image.Image,
                             slots: list[list[int]]) -> Image.Image:
    """Convert each authored ramp index to a canonical grayscale proxy."""
    if image.mode != "RGB" or image.size != (WIDTH, HEIGHT):
        raise ValueError(f"expected RGB {(WIDTH, HEIGHT)} author image")
    if len(slots) != ridge.MAP_H or any(len(row) != ridge.MAP_W for row in slots):
        raise ValueError(f"expected {ridge.MAP_W}x{ridge.MAP_H} palette grid")
    palette_indices = [{color: index for index, color in enumerate(palette)}
                       for palette in PALETTES]
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


def _unique_indexed_tiles(image: Image.Image, slots: list[list[int]]) -> int:
    patterns = set()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            pixels = tuple(image.getpixel((tx * TILE + x, ty * TILE + y))
                           for y in range(TILE) for x in range(TILE))
            patterns.add((slot, pixels))
    return len(patterns)


def _check_owned_outputs() -> None:
    expected_id = ridge.BACKGROUND_ID
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
    unique = _unique_indexed_tiles(proxy, slots)
    if unique > MAX_UNIQUE_TILES:
        raise AssertionError(
            f"wind_ridge uses {unique} unique indexed tiles (budget {MAX_UNIQUE_TILES})")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    proxy.save(OUTPUT, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": ridge.BACKGROUND_ID,
        "name": "wind_ridge",
        "symbol": "bg_wind_ridge",
        "filename": OUTPUT.name,
        "width": ridge.MAP_W,
        "height": ridge.MAP_H,
        "imageWidth": proxy.width,
        "imageHeight": proxy.height,
        "autoColor": False,
        "tileColors": collision_rle(slots, ridge.MAP_W, ridge.MAP_H),
    }
    SIDECAR.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    slot_counts = {slot: sum(value == slot for row in slots for value in row)
                   for slot in range(7)}
    print(f"generated {OUTPUT.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
          f"{unique} unique indexed tiles (budget {MAX_UNIQUE_TILES}), "
          f"palette tiles {slot_counts}")


if __name__ == "__main__":
    main()
