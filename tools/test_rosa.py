"""Signal Hill checks: python3 -m unittest discover -s tools -p test_rosa.py (or cd tools)."""
import itertools
import json
import re
import unittest
from pathlib import Path

import climb
import grid_chain
import hazards
import intro
import make_climb_scene as shared
import make_rosa_scene as scene
import opening
import ridge
import rosa
import tickets
import kiko
from test_grid_chain import sprite_budget, sprite_profiles

# Hermetic fixtures: the builders only reference these IDs, so fixed strings
# keep the structural tests independent of which art sidecars exist yet.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite", "arc": "arc-sprite"}
PROJECT_DIR = scene.PROJECT_DIR
LINES = scene.LINES


def built_scene():
    return scene.build_scene(FAKE_MUSIC, FAKE_AUDIO)


def built_actors():
    return scene.build_actors(FAKE_SPRITES, FAKE_AUDIO)


def box_script_resources():
    return scene.box_script_resources(FAKE_AUDIO)


def box_script(line):
    return next(script for _, script in box_script_resources()
                if script["id"] == scene.CHAIN.box_script_id(line))


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
    lists.extend(script["script"] for _, script in box_script_resources())
    for trigger in built_triggers():
        lists.extend([trigger["script"], trigger["leaveScript"]])
    return lists


def actor_by_symbol(symbol):
    return next(a for a in built_actors() if a["symbol"] == symbol)


def box_script_actor_arg(line, target_actor_id):
    return str(next(index for index, (actor_id, _name)
                    in enumerate(scene.CHAIN.box_script_actor_bindings(line))
                    if actor_id == target_actor_id))


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


def is_at_least(event, variable, value):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == "gte"
            and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


def texts(events):
    return [e["args"]["text"] for e in events if e["command"] == "EVENT_TEXT"]


def spots():
    """Every collision-supported hero position plus explicit interactables/hazard lanes."""
    grid = rosa.collision_grid()
    found = {(x, y) for y in range(2, rosa.MAP_H - 1) for x in range(1, rosa.MAP_W - 1)
             if grid_chain.stands(grid, x, y)}
    found.update((rosa.START, rosa.HOUSE_DOOR))
    for line in LINES:
        found.update((line["pole_at"], line["box_at"], line["checkpoint"]))
    found.update((x0, row + 1) for row, x0, _ in rosa._all_hazard_lanes())
    return sorted(found)


