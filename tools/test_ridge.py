"""Wind Ridge checks: python3 -m unittest discover -s tools -p test_ridge.py (or cd tools)."""
import json
import re
import unittest
from pathlib import Path

import climb
import intro
import make_climb_scene as shared
import make_ridge_scene as scene
import opening
import ridge
import rosa

# Hermetic fixtures: the builders only reference these IDs, so fixed strings
# keep the structural tests independent of which art sidecars exist yet.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"hazard": "hazard-sprite", "gust": "gust-sprite"}
PROJECT_DIR = scene.PROJECT_DIR


def built_scene():
    return scene.build_scene(FAKE_MUSIC, FAKE_AUDIO["death"])


def built_actors():
    return scene.build_actors(FAKE_SPRITES, FAKE_AUDIO)


def built_triggers():
    return scene.build_triggers(FAKE_AUDIO)


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def sequences(events):
    """Yield every sibling list, top level first, including branch children."""
    yield events
    for entry in events:
        for branch in entry.get("children", {}).values():
            yield from sequences(branch)


def all_script_lists():
    """Every authored script list reachable from the scene, actors and triggers."""
    lists = [built_scene()["script"], built_scene()["playerHit1Script"]]
    for actor in built_actors():
        lists.extend([actor["script"], actor["startScript"], actor["updateScript"],
                      actor["hit1Script"]])
    for trigger in built_triggers():
        lists.extend([trigger["script"], trigger["leaveScript"]])
    return lists


def actor_by_symbol(symbol):
    return next(a for a in built_actors() if a["symbol"] == symbol)


def trigger_by_symbol(symbol):
    return next(t for t in built_triggers() if t["symbol"] == symbol)


def decode_rle(text):
    """Independent decoder for the GB Studio collision RLE (value, then '!' or 'hex+')."""
    values, i = [], 0
    while i < len(text):
        value = int(text[i:i + 2], 16)
        i += 2
        if text[i] == "!":
            count, i = 1, i + 1
        else:
            end = text.index("+", i)
            count, i = int(text[i:end], 16), end + 1
        values.extend([value] * count)
    return values


def var_value(event):
    return event["args"]["value"]["value"]


def is_set(event, variable, value):
    return (event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == variable
            and var_value(event) == value)


def is_var_if(event, variable, value):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


