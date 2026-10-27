"""Generate the Pine Hollow background from the ``kiko.py`` contract.

Modelled on ``make_rosa_art.py``: the RGB image returned by
:func:`make_background` is the artist-facing source, and the compiler-facing
PNG is a grayscale index proxy that uses GB Studio's native index thresholds.
This generator owns only ``pine_hollow.png`` and its background sidecar.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import kiko
import opening
from make_climb_scene import collision_rle


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/pine_hollow.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
TILE = kiko.TILE
WIDTH, HEIGHT = kiko.MAP_W * TILE, kiko.MAP_H * TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
MAX_UNIQUE_TILES = 192

# BG palette families (opening.BG_PALETTES order). Slot 7 is the editor UI.
SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, EARTH = range(7)
LINE = climb.LINE_BG_SLOT
assert LINE == METAL, "cable slot must be the metal family"
assert kiko.WINDOW_BG_SLOT == WINDOW, "window slot must be the window family"

# Night hollow: a low forest hill behind the route. It stops at the floor top
# and never reaches the HUD rows (0-1).
HILL_LINE = [(0, 70), (20, 62), (40, 66), (64, 58), (88, 64), (112, 60),
             (136, 68), (160, 62), (184, 58), (208, 66), (232, 60), (256, 68),
             (280, 64), (304, 58), (320, 66)]
HILL_HIGHLIGHTS = [[(64, 58), (68, 64)], [(184, 58), (180, 64)],
                   [(304, 58), (300, 64)]]
# Stars above the cable run (pixel rows 16-27 only).
STARS = [(24, 20), (64, 26), (120, 20), (176, 24), (226, 20), (262, 26)]
# Pine silhouettes (x, top, w, bottom) in pixels, standing on the hill. Their
# tips rise above the hill line into open sky. They are drawn in the sky
# family, so they clip against the cable, mesa, cabin and gust placard.
PINES = [(14, 40, 14, 79), (30, 52, 10, 79), (46, 40, 16, 79),
         (102, 48, 12, 79), (196, 40, 14, 79), (214, 52, 10, 79),
         (240, 44, 14, 79)]

# The snapped utility pole (contract: kiko.DAMAGED_POLE, kiko.HOUSE_POLE) is the
# animated intro_pole actor (see make_kiko_scene); the background draws no pole.
# Each wire leaves a pole's top tile (kiko.WIRE_ROUTES).

# Downed-wire posts: one at each end of every arc lane, standing on the floor.
# Each entry is the post's top tile; the post is two tiles tall. Posts use the
# stone slot: the metal slot holds nothing but wire.
ARC_POST_TOPS = [(tx, row) for row, x0, x1 in kiko.ARC_LANES
                 for tx in (x0 - 1, x1 + 1)]
ARC_POST_TILES = [(tx, ty) for tx, top in ARC_POST_TOPS for ty in (top, top + 1)]

# Lane cells, arc and gust alike: no art may sit on them.
LANE_CELLS = {(row, x) for row, x0, x1 in kiko.hazard_lanes()
              for x in range(x0, x1 + 1)}


def _mask_pixels(draw) -> frozenset[tuple[int, int]]:
    mask = Image.new("1", (WIDTH + 2, HEIGHT + 2), 0)
    draw(ImageDraw.Draw(mask))
    w = mask.width
    return frozenset((i % w, i // w) for i, v in enumerate(mask.get_flattened_data()) if v)


def _polyline_pixels(route) -> frozenset[tuple[int, int]]:
    """2px-thick polyline through contract tile centres (inside the tile)."""
    pts = [(tx * TILE + 3, ty * TILE + 3) for tx, ty in route]

    def draw(d):
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
            d.line([(x + dx, y + dy) for x, y in pts], fill=1, width=1)
    return _mask_pixels(draw)


@functools.lru_cache(maxsize=None)
def stage_pixels(stage: int) -> frozenset[tuple[int, int]]:
    """Every pixel that may carry the wire colour index of ``stage``."""
    out: set[tuple[int, int]] = set()
    for s, route in kiko.WIRE_ROUTES:
        if s == stage:
            out |= _polyline_pixels(route)
    return frozenset(out)


@functools.lru_cache(maxsize=None)
def wire_tiles() -> frozenset[tuple[int, int]]:
    """(tx, ty) tiles any wire pixel touches."""
    return frozenset((x // TILE, y // TILE) for stage in range(1, kiko.STAGE_COUNT + 1)
                     for x, y in stage_pixels(stage))


def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int,
              y0: int, y1: int) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            slots[ty][tx] = slot


def _slots(grid: list[list[int]]) -> list[list[int]]:
    """Choose one palette family per tile, respecting the collision grid."""
    slots = [[SKY] * kiko.MAP_W for _ in range(kiko.MAP_H)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = EARTH if ty > kiko.GROUND_ROW else STONE
            elif cell == climb.COL_TOP:
                slots[ty][tx] = TIMBER

    # Pine silhouettes: sky family only, open air only, never on a lane.
    for x, top, w, bottom in PINES:
        for ty in range(top // TILE, (bottom - 1) // TILE + 1):
            for tx in range(x // TILE, (x + w - 1) // TILE + 1):
                if grid[ty][tx] == climb.COL_EMPTY and (ty, tx) not in LANE_CELLS:
                    slots[ty][tx] = SKY

    # The house: timber body over the floor, two lit windows, one door.
    x0, x1, y0, y1 = kiko.HOUSE_RECT
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            if grid[ty][tx] != climb.COL_EMPTY:
                raise AssertionError(f"house overlaps collision at {tx},{ty}")
    _set_rect(slots, TIMBER, x0, x1, y0, y1)
    # Each window owns exactly one whole tile; no other tile uses this slot.
    for tx, ty in kiko.HOUSE_WINDOWS:
        slots[ty][tx] = WINDOW

    # Downed-wire posts: stone family, open air, never on a lane.
    for tx, ty in ARC_POST_TILES:
        if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in LANE_CELLS:
            raise AssertionError(f"arc post overlaps collision or lane at {tx},{ty}")
        slots[ty][tx] = STONE

    # Gust lanes on the mesa get a stone hazard placard (the metal slot is wire only).
    for row, x0, x1 in kiko.GUST_LANES:
        for tx in range(x0, x1 + 1):
            if grid[row][tx] != climb.COL_EMPTY:
                raise AssertionError(f"gust placard overlaps collision at {tx},{row}")
            slots[row][tx] = STONE

    # Wire tiles take the metal slot last. They may never hit collision (power
    # enters through the left cliff wall), a lane, the cabin, a post or a placard.
    hx0, hx1, hy0, hy1 = kiko.HOUSE_RECT
    house = {(tx, ty) for ty in range(hy0, hy1 + 1) for tx in range(hx0, hx1 + 1)}
    posts = set(ARC_POST_TILES)
    for tx, ty in sorted(wire_tiles()):
        if grid[ty][tx] != climb.COL_EMPTY:
            assert tx == 0, f"wire tile {tx},{ty} inside collision"
            continue
        if (ty, tx) in LANE_CELLS or (tx, ty) in house or (tx, ty) in posts:
            raise AssertionError(f"wire tile {tx},{ty} collides with other art")
        if slots[ty][tx] != SKY:
            raise AssertionError(f"wire tile {tx},{ty} is not open sky")
        slots[ty][tx] = LINE

    assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
    assert all(slots[ty][tx] == STONE for tx, ty in ARC_POST_TILES)
    assert all(slots[ty][tx] == WINDOW for tx, ty in kiko.HOUSE_WINDOWS)
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
    # One flat night-family hill mass behind the route. It is the same slot as
    # the sky, so rock and timber always win where they overlap.
    c.polygon(SKY, HILL_LINE + [(WIDTH, HEIGHT - 24), (0, HEIGHT - 24)], p[1])
    for points in HILL_HIGHLIGHTS:
        c.line(SKY, points, p[2])
    for x, y in STARS:
        c.point(SKY, (x, y), p[2])


def _draw_pines(c: _Canvas) -> None:
    # Silhouettes in the sky family: hill colour for the body, so the tiers
    # read against the darker open sky above the hill line.
    p = PALETTES[SKY]
    for x, top, w, bottom in PINES:
        center = x + w // 2
        c.polygon(SKY, [(center, top), (x + 2, top + 11), (x + 5, top + 10),
                        (x, top + 20), (x + 5, top + 19), (x, bottom - 2),
                        (x + w, bottom - 2), (x + w - 5, top + 19),
                        (x + w, top + 20), (x + w - 5, top + 10),
                        (x + w - 2, top + 11)], p[1])
        c.line(SKY, [(center, top + 2), (center, bottom - 2)], p[0])
        c.line(SKY, [(center - 1, top + 7), (center - 3, top + 12)], p[2])


def _draw_rock(c: _Canvas, grid: list[list[int]]) -> None:
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != climb.COL_SOLID:
                continue
            slot = EARTH if ty > kiko.GROUND_ROW else STONE
            ramp = PALETTES[slot]
            x, y = tx * TILE, ty * TILE
            c.rect(slot, (x, y, x + 7, y + 7), ramp[1])
            # Exposed rock gets a lit surface edge; the joint seams are
            # diagonal, as in the climb rock. Step and mesa read as one stone.
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


def _draw_cabin(c: _Canvas) -> None:
    p = PALETTES[TIMBER]
    x0, x1, y0, y1 = kiko.HOUSE_RECT
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
    dx = kiko.HOUSE_DOOR[0] * TILE
    dy0 = (kiko.HOUSE_DOOR[1] - 2) * TILE
    c.rect(TIMBER, (dx, dy0, dx + 7, bottom), p[0])
    c.line(TIMBER, [(dx, dy0), (dx, bottom)], p[3])
    c.line(TIMBER, [(dx + 7, dy0), (dx + 7, bottom)], p[3])
    c.point(TIMBER, (dx + 5, dy0 + 12), p[3])


def _draw_windows(c: _Canvas) -> None:
    p = PALETTES[WINDOW]
    # Cold glass; the scene swaps this slot to warm when the line is live.
    for tx, ty in kiko.HOUSE_WINDOWS:
        x, y = tx * TILE, ty * TILE
        c.rect(WINDOW, (x, y, x + 7, y + 7), p[0])
        c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[1])
        c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[3])
        c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[2])
        c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[2])


def _draw_arc_posts(c: _Canvas) -> None:
    # Stone-family posts (the metal slot is wire only).
    p = PALETTES[STONE]
    for tx, top in ARC_POST_TOPS:
        x = tx * TILE + 3
        y0, y1 = top * TILE + 2, (top + 2) * TILE - 1
        c.rect(STONE, (x, y0, x + 1, y1), p[0])
        c.line(STONE, [(x + 2, y0), (x + 2, y1)], p[2])
        c.rect(STONE, (x - 1, y0, x + 3, y0 + 1), p[3])


def _draw_warnings(c: _Canvas) -> None:
    # Stone-family placards on the mesa (the metal slot is wire only).
    p = PALETTES[STONE]
    for row, x0, x1 in kiko.GUST_LANES:
        left, right = x0 * TILE, x1 * TILE + 7
        y = row * TILE
        c.rect(STONE, (left + 2, y + 2, right - 2, y + 5), p[0])
        c.line(STONE, [(left + 4, y + 2), (right - 4, y + 5)], p[2])
        c.line(STONE, [(right - 4, y + 2), (left + 4, y + 5)], p[2])
        center = (left + right) // 2
        c.line(STONE, [(center - 2, y + 3), (center + 2, y + 3)], p[3])
        c.line(STONE, [(center, y + 1), (center, y + 6)], p[3])


def _draw_cable(c: _Canvas, slots: list[list[int]]) -> None:
    """Paint each stage's wire pixels in its metal colour index, on claimed wire tiles only."""
    px = c.image.load()
    for stage in range(1, kiko.STAGE_COUNT + 1):
        color = PALETTES[LINE][kiko.STAGE_COLOR_INDEX[stage - 1]]
        for x, y in sorted(stage_pixels(stage)):
            if x < WIDTH and y < HEIGHT and slots[y // TILE][x // TILE] == LINE:
                px[x, y] = color


def make_background() -> tuple[Image.Image, list[list[int]]]:
    """Return authored 320x144 RGB art and its 40x18 tile-palette map."""
    grid = kiko.collision_grid()
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
    _draw_cabin(canvas)
    _draw_windows(canvas)
    _draw_arc_posts(canvas)
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
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                color = image.getpixel((tx * TILE + 3, ty * TILE + 3))
                assert color in PALETTES[slots[ty][tx]], f"rock miss at {tx},{ty}"
                assert slots[ty][tx] in (STONE, EARTH), f"solid not rock at {tx},{ty}"
    # Metal-slot pixels of each stage's index belong to that stage's wire only.
    for stage in range(1, kiko.STAGE_COUNT + 1):
        color = PALETTES[LINE][kiko.STAGE_COLOR_INDEX[stage - 1]]
        owner = stage_pixels(stage)
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                if slot != LINE:
                    continue
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        if image.getpixel((x, y)) == color:
                            assert (x, y) in owner, f"stray stage {stage} wire at {x},{y}"


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
    if len(slots) != kiko.MAP_H or any(len(row) != kiko.MAP_W for row in slots):
        raise ValueError(f"expected {kiko.MAP_W}x{kiko.MAP_H} palette grid")
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
    expected_id = kiko.BACKGROUND_ID
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
            f"pine_hollow uses {unique} unique indexed tiles (budget {MAX_UNIQUE_TILES})")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    proxy.save(OUTPUT, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": kiko.BACKGROUND_ID,
        "name": "pine_hollow",
        "symbol": "bg_pine_hollow",
        "filename": OUTPUT.name,
        "width": kiko.MAP_W,
        "height": kiko.MAP_H,
        "imageWidth": proxy.width,
        "imageHeight": proxy.height,
        "autoColor": False,
        "tileColors": collision_rle(slots, kiko.MAP_W, kiko.MAP_H),
    }
    SIDECAR.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    slot_counts = {slot: sum(value == slot for row in slots for value in row)
                   for slot in range(7)}
    print(f"generated {OUTPUT.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
          f"{unique} unique indexed tiles (budget {MAX_UNIQUE_TILES}), "
          f"palette tiles {slot_counts}")


if __name__ == "__main__":
    main()
