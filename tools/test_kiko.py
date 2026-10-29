"""Pine Hollow checks: python3 -m unittest discover -s tools -p test_kiko.py (or cd tools)."""
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
import make_kiko_scene as scene
import opening
import ridge
import rosa
import kiko
from test_grid_chain import sprite_budget, sprite_profiles

# Hermetic fixtures: the builders only reference these IDs, so fixed strings
# keep the structural tests independent of which art sidecars exist yet.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
PROJECT_DIR = scene.PROJECT_DIR


def built_scene():
    return scene.build_scene(FAKE_MUSIC, FAKE_AUDIO)


def built_actors():
    return scene.build_actors(FAKE_AUDIO)


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


def stands(grid, x, y):
    """A 24px hero at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == climb.COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (climb.COL_TOP, climb.COL_SOLID))


def budget_spots():
    """Every collision-supported hero tile plus explicit props/checkpoints/hazards."""
    grid = kiko.collision_grid()
    found = {(x, y) for y in range(2, kiko.MAP_H - 1) for x in range(1, kiko.MAP_W - 1)
             if grid_chain.stands(grid, x, y)}
    found.update((kiko.START, kiko.HOUSE_DOOR))
    for line in scene.LINES:
        found.update((line["pole_at"], line["box_at"], line["checkpoint"]))
    found.update((x0, row + 1) for row, x0, _ in kiko.hazard_lanes())
    found.update((x0, row + 1) for row, x0, _ in hazards.HIDDEN_CABLES["pine_hollow"])
    return sorted(found)


def overlaps(a, b):
    """Two (x, y, w, h) rectangles in pixels overlap."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def hero_px(x, feet):
    """The 24px hero's pixel rectangle standing with feet on tile row ``feet``."""
    return (x * 8, (feet - 2) * 8, 24, 24)


def tile_px(x, y, w=1, h=1):
    return (x * 8, y * 8, w * 8, h * 8)


def walk_texts(events):
    """Every EVENT_TEXT string, in order, anywhere under ``events``."""
    return [e["args"]["text"] for e in walk(events) if e["command"] == "EVENT_TEXT"]


def set_positions(events):
    return [(e["args"]["x"]["value"], e["args"]["y"]["value"])
            for e in walk(events) if e["command"] == "EVENT_ACTOR_SET_POSITION"]


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


