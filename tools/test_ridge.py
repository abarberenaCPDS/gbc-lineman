"""Hiroshi's ridge (job 2: wind_ridge + ridge_saddle) checks.

Run: python3 -m unittest discover -s tools -p test_ridge.py (stdlib + contracts).
"""
import itertools
import json
import re
import unittest

import climb
import grid_chain
import hazards
import intro
import make_climb_scene as shared
import make_ridge_scene as scene
import opening
import redesign_maps
import ridge
import rosa
import scene_links
import scenes
import tickets
from test_grid_chain import actor_profile, sprite_budget, sprite_profiles

# Hermetic fixtures: the builders only reference these IDs.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite", "arc": "arc-sprite"}
PROJECT_DIR = scene.PROJECT_DIR
FOLDERS = ridge.SCENE_ORDER
RIDGE, SADDLE = ridge.RIDGE, ridge.SADDLE
LINES = scene.LINES
B = scene.BUILDERS


def built_scene(folder):
    return B[folder].build_scene(FAKE_MUSIC, FAKE_AUDIO)


def built_actors(folder):
    return B[folder].build_actors(FAKE_SPRITES)


def built_triggers(folder):
    return B[folder].build_triggers(FAKE_AUDIO)


def box_scripts():
    return scene.all_box_script_resources(FAKE_AUDIO)


def box_script(line):
    return next(script for _, script in box_scripts() if script["id"] == ridge.resource_id(f"script:box:{line['key']}"))


def builder_of_box(line):
    return B[line["box_scene"]]


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def sequences(events):
    yield events
    for entry in events:
        for branch in entry.get("children", {}).values():
            yield from sequences(branch)


def all_script_lists(folder):
    """Every authored script list reachable from one scene, its actors, triggers and box scripts."""
    resource = built_scene(folder)
    lists = [resource["script"], resource["playerHit1Script"]]
    for actor in built_actors(folder):
        lists.extend([actor["script"], actor["startScript"], actor["updateScript"], actor["hit1Script"]])
    lists.extend(script["script"] for _, script in B[folder].box_script_resources(FAKE_AUDIO))
    for trigger in built_triggers(folder):
        lists.extend([trigger["script"], trigger["leaveScript"]])
    return lists


def texts(events):
    return [e["args"]["text"] for e in walk(events) if e["command"] == "EVENT_TEXT"]


def positions(events):
    return [(e["args"]["x"]["value"], e["args"]["y"]["value"])
            for e in walk(events) if e["command"] == "EVENT_ACTOR_SET_POSITION"]


def var_value(event):
    return event["args"]["value"]["value"]


def is_set(event, variable, value):
    return (event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == variable
            and var_value(event) == value)


def is_var_if(event, variable, value, kind="eq"):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == kind
            and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


def actor_by_symbol(folder, symbol):
    return next(a for a in built_actors(folder) if a["symbol"] == symbol)


def trigger_by_symbol(folder, symbol):
    return next(t for t in built_triggers(folder) if t["symbol"] == symbol)


def rect(trigger):
    return (trigger["x"], trigger["y"], trigger["width"], trigger["height"])


def decode_rle(text):
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


