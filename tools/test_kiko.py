"""Emil's job (job 4): 4A pine_hollow, 4B pine_ladder, 4C pine_rim (docs/LEVEL_REDESIGN.md §2 Job 4).

Run: "$PY" -m unittest discover -s tools -p 'test_kiko*.py' (after make_kiko_art / make_kiko_scene /
make_ladder_scene). The shared route, link and chain rules run in test_routes / test_scene_links.
"""
import json
import re
import unittest

import climb
import grid_chain
import hazards
import intro
import kiko
import make_climb_scene as shared
import make_kiko_scene as scene
import make_ladder_scene as ladder
import redesign_maps
import rosa
import scene_links
import scenes
import shaft
import test_routes
import tickets

HOLLOW, LADDER, RIM = kiko.HOLLOW, kiko.LADDER, kiko.RIM
FOLDERS = kiko.SCENE_ORDER
FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite"}
# docs/LEVEL_REDESIGN.md §5: actors, triggers, window OBJ (hero excluded), worst scanline.
SPEC_BUDGETS = {HOLLOW: (12, 8, 26, 10), LADDER: (13, 9, 41, 8), RIM: (9, 5, 21, 9)}


def built(folder, music=FAKE_MUSIC, audio=None, sprites=None):
    audio, sprites = audio or FAKE_AUDIO, sprites or FAKE_SPRITES
    actors = scene.build_actors(folder, sprites)
    extra = [ladder.cull_thread_event(actors)] if folder == LADDER else None
    return {"scene": scene.build_scene(folder, music, audio, extra), "actors": actors,
            "triggers": scene.build_triggers(folder, audio),
            "scripts": scene.box_script_resources(folder, audio)}


BUILT = {folder: built(folder) for folder in FOLDERS}


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


def script_lists(folder):
    b = BUILT[folder]
    lists = [b["scene"]["script"], b["scene"]["playerHit1Script"]]
    for actor in b["actors"]:
        lists += [actor["script"], actor["startScript"], actor["updateScript"]]
    for trigger in b["triggers"]:
        lists += [trigger["script"], trigger["leaveScript"]]
    lists += [script["script"] for _, script in b["scripts"]]
    return lists


def is_var_if(event, variable, value, kind="eq"):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == kind
            and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


def is_set(event, variable, value):
    return (event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == variable
            and event["args"]["value"]["value"] == value)


def set_positions(events):
    return [(e["args"]["x"]["value"], e["args"]["y"]["value"])
            for e in walk(events) if e["command"] == "EVENT_ACTOR_SET_POSITION"]


