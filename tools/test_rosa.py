"""Priya's job (3A signal_hill, 3B signal_gully, 3C signal_porch): contract and scene checks.

Run: python3 -m unittest discover -s tools -p test_rosa.py (managed Python for the scanline
check, which reads the real sprite sidecars). The gully's drop-through route is test_rosa_gully.py.
"""
import json
import unittest
from collections import Counter

import climb
import grid_chain
import hazards
import intro
import make_climb_scene as shared
import make_rosa_scene as scene
import opening
import redesign_maps
import ridge
import rosa
import scene_links
import scenes
import test_routes
import tickets
from test_grid_chain import sprite_budget, sprite_profiles

FAKE_MUSIC = "test-music"
FAKE_AUDIO = {"death": "death-sound", "connect": "connect-sound", "pickup": "pickup-sound"}
FAKE_SPRITES = {"gust": "gust-sprite"}
PROJECT_DIR = scene.PROJECT_DIR
FOLDERS = rosa.SCENE_ORDER
HILL, GULLY, PORCH = FOLDERS


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def sequences(events):
    """Every sibling list, top level first, including branch children."""
    yield events
    for entry in events:
        for branch in entry.get("children", {}).values():
            yield from sequences(branch)


def built(folder):
    builder = scene.SCENES[folder]
    return {"scene": builder.build_scene(FAKE_MUSIC, FAKE_AUDIO), "actors": builder.build_actors(FAKE_SPRITES),
            "triggers": builder.build_triggers(FAKE_AUDIO), "scripts": builder.box_script_resources(FAKE_AUDIO)}


BUILT = {folder: built(folder) for folder in FOLDERS}


def script_lists(folder):
    out = BUILT[folder]
    lists = [out["scene"]["script"], out["scene"]["playerHit1Script"]]
    for actor in out["actors"]:
        lists += [actor["script"], actor["startScript"], actor["updateScript"], actor["hit1Script"]]
    for trigger in out["triggers"]:
        lists += [trigger["script"], trigger["leaveScript"]]
    lists += [script["script"] for _, script in out["scripts"]]
    return lists


def all_events(folder):
    return [event for events in script_lists(folder) for event in walk(events)]


def is_set(event, variable, value):
    return (event["command"] == "EVENT_SET_VALUE" and event["args"]["variable"] == variable
            and event["args"]["value"].get("value") == value)


def is_var_if(event, variable, value, kind="eq"):
    condition = event["args"].get("condition", {})
    return (event["command"] == "EVENT_IF" and condition.get("type") == kind
            and condition.get("valueA", {}).get("value") == variable
            and condition.get("valueB", {}).get("value") == value)


def actor(folder, symbol):
    return next(a for a in BUILT[folder]["actors"] if a["symbol"] == symbol)


def trigger_rect(trigger):
    return (trigger["x"], trigger["y"], trigger["width"], trigger["height"])


