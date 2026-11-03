"""Priya's three backgrounds (signal_hill, signal_gully, signal_porch): contract and native proxy checks.

Run with the managed Python (Pillow): -m unittest discover -s tools -p test_rosa_background.py
"""
import json
import unittest

from PIL import Image

import climb
import make_rosa_art as art
import rosa
from test_opening import decode_rle


class RosaBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {}
        for folder in rosa.SCENE_ORDER:
            width, height = rosa.size(folder)
            sidecar = json.loads(art.SIDECARS[folder].read_text(encoding="utf-8"))
            flat = decode_rle(sidecar["tileColors"])
            with Image.open(art.OUTPUTS[folder]) as image:
                proxy = image.convert("RGB")
            cls.data[folder] = {
                "grid": rosa.collision_grid(folder), "sidecar": sidecar, "flat": flat, "proxy": proxy,
                "slots": [flat[y * width:(y + 1) * width] for y in range(height)],
            }

    def each(self):
        for folder in rosa.SCENE_ORDER:
            with self.subTest(folder=folder):
                yield folder, self.data[folder]

    def test_size_identity_and_proxy(self):
        for folder, d in self.each():
            width, height = rosa.size(folder)
            self.assertEqual(d["proxy"].size, (width * 8, height * 8))
            self.assertEqual((d["sidecar"]["width"], d["sidecar"]["height"]), (width, height))
            self.assertEqual(d["sidecar"]["id"], rosa.BACKGROUND_IDS[folder])
            self.assertEqual(d["sidecar"]["name"], folder)
            self.assertFalse(d["sidecar"]["autoColor"])
            self.assertEqual(len(d["flat"]), width * height)
            self.assertTrue(all(0 <= slot < 7 for slot in d["flat"]))
            self.assertTrue(set(d["proxy"].get_flattened_data()) <= {(v, v, v) for v in (0, 85, 170, 255)})
            self.assertLessEqual(art._unique_indexed_tiles(d["proxy"], d["slots"]), art.MAX_UNIQUE_TILES)

    def test_generated_image_and_palette_map_are_reproducible(self):
        for folder, d in self.each():
            image, slots = art.make_background(folder)
            self.assertEqual(slots, d["slots"])
            self.assertEqual(art.encode_native_background(image, slots, folder).tobytes(), d["proxy"].tobytes())

    def test_wire_slots_hold_only_their_stages(self):
        for folder, d in self.each():
            stages = art.stages(folder)
            owners = {s: art.stage_pixels(s, folder) for s in stages}
            for y, row in enumerate(d["slots"]):
                for x, slot in enumerate(row):
                    if slot not in (art.METAL, art.WIRE_2):
                        continue
                    self.assertEqual(d["grid"][y][x], climb.COL_EMPTY, (x, y))
                    for dy in range(8):
                        for dx in range(8):
                            px, py = x * 8 + dx, y * 8 + dy
                            gray = d["proxy"].getpixel((px, py))[0]
                            if gray == 255:
                                continue
                            self.assertTrue(any(art.stage_slot(s) == slot
                                                and gray == art.NATIVE_PROXY_BY_INDEX[rosa.STAGE_COLOR_INDEX[s - 1]]
                                                and (px, py) in owners[s] for s in stages), (px, py, slot, gray))
            for stage in stages:
                slot = art.stage_slot(stage)
                painted = [p for p in owners[stage] if p[0] < d["proxy"].width and p[1] < d["proxy"].height
                           and d["slots"][p[1] // 8][p[0] // 8] == slot]
                self.assertGreater(len(painted), 20, f"stage {stage} missing")

    def test_wires_reach_the_edge_on_their_ports(self):
        for stage, rows in rosa.EDGE_PORTS.items():
            for folder, row in rows.items():
                d = self.data[folder]
                width = rosa.size(folder)[0]
                with self.subTest(stage=stage, folder=folder):
                    # The last open tile before the edge wall on the port row carries the wire.
                    edge = 1 if (0, row) in {c for s, r in rosa.WIRE_ROUTES_BY_SCENE[folder] if s == stage for c in r} \
                        else width - 2
                    self.assertEqual(d["slots"][row][edge], art.stage_slot(stage))

    def test_terrain_hazards_windows_and_hud(self):
        for folder, d in self.each():
            for y, row in enumerate(d["grid"]):
                for x, cell in enumerate(row):
                    if cell == climb.COL_SOLID:
                        self.assertEqual(d["slots"][y][x], art.STONE, (x, y))
                    elif cell == climb.COL_TOP:
                        self.assertEqual(d["slots"][y][x], art.TIMBER, (x, y))
                        self.assertEqual(d["proxy"].getpixel((x * 8, y * 8))[0], 0, (x, y))
            for row, x in art.placard_cells(folder):
                self.assertEqual(d["slots"][row][x], art.STONE, (x, row))
            windows = {(x, y) for y, row in enumerate(d["slots"]) for x, slot in enumerate(row) if slot == art.WINDOW}
            self.assertEqual(windows, set(rosa.HOUSE_WINDOWS) if folder == rosa.PORCH else set())
            for line in rosa.box_lines(folder):
                top, body = rosa.transformer_tiles(line["box"])
                self.assertTrue(all(d["slots"][y][x] == art.stage_slot(line["number"]) for x, y in top))
                self.assertTrue(all(d["slots"][y][x] == art.STONE for x, y in body))
            for y in range(rosa.HUD_ROWS):
                self.assertTrue(all(d["grid"][y][x] != climb.COL_EMPTY or d["slots"][y][x] == art.SKY
                                    for x in range(rosa.size(folder)[0])))

    def test_boards_are_cracked_planks_and_spans_lie_in_their_stage(self):
        for folder, d in self.each():
            for row, x0, x1 in rosa.LAYOUTS[folder]["boards"]:
                self.assertTrue(all(d["slots"][row][x] == art.TIMBER for x in range(x0, x1 + 1)))
            for span in rosa.LAYOUTS[folder]["spans"]:
                pixels = art._span_pixels(span, folder)
                x0, x1 = span["columns"]
                self.assertEqual({x // 8 for x, _ in pixels}, set(range(x0, x1 + 1)))
                self.assertEqual({y // 8 for _, y in pixels}, {span["arcs"][0][0] + 1})
                for x, y in pixels:
                    self.assertEqual(d["slots"][y // 8][x // 8], art.stage_slot(span["live_after"]))


if __name__ == "__main__":
    unittest.main()
