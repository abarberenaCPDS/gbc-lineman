"""Generate the logo / intro-story / title backgrounds from the ``intro.py`` contract.

Modelled on ``make_kiko_art.py``: each scene is authored as 4-colour indices per
pixel plus one BG palette slot per 8x8 tile, rendered to an RGB artist preview
(``build/intro_preview/``) and encoded as the compiler-facing grayscale index
proxy (``NATIVE_PROXY_BY_INDEX``). This generator owns only the three
backgrounds below and their sidecars.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image, ImageDraw

import intro
from make_climb_scene import collision_rle

ROOT = intro.ROOT
BG_DIR = ROOT / "assets/backgrounds"
PREVIEW_DIR = ROOT / "build/intro_preview"
TILE = intro.TILE
MAP_W, MAP_H = intro.MAP_W, intro.MAP_H
WIDTH, HEIGHT = MAP_W * TILE, MAP_H * TILE
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
MAX_UNIQUE_TILES = 192
# The title is a TOPDOWN scene with no runtime text; CGB splits its tiles over
# both VRAM banks (GB Studio MAX_BACKGROUND_TILES_CGB = 384).
TILE_BUDGET = {"intro_logo": MAX_UNIQUE_TILES, "intro_story": MAX_UNIQUE_TILES, "title": 256}
UI_SLOT = 7

SLOTS_BY_STEM = {"intro_logo": intro.LOGO_SLOTS, "intro_story": intro.STORY_SLOTS,
                 "title": intro.TITLE_SLOTS}


def _rgb(hexcolor: str) -> tuple[int, int, int]:
    return tuple(bytes.fromhex(hexcolor))


# ---------------------------------------------------------------------------
# Pixel fonts (rows of '#'), variable width, 7 tall.
# ---------------------------------------------------------------------------
FONT = {
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "B": ["####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."],
    "C": [".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."],
    "E": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
    "F": ["#####", "#....", "#....", "####.", "#....", "#....", "#...."],
    "G": [".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."],
    "M": ["#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"],
    "P": ["####.", "#...#", "#...#", "####.", "#....", "#....", "#...."],
    "R": ["####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"],
    "S": [".####", "#....", "#....", ".###.", "....#", "....#", "####."],
    "T": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
    "N": ["#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"],
    "'": ["##", "##", "#.", "..", "..", "..", ".."],
    "f": [".##", "#..", "###", "#..", "#..", "#..", "#.."],
    "t": ["#..", "#..", "###", "#..", "#..", "#..", ".##"],
    "e": ["....", "....", ".##.", "#..#", "####", "#...", ".###"],
    "r": ["...", "...", "#.#", "##.", "#..", "#..", "#.."],
    "h": ["#...", "#...", "###.", "#..#", "#..#", "#..#", "#..#"],
    "o": ["....", "....", ".##.", "#..#", "#..#", "#..#", ".##."],
    "m": [".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"],
    # Version tag (read from VERSION at generation time).
    "v": ["...", "...", "#.#", "#.#", "#.#", "#.#", ".#."],
    "d": ["...#", "...#", ".###", "#..#", "#..#", "#..#", ".###"],
    "a": ["....", "....", ".##.", "...#", ".###", "#..#", ".###"],
    "l": ["#", "#", "#", "#", "#", "#", "#"],
    "b": ["#...", "#...", "###.", "#..#", "#..#", "#..#", "###."],
    "c": ["...", "...", ".##", "#..", "#..", "#..", ".##"],
    ".": [".", ".", ".", ".", ".", ".", "#"],
    "-": ["...", "...", "...", "###", "...", "...", "..."],
    "+": ["...", "...", ".#.", "###", ".#.", "...", "..."],
    "0": [".##.", "#..#", "#..#", "#..#", "#..#", "#..#", ".##."],
    "1": [".#", "##", ".#", ".#", ".#", ".#", ".#"],
    "2": [".##.", "#..#", "...#", "..#.", ".#..", "#...", "####"],
    "3": ["###.", "...#", "...#", ".##.", "...#", "...#", "###."],
    "4": ["#..#", "#..#", "#..#", "####", "...#", "...#", "...#"],
    "5": ["####", "#...", "###.", "...#", "...#", "#..#", ".##."],
    "6": [".##.", "#...", "###.", "#..#", "#..#", "#..#", ".##."],
    "7": ["####", "...#", "..#.", "..#.", ".#..", ".#..", ".#.."],
    "8": [".##.", "#..#", "#..#", ".##.", "#..#", "#..#", ".##."],
    "9": [".##.", "#..#", "#..#", ".###", "...#", "...#", ".##."],
    "\u00a9": [".#####.", "#.....#", "#.###.#", "#.#...#", "#.###.#", "#.....#", ".#####."],
}
SPACE_COLS = 3


def text_mask(text: str, sx: int, sy: int, gap: int) -> tuple[set[tuple[int, int]], int, int]:
    """Scaled pixel mask (relative coords), plus its width and height."""
    pen = 0
    mask: set[tuple[int, int]] = set()
    for ch in text:
        if ch == " ":
            pen += SPACE_COLS * sx
            continue
        glyph = FONT[ch]
        for gy, row in enumerate(glyph):
            for gx, c in enumerate(row):
                if c == "#":
                    for dy in range(sy):
                        for dx in range(sx):
                            mask.add((pen + gx * sx + dx, gy * sy + dy))
        pen += len(glyph[0]) * sx + gap
    return mask, pen - gap, 7 * sy


class Scene:
    """Index canvas (0-3 per pixel) + BG palette slot per tile."""

    def __init__(self, stem: str):
        self.stem = stem
        self.names = SLOTS_BY_STEM[stem]
        self.idx = Image.new("L", (WIDTH, HEIGHT), 0)
        self.slots = [[0] * MAP_W for _ in range(MAP_H)]

    def set_rows(self, lo: int, hi: int, slot: int, x0: int = 0, x1: int = MAP_W - 1):
        for ty in range(lo, hi + 1):
            for tx in range(x0, x1 + 1):
                self.slots[ty][tx] = slot

    def put(self, x: int, y: int, v: int):
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            self.idx.putpixel((x, y), v)

    def rect(self, x0, y0, x1, y1, v):
        ImageDraw.Draw(self.idx).rectangle((x0, y0, x1, y1), fill=v)

    def tile_rect(self, tx0, ty0, tx1, ty1, v):
        self.rect(tx0 * TILE, ty0 * TILE, tx1 * TILE + 7, ty1 * TILE + 7, v)

    def ellipse(self, box, v):
        ImageDraw.Draw(self.idx).ellipse(box, fill=v)

    def text(self, text, rows, sx, sy, gap, hi, lo, shadow, shade_rows=2, sh=(2, 2),
             x_center=WIDTH // 2, y_off=None):
        """Chunky lettering centred in tile rows ``rows`` with a drop shadow."""
        mask, w, h = text_mask(text, sx, sy, gap)
        x0 = x_center - w // 2
        top, bottom = rows[0] * TILE, (rows[1] + 1) * TILE
        y0 = top + ((bottom - top - h - sh[1]) // 2 if y_off is None else y_off)
        assert x0 >= 0 and x0 + w + sh[0] <= WIDTH, f"{text!r} too wide"
        assert y0 >= top and y0 + h + sh[1] <= bottom, f"{text!r} too tall"
        for mx, my in mask:
            self.put(x0 + mx + sh[0], y0 + my + sh[1], shadow)
        for mx, my in mask:
            self.put(x0 + mx, y0 + my, hi if my < shade_rows * sy else lo)
        return x0, y0, w, h

    # -- outputs ----------------------------------------------------------
    def rgb(self) -> Image.Image:
        pals = [[_rgb(c) for c in intro.BG_PALETTES[n]] for n in self.names]
        out = Image.new("RGB", self.idx.size)
        src, dst = self.idx.load(), out.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                dst[x, y] = pals[self.slots[y // TILE][x // TILE]][src[x, y]]
        return out

    def proxy(self) -> Image.Image:
        out = Image.new("RGB", self.idx.size)
        src, dst = self.idx.load(), out.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                g = NATIVE_PROXY_BY_INDEX[src[x, y]]
                dst[x, y] = (g, g, g)
        return out


# ---------------------------------------------------------------------------
# 1. Logo
# ---------------------------------------------------------------------------
def make_logo() -> Scene:
    s = Scene("intro_logo")
    rows_big = intro.LOGO_TEXT_ROWS["ABE'S GAMES"]
    rows_small = intro.LOGO_TEXT_ROWS["PRESENT"]
    s.set_rows(*rows_big, 1)
    s.set_rows(*rows_small, 1)
    # Sparse stars (sky slot only), plus-shaped so they survive on hardware.
    rng = random.Random(0xABE5)
    free = [r for r in range(MAP_H - 1) if s.slots[r][0] == 0 and
            r not in (rows_big[0] - 1, rows_small[0] - 1) and r < rows_big[0] - 1
            or r > rows_small[1] + 1]
    stars = []
    while len(stars) < 9:
        tx, ty = rng.randrange(1, MAP_W - 1), rng.choice(free)
        if ty >= MAP_H - 1 or s.slots[ty][tx] != 0:
            continue
        if all(abs(tx - a) + abs(ty - b) > 2 for a, b in stars):
            stars.append((tx, ty))
    for i, (tx, ty) in enumerate(stars):
        cx, cy = tx * TILE + 4, ty * TILE + 4
        s.put(cx, cy, 3)
        if i % 2 == 0:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                s.put(cx + dx, cy + dy, 2)
        else:
            s.put(cx + 1, cy, 2)
            s.put(cx, cy + 1, 2)
    s.text("ABE'S GAMES", rows_big, 2, 4, 2, hi=3, lo=2, shadow=1, shade_rows=2)
    s.text("PRESENT", rows_small, 2, 2, 2, hi=3, lo=2, shadow=1, shade_rows=2, sh=(1, 1))
    return s


# ---------------------------------------------------------------------------
# 2. Story: hillside village at dusk
# ---------------------------------------------------------------------------
def _cloud(s: Scene, cx: int, cy: int, w: int):
    """Flat-bottomed cloud: lumps one index brighter than the band behind."""
    h = max(6, w // 3)
    for ox, oy, ww, hh in ((0, 2, w, h - 2), (w // 6, 0, w // 2, h - 1),
                           (w // 2, 1, w // 3, h - 2)):
        for y in range(cy + oy, cy + oy + hh):
            for x in range(cx + ox, cx + ox + ww):
                pass
    px = s.idx.load()
    cover = []
    for oy in range(h):
        for ox in range(w):
            ex = (ox - w / 2) / (w / 2)
            ey = (oy - h * 0.6) / (h * 0.6)
            if oy <= h - 3 and ex * ex + ey * ey <= 1.0 or (oy > h - 3 and abs(ex) < 0.8
                                                          and oy < h - 1):
                cover.append((cx + ox, cy + oy, oy))
    for x, y, oy in cover:
        if 0 <= x < WIDTH and 0 <= y < HEIGHT:
            band = px[x, y]
            px[x, y] = min(3, band + 1) if band < 3 else 2
    return


def make_story() -> Scene:
    s = Scene("intro_story")
    hz = intro.HORIZON_ROW
    # Sky bands (all four ramp indices, darkest top, glow at the horizon).
    sky_h = hz * TILE
    cuts = [0, sky_h * 3 // 8, sky_h * 6 // 9 - 2, sky_h * 8 // 9 - 4, sky_h]
    for band in range(4):
        s.rect(0, cuts[band], WIDTH - 1, cuts[band + 1] - 1, band)
    # Keep clear of the bolt / pole columns (sprites live there).
    bx, by = intro.BOLT
    clear = (bx - 1, bx + 2)
    for cx, cy, w in ((6, 14, 34), (88, 10, 40), (36, 40, 30), (112, 36, 28), (60, 22, 24)):
        if cx // TILE <= clear[1] and (cx + w) // TILE >= clear[0]:
            continue
        _cloud(s, cx, cy, w)
    # Hill / foliage: slot 1 from the horizon row to the bottom.
    s.set_rows(hz, MAP_H - 1, 1)
    s.tile_rect(0, hz, MAP_W - 1, MAP_H - 1, 1)
    # Tree-line tufts on the crest (row hz) and dark bushes below.
    rng = random.Random(0x5701)
    for x in range(0, WIDTH, 4):
        top = hz * TILE + rng.choice((0, 1, 1, 2))
        s.rect(x, top, x + 3, hz * TILE + 7, 1)
        s.rect(x, top, x + 3, top + 1, 2)
    for x in range(0, WIDTH, 8):
        s.put(x + rng.randrange(8), hz * TILE + rng.randrange(1, 3), 3)
    for ty in range(hz + 1, intro.GROUND_ROW):
        for tx in range(MAP_W):
            if rng.random() < 0.35:
                x, y = tx * TILE + rng.randrange(0, 5), ty * TILE + rng.randrange(0, 5)
                s.rect(x, y, x + 3, y + 2, 0)
                s.rect(x + 1, y, x + 2, y, 2)
    s.tile_rect(0, intro.GROUND_ROW, MAP_W - 1, MAP_H - 1, 1)
    for ty in range(intro.GROUND_ROW, MAP_H):
        for tx in range(MAP_W):
            if (tx + ty) % 3 == 0:
                s.rect(tx * TILE, ty * TILE + 2, tx * TILE + 5, ty * TILE + 3, 0)
    # Keep the pole / sprite columns plain.
    for px, py in intro.POLES:
        s.tile_rect(px, py - 3, px + 1, py, 1)
    # Houses.
    for x0, x1, roof, base, windows, wslot in intro.HOUSES:
        wset = set(windows)
        # walls (timber, slot 2)
        s.set_rows(roof + 1, base, 2, x0, x1)
        s.tile_rect(x0, roof + 1, x1, base, 1)
        for x in range(x0 * TILE, x1 * TILE + 8):
            s.rect(x, (roof + 1) * TILE, x, (base + 1) * TILE - 1, 2 if x % 8 not in (7, 0) else (0 if x % 8 == 7 else 3))
        s.rect(x0 * TILE, (base + 1) * TILE - 2, x1 * TILE + 7, (base + 1) * TILE - 1, 0)
        # roof (stone, slot 6): shingled slab with a lit ridge and dark eave
        s.set_rows(roof, roof, 6, x0, x1)
        ry = roof * TILE
        s.tile_rect(x0, roof, x1, roof, 2)
        s.rect(x0 * TILE, ry, x1 * TILE + 7, ry + 1, 3)
        for k, y in enumerate(range(ry + 2, ry + 7)):
            for x in range(x0 * TILE, x1 * TILE + 8):
                if (x + (k % 2) * 4) % 8 == 0:
                    s.put(x, y, 1)
        s.rect(x0 * TILE, ry + 6, x1 * TILE + 7, ry + 7, 0)
        # door at the left tile, two tiles tall
        dx = x0 * TILE
        s.rect(dx + 1, (base - 1) * TILE + 1, dx + 6, (base + 1) * TILE - 3, 0)
        s.rect(dx + 1, (base - 1) * TILE + 1, dx + 1, (base + 1) * TILE - 3, 1)
        s.put(dx + 5, base * TILE + 2, 3)
        # windows: whole tiles in the house's own window slot
        for wx, wy in windows:
            s.slots[wy][wx] = wslot
            x, y = wx * TILE, wy * TILE
            s.rect(x, y, x + 7, y + 7, 0)
            s.rect(x + 1, y + 1, x + 6, y + 6, 3)
            s.rect(x + 1, y + 5, x + 6, y + 6, 2)
            s.rect(x + 3, y + 1, x + 4, y + 6, 0)
            s.rect(x + 1, y + 3, x + 6, y + 3, 0)
    return s


# ---------------------------------------------------------------------------
# 3. Title
# ---------------------------------------------------------------------------
def _storm_cloud(s: Scene, cx: int, cy: int, w: int, h: int):
    s.ellipse((cx, cy, cx + w, cy + h), 1)
    s.ellipse((cx + w // 4, cy - h // 3, cx + w * 3 // 4, cy + h // 2), 1)
    s.rect(cx + 2, cy + h // 2, cx + w - 2, cy + h // 2 + 1, 2)


def _bolt(s: Scene, tx0: int, mirror: bool):
    """Lightning accent in metal slot 2 across two tile columns, logo rows."""
    lo, hi = intro.TITLE_ROWS["MR CFE"]
    ox, oy = tx0 * TILE, lo * TILE
    h = (hi - lo + 1) * TILE
    pts = [(9, 0), (2, h * 5 // 11), (7, h * 5 // 11), (4, h - 1),
           (13, h * 4 // 10), (8, h * 4 // 10), (13, 0)]
    if mirror:
        pts = [(15 - x, y) for x, y in pts]
    img = Image.new("L", (16, h), 0)
    d = ImageDraw.Draw(img)
    d.polygon([(x + 1, y + 1) for x, y in pts], fill=1)
    d.polygon(pts, fill=2)
    inner = [(x, y) for x, y in pts]
    d.polygon(inner, fill=3, outline=2)
    for y in range(h):
        for x in range(16):
            if img.getpixel((x, y)):
                s.put(ox + x, oy + y, img.getpixel((x, y)))


def make_title() -> Scene:
    s = Scene("title")
    rows = intro.TITLE_ROWS
    band_lo, band_hi = intro.TEXT_BAND_ROWS
    s.set_rows(0, MAP_H - 1, 0)
    # Storm clouds in the sky-slot rows (0, 2, 9).
    for cx, cy, w, h in ((6, 2, 34, 8), (60, 0, 40, 6), (112, 3, 36, 7)):
        _storm_cloud(s, cx, cy, w, h)
    for cx, w in ((20, 40), (100, 44)):
        s.ellipse((cx, 9 * TILE - 2, cx + w, 9 * TILE + 5), 1)
        s.rect(cx + 3, 9 * TILE + 3, cx + w - 3, 9 * TILE + 4, 2)
    # Row 1: small gold byline.
    s.set_rows(*rows["ABE'S GAMES PRESENT"], 1)
    s.rect(0, rows["ABE'S GAMES PRESENT"][0] * TILE, WIDTH - 1,
           rows["ABE'S GAMES PRESENT"][1] * TILE + 7, 0)
    s.text("ABE'S GAMES PRESENT", rows["ABE'S GAMES PRESENT"], 1, 1, 1, hi=3, lo=3,
           shadow=1, sh=(1, 1), y_off=0)
    # Logotype.
    lo, hi = rows["MR CFE"]
    s.set_rows(lo, hi, 1)
    s.rect(0, lo * TILE, WIDTH - 1, hi * TILE + 7, 0)
    s.set_rows(lo, hi, 2, 0, 1)
    s.set_rows(lo, hi, 2, MAP_W - 2, MAP_W - 1)
    s.rect(0, lo * TILE, 15, hi * TILE + 7, 0)
    s.rect(WIDTH - 16, lo * TILE, WIDTH - 1, hi * TILE + 7, 0)
    x0, y0, w, h = s.text("MR CFE", (lo, hi), 4, 6, 2, hi=3, lo=2, shadow=1,
                          shade_rows=3, sh=(3, 3))
    assert x0 >= 16 and x0 + w + 3 <= WIDTH - 16, "logotype collides with bolt columns"
    _bolt(s, 0, False)
    _bolt(s, MAP_W - 2, True)
    # Subtitle (metal slot 2).
    lo2, hi2 = rows["After the Storm"]
    s.set_rows(lo2, hi2, 2)
    s.rect(0, lo2 * TILE, WIDTH - 1, hi2 * TILE + 7, 0)
    s.text("After the Storm", (lo2, hi2), 2, 2, 1, hi=3, lo=3, shadow=1, shade_rows=0,
           sh=(1, 1))
    # Row 12 village silhouette (foliage slot 3) with lit windows (slot 4).
    vrow = hi2 + 1
    assert vrow < band_lo
    s.set_rows(vrow, vrow, 3)
    s.rect(0, vrow * TILE, WIDTH - 1, vrow * TILE + 7, 0)
    layout = [(0, 3), (4, 4), (9, 3), (13, 4), (18, 2)]     # (first tile, width)
    wins = {1: [1], 3: [2]}
    for i, (c0, w) in enumerate(layout):
        wall_top = vrow * TILE + 3
        s.rect(c0 * TILE, wall_top, (c0 + w) * TILE - 1, vrow * TILE + 7, 1)
        s.rect(c0 * TILE, wall_top, (c0 + w) * TILE - 1, wall_top, 2)
        # stepped roof peak
        for k in range(min(3, w * 2 - 1)):
            inset = (k + 1) * 4
            if inset * 2 >= w * TILE:
                break
            s.rect(c0 * TILE + inset, wall_top - 1 - k, (c0 + w) * TILE - 1 - inset,
                   wall_top - 1 - k, 1)
        for tx in wins.get(i, []):
            tcol = c0 + tx
            s.slots[vrow][tcol] = 4
            x, y = tcol * TILE, vrow * TILE
            s.rect(x, y, x + 7, y + 7, 1)
            s.rect(x + 1, y + 2, x + 6, y + 6, 0)
            s.rect(x + 2, y + 3, x + 5, y + 5, 3)
            s.rect(x + 2, y + 5, x + 5, y + 5, 2)
    for tx in range(MAP_W):                                # trees in the gaps
        if not any(c0 <= tx < c0 + w for c0, w in layout):
            x = tx * TILE
            s.rect(x + 3, vrow * TILE + 1, x + 4, vrow * TILE + 7, 1)
            s.rect(x + 2, vrow * TILE + 3, x + 5, vrow * TILE + 7, 1)
            s.rect(x + 3, vrow * TILE + 1, x + 4, vrow * TILE + 2, 2)
    # Text band: flat UI index 0, with PRESS START (blinked by swapping its
    # slot) and the version tag baked in; the title draws no runtime text.
    s.set_rows(band_lo, band_hi, UI_SLOT)
    s.tile_rect(0, band_lo, MAP_W - 1, band_hi, 0)
    press_row, version_row = intro.PRESS_START_ROW, intro.VERSION_ROW
    s.set_rows(press_row, press_row, intro.PRESS_SLOT)
    s.text(intro.PRESS_START, (press_row, press_row), 1, 1, 1, hi=3, lo=3, shadow=0,
           sh=(0, 0), y_off=0)
    version = intro.read_version()
    _, vw, _ = text_mask(version, 1, 1, 1)
    s.set_rows(version_row, version_row, intro.VERSION_SLOT)
    s.text(version, (version_row, version_row), 1, 1, 1, hi=2, lo=2, shadow=0,
           sh=(0, 0), y_off=0, x_center=WIDTH - TILE - (vw + 1) // 2)
    s.set_rows(intro.COPYRIGHT_ROW, intro.COPYRIGHT_ROW, intro.VERSION_SLOT)
    s.text(intro.COPYRIGHT, (intro.COPYRIGHT_ROW, intro.COPYRIGHT_ROW), 1, 1, 1, hi=2, lo=2,
           shadow=0, sh=(0, 0), y_off=0)
    return s


BUILDERS = {"intro_logo": make_logo, "intro_story": make_story, "title": make_title}


def _unique_tiles(scene: Scene) -> int:
    seen = set()
    px = scene.idx.load()
    for ty in range(MAP_H):
        for tx in range(MAP_W):
            seen.add((scene.slots[ty][tx], tuple(px[tx * TILE + x, ty * TILE + y]
                      if False else px[tx * TILE + x, ty * TILE + y]
                      for y in range(TILE) for x in range(TILE))))
    return len(seen)


def _check_slots(scene: Scene) -> None:
    allowed = {"intro_logo": {0, 1}, "intro_story": {0, 1, 2, 3, 4, 5, 6},
               "title": {0, 1, 2, 3, 4, 5, 6, 7}}[scene.stem]
    for row in scene.slots:
        for slot in row:
            assert slot in allowed, f"{scene.stem}: slot {slot} not allowed"


def _check_owned(stem: str) -> None:
    sidecar = BG_DIR / f"{stem}.png.gbsres"
    if sidecar.exists():
        cur = json.loads(sidecar.read_text(encoding="utf-8"))
        if cur.get("id") != intro.BACKGROUND_IDS[stem]:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {sidecar}")


def write_scene(scene: Scene) -> int:
    stem = scene.stem
    _check_slots(scene)
    unique = _unique_tiles(scene)
    if unique > TILE_BUDGET[stem]:
        raise AssertionError(f"{stem} uses {unique} unique tiles (budget {TILE_BUDGET[scene.stem]})")
    BG_DIR.mkdir(parents=True, exist_ok=True)
    out = BG_DIR / f"{stem}.png"
    scene.proxy().save(out, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": intro.BACKGROUND_IDS[stem],
        "name": stem,
        "symbol": f"bg_{stem}",
        "filename": out.name,
        "width": MAP_W,
        "height": MAP_H,
        "imageWidth": WIDTH,
        "imageHeight": HEIGHT,
        "autoColor": False,
        "tileColors": collision_rle(scene.slots, MAP_W, MAP_H),
    }
    Path(str(out) + ".gbsres").write_text(json.dumps(resource, indent=2) + "\n",
                                          encoding="utf-8")
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    scene.rgb().save(PREVIEW_DIR / f"{stem}.png")
    return unique


def main() -> None:
    for stem in BUILDERS:
        _check_owned(stem)
    scenes = [BUILDERS[stem]() for stem in BUILDERS]
    for scene in scenes:
        unique = write_scene(scene)
        print(f"generated assets/backgrounds/{scene.stem}.png: {unique} unique tiles "
              f"(budget {TILE_BUDGET[scene.stem]})")
    sheet = Image.new("RGB", (3 * WIDTH * 2 + 4 * 12, HEIGHT * 2 + 24), (40, 40, 40))
    for i, scene in enumerate(scenes):
        sheet.paste(scene.rgb().resize((WIDTH * 2, HEIGHT * 2), Image.NEAREST),
                    (12 + i * (WIDTH * 2 + 12), 12))
    sheet.save(PREVIEW_DIR / "contact_sheet.png")


if __name__ == "__main__":
    main()
