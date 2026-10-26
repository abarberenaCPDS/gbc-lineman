"""Climb-art integration checks; run with managed Python after regeneration."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

import climb
import opening
from test_opening import decode_rle

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = ROOT / "assets/backgrounds/storm_climb.png"


class ClimbBackgroundTests(unittest.TestCase):
    def test_compiler_proxy_and_palette_slots(self):
        sidecar = json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())
        self.assertEqual((sidecar["width"], sidecar["height"]), (20, 36))
        self.assertEqual((sidecar["imageWidth"], sidecar["imageHeight"]), (160, 288))
        self.assertFalse(sidecar["autoColor"])
        slots = decode_rle(sidecar["tileColors"])
        self.assertEqual(len(slots), 20 * 36)
        self.assertTrue(all(0 <= slot < 7 for slot in slots), "UI slot 7 is reserved")
        with Image.open(BACKGROUND) as image:
            self.assertEqual(image.size, (160, 288))
            self.assertTrue(set(image.convert("RGB").get_flattened_data()) <= {
                (255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0),
            })

    def test_material_signal_at_supported_collisions(self):
        """The lower game-facing portion must not revert to blank debug bars."""
        slots = decode_rle(json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())["tileColors"])
        grid = climb.collision_grid()
        # A supported edge must be a terrain/catwalk palette, not night or UI.
        for row, x0, x1 in climb.PLATFORMS:
            for x in range(x0, x1 + 1):
                self.assertEqual(grid[row][x], climb.COL_TOP)
                self.assertIn(slots[row * climb.MAP_W + x], (1, 2, 4, 5, 6))
        self.assertEqual(len(opening.BG_PALETTES), 7)

    def test_summit_windows_alone_own_the_power_slot(self):
        import make_climb_art
        slots = decode_rle(json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())["tileColors"])
        lit = {(i % climb.MAP_W, i // climb.MAP_W) for i, slot in enumerate(slots) if slot == 3}
        self.assertEqual(lit, set(make_climb_art.SUMMIT_WINDOW_TILES))

    def _slot_and_proxy(self):
        slots = decode_rle(json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())["tileColors"])
        with Image.open(BACKGROUND) as image:
            return slots, image.convert("RGB")

    def test_only_cable_pixels_use_the_line_index_in_metal_slot(self):
        import make_climb_art as art
        slots, proxy = self._slot_and_proxy()
        route = art.cable_route_tiles()
        line_cells = set()
        for ty in range(climb.MAP_H):
            for tx in range(climb.MAP_W):
                if slots[ty * climb.MAP_W + tx] != climb.LINE_BG_SLOT:
                    continue
                for y in range(climb.TILE):
                    for x in range(climb.TILE):
                        gray = proxy.getpixel((tx * climb.TILE + x, ty * climb.TILE + y))[0]
                        if art._gb_studio_native_index(gray) == climb.LINE_COLOR_INDEX:
                            line_cells.add((tx, ty))
        claimed_route = {
            (tx, ty) for tx, ty in route
            if slots[ty * climb.MAP_W + tx] == climb.LINE_BG_SLOT
        }
        # Every index-1 metal pixel is a cable pixel on a claimed route tile,
        # and every claimed route tile carries cable pixels.
        self.assertTrue(line_cells)
        self.assertEqual(line_cells, claimed_route)

    def test_cable_links_pole_and_junction_box(self):
        import make_climb_art as art
        slots, _ = self._slot_and_proxy()
        cells = {
            (tx, ty) for tx, ty in art.cable_route_tiles()
            if slots[ty * climb.MAP_W + tx] == climb.LINE_BG_SLOT
        }

        def near(tiles, targets):
            return any(max(abs(ax - bx), abs(ay - by)) <= 1
                       for ax, ay in tiles for bx, by in targets)

        self.assertTrue(near(cells, set(art.POLE_TILES) | {climb.DAMAGED_POLE}))
        self.assertTrue(near(cells, {climb.JUNCTION_BOX}))

    def test_cable_cells_are_empty_collision(self):
        import make_climb_art as art
        slots, _ = self._slot_and_proxy()
        grid = climb.collision_grid()
        for tx, ty in art.cable_route_tiles():
            if slots[ty * climb.MAP_W + tx] == climb.LINE_BG_SLOT:
                self.assertEqual(grid[ty][tx], climb.COL_EMPTY, f"cable on collision {tx},{ty}")
        for tx, ty in art.POLE_TILES:
            self.assertEqual(grid[ty][tx], climb.COL_EMPTY, f"pole on collision {tx},{ty}")

    def test_background_tile_budget(self):
        import make_climb_art as art
        slots, proxy = self._slot_and_proxy()
        grid_slots = [slots[row * climb.MAP_W:(row + 1) * climb.MAP_W]
                      for row in range(climb.MAP_H)]
        self.assertLessEqual(art._unique_indexed_tiles(proxy, grid_slots), 192)


if __name__ == "__main__":
    unittest.main()
