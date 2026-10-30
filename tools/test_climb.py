"""Storm Climb contract and scene checks (stdlib only).

Run: python3 -m unittest discover -s tools -p 'test_climb*.py' (the background
test needs the managed Python with Pillow; music lives in test_climb_music.py).
"""
import json
import re
import unittest

import climb
import grid_chain
import hazards
import intro
import level
import make_climb_scene as scene
import opening
import ridge
import rosa
import tickets

CLIMB_AUDIO = {"death": "death-sfx", "connect": "connect-sfx", "pickup": "pickup-sfx"}
SPRITES = {"marta": opening.resource_id("sprite:opening_marta"), "gust": "gust-sprite"}


def flatten(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from flatten(branch)


def rect(t):
    return (t["x"], t["y"], t["width"], t["height"])


def overlaps(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def texts(events):
    return [e["args"]["text"] for e in flatten(events) if e["command"] == "EVENT_TEXT"]


class Fixture:
    actors = scene.build_actors(SPRITES)
    triggers = scene.build_triggers(CLIMB_AUDIO)
    resource = scene.build_scene("test-music", CLIMB_AUDIO, actors)
    script = resource["script"]
    boxes = dict(scene.box_script_resources(CLIMB_AUDIO))
    by_symbol = {a["symbol"]: a for a in actors}
    triggers_by_symbol = {t["symbol"]: t for t in triggers}


class ClimbContractTests(unittest.TestCase):
    def test_geometry_and_budget_invariants(self):
        climb._self_check()

    def test_collision_encoding_matches_existing_encoder(self):
        grid = climb.collision_grid()
        self.assertEqual(scene.collision_rle(grid, climb.MAP_W, climb.MAP_H),
                         level.rle([cell for row in grid for cell in row]))

    def test_power_climbs_bottom_to_top_through_five_lines(self):
        self.assertEqual(climb.LINE_COUNT, 5)
        rows = [line["pole"][1] for line in climb.LINES] + [climb.LINES[-1]["box"][1]]
        self.assertEqual(rows, sorted(rows, reverse=True), "each line ends higher than it starts")
        self.assertEqual(climb.LINES[0]["pole"][1], climb.START[1], "pole 1 is on the bottom deck")
        self.assertEqual(climb.LINES[-1]["box"][1], climb.HOUSE_A["y"], "line 5 ends on Amara's summit")
        self.assertEqual(climb.LINES[-1]["live_var"], climb.VAR_LINE_LIVE, "var 7 stays Amara's line")
        self.assertEqual([line["number"] for line in climb.LINES], [1, 2, 3, 4, 5])

    def test_rises_are_short_taps_and_the_summit_leap(self):
        rises = [a[0] - b[0] for a, b in zip(climb.ROUTE, climb.ROUTE[1:])]
        self.assertEqual(rises, [3] * 8 + [4])

    def test_deck_ends_are_rock_so_a_long_jump_cannot_skip_a_carry(self):
        grid = climb.collision_grid()
        for line in climb.LINES[:4]:
            for x, y in (line["pole"], line["box"]):
                if y == climb.START[1] or y < climb.DECK_ROWS[-1]:
                    continue  # the bottom deck has no slab above; L8 leads on to the summit
                above = [r for r in range(y - 1, -1, -1) if grid[r][x] != climb.COL_EMPTY]
                self.assertTrue(above, (x, y))
                self.assertEqual(grid[above[0]][x], climb.COL_SOLID, f"open sky above {(x, y)}")

    def test_variables_are_new_and_registered_without_renaming(self):
        used = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15",
                "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
                "30", "31", "32", "33", "34", "35"}
        ids = [v for v, _, _ in climb.VARIABLES]
        self.assertEqual(ids, [str(n) for n in range(40, 50)])
        self.assertTrue(used.isdisjoint(ids))
        registered = scene.merged_variables({"variables": []})["variables"]
        for key, name, symbol in climb.VARIABLES:
            self.assertIn({"id": key, "name": name, "symbol": symbol}, registered)
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "44", "name": "Other", "symbol": "var_other"}]})
        on_disk = json.loads((scene.PROJECT_DIR / "project/variables.gbsres").read_text())["variables"]
        for key, name, symbol in climb.VARIABLES:
            self.assertIn({"id": key, "name": name, "symbol": symbol}, on_disk)

    def test_chain_palettes_light_exactly_the_leading_stages(self):
        for live, slots in climb.CHAIN_PALETTES.items():
            self.assertEqual(set(slots), {5, 6})
            for stage in range(1, 6):
                colour = slots[climb.stage_slot(stage)][climb.STAGE_COLOR_INDEX[stage - 1]]
                self.assertEqual(colour, climb.WIRE_LIVE if stage <= live else climb.WIRE_DEAD)
            self.assertEqual(slots[5][0], "0B101E", "wire tiles blend into the night sky")
        files = scene.chain_palette_resources()
        self.assertEqual(len(files), 12)
        self.assertTrue(all(path.startswith("project/palettes/storm_climb_bg_chain_") for path, _ in files))

    def test_scanline_and_oam_budgets(self):
        self.assertLessEqual(max(climb.scanline_load().values()) + climb.HERO_COLUMNS, 10)
        for top in range(climb.CAMERA_MAX_TOP + 1):
            self.assertLessEqual(climb.oam_load(top, worst=False), climb.OAM_LIMIT, top)
            # Every timed hazard visible at once plus a creaking board: a rare
            # alignment, kept in a narrow band so regressions show up.
            self.assertLessEqual(climb.oam_load(top, worst=True), 45, top)
        self.assertLessEqual(climb.actor_count(), 20)
        self.assertEqual(climb.actor_count(), len(Fixture.actors))