class ContractTests(unittest.TestCase):
    def test_maps_match_the_spec(self):
        specs = redesign_maps.load()
        for folder in FOLDERS:
            spec, contract = specs[folder], kiko.SCENES[folder]
            with self.subTest(folder=folder):
                self.assertEqual((contract.map_w, contract.map_h), (spec.width, spec.height))
                self.assertEqual(contract.collision_grid(), spec.grid)
                self.assertEqual(sorted(contract.kinded_lanes()), sorted(spec.lanes))
                self.assertEqual(sorted(contract.boards), sorted(spec.boards))
                self.assertEqual([link.rect for link in contract.links()], [rect for _, rect in spec.triggers])
                self.assertEqual(contract.start, spec.start)
                lines = [{k: v for k, v in line.items() if k in ("number", "pole", "box", "checkpoint")}
                         for line in contract.lines()]
                self.assertEqual(lines, spec.lines)
                house = contract.house or {}
                self.assertEqual([house["npc"]] if house else [], spec.npcs)
                self.assertEqual([house["device"]] if house else [], spec.devices)
        self.assertEqual(kiko.collision_grid(), specs[HOLLOW].grid)
        self.assertEqual((kiko.MAP_W, kiko.MAP_H), (64, 18))

    def test_lines_are_global_with_scene_local_poles_and_boxes(self):
        self.assertEqual([line["key"] for line in kiko.LINES], ["feeder", "west", "middle", "east", "house"])
        self.assertEqual([(line["pole_scene"], line["box_scene"]) for line in kiko.LINES],
                         [(HOLLOW, HOLLOW), (HOLLOW, HOLLOW), (HOLLOW, LADDER), (LADDER, LADDER), (LADDER, RIM)])
        grid_chain.check_chain_order(kiko.LINES, scene_order=FOLDERS, axes=kiko.SCENE_AXES)
        # Line 3 and line 5 are the cross-scene carries; their wires leave and enter on edge ports.
        self.assertEqual(kiko.SCENES[HOLLOW].edge_ports, {3: (63, 3)})
        self.assertEqual(kiko.SCENES[LADDER].edge_ports, {3: (0, 29), 5: (19, 2)})
        self.assertEqual(kiko.SCENES[RIM].edge_ports, {5: (0, 2)})
        self.assertEqual(scene_links.JOB_SCENES[kiko.JOB], FOLDERS)
        self.assertEqual(tickets.TICKETS[4]["start"], kiko.START)
        self.assertEqual(kiko.START, scene_links.REDESIGN_START[kiko.JOB])

    def test_ids_follow_the_registry(self):
        self.assertEqual(kiko.SCENE_ID, "4d9329db-9c79-52dd-8372-d215a891bcb8", "the entry scene keeps its id")
        for folder in FOLDERS:
            self.assertEqual(kiko.SCENE_IDS[folder], scenes.REGISTRY[folder]["id"])
            self.assertEqual(BUILT[folder]["scene"]["id"], scenes.REGISTRY[folder]["id"])
            self.assertEqual(BUILT[folder]["scene"]["name"], scenes.REGISTRY[folder]["name"])
            self.assertEqual((BUILT[folder]["scene"]["x"], BUILT[folder]["scene"]["y"]),
                             scenes.editor_position(folder))
        self.assertEqual(len(set(kiko.BACKGROUND_IDS.values())), 3)
        self.assertEqual(kiko.BACKGROUND_IDS[HOLLOW], kiko.BACKGROUND_ID)

    def test_hardest_timings_never_easier_than_priyas(self):
        """Warnings and rests no longer than Priya's (job 3), active windows no shorter."""
        pairs = [
            ((kiko.GUST_WARNING_FRAMES, kiko.GUST_ACTIVE_FRAMES, kiko.GUST_REST_FRAMES),
             (rosa.GUST_WARNING_FRAMES, rosa.GUST_ACTIVE_FRAMES, rosa.GUST_REST_FRAMES)),
            ((kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES),
             (rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES)),
            ((kiko.WHIP_SWAY_FRAMES, kiko.WHIP_SWING_FRAMES, kiko.WHIP_HANG_FRAMES),
             (rosa.WHIP_SWAY_FRAMES, rosa.WHIP_SWING_FRAMES, rosa.WHIP_HANG_FRAMES)),
        ]
        cable = hazards.CABLE_TIMINGS["kiko"]
        rosa_cable = hazards.CABLE_TIMINGS["rosa"]
        pairs.append(((cable[1], cable[2], cable[0]), (rosa_cable[1], rosa_cable[2], rosa_cable[0])))
        for (warn, active, rest), (p_warn, p_active, p_rest) in pairs:
            with self.subTest(emil=(warn, active, rest), priya=(p_warn, p_active, p_rest)):
                self.assertLessEqual(warn, p_warn)
                self.assertGreaterEqual(active, p_active)
                self.assertLessEqual(rest, p_rest)
                self.assertGreaterEqual(warn, 20, "still a readable warning")
        # Spec §1 tier for Emil.
        self.assertEqual((kiko.GUST_WARNING_FRAMES, kiko.GUST_ACTIVE_FRAMES, kiko.GUST_REST_FRAMES), (44, 24, 58))
        self.assertEqual((kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES), (36, 26, 48))
        self.assertEqual((kiko.WHIP_SWAY_FRAMES, kiko.WHIP_SWING_FRAMES, kiko.WHIP_HANG_FRAMES), (36, 24, 46))
        self.assertEqual(cable, (120, 20, 26))

    def test_budgets_match_the_spec(self):
        for folder in FOLDERS:
            actors, triggers, window, line = SPEC_BUDGETS[folder]
            route = next(s for s in kiko.ROUTE_SCENES if s["folder"] == folder)
            with self.subTest(folder=folder):
                self.assertEqual(len(BUILT[folder]["actors"]), actors)
                self.assertEqual(len(BUILT[folder]["triggers"]), triggers)
                self.assertEqual(test_routes.oam_window(route), window)
                self.assertEqual(test_routes.worst_scanline(route), line)
                self.assertLessEqual(line, grid_chain.SCANLINE_OBJ_LIMIT)
                if folder != LADDER:
                    self.assertLessEqual(window + shaft.HERO_OBJ, shaft.OAM_LIMIT)

    def test_ladder_culling_keeps_the_oam_within_40(self):
        route = next(s for s in kiko.ROUTE_SCENES if s["folder"] == LADDER)
        self.assertGreater(test_routes.oam_window(route) + shaft.HERO_OBJ, shaft.OAM_LIMIT,
                           "without the thread the 30-row window overflows (spec: 41+4)")
        loads = [kiko.ladder_oam_load(top) for top in range(kiko.LADDER_CAMERA_MAX_TOP + 1)]
        self.assertLessEqual(max(loads), shaft.OAM_LIMIT, loads)
        self.assertTrue(route["culled"])
        self.assertEqual(len(kiko.ladder_sprites()), len(BUILT[LADDER]["actors"]))

    def test_report_exit_reachable_from_the_last_checkpoint(self):
        route = next(s for s in kiko.ROUTE_SCENES if s["folder"] == RIM)
        routes = test_routes.Routes(route)
        report = scene_links.link(RIM, scene_links.REPORT, scene_links.table("redesign"))
        tiles = routes.exit_tiles(report.rect)
        door_x, door_y = kiko.HOUSE_DOOR
        for source in (kiko.LINES[-1]["checkpoint"], (door_x - 1, door_y)):
            with self.subTest(source=source):
                self.assertTrue(tiles & routes.reach(source))
        self.assertEqual(tickets.REPORT_EXIT, report.rect)
        self.assertEqual(report.gate, kiko.VAR_HOME_POWERED)

    def test_route_scenes_pass_every_rule(self):
        for route in kiko.ROUTE_SCENES:
            for rule, found in test_routes.problems(route).items():
                with self.subTest(folder=route["folder"], rule=rule):
                    self.assertEqual(found, [])


