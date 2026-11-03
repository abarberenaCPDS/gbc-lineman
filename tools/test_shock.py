import json
import unittest
from pathlib import Path

import shock

ROOT = Path(__file__).resolve().parent.parent


class ShockTests(unittest.TestCase):
    def test_events_shape_and_return_to_default(self):
        events = shock.shock_events("t")
        self.assertEqual(events[0]["args"]["spriteStateId"], "Shock")
        self.assertEqual(events[-1]["args"]["spriteStateId"], "")
        self.assertTrue(all(e["args"].get("actorId", "player") == "player" for e in events))
        self.assertIn("EVENT_SOUND_PLAY_EFFECT", [e["command"] for e in events])
        ids = [e["id"] for e in events]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual((shock.SHAKE_FRAMES + shock.SHOCK_FRAMES) / 60, 0.5)

    def test_sound_exists(self):
        meta = json.loads((ROOT / "assets/sounds/shock.wav.gbsres").read_text())
        self.assertEqual(meta["id"], shock.sound_id())
        self.assertTrue((ROOT / "assets/sounds/shock.wav").exists())

    def test_hero_has_shock_state_with_three_frames(self):
        meta = json.loads((ROOT / "assets/sprites/opening_worker24.png.gbsres").read_text())
        state = next(s for s in meta["states"] if s["name"] == "Shock")
        self.assertEqual(len(state["animations"][0]["frames"]), 3)
        self.assertTrue(all(f["tiles"] for f in state["animations"][0]["frames"]))

    def test_every_hazard_scene_hit_script_shocks(self):
        # Generated output, not generator source: every job and lab scene's
        # contact hit plays the Shock state (service_opening has no hazards).
        import scenes
        for folder, entry in scenes.REGISTRY.items():
            path = ROOT / "project/scenes" / folder / "scene.gbsres"
            if entry["tag"] == "legacy" or not path.exists():
                continue
            scene = json.loads(path.read_text())
            if scene["type"] != "PLATFORM" or folder == "service_opening":
                continue
            with self.subTest(folder=folder):
                self.assertIn('"spriteStateId": "Shock"', json.dumps(scene["playerHit1Script"]))

if __name__ == "__main__":
    unittest.main()
