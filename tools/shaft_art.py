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

WP5 dressing helpers (art only, no geometry):

  exit_markers(folder, width, height)      the 2x3-tile "route continues" motif of every scene link
  claim_markers(slots, grid, markers, slot) move free sky tiles under the motif into its slot
  draw_marker(c, marker, style, ramp, slot) arch / brace / sign / pine motif
  puddles / branches / rope_lashings        storm damage and one-way-timber dressing

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


# ---------------------------------------------------------------------------
# WP5 dressing: route markers, storm damage
# ---------------------------------------------------------------------------
HUD_PX = 16          # the two HUD tile rows stay plain in every scene


def exit_markers(folder: str, width: int, height: int) -> list[tuple[str, int, int]]:
    """One (side, first column, top row) per link that leaves ``folder``: a 2x3 tile motif
    on the exit rect's rows, on the map-edge side of the map, derived from scene_links."""
    import scene_links
    out = []
    for link in scene_links.links():
        if link.source != folder:
            continue
        x, y, _w, _h = link.rect
        side = "left" if x < width // 2 else "right"
        out.append((side, x if side == "left" else x - 1, y))
    return out


def marker_tiles(marker: tuple[str, int, int]) -> list[tuple[int, int]]:
    _side, tx, ty = marker
    return [(tx + dx, ty + dy) for dy in range(3) for dx in range(2)]


def claim_markers(slots: list[list[int]], grid: list[list[int]], markers, slot: int, sky: int = 0) -> set[tuple[int, int]]:
    """Free open-air sky tiles under each motif move to ``slot`` (wire, post, hazard and
    terrain tiles keep theirs: the motif simply gaps around them). Call after the wires."""
    claimed = set()
    for marker in markers:
        for tx, ty in marker_tiles(marker):
            if slots[ty][tx] == sky and grid[ty][tx] == shaft.COL_EMPTY and ty * TILE >= HUD_PX:
                slots[ty][tx] = slot
                claimed.add((tx, ty))
    return claimed


def draw_marker(c: Canvas, marker: tuple[str, int, int], style: str, ramp: Sequence[Color], slot: int) -> None:
    """Paint one 16x24 motif; ``u`` runs from the map-edge side inward, ``v`` downward."""
    side, tx, ty = marker
    x0, y0 = tx * TILE, ty * TILE

    def X(u):
        return x0 + u if side == "left" else x0 + 15 - u

    def R(u0, u1, v0, v1, color):
        xa, xb = sorted((X(u0), X(u1)))
        c.rect(slot, (xa, y0 + v0, xb, y0 + v1), color)

    def L(points, color, width=1):
        c.line(slot, [(X(u), y0 + v) for u, v in points], color, width)

    def chevrons(color, count=2):
        for k in range(count):
            u = 3 + 4 * k
            L([(u + 2, 9), (u, 12), (u + 2, 15)], color, 2)

    if style in ("arch", "brace"):
        R(0, 15, 0, 23, ramp[1])                       # dim doorway behind the hero
        R(0, 15, 0, 0, ramp[3])                        # lintel
        R(0, 15, 1, 1, ramp[2])
        R(0, 15, 2, 3, ramp[0])
        R(0, 2, 0, 23, ramp[0])                        # edge-side post
        R(2, 2, 3, 23, ramp[2])
        R(13, 15, 0, 23, ramp[0])                      # inboard post
        R(13, 13, 3, 23, ramp[2])
        if style == "brace":                           # wind braces under the lintel
            L([(3, 4), (7, 8)], ramp[2], 2)
            L([(12, 4), (8, 8)], ramp[2], 2)
        chevrons(ramp[3])
    elif style == "sign":                              # post with an arrow board pointing out
        R(6, 8, 8, 23, ramp[2])
        R(6, 6, 8, 23, ramp[3])
        R(8, 8, 8, 23, ramp[0])
        c.polygon(slot, [(X(0), y0 + 10), (X(3), y0 + 4), (X(14), y0 + 4), (X(14), y0 + 15), (X(3), y0 + 15)], ramp[2])
        c.polygon(slot, [(X(3), y0 + 7), (X(5), y0 + 7), (X(5), y0 + 12), (X(3), y0 + 12), (X(2), y0 + 10)], ramp[3])
        R(6, 13, 7, 7, ramp[3])
        R(6, 13, 15, 15, ramp[0])
        R(8, 12, 10, 11, ramp[0])
    elif style == "pine":                              # two pines make a gate onto the path
        for u0 in (0, 10):
            mid = u0 + 3
            c.polygon(slot, [(X(mid), y0 + 1), (X(u0), y0 + 10), (X(u0 + 2), y0 + 10), (X(u0 - 1 if u0 else u0), y0 + 18),
                             (X(u0 + 6), y0 + 18), (X(u0 + 5), y0 + 10), (X(u0 + 6), y0 + 10)], ramp[1])
            R(mid, mid, 4, 23, ramp[0])
            L([(mid - 2, 12), (mid - 1, 8)], ramp[2])
        R(3, 12, 20, 23, ramp[0])
        chevrons(ramp[2])


def puddles(c: Canvas, grid: list[list[int]], ramp: Sequence[Color], slot: int, seed: int = 0) -> None:
    """Storm puddles on flat, exposed rock: a dark wet patch with a glint (drawn in the rock tile)."""
    for ty in range(1, len(grid)):
        if ty * TILE < HUD_PX:
            continue
        for tx in range(1, len(grid[ty]) - 1):
            flat = all(grid[ty][t] == shaft.COL_SOLID and grid[ty - 1][t] == shaft.COL_EMPTY for t in (tx - 1, tx, tx + 1))
            if flat and (tx * 5 + ty * 3 + seed) % 9 == 0:
                x, y = tx * TILE, ty * TILE
                c.rect(slot, (x + 1, y + 1, x + 6, y + 2), ramp[0])
                c.line(slot, [(x + 2, y + 1), (x + 4, y + 1)], ramp[2])