def b_script():
    """The scene's one B input script (EVENT_SET_INPUT_SCRIPT) from init."""
    [attach] = [e for e in built_scene()["script"] if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
    return attach


def b_zones(attach):
    """({near value: its true events}, events after the last zone) for the B script's zone chain."""
    zones = {}
    events = attach["children"]["true"]
    while len(events) == 1 and events[0]["command"] in (
            "EVENT_IF_ACTOR_AT_POSITION", "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR"):
        npc = events[0]
        zones.setdefault(grid_chain.NPC_ZONE, npc["children"]["true"])
        events = npc["children"]["false"]
    while (len(events) == 1 and events[0]["command"] == "EVENT_IF"
           and events[0]["args"]["condition"]["valueA"] == {"type": "variable", "value": climb.VAR_NEAR}):
        entry = events[0]
        zones[entry["args"]["condition"]["valueB"]["value"]] = entry["children"]["true"]
        events = entry["children"]["false"]
    if len(events) == 1 and events[0]["command"] == "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR":
        npc = events[0]
        zones[grid_chain.NPC_ZONE] = npc["children"]["true"]
        events = npc["children"]["false"]
        if (len(events) == 1 and events[0]["command"] == "EVENT_IF"
                and events[0]["args"]["condition"]["valueA"] ==
                {"type": "variable", "value": climb.VAR_NEAR}
                and events[0]["args"]["condition"]["valueB"]["value"] == grid_chain.NPC_ZONE):
            events = events[0]["children"]["false"]
    return zones, events


def zone_symbols():
    return [t["symbol"] for t in built_triggers() if t["symbol"].endswith(("_reach", "_pole_zone"))]


def first_hit(triggers, tile):
    """The trigger the engine fires for a hero covering ``tile``: the first listed trigger that holds it."""
    x, y = tile
    return next((t for t in triggers
                 if t["x"] <= x < t["x"] + t["width"] and t["y"] <= y < t["y"] + t["height"]), None)


def box_tiles(box):
    """Every tile a hero standing on this box covers: its two columns, the body rows above the feet."""
    bx, by = box
    return [(x, y) for x in (bx, bx + 1) for y in (by - 2, by - 1, by)]


class RosaTests(unittest.TestCase):
    def test_ids_are_stable_and_unique(self):
        ids = {
            "scene": rosa.SCENE_ID,
            "background": rosa.BACKGROUND_ID,
            "rosa_sprite": rosa.ROSA_SPRITE_ID,
            "workstation_sprite": rosa.WORKSTATION_SPRITE_ID,
            "arc_sprite": rosa.ARC_SPRITE_ID,
            "rosa_palette": scene.rosa_palette_id(),
            "arc_palette": scene.arc_palette_id(),
            "trigger": rosa.resource_id("trigger:rosa-door"),
        }
        actor_ids = [a["id"] for a in built_actors()]
        ids.update({f"actor{i}": value for i, value in enumerate(actor_ids)})
        ids.update({f"box_script{i}": script["id"]
                    for i, (_, script) in enumerate(box_script_resources())})
        self.assertEqual(len(set(ids.values())), len(ids), "resource IDs collide")
        self.assertEqual(rosa.resource_id("scene:signal-hill"), rosa.SCENE_ID)
        self.assertNotEqual(rosa.resource_id("actor:rosa"), rosa.resource_id("trigger:rosa-door"))
        # The house line keeps the original job's actor keys (stable IDs).
        self.assertEqual(scene.actor_id("pole"), rosa.resource_id("actor:pole"))
        self.assertEqual(scene.actor_id("cable-end"), rosa.resource_id("actor:cable-end"))
        self.assertEqual(scene.actor_id("junction-box"), rosa.resource_id("actor:junction-box"))
        self.assertEqual(built_scene(), built_scene(), "scene build is deterministic")
        self.assertEqual(built_actors(), built_actors(), "actor build is deterministic")

    def test_event_ids_are_unique_within_the_scene(self):
        seen = []
        for script in all_script_lists():
            seen.extend(entry["id"] for entry in walk(script))
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)), "duplicate event ID inside signal_hill")

    def test_scene_fields_match_signal_hill_contract(self):
        resource = built_scene()
        self.assertEqual(resource["name"], "Signal Hill")
        self.assertEqual(resource["symbol"], "scene_signal_hill")
        self.assertEqual(resource["type"], "PLATFORM")
        self.assertEqual((resource["width"], resource["height"]), (100, 18))
        self.assertEqual(resource["backgroundId"], rosa.BACKGROUND_ID)
        self.assertEqual(resource["id"], rosa.SCENE_ID)
        self.assertEqual(resource["_resourceType"], "scene")
        self.assertEqual(resource["tilesetId"], "", "tilesets are not used by this job")
        self.assertEqual(resource["_index"], 5, "next index after wind_ridge (4)")
        self.assertEqual((resource["x"], resource["y"]), (800, 360))
        taken = []
        for path in (PROJECT_DIR / "project" / "scenes").glob("*/scene.gbsres"):
            if path.parent.name != "signal_hill":
                other = shared.load_json(path)
                taken.append((other["_index"], other["x"], other["y"]))
        self.assertNotIn((resource["_index"], resource["x"], resource["y"]), taken,
                         "editor index and position must be free")
        self.assertNotIn(resource["_index"], [t[0] for t in taken], "scene index must be unique")

    def test_five_line_route_and_full_hazard_kit(self):
        self.assertEqual((rosa.MAP_W, rosa.MAP_H), (100, 18))
        self.assertEqual([(line["key"], line["pole"], line["box"], line["checkpoint"], line["live_var"])
                          for line in rosa.LINES], [
            ("feeder", (7, 8), (9, 14), (14, 14), "21"),
            ("west", (12, 11), (26, 14), (27, 14), "30"),
            ("middle", (31, 8), (55, 8), (56, 8), "31"),
            ("east", (59, 11), (70, 8), (71, 8), "32"),
            ("house", (73, 8), (89, 11), (88, 11), "10"),
        ])
        self.assertEqual(rosa.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual(rosa.ARC_LANES, [(13, 17, 18)])
        self.assertEqual(rosa.GUST_LANES, [])
        self.assertEqual(rosa.span_arc_lanes(), [(13, 43, 44), (13, 83, 84)])
        self.assertEqual(rosa.WHIP_LANES, [(13, 48, 49), (13, 64, 65), (13, 78, 79)])
        self.assertEqual(hazards.HIDDEN_CABLES["signal_hill"], [(7, 35, 36)])
        self.assertEqual(hazards.BOARDS["signal_hill"], [(15, 20, 22)])
        self.assertEqual(rosa.actor_count(), rosa.MAX_SCENE_ACTORS)

    def test_collisions_match_contract(self):
        resource = built_scene()
        self.assertEqual(decode_rle(resource["collisions"]),
                         [cell for row in rosa.collision_grid() for cell in row])
        self.assertEqual(
            shared.collision_rle(rosa.collision_grid(), rosa.MAP_W, rosa.MAP_H),
            resource["collisions"],
        )

    def test_variables_register_without_changing_existing(self):
        base = shared.load_json(PROJECT_DIR / "project" / "variables.gbsres")
        merged = scene.merged_variables(base)
        self.assertEqual(scene.merged_variables(merged), merged, "registration is idempotent")
        self.assertEqual(merged["variables"][:len(base["variables"])], base["variables"])
        by_id = {v["id"]: v for v in merged["variables"]}
        self.assertEqual(by_id[rosa.VAR_LINE_LIVE],
                         {"id": "10", "name": "Hill Line Live", "symbol": "var_hill_line_live"})
        self.assertEqual(by_id[rosa.VAR_HOME_POWERED],
                         {"id": "11", "name": "Rosa Home Powered", "symbol": "var_rosa_home_powered"})
        self.assertEqual(by_id["21"], {"id": "21", "name": "Hill Feeder Live",
                                       "symbol": "var_hill_feeder_live"})
        self.assertEqual(by_id["22"], {"id": "22", "name": "Hill Lines Live",
                                       "symbol": "var_hill_lines_live"})
        self.assertEqual(by_id["23"], {"id": "23", "name": "Hill Chain Live",
                                       "symbol": "var_hill_chain_live"})
        self.assertEqual(by_id["6"]["symbol"], "var_carrying_cable")
        self.assertEqual(by_id["7"]["symbol"], "var_line_live")
        self.assertEqual(by_id["8"]["symbol"], "var_ridge_line_live")
        self.assertEqual(by_id["9"]["symbol"], "var_tomas_home_powered")
        self.assertEqual(by_id[climb.VAR_NEAR], {"id": "27", "name": "Chain Near", "symbol": "var_chain_near"})

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(8)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:8], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(8)]
                         + [v[0] for v in rosa.VARIABLES if v[0] not in {str(i) for i in range(8)}]
                         + [hazards.VAR_ON_BOARD, climb.VAR_NEAR])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "10", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_chain(self):
        script = built_scene()["script"]
        for variable in ("6", "10", "11", rosa.VAR_FEEDER_LIVE, rosa.VAR_LINES_LIVE, rosa.VAR_CHAIN_LIVE):
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
        self.assertEqual(palette_events[0]["args"][f"palette{rosa.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:window"))
        # The chain refresh's outermost check is the feeder line; its "not live"
        # branch is the zero-stage palette, so the chain starts dark.
        feeder_check = next(e for e in script if is_var_if(e, rosa.VAR_FEEDER_LIVE, 1))
        self.assertEqual({e["args"][f"palette{rosa.LINE_BG_SLOT}"] for e in feeder_check["children"]["false"]
                          if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"},
                         {scene.chain_palette_id(0)}, "the chain starts dark")
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        intro = [e for e in script if e["command"] == "EVENT_TEXT"]
        self.assertEqual([e["args"]["text"] for e in intro],
                         [["Priya's offline.\nDeadline: now!"], ["Sparks bite. Hop!"]])
        for line in LINES:
            self.assertIn((scene.actor_id(line["pole"]), "Snapped+Cable"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in script if e["command"] == "EVENT_ACTOR_SET_STATE"])

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
                    self.assertEqual(redraws[0]["args"]["text"], rosa.HUD_TEXT)
        # Authored in-play texts: two init boxes, Priya x3, the chain's cable ends and
        # boxes, door x2 (power, closed) and the no-power box, plus the exit refusal.
        self.assertGreaterEqual(checked, rosa.LINE_COUNT * 10)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(rosa.HUD_TEXT, f"LINES %D1${rosa.VAR_LINES_LIVE}$/5 HOME %D1${rosa.VAR_HOME_POWERED}$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws - {intro.dev_label()} - {None}, {rosa.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", rosa.HUD_TEXT)
        self.assertEqual(tokens, ["22", "11"])
        self.assertTrue(all(len(token) == 2 for token in tokens))
        self.assertLessEqual(len(re.sub(r"%D1\$\d+\$", "00", rosa.HUD_TEXT)), 20,
                             "HUD must fit the 20-tile overlay row")

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
                        self.assertNotIn("’", part, "use ASCII apostrophes in dialogue")
                        checked += 1
        self.assertGreaterEqual(checked, rosa.LINE_COUNT * 18)

    def test_cable_drop_runs_before_respawn_in_player_hit(self):
        hit = built_scene()["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT", "death sound plays first")
        respawn = next(i for i, e in enumerate(hit) if is_var_if(e, rosa.VAR_HOME_POWERED, 0))
        for line in LINES:
            drop = next(i for i, e in enumerate(hit)
                        if is_var_if(e, rosa.VAR_CARRYING_CABLE, line["number"]))
            self.assertLess(drop, respawn)
            drop_events = hit[drop]["children"]["true"]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in drop_events))
            self.assertIn((scene.actor_id(line["pole"]), "Snapped+Cable"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in drop_events if e["command"] == "EVENT_ACTOR_SET_STATE"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_SHOW" for e in drop_events))
        flat = list(walk(hit))
        first_move = next(i for i, e in enumerate(flat) if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertGreater(first_move, 0)

    def test_respawn_goes_to_the_furthest_checkpoint_before_power_and_to_door_after(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, rosa.VAR_HOME_POWERED, 0))
        moves = [(e["args"]["x"]["value"], e["args"]["y"]["value"])
                 for e in walk(branch["children"]["true"]) if e["command"] == "EVENT_ACTOR_SET_POSITION"]
        expected = {rosa.START, *(line["checkpoint"] for line in LINES)}
        self.assertEqual(set(moves), expected, "respawn lands on START or a repaired line's checkpoint")
        # The furthest repaired line wins: the house line (last) is tested first.
        self.assertTrue(is_var_if(branch["children"]["true"][0], rosa.VAR_LINE_LIVE, 1))
        door = branch["children"]["false"][0]
        door_x, door_y = rosa.HOUSE_DOOR
        self.assertEqual((door["args"]["x"]["value"], door["args"]["y"]["value"]),
                         (door_x - 1, door_y), "respawn stands in front of the door")

    def test_door_is_gated_on_both_lines_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         rosa.DOOR_TRIGGER)
        script = trigger["script"]
        line = next(e for e in script if is_var_if(e, rosa.VAR_LINES_LIVE, rosa.LINE_COUNT))
        power = next(e for e in line["children"]["true"] if is_var_if(e, rosa.VAR_HOME_POWERED, 0))
        reward = power["children"]["true"]
        self.assertTrue(any(is_set(e, rosa.VAR_HOME_POWERED, 1) for e in reward))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" for e in reward))
        window = next(e for e in reward if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(window["args"][f"palette{rosa.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:powered_window"))
        states = {(e["args"]["actorId"], e["args"]["spriteStateId"])
                  for e in reward if e["command"] == "EVENT_ACTOR_SET_STATE"}
        self.assertEqual(states, {(scene.actor_id(scene.ROSA_KEY), "Relieved"),
                                  (scene.actor_id(scene.WORKSTATION_KEY), "On")})
        self.assertEqual([e["args"]["text"] for e in reward if e["command"] == "EVENT_TEXT"],
                         [["Priya:\nRouter's alive!\nEmail, here I go!"], tickets.closed_lines(3)])
        dead = line["children"]["false"]
        self.assertEqual(texts(dead), [["Still no power.\nFix all 5 lines!"]])
        # Only the door's reward writes var 11 to 1; init writes 0 and nothing else touches it.
        writers_to_one = [e for script in all_script_lists() for e in walk(script)
                          if e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "11"
                          and var_value(e) == 1]
        self.assertEqual([e["id"] for e in writers_to_one],
                         [e["id"] for e in walk(reward) if is_set(e, rosa.VAR_HOME_POWERED, 1)])

    def test_arc_and_gust_start_delays_are_distinct_and_run_once(self):
        self.assertEqual(len(rosa.ARC_START_DELAYS), len(rosa.ARC_LANES))
        self.assertEqual(len(rosa.GUST_START_DELAYS), len(rosa.GUST_LANES))
        self.assertEqual(len(set(rosa.ARC_START_DELAYS + rosa.GUST_START_DELAYS)),
                         len(rosa.ARC_START_DELAYS + rosa.GUST_START_DELAYS),
                         "no two hazards may fire in lockstep")
        arcs = [a for a in built_actors() if a["symbol"].startswith("signal_arc_")]
        gusts = [a for a in built_actors() if a["symbol"].startswith("signal_gust_")]
        self.assertEqual(len(arcs), len(rosa.ARC_LANES))
        self.assertEqual(len(gusts), len(rosa.GUST_LANES))
        cases = [
            (arcs, rosa.ARC_LANES, rosa.ARC_START_DELAYS, rosa.ARC_SPRITE_ID,
             ["Warning", "Arc"], [rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES]),
            (gusts, rosa.GUST_LANES, rosa.GUST_START_DELAYS, FAKE_SPRITES["gust"],
             ["Warning", "Burst"], [rosa.GUST_WARNING_FRAMES, rosa.GUST_ACTIVE_FRAMES, rosa.GUST_REST_FRAMES]),
        ]
        for actors, lanes, delays, sprite, states_expected, loops_expected in cases:
            for actor, lane, delay in zip(actors, lanes, delays):
                row, x0, _ = lane
                self.assertEqual((actor["x"], actor["y"]), (x0, row))
                self.assertEqual(actor["collisionGroup"], "1")
                self.assertEqual(actor["spriteSheetId"], sprite)
                self.assertEqual(actor["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
                update = actor["updateScript"]
                guard = update[0]
                self.assertEqual(guard["command"], "EVENT_IF_ACTOR_DIRECTION")
                self.assertEqual(guard["args"]["direction"]["value"], "down")
                waits = [e for e in walk(guard["children"]["true"]) if e["command"] == "EVENT_WAIT"]
                if delay:
                    self.assertEqual([w["args"]["frames"]["value"] for w in waits], [delay])
                else:
                    self.assertEqual(waits, [])
                # Only the first-cycle branch holds the start delay; the loop waits are the hazard's own.
                loop_waits = [e["args"]["frames"]["value"] for e in update[1:]
                              if e["command"] == "EVENT_WAIT"]
                self.assertEqual(loop_waits, loops_expected)
                states = [e["args"]["spriteStateId"] for e in update
                          if e["command"] == "EVENT_ACTOR_SET_STATE"]
                self.assertEqual(states, states_expected)
                self.assertFalse(any(e["command"] == "EVENT_ACTOR_COLLISIONS_ENABLE"
                                     for e in walk(guard["children"]["true"])),
                                 "start delay must not enable the hazard early")
                # Rest leaves the hazard hidden and safe.
                rest = update[-3:]
                self.assertEqual([e["command"] for e in rest[:2]],
                          ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
        hazard_indices = [a["_index"] for a in built_actors()
                          if a["symbol"].startswith(("signal_arc_", "signal_gust_"))]
        first_hazard = 2 + 2 * rosa.LINE_COUNT   # Priya, her workstation, then pole-and-box pairs
        self.assertEqual(hazard_indices, list(range(first_hazard, first_hazard + len(arcs) + len(gusts))))

    def test_hidden_cable_starts_dark_and_has_one_timed_arc_window(self):
        actor = actor_by_symbol("signal_hidden_cable_01")
        row, x0, _ = hazards.HIDDEN_CABLES["signal_hill"][0]
        self.assertEqual((actor["x"], actor["y"]), (x0, row))
        self.assertEqual(actor["collisionGroup"], "1")
        self.assertEqual([e["command"] for e in actor["startScript"]],
                         ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
        update = actor["updateScript"]
        self.assertEqual([e["command"] for e in update[:2]],
                         ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
        first = next(e for e in update if e["command"] == "EVENT_IF_ACTOR_DIRECTION")
        self.assertEqual([e["args"]["frames"]["value"] for e in first["children"]["true"]
                          if e["command"] == "EVENT_WAIT"],
                         hazards.CABLE_START_DELAYS["signal_hill"])
        self.assertEqual([e["args"]["spriteStateId"] for e in update
                          if e["command"] == "EVENT_ACTOR_SET_STATE"], ["Warning", "Arc"])
        commands = [e["command"] for e in update]
        self.assertLess(commands.index("EVENT_ACTOR_SHOW"), commands.index("EVENT_ACTOR_COLLISIONS_ENABLE"))

    def test_board_trigger_and_actor_use_the_contract_rectangle_and_number(self):
        board = hazards.BOARDS["signal_hill"][0]
        actor = actor_by_symbol("signal_board_01")
        trigger = trigger_by_symbol("trigger_signal_cracked_board_01")
        self.assertEqual((actor["x"], actor["y"]), hazards.board_actor_position(board))
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         hazards.board_trigger_rect(board))
        self.assertEqual(var_value(trigger["script"][0]), 1)
        self.assertEqual(actor["collisionGroup"], "1")
        self.assertEqual(actor["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_every_view_stays_within_ten_sprites_per_scanline(self):
        # Count real 8x16 OBJ tiles from the sprite sidecars, including all hazards.
        actors = built_actors()
        profiles = sprite_profiles(PROJECT_DIR)
        for spot in spots():
            load, _ = sprite_budget(PROJECT_DIR, actors, spot, rosa.MAP_W, rosa.MAP_H,
                                    profiles=profiles)
            self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (spot, load))

    def test_every_view_stays_within_the_active_actor_limit(self):
        actors = built_actors()
        profiles = sprite_profiles(PROJECT_DIR)
        for spot in spots():
            _, near = sprite_budget(PROJECT_DIR, actors, spot, rosa.MAP_W, rosa.MAP_H,
                                    profiles=profiles)
            self.assertLessEqual(len(near), rosa.MAX_ACTIVE_ACTORS, (spot, near))

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        house = LINES[-1]
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual(pole["id"], scene.actor_id("pole"))
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertEqual((pole["x"], pole["y"]), house["pole_at"])
        self.assertTrue(pole["animate"])
        self.assertEqual(pole["script"], [], "pole is not interactive")
        self.assertEqual(pole["collisionGroup"], "", "pole does not collide")
        self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE",
                         "B must find the cable end on the pole's tile (B-13)")
        start = pole["startScript"][1]
        self.assertTrue(is_var_if(start, rosa.VAR_LINE_LIVE, 1))
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["true"]], [("$self$", "Standing")])
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["false"]], [("$self$", "Snapped+Cable")])
        init = built_scene()["script"]
        self.assertIn((scene.pole_actor_id(), "Snapped+Cable"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_every_pole_starts_snapped_unless_its_line_is_live(self):
        for line in LINES:
            pole = actor_by_symbol(line["pole_symbol"])
            self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
            start = pole["startScript"][1]
            self.assertTrue(is_var_if(start, line["live_var"], 1))
            self.assertEqual([e["args"]["spriteStateId"] for e in start["children"]["true"]], ["Standing"])
            self.assertEqual([e["args"]["spriteStateId"] for e in start["children"]["false"]],
                             ["Snapped+Cable"])

    def test_feeder_pole_stands_on_the_upper_step(self):
        feeder = LINES[0]
        self.assertEqual(feeder["pole_at"], (7, 8))
        self.assertEqual(rosa.collision_grid()[feeder["pole_at"][1] + 1][feeder["pole_at"][0]],
                         climb.COL_SOLID)

    def test_b16_feeder_pit_ledge_and_reach_trigger_are_preserved(self):
        self.assertIn((4, 8, 12, 14), rosa.SOLID_BLOCKS)
        self.assertIn((6, 8, 9, 11), rosa.SOLID_BLOCKS)
        self.assertEqual(rosa.LEDGES, [(13, 10, 10)])
        trigger = trigger_by_symbol("trigger_signal_feeder_reach")
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         (9, 12, 2, 3))
        grid = rosa.collision_grid()
        self.assertTrue(all(grid[row][x] == climb.COL_EMPTY
                            for row in (12, 14) for x in (9, 10)))
        self.assertEqual(grid[13][9], climb.COL_EMPTY)
        self.assertEqual(grid[13][10], climb.COL_TOP)

    def test_storm_pole_palette_has_its_own_slot(self):
        sprites = built_scene()["spritePaletteIds"]
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertNotEqual(intro.SPRITE_SLOTS["pole"], rosa.ARC_SPRITE_PALETTE_SLOT)

    def test_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        expected = [scene.ROSA_SYMBOL, scene.WORKSTATION_SYMBOL]
        for line in LINES:
            expected.extend((line["pole_symbol"], line["box_symbol"]))
        expected += [f"signal_arc_{n:02d}" for n in range(1, len(rosa.ARC_LANES) + 1)]
        expected += [f"signal_gust_{n:02d}" for n in range(1, len(rosa.GUST_LANES) + 1)]
        expected += [f"signal_span_arc_{n:02d}" for n in range(1, len(rosa.span_arc_lanes()) + 1)]
        expected += [f"signal_whip_{n:02d}" for n in range(1, len(rosa.WHIP_LANES) + 1)]
        expected += [f"signal_hidden_cable_{n:02d}"
                     for n in range(1, len(hazards.HIDDEN_CABLES["signal_hill"]) + 1)]
        expected += [f"signal_board_{n:02d}"
                     for n in range(1, len(hazards.BOARDS["signal_hill"]) + 1)]
        self.assertEqual(symbols, expected)
        self.assertFalse(any("debris" in s for s in symbols), "no debris in Signal Hill")
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertEqual(len(actors), rosa.actor_count())
        self.assertEqual(len(actors), rosa.MAX_SCENE_ACTORS, "full hazard kit fits the 20-actor budget")
        self.assertLessEqual(len(actors), rosa.MAX_SCENE_ACTORS)
        rosa_actor = actor_by_symbol(scene.ROSA_SYMBOL)
        self.assertEqual((rosa_actor["x"], rosa_actor["y"]), rosa.ROSA)
        self.assertEqual(rosa_actor["spriteSheetId"], rosa.ROSA_SPRITE_ID)
        self.assertEqual(rosa_actor["startScript"][0]["args"]["spriteStateId"], "Waiting")
        self.assertTrue(rosa_actor["animate"])
        self.assertEqual(rosa_actor["collisionGroup"], "")
        ws = actor_by_symbol(scene.WORKSTATION_SYMBOL)
        self.assertEqual((ws["x"], ws["y"]), rosa.WORKSTATION)
        self.assertEqual(ws["spriteSheetId"], rosa.WORKSTATION_SPRITE_ID)
        self.assertEqual(ws["startScript"][0]["args"]["spriteStateId"], "Off")
        for line in LINES:
            pole = actor_by_symbol(line["pole_symbol"])
            self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
            self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
            self.assertNotIn(line["cable_symbol"], symbols)
            box = actor_by_symbol(line["box_symbol"])
            self.assertEqual((box["x"], box["y"]), line["box_at"])
            self.assertEqual(box["startScript"][0]["args"]["spriteStateId"], "Dead")
        transformer = actor_by_symbol("signal_feeder_transformer")
        self.assertEqual(transformer["spriteSheetId"], ridge.TRANSFORMER_SPRITE_ID,
                         "the Wind Ridge transformer asset, reused")
        junction = actor_by_symbol("signal_junction_box")
        self.assertEqual(junction["spriteSheetId"], ridge.TRANSFORMER_SPRITE_ID)  # house box matches every transformer
        arc = actor_by_symbol("signal_arc_01")
        self.assertEqual(arc["spriteSheetId"], rosa.ARC_SPRITE_ID)
        self.assertEqual(arc["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_rosa_talk_tracks_home_and_both_lines(self):
        script = actor_by_symbol(scene.ROSA_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], rosa.VAR_HOME_POWERED, 1))
        self.assertEqual(texts(script[0]["children"]["true"]), [["Priya:\nBack online!\nYou're a star!"]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], rosa.VAR_LINES_LIVE, rosa.LINE_COUNT))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual(texts(live), [["Priya:\nFive lines live!\nTry my door."]])
        self.assertEqual(texts(dead), [["Priya:\nNo wifi, no work.\nSend help!"]])

    def test_each_box_takes_only_its_own_cable_and_counts_the_line(self):
        zones, _ = b_zones(b_script())
        for line in LINES:
            [invoke] = zones[grid_chain.BOX_ZONE + line["number"]]
            script = box_script(line)
            self.assertEqual(invoke["command"], "EVENT_CALL_CUSTOM_EVENT")
            self.assertEqual(invoke["args"]["customEventId"], script["id"])
            expected_actor_args = {
                f"$actor[{index}]$": actor_id
                for index, (actor_id, _name) in enumerate(scene.CHAIN.box_script_actor_bindings(line))
            }
            self.assertEqual({key: value for key, value in invoke["args"].items()
                              if key.startswith("$actor[")}, expected_actor_args)
            self.assertEqual(actor_by_symbol(line["box_symbol"])["script"], [])
            [live] = script["script"]
            self.assertTrue(is_var_if(live, line["live_var"], 1))
            self.assertEqual(texts(live["children"]["true"]), [["Already fixed."]])
            has_cable = next(e for e in live["children"]["false"]
                             if is_var_if(e, rosa.VAR_CARRYING_CABLE, line["number"]))
            branch = has_cable["children"]["true"]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in branch))
            self.assertTrue(any(is_set(e, line["live_var"], 1) for e in branch))
            self.assertEqual([e["args"]["variable"] for e in branch if e["command"] == "EVENT_INC_VALUE"],
                             [rosa.VAR_LINES_LIVE])
            pole_arg = box_script_actor_arg(line, scene.actor_id(line["pole"]))
            self.assertIn((pole_arg, "Standing"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"])
            # Both wire slots change for five stages; no unrelated BG slot may change.
            for palette in (e for e in walk(branch) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"):
                self.assertEqual({k for k, v in palette["args"].items() if v != "keep"},
                                 {f"palette{rosa.LINE_BG_SLOT}", f"palette{rosa.LINE_BG_SLOT_2}"})
            [other] = has_cable["children"]["false"]
            self.assertTrue(is_var_if(other, rosa.VAR_CARRYING_CABLE, 0))
            self.assertEqual(texts(other["children"]["true"]), [["No cable yet.\nFind its pole."]])
            self.assertEqual(texts(other["children"]["false"]), [["Wrong cable\nfor this box."]])
        incs = [e for script in all_script_lists() for e in walk(script) if e["command"] == "EVENT_INC_VALUE"]
        # One connect path per box, reached only from its B press: one count per line, nothing else.
        self.assertEqual(len(incs), rosa.LINE_COUNT, "nothing else changes the counter")

    def test_power_reaches_a_box_only_through_every_line_upstream(self):
        zones, _ = b_zones(b_script())
        for line in LINES:
            [invoke] = zones[grid_chain.BOX_ZONE + line["number"]]
            self.assertEqual(invoke["command"], "EVENT_CALL_CUSTOM_EVENT")
            script = box_script(line)
            self.assertEqual(invoke["args"]["customEventId"], script["id"])
            [live] = script["script"]
            has_cable = next(e for e in live["children"]["false"]
                             if is_var_if(e, rosa.VAR_CARRYING_CABLE, line["number"]))
            plugged = has_cable["children"]["true"]
            commands = [e["command"] for e in plugged]
            # The chain refresh (which sets VAR_CHAIN_LIVE) runs before the message reads it.
            refresh = next(i for i, e in enumerate(plugged)
                           if any(is_set(x, rosa.VAR_CHAIN_LIVE, 0) for x in walk([e])))
            message = plugged[-1]
            self.assertLess(refresh, len(commands) - 1)
            self.assertTrue(is_var_if(message, rosa.VAR_CHAIN_LIVE, rosa.LINE_COUNT))
            self.assertEqual(texts(message["children"]["true"]), [["All 5 lines live!\nGo see Priya."]])
            [lit] = message["children"]["false"]
            self.assertTrue(is_at_least(lit, rosa.VAR_CHAIN_LIVE, line["number"]))
            self.assertEqual(texts(lit["children"]["true"]), [["Power flows on!\nKeep going."]])
            self.assertEqual(texts(lit["children"]["false"]), [["Fixed. No power\nfrom upstream."]])

    def test_chain_lights_wires_and_boxes_only_as_far_as_continuous(self):
        refresh = scene.chain_refresh_events("probe")

        def outcome(live):
            events = refresh
            while len(events) == 1 and events[0]["command"] == "EVENT_IF":
                variable = events[0]["args"]["condition"]["valueA"]["value"]
                events = events[0]["children"]["true" if live[variable] else "false"]
            palette_event = next(e["args"] for e in events
                                 if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
            palette = {slot: palette_event[f"palette{slot}"]
                       for slot in (rosa.LINE_BG_SLOT, rosa.LINE_BG_SLOT_2)}
            stages_set = next(var_value(e) for e in events if e["command"] == "EVENT_SET_VALUE"
                              and e["args"]["variable"] == rosa.VAR_CHAIN_LIVE)
            boxes = {e["args"]["actorId"]: e["args"]["spriteStateId"] for e in events
                     if e["command"] == "EVENT_ACTOR_SET_STATE"}
            return palette, boxes, stages_set

        for bits in itertools.product((0, 1), repeat=len(LINES)):
            live = {line["live_var"]: bit for line, bit in zip(LINES, bits)}
            stages = next((i for i, bit in enumerate(bits) if not bit), len(LINES))
            palette, boxes, stages_set = outcome(live)
            self.assertEqual(palette, {
                rosa.LINE_BG_SLOT: grid_chain.chain_palette_id(rosa.resource_id, stages,
                                                              rosa.LINE_BG_SLOT),
                rosa.LINE_BG_SLOT_2: grid_chain.chain_palette_id(rosa.resource_id, stages,
                                                                 rosa.LINE_BG_SLOT_2),
            }, bits)
            self.assertEqual(stages_set, stages, bits)
            for line in LINES:
                self.assertEqual(boxes[scene.actor_id(line["box"])],
                                 "Live" if line["number"] <= stages else "Dead", (bits, line["key"]))

    def test_chain_palettes_light_stages_in_order(self):
        palettes = {p["id"]: p["colors"] for _, p in scene.rosa_palettes()}
        for stages, colors in rosa.CHAIN_PALETTES.items():
            for slot in (rosa.LINE_BG_SLOT, rosa.LINE_BG_SLOT_2):
                self.assertEqual(palettes[grid_chain.chain_palette_id(rosa.resource_id, stages, slot)],
                                 colors[slot])
            for stage, index in enumerate(rosa.STAGE_COLOR_INDEX, start=1):
                slot = rosa.LINE_BG_SLOT if stage <= 3 else rosa.LINE_BG_SLOT_2
                self.assertEqual(palettes[grid_chain.chain_palette_id(rosa.resource_id, stages, slot)][index],
                                 rosa.WIRE_LIVE if stage <= stages else rosa.WIRE_DEAD)
        self.assertEqual(len(rosa.STAGE_COLOR_INDEX), rosa.LINE_COUNT, "one colour per line")

    def test_pickup_is_b_in_the_pole_zone_with_empty_hands_and_dead_line(self):
        zones, _ = b_zones(b_script())
        for line in LINES:
            [empty] = zones[line["number"]]
            self.assertTrue(is_var_if(empty, rosa.VAR_CARRYING_CABLE, 0))
            [dead] = empty["children"]["true"]
            self.assertTrue(is_var_if(dead, line["live_var"], 0))
            take = dead["children"]["true"]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, line["number"]) for e in take))
            self.assertIn((scene.actor_id(line["pole"]), "Snapped"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in take if e["command"] == "EVENT_ACTOR_SET_STATE"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_HIDE" for e in take))
            self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                                e["args"]["type"] == FAKE_AUDIO["pickup"] for e in take))
            self.assertEqual(texts(empty["children"]["false"]), [["Hands full!\nOne cable a trip."]])

    def test_b_away_from_every_zone_drops_the_carried_cable_to_its_pole(self):
        attach = b_script()
        zones, rest = b_zones(attach)
        self.assertTrue(attach["args"]["override"], "one B press must dispatch either talk or a cable action")
        self.assertEqual(texts(list(walk(zones[grid_chain.NPC_ZONE]))),
                         texts(list(walk(actor_by_symbol(scene.ROSA_SYMBOL)["script"]))))
        self.assertNotIn(["Cable dropped."], texts(list(walk(zones[grid_chain.NPC_ZONE]))))
        [drop] = rest
        self.assertTrue(is_at_least(drop, rosa.VAR_CARRYING_CABLE, 1))
        branches = {e["args"]["condition"]["valueB"]["value"]: e["children"]["true"]
                    for e in drop["children"]["true"] if e["command"] == "EVENT_IF"}
        self.assertEqual(set(branches), {line["number"] for line in LINES})
        for line in LINES:
            branch = branches[line["number"]]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in branch))
            self.assertIn((scene.actor_id(line["pole"]), "Snapped+Cable"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_SHOW" for e in branch))
            self.assertEqual(texts(branch), [["Cable dropped."]])

    def test_zone_triggers_set_near_on_enter_and_clear_only_their_own_value(self):
        triggers = {t["symbol"]: t for t in built_triggers()}
        expected = {}
        for line in LINES:
            expected[f"trigger_signal_{line['key']}_reach"] = grid_chain.BOX_ZONE + line["number"]
            expected[f"trigger_signal_{line['key']}_pole_zone"] = line["number"]
        self.assertEqual(set(zone_symbols()), set(expected))
        for symbol, value in expected.items():
            zone = triggers[symbol]
            [enter] = zone["script"]
            self.assertEqual((enter["command"], enter["args"]["variable"], var_value(enter)),
                             ("EVENT_SET_VALUE", climb.VAR_NEAR, value), symbol)
            [leave] = zone["leaveScript"]
            self.assertTrue(is_var_if(leave, climb.VAR_NEAR, value), symbol)

    def test_standing_on_any_box_tile_resolves_to_that_boxs_zone(self):
        # The engine fires the first listed trigger that covers the hero, so a hero
        # on a box's own tiles must resolve to that box's zone, not a neighbour's.
        triggers = built_triggers()
        for line in LINES:
            for tile in box_tiles(line["box_at"]):
                hit = first_hit(triggers, tile)
                self.assertIsNotNone(hit, (line["key"], tile))
                self.assertEqual(hit["symbol"], "trigger_signal_" + line["key"] + "_reach",
                                 (line["key"], tile))
        house = LINES[-1]
        approach = (house["box_at"][0] - 1, house["box_at"][1])
        self.assertEqual(first_hit(triggers, approach)["symbol"], "trigger_signal_house_reach")

    def test_zones_fit_the_trigger_budget_and_clear_the_exit_and_door(self):
        triggers = built_triggers()
        self.assertEqual(len(triggers), 2 + len(hazards.BOARDS["signal_hill"]) + 2 * len(LINES),
                         "five lines, full hazards and exits use 13 triggers; talk uses a position test")
        self.assertLessEqual(len(triggers), grid_chain.MAX_TRIGGERS)

        def rect(t):
            return (t["x"], t["y"], t["width"], t["height"])

        def overlap(a, b):
            return (a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3])

        for index, trigger in enumerate(triggers):
            for other in triggers[index + 1:]:
                self.assertFalse(overlap(rect(trigger), rect(other)),
                                 (trigger["symbol"], other["symbol"]))

    def test_checked_in_files_match_the_builders(self):
        """Run after make_rosa_scene.py: disk must match the in-memory build."""
        music = shared.sidecar_id(scene.MUSIC_SIDECAR, "music")
        audio = {
            "death": shared.sidecar_id(scene.DEATH_SOUND, "sound"),
            "connect": shared.sidecar_id(scene.CONNECT_SOUND, "sound"),
            "pickup": shared.sidecar_id(scene.PICKUP_SOUND, "sound"),
        }
        sprites = {"gust": shared.sidecar_id(scene.GUST_SPRITE, "sprite")}
        expected = scene.build_scene(music, audio)
        self.assertEqual(shared.load_json(scene.SCENE_DIR / "scene.gbsres"), expected)
        for actor in scene.build_actors(sprites, audio):
            path = scene.SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), actor)
        for trigger in scene.build_triggers(audio):
            path = scene.SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), trigger)
        for relative, script in scene.box_script_resources(audio):
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), script)
        for relative, palette in scene.rosa_palettes():
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), palette)

    def test_palette_slots_and_palette_resources(self):
        resource = built_scene()
        template = shared.load_json(scene.CLIMB_SCENE)
        sprites = resource["spritePaletteIds"]
        self.assertEqual(len(sprites), 8)
        self.assertEqual(sprites[0], opening.resource_id("palette:sprite:worker"))
        self.assertEqual(sprites[rosa.ROSA_SPRITE_PALETTE_SLOT], scene.rosa_palette_id())
        self.assertEqual(sprites[rosa.GRID_SPRITE_PALETTE_SLOT],
                         climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(sprites[rosa.ARC_SPRITE_PALETTE_SLOT], scene.arc_palette_id())
        self.assertEqual(sprites[hazards.BOARD_SPRITE_PALETTE_SLOT], hazards.BOARD_PALETTE_ID)
        self.assertEqual(sprites[rosa.GUST_SPRITE_PALETTE_SLOT], template["spritePaletteIds"][5])
        self.assertEqual(sprites[rosa.WHIP_SPRITE_PALETTE_SLOT], rosa.WHIP_PALETTE_ID)
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertEqual(rosa.ROSA_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(rosa.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(rosa.ARC_SPRITE_PALETTE_SLOT, 3)
        self.assertEqual(rosa.GUST_SPRITE_PALETTE_SLOT, 5)
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[rosa.LINE_BG_SLOT], scene.chain_palette_id(0))
        self.assertEqual(backgrounds[rosa.LINE_BG_SLOT_2],
                         grid_chain.chain_palette_id(rosa.resource_id, 0, rosa.LINE_BG_SLOT_2))
        self.assertEqual(backgrounds[7], "default-ui")
        palettes = dict(scene.rosa_palettes())
        rosa_palette = palettes["project/palettes/signal_hill_sprite_rosa.gbsres"]
        arc_palette = palettes["project/palettes/signal_hill_sprite_arc.gbsres"]
        self.assertEqual(rosa_palette["id"], scene.rosa_palette_id())
        self.assertEqual(arc_palette["id"], scene.arc_palette_id())
        self.assertEqual(rosa_palette["colors"], [
            rosa.ROSA_SPRITE_HARDWARE[1], rosa.ROSA_SPRITE_HARDWARE[2],
            rosa.ROSA_SPRITE_HARDWARE[3], rosa.ROSA_SPRITE_HARDWARE[3],
        ])
        self.assertEqual(arc_palette["colors"], [
            rosa.ARC_SPRITE_HARDWARE[1], rosa.ARC_SPRITE_HARDWARE[2],
            rosa.ARC_SPRITE_HARDWARE[3], rosa.ARC_SPRITE_HARDWARE[3],
        ])
        self.assertNotEqual(rosa_palette["id"], arc_palette["id"])
        for stages in rosa.CHAIN_PALETTES:
            self.assertIn(f"project/palettes/signal_hill_bg_chain_{stages}_live.gbsres", palettes)
            self.assertIn(f"project/palettes/signal_hill_bg_chain_{stages}_live_slot_6.gbsres", palettes)
        self.assertEqual(sum("_bg_chain_" in path for path in palettes), 2 * (rosa.LINE_COUNT + 1))

    def test_shared_sidecars_exist(self):
        """Sounds, music, the gust sprite and the reused transformer are already on disk."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)
        self.assertTrue((PROJECT_DIR / "assets/sprites/transformer.png.gbsres").exists())

    def test_each_box_has_a_zone_on_open_air_that_arms_its_own_plug_in(self):
        # B-06: walking up to a box arms its B press (the zone sets var 27); the press
        # plugs the cable in. T1 sits in the pit between the step and the storm-pole rock,
        # so its zone is the pit.
        grid = rosa.collision_grid()
        for line in scene.LINES:
            trigger = trigger_by_symbol(f"trigger_signal_{line['key']}_reach")
            rect = (trigger["x"], trigger["y"], trigger["width"], trigger["height"])
            self.assertEqual(rect, line.get("reach") or grid_chain.reach_rect(line["box_at"]))
            x, y, w, h = rect
            self.assertTrue(all(grid[r][c] in (climb.COL_EMPTY, climb.COL_TOP)
                                for r in range(y, y + h) for c in range(x, x + w)),
                            f"{line['key']} trigger in rock")
            [enter] = trigger["script"]
            self.assertTrue(is_set(enter, climb.VAR_NEAR, grid_chain.BOX_ZONE + line["number"]))
        self.assertEqual(trigger_by_symbol("trigger_signal_feeder_reach")["x"], rosa.LINES[0]["box"][0])

    def test_hollow_exit_leads_to_pine_hollow_only_after_rosa_is_powered(self):
        trigger = trigger_by_symbol("trigger_signal_hollow_exit")
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         kiko.HILL_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "11"})
        cutoff, hide, ticket, switch = gate["children"]["true"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        # Work order 4 first; its card then switches to the next job's start.
        self.assertEqual((ticket["args"]["variable"], ticket["args"]["value"]["value"]),
                         (tickets.VAR_TICKET, 4))
        self.assertEqual(switch["args"]["sceneId"], tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(tickets.TICKETS[4]["scene_id"], kiko.SCENE_ID)
        self.assertEqual(tickets.TICKETS[4]["start"], kiko.START)
        refused = gate["children"]["false"]
        self.assertNotIn("EVENT_ACTOR_SET_POSITION", [e["command"] for e in walk(refused)])
        tx, _, tw, _ = rosa.DOOR_TRIGGER
        self.assertGreaterEqual(trigger["x"], tx + tw)


if __name__ == "__main__":
    unittest.main()
