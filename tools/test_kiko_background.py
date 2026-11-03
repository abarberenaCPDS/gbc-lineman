"""Emil's three backgrounds (pine_hollow, pine_ladder, pine_rim): contract, palette map and native proxy."""
import json
import unittest

from PIL import Image

import climb
import kiko
import make_kiko_art as art


def decode_rle(text):
    values, i = [], 0
    while i < len(text):
        value = int(text[i:i + 2], 16)
        i += 2
        if text[i] == "!":
            count, i = 1, i + 1
        else:
            end = text.index("+", i)
            count, i = int(text[i:end], 16), end + 1
        values.extend([value] * count)
    return values


class KikoBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = {}
        for folder in kiko.SCENE_ORDER:
            contract = kiko.SCENES[folder]
            meta = json.loads(art.sidecar(folder).read_text(encoding="utf-8"))
            flat = decode_rle(meta["tileColors"])
            slots = [flat[y * contract.map_w:(y + 1) * contract.map_w] for y in range(contract.map_h)]
            with Image.open(art.output(folder)) as image:
                proxy = image.convert("RGB")
            cls.data[folder] = (contract, meta, slots, proxy, contract.collision_grid())

    def test_size_identity_and_proxy(self):
        for folder, (c, meta, slots, proxy, _) in self.data.items():
            with self.subTest(folder=folder):
                self.assertEqual(proxy.size, (c.map_w * 8, c.map_h * 8))
                self.assertEqual((meta["width"], meta["height"]), (c.map_w, c.map_h))
                self.assertEqual(meta["id"], kiko.BACKGROUND_IDS[folder])
                self.assertEqual((meta["name"], meta["filename"]), (folder, f"{folder}.png"))
                self.assertFalse(meta["autoColor"])
                self.assertTrue(all(0 <= slot < 7 for row in slots for slot in row))
                self.assertTrue(set(proxy.get_flattened_data()) <= {(v, v, v) for v in (0, 85, 170, 255)})
                self.assertLessEqual(art.unique_indexed_tiles(proxy, slots), art.MAX_UNIQUE_TILES)

    def test_generated_image_and_palette_map_are_reproducible(self):
        for folder, (_, _, slots, proxy, _) in self.data.items():
            image, built = art.make_background(folder)
            with self.subTest(folder=folder):
                self.assertEqual(built, slots)
                self.assertEqual(art.encode_native_background(image, built).tobytes(), proxy.tobytes())

    def test_wire_stages_use_the_jobs_chain_slots(self):
        self.assertEqual(kiko.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual([art.stage_slot(s) for s in range(1, 6)], [5, 5, 5, 6, 6])
        expected = {kiko.HOLLOW: [1, 2, 3], kiko.LADDER: [3, 4, 5], kiko.RIM: [4, 5]}
        for folder, (c, _, slots, proxy, grid) in self.data.items():
            scene_art = art.scene_art(folder)
            with self.subTest(folder=folder):
                self.assertEqual(scene_art.stages(), expected[folder])
                for stage in scene_art.stages():
                    slot, index = art.stage_slot(stage), kiko.STAGE_COLOR_INDEX[stage - 1]
                    painted = [(x, y) for x, y in scene_art.stage_pixels(stage) if slots[y // 8][x // 8] == slot]
                    self.assertGreater(len(painted), 20, f"stage {stage} missing")
                    lit = [p for p in painted if proxy.getpixel(p)[0] == art.NATIVE_PROXY_BY_INDEX[index]]
                    self.assertGreater(len(lit), len(painted) // 2, f"stage {stage} colour")
                # Wire slots only on open tiles that a stage owns.
                owners = {s: {(x // 8, y // 8) for x, y in scene_art.stage_pixels(s)} for s in scene_art.stages()}
                for y, row in enumerate(slots):
                    for x, slot in enumerate(row):
                        if slot in (5, 6):
                            self.assertEqual(grid[y][x], climb.COL_EMPTY, (x, y))
                            self.assertTrue(any((x, y) in owners[s] and art.stage_slot(s) == slot for s in owners))

    def test_terrain_hazards_windows_and_hud(self):
        for folder, (c, _, slots, proxy, grid) in self.data.items():
            with self.subTest(folder=folder):
                for y, row in enumerate(grid):
                    for x, cell in enumerate(row):
                        if cell == climb.COL_SOLID:
                            self.assertEqual(slots[y][x], art.STONE, (x, y))
                        elif cell == climb.COL_TOP:
                            self.assertEqual(slots[y][x], art.TIMBER, (x, y))
                for row, x0, x1 in c.hazard_lanes():
                    for x in range(x0, x1 + 1):
                        self.assertEqual(slots[row][x], art.STONE, (x, row))
                windows = {(x, y) for y, row in enumerate(slots) for x, slot in enumerate(row) if slot == art.WINDOW}
                self.assertEqual(windows, set(c.house["windows"]) if c.house else set())
                for line in c.box_lines():
                    top, body = kiko.transformer_tiles(line["box"])
                    self.assertTrue(all(slots[ty][tx] == art.stage_slot(line["number"]) for tx, ty in top))
                    self.assertTrue(all(slots[ty][tx] == kiko.TRANSFORMER_BODY_SLOT for tx, ty in body))
                if not c.shaft:
                    for y in range(kiko.HUD_ROWS):
                        self.assertEqual(set(slots[y]), {art.SKY})


if __name__ == "__main__":
    unittest.main()
