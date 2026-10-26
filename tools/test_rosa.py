"""Signal Hill checks: python3 -m unittest discover -s tools -p test_rosa.py (or cd tools)."""
import json
import re
import unittest
from pathlib import Path

import climb
import make_climb_scene as shared
import make_rosa_scene as scene
import opening
import rosa
import kiko

# Hermetic fixtures: the builders only reference these IDs, so fixed strings
# keep the structural tests independent of which art sidecars exist yet.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite"}
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


def sprite_load(sprites):
    """OBJ columns per tile row. Each entry is ((x, feet_row), width_tiles, height_tiles)."""
    load = {}
    for (_, feet), width, height in sprites:
        for row in range(feet - height + 1, feet + 1):
            load[row] = load.get(row, 0) + width
    return load


def hazard_sprites():
    """Every live arc and gust, all visible at once (the worst case for a scanline)."""
    sprites = [((x0, row), 2, 2) for row, x0, _ in rosa.ARC_LANES]
    sprites += [((x0, row), 3, 2) for row, x0, _ in rosa.GUST_LANES]
    return sprites


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
        self.assertEqual(len(set(ids.values())), len(ids), "resource IDs collide")
        self.assertEqual(rosa.resource_id("scene:signal-hill"), rosa.SCENE_ID)
        self.assertNotEqual(rosa.resource_id("actor:rosa"), rosa.resource_id("trigger:rosa-door"))
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
        self.assertEqual((resource["width"], resource["height"]), (40, 18))
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

    def test_collisions_match_contract(self):
        resource = built_scene()
        self.assertEqual(decode_rle(resource["collisions"]),
                         [cell for row in rosa.collision_grid() for cell in row])
        self.assertEqual(
            shared.collision_rle(rosa.collision_grid(), 40, 18),
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
        self.assertEqual(by_id["6"]["symbol"], "var_carrying_cable")
        self.assertEqual(by_id["7"]["symbol"], "var_line_live")
        self.assertEqual(by_id["8"]["symbol"], "var_ridge_line_live")
        self.assertEqual(by_id["9"]["symbol"], "var_tomas_home_powered")

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(8)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:8], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(8)] + ["10", "11"])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "10", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_line(self):
        script = built_scene()["script"]
        for variable in ("6", "10", "11"):
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
        self.assertEqual(palette_events[1]["args"][f"palette{rosa.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_dead"))
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        intro = [e for e in script if e["command"] == "EVENT_TEXT"]
        self.assertEqual([e["args"]["text"] for e in intro],
                         [["Rosa's offline!\nHer work is due."], ["Mind the sparks!"]])

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
        # Authored in-play texts: two init boxes, Rosa x3, cable pickup, junction x3, door x2.
        self.assertEqual(checked, 12)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(rosa.HUD_TEXT, "LINE %D1$10$/1 HOME %D1$11$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws, {rosa.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", rosa.HUD_TEXT)
        self.assertEqual(tokens, ["10", "11"])
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
        # One part per line; two-line boxes count each part.
        self.assertEqual(checked, 26)  # +4 "Rosa:" name lines

    def test_cable_drop_runs_before_respawn_in_player_hit(self):
        hit = built_scene()["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT", "death sound plays first")
        drop = next(i for i, e in enumerate(hit)
                    if is_var_if(e, rosa.VAR_CARRYING_CABLE, 1))
        respawn = next(i for i, e in enumerate(hit) if is_var_if(e, rosa.VAR_HOME_POWERED, 0))
        self.assertLess(drop, respawn)
        drop_events = hit[drop]["children"]["true"]
        self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in drop_events))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_SHOW" and
                            e["args"]["actorId"] == scene.actor_id(scene.CABLE_KEY)
                            for e in drop_events))
        flat = list(walk(hit))
        first_move = next(i for i, e in enumerate(flat) if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertGreater(first_move, 0)

    def test_respawn_goes_to_start_before_power_and_to_door_after(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, rosa.VAR_HOME_POWERED, 0))
        start = branch["children"]["true"][0]
        self.assertEqual(start["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((start["args"]["x"]["value"], start["args"]["y"]["value"]), rosa.START)
        door = branch["children"]["false"][0]
        door_x, door_y = rosa.HOUSE_DOOR
        self.assertEqual((door["args"]["x"]["value"], door["args"]["y"]["value"]),
                         (door_x - 1, door_y), "respawn stands in front of the door")

    def test_door_is_gated_on_live_line_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         rosa.DOOR_TRIGGER)
        script = trigger["script"]
        line = next(e for e in script if is_var_if(e, rosa.VAR_LINE_LIVE, 1))
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
                         [["Rosa:\nRouter's on!\nI'm online again."]])
        dead = line["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Still no power.\nFix the line!"]])
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
             ["Warning", "Arc"], [rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES]),
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
        self.assertEqual(hazard_indices, list(range(4, 4 + len(arcs) + len(gusts))))

    def test_house_view_stays_within_ten_sprites_per_scanline(self):
        # Same budget as Wind Ridge: count OBJ columns per tile row with the hero
        # standing at the junction box, Rosa and her workstation drawn, and every
        # arc and gust visible.
        bx, by = rosa.JUNCTION_BOX
        sprites = [((bx, by), 3, 3)]  # hero: 24px wide, 24px tall
        sprites += [(pos, 2, 2) for pos in (rosa.JUNCTION_BOX, rosa.ROSA, rosa.WORKSTATION)]
        sprites += hazard_sprites()
        load = sprite_load(sprites)
        self.assertLessEqual(max(load.values()), 10, load)

    def test_floor_between_hazards_stays_within_ten_sprites_per_scanline(self):
        # Every floor tile the hero can stand on, with all arcs and the gust visible.
        grid = rosa.collision_grid()
        feet = rosa.GROUND_ROW - 1
        standing = [x for x in range(1, rosa.MAP_W - 1)
                    if all(grid[r][x] == climb.COL_EMPTY for r in (feet, feet - 1, feet - 2))
                    and grid[rosa.GROUND_ROW][x] == climb.COL_SOLID]
        self.assertTrue(standing)
        for x in standing:
            sprites = [((x, feet), 3, 3)] + hazard_sprites()
            load = sprite_load(sprites)
            self.assertLessEqual(max(load.values()), 10, (x, load))

    def test_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        self.assertEqual(symbols, [
            scene.ROSA_SYMBOL, scene.WORKSTATION_SYMBOL, scene.CABLE_SYMBOL,
            scene.JUNCTION_SYMBOL, "signal_arc_01", "signal_arc_02", "signal_gust_01",
        ])
        self.assertFalse(any("debris" in s for s in symbols), "no debris in Signal Hill")
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertEqual(len(actors), 7, "keep the actor count modest")
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
        cable = actor_by_symbol(scene.CABLE_SYMBOL)
        self.assertEqual((cable["x"], cable["y"]), rosa.DAMAGED_POLE)
        self.assertEqual(cable["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
        self.assertEqual(cable["startScript"][0]["args"]["spriteStateId"], "Dangling")
        junction = actor_by_symbol(scene.JUNCTION_SYMBOL)
        self.assertEqual((junction["x"], junction["y"]), rosa.JUNCTION_BOX)
        self.assertEqual(junction["spriteSheetId"], climb.grid_resource_id("sprite:grid_junction_box"))
        self.assertEqual(junction["startScript"][0]["args"]["spriteStateId"], "Dead")
        arc = actor_by_symbol("signal_arc_01")
        self.assertEqual(arc["spriteSheetId"], rosa.ARC_SPRITE_ID)
        self.assertEqual(arc["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_rosa_talk_tracks_home_and_line(self):
        script = actor_by_symbol(scene.ROSA_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], rosa.VAR_HOME_POWERED, 1))
        self.assertEqual([e["args"]["text"] for e in script[0]["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Rosa:\nI'm back online!\nThank you!"]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], rosa.VAR_LINE_LIVE, 1))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in live if e["command"] == "EVENT_TEXT"],
                         [["Rosa:\nLine's live!\nTry my door."]])
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Rosa:\nNo internet...\nI can't work."]])

    def test_junction_plugs_carried_cable_once_and_lights_slot_five(self):
        script = actor_by_symbol(scene.JUNCTION_SYMBOL)["script"]
        live = next(e for e in script if is_var_if(e, rosa.VAR_LINE_LIVE, 1))
        self.assertEqual([e["args"]["text"] for e in live["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Line is live."]])
        has_cable = next(e for e in live["children"]["false"]
                         if is_var_if(e, rosa.VAR_CARRYING_CABLE, 1))
        branch = has_cable["children"]["true"]
        self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in branch))
        self.assertTrue(any(is_set(e, rosa.VAR_LINE_LIVE, 1) for e in branch))
        palette = next(e for e in branch if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(palette["args"][f"palette{rosa.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_live"))
        self.assertEqual(set(k for k, v in palette["args"].items() if v != "keep"),
                         {f"palette{rosa.LINE_BG_SLOT}"})
        states = [e["args"]["spriteStateId"] for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"]
        self.assertEqual(states, ["Live"])
        no_cable = has_cable["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in no_cable if e["command"] == "EVENT_TEXT"],
                         [["No cable yet.\nCheck the pole."]])

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        script = actor_by_symbol(scene.CABLE_SYMBOL)["script"]
        empty = script[0]
        self.assertTrue(is_var_if(empty, rosa.VAR_CARRYING_CABLE, 0))
        dead = next(e for e in empty["children"]["true"] if is_var_if(e, rosa.VAR_LINE_LIVE, 0))
        self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 1) for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                            e["args"]["type"] == FAKE_AUDIO["pickup"]
                            for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_TEXT" and
                            e["args"]["text"] == ["Got the cable!\nTo the box ahead."]
                            for e in dead["children"]["true"]))

    def test_checked_in_files_match_the_builders(self):
        """Run after make_rosa_scene.py: disk must match the in-memory build."""
        music = shared.sidecar_id(scene.MUSIC_SIDECAR, "music")
        audio = {
            "death": shared.sidecar_id(scene.DEATH_SOUND, "sound"),
            "connect": shared.sidecar_id(scene.CONNECT_SOUND, "sound"),
            "pickup": shared.sidecar_id(scene.PICKUP_SOUND, "sound"),
        }
        sprites = {"gust": shared.sidecar_id(scene.GUST_SPRITE, "sprite")}
        expected = scene.build_scene(music, audio["death"])
        self.assertEqual(shared.load_json(scene.SCENE_DIR / "scene.gbsres"), expected)
        for actor in scene.build_actors(sprites, audio):
            path = scene.SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), actor)
        for trigger in scene.build_triggers(audio):
            path = scene.SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres"
            self.assertEqual(shared.load_json(path), trigger)
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
        self.assertEqual(sprites[4:], template["spritePaletteIds"][4:],
                         "gust (slot 5) and unused slots keep the climb palettes")
        self.assertEqual(rosa.ROSA_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(rosa.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(rosa.ARC_SPRITE_PALETTE_SLOT, 3)
        self.assertEqual(rosa.GUST_SPRITE_PALETTE_SLOT, 5)
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[5], climb.grid_resource_id("palette:bg:metal_dead"))
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

    def test_shared_sidecars_exist(self):
        """Sounds, music and the gust sprite are already on disk; Rosa and arc art are not required."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)

    def test_hollow_exit_leads_to_pine_hollow_only_after_rosa_is_powered(self):
        trigger = trigger_by_symbol("trigger_signal_hollow_exit")
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         kiko.HILL_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": "11"})
        cutoff, hide, switch = gate["children"]["true"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        self.assertEqual(switch["args"]["sceneId"], kiko.SCENE_ID)
        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), kiko.START)
        refused = gate["children"]["false"]
        self.assertNotIn("EVENT_ACTOR_SET_POSITION", [e["command"] for e in walk(refused)])
        tx, _, tw, _ = rosa.DOOR_TRIGGER
        self.assertGreaterEqual(trigger["x"], tx + tw)


if __name__ == "__main__":
    unittest.main()