class GeneratedSceneTests(unittest.TestCase):
    def test_checked_in_files_match_the_builders(self):
        music_id, audio_ids, sprite_ids = scene.load_ids()
        for folder in FOLDERS:
            real = built(folder, music_id, audio_ids, sprite_ids)
            directory = scene.scene_dir(folder)
            with self.subTest(folder=folder):
                self.assertEqual(json.loads((directory / "scene.gbsres").read_text()), real["scene"])
                for sub in ("actors", "triggers"):
                    on_disk = {p.name: json.loads(p.read_text()) for p in (directory / sub).glob("*.gbsres")}
                    self.assertEqual(on_disk, {f"{item['symbol']}.gbsres": item for item in real[sub]})
                for path, resource in real["scripts"]:
                    self.assertEqual(json.loads((scene.PROJECT_DIR / path).read_text()), resource)

    def test_ids_and_symbols_are_unique_across_the_job(self):
        events, resources, symbols = [], [], []
        for folder in FOLDERS:
            b = BUILT[folder]
            for script in script_lists(folder):
                events += [e["id"] for e in walk(script)]
            resources += [item["id"] for item in (*b["actors"], *b["triggers"])]
            symbols += [item["symbol"] for item in (*b["actors"], *b["triggers"])]
        self.assertEqual(len(events), len(set(events)))
        self.assertEqual(len(resources), len(set(resources)))
        self.assertEqual(len(symbols), len(set(symbols)))

    def test_entry_scene_resets_the_job_once_and_plays_music_on_a_fresh_start(self):
        init = BUILT[HOLLOW]["scene"]["script"]
        commands = [e["command"] for e in init]
        self.assertEqual(commands[0], "EVENT_PLAYER_SET_SPRITE")
        reset = init[1]
        self.assertTrue(is_var_if(reset, grid_chain.VAR_TICKET, kiko.JOB))
        zeroed = {e["args"]["variable"] for e in reset["children"]["true"] if e["command"] == "EVENT_SET_VALUE"}
        self.assertEqual(zeroed, {line["live_var"] for line in kiko.LINES}
                         | {kiko.VAR_CARRYING_CABLE, kiko.VAR_LINES_LIVE, kiko.VAR_CHAIN_LIVE, kiko.VAR_HOME_POWERED})
        fresh = init[-1]
        self.assertTrue(is_var_if(fresh, grid_chain.VAR_TICKET, kiko.JOB))
        inside = fresh["children"]["true"]
        self.assertEqual(inside[0]["command"], "EVENT_MUSIC_PLAY")
        self.assertTrue(is_set(inside[-1], grid_chain.VAR_TICKET, 0))
        self.assertEqual(sum(e["command"] == "EVENT_MUSIC_PLAY" for e in walk(init)), 1)

    def test_other_scenes_never_reset_or_restart_music(self):
        for folder in (LADDER, RIM):
            init = BUILT[folder]["scene"]["script"]
            with self.subTest(folder=folder):
                self.assertFalse(any(e["command"] == "EVENT_MUSIC_PLAY" for e in walk(init)))
                self.assertFalse(any(is_var_if(e, grid_chain.VAR_TICKET, kiko.JOB) for e in walk(init)))
                self.assertFalse(any(e["command"] == "EVENT_SET_VALUE" and e["args"]["variable"] in
                                     {line["live_var"] for line in kiko.LINES} for e in walk(init)))

    def test_every_scene_restores_a_carried_cable_and_sets_its_poles(self):
        for folder in FOLDERS:
            init = BUILT[folder]["scene"]["script"]
            with self.subTest(folder=folder):
                carry = [i for i, e in enumerate(init) if is_var_if(e, kiko.VAR_CARRYING_CABLE, 0, "ne")]
                self.assertEqual(len(carry), 1)
                hero = init[carry[0]]["children"]["true"][0]
                self.assertEqual((hero["args"]["actorId"], hero["args"]["spriteStateId"]), ("player", "Carry"))
                self.assertGreater(carry[0], 0, "after EVENT_PLAYER_SET_SPRITE")
                poles = [line for line in kiko.LINES if line["pole_scene"] == folder]
                pole_ids = {scene.CHAINS[folder].actor_id(sl["pole"]) for sl in scene.LINES
                            if sl["pole_scene"] == folder}
                states = {(e["args"]["actorId"], e["args"]["spriteStateId"]) for e in walk(init)
                          if e["command"] == "EVENT_ACTOR_SET_STATE" and e["args"]["actorId"] in pole_ids}
                self.assertEqual(len(states), 3 * len(poles))
                # Each pole's own start script uses the same rule (a culled pole re-runs it).
                for actor in BUILT[folder]["actors"]:
                    if actor["id"] in pole_ids:
                        found = {e["args"]["spriteStateId"] for e in walk(actor["startScript"])
                                 if e["command"] == "EVENT_ACTOR_SET_STATE"}
                        self.assertEqual(found, {"Standing", "Snapped", "Snapped+Cable"})

    def test_respawn_drops_the_cable_then_uses_this_scenes_checkpoints(self):
        expected = {HOLLOW: [(20, 8), (39, 11)], LADDER: [(4, 26), (4, 14)], RIM: [(43, 11)]}
        for folder in FOLDERS:
            hit = BUILT[folder]["scene"]["playerHit1Script"]
            with self.subTest(folder=folder):
                self.assertEqual(hit[0]["command"], "EVENT_SOUND_PLAY_EFFECT")
                drops = [i for i, e in enumerate(hit) if is_var_if(e, kiko.VAR_CARRYING_CABLE, 1)]
                moves = [i for i, e in enumerate(hit) if set_positions([e])]
                self.assertTrue(drops and moves and max(drops) < min(moves))
                # Every line's cable drops home, wherever its pole stands.
                self.assertEqual(sum(1 for e in hit if e["command"] == "EVENT_IF"
                                     and e["args"]["condition"]["valueA"]["value"] == kiko.VAR_CARRYING_CABLE),
                                 kiko.LINE_COUNT)
                positions = set(set_positions(hit))
                start = kiko.SCENES[folder].start
                self.assertEqual(positions - {start, (kiko.HOUSE_DOOR[0] - 1, kiko.HOUSE_DOOR[1])},
                                 set(expected[folder]))
                self.assertIn(start, positions)

    def test_exits_come_from_scene_links_first_in_trigger_order(self):
        for folder in FOLDERS:
            links = kiko.SCENES[folder].links()
            triggers = BUILT[folder]["triggers"]
            with self.subTest(folder=folder):
                for link, trigger in zip(links, triggers):
                    self.assertEqual((trigger["x"], trigger["y"], trigger["width"], trigger["height"]), link.rect)
                    top = trigger["script"][0]
                    if link.gate is None:
                        self.assertEqual(top["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                        go = trigger["script"]
                    else:
                        self.assertTrue(is_var_if(top, link.gate, 1))
                        go = top["children"]["true"]
                        refusal = [e["args"]["text"] for e in walk(top["children"]["false"])
                                   if e["command"] == "EVENT_TEXT"]
                        self.assertEqual(refusal, [["Power Emil's\nhouse first."]])
                    self.assertEqual([e["command"] for e in go[:2]],
                                     ["EVENT_OVERLAY_SET_SCANLINE_CUTOFF", "EVENT_OVERLAY_HIDE"])
                    switch = go[-1]
                    self.assertEqual(switch["command"], "EVENT_SWITCH_SCENE")
                    self.assertEqual(switch["args"]["sceneId"], scene_links.scene_id(link.target))
                    self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), link.entry)
                    self.assertEqual(switch["args"]["fadeSpeed"], "2")
                others = [t for t in triggers[len(links):]
                          if any(e["command"] == "EVENT_SWITCH_SCENE" for e in walk(t["script"]))]
                self.assertEqual(others, [])
        rim = BUILT[RIM]["triggers"]
        self.assertEqual([t["symbol"] for t in rim[:3]],
                         ["trigger_rim_exit_pine_ladder", "trigger_rim_report_exit", scene.DOOR_TRIGGER_SYMBOL])
        self.assertEqual(rim[1]["id"], kiko.resource_id("trigger:report-exit"))

    def test_door_powers_the_house_once_with_all_five_lines(self):
        door = next(t for t in BUILT[RIM]["triggers"] if t["symbol"] == scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual((door["x"], door["y"], door["width"], door["height"]), kiko.DOOR_TRIGGER)
        top = door["script"][0]
        self.assertTrue(is_var_if(top, kiko.VAR_LINES_LIVE, kiko.LINE_COUNT))
        once = top["children"]["true"][0]
        self.assertTrue(is_var_if(once, kiko.VAR_HOME_POWERED, 0))
        self.assertTrue(is_set(once["children"]["true"][0], kiko.VAR_HOME_POWERED, 1))
        texts = [e["args"]["text"] for e in walk(once["children"]["true"]) if e["command"] == "EVENT_TEXT"]
        self.assertIn(tickets.closed_lines(4), texts)
        # Emil, the stove and the window follow var 13 on every entry, too.
        init = BUILT[RIM]["scene"]["script"]
        home = next(e for e in init if is_var_if(e, kiko.VAR_HOME_POWERED, 1))
        self.assertEqual({e["args"].get("spriteStateId") for e in home["children"]["true"]} - {None},
                         {"Relieved", "On"})

    def test_every_dialogue_line_fits_and_follows_a_cutoff(self):
        self.assertEqual(scene.MAX_DIALOGUE_CHARS, 17)
        for folder in FOLDERS:
            checked = 0
            for script in script_lists(folder):
                for events in sequences(script):
                    for i, entry in enumerate(events):
                        if entry["command"] != "EVENT_TEXT":
                            continue
                        checked += 1
                        before = events[i - 1]
                        self.assertEqual((before["command"], before["args"]["y"]["value"]),
                                         ("EVENT_OVERLAY_SET_SCANLINE_CUTOFF", 150))
                        redraws = [e for e in events[i + 1:] if e["command"] == "EVENT_TEXT_DRAW"]
                        self.assertEqual(redraws[0]["args"]["text"], kiko.HUD_TEXT)
                        for text in entry["args"]["text"]:
                            for part in text.split("\n"):
                                self.assertLessEqual(len(part), scene.MAX_DIALOGUE_CHARS, part)
            with self.subTest(folder=folder):
                self.assertGreater(checked, 5)

    def test_hud_is_drawn_on_every_entry(self):
        for folder in FOLDERS:
            init = BUILT[folder]["scene"]["script"]
            draws = [e for e in init if e["command"] == "EVENT_TEXT_DRAW"]
            with self.subTest(folder=folder):
                self.assertEqual(draws[0]["args"]["text"], kiko.HUD_TEXT)
        self.assertEqual(re.findall(r"\$(\d+)\$", kiko.HUD_TEXT), [kiko.VAR_LINES_LIVE, kiko.VAR_HOME_POWERED])

    def test_hazards_use_the_job_timings(self):
        for folder in FOLDERS:
            waits = {}
            for actor in BUILT[folder]["actors"]:
                frames = [e["args"]["frames"]["value"] for e in walk(actor["updateScript"])
                          if e["command"] == "EVENT_WAIT"]
                waits.setdefault(actor["symbol"].split("_", 1)[1].rsplit("_", 1)[0], set()).update(frames)
            with self.subTest(folder=folder):
                self.assertLessEqual({44, 24, 58}, waits["gust"])
                self.assertLessEqual({36, 24, 46}, waits["whip"])
                self.assertLessEqual({36, 26, 48}, waits["span_arc"])
                self.assertLessEqual({120, 20, 26}, waits["hidden_cable"])

    def test_ladder_runs_the_culling_thread_and_every_cycle_starts_safe(self):
        init = BUILT[LADDER]["scene"]["script"]
        thread = init[-1]
        self.assertEqual(thread["command"], "EVENT_THREAD_START")
        for folder in (HOLLOW, RIM):
            self.assertFalse(any(e["command"] == "EVENT_THREAD_START" for e in walk(BUILT[folder]["scene"]["script"])))
        activated = {e["args"]["actorId"] for e in walk([thread]) if e["command"] == "EVENT_ACTOR_ACTIVATE"}
        bounded = {a["id"] for a in BUILT[LADDER]["actors"]
                   if shaft.cull_condition(a["y"], kiko.LADDER_CAMERA_MAX_TOP) is not None}
        self.assertEqual(activated, bounded)
        self.assertTrue(bounded)
        # The thread restarts an update script on reactivation: each live cycle starts safe.
        for actor in BUILT[LADDER]["actors"]:
            if actor["collisionGroup"] != "1" or "board" in actor["symbol"]:
                continue
            update = actor["updateScript"]
            if update[0]["command"] == "EVENT_IF" and "span_arc" in actor["symbol"]:
                update = update[0]["children"]["true"]
            commands = [e["command"] for e in update if e["command"] != "EVENT_IF_ACTOR_DIRECTION"]
            with self.subTest(actor=actor["symbol"]):
                first_change = next(c for c in commands if c.startswith("EVENT_ACTOR_COLLISIONS"))
                self.assertEqual(first_change, "EVENT_ACTOR_COLLISIONS_DISABLE")

    def test_box_scripts_bind_only_actors_in_their_scene(self):
        paths = {}
        for folder in FOLDERS:
            for path, script in BUILT[folder]["scripts"]:
                paths[path] = script
        self.assertEqual(sorted(paths), sorted(f"project/scripts/pine_hollow_box_{line['key']}.gbsres"
                                               for line in kiko.LINES))
        for line in scene.LINES:
            script = paths[f"project/scripts/pine_hollow_box_{line['key']}.gbsres"]
            with self.subTest(line=line["key"]):
                expected = 1 if line["pole_scene"] == line["box_scene"] else 0
                self.assertEqual(len(script["actors"]), expected)

    def test_variables_register_without_changing_existing(self):
        data = {"variables": [{"id": "0", "name": "Amara Checkpoint", "symbol": "var_marta_checkpoint"}]}
        merged = scene.merged_variables(data, ladder.CULL_VARIABLES)
        ids = {v["id"] for v in merged["variables"]}
        self.assertLessEqual({v for v, _, _ in kiko.VARIABLES} | {"46", "47", "48", "49"}, ids)
        with self.assertRaises(ValueError):
            scene.merged_variables({"variables": [{"id": "13", "name": "Other", "symbol": "var_other"}]})

    def test_palettes_and_sprite_slots(self):
        for folder in FOLDERS:
            s = BUILT[folder]["scene"]
            with self.subTest(folder=folder):
                self.assertEqual(s["backgroundId"], kiko.BACKGROUND_IDS[folder])
                self.assertEqual(s["paletteIds"][7], "default-ui")
                self.assertEqual(s["paletteIds"][5], scene.chain_palette_id(0))
                self.assertEqual(s["spritePaletteIds"][intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))
                self.assertEqual(s["spritePaletteIds"][hazards.BOARD_SPRITE_PALETTE_SLOT], hazards.BOARD_PALETTE_ID)
                self.assertEqual(s["collisions"], shared.collision_rle(kiko.SCENES[folder].collision_grid(),
                                                                       s["width"], s["height"]))
                self.assertEqual(s["type"], "PLATFORM")
        self.assertEqual(climb.LINE_BG_SLOT, kiko.LINE_BG_SLOT)


if __name__ == "__main__":
    unittest.main()