class ContractTests(unittest.TestCase):
    """rosa.py against the spec's §2 maps (docs/LEVEL_REDESIGN.md) and the shared route rules."""

    @classmethod
    def setUpClass(cls):
        cls.specs = redesign_maps.load()

    def test_maps_equal_the_spec(self):
        for folder in FOLDERS:
            spec = self.specs[folder]
            with self.subTest(folder=folder):
                self.assertEqual(rosa.size(folder), (spec.width, spec.height))
                self.assertEqual(rosa.collision_grid(folder), spec.grid)
                self.assertEqual(rosa.LAYOUTS[folder]["start"], spec.start)
                self.assertLessEqual(set(spec.entries), set(rosa.entries(folder)))
                self.assertEqual(set(rosa.entries(folder)) - set(spec.entries),
                                 {l.entry for l in scene_links.table("redesign")
                                  if l.target == folder and l.ticket is None} - set(spec.entries))
                self.assertEqual(rosa.npcs(folder), spec.npcs)
                self.assertEqual(rosa.devices(folder), spec.devices)

    def test_lines_equal_the_spec(self):
        for folder in FOLDERS:
            spec = {line["number"]: line for line in self.specs[folder].lines}
            here = {line["number"]: line for line in rosa.lines_here(folder)}
            with self.subTest(folder=folder):
                self.assertEqual(set(here), set(spec))
                for number, line in here.items():
                    for name in ("pole", "box", "checkpoint"):
                        self.assertEqual(line.get(name), spec[number].get(name), (number, name))

    def test_hazards_equal_the_spec(self):
        for folder in FOLDERS:
            spec = self.specs[folder]
            with self.subTest(folder=folder):
                self.assertEqual(sorted(rosa.route_lanes(folder)), sorted(spec.lanes))
                self.assertEqual(sorted(rosa.LAYOUTS[folder]["boards"]), sorted(spec.boards))
                self.assertEqual(rosa.hazard_count(folder), len(spec.lanes) + len(spec.boards))
        self.assertEqual(sum(rosa.hazard_count(f) for f in FOLDERS), 20, "spec §1: 20 hazards (was 13)")

    def test_exits_equal_the_spec_and_scene_links(self):
        for folder in FOLDERS:
            with self.subTest(folder=folder):
                self.assertEqual([link.rect for link in rosa.links(folder)],
                                 [rect for _, rect in self.specs[folder].triggers])
        self.assertEqual(rosa.HILL_EXIT, rosa.downstream_exit(HILL))
        porch_exit = scene_links.link(PORCH, "pine_hollow", scene_links.table("redesign"))
        self.assertEqual((porch_exit.gate, porch_exit.ticket), (rosa.VAR_HOME_POWERED, 4))

    def test_route_scenes_pass_every_rule_with_the_spec_budgets(self):
        self.assertEqual([s["folder"] for s in rosa.ROUTE_SCENES], list(FOLDERS))
        for route in rosa.ROUTE_SCENES:
            with self.subTest(folder=route["folder"]):
                for rule, found in test_routes.problems(route).items():
                    self.assertEqual(found, [], rule)
                spec = self.specs[route["folder"]].validator
                self.assertEqual(test_routes.oam_window(route), spec["window"])
                self.assertEqual(test_routes.worst_scanline(route), spec["scanline"])
                self.assertLessEqual(test_routes.oam_window(route) + 4, 40, "OAM window without culling")
                self.assertFalse(route["culled"])

    def test_lines_are_global_and_scenes_ordered(self):
        self.assertEqual([line["key"] for line in rosa.LINES], ["feeder", "west", "middle", "east", "house"])
        self.assertEqual([line["live_var"] for line in rosa.LINES], ["21", "30", "31", "32", "10"])
        self.assertEqual([(line["pole_scene"], line["box_scene"]) for line in rosa.LINES],
                         [(HILL, HILL), (HILL, HILL), (HILL, GULLY), (GULLY, GULLY), (GULLY, PORCH)])
        grid_chain.check_chain_order(rosa.LINES, scene_order=FOLDERS, axes=rosa.SCENE_AXES)
        self.assertEqual(scenes.JOB_SCENES[3], FOLDERS)
        # Two cross-scene carries (spec §1): cables 3 and 5.
        self.assertEqual([line["number"] for line in rosa.LINES if line["pole_scene"] != line["box_scene"]], [3, 5])

    def test_timings_are_tighter_than_wind_ridge(self):
        self.assertEqual((rosa.GUST_WARNING_FRAMES, rosa.GUST_ACTIVE_FRAMES, rosa.GUST_REST_FRAMES), (44, 22, 62))
        self.assertEqual((rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES),
                         (40, 24, 52))
        self.assertEqual((rosa.WHIP_SWAY_FRAMES, rosa.WHIP_SWING_FRAMES, rosa.WHIP_HANG_FRAMES), (36, 22, 54))
        self.assertEqual(rosa.CABLE_TIMINGS, (140, 20, 24))
        self.assertLess(rosa.GUST_REST_FRAMES, ridge.GUST_REST_FRAMES)
        self.assertLessEqual(rosa.GUST_WARNING_FRAMES, ridge.GUST_WARNING_FRAMES)
        self.assertLess(rosa.WHIP_HANG_FRAMES, ridge.WHIP_HANG_FRAMES)
        self.assertLess(rosa.JOB_ARC_REST_FRAMES, ridge.JOB_ARC_REST_FRAMES)
        self.assertLess(rosa.CABLE_TIMINGS[0], hazards.cable_timings("wind_ridge")[0])
        # The lab and the climb keep Amara's arc tier.
        self.assertEqual((rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES), (48, 24, 80))

    def test_wires_cross_the_scene_edges_on_their_ports(self):
        for stage, rows in rosa.EDGE_PORTS.items():
            for folder, row in rows.items():
                width = rosa.size(folder)[0]
                cells = {c for s, route in rosa.WIRE_ROUTES_BY_SCENE[folder] if s == stage for c in route}
                with self.subTest(stage=stage, folder=folder):
                    self.assertTrue({(0, row), (width - 1, row)} & cells)
        self.assertEqual({s for s, _ in rosa.WIRE_ROUTES_BY_SCENE[HILL]}, {1, 2, 3})
        self.assertEqual({s for s, _ in rosa.WIRE_ROUTES_BY_SCENE[GULLY]}, {3, 4, 5})
        self.assertEqual({s for s, _ in rosa.WIRE_ROUTES_BY_SCENE[PORCH]}, {5})

    def test_ids_are_stable_and_registered(self):
        self.assertEqual(rosa.SCENE_ID, "7c856987-bbdf-5d75-a97e-327259a90956")
        for folder in FOLDERS:
            self.assertEqual(rosa.SCENE_IDS[folder], scenes.REGISTRY[folder]["id"])
        ids = [*rosa.SCENE_IDS.values(), *rosa.BACKGROUND_IDS.values(), rosa.ROSA_SPRITE_ID,
               rosa.WORKSTATION_SPRITE_ID, rosa.ARC_SPRITE_ID]
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(tickets.TICKETS[3]["scene_id"], rosa.SCENE_ID)
        self.assertEqual(tuple(tickets.TICKETS[3]["start"]), scene_links.REDESIGN_START[3])

    def test_names_other_jobs_import_stay(self):
        for name in ("ARC_SPRITE_ID", "ARC_SPRITE_PALETTE_SLOT", "ARC_SPRITE_HARDWARE", "GUST_SPRITE_PALETTE_SLOT",
                     "PORCH_ROW", "DOOR_TRIGGER", "MAP_W", "VAR_HOME_POWERED", "RIDGE_EXIT", "RIDGE_EXIT_GATE_VAR",
                     "ROSA_SPRITE_HARDWARE", "WORKSTATION_SPRITE_ID", "ROSA_SPRITE_ID"):
            self.assertTrue(hasattr(rosa, name), name)


