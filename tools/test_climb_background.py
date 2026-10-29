"""Climb-art integration checks; run with managed Python after regeneration."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

import climb
import make_climb_art as art
from test_opening import decode_rle

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = ROOT / "assets/backgrounds/storm_climb.png"
PROXY_INDEX = {255: 0, 170: 1, 85: 2, 0: 3}


def load():
    slots = decode_rle(json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())["tileColors"])
    with Image.open(BACKGROUND) as image:
        proxy = image.convert("RGB")
    return [slots[row * climb.MAP_W:(row + 1) * climb.MAP_W] for row in range(climb.MAP_H)], proxy


class ClimbBackgroundTests(unittest.TestCase):
    def test_compiler_proxy_and_palette_slots(self):
        sidecar = json.loads(Path(str(BACKGROUND) + ".gbsres").read_text())
        self.assertEqual((sidecar["width"], sidecar["height"]), (20, 36))
        self.assertEqual((sidecar["imageWidth"], sidecar["imageHeight"]), (160, 288))
        self.assertFalse(sidecar["autoColor"])
        slots, proxy = load()
        self.assertTrue(all(0 <= slot < 7 for row in slots for slot in row), "UI slot 7 is reserved")
        self.assertEqual(proxy.size, (160, 288))
        self.assertTrue({proxy.getpixel((x, y)) for y in range(288) for x in range(160)}
                        <= {(v, v, v) for v in PROXY_INDEX})

    def test_disk_matches_the_generator(self):
        image, slots = art.make_background()
        disk_slots, proxy = load()
        self.assertEqual(disk_slots, slots)
        self.assertEqual(list(art.encode_native_background(image, slots).get_flattened_data()),
                         list(proxy.get_flattened_data()))

    def test_collision_materials(self):
        slots, _ = load()
        grid = climb.collision_grid()
        for y, row in enumerate(grid):
            for x, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    self.assertEqual(slots[y][x], art.STONE, (x, y))
                elif cell == climb.COL_TOP:
                    self.assertEqual(slots[y][x], art.TIMBER, (x, y))

    def test_summit_windows_alone_own_the_power_slot(self):
        slots, _ = load()
        lit = {(x, y) for y, row in enumerate(slots) for x, slot in enumerate(row) if slot == art.WINDOW}
        self.assertEqual(lit, set(climb.SUMMIT_WINDOW_TILES))

    def test_transformers_are_hardware_with_bushings_in_their_stage_slot(self):
        slots, proxy = load()
        for line in climb.LINES:
            top, body = climb.transformer_tiles(line["box"])
            stage = line["number"]
            for x, y in body:
                self.assertEqual(slots[y][x], art.HARDWARE)
            stage_index = climb.STAGE_COLOR_INDEX[stage - 1]
            for x, y in top:
                self.assertEqual(slots[y][x], climb.stage_slot(stage))
                indexes = {PROXY_INDEX[proxy.getpixel((x * 8 + dx, y * 8 + dy))[0]]
                           for dy in range(8) for dx in range(8)}
                self.assertIn(stage_index, indexes, f"transformer {stage} bushing tile {(x, y)} not lit-able")
        hardware = {(x, y) for y, row in enumerate(slots) for x, slot in enumerate(row) if slot == art.HARDWARE}
        sx0, sx1, sy0, sy1 = climb.SUBSTATION_TILES
        substation = {(x, y) for x in range(sx0, sx1 + 1) for y in range(sy0, sy1 + 1)}
        bodies = {cell for line in climb.LINES for cell in climb.transformer_tiles(line["box"])[1]}
        self.assertEqual(hardware, substation | bodies)

    def test_wire_tiles_light_only_their_own_stage(self):
        """In slots 5 and 6, every non-zero index is a stage colour drawn by that stage's wire or bushing."""
        slots, proxy = load()
        bushing = {}
        for line in climb.LINES:
            bx, by = line["box"]
            left, top = bx * 8, (by - climb.TRANSFORMER_H + 1) * 8
            for dy, row in enumerate(art.TRANSFORMER_ART):
                for dx, code in enumerate(row):
                    if code == "W":
                        bushing[(left + dx, top + dy)] = line["number"]
        checked = 0
        for ty, row in enumerate(slots):
            for tx, slot in enumerate(row):
                if slot not in (art.WIRE_1, art.WIRE_2):
                    continue
                for y in range(ty * 8, ty * 8 + 8):
                    for x in range(tx * 8, tx * 8 + 8):
                        index = PROXY_INDEX[proxy.getpixel((x, y))[0]]
                        if index == 0:
                            continue
                        stages = {s for s in range(1, 6) if (x, y) in art.stage_pixels(s)}
                        if (x, y) in bushing:
                            stages.add(bushing[(x, y)])
                        owners = [s for s in stages if climb.stage_slot(s) == slot
                                  and climb.STAGE_COLOR_INDEX[s - 1] == index]
                        self.assertTrue(owners, f"stray index {index} at {(x, y)}")
                        checked += 1
        self.assertGreater(checked, 500)

    def test_every_stage_shows_a_continuous_visible_run(self):
        slots, _ = load()
        grid = climb.collision_grid()
        for stage in range(1, 6):
            tiles = {(x // 8, y // 8) for x, y in art.stage_pixels(stage)}
            shown = {(x, y) for x, y in tiles if slots[y][x] == climb.stage_slot(stage)}
            self.assertGreaterEqual(len(shown), 8, f"stage {stage} barely visible")
            for x, y in shown:
                self.assertEqual(grid[y][x], climb.COL_EMPTY, "wires are drawn on open air only")

    def test_background_tile_budget(self):
        image, slots = art.make_background()
        unique = art.unique_indexed_tiles(art.encode_native_background(image, slots), slots)
        self.assertLess(unique, art.MAX_UNIQUE_TILES)


if __name__ == "__main__":
    unittest.main()
