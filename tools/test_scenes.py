"""Scene registry contract (tools/scenes.py) against project/scenes/ and the start scene.

Run with the managed Python: `python -m unittest discover -s tools -p test_scenes.py`.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import scenes

ROOT = scenes.ROOT
SCENES_DIR = scenes.SCENES_DIR
SETTINGS = ROOT / "project" / "settings.gbsres"
TOOLS_DIR = ROOT / "tools"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def folders_on_disk() -> list[str]:
    return sorted(p.name for p in SCENES_DIR.iterdir() if p.is_dir())


def walk(events):
    """Every event, depth first, including each ``children`` branch."""
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def script_lists(folder: str):
    """Every event list in a scene: its own script, and every actor/trigger *Script field."""
    scene_dir = SCENES_DIR / folder
    scene = load(scene_dir / "scene.gbsres")
    for key, value in scene.items():
        if (key == "script" or key.endswith("Script")) and isinstance(value, list):
            yield f"scene.{key}", value
    for sub in ("actors", "triggers"):
        for path in sorted((scene_dir / sub).glob("*.gbsres")):
            resource = load(path)
            for key, value in resource.items():
                if (key == "script" or key.endswith("Script")) and isinstance(value, list):
                    yield f"{sub}/{path.name}.{key}", value


def switch_targets(events):
    for entry in walk(events):
        if entry.get("command") == "EVENT_SWITCH_SCENE":
            target = entry.get("args", {}).get("sceneId")
            if isinstance(target, dict):
                target = target.get("value")
            yield target


class RegistryTests(unittest.TestCase):
    def test_every_folder_is_registered(self):
        for folder in folders_on_disk():
            self.assertIn(folder, scenes.REGISTRY, f"project/scenes/{folder} is not in tools/scenes.py")

    def test_entries_are_well_formed(self):
        for folder, entry in scenes.REGISTRY.items():
            with self.subTest(folder=folder):
                self.assertIn(entry["tag"], scenes.TAGS)
                self.assertTrue(entry["id"])
                self.assertTrue(entry["name"])
                self.assertEqual(len(entry["editor"]), 2)

    def test_ids_are_unique(self):
        ids = [entry["id"] for entry in scenes.REGISTRY.values()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_game_generators_exist(self):
        for folder, entry in scenes.by_tag(scenes.GAME).items():
            with self.subTest(folder=folder):
                self.assertTrue((TOOLS_DIR / entry["generator"]).is_file())

    def test_registered_non_lab_scenes_exist(self):
        for folder, entry in scenes.REGISTRY.items():
            if entry["tag"] != scenes.LAB:
                with self.subTest(folder=folder):
                    self.assertTrue(scenes.present(folder), f"{folder} is registered but missing")

    def test_lab_names_start_with_lab_prefix(self):
        labs = scenes.by_tag(scenes.LAB)
        self.assertTrue(labs)
        for folder, entry in labs.items():
            with self.subTest(folder=folder):
                self.assertTrue(entry["name"].startswith("LAB_"), entry["name"])
                if scenes.present(folder):
                    self.assertTrue(load(SCENES_DIR / folder / "scene.gbsres")["name"].startswith("LAB_"))

    def test_helpers(self):
        self.assertEqual(scenes.editor_position("service_opening"), (0, 360))
        self.assertEqual(sorted(scenes.by_tag(scenes.LAB)), ["lab_hazard_gallery", "lab_movement_room"])
        self.assertEqual(scenes.ids(scenes.LAB), [scenes.REGISTRY[f]["id"] for f in scenes.by_tag(scenes.LAB)])
        self.assertIn(scenes.REGISTRY["storm_night"]["id"], scenes.ids(scenes.LEGACY))
        with self.assertRaises(ValueError):
            scenes.by_tag("nope")


class SceneFileTests(unittest.TestCase):
    def test_scene_ids_and_names_match_registry(self):
        for folder in folders_on_disk():
            if folder not in scenes.REGISTRY:
                continue
            entry = scenes.REGISTRY[folder]
            scene = load(SCENES_DIR / folder / "scene.gbsres")
            with self.subTest(folder=folder):
                self.assertEqual(scene["id"], entry["id"])
                self.assertEqual(scene["name"], entry["name"])

    def test_editor_positions_match_registry(self):
        for folder in folders_on_disk():
            if folder not in scenes.REGISTRY:
                continue
            scene = load(SCENES_DIR / folder / "scene.gbsres")
            with self.subTest(folder=folder):
                self.assertEqual((scene["x"], scene["y"]), tuple(scenes.editor_position(folder)))


class ReachabilityTests(unittest.TestCase):
    def test_game_scenes_never_switch_to_lab_or_legacy(self):
        forbidden = set(scenes.ids(scenes.LAB)) | set(scenes.ids(scenes.LEGACY))
        for folder in scenes.by_tag(scenes.GAME):
            if not scenes.present(folder):
                continue
            for label, events in script_lists(folder):
                for target in switch_targets(events):
                    with self.subTest(folder=folder, where=label):
                        self.assertNotIn(target, forbidden)

    def test_start_scene_is_a_game_scene(self):
        start = load(SETTINGS)["startSceneId"]
        self.assertIn(start, scenes.ids(scenes.GAME))


if __name__ == "__main__":
    unittest.main()
