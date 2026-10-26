"""Focused generator checks: python3 -m unittest discover -s tools -p test_climb.py."""
import json
from pathlib import Path
import unittest

import climb
import level
import make_climb_scene as scene
import compose_climb
import opening
import uge_report


class ClimbTests(unittest.TestCase):
    def test_geometry_invariants(self):
        climb._self_check()

    def test_lower_transitions_have_clear_two_tile_landings(self):
        hazards = climb._hazard_cells()
        for lower, upper in zip(climb.PLATFORMS[:5], climb.PLATFORMS[1:6]):
            lower_row, lx0, lx1 = lower
            upper_row, ux0, ux1 = upper
            candidates = range(max(lx0, ux0), min(lx1, ux1))
            self.assertTrue(any(
                all((row, col) not in hazards
                    for row in range(upper_row + 1, lower_row)
                    for col in (x, x + 1))
                for x in candidates
            ), f"no two-tile safe landing for {lower_row}->{upper_row}")

    def test_collision_encoding_matches_existing_encoder(self):
        grid = climb.collision_grid()
        self.assertEqual(
            scene.collision_rle(grid, climb.MAP_W, climb.MAP_H),
            level.rle([cell for row in grid for cell in row]),
        )

    def test_ids_repeat_and_do_not_overlap(self):
        self.assertEqual(scene.resource_id("scene"), scene.resource_id("scene"))
        self.assertNotEqual(scene.resource_id("scene"), scene.resource_id("actor"))

    def test_new_scene_uses_matching_background(self):
        resource = scene.build_scene("test-music")
        self.assertEqual(resource["backgroundId"], scene.resource_id("background:storm-climb"))
        self.assertEqual((resource["width"], resource["height"]), (20, 36))

    def test_scene_starts_with_approved_24px_worker_facing_right(self):
        resource = scene.build_scene("test-music")
        script = resource["script"]

        self.assertEqual(opening.resource_id("sprite:opening_worker24"),
                         "9cb46fea-def2-507c-8edb-a3ca83a61946")
        self.assertEqual(script[0]["command"], "EVENT_PLAYER_SET_SPRITE")
        self.assertEqual(script[0]["args"], {
            "spriteSheetId": "9cb46fea-def2-507c-8edb-a3ca83a61946",
        })
        self.assertEqual(script[1]["command"], "EVENT_ACTOR_SET_DIRECTION")
        self.assertEqual(script[1]["args"], {
            "actorId": "player", "direction": {"type": "direction", "value": "right"},
        })

    def test_scene_init_retains_checkpoint_music_help_and_hud(self):
        script = scene.build_scene("test-music")["script"]
        self.assertEqual(script[2]["command"], "EVENT_SET_VALUE")
        self.assertEqual(script[2]["args"]["variable"], "0")
        self.assertEqual(script[2]["args"]["value"]["value"], 0)
        self.assertEqual(script[3]["command"], "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(script[4]["args"]["musicId"], "test-music")
        self.assertEqual(script[5]["args"]["text"], ["A: jump\nDown+A: drop"])
        self.assertEqual([event["command"] for event in script[6:]], [
            "EVENT_OVERLAY_SET_SCANLINE_CUTOFF", "EVENT_OVERLAY_SHOW", "EVENT_TEXT_DRAW",
        ])
        self.assertFalse(any(
            event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == "4"
            for event in script
        ), "Storm Climb init must not reset Service Restored")

    def test_scene_uses_opening_background_palettes_and_preserves_legacy_sprite_slots(self):
        resource = scene.build_scene("test-music")
        expected_backgrounds = [
            "71085f61-67fb-53bf-ab00-42f6ae97915c",
            "6dca60e7-b2dc-5a6f-a856-2d2139cfc0fc",
            "b2dbc43f-5ea2-5ffc-a0db-359d862e8847",
            "7236f4af-b46f-5c4c-8d8b-827b1065a563",
            "36aaf291-f0e8-5d60-8f28-bb0ce316b9a4",
            "c25ce4da-331a-5bf6-8ba2-ec1e56cbc9de",
            "87767377-69df-5af2-a439-3d97ab633758",
            "default-ui",
        ]
        self.assertEqual(expected_backgrounds[:7], [
            opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
        ])
        self.assertEqual(resource["paletteIds"], expected_backgrounds)
        self.assertEqual(len(resource["paletteIds"]), 8)
        self.assertEqual(resource["paletteIds"][7], "default-ui")

        legacy_sprite_palettes = scene.load_json(scene.REFERENCE_SCENE)["spritePaletteIds"]
        self.assertEqual(len(resource["spritePaletteIds"]), 8)
        self.assertEqual(resource["spritePaletteIds"][0],
                         "030624ef-c88f-5e59-8664-65193264ce80")
        # Slot 1 now carries Marta; debris (4), gust (5) and the rest keep legacy IDs.
        self.assertEqual(resource["spritePaletteIds"][1], opening.resource_id("palette:sprite:marta"))
        self.assertEqual(resource["spritePaletteIds"][2:7], legacy_sprite_palettes[2:7])
        self.assertEqual(resource["spritePaletteIds"][7], legacy_sprite_palettes[7])
        self.assertEqual(opening.resource_id("palette:sprite:worker"),
                         "030624ef-c88f-5e59-8664-65193264ce80")

    @staticmethod
    def _flatten(events):
        for entry in events:
            yield entry
            for branch in entry.get("children", {}).values():
                yield from ClimbTests._flatten(branch)

    @staticmethod
    def _checkpoint_trigger():
        return scene.build_checkpoint_trigger(
            scene.sidecar_id("assets/sounds/death.wav.gbsres", "sound"),
            scene.sidecar_id("assets/sounds/connect.wav.gbsres", "sound"),
        )

    def test_checkpoint_gate_is_once_only_and_swaps_summit_window_warm(self):
        trigger = self._checkpoint_trigger()
        gate = trigger["script"][0]
        self.assertEqual(gate["command"], "EVENT_IF")
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "0"})
        self.assertEqual(gate["args"]["condition"]["valueB"], {"type": "number", "value": 0})
        self.assertEqual(gate["children"]["false"], [])
        true_events = list(self._flatten(gate["children"]["true"]))
        self.assertEqual(true_events[0]["command"], "EVENT_SET_VALUE")
        self.assertEqual(true_events[0]["args"]["value"]["value"], 1)

        palette = next(e for e in true_events if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(palette["args"]["palette3"],
                         opening.resource_id("palette:bg:powered_window"))
        self.assertEqual({k: v for k, v in palette["args"].items() if k != "palette3"},
                         {f"palette{i}": "keep" for i in range(8) if i != 3})

        marta = next(e for e in true_events if e["command"] == "EVENT_ACTOR_SET_STATE")
        self.assertEqual(marta["args"]["actorId"], scene.marta_actor_id())
        self.assertEqual(marta["args"]["spriteStateId"], "Powered")

        sound = next(e for e in true_events if e["command"] == "EVENT_SOUND_PLAY_EFFECT")
        self.assertEqual(sound["args"]["type"],
                         scene.sidecar_id("assets/sounds/connect.wav.gbsres", "sound"))

        text = next(e for e in true_events if e["command"] == "EVENT_TEXT")
        self.assertEqual(text["args"]["text"], ["Made it, CFE!\nRest here."])
        self.assertEqual(scene.MAX_DIALOGUE_CHARS, 17)

    def test_scene_init_sets_summit_window_cold_on_every_entry(self):
        script = scene.build_scene("test-music")["script"]
        palette_events = [e for e in script if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertEqual(len(palette_events), 1)
        args = palette_events[0]["args"]
        self.assertEqual(args["palette3"], opening.resource_id("palette:bg:window"))
        self.assertEqual(args["palette3"], "7236f4af-b46f-5c4c-8d8b-827b1065a563")
        self.assertEqual({k: v for k, v in args.items() if k != "palette3"},
                         {f"palette{i}": "keep" for i in range(8) if i != 3})

    def test_marta_checkpoint_actor_uses_opening_sprite_on_summit_shelf(self):
        actor = scene.checkpoint_actor(0, opening.resource_id("sprite:opening_marta"))
        self.assertEqual(actor["id"], "0a208a0e-9313-59b7-be31-3be4c204ab2a")
        self.assertEqual(actor["id"], scene.resource_id("actor:marta-checkpoint"))
        self.assertEqual(actor["symbol"], "marta_checkpoint")
        self.assertEqual(actor["spriteSheetId"], opening.resource_id("sprite:opening_marta"))
        self.assertEqual(actor["collisionGroup"], "")
        self.assertTrue(actor["animate"])
        self.assertEqual((actor["x"], actor["y"]), scene.MARTA_SHELF_POSITION)
        x, y = actor["x"], actor["y"]
        self.assertEqual(climb.collision_grid()[y + 1][x], climb.COL_TOP)
        self.assertEqual(climb.collision_grid()[y][x], climb.COL_EMPTY)
        self.assertEqual(actor["startScript"][0]["args"]["spriteStateId"], "Waiting")
        self.assertEqual(actor["startScript"][0]["args"]["actorId"], "$self$")

    def test_marta_sprite_palette_slot_is_free_and_matches_sprite_tiles(self):
        def palette_indexes(path):
            found = set()
            def walk(node):
                if isinstance(node, dict):
                    if "paletteIndex" in node:
                        found.add(node["paletteIndex"])
                    for value in node.values():
                        walk(value)
                elif isinstance(node, list):
                    for value in node:
                        walk(value)
            walk(json.loads((scene.PROJECT_DIR / path).read_text(encoding="utf-8")))
            return found

        marta_slots = palette_indexes("assets/sprites/opening_marta.png.gbsres")
        self.assertEqual(marta_slots, {scene.MARTA_SPRITE_PALETTE_SLOT})
        other_slots = set()
        for path in ("assets/sprites/opening_worker24.png.gbsres",
                     "assets/sprites/climb_debris.png.gbsres",
                     "assets/sprites/climb_gust.png.gbsres"):
            other_slots |= palette_indexes(path)
        self.assertEqual(other_slots, {0, 4, 5})
        self.assertNotIn(scene.MARTA_SPRITE_PALETTE_SLOT, other_slots)

        resource = scene.build_scene("test-music")
        self.assertEqual(resource["spritePaletteIds"][scene.MARTA_SPRITE_PALETTE_SLOT],
                         opening.resource_id("palette:sprite:marta"))
        self.assertEqual(resource["spritePaletteIds"][0],
                         opening.resource_id("palette:sprite:worker"))

    def test_arrival_trigger_covers_house_and_standing_24px_hero_without_hazards(self):
        trigger = self._checkpoint_trigger()
        x, y, width, height = scene.arrival_rect()
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         (x, y, width, height))
        house_x, house_y = climb.HOUSE_A["x"], climb.HOUSE_A["y"]
        self.assertTrue(x <= house_x < x + width, "doorway columns include House A")

        # Hero hitbox from the 24px worker asset: bounds y -16, height 24, so
        # standing at House A's tile row covers rows house_y-2 .. house_y.
        worker = scene.load_json(scene.PROJECT_DIR / "assets/sprites/opening_worker24.png.gbsres")
        top = house_y * 8 + worker["boundsY"]
        bottom = top + worker["boundsHeight"] - 1
        covered_rows = range(top // 8, bottom // 8 + 1)
        self.assertEqual(list(covered_rows), list(range(house_y - 2, house_y + 1)))
        self.assertIn(top // 8, range(y, y + height))

        # Regression from exact-ROM play: an 8-frame A tap rises 38px, so a
        # jump from shelf 12 (or below) must not reach the trigger row, and
        # the clear 12->9->6 takeoff at x72 (collider 74..85) stays left of it.
        shelf12_top = (12 - 1) * 8 + worker["boundsY"]
        self.assertGreater(shelf12_top - 38, (y + height) * 8 - 1)
        self.assertGreater(x * 8, 72 + worker["boundsX"] + worker["boundsWidth"] - 1)

        grid = climb.collision_grid()
        hazards = climb._hazard_cells()
        for row in range(y, y + height):
            for column in range(x, x + width):
                self.assertEqual(grid[row][column], climb.COL_EMPTY)
                self.assertNotIn((row, column), hazards)

    def test_respawn_remains_checkpoint_aware_for_debris_and_gusts(self):
        player_hit = scene.build_scene("test-music")["playerHit1Script"]
        branch = next(e for e in player_hit if e["command"] == "EVENT_IF")["children"]
        self.assertEqual(branch["true"][0]["args"]["x"]["value"], climb.START[0])
        self.assertEqual(branch["false"][0]["args"]["y"]["value"], climb.HOUSE_A["y"])
        gust = scene.trigger_resource(1, climb.GUST_LANES[0], "death-sound")
        gust_if = gust["script"][1]
        self.assertEqual(gust_if["children"]["false"][0]["args"]["x"]["value"], climb.HOUSE_A["x"])
        self.assertEqual(gust_if["children"]["true"][0]["args"]["x"]["value"], climb.START[0])

    def test_checkpoint_trigger_keeps_stable_resource_id(self):
        self.assertEqual(self._checkpoint_trigger()["id"],
                         "b02fc406-5513-54f5-abd9-25c1adb2da51")

    def test_every_storm_climb_dialogue_line_fits_limit(self):
        scripts = [scene.build_scene("test-music")["script"],
                   scene.checkpoint_actor(0, "sprite")["script"],
                   self._checkpoint_trigger()["script"]]
        checked = 0
        for script in scripts:
            for entry in self._flatten(script):
                if entry["command"] != "EVENT_TEXT":
                    continue
                for line in entry["args"]["text"]:
                    for part in line.split("\n"):
                        self.assertLessEqual(len(part), scene.MAX_DIALOGUE_CHARS, part)
                        checked += 1
        self.assertGreaterEqual(checked, 6)

    def test_debris_has_safe_warning_then_damaging_fall(self):
        actor = scene.debris_actor(1, climb.HAZARD_DEBRIS[0], "test-sprite")
        self.assertEqual(actor["collisionGroup"], "1")
        commands = [e["command"] for e in actor["updateScript"]]
        self.assertEqual(commands[0], "EVENT_ACTOR_COLLISIONS_DISABLE")
        warning = next(e for e in actor["updateScript"] if e["command"] == "EVENT_WAIT")
        self.assertEqual(warning["args"]["frames"]["value"], climb.DEBRIS_WARNING_FRAMES)
        self.assertGreater(commands.index("EVENT_ACTOR_COLLISIONS_ENABLE"), commands.index("EVENT_WAIT"))
        self.assertEqual(commands[-3:], ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE", "EVENT_WAIT"])
        positions = [e["args"]["y"]["value"] for e in actor["updateScript"]
                     if e["command"] == "EVENT_ACTOR_SET_POSITION"]
        self.assertEqual(positions[-1], climb.HAZARD_DEBRIS[0]["row_bottom"] * 8)

    def test_first_timed_gust_has_safe_warning_and_actor_owned_collision(self):
        lane = climb.GUST_LANES[0]
        actor = scene.timed_gust_actor(1, lane, "test-gust-sprite")
        self.assertEqual((actor["x"], actor["y"]), (lane[1], lane[0]))
        self.assertEqual(actor["collisionGroup"], "1")
        self.assertEqual(actor["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        script = actor["updateScript"]
        commands = [entry["command"] for entry in script]
        assert_order = lambda a, b: self.assertLess(commands.index(a), commands.index(b))
        assert_order("EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_SET_STATE")
        assert_order("EVENT_WAIT", "EVENT_ACTOR_COLLISIONS_ENABLE")
        self.assertEqual([entry["args"]["spriteStateId"] for entry in script
                          if entry["command"] == "EVENT_ACTOR_SET_STATE"], ["Warning", "Burst"])
        self.assertEqual([entry["args"]["frames"]["value"] for entry in script
                          if entry["command"] == "EVENT_WAIT"],
                         [climb.GUST_WARNING_FRAMES, climb.GUST_ACTIVE_FRAMES,
                          climb.GUST_REST_FRAMES])
        self.assertEqual(commands[-3:], ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE", "EVENT_WAIT"])
        legacy = scene.trigger_resource(1, lane, "death-sound")
        self.assertTrue(legacy["script"], "base trigger constructor retains legacy shape")

    def test_no_instant_reset_trigger_left_on_unverified_gust_lanes(self):
        markers = scene.gust_marker_triggers("death-sound")
        self.assertEqual(len(markers), len(climb.GUST_LANES))
        self.assertTrue(all(marker["script"] == [] for marker in markers))
        self.assertEqual(markers[0]["id"],
                         scene.trigger_resource(1, climb.GUST_LANES[0], "death-sound")["id"])
        self.assertIn("timed actor-owned", markers[0]["name"])
        self.assertTrue(all("inactive preview" in marker["name"] for marker in markers[1:]))

    def test_debris_reset_does_not_erase_checkpoint(self):
        commands = scene.respawn_events("test-reset", "death-sound")
        self.assertEqual(commands[1]["command"], "EVENT_IF")
        branch = commands[1]["children"]
        self.assertEqual(branch["true"][0]["args"]["x"]["value"], climb.START[0])
        self.assertEqual(branch["false"][0]["args"]["y"]["value"], climb.HOUSE_A["y"])

    def test_climb_theme_structure_is_deterministic(self):
        music = compose_climb.song()
        compose_climb.validate(music)
        self.assertEqual(music, compose_climb.song())
        self.assertEqual(len(music["patterns"]), 32)
        self.assertEqual(music["ticks_per_row"], 6)
        self.assertTrue(all(len(sequence) == 8 for sequence in music["orders"]))

    def test_music_bridge_is_less_dense_than_opening(self):
        patterns = compose_climb.song()["patterns"]
        count = lambda key: sum(e["note"] is not None for e in patterns[str(key)])
        self.assertLess(count(4), count(0))

    def test_climb_music_json_is_regenerated_from_canonical_source(self):
        path = Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.json"
        self.assertEqual(json.loads(path.read_text()), compose_climb.song())

    def test_climb_uge_patterns_and_orders_match_canonical_json(self):
        source = compose_climb.song()
        binary = uge_report.parse(str(Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.uge"))

        self.assertEqual(binary["version"], 6)
        self.assertEqual(binary["ticks_per_row"], source["ticks_per_row"])
        self.assertEqual(binary["trailing_bytes"], 0)
        self.assertEqual(len(binary["patterns"]), 32)
        self.assertEqual(
            binary["orders"], [sequence + [0] for sequence in source["orders"]]
        )

        total_events = 0
        for key, events in source["patterns"].items():
            expected = {}
            for event in events:
                pitch = event["note"]
                note_code = (
                    uge_report.NO_NOTE
                    if pitch is None
                    else uge_report.NOTE_NAMES.index(
                        pitch[0] + (pitch[1:] if "#" in pitch else "-" + pitch[1:])
                    )
                )
                expected[event["row"]] = {
                    "note": note_code,
                    "inst": event["inst"],
                    "vol": 0,
                    "fx": event["fx"],
                    "fxp": event["fxp"],
                }
            self.assertEqual(len(expected), len(events), f"duplicate source row in {key}")
            actual = {event["row"]: {k: v for k, v in event.items() if k != "row"}
                      for event in binary["patterns"][int(key)]}
            self.assertEqual(actual, expected, f"pattern {key} differs from JSON")
            total_events += len(actual)

        self.assertEqual(total_events, 840)

    def test_climb_uge_instrument_envelopes_and_volume_effects(self):
        binary = uge_report.parse(str(Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.uge"))
        instruments = binary["instruments"]

        # Global IDs are one-based; slot 16 is the first wave instrument.
        self.assertEqual((instruments[0]["initial_volume"],
                          instruments[0]["vol_sweep_direction"],
                          instruments[0]["vol_sweep_amount"]), (6, "down", 2))
        self.assertEqual((instruments[1]["initial_volume"],
                          instruments[1]["vol_sweep_direction"],
                          instruments[1]["vol_sweep_amount"]), (10, "down", 2))
        self.assertEqual(instruments[15]["type_name"], "wave")
        self.assertEqual(instruments[15]["output_level"], 2)
        self.assertTrue(all(instruments[index]["type_name"] == "noise"
                            and instruments[index]["initial_volume"] == 7
                            and instruments[index]["vol_sweep_direction"] == "down"
                            and instruments[index]["vol_sweep_amount"] == 2
                            for index in (30, 31)))

        for cells in binary["patterns"].values():
            for cell in cells:
                if cell["fx"] == 0xC:
                    self.assertLessEqual(cell["fxp"], 15)

    def test_b_major_turnaround_phrase_has_matching_backing(self):
        source = compose_climb.song()

        def pitch_class(pitch):
            return pitch[:-1]

        for section, phrase_ids in enumerate(compose_climb.SECTIONS):
            for bar, phrase_id in enumerate(phrase_ids):
                if phrase_id != 7:
                    continue
                first_row = bar * 16
                last_row = first_row + 16
                melody = {
                    pitch_class(event["note"])
                    for event in source["patterns"][str(section)]
                    if first_row <= event["row"] < last_row and event["note"] is not None
                }
                backing = {
                    pitch_class(event["note"])
                    for channel in (1, 2)
                    for event in source["patterns"][str(section + channel * 100)]
                    if first_row <= event["row"] < last_row and event["note"] is not None
                }
                with self.subTest(section=section, bar=bar + 1):
                    self.assertTrue(
                        melody <= backing,
                        f"B-major phrase {sorted(melody)} is not supported by "
                        f"accompaniment {sorted(backing)}",
                    )


if __name__ == "__main__":
    unittest.main()
