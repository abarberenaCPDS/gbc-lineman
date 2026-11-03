#!/usr/bin/env python3
"""The grid line's cable is part of its pole actor, which must not take B."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# scene folder: pole actor resource file
JOBS = {
    "storm_climb": "climb_storm_pole",
    "wind_ridge": "ridge_feeder_pole",
    "ridge_saddle": "ridge_storm_pole",
    "signal_gully": "rosa_storm_pole",
    "pine_hollow": "kiko_storm_pole",
}


def actor(scene: str, name: str) -> dict:
    return json.loads((ROOT / f"project/scenes/{scene}/actors/{name}.gbsres").read_text())


class PoleCableTests(unittest.TestCase):
    def test_pole_never_takes_the_b_press(self):
        for scene, pole_name in JOBS.items():
            pole = actor(scene, pole_name)
            self.assertEqual(pole["startScript"][0]["command"],
                             "EVENT_ACTOR_COLLISIONS_DISABLE", scene)
            self.assertEqual(pole["startScript"][0]["args"]["actorId"], "$self$", scene)
            self.assertEqual(pole["script"], [], scene)

    def test_scene_actor_rosters_have_no_separate_cable_end(self):
        for scene in JOBS:
            actor_dir = ROOT / f"project/scenes/{scene}/actors"
            cables = [path.name for path in actor_dir.glob("*.gbsres")
                      if "cable_end" in path.stem]
            self.assertEqual(cables, [], scene)


if __name__ == "__main__":
    unittest.main()
