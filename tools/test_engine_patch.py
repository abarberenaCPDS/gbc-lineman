"""Local engine overlay for B-07 (stdlib only)."""

from __future__ import annotations

import unittest

import climb
import make_engine_patch as patch
import opening


def min_shelf_gap_rows(grid: list[list[int]], top: int) -> int:
    gaps = []
    for x in range(len(grid[0])):
        rows = [y for y in range(len(grid)) if grid[y][x] == top]
        gaps += [b - a for a, b in zip(rows, rows[1:])]
    return min(gaps)


class EnginePatchTests(unittest.TestCase):
    def test_overlay_is_the_vendor_file_with_one_line_changed(self):
        if not patch.VENDOR_PLATFORM.exists():
            self.skipTest("managed GB Studio engine not installed")
        vendor = patch.VENDOR_PLATFORM.read_text(encoding="utf-8")
        overlay = patch.OVERLAY_PLATFORM.read_text(encoding="utf-8")
        self.assertEqual(overlay, patch.patched_source(vendor),
                         "overlay drifted from the vendor engine: rerun tools/make_engine_patch.py")

    def test_overlay_is_the_only_engine_file(self):
        files = [p for p in patch.OVERLAY_PLATFORM.parents[2].rglob("*") if p.is_file()]
        self.assertEqual(files, [patch.OVERLAY_PLATFORM])

    def test_one_tap_drops_exactly_one_shelf(self):
        if not patch.VENDOR_PLATFORM.exists():
            self.skipTest("managed GB Studio engine not installed")
        fallen = patch.drop_distance_px(patch.DROP_FRAMES, patch.default_gravity())
        self.assertGreater(fallen, 8, "must clear the shelf the hero stands on")
        for grid in (climb.collision_grid(), opening.collision_grid()):
            gap_px = 8 * min_shelf_gap_rows(grid, climb.COL_TOP)
            self.assertLess(fallen, gap_px - 8, "must stop above the next shelf down")


if __name__ == "__main__":
    unittest.main()
