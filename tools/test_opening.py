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
        self.assertEqual([(e["args"]["variable"], e["args"]["value"]["value"]) for e in writes], [
            (opening.VAR_CARRYING_CABLE, 0), (scene.RESTORED, 1),
        ])
        entry = scene.build_scene([], [])["script"]
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == scene.RESTORED
                             for e in entry))
        def walk(events):
            for e in events:
                yield e
                for branch in e.get("children", {}).values():
                    yield from walk(branch)
        self.assertTrue(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == opening.VAR_CARRYING_CABLE
                            for e in walk(entry)))

    def test_entry_uses_only_the_24px_hero_and_no_select_input(self):
        import make_opening_scene as scene
        entry = scene.build_scene([], [])["script"]
        self.assertEqual(self.sprite_and_speed(entry), (
            opening.resource_id("sprite:opening_worker24"), scene.hero_speed(24),
        ))
        self.assertNotIn("EVENT_SET_INPUT_SCRIPT", list(self.all_commands(entry)))
        self.assertFalse(any(e["command"] == "EVENT_IF" and e["args"]["condition"]["valueA"]["value"] == "5"
                             for e in entry))
        def walk(events):
            for e in events:
                yield e
                for branch in e.get("children", {}).values():
                    yield from walk(branch)
        controls = [e["args"]["text"][0] for e in walk(entry) if e["command"] == "EVENT_TEXT"]
        self.assertEqual(controls, [
            "D-pad: move.\nTap A: short hop",
            "Hold A: rise.\nClear overhead.",
            "B: pick up cable.\nB: use cable.",
        ])

    def test_tutorial_requires_explicit_cable_pickup_before_repair(self):
        import make_opening_scene as scene
        cable = scene.cable_actor()
        self.assertEqual(cable["id"], opening.resource_id("actor:tutorial_cable"))
        self.assertEqual((cable["x"], cable["y"]), opening.CABLE)
        pickup = cable["script"][0]["children"]["true"][0]["children"]["true"]
        self.assertEqual(pickup[0]["args"]["variable"], opening.VAR_CARRYING_CABLE)
        self.assertEqual(pickup[0]["args"]["value"]["value"], 1)
        terminal = scene.repair_interaction()[0]
        carry_gate = terminal["children"]["true"][0]
        self.assertEqual(carry_gate["args"]["condition"]["valueA"]["value"], opening.VAR_CARRYING_CABLE)
        repair = carry_gate["children"]["true"][0]["children"]["true"]
        consume = next(e for e in repair if e["command"] == "EVENT_SET_VALUE"
                       and e["args"]["variable"] == opening.VAR_CARRYING_CABLE)
        self.assertEqual(consume["args"]["value"]["value"], 0)
        self.assertTrue(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == scene.RESTORED
                            for e in repair))

    def test_tutorial_pad_reachable_after_pickup_without_changing_physics(self):
        reach = opening.reachable(opening.START, body_rows=3)
        self.assertIn(opening.CABLE, reach)
        self.assertIn(opening.PANEL, reach)
        self.assertEqual(opening.CABLE, (14, 12))  # cable follows the one-shelf rise
        self.assertEqual(opening.PANEL, (4, 15))  # cabinet art and repair pad remain aligned

    def test_wind_is_post_repair_and_recovers_to_panel_checkpoint(self):
        import make_opening_scene as scene
        wind = scene.wind_actor()
        commands = list(self.all_commands(wind["updateScript"]))
        self.assertEqual(wind["id"], opening.resource_id("actor:tutorial_wind"))
        self.assertIn("EVENT_ACTOR_COLLISIONS_DISABLE", self.all_commands(wind["startScript"]))
        self.assertEqual(wind["collisionGroup"], "1")
        self.assertIn("EVENT_ACTOR_COLLISIONS_ENABLE", commands)
        self.assertIn("EVENT_ACTOR_SHOW", commands)
        self.assertIn("EVENT_ACTOR_HIDE", commands)
        self.assertEqual(wind["updateScript"][0]["args"]["condition"]["valueA"]["value"], scene.RESTORED)
        self.assertEqual(wind["updateScript"][0]["args"]["condition"]["valueB"]["value"], 1)
        hit = scene.wind_recovery_events()
        self.assertEqual(hit[0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        self.assertEqual(hit[-1]["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((hit[-1]["args"]["x"]["value"], hit[-1]["args"]["y"]["value"]), opening.PANEL)
        self.assertNotIn("EVENT_TEXT", list(self.all_commands(hit)))
        scene_events = scene.build_scene([], [])["playerHit1Script"]
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == scene.RESTORED
                             for e in scene_events))

    def test_opening_sprite_palette_slots_match_pole_and_gust_art(self):
        import make_opening_scene as scene
        _, sprites = scene.write_palettes()
        import intro
        self.assertEqual(sprites[5], intro.palette_id("rain"))
        self.assertEqual(sprites[7], intro.palette_id("pole"))

    def test_repair_restores_24px_animation_speed(self):
        import make_opening_scene as scene
        script = scene.repair_script()[0]["children"]["true"]
        resume = next(e for e in script if e.get("id") == opening.resource_id("event:repair:resume-speed"))
        self.assertEqual(resume["command"], "EVENT_ACTOR_SET_ANIMATION_SPEED")
        self.assertEqual(resume["args"]["speed"], scene.hero_speed(24))
        self.assertFalse(any(e["command"] == "EVENT_IF" and e["args"]["condition"]["valueA"]["value"] == "5"
                             for e in script))

    def test_geometry(self):
        opening._self_check()
        grid = opening.collision_grid()
        self.assertTrue(all(cell == 15 for cell in grid[16]))
        self.assertEqual(grid[13][13:17], [1] * 4)
        self.assertEqual(grid[10][11:19], [1] * 8)

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
        for name, states in (("opening_worker24", {"Default", "Repair", "Carry", "Shock"}),
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
        for size, min_y in ((24, -16),):
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
                            self.assertLessEqual(len(frame["tiles"]), 4)
                            for tile in frame["tiles"]:
                                for py in range(16):
                                    for px in range(8):
                                        r, g, b, a = sheet.getpixel((tile["sliceX"] + px, tile["sliceY"] + py))
                                        if a and (r, g, b) != (0, 255, 0):
                                            world_y = -tile["y"] - 8 + py
                                            # Carry (plug overhead) and Shock sparks may rise above the hitbox.
                                            floor = min_y - 8 if state["name"] in ("Carry", "Shock") else min_y
                                            self.assertGreaterEqual(world_y, floor)
                                            self.assertLess(world_y, 8)

    def test_carry_state_differs_from_default_with_same_bounds(self):
        for size in (24,):
            path = ROOT / f"assets/sprites/opening_worker{size}.png"
            metadata = json.loads(Path(str(path) + ".gbsres").read_text())
            default = metadata["states"][0]
            carry = next(s for s in metadata["states"] if s["name"] == "Carry")
            self.assertEqual(carry["name"], "Carry")
            self.assertEqual(carry["animationType"], default["animationType"])
            self.assertEqual(metadata["boundsY"], -16)
            self.assertEqual(metadata["boundsHeight"], size)
            with Image.open(path) as sheet:
                sheet = sheet.convert("RGBA")

                def pix(frame):
                    return b"".join(
                        sheet.crop((t["sliceX"], t["sliceY"], t["sliceX"] + 8, t["sliceY"] + 16)).tobytes()
                        for t in frame["tiles"])
                for d_anim, c_anim in zip(default["animations"], carry["animations"]):
                    self.assertEqual(len(d_anim["frames"]), len(c_anim["frames"]))
                    if not d_anim["frames"][0]["tiles"]:
                        continue
                    for d, c in zip(d_anim["frames"], c_anim["frames"]):
                        self.assertNotEqual(pix(d), pix(c))

    def test_repair_frames_are_visually_distinct_not_just_different_ids(self):
        from PIL import ImageOps
        for size in (24,):
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

    def test_exit_true_branch_opens_amaras_work_order(self):
        import make_opening_scene as scene
        import climb
        from make_climb_scene import resource_id as climb_id
        gate = scene.exit_trigger()["script"][0]
        first_dispatch = gate["children"]["true"][0]["children"]["true"]
        switches = [e for e in first_dispatch if e["command"] == "EVENT_SWITCH_SCENE"]
        self.assertEqual(len(switches), 1)
        args = switches[0]["args"]
        # Amara's work order first; ticket 1 then switches to the climb's start.
        import tickets
        self.assertEqual(args["sceneId"], tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(args["fadeSpeed"], "2")
        self.assertEqual(tickets.TICKETS[1]["scene_id"], climb_id("scene:storm-climb"))
        self.assertEqual(tickets.TICKETS[1]["start"], climb.START)

    @staticmethod
    def follow_transition(events, state):
        """Interpret the generated transition's variable branches; retain visible effects.

        Input handlers and actor threads are installed, not executed by scene init.
        This intentionally models only the transition commands used in these tests.
        """
        effects = []
        def value(v):
            return state.get(v["value"], 0) if v["type"] == "variable" else v["value"]
        for e in events:
            command, args = e["command"], e.get("args", {})
            if command == "EVENT_IF":
                condition = args["condition"]
                a, b = value(condition["valueA"]), value(condition["valueB"])
                matched = {"eq": a == b, "ne": a != b, "gte": a >= b}[condition["type"]]
                effects += OpeningTests.follow_transition(e["children"]["true" if matched else "false"], state)
            elif command == "EVENT_SET_VALUE":
                state[args["variable"]] = value(args["value"])
            elif command in ("EVENT_TEXT", "EVENT_SWITCH_SCENE", "EVENT_MUSIC_PLAY"):
                effects.append(e)
        return effects

    def test_first_dispatch_initializes_job_and_briefing_once(self):
        import make_opening_scene as scene
        import make_climb_scene as climb_scene
        import tickets
        state = {opening.VAR_SERVICE_RESTORED: 1}
        exit_effects = self.follow_transition(scene.exit_trigger()["script"], state)
        self.assertEqual([e["args"]["sceneId"] for e in exit_effects
                          if e["command"] == "EVENT_SWITCH_SCENE"], [tickets.WORK_ORDER_SCENE_ID])
        self.assertEqual(state[opening.VAR_AMARA_DISPATCHED], 1)
        self.assertEqual(state[tickets.VAR_TICKET], 1)
        init = self.follow_transition(climb_scene.scene_script("music", {"pickup": "p", "connect": "c"}), state)
        self.assertTrue(any(e["command"] == "EVENT_TEXT" for e in init))
        self.assertEqual(state[tickets.VAR_TICKET], 0)
        self.assertEqual(state[climb.VAR_LINES_LIVE], 0)

    def test_street_round_trips_skip_dispatch_and_briefing_with_zero_or_completed_lines(self):
        import make_opening_scene as scene
        import make_climb_scene as climb_scene
        import grid_chain
        import tickets
        for completed in (0, 1, climb.LINE_COUNT):
            state = {opening.VAR_SERVICE_RESTORED: 1, opening.VAR_AMARA_DISPATCHED: 1,
                     tickets.VAR_TICKET: 0, climb.VAR_CHAIN_LIVE: completed,
                     climb.VAR_LINES_LIVE: completed, grid_chain.VAR_PICKUP_TAUGHT: 1}
            state.update({line["live_var"]: int(line["number"] <= completed) for line in climb.LINES})
            before = dict(state)
            for repeat in range(2):
                with self.subTest(completed=completed, repeat=repeat):
                    effects = self.follow_transition(scene.exit_trigger()["script"], state)
                    self.assertEqual(len(effects), 1)
                    args = effects[0]["args"]
                    self.assertEqual(args["sceneId"], tickets.CLIMB_SCENE_ID)
                    self.assertEqual((args["x"]["value"], args["y"]["value"]), climb.START)
                    init = self.follow_transition(climb_scene.scene_script("music", {"pickup": "p", "connect": "c"}), state)
                    self.assertFalse(any(e["command"] in ("EVENT_TEXT", "EVENT_MUSIC_PLAY") for e in init))
                    self.assertEqual({key: state[key] for key in before}, before)

    def test_opening_variables_have_stable_unused_dispatch_id(self):
        self.assertEqual(opening.VAR_AMARA_DISPATCHED, "54")
        declared = {key: (name, symbol) for key, name, symbol in opening.VARIABLES}
        self.assertEqual(declared["54"], ("Amara Dispatched", "var_amara_dispatched"))

    def test_exit_false_branch_has_no_scene_switch_and_nudges_back(self):
        import make_opening_scene as scene
        gate = scene.exit_trigger()["script"][0]
        self.assertNotIn("EVENT_SWITCH_SCENE", list(self.all_commands(gate["children"]["false"])))
        nudge = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((nudge["args"]["x"]["value"], nudge["args"]["y"]["value"]), opening.EXIT_NUDGE)
        dialogue_lines = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_TEXT")["args"]["text"][0]
        self.assertTrue(all(len(line) <= 17 for line in dialogue_lines.split("\n")))

    def test_exit_geometry_is_reachable_for_the_24px_hero(self):
        reach = opening.reachable(opening.START, body_rows=3)
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

    def test_tutorial_actor_files_match_generator(self):
        import make_opening_scene as scene
        for name, expected in (("tutorial_cable", scene.cable_actor()), ("tutorial_wind", scene.wind_actor())):
            path = ROOT / "project/scenes/service_opening/actors" / f"{name}.gbsres"
            self.assertEqual(json.loads(path.read_text()), expected)

    def test_exit_unpowered_text_references_gate_and_fits(self):
        import make_opening_scene as scene
        gate = scene.exit_trigger()["script"][0]
        text = next(e for e in gate["children"]["false"] if e["command"] == "EVENT_TEXT")["args"]["text"][0]
        self.assertIn("Gate's locked", text)
        self.assertTrue(all(len(line) <= 17 for line in text.split("\n")))


if __name__ == "__main__":
    unittest.main()
