"""Wind Ridge background checks; run with managed Python after regeneration."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

import climb
import intro
import make_ridge_art as art
import opening
import ridge
from test_opening import decode_rle

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = ROOT / "assets/backgrounds/wind_ridge.png"
SIDECAR = Path(str(BACKGROUND) + ".gbsres")
GRAYS = {255, 170, 85, 0}


class RidgeBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
        cls.flat_slots = decode_rle(cls.sidecar["tileColors"])
        cls.slots = [cls.flat_slots[row * ridge.MAP_W:(row + 1) * ridge.MAP_W]
                     for row in range(ridge.MAP_H)]
        with Image.open(BACKGROUND) as image:
            cls.proxy = image.convert("RGB")
            cls.image_size = image.size
        cls.grid = ridge.collision_grid()

    def slot(self, tx: int, ty: int) -> int:
        return self.slots[ty][tx]

    def native(self, tx: int, ty: int, x: int, y: int) -> int:
        gray = self.proxy.getpixel((tx * ridge.TILE + x, ty * ridge.TILE + y))[0]
        return art._gb_studio_native_index(gray)

    def test_size_and_sidecar_identity(self):
        self.assertEqual(self.image_size, (320, 144))
        self.assertEqual(self.sidecar["id"], ridge.BACKGROUND_ID)
        self.assertEqual(self.sidecar["name"], "wind_ridge")
        self.assertEqual((self.sidecar["width"], self.sidecar["height"]), (40, 18))
        self.assertEqual((self.sidecar["imageWidth"], self.sidecar["imageHeight"]), (320, 144))
        self.assertFalse(self.sidecar["autoColor"])
        self.assertEqual(len(self.flat_slots), 40 * 18)

    def test_proxy_is_grayscale_native_indices(self):
        pixels = list(self.proxy.get_flattened_data())
        self.assertTrue(all(r == g == b for r, g, b in pixels), "proxy must be grayscale")
        self.assertTrue({r for r, _, _ in pixels} <= GRAYS)

    def test_committed_art_matches_generator(self):
        image, slots = art.make_background()
        self.assertEqual(slots, self.slots, "run tools/make_ridge_art.py to regenerate")
        proxy = art.encode_native_background(image, slots)
        self.assertEqual(proxy.tobytes(), self.proxy.tobytes())

    def test_palette_slots_avoid_ui_and_stay_in_bg_families(self):
        self.assertEqual(len(opening.BG_PALETTES), 7, "slot 7 is reserved for UI")
        self.assertTrue(all(0 <= slot < 7 for slot in self.flat_slots))

    def test_collision_and_art_alignment(self):
        for ty, row in enumerate(self.grid):
            for tx, cell in enumerate(row):
                slot = self.slot(tx, ty)
                if cell == climb.COL_SOLID:
                    self.assertIn(slot, (art.STONE, art.EARTH), f"solid tile {tx},{ty} not rock")
                elif cell == climb.COL_EMPTY:
                    self.assertNotIn(slot, (art.STONE, art.EARTH),
                                     f"open air at {tx},{ty} drawn as rock")
                else:
                    self.assertEqual(slot, art.TIMBER, f"one-way tile {tx},{ty} not timber")

    def test_solid_tiles_read_as_rock(self):
        for ty, row in enumerate(self.grid):
            for tx, cell in enumerate(row):
                if cell != climb.COL_SOLID:
                    continue
                body = sum(self.native(tx, ty, x, y) == 1
                           for y in range(ridge.TILE) for x in range(ridge.TILE))
                self.assertGreaterEqual(body, 40, f"rock tile {tx},{ty} is not solid")

    def test_ledges_are_thin_timber_catwalks(self):
        for row, x0, x1 in ridge.LEDGES:
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.slot(tx, row), art.TIMBER)
                self.assertTrue(all(self.native(tx, row, x, 0) == 3 for x in range(ridge.TILE)),
                                f"ledge lip missing at {tx},{row}")
                body = sum(self.native(tx, row, x, y) == 1
                           for y in (2, 3, 4) for x in range(ridge.TILE))
                self.assertGreaterEqual(body, 12, f"ledge body missing at {tx},{row}")

    def test_pole_stands_on_plateau_and_background_draws_no_stub(self):
        # The pole is the intro_pole actor: its footprint (rows py-3..py, two
        # tiles wide) keeps no BG timber stub, and the cable starts on its top row.
        px, py = ridge.DAMAGED_POLE
        self.assertEqual(self.grid[py][px], climb.COL_EMPTY)
        self.assertEqual(self.grid[py + 1][px], climb.COL_SOLID, "pole must stand on the plateau")
        self.assertEqual(ridge.CABLE_ROUTE[0], (px, py - 3))
        self.assertFalse(hasattr(art, "POLE_TILES"))
        for ty in range(py - 3, py + 1):
            for tx in (px, px + 1):
                self.assertEqual(self.grid[ty][tx], climb.COL_EMPTY)
                self.assertNotEqual(self.slot(tx, ty), art.TIMBER, f"BG stub at {tx},{ty}")

    def test_only_cable_pixels_use_the_line_index_in_metal_slot(self):
        route = art.cable_route_tiles()
        line_cells = set()
        for ty in range(ridge.MAP_H):
            for tx in range(ridge.MAP_W):
                if self.slot(tx, ty) != climb.LINE_BG_SLOT:
                    continue
                for y in range(ridge.TILE):
                    for x in range(ridge.TILE):
                        if self.native(tx, ty, x, y) == climb.LINE_COLOR_INDEX:
                            line_cells.add((tx, ty))
        claimed_route = {(tx, ty) for tx, ty in route
                         if self.slot(tx, ty) == climb.LINE_BG_SLOT}
        self.assertTrue(line_cells)
        self.assertEqual(line_cells, claimed_route)

    def test_cable_links_pole_and_junction_box_and_house(self):
        cells = {(tx, ty) for tx, ty in art.cable_route_tiles()
                 if self.slot(tx, ty) == climb.LINE_BG_SLOT}

        def near(targets, reach=1):
            return any(max(abs(ax - bx), abs(ay - by)) <= reach
                       for ax, ay in cells for bx, by in targets)

        pole = {(ridge.DAMAGED_POLE[0], ridge.DAMAGED_POLE[1] - 3)}
        house_x0, house_x1, house_y0, house_y1 = ridge.HOUSE_RECT
        house = {(x, y) for x in range(house_x0, house_x1 + 1)
                 for y in range(house_y0, house_y1 + 1)}
        self.assertTrue(near(pole), "cable must leave the pole")
        self.assertTrue(near({ridge.JUNCTION_BOX}), "cable must reach the junction box")
        self.assertTrue(near(house, reach=1), "cable must reach the house")

    def test_cable_cells_are_empty_collision(self):
        for tx, ty in art.cable_route_tiles():
            if self.slot(tx, ty) == climb.LINE_BG_SLOT:
                self.assertEqual(self.grid[ty][tx], climb.COL_EMPTY, f"cable on collision {tx},{ty}")
                self.assertNotIn((ty, tx), art.LANE_CELLS)

    def test_window_slot_belongs_to_house_windows_alone(self):
        lit = {(tx, ty) for ty in range(ridge.MAP_H) for tx in range(ridge.MAP_W)
               if self.slot(tx, ty) == ridge.WINDOW_BG_SLOT}
        self.assertEqual(lit, set(ridge.HOUSE_WINDOWS))
        self.assertEqual(len(ridge.HOUSE_WINDOWS), len(lit), "each window is one tile")
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        for tx, ty in ridge.HOUSE_WINDOWS:
            self.assertTrue(x0 <= tx <= x1 and y0 <= ty <= y1)

    def test_cabin_sits_in_open_air_with_its_door(self):
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.grid[ty][tx], climb.COL_EMPTY)
        dx, dy = ridge.HOUSE_DOOR
        self.assertTrue(x0 <= dx <= x1 and y0 <= dy <= y1)
        self.assertEqual(self.slot(dx, dy), art.TIMBER)
        # The doorway is dark timber, not a window.
        self.assertTrue(all(self.native(dx, dy, x, 2) == 0 for x in range(2, 6)))

    def test_gust_lanes_are_open_air_metal_placards(self):
        for row, x0, x1 in ridge.GUST_LANES:
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.grid[row][tx], climb.COL_EMPTY)
                self.assertEqual(self.slot(tx, row), art.METAL)

    def test_hud_rows_are_plain_sky(self):
        for ty in range(ridge.HUD_ROWS):
            for tx in range(ridge.MAP_W):
                self.assertEqual(self.slot(tx, ty), art.SKY)
                self.assertTrue(all(self.native(tx, ty, x, y) == 0
                                    for y in range(ridge.TILE) for x in range(ridge.TILE)))

    def test_background_tile_budget(self):
        self.assertLessEqual(art._unique_indexed_tiles(self.proxy, self.slots), 192)
        self.assertLessEqual(art._unique_indexed_tiles(self.proxy, self.slots),
                             art.MAX_UNIQUE_TILES)


if __name__ == "__main__":
    unittest.main()