class RidgeTests(unittest.TestCase):
    def test_ids_are_stable_and_unique(self):
        ids = {
            "scene": ridge.SCENE_ID,
            "background": ridge.BACKGROUND_ID,
            "tomas_sprite": ridge.TOMAS_SPRITE_ID,
            "concentrator_sprite": ridge.CONCENTRATOR_SPRITE_ID,
            "tomas_palette": scene.tomas_palette_id(),
            "trigger": ridge.resource_id("trigger:tomas-door"),
        }
        actor_ids = [a["id"] for a in built_actors()]
        ids.update({f"actor{i}": value for i, value in enumerate(actor_ids)})
        self.assertEqual(len(set(ids.values())), len(ids), "resource IDs collide")
        self.assertEqual(ids["scene"], ridge.resource_id("scene:wind-ridge"))
        self.assertEqual(ridge.resource_id("scene:wind-ridge"), ridge.SCENE_ID)
        self.assertNotEqual(ridge.resource_id("actor:tomas"), ridge.resource_id("trigger:tomas-door"))
        self.assertEqual(built_scene(), built_scene(), "scene build is deterministic")
        self.assertEqual(built_actors(), built_actors(), "actor build is deterministic")

    def test_event_ids_are_unique_within_the_scene(self):
        seen = []
        for script in all_script_lists():
            seen.extend(entry["id"] for entry in walk(script))
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)), "duplicate event ID inside wind_ridge")

    def test_scene_fields_match_wind_ridge_contract(self):
        resource = built_scene()
        self.assertEqual(resource["name"], "Wind Ridge")
        self.assertEqual(resource["symbol"], "scene_wind_ridge")
        self.assertEqual(resource["type"], "PLATFORM")
        self.assertEqual((resource["width"], resource["height"]), (40, 18))
        self.assertEqual(resource["backgroundId"], ridge.BACKGROUND_ID)
        self.assertEqual(resource["id"], ridge.SCENE_ID)
        self.assertEqual(resource["_resourceType"], "scene")
        self.assertEqual(resource["tilesetId"], "", "tilesets are not used by this job")
        self.assertIn((resource["x"], resource["y"]), [(400, 360)])
        taken = []
        for path in (PROJECT_DIR / "project" / "scenes").glob("*/scene.gbsres"):
            if path.parent.name != "wind_ridge":
                taken.append((shared.load_json(path)["_index"], shared.load_json(path)["x"],
                              shared.load_json(path)["y"]))
        self.assertNotIn((resource["_index"], resource["x"], resource["y"]), taken,
                         "editor index and position must be free")

    def test_collisions_match_contract(self):
        resource = built_scene()
        self.assertEqual(decode_rle(resource["collisions"]),
                         [cell for row in ridge.collision_grid() for cell in row])
        self.assertEqual(
            shared.collision_rle(ridge.collision_grid(), 40, 18),
            resource["collisions"],
        )

    def test_variables_register_without_changing_existing(self):
        base = shared.load_json(PROJECT_DIR / "project" / "variables.gbsres")
        merged = scene.merged_variables(base)
        self.assertEqual(scene.merged_variables(merged), merged, "registration is idempotent")
        self.assertEqual(merged["variables"][:len(base["variables"])], base["variables"])
        by_id = {v["id"]: v for v in merged["variables"]}
        self.assertEqual(by_id[ridge.VAR_LINE_LIVE],
                         {"id": "8", "name": "Ridge Line Live", "symbol": "var_ridge_line_live"})
        self.assertEqual(by_id[ridge.VAR_HOME_POWERED],
                         {"id": "9", "name": "Tomas Home Powered", "symbol": "var_tomas_home_powered"})
        self.assertEqual(by_id["6"]["symbol"], "var_carrying_cable")
        self.assertEqual(by_id["7"]["symbol"], "var_line_live")

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(8)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:8], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]], [str(i) for i in range(10)])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "8", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_line(self):
        script = built_scene()["script"]
        for variable in ("6", "8", "9"):
            self.assertTrue(any(is_set(e, variable, 0) for e in script),
                            f"init must reset var {variable}")
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "4"
                             for e in script), "init must not reset Service Restored")
        commands = [e["command"] for e in script]
        self.assertEqual(commands[:2], ["EVENT_PLAYER_SET_SPRITE", "EVENT_ACTOR_SET_DIRECTION"])
        self.assertEqual(script[0]["args"]["spriteSheetId"],
                         opening.resource_id("sprite:opening_worker24"))
        self.assertEqual(script[1]["args"]["direction"]["value"], "right")
        palette_events = [e for e in script if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertEqual(palette_events[0]["args"][f"palette{ridge.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:window"))
        self.assertEqual(palette_events[1]["args"][f"palette{ridge.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_dead"))
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        intro = next(e for e in script if e["command"] == "EVENT_TEXT")
        self.assertEqual(intro["args"]["text"], ["Hiroshi needs his\noxygen machine!"])

    def test_every_in_play_text_is_preceded_by_cutoff_and_followed_by_hud(self):
        checked = 0
        for script in all_script_lists():
            for events in sequences(script):
                for i, entry in enumerate(events):
                    if entry["command"] != "EVENT_TEXT":
                        continue
                    checked += 1
                    self.assertGreater(i, 0, "text cannot be the first event of a list")
                    before = events[i - 1]
                    self.assertEqual(before["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                    self.assertEqual(before["args"]["y"]["value"], 150)
                    redraws = [e for e in events[i + 1:] if e["command"] == "EVENT_TEXT_DRAW"]
                    self.assertTrue(redraws, "HUD must be redrawn after text")
                    self.assertEqual(redraws[0]["args"]["text"], ridge.HUD_TEXT)
        # Authored in-play texts: init intro, Hiroshi x3, cable pickup, junction x3, door x2.
        self.assertEqual(checked, 11)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(ridge.HUD_TEXT, "LINE %D1$08$/1 HOME %D1$09$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws, {ridge.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", ridge.HUD_TEXT)
        self.assertEqual(tokens, ["08", "09"])
        self.assertTrue(all(len(token) == 2 for token in tokens))

    def test_every_dialogue_line_fits_the_limit(self):
        self.assertEqual(scene.MAX_DIALOGUE_CHARS, 17)
        checked = 0
        for script in all_script_lists():
            for entry in walk(script):
                if entry["command"] != "EVENT_TEXT":
                    continue
                for line in entry["args"]["text"]:
                    for part in line.split("\n"):
                        self.assertLessEqual(len(part), scene.MAX_DIALOGUE_CHARS, part)
                        checked += 1
        # One line per in-play text, two-line boxes count each part. Hiroshi names 4 boxes.
        self.assertEqual(checked, 25)

    def test_cable_drop_runs_before_respawn_in_player_hit(self):
        hit = built_scene()["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT", "death sound plays first")
        drop = next(i for i, e in enumerate(hit)
                    if is_var_if(e, ridge.VAR_CARRYING_CABLE, 1))
        respawn = next(i for i, e in enumerate(hit) if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        self.assertLess(drop, respawn)
        drop_events = hit[drop]["children"]["true"]
        self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 0) for e in drop_events))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_SHOW" and
                            e["args"]["actorId"] == scene.actor_id(scene.CABLE_KEY)
                            for e in drop_events))
        flat = list(walk(hit))
        first_move = next(i for i, e in enumerate(flat) if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertGreater(first_move, 0)

    def test_respawn_goes_to_start_before_power_and_to_door_after(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        start = branch["children"]["true"][0]
        self.assertEqual(start["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((start["args"]["x"]["value"], start["args"]["y"]["value"]), ridge.START)
        door = branch["children"]["false"][0]
        door_x, door_y = ridge.HOUSE_DOOR
        self.assertEqual((door["args"]["x"]["value"], door["args"]["y"]["value"]),
                         (door_x - 1, door_y), "respawn stands in front of the door")

    def test_door_is_gated_on_live_line_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         ridge.DOOR_TRIGGER)
        script = trigger["script"]
        line = next(e for e in script if is_var_if(e, ridge.VAR_LINE_LIVE, 1))
        power = next(e for e in line["children"]["true"] if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        reward = power["children"]["true"]
        self.assertTrue(any(is_set(e, ridge.VAR_HOME_POWERED, 1) for e in reward))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" for e in reward))
        window = next(e for e in reward if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(window["args"][f"palette{ridge.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:powered_window"))
        states = {(e["args"]["actorId"], e["args"]["spriteStateId"])
                  for e in reward if e["command"] == "EVENT_ACTOR_SET_STATE"}
        self.assertEqual(states, {(scene.actor_id(scene.TOMAS_KEY), "Relieved"),
                                  (scene.actor_id(scene.CONCENTRATOR_KEY), "On")})
        self.assertIn("Hiroshi:\nPower's on!\nI can breathe.", [
            e["args"]["text"] for e in reward if e["command"] == "EVENT_TEXT"][0])
        dead = line["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Still no power.\nFix the line!"]])
        # Only the door's reward writes var 9 to 1; init writes 0 and nothing else touches it.
        writers_to_one = [e for script in all_script_lists() for e in walk(script)
                          if e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "9"
                          and var_value(e) == 1]
        self.assertEqual([e["id"] for e in writers_to_one],
                         [e["id"] for e in walk(reward) if is_set(e, ridge.VAR_HOME_POWERED, 1)])

    def test_gust_start_delays_are_distinct_and_run_once(self):
        self.assertEqual(len(ridge.GUST_START_DELAYS), len(ridge.GUST_LANES))
        self.assertEqual(len(set(ridge.GUST_START_DELAYS)), len(ridge.GUST_START_DELAYS))
        gusts = [a for a in built_actors() if a["symbol"].startswith("ridge_gust_")]
        self.assertEqual(len(gusts), len(ridge.GUST_LANES))
        for gust, lane, delay in zip(gusts, ridge.GUST_LANES, ridge.GUST_START_DELAYS):
            row, x0, _ = lane
            self.assertEqual((gust["x"], gust["y"]), (x0, row))
            self.assertEqual(gust["collisionGroup"], "1")
            self.assertEqual(gust["spriteSheetId"], FAKE_SPRITES["gust"])
            update = gust["updateScript"]
            guard = update[0]
            self.assertEqual(guard["command"], "EVENT_IF_ACTOR_DIRECTION")
            self.assertEqual(guard["args"]["direction"]["value"], "down")
            waits = [e for e in walk(guard["children"]["true"]) if e["command"] == "EVENT_WAIT"]
            if delay:
                self.assertEqual([w["args"]["frames"]["value"] for w in waits], [delay])
            else:
                self.assertEqual(waits, [])
            # Only the first-cycle branch may hold the start delay; the loop waits are the climb's.
            loop_waits = [e["args"]["frames"]["value"] for e in update[1:]
                          if e["command"] == "EVENT_WAIT"]
            self.assertEqual(loop_waits, [ridge.GUST_WARNING_FRAMES, ridge.GUST_ACTIVE_FRAMES,
                                          ridge.GUST_REST_FRAMES])
            states = [e["args"]["spriteStateId"] for e in update
                      if e["command"] == "EVENT_ACTOR_SET_STATE"]
            self.assertEqual(states, ["Warning", "Burst"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_COLLISIONS_ENABLE"
                                 for e in walk(guard["children"]["true"])),
                             "start delay must not enable the hazard early")
        self.assertEqual([g["_index"] for g in gusts], [len(built_actors()) - 2, len(built_actors()) - 1])  # the storm pole sits before the cable end

    def test_hill_exit_leads_to_signal_hill_only_after_tomas_is_powered(self):
        trigger = trigger_by_symbol("trigger_ridge_hill_exit")
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         rosa.RIDGE_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "9"})
        cutoff, hide, switch = gate["children"]["true"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        self.assertEqual(switch["args"]["sceneId"], rosa.SCENE_ID)
        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), rosa.START)
        # The refusal never moves the hero: a nudge re-entered the summit exit and looped.
        refused = gate["children"]["false"]
        self.assertNotIn("EVENT_ACTOR_SET_POSITION", [e["command"] for e in walk(refused)])
        self.assertEqual(refused[0]["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
        # Standing on the porch at the exit is clear of Hiroshi's door trigger.
        tx, _, tw, _ = ridge.DOOR_TRIGGER
        self.assertGreaterEqual(trigger["x"], tx + tw)
        grid = ridge.collision_grid()
        self.assertTrue(all(grid[r][trigger["x"]] == ridge.COL_EMPTY
                            for r in range(trigger["y"], trigger["y"] + trigger["height"])))

    def _scanline_load(self, hero_x, hero_feet):
        """OBJ columns per tile row on the 20-tile screen centred on the hero."""
        sprites = [((hero_x, hero_feet), 3, 3)]  # hero: 24px wide, 24px tall
        sprites += [(ridge.TOMAS, 2, 3)]          # Hiroshi: 24px figure on a 16x32 canvas
        sprites += [(pos, 2, 2) for pos in (ridge.JUNCTION_BOX, ridge.CONCENTRATOR)]
        sprites += [((x0, row), 3, 2) for row, x0, _ in ridge.GUST_LANES]
        # Storm pole (2x4 intro sprite) and cable end (2x2) share the pickup's tile.
        sprites += [(ridge.DAMAGED_POLE, 2, 4), (ridge.DAMAGED_POLE, 2, 2)]
        left = hero_x - 10
        load = {}
        for (x, feet), width, height in sprites:
            if x + width <= left or x >= left + 20:
                continue  # off screen: not drawn
            for row in range(feet - height + 1, feet + 1):
                load[row] = load.get(row, 0) + width
        return load

    def test_house_view_stays_within_ten_sprites_per_scanline(self):
        # Exact ROM e05b693c showed the concentrator losing its top half when
        # the house props shared the gusts' rows (13 8x16 OBJs on one line).
        # Count OBJ columns per tile row with the hero standing at the box and
        # every on-screen gust visible; debris passes through briefly and is excluded.
        load = self._scanline_load(*ridge.JUNCTION_BOX)
        self.assertLessEqual(max(load.values()), 10, load)

    def test_pole_view_stays_within_ten_sprites_per_scanline(self):
        load = self._scanline_load(*ridge.DAMAGED_POLE)
        self.assertLessEqual(max(load.values()), 10, load)

    def test_debris_and_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        self.assertEqual(symbols, [
            scene.TOMAS_SYMBOL, scene.CONCENTRATOR_SYMBOL, scene.POLE_SYMBOL, scene.CABLE_SYMBOL,
            scene.JUNCTION_SYMBOL, "ridge_debris_01", "ridge_gust_01", "ridge_gust_02",
        ])
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        tomas = actor_by_symbol(scene.TOMAS_SYMBOL)
        self.assertEqual((tomas["x"], tomas["y"]), ridge.TOMAS)
        self.assertEqual(tomas["spriteSheetId"], ridge.TOMAS_SPRITE_ID)
        self.assertEqual(tomas["startScript"][0]["args"]["spriteStateId"], "Waiting")
        self.assertTrue(tomas["animate"])
        self.assertEqual(tomas["collisionGroup"], "")
        conc = actor_by_symbol(scene.CONCENTRATOR_SYMBOL)
        self.assertEqual((conc["x"], conc["y"]), ridge.CONCENTRATOR)
        self.assertEqual(conc["spriteSheetId"], ridge.CONCENTRATOR_SPRITE_ID)
        self.assertEqual(conc["startScript"][0]["args"]["spriteStateId"], "Off")
        cable = actor_by_symbol(scene.CABLE_SYMBOL)
        self.assertEqual((cable["x"], cable["y"]), ridge.DAMAGED_POLE)
        self.assertEqual(cable["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
        self.assertEqual(cable["startScript"][0]["args"]["spriteStateId"], "Dangling")
        junction = actor_by_symbol(scene.JUNCTION_SYMBOL)
        self.assertEqual((junction["x"], junction["y"]), ridge.JUNCTION_BOX)
        self.assertEqual(junction["spriteSheetId"], climb.grid_resource_id("sprite:grid_junction_box"))
        self.assertEqual(junction["startScript"][0]["args"]["spriteStateId"], "Dead")
        debris = actor_by_symbol("ridge_debris_01")
        self.assertEqual(debris["collisionGroup"], "1")
        self.assertEqual((debris["x"], debris["y"]), (ridge.HAZARD_DEBRIS[0]["x"],
                                                     ridge.HAZARD_DEBRIS[0]["row_top"]))
        self.assertEqual(debris["spriteSheetId"], FAKE_SPRITES["hazard"])
        self.assertEqual(len(actors), 8, "keep the actor count modest")

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual(pole["id"], scene.actor_id("pole"))
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertEqual((pole["x"], pole["y"]), ridge.DAMAGED_POLE)
        self.assertTrue(pole["animate"])
        self.assertEqual(pole["script"], [], "pole is not interactive")
        self.assertEqual(pole["collisionGroup"], "", "pole does not collide")
        self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE",
                         "B must find the cable end on the pole's tile (B-13)")
        start = pole["startScript"][1]
        self.assertTrue(is_var_if(start, ridge.VAR_LINE_LIVE, 1))
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["true"]], [("$self$", "Standing")])
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["false"]], [("$self$", "Snapped")])
        init = built_scene()["script"]
        self.assertIn((scene.pole_actor_id(), "Snapped"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_tomas_talk_tracks_power_and_line(self):
        script = actor_by_symbol(scene.TOMAS_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], ridge.VAR_HOME_POWERED, 1))
        self.assertEqual([e["args"]["text"] for e in script[0]["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Hiroshi:\nThanks, friend!\nBreathing easy."]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], ridge.VAR_LINE_LIVE, 1))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in live if e["command"] == "EVENT_TEXT"],
                         [["Hiroshi:\nLine's live!\nTry my door."]])
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Hiroshi:\nThe line's dead!\nMy machine's off."]])

    def test_junction_plugs_carried_cable_once_and_lights_slot_five(self):
        script = actor_by_symbol(scene.JUNCTION_SYMBOL)["script"]
        live = next(e for e in script if is_var_if(e, ridge.VAR_LINE_LIVE, 1))
        has_cable = next(e for e in live["children"]["false"] if is_var_if(e, ridge.VAR_CARRYING_CABLE, 1))
        branch = has_cable["children"]["true"]
        self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 0) for e in branch))
        self.assertTrue(any(is_set(e, ridge.VAR_LINE_LIVE, 1) for e in branch))
        palette = next(e for e in branch if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(palette["args"][f"palette{ridge.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_live"))
        self.assertEqual(set(k for k, v in palette["args"].items() if v != "keep"),
                         {f"palette{ridge.LINE_BG_SLOT}"})
        states = [(e["args"]["actorId"], e["args"]["spriteStateId"])
                  for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"]
        self.assertEqual(states, [("$self$", "Live"), (scene.pole_actor_id(), "Standing")])

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        script = actor_by_symbol(scene.CABLE_SYMBOL)["script"]
        empty = script[0]
        self.assertTrue(is_var_if(empty, ridge.VAR_CARRYING_CABLE, 0))
        dead = next(e for e in empty["children"]["true"] if is_var_if(e, ridge.VAR_LINE_LIVE, 0))
        self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 1) for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                            e["args"]["type"] == FAKE_AUDIO["pickup"]
                            for e in dead["children"]["true"]))

    def test_checked_in_files_match_the_builders(self):
        """Run after make_ridge_scene.py: disk must match the in-memory build."""
        music = shared.sidecar_id(scene.MUSIC_SIDECAR, "music")
        audio = {
            "death": shared.sidecar_id(scene.DEATH_SOUND, "sound"),
            "connect": shared.sidecar_id(scene.CONNECT_SOUND, "sound"),
            "pickup": shared.sidecar_id(scene.PICKUP_SOUND, "sound"),
        }
        sprites = {
            "hazard": shared.sidecar_id(scene.DEBRIS_SPRITE, "sprite"),
            "gust": shared.sidecar_id(scene.GUST_SPRITE, "sprite"),
        }
        expected = scene.build_scene(music, audio["death"])
        self.assertEqual(shared.load_json(scene.SCENE_DIR / "scene.gbsres"), expected)
        for actor in scene.build_actors(sprites, audio):
            path = scene.SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), actor)
        for trigger in scene.build_triggers(audio):
            path = scene.SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), trigger)
        for relative, palette in scene.tomas_palettes():
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), palette)

    def test_palette_slots_and_tomas_palette(self):
        resource = built_scene()
        template = shared.load_json(scene.CLIMB_SCENE)
        sprites = resource["spritePaletteIds"]
        self.assertEqual(len(sprites), 8)
        self.assertEqual(sprites[0], opening.resource_id("palette:sprite:worker"))
        self.assertEqual(sprites[1], scene.tomas_palette_id())
        self.assertEqual(sprites[2], climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(sprites[shared.POLE_SPRITE_PALETTE_SLOT], intro.palette_id("pole"))
        self.assertEqual(sprites[4:], template["spritePaletteIds"][4:])
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[5], climb.grid_resource_id("palette:bg:metal_dead"))
        self.assertEqual(backgrounds[7], "default-ui")
        palette = scene.tomas_palettes()[0][1]
        self.assertEqual(palette["id"], scene.tomas_palette_id())
        self.assertEqual(palette["colors"], [
            ridge.TOMAS_SPRITE_HARDWARE[1], ridge.TOMAS_SPRITE_HARDWARE[2],
            ridge.TOMAS_SPRITE_HARDWARE[3], ridge.TOMAS_SPRITE_HARDWARE[3],
        ])
        self.assertEqual(ridge.TOMAS_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(ridge.GRID_SPRITE_PALETTE_SLOT, 2)

    def test_shared_sidecars_exist(self):
        """Sounds, music and the climb-owned sprites are already on disk; Hiroshi art is not required."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.DEBRIS_SPRITE, scene.GUST_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
