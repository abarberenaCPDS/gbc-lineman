"""Pine Hollow checks: python3 -m unittest discover -s tools -p test_kiko.py (or cd tools)."""
import json
import re
import unittest
from pathlib import Path

import climb
import intro
import make_climb_scene as shared
import make_kiko_scene as scene
import opening
import rosa
import kiko

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


def stands(grid, x, y):
    """A 24px hero at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == climb.COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (climb.COL_TOP, climb.COL_SOLID))


def sprite_load(sprites):
    """OBJ columns per tile row. Each entry is ((x, feet_row), width_tiles, height_tiles)."""
    load = {}
    for (_, feet), width, height in sprites:
        for row in range(feet - height + 1, feet + 1):
            load[row] = load.get(row, 0) + width
    return load


def arc_sprites():
    return [((x0, row), 2, 2) for row, x0, _ in kiko.ARC_LANES]


def gust_sprites():
    return [((x0, row), 3, 2) for row, x0, _ in kiko.GUST_LANES]


def debris_sprites(y):
    """Debris is 16px: two OBJ columns. Counted one tile taller than its feet row, as a margin."""
    return [((debris["x"], y + 1), 2, 3) for debris in kiko.HAZARD_DEBRIS]


def hazard_sprites():
    """Every arc, gust and the debris column at its lowest, all visible at once."""
    sprites = arc_sprites() + gust_sprites()
    for debris in kiko.HAZARD_DEBRIS:
        sprites += debris_sprites(debris["row_bottom"])
    return sprites


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
        self.assertEqual((resource["width"], resource["height"]), (40, 18))
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

    def test_collisions_match_contract(self):
        resource = built_scene()
        self.assertEqual(decode_rle(resource["collisions"]),
                         [cell for row in kiko.collision_grid() for cell in row])
        self.assertEqual(
            shared.collision_rle(kiko.collision_grid(), 40, 18),
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
        self.assertEqual(by_id["10"]["symbol"], "var_hill_line_live")
        self.assertEqual(by_id["11"]["symbol"], "var_rosa_home_powered")

        synthetic = {"variables": [{"id": str(i), "name": f"v{i}", "symbol": f"var_v{i}"}
                                   for i in range(12)]}
        grown = scene.merged_variables(synthetic)
        self.assertEqual(grown["variables"][:12], synthetic["variables"])
        self.assertEqual([v["id"] for v in grown["variables"]],
                         [str(i) for i in range(12)] + ["12", "13"])
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "12", "name": "Other", "symbol": "x"}]})

    def test_scene_init_resets_vars_and_sets_cold_window_and_dead_line(self):
        script = built_scene()["script"]
        for variable in ("6", "12", "13"):
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
        self.assertEqual(palette_events[1]["args"][f"palette{kiko.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_dead"))
        music = next(e for e in script if e["command"] == "EVENT_MUSIC_PLAY")
        self.assertEqual(music["args"]["musicId"], FAKE_MUSIC)
        intro = [e for e in script if e["command"] == "EVENT_TEXT"]
        self.assertEqual([e["args"]["text"] for e in intro],
                         [["No power at\nKiko's house!"], ["Dinner's cold..."]])

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
        # Authored in-play texts: two intro boxes, Kiko x3, cable pickup, junction x3, door x2.
        self.assertEqual(checked, 11)

    def test_hud_uses_exact_two_digit_variable_tokens(self):
        self.assertEqual(kiko.HUD_TEXT, "LINE %D1$12$/1 HOME %D1$13$/1")
        draws = {entry["args"]["text"] for script in all_script_lists()
                 for entry in walk(script) if entry["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws, {kiko.HUD_TEXT})
        tokens = re.findall(r"\$(\d+)\$", kiko.HUD_TEXT)
        self.assertEqual(tokens, ["12", "13"])
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
        self.assertEqual(checked, 24)  # +4 "Kiko:" name lines

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
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_SHOW" and
                            e["args"]["actorId"] == scene.actor_id(scene.CABLE_KEY)
                            for e in drop_events))
        flat = list(walk(hit))
        first_move = next(i for i, e in enumerate(flat) if e["command"] == "EVENT_ACTOR_SET_POSITION")
        self.assertGreater(first_move, 0)

    def test_respawn_goes_to_start_before_power_and_to_door_after(self):
        hit = built_scene()["playerHit1Script"]
        branch = next(e for e in hit if is_var_if(e, kiko.VAR_HOME_POWERED, 0))
        start = branch["children"]["true"][0]
        self.assertEqual(start["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertEqual((start["args"]["x"]["value"], start["args"]["y"]["value"]), kiko.START)
        door = branch["children"]["false"][0]
        door_x, door_y = kiko.HOUSE_DOOR
        self.assertEqual((door["args"]["x"]["value"], door["args"]["y"]["value"]),
                         (door_x - 1, door_y), "respawn stands in front of the door")

    def test_door_is_gated_on_live_line_and_pays_out_once(self):
        trigger = trigger_by_symbol(scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]),
                         kiko.DOOR_TRIGGER)
        script = trigger["script"]
        line = next(e for e in script if is_var_if(e, kiko.VAR_LINE_LIVE, 1))
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
                         [["Kiko:\nStove's on!\nSoup is cooking!"]])
        dead = line["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Still no power.\nFix the line!"]])
        # Only the door's reward writes var 13 to 1; init writes 0 and nothing else touches it.
        writers_to_one = [e for script in all_script_lists() for e in walk(script)
                          if e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] == "13"
                          and var_value(e) == 1]
        self.assertEqual([e["id"] for e in writers_to_one],
                         [e["id"] for e in walk(reward) if is_set(e, kiko.VAR_HOME_POWERED, 1)])

    def test_arc_and_gust_start_delays_are_distinct_and_run_once(self):
        self.assertEqual(len(kiko.ARC_START_DELAYS), len(kiko.ARC_LANES))
        self.assertEqual(len(kiko.GUST_START_DELAYS), len(kiko.GUST_LANES))
        self.assertEqual(len(set(kiko.ARC_START_DELAYS + kiko.GUST_START_DELAYS)),
                         len(kiko.ARC_START_DELAYS + kiko.GUST_START_DELAYS),
                         "no two hazards may fire in lockstep")
        arcs = [a for a in built_actors() if a["symbol"].startswith("pine_arc_")]
        gusts = [a for a in built_actors() if a["symbol"].startswith("pine_gust_")]
        self.assertEqual(len(arcs), len(kiko.ARC_LANES))
        self.assertEqual(len(gusts), len(kiko.GUST_LANES))
        cases = [
            (arcs, kiko.ARC_LANES, kiko.ARC_START_DELAYS, kiko.ARC_SPRITE_ID,
             ["Warning", "Arc"], [kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES]),
            (gusts, kiko.GUST_LANES, kiko.GUST_START_DELAYS, FAKE_SPRITES["gust"],
             ["Warning", "Burst"], [kiko.GUST_WARNING_FRAMES, kiko.GUST_ACTIVE_FRAMES, kiko.GUST_REST_FRAMES]),
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
                          if a["symbol"].startswith(("pine_arc_", "pine_gust_"))]
        self.assertEqual(hazard_indices, [5, 6])

    def test_debris_collision_is_only_active_while_falling(self):
        debris = actor_by_symbol("pine_debris_01")
        self.assertEqual(debris["collisionGroup"], "1")
        self.assertEqual((debris["x"], debris["y"]),
                         (kiko.HAZARD_DEBRIS[0]["x"], kiko.HAZARD_DEBRIS[0]["row_top"]))
        self.assertEqual(debris["spriteSheetId"], FAKE_SPRITES["hazard"])
        self.assertEqual(debris["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        update = debris["updateScript"]
        self.assertTrue(all(e["command"] != "EVENT_IF" for e in update), "debris has no branches")
        collide = [i for i, e in enumerate(update)
                   if e["command"] in ("EVENT_ACTOR_COLLISIONS_ENABLE", "EVENT_ACTOR_COLLISIONS_DISABLE")]
        enables = [i for i in collide if update[i]["command"] == "EVENT_ACTOR_COLLISIONS_ENABLE"]
        self.assertEqual(len(enables), 1, "one hitbox window per fall")
        enable = enables[0]
        rest_disable = next(i for i in collide if i > enable)
        self.assertEqual(update[rest_disable]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        self.assertEqual(update[collide[0]]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE",
                         "warning is safe")
        self.assertTrue(all(e["command"] in ("EVENT_ACTOR_SET_POSITION", "EVENT_WAIT")
                            for e in update[enable + 1:rest_disable]),
                        "only falling steps sit inside the hitbox window")
        states = [e["args"]["spriteStateId"] for e in update if e["command"] == "EVENT_ACTOR_SET_STATE"]
        self.assertEqual(states, ["Warning", "Rock"])
        self.assertLess(next(i for i, e in enumerate(update) if e["command"] == "EVENT_ACTOR_SET_STATE"
                             and e["args"]["spriteStateId"] == "Rock"), enable)
        fall = [e["args"]["y"]["value"] for e in update[enable + 1:rest_disable]
                if e["command"] == "EVENT_ACTOR_SET_POSITION"]
        top, bottom = kiko.HAZARD_DEBRIS[0]["row_top"] * 8, kiko.HAZARD_DEBRIS[0]["row_bottom"] * 8
        self.assertEqual(fall, list(range(top, bottom + 1, kiko.DEBRIS_STEP_PIXELS)))
        waits = [e["args"]["frames"]["value"] for e in update if e["command"] == "EVENT_WAIT"]
        self.assertEqual(waits[0], kiko.DEBRIS_WARNING_FRAMES)
        self.assertEqual(waits[-1], kiko.DEBRIS_REST_FRAMES + 1 * 13)
        self.assertEqual(update[rest_disable + 1]["command"], "EVENT_ACTOR_HIDE")

    def test_house_view_stays_within_ten_sprites_per_scanline(self):
        # Count OBJ columns per tile row with the hero standing anywhere on the
        # porch, Kiko, the stove and the junction box drawn, and every hazard visible.
        grid = kiko.collision_grid()
        porch = [x for x in range(kiko.PORCH[0], kiko.PORCH[1] + 1)
                 if stands(grid, x, kiko.PORCH_ROW)]
        self.assertTrue(porch)
        for x in porch:
            sprites = [((x, kiko.PORCH_ROW), 3, 3)]  # hero: 24px wide, 24px tall
            sprites += [(pos, 2, 2) for pos in (kiko.JUNCTION_BOX, kiko.KIKO, kiko.STOVE)]
            sprites += hazard_sprites()
            load = sprite_load(sprites)
            self.assertLessEqual(max(load.values()), 10, (x, load))

    def test_mesa_view_stays_within_ten_sprites_per_scanline(self):
        # The mesa carries the hero, the falling debris, the gust and the cable end.
        grid = kiko.collision_grid()
        mesa = [x for x in range(kiko.MESA[0], kiko.MESA[1] + 1)
                if stands(grid, x, kiko.MESA_ROW)]
        self.assertTrue(mesa)
        debris = kiko.HAZARD_DEBRIS[0]
        for x in mesa:
            for y in range(debris["row_top"], debris["row_bottom"] + 1):
                sprites = [((x, kiko.MESA_ROW), 3, 3)]
                sprites += [(kiko.DAMAGED_POLE, 2, 2)]
                sprites += debris_sprites(y)
                sprites += gust_sprites()
                load = sprite_load(sprites)
                self.assertLessEqual(max(load.values()), 10, (x, y, load))

    def test_floor_view_stays_within_ten_sprites_per_scanline(self):
        # Every floor tile the hero can stand on, with the live arc visible.
        grid = kiko.collision_grid()
        feet = kiko.GROUND_ROW - 1
        standing = [x for x in range(1, kiko.MAP_W - 1) if stands(grid, x, feet)]
        self.assertTrue(standing)
        for x in standing:
            sprites = [((x, feet), 3, 3)] + arc_sprites()
            load = sprite_load(sprites)
            self.assertLessEqual(max(load.values()), 10, (x, load))

    def test_storm_pole_uses_intro_sprite_and_starts_snapped_unless_live(self):
        pole = actor_by_symbol(scene.POLE_SYMBOL)
        self.assertEqual(pole["id"], scene.actor_id("pole"))
        self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
        self.assertEqual((pole["x"], pole["y"]), kiko.DAMAGED_POLE)
        self.assertTrue(pole["animate"])
        self.assertEqual(pole["script"], [], "pole is not interactive")
        self.assertEqual(pole["collisionGroup"], "", "pole does not collide")
        start = pole["startScript"][0]
        self.assertTrue(is_var_if(start, kiko.VAR_LINE_LIVE, 1))
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["true"]], [("$self$", "Standing")])
        self.assertEqual([(e["args"]["actorId"], e["args"]["spriteStateId"])
                          for e in start["children"]["false"]], [("$self$", "Snapped")])
        init = built_scene()["script"]
        self.assertIn((scene.pole_actor_id(), "Snapped"),
                      [(e["args"]["actorId"], e["args"]["spriteStateId"])
                       for e in init if e["command"] == "EVENT_ACTOR_SET_STATE"])

    def test_storm_pole_palette_has_its_own_slot(self):
        sprites = built_scene()["spritePaletteIds"]
        self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
        self.assertNotEqual(intro.SPRITE_SLOTS["pole"], kiko.ARC_SPRITE_PALETTE_SLOT)

    def test_actor_roster(self):
        actors = built_actors()
        symbols = [a["symbol"] for a in actors]
        self.assertEqual(symbols, [
            scene.KIKO_SYMBOL, scene.STOVE_SYMBOL, scene.CABLE_SYMBOL,
            scene.JUNCTION_SYMBOL, "pine_debris_01", "pine_arc_01", "pine_gust_01",
            scene.POLE_SYMBOL,
        ])
        self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
        self.assertEqual(len(set(a["id"] for a in actors)), len(actors))
        self.assertEqual(len(actors), 8, "keep the actor count modest")  # 7 + storm pole
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
        cable = actor_by_symbol(scene.CABLE_SYMBOL)
        self.assertEqual((cable["x"], cable["y"]), kiko.DAMAGED_POLE)
        self.assertEqual(cable["spriteSheetId"], climb.grid_resource_id("sprite:grid_cable_end"))
        self.assertEqual(cable["startScript"][0]["args"]["spriteStateId"], "Dangling")
        junction = actor_by_symbol(scene.JUNCTION_SYMBOL)
        self.assertEqual((junction["x"], junction["y"]), kiko.JUNCTION_BOX)
        self.assertEqual(junction["spriteSheetId"], climb.grid_resource_id("sprite:grid_junction_box"))
        self.assertEqual(junction["startScript"][0]["args"]["spriteStateId"], "Dead")
        debris = actor_by_symbol("pine_debris_01")
        self.assertEqual(debris["spriteSheetId"], FAKE_SPRITES["hazard"])
        arc = actor_by_symbol("pine_arc_01")
        self.assertEqual(arc["spriteSheetId"], kiko.ARC_SPRITE_ID)
        self.assertEqual(arc["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_kiko_talk_tracks_home_and_line(self):
        script = actor_by_symbol(scene.KIKO_SYMBOL)["script"]
        self.assertTrue(is_var_if(script[0], kiko.VAR_HOME_POWERED, 1))
        self.assertEqual([e["args"]["text"] for e in script[0]["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Kiko:\nDinner time!\nThank you!"]])
        otherwise = script[0]["children"]["false"]
        self.assertTrue(is_var_if(otherwise[0], kiko.VAR_LINE_LIVE, 1))
        live = otherwise[0]["children"]["true"]
        dead = otherwise[0]["children"]["false"]
        self.assertEqual([e["args"]["text"] for e in live if e["command"] == "EVENT_TEXT"],
                         [["Kiko:\nLine's live!\nTry our door."]])
        self.assertEqual([e["args"]["text"] for e in dead if e["command"] == "EVENT_TEXT"],
                         [["Kiko:\nOur stove's dead.\nI'm so hungry!"]])

    def test_junction_plugs_carried_cable_once_and_lights_line(self):
        script = actor_by_symbol(scene.JUNCTION_SYMBOL)["script"]
        live = next(e for e in script if is_var_if(e, kiko.VAR_LINE_LIVE, 1))
        self.assertEqual([e["args"]["text"] for e in live["children"]["true"]
                          if e["command"] == "EVENT_TEXT"], [["Line is live."]])
        has_cable = next(e for e in live["children"]["false"]
                         if is_var_if(e, kiko.VAR_CARRYING_CABLE, 1))
        branch = has_cable["children"]["true"]
        self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, 0) for e in branch))
        self.assertTrue(any(is_set(e, kiko.VAR_LINE_LIVE, 1) for e in branch))
        palette = next(e for e in branch if e["command"] == "EVENT_PALETTE_SET_BACKGROUND")
        self.assertEqual(palette["args"][f"palette{kiko.LINE_BG_SLOT}"],
                         climb.grid_resource_id("palette:bg:metal_live"))
        self.assertEqual(set(k for k, v in palette["args"].items() if v != "keep"),
                         {f"palette{kiko.LINE_BG_SLOT}"})
        states = [e["args"]["spriteStateId"] for e in branch if e["command"] == "EVENT_ACTOR_SET_STATE"]
        self.assertEqual(states, ["Live", "Standing"])  # junction box, then the pole
        self.assertEqual([e["args"]["text"] for e in branch if e["command"] == "EVENT_TEXT"],
                         [["Line is live!\nGo see Kiko."]])
        # Empty hands at a dead line point back to the pole, like the other jobs.
        self.assertEqual([e["args"]["text"] for e in has_cable["children"]["false"]
                          if e["command"] == "EVENT_TEXT"], [["No cable yet.\nCheck the pole."]])

    def test_cable_pickup_requires_empty_hands_and_dead_line(self):
        script = actor_by_symbol(scene.CABLE_SYMBOL)["script"]
        empty = script[0]
        self.assertTrue(is_var_if(empty, kiko.VAR_CARRYING_CABLE, 0))
        dead = next(e for e in empty["children"]["true"] if is_var_if(e, kiko.VAR_LINE_LIVE, 0))
        self.assertTrue(any(is_set(e, kiko.VAR_CARRYING_CABLE, 1) for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" and
                            e["args"]["type"] == FAKE_AUDIO["pickup"]
                            for e in dead["children"]["true"]))
        self.assertTrue(any(e["command"] == "EVENT_TEXT" and
                            e["args"]["text"] == ["Got the cable!\nTo the box ahead."]
                            for e in dead["children"]["true"]))

    def test_checked_in_files_match_the_builders(self):
        """Run after make_kiko_scene.py: disk must match the in-memory build."""
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
        self.assertEqual(sprites[4:], template["spritePaletteIds"][4:],
                         "debris (slot 4) and gust (slot 5) keep the climb palettes")
        self.assertEqual(kiko.KIKO_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(kiko.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(kiko.ARC_SPRITE_PALETTE_SLOT, 3)
        self.assertEqual(kiko.DEBRIS_SPRITE_PALETTE_SLOT, 4)
        self.assertEqual(kiko.GUST_SPRITE_PALETTE_SLOT, 5)
        backgrounds = resource["paletteIds"]
        self.assertEqual(len(backgrounds), 8)
        self.assertEqual(backgrounds[:5], [opening.resource_id(f"palette:bg:{name}")
                                           for name in ["night", "stone", "timber", "window", "foliage"]])
        self.assertEqual(backgrounds[5], climb.grid_resource_id("palette:bg:metal_dead"))
        self.assertEqual(backgrounds[7], "default-ui")
        [(relative, kiko_palette)] = scene.kiko_palettes()
        self.assertEqual(relative, "project/palettes/pine_hollow_sprite_kiko.gbsres")
        self.assertEqual(kiko_palette["id"], scene.kiko_palette_id())
        self.assertEqual(kiko_palette["colors"], [
            kiko.KIKO_SPRITE_HARDWARE[1], kiko.KIKO_SPRITE_HARDWARE[2],
            kiko.KIKO_SPRITE_HARDWARE[3], kiko.KIKO_SPRITE_HARDWARE[3],
        ])
        self.assertNotEqual(kiko_palette["id"], scene.arc_palette_id())
        self.assertEqual(scene.arc_palette_id(), rosa.resource_id("palette:sprite:arc"),
                         "arc palette is Signal Hill's resource, not a duplicate")

    def test_shared_sidecars_exist(self):
        """Sounds, music, debris/gust sprites and Signal Hill's arc are already on disk."""
        for path in (scene.DEATH_SOUND, scene.CONNECT_SOUND, scene.PICKUP_SOUND,
                     scene.MUSIC_SIDECAR, scene.GUST_SPRITE, scene.DEBRIS_SPRITE):
            self.assertTrue((PROJECT_DIR / path).exists(), path)
        arc_palette = shared.load_json(PROJECT_DIR / "project" / "palettes" / "signal_hill_sprite_arc.gbsres")
        self.assertEqual(arc_palette["id"], scene.arc_palette_id())
        live_arc = shared.load_json(PROJECT_DIR / "assets" / "sprites" / "live_arc.png.gbsres")
        self.assertEqual(live_arc["id"], kiko.ARC_SPRITE_ID, "Kiko reuses Signal Hill's live arc sprite")


if __name__ == "__main__":
    unittest.main()


class PorchExitPriorityTests(unittest.TestCase):
    """The engine fires the first trigger the hero's box overlaps.

    At the right wall the hero overlaps both the door trigger and the porch
    exit, so the exit must sort first or the next job is unreachable (cart
    ROM 6bfec7b4: Signal Hill could not be reached from Tomas's porch).
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
