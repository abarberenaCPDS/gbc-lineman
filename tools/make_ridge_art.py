"""Generate Hiroshi's two ridge backgrounds (job 2) from the ``ridge.py`` contract.

Modelled on ``make_climb_art.py``: the RGB image returned by
:meth:`SceneArt.make_background` is the artist-facing source, and the
compiler-facing PNG is a grayscale index proxy that uses GB Studio's native
index thresholds. This generator owns ``wind_ridge.png`` (2A, background ID
kept from the 100x30 level) and ``ridge_saddle.png`` (2B) and their sidecars.

Functional art (WP2): sky, pines, rock, catwalks, posts, hazard placards, board
planks, transformers and wires, plus Hiroshi's cabin in 2B. An art-polish pass
(WP5) may dress it; keep the slot rules below.

Both metal BG slots hold wire pixels and the transformers' stage rows only;
placards and whip brackets live in the stone slot. Shared junction tiles use the
downstream stage's slot. The boxes are the shared background transformer
(``transformer_art.py``): the top tile row in its stage's wire slot, the can and
post in the stone slot (``ridge.TRANSFORMER_BODY_SLOT``). Cracked boards are drawn
as cracked planks on their catwalk; the board actor only shows while it creaks.
Line 3's wire leaves 2A through its right wall and enters 2B through its left
wall on the same row (``ridge.EDGE_PORTS``).
"""
from __future__ import annotations

import bisect
import functools
import json
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import opening
import ridge
import transformer_art
from make_climb_scene import collision_rle


ROOT = Path(__file__).resolve().parent.parent
TILE = ridge.TILE
WIDTH, HEIGHT = ridge.MAP_W * TILE, ridge.MAP_H * TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)

# BG palette families (opening.BG_PALETTES order). Slot 7 is the editor UI.
SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, WIRE_2 = range(7)
PALETTES[WIRE_2] = PALETTES[METAL][:]
LINE = climb.LINE_BG_SLOT
assert LINE == METAL, "cable slot must be the metal family"
assert ridge.WINDOW_BG_SLOT == WINDOW, "window slot must be the window family"
assert ridge.TRANSFORMER_BODY_SLOT == STONE, "transformer cans use the stone ramp"

# Unique (slot, pattern) tiles before GB Studio's flip dedupe (CGB limit 384).
# Spec WP2: Wind Ridge stays below 200.
MAX_UNIQUE_TILES = {ridge.RIDGE: 199, ridge.SADDLE: 240}
# Per-scene backdrop: pine columns and tops (px), skyline seeds.
PINES = {ridge.RIDGE: [(2, 48), (22, 40), (33, 56)], ridge.SADDLE: [(7, 48), (48, 40)]}
SKY_SEEDS = {ridge.RIDGE: (7, 19, 41), ridge.SADDLE: (11, 23, 43)}


def stage_slot(stage: int) -> int:
    return LINE if stage <= 3 else WIRE_2


def _gb_studio_native_index(green: int) -> int:
    if green < 65:
        return 3
    if green < 130:
        return 2
    if green < 205:
        return 1
    return 0


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


def span_points(span) -> list[tuple[int, int]]:
    """Sagging zigzag wire lying on the floor row, across the span's columns."""
    y0 = (ridge.GROUND_ROW - 1) * TILE
    x0, x1 = span["columns"][0] * TILE + 1, (span["columns"][1] + 1) * TILE - 2
    pts, x, k = [], x0, 0
    while x < x1:
        pts.append((x, y0 + (4, 2, 4, 3)[k % 4]))
        x += 6
        k += 1
    pts.append((x1, y0 + 4))
    return pts


def _span_pixels(span) -> frozenset[tuple[int, int]]:
    pts = span_points(span)

    def draw(d):
        d.line(pts, fill=1, width=1)
        d.line([(x, y + 1) for x, y in pts], fill=1, width=1)
    return _mask_pixels(draw)


