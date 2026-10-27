"""LAB scenes (tools/make_lab_scene.py): registry agreement, layout, hazards, budgets.

Run with the managed Python: `python -m unittest discover -s tools -p test_lab.py`.
The scene files are read back from project/scenes/, so regenerate first.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import climb
import hazards
import make_lab_scene as lab
import make_project
import scenes

SCENES_DIR = scenes.SCENES_DIR
MAX_ACTORS = 20                 # GB Studio's active actor budget, excluding the player
MAX_SPRITES_PER_SCANLINE = 10   # the hardware OBJ limit per scanline
HERO_OBJS = 3                   # a 24px hero is three 8px OBJs wide
CAMERA_TILES = 20               # the visible width in tiles
MAX_DIALOGUE_CHARS = 17         # make_climb_scene.MAX_DIALOGUE_CHARS


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def scene_resources(folder: str):
    """(label, resource) for the scene, every actor and every trigger."""
    scene_dir = SCENES_DIR / folder
    yield "scene", load(scene_dir / "scene.gbsres")
    for sub in ("actors", "triggers"):
        for path in sorted((scene_dir / sub).glob("*.gbsres")):
            yield f"{sub}/{path.name}", load(path)


def event_lists(resource: dict):
    for key, value in resource.items():
        if (key == "script" or key.endswith("Script")) and isinstance(value, list):
            yield key, value


def decode_collisions(text: str, width: int, height: int) -> list[list[int]]:
    """Inverse of make_climb_scene.collision_rle: each run is a value, then "!" or "<hex count>+"."""
    values: list[int] = []
    i = 0
    while i < len(text):
        value = int(text[i:i + 2], 16)
        i += 2
        if text[i] == "!":
            count = 1
            i += 1
        else:
            end = text.index("+", i)
            count = int(text[i:end], 16)
            i = end + 1
        values.extend([value] * count)
    assert len(values) == width * height, "collision RLE does not cover the scene"
    return [values[row * width:(row + 1) * width] for row in range(height)]


def hazard_actors(folder: str) -> list[dict]:
    actors = []
    for _, resource in scene_resources(folder):
        if resource["_resourceType"] == "actor" and resource["symbol"].startswith(folder + "_"):
            actors.append(resource)
    return sorted(actors, key=lambda a: a["_index"])


def hazard_kind(actor: dict) -> str:
    symbol = actor["symbol"]
    for kind in ("board", "hidden_cable", "live_arc", "gust", "whip"):
        if f"_{kind}_" in symbol:
            return kind
    return "other"


def sprite_tiles(actor: dict) -> tuple[int, int]:
    """(width, height) in tiles: 24x16 boards and gusts, 16x32 whips, 16x16 cables and arcs."""
    kind = hazard_kind(actor)
    if kind in {"board", "gust"}:
        return 3, 2
    if kind == "whip":
        return lab.WHIP_CANVAS_TILES
    return 2, 2


class RegistryTests(unittest.TestCase):
    def test_lab_scenes_exist_with_registry_id_name_and_position(self):
        for folder, entry in scenes.by_tag(scenes.LAB).items():
            with self.subTest(folder=folder):
                scene = load(SCENES_DIR / folder / "scene.gbsres")
                self.assertEqual(scene["id"], entry["id"])
                self.assertEqual(scene["name"], entry["name"])
                self.assertTrue(scene["name"].startswith("LAB_"))
                self.assertEqual((scene["x"], scene["y"]), tuple(entry["editor"]))

    def test_rooms_are_the_registered_lab_scenes(self):
        self.assertEqual(sorted(lab.ROOMS), sorted(scenes.by_tag(scenes.LAB)))

    def test_rooms_are_40_by_18_platform(self):
        for folder in lab.ROOMS:
            with self.subTest(folder=folder):
                scene = load(SCENES_DIR / folder / "scene.gbsres")
                self.assertEqual((scene["width"], scene["height"], scene["type"]), (40, 18, "PLATFORM"))

    def test_profile_builds_the_lab_generator(self):
        self.assertEqual(make_project.PROFILES["lab"], ("make_lab_scene.py",))

    def test_resource_ids_are_unique_across_the_project(self):
        lab_ids: list[str] = []
        for folder in lab.ROOMS:
            for _, resource in scene_resources(folder):
                lab_ids.append(resource["id"])
                for key, events in event_lists(resource):
                    lab_ids.extend(entry["id"] for entry in walk(events))
        self.assertEqual(len(lab_ids), len(set(lab_ids)), "duplicate id inside the lab scenes")
        other_ids: set[str] = set()
        for folder in SCENES_DIR.iterdir():
            if not folder.is_dir() or folder.name in lab.ROOMS:
                continue
            for path in folder.rglob("*.gbsres"):
                data = load(path)
                if "id" in data:
                    other_ids.add(data["id"])
                for _, events in event_lists(data):
                    other_ids.update(entry["id"] for entry in walk(events))
        self.assertFalse(set(lab_ids) & other_ids, "lab ids collide with another scene's ids")


class ContentTests(unittest.TestCase):
    def test_actor_count_is_within_the_limit(self):
        for folder in lab.ROOMS:
            with self.subTest(folder=folder):
                self.assertLessEqual(len(hazard_actors(folder)), MAX_ACTORS)

    def test_gallery_has_every_hazard_kind(self):
        kinds = {hazard_kind(actor) for actor in hazard_actors(lab.GALLERY)}
        self.assertEqual(kinds, {"board", "hidden_cable", "live_arc", "gust", "whip"})

    def test_gallery_hazards_are_at_least_six_tiles_apart(self):
        xs = sorted(actor["x"] for actor in hazard_actors(lab.GALLERY))
        self.assertGreaterEqual(len(xs), 4)
        for left, right in zip(xs, xs[1:]):
            self.assertGreaterEqual(right - left, 6, (left, right))

    def test_gallery_hazards_match_the_hazard_tables(self):
        actors = hazard_actors(lab.GALLERY)
        boards = [a for a in actors if hazard_kind(a) == "board"]
        cables = [a for a in actors if hazard_kind(a) == "hidden_cable"]
        self.assertEqual(len(boards), len(hazards.BOARDS[lab.GALLERY]))
        self.assertEqual(len(cables), len(hazards.HIDDEN_CABLES[lab.GALLERY]))
        for actor, (row, x0, _) in zip(boards, hazards.BOARDS[lab.GALLERY]):
            self.assertEqual((actor["x"], actor["y"]), (x0, row))
        triggers = [r for label, r in scene_resources(lab.GALLERY)
                    if r["_resourceType"] == "trigger"]
        self.assertEqual(len(triggers), len(hazards.BOARDS[lab.GALLERY]))

    def test_movement_room_has_no_hazards(self):
        self.assertEqual(hazard_actors(lab.ROOM), [])
        self.assertEqual(hazards.BOARDS[lab.ROOM], [])
        self.assertEqual(hazards.HIDDEN_CABLES[lab.ROOM], [])

    def test_no_scene_switches_anywhere_in_the_lab(self):
        for folder in lab.ROOMS:
            for label, resource in scene_resources(folder):
                for key, events in event_lists(resource):
                    for entry in walk(events):
                        with self.subTest(folder=folder, where=f"{label}.{key}"):
                            self.assertNotEqual(entry["command"], "EVENT_SWITCH_SCENE")

    def test_dialogue_lines_fit_the_box(self):
        for folder in lab.ROOMS:
            for label, resource in scene_resources(folder):
                for key, events in event_lists(resource):
                    for entry in walk(events):
                        if entry["command"] != "EVENT_TEXT":
                            continue
                        for line in entry["args"]["text"]:
                            for part in line.split("\n"):
                                with self.subTest(folder=folder, where=label):
                                    self.assertLessEqual(len(part), MAX_DIALOGUE_CHARS, part)

    def test_entry_signs_name_their_room(self):
        self.assertEqual(lab.ROOMS[lab.GALLERY]["entry"], "LAB: hazards")
        self.assertEqual(lab.ROOMS[lab.ROOM]["entry"], "LAB: movement")


class LayoutTests(unittest.TestCase):
    def test_scene_collisions_match_the_generator_layout(self):
        for folder in lab.ROOMS:
            with self.subTest(folder=folder):
                scene = load(SCENES_DIR / folder / "scene.gbsres")
                decoded = decode_collisions(scene["collisions"], 40, 18)
                self.assertEqual(decoded, lab.collision_grid(folder))

    def test_hero_stands_on_the_start_tile(self):
        x, y = lab.START
        for folder in lab.ROOMS:
            grid = lab.collision_grid(folder)
            with self.subTest(folder=folder):
                self.assertEqual(grid[y][x], climb.COL_EMPTY)
                self.assertEqual(grid[y + 1][x], climb.COL_SOLID)

    def test_gap_ladder_widths_are_one_to_four(self):
        grid = lab.collision_grid(lab.ROOM)
        floor = grid[lab.GROUND_ROW]
        widths, run = [], 0
        for cell in floor[1:-1]:
            if cell == climb.COL_EMPTY:
                run += 1
            elif run:
                widths.append(run)
                run = 0
        self.assertEqual(widths, [1, 2, 3, 4])

    def test_drop_through_shelf_is_one_way(self):
        grid = lab.collision_grid(lab.ROOM)
        self.assertTrue(all(grid[12][x] == climb.COL_TOP for x in range(18, 21)))
        self.assertTrue(all(grid[row][x] == climb.COL_EMPTY for row in (11, 10) for x in range(18, 21)))

    def test_shelves_are_one_tile_thick_and_rise_three(self):
        grid = lab.collision_grid(lab.ROOM)
        shelves = lab.ROOMS[lab.ROOM]["shelves"]
        for x0, x1, row0, row1, value in shelves:
            with self.subTest(shelf=(x0, x1, row0)):
                self.assertEqual(row0, row1)
                self.assertTrue(all(grid[row0][x] == value for x in range(x0, x1 + 1)))
        # Each rise is one A tap: three tiles up from the floor, then from the first shelf.
        self.assertEqual(lab.GROUND_ROW - shelves[0][2], 3)
        self.assertEqual(shelves[0][2] - shelves[1][2], 3)

    def test_hazard_lanes_are_clear_air_on_the_floor(self):
        grid = lab.collision_grid(lab.GALLERY)
        for row, x0, x1 in lab.hazard_lanes(lab.GALLERY):
            with self.subTest(lane=(row, x0, x1)):
                self.assertEqual(row, lab.GROUND_ROW - 2)
                self.assertTrue(all(grid[row][x] == climb.COL_EMPTY for x in range(x0, x1 + 1)))


class ScanlineTests(unittest.TestCase):
    def sprite_load(self, actors, left):
        """OBJs per row for the hazards visible in the camera window starting at ``left``."""
        load: dict[int, int] = {}
        for actor in actors:
            width, height = sprite_tiles(actor)
            x, y = actor["x"], actor["y"]
            if x + width <= left or x >= left + CAMERA_TILES:
                continue
            # Sprites hang up from the actor's row at the bottom: each 8x16 OBJ column
            # covers two tile rows, so a 32px whip adds its width on four rows.
            for row in range(y - height + 1, y + 1):
                load[row] = load.get(row, 0) + width
        return load

    def test_every_camera_window_stays_within_ten_sprites_per_scanline(self):
        for folder in lab.ROOMS:
            actors = hazard_actors(folder)
            width = 40
            for left in range(0, width - CAMERA_TILES + 1):
                with self.subTest(folder=folder, left=left):
                    load = self.sprite_load(actors, left)
                    # The hero may stand anywhere in the window: add its OBJs on every row.
                    worst = max(load.values(), default=0) + HERO_OBJS
                    self.assertLessEqual(worst, MAX_SPRITES_PER_SCANLINE, load)


if __name__ == "__main__":
    unittest.main()
