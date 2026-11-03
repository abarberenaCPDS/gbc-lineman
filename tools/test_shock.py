import json
import unittest
from pathlib import Path

import shock

ROOT = Path(__file__).resolve().parent.parent


def walk_events(value):
    """Yield every nested event in a generated script tree."""
    if isinstance(value, list):
        for child in value:
            yield from walk_events(child)
    elif isinstance(value, dict):
        if isinstance(value.get("command"), str):
            yield value
        for child in value.values():
            yield from walk_events(child)


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

    def test_every_hazard_hit_has_one_shock_cue_and_fixed_recovery_timing(self):
        import scenes
        expected = shock.shock_events("generated-check")
        expected_commands = [event["command"] for event in expected]
        for folder, entry in scenes.REGISTRY.items():
            path = ROOT / "project/scenes" / folder / "scene.gbsres"
            if entry["tag"] == "legacy" or not path.exists():
                continue
            scene = json.loads(path.read_text())
            if scene["type"] != "PLATFORM" or folder == "service_opening":
                continue
            hit = scene["playerHit1Script"]
            events = list(walk_events(hit))
            with self.subTest(folder=folder):
                effects = [event for event in events if event["command"] == "EVENT_SOUND_PLAY_EFFECT"]
                self.assertEqual(len(effects), 1)
                self.assertEqual(effects[0]["args"]["type"], shock.sound_id())
                self.assertFalse(any(event["command"] in {"EVENT_MUSIC_PLAY", "EVENT_MUSIC_STOP"}
                                     for event in events))
                self.assertEqual([event["command"] for event in hit[:len(expected)]], expected_commands)
                self.assertEqual(hit[0]["args"]["spriteStateId"], "Shock")
                self.assertEqual(hit[2]["args"]["frames"], shock.SHAKE_FRAMES)
                self.assertEqual(hit[3]["args"]["frames"]["value"], shock.SHOCK_FRAMES)
                self.assertEqual(hit[4]["args"]["spriteStateId"], "")

if __name__ == "__main__":
    unittest.main()