def b_script(folder):
    [attach] = [e for e in built_scene(folder)["script"] if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
    return attach


def b_zones(attach):
    """({near value: its true events}, events after the last zone) for the B script's zone chain."""
    zones = {}
    events = attach["children"]["true"]
    while (len(events) == 1 and events[0]["command"] == "EVENT_IF"
           and events[0]["args"]["condition"]["valueA"] == {"type": "variable", "value": climb.VAR_NEAR}
           and events[0]["args"]["condition"]["valueB"]["value"] != grid_chain.NPC_ZONE):
        entry = events[0]
        zones[entry["args"]["condition"]["valueB"]["value"]] = entry["children"]["true"]
        events = entry["children"]["false"]
    if len(events) == 1 and events[0]["command"] == "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR":
        zones[grid_chain.NPC_ZONE] = events[0]["children"]["true"]
        events = events[0]["children"]["false"]
    if (len(events) == 1 and events[0]["command"] == "EVENT_IF"
            and events[0]["args"]["condition"]["valueB"]["value"] == grid_chain.NPC_ZONE):
        events = events[0]["children"]["false"]
    return zones, events


def first_hit(triggers, tile):
    x, y = tile
    return next((t for t in triggers
                 if t["x"] <= x < t["x"] + t["width"] and t["y"] <= y < t["y"] + t["height"]), None)


def zone_symbols(folder):
    return [t["symbol"] for t in built_triggers(folder) if t["symbol"].endswith(("_reach", "_pole_zone"))]


def local(folder, field):
    return [line for line in LINES if line[field] == folder]


class ContractTests(unittest.TestCase):
    def test_contract_is_the_spec_map(self):
        specs = redesign_maps.load()
        for folder in FOLDERS:
            layout, spec = ridge.LAYOUTS[folder], specs[folder]
            with self.subTest(folder=folder):
                self.assertEqual((ridge.MAP_W, ridge.MAP_H), (spec.width, spec.height))
                self.assertEqual(layout.collision_grid(), spec.grid)
                self.assertEqual(sorted(layout.lanes()), sorted(spec.lanes))
                self.assertEqual(sorted(layout.BOARDS), sorted(spec.boards))
                self.assertEqual([{k: v for k, v in line.items() if k in ("number", "pole", "box", "checkpoint")}
                                  for line in layout.LINES], spec.lines)
                self.assertEqual(layout.EXITS, [r for _, r in spec.triggers])
                self.assertEqual(layout.START, spec.start)
                self.assertLessEqual(set(spec.entries), set(layout.ENTRIES))
                route = layout.route_scene()
                self.assertEqual((route["npcs"], route["devices"]), (spec.npcs, spec.devices))
                cols = {x for y, row in enumerate(spec.rows) for x, c in enumerate(row) if c in "tABCDE"}
                for line in ridge.LINES:
                    if line["box_scene"] == folder:
                        self.assertIn(line["box"][0], cols)

    def test_route_scenes_are_declared(self):
        self.assertEqual([s["folder"] for s in ridge.ROUTE_SCENES], list(FOLDERS))
        for route, folder in zip(ridge.ROUTE_SCENES, FOLDERS):
            self.assertEqual(route["lines"], grid_chain.scene_lines(ridge.LINES, folder))
            self.assertEqual(route["exits"], [link.rect for link in
                                              scene_links.from_scene(folder, scene_links.table("redesign"))])

    def test_lines_tiers_and_hazard_kit(self):
        self.assertEqual([line["key"] for line in ridge.LINES], ["feeder", "west", "middle", "east", "house"])
        self.assertEqual([line["live_var"] for line in ridge.LINES], ["17", "28", "19", "29", "8"])
        self.assertEqual(ridge.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual([(line["pole_scene"], line["box_scene"]) for line in ridge.LINES],
                         [(RIDGE, RIDGE)] * 2 + [(RIDGE, SADDLE)] + [(SADDLE, SADDLE)] * 2)
        feet = {line["pole"][1] for line in ridge.LINES} | {line["box"][1] for line in ridge.LINES}
        self.assertEqual(feet, {ridge.SURFACE_STEP - 1, ridge.SURFACE_HIGH - 1, ridge.SURFACE_TOP - 1})
        # Spec §1: 16 hazards for Hiroshi (was 11), every kind in both scenes.
        self.assertEqual(ridge.hazard_count(), 16)
        for layout in ridge.LAYOUTS.values():
            with self.subTest(folder=layout.folder):
                self.assertTrue(layout.GUST_LANES and layout.WHIP_LANES and layout.FALLEN_SPANS
                                and layout.HIDDEN_CABLES and layout.BOARDS)
                self.assertTrue(any(row == ridge.CHEST_HIGH for row, _, _ in layout.hazard_lanes()))
                self.assertTrue(any(row == ridge.CHEST_LOW for row, _, _ in layout.hazard_lanes()))
        self.assertEqual((ridge.actor_count(RIDGE), ridge.actor_count(SADDLE)), (12, 11))
        self.assertEqual((ridge.LAYOUTS[RIDGE].trigger_count(), ridge.LAYOUTS[SADDLE].trigger_count()), (8, 10))

    def test_difficulty_sits_between_amara_and_priya(self):
        self.assertEqual((ridge.GUST_WARNING_FRAMES, ridge.GUST_ACTIVE_FRAMES, ridge.GUST_REST_FRAMES), (48, 22, 70))
        self.assertEqual((ridge.JOB_ARC_WARNING_FRAMES, ridge.JOB_ARC_ACTIVE_FRAMES, ridge.JOB_ARC_REST_FRAMES),
                         (42, 24, 60))
        self.assertEqual((ridge.WHIP_SWAY_FRAMES, ridge.WHIP_SWING_FRAMES, ridge.WHIP_HANG_FRAMES), (40, 22, 62))
        self.assertEqual(ridge.CABLE_TIMINGS, (150, 20, 24))
        self.assertLessEqual(ridge.GUST_WARNING_FRAMES, climb.GUST_WARNING_FRAMES)
        self.assertLess(ridge.GUST_REST_FRAMES, climb.GUST_REST_FRAMES)

    def test_cross_scene_carry_and_edge_port(self):
        line = ridge.CROSS_LINE
        self.assertEqual(line["number"], 3)
        port = ridge.EDGE_PORTS[3]
        self.assertEqual(ridge.RIDGE_ROUTES[-1], (3, ridge.RIDGE_ROUTES[-1][1]))
        self.assertEqual(ridge.RIDGE_ROUTES[-1][1][-1], (ridge.MAP_W - 1, port))
        self.assertEqual(ridge.SADDLE_ROUTES[0][1][0], (0, port))
        # 2A: line 3 has a pole and a pole zone, no box; 2B: box zone, no pole.
        ridge_triggers = {t["symbol"] for t in built_triggers(RIDGE)}
        saddle_triggers = {t["symbol"] for t in built_triggers(SADDLE)}
        self.assertIn("trigger_ridge_middle_pole_zone", ridge_triggers)
        self.assertNotIn("trigger_ridge_middle_reach", ridge_triggers)
        self.assertIn("trigger_ridge_middle_reach", saddle_triggers)
        self.assertNotIn("trigger_ridge_middle_pole_zone", saddle_triggers)
        self.assertIn("ridge_middle_pole", {a["symbol"] for a in built_actors(RIDGE)})
        self.assertNotIn("ridge_middle_pole", {a["symbol"] for a in built_actors(SADDLE)})
        # Line 3's box script in 2B binds no actor: its pole stands in 2A.
        self.assertEqual(B[SADDLE].chain.box_script_actor_bindings(scene.LINE_BY_KEY["middle"]), [])

    def test_boxes_are_background_transformers(self):
        self.assertTrue(ridge.BACKGROUND_BOXES)
        for folder in FOLDERS:
            chain = B[folder].chain
            self.assertTrue(chain.background_boxes)
            grid = ridge.LAYOUTS[folder].collision_grid()
            for line in local(folder, "box_scene"):
                top, body = ridge.transformer_tiles(line["box_at"])
                self.assertTrue(all(grid[y][x] == ridge.COL_EMPTY for x, y in top + body), line["key"])
                with self.assertRaises(ValueError):
                    chain.box_actor(line, 0, ridge.TRANSFORMER_SPRITE_ID)


class SceneTests(unittest.TestCase):
    def test_ids_are_stable_and_unique(self):
        ids = {"scene": ridge.SCENE_ID, "saddle": ridge.SADDLE_SCENE_ID, "background": ridge.BACKGROUND_ID,
               "saddle_bg": ridge.SADDLE_BACKGROUND_ID, "tomas_sprite": ridge.TOMAS_SPRITE_ID,
               "concentrator_sprite": ridge.CONCENTRATOR_SPRITE_ID, "tomas_palette": scene.tomas_palette_id()}
        for folder in FOLDERS:
            ids.update({f"{folder}:actor:{a['symbol']}": a["id"] for a in built_actors(folder)})
            ids.update({f"{folder}:trigger:{t['symbol']}": t["id"] for t in built_triggers(folder)})
        ids.update({f"box_script{i}": s["id"] for i, (_, s) in enumerate(box_scripts())})
        self.assertEqual(len(set(ids.values())), len(ids), "resource IDs collide")
        self.assertEqual(ridge.SCENE_ID, scenes.REGISTRY[RIDGE]["id"])
        self.assertEqual(ridge.SADDLE_SCENE_ID, scenes.REGISTRY[SADDLE]["id"])
        self.assertEqual(ridge.SADDLE_SCENE_ID, ridge.resource_id("scene:ridge_saddle"))
        # 2A keeps the 100x30 level's resource IDs where they survive.
        self.assertEqual(actor_by_symbol(SADDLE, scene.TOMAS_SYMBOL)["id"], ridge.resource_id("actor:tomas"))
        self.assertEqual(actor_by_symbol(RIDGE, "ridge_feeder_pole")["id"], ridge.resource_id("actor:pole:feeder"))
        for folder in FOLDERS:
            self.assertEqual(built_scene(folder), built_scene(folder), "scene build is deterministic")
            self.assertEqual(built_actors(folder), built_actors(folder), "actor build is deterministic")

    def test_event_ids_are_unique_across_both_scenes(self):
        seen = []
        for folder in FOLDERS:
            for script in all_script_lists(folder):
                seen.extend(entry["id"] for entry in walk(script))
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)), "duplicate event ID in the ridge scenes")

    def test_scene_fields(self):
        names = {RIDGE: ("Wind Ridge", "scene_wind_ridge"), SADDLE: ("Ridge Saddle", "scene_ridge_saddle")}
        for folder in FOLDERS:
            resource = built_scene(folder)
            layout = ridge.LAYOUTS[folder]
            with self.subTest(folder=folder):
                self.assertEqual((resource["name"], resource["symbol"]), names[folder])
                self.assertEqual(resource["type"], "PLATFORM")
                self.assertEqual((resource["width"], resource["height"]), (64, 18))
                self.assertEqual(resource["backgroundId"], layout.BACKGROUND_ID)
                self.assertEqual(resource["id"], layout.SCENE_ID)
                self.assertEqual(resource["tilesetId"], "")
                self.assertEqual((resource["x"], resource["y"]), scenes.editor_position(folder))
                self.assertEqual(decode_rle(resource["collisions"]),
                                 [cell for row in layout.collision_grid() for cell in row])
        self.assertEqual(ridge.BACKGROUND_ID, ridge.resource_id("background:wind-ridge"), "2A keeps its background")
        self.assertEqual(ridge.START, scene_links.REDESIGN_START[2])

    def test_variables_register_without_changing_existing(self):
        base = shared.load_json(PROJECT_DIR / "project" / "variables.gbsres")
        merged = scene.merged_variables(base)
        self.assertEqual(scene.merged_variables(merged), merged, "registration is idempotent")
        self.assertEqual(merged["variables"][:len(base["variables"])], base["variables"])
        by_id = {v["id"]: v for v in merged["variables"]}
        self.assertEqual(by_id["8"], {"id": "8", "name": "Ridge Line Live", "symbol": "var_ridge_line_live"})
        self.assertEqual(by_id["9"], {"id": "9", "name": "Tomas Home Powered", "symbol": "var_tomas_home_powered"})
        for var, name in (("17", "Ridge Feeder Live"), ("18", "Ridge Lines Live"), ("19", "Ridge Middle Live"),
                          ("20", "Ridge Chain Live"), ("28", "Ridge West Live"), ("29", "Ridge East Live")):
            self.assertEqual(by_id[var]["name"], name)
        self.assertEqual(by_id[climb.VAR_NEAR]["symbol"], "var_chain_near")
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "8", "name": "Other", "symbol": "x"}]})

    def test_entry_scene_resets_the_job_only_on_a_fresh_start(self):
        script = built_scene(RIDGE)["script"]
        self.assertEqual(script[0]["command"], "EVENT_PLAYER_SET_SPRITE")
        self.assertEqual(script[0]["args"]["spriteSheetId"], opening.resource_id("sprite:opening_worker24"))
        [reset] = [e for e in script if is_var_if(e, tickets.VAR_TICKET, 2) and
                   any(is_set(x, ridge.VAR_CHAIN_LIVE, 0) for x in walk([e]))]
        resets = reset["children"]["true"]
        for variable in (ridge.VAR_CARRYING_CABLE, ridge.VAR_HOME_POWERED, ridge.VAR_LINES_LIVE,
                         ridge.VAR_CHAIN_LIVE, *(line["live_var"] for line in LINES)):
            self.assertTrue(any(is_set(e, variable, 0) for e in resets), variable)
        # Outside the fresh-start gate nothing zeroes a job variable (a carry survives the edge).
        outside = [e for e in script if e is not reset]
        job_vars = {ridge.VAR_CARRYING_CABLE, ridge.VAR_HOME_POWERED, *(line["live_var"] for line in LINES)}
        self.assertFalse([e for e in outside if e["command"] == "EVENT_SET_VALUE"
                          and e["args"]["variable"] in job_vars])
        [fresh] = [e for e in script if is_var_if(e, tickets.VAR_TICKET, 2) and e is not reset]
        self.assertIs(script[-1], fresh, "music and intro run last")
        self.assertTrue(is_set(fresh["children"]["true"][-1], tickets.VAR_TICKET, 0))
        music = [e for e in walk(script) if e["command"] == "EVENT_MUSIC_PLAY"]
        self.assertEqual([e["args"]["musicId"] for e in music], [FAKE_MUSIC])
        self.assertIn(music[0], fresh["children"]["true"])
        self.assertEqual([e["args"]["text"] for e in fresh["children"]["true"] if e["command"] == "EVENT_TEXT"],
                         [["Hiroshi's oxygen\nmachine is off!"], ["Fix all 5 lines.\nOne cable a trip."]])
        self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "4"
                             for e in walk(script)), "init must not reset Service Restored")

    def test_saddle_never_resets_the_job_or_restarts_music(self):
        script = built_scene(SADDLE)["script"]
        self.assertEqual(script[0]["command"], "EVENT_PLAYER_SET_SPRITE")
        events = list(walk([e for e in script if e["command"] != "EVENT_SET_INPUT_SCRIPT"]))
        self.assertFalse([e for e in walk(script) if e["command"] == "EVENT_MUSIC_PLAY"])
        job_vars = {tickets.VAR_TICKET, ridge.VAR_CARRYING_CABLE, ridge.VAR_HOME_POWERED, ridge.VAR_LINES_LIVE,
                    *(line["live_var"] for line in LINES)}
        self.assertFalse([e for e in events if e["command"] == "EVENT_SET_VALUE"
                          and e["args"]["variable"] in job_vars])
        # The window follows var 9 (the player may come back after powering the house).
        [window] = [e for e in script if is_var_if(e, ridge.VAR_HOME_POWERED, 1)]
        self.assertEqual(window["children"]["true"][0]["args"]["palette3"],
                         opening.resource_id("palette:bg:powered_window"))
        self.assertEqual(window["children"]["false"][0]["args"]["palette3"], opening.resource_id("palette:bg:window"))

    def test_init_order_restores_poles_and_a_carried_cable(self):
        for folder in FOLDERS:
            script = built_scene(folder)["script"]
            commands = [e["command"] for e in script]
            near = next(i for i, e in enumerate(script) if is_set(e, climb.VAR_NEAR, grid_chain.NEAR_NONE))
            attach = commands.index("EVENT_SET_INPUT_SCRIPT")
            refresh = next(i for i, e in enumerate(script) if any(is_set(x, ridge.VAR_CHAIN_LIVE, 5) for x in walk([e])))
            carry = next(i for i, e in enumerate(script) if is_var_if(e, ridge.VAR_CARRYING_CABLE, 0, "ne"))
            hud = next(i for i, e in enumerate(script) if e["command"] == "EVENT_TEXT_DRAW")
            with self.subTest(folder=folder):
                self.assertLess(near, attach)
                self.assertLess(attach, refresh)
                self.assertLess(refresh, carry)
                self.assertLess(carry, hud)
                self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                                  for e in script[carry]["children"]["true"]], [("player", "Carry")])
                # Pole init: live -> Standing; carried -> Snapped; else Snapped+Cable, local poles only.
                poles = [e for e in script[refresh + 1:carry] if e["command"] == "EVENT_IF"]
                self.assertEqual(len(poles), len(local(folder, "pole_scene")))
                for event, line in zip(poles, local(folder, "pole_scene")):
                    pole = B[folder].actor_id(line["pole"])
                    self.assertTrue(is_var_if(event, line["live_var"], 1))
                    self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                                      for e in event["children"]["true"]], [(pole, "Standing")])
                    [carried] = event["children"]["false"]
                    self.assertTrue(is_var_if(carried, ridge.VAR_CARRYING_CABLE, line["number"]))
                    self.assertEqual(carried["children"]["true"][0]["args"]["spriteStateId"], "Snapped")
                    self.assertEqual(carried["children"]["false"][0]["args"]["spriteStateId"], "Snapped+Cable")

    def test_every_in_play_text_is_preceded_by_cutoff_and_followed_by_hud(self):
        for folder in FOLDERS:
            checked = 0
            for script in all_script_lists(folder):
                for events in sequences(script):
                    for i, entry in enumerate(events):
                        if entry["command"] != "EVENT_TEXT":
                            continue
                        checked += 1
                        self.assertGreater(i, 0)
                        before = events[i - 1]
                        self.assertEqual(before["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                        self.assertEqual(before["args"]["y"]["value"], 150)
                        redraws = [e for e in events[i + 1:] if e["command"] == "EVENT_TEXT_DRAW"]
                        self.assertEqual(redraws[0]["args"]["text"], ridge.HUD_TEXT)
            self.assertGreaterEqual(checked, 20, folder)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(ridge.HUD_TEXT, f"LINE %D1${ridge.VAR_LINES_LIVE}$/5 HOME %D1$09$/1")
        self.assertEqual(re.findall(r"\$(\d+)\$", ridge.HUD_TEXT), ["18", "09"])
        for folder in FOLDERS:
            draws = {entry["args"]["text"] for script in all_script_lists(folder)
                     for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
            self.assertEqual(draws - {intro.dev_label()} - {None}, {ridge.HUD_TEXT})

    def test_every_dialogue_line_fits_the_limit(self):
        self.assertEqual(scene.MAX_DIALOGUE_CHARS, 17)
        for folder in FOLDERS:
            for script in all_script_lists(folder):
                for entry in walk(script):
                    if entry["command"] == "EVENT_TEXT":
                        for line in entry["args"]["text"]:
                            for part in line.split("\n"):
                                self.assertLessEqual(len(part), 17, part)

    def test_a_hit_sends_any_carried_cable_home_before_the_respawn(self):
        """Abe (§9): a hit in another scene sends the carried cable back to its pole, as now."""
        for folder in FOLDERS:
            hit = built_scene(folder)["playerHit1Script"]
            self.assertEqual(hit[0]["command"], "EVENT_SOUND_PLAY_EFFECT")
            respawn = next(i for i, e in enumerate(hit) if positions([e]))
            for line in LINES:
                drop = next(i for i, e in enumerate(hit) if is_var_if(e, ridge.VAR_CARRYING_CABLE, line["number"]))
                self.assertLess(drop, respawn)
                events = hit[drop]["children"]["true"]
                self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, 0) for e in events))
                states = [(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in events if e["command"] == "EVENT_ACTOR_SET_STATE"]
                pole = (B[folder].actor_id(line["pole"]), "Snapped+Cable")
                if line["pole_scene"] == folder:
                    self.assertIn(pole, states)
                else:
                    self.assertNotIn(pole, states, "a pole in the other scene re-inits on entry")

    def test_respawn_is_per_scene(self):
        hit = built_scene(RIDGE)["playerHit1Script"]
        [chain] = [e for e in hit if positions([e])]
        current = [chain]
        for line in reversed(local(RIDGE, "box_scene")):
            [check] = current
            self.assertTrue(is_var_if(check, line["live_var"], 1), line["key"])
            self.assertEqual(positions(check["children"]["true"]), [line["checkpoint"]])
            current = check["children"]["false"]
        self.assertEqual(positions(current), [ridge.START])
        hit = built_scene(SADDLE)["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        door_x, door_y = ridge.HOUSE_DOOR
        self.assertEqual(positions(branch["children"]["false"]), [(door_x - 1, door_y)])
        current = branch["children"]["true"]
        for line in reversed(local(SADDLE, "box_scene")):
            [check] = current
            self.assertTrue(is_var_if(check, line["live_var"], 1), line["key"])
            self.assertEqual(positions(check["children"]["true"]), [line["checkpoint"]])
            current = check["children"]["false"]
        self.assertEqual(positions(current), [ridge.SADDLE_LAYOUT.START])

    def test_door_is_gated_on_live_lines_and_pays_out_once(self):
        trigger = trigger_by_symbol(SADDLE, scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual(rect(trigger), ridge.DOOR_TRIGGER)
        line = next(e for e in trigger["script"] if is_var_if(e, ridge.VAR_LINES_LIVE, ridge.LINE_COUNT))
        power = next(e for e in line["children"]["true"] if is_var_if(e, ridge.VAR_HOME_POWERED, 0))
        reward = power["children"]["true"]
        self.assertTrue(any(is_set(e, ridge.VAR_HOME_POWERED, 1) for e in reward))
        states = {(e["args"]["actorId"], e["args"]["spriteStateId"])
                  for e in reward if e["command"] == "EVENT_ACTOR_SET_STATE"}
        self.assertEqual(states, {(B[SADDLE].actor_id(scene.TOMAS_KEY), "Relieved"),
                                  (B[SADDLE].actor_id(scene.CONCENTRATOR_KEY), "On")})
        self.assertIn("Hiroshi:\nLights are on.\nI stayed calm.", texts(reward)[0])
        self.assertEqual(texts(line["children"]["false"]), [["Still no power.\nFix every line!"]])
        writers = [e for folder in FOLDERS for script in all_script_lists(folder) for e in walk(script)
                   if is_set(e, "9", 1)]
        self.assertEqual([e["id"] for e in writers], [e["id"] for e in walk(reward) if is_set(e, "9", 1)])

    def test_exits_follow_the_link_table(self):
        table = scene_links.table("redesign")
        for folder in FOLDERS:
            triggers = built_triggers(folder)
            links = scene_links.from_scene(folder, table)
            self.assertEqual([rect(t) for t in triggers[:len(links)]], [link.rect for link in links],
                             "exits come first, in table order")
            for trigger, link in zip(triggers, links):
                with self.subTest(folder=folder, target=link.target):
                    events = list(walk(trigger["script"]))
                    [switch] = [e for e in events if e["command"] == "EVENT_SWITCH_SCENE"]
                    self.assertEqual(switch["args"]["fadeSpeed"], "2", "keep the fade (Abe)")
                    go = trigger["script"] if link.gate is None else trigger["script"][0]["children"]["true"]
                    self.assertEqual([e["command"] for e in go[:2]],
                                     ["EVENT_OVERLAY_SET_SCANLINE_CUTOFF", "EVENT_OVERLAY_HIDE"])
                    if link.gate is None:
                        self.assertNotEqual(trigger["script"][0]["command"], "EVENT_IF")
                        self.assertEqual(switch["args"]["sceneId"], scene_links.scene_id(link.target))
                        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), link.entry)
                        self.assertEqual(switch["args"]["direction"], link.facing)
                    else:
                        [gate] = trigger["script"]
                        self.assertTrue(is_var_if(gate, ridge.VAR_HOME_POWERED, 1))
                        self.assertEqual(switch["args"]["sceneId"], tickets.WORK_ORDER_SCENE_ID)
                        self.assertTrue(any(is_set(e, tickets.VAR_TICKET, 3) for e in go))
                        refused = gate["children"]["false"]
                        self.assertNotIn("EVENT_ACTOR_SET_POSITION", [e["command"] for e in walk(refused)])
                        self.assertEqual(texts(refused), [["Power Hiroshi's\nhouse first."]])
                        tx, _, tw, _ = ridge.DOOR_TRIGGER
                        self.assertGreaterEqual(trigger["x"], tx + tw)
        self.assertEqual(tickets.TICKETS[3]["scene_id"], rosa.SCENE_ID)

    def _spots(self, folder):
        layout = ridge.LAYOUTS[folder]
        grid = layout.collision_grid()
        standing = {(x, y) for y in range(2, ridge.MAP_H - 1) for x in range(1, ridge.MAP_W - 1)
                    if grid_chain.stands(grid, x, y)}
        standing.update(layout.ENTRIES)
        for line in layout.LINES:
            standing.update(line[k] for k in ("pole", "box", "checkpoint") if k in line)
        standing.update((x0, row + 1) for row, x0, _ in layout.all_hazard_lanes())
        return sorted(standing)

    def test_every_view_stays_within_the_sprite_budgets(self):
        """Ten OBJs per scanline, eleven active actors and 40 OBJs, with real art bounds."""
        profiles = sprite_profiles(PROJECT_DIR)
        for folder in FOLDERS:
            actors = built_actors(folder)
            by_symbol = {a["symbol"]: a for a in actors}
            for spot in self._spots(folder):
                load, near = sprite_budget(PROJECT_DIR, actors, spot, ridge.MAP_W, ridge.MAP_H, profiles=profiles)
                self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (folder, spot, load))
                self.assertLessEqual(len(near), ridge.MAX_ACTIVE_ACTORS, (folder, spot, near))
                total = 4 + sum(max(len(frame) for frame in actor_profile(by_symbol[s], profiles)["frames"])
                                for s in near)
                self.assertLessEqual(total, 40, (folder, spot))

    def test_actor_rosters(self):
        expected = {
            RIDGE: ["ridge_feeder_pole", "ridge_west_pole", "ridge_middle_pole", "ridge_gust_01", "ridge_gust_02",
                    "ridge_span_arc_01", "ridge_whip_01", "ridge_whip_02", "ridge_hidden_cable_01",
                    "ridge_hidden_cable_02", "ridge_board_01", "ridge_board_02"],
            SADDLE: [scene.TOMAS_SYMBOL, scene.CONCENTRATOR_SYMBOL, "ridge_east_pole", scene.POLE_SYMBOL,
                     "ridge_gust_03", "ridge_gust_04", "ridge_span_arc_02", "ridge_whip_03",
                     "ridge_hidden_cable_03", "ridge_board_03", "ridge_board_04"],
        }
        for folder in FOLDERS:
            actors = built_actors(folder)
            with self.subTest(folder=folder):
                self.assertEqual([a["symbol"] for a in actors], expected[folder])
                self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
                self.assertEqual(len(actors), ridge.actor_count(folder))
                self.assertNotIn(ridge.TRANSFORMER_SPRITE_ID, {a["spriteSheetId"] for a in actors})
                for line in local(folder, "pole_scene"):
                    pole = actor_by_symbol(folder, line["pole_symbol"])
                    self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
                    self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
                    self.assertEqual(pole["script"], [])
                    self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        tomas = actor_by_symbol(SADDLE, scene.TOMAS_SYMBOL)
        self.assertEqual((tomas["x"], tomas["y"]), ridge.TOMAS)
        conc = actor_by_symbol(SADDLE, scene.CONCENTRATOR_SYMBOL)
        self.assertEqual((conc["x"], conc["y"]), ridge.CONCENTRATOR)
        for actor, powered, cold in ((tomas, "Relieved", "Waiting"), (conc, "On", "Off")):
            [gate] = actor["startScript"]
            self.assertTrue(is_var_if(gate, ridge.VAR_HOME_POWERED, 1))
            self.assertEqual(gate["children"]["true"][0]["args"]["spriteStateId"], powered)
            self.assertEqual(gate["children"]["false"][0]["args"]["spriteStateId"], cold)

    def test_hazard_actors(self):
        for folder in FOLDERS:
            layout = ridge.LAYOUTS[folder]
            actors = built_actors(folder)
            grid = layout.collision_grid()
            gusts = [a for a in actors if a["symbol"].startswith("ridge_gust_")]
            self.assertEqual(len(set(layout.GUST_START_DELAYS)), len(layout.GUST_START_DELAYS))
            for gust, (row, x0, _), delay in zip(gusts, layout.GUST_LANES, layout.GUST_START_DELAYS):
                self.assertEqual((gust["x"], gust["y"]), (x0, row))
                self.assertEqual(gust["spriteSheetId"], FAKE_SPRITES["gust"])
                guard = gust["updateScript"][0]
                waits = [e["args"]["frames"]["value"] for e in walk(guard["children"]["true"])
                         if e["command"] == "EVENT_WAIT"]
                self.assertEqual(waits, [delay] if delay else [])
                self.assertEqual([e["args"]["frames"]["value"] for e in gust["updateScript"][1:]
                                  if e["command"] == "EVENT_WAIT"],
                                 [ridge.GUST_WARNING_FRAMES, ridge.GUST_ACTIVE_FRAMES, ridge.GUST_REST_FRAMES])
            whips = [a for a in actors if a["symbol"].startswith("ridge_whip_")]
            for whip, (row, x0, _) in zip(whips, layout.WHIP_LANES):
                self.assertEqual((whip["x"], whip["y"]), (x0, row + 1))
                self.assertEqual(whip["spriteSheetId"], ridge.WHIP_SPRITE_ID)
                self.assertEqual([e["args"]["frames"]["value"] for e in whip["updateScript"][1:]
                                  if e["command"] == "EVENT_WAIT"],
                                 [ridge.WHIP_SWAY_FRAMES, ridge.WHIP_SWING_FRAMES, ridge.WHIP_HANG_FRAMES])
            arcs = [a for a in actors if a["symbol"].startswith("ridge_span_arc_")]
            expected = [(lane, span["live_after"]) for span in layout.FALLEN_SPANS for lane in span["arcs"]]
            self.assertEqual(len(arcs), len(expected))
            for arc, ((row, x0, _), live_after) in zip(arcs, expected):
                self.assertEqual((arc["x"], arc["y"]), (x0, row))
                [gate] = arc["updateScript"]
                self.assertTrue(is_var_if(gate, ridge.VAR_CHAIN_LIVE, live_after, "gte"))
                self.assertNotIn("EVENT_ACTOR_COLLISIONS_ENABLE", [e["command"] for e in walk(gate["children"]["false"])])
            cables = [a for a in actors if a["symbol"].startswith("ridge_hidden_cable_")]
            for cable, (row, x0, _), delay in zip(cables, layout.HIDDEN_CABLES, layout.CABLE_START_DELAYS):
                self.assertEqual((cable["x"], cable["y"]), (x0, row))
                first = next(e for e in cable["updateScript"] if e["command"] == "EVENT_IF_ACTOR_DIRECTION")
                self.assertEqual([e["args"]["frames"]["value"] for e in first["children"]["true"]
                                  if e["command"] == "EVENT_WAIT"], [delay])
                self.assertEqual([e["args"]["frames"]["value"] for e in cable["updateScript"]
                                  if e["command"] == "EVENT_WAIT"], list(ridge.CABLE_TIMINGS))
            boards = [a for a in actors if a["symbol"].startswith("ridge_board_")]
            self.assertEqual(actors[-len(boards):], boards, "boards draw last")
            for (number, board), actor in zip(B[folder].boards(), boards):
                self.assertEqual(actor["symbol"], f"ridge_board_{number:02d}")
                self.assertEqual((actor["x"], actor["y"]), hazards.board_actor_position(board))
                [gate] = actor["updateScript"]
                self.assertTrue(is_var_if(gate, hazards.VAR_ON_BOARD, number))
                row, x0, x1 = board
                self.assertTrue(all(grid[row][x] == ridge.COL_TOP for x in range(x0, x1 + 1)))
                trigger = trigger_by_symbol(folder, f"trigger_ridge_cracked_board_{number:02d}")
                self.assertEqual(rect(trigger), hazards.board_trigger_rect(board))
                self.assertTrue(is_set(trigger["script"][0], hazards.VAR_ON_BOARD, number))

    def test_b_dispatch_pickups_and_boxes_are_local(self):
        for folder in FOLDERS:
            zones, rest = b_zones(b_script(folder))
            with self.subTest(folder=folder):
                expected = {line["number"] for line in local(folder, "pole_scene")}
                expected |= {grid_chain.BOX_ZONE + line["number"] for line in local(folder, "box_scene")}
                self.assertEqual(set(zones) - {grid_chain.NPC_ZONE}, expected)
                for line in local(folder, "box_scene"):
                    [invoke] = zones[grid_chain.BOX_ZONE + line["number"]]
                    self.assertEqual(invoke["command"], "EVENT_CALL_CUSTOM_EVENT")
                    self.assertEqual(invoke["args"]["customEventId"], box_script(line)["id"])
                for line in local(folder, "pole_scene"):
                    [empty] = zones[line["number"]]
                    self.assertTrue(is_var_if(empty, ridge.VAR_CARRYING_CABLE, 0))
                    [dead] = empty["children"]["true"]
                    take = dead["children"]["true"]
                    self.assertTrue(any(is_set(e, ridge.VAR_CARRYING_CABLE, line["number"]) for e in take))
                    self.assertEqual(texts(empty["children"]["false"]), [["Hands full!\nOne cable a trip."]])
                [drop] = rest
                self.assertTrue(is_var_if(drop, ridge.VAR_CARRYING_CABLE, 1, "gte"))
                branches = {e["args"]["condition"]["valueB"]["value"]: e["children"]["true"]
                            for e in drop["children"]["true"] if e["command"] == "EVENT_IF"}
                self.assertEqual(set(branches), {line["number"] for line in LINES}, "any carried cable drops")
                for line in LINES:
                    self.assertEqual(texts(branches[line["number"]]), [["Cable dropped."]])
        zones, _ = b_zones(b_script(SADDLE))
        self.assertEqual(texts(list(walk(zones[grid_chain.NPC_ZONE]))),
                         texts(list(walk(actor_by_symbol(SADDLE, scene.TOMAS_SYMBOL)["script"]))))
        self.assertTrue(b_script(SADDLE)["args"]["override"])

    def test_each_box_takes_only_its_own_cable_and_counts_the_line(self):
        for line in LINES:
            script = box_script(line)
            [live] = script["script"]
            self.assertTrue(is_var_if(live, line["live_var"], 1))
            self.assertEqual(texts(live["children"]["true"]), [["Already fixed."]])
            has_cable = next(e for e in live["children"]["false"]
                             if is_var_if(e, ridge.VAR_CARRYING_CABLE, line["number"]))
            branch = has_cable["children"]["true"]
            self.assertTrue(any(is_set(e, line["live_var"], 1) for e in branch))
            self.assertEqual([e["args"]["variable"] for e in branch if e["command"] == "EVENT_INC_VALUE"],
                             [ridge.VAR_LINES_LIVE])
            message = branch[-1]
            self.assertTrue(is_var_if(message, ridge.VAR_CHAIN_LIVE, ridge.LINE_COUNT))
            [lit] = message["children"]["false"]
            self.assertTrue(is_var_if(lit, ridge.VAR_CHAIN_LIVE, line["number"], "gte"))
            for palette in (e for e in walk(branch) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"):
                self.assertEqual({k for k, v in palette["args"].items() if v != "keep"},
                                 {f"palette{ridge.LINE_BG_SLOT}", f"palette{ridge.LINE_BG_SLOT_2}"})
            [other] = has_cable["children"]["false"]
            self.assertEqual(texts(other["children"]["false"]), [["Wrong cable\nfor this box."]])
        incs = [e for folder in FOLDERS for script in all_script_lists(folder) for e in walk(script)
                if e["command"] == "EVENT_INC_VALUE"]
        self.assertEqual(len(incs), ridge.LINE_COUNT, "one count per line, nothing else")

    def test_chain_lights_wires_only_as_far_as_continuous_in_both_scenes(self):
        for folder in FOLDERS:
            refresh = B[folder].chain.chain_refresh_events("probe")
            for bits in itertools.product((0, 1), repeat=len(LINES)):
                live = {line["live_var"]: bit for line, bit in zip(LINES, bits)}
                events = refresh
                while len(events) == 1 and events[0]["command"] == "EVENT_IF":
                    events = events[0]["children"]["true" if live[events[0]["args"]["condition"]["valueA"]["value"]]
                                                   else "false"]
                stages = next((i for i, bit in enumerate(bits) if not bit), len(LINES))
                palette = next(e["args"] for e in events if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
                self.assertEqual({slot: palette[f"palette{slot}"] for slot in (5, 6)},
                                 {slot: scene.chain_palette_id(stages, slot) for slot in (5, 6)})
                self.assertFalse([e for e in events if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_chain_palettes_light_stages_in_order(self):
        palettes = {p["id"]: p["colors"] for _, p in scene.tomas_palettes()}
        for stages, colors in ridge.CHAIN_PALETTES.items():
            for stage, index in enumerate(ridge.STAGE_COLOR_INDEX, start=1):
                slot = ridge.LINE_BG_SLOT if stage <= 3 else ridge.LINE_BG_SLOT_2
                self.assertEqual(palettes[scene.chain_palette_id(stages, slot)][index],
                                 ridge.WIRE_LIVE if stage <= stages else ridge.WIRE_DEAD)
        for folder in FOLDERS:
            backgrounds = built_scene(folder)["paletteIds"]
            self.assertEqual(backgrounds[5], scene.chain_palette_id(0, 5), "one chain palette set for the job")
            self.assertEqual(backgrounds[6], scene.chain_palette_id(0, 6))

    def test_zone_triggers_and_trigger_budget(self):
        for folder in FOLDERS:
            triggers = built_triggers(folder)
            with self.subTest(folder=folder):
                expected = {f"trigger_ridge_{line['key']}_reach": grid_chain.BOX_ZONE + line["number"]
                            for line in local(folder, "box_scene")}
                expected.update({f"trigger_ridge_{line['key']}_pole_zone": line["number"]
                                 for line in local(folder, "pole_scene")})
                self.assertEqual(set(zone_symbols(folder)), set(expected))
                for symbol, value in expected.items():
                    zone = trigger_by_symbol(folder, symbol)
                    [enter] = zone["script"]
                    self.assertTrue(is_set(enter, climb.VAR_NEAR, value))
                    [leave] = zone["leaveScript"]
                    self.assertTrue(is_var_if(leave, climb.VAR_NEAR, value))
                self.assertEqual(len(triggers), ridge.LAYOUTS[folder].trigger_count())
                for index, trigger in enumerate(triggers):
                    for other in triggers[index + 1:]:
                        a, b = rect(trigger), rect(other)
                        overlap = a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]
                        self.assertFalse(overlap, (trigger["symbol"], other["symbol"]))
                for line in local(folder, "box_scene"):
                    bx, by = line["box_at"]
                    for tile in [(x, y) for x in (bx, bx + 1) for y in (by - 2, by - 1, by)]:
                        self.assertEqual(first_hit(triggers, tile)["symbol"], f"trigger_ridge_{line['key']}_reach")

    def test_checked_in_files_match_the_builders(self):
        """Run after make_ridge_scene.py: disk must match the in-memory build."""
        music, audio, sprites = scene.audio_and_sprite_ids()
        for folder in FOLDERS:
            builder = B[folder]
            with self.subTest(folder=folder):
                self.assertEqual(shared.load_json(builder.scene_dir / "scene.gbsres"),
                                 builder.build_scene(music, audio))
                for kind, items in (("actors", builder.build_actors(sprites)),
                                    ("triggers", builder.build_triggers(audio))):
                    for item in items:
                        self.assertEqual(shared.load_json(builder.scene_dir / kind / f"{item['symbol']}.gbsres"), item)
                    on_disk = {p.name for p in (builder.scene_dir / kind).glob("*.gbsres")}
                    self.assertEqual(on_disk, {f"{item['symbol']}.gbsres" for item in items}, "no stale files")
        for relative, script in scene.all_box_script_resources(audio):
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), script)
        for relative, palette in scene.tomas_palettes() + shared.hazard_palettes():
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), palette)

    def test_palette_slots(self):
        template = shared.load_json(scene.CLIMB_SCENE)
        for folder in FOLDERS:
            resource = built_scene(folder)
            sprites = resource["spritePaletteIds"]
            self.assertEqual(sprites[0], opening.resource_id("palette:sprite:worker"))
            self.assertEqual(sprites[1], scene.tomas_palette_id())
            self.assertEqual(sprites[2], climb.grid_resource_id("palette:sprite:grid"))
            self.assertEqual(sprites[shared.POLE_SPRITE_PALETTE_SLOT], intro.palette_id("pole"))
            self.assertEqual(sprites[hazards.BOARD_SPRITE_PALETTE_SLOT], hazards.BOARD_PALETTE_ID)
            self.assertEqual(sprites[5], template["spritePaletteIds"][5])
            self.assertEqual(sprites[ridge.ARC_SPRITE_PALETTE_SLOT], rosa.resource_id("palette:sprite:arc"))
            self.assertEqual(sprites[ridge.WHIP_SPRITE_PALETTE_SLOT], ridge.WHIP_PALETTE_ID)
            backgrounds = resource["paletteIds"]
            self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                               for name in ["night", "stone", "timber", "window", "foliage"]])
            self.assertEqual(backgrounds[7], "default-ui")

    def test_shared_sidecars_exist(self):
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE, scene.ARC_SPRITE, scene.WHIP_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)
        for layout in ridge.LAYOUTS.values():
            sidecar = PROJECT_DIR / f"assets/backgrounds/{layout.folder}.png.gbsres"
            self.assertEqual(json.loads(sidecar.read_text())["id"], layout.BACKGROUND_ID)


if __name__ == "__main__":
    unittest.main()
