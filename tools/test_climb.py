"""Focused generator checks: python3 -m unittest discover -s tools -p test_climb.py."""
import unittest

import climb
import level
import make_climb_scene as scene


class ClimbTests(unittest.TestCase):
    def test_geometry_invariants(self):
        climb._self_check()

    def test_collision_encoding_matches_existing_encoder(self):
        grid = climb.collision_grid()
        self.assertEqual(
            scene.collision_rle(grid, climb.MAP_W, climb.MAP_H),
            level.rle([cell for row in grid for cell in row]),
        )

    def test_ids_repeat_and_do_not_overlap(self):
        self.assertEqual(scene.resource_id("scene"), scene.resource_id("scene"))
        self.assertNotEqual(scene.resource_id("scene"), scene.resource_id("actor"))

    def test_new_scene_uses_matching_background(self):
        resource = scene.build_scene("test-music")
        self.assertEqual(resource["backgroundId"], scene.resource_id("background:storm-climb"))
        self.assertEqual((resource["width"], resource["height"]), (20, 36))


if __name__ == "__main__":
    unittest.main()
