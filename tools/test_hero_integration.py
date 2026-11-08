"""Keep the Storm Worker wired into every active platform gameplay scene.

This checks generated scene resources, including planned scenes already present
in the worktree. Cinematic and ticket scenes own separate presentation sprites;
legacy scenes are retained references and are outside the active gameplay set.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import opening  # noqa: E402
import scenes  # noqa: E402

ROOT = TOOLS.parent
WORKER_ID = opening.resource_id("sprite:opening_worker24")


def walk_events(value):
    if isinstance(value, list):
        for item in value:
            yield from walk_events(item)
    elif isinstance(value, dict):
        if isinstance(value.get("command"), str):
            yield value
        for child in value.values():
            yield from walk_events(child)


class HeroIntegrationTests(unittest.TestCase):
    def test_every_active_platform_scene_sets_the_storm_worker(self):
        checked = []
        for folder, entry in scenes.REGISTRY.items():
            if entry["tag"] not in (scenes.GAME, scenes.LAB) or not scenes.present(folder):
                continue
            path = scenes.SCENES_DIR / folder / "scene.gbsres"
            scene = json.loads(path.read_text(encoding="utf-8"))
            if scene.get("type") != "PLATFORM":
                continue
            checked.append(folder)
            events = list(walk_events(scene.get("script", [])))
            sprites = [event.get("args", {}).get("spriteSheetId") for event in events
                       if event.get("command") == "EVENT_PLAYER_SET_SPRITE"]
            with self.subTest(scene=folder):
                self.assertTrue(sprites, "platform scene must initialize the player sprite")
                self.assertEqual(sprites[0], WORKER_ID)
        self.assertTrue(checked, "scene registry contains no active platform gameplay scenes")

    def test_worker_keeps_gameplay_states_and_24px_foot_bounds(self):
        path = ROOT / "assets/sprites/opening_worker24.png.gbsres"
        sprite = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(sprite["id"], WORKER_ID)
        self.assertEqual((sprite["boundsY"], sprite["boundsHeight"]), (-16, 24))
        self.assertEqual([state["name"] for state in sprite["states"]],
                         ["Default", "Repair", "Carry", "Shock"])
        for state in sprite["states"]:
            with self.subTest(state=state["name"]):
                self.assertEqual(len(state["animations"]), 8)
                self.assertTrue(all(animation["frames"] for animation in state["animations"]))


if __name__ == "__main__":
    unittest.main()
