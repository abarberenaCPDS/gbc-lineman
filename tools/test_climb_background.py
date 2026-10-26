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


if __name__ == "__main__":
    unittest.main()
