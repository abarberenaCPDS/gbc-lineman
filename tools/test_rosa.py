"""Signal Hill checks: python3 -m unittest discover -s tools -p test_rosa.py (or cd tools)."""
import itertools
import json
import re
import unittest
from pathlib import Path

import climb
import grid_chain
import intro
import make_climb_scene as shared
import make_rosa_scene as scene
import opening
import ridge
import rosa
import tickets
import kiko

# Hermetic fixtures: the builders only reference these IDs, so fixed strings
# keep the structural tests independent of which art sidecars exist yet.
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite", "arc": "arc-sprite"}
PROJECT_DIR = scene.PROJECT_DIR
LINES = scene.LINES


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


def is_at_least(event, variable, value):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == "gte"
            and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


def texts(events):
    return [e["args"]["text"] for e in events if e["command"] == "EVENT_TEXT"]


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


def on_screen_sprites():
    """(feet tile, OBJ columns, OBJ tile rows) for every actor that can be visible."""
    sprites = [(rosa.ROSA, 2, 3), (rosa.WORKSTATION, 2, 2)]   # Priya: 24px figure
    sprites += grid_chain.chain_sprites(LINES)
    sprites += hazard_sprites()
    return sprites


def spots():
    """Every place the hero stands on purpose: start, door, poles, boxes, checkpoints, hazards."""
    found = [rosa.START, rosa.HOUSE_DOOR]
    for line in LINES:
        found += [line["pole_at"], line["box_at"], line["checkpoint"]]
    found += [(x0, row + 1) for row, x0, _ in rosa.hazard_lanes()]
    return found


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

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(8)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:8], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(8)] + ["10", "11", "21", "22", "23"])
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
                         [["Priya's offline!\nHer work is due."], ["Mind the sparks!"]])
        for line in LINES:
            self.assertIn((scene.actor_id(line["pole"]), "Snapped"),
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
        self.assertGreaterEqual(checked, 20)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(rosa.HUD_TEXT, "LINES %D1$22$/2 HOME %D1$11$/1")
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
        self.assertGreaterEqual(checked, 40)

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
            self.assertTrue(any(e["command"] == "EVENT_ACTOR_SHOW" and
                                e["args"]["actorId"] == scene.actor_id(line["cable"])
                                for e in drop_events))
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
                         [["Priya:\nRouter's on!\nI'm online again."], tickets.closed_lines(3)])
        dead = line["children"]["false"]
        self.assertEqual(texts(dead), [["Still no power.\nFix both lines!"]])
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
        first_hazard = 2 + 3 * rosa.LINE_COUNT   # Priya, her workstation, then three per line
        self.assertEqual(hazard_indices, list(range(first_hazard, first_hazard + len(arcs) + len(gusts))))

    def test_every_view_stays_within_ten_sprites_per_scanline(self):
        # Same budget as Wind Ridge: OBJ columns per tile row with the hero standing
        # on every spot (start, door, poles, boxes, checkpoints, hazards), with
        # Priya, her workstation, the whole chain and every arc and gust drawn.
        for spot in spots():
            load = grid_chain.scanline_load(on_screen_sprites(), rosa.MAP_W, *spot)
            self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (spot, load))

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

    def test_every_view_stays_within_the_active_actor_limit(self):
        for hero_x, _ in spots():
            near = grid_chain.actors_near(on_screen_sprites(), rosa.MAP_W, hero_x)
            self.assertLessEqual(len(near), rosa.MAX_ACTIVE_ACTORS, (hero_x, near))

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        house = LINES[1]
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
                          for e in start["children"]["false"]], [("$self$", "Snapped")])
        init = built_scene()["script"]
        self.assertIn((scene.pole_actor_id(), "Snapped"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_every_pole_starts_snapped_unless_its_line_is_live(self):
        for line in LINES:
            pole = actor_by_symbol(line["pole_symbol"])
            self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
            start = pole["startScript"][1]
            self.assertTrue(is_var_if(start, line["live_var"], 1))
            self.assertEqual([e["args"]["spriteStateId"] for e in start["children"]["true"]], ["Standing"])
            self.assertEqual([e["args"]["spriteStateId"] for e in start["children"]["false"]], ["Snapped"])

    def test_feeder_pole_stands_on_the_upper_step(self):
        feeder = LINES[0]
        self.assertEqual(feeder["pole_at"], (7, 8))
        self.assertEqual(rosa.collision_grid()[feeder["pole_at"][1] + 1][feeder["pole_at"][0]],
                         climb.COL_SOLID)

    def test_storm_pole_palette_has_its_own_slot(self):
        sprites = built_scene()["spritePaletteIds"]
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertNotEqual(intro.SPRITE_SLOTS["pole"], rosa.ARC_SPRITE_PALETTE_SLOT)

    def test_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        self.assertEqual(symbols, [
            scene.ROSA_SYMBOL, scene.WORKSTATION_SYMBOL,
            "rosa_feeder_pole", "signal_feeder_cable_end", "signal_feeder_transformer",
            scene.POLE_SYMBOL, "signal_cable_end", "signal_junction_box",
            "signal_arc_01", "signal_arc_02", "signal_gust_01",
        ])
        self.assertFalse(any("debris" in s for s in symbols), "no debris in Signal Hill")
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertEqual(len(actors), rosa.actor_count())
        self.assertLessEqual(len(actors), 20, "the engine's actor budget")
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
            cable = actor_by_symbol(line["cable_symbol"])
            self.assertEqual((cable["x"], cable["y"]), line["pole_at"])
            self.assertEqual(cable["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
            self.assertEqual(cable["startScript"][0]["args"]["spriteStateId"], "Dangling")
            box = actor_by_symbol(line["box_symbol"])
            self.assertEqual((box["x"], box["y"]), line["box_at"])
            self.assertEqual(box["startScript"][0]["args"]["spriteStateId"], "Dead")
        transformer = actor_by_symbol("signal_feeder_transformer")
        self.assertEqual(transformer["spriteSheetId"], ridge.TRANSFORMER_SPRITE_ID,
                         "the Wind Ridge transformer asset, reused")
        junction = actor_by_symbol("signal_junction_box")
        self.assertEqual(junction["spriteSheetId"], climb.grid_resource_id("sprite:grid_junction_box"))
        arc = actor_by_symbol("signal_arc_01")
        self.assertEqual(arc["spriteSheetId"], rosa.ARC_SPRITE_ID)
        self.assertEqual(arc["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_rosa_talk_tracks_home_and_both_lines(self):
        script = actor_by_symbol(scene.ROSA_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], rosa.VAR_HOME_POWERED, 1))
        self.assertEqual(texts(script[0]["children"]["true"]), [["Priya:\nI'm back online!\nThank you!"]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], rosa.VAR_LINES_LIVE, rosa.LINE_COUNT))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual(texts(live), [["Priya:\nLines are live!\nTry my door."]])
        self.assertEqual(texts(dead), [["Priya:\nNo internet...\nI can't work."]])

    def test_each_box_takes_only_its_own_cable_and_counts_the_line(self):
        for line in LINES:
            script = actor_by_symbol(line["box_symbol"])["script"]
            live = next(e for e in script if is_var_if(e, line["live_var"], 1))
            self.assertEqual(texts(live["children"]["true"]), [["Already fixed."]])
            has_cable = next(e for e in live["children"]["false"]
                             if is_var_if(e, rosa.VAR_CARRYING_CABLE, line["number"]))
            branch = has_cable["children"]["true"]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, 0) for e in branch))
            self.assertTrue(any(is_set(e, line["live_var"], 1) for e in branch))
            self.assertEqual([e["args"]["variable"] for e in branch if e["command"] == "EVENT_INC_VALUE"],
                             [rosa.VAR_LINES_LIVE])
            self.assertIn((scene.actor_id(line["pole"]), "Standing"),
                          [(e["args"]["actorId"], e["args"]["spriteStateId"])
                           for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"])
            # Only the metal slot changes, to a chain palette.
            for palette in (e for e in walk(branch) if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"):
                self.assertEqual({k for k, v in palette["args"].items() if v != "keep"},
                                 {f"palette{rosa.LINE_BG_SLOT}"})
            [other] = has_cable["children"]["false"]
            self.assertTrue(is_var_if(other, rosa.VAR_CARRYING_CABLE, 0))
            self.assertEqual(texts(other["children"]["true"]), [["No cable yet.\nFind its pole."]])
            self.assertEqual(texts(other["children"]["false"]), [["Wrong cable\nfor this box."]])
        incs = [e for script in all_script_lists() for e in walk(script) if e["command"] == "EVENT_INC_VALUE"]
        # Each line connects from its box (B) or its reach trigger (B-06); nothing else counts.
        self.assertEqual(len(incs), 2 * rosa.LINE_COUNT, "nothing else changes the counter")

    def test_power_reaches_a_box_only_through_every_line_upstream(self):
        for line in LINES:
            script = actor_by_symbol(line["box_symbol"])["script"]
            plugged = next(e for e in walk(script) if is_var_if(e, rosa.VAR_CARRYING_CABLE, line["number"])
                           and e["children"]["true"])["children"]["true"]
            commands = [e["command"] for e in plugged]
            # The chain refresh (which sets VAR_CHAIN_LIVE) runs before the message reads it.
            refresh = next(i for i, e in enumerate(plugged)
                           if any(is_set(x, rosa.VAR_CHAIN_LIVE, 0) for x in walk([e])))
            message = plugged[-1]
            self.assertLess(refresh, len(commands) - 1)
            self.assertTrue(is_var_if(message, rosa.VAR_CHAIN_LIVE, rosa.LINE_COUNT))
            self.assertEqual(texts(message["children"]["true"]), [["Both lines live!\nGo see Priya."]])
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
            palette = next(e["args"][f"palette{rosa.LINE_BG_SLOT}"] for e in events
                           if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
            stages_set = next(var_value(e) for e in events if e["command"] == "EVENT_SET_VALUE"
                              and e["args"]["variable"] == rosa.VAR_CHAIN_LIVE)
            boxes = {e["args"]["actorId"]: e["args"]["spriteStateId"] for e in events
                     if e["command"] == "EVENT_ACTOR_SET_STATE"}
            return palette, boxes, stages_set

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
        palettes = {p["id"]: p["colors"] for _, p in scene.rosa_palettes()}
        for stages, colors in rosa.CHAIN_PALETTES.items():
            self.assertEqual(palettes[scene.chain_palette_id(stages)], colors)
            for stage, index in enumerate(rosa.STAGE_COLOR_INDEX, start=1):
                self.assertEqual(colors[index], rosa.WIRE_LIVE if stage <= stages else rosa.WIRE_DEAD)
        self.assertEqual(len(rosa.STAGE_COLOR_INDEX), rosa.LINE_COUNT, "one colour per line")

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        for line in LINES:
            script = actor_by_symbol(line["cable_symbol"])["script"]
            empty = script[0]
            self.assertTrue(is_var_if(empty, rosa.VAR_CARRYING_CABLE, 0))
            dead = next(e for e in empty["children"]["true"] if is_var_if(e, line["live_var"], 0))
            take = dead["children"]["true"]
            self.assertTrue(any(is_set(e, rosa.VAR_CARRYING_CABLE, line["number"]) for e in take))
            self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in take))
            self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                                e["args"]["type"] == FAKE_AUDIO["pickup"] for e in take))
            self.assertEqual(texts(empty["children"]["false"]), [["Hands full!\nOne cable a trip."]])

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
        self.assertEqual(backgrounds[rosa.LINE_BG_SLOT], scene.chain_palette_id(0))
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

    def test_shared_sidecars_exist(self):
        """Sounds, music, the gust sprite and the reused transformer are already on disk."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)
        self.assertTrue((PROJECT_DIR / "assets/sprites/transformer.png.gbsres").exists())

    def test_each_box_has_a_reach_trigger_on_open_air_for_its_own_cable(self):
        # B-06: walking (or dropping) up to a box with its cable plugs it in. T1 sits
        # in the pit between the step and the storm-pole rock, so its trigger is the pit.
        grid = rosa.collision_grid()
        for line in scene.LINES:
            trigger = trigger_by_symbol(f"trigger_signal_{line['key']}_reach")
            rect = (trigger["x"], trigger["y"], trigger["width"], trigger["height"])
            self.assertEqual(rect, line.get("reach") or grid_chain.reach_rect(line["box_at"]))
            x, y, w, h = rect
            self.assertTrue(all(grid[r][c] in (climb.COL_EMPTY, climb.COL_TOP)
                                for r in range(y, y + h) for c in range(x, x + w)),
                            f"{line['key']} trigger in rock")
            [gate] = trigger["script"]
            self.assertTrue(is_var_if(gate, rosa.VAR_CARRYING_CABLE, line["number"]))
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
