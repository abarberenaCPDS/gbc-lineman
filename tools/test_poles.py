#!/usr/bin/env python3
"""Cart bug B-13: the storm pole hid the cable end and stole its B press.

Actors draw in descending index order (higher index = lower OAM = on top), and
the B probe found the pole (no script) on the shared tile. Each job's cable end
must out-rank its pole, and the pole must start with collisions off.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# scene folder: (pole actor file, cable end actor file)
JOBS = {
    "storm_climb": ("climb_storm_pole", "grid_cable_end"),
    "wind_ridge": ("ridge_storm_pole", "ridge_cable_end"),
    "signal_hill": ("rosa_storm_pole", "signal_cable_end"),
    "pine_hollow": ("kiko_storm_pole", "pine_cable_end"),
}


def actor(scene: str, name: str) -> dict:
    return json.loads((ROOT / f"project/scenes/{scene}/actors/{name}.gbsres").read_text())


class PoleCableTests(unittest.TestCase):
    def test_cable_end_draws_above_the_pole(self):
        for scene, (pole_name, cable_name) in JOBS.items():
            pole, cable = actor(scene, pole_name), actor(scene, cable_name)
            self.assertEqual((pole["x"], pole["y"]), (cable["x"], cable["y"]), scene)
            self.assertGreater(cable["_index"], pole["_index"], scene)

    def test_pole_never_takes_the_b_press(self):
        for scene, (pole_name, _) in JOBS.items():
            pole = actor(scene, pole_name)
            self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE", scene)
            self.assertEqual(pole["script"], [], scene)


if __name__ == "__main__":
    unittest.main()
