"""Generate Emil's three backgrounds (4A pine_hollow, 4B pine_ladder, 4C pine_rim) from ``kiko.py``.

Modelled on ``make_rosa_art.py``: the RGB image returned by
:func:`make_background` is the artist-facing source, and the compiler-facing
PNG is a grayscale index proxy that uses GB Studio's native index thresholds.
This generator owns ``pine_hollow.png``, ``pine_ladder.png``, ``pine_rim.png``
and their background sidecars.

The pine hollow frames the ascent with close trees. Timber switchbacks open
onto the lake, with a trail pennant at both sides of the rim seam.

Both metal BG slots hold wire pixels and the transformers' stage rows only;
placards and whip brackets live in the stone slot. Every box is the shared
background transformer (``transformer_art.py``): the top tile row in its
stage's wire slot, the can and post in the stone slot
(``kiko.TRANSFORMER_BODY_SLOT``). Where a wire crosses rock or timber (the map
edges, the shaft's slabs) it passes behind as a gap. Cracked boards are drawn
as cracked planks on their timber; the board actor only shows while it creaks.
"""
from __future__ import annotations

import functools
import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import kiko
import opening
import shaft_art
import transformer_art
from make_climb_scene import collision_rle


ROOT = Path(__file__).resolve().parent.parent
TILE = kiko.TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
# Unique (slot, pattern) tiles before GB Studio's flip dedupe; the CGB limit is 384.
MAX_UNIQUE_TILES = 300

# BG palette families (opening.BG_PALETTES order). Slot 7 is the editor UI.
SKY, STONE, TIMBER, WINDOW, FOLIAGE, METAL, WIRE_2 = range(7)
PALETTES[WIRE_2] = PALETTES[METAL][:]
LINE = climb.LINE_BG_SLOT
assert LINE == METAL, "cable slot must be the metal family"
assert kiko.WINDOW_BG_SLOT == WINDOW, "window slot must be the window family"
assert kiko.TRANSFORMER_BODY_SLOT == STONE, "transformer cans use the stone ramp"

FOLDERS = kiko.SCENE_ORDER
WAYMARKS = {kiko.HOLLOW: ("right", 61, 9), kiko.LADDER: ("right", 16, 2),
            kiko.RIM: ("left", 1, 6)}


def output(folder: str) -> Path:
    return ROOT / "assets" / "backgrounds" / f"{folder}.png"


def sidecar(folder: str) -> Path:
    return Path(str(output(folder)) + ".gbsres")


def stage_slot(stage: int) -> int:
    return LINE if stage <= 3 else WIRE_2