class SceneTests(unittest.TestCase):
    """The three generated scenes (builders with fake asset IDs)."""

    def test_scene_resources(self):
        for folder in FOLDERS:
            resource = BUILT[folder]["scene"]
            width, height = rosa.size(folder)
            with self.subTest(folder=folder):
                self.assertEqual(resource["id"], scenes.REGISTRY[folder]["id"])
                self.assertEqual(resource["name"], scenes.REGISTRY[folder]["name"])
                self.assertEqual((resource["x"], resource["y"]), scenes.editor_position(folder))
                self.assertEqual((resource["type"], resource["width"], resource["height"]), ("PLATFORM", width, height))
                self.assertEqual(resource["backgroundId"], rosa.BACKGROUND_IDS[folder])
                self.assertEqual(resource["collisions"],
                                 shared.collision_rle(rosa.collision_grid(folder), width, height))
                palettes = resource["paletteIds"]
                self.assertEqual(palettes[5], scene.chain_palette_id(0))
                self.assertEqual(palettes[6], grid_chain.chain_palette_id(rosa.resource_id, 0, 6))
                self.assertEqual(palettes[7], "default-ui")
                sprites = resource["spritePaletteIds"]
                self.assertEqual(sprites[rosa.ARC_SPRITE_PALETTE_SLOT], scene.arc_palette_id())
                self.assertEqual(sprites[intro.SPRITE_SLOTS["pole"]], intro.palette_id("pole"))

    def test_ids_unique_across_the_three_scenes(self):
        events = [e["id"] for folder in FOLDERS for e in all_events(folder)]
        duplicates = [i for i, n in Counter(events).items() if n > 1]
        self.assertEqual(duplicates, [])
        actors = [a["id"] for folder in FOLDERS for a in BUILT[folder]["actors"]]
        triggers = [t["id"] for folder in FOLDERS for t in BUILT[folder]["triggers"]]
        scripts = [s["id"] for folder in FOLDERS for _, s in BUILT[folder]["scripts"]]
        for ids in (actors, triggers, scripts, actors + triggers + scripts):
            self.assertEqual(len(ids), len(set(ids)))
        for folder in FOLDERS:
            symbols = [a["symbol"] for a in BUILT[folder]["actors"]] + [t["symbol"] for t in BUILT[folder]["triggers"]]
            self.assertEqual(len(symbols), len(set(symbols)))
            self.assertTrue(all(s.replace("_", "").isalnum() for s in symbols), symbols)

    def test_hill_keeps_its_ids(self):
        pole = actor(HILL, "rosa_feeder_pole")
        self.assertEqual(pole["id"], rosa.resource_id("actor:pole:feeder"))
        self.assertEqual(actor(HILL, "signal_arc_01")["id"], rosa.resource_id("actor:arc:1"))
        self.assertEqual(actor(GULLY, scene.POLE_SYMBOL)["id"], rosa.resource_id("actor:signal_gully:pole"))

    def test_box_scripts_one_scene_each(self):
        by_folder = {folder: {s["id"] for _, s in BUILT[folder]["scripts"]} for folder in FOLDERS}
        for line in rosa.LINES:
            owners = [f for f, ids in by_folder.items() if scene.CHAIN.box_script_id(line) in ids]
            self.assertEqual(owners, [line["box_scene"]], line["key"])
        paths = [p for folder in FOLDERS for p, _ in BUILT[folder]["scripts"]]
        self.assertEqual(len(paths), len(set(paths)))

    def test_actor_roster_matches_the_contract(self):
        for folder in FOLDERS:
            actors = BUILT[folder]["actors"]
            layout = rosa.LAYOUTS[folder]
            with self.subTest(folder=folder):
                self.assertEqual(len(actors), rosa.actor_count(folder))
                self.assertEqual([a["_index"] for a in actors], list(range(len(actors))))
                poles = [a for a in actors if a["spriteSheetId"] == intro.POLE_SPRITE_ID]
                self.assertEqual([(a["x"], a["y"]) for a in poles], [l["pole"] for l in rosa.pole_lines(folder)])
                positions = {(a["x"], a["y"]) for a in actors}
                for row, x0, _ in [*layout["arcs"], *layout["gusts"], *rosa.span_arc_lanes(folder),
                                   *layout["cables"]]:
                    self.assertIn((x0, row), positions)
                for row, x0, _ in layout["whips"]:
                    self.assertIn((x0, row + 1), positions)
                for board in layout["boards"]:
                    self.assertIn(hazards.board_actor_position(board), positions)
                self.assertTrue(actors[-1]["symbol"].endswith(f"_board_{len(layout['boards']):02d}"),
                                "boards draw on top")
        self.assertEqual((actor(PORCH, scene.ROSA_SYMBOL)["x"], actor(PORCH, scene.ROSA_SYMBOL)["y"]), rosa.ROSA)
        self.assertEqual((actor(PORCH, scene.WORKSTATION_SYMBOL)["x"],
                          actor(PORCH, scene.WORKSTATION_SYMBOL)["y"]), rosa.WORKSTATION)

    def test_exits_come_first_and_follow_scene_links(self):
        for folder in FOLDERS:
            triggers = BUILT[folder]["triggers"]
            links = rosa.links(folder)
            with self.subTest(folder=folder):
                self.assertEqual([trigger_rect(t) for t in triggers[:len(links)]], [l.rect for l in links])
                for trigger, link in zip(triggers, links):
                    switches = [e for e in walk(trigger["script"]) if e["command"] == "EVENT_SWITCH_SCENE"]
                    self.assertEqual(len(switches), 1)
                    args = switches[0]["args"]
                    self.assertEqual(args["fadeSpeed"], scene_links.FADE_SPEED)
                    if link.ticket is None:
                        self.assertEqual(args["sceneId"], scenes.REGISTRY[link.target]["id"])
                        self.assertEqual((args["x"]["value"], args["y"]["value"]), link.entry)
                        self.assertEqual(args["direction"], link.facing)
                        self.assertNotEqual(trigger["script"][0]["command"], "EVENT_IF", "internal: ungated")
                    else:
                        self.assertTrue(is_var_if(trigger["script"][0], link.gate, 1))
                        events = list(walk(trigger["script"]))
                        self.assertTrue(any(is_set(e, scene_links.VAR_TICKET, link.ticket) for e in events))
                    go = next(seq for seq in sequences(trigger["script"])
                              if any(e["command"] == "EVENT_SWITCH_SCENE" for e in seq))
                    commands = [e["command"] for e in go]
                    self.assertLess(commands.index("EVENT_OVERLAY_HIDE"), commands.index("EVENT_SWITCH_SCENE"))
                    self.assertEqual(go[0]["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")

    def test_zones_only_for_local_poles_and_boxes(self):
        for folder in FOLDERS:
            symbols = [t["symbol"] for t in BUILT[folder]["triggers"]]
            with self.subTest(folder=folder):
                self.assertEqual(sorted(s for s in symbols if s.endswith("_reach")),
                                 sorted(f"trigger_signal_{l['key']}_reach" for l in rosa.box_lines(folder)))
                self.assertEqual(sorted(s for s in symbols if s.endswith("_pole_zone")),
                                 sorted(f"trigger_signal_{l['key']}_pole_zone" for l in rosa.pole_lines(folder)))
                boards = [t for t in BUILT[folder]["triggers"] if "cracked_board" in t["symbol"]]
                self.assertEqual([trigger_rect(t) for t in boards],
                                 [hazards.board_trigger_rect(b) for b in rosa.LAYOUTS[folder]["boards"]])
                grid_chain.check_scene_limits(len(BUILT[folder]["actors"]), len(BUILT[folder]["triggers"]))

    def test_entry_scene_resets_once_and_plays_music_on_a_fresh_start(self):
        script = BUILT[HILL]["scene"]["script"]
        commands = [e["command"] for e in script]
        self.assertEqual(commands[0], "EVENT_PLAYER_SET_SPRITE")
        reset = script[1]
        self.assertTrue(is_var_if(reset, grid_chain.VAR_TICKET, rosa.JOB))
        zeroed = {e["args"]["variable"] for e in reset["children"]["true"] if e["command"] == "EVENT_SET_VALUE"}
        self.assertEqual(zeroed, {rosa.VAR_CARRYING_CABLE, rosa.VAR_LINES_LIVE, rosa.VAR_CHAIN_LIVE,
                                  rosa.VAR_HOME_POWERED, *(l["live_var"] for l in rosa.LINES),
                                  *(v for v, _, _ in grid_chain.VARIABLES)})
        # Outside the reset, the init never clears the job (a carried cable survives the edge).
        top_sets = {e["args"]["variable"] for e in script if e["command"] == "EVENT_SET_VALUE"}
        self.assertTrue(top_sets.isdisjoint(zeroed), top_sets)
        fresh = script[-1]
        self.assertTrue(is_var_if(fresh, grid_chain.VAR_TICKET, rosa.JOB))
        inner = [e["command"] for e in fresh["children"]["true"]]
        self.assertEqual(inner[0], "EVENT_MUSIC_PLAY")
        self.assertTrue(is_set(fresh["children"]["true"][-1], grid_chain.VAR_TICKET, 0))
        self.assertEqual(sum(e["command"] == "EVENT_MUSIC_PLAY" for e in walk(script)), 1)

    def test_other_scenes_never_reset_or_play_music(self):
        for folder in (GULLY, PORCH):
            script = [e for e in BUILT[folder]["scene"]["script"] if e["command"] != "EVENT_SET_INPUT_SCRIPT"]
            events = list(walk(script))
            with self.subTest(folder=folder):
                self.assertFalse(any(e["command"] == "EVENT_MUSIC_PLAY" for e in events))
                self.assertFalse(any(is_var_if(e, grid_chain.VAR_TICKET, rosa.JOB) for e in events))
                self.assertFalse(any(e["command"] == "EVENT_SET_VALUE"
                                     and e["args"]["variable"] in {rosa.VAR_CARRYING_CABLE, grid_chain.VAR_TICKET}
                                     for e in events))

    def test_init_restores_poles_carry_and_hud(self):
        for folder in FOLDERS:
            script = BUILT[folder]["scene"]["script"]
            chain = scene.SCENES[folder].chain
            with self.subTest(folder=folder):
                commands = [e["command"] for e in script]
                self.assertEqual(commands[0], "EVENT_PLAYER_SET_SPRITE")
                carry = next(i for i, e in enumerate(script)
                             if is_var_if(e, rosa.VAR_CARRYING_CABLE, 0, kind="ne"))
                self.assertEqual(script[carry]["children"]["true"][0]["args"],
                                 {"actorId": "player", "spriteStateId": "Carry", "loopAnim": True})
                attach = next(i for i, e in enumerate(script) if e["command"] == "EVENT_SET_INPUT_SCRIPT")
                refresh = next(i for i, e in enumerate(script) if is_var_if(e, rosa.LINES[0]["live_var"], 1))
                self.assertLess(attach, refresh)
                self.assertLess(refresh, carry)
                for line in chain.pole_lines():
                    pole = chain.actor_id(line["pole"])
                    init = next(e for e in script if is_var_if(e, line["live_var"], 1)
                                and e["children"]["true"][0]["args"].get("actorId") == pole)
                    self.assertEqual(init["children"]["true"][0]["args"]["spriteStateId"], "Standing")
                    carried = init["children"]["false"][0]
                    self.assertTrue(is_var_if(carried, rosa.VAR_CARRYING_CABLE, line["number"]))
                    self.assertEqual(carried["children"]["true"][0]["args"]["spriteStateId"], "Snapped")
                    self.assertEqual(carried["children"]["false"][0]["args"]["spriteStateId"], "Snapped+Cable")
                draws = [e for e in script if e["command"] == "EVENT_TEXT_DRAW"]
                self.assertEqual(draws[0]["args"]["text"], rosa.HUD_TEXT)

    def test_respawn_drops_the_cable_then_uses_this_scenes_checkpoints(self):
        for folder in FOLDERS:
            hit = BUILT[folder]["scene"]["playerHit1Script"]
            with self.subTest(folder=folder):
                drops = [i for i, e in enumerate(hit) if is_var_if(e, rosa.VAR_CARRYING_CABLE, 1)]
                moves = [i for i, e in enumerate(hit) if any(x["command"] == "EVENT_ACTOR_SET_POSITION"
                                                             for x in walk([e]))]
                self.assertTrue(drops and moves and max(drops) < min(moves))
                # Every line's cable drops, wherever its pole stands (Abe: a hit sends it home).
                self.assertEqual(sum(1 for e in hit if e["command"] == "EVENT_IF"
                                     and e["args"]["condition"]["valueA"]["value"] == rosa.VAR_CARRYING_CABLE),
                                 rosa.LINE_COUNT)
                targets = {(e["args"]["x"]["value"], e["args"]["y"]["value"]) for e in walk(hit)
                           if e["command"] == "EVENT_ACTOR_SET_POSITION"}
                expected = {rosa.LAYOUTS[folder]["start"]}
                expected |= {l["checkpoint"] for l in rosa.lines_here(folder) if "checkpoint" in l}
                if folder == PORCH:
                    expected.add((rosa.HOUSE_DOOR[0] - 1, rosa.HOUSE_DOOR[1]))
                self.assertEqual(targets, expected)

    def test_every_text_lifts_the_cutoff_redraws_the_hud_and_fits(self):
        checked = 0
        for folder in FOLDERS:
            for events in script_lists(folder):
                for seq in sequences(events):
                    for i, e in enumerate(seq):
                        if e["command"] != "EVENT_TEXT":
                            continue
                        checked += 1
                        before = seq[i - 1]
                        self.assertEqual(before["command"], "EVENT_OVERLAY_SET_SCANLINE_CUTOFF")
                        self.assertEqual(before["args"]["y"]["value"], 150)
                        after = [x for x in seq[i + 1:] if x["command"] == "EVENT_TEXT_DRAW"]
                        self.assertTrue(after and after[0]["args"]["text"] == rosa.HUD_TEXT)
                        for page in e["args"]["text"]:
                            for line in page.split("\n"):
                                self.assertLessEqual(len(line), scene.MAX_DIALOGUE_CHARS, line)
        self.assertGreaterEqual(checked, 40)

    def test_gully_teaches_the_drop(self):
        hint = BUILT[GULLY]["scene"]["script"][-1]
        self.assertTrue(is_var_if(hint, rosa.VAR_MIDDLE_LIVE, 0))
        texts = [e["args"]["text"] for e in walk([hint]) if e["command"] == "EVENT_TEXT"]
        self.assertTrue(any("Down + A" in page for text in texts for page in text))

    def test_hazard_timings_in_the_scripts(self):
        for folder in FOLDERS:
            for a in BUILT[folder]["actors"]:
                waits = [e["args"]["frames"]["value"] for e in walk(a["updateScript"]) if e["command"] == "EVENT_WAIT"]
                if "_hidden_cable_" in a["symbol"]:
                    self.assertEqual(waits[-3:], list(rosa.CABLE_TIMINGS))
                elif "_gust_" in a["symbol"]:
                    self.assertEqual(waits[-3:], [rosa.GUST_WARNING_FRAMES, rosa.GUST_ACTIVE_FRAMES,
                                                  rosa.GUST_REST_FRAMES])
                elif "_span_arc_" in a["symbol"]:
                    self.assertEqual(waits[-4:-1], [rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES,
                                                    rosa.JOB_ARC_REST_FRAMES])
                elif "_arc_" in a["symbol"]:
                    self.assertEqual(waits[-3:], [rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES,
                                                  rosa.JOB_ARC_REST_FRAMES])
                elif "_whip_" in a["symbol"]:
                    self.assertEqual(waits[-3:], [rosa.WHIP_SWAY_FRAMES, rosa.WHIP_SWING_FRAMES,
                                                  rosa.WHIP_HANG_FRAMES])
                if a["collisionGroup"] == "1":
                    self.assertEqual(a["startScript"][0]["command"] in ("EVENT_ACTOR_COLLISIONS_DISABLE",), True,
                                     a["symbol"])

    def test_span_arcs_wait_for_their_lines(self):
        for folder in FOLDERS:
            spans = [a for a in BUILT[folder]["actors"] if "_span_arc_" in a["symbol"]]
            expected = [span["live_after"] for span in rosa.LAYOUTS[folder]["spans"]]
            gates = [a["updateScript"][0]["args"]["condition"]["valueB"]["value"] for a in spans]
            self.assertEqual(gates, expected, folder)

    def test_porch_door_and_priya(self):
        door = next(t for t in BUILT[PORCH]["triggers"] if t["symbol"] == scene.DOOR_TRIGGER_SYMBOL)
        self.assertEqual(trigger_rect(door), rosa.DOOR_TRIGGER)
        gate = door["script"][0]
        self.assertTrue(is_var_if(gate, rosa.VAR_LINES_LIVE, rosa.LINE_COUNT))
        power = gate["children"]["true"][0]
        self.assertTrue(is_var_if(power, rosa.VAR_HOME_POWERED, 0))
        self.assertTrue(any(is_set(e, rosa.VAR_HOME_POWERED, 1) for e in power["children"]["true"]))
        exit_index = next(i for i, t in enumerate(BUILT[PORCH]["triggers"]) if "work_order" in t["symbol"])
        door_index = BUILT[PORCH]["triggers"].index(door)
        self.assertLess(exit_index, door_index, "the exit fires before the door at the wall")
        # Re-entering after the payoff restores Priya, her workstation and the warm window.
        for symbol, states in ((scene.ROSA_SYMBOL, ("Relieved", "Waiting")), (scene.WORKSTATION_SYMBOL, ("On", "Off"))):
            start = actor(PORCH, symbol)["startScript"][0]
            self.assertTrue(is_var_if(start, rosa.VAR_HOME_POWERED, 1))
            self.assertEqual((start["children"]["true"][0]["args"]["spriteStateId"],
                              start["children"]["false"][0]["args"]["spriteStateId"]), states)
        window = next(e for e in BUILT[PORCH]["scene"]["script"] if is_var_if(e, rosa.VAR_HOME_POWERED, 1))
        self.assertEqual(window["children"]["true"][0]["args"]["palette3"],
                         opening.resource_id("palette:bg:powered_window"))
        self.assertEqual(window["children"]["false"][0]["args"]["palette3"], opening.resource_id("palette:bg:window"))

    def test_b_script_dispatches_local_zones_and_priya(self):
        for folder in FOLDERS:
            chain = scene.SCENES[folder].chain
            [attach] = [e for e in BUILT[folder]["scene"]["script"] if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
            values = {e["args"]["condition"]["valueB"]["value"] for e in walk([attach])
                      if e["command"] == "EVENT_IF" and e["args"]["condition"]["valueA"]["value"] == climb.VAR_NEAR}
            expected = {l["number"] for l in chain.pole_lines()} | {grid_chain.BOX_ZONE + l["number"]
                                                                    for l in chain.box_lines()}
            with self.subTest(folder=folder):
                self.assertEqual(values - {grid_chain.NPC_ZONE}, expected)
                npc = [e for e in walk([attach]) if e["command"] == "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR"]
                self.assertEqual(bool(npc), folder == PORCH)

    def test_variables_register_without_changing_existing(self):
        data = json.loads(scene.VARIABLES_PATH.read_text(encoding="utf-8"))
        merged = scene.merged_variables(data)
        by_id = {v["id"]: v for v in merged["variables"]}
        for key, name, symbol in rosa.VARIABLES:
            self.assertEqual(by_id[key], {"id": key, "name": name, "symbol": symbol})
        self.assertEqual(scene.merged_variables(merged), merged)

    def test_every_view_stays_within_ten_sprites_per_scanline(self):
        profiles = sprite_profiles(PROJECT_DIR)
        for folder in FOLDERS:
            grid = rosa.collision_grid(folder)
            width, height = rosa.size(folder)
            spots = {(x, y) for y in range(2, height - 1) for x in range(1, width - 1) if grid_chain.stands(grid, x, y)}
            spots |= {(x0, row + 1) for row, x0, _ in rosa._all_hazard_lanes(folder)}
            for spot in sorted(spots):
                load, _ = sprite_budget(PROJECT_DIR, BUILT[folder]["actors"], spot, width, height, profiles=profiles)
                self.assertLessEqual(max(load.values()), grid_chain.SCANLINE_OBJ_LIMIT, (folder, spot, load))


class GeneratedFilesTests(unittest.TestCase):
    """The written scene folders equal what the builders make (run after regeneration)."""

    def test_generated_folders_match_the_builders(self):
        for folder in FOLDERS:
            directory = scene.SCENES_DIR / folder
            with self.subTest(folder=folder):
                self.assertTrue(scenes.present(folder))
                written = json.loads((directory / "scene.gbsres").read_text(encoding="utf-8"))
                self.assertEqual(written["collisions"], BUILT[folder]["scene"]["collisions"])
                self.assertEqual(written["id"], BUILT[folder]["scene"]["id"])
                for kind in ("actors", "triggers"):
                    files = sorted(p.name for p in (directory / kind).glob("*.gbsres"))
                    self.assertEqual(files, sorted(f"{item['symbol']}.gbsres" for item in BUILT[folder][kind]))
        self.assertTrue(scene_links.migrated(3))


if __name__ == "__main__":
    unittest.main()