def branches(c: Canvas, spots: Iterable[tuple[int, int, int]], ramp: Sequence[Color], slot: int) -> None:
    """Snapped branches lying on the ground. ``spots`` are (tile column, floor row of the open
    tile above the ground, direction +1/-1); only tiles already in ``slot`` are painted."""
    for tx, ty, d in spots:
        x, y = tx * TILE, ty * TILE
        a = (lambda u: x + u) if d > 0 else (lambda u: x + 7 - u)
        c.line(slot, [(a(0), y + 6), (a(7), y + 5)], ramp[2], 2)
        c.line(slot, [(a(3), y + 5), (a(5), y + 2)], ramp[2], 1)
        c.line(slot, [(a(5), y + 5), (a(7), y + 3)], ramp[2], 1)


def rope_lashings(c: Canvas, platforms: Iterable[tuple[int, int, int]], ramp: Sequence[Color], slot: int) -> None:
    """Rope binding at both ends of every one-way plank walk, plus a drooping rope under the
    middle, so "drop through here" reads as plank-and-rope, not rock. The lip row is untouched."""
    for row, x0, x1 in platforms:
        y = row * TILE
        left, right = x0 * TILE, x1 * TILE + 7
        for x in (left + 3, right - 4):
            c.rect(slot, (x, y + 1, x + 2, y + 6), ramp[2])
            for k in (2, 4):
                c.line(slot, [(x, y + k), (x + 2, y + k + 1)], ramp[0])
        mid = (left + right) // 2
        c.line(slot, [(left + 5, y + 7), (mid - 4, y + 7)], ramp[2])


def ground_spots(grid: list[list[int]], avoid: set[tuple[int, int]], seed: int = 0, mod: int = 11) -> list[tuple[int, int, int]]:
    """(column, open row above the rock, direction) of spread-out exposed rock tops for debris.
    ``avoid`` holds (row, column) cells to keep clear (hazard lanes and their neighbours)."""
    out = []
    for ty in range(1, len(grid)):
        if ty * TILE < HUD_PX + TILE:
            continue
        for tx in range(1, len(grid[ty]) - 1):
            if grid[ty][tx] != shaft.COL_SOLID or grid[ty - 1][tx] != shaft.COL_EMPTY:
                continue
            if any((ty - 1, tx + dx) in avoid or (ty - 2, tx + dx) in avoid for dx in (-1, 0, 1)):
                continue
            if (tx * 7 + ty * 5 + seed) % mod == 0:
                out.append((tx, ty - 1, 1 if (tx + ty) % 2 else -1))
    return out


def paint_markers(c: Canvas, markers, claimed: set[tuple[int, int]], style: str, ramp: Sequence[Color], slot: int) -> None:
    """Draw every motif, painting only the tiles ``claim_markers`` took for it."""
    masked = [[slot if (tx, ty) in claimed else -1 for tx in range(len(row))] for ty, row in enumerate(c.slots)]
    only = Canvas(c.image, masked)
    for marker in markers:
        draw_marker(only, marker, style, ramp, slot)


def runoff(c: Canvas, grid: list[list[int]], ramp: Sequence[Color], slot: int, seed: int = 0, mod: int = 7) -> None:
    """Wet streaks where water runs down interior rock faces (solid above and below): a dark
    two-pixel stain with a pale drip at its foot, drawn inside the rock tile."""
    for ty in range(1, len(grid) - 1):
        if ty * TILE < HUD_PX:
            continue
        for tx in range(len(grid[ty])):
            if grid[ty][tx] == shaft.COL_SOLID and grid[ty - 1][tx] == shaft.COL_SOLID \
                    and grid[ty + 1][tx] == shaft.COL_SOLID and (tx * 3 + ty * 5 + seed) % mod == 0:
                x, y = tx * TILE + 2 + (tx + ty) % 3 * 2, ty * TILE
                c.rect(slot, (x, y, x + 1, y + 6), ramp[0])
                c.point(slot, (x, y + 7), ramp[2])


def mast(c: Canvas, slot: int, x: int, top: int, bottom: int, ramp: Sequence[Color]) -> None:
    """A radio mast in the night slot: tapering lattice, cross-bracing, a lit beacon and a dish."""
    for k, y in enumerate(range(top + 6, bottom - 4, 10)):
        half = 2 + (y - top) // 12
        c.line(slot, [(x - half, y + 10), (x + half, y)] if k % 2 else [(x - half, y), (x + half, y + 10)], ramp[3])
    c.line(slot, [(x - 2, top + 8), (x, top)], ramp[3], 2)
    c.line(slot, [(x + 2, top + 8), (x, top)], ramp[3], 2)
    c.line(slot, [(x - 2 - (bottom - top) // 12, bottom), (x - 2, top + 8)], ramp[3], 2)
    c.line(slot, [(x + 2 + (bottom - top) // 12, bottom), (x + 2, top + 8)], ramp[3], 2)
    c.rect(slot, (x - 1, top - 2, x, top - 1), ramp[3])                 # beacon
    c.polygon(slot, [(x + 3, top + 14), (x + 8, top + 11), (x + 8, top + 19)], ramp[3])   # dish
