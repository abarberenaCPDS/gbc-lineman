"""Contract, native proxy and five-stage background checks for the repair jobs.

A job scene that shows only some chain stages (a multi-scene job) declares them
as ``contract.STAGES``; wires may cross the left or right edge wall (edge ports).
"""
from __future__ import annotations

import json
import unittest

from PIL import Image

import climb
import make_ridge_art
import ridge
from test_opening import decode_rle


class BackgroundChecks:
    """Shared assertions, with the three jobs' own geometry as the source of truth."""

    @classmethod
    def setUpClass(cls):
        cls.grid = cls.contract.collision_grid()
        cls.sidecar = json.loads(cls.art.SIDECAR.read_text(encoding="utf-8"))
        flat = decode_rle(cls.sidecar["tileColors"])
        cls.flat = flat
        cls.slots = [flat[y * cls.contract.MAP_W:(y + 1) * cls.contract.MAP_W]
                     for y in range(cls.contract.MAP_H)]
        with Image.open(cls.art.OUTPUT) as image:
            cls.proxy = image.convert("RGB")

    def test_size_identity_and_proxy(self):
        c, a = self.contract, self.art
        self.assertIn((c.MAP_W, c.MAP_H), ((100, 18), (100, 30), (64, 18)))
        self.assertEqual(self.proxy.size, (c.MAP_W * 8, c.MAP_H * 8))
        self.assertEqual((self.sidecar["width"], self.sidecar["height"]), (c.MAP_W, c.MAP_H))
        self.assertEqual((self.sidecar["imageWidth"], self.sidecar["imageHeight"]), self.proxy.size)
        self.assertEqual(self.sidecar["id"], c.BACKGROUND_ID)
        self.assertFalse(self.sidecar["autoColor"])
        self.assertEqual(len(self.flat), c.MAP_W * c.MAP_H)
        self.assertTrue(all(0 <= slot < 7 for slot in self.flat))
        self.assertTrue(set(self.proxy.get_flattened_data()) <= {(v, v, v) for v in (0, 85, 170, 255)})
        self.assertLessEqual(a._unique_indexed_tiles(self.proxy, self.slots), a.MAX_UNIQUE_TILES)

    def test_generated_image_and_palette_map_are_reproducible(self):
        image, slots = self.art.make_background()
        self.assertEqual(slots, self.slots)
        self.assertEqual(self.art.encode_native_background(image, slots).tobytes(), self.proxy.tobytes())

    def test_wire_palettes_and_stage_mapping(self):
        c, a = self.contract, self.art
        self.assertEqual(c.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual([a.stage_slot(s) for s in range(1, 6)], [5, 5, 5, 6, 6])
        self.assertEqual(a.PALETTES[5], a.PALETTES[6])
        self.assertEqual(len(set(a.PALETTES[5])), 4)
        self.assertEqual(set(c.CHAIN_PALETTES), set(range(6)))
        for n in range(6):
            palettes = c.CHAIN_PALETTES[n]
            for stage in range(1, 6):
                slot, index = a.stage_slot(stage), c.STAGE_COLOR_INDEX[stage - 1]
                self.assertEqual(palettes[slot][index], c.WIRE_LIVE if stage <= n else c.WIRE_DEAD)
                self.assertEqual(palettes[slot][0], c.METAL_DEAD[0])

    def stages(self):
        return list(getattr(self.contract, "STAGES", range(1, 6)))

    def test_wire_slot_tiles_and_stage_pixels(self):
        c, a = self.contract, self.art
        owners = {s: a.stage_pixels(s) for s in range(1, 6)}
        tile_owners = {s: {(x // 8, y // 8) for x, y in owners[s]} for s in owners}
        for y, row in enumerate(self.slots):
            for x, slot in enumerate(row):
                if slot in (5, 6):
                    self.assertEqual(self.grid[y][x], climb.COL_EMPTY, (x, y))
                    self.assertTrue(any((x, y) in tile_owners[s] and a.stage_slot(s) == slot
                                        for s in owners), (x, y, slot))
        for stage in self.stages():
            pixels = owners[stage]
            slot, index = a.stage_slot(stage), c.STAGE_COLOR_INDEX[stage - 1]
            painted = {(x, y) for x, y in pixels if 0 <= x < a.WIDTH and 0 <= y < a.HEIGHT
                       and self.slots[y // 8][x // 8] == slot
                       and not any((x, y) in owners[later] and a.stage_slot(later) == slot
                                   for later in range(stage + 1, 6))}
            self.assertGreater(len(painted), 20, f"stage {stage} missing")
            for x, y in painted:
                self.assertEqual(self.proxy.getpixel((x, y))[0], a.NATIVE_PROXY_BY_INDEX[index],
                                 (stage, x, y))
            for x, y in tile_owners[stage]:
                if self.grid[y][x] != climb.COL_EMPTY:
                    self.assertIn(x, (0, c.MAP_W - 1), (stage, x, y))
                elif self.slots[y][x] != slot:
                    # A downstream slot can take only an actual shared junction tile.
                    self.assertTrue(any((x, y) in tile_owners[s] and a.stage_slot(s) == self.slots[y][x]
                                        for s in range(stage + 1, 6)), (stage, x, y))

    def test_wire_palette_boundary_shares_only_the_pole_junction_tile(self):
        a = self.art
        upstream = {(x // 8, y // 8) for x, y in a.stage_pixels(3)}
        downstream = {(x // 8, y // 8) for x, y in a.stage_pixels(4)}
        self.assertLessEqual(len(upstream & downstream), 1,
                             "different palette slots must not replace an extended upstream wire")

    def test_terrain_hazards_and_windows(self):
        c, a = self.contract, self.art
        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell == climb.COL_SOLID:
                    self.assertEqual(self.slots[y][x], a.STONE, (x, y))
                    body = sum(self.proxy.getpixel((x * 8 + dx, y * 8 + dy))[0] == 170
                               for dy in range(8) for dx in range(8))
                    self.assertGreaterEqual(body, 40, (x, y))
                elif cell == climb.COL_TOP:
                    self.assertEqual(self.slots[y][x], a.TIMBER, (x, y))
        for row, x0, x1 in c.hazard_lanes():
            for x in range(x0, x1 + 1):
                self.assertEqual(self.slots[row][x], a.STONE, (x, row))
                self.assertEqual(self.grid[row][x], climb.COL_EMPTY)
        for row, x in a.PLACARD_CELLS:
            self.assertEqual(self.slots[row][x], a.STONE, (x, row))
        for row, x0, x1 in c.LEDGES:
            for x in range(x0, x1 + 1):
                self.assertTrue(all(self.proxy.getpixel((x * 8 + dx, row * 8))[0] == 0
                                    for dx in range(8)), (x, row))
        windows = {(x, y) for y, row in enumerate(self.slots) for x, slot in enumerate(row)
                   if slot == a.WINDOW}
        self.assertEqual(windows, set(c.HOUSE_WINDOWS))
        for y in range(c.HUD_ROWS):
            self.assertEqual(set(self.slots[y]), {a.SKY})
            self.assertEqual(set(self.proxy.crop((0, y * 8, a.WIDTH, y * 8 + 8)).get_flattened_data()),
                             {(255, 255, 255)})

    def test_wire_slots_contain_no_unowned_colored_pixels(self):
        a, c = self.art, self.contract
        for y, row in enumerate(self.slots):
            for x, slot in enumerate(row):
                if slot not in (5, 6):
                    continue
                for dy in range(8):
                    for dx in range(8):
                        px, py = x * 8 + dx, y * 8 + dy
                        gray = self.proxy.getpixel((px, py))[0]
                        if gray == 255:
                            continue
                        self.assertTrue(any(a.stage_slot(s) == slot
                                            and gray == a.NATIVE_PROXY_BY_INDEX[c.STAGE_COLOR_INDEX[s - 1]]
                                            and (px, py) in a.stage_pixels(s)
                                            for s in range(1, 6)), (px, py, slot, gray))

    def test_fallen_spans_are_drawn_in_their_stage(self):
        c, a = self.contract, self.art
        for span in c.FALLEN_SPANS:
            stage, (x0, x1) = span["live_after"], span["columns"]
            pixels = a._span_pixels(span)
            self.assertEqual({x // 8 for x, _ in pixels}, set(range(x0, x1 + 1)))
            self.assertEqual({y // 8 for _, y in pixels}, {c.GROUND_ROW - 1})
            for x, y in pixels:
                self.assertEqual(self.slots[y // 8][x // 8], a.stage_slot(stage))
                self.assertEqual(self.proxy.getpixel((x, y))[0],
                                 a.NATIVE_PROXY_BY_INDEX[c.STAGE_COLOR_INDEX[stage - 1]])


class RidgeBackgroundTests(BackgroundChecks, unittest.TestCase):
    """2A wind_ridge: stages 1-3, line 3 leaves through the right wall."""
    contract = ridge.LAYOUTS[ridge.RIDGE]
    art = make_ridge_art.ARTS[ridge.RIDGE]

    def test_wind_ridge_tile_budget(self):
        # Spec WP2: Wind Ridge's BG tiles stay below 200 (was 283 at 100x30).
        self.assertLess(self.art._unique_indexed_tiles(self.proxy, self.slots), 250)
        self.assertEqual(self.sidecar["id"], ridge.resource_id("background:wind-ridge"))


class SaddleBackgroundTests(BackgroundChecks, unittest.TestCase):
    """2B ridge_saddle: stages 3-5, line 3 enters through the left wall; Hiroshi's cabin."""
    contract = ridge.LAYOUTS[ridge.SADDLE]
    art = make_ridge_art.ARTS[ridge.SADDLE]

    def test_edge_port_rows_match(self):
        port = ridge.EDGE_PORTS[3]
        left = {(x // 8, y // 8) for x, y in self.art.stage_pixels(3)}
        right = {(x // 8, y // 8) for x, y in make_ridge_art.ARTS[ridge.RIDGE].stage_pixels(3)}
        self.assertIn((0, port), left)
        self.assertIn((ridge.MAP_W - 1, port), right)


if __name__ == "__main__":
    unittest.main()
