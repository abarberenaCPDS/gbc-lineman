"""Crest art (climb_crest.png) integration checks; run with managed Python after regeneration."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

import climb
import make_climb_art as art
from test_opening import decode_rle

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = ROOT / "assets/backgrounds/climb_crest.png"
PROXY_INDEX = {255: 0, 170: 1, 85: 2, 0: 3}
BG_TILE_BUDGET = 200      # §5 estimated 110 for the functional pass; the WP5 backdrop raised it (MCP limit 384)


def load():
    slots = decode_rle(json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())["tileColors"])
    with Image.open(BACKGROUND) as image:
        proxy = image.convert("RGB")
    return [slots[row * climb.CREST_W:(row + 1) * climb.CREST_W] for row in range(climb.CREST_H)], proxy


class CrestBackgroundTests(unittest.TestCase):
    def test_sidecar_and_proxy(self):
        sidecar = json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())
        self.assertEqual(sidecar["id"], art.resource_id("background:climb-crest"))
        self.assertEqual((sidecar["width"], sidecar["height"]), (56, 18))
        self.assertEqual((sidecar["imageWidth"], sidecar["imageHeight"]), (448, 144))
        self.assertFalse(sidecar["autoColor"])
        slots, proxy = load()
        self.assertTrue(all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 is reserved")
        self.assertTrue({proxy.getpixel((x, y)) for y in range(144) for x in range(448)}
                        <= {(v, v, v) for v in PROXY_INDEX})

    def test_disk_matches_the_generator(self):
        image, slots = art.make_crest_background()
        disk_slots, proxy = load()
        self.assertEqual(disk_slots, slots)
        self.assertEqual(list(art.encode_native_background(image, slots).get_flattened_data()),
                         list(proxy.get_flattened_data()))

    def test_collision_materials(self):
        slots, _ = load()
        for y, row in enumerate(climb.crest_collision_grid()):
            for x, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    self.assertEqual(slots[y][x], art.STONE, (x, y))
                elif cell == climb.COL_TOP:
                    self.assertEqual(slots[y][x], art.TIMBER, (x, y))

    def test_amaras_house_and_windows_on_the_porch(self):
        slots, _ = load()
        lit = {(x, y) for y, row in enumerate(slots) for x, slot in enumerate(row) if slot == art.WINDOW}
        self.assertEqual(lit, set(climb.CREST_WINDOW_TILES))
        hx0, hx1, hy0, hy1 = climb.CREST_HOUSE_RECT
        for y in range(hy0, hy1 + 1):
            for x in range(hx0, hx1 + 1):
                self.assertIn(slots[y][x], (art.TIMBER, art.WINDOW), (x, y))

    def test_transformer_five_lights_with_stage_five(self):
        slots, proxy = load()
        [line] = climb.boxes_in(climb.CREST_SCENE)
        top, body = climb.transformer_tiles(line["box"])
        self.assertTrue(all(slots[y][x] == art.HARDWARE for x, y in body))
        index = climb.STAGE_COLOR_INDEX[4]
        for x, y in top:
            self.assertEqual(slots[y][x], climb.stage_slot(5))
            indexes = {PROXY_INDEX[proxy.getpixel((x * 8 + dx, y * 8 + dy))[0]] for dy in range(8) for dx in range(8)}
            self.assertIn(index, indexes)
        hardware = {(x, y) for y, row in enumerate(slots) for x, slot in enumerate(row) if slot == art.HARDWARE}
        self.assertEqual(hardware, set(body))

    def test_stage_five_wire_enters_on_the_edge_port_row(self):
        slots, _ = load()
        grid = climb.crest_collision_grid()
        tiles = {(x // 8, y // 8) for x, y in art.crest_stage_pixels(5)}
        shown = {(x, y) for x, y in tiles if slots[y][x] == climb.stage_slot(5)}
        self.assertGreaterEqual(len(shown), 40)
        self.assertIn((1, climb.EDGE_PORT_ROW), shown)
        self.assertTrue(all(grid[y][x] == climb.COL_EMPTY for x, y in shown))
        self.assertFalse(any(slot == art.WIRE_1 for row in slots for slot in row), "stages 1-3 stay in the climb")

    def test_background_tile_budget(self):
        image, slots = art.make_crest_background()
        unique = art.unique_indexed_tiles(art.encode_native_background(image, slots), slots)
        self.assertLessEqual(unique, BG_TILE_BUDGET)


if __name__ == "__main__":
    unittest.main()
