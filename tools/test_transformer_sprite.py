import json
import unittest
from pathlib import Path

from PIL import Image

import make_transformer_sprite as gen
import ridge

SPR = Path(__file__).resolve().parent.parent / "assets" / "sprites"


class TransformerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.meta = json.loads((SPR / "transformer.png.gbsres").read_text())
        cls.img = Image.open(SPR / "transformer.png").convert("RGBA")

    def frame(self, i):
        return self.img.crop((i * 16, 0, i * 16 + 16, 32))

    def test_identity_canvas_states(self):
        m = self.meta
        self.assertEqual(m["id"], ridge.TRANSFORMER_SPRITE_ID)
        self.assertEqual((m["canvasWidth"], m["canvasHeight"]), ridge.TRANSFORMER_CANVAS)
        self.assertEqual(m["spriteMode"], "8x16")
        self.assertEqual([s["name"] for s in m["states"]], ridge.TRANSFORMER_STATES)
        self.assertEqual([len(s["animations"][0]["frames"]) for s in m["states"]], [1, 2])

    def test_slot_and_tile_y_up(self):
        count = 0
        for s in self.meta["states"]:
            for a in s["animations"]:
                for f in a["frames"]:
                    for t in f["tiles"]:
                        count += 1
                        self.assertEqual(t["paletteIndex"], ridge.GRID_SPRITE_PALETTE_SLOT)
                        self.assertEqual((t["y"], t["sliceY"]),
                                         (16, 0) if t["sliceY"] == 0 else (0, 16))
        self.assertGreater(count, 0)

    def test_bounds(self):
        m = self.meta
        self.assertEqual((m["boundsX"], m["boundsY"], m["boundsWidth"], m["boundsHeight"]),
                         (0, -8, 16, 16))

    def test_terminal_and_live(self):
        for i in range(3):
            top = self.frame(i).crop((0, 0, 16, 8))
            self.assertTrue(any(p[3] for p in top.get_flattened_data()))
        dead, a, b = (self.frame(i).tobytes() for i in range(3))
        self.assertEqual(len({dead, a, b}), 3)

        def acc(i):
            return sum(1 for p in self.frame(i).get_flattened_data() if p == (160, 160, 160, 255))
        self.assertEqual(acc(0), 0)
        self.assertTrue(0 < acc(2) < acc(1) <= 4)

    def test_generator_matches_disk(self):
        sheet, _ = gen.make_asset()
        self.assertEqual(sheet.tobytes(), self.img.tobytes())


if __name__ == "__main__":
    unittest.main()
