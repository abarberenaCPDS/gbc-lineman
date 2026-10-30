"""Shaft background drawing shared by the vertical scenes (Pillow).

Moved out of ``make_climb_art.py`` (1A storm_climb), which re-exports it; the
redesign's 3B ``signal_gully`` and 4B ``pine_ladder`` art passes draw their
decks, ledges, slabs and posts with the same helpers (docs/LEVEL_REDESIGN.md §4)
and add their own dressing on top.

Every helper paints through a ``Canvas``: an RGB image plus a tile-palette map
(one BG palette slot per 8x8 tile). Painting is clipped to the tiles whose slot
matches, so a material never leaks a colour outside its palette family.

  Canvas(image, slots)                     rect / line / polygon / point(slot, ..., colour)
  post_tiles(grid, ledges, lanes, map_h)   timber posts under each ledge end (at most three rows)
  draw_stone(c, grid, ramp, slot)          solid tiles: fill, walkable top edge, chips
  draw_platforms(c, platforms, ramp, slot) one-way timber: lip on the collision row, planks
  draw_posts(c, posts, ramp, slot)         two-pixel posts under the ledge ends

``ramp`` is the slot's four colours, light index 0 first as in
``opening.BG_PALETTES``; ``grid`` is the contract's collision grid (``shaft.py``).
"""
from __future__ import annotations

from typing import Iterable, Sequence

from PIL import Image, ImageDraw

import shaft

TILE = 8
Color = tuple[int, int, int]


class Canvas:
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


def post_tiles(grid: list[list[int]], ledges: Iterable[tuple[int, int, int]],
               lanes: set[tuple[int, int]], map_h: int) -> list[tuple[int, int]]:
    """Timber posts under each ledge end, down to the next occupied cell (at most three rows).

    ``lanes`` are (row, x) hazard cells a post must not cross.
    """
    posts = []
    for row, x0, x1 in ledges:
        for tx in (x0, x1):
            for ty in range(row + 1, min(row + 4, map_h)):
                if grid[ty][tx] != shaft.COL_EMPTY or (ty, tx) in lanes:
                    break
                posts.append((tx, ty))
    return posts


def draw_stone(c: Canvas, grid: list[list[int]], ramp: Sequence[Color], slot: int) -> None:
    for ty, row in enumerate(grid):
        for tx, cell in enumerate(row):
            if cell != shaft.COL_SOLID:
                continue
            x, y = tx * TILE, ty * TILE
            c.rect(slot, (x, y, x + 7, y + 7), ramp[1])
            if ty > 0 and grid[ty - 1][tx] == shaft.COL_EMPTY:
                c.line(slot, [(x, y), (x + 7, y)], ramp[3])   # walkable top edge
            if (tx + ty) % 3 == 0:
                c.polygon(slot, [(x, y + 3), (x + 3, y + 1), (x + 4, y + 3), (x + 2, y + 5)], ramp[0])
            else:
                c.line(slot, [(x + 1, y + 2), (x + 3, y + 3), (x + 2, y + 5)], ramp[0])
            c.line(slot, [(x + 5, y + 2), (x + 6, y + 4)], ramp[2])


def draw_platforms(c: Canvas, platforms: Iterable[tuple[int, int, int]], ramp: Sequence[Color],
                   slot: int) -> None:
    for row, x0, x1 in platforms:
        y = row * TILE
        left, right = x0 * TILE, x1 * TILE + 7
        # The light top edge is exactly the collision row's first pixel.
        c.line(slot, [(left, y), (right, y)], ramp[3])
        c.line(slot, [(left, y + 1), (right, y + 1)], ramp[2])
        c.rect(slot, (left, y + 2, right, y + 4), ramp[1])
        c.line(slot, [(left, y + 5), (right, y + 5)], ramp[0])
        c.line(slot, [(left, y + 6), (right, y + 6)], ramp[0])
        for x in range(left + 10, right - 2, 16):
            c.line(slot, [(x, y + 2), (x, y + 4)], ramp[0])
            c.point(slot, (x + 3, y + 2), ramp[3])


def draw_posts(c: Canvas, posts: Iterable[tuple[int, int]], ramp: Sequence[Color], slot: int) -> None:
    for tx, ty in posts:
        x, y = tx * TILE + 3, ty * TILE
        c.line(slot, [(x, y), (x, y + 7)], ramp[0], 2)
        c.line(slot, [(x + 2, y), (x + 2, y + 7)], ramp[2])