def _ridge_line(seed: int, base: int, amp: int, lo: int, hi: int) -> list[tuple[int, int]]:
    """Jagged skyline across the whole map (deterministic)."""
    rng = random.Random(seed)
    pts, x, y = [], 0, base
    while x < WIDTH:
        pts.append((x, y))
        x += rng.choice((16, 16, 24))
        y = max(lo, min(hi, base + 8 * rng.randint(-amp // 8, amp // 8)))
    pts.append((WIDTH, y))
    return pts


def _ridge_y(points, x: int) -> int:
    xs = [p[0] for p in points]
    k = max(1, min(len(points) - 1, bisect.bisect_right(xs, x)))
    (x0, y0), (x1, y1) = points[k - 1], points[k]
    return y0 + (y1 - y0) * (x - x0) // max(1, x1 - x0)


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


class SceneArt:
    """One ridge background: the per-scene art the tests read as ``art`` (see test_ridge_background)."""

    PALETTES = PALETTES
    NATIVE_PROXY_BY_INDEX = NATIVE_PROXY_BY_INDEX
    SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, WIRE_2 = SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, WIRE_2
    WIDTH, HEIGHT = WIDTH, HEIGHT

    def __init__(self, folder: str) -> None:
        self.folder = folder
        self.c = c = ridge.LAYOUTS[folder]
        self.OUTPUT = ROOT / f"assets/backgrounds/{folder}.png"
        self.SIDECAR = Path(str(self.OUTPUT) + ".gbsres")
        self.MAX_UNIQUE_TILES = MAX_UNIQUE_TILES[folder]
        self.LANE_CELLS = {(row, x) for row, x0, x1 in c.hazard_lanes() for x in range(x0, x1 + 1)}
        # Stone bracket over each whip lane: the 16x32 whip canvas spans lane rows
        # -1..+2, so the two rows just above it are lane rows -3 and -2.
        self.BRACKET_CELLS = {(row + dr, x) for row, x0, x1 in c.WHIP_LANES
                              for x in range(x0 - 1, x1 + 2) for dr in (-3, -2)}
        self.PLACARD_CELLS = self.LANE_CELLS | self.BRACKET_CELLS
        self.PINES = [(tx * TILE, top, 16, ridge.GROUND_ROW * TILE) for tx, top in PINES[folder]]
        far, near, decor = SKY_SEEDS[folder]
        self.FAR_RIDGE = _ridge_line(far, 40, 16, 28, 56)
        self.NEAR_RIDGE = _ridge_line(near, 80, 16, 64, 96)
        self.RAIN_SLASHES, self.SPARKS = self._decor(decor)
        self.TRANSFORMER_TILES = {cell for line in c.box_lines() for cell in transformer_art.all_tiles(line["box"])}

    stage_slot = staticmethod(stage_slot)
    span_points = staticmethod(span_points)
    _span_pixels = staticmethod(_span_pixels)

    def _decor(self, seed: int):
        rng = random.Random(seed)
        slashes = []
        for _ in range(16):
            x = rng.randint(1, WIDTH // 8 - 1) * 8 + rng.choice((2, 5))
            slashes.append((x, rng.randint(3, max(4, (_ridge_y(self.FAR_RIDGE, x) - 12) // 8)) * 8 + 1))
        sparks = []
        for _ in range(8):
            x = rng.randint(1, WIDTH // 8 - 1) * 8 + 4
            sparks.append((x, rng.randint(3, max(4, (_ridge_y(self.FAR_RIDGE, x) - 8) // 8)) * 8 + 3,
                           rng.choice((2, 3))))
        return slashes, sparks

    # -- wire pixels ----------------------------------------------------------
    @functools.lru_cache(maxsize=None)
    def stage_pixels(self, stage: int) -> frozenset[tuple[int, int]]:
        """Every pixel of this scene that may carry the wire colour index of ``stage``."""
        out: set[tuple[int, int]] = set()
        for s, route in self.c.WIRE_ROUTES:
            if s == stage:
                out |= _polyline_pixels(route)
        for span in self.c.FALLEN_SPANS:
            if span["live_after"] == stage:
                out |= _span_pixels(span)
        line = ridge.LINES[stage - 1]
        if line["box_scene"] == self.folder:
            # The transformer's cap, bushing, clamp, collar and lid light with its stage.
            out |= transformer_art.stage_pixels(line["box"])
        return frozenset(out)

    def wire_tiles(self) -> frozenset[tuple[int, int]]:
        return frozenset((x // TILE, y // TILE) for stage in range(1, ridge.LINE_COUNT + 1)
                         for x, y in self.stage_pixels(stage))

    # -- layout of palette families ------------------------------------------------
    def _post_run(self, grid, row: int, tx: int) -> list[tuple[int, int]]:
        """Tiles of a post under catwalk ``row`` at column ``tx`` down to the floor."""
        out = []
        for ty in range(row + 1, ridge.MAP_H):
            if grid[ty][tx] != climb.COL_EMPTY:
                break
            out.append((tx, ty))
        return out

    def _post_columns(self) -> list[tuple[int, int]]:
        """(catwalk row, column) of each support: ends plus one inboard, whose run
        down to the floor stays clear of spans, hazard art and transformers."""
        grid = self.c.collision_grid()
        spans = [s["columns"] for s in self.c.FALLEN_SPANS]
        out = []
        for row, x0, x1 in self.c.LEDGES:
            for x in sorted({x0, x0 + 3, x1}):
                if any(c0 <= x <= c1 for c0, c1 in spans):
                    continue
                run = self._post_run(grid, row, x)
                if any((ty, tx) in self.PLACARD_CELLS or (tx, ty) in self.TRANSFORMER_TILES for tx, ty in run):
                    continue
                if any(lrow > row and lx0 - 1 <= x <= lx1 + 1 for lrow, lx0, lx1 in self.c.all_hazard_lanes()):
                    continue          # no post right beside a lane below the catwalk
                out.append((row, x))
        return out

    def _post_tiles(self, grid) -> list[tuple[int, int]]:
        return [tile for row, tx in self._post_columns() for tile in self._post_run(grid, row, tx)]

    def _slots(self, grid: list[list[int]]) -> list[list[int]]:
        """Choose one palette family per tile, respecting the collision grid."""
        c = self.c
        slots = [[SKY] * ridge.MAP_W for _ in range(ridge.MAP_H)]
        for ty, row in enumerate(grid):
            for tx, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    slots[ty][tx] = STONE
                elif cell == climb.COL_TOP:
                    slots[ty][tx] = TIMBER
        for x, top, w, bottom in self.PINES:
            for ty in range(top // TILE, (bottom - 1) // TILE + 1):
                for tx in range(x // TILE, (x + w - 1) // TILE + 1):
                    if grid[ty][tx] == climb.COL_EMPTY and slots[ty][tx] == SKY:
                        slots[ty][tx] = FOLIAGE
        posts = set(self._post_tiles(grid))
        for tx, ty in posts:
            slots[ty][tx] = TIMBER
        house: set[tuple[int, int]] = set()
        if c.HOUSE:
            x0, x1, y0, y1 = ridge.HOUSE_RECT
            house = {(tx, ty) for ty in range(y0, y1 + 1) for tx in range(x0, x1 + 1)}
            for tx, ty in house:
                if grid[ty][tx] != climb.COL_EMPTY:
                    raise AssertionError(f"house overlaps collision at {tx},{ty}")
                slots[ty][tx] = TIMBER
            for tx, ty in c.HOUSE_WINDOWS:
                slots[ty][tx] = WINDOW
        # Placards and whip brackets: STONE slot (the metal slot is wire only).
        for row, tx in sorted(self.PLACARD_CELLS):
            if grid[row][tx] != climb.COL_EMPTY:
                raise AssertionError(f"hazard art overlaps collision at {tx},{row}")
            if (tx, row) in self.TRANSFORMER_TILES:
                raise AssertionError(f"hazard art overlaps a transformer at {tx},{row}")
            slots[row][tx] = STONE
        # Background transformers: the top row in the stage's wire slot, the can in stone.
        bodies = set()
        for line in c.box_lines():
            top, body = transformer_art.tiles(line["box"])
            for tx, ty in top + body:
                if grid[ty][tx] != climb.COL_EMPTY or (tx, ty) in posts:
                    raise AssertionError(f"transformer {line['key']} overlaps terrain at {tx},{ty}")
            for tx, ty in body:
                slots[ty][tx] = ridge.TRANSFORMER_BODY_SLOT
                bodies.add((tx, ty))
            for tx, ty in top:
                slots[ty][tx] = stage_slot(line["number"])
        # Wire tiles take the metal slot last; they may never hit collision (except
        # the edge walls they cross), hazard art, the cabin or a post.
        for stage in range(1, ridge.LINE_COUNT + 1):
            for tx, ty in sorted({(x // TILE, y // TILE) for x, y in self.stage_pixels(stage)}):
                if grid[ty][tx] != climb.COL_EMPTY:
                    assert tx in (0, ridge.MAP_W - 1), f"wire tile {tx},{ty} inside collision"
                    continue
                if (ty, tx) in self.PLACARD_CELLS or (tx, ty) in house or (tx, ty) in posts or (tx, ty) in bodies:
                    raise AssertionError(f"{self.folder}: wire tile {tx},{ty} collides with other art")
                slots[ty][tx] = stage_slot(stage)
        assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
        assert all(slots[ty][tx] == WINDOW for tx, ty in c.HOUSE_WINDOWS)
        return slots

    # -- painting ----------------------------------------------------------------
    def _draw_sky(self, cv: _Canvas) -> None:
        p = PALETTES[SKY]
        base = [(WIDTH, HEIGHT - 24), (0, HEIGHT - 24)]
        cv.polygon(SKY, self.FAR_RIDGE + base, p[1])
        cv.line(SKY, self.FAR_RIDGE, p[2])
        cv.polygon(SKY, self.NEAR_RIDGE + base, p[0])
        for (x0, y0), (x1, y1) in zip(self.NEAR_RIDGE, self.NEAR_RIDGE[1:]):
            if (x0 // 8) % 2 == 0 and y1 > y0:          # rim light on some slopes
                cv.line(SKY, [(x0, y0 + 1), (x1, y1 + 1)], p[1])
        for x, y in self.RAIN_SLASHES:
            cv.line(SKY, [(x, y), (x - 2, y + 4)], p[2])
        for x, y, index in self.SPARKS:
            cv.point(SKY, (x, y), p[index])

    def _draw_pines(self, cv: _Canvas) -> None:
        p = PALETTES[FOLIAGE]
        for x, top, w, bottom in self.PINES:
            center = x + w // 2
            cv.polygon(FOLIAGE, [(center, top), (x + 2, top + 11), (x + 5, top + 10),
                                 (x, top + 20), (x + 5, top + 19), (x, bottom - 2),
                                 (x + w, bottom - 2), (x + w - 5, top + 19),
                                 (x + w, top + 20), (x + w - 5, top + 10),
                                 (x + w - 2, top + 11)], p[1])
            cv.line(FOLIAGE, [(center, top + 2), (center, bottom - 2)], p[0])
            cv.line(FOLIAGE, [(center - 1, top + 7), (center - 3, top + 12)], p[2])

    def _draw_rock(self, cv: _Canvas, grid) -> None:
        ramp = PALETTES[STONE]
        for ty, row in enumerate(grid):
            for tx, cell in enumerate(row):
                if cell != climb.COL_SOLID:
                    continue
                x, y = tx * TILE, ty * TILE
                cv.rect(STONE, (x, y, x + 7, y + 7), ramp[1])
                if ty == 0 or grid[ty - 1][tx] != climb.COL_SOLID:
                    cv.line(STONE, [(x, y), (x + 7, y)], ramp[3])
                if (tx + ty) % 3 == 0:
                    cv.polygon(STONE, [(x, y + 2), (x + 3, y), (x + 4, y + 2), (x + 2, y + 4)], ramp[0])
                else:
                    cv.line(STONE, [(x + 1, y + 1), (x + 3, y + 2), (x + 2, y + 4)], ramp[0])
                cv.line(STONE, [(x + 5, y + 1), (x + 6, y + 3)], ramp[2])

    def _draw_ledges(self, cv: _Canvas) -> None:
        p = PALETTES[TIMBER]
        for row, x0, x1 in self.c.LEDGES:
            y = row * TILE
            left, right = x0 * TILE, x1 * TILE + 7
            cv.line(TIMBER, [(left, y), (right, y)], p[3])
            cv.line(TIMBER, [(left, y + 1), (right, y + 1)], p[2])
            cv.rect(TIMBER, (left, y + 2, right, y + 4), p[1])
            cv.line(TIMBER, [(left, y + 5), (right, y + 5)], p[0])
            cv.line(TIMBER, [(left, y + 6), (right, y + 6)], p[0])
            for x in range(left + 10, right - 2, 16):
                cv.line(TIMBER, [(x, y + 2), (x, y + 4)], p[0])
                cv.point(TIMBER, (x + 3, y + 2), p[3])

    def _draw_posts(self, cv: _Canvas, grid) -> None:
        p = PALETTES[TIMBER]
        for tx, ty in self._post_tiles(grid):
            x, y = tx * TILE + 3, ty * TILE
            cv.line(TIMBER, [(x, y), (x, y + 7)], p[0], 2)
            cv.line(TIMBER, [(x + 2, y), (x + 2, y + 7)], p[2])

    def _draw_cabin(self, cv: _Canvas) -> None:
        p = PALETTES[TIMBER]
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        left, right = x0 * TILE, x1 * TILE + 7
        top, bottom = y0 * TILE, y1 * TILE + 7
        cv.rect(TIMBER, (left, top + 8, right, bottom), p[1])
        for x in range(left + 7, right, TILE):
            cv.line(TIMBER, [(x, top + 8), (x, bottom)], p[0])
        mid = (left + right) // 2
        cv.polygon(TIMBER, [(left, top + 7), (mid, top), (right, top + 7)], p[2])
        cv.line(TIMBER, [(left, top + 7), (right, top + 7)], p[3])
        dx = ridge.HOUSE_DOOR[0] * TILE
        dy0 = (ridge.HOUSE_DOOR[1] - 2) * TILE
        cv.rect(TIMBER, (dx, dy0, dx + 7, bottom), p[0])
        cv.line(TIMBER, [(dx, dy0), (dx, bottom)], p[3])
        cv.line(TIMBER, [(dx + 7, dy0), (dx + 7, bottom)], p[3])
        cv.point(TIMBER, (dx + 5, dy0 + 12), p[3])

    def _draw_windows(self, cv: _Canvas) -> None:
        p = PALETTES[WINDOW]
        for tx, ty in self.c.HOUSE_WINDOWS:
            x, y = tx * TILE, ty * TILE
            cv.rect(WINDOW, (x, y, x + 7, y + 7), p[0])
            cv.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), p[1])
            cv.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), p[3])
            cv.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], p[2])
            cv.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], p[2])

    def _draw_warnings(self, cv: _Canvas) -> None:
        p = PALETTES[STONE]
        for row, x0, x1 in self.c.hazard_lanes():
            left, right = x0 * TILE, x1 * TILE + 7
            y = row * TILE
            cv.rect(STONE, (left + 2, y + 2, right - 2, y + 5), p[1])
            cv.line(STONE, [(left + 4, y + 2), (right - 4, y + 5)], p[3])
            cv.line(STONE, [(right - 4, y + 2), (left + 4, y + 5)], p[3])
        for row, x0, x1 in self.c.WHIP_LANES:
            left, right = (x0 - 1) * TILE + 1, (x1 + 2) * TILE - 2
            y = (row - 3) * TILE
            cv.rect(STONE, (left, y + 10, right, y + 13), p[2])       # crossarm
            cv.line(STONE, [(left, y + 10), (right, y + 10)], p[3])
            cv.line(STONE, [(left, y + 14), (right, y + 14)], p[0])
            for x in (left + 2, right - 3):                           # end brackets
                cv.rect(STONE, (x, y + 3, x + 1, y + 9), p[2])
            mid = (left + right) // 2
            cv.rect(STONE, (mid, y + 14, mid + 1, y + 15), p[3])      # wire hook

    def _draw_boards(self, cv: _Canvas) -> None:
        """Cracked planks on their catwalk (the board actor only shows while it creaks)."""
        p = PALETTES[TIMBER]
        for row, x0, x1 in self.c.BOARDS:
            y = row * TILE
            for tx in range(x0, x1 + 1):
                x = tx * TILE
                cv.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
                cv.point(TIMBER, (x + 6, y + 4), p[0])

    def _draw_transformers(self, cv: _Canvas) -> None:
        body_rgb = {code: PALETTES[ridge.TRANSFORMER_BODY_SLOT][index]
                    for code, index in ridge.TRANSFORMER_BODY_INDEX.items()}
        for line in self.c.box_lines():
            stage = line["number"]
            transformer_art.paint(cv.image.load(), line["box"],
                                  stage_rgb=PALETTES[stage_slot(stage)][ridge.STAGE_COLOR_INDEX[stage - 1]],
                                  body_rgb=body_rgb)

    def _draw_cable(self, cv: _Canvas, slots) -> None:
        """Paint each stage's wire pixels in its metal colour index."""
        px = cv.image.load()
        for stage in range(1, ridge.LINE_COUNT + 1):
            slot = stage_slot(stage)
            color = PALETTES[slot][ridge.STAGE_COLOR_INDEX[stage - 1]]
            for x, y in sorted(self.stage_pixels(stage)):
                if x < WIDTH and y < HEIGHT and slots[y // TILE][x // TILE] == slot:
                    px[x, y] = color

    def make_background(self) -> tuple[Image.Image, list[list[int]]]:
        """Return authored 512x144 RGB art and its 64x18 tile-palette map."""
        grid = self.c.collision_grid()
        slots = self._slots(grid)
        image = Image.new("RGB", (WIDTH, HEIGHT))
        pixels = image.load()
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                color = PALETTES[slot][0]
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        pixels[x, y] = color
        cv = _Canvas(image, slots)
        self._draw_sky(cv)
        self._draw_pines(cv)
        self._draw_rock(cv, grid)
        self._draw_ledges(cv)
        self._draw_posts(cv, grid)
        if self.c.HOUSE:
            self._draw_cabin(cv)
            self._draw_windows(cv)
        self._draw_warnings(cv)
        self._draw_boards(cv)
        self._draw_transformers(cv)
        self._draw_cable(cv, slots)
        allowed = [set(colors) for colors in PALETTES]
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        if image.getpixel((x, y)) not in allowed[slot]:
                            raise AssertionError(f"illegal palette color in tile {tx},{ty}")
        self._check_geometry_art(image, grid, slots)
        return image, slots

    def _check_geometry_art(self, image: Image.Image, grid, slots) -> None:
        for row, x0, x1 in self.c.LEDGES:
            py = row * TILE
            assert all(grid[row][x] == climb.COL_TOP for x in range(x0, x1 + 1))
            assert all(image.getpixel((x * TILE, py)) == PALETTES[TIMBER][3]
                       for x in range(x0, x1 + 1)), f"ledge lip drift on row {row}"
        for ty, row in enumerate(grid):
            for tx, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    assert slots[ty][tx] == STONE, f"solid not rock at {tx},{ty}"
        # Metal-slot pixels of indices 1-3 belong to their stage's wire only.
        for stage in range(1, ridge.LINE_COUNT + 1):
            wire_slot = stage_slot(stage)
            color = PALETTES[wire_slot][ridge.STAGE_COLOR_INDEX[stage - 1]]
            owner = self.stage_pixels(stage)
            for ty, row in enumerate(slots):
                for tx, slot in enumerate(row):
                    if slot != wire_slot:
                        continue
                    for y in range(ty * TILE, ty * TILE + TILE):
                        for x in range(tx * TILE, tx * TILE + TILE):
                            if image.getpixel((x, y)) == color:
                                assert (x, y) in owner, f"stray stage {stage} wire at {x},{y}"

    # -- compiler proxy -----------------------------------------------------------------
    @staticmethod
    def encode_native_background(image: Image.Image, slots) -> Image.Image:
        """Convert each authored ramp index to a canonical grayscale proxy."""
        if image.mode != "RGB" or image.size != (WIDTH, HEIGHT):
            raise ValueError(f"expected RGB {(WIDTH, HEIGHT)} author image")
        if len(slots) != ridge.MAP_H or any(len(row) != ridge.MAP_W for row in slots):
            raise ValueError(f"expected {ridge.MAP_W}x{ridge.MAP_H} palette grid")
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

    @staticmethod
    def _unique_indexed_tiles(image: Image.Image, slots) -> int:
        patterns = set()
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                pixels = tuple(image.getpixel((tx * TILE + x, ty * TILE + y))
                               for y in range(TILE) for x in range(TILE))
                patterns.add((slot, pixels))
        return len(patterns)

    def _check_owned_outputs(self) -> None:
        if self.SIDECAR.exists():
            try:
                current = json.loads(self.SIDECAR.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise RuntimeError(f"refusing to overwrite unreadable sidecar: {self.SIDECAR}") from exc
            if current.get("id") != self.c.BACKGROUND_ID:
                raise RuntimeError(f"refusing to overwrite unowned sidecar: {self.SIDECAR}")
        elif self.OUTPUT.exists():
            raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {self.OUTPUT}")

    def write(self) -> None:
        self._check_owned_outputs()
        author_image, slots = self.make_background()
        proxy = self.encode_native_background(author_image, slots)
        unique = self._unique_indexed_tiles(proxy, slots)
        if unique > self.MAX_UNIQUE_TILES:
            raise AssertionError(f"{self.folder} uses {unique} unique indexed tiles (budget {self.MAX_UNIQUE_TILES})")
        self.OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        proxy.save(self.OUTPUT, format="PNG", optimize=False)
        resource = {
            "_resourceType": "background",
            "id": self.c.BACKGROUND_ID,
            "name": self.folder,
            "symbol": f"bg_{self.folder}",
            "filename": self.OUTPUT.name,
            "width": ridge.MAP_W,
            "height": ridge.MAP_H,
            "imageWidth": proxy.width,
            "imageHeight": proxy.height,
            "autoColor": False,
            "tileColors": collision_rle(slots, ridge.MAP_W, ridge.MAP_H),
        }
        self.SIDECAR.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
        slot_counts = {slot: sum(value == slot for row in slots for value in row) for slot in range(7)}
        print(f"generated {self.OUTPUT.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
              f"{unique} unique indexed tiles (budget {self.MAX_UNIQUE_TILES}), palette tiles {slot_counts}")


ARTS = {folder: SceneArt(folder) for folder in ridge.SCENE_ORDER}


def preview(path: Path) -> None:
    """Both authored backgrounds stacked at 2x (2A over 2B) for a one-look review."""
    images = [ARTS[folder].make_background()[0] for folder in ridge.SCENE_ORDER]
    sheet = Image.new("RGB", (WIDTH, HEIGHT * len(images) + 8 * (len(images) - 1)), (40, 40, 40))
    for index, image in enumerate(images):
        sheet.paste(image, (0, index * (HEIGHT + 8)))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(path)
    print(f"wrote preview {path}")


def main() -> None:
    if len(sys.argv) == 3 and sys.argv[1] == "--preview":
        preview(Path(sys.argv[2]))
        return
    for art in ARTS.values():
        art.write()


if __name__ == "__main__":
    main()
