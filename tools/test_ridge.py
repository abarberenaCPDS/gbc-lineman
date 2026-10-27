"""Wind Ridge checks: python3 -m unittest discover -s tools -p test_ridge.py (or cd tools)."""
import json
import re
import unittest
from pathlib import Path

import climb
import grid_chain
import tickets
import hazards
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
FAKE_SPRITES = {"gust": "gust-sprite", "arc": "arc-sprite"}
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


def texts(events):
    return [e["args"]["text"] for e in walk(events) if e["command"] == "EVENT_TEXT"]


def positions(events):
    return [(e["args"]["x"]["value"], e["args"]["y"]["value"])
            for e in walk(events) if e["command"] == "EVENT_ACTOR_SET_POSITION"]


LINES = scene.LINES
HOUSE_LINE = scene.LINE_BY_KEY["house"]


def is_at_least(event, variable, value):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == "gte"
            and condition["valueA"]["value"] == variable and condition["valueB"]["value"] == value)


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
        self.assertEqual((resource["width"], resource["height"]), (100, 30))
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
            shared.collision_rle(ridge.collision_grid(), ridge.MAP_W, ridge.MAP_H),
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
        self.assertEqual(by_id[ridge.VAR_FEEDER_LIVE],
                         {"id": "17", "name": "Ridge Feeder Live", "symbol": "var_ridge_feeder_live"})
        self.assertEqual(by_id[ridge.VAR_LINES_LIVE],
                         {"id": "18", "name": "Ridge Lines Live", "symbol": "var_ridge_lines_live"})
        self.assertEqual(by_id[hazards.VAR_ON_BOARD],
                         {"id": "15", "name": "On Cracked Board", "symbol": "var_on_cracked_board"})
        self.assertEqual(by_id["6"]["symbol"], "var_carrying_cable")
        self.assertEqual(by_id["7"]["symbol"], "var_line_live")

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(8)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:8], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(10)] + ["17", "18", "19", "20", hazards.VAR_ON_BOARD])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "8", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_line(self):
        script = built_scene()["script"]
        for variable in ("6", "8", "9", "17", "18", "19", "20"):
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
        # Both lines start dead: the init's palette chain resolves to dead/dead.
        lines = [e for e in walk(script) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"
                 and e["args"][f"palette{ridge.LINE_BG_SLOT}"] != "keep"]
        self.assertEqual({e["args"][f"palette{ridge.LINE_BG_SLOT}"] for e in lines},
                         {scene.chain_palette_id(n) for n in range(len(LINES) + 1)})
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        self.assertEqual(texts(script), [["Hiroshi needs his\noxygen machine!"],
                                         ["Three lines down.\nOne cable a trip."]])

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
        # Init x2, Hiroshi x3, 3 x (pickup + hands full), 3 x box (already, all, lit,
        # dark, no cable, wrong), door x2, CLOSED box, hill exit refusal, and each
        # box's reach trigger repeats its status lines (all, lit, dark) once per line.
        self.assertEqual(checked, 42)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(ridge.HUD_TEXT, "LINE %D1$18$/3 HOME %D1$09$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws - {intro.dev_label()} - {None}, {ridge.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", ridge.HUD_TEXT)
        self.assertEqual(tokens, ["18", "09"])
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
        self.assertEqual(checked, 85)  # 67 + the reach triggers' status lines (speaker lines included)

    def test_cable_drop_runs_before_respawn_in_player_hit(self):
        hit = built_scene()["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT", "death sound plays first")
        respawn = next(i for i, e in enumerate(hit) if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        for line in LINES:
            drop = next(i for i, e in enumerate(hit) if is_var_if(e, ridge.VAR_CARRYING_CABLE, line["number"]))
            self.assertLess(drop, respawn)
            drop_events = hit[drop]["children"]["true"]
            self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 0) for e in drop_events))
            # Each cable falls back to its own pole.
            self.assertEqual([e["args"]["actorId"] for e in drop_events if e["command"] == "EVENT_ACTOR_SHOW"],
                             [scene.actor_id(line["cable"])])

    def test_respawn_uses_the_furthest_repaired_line(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        door_x, door_y = ridge.HOUSE_DOOR
        self.assertEqual(positions(branch["children"]["false"]), [(door_x - 1, door_y)])
        current = branch["children"]["true"]
        for line in reversed(LINES):
            [check] = current
            self.assertTrue(is_var_if(check, line["live_var"], 1), line["key"])
            self.assertEqual(positions(check["children"]["true"]), [line["checkpoint"]])
            current = check["children"]["false"]
        self.assertEqual(positions(current), [ridge.START])

    def test_door_is_gated_on_live_line_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         ridge.DOOR_TRIGGER)
        script = trigger["script"]
        line = next(e for e in script if is_var_if(e, ridge.VAR_LINES_LIVE, ridge.LINE_COUNT))
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
                         [["Still no power.\nFix every line!"]])
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
        # The board draws last.
        self.assertEqual(built_actors()[-1]["symbol"], "ridge_board_01")

    def test_hill_exit_leads_to_signal_hill_only_after_tomas_is_powered(self):
        trigger = trigger_by_symbol("trigger_ridge_hill_exit")
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         rosa.RIDGE_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "9"})
        cutoff, hide, ticket, switch = gate["children"]["true"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        # Work order 3 first; its card then switches to the next job's start.
        self.assertEqual((ticket["args"]["variable"], ticket["args"]["value"]["value"]),
                         (tickets.VAR_TICKET, 3))
        self.assertEqual(switch["args"]["sceneId"], tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(tickets.TICKETS[3]["scene_id"], rosa.SCENE_ID)
        self.assertEqual(tickets.TICKETS[3]["start"], rosa.START)
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

    def _on_screen_sprites(self):
        """(feet tile, OBJ columns, OBJ tile rows) for every actor that can be visible."""
        sprites = [(ridge.TOMAS, 2, 3)]          # Hiroshi: 24px figure on a 16x32 canvas
        sprites += [(ridge.CONCENTRATOR, 2, 2)]
        sprites += grid_chain.chain_sprites(LINES)
        sprites += [((x0, row), 3, 2) for row, x0, _ in ridge.GUST_LANES]
        sprites += [((x0, row), 2, 2) for row, x0, _ in ridge.span_arc_lanes()]
        sprites += [((x0, row + 1), 2, 4) for row, x0, _ in ridge.WHIP_LANES]
        sprites += [(hazards.board_actor_position(board), 3, 2) for board in hazards.BOARDS["wind_ridge"]]
        return sprites

    def _scanline_load(self, hero_x, hero_feet):
        """OBJ columns per tile row on the screen around the hero."""
        return grid_chain.scanline_load(self._on_screen_sprites(), ridge.MAP_W, hero_x, hero_feet)

    def _spots(self):
        spots = [ridge.START, ridge.HOUSE_DOOR]
        for line in LINES:
            spots += [line["pole_at"], line["box_at"], line["checkpoint"]]
        spots += [(x0, row + 1) for row, x0, _ in ridge.hazard_lanes()]
        return spots

    def test_every_view_stays_within_ten_sprites_per_scanline(self):
        # Exact ROM e05b693c showed the concentrator losing its top half when
        # the house props shared the gusts' rows (13 8x16 OBJs on one line).
        for spot in self._spots():
            load = self._scanline_load(*spot)
            self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (spot, load))

    def test_every_view_stays_within_the_active_actor_limit(self):
        # gbvm runs at most 12 actors at once, the player included. Count actors
        # within a screen plus two tiles each side of every spot.
        for hero_x, _ in self._spots():
            near = grid_chain.actors_near(self._on_screen_sprites(), ridge.MAP_W, hero_x)
            # Pole and cable end share a tile but are two actors; count entries, not tiles.
            self.assertLessEqual(len(near), ridge.MAX_ACTIVE_ACTORS, (hero_x, near))

    def test_debris_and_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        expected = [scene.TOMAS_SYMBOL, scene.CONCENTRATOR_SYMBOL]
        for line in LINES:
            expected += [line["pole_symbol"], line["cable_symbol"], line["box_symbol"]]
        expected += ["ridge_gust_01", "ridge_gust_02", "ridge_span_arc_01", "ridge_span_arc_02",
                     "ridge_whip_01", "ridge_whip_02", "ridge_board_01"]
        self.assertEqual(symbols, expected)
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertLessEqual(len(actors), ridge.MAX_SCENE_ACTORS, "gbvm allows 20 actors besides the player")
        self.assertEqual(len(actors), ridge.actor_count())
        tomas = actor_by_symbol(scene.TOMAS_SYMBOL)
        self.assertEqual((tomas["x"], tomas["y"]), ridge.TOMAS)
        self.assertEqual(tomas["spriteSheetId"], ridge.TOMAS_SPRITE_ID)
        self.assertEqual(tomas["startScript"][0]["args"]["spriteStateId"], "Waiting")
        conc = actor_by_symbol(scene.CONCENTRATOR_SYMBOL)
        self.assertEqual((conc["x"], conc["y"]), ridge.CONCENTRATOR)
        self.assertEqual(conc["startScript"][0]["args"]["spriteStateId"], "Off")
        for line in LINES:
            cable = actor_by_symbol(line["cable_symbol"])
            pole = actor_by_symbol(line["pole_symbol"])
            box = actor_by_symbol(line["box_symbol"])
            self.assertEqual((cable["x"], cable["y"]), line["pole_at"])
            self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
            self.assertEqual((box["x"], box["y"]), line["box_at"])
            self.assertEqual(cable["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
            self.assertEqual(box["spriteSheetId"], ridge.TRANSFORMER_SPRITE_ID if line["box_kind"] == "transformer"
                             else climb.grid_resource_id("sprite:grid_junction_box"))
            self.assertEqual(box["startScript"][0]["args"]["spriteStateId"], "Dead")
            # Each cable end out-ranks its pole so it draws on top (B-13).
            self.assertGreater(symbols.index(line["cable_symbol"]), symbols.index(line["pole_symbol"]))
        self.assertFalse([a for a in actors if "debris" in a["symbol"]])

    def test_cracked_board_sits_on_the_floor_with_group_one(self):
        board = hazards.BOARDS["wind_ridge"][0]
        actor = actor_by_symbol("ridge_board_01")
        self.assertEqual((actor["x"], actor["y"]), hazards.board_actor_position(board))
        self.assertEqual(actor["spriteSheetId"], hazards.BOARD_SPRITE_ID)
        self.assertEqual(actor["collisionGroup"], "1")
        self.assertEqual(actor["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        self.assertEqual(actor["startScript"][1]["args"]["spriteStateId"], "Idle")
        ifs = [e for e in actor["updateScript"] if e["command"] == "EVENT_IF"]
        self.assertEqual(ifs[0]["args"]["condition"]["valueB"]["value"], 1)
        # Floor boards: the plank row is ground and the standing row above it is clear.
        grid = ridge.collision_grid()
        row, x0, x1 = board
        self.assertTrue(all(grid[row][x] == ridge.COL_SOLID for x in range(x0, x1 + 1)))
        self.assertTrue(all(grid[row - 1][x] == ridge.COL_EMPTY for x in range(x0, x1 + 1)))

    def test_cracked_board_trigger_is_after_the_hill_exit_and_door(self):
        triggers = scene.build_triggers(FAKE_AUDIO)
        board = next(t for t in triggers if t["symbol"] == "trigger_ridge_cracked_board_01")
        self.assertEqual((board["x"], board["y"], board["width"], board["height"]),
                         hazards.board_trigger_rect(hazards.BOARDS["wind_ridge"][0]))
        self.assertEqual(board["script"][0]["args"]["value"]["value"], 1)
        self.assertEqual(board["leaveScript"][0]["args"]["value"]["value"], 0)
        # The exit and the door come first; the box reach triggers sit after the boards.
        exits = [t["_index"] for t in triggers
                 if t["symbol"] in ("trigger_ridge_hill_exit", scene.DOOR_TRIGGER_SYMBOL)]
        self.assertTrue(all(board["_index"] > index for index in exits))
        self.assertEqual(hazards.VAR_ON_BOARD, "15")

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual(pole["id"], scene.actor_id("pole"))
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertEqual((pole["x"], pole["y"]), HOUSE_LINE["pole_at"])
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

    def test_every_pole_starts_snapped_unless_its_line_is_live(self):
        init = built_scene()["script"]
        snapped = [(e["args"]["actorId"], e["args"]["spriteStateId"])
                   for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"]
        for line in LINES:
            pole = actor_by_symbol(line["pole_symbol"])
            self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
            self.assertEqual(pole["script"], [])
            self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
            self.assertTrue(is_var_if(pole["startScript"][1], line["live_var"], 1))
            self.assertIn((pole["id"], "Snapped"), snapped)

    def test_tomas_talk_tracks_power_and_every_line(self):
        script = actor_by_symbol(scene.TOMAS_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], ridge.VAR_HOME_POWERED, 1))
        self.assertEqual(texts(script[0]["children"]["true"]),
                         [["Hiroshi:\nThanks, friend!\nBreathing easy."]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], ridge.VAR_LINES_LIVE, ridge.LINE_COUNT))
        self.assertEqual(texts(otherwise[0]["children"]["true"]), [["Hiroshi:\nLine's live!\nTry my door."]])
        self.assertEqual(texts(otherwise[0]["children"]["false"]),
                         [["Hiroshi:\nThe line's dead!\nMy machine's off."]])

    def test_each_box_takes_only_its_own_cable_and_counts_the_line(self):
        for line in LINES:
            script = actor_by_symbol(line["box_symbol"])["script"]
            live = next(e for e in script if is_var_if(e, line["live_var"], 1))
            self.assertEqual(texts(live["children"]["true"]), [["Already fixed."]])
            has_cable = next(e for e in live["children"]["false"]
                             if is_var_if(e, ridge.VAR_CARRYING_CABLE, line["number"]))
            branch = has_cable["children"]["true"]
            self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 0) for e in branch))
            self.assertTrue(any(is_set(e, line["live_var"], 1) for e in branch))
            self.assertEqual([e["args"]["variable"] for e in branch if e["command"] == "EVENT_INC_VALUE"],
                             [ridge.VAR_LINES_LIVE])
            self.assertIn((scene.actor_id(line["pole"]), "Standing"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"])
            # Only slot 5 changes, to a chain palette.
            for palette in (e for e in walk(branch) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"):
                self.assertEqual({k for k, v in palette["args"].items() if v != "keep"},
                                 {f"palette{ridge.LINE_BG_SLOT}"})
            [other] = has_cable["children"]["false"]
            self.assertTrue(is_var_if(other, ridge.VAR_CARRYING_CABLE, 0))
            self.assertEqual(texts(other["children"]["true"]), [["No cable yet.\nFind its pole."]])
            self.assertEqual(texts(other["children"]["false"]), [["Wrong cable\nfor this box."]])
        incs = [e for script in all_script_lists() for e in walk(script) if e["command"] == "EVENT_INC_VALUE"]
        # Each box and its reach trigger share one connect path: two counts per line, nothing else.
        self.assertEqual(len(incs), 2 * ridge.LINE_COUNT, "nothing else changes the counter")

    def test_power_reaches_a_box_only_through_every_line_upstream(self):
        for line in LINES:
            script = actor_by_symbol(line["box_symbol"])["script"]
            plugged = next(e for e in walk(script) if is_var_if(e, ridge.VAR_CARRYING_CABLE, line["number"])
                           and e["children"]["true"])["children"]["true"]
            commands = [e["command"] for e in plugged]
            # The chain refresh (which sets VAR_CHAIN_LIVE) runs before the message reads it.
            refresh = next(i for i, e in enumerate(plugged)
                           if any(is_set(x, ridge.VAR_CHAIN_LIVE, 0) for x in walk([e])))
            message = plugged[-1]
            self.assertLess(refresh, len(commands) - 1)
            self.assertTrue(is_var_if(message, ridge.VAR_CHAIN_LIVE, ridge.LINE_COUNT))
            self.assertEqual(texts(message["children"]["true"]), [["All lines live!\nGo see Hiroshi."]])
            [lit] = message["children"]["false"]
            self.assertTrue(is_at_least(lit, ridge.VAR_CHAIN_LIVE, line["number"]))
            self.assertEqual(texts(lit["children"]["true"]), [["Power flows on!\nKeep going."]])
            self.assertEqual(texts(lit["children"]["false"]), [["Fixed. No power\nfrom upstream."]])

    def test_chain_lights_wires_and_boxes_only_as_far_as_continuous(self):
        refresh = scene.chain_refresh_events("probe")

        def outcome(live):
            events = refresh
            while len(events) == 1 and events[0]["command"] == "EVENT_IF":
                variable = events[0]["args"]["condition"]["valueA"]["value"]
                events = events[0]["children"]["true" if live[variable] else "false"]
            palette = next(e["args"][f"palette{ridge.LINE_BG_SLOT}"] for e in events
                           if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
            stages_set = next(var_value(e) for e in events if e["command"] == "EVENT_SET_VALUE"
                              and e["args"]["variable"] == ridge.VAR_CHAIN_LIVE)
            boxes = {e["args"]["actorId"]: e["args"]["spriteStateId"] for e in events
                     if e["command"] == "EVENT_ACTOR_SET_STATE"}
            return palette, boxes, stages_set

        import itertools
        for bits in itertools.product((0, 1), repeat=len(LINES)):
            live = {line["live_var"]: bit for line, bit in zip(LINES, bits)}
            stages = next((i for i, bit in enumerate(bits) if not bit), len(LINES))
            palette, boxes, stages_set = outcome(live)
            self.assertEqual(palette, scene.chain_palette_id(stages), bits)
            self.assertEqual(stages_set, stages, bits)
            for line in LINES:
                self.assertEqual(boxes[scene.actor_id(line["box"])],
                                 "Live" if line["number"] <= stages else "Dead", (bits, line["key"]))

    def test_chain_palettes_light_stages_in_order(self):
        palettes = {p["id"]: p["colors"] for _, p in scene.tomas_palettes()}
        for stages, colors in ridge.CHAIN_PALETTES.items():
            self.assertEqual(palettes[scene.chain_palette_id(stages)], colors)
            for stage, index in enumerate(ridge.STAGE_COLOR_INDEX, start=1):
                self.assertEqual(colors[index], ridge.WIRE_LIVE if stage <= stages else ridge.WIRE_DEAD)

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        for line in LINES:
            script = actor_by_symbol(line["cable_symbol"])["script"]
            empty = script[0]
            self.assertTrue(is_var_if(empty, ridge.VAR_CARRYING_CABLE, 0))
            dead = next(e for e in empty["children"]["true"] if is_var_if(e, line["live_var"], 0))
            take = dead["children"]["true"]
            self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, line["number"]) for e in take))
            self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in take))
            self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                                e["args"]["type"] == FAKE_AUDIO["pickup"] for e in take))
            self.assertEqual(texts(empty["children"]["false"]), [["Hands full!\nOne cable a trip."]])

    def test_span_arcs_stay_dark_until_every_line_upstream_is_live(self):
        arcs = [a for a in built_actors() if a["symbol"].startswith("ridge_span_arc_")]
        expected = [(lane, delay, span["live_after"]) for span in ridge.FALLEN_SPANS
                    for lane, delay in zip(span["arcs"], span["delays"])]
        self.assertEqual(len(arcs), len(expected))
        for arc, ((row, x0, _), delay, live_after) in zip(arcs, expected):
            self.assertEqual((arc["x"], arc["y"]), (x0, row))
            self.assertEqual(arc["spriteSheetId"], FAKE_SPRITES["arc"])
            self.assertEqual(arc["collisionGroup"], "1")
            self.assertEqual([e["command"] for e in arc["startScript"]],
                             ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
            [gate] = arc["updateScript"]
            self.assertTrue(is_at_least(gate, ridge.VAR_CHAIN_LIVE, live_after))
            dead = gate["children"]["false"]
            self.assertNotIn("EVENT_ACTOR_COLLISIONS_ENABLE", [e["command"] for e in walk(dead)])
            self.assertNotIn("EVENT_ACTOR_SHOW", [e["command"] for e in walk(dead)])
            live = gate["children"]["true"]
            first = live[0]
            self.assertEqual(first["command"], "EVENT_IF_ACTOR_DIRECTION")
            self.assertEqual([w["args"]["frames"]["value"] for w in walk(first["children"]["true"])
                              if w["command"] == "EVENT_WAIT"], [delay] if delay else [])
            self.assertEqual([e["args"]["frames"]["value"] for e in live[1:] if e["command"] == "EVENT_WAIT"],
                             [rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES])

    def test_whips_sway_safely_then_hit_only_while_swinging(self):
        whips = [a for a in built_actors() if a["symbol"].startswith("ridge_whip_")]
        self.assertEqual(len(whips), len(ridge.WHIP_LANES))
        for whip, (row, x0, _) in zip(whips, ridge.WHIP_LANES):
            self.assertEqual((whip["x"], whip["y"]), (x0, row + 1))
            self.assertEqual(whip["spriteSheetId"], ridge.WHIP_SPRITE_ID)
            self.assertEqual(whip["collisionGroup"], "1")
            self.assertEqual(whip["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
            loop = [(e["command"], e["args"].get("spriteStateId") or e["args"].get("frames", {}).get("value"))
                    for e in whip["updateScript"][1:]]
            self.assertEqual(loop, [
                ("EVENT_ACTOR_COLLISIONS_DISABLE", None), ("EVENT_ACTOR_SET_STATE", "Sway"),
                ("EVENT_WAIT", ridge.WHIP_SWAY_FRAMES), ("EVENT_ACTOR_SET_STATE", "Swing"),
                ("EVENT_ACTOR_COLLISIONS_ENABLE", None), ("EVENT_WAIT", ridge.WHIP_SWING_FRAMES),
                ("EVENT_ACTOR_COLLISIONS_DISABLE", None), ("EVENT_ACTOR_SET_STATE", "Hang"),
                ("EVENT_WAIT", ridge.WHIP_HANG_FRAMES),
            ])

    def test_checked_in_files_match_the_builders(self):
        """Run after make_ridge_scene.py: disk must match the in-memory build."""
        music = shared.sidecar_id(scene.MUSIC_SIDECAR, "music")
        audio = {
            "death": shared.sidecar_id(scene.DEATH_SOUND, "sound"),
            "connect": shared.sidecar_id(scene.CONNECT_SOUND, "sound"),
            "pickup": shared.sidecar_id(scene.PICKUP_SOUND, "sound"),
        }
        sprites = {
            "gust": shared.sidecar_id(scene.GUST_SPRITE, "sprite"),
            "arc": shared.sidecar_id(scene.ARC_SPRITE, "sprite"),
        }
        expected = scene.build_scene(music, audio["death"])
        self.assertEqual(shared.load_json(scene.SCENE_DIR / "scene.gbsres"), expected)
        for actor in scene.build_actors(sprites, audio):
            path = scene.SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), actor)
        for trigger in scene.build_triggers(audio):
            path = scene.SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), trigger)
        for relative, palette in scene.tomas_palettes() + shared.hazard_palettes():
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), palette)
        self.assertEqual(list((scene.SCENE_DIR / "actors").glob("ridge_debris_*.gbsres")), [])
        on_disk = {p.name for p in (scene.SCENE_DIR / "actors").glob("*.gbsres")}
        self.assertEqual(on_disk, {f"{a['symbol']}.gbsres" for a in scene.build_actors(sprites, audio)},
                         "no retired actor files left behind")

    def test_palette_slots_and_tomas_palette(self):
        resource = built_scene()
        template = shared.load_json(scene.CLIMB_SCENE)
        sprites = resource["spritePaletteIds"]
        self.assertEqual(len(sprites), 8)
        self.assertEqual(sprites[0], opening.resource_id("palette:sprite:worker"))
        self.assertEqual(sprites[1], scene.tomas_palette_id())
        self.assertEqual(sprites[2], climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(sprites[shared.POLE_SPRITE_PALETTE_SLOT], intro.palette_id("pole"))
        self.assertEqual(sprites[hazards.BOARD_SPRITE_PALETTE_SLOT], hazards.BOARD_PALETTE_ID)
        self.assertEqual(sprites[5], template["spritePaletteIds"][5])
        self.assertEqual(sprites[ridge.ARC_SPRITE_PALETTE_SLOT], rosa.resource_id("palette:sprite:arc"))
        self.assertEqual(sprites[ridge.WHIP_SPRITE_PALETTE_SLOT], ridge.WHIP_PALETTE_ID)
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[5], scene.chain_palette_id(0))
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
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE, scene.ARC_SPRITE, scene.WHIP_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)


if __name__ == "__main__":
    unittest.main()
