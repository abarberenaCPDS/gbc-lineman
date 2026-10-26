"""Focused generator checks: python3 -m unittest discover -s tools -p test_climb.py."""
import json
import re
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
        self.assertEqual(
            [(e["args"]["variable"], e["args"]["value"]["value"]) for e in script[3:5]],
            [(climb.VAR_CARRYING_CABLE, 0), (climb.VAR_LINE_LIVE, 0)],
        )
        self.assertEqual(script[5]["command"], "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(script[6]["command"], "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(script[7]["args"]["musicId"], "test-music")
        self.assertEqual(script[8]["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
        self.assertEqual(script[9]["args"]["text"], ["A: jump\nDown+A: drop"])
        self.assertEqual([event["command"] for event in script[10:]], [
            "EVENT_OVERLAY_SET_SCANLINE_CUTOFF", "EVENT_OVERLAY_SHOW", "EVENT_TEXT_DRAW",
        ])
        self.assertFalse(any(
            event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == "4"
            for event in script
        ), "Storm Climb init must not reset Service Restored")

    def test_scene_uses_opening_background_palettes_and_preserves_legacy_sprite_slots(self):
        resource = scene.build_scene("test-music")
        opening_backgrounds = [
            opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
        ]
        self.assertEqual(opening_backgrounds[:5], [
            "71085f61-67fb-53bf-ab00-42f6ae97915c",
            "6dca60e7-b2dc-5a6f-a856-2d2139cfc0fc",
            "b2dbc43f-5ea2-5ffc-a0db-359d862e8847",
            "7236f4af-b46f-5c4c-8d8b-827b1065a563",
            "36aaf291-f0e8-5d60-8f28-bb0ce316b9a4",
        ])
        self.assertEqual(opening_backgrounds[6], "87767377-69df-5af2-a439-3d97ab633758")
        # Slot 5 was opening metal; Live Wire's metal dead has identical colours,
        # so the scene default looks the same and only the ID is the climb's own.
        self.assertEqual(opening_backgrounds[5], "c25ce4da-331a-5bf6-8ba2-ec1e56cbc9de")
        self.assertEqual(dict(opening.BG_PALETTES)["metal"], climb.METAL_DEAD)
        expected_backgrounds = (
            opening_backgrounds[:5]
            + [climb.grid_resource_id("palette:bg:metal_dead")]
            + opening_backgrounds[6:]
            + ["default-ui"]
        )
        self.assertEqual(resource["paletteIds"], expected_backgrounds)
        self.assertEqual(len(resource["paletteIds"]), 8)
        self.assertEqual(resource["paletteIds"][7], "default-ui")

        legacy_sprite_palettes = scene.load_json(scene.REFERENCE_SCENE)["spritePaletteIds"]
        self.assertEqual(len(resource["spritePaletteIds"]), 8)
        self.assertEqual(resource["spritePaletteIds"][0],
                         "030624ef-c88f-5e59-8664-65193264ce80")
        # Slot 1 carries Marta and slot 2 the Live Wire grid; the rest keep legacy IDs.
        self.assertEqual(resource["spritePaletteIds"][1], opening.resource_id("palette:sprite:marta"))
        self.assertEqual(resource["spritePaletteIds"][2], climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(resource["spritePaletteIds"][3:7], legacy_sprite_palettes[3:7])
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

    def test_checkpoint_reward_needs_live_line_and_is_once_only(self):
        trigger = self._checkpoint_trigger()
        gate = trigger["script"][0]
        self.assertEqual(gate["command"], "EVENT_IF")
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "7"})
        self.assertEqual(gate["args"]["condition"]["valueB"], {"type": "number", "value": 1})

        # Without power the door only complains: no checkpoint, no var 0 write.
        no_power = list(self._flatten(gate["children"]["false"]))
        self.assertEqual(self._texts(no_power), [["Still no power.\nFix the line!"]])
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" for e in no_power))

        once = gate["children"]["true"]
        self.assertEqual(len(once), 1)
        once_gate = once[0]
        self.assertEqual(once_gate["args"]["condition"]["valueA"], {"type": "variable", "value": "0"})
        self.assertEqual(once_gate["args"]["condition"]["valueB"], {"type": "number", "value": 0})
        self.assertEqual(once_gate["children"]["false"], [])
        true_events = list(self._flatten(once_gate["children"]["true"]))
        self.assertEqual(true_events[0]["command"], "EVENT_SET_VALUE")
        self.assertEqual(true_events[0]["args"]["variable"], "0")
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
        self.assertEqual(text["args"]["text"], ["Power's back!\nMy fridge hums."])
        self.assertEqual(scene.MAX_DIALOGUE_CHARS, 17)

    def test_scene_init_sets_summit_window_cold_and_line_dead_on_every_entry(self):
        script = scene.build_scene("test-music")["script"]
        palette_events = [e for e in script if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertEqual(len(palette_events), 2)
        args = palette_events[0]["args"]
        self.assertEqual(args["palette3"], opening.resource_id("palette:bg:window"))
        self.assertEqual(args["palette3"], "7236f4af-b46f-5c4c-8d8b-827b1065a563")
        self.assertEqual({k: v for k, v in args.items() if k != "palette3"},
                         {f"palette{i}": "keep" for i in range(8) if i != 3})
        line_args = palette_events[1]["args"]
        self.assertEqual(line_args["palette5"], climb.grid_resource_id("palette:bg:metal_dead"))
        self.assertEqual({k: v for k, v in line_args.items() if k != "palette5"},
                         {f"palette{i}": "keep" for i in range(8) if i != 5})

    @staticmethod
    def _checkpoint_branch(events):
        """The respawn IF keyed on var 0: start when unreached, else House A."""
        return next(e for e in events if e["command"] == "EVENT_IF"
                    and e["args"]["condition"]["valueA"] == {"type": "variable", "value": "0"})

    @staticmethod
    def _variable_branch(events, variable):
        return next(e for e in events if e["command"] == "EVENT_IF"
                    and e["args"]["condition"]["valueA"] == {"type": "variable", "value": variable})

    def test_line_palette_swap_touches_only_slot_five(self):
        for live in (False, True):
            args = scene.line_palette_state(live, "test")["args"]
            self.assertEqual(args["palette5"], climb.grid_resource_id(
                "palette:bg:metal_" + ("live" if live else "dead")))
            self.assertEqual({k: v for k, v in args.items() if k != "palette5"},
                             {f"palette{i}": "keep" for i in range(8) if i != 5})

    def test_grid_palettes_serialize_intended_colors_and_match_disk(self):
        files = dict(scene.grid_palettes())
        self.assertEqual(sorted(files), [
            "project/palettes/storm_climb_bg_metal_dead.gbsres",
            "project/palettes/storm_climb_bg_metal_live.gbsres",
            "project/palettes/storm_climb_sprite_grid.gbsres",
        ])
        sprite = files["project/palettes/storm_climb_sprite_grid.gbsres"]
        self.assertEqual(sprite["id"], climb.grid_resource_id("palette:sprite:grid"))
        # Editor [light, mid, dark, dark]: hardware 1..3 survive GB Studio's [p0,p0,p1,p3].
        self.assertEqual(sprite["colors"], ["C7DCE1", "38C8D8", "142332", "142332"])
        self.assertEqual(sprite["defaultColors"], sprite["colors"])
        dead = files["project/palettes/storm_climb_bg_metal_dead.gbsres"]
        live = files["project/palettes/storm_climb_bg_metal_live.gbsres"]
        self.assertEqual(dead["id"], climb.grid_resource_id("palette:bg:metal_dead"))
        self.assertEqual(live["id"], climb.grid_resource_id("palette:bg:metal_live"))
        self.assertEqual(dead["colors"], climb.METAL_DEAD)
        self.assertEqual(live["colors"], climb.METAL_LIVE)
        # Only colour index 1 (the cable route) changes between dead and live.
        self.assertEqual([a != b for a, b in zip(climb.METAL_DEAD, climb.METAL_LIVE)],
                         [False, True, False, False])
        for path, resource in files.items():
            self.assertEqual(json.loads((scene.PROJECT_DIR / path).read_text(encoding="utf-8")),
                             resource, path)

    def test_live_wire_variables_are_registered_without_changing_existing(self):
        data = scene.load_json(scene.PROJECT_DIR / "project" / "variables.gbsres")
        merged = scene.merged_variables(data)
        self.assertEqual(scene.merged_variables(merged), merged, "registration is idempotent")
        by_id = {v["id"]: v for v in merged["variables"]}
        self.assertEqual(by_id[climb.VAR_CARRYING_CABLE],
                         {"id": "6", "name": "Carrying Cable", "symbol": "var_carrying_cable"})
        self.assertEqual(by_id[climb.VAR_LINE_LIVE],
                         {"id": "7", "name": "Line Live", "symbol": "var_line_live"})
        self.assertEqual(by_id["4"]["symbol"], "var_service_restored")
        self.assertEqual(by_id["5"]["symbol"], "var_opening_hero_size")
        self.assertEqual(data["variables"], merged["variables"][:len(data["variables"])])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "6", "name": "Other", "symbol": "var_other"}]})

    def test_cable_end_is_dangling_pickup_on_storm_pole(self):
        actor = scene.cable_end_actor(6, climb.grid_resource_id("sprite:grid_cable_end"), "pickup-sfx")
        self.assertEqual(actor["id"], scene.resource_id("actor:cable-end"))
        self.assertEqual(actor["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
        self.assertEqual((actor["x"], actor["y"]), climb.DAMAGED_POLE)
        self.assertEqual(actor["startScript"][0]["args"]["spriteStateId"], "Dangling")

        outer = actor["script"][0]
        self.assertEqual(outer["args"]["condition"]["valueA"], {"type": "variable", "value": "6"})
        self.assertEqual(outer["args"]["condition"]["valueB"], {"type": "number", "value": 0})
        self.assertEqual(outer["children"]["false"], [])
        inner = outer["children"]["true"][0]
        self.assertEqual(inner["args"]["condition"]["valueA"], {"type": "variable", "value": "7"})
        self.assertEqual(inner["args"]["condition"]["valueB"], {"type": "number", "value": 0})
        self.assertEqual(inner["children"]["false"], [])
        flat = list(self._flatten(inner["children"]["true"]))
        self.assertEqual([(e["args"]["variable"], e["args"]["value"]["value"])
                          for e in flat if e["command"] == "EVENT_SET_VALUE"], [("6", 1)])
        hide = next(e for e in flat if e["command"] == "EVENT_ACTOR_HIDE")
        self.assertEqual(hide["args"]["actorId"], "$self$")
        sound = next(e for e in flat if e["command"] == "EVENT_SOUND_PLAY_EFFECT")
        self.assertEqual(sound["args"]["type"], "pickup-sfx")
        text = next(e for e in flat if e["command"] == "EVENT_TEXT")
        self.assertEqual(text["args"]["text"], ["Got the cable!\nTake it up top."])
        self.assertTrue(any(e["command"] == "EVENT_TEXT_DRAW" for e in flat), "HUD redraw")

    def test_junction_box_plugs_carried_cable_once_and_lights_slot_five(self):
        box = scene.junction_box_actor(7, climb.grid_resource_id("sprite:grid_junction_box"),
                                       "connect-sfx")
        self.assertEqual(box["id"], scene.resource_id("actor:junction-box"))
        self.assertEqual(box["spriteSheetId"], climb.grid_resource_id("sprite:grid_junction_box"))
        self.assertEqual((box["x"], box["y"]), climb.JUNCTION_BOX)
        self.assertEqual(box["startScript"][0]["args"]["spriteStateId"], "Dead")

        top = box["script"][0]
        self.assertEqual(top["args"]["condition"]["valueA"], {"type": "variable", "value": "7"})
        self.assertEqual(self._texts(top["children"]["true"]), [["Line is live."]])
        has_cable = top["children"]["false"][0]
        self.assertEqual(has_cable["args"]["condition"]["valueA"], {"type": "variable", "value": "6"})
        self.assertEqual(self._texts(has_cable["children"]["false"]),
                         [["No cable yet.\nCheck the pole."]])
        flat = list(self._flatten(has_cable["children"]["true"]))
        self.assertEqual([(e["args"]["variable"], e["args"]["value"]["value"])
                          for e in flat if e["command"] == "EVENT_SET_VALUE"],
                         [("6", 0), ("7", 1)])
        state = next(e for e in flat if e["command"] == "EVENT_ACTOR_SET_STATE")
        self.assertEqual((state["args"]["actorId"], state["args"]["spriteStateId"]), ("$self$", "Live"))
        palette = next(e for e in flat if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(palette["args"]["palette5"], climb.grid_resource_id("palette:bg:metal_live"))
        self.assertEqual({k: v for k, v in palette["args"].items() if k != "palette5"},
                         {f"palette{i}": "keep" for i in range(8) if i != 5})
        sound = next(e for e in flat if e["command"] == "EVENT_SOUND_PLAY_EFFECT")
        self.assertEqual(sound["args"]["type"], "connect-sfx")
        text = next(e for e in flat if e["command"] == "EVENT_TEXT")
        self.assertEqual(text["args"]["text"], ["Line is live!\nOn to Marta's."])

    def test_respawn_drops_carried_cable_before_repositioning(self):
        for events in (scene.build_scene("test-music")["playerHit1Script"],
                       scene.trigger_resource(1, climb.GUST_LANES[0], "death-sound")["script"]):
            drop = self._variable_branch(events, "6")
            self.assertEqual(drop["args"]["condition"]["valueB"], {"type": "number", "value": 1})
            self.assertLess(events.index(drop), events.index(self._checkpoint_branch(events)))
            flat = list(self._flatten(drop["children"]["true"]))
            self.assertEqual([(e["args"]["variable"], e["args"]["value"]["value"])
                              for e in flat if e["command"] == "EVENT_SET_VALUE"], [("6", 0)])
            show = next(e for e in flat if e["command"] == "EVENT_ACTOR_SHOW")
            self.assertEqual(show["args"]["actorId"], scene.cable_actor_id())
            state = next(e for e in flat if e["command"] == "EVENT_ACTOR_SET_STATE")
            self.assertEqual((state["args"]["actorId"], state["args"]["spriteStateId"]),
                             (scene.cable_actor_id(), "Dangling"))
            self.assertTrue(any(e["command"] == "EVENT_TEXT_DRAW" for e in flat), "HUD redraw")

    def test_marta_talk_tracks_line_and_saved_food(self):
        talk = scene.checkpoint_actor(0, "sprite")["script"][0]
        self.assertEqual(talk["args"]["condition"]["valueA"], {"type": "variable", "value": "0"})
        self.assertEqual(len(talk["children"]["true"]), 1)
        line = talk["children"]["true"][0]
        self.assertEqual(line["args"]["condition"]["valueA"], {"type": "variable", "value": "7"})
        self.assertEqual(self._texts(line["children"]["true"]), [["Storm broke the\nline below."]])
        self.assertEqual(self._texts(line["children"]["false"]), [["Line's live!\nGo to my door."]])
        self.assertEqual(self._texts(talk["children"]["false"]), [["Food is saved.\nThank you, CFE!"]])

    def test_in_play_text_lifts_hud_cutoff_first(self):
        """Exact-ROM regression: text behind the 16px HUD cutoff was invisible
        while its script waited for A, freezing the player after the pickup."""
        scripts = [
            # Scene init too: re-entry inherits whatever cutoff was last set.
            scene.build_scene("test-music")["script"],
            scene.checkpoint_actor(0, "sprite")["script"],
            scene.cable_end_actor(6, "sprite", "sfx")["script"],
            scene.junction_box_actor(7, "sprite", "sfx")["script"],
            scene.build_checkpoint_trigger("death", "connect")["script"],
        ]

        def sequences(events):
            yield events
            for event in events:
                for branch in event.get("children", {}).values():
                    yield from sequences(branch)

        checked = 0
        for script in scripts:
            for events in sequences(script):
                for i, event in enumerate(events):
                    if event["command"] == "EVENT_TEXT":
                        checked += 1
                        self.assertGreater(i, 0)
                        before = events[i - 1]
                        self.assertEqual(before["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                        self.assertEqual(before["args"]["y"]["value"], 150)
                        self.assertTrue(any(e["command"] == "EVENT_TEXT_DRAW" for e in events[i + 1:]),
                                        "HUD restored after text")
        self.assertGreaterEqual(checked, 8)

    @staticmethod
    def _texts(events):
        return [e["args"]["text"] for e in events if e["command"] == "EVENT_TEXT"]

    def test_init_resets_cable_and_line_on_every_entry(self):
        script = scene.build_scene("test-music")["script"]
        resets = [(e["args"]["variable"], e["args"]["value"]["value"])
                  for e in script if e["command"] == "EVENT_SET_VALUE"]
        self.assertEqual(resets, [("0", 0), ("6", 0), ("7", 0)])

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
        # Live Wire grid sprites take OBJ slot 2; no existing climb sprite may use it.
        self.assertNotIn(climb.GRID_SPRITE_PALETTE_SLOT, other_slots)
        self.assertEqual(climb.GRID_SPRITE_PALETTE_SLOT, 2)

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
        branch = self._checkpoint_branch(player_hit)["children"]
        self.assertEqual(branch["true"][0]["args"]["x"]["value"], climb.START[0])
        self.assertEqual(branch["false"][0]["args"]["y"]["value"], climb.HOUSE_A["y"])
        gust = scene.trigger_resource(1, climb.GUST_LANES[0], "death-sound")
        gust_branch = self._checkpoint_branch(gust["script"])["children"]
        self.assertEqual(gust_branch["false"][0]["args"]["x"]["value"], climb.HOUSE_A["x"])
        self.assertEqual(gust_branch["true"][0]["args"]["x"]["value"], climb.START[0])

    def test_checkpoint_trigger_keeps_stable_resource_id(self):
        self.assertEqual(self._checkpoint_trigger()["id"],
                         "b02fc406-5513-54f5-abd9-25c1adb2da51")

    def _all_scripts(self):
        """Every authored script list in the Storm Climb scene and its objects."""
        return [
            scene.build_scene("test-music")["script"],
            scene.build_scene("test-music")["playerHit1Script"],
            scene.checkpoint_actor(0, "sprite")["script"],
            scene.cable_end_actor(6, "sprite", "pickup")["script"],
            scene.junction_box_actor(7, "sprite", "connect")["script"],
            self._checkpoint_trigger()["script"],
            scene.trigger_resource(1, climb.GUST_LANES[0], "death-sound")["script"],
            scene.respawn_events("test-reset", "death-sound"),
        ]

    def test_every_storm_climb_dialogue_line_fits_limit(self):
        checked = 0
        for script in self._all_scripts():
            for entry in self._flatten(script):
                if entry["command"] != "EVENT_TEXT":
                    continue
                for line in entry["args"]["text"]:
                    for part in line.split("\n"):
                        self.assertLessEqual(len(part), scene.MAX_DIALOGUE_CHARS, part)
                        checked += 1
        self.assertGreaterEqual(checked, 15)

    def test_hud_uses_two_digit_variable_tokens_on_every_redraw(self):
        draws = [entry["args"]["text"] for script in self._all_scripts()
                 for entry in self._flatten(script) if entry["command"] == "EVENT_TEXT_DRAW"]
        self.assertTrue(draws, "HUD must be drawn")
        self.assertEqual(set(draws), {scene.HUD_TEXT})
        self.assertEqual(scene.HUD_TEXT, "LINE %D1$07$/1 HOME %D1$00$/1")
        tokens = re.findall(r"\$(\d+)\$", scene.HUD_TEXT)
        self.assertEqual(tokens, ["07", "00"])
        self.assertTrue(all(len(token) == 2 for token in tokens))

    def test_existing_actor_and_trigger_ids_are_unchanged(self):
        self.assertEqual(scene.build_scene("test-music")["id"],
                         "e8778f37-44a7-5d3a-ad39-49d52fe4c5c7")
        self.assertEqual(scene.checkpoint_actor(0, "s")["id"],
                         "0a208a0e-9313-59b7-be31-3be4c204ab2a")
        debris_ids = [scene.debris_actor(index, item, "s")["id"]
                      for index, item in enumerate(climb.HAZARD_DEBRIS, start=1)]
        self.assertEqual(debris_ids, [
            "e065f722-1457-5d3d-9e51-7208b614a0df",
            "894ce2e9-3c76-5793-887a-40e6496dc1e7",
            "ff2edd10-6c19-5348-b65f-badd72b3f151",
            "1975435b-c282-5c47-9cbe-9edae2c5e0b5",
        ])
        self.assertEqual(scene.timed_gust_actor(1, climb.GUST_LANES[0], "s")["id"],
                         "87bc8be0-aafb-5804-af87-3bd9a2efef96")
        self.assertEqual([t["id"] for t in scene.gust_marker_triggers("s")], [
            "3fe92e59-004f-5fcf-9aa2-808b4d935b52",
            "445eeab9-8c38-5f04-8850-7916aa2ac5c1",
            "0e782e08-57a1-5998-b79f-5691515f9ed3",
            "826886c2-8bae-5d07-adeb-6caf4835b440",
            "72eb2ec8-7234-5e9a-a6ef-fb1fb011084f",
            "e052fa35-c859-57dc-a8cd-55b6624a6981",
            "17ed159c-3f9b-51d8-b9ae-5daae23626a2",
            "b5d8455e-a64b-5abc-955e-e4b624739396",
        ])
        self.assertEqual(self._checkpoint_trigger()["id"],
                         "b02fc406-5513-54f5-abd9-25c1adb2da51")

    def test_street_exit_returns_to_opening_clear_of_start_and_hazards(self):
        trigger = scene.street_exit_trigger()
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         climb.STREET_EXIT)
        cutoff, hide, switch = trigger["script"]
        # Exact-ROM regression: the HUD cutoff survived the switch and hid the
        # opening's modal controls text, freezing input until A.
        self.assertEqual(cutoff["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        self.assertEqual(switch["command"], "EVENT_SWITCH_SCENE")
        self.assertEqual(switch["args"]["sceneId"], opening.resource_id("scene:service-opening"))
        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]),
                         opening.EXIT_NUDGE)
        # Respawning at START (16px-wide hero) must not overlap the exit column.
        self.assertGreater(climb.START[0], trigger["x"] + trigger["width"])
        ids = {t["id"] for t in scene.gust_marker_triggers("s")} | {self._checkpoint_trigger()["id"]}
        self.assertNotIn(trigger["id"], ids)

    def test_reentry_resets_live_wire_state_and_keeps_opening_progress(self):
        script = scene.build_scene("test-music")["script"]
        sets = {entry["args"]["variable"]: entry["args"]["value"]["value"]
                for entry in script if entry["command"] == "EVENT_SET_VALUE"}
        self.assertEqual(sets, {scene.VARIABLE_CHECKPOINTS_REACHED: 0,
                                scene.VAR_CARRYING_CABLE_ID: 0, scene.VAR_LINE_LIVE_ID: 0})
        written = {entry["args"]["variable"] for s in self._all_scripts()
                   for entry in self._flatten(s) if entry["command"] == "EVENT_SET_VALUE"}
        self.assertNotIn("4", written, "the climb must never clear Service Restored")

    def test_grid_sprite_sidecars_match_climb_ids_when_present(self):
        # The grid sprite sheets are generated separately; check them only if they exist.
        sprites = scene.PROJECT_DIR / "assets" / "sprites"

        def palette_indexes(node, found):
            if isinstance(node, dict):
                if "paletteIndex" in node:
                    found.add(node["paletteIndex"])
                for value in node.values():
                    palette_indexes(value, found)
            elif isinstance(node, list):
                for value in node:
                    palette_indexes(value, found)
            return found

        for pattern, sprite_key in (("*grid_cable_end*.gbsres", "sprite:grid_cable_end"),
                                    ("*grid_junction_box*.gbsres", "sprite:grid_junction_box")):
            for path in sorted(sprites.glob(pattern)):
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("_resourceType") != "sprite":
                    continue
                self.assertEqual(data["id"], climb.grid_resource_id(sprite_key), path.name)
                self.assertEqual(palette_indexes(data, set()), {climb.GRID_SPRITE_PALETTE_SLOT},
                                 path.name)

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
        self.assertEqual(commands[0]["command"], "EVENT_SOUND_PLAY_EFFECT")
        branch = self._checkpoint_branch(commands)["children"]
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
