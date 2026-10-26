"""M-V1 checks; run with managed Python (Pillow) after opening generators."""
import json
from pathlib import Path
import unittest

from PIL import Image

import opening

ROOT = Path(__file__).resolve().parent.parent


def decode_rle(value):
    cells = []
    index = 0
    while index < len(value):
        cell = int(value[index:index + 2], 16)
        index += 2
        start = index
        while value[index] not in "!+":
            index += 1
        count = 1 if value[index] == "!" else int(value[start:index], 16)
        cells.extend([cell] * count)
        index += 1
    return cells


class OpeningTests(unittest.TestCase):
    def test_editor_sprite_palette_expands_to_intended_opaque_colors(self):
        import make_opening_scene as scene
        for name, ramp in opening.SPRITE_PALETTES:
            stored = scene.palette("sprite", name, ramp)["colors"]
            compiled = [stored[0], stored[0], stored[1], stored[3]]
            self.assertEqual(compiled[1:], ramp[1:])

    def test_repair_palette_changes_only_window_slot(self):
        import make_opening_scene as scene
        for powered in (False, True):
            args = scene.palette_state(powered, "test")["args"]
            self.assertEqual(len(args), 8)
            self.assertTrue(all(args[f"palette{slot}"] == "keep" for slot in (0, 1, 2, 4, 5, 6, 7)))
            expected = "powered_window" if powered else "window"
            self.assertEqual(args["palette3"], opening.resource_id("palette:bg:" + expected))

    def test_repair_is_idempotent_and_persists_in_scene_entry(self):
        import make_opening_scene as scene
        script = scene.repair_script()
        self.assertEqual(script[0]["args"]["condition"]["valueA"]["value"], scene.RESTORED)
        self.assertEqual(script[0]["children"]["false"], [])
        writes = [e for e in script[0]["children"]["true"] if e["command"] == "EVENT_SET_VALUE"]
        self.assertEqual([(e["args"]["variable"], e["args"]["value"]["value"]) for e in writes], [(scene.RESTORED, 1)])
        entry = scene.build_scene([], [])["script"]
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" for e in entry))

    def test_size_comparison_returns_to_clear_ground_first(self):
        import make_opening_scene as scene
        script = scene.size_comparison_script()
        self.assertEqual(script[0]["command"], "EVENT_SCRIPT_LOCK")
        self.assertEqual(script[1]["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((script[1]["args"]["x"]["value"], script[1]["args"]["y"]["value"]), opening.START)
        self.assertEqual(script[-1]["command"], "EVENT_SCRIPT_UNLOCK")
        for branch in ("true", "false"):
            self.assertIn("EVENT_PLAYER_SET_SPRITE", [e["command"] for e in script[2]["children"][branch]])

    def test_geometry(self):
        opening._self_check()
        grid = opening.collision_grid()
        self.assertTrue(all(cell == 15 for cell in grid[16]))
        self.assertEqual(grid[13][13:17], [1] * 4)
        self.assertEqual(grid[10][11:19], [1] * 8)

    def test_opening_ids_do_not_overlap_climb(self):
        from make_climb_scene import resource_id
        self.assertNotEqual(opening.resource_id("scene:service-opening"), resource_id("scene:storm-climb"))

    def test_background_obeys_each_tile_palette(self):
        from make_opening_art import make_background, encode_native_background
        path = ROOT / "assets/backgrounds/service_opening.png"
        metadata = json.loads(Path(str(path) + ".gbsres").read_text())
        slots = decode_rle(metadata["tileColors"])
        self.assertEqual(len(slots), 360)
        self.assertTrue(all(0 <= value < 7 for value in slots))
        self.assertGreater(slots.count(3), 0)
        self.assertLess(slots.count(3), 90, "power transformation must remain local")
        with Image.open(path) as image:
            self.assertEqual(image.size, (160, 144))
            authored, expected_slots = make_background()
            self.assertEqual(slots, [slot for row in expected_slots for slot in row])
            self.assertEqual(image.convert("RGB").tobytes(), encode_native_background(authored, expected_slots).tobytes())
            self.assertTrue(set(image.convert("RGB").get_flattened_data()) <= {
                (255, 255, 255), (170, 170, 170), (85, 85, 85), (0, 0, 0),
            })
            for ty in range(18):
                for tx in range(20):
                    palette = opening.BG_PALETTES[slots[ty * 20 + tx]][1]
                    allowed = {tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) for color in palette}
                    tile = authored.convert("RGB").crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8))
                    self.assertTrue(set(tile.get_flattened_data()) <= allowed, f"palette spill at {tx},{ty}")

    def test_character_states_and_proxy_colors(self):
        for name, states in (("opening_worker16", {"Default", "Repair"}),
                              ("opening_worker24", {"Default", "Repair"}),
                              ("opening_marta", {"Waiting", "Powered"}),
                              ("opening_terminal", {"Off", "On"})):
            with self.subTest(asset=name):
                path = ROOT / f"assets/sprites/{name}.png"
                metadata = json.loads(Path(str(path) + ".gbsres").read_text())
                self.assertTrue(states <= {state["name"] for state in metadata["states"]})
                self.assertTrue(all(len(state["animations"]) == 8 for state in metadata["states"]))
                with Image.open(path) as image:
                    self.assertEqual(image.size, (metadata["width"], metadata["height"]))
                    for r, g, b, a in image.convert("RGBA").get_flattened_data():
                        if a and (r, g, b) != (0, 255, 0):
                            self.assertIn((r, g, b), {(255, 255, 255), (160, 160, 160), (0, 0, 0)})

    def test_candidate_feet_and_art_heights(self):
        for size, min_y in ((16, -8), (24, -16)):
            name = f"opening_worker{size}"
            path = ROOT / f"assets/sprites/{name}.png"
            metadata = json.loads(Path(str(path) + ".gbsres").read_text())
            self.assertEqual(metadata["boundsY"], min_y)
            self.assertEqual(metadata["boundsHeight"], size)
            with Image.open(path) as sheet:
                sheet = sheet.convert("RGBA")
                for state in metadata["states"]:
                    for animation in state["animations"]:
                        for frame in animation["frames"]:
                            self.assertLessEqual(len(frame["tiles"]), 2 if size == 16 else 4)
                            for tile in frame["tiles"]:
                                for py in range(16):
                                    for px in range(8):
                                        r, g, b, a = sheet.getpixel((tile["sliceX"] + px, tile["sliceY"] + py))
                                        if a and (r, g, b) != (0, 255, 0):
                                            world_y = -tile["y"] - 8 + py
                                            self.assertGreaterEqual(world_y, min_y)
                                            self.assertLess(world_y, 8)

    def test_repair_frames_are_visually_distinct_not_just_different_ids(self):
        from PIL import ImageOps
        for size in (16, 24):
            path = ROOT / f"assets/sprites/opening_worker{size}.png"
            metadata = json.loads(Path(str(path) + ".gbsres").read_text())
            state = next(s for s in metadata["states"] if s["name"] == "Repair")
            frames = state["animations"][0]["frames"]
            self.assertEqual(len(frames), 2)
            signatures = []
            with Image.open(path) as sheet:
                for frame in frames:
                    pieces = []
                    for tile in sorted(frame["tiles"], key=lambda t: (t["y"], t["x"])):
                        x, y = tile["sliceX"], tile["sliceY"]
                        crop = sheet.crop((x, y, x + 8, y + 16))
                        if tile.get("flipX"):
                            crop = ImageOps.mirror(crop)
                        if tile.get("flipY"):
                            crop = ImageOps.flip(crop)
                        pieces.append((tile["x"], tile["y"], crop.tobytes()))
                    signatures.append(tuple(pieces))
            self.assertNotEqual(signatures[0], signatures[1], f"{size}px repair poses are identical")


if __name__ == "__main__":
    unittest.main()
