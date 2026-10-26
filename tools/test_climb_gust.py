"""Focused deterministic contract tests for the generated climb gust sprite."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_climb_gust as gust  # noqa: E402


class ClimbGustTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.image = Image.open(gust.OUTPUT).convert("RGB")
        cls.png_bytes = gust.OUTPUT.read_bytes()
        cls.metadata = json.loads(gust.METADATA.read_text(encoding="utf-8"))

    def test_native_metadata_contract_and_checksum(self) -> None:
        data = self.metadata
        self.assertEqual(data["_resourceType"], "sprite")
        self.assertEqual(data["name"], "climb_gust")
        self.assertEqual((data["width"], data["height"]), (96, 16))
        self.assertEqual((data["canvasWidth"], data["canvasHeight"]), (24, 16))
        self.assertEqual((data["boundsX"], data["boundsY"], data["boundsWidth"],
                          data["boundsHeight"]), (0, 0, 24, 8))
        self.assertEqual(data["spriteMode"], "8x16")
        self.assertEqual(data["checksum"], hashlib.sha1(self.png_bytes).hexdigest())
        self.assertEqual(data["states"][0]["name"], "Warning")
        self.assertEqual(data["states"][1]["name"], "Burst")
        self.assertEqual([len(state["animations"]) for state in data["states"]], [8, 8])
        self.assertEqual([len(state["animations"][0]["frames"]) for state in data["states"]], [2, 2])
        self.assertGreater(data["numTiles"], 0)
        self.assertNotEqual(data["id"], "2be8c676-2f99-5e22-8928-b11e02e78046")
        self.assertTrue(all(tile["paletteIndex"] == 5
                            for state in data["states"]
                            for frame in state["animations"][0]["frames"]
                            for tile in frame["tiles"]))

    def test_proxy_colors_animation_areas_and_bounds(self) -> None:
        gust.validate(self.image, self.metadata)
        self.assertLessEqual(set(self.image.get_flattened_data()), gust.PROXY_COLORS)
        with Image.open(gust.OUTPUT) as native:
            self.assertEqual(native.mode, "RGBA")
            gust.validate(native, self.metadata)
        state_areas = []
        for state_index in range(2):
            rendered = []
            area = 0
            for phase in range(2):
                frame_index = state_index * 2 + phase
                frame = self.image.crop((frame_index * 24, 0, frame_index * 24 + 24, 16))
                rendered.append(frame.tobytes())
                area += sum(pixel != gust.TRANSPARENT for pixel in frame.get_flattened_data())
                self.assertTrue(all(frame.getpixel((x, y)) == gust.TRANSPARENT
                                    for x in range(24) for y in range(8)))
            self.assertNotEqual(rendered[0], rendered[1])
            state_areas.append(area)
        self.assertLess(state_areas[0], state_areas[1])

    def test_each_frame_is_capped_at_three_hardware_objects(self) -> None:
        for state in self.metadata["states"]:
            for slot, animation in enumerate(state["animations"]):
                for frame in animation["frames"]:
                    self.assertLessEqual(len(frame["tiles"]), 3)
                    if slot == 0:
                        self.assertEqual(len(frame["tiles"]), 3)


if __name__ == "__main__":
    unittest.main()
