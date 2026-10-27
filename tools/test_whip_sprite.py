"""Whip-wire sprite checks; run with managed Python (Pillow)."""
import json
import unittest
from pathlib import Path

from PIL import Image

import make_whip_sprite as mw
import ridge

ROOT = Path(__file__).resolve().parent.parent
PNG = ROOT / "assets" / "sprites" / "whip_wire.png"
W, H = ridge.WHIP_CANVAS
SPARK = mw.PROXY[1]


def _load():
    return (Image.open(PNG).convert("RGBA"),
            json.loads(Path(str(PNG) + ".gbsres").read_text(encoding="utf-8")))


def _frame(img, i):
    return img.crop((i * W, 0, (i + 1) * W, H))


def _spark_xs(frame, rows):
    return sorted({x for y in rows for x in range(W) if frame.getpixel((x, y)) == SPARK})


def _spark_count(img, frames):
    return sum(1 for i in frames for y in range(H) for x in range(W)
               if _frame(img, i).getpixel((x, y)) == SPARK)


class WhipSpriteTests(unittest.TestCase):
    def test_canvas_states_frames(self):
        img, meta = _load()
        self.assertEqual(img.size, (W * 6, H))
        self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (16, 32))
        self.assertEqual(meta["spriteMode"], "8x16")
        self.assertEqual(meta["id"], ridge.WHIP_SPRITE_ID)
        self.assertEqual([s["name"] for s in meta["states"]], ["Hang", "Sway", "Swing"])
        self.assertEqual([len(s["animations"][0]["frames"]) for s in meta["states"]], [2, 2, 2])
        for s in meta["states"]:
            self.assertEqual(len(s["animations"]), 8)

    def test_slot_baked_and_tile_y_counts_up(self):
        _, meta = _load()
        ids = set()
        for s in meta["states"]:
            for a in s["animations"]:
                for f in a["frames"]:
                    for t in f["tiles"]:
                        self.assertEqual(t["paletteIndex"], 6)
                        self.assertEqual(t["y"], H - 16 - t["sliceY"])
                        self.assertNotIn(t["id"], ids)
                        ids.add(t["id"])
        top = [t for t in meta["states"][0]["animations"][0]["frames"][0]["tiles"]
               if t["sliceY"] == 0]
        self.assertTrue(top and all(t["y"] == 16 for t in top))  # upper slice sits 16 px up

    def test_bounds_cover_chest_row_full_width(self):
        _, meta = _load()
        # chest row 13 = canvas rows 16..23; origin is canvas bottom - 8 (rosa convention)
        self.assertEqual((meta["boundsX"], meta["boundsWidth"]), (0, 16))
        self.assertEqual(meta["boundsHeight"], 8)
        self.assertEqual(meta["boundsY"] + (H - 8), 16)

    def test_swing_spark_spans_chest_height(self):
        img, _ = _load()
        for i in (4, 5):
            xs = _spark_xs(_frame(img, i), range(16, 24))
            self.assertGreaterEqual(xs[-1] - xs[0] + 1, 9, f"frame {i} spark span {xs}")
        both = _spark_xs(_frame(img, 4), range(16, 24)) + _spark_xs(_frame(img, 5), range(16, 24))
        self.assertGreaterEqual(max(both) - min(both) + 1, 12)
        self.assertGreater(_spark_count(img, (4, 5)), _spark_count(img, (0, 1)))

    def test_wire_hangs_from_top_and_hang_tip_at_chest(self):
        img, _ = _load()
        for i in range(6):
            f = _frame(img, i)
            self.assertTrue(any(f.getpixel((x, 0))[3] for x in range(W)), f"frame {i} anchor")
        f = _frame(img, 0)
        self.assertTrue(any(f.getpixel((x, y))[3] for x in range(W) for y in range(18, 25)))

    def test_regeneration_matches_committed(self):
        img, meta = _load()
        new_img, new_meta = mw.make_asset()
        self.assertEqual(new_img.tobytes(), img.tobytes())
        new_meta["checksum"] = meta["checksum"]
        self.assertEqual(new_meta, meta)


if __name__ == "__main__":
    unittest.main()