class KikoTests(unittest.TestCase):
    def test_ids_are_stable_and_unique(self):
        ids = {
            "scene": kiko.SCENE_ID,
            "background": kiko.BACKGROUND_ID,
            "kiko_sprite": kiko.KIKO_SPRITE_ID,
            "stove_sprite": kiko.STOVE_SPRITE_ID,
            "arc_sprite": kiko.ARC_SPRITE_ID,
            "kiko_palette": scene.kiko_palette_id(),
            "trigger": kiko.resource_id("trigger:kiko-door"),
        }
        actor_ids = [a["id"] for a in built_actors()]
        ids.update({f"actor{i}": value for i, value in enumerate(actor_ids)})
        ids.update({f"box_script{i}": script["id"]
                    for i, (_, script) in enumerate(box_script_resources())})
        self.assertEqual(len(set(ids.values())), len(ids), "resource IDs collide")
        self.assertEqual(kiko.resource_id("scene:pine-hollow"), kiko.SCENE_ID)
        self.assertNotEqual(kiko.resource_id("actor:kiko"), kiko.resource_id("trigger:kiko-door"))
        self.assertNotIn(kiko.SCENE_ID, {rosa.SCENE_ID, rosa.BACKGROUND_ID, rosa.ROSA_SPRITE_ID})
        self.assertEqual(built_scene(), built_scene(), "scene build is deterministic")
        self.assertEqual(built_actors(), built_actors(), "actor build is deterministic")

    def test_event_ids_are_unique_within_the_scene(self):
        seen = []
        for script in all_script_lists():
            seen.extend(entry["id"] for entry in walk(script))
        self.assertTrue(seen)
        self.assertEqual(len(seen), len(set(seen)), "duplicate event ID inside pine_hollow")

    def test_scene_fields_match_pine_hollow_contract(self):
        resource = built_scene()
        self.assertEqual(resource["name"], "Pine Hollow")
        self.assertEqual(resource["symbol"], "scene_pine_hollow")
        self.assertEqual(resource["type"], "PLATFORM")
        self.assertEqual((resource["width"], resource["height"]), (100, 18))
        self.assertEqual(resource["backgroundId"], kiko.BACKGROUND_ID)
        self.assertEqual(resource["id"], kiko.SCENE_ID)
        self.assertEqual(resource["_resourceType"], "scene")
        self.assertEqual(resource["tilesetId"], "", "tilesets are not used by this job")
        self.assertEqual(resource["_index"], 6, "next index after signal_hill (5)")
        self.assertEqual((resource["x"], resource["y"]), (1200, 360))
        taken = []
        for path in (PROJECT_DIR / "project" / "scenes").glob("*/scene.gbsres"):
            if path.parent.name != "pine_hollow":
                other = shared.load_json(path)
                taken.append((other["_index"], other["x"], other["y"]))
        self.assertNotIn((resource["_index"], resource["x"], resource["y"]), taken,
                         "editor index and position must be free")
        self.assertNotIn(resource["_index"], [t[0] for t in taken], "scene index must be unique")

    def test_five_line_route_preserves_the_opening_mesa_and_full_hazard_kit(self):
        self.assertEqual((kiko.MAP_W, kiko.MAP_H), (100, 18))
        self.assertIn((5, 6, 12, 14), kiko.SOLID_BLOCKS)
        self.assertIn((7, 18, 9, 14), kiko.SOLID_BLOCKS)
        self.assertEqual((kiko.DAMAGED_POLE, kiko.FEEDER_BOX), ((9, 8), (16, 8)))
        self.assertEqual(hazards.HIDDEN_CABLES["pine_hollow"], [(7, 11, 12)])
        self.assertEqual([(line["key"], line["pole"], line["box"], line["checkpoint"], line["live_var"])
                          for line in kiko.LINES], [
            ("feeder", (9, 8), (16, 8), (14, 8), "24"),
            ("west", (22, 11), (35, 14), (36, 14), "33"),
            ("middle", (41, 8), (57, 8), (58, 8), "34"),
            ("east", (61, 11), (70, 8), (71, 8), "35"),
            ("house", (74, 8), (89, 11), (88, 11), "12"),
        ])
        self.assertEqual(kiko.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual(kiko.actor_count(), kiko.MAX_SCENE_ACTORS)

    def test_collisions_match_contract(self):
        resource = built_scene()
        self.assertEqual(decode_rle(resource["collisions"]),
                         [cell for row in kiko.collision_grid() for cell in row])
        self.assertEqual(
            shared.collision_rle(kiko.collision_grid(), kiko.MAP_W, kiko.MAP_H),
            resource["collisions"],
        )

    def test_variables_register_without_changing_existing(self):
        base = shared.load_json(PROJECT_DIR / "project" / "variables.gbsres")
        merged = scene.merged_variables(base)
        self.assertEqual(scene.merged_variables(merged), merged, "registration is idempotent")
        self.assertEqual(merged["variables"][:len(base["variables"])], base["variables"])
        by_id = {v["id"]: v for v in merged["variables"]}
        self.assertEqual(by_id[kiko.VAR_LINE_LIVE],
                         {"id": "12", "name": "Hollow Line Live", "symbol": "var_hollow_line_live"})
        self.assertEqual(by_id[kiko.VAR_HOME_POWERED],
                         {"id": "13", "name": "Kiko Home Powered", "symbol": "var_kiko_home_powered"})
        self.assertEqual(by_id["6"]["symbol"], "var_carrying_cable")
        self.assertEqual(by_id[climb.VAR_NEAR], {"id": "27", "name": "Chain Near", "symbol": "var_chain_near"})
        self.assertEqual(by_id["10"]["symbol"], "var_hill_line_live")
        self.assertEqual(by_id["11"]["symbol"], "var_rosa_home_powered")

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(12)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:12], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(12)]
                         + [v[0] for v in kiko.VARIABLES if v[0] not in {str(i) for i in range(12)}]
                         + [hazards.VAR_ON_BOARD, climb.VAR_NEAR])
        self.assertEqual(by_id["24"]["symbol"], "var_hollow_feeder_live")
        self.assertEqual(by_id["25"]["symbol"], "var_hollow_lines_live")
        self.assertEqual(by_id["26"]["symbol"], "var_hollow_chain_live")
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "12", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_line(self):
        script = built_scene()["script"]
        for variable in (kiko.VAR_CARRYING_CABLE, kiko.VAR_LINE_LIVE, kiko.VAR_HOME_POWERED,
                         kiko.VAR_FEEDER_LIVE, kiko.VAR_LINES_LIVE, kiko.VAR_CHAIN_LIVE,
                         *(line["live_var"] for line in scene.LINES)):
            self.assertTrue(any(is_set(e, variable, 0) for e in script),
                            f"init must reset var {variable}")
        for variable in ("4", "10", "11"):
            self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == variable
                                 for e in script), f"init must not reset var {variable}")
        commands = [e["command"] for e in script]
        self.assertEqual(commands[:2], ["EVENT_PLAYER_SET_SPRITE", "EVENT_ACTOR_SET_DIRECTION"])
        self.assertEqual(script[0]["args"]["spriteSheetId"],
                         opening.resource_id("sprite:opening_worker24"))
        self.assertEqual(script[1]["args"]["direction"]["value"], "right")
        palette_events = [e for e in script if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertEqual(palette_events[0]["args"][f"palette{kiko.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:window"))
        # The wire slot starts with no stage lit: the chain's zero-stage palette.
        lit_zero = [e for e in walk(script) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"
                    and e["args"][f"palette{kiko.LINE_BG_SLOT}"] != "keep"]
        self.assertTrue(lit_zero)
        self.assertEqual({e["args"][f"palette{kiko.LINE_BG_SLOT}"] for e in lit_zero},
                         {scene.chain_palette_id(stages) for stages in range(kiko.STAGE_COUNT + 1)})
        self.assertEqual({e["args"][f"palette{kiko.LINE_BG_SLOT_2}"] for e in lit_zero},
                         {grid_chain.chain_palette_id(kiko.resource_id, stages, kiko.LINE_BG_SLOT_2)
                          for stages in range(kiko.STAGE_COUNT + 1)})
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        intro = [e for e in script if e["command"] == "EVENT_TEXT"]
        self.assertEqual([e["args"]["text"] for e in intro],
                         [["Emil's house is\ndark and hungry!"], ["Fix 5 lines,\nthen soup!"],
                          ["Dinner's cold..."]])

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
                    self.assertEqual(redraws[0]["args"]["text"], kiko.HUD_TEXT)
        # Authored in-play texts: two intro boxes, Emil x3, cable pickup, junction x3, door x2.
        # Intro x3, Emil x4, two chain ends and three boxes each (status + pickup/no cable),
        # door x2 + CLOSED box, report-exit refusal; the B drop's line once per branch.
        self.assertGreaterEqual(checked, kiko.LINE_COUNT * 10)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(kiko.HUD_TEXT, f"LINES %D1${kiko.VAR_LINES_LIVE}$/5 HOME %D1${kiko.VAR_HOME_POWERED}$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws - {intro.dev_label()} - {None}, {kiko.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", kiko.HUD_TEXT)
        self.assertEqual(tokens, [kiko.VAR_LINES_LIVE, kiko.VAR_HOME_POWERED])
        self.assertTrue(all(len(token) == 2 for token in tokens))
        self.assertLessEqual(len(re.sub(r"%D1\$\d+\$", "00", kiko.HUD_TEXT)), 20,
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
        # One part per line; two-line boxes count each part.
        self.assertGreaterEqual(checked, kiko.LINE_COUNT * 18)

    def test_cable_drop_runs_before_respawn_in_player_hit(self):
        hit = built_scene()["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT", "death sound plays first")
        drop = next(i for i, e in enumerate(hit)
                    if is_var_if(e, kiko.VAR_CARRYING_CABLE, 1))
        respawn = next(i for i, e in enumerate(hit) if is_var_if(e, kiko.VAR_HOME_POWERED, 0))
        self.assertLess(drop, respawn)
        drop_events = hit[drop]["children"]["true"]
        self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, 0) for e in drop_events))
        self.assertIn((scene.actor_id(scene.POLE_KEY), "Snapped+Cable"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in drop_events if e["command"] == "EVENT_ACTOR_SET_STATE"])
        self.assertFalse(any(e["command"] == "EVENT_ACTOR_SHOW" for e in drop_events))
        flat = list(walk(hit))
        first_move = next(i for i, e in enumerate(flat) if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertGreater(first_move, 0)

    def test_respawn_follows_the_chain_before_power_and_to_door_after(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, kiko.VAR_HOME_POWERED, 0))
        # Before Emil's power: the furthest repaired line's checkpoint, else START.
        self.assertEqual(set(set_positions(branch["children"]["true"])),
                         {kiko.START, *(line["checkpoint"] for line in scene.LINES)})
        self.assertEqual(set_positions(branch["children"]["true"])[-1], kiko.START,
                         "START is the fallback, reached when no line is live")
        house = next(e for e in branch["children"]["true"] if is_var_if(e, kiko.VAR_LINE_LIVE, 1))
        self.assertEqual(set_positions(house["children"]["true"]), [kiko.HOUSE_CHECKPOINT])
        door = branch["children"]["false"][0]
        door_x, door_y = kiko.HOUSE_DOOR
        self.assertEqual((door["args"]["x"]["value"], door["args"]["y"]["value"]),
                         (door_x - 1, door_y), "respawn stands in front of the door")

    def test_door_is_gated_on_live_line_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         kiko.DOOR_TRIGGER)
        script = trigger["script"]
        # The door needs every line in the five-line chain.
        line = next(e for e in script if is_var_if(e, kiko.VAR_LINES_LIVE, kiko.LINE_COUNT))
        power = next(e for e in line["children"]["true"]
                     if is_var_if(e, kiko.VAR_HOME_POWERED, 0))
        reward = power["children"]["true"]
        self.assertTrue(any(is_set(e, kiko.VAR_HOME_POWERED, 1) for e in reward))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" for e in reward))
        window = next(e for e in reward if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(window["args"][f"palette{kiko.WINDOW_BG_SLOT}"],
                         opening.resource_id("palette:bg:powered_window"))
        states = {(e["args"]["actorId"], e["args"]["spriteStateId"])
                  for e in reward if e["command"] == "EVENT_ACTOR_SET_STATE"}
        self.assertEqual(states, {(scene.actor_id(scene.KIKO_KEY), "Relieved"),
                                  (scene.actor_id(scene.STOVE_KEY), "On")})
        self.assertEqual([e["args"]["text"] for e in reward if e["command"] == "EVENT_TEXT"],
                         [["Emil:\nStove's on!\nSoup party!"], tickets.closed_lines(4)])
        dead = line["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                          [["Still no power.\nFix all 5 lines!"]])
        # Only the door's reward writes var 13 to 1; init writes 0 and nothing else touches it.
        writers_to_one = [e for script in all_script_lists() for e in walk(script)
                          if e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "13"
                          and var_value(e) == 1]
        self.assertEqual([e["id"] for e in writers_to_one],
                         [e["id"] for e in walk(reward) if is_set(e, kiko.VAR_HOME_POWERED, 1)])

    def test_arc_start_delays_run_once(self):
        self.assertEqual(len(kiko.ARC_START_DELAYS), len(kiko.ARC_LANES))
        arcs = [a for a in built_actors() if a["symbol"].startswith("pine_arc_")]
        self.assertEqual(len(arcs), len(kiko.ARC_LANES))
        cases = [
            (arcs, kiko.ARC_LANES, kiko.ARC_START_DELAYS, kiko.ARC_SPRITE_ID,
             ["Warning", "Arc"], [kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES]),
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
                          if a["symbol"].startswith("pine_arc_")]
        first_hazard = 2 + 2 * kiko.LINE_COUNT
        self.assertEqual(hazard_indices, list(range(first_hazard, first_hazard + len(arcs))))

    def test_hidden_cable_lane_is_open_air_on_the_mesa(self):
        grid = kiko.collision_grid()
        for row, x0, x1 in hazards.HIDDEN_CABLES["pine_hollow"]:
            for x in range(x0, x1 + 1):
                self.assertEqual(grid[row][x], climb.COL_EMPTY)
                self.assertEqual(grid[row + 1][x], climb.COL_EMPTY)
                self.assertEqual(grid[row + 2][x], climb.COL_SOLID, "mesa rock under the lane")

    def test_hidden_cable_is_hidden_and_group_one_until_it_arcs(self):
        cable = actor_by_symbol("pine_hidden_cable_01")
        row, x0, _ = hazards.HIDDEN_CABLES["pine_hollow"][0]
        self.assertEqual((cable["x"], cable["y"]), (x0, row))
        self.assertEqual(cable["collisionGroup"], "1")
        self.assertEqual(cable["spriteSheetId"], kiko.ARC_SPRITE_ID)
        self.assertEqual([e["command"] for e in cable["startScript"]],
                         ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
        update = cable["updateScript"]
        commands = [e["command"] for e in update]
        self.assertEqual(commands[:2], ["EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE"])
        enables = [i for i, c in enumerate(commands) if c == "EVENT_ACTOR_COLLISIONS_ENABLE"]
        self.assertEqual(len(enables), 1, "one hitbox window per arc")
        self.assertLess(commands.index("EVENT_ACTOR_SHOW"), enables[0])
        self.assertEqual([e["args"]["spriteStateId"] for e in update
                          if e["command"] == "EVENT_ACTOR_SET_STATE"], ["Warning", "Arc"])
        first = next(e for e in update if e["command"] == "EVENT_IF_ACTOR_DIRECTION")
        self.assertEqual([e["args"]["frames"]["value"] for e in first["children"]["true"]
                          if e["command"] == "EVENT_WAIT"], [hazards.CABLE_START_DELAYS["pine_hollow"][0]])

    def test_board_trigger_and_actor_use_the_contract_rectangle_and_number(self):
        board = hazards.BOARDS["pine_hollow"][0]
        actor = actor_by_symbol("pine_board_01")
        trigger = trigger_by_symbol("trigger_pine_cracked_board_01")
        self.assertEqual((actor["x"], actor["y"]), hazards.board_actor_position(board))
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         hazards.board_trigger_rect(board))
        self.assertEqual(var_value(trigger["script"][0]), 1)
        self.assertEqual(actor["collisionGroup"], "1")
        self.assertEqual(actor["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_every_view_stays_within_ten_sprites_per_scanline(self):
        actors = built_actors()
        profiles = sprite_profiles(PROJECT_DIR)
        for spot in budget_spots():
            load, _ = sprite_budget(PROJECT_DIR, actors, spot, kiko.MAP_W, kiko.MAP_H,
                                    profiles=profiles)
            self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (spot, load))

    def test_every_view_stays_within_the_active_actor_limit(self):
        actors = built_actors()
        profiles = sprite_profiles(PROJECT_DIR)
        for spot in budget_spots():
            _, near = sprite_budget(PROJECT_DIR, actors, spot, kiko.MAP_W, kiko.MAP_H,
                                    profiles=profiles)
            self.assertLessEqual(len(near), kiko.MAX_ACTIVE_ACTORS, (spot, near))

    def test_chain_wire_routes_are_continuous_and_stage_coloured(self):
        grid_chain.check_wire_routes(kiko.WIRE_ROUTES, kiko.STAGE_COUNT, kiko.MAP_W, kiko.HUD_ROWS,
                                     kiko.GROUND_ROW)
        self.assertEqual(kiko.STAGE_COLOR_INDEX, [1, 3, 2, 1, 3])
        self.assertEqual(kiko.WIRE_ROUTES[0][1][0], (0, kiko.OVERHEAD), "power enters at the left edge")
        self.assertEqual(kiko.WIRE_ROUTES[-1][1][-1][0], kiko.HOUSE_RECT[0], "the chain ends at the house")

    def test_lines_are_feeder_then_house_with_their_checkpoints(self):
        self.assertEqual([line["key"] for line in scene.LINES],
                         ["feeder", "west", "middle", "east", "house"])
        feeder, house = scene.LINES[0], scene.LINES[-1]
        self.assertEqual((feeder["number"], feeder["live_var"]), (1, kiko.VAR_FEEDER_LIVE))
        self.assertEqual((house["number"], house["live_var"]), (5, kiko.VAR_LINE_LIVE))
        self.assertEqual(feeder["pole_at"], kiko.DAMAGED_POLE)
        self.assertEqual(feeder["box_at"], kiko.FEEDER_BOX)
        self.assertEqual(house["pole_at"], kiko.HOUSE_POLE)
        self.assertEqual(house["box_at"], kiko.JUNCTION_BOX)
        # Legacy keys: the mesa's pole and cable end, and the porch's junction box.
        self.assertEqual((feeder["pole"], feeder["cable"], house["box"]),
                         (scene.POLE_KEY, scene.CABLE_KEY, scene.JUNCTION_KEY))
        self.assertLess(feeder["box_at"][0], house["pole_at"][0])
        self.assertLess(house["pole_at"][0], house["box_at"][0])

    def test_actor_count_stays_within_the_engine_budget(self):
        actors = built_actors()
        self.assertLessEqual(len(actors), kiko.MAX_SCENE_ACTORS, "gbvm allows 20 actors besides the player")
        self.assertEqual(len(actors), kiko.actor_count())
        self.assertEqual(len(actors), kiko.MAX_SCENE_ACTORS, "full hazard kit fits the 20-actor budget")

    def test_each_line_has_a_box_zone_that_arms_only_its_own_plug_in(self):
        triggers = built_triggers()
        for line in scene.LINES:
            trigger = trigger_by_symbol(f"trigger_pine_{line['key']}_reach")
            self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                             line.get("reach") or grid_chain.reach_rect(line["box_at"]))
            reach_end = trigger["x"] + trigger["width"]
            self.assertIn(reach_end, (line["box_at"][0], line["box_at"][0] + 2),
                          "reach is either the three approach tiles or approach plus box")
            [enter] = trigger["script"]
            self.assertTrue(is_set(enter, climb.VAR_NEAR, grid_chain.BOX_ZONE + line["number"]),
                            "the zone arms this line's box only")
            [leave] = trigger["leaveScript"]
            self.assertTrue(is_var_if(leave, climb.VAR_NEAR, grid_chain.BOX_ZONE + line["number"]))
            self.assertEqual(sum(t["_index"] == trigger["_index"] for t in triggers), 1,
                             "trigger indices are unique")
        self.assertEqual([t["symbol"] for t in triggers[2:]],
                         ["trigger_pine_cracked_board_01"]
                         + [f"trigger_pine_{line['key']}_reach" for line in scene.LINES]
                         + [f"trigger_pine_{line['key']}_pole_zone" for line in scene.LINES])
        self.assertEqual([t["_index"] for t in triggers], list(range(len(triggers))))

    def test_global_b_invokes_the_matching_box_actor_script(self):
        zones, _ = b_zones(b_script())
        for line in scene.LINES:
            with self.subTest(line=line["key"]):
                [invoke] = zones[grid_chain.BOX_ZONE + line["number"]]
                script = box_script(line)
                self.assertEqual(invoke["command"], "EVENT_CALL_CUSTOM_EVENT")
                self.assertEqual(invoke["args"]["customEventId"], script["id"])
                self.assertTrue(script["script"], "the canonical script owns the large repair/refresh body")
                self.assertEqual(actor_by_symbol(line["box_symbol"])["script"], [])
                expected_actor_args = {
                    f"$actor[{index}]$": actor_id
                    for index, (actor_id, _name) in enumerate(scene.CHAIN.box_script_actor_bindings(line))
                }
                self.assertEqual({key: value for key, value in invoke["args"].items()
                                  if key.startswith("$actor[")}, expected_actor_args)

    def test_house_box_zone_covers_the_dynamic_house_box_position(self):
        # The house box zone includes the player's standing rectangle on the porch.
        trigger = trigger_by_symbol("trigger_pine_house_reach")
        trig = tile_px(trigger["x"], trigger["y"], trigger["width"], trigger["height"])
        hero = ((kiko.JUNCTION_BOX[0] - 1) * 8 + 3, (kiko.PORCH_ROW - 2) * 8, 24, 24)
        self.assertTrue(overlaps(hero, trig), "hero is inside the house box zone")
        self.assertEqual(trigger["x"], kiko.JUNCTION_BOX[0] - 3)
        [enter] = trigger["script"]
        self.assertTrue(is_set(enter, climb.VAR_NEAR, grid_chain.BOX_ZONE + kiko.LINE_COUNT))

    def test_standing_on_any_box_tile_resolves_to_that_boxs_zone(self):
        # The engine fires the first listed trigger that covers the hero, so a hero
        # on a box's own tiles must resolve to that box's zone, not a neighbour's.
        triggers = built_triggers()
        for line in scene.LINES:
            for tile in box_tiles(line["box_at"]):
                hit = first_hit(triggers, tile)
                self.assertIsNotNone(hit, (line["key"], tile))
                self.assertEqual(hit["symbol"], "trigger_pine_" + line["key"] + "_reach",
                                 (line["key"], tile))

    def test_reach_triggers_do_not_overlap_the_exit_or_the_door(self):
        triggers = built_triggers()
        self.assertEqual(len(triggers), 2 + len(hazards.BOARDS["pine_hollow"]) + 2 * len(scene.LINES),
                         "five lines, full hazards and exits use 13 triggers; talk uses a position test")
        self.assertLessEqual(len(triggers), grid_chain.MAX_TRIGGERS)
        rects = {t["symbol"]: (t["x"], t["y"], t["width"], t["height"]) for t in triggers}
        items = list(rects.items())
        for index, (name, rect) in enumerate(items):
            for other, other_rect in items[index + 1:]:
                self.assertFalse(overlaps(tile_px(*rect), tile_px(*other_rect)), (name, other))
        self.assertEqual(rects[scene.DOOR_TRIGGER_SYMBOL], kiko.DOOR_TRIGGER)

    def test_checkpoint_positions_are_clear_of_the_door_and_the_hazards(self):
        grid = kiko.collision_grid()
        for line in scene.LINES:
            x, y = line["checkpoint"]
            self.assertTrue(stands(grid, x, y), line["checkpoint"])
        self.assertLess(kiko.HOUSE_CHECKPOINT[0], kiko.DOOR_TRIGGER[0], "house checkpoint stays off the door")

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual(pole["id"], scene.actor_id("pole"))
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertEqual((pole["x"], pole["y"]), kiko.DAMAGED_POLE)
        self.assertTrue(pole["animate"])
        self.assertEqual(pole["script"], [], "pole is not interactive")
        self.assertEqual(pole["collisionGroup"], "", "pole does not collide")
        self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE",
                         "B must find the cable end on the pole's tile (B-13)")
        start = pole["startScript"][1]
        self.assertTrue(is_var_if(start, kiko.VAR_FEEDER_LIVE, 1))
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["true"]], [("$self$", "Standing")])
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["false"]], [("$self$", "Snapped+Cable")])
        init = built_scene()["script"]
        self.assertIn((scene.pole_actor_id(), "Snapped+Cable"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_storm_pole_palette_has_its_own_slot(self):
        sprites = built_scene()["spritePaletteIds"]
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertNotEqual(intro.SPRITE_SLOTS["pole"], kiko.ARC_SPRITE_PALETTE_SLOT)

    def test_report_exit_follows_emils_house_and_wins_over_the_door(self):
        triggers = scene.build_triggers({"connect": "sfx"})
        exit_, door = triggers[:2]
        self.assertEqual(exit_["symbol"], "trigger_pine_report_exit")
        self.assertLess(exit_["_index"], door["_index"], "first matching trigger wins (B-05)")
        self.assertEqual((exit_["x"], exit_["y"], exit_["width"], exit_["height"]), tickets.REPORT_EXIT)
        [gate] = exit_["script"]
        self.assertTrue(is_var_if(gate, kiko.VAR_HOME_POWERED, 1))
        switch = gate["children"]["true"][-1]
        self.assertEqual(switch["args"]["sceneId"], tickets.REPORT_SCENE_ID)

    def test_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        expected = [scene.KIKO_SYMBOL, scene.STOVE_SYMBOL]
        for line in scene.LINES:
            expected.extend((line["pole_symbol"], line["box_symbol"]))
        expected += [f"pine_arc_{n:02d}" for n in range(1, len(kiko.ARC_LANES) + 1)]
        expected += [f"pine_gust_{n:02d}" for n in range(1, len(kiko.GUST_LANES) + 1)]
        expected += [f"pine_span_arc_{n:02d}" for n in range(1, len(kiko.span_arc_lanes()) + 1)]
        expected += [f"pine_whip_{n:02d}" for n in range(1, len(kiko.WHIP_LANES) + 1)]
        expected += [f"pine_hidden_cable_{n:02d}"
                     for n in range(1, len(hazards.HIDDEN_CABLES["pine_hollow"]) + 1)]
        expected += [f"pine_board_{n:02d}"
                     for n in range(1, len(hazards.BOARDS["pine_hollow"]) + 1)]
        self.assertEqual(symbols, expected)
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertEqual(len(actors), kiko.MAX_SCENE_ACTORS)
        kiko_actor = actor_by_symbol(scene.KIKO_SYMBOL)
        self.assertEqual((kiko_actor["x"], kiko_actor["y"]), kiko.KIKO)
        self.assertEqual(kiko_actor["spriteSheetId"], kiko.KIKO_SPRITE_ID)
        self.assertEqual(kiko_actor["startScript"][0]["args"]["spriteStateId"], "Waiting")
        self.assertTrue(kiko_actor["animate"])
        self.assertEqual(kiko_actor["collisionGroup"], "")
        stove = actor_by_symbol(scene.STOVE_SYMBOL)
        self.assertEqual((stove["x"], stove["y"]), kiko.STOVE)
        self.assertEqual(stove["spriteSheetId"], kiko.STOVE_SPRITE_ID)
        self.assertEqual(stove["startScript"][0]["args"]["spriteStateId"], "Off")
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual((pole["x"], pole["y"]), kiko.DAMAGED_POLE)
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertNotIn(scene.CABLE_SYMBOL, symbols)
        junction = actor_by_symbol(scene.JUNCTION_SYMBOL)
        self.assertEqual((junction["x"], junction["y"]), kiko.JUNCTION_BOX)
        self.assertEqual(junction["spriteSheetId"], ridge.TRANSFORMER_SPRITE_ID)  # house box matches every transformer
        self.assertEqual(junction["startScript"][0]["args"]["spriteStateId"], "Dead")
        self.assertFalse([a for a in actors if "debris" in a["symbol"]])
        arc = actor_by_symbol("pine_span_arc_01")
        self.assertEqual(arc["spriteSheetId"], kiko.ARC_SPRITE_ID)
        self.assertEqual(arc["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_kiko_talk_tracks_home_and_line(self):
        script = actor_by_symbol(scene.KIKO_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], kiko.VAR_HOME_POWERED, 1))
        self.assertEqual([e["args"]["text"] for e in script[0]["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Emil:\nDinner time!\nThank you!"]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], kiko.VAR_LINES_LIVE, kiko.LINE_COUNT))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in live if e["command"] == "EVENT_TEXT"],
                          [["Emil:\nAll 5 lines live!\nTry our door."]])
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Emil:\nStove's dead.\nMy tummy growls!"]])

    def test_junction_plugs_carried_cable_once_and_lights_line(self):
        zones, _ = b_zones(b_script())
        [invoke] = zones[grid_chain.BOX_ZONE + kiko.LINE_COUNT]
        script = box_script(scene.LINES[-1])
        self.assertEqual(invoke["command"], "EVENT_CALL_CUSTOM_EVENT")
        self.assertEqual(invoke["args"]["customEventId"], script["id"])
        [live] = script["script"]
        self.assertTrue(is_var_if(live, kiko.VAR_LINE_LIVE, 1))
        self.assertEqual(walk_texts(live["children"]["true"]), [["Line is live."]])
        has_cable = next(e for e in live["children"]["false"]
                         if is_var_if(e, kiko.VAR_CARRYING_CABLE, kiko.LINE_COUNT))
        branch = has_cable["children"]["true"]
        self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, 0) for e in branch))
        self.assertTrue(any(is_set(e, kiko.VAR_LINE_LIVE, 1) for e in branch))
        self.assertEqual(sum(is_set(e, kiko.VAR_LINE_LIVE, 1) for e in walk(branch)), 1)
        states = [e["args"]["spriteStateId"] for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"]
        # The hero drops the Carry pose, then the house pole stands; the box's own state comes from the chain.
        self.assertEqual(states, ["", "Standing"])
        junction = box_script_actor_arg(scene.LINES[-1], scene.actor_id(scene.JUNCTION_KEY))
        box_states = {e["args"]["spriteStateId"] for e in walk(branch)
                      if e["command"] == "EVENT_ACTOR_SET_STATE" and e["args"]["actorId"] == junction}
        self.assertEqual(box_states, {"Live", "Dead"}, "the chain refresh sets the box Live or Dead")
        # The status line names how far power reaches once the house line is in.
        self.assertEqual(walk_texts(branch), [["All 5 lines live!\nGo see Emil."],
                                               ["Power flows on!\nKeep going."],
                                              ["Fixed. No power\nfrom upstream."]])
        # Empty hands at a dead line point back to the pole, like the other jobs.
        self.assertEqual(walk_texts(has_cable["children"]["false"])[0], ["No cable yet.\nCheck the pole."])

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        zones, _ = b_zones(b_script())
        for line in scene.LINES:
            number, live_var = line["number"], line["live_var"]
            [empty] = zones[number]
            self.assertTrue(is_var_if(empty, kiko.VAR_CARRYING_CABLE, 0))
            dead = next(e for e in empty["children"]["true"] if is_var_if(e, live_var, 0))
            take = dead["children"]["true"]
            self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, number) for e in take))
            self.assertIn((scene.actor_id(line["pole"]), "Snapped"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in take if e["command"] == "EVENT_ACTOR_SET_STATE"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_HIDE" for e in take))
            self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                                e["args"]["type"] == FAKE_AUDIO["pickup"] for e in take))
        feeder = next(e for e in zones[1][0]["children"]["true"] if is_var_if(e, kiko.VAR_FEEDER_LIVE, 0))
        self.assertTrue(any(e["command"] == "EVENT_TEXT" and
                            e["args"]["text"] == ["Got the cable!\nTo the box ahead."]
                            for e in feeder["children"]["true"]))
        self.assertEqual(walk_texts(zones[1][0]["children"]["false"]), [["Hands full!\nOne cable a trip."]])

    def test_b_away_from_every_zone_drops_the_carried_cable_to_its_pole(self):
        attach = b_script()
        zones, rest = b_zones(attach)
        self.assertTrue(attach["args"]["override"], "one B press must dispatch either talk or a cable action")
        self.assertEqual(walk_texts(zones[grid_chain.NPC_ZONE]),
                         walk_texts(actor_by_symbol(scene.KIKO_SYMBOL)["script"]))
        self.assertNotIn(["Cable dropped."], walk_texts(zones[grid_chain.NPC_ZONE]))
        [drop] = rest
        branches = {e["args"]["condition"]["valueB"]["value"]: e["children"]["true"]
                    for e in drop["children"]["true"] if e["command"] == "EVENT_IF"}
        self.assertEqual(set(branches), {line["number"] for line in scene.LINES})
        for number in range(1, kiko.LINE_COUNT + 1):
            self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, 0) for e in branches[number]))
            line = next(line for line in scene.LINES if line["number"] == number)
            self.assertIn((scene.actor_id(line["pole"]), "Snapped+Cable"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in branches[number] if e["command"] == "EVENT_ACTOR_SET_STATE"])
            self.assertFalse(any(e["command"] == "EVENT_ACTOR_SHOW" for e in branches[number]))
            self.assertEqual(walk_texts(branches[number]), [["Cable dropped."]])

    def test_checked_in_files_match_the_builders(self):
        """Run after make_kiko_scene.py: disk must match the in-memory build."""
        music = shared.sidecar_id(scene.MUSIC_SIDECAR, "music")
        audio = {
            "death": shared.sidecar_id(scene.DEATH_SOUND, "sound"),
            "connect": shared.sidecar_id(scene.CONNECT_SOUND, "sound"),
            "pickup": shared.sidecar_id(scene.PICKUP_SOUND, "sound"),
        }
        expected = scene.build_scene(music, audio)
        self.assertEqual(shared.load_json(scene.SCENE_DIR / "scene.gbsres"), expected)
        for actor in scene.build_actors(audio):
            path = scene.SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), actor)
        for trigger in scene.build_triggers(audio):
            path = scene.SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), trigger)
        for relative, script in scene.box_script_resources(audio):
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), script)
        for relative, palette in scene.kiko_palettes():
            self.assertEqual(shared.load_json(PROJECT_DIR / relative), palette)
        on_disk = shared.load_json(scene.VARIABLES_PATH)
        self.assertEqual(scene.merged_variables(on_disk), on_disk, "variables registered on disk")

    def test_palette_slots_and_palette_resources(self):
        resource = built_scene()
        template = shared.load_json(scene.CLIMB_SCENE)
        sprites = resource["spritePaletteIds"]
        self.assertEqual(len(sprites), 8)
        self.assertEqual(sprites[0], opening.resource_id("palette:sprite:worker"))
        self.assertEqual(sprites[kiko.KIKO_SPRITE_PALETTE_SLOT], scene.kiko_palette_id())
        self.assertEqual(sprites[kiko.GRID_SPRITE_PALETTE_SLOT],
                         climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(sprites[kiko.ARC_SPRITE_PALETTE_SLOT], rosa.resource_id("palette:sprite:arc"))
        self.assertEqual(sprites[hazards.BOARD_SPRITE_PALETTE_SLOT], hazards.BOARD_PALETTE_ID)
        self.assertEqual(sprites[kiko.GUST_SPRITE_PALETTE_SLOT], template["spritePaletteIds"][5])
        self.assertEqual(sprites[kiko.WHIP_SPRITE_PALETTE_SLOT], ridge.WHIP_PALETTE_ID)
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertEqual(kiko.KIKO_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(kiko.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(kiko.ARC_SPRITE_PALETTE_SLOT, 3)
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[kiko.LINE_BG_SLOT], scene.chain_palette_id(0), "the wire slot starts dark")
        self.assertEqual(backgrounds[kiko.LINE_BG_SLOT_2],
                         grid_chain.chain_palette_id(kiko.resource_id, 0, kiko.LINE_BG_SLOT_2))
        self.assertEqual(backgrounds[7], "default-ui")
        palettes = dict(scene.kiko_palettes())
        self.assertEqual(len(palettes), 1 + (kiko.STAGE_COUNT + 1) * 2,
                         "Emil's sprite plus both wire palettes per chain count")
        chain_files = sorted(p for p in palettes if "_bg_chain_" in p)
        expected_files = {f"project/palettes/pine_hollow_bg_chain_{n}_live.gbsres"
                          for n in range(kiko.STAGE_COUNT + 1)}
        expected_files |= {f"project/palettes/pine_hollow_bg_chain_{n}_live_slot_6.gbsres"
                           for n in range(kiko.STAGE_COUNT + 1)}
        self.assertEqual(set(chain_files), expected_files)
        self.assertEqual({palettes[p]["id"] for p in chain_files},
                         {grid_chain.chain_palette_id(kiko.resource_id, n, slot)
                          for n in range(kiko.STAGE_COUNT + 1)
                          for slot in (kiko.LINE_BG_SLOT, kiko.LINE_BG_SLOT_2)})
        kiko_palette = palettes["project/palettes/pine_hollow_sprite_kiko.gbsres"]
        relative = "project/palettes/pine_hollow_sprite_kiko.gbsres"
        self.assertEqual(kiko_palette["id"], scene.kiko_palette_id())
        self.assertEqual(kiko_palette["colors"], [
            kiko.KIKO_SPRITE_HARDWARE[1], kiko.KIKO_SPRITE_HARDWARE[2],
            kiko.KIKO_SPRITE_HARDWARE[3], kiko.KIKO_SPRITE_HARDWARE[3],
        ])
        self.assertNotEqual(kiko_palette["id"], scene.arc_palette_id())
        self.assertEqual(scene.arc_palette_id(), rosa.resource_id("palette:sprite:arc"),
                         "arc palette is Signal Hill's resource, not a duplicate")

    def test_shared_sidecars_exist(self):
        """Sounds, music and Signal Hill's arc are already on disk."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR):
            self.assertTrue((PROJECT_DIR / path).exists(), path)
        arc_palette = shared.load_json(PROJECT_DIR / "project" / "palettes" / "signal_hill_sprite_arc.gbsres")
        self.assertEqual(arc_palette["id"], scene.arc_palette_id())
        live_arc = shared.load_json(PROJECT_DIR / "assets" / "sprites" / "live_arc.png.gbsres")
        self.assertEqual(live_arc["id"], kiko.ARC_SPRITE_ID, "Emil reuses Signal Hill's live arc sprite")


if __name__ == "__main__":
    unittest.main()


class PorchExitPriorityTests(unittest.TestCase):
    """The engine fires the first trigger the hero's box overlaps.

    At the right wall the hero overlaps both the door trigger and the porch
    exit, so the exit must sort first or the next job is unreachable (cart
    ROM 6bfec7b4: Signal Hill could not be reached from Hiroshi's porch).
    """

    def test_porch_exit_sorts_before_the_door(self):
        import json
        from pathlib import Path
        scenes = Path(__file__).resolve().parent.parent / "project" / "scenes"
        for scene in ("wind_ridge", "signal_hill"):
            triggers = sorted((json.loads(p.read_text()) for p in
                               (scenes / scene / "triggers").glob("*.gbsres")),
                              key=lambda t: t["_index"])
            first = json.dumps(triggers[0]["script"])
            self.assertIn("EVENT_SWITCH_SCENE", first, scene)
