"""Tests for the logo / intro story / title backgrounds (make_intro_art.py)."""
import json
import re
import unittest
from pathlib import Path

from PIL import Image

import intro

BG = intro.ROOT / "assets/backgrounds"
TILE = intro.TILE
STEMS = ("intro_logo", "intro_story", "title")
GRAY_TO_INDEX = {255: 0, 170: 1, 85: 2, 0: 3}
ALLOWED = {"intro_logo": {0, 1}, "intro_story": {0, 1, 2, 3, 4, 5, 6},
           "title": {0, 1, 2, 3, 4, 5, 6, 7}}
_RLE = re.compile(r"([0-9a-f]{2})(?:!|([0-9a-f]+)\+)")


def sidecar(stem):
    return json.loads((BG / f"{stem}.png.gbsres").read_text())


def decode(rle, count):
    out = []
    for value, n in _RLE.findall(rle):
        out.extend([int(value, 16)] * (int(n, 16) if n else 1))
    assert len(out) == count, (len(out), count)
    return [out[r * intro.MAP_W:(r + 1) * intro.MAP_W] for r in range(intro.MAP_H)]


def tile_indices(img, tx, ty):
    return [GRAY_TO_INDEX[img.getpixel((tx * TILE + x, ty * TILE + y))[0]]
            for y in range(TILE) for x in range(TILE)]


class IntroBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.img = {s: Image.open(BG / f"{s}.png").convert("RGB") for s in STEMS}
        cls.res = {s: sidecar(s) for s in STEMS}
        cls.slots = {s: decode(cls.res[s]["tileColors"], intro.MAP_W * intro.MAP_H)
                     for s in STEMS}

    def test_sizes_and_sidecars(self):
        for s in STEMS:
            self.assertEqual(self.img[s].size, (160, 144))
            r = self.res[s]
            self.assertEqual(r["id"], intro.BACKGROUND_IDS[s])
            self.assertEqual((r["width"], r["height"]), (20, 18))
            self.assertEqual((r["imageWidth"], r["imageHeight"]), (160, 144))
            self.assertIs(r["autoColor"], False)
            self.assertEqual(r["filename"], f"{s}.png")

    def test_proxy_values_and_unique_tiles(self):
        for s in STEMS:
            tiles = set()
            for ty in range(intro.MAP_H):
                for tx in range(intro.MAP_W):
                    tiles.add((self.slots[s][ty][tx], tuple(tile_indices(self.img[s], tx, ty))))
            self.assertLessEqual(len(tiles), {"title": 256}.get(s, 192), s)

    def test_slots_allowed(self):
        for s in STEMS:
            used = {v for row in self.slots[s] for v in row}
            self.assertLessEqual(used, ALLOWED[s], s)

    def test_story_windows(self):
        slots = self.slots["intro_story"]
        window_tiles = {}
        for x0, x1, roof, base, windows, wslot in intro.HOUSES:
            for x, y in windows:
                window_tiles[(x, y)] = wslot
                self.assertEqual(slots[y][x], wslot)
                idx = tile_indices(self.img["intro_story"], x, y)
                self.assertIn(0, idx)
                self.assertGreaterEqual(sum(i >= 2 for i in idx), 16)
            for y in range(roof, base + 1):
                for x in range(x0, x1 + 1):
                    if (x, y) not in window_tiles:
                        self.assertEqual(slots[y][x], 6 if y == roof else 2)
        for y, row in enumerate(slots):
            for x, v in enumerate(row):
                if v in intro.WINDOW_SLOTS:
                    self.assertIn((x, y), window_tiles)

    def test_story_plain_sprite_areas(self):
        slots = self.slots["intro_story"]
        px, py = intro.POLE
        for y in range(py - 3, py + 1):
            for x in (px, px + 1):
                self.assertEqual(slots[y][x], 1)
        for y in range(intro.HORIZON_ROW):
            self.assertTrue(all(slots[y][x] == intro.SKY_SLOT for x in range(intro.MAP_W)
                                if not any(h[2] <= y <= h[3] and h[0] <= x <= h[1]
                                           for h in intro.HOUSES)))
        self.assertTrue(all(slots[y][x] == 1 for y in range(intro.HORIZON_ROW, intro.MAP_H)
                            for x in range(intro.MAP_W)
                            if not any(h[0] <= x <= h[1] and h[2] <= y <= h[3]
                                       for h in intro.HOUSES)))
        # sky uses all four ramp indices
        used = {i for y in range(intro.HORIZON_ROW * TILE) for x in range(160)
                for i in [GRAY_TO_INDEX[self.img["intro_story"].getpixel((x, y))[0]]]}
        self.assertEqual(used, {0, 1, 2, 3})

    def test_title_text_band(self):
        # Flat UI[0] band; PRESS START and the version tag are baked into their
        # own whole rows (PRESS_SLOT / VERSION_SLOT) so blinking swaps one slot.
        lo, hi = intro.TEXT_BAND_ROWS
        text_rows = {intro.PRESS_START_ROW: intro.PRESS_SLOT,
                     intro.VERSION_ROW: intro.VERSION_SLOT,
                     intro.COPYRIGHT_ROW: intro.VERSION_SLOT}
        for ty in range(lo, hi + 1):
            slot = text_rows.get(ty, 7)
            used = set()
            for tx in range(intro.MAP_W):
                self.assertEqual(self.slots["title"][ty][tx], slot)
                used |= set(tile_indices(self.img["title"], tx, ty))
            self.assertEqual(used == {0}, ty not in text_rows, ty)
        for ty in range(lo):
            self.assertTrue({5, 6, 7}.isdisjoint(self.slots["title"][ty]))

    def _bright_rows(self, stem, rows):
        lo, hi = rows
        count = sum(i >= 2 for ty in range(lo, hi + 1) for tx in range(intro.MAP_W)
                    for i in tile_indices(self.img[stem], tx, ty))
        return count

    def test_lettering_present(self):
        for rows in intro.LOGO_TEXT_ROWS.values():
            self.assertGreater(self._bright_rows("intro_logo", rows), 100)
            for ty in range(rows[0], rows[1] + 1):
                self.assertEqual({self.slots["intro_logo"][ty][x] for x in range(20)}, {1})
        for rows in intro.TITLE_ROWS.values():
            self.assertGreater(self._bright_rows("title", rows), 50)
        lo, hi = intro.TITLE_ROWS["MR CFE"]
        for ty in range(lo, hi + 1):
            self.assertTrue(all(self.slots["title"][ty][x] == 1 for x in range(2, 18)))


if __name__ == "__main__":
    unittest.main()
