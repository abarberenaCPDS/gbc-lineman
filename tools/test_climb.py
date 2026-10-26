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
        self.assertEqual(script[3]["args"]["musicId"], "test-music")
        self.assertEqual(script[4]["args"]["text"], ["A: jump\nDown+A: drop"])
        self.assertEqual([event["command"] for event in script[5:]], [
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
        self.assertEqual(resource["spritePaletteIds"][1:7], legacy_sprite_palettes[1:7])
        self.assertEqual(resource["spritePaletteIds"][7], legacy_sprite_palettes[7])
        self.assertEqual(opening.resource_id("palette:sprite:worker"),
                         "030624ef-c88f-5e59-8664-65193264ce80")

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
