"""Generate the authored, collision-aligned Storm Climb background.

The RGB image returned by :func:`make_background` is the artist-facing source.
The compiler-facing PNG is a grayscale index proxy, matching the native
GB Studio color-index thresholds.  This generator owns only
``storm_climb.png`` and its background sidecar.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import opening
from make_climb_scene import collision_rle, resource_id


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/storm_climb.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
WIDTH, HEIGHT = climb.MAP_W * climb.TILE, climb.MAP_H * climb.TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
# Marta's two windows flank the door; slot 3 is reserved for them alone.
SUMMIT_WINDOW_TILES = ((11, 4), (14, 4))
LANE_CELLS = {
    (row, x) for row, x0, x1 in climb.GUST_LANES for x in range(x0, x1 + 1)
}

# Marta's broken line (gameplay contract: climb.DAMAGED_POLE / JUNCTION_BOX).
# A snapped timber pole stands on the shelf-21 pickup corner; its cable hangs
# from the top, rises to row 11, sags across the mountain and drops into the
# junction box.  Cable pixels are only painted on empty sky/ridge tiles, which
# are claimed for BG slot 5 (LINE_BG_SLOT).  Posts, foliage, windows and shelf
# or rock tiles are never claimed, so the line passes behind them as gaps.
POLE_TILES = ((4, 16), (4, 17), (4, 18), (4, 19), (4, 20))  # (tx, ty), base on row 21
CROSSARM_TILES = ((3, 17), (5, 17))
CABLE_ATTACH = (44, 133)      # tile (5,16): just right of the snapped pole top
CABLE_CORNER = (50, 88)       # tile (6,11): leaves the pole on row 11
CABLE_SPAN_END = (134, 88)    # tile (16,11): end of the sagging span
CABLE_SPAN_SAG = 5            # pixels the span dips below its chord at mid-span
CABLE_BOX_DROP = (138, 100)   # tile (17,12)
CABLE_BOX_TOP = (139, 111)    # tile (17,13): directly above the junction box


@functools.lru_cache(maxsize=None)
def cable_waypoints() -> tuple[tuple[int, int], ...]:
    """Pixel polyline for the cable: pole, rise, sagging span, box drop."""
    x0, y0 = CABLE_CORNER
    x1, y1 = CABLE_SPAN_END
    assert y0 == y1, "span must be level at both ends"
    mid, half = (x0 + x1) / 2, (x1 - x0) / 2
    span = [(x, round(y0 + CABLE_SPAN_SAG * (1 - ((x - mid) / half) ** 2)))
            for x in range(x0, x1 + 1)]
    return (CABLE_ATTACH, *span, CABLE_BOX_DROP, CABLE_BOX_TOP)


@functools.lru_cache(maxsize=None)
def cable_pixels() -> frozenset[tuple[int, int]]:
    """Every (x, y) pixel the 1px cable would occupy before tile occlusion."""
    mask = Image.new("1", (WIDTH, HEIGHT), 0)
    ImageDraw.Draw(mask).line(list(cable_waypoints()), fill=255, width=1)
    return frozenset((x, y) for y in range(HEIGHT) for x in range(WIDTH)
                     if mask.getpixel((x, y)))


@functools.lru_cache(maxsize=None)
def cable_route_tiles() -> frozenset[tuple[int, int]]:
    """(tx, ty) tiles the cable passes through; some may be occluded."""
    return frozenset((x // 8, y // 8) for x, y in cable_pixels())


def _set_slot(slots: list[list[int]], tx: int, ty: int, slot: int,
              *, empty_only: bool = False) -> bool:
    if not (0 <= tx < climb.MAP_W and 0 <= ty < climb.MAP_H):
        return False
    if empty_only and slots[ty][tx] != 0:
        return False
    slots[ty][tx] = slot
    return True


def _set_rect(slots: list[list[int]], slot: int, x0: int, x1: int,
              y0: int, y1: int, *, empty_only: bool = False) -> None:
    for ty in range(y0, y1 + 1):
        for tx in range(x0, x1 + 1):
            _set_slot(slots, tx, ty, slot, empty_only=empty_only)


def _slots(grid: list[list[int]]) -> list[list[int]]:
    """Choose palette families by tile while respecting authored geometry."""
    slots = [[0] * climb.MAP_W for _ in range(climb.MAP_H)]
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell == climb.COL_SOLID:
                slots[ty][tx] = 6 if ty >= 34 else 1
            elif cell == climb.COL_TOP:
                slots[ty][tx] = 2

    # Layered blue-violet mountain silhouettes.  Their irregular stepped
    # profiles stay behind the route; the actual rock collisions remain the
    # opaque, nearer buttresses and ground.
    ridge_spans = {
        0: [(0, 6), (16, 19)],
        1: [(0, 7), (15, 19)],
        2: [(0, 8), (17, 19)],
        3: [(0, 7), (16, 19)],
        4: [(0, 5), (17, 19)],
        5: [(0, 4), (18, 19)],
        7: [(0, 2), (18, 19)],
        8: [(0, 3), (18, 19)],
        9: [(0, 4), (19, 19)],
        11: [(0, 5), (16, 19)],
        12: [(0, 4), (17, 19)],
        14: [(0, 4), (16, 19)],
        15: [(0, 3), (17, 19)],
        17: [(0, 4), (16, 19)],
        18: [(0, 3), (17, 19)],
        20: [(0, 4), (16, 19)],
        21: [(0, 3), (17, 19)],
        23: [(0, 4), (16, 19)],
        24: [(0, 3), (17, 19)],
        26: [(0, 4), (16, 19)],
        27: [(0, 3), (17, 19)],
        29: [(0, 4), (16, 19)],
        30: [(0, 3), (17, 19)],
        32: [(0, 2), (17, 19)],
    }
    for ty, spans in ridge_spans.items():
        for x0, x1 in spans:
            _set_rect(slots, 1, x0, x1, ty, ty, empty_only=True)

    # Foliage frames the route at the cliff margins, not over the jump lanes.
    foliage = [
        (0, 2, 8, 9), (0, 1, 10, 11), (0, 3, 15, 16),
        (0, 2, 21, 22), (0, 2, 24, 24), (0, 3, 28, 29),
        (0, 2, 31, 31), (17, 19, 8, 9), (18, 19, 12, 13),
        (17, 19, 18, 18), (17, 19, 21, 21), (17, 19, 24, 24),
        (17, 19, 27, 27), (17, 19, 30, 31),
    ]
    for x0, x1, y0, y1 in foliage:
        _set_rect(slots, 4, x0, x1, y0, y1, empty_only=True)

    # Powered home: reserve its small facade/window area above the summit walk.
    _set_rect(slots, 2, 8, 17, 1, 5)
    # Each lit window owns exactly one whole tile, so the checkpoint's slot-3
    # palette swap warms both windows and nothing else on the facade.
    for tx, ty in SUMMIT_WINDOW_TILES:
        _set_slot(slots, tx, ty, 3)

    # Base substation and its timber service frame near the spawn. The player
    # remains in front of this background structure at (2,32).
    _set_rect(slots, 5, 0, 4, 28, 32, empty_only=True)
    _set_rect(slots, 2, 0, 4, 27, 27, empty_only=True)

    # Two metal mast fragments and the torn conductor link infrastructure up
    # the cliff. Only sky/backdrop cells are claimed; platforms remain visible.
    for tx, ty in [(5, 29), (5, 30), (5, 31), (6, 31), (8, 24),
                   (8, 23), (14, 17), (14, 16), (6, 9), (6, 8)]:
        _set_slot(slots, tx, ty, 5, empty_only=True)

    # Marta's snapped timber pole and crossarm, on empty sky next to the pickup.
    for tx, ty in (*POLE_TILES, *CROSSARM_TILES):
        if grid[ty][tx] != climb.COL_EMPTY:
            raise AssertionError(f"grid pole overlaps collision at {tx},{ty}")
        slots[ty][tx] = 2

    # These are currently static reset lanes.  Give every lane a distinct
    # metal-backed warning marker; do not imply a timed gust animation.
    for row, x0, x1 in climb.GUST_LANES:
        for tx in range(x0, x1 + 1):
            if grid[row][tx] != climb.COL_EMPTY:
                raise AssertionError(f"static warning overlaps collision at {tx},{row}")
            slots[row][tx] = 5

    # Catwalk supports are only vertical timber posts below the exact collision
    # row. They stop at the next occupied tile or at a marked warning lane.
    for row, x0, x1 in climb.PLATFORMS:
        support_xs = sorted({x0, x1, *range(x0 + 3, x1, 4)})
        for tx in support_xs:
            for ty in range(row + 1, min(row + 4, climb.MAP_H)):
                if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in LANE_CELLS:
                    break
                if slots[ty][tx] in (3, 4, 5):
                    break
                slots[ty][tx] = 2

    # Claim the cable's empty sky/ridge tiles for the metal line slot, after
    # posts and lanes are placed. Posts, foliage, windows and shelves keep
    # their slots, so the line passes behind them as a gap, not a recolour.
    for tx, ty in sorted(cable_route_tiles()):
        if grid[ty][tx] != climb.COL_EMPTY or (ty, tx) in LANE_CELLS:
            continue
        if slots[ty][tx] == climb.LINE_BG_SLOT:
            raise AssertionError(f"cable route crosses existing slot-5 tile {tx},{ty}")
        if slots[ty][tx] in (0, 1):
            slots[ty][tx] = climb.LINE_BG_SLOT

    # Keep the editor's UI palette reserved and unused by background tiles.
    assert all(slot in range(7) for row in slots for slot in row)
    assert all(slots[row][x] == 2 for row, x0, x1 in climb.PLATFORMS
               for x in range(x0, x1 + 1))
    assert all(slots[row][x] == 5 for row, x0, x1 in climb.GUST_LANES
               for x in range(x0, x1 + 1))
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
                if rgba[3] and self.slots[y // 8][x // 8] == slot:
                    px[x, y] = rgba[:3]

    @staticmethod
    def _rgba(color):
        return tuple(color) + (255,)

    def rect(self, slot: int, box, color, outline=None, width=1) -> None:
        fill = self._rgba(color)
        edge = self._rgba(outline) if outline is not None else None
        self._apply(slot, lambda d: d.rectangle(box, fill=fill, outline=edge,
                                                 width=width))

    def line(self, slot: int, points, color, width=1) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.line(points, fill=rgba, width=width))

    def polygon(self, slot: int, points, color) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.polygon(points, fill=rgba))

    def point(self, slot: int, xy, color) -> None:
        rgba = self._rgba(color)
        self._apply(slot, lambda d: d.point(xy, fill=rgba))


def _draw_terrain(c: _Canvas, grid: list[list[int]]) -> None:
    p = PALETTES
    # Distant ridges have broad, cool facets and restrained summit catches.
    c.polygon(1, [(-4, 52), (5, 44), (17, 48), (32, 31), (44, 37),
                  (58, 25), (72, 34), (85, 26), (101, 39), (117, 30),
                  (133, 40), (149, 28), (164, 38), (164, 66), (-4, 66)], p[1][1])
    c.polygon(1, [(-3, 60), (12, 50), (25, 57), (39, 44), (53, 52),
                  (68, 42), (84, 54), (100, 43), (116, 52), (133, 42),
                  (148, 52), (163, 46), (163, 73), (-3, 73)], p[1][0])
    # Distant ranges in the night-sky family continue behind the playable
    # route. Keeping these in slot 0 makes them low-contrast atmosphere rather
    # than false solid ledges.
    c.polygon(0, [(-3, 105), (11, 94), (24, 100), (39, 87), (52, 95),
                  (68, 83), (84, 96), (99, 86), (114, 98), (130, 87),
                  (147, 98), (163, 90), (163, 132), (-3, 132)], p[0][1])
    c.polygon(0, [(-3, 121), (13, 111), (27, 118), (43, 106), (57, 116),
                  (74, 103), (89, 116), (106, 105), (123, 118), (140, 106),
                  (163, 120), (163, 139), (-3, 139)], p[0][2])
    for points in [
        [(4, 47), (17, 48), (30, 34), (39, 36), (27, 43), (19, 52), (8, 51)],
        [(56, 28), (62, 26), (73, 35), (67, 32)],
        [(113, 34), (118, 31), (132, 40), (125, 38)],
        [(147, 31), (151, 29), (162, 38), (156, 36)],
    ]:
        c.polygon(1, points, p[1][2])
    for points in [[(32, 32), (36, 31), (40, 35)],
                   [(58, 26), (62, 25), (65, 29)],
                   [(117, 31), (120, 30), (123, 33)],
                   [(149, 29), (152, 28), (155, 31)]]:
        c.line(1, points, p[1][3])

    # The lower route gets a second, subdued cliff horizon rather than a
    # vertically stretched opening backdrop.
    c.polygon(1, [(-2, 149), (12, 138), (24, 145), (36, 132), (49, 139),
                  (63, 128), (77, 138), (90, 130), (105, 141), (120, 132),
                  (136, 143), (151, 132), (162, 139), (162, 165), (-2, 165)], p[1][0])
    c.polygon(1, [(-2, 229), (12, 220), (25, 226), (40, 214), (54, 221),
                  (68, 211), (82, 222), (99, 213), (114, 224), (130, 214),
                  (146, 225), (162, 216), (162, 246), (-2, 246)], p[1][0])
    c.polygon(0, [(-2, 181), (12, 171), (25, 178), (41, 164), (57, 174),
                  (74, 160), (90, 173), (107, 161), (122, 175), (140, 163),
                  (162, 177), (162, 207), (-2, 207)], p[0][1])
    c.polygon(0, [(-2, 201), (14, 191), (29, 198), (45, 185), (61, 196),
                  (78, 181), (96, 195), (111, 184), (128, 198), (145, 185),
                  (162, 198), (162, 216), (-2, 216)], p[0][2])
    c.polygon(0, [(-2, 258), (14, 246), (28, 253), (42, 241), (59, 252),
                  (75, 238), (92, 251), (109, 239), (126, 253), (142, 241),
                  (162, 254), (162, 276), (-2, 276)], p[0][1])
    for x, y in [(13, 142), (37, 136), (64, 131), (91, 133),
                 (121, 135), (151, 135), (14, 223), (41, 217),
                 (69, 214), (100, 216), (132, 217)]:
        c.line(1, [(x, y), (x + 2, y - 1)], p[1][2])

    # Uneven stone planes in collision blocks: every solid tile is filled
    # edge-to-edge, with diagonal seams rather than shelf-like highlights.
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != climb.COL_SOLID:
                continue
            x, y = tx * 8, ty * 8
            slot = 6 if ty >= 34 else 1
            ramp = p[slot]
            c.rect(slot, (x, y, x + 7, y + 7), ramp[1])
            if (tx + ty) % 3 == 0:
                c.polygon(slot, [(x, y + 2), (x + 3, y), (x + 4, y + 2),
                                 (x + 2, y + 4)], ramp[0])
            else:
                c.line(slot, [(x + 1, y + 1), (x + 3, y + 2), (x + 2, y + 4)], ramp[0])
            c.line(slot, [(x + 5, y + 1), (x + 6, y + 3)], ramp[2])
            if (tx * 3 + ty) % 4 == 0:
                c.point(slot, (x + 6, y + 6), ramp[3])
    # Valley bedrock has broad earthen strata, still fully opaque.
    c.polygon(6, [(0, 278), (29, 278), (39, 282), (67, 282), (77, 278),
                  (109, 278), (121, 283), (151, 283), (160, 278),
                  (160, 288), (0, 288)], p[6][2])
    for x, y in [(11, 280), (45, 285), (87, 281), (132, 286)]:
        c.line(6, [(x, y), (x + 5, y - 1)], p[6][0])


def _draw_foliage(c: _Canvas) -> None:
    p = PALETTES[4]
    # Fir bough silhouettes are built from short downward/diagonal tiers, not
    # flat shelves; all strokes are clipped to reserved foliage tiles.
    pines = [
        (4, 75, 11, 102), (25, 123, 34, 147), (3, 169, 12, 196),
        (20, 205, 29, 232), (2, 247, 12, 276),
        (143, 78, 153, 106), (126, 111, 137, 139),
        (145, 157, 156, 185), (128, 194, 139, 221),
        (145, 235, 155, 264),
    ]
    for index, (x, y, w, h) in enumerate(pines):
        center = x + w // 2
        c.polygon(4, [(center, y), (x + 2, y + 11), (x + 5, y + 10),
                      (x, y + 20), (x + 5, y + 19), (x, h - 2),
                      (x + w, h - 2), (x + w - 5, y + 19), (x + w, y + 20),
                      (x + w - 5, y + 10), (x + w - 2, y + 11)], p[1])
        c.line(4, [(center, y + 2), (center, h - 2)], p[0])
        c.line(4, [(center - 1, y + 7), (center - 3, y + 12)], p[2])
        if index % 2 == 0:
            c.point(4, (center + 1, y + 16), p[3])


def _draw_platforms(c: _Canvas) -> None:
    p = PALETTES[2]
    for row, x0, x1 in climb.PLATFORMS:
        y = row * 8
        left, right = x0 * 8, x1 * 8 + 7
        # The light top edge is exactly the collision row's first pixel.
        c.line(2, [(left, y), (right, y)], p[3], 1)
        c.line(2, [(left, y + 1), (right, y + 1)], p[2], 1)
        c.rect(2, (left, y + 2, right, y + 4), p[1])
        c.line(2, [(left, y + 5), (right, y + 5)], p[0])
        c.line(2, [(left, y + 6), (right, y + 6)], p[0])
        # Repeating short plank seams and occasional fastening pegs.
        for x in range(left + 10, right - 2, 16):
            c.line(2, [(x, y + 2), (x, y + 4)], p[0])
            c.point(2, (x + 3, y + 2), p[3])


def _draw_supports(c: _Canvas, slots: list[list[int]]) -> None:
    p = PALETTES[2]
    for row, x0, x1 in climb.PLATFORMS:
        supports = sorted({x0, x1, *range(x0 + 3, x1, 4)})
        for tx in supports:
            for ty in range(row + 1, min(row + 4, climb.MAP_H)):
                if slots[ty][tx] != 2 or (ty, tx) in LANE_CELLS:
                    break
                x, y = tx * 8 + 3, ty * 8
                c.line(2, [(x, y), (x, y + 7)], p[0], 2)
                c.line(2, [(x + 2, y), (x + 2, y + 7)], p[2])


def _draw_home(c: _Canvas) -> None:
    p = PALETTES
    # A compact powered service home, perched above the summit walk.
    c.polygon(2, [(69, 35), (84, 12), (104, 3), (124, 15), (140, 35),
                  (134, 38), (121, 23), (104, 14), (86, 23), (75, 38)], p[2][0])
    c.polygon(2, [(75, 34), (87, 19), (104, 8), (121, 19), (135, 34),
                  (128, 34), (119, 24), (104, 16), (88, 25), (81, 34)], p[2][2])
    c.rect(2, (81, 31, 128, 47), p[2][1])
    c.line(2, [(82, 32), (82, 46)], p[2][3])
    c.line(2, [(127, 32), (127, 46)], p[2][0])
    c.rect(2, (99, 36, 108, 47), p[2][0])
    c.point(2, (105, 41), p[2][3])
    # Slot 3 is the selective power/window family; bright source index 3 marks
    # a lit room without warming the whole facade.
    for tx, ty in SUMMIT_WINDOW_TILES:
        x, y = tx * 8, ty * 8
        c.rect(3, (x, y, x + 7, y + 7), p[3][0])
        c.rect(3, (x + 1, y + 1, x + 6, y + 6), p[3][1])
        c.rect(3, (x + 2, y + 2, x + 5, y + 5), p[3][3])
        c.line(3, [(x + 3, y + 2), (x + 3, y + 5)], p[3][2])
        c.line(3, [(x + 2, y + 4), (x + 5, y + 4)], p[3][2])


def _draw_infrastructure(c: _Canvas) -> None:
    p = PALETTES
    # Service cabinet and timber mounting frame at the valley start.
    c.rect(2, (0, 225, 39, 231), p[2][0])
    c.rect(2, (2, 222, 38, 224), p[2][2])
    c.line(2, [(4, 226), (4, 262)], p[2][2], 2)
    c.line(2, [(37, 226), (37, 262)], p[2][2], 2)
    c.rect(5, (8, 230, 31, 262), p[5][0])
    c.line(5, [(9, 230), (30, 230)], p[5][3])
    c.line(5, [(9, 231), (9, 260)], p[5][2])
    c.rect(5, (12, 234, 27, 237), p[5][2])
    c.rect(5, (12, 240, 27, 256), p[5][0])
    c.line(5, [(14, 242), (25, 242)], p[5][2])
    c.line(5, [(14, 245), (17, 245)], p[5][3])
    c.line(5, [(14, 249), (17, 249)], p[5][3])
    c.line(5, [(14, 253), (23, 253)], p[5][2])

    # Two narrow mast remnants and a snapped conductor, articulated in metal.
    c.line(5, [(44, 263), (44, 226)], p[5][2], 2)
    c.line(5, [(41, 230), (47, 230)], p[5][3])
    c.line(5, [(44, 229), (56, 221), (69, 217), (80, 210)], p[5][2])
    c.line(5, [(82, 208), (91, 204), (101, 194)], p[5][2])
    c.line(5, [(103, 193), (111, 187), (119, 181)], p[5][2])
    c.line(5, [(121, 179), (126, 176)], p[5][2])
    c.line(5, [(126, 176), (130, 177)], p[5][3])
    c.line(5, [(136, 170), (136, 145)], p[5][2], 2)
    c.line(5, [(132, 149), (140, 149)], p[5][3])
    c.line(5, [(136, 148), (125, 143), (115, 141)], p[5][2])
    # Broken ceramic forks make the conductor visibly torn, not a clean line.
    c.line(5, [(123, 141), (121, 138)], p[5][3])
    c.line(5, [(126, 143), (129, 140)], p[5][2])
    c.line(5, [(131, 141), (134, 138)], p[5][3])


def _draw_warnings(c: _Canvas) -> None:
    p = PALETTES[5]
    for row, x0, x1 in climb.GUST_LANES:
        left, right = x0 * 8, x1 * 8 + 7
        y = row * 8
        # Fixed, high-contrast metal hazard placard. Cross center pixels use
        # palette index 3 and are visible in the compiler proxy as native 3.
        c.rect(5, (left + 2, y + 2, right - 2, y + 5), p[0])
        c.line(5, [(left + 4, y + 2), (right - 4, y + 5)], p[2])
        c.line(5, [(right - 4, y + 2), (left + 4, y + 5)], p[2])
        center = (left + right) // 2
        c.line(5, [(center - 2, y + 3), (center + 2, y + 3)], p[3])
        c.line(5, [(center, y + 1), (center, y + 6)], p[3])


def _draw_grid_pole(c: _Canvas) -> None:
    p = PALETTES[2]
    # Snapped timber stub standing on the shelf-21 pickup corner, with one
    # crossarm just under its broken top.  Painting is clipped to POLE tiles.
    c.line(2, [(35, 130), (34, 167)], p[2], 2)
    c.line(2, [(33, 131), (32, 167)], p[3])
    c.line(2, [(24, 138), (47, 138)], p[1])
    c.line(2, [(24, 139), (47, 139)], p[0])
    c.point(2, (24, 137), p[3])
    c.point(2, (47, 137), p[3])


def _draw_cable(c: _Canvas, slots: list[list[int]]) -> None:
    """Paint the cable in LINE_COLOR_INDEX on claimed slot-5 route tiles only."""
    color = PALETTES[climb.LINE_BG_SLOT][climb.LINE_COLOR_INDEX]
    px = c.image.load()
    for x, y in sorted(cable_pixels()):
        tx, ty = x // 8, y // 8
        if slots[ty][tx] == climb.LINE_BG_SLOT and (ty, tx) not in LANE_CELLS:
            px[x, y] = color


def _draw_sky(c: _Canvas) -> None:
    p = PALETTES[0]
    # Small rain slashes and isolated storm lights leave the climbing corridor
    # legible. Repeated marks share patterns to keep native tile use bounded.
    for x, y, color in [(20, 16, 2), (52, 20, 3), (136, 12, 2),
                        (148, 65, 3), (21, 112, 2), (101, 126, 3),
                        (40, 181, 2), (91, 202, 3), (151, 227, 2)]:
        c.point(0, (x, y), p[color])
    for x, y in [(71, 14), (121, 76), (92, 112), (67, 157),
                 (112, 190), (53, 235)]:
        c.line(0, [(x, y), (x - 2, y + 4)], p[1])
    # A broken storm cloud edge in the upper-left sky.
    c.line(0, [(8, 63), (17, 61), (22, 63)], p[1], 2)
    c.line(0, [(11, 66), (16, 65)], p[2])


def make_background() -> tuple[Image.Image, list[list[int]]]:
    """Return authored 160x288 RGB art and its 20x36 tile-palette map."""
    grid = climb.collision_grid()
    slots = _slots(grid)
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            color = PALETTES[slot][0]
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    pixels[x, y] = color
    canvas = _Canvas(image, slots)
    _draw_terrain(canvas, grid)
    _draw_foliage(canvas)
    _draw_platforms(canvas)
    _draw_supports(canvas, slots)
    _draw_home(canvas)
    _draw_infrastructure(canvas)
    _draw_warnings(canvas)
    _draw_grid_pole(canvas)
    _draw_cable(canvas, slots)
    _draw_sky(canvas)

    # Every material remains within its one tile palette's four native colors.
    allowed = [set(colors) for colors in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    if image.getpixel((x, y)) not in allowed[slot]:
                        raise AssertionError(f"illegal palette color in tile {tx},{ty}")
    _check_geometry_art(image, grid)
    return image, slots


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
    if len(slots) != climb.MAP_H or any(len(row) != climb.MAP_W for row in slots):
        raise ValueError(f"expected {climb.MAP_W}x{climb.MAP_H} palette grid")
    palette_indices = [{color: index for index, color in enumerate(palette)}
                       for palette in PALETTES]
    proxy = Image.new("RGB", image.size)
    src, dst = image.load(), proxy.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            slot = slots[y // 8][x // 8]
            try:
                intended = palette_indices[slot][src[x, y]]
            except (IndexError, KeyError) as exc:
                raise ValueError(f"invalid palette/color at {x},{y}") from exc
            gray = NATIVE_PROXY_BY_INDEX[intended]
            if _gb_studio_native_index(gray) != intended:
                raise AssertionError(f"proxy brightness mismatch at {x},{y}")
            dst[x, y] = (gray, gray, gray)
    return proxy


def _unique_indexed_tiles(image: Image.Image,
                          slots: list[list[int]]) -> int:
    patterns = set()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            pixels = tuple(image.getpixel((tx * 8 + x, ty * 8 + y))
                           for y in range(8) for x in range(8))
            patterns.add((slot, pixels))
    return len(patterns)


def _check_geometry_art(image: Image.Image, grid: list[list[int]]) -> None:
    # All ten collision rows have a bright timber edge at exactly y=row*8.
    for row, x0, x1 in climb.PLATFORMS:
        py = row * 8
        assert all(grid[row][x] == climb.COL_TOP for x in range(x0, x1 + 1))
        assert all(image.getpixel((x * 8, py)) == PALETTES[2][3]
                   for x in range(x0, x1 + 1)), f"platform lip drift on row {row}"
        assert grid[row][x0] == climb.COL_TOP
    for x0, x1, row0, row1 in climb.SOLID_BLOCKS:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                assert grid[row][x] == climb.COL_SOLID
                color = image.getpixel((x * 8 + 3, row * 8 + 3))
                assert color in PALETTES[6 if row >= 34 else 1]


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
    unique = _unique_indexed_tiles(proxy, slots)
    if unique >= 300:
        raise AssertionError(f"storm_climb uses {unique} unique indexed tiles (target <300)")
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
    contents = json.dumps(resource, indent=2) + "\n"
    SIDECAR.write_text(contents, encoding="utf-8")
    slot_counts = {slot: sum(value == slot for row in slots for value in row)
                   for slot in range(7)}
    print(f"generated {OUTPUT.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
          f"{unique} unique indexed tiles (<300 target), palette tiles {slot_counts}")


if __name__ == "__main__":
    main()