def _mask_pixels(width: int, height: int, draw) -> frozenset[tuple[int, int]]:
    mask = Image.new("1", (width + 2, height + 2), 0)
    draw(ImageDraw.Draw(mask))
    w = mask.width
    return frozenset((i % w, i // w) for i, v in enumerate(mask.get_flattened_data()) if v)


class SceneArt:
    """One scene's palette map and drawing, from its kiko.Scene."""

    def __init__(self, folder: str) -> None:
        self.folder = folder
        self.scene = kiko.SCENES[folder]
        self.width, self.height = self.scene.map_w * TILE, self.scene.map_h * TILE
        self.grid = self.scene.collision_grid()
        self.lane_cells = {(row, x) for row, x0, x1 in self.scene.hazard_lanes() for x in range(x0, x1 + 1)}
        # Run whips hang from a stone bracket; shaft whips hang from the walk above.
        self.bracket_cells = set() if self.scene.shaft else {
            (row + dr, x) for row, x0, x1 in self.scene.whip_lanes
            for x in range(x0 - 1, x1 + 2) for dr in (-3, -2)}
        self.placard_cells = self.lane_cells | self.bracket_cells
        self.transformer_tiles = {cell for line in self.scene.box_lines()
                                  for cell in transformer_art.all_tiles(line["box"])}
        ledges = [*kiko.LADDER_STEPS[:-1], kiko.ARRIVAL_SHELF]
        # Pine gates for the other links; the rim trail has matching pennants.
        self.markers = shaft_art.exit_markers(folder, self.scene.map_w, self.scene.map_h)
        self.claimed: set[tuple[int, int]] = set()
        self.tree_tiles: set[tuple[int, int]] = set()
        self.trees: list[tuple[int, int, int]] = []      # (first column, top row, bottom row) of 2-column pines
        self.posts = []
        if self.scene.shaft:
            reserved = self.transformer_tiles | {(x // TILE, y // TILE) for stage in self.stages()
                                                 for x, y in self.stage_pixels(stage)}
            self.posts = [cell for cell in shaft_art.post_tiles(self.grid, ledges, self.scene.hazard_cells(),
                                                               self.scene.map_h) if cell not in reserved]

    # -- wires -----------------------------------------------------------------
    def _polyline_pixels(self, route) -> frozenset[tuple[int, int]]:
        """2px-thick polyline through contract tile centres (inside the tile)."""
        pts = [(tx * TILE + 3, ty * TILE + 3) for tx, ty in route]

        def draw(d):
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                d.line([(x + dx, y + dy) for x, y in pts], fill=1, width=1)
        return _mask_pixels(self.width, self.height, draw)

    def _span_pixels(self, span) -> frozenset[tuple[int, int]]:
        x0, x1 = span["columns"]
        y = span["row"] * TILE
        pts = [(x, y + (3 if (x // 6) % 2 else 5)) for x in range(x0 * TILE + 1, (x1 + 1) * TILE - 1, 6)]
        pts.append(((x1 + 1) * TILE - 2, y + 4))
        return _mask_pixels(self.width, self.height, lambda d: d.line(pts, fill=1, width=2))

    @functools.lru_cache(maxsize=None)
    def stage_pixels(self, stage: int) -> frozenset[tuple[int, int]]:
        """Every pixel that may carry the wire colour index of ``stage`` in this scene."""
        out: set[tuple[int, int]] = set()
        for s, route in self.scene.wire_routes:
            if s == stage:
                out |= self._polyline_pixels(route)
        for span in self.scene.spans:
            if span["live_after"] == stage:
                out |= self._span_pixels(span)
        line = kiko.LINES[stage - 1]
        if line["box_scene"] == self.folder:
            # The transformer's cap, bushing, clamp, collar and lid light with its stage.
            out |= transformer_art.stage_pixels(line["box"])
        return frozenset((x, y) for x, y in out if x < self.width and y < self.height)

    def stages(self) -> list[int]:
        return sorted({s for s, _ in self.scene.wire_routes} | {span["live_after"] for span in self.scene.spans}
                      | {line["number"] for line in self.scene.box_lines()})

    def house_tiles(self) -> set[tuple[int, int]]:
        if not self.scene.house:
            return set()
        hx0, hx1, hy0, hy1 = self.scene.house["rect"]
        return {(tx, ty) for ty in range(hy0, hy1 + 1) for tx in range(hx0, hx1 + 1)}

    # -- palette map -----------------------------------------------------------
    def slots(self) -> list[list[int]]:
        """Choose one palette family per tile, respecting the collision grid."""
        grid, scene = self.grid, self.scene
        slots = [[SKY] * scene.map_w for _ in range(scene.map_h)]
        for ty, row in enumerate(grid):
            for tx, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    slots[ty][tx] = STONE
                elif cell == climb.COL_TOP:
                    slots[ty][tx] = TIMBER
        for tx, ty in self.posts:
            slots[ty][tx] = TIMBER
        if scene.house:
            x0, x1, y0, y1 = scene.house["rect"]
            for ty in range(y0, y1 + 1):
                for tx in range(x0, x1 + 1):
                    if grid[ty][tx] != climb.COL_EMPTY:
                        raise AssertionError(f"house overlaps collision at {tx},{ty}")
                    slots[ty][tx] = TIMBER
            # Each window owns exactly one whole tile; no other tile uses this slot.
            for tx, ty in scene.house["windows"]:
                slots[ty][tx] = WINDOW
        for row, tx in sorted(self.placard_cells):
            if grid[row][tx] != climb.COL_EMPTY or (tx, row) in self.transformer_tiles:
                raise AssertionError(f"{self.folder}: hazard placard overlaps terrain at {tx},{row}")
            slots[row][tx] = STONE
        # Background transformers: the top row in the stage's wire slot, the can in stone.
        bodies = set()
        for line in scene.box_lines():
            top, body = transformer_art.tiles(line["box"])
            for tx, ty in top + body:
                if grid[ty][tx] != climb.COL_EMPTY or (tx, ty) in self.house_tiles() or (tx, ty) in self.posts:
                    raise AssertionError(f"transformer {line['key']} overlaps terrain at {tx},{ty}")
            for tx, ty in body:
                slots[ty][tx] = kiko.TRANSFORMER_BODY_SLOT
                bodies.add((tx, ty))
            for tx, ty in top:
                slots[ty][tx] = stage_slot(line["number"])
        # Wire tiles take their stage's slot last, upstream first. Over rock or timber
        # (map edges, shaft slabs) the wire passes behind as a gap; it may never hit
        # a placard, the house, a post or a transformer's can.
        house, posts = self.house_tiles(), set(self.posts)
        for stage in self.stages():
            for tx, ty in sorted({(x // TILE, y // TILE) for x, y in self.stage_pixels(stage)}):
                if grid[ty][tx] != climb.COL_EMPTY:
                    continue
                if (ty, tx) in self.placard_cells or (tx, ty) in house or (tx, ty) in posts or (tx, ty) in bodies:
                    raise AssertionError(f"{self.folder}: wire tile {tx},{ty} collides with other art")
                slots[ty][tx] = stage_slot(stage)
        self._claim_trees(slots)
        self.claimed = shaft_art.claim_markers(slots, grid, self.markers, FOLIAGE)
        assert all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 reserved"
        return slots

    def _lane_neighbourhood(self) -> set[tuple[int, int]]:
        """(row, column) of every hazard lane widened by one tile each way, so a spark stays on dark sky."""
        lanes = self.scene.hazard_cells()
        return {(row + dr, x + dx) for row, x in lanes for dr in (-1, 0, 1) for dx in (-1, 0, 1)}

    def _free(self, slots, tx: int, ty: int, avoid) -> bool:
        return (self.grid[ty][tx] == climb.COL_EMPTY and slots[ty][tx] == SKY and (ty, tx) not in avoid
                and ty >= kiko.HUD_ROWS)

    def _claim_trees(self, slots) -> None:
        """Pine trunks behind the shaft's slabs (4B) / tall standing pines on the runs (4A, 4C):
        foliage tiles on open sky only, never beside a hazard lane, never over wires or art."""
        self.trees.clear()
        self.tree_tiles.clear()
        avoid = self._lane_neighbourhood()
        marker_cols = {tx + dx for _s, tx, _t in self.markers for dx in (-3, -2, -1, 0, 1, 2, 3, 4)}
        width, height = self.scene.map_w, self.scene.map_h
        if self.scene.shaft:
            def runs(col):
                out, run = [], []
                for ty in range(height):
                    if ty >= 13 and all(self._free(slots, col + dx, ty, avoid) for dx in (0, 1)):
                        run.append(ty)
                    else:
                        out, run = (out + [run] if len(run) >= 3 else out), []
                return out + ([run] if len(run) >= 3 else [])
            best = sorted(range(1, width - 3), key=lambda col: -sum(len(r) for r in runs(col)))
            chosen: list[int] = []
            for col in best:
                if all(abs(col - other) >= 5 for other in chosen) and len(chosen) < 3:
                    chosen.append(col)
            for col in sorted(chosen):
                for run in runs(col):
                    self.trees.append((col, run[0], run[-1]))
        else:
            chosen = []
            for col in range(3, width - 5):
                if self.folder == kiko.RIM and 12 <= col <= 43:
                    continue  # leave the lake visible above the rock and footbridges
                if col in marker_cols or any(abs(col - other) < 11 for other in chosen):
                    continue
                floor = next(ty for ty in range(height) if self.grid[ty][col] != climb.COL_EMPTY)
                top = kiko.HUD_ROWS + 3 + (col * 3) % 3
                if all(self._free(slots, col + dx, ty, avoid) for dx in (0, 1) for ty in range(top, floor)) \
                        and all(self.grid[floor][col + dx] != climb.COL_EMPTY for dx in (0, 1)):
                    chosen.append(col)
                    self.trees.append((col, top, floor - 1))
        for col, top, bottom in self.trees:
            for ty in range(top, bottom + 1):
                for dx in (0, 1):
                    slots[ty][col + dx] = FOLIAGE
                    self.tree_tiles.add((col + dx, ty))

    # -- drawing ---------------------------------------------------------------
    def _draw_backdrop(self, c) -> None:
        """Closed pines below; open sky and the far shore at the top."""
        if self.folder in (kiko.LADDER, kiko.RIM):
            self._draw_lake(c, shore=43 if self.scene.shaft else 66,
                            bottom=113 if self.scene.shaft else 132)
        if self.folder == kiko.RIM:
            return
        p = PALETTES[SKY]
        bands = [68] if not self.scene.shaft else [119, 207]
        for band, base in enumerate(bands):
            hill = [(x, base + ((x // 24 * 11 + x // 96 * 3 + band * 5) % 4) * 4)
                    for x in range(0, self.width + 1, 24)] + [(self.width, base + 8)]
            c.polygon(SKY, hill + [(self.width, base + 70), (0, base + 70)], p[1])
            for x, y in hill[2:-1:5]:
                c.line(SKY, [(x, y), (x + 4, y + 6)], p[2])
            for i, x in enumerate(range(14 + band * 9, self.width - 30, 34)):
                top, w, bottom = base - 20 + (i % 3) * 6, 12 + (i % 2) * 4, base + 22
                center = x + w // 2
                c.polygon(SKY, [(center, top), (x + 2, top + 11), (x + 5, top + 10), (x, top + 20),
                                (x + 5, top + 19), (x, bottom - 2), (x + w, bottom - 2), (x + w - 5, top + 19),
                                (x + w, top + 20), (x + w - 5, top + 10), (x + w - 2, top + 11)], p[1])
                c.line(SKY, [(center, top + 2), (center, bottom - 2)], p[0])
                c.line(SKY, [(center - 1, top + 7), (center - 3, top + 12)], p[2])
        for i in range(self.width // 40 * (len(bands))):
            x = (i * 53 + 24) % self.width
            y = bands[i % len(bands)] - 42 + (i * 37) % 10
            c.point(SKY, (x, y), p[2])
        if self.folder == kiko.HOLLOW:
            # From the catwalk, a dark headland and the crooked spruce foreshadow the climb.
            x = self.width - 152
            bluff = [(x, 80), (x + 39, 69), (x + 63, 56), (x + 95, 44),
                     (x + 126, 51), (self.width, 40)]
            c.polygon(SKY, bluff + [(self.width, 119), (x, 119)], p[1])
            c.line(SKY, bluff, p[2])
            self._draw_far_spruce(c, x + 93, 25, 45)

    def _draw_far_spruce(self, c, x: int, top: int, bottom: int) -> None:
        p = PALETTES[SKY]
        c.polygon(SKY, [(x, top), (x + 4, top + 7), (x + 3, top + 7),
                        (x + 7, bottom - 2), (x - 6, bottom - 2),
                        (x - 2, top + 8), (x - 4, top + 8)], p[1])
        c.line(SKY, [(x, top + 2), (x + 1, bottom)], p[2])

    def _draw_lake(self, c, *, shore: int, bottom: int) -> None:
        p = PALETTES[SKY]
        w = self.width
        # Two continuous silhouettes behind the water, with a stepped bluff to the left.
        far = [(0, shore - 9), (w // 12, shore - 18), (w // 5, shore - 23),
               (w // 3, shore - 16), (w // 2, shore - 20), (2 * w // 3, shore - 13),
               (4 * w // 5, shore - 17), (w, shore - 10)]
        bank = [(0, shore - 4), (w // 6, shore - 9), (w // 3, shore - 6),
                (w // 2, shore - 2), (2 * w // 3, shore), (5 * w // 6, shore - 5), (w, shore - 6)]
        c.rect(SKY, (0, shore - 7, w - 1, bottom), p[1])
        c.polygon(SKY, far + [(w, shore + 1), (0, shore + 1)], p[1])
        c.line(SKY, far, p[2])
        c.polygon(SKY, bank + [(w, shore + 1), (0, shore + 1)], p[0])
        for y in range(shore + 7, bottom - 2, 9):
            for x in range(12 + (y % 4) * 9, w - 13, 54):
                c.line(SKY, [(x, y), (x + 11 + 5 * (y % 3), y)], p[2])
        # Far houses and their pier, small enough to read as distant lights.
        for x in (w // 2 - 27, w // 2 - 13, w // 2 + 1):
            y = shore - 6 + (x % 3)
            c.polygon(SKY, [(x, y), (x + 4, y - 3), (x + 8, y),
                            (x + 7, y + 3), (x + 1, y + 3)], p[2])
            c.point(SKY, (x + 4, y + 1), p[3])
        x = w // 2 - 8
        c.line(SKY, [(x, shore + 1), (x + 14, shore + 4), (x + 24, shore + 4)], p[0])
        c.line(SKY, [(x + 14, shore + 5), (x + 24, shore + 5)], p[2])

    def _draw_trees(self, c) -> None:
        p = PALETTES[FOLIAGE]
        for col, top, bottom in self.trees:
            x, y0, y1 = col * TILE, top * TILE, (bottom + 1) * TILE - 1
            if self.scene.shaft:       # trunk behind the slabs: body, shaded side, bark cracks, branch stubs
                c.rect(FOLIAGE, (x + 2, y0, x + 13, y1), p[1])
                c.rect(FOLIAGE, (x + 2, y0, x + 3, y1), p[0])
                c.line(FOLIAGE, [(x + 11, y0), (x + 11, y1)], p[2])
                for ty in range(top, bottom + 1):
                    yy = ty * TILE
                    c.line(FOLIAGE, [(x + 6, yy + 1 + ty % 3), (x + 6, yy + 5 + ty % 3)], p[0])
                    c.line(FOLIAGE, [(x + 9, yy + 4 - ty % 3), (x + 9, yy + 7)], p[0])
                    if ty % 3 == col % 3:
                        c.line(FOLIAGE, [(x + 13, yy + 3), (x + 15, yy)], p[1], 2)
                        c.line(FOLIAGE, [(x + 2, yy + 5), (x, yy + 7)], p[1], 2)
                continue
            w, center = 16, x + 8
            c.polygon(FOLIAGE, [(center, y0), (x + 2, y0 + 11), (x + 5, y0 + 10), (x, y0 + 20), (x + 5, y0 + 19),
                                (x, y1 - 1), (x + w, y1 - 1), (x + w - 5, y0 + 19), (x + w, y0 + 20),
                                (x + w - 5, y0 + 10), (x + w - 2, y0 + 11)], p[1])
            c.line(FOLIAGE, [(center, y0 + 2), (center, y1 - 1)], p[0])
            c.line(FOLIAGE, [(center - 1, y0 + 7), (center - 3, y0 + 12)], p[2])
            c.line(FOLIAGE, [(center + 3, y0 + 21), (center + 5, y0 + 25)], p[2])

    def _draw_storm_damage(self, c) -> None:
        """Puddles on flat rock, snapped branches on the ground, clear of every hazard lane."""
        keep = self._lane_neighbourhood() | self.placard_cells
        for span in self.scene.spans:
            keep |= {(row, x + dx) for row, x0, x1 in span["arcs"] for x in range(x0, x1 + 1) for dx in (-2, -1, 0, 1, 2)}
        seed = len(self.folder)
        shaft_art.puddles(c, self.grid, PALETTES[STONE], STONE, seed=seed)
        shaft_art.branches(c, shaft_art.ground_spots(self.grid, keep, seed=seed + 1, mod=8), PALETTES[SKY], SKY)

    def _draw_rock(self, c) -> None:
        grid = self.grid
        if self.scene.shaft:
            shaft_art.draw_stone(c, grid, PALETTES[STONE], STONE)
            return
        ramp = PALETTES[STONE]
        for ty, row in enumerate(grid):
            for tx, cell in enumerate(row):
                if cell != climb.COL_SOLID:
                    continue
                x, y = tx * TILE, ty * TILE
                c.rect(STONE, (x, y, x + 7, y + 7), ramp[1])
                if ty == 0 or grid[ty - 1][tx] != climb.COL_SOLID:
                    c.line(STONE, [(x, y), (x + 7, y)], ramp[3])
                if (tx + ty) % 3 == 0:
                    c.polygon(STONE, [(x, y + 2), (x + 3, y), (x + 4, y + 2), (x + 2, y + 4)], ramp[0])
                else:
                    c.line(STONE, [(x + 1, y + 1), (x + 3, y + 2), (x + 2, y + 4)], ramp[0])
                c.line(STONE, [(x + 5, y + 1), (x + 6, y + 3)], ramp[2])
                if (tx * 3 + ty) % 4 == 0:
                    c.point(STONE, (x + 6, y + 6), ramp[3])

    def _draw_timber(self, c) -> None:
        p = PALETTES[TIMBER]
        if self.scene.shaft:
            shaft_art.draw_platforms(c, self.scene.platforms, p, TIMBER)
            shaft_art.draw_posts(c, self.posts, p, TIMBER)
            return
        for row, x0, x1 in self.scene.platforms:
            left, right, y = x0 * TILE, (x1 + 1) * TILE - 1, row * TILE
            c.line(TIMBER, [(left, y), (right, y)], p[3])
            c.rect(TIMBER, (left, y + 1, right, y + 4), p[1])
            c.line(TIMBER, [(left, y + 5), (right, y + 5)], p[0])
            for x in range(left + 4, right, 8):
                c.point(TIMBER, (x, y + 3), p[2])

    def _draw_waymarks(self, c) -> None:
        mark = WAYMARKS[self.folder]
        p = PALETTES[FOLIAGE]
        shaft_art.paint_markers(c, [m for m in self.markers if m != mark], self.claimed,
                                "pine", p, FOLIAGE)
        # The same trail pennant at each threshold; its broad point indicates the opening.
        cells = self.claimed & set(shaft_art.marker_tiles(mark))
        masked = [[FOLIAGE if (x, y) in cells else -1 for x in range(len(row))]
                  for y, row in enumerate(c.slots)]
        m = shaft_art.Canvas(c.image, masked)
        side, tx, ty = mark
        x, y = tx * TILE, ty * TILE
        def point(u, v):
            return (x + (u if side == "right" else 15 - u), y + v)

        m.line(FOLIAGE, [point(3, 3), point(3, 23)], p[2], 2)
        m.point(FOLIAGE, point(3, 2), p[3])
        m.polygon(FOLIAGE, [point(4, 5), point(14, 9), point(4, 13)], p[3])
        m.line(FOLIAGE, [point(5, 12), point(13, 9)], p[2])
        m.line(FOLIAGE, [point(2, 17), point(5, 17)], p[1])
        m.line(FOLIAGE, [point(1, 23), point(7, 23)], p[1])

    def _draw_cabin(self, c) -> None:
        house = self.scene.house
        if not house:
            return
        p = PALETTES[TIMBER]
        x0, x1, y0, y1 = house["rect"]
        left, right = x0 * TILE, x1 * TILE + 7
        top, bottom = y0 * TILE, y1 * TILE + 7
        c.rect(TIMBER, (left, top + 8, right, bottom), p[1])
        for y in range(top + 11, bottom, 5):
            c.line(TIMBER, [(left, y), (right, y)], p[0])
            c.line(TIMBER, [(left + 1, y + 1), (left + 4, y + 1)], p[2])
        mid = (left + right) // 2
        c.rect(TIMBER, (right - 8, top + 1, right - 5, top + 6), p[1])
        c.line(TIMBER, [(right - 9, top + 1), (right - 4, top + 1)], p[2])
        c.polygon(TIMBER, [(left, top + 7), (mid, top), (right, top + 7)], p[2])
        c.line(TIMBER, [(left, top + 7), (mid, top)], p[3])
        c.line(TIMBER, [(mid, top), (right, top + 7)], p[1])
        c.line(TIMBER, [(left, top + 7), (right, top + 7)], p[3])
        dx = house["door"][0] * TILE
        dy0 = (house["door"][1] - 2) * TILE
        c.rect(TIMBER, (dx, dy0, dx + 7, bottom), p[0])
        c.line(TIMBER, [(dx, dy0), (dx, bottom)], p[3])
        c.line(TIMBER, [(dx + 7, dy0), (dx + 7, bottom)], p[3])
        c.point(TIMBER, (dx + 5, dy0 + 12), p[3])
        w = PALETTES[WINDOW]
        # Cold glass; the scene swaps this slot to warm when the house is powered.
        for tx, ty in house["windows"]:
            x, y = tx * TILE, ty * TILE
            c.rect(WINDOW, (x, y, x + 7, y + 7), w[0])
            c.rect(WINDOW, (x + 1, y + 1, x + 6, y + 6), w[1])
            c.rect(WINDOW, (x + 2, y + 2, x + 5, y + 5), w[3])
            c.line(WINDOW, [(x + 3, y + 2), (x + 3, y + 5)], w[2])
            c.line(WINDOW, [(x + 2, y + 4), (x + 5, y + 4)], w[2])

    def _draw_warnings(self, c) -> None:
        p = PALETTES[STONE]
        for row, x0, x1 in self.scene.hazard_lanes():
            left, right, y = x0 * TILE, (x1 + 1) * TILE - 1, row * TILE
            c.rect(STONE, (left + 2, y + 2, right - 2, y + 5), p[0])
            c.line(STONE, [(left + 3, y + 2), (right - 3, y + 5)], p[3])
            c.line(STONE, [(right - 3, y + 2), (left + 3, y + 5)], p[3])
        if self.scene.shaft:
            return
        for row, x0, x1 in self.scene.whip_lanes:
            left, right, y = (x0 - 1) * TILE + 1, (x1 + 2) * TILE - 2, (row - 3) * TILE
            c.rect(STONE, (left, y + 10, right, y + 13), p[2])
            c.line(STONE, [(left, y + 10), (right, y + 10)], p[3])
            for x in (left + 2, right - 3):
                c.rect(STONE, (x, y + 3, x + 1, y + 9), p[2])

    def _draw_boards(self, c) -> None:
        """Cracked planks on their timber (the board actor only shows while it creaks)."""
        p = PALETTES[TIMBER]
        for row, x0, x1 in self.scene.boards:
            y = row * TILE
            for tx in range(x0, x1 + 1):
                x = tx * TILE
                c.line(TIMBER, [(x + 1, y + 2), (x + 3, y + 4), (x + 5, y + 3)], p[0])
                c.point(TIMBER, (x + 6, y + 4), p[0])

    def _draw_transformers(self, c) -> None:
        body_rgb = {code: PALETTES[kiko.TRANSFORMER_BODY_SLOT][index]
                    for code, index in kiko.TRANSFORMER_BODY_INDEX.items()}
        for line in self.scene.box_lines():
            stage = line["number"]
            transformer_art.paint(c.image.load(), line["box"],
                                  stage_rgb=PALETTES[stage_slot(stage)][kiko.STAGE_COLOR_INDEX[stage - 1]],
                                  body_rgb=body_rgb)

    def _draw_cable(self, c, slots: list[list[int]]) -> None:
        """Paint each stage's wire pixels in its metal colour index, on claimed wire tiles only."""
        px = c.image.load()
        for stage in self.stages():
            slot = stage_slot(stage)
            color = PALETTES[slot][kiko.STAGE_COLOR_INDEX[stage - 1]]
            for x, y in sorted(self.stage_pixels(stage)):
                if slots[y // TILE][x // TILE] == slot:
                    px[x, y] = color

    def make_background(self) -> tuple[Image.Image, list[list[int]]]:
        """Return authored art and the contract-sized tile-palette map."""
        slots = self.slots()
        image = Image.new("RGB", (self.width, self.height))
        pixels = image.load()
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                color = PALETTES[slot][0]
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        pixels[x, y] = color
        canvas = shaft_art.Canvas(image, slots)
        self._draw_backdrop(canvas)
        self._draw_trees(canvas)
        self._draw_rock(canvas)
        self._draw_timber(canvas)
        self._draw_storm_damage(canvas)
        self._draw_waymarks(canvas)
        self._draw_cabin(canvas)
        self._draw_warnings(canvas)
        self._draw_boards(canvas)
        self._draw_transformers(canvas)
        self._draw_cable(canvas, slots)

        allowed = [set(colors) for colors in PALETTES]
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                for y in range(ty * TILE, ty * TILE + TILE):
                    for x in range(tx * TILE, tx * TILE + TILE):
                        if pixels[x, y] not in allowed[slot]:
                            raise AssertionError(f"{self.folder}: illegal palette color in tile {tx},{ty}")
        self._check_geometry_art(image, slots)
        return image, slots

    def _check_geometry_art(self, image: Image.Image, slots: list[list[int]]) -> None:
        for ty, row in enumerate(self.grid):
            for tx, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    assert slots[ty][tx] == STONE, f"solid not rock at {tx},{ty}"
        # Metal-slot pixels of each stage's index belong to that stage's wire only.
        pixels = image.load()
        for stage in self.stages():
            wire_slot = stage_slot(stage)
            color = PALETTES[wire_slot][kiko.STAGE_COLOR_INDEX[stage - 1]]
            owner = self.stage_pixels(stage)
            for ty, row in enumerate(slots):
                for tx, slot in enumerate(row):
                    if slot != wire_slot:
                        continue
                    for y in range(ty * TILE, ty * TILE + TILE):
                        for x in range(tx * TILE, tx * TILE + TILE):
                            if pixels[x, y] == color:
                                assert (x, y) in owner, f"{self.folder}: stray stage {stage} wire at {x},{y}"


@functools.lru_cache(maxsize=None)
def scene_art(folder: str) -> SceneArt:
    return SceneArt(folder)


def make_background(folder: str = kiko.HOLLOW) -> tuple[Image.Image, list[list[int]]]:
    return scene_art(folder).make_background()


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
    if image.mode != "RGB" or image.size != (len(slots[0]) * TILE, len(slots) * TILE):
        raise ValueError("expected an RGB author image matching its palette grid")
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


def unique_indexed_tiles(image: Image.Image, slots: list[list[int]]) -> int:
    patterns = set()
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            patterns.add((slot, tuple(pixels[tx * TILE + x, ty * TILE + y] for y in range(TILE) for x in range(TILE))))
    return len(patterns)


def _check_owned_outputs(folder: str) -> None:
    expected_id = kiko.BACKGROUND_IDS[folder]
    path, meta = output(folder), sidecar(folder)
    if meta.exists():
        try:
            current = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"refusing to overwrite unreadable sidecar: {meta}") from exc
        if current.get("id") != expected_id:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {meta}")
    elif path.exists():
        raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {path}")


def sidecar_resource(folder: str, proxy: Image.Image, slots: list[list[int]]) -> dict:
    scene = kiko.SCENES[folder]
    return {
        "_resourceType": "background",
        "id": kiko.BACKGROUND_IDS[folder],
        "name": folder,
        "symbol": f"bg_{folder}",
        "filename": output(folder).name,
        "width": scene.map_w,
        "height": scene.map_h,
        "imageWidth": proxy.width,
        "imageHeight": proxy.height,
        "autoColor": False,
        "tileColors": collision_rle(slots, scene.map_w, scene.map_h),
    }


def main() -> None:
    for folder in FOLDERS:
        _check_owned_outputs(folder)
        author_image, slots = make_background(folder)
        proxy = encode_native_background(author_image, slots)
        unique = unique_indexed_tiles(proxy, slots)
        if unique > MAX_UNIQUE_TILES:
            raise AssertionError(f"{folder} uses {unique} unique indexed tiles (budget {MAX_UNIQUE_TILES})")
        path = output(folder)
        path.parent.mkdir(parents=True, exist_ok=True)
        proxy.save(path, format="PNG", optimize=False)
        sidecar(folder).write_text(json.dumps(sidecar_resource(folder, proxy, slots), indent=2) + "\n",
                                   encoding="utf-8")
        counts = {slot: sum(value == slot for row in slots for value in row) for slot in range(7)}
        print(f"generated {path.relative_to(ROOT)}: {proxy.width}x{proxy.height}px, "
              f"{unique} unique indexed tiles (budget {MAX_UNIQUE_TILES}), palette tiles {counts}")


if __name__ == "__main__":
    main()
