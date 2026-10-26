"""M-V1 checks; run with managed Python (Pillow) after opening generators."""
import json
from pathlib import Path
import unittest

from PIL import Image

import climb
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
    @staticmethod
    def sprite_and_speed(events):
        sprite = next(e for e in events if e["command"] == "EVENT_PLAYER_SET_SPRITE")
        speed = next(e for e in events if e["command"] == "EVENT_ACTOR_SET_ANIMATION_SPEED")
        return sprite["args"]["spriteSheetId"], speed["args"]["speed"]

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

    def test_fresh_entry_selects_24px_hero_for_default_zero(self):
        import make_opening_scene as scene
        self.assertEqual((scene.HERO_SIZE_24, scene.HERO_SIZE_16), (0, 1))
        entry = scene.build_scene([], [])["script"][0]
        self.assertEqual(entry["args"]["condition"]["valueA"]["value"], scene.HERO_SIZE)
        self.assertEqual(entry["args"]["condition"]["valueB"]["value"], scene.HERO_SIZE_24)
        self.assertEqual(self.sprite_and_speed(entry["children"]["true"]), (
            opening.resource_id("sprite:opening_worker24"), scene.hero_speed(24),
        ))
        self.assertEqual(self.sprite_and_speed(entry["children"]["false"]), (
            opening.resource_id("sprite:opening_worker16"), scene.hero_speed(16),
        ))

    def test_select_toggles_default_24_to_16_then_back(self):
        import make_opening_scene as scene
        script = scene.size_comparison_script()
        toggle = script[2]
        self.assertEqual(toggle["args"]["condition"]["valueA"]["value"], scene.HERO_SIZE)
        self.assertEqual(toggle["args"]["condition"]["valueB"]["value"], scene.HERO_SIZE_24)

        # With default 0, SELECT chooses the 16px comparison sprite and writes 1.
        from_24 = toggle["children"]["true"]
        self.assertEqual(self.sprite_and_speed(from_24), (
            opening.resource_id("sprite:opening_worker16"), scene.hero_speed(16),
        ))
        write_16 = next(e for e in from_24 if e["command"] == "EVENT_SET_VALUE")
        self.assertEqual((write_16["args"]["variable"], write_16["args"]["value"]["value"]),
                         (scene.HERO_SIZE, scene.HERO_SIZE_16))

        # With 1, the next SELECT restores the 24px hero and writes 0.
        from_16 = toggle["children"]["false"]
        self.assertEqual(self.sprite_and_speed(from_16), (
            opening.resource_id("sprite:opening_worker24"), scene.hero_speed(24),
        ))
        write_24 = next(e for e in from_16 if e["command"] == "EVENT_SET_VALUE")
        self.assertEqual((write_24["args"]["variable"], write_24["args"]["value"]["value"]),
                         (scene.HERO_SIZE, scene.HERO_SIZE_24))

    def test_repair_restores_animation_speed_for_active_sprite(self):
        import make_opening_scene as scene
        script = scene.repair_script()[0]["children"]["true"]
        resume = next(e for e in script if e.get("id") == opening.resource_id("event:repair:resume-speed"))
        self.assertEqual(resume["args"]["condition"]["valueA"]["value"], scene.HERO_SIZE)
        self.assertEqual(resume["args"]["condition"]["valueB"]["value"], scene.HERO_SIZE_24)
        speed24 = resume["children"]["true"][0]
        speed16 = resume["children"]["false"][0]
        self.assertEqual(speed24["args"]["speed"], scene.hero_speed(24))
        self.assertEqual(speed16["args"]["speed"], scene.hero_speed(16))

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

    @staticmethod
    def all_commands(events):
        for event in events:
            yield event["command"]
            for branch in event.get("children", {}).values():
                yield from OpeningTests.all_commands(branch)

    def test_exit_trigger_has_stable_id_and_geometry(self):
        import make_opening_scene as scene
        trigger = scene.exit_trigger()
        self.assertEqual(trigger["_resourceType"], "trigger")
        self.assertEqual(trigger["id"], opening.resource_id("trigger:exit"))
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]), opening.EXIT)
        self.assertGreaterEqual(trigger["height"], 3, "exit must cover the 24px hero body")

    def test_exit_is_gated_on_service_restored(self):
        import make_opening_scene as scene
        gate = scene.exit_trigger()["script"][0]
        self.assertEqual(gate["command"], "EVENT_IF")
        self.assertEqual(gate["args"]["condition"]["valueA"]["value"], scene.RESTORED)
        self.assertEqual(gate["args"]["condition"]["valueB"]["value"], 1)

    def test_exit_true_branch_switches_to_climb_start_facing_right(self):
        import make_opening_scene as scene
        import climb
        from make_climb_scene import resource_id as climb_id
        gate = scene.exit_trigger()["script"][0]
        switches = [e for e in gate["children"]["true"] if e["command"] == "EVENT_SWITCH_SCENE"]
        self.assertEqual(len(switches), 1)
        args = switches[0]["args"]
        self.assertEqual(args["sceneId"], climb_id("scene:storm-climb"))
        self.assertEqual((args["x"]["value"], args["y"]["value"]), climb.START)
        self.assertEqual(args["direction"], "right")
        self.assertEqual(args["fadeSpeed"], "2")

    def test_exit_false_branch_has_no_scene_switch_and_nudges_back(self):
        import make_opening_scene as scene
        gate = scene.exit_trigger()["script"][0]
        self.assertNotIn("EVENT_SWITCH_SCENE", list(self.all_commands(gate["children"]["false"])))
        nudge = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((nudge["args"]["x"]["value"], nudge["args"]["y"]["value"]), opening.EXIT_NUDGE)
        dialogue_lines = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_TEXT")["args"]["text"][0]
        self.assertTrue(all(len(line) <= 17 for line in dialogue_lines.split("\n")))

    def test_exit_geometry_is_reachable_for_both_hero_sizes(self):
        for body_rows in (3, 2):  # 24px default and 16px comparison
            with self.subTest(body_rows=body_rows):
                reach = opening.reachable(opening.START, body_rows=body_rows)
                self.assertIn(opening.EXIT_STAND, reach)
                self.assertIn(opening.EXIT_NUDGE, reach)

    def test_exit_trigger_file_matches_generator_and_climb_id(self):
        import make_opening_scene as scene
        from make_climb_scene import resource_id as climb_id
        path = ROOT / "project/scenes/service_opening/triggers" / f"{scene.EXIT_SYMBOL}.gbsres"
        self.assertEqual(json.loads(path.read_text()), scene.exit_trigger())
        climb_scene = json.loads((ROOT / "project/scenes/storm_climb/scene.gbsres").read_text())
        self.assertEqual(climb_scene["id"], climb_id("scene:storm-climb"))

    def test_service_gate_actor_has_stable_id_position_and_no_collision(self):
        import make_opening_scene as scene
        gate = scene.service_gate_actor()
        self.assertEqual(gate["_resourceType"], "actor")
        self.assertEqual(gate["id"], opening.resource_id("actor:service_gate"))
        self.assertEqual(gate["symbol"], "opening_service_gate")
        self.assertEqual((gate["x"], gate["y"]), opening.GATE)
        self.assertEqual(gate["collisionGroup"], "")
        self.assertEqual(gate["spriteSheetId"], climb.grid_resource_id("sprite:service_gate"))
        # The gate stands on the awning end, beside the exit column.
        self.assertEqual(opening.GATE[0], opening.EXIT[0])
        self.assertEqual(opening.GATE[1], opening.EXIT_STAND[1])
        self.assertTrue(opening.standing(*opening.GATE, body_rows=3))

    def test_service_gate_start_script_is_gated_on_restored(self):
        import make_opening_scene as scene
        script = scene.service_gate_actor()["startScript"]
        self.assertEqual(len(script), 1)
        self.assertEqual(script[0]["command"], "EVENT_IF")
        self.assertEqual(script[0]["args"]["condition"]["valueA"]["value"], scene.RESTORED)
        self.assertEqual(script[0]["args"]["condition"]["valueB"]["value"], 0)
        closed = next(e for e in script[0]["children"]["true"] if e["command"] == "EVENT_ACTOR_SET_STATE")
        opened = next(e for e in script[0]["children"]["false"] if e["command"] == "EVENT_ACTOR_SET_STATE")
        self.assertEqual((closed["args"]["actorId"], closed["args"]["spriteStateId"]), ("$self$", "Closed"))
        self.assertEqual((opened["args"]["actorId"], opened["args"]["spriteStateId"]), ("$self$", "Open"))

    def test_repair_opens_service_gate_after_restore_without_second_sound(self):
        import make_opening_scene as scene
        branch = scene.repair_script()[0]["children"]["true"]
        restored = next(i for i, e in enumerate(branch) if e["command"] == "EVENT_SET_VALUE"
                        and e["args"]["variable"] == scene.RESTORED)
        gate_open = next(i for i, e in enumerate(branch) if e["command"] == "EVENT_ACTOR_SET_STATE"
                         and e["args"]["actorId"] == opening.resource_id("actor:service_gate"))
        self.assertGreater(gate_open, restored)
        self.assertEqual(branch[gate_open]["args"]["spriteStateId"], "Open")
        sounds = [e for e in branch if e["command"] == "EVENT_SOUND_PLAY_EFFECT"]
        self.assertEqual(len(sounds), 1, "gate reuses the existing connect sound")

    def test_service_gate_sprite_sidecar_id_when_present(self):
        path = ROOT / "assets/sprites/service_gate.png.gbsres"
        if not path.exists():
            self.skipTest("service_gate sprite sidecar not generated yet")
        self.assertEqual(json.loads(path.read_text())["id"], climb.grid_resource_id("sprite:service_gate"))

    def test_service_gate_actor_file_matches_generator(self):
        import make_opening_scene as scene
        path = ROOT / "project/scenes/service_opening/actors/service_gate.gbsres"
        self.assertEqual(json.loads(path.read_text()), scene.service_gate_actor())

    def test_exit_unpowered_text_references_gate_and_fits(self):
        import make_opening_scene as scene
        gate = scene.exit_trigger()["script"][0]
        text = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_TEXT")["args"]["text"][0]
        self.assertIn("Gate's locked", text)
        self.assertTrue(all(len(line) <= 17 for line in text.split("\n")))


if __name__ == "__main__":
    unittest.main()