class ClimbSceneTests(unittest.TestCase):
    def test_scene_identity_size_and_background(self):
        r = Fixture.resource
        self.assertEqual(r["id"], "e8778f37-44a7-5d3a-ad39-49d52fe4c5c7")
        self.assertEqual(r["backgroundId"], scene.resource_id("background:storm-climb"))
        self.assertEqual((r["width"], r["height"]), (20, 36))
        self.assertEqual(r["type"], "PLATFORM")

    def test_palette_slots(self):
        r = Fixture.resource
        bg = r["paletteIds"]
        self.assertEqual(bg[:4], [opening.resource_id(f"palette:bg:{n}") for n, _ in opening.BG_PALETTES[:4]])
        self.assertEqual(bg[4], scene.hardware_palette_id())
        self.assertEqual(bg[5:7], [scene.CHAIN.chain_palette_ids(0)[5], scene.CHAIN.chain_palette_ids(0)[6]])
        self.assertEqual(bg[7], "default-ui")
        sp = r["spritePaletteIds"]
        self.assertEqual(sp[0], opening.resource_id("palette:sprite:worker"))
        self.assertEqual(sp[1], opening.resource_id("palette:sprite:marta"))
        self.assertEqual(sp[2], climb.grid_resource_id("palette:sprite:grid"))
        self.assertEqual(sp[3], rosa.resource_id("palette:sprite:arc"))
        self.assertEqual(sp[4], hazards.BOARD_PALETTE_ID)
        self.assertEqual(sp[6], ridge.WHIP_PALETTE_ID)
        self.assertEqual(sp[7], intro.palette_id("pole"))
        self.assertEqual(ridge.WHIP_SPRITE_PALETTE_SLOT, 6)

    def test_sprite_obj_slots_match_their_scene_slots(self):
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

        expected = {"opening_worker24": {0}, "opening_marta": {1}, "live_arc": {3}, "cracked_board": {4},
                    "climb_gust": {5}, "whip_wire": {6}, "intro_pole": {7}}
        for name, slots in expected.items():
            self.assertEqual(palette_indexes(f"assets/sprites/{name}.png.gbsres"), slots, name)

    def test_actor_roster(self):
        symbols = [a["symbol"] for a in Fixture.actors]
        self.assertEqual(symbols, [
            "marta_checkpoint", "climb_base_pole", "climb_lower_pole", "climb_middle_pole", "climb_upper_pole",
            "climb_storm_pole", "gust_01", "gust_02", "climb_span_arc_01", "climb_whip_01", "climb_whip_02",
            "hidden_cable_01", "board_01", "board_02", "board_03"])
        self.assertEqual([a["_index"] for a in Fixture.actors], list(range(len(symbols))))
        self.assertNotIn("grid_junction_box", symbols, "transformers are background art")
        on_disk = sorted(p.stem for p in (scene.SCENE_DIR / "actors").glob("*.gbsres"))
        self.assertEqual(on_disk, sorted(symbols))

    def test_stable_ids_are_kept(self):
        a = Fixture.by_symbol
        self.assertEqual(a["marta_checkpoint"]["id"], "0a208a0e-9313-59b7-be31-3be4c204ab2a")
        self.assertEqual(a["gust_01"]["id"], "87bc8be0-aafb-5804-af87-3bd9a2efef96")
        self.assertEqual(a["climb_storm_pole"]["id"], scene.resource_id("actor:pole"))
        for n in (1, 2, 3):
            self.assertEqual(a[f"board_{n:02d}"]["id"], scene.resource_id(f"actor:board:{n}"))
        self.assertEqual(a["hidden_cable_01"]["id"], scene.resource_id("actor:hidden-cable:1"))
        t = Fixture.triggers_by_symbol
        self.assertEqual([t[f"trigger_gust_lane_{n:02d}"]["id"] for n in range(1, 9)], [
            "3fe92e59-004f-5fcf-9aa2-808b4d935b52", "445eeab9-8c38-5f04-8850-7916aa2ac5c1",
            "0e782e08-57a1-5998-b79f-5691515f9ed3", "826886c2-8bae-5d07-adeb-6caf4835b440",
            "72eb2ec8-7234-5e9a-a6ef-fb1fb011084f", "e052fa35-c859-57dc-a8cd-55b6624a6981",
            "17ed159c-3f9b-51d8-b9ae-5daae23626a2", "b5d8455e-a64b-5abc-955e-e4b624739396"])
        self.assertEqual(t["trigger_marta_arrival"]["id"], "b02fc406-5513-54f5-abd9-25c1adb2da51")
        self.assertEqual(t["trigger_grid_pole_zone"]["id"], scene.resource_id("trigger:pole-zone:cable"))
        self.assertEqual(t["trigger_grid_junction_zone"]["id"], scene.resource_id("trigger:reach:junction"))
        self.assertEqual(t["trigger_street_exit"]["id"], scene.resource_id("trigger:street-exit"))
        self.assertEqual(t["trigger_summit_exit"]["id"], scene.resource_id("trigger:summit-exit"))

    def test_poles_never_take_b_and_start_snapped_unless_live(self):
        for line in scene.LINES:
            pole = Fixture.by_symbol[line["pole_symbol"]]
            self.assertEqual((pole["x"], pole["y"]), line["pole_at"])
            self.assertEqual(pole["spriteSheetId"], intro.POLE_SPRITE_ID)
            self.assertEqual(pole["script"], [])
            self.assertEqual(pole["startScript"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
            check = pole["startScript"][1]
            self.assertEqual(check["args"]["condition"]["valueA"]["value"], line["live_var"])
            self.assertEqual(check["children"]["true"][0]["args"]["spriteStateId"], "Standing")
            self.assertEqual(check["children"]["false"][0]["args"]["spriteStateId"], "Snapped+Cable")

    def test_init_resets_every_line_and_pins_poles_snapped(self):
        sets = [(e["args"]["variable"], e["args"]["value"]["value"]) for e in Fixture.script
                if e["command"] == "EVENT_SET_VALUE"]
        self.assertEqual(sets, [("0", 0), ("6", 0), ("40", 0), ("41", 0), ("42", 0), ("43", 0), ("7", 0),
                                ("45", 0), (climb.VAR_NEAR, 0), (hazards.VAR_ON_BOARD, 0)])
        refresh = [e for e in Fixture.script if e["command"] == "EVENT_IF"
                   and e["args"]["condition"]["valueA"]["value"] == "40"]
        self.assertEqual(len(refresh), 1, "chain refresh sets var 44 and both wire slots")
        pinned = [e["args"]["actorId"] for e in Fixture.script if e["command"] == "EVENT_ACTOR_SET_STATE"
                  and e["args"]["spriteStateId"] == "Snapped+Cable"]
        self.assertEqual(pinned, [scene.CHAIN.actor_id(line["pole"]) for line in scene.LINES])
        written = {e["args"]["variable"] for e in flatten(Fixture.script) if e["command"] == "EVENT_SET_VALUE"}
        self.assertNotIn("4", written, "the climb must never clear Service Restored")

    def test_b_press_dispatches_pole_and_box_zones_and_keeps_native_talk(self):
        [b] = [e for e in Fixture.script if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
        self.assertEqual(b["args"], {"input": ["b"], "override": False})
        values = []
        node = b["children"]["true"]
        while node and node[0]["command"] == "EVENT_IF" and \
                node[0]["args"]["condition"]["valueA"]["value"] == climb.VAR_NEAR:
            values.append(node[0]["args"]["condition"]["valueB"]["value"])
            if node[0]["args"]["condition"]["valueB"]["value"] == grid_chain.NPC_ZONE:
                self.assertEqual(node[0]["children"]["true"], [], "Amara's zone leaves native talk")
                break
            node = node[0]["children"]["false"]
        self.assertEqual(values, [1, 101, 2, 102, 3, 103, 4, 104, 5, 105, grid_chain.NPC_ZONE])
        calls = [e for e in flatten(b["children"]["true"]) if e["command"] == "EVENT_CALL_CUSTOM_EVENT"]
        self.assertEqual([c["args"]["customEventId"] for c in calls],
                         [scene.CHAIN.box_script_id(line) for line in scene.LINES])
        self.assertFalse([e for e in flatten(b["children"]["true"]) if e["command"] == "EVENT_ACTOR_INVOKE"],
                         "B-17: never EVENT_ACTOR_INVOKE")

    def test_box_scripts_light_the_chain_without_box_actors(self):
        self.assertEqual(sorted(Fixture.boxes), sorted(
            f"project/scripts/storm_climb_box_{line['key']}.gbsres" for line in scene.LINES))
        for line in scene.LINES:
            box = Fixture.boxes[f"project/scripts/storm_climb_box_{line['key']}.gbsres"]
            self.assertEqual(box["actors"], {"0": {"id": "0", "name": line["pole_name"]}})
            events = list(flatten(box["script"]))
            sets = {(e["args"]["variable"], e["args"]["value"]["value"]) for e in events
                    if e["command"] == "EVENT_SET_VALUE"}
            self.assertIn((line["live_var"], 1), sets)
            self.assertIn((climb.VAR_CHAIN_LIVE, 5), sets)
            self.assertIn({"variable": climb.VAR_LINES_LIVE},
                          [e["args"] for e in events if e["command"] == "EVENT_INC_VALUE"])
            states = {(e["args"]["actorId"], e["args"]["spriteStateId"]) for e in events
                      if e["command"] == "EVENT_ACTOR_SET_STATE"}
            self.assertEqual(states, {("player", ""), ("0", "Standing")}, "no box actor to set")
            palettes = [e for e in events if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
            self.assertEqual(len(palettes), 6)
            self.assertTrue(all(p["args"]["palette5"] != "keep" and p["args"]["palette6"] != "keep"
                                for p in palettes))

    def test_zones_cover_their_props_and_never_overlap(self):
        t = Fixture.triggers_by_symbol
        for line in scene.LINES:
            box, pole = t[line["box_zone_symbol"]], t[line["pole_zone_symbol"]]
            self.assertEqual(rect(box), line["reach"])
            self.assertEqual(rect(pole), grid_chain.pole_zone_rect(line["pole_at"]))
            self.assertEqual(box["script"][0]["args"]["value"]["value"], grid_chain.BOX_ZONE + line["number"])
            self.assertEqual(pole["script"][0]["args"]["value"]["value"], line["number"])
        live = [tr for tr in Fixture.triggers if tr["script"] or tr["leaveScript"]]
        for i, a in enumerate(live):
            for b in live[i + 1:]:
                self.assertFalse(overlaps(rect(a), rect(b)), f"{a['symbol']} overlaps {b['symbol']}")

    def test_trigger_order_exits_first_and_inert_gust_markers_last(self):
        symbols = [tr["symbol"] for tr in Fixture.triggers]
        self.assertEqual(symbols[:3], ["trigger_street_exit", "trigger_summit_exit", "trigger_marta_arrival"])
        self.assertEqual(symbols[-8:], [f"trigger_gust_lane_{n:02d}" for n in range(1, 9)])
        self.assertTrue(all(tr["script"] == [] and tr["leaveScript"] == [] for tr in Fixture.triggers[-8:]))
        self.assertEqual([tr["_index"] for tr in Fixture.triggers], list(range(len(symbols))))
        self.assertLessEqual(len(symbols), grid_chain.MAX_TRIGGERS)
        on_disk = sorted(p.stem for p in (scene.SCENE_DIR / "triggers").glob("*.gbsres"))
        self.assertEqual(on_disk, sorted(symbols))

    def test_amaras_door_needs_all_five_lines_and_is_once_only(self):
        door = Fixture.triggers_by_symbol["trigger_marta_arrival"]
        self.assertEqual(rect(door), scene.arrival_rect())
        [gate] = door["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"]["value"], climb.VAR_CHAIN_LIVE)
        self.assertEqual(gate["args"]["condition"]["valueB"]["value"], 5)
        [once] = gate["children"]["true"]
        self.assertEqual(once["args"]["condition"]["valueA"]["value"], scene.VARIABLE_CHECKPOINTS_REACHED)
        self.assertEqual(once["children"]["false"], [])
        self.assertIn(["Power's back!\nMy fridge hums.", *tickets.closed_lines(1)], texts(once["children"]["true"]))
        [hint] = gate["children"]["false"]
        self.assertEqual(hint["args"]["condition"]["valueA"]["value"], climb.VAR_CARRYING_CABLE)
        self.assertEqual(texts(hint["children"]["true"]), [["Still no power.\nFix all 5 lines!"]])

    def test_amara_talk_tracks_the_chain(self):
        talk = Fixture.by_symbol["marta_checkpoint"]["script"][0]
        line = talk["children"]["true"][0]
        self.assertEqual(line["args"]["condition"]["valueA"]["value"], climb.VAR_CHAIN_LIVE)
        self.assertEqual(texts(line["children"]["true"]), [["Amara:\nPower's up here!\nTry my door."]])
        self.assertEqual(texts(line["children"]["false"]), [["Amara:\nStorm cut five\nlines below me!"]])
        self.assertEqual(texts(talk["children"]["false"]), [["Amara:\nFood is saved.\nThanks, lineman!"]])

    def test_respawn_drops_the_cable_then_returns_to_the_furthest_repaired_line(self):
        hit = Fixture.resource["playerHit1Script"]
        commands = [e["command"] for e in hit]
        self.assertEqual(commands[0], "EVENT_SOUND_PLAY_EFFECT")
        drops = [i for i, e in enumerate(hit) if e["command"] == "EVENT_IF"
                 and e["args"]["condition"]["valueA"]["value"] == climb.VAR_CARRYING_CABLE]
        self.assertEqual(len(drops), 5)
        check = hit[-1]
        self.assertEqual(check["args"]["condition"]["valueA"]["value"], scene.VARIABLE_CHECKPOINTS_REACHED)
        self.assertGreater(len(hit) - 1, max(drops))
        positions = [(e["args"]["x"]["value"], e["args"]["y"]["value"]) for e in flatten(check["children"]["true"])
                     if e["command"] == "EVENT_ACTOR_SET_POSITION"]
        self.assertEqual(set(positions), {climb.START, *[line["checkpoint"] for line in climb.LINES]})
        outer = check["children"]["true"][0]
        self.assertEqual(outer["args"]["condition"]["valueA"]["value"], climb.LINES[-1]["live_var"])
        self.assertEqual(check["children"]["false"][0]["args"]["x"]["value"], climb.HOUSE_A["x"])

    def test_hazards_cover_every_designed_obstacle(self):
        a = Fixture.by_symbol
        for n, board in enumerate(hazards.BOARDS["storm_climb"], start=1):
            actor = a[f"board_{n:02d}"]
            self.assertEqual((actor["x"], actor["y"]), hazards.board_actor_position(board))
            self.assertEqual(actor["collisionGroup"], "1")
            self.assertEqual(actor["startScript"][-1]["command"], "EVENT_ACTOR_HIDE", "idle plank is background")
            cmds = [e["command"] for e in flatten(actor["updateScript"])]
            self.assertLess(cmds.index("EVENT_ACTOR_SHOW"), cmds.index("EVENT_ACTOR_COLLISIONS_ENABLE"))
            waits = [e["args"]["frames"]["value"] for e in flatten(actor["updateScript"])
                     if e["command"] == "EVENT_WAIT"]
            self.assertIn(hazards.CREAK_FRAMES, waits)
        for n in (1, 2):
            gust = a[f"gust_{n:02d}"]
            row, x0, _ = climb.GUST_LANES[n - 1]
            self.assertEqual((gust["x"], gust["y"], gust["collisionGroup"]), (x0, row, "1"))
        arc = a["climb_span_arc_01"]
        self.assertEqual(arc["spriteSheetId"], rosa.ARC_SPRITE_ID)
        upstream = arc["updateScript"][0]
        self.assertEqual(upstream["args"]["condition"]["valueA"]["value"], climb.VAR_CHAIN_LIVE)
        self.assertEqual(upstream["args"]["condition"]["valueB"]["value"], 2)
        self.assertEqual(upstream["children"]["true"][0]["command"], "EVENT_ACTOR_COLLISIONS_DISABLE")
        for n, (row, x0, _) in enumerate(climb.WHIP_LANES, start=1):
            whip = a[f"climb_whip_{n:02d}"]
            self.assertEqual((whip["x"], whip["y"], whip["spriteSheetId"], whip["collisionGroup"]),
                             (x0, row + 1, ridge.WHIP_SPRITE_ID, "1"))
        cable = a["hidden_cable_01"]
        self.assertEqual((cable["y"], cable["spriteSheetId"]), (hazards.HIDDEN_CABLES["storm_climb"][0][0],
                                                                 rosa.ARC_SPRITE_ID))

    def test_culling_thread_keeps_every_visible_actor_active(self):
        thread = Fixture.script[-1]
        self.assertEqual(thread["command"], "EVENT_THREAD_START")
        loop = thread["children"]["true"][-1]
        self.assertEqual(loop["command"], "EVENT_LOOP")
        body = loop["children"]["true"]
        self.assertEqual([e["command"] for e in body],
                         ["EVENT_ACTOR_GET_POSITION", "EVENT_SET_VALUE", "EVENT_IF", "EVENT_WAIT"])
        self.assertGreaterEqual(body[-1]["args"]["frames"]["value"], 8, "idle loop must be cheap")
        changed = body[2]
        self.assertEqual(changed["args"]["condition"]["type"], "ne")
        self.assertEqual(changed["children"]["false"], [], "nothing runs while the camera row is unchanged")
        apply = changed["children"]["true"]
        self.assertEqual(apply[0]["args"]["variable"], climb.VAR_CULL_TOP)
        culled = {e["children"]["true"][0]["args"]["actorId"] for e in apply if e["command"] == "EVENT_IF"}
        always = {a["id"] for a in Fixture.actors if climb.cull_range(a["y"]) == (-128, 127)}
        self.assertEqual(culled | always, {a["id"] for a in Fixture.actors})
        self.assertFalse(culled & always)
        for actor in Fixture.actors:
            footprint = next(f for f in climb.sprite_footprints()
                             if (f["x"], f["anchor"]) == (actor["x"], actor["y"]))
            lo, hi = climb.cull_range(actor["y"])
            for true_top in range(climb.CAMERA_MAX_TOP + 1):
                visible = (actor["y"] >= true_top and actor["y"] - footprint["rows"] + 1 <= true_top + 18)
                refresh = true_top - 1 <= actor["y"] <= true_top + 19
                if not (visible or refresh):
                    continue
                for estimate in (true_top - 1, true_top, true_top + 1):
                    s_est = min(max(estimate, 0), climb.CAMERA_MAX_TOP)
                    self.assertTrue((lo == -128 or s_est >= lo) and (hi == 127 or s_est <= hi),
                                    f"{actor['symbol']} culled at camera {true_top} (estimate {s_est})")

    def test_in_play_text_lifts_the_hud_cutoff_first(self):
        scripts = [Fixture.script, Fixture.by_symbol["marta_checkpoint"]["script"],
                   Fixture.triggers_by_symbol["trigger_marta_arrival"]["script"],
                   *[box["script"] for box in Fixture.boxes.values()]]

        def sequences(events):
            yield events
            for e in events:
                for branch in e.get("children", {}).values():
                    yield from sequences(branch)

        checked = 0
        for script in scripts:
            for events in sequences(script):
                for i, e in enumerate(events):
                    if e["command"] == "EVENT_TEXT":
                        checked += 1
                        self.assertEqual(events[i - 1]["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                        self.assertEqual(events[i - 1]["args"]["y"]["value"], 150)
        self.assertGreaterEqual(checked, 15)

    def test_dialogue_fits_and_hud_uses_two_digit_tokens(self):
        everything = [Fixture.script, Fixture.resource["playerHit1Script"],
                      *[a["script"] for a in Fixture.actors], *[t["script"] for t in Fixture.triggers],
                      *[box["script"] for box in Fixture.boxes.values()]]
        lines = [part for s in everything for t in texts(s) for page in t for part in page.split("\n")]
        self.assertGreater(len(lines), 20)
        self.assertTrue(all(len(part) <= scene.MAX_DIALOGUE_CHARS for part in lines), lines)
        draws = {e["args"]["text"] for s in everything for e in flatten(s) if e["command"] == "EVENT_TEXT_DRAW"}
        self.assertEqual(draws - {intro.dev_label(), None}, {scene.HUD_TEXT})
        self.assertEqual(scene.HUD_TEXT, "LINE %D1$45$/5 HOME %D1$00$/1")
        self.assertTrue(all(len(token) == 2 for token in re.findall(r"\$(\d+)\$", scene.HUD_TEXT)))

    def test_street_exit_returns_to_the_opening(self):
        trigger = Fixture.triggers_by_symbol["trigger_street_exit"]
        self.assertEqual(rect(trigger), climb.STREET_EXIT)
        cutoff, hide, switch = trigger["script"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        self.assertEqual(switch["args"]["sceneId"], opening.resource_id("scene:service-opening"))
        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), opening.EXIT_NUDGE)
        self.assertGreater(climb.START[0], trigger["x"] + trigger["width"])

    def test_summit_exit_leads_to_ridge_only_after_amaras_checkpoint(self):
        trigger = Fixture.triggers_by_symbol["trigger_summit_exit"]
        self.assertEqual(rect(trigger), ridge.CLIMB_SUMMIT_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"], {"type": "variable", "value": ridge.CLIMB_EXIT_GATE_VAR})
        nudge = gate["children"]["false"][0]
        self.assertLess(nudge["args"]["x"]["value"] * 8 + 16, ridge.CLIMB_SUMMIT_EXIT[0] * 8)
        grid = climb.collision_grid()
        x, y, _, h = ridge.CLIMB_SUMMIT_EXIT
        self.assertTrue(all(grid[r][x] == climb.COL_EMPTY for r in range(y, y + h)))
        self.assertEqual(grid[climb.SUMMIT_ROW][x - 1], climb.COL_TOP, "the summit reaches the exit column")


if __name__ == "__main__":
    unittest.main()
