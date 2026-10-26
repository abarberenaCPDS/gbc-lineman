"""Cracked-board sprite checks; run with managed Python (Pillow)."""
import json
import unittest
from pathlib import Path

from PIL import Image

import hazards
import make_hazard_sprites as mh

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "assets" / "sprites" / "cracked_board.png"
W, H = hazards.BOARD_CANVAS


def _load():
    return (Image.open(PNG).convert("RGBA"),
            json.loads(Path(str(PNG) + ".gbsres").read_text(encoding="utf-8")))


def _frame(img, i):
    return img.crop((i * W, 0, (i + 1) * W, H))


class BoardSpriteTests(unittest.TestCase):
    def test_canvas_states_frames(self):
        img, meta = _load()
        self.assertEqual(img.size, (W * 5, H))
        self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (W, H))
        self.assertEqual(meta["spriteMode"], "8x16")
        self.assertEqual(meta["id"], hazards.BOARD_SPRITE_ID)
        self.assertEqual([s["name"] for s in meta["states"]], hazards.BOARD_STATES)
        counts = [len(s["animations"][0]["frames"]) for s in meta["states"]]
        self.assertEqual(counts, [1, 2, 2])
        for s in meta["states"]:
            self.assertEqual(len(s["animations"]), 8)
            self.assertEqual(s["animationType"], "fixed")

    def test_bounds_and_palette(self):
        _, meta = _load()
        self.assertEqual((meta["boundsX"], meta["boundsY"], meta["boundsWidth"],
                          meta["boundsHeight"]), hazards.BOARD_BOUNDS)
        ids = set()
        for s in meta["states"]:
            for a in s["animations"]:
                for f in a["frames"]:
                    for t in f["tiles"]:
                        self.assertEqual(t["paletteIndex"], hazards.BOARD_SPRITE_PALETTE_SLOT)
                        self.assertEqual(t["y"], 0)
                        self.assertNotIn(t["id"], ids)
                        ids.add(t["id"])

    def test_regeneration_matches_committed(self):
        img, meta = _load()
        new_img, new_meta = mh.make_asset()
        self.assertEqual(new_img.tobytes(), img.tobytes())
        new_meta["checksum"] = meta["checksum"]
        self.assertEqual(new_meta, meta)

    def test_idle_crack_present(self):
        img, _ = _load()
        idle = _frame(img, 0)
        dark = [(x, y) for y in range(8, 16) for x in range(10, 14)
                if idle.getpixel((x, y)) == mh.PROXY[3]]
        self.assertGreaterEqual(len(dark), 8)
        self.assertTrue(all(idle.getpixel((x, y))[3] == 0 for y in range(8) for x in range(W)))

    def test_creak_frames_differ_and_have_ticks(self):
        img, _ = _load()
        a, b = _frame(img, 1), _frame(img, 2)
        self.assertNotEqual(a.tobytes(), b.tobytes())
        for f in (a, b):
            above = sum(1 for y in range(8) for x in range(W) if f.getpixel((x, y))[3])
            self.assertGreaterEqual(above, 6)
        self.assertNotEqual(_frame(img, 3).tobytes(), _frame(img, 4).tobytes())


if __name__ == "__main__":
    unittest.main()
