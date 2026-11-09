"""Climb Crest (job 1B, climb_crest) contract and scene checks (stdlib only).

Run: "$PY" -m unittest discover -s tools -p 'test_crest*.py' (the background test,
test_crest_background.py, needs the managed Python with Pillow).
"""
import json
import unittest

import climb
import grid_chain
import hazards
import make_climb_scene as shared
import make_crest_scene as crest
import opening
import redesign_maps
import rosa
import scene_links
import scenes
import test_routes
import tickets
from test_climb import CLIMB_AUDIO, SPRITES, flatten, overlaps, rect, simulate, texts


class Fixture:
    actors = crest.build_actors(SPRITES)
    triggers = crest.build_triggers(CLIMB_AUDIO)
    resource = crest.build_scene(CLIMB_AUDIO)
    script = resource["script"]
    boxes = dict(crest.box_script_resources(CLIMB_AUDIO))
    by_symbol = {a["symbol"]: a for a in actors}
    triggers_by_symbol = {t["symbol"]: t for t in triggers}
    route = next(s for s in climb.ROUTE_SCENES if s["folder"] == climb.CREST_SCENE)


def ids(node):
    """Every "id" in a resource tree."""
    if isinstance(node, dict):
        if isinstance(node.get("id"), str):
            yield node["id"]
        for value in node.values():
            yield from ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from ids(value)


class CrestContractTests(unittest.TestCase):
    def test_redesign_keeps_the_cable_destination_and_scene_boundaries(self):
        spec = redesign_maps.load()["climb_crest"]
        self.assertEqual((climb.CREST_W, climb.CREST_H), (spec.width, spec.height))
        self.assertEqual(climb.CREST_START, spec.start)
        self.assertEqual([climb.CREST_AMARA], spec.npcs)
        self.assertEqual(spec.rows[climb.CREST_DOOR[1]][climb.CREST_DOOR[0]], "d")
        self.assertEqual(Fixture.route["exits"], [r for _, r in spec.triggers])
        [line] = Fixture.route["lines"]
        self.assertEqual({k: v for k, v in line.items() if k in ("number", "box", "checkpoint")}, spec.lines[0])
        self.assertNotIn("pole", line, "pole 5 stays on the climb's L8 deck")

    def test_broken_walkway_has_a_local_recovery_and_reverse_route(self):
        grid = Fixture.route["grid"]
        routes = test_routes.Routes(Fixture.route)
        x0, x1 = climb.CREST_GAP
        catch_row = climb.CREST_CATCH_ROW - 1
        [line] = Fixture.route["lines"]
        recover_to_porch = routes.can_reach(routes.zone(line))
        recover_to_entry = routes.can_reach(routes.exit_tiles(climb.CREST_BACK_EXIT))
        for x in range(x0, x1 + 1):
            self.assertTrue(all(grid[y][x] == climb.COL_EMPTY for y in range(climb.CREST_CATWALK_ROW, catch_row + 1)))
            self.assertIn((x, catch_row), recover_to_porch)
            self.assertIn((x, catch_row), recover_to_entry)
        self.assertGreater(line["reach"][0], x1, "the repair belongs on the cabin side")

    def test_route_rules(self):
        for rule, found in test_routes.problems(Fixture.route).items():
            with self.subTest(rule=rule):
                self.assertEqual(found, [])

    def test_approach_is_a_single_wire_then_walkway_damage(self):
        """Rest pad precedes the timber hazards; the span is live during carry 5."""
        self.assertEqual([span["live_after"] for span in climb.CREST_FALLEN_SPANS], [4])
        [(row, arc0, arc1)] = climb.crest_span_arc_lanes()
        [(plank_row, _, board1)] = Fixture.route["boards"]
        [(whip_row, whip0, whip1)] = climb.CREST_WHIP_LANES
        self.assertEqual(climb.crest_play_lanes(), [(whip_row, whip0, whip1), (row, arc0, arc1)])
        self.assertGreaterEqual(whip0 - board1 - 1, 2, "waiting space between the plank and wire")
        self.assertGreaterEqual(climb.CREST_GAP[0] - whip1 - 1, 4, "launch space past the whip")
        self.assertEqual(plank_row, whip_row + 2, "both threats belong to the elevated walkway")


class CrestSceneTests(unittest.TestCase):
    def test_scene_identity_size_and_background(self):
        r = Fixture.resource
        self.assertEqual(r["id"], scenes.REGISTRY["climb_crest"]["id"])
        self.assertEqual(r["id"], shared.resource_id("scene:climb_crest"))
        self.assertEqual((r["width"], r["height"], r["type"]), (56, 18, "PLATFORM"))
        self.assertEqual(r["backgroundId"], shared.resource_id("background:climb-crest"))
        self.assertEqual((r["x"], r["y"]), scenes.editor_position("climb_crest"))
        self.assertEqual(r["symbol"], "scene_climb_crest")
        climb_scene = shared.build_scene("m", CLIMB_AUDIO, [])
        self.assertEqual(r["paletteIds"], climb_scene["paletteIds"], "one job, one set of chain palettes")
        self.assertEqual(r["spritePaletteIds"], climb_scene["spritePaletteIds"])
        self.assertEqual(r["spritePaletteIds"][1], opening.resource_id("palette:sprite:marta"))

    def test_ids_do_not_collide_with_the_climb(self):
        climb_ids = set(ids([shared.build_actors(SPRITES), shared.build_triggers(CLIMB_AUDIO),
                             shared.build_scene("m", CLIMB_AUDIO, [])]))
        crest_ids = list(ids([Fixture.actors, Fixture.triggers, Fixture.resource]))
        self.assertEqual(len(crest_ids), len(set(crest_ids)), "duplicate IDs inside the crest")
        self.assertFalse(climb_ids & set(crest_ids) - {Fixture.resource["backgroundId"]}
                         - set(Fixture.resource["paletteIds"]) - set(Fixture.resource["spritePaletteIds"])
                         - {a["spriteSheetId"] for a in Fixture.actors})

    def test_moved_resources_keep_their_stable_ids(self):
        a, t = Fixture.by_symbol, Fixture.triggers_by_symbol
        self.assertEqual(a["marta_checkpoint"]["id"], "0a208a0e-9313-59b7-be31-3be4c204ab2a")
        self.assertEqual(t["trigger_marta_arrival"]["id"], "b02fc406-5513-54f5-abd9-25c1adb2da51")
        self.assertEqual(t["trigger_grid_junction_zone"]["id"], shared.resource_id("trigger:reach:junction"))
        self.assertEqual(t["trigger_marta_zone"]["id"], shared.resource_id("trigger:npc-zone:marta"))
        self.assertEqual(list(Fixture.boxes), ["project/scripts/storm_climb_box_summit.gbsres"])
        self.assertEqual(Fixture.boxes["project/scripts/storm_climb_box_summit.gbsres"]["id"],
                         shared.CHAIN.box_script_id(shared.LINE_BY_KEY["summit"]))

    def test_roster_and_trigger_order(self):
        self.assertEqual([x["symbol"] for x in Fixture.actors], [
            "marta_checkpoint", "crest_span_arc_01", "crest_whip_01", "climb_crest_board_01"])
        self.assertEqual([x["symbol"] for x in Fixture.triggers], [
            "trigger_crest_back_exit", "trigger_crest_porch_exit", "trigger_marta_arrival",
            "climb_crest_trigger_cracked_board_01", "trigger_grid_junction_zone", "trigger_marta_zone"])
        self.assertEqual([x["_index"] for x in Fixture.actors], list(range(4)))
        self.assertEqual([x["_index"] for x in Fixture.triggers], list(range(6)))
        live = [tr for tr in Fixture.triggers if tr["script"] or tr["leaveScript"]]
        for i, first in enumerate(live):
            for second in live[i + 1:]:
                self.assertFalse(overlaps(rect(first), rect(second)), f"{first['symbol']} / {second['symbol']}")

    def test_files_on_disk_match_the_generator(self):
        if not scenes.present("climb_crest"):
            self.skipTest("climb_crest not generated yet")
        _, sprite_ids, audio_ids = shared.load_ids()
        built = (("actors", crest.build_actors(sprite_ids)), ("triggers", crest.build_triggers(audio_ids)))
        for folder, items in built:
            on_disk = sorted(p.stem for p in (crest.SCENE_DIR / folder).glob("*.gbsres"))
            self.assertEqual(on_disk, sorted(item["symbol"] for item in items))
            for item in items:
                path = crest.SCENE_DIR / folder / f"{item['symbol']}.gbsres"
                self.assertEqual(json.loads(path.read_text()), item)
        self.assertEqual(json.loads((crest.SCENE_DIR / "scene.gbsres").read_text()), crest.build_scene(audio_ids))

    def test_init_neither_resets_nor_plays_music(self):
        """Not the entry scene: no job reset, no EVENT_MUSIC_PLAY (spec §3 rules 1, 6)."""
        events = list(flatten(Fixture.script))
        self.assertFalse([e for e in events if e["command"] == "EVENT_MUSIC_PLAY"])
        self.assertFalse([e for e in events if e["command"] == "EVENT_IF"
                          and e["args"]["condition"]["valueA"]["value"] == grid_chain.VAR_TICKET])
        written = {e["args"]["variable"] for e in Fixture.script if e["command"] == "EVENT_SET_VALUE"}
        self.assertEqual(written, {climb.VAR_NEAR, hazards.VAR_ON_BOARD})
        self.assertEqual(Fixture.script[0]["command"], "EVENT_PLAYER_SET_SPRITE")

    def test_carried_cable_and_door_survive_the_edge(self):
        marta = crest.marta_actor_id()
        carrying = simulate(Fixture.script, {"6": 5, "40": 1, "41": 1, "42": 1, "43": 1})
        self.assertEqual(carrying[-1], ("player", "Carry"), "cross-scene carry: cable 5 still in hand")
        self.assertIn((marta, "Waiting"), carrying)
        done = simulate(Fixture.script, {"0": 1, "40": 1, "41": 1, "42": 1, "43": 1, "7": 1})
        self.assertIn((marta, "Powered"), done)
        self.assertNotIn(("player", "Carry"), done)
        [door] = [e for e in Fixture.script if e["command"] == "EVENT_IF"
                  and e["args"]["condition"]["valueA"]["value"] == crest.VAR_DOOR]
        warm = door["children"]["true"][0]["args"]["palette3"]
        self.assertEqual(warm, opening.resource_id("palette:bg:powered_window"))

    def test_b_press_plugs_transformer_five_and_keeps_amaras_talk(self):
        [b] = [e for e in Fixture.script if e["command"] == "EVENT_SET_INPUT_SCRIPT"]
        self.assertEqual(b["args"], {"input": ["b"], "override": False})
        first = b["children"]["true"][0]
        self.assertEqual(first["args"]["condition"]["valueB"]["value"], grid_chain.BOX_ZONE + 5)
        npc = first["children"]["false"][0]
        self.assertEqual(npc["args"]["condition"]["valueB"]["value"], grid_chain.NPC_ZONE)
        self.assertEqual(npc["children"]["true"], [], "Amara's zone leaves native talk")
        calls = [e for e in flatten([b]) if e["command"] == "EVENT_CALL_CUSTOM_EVENT"]
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["args"], {
            "customEventId": crest.CHAIN.box_script_id(shared.LINE_BY_KEY["summit"]),
            "$actor[0]$": crest.CHAIN.actor_id(f"span-arc:{crest.SPAN_ARC_FIRST_NUMBER}"),
        })

    def test_transformer_five_box_script_lights_the_whole_chain(self):
        box = Fixture.boxes["project/scripts/storm_climb_box_summit.gbsres"]
        self.assertEqual(box["actors"], {"0": {"id": "0", "name": "Downed Span Arc (crest) 1"}},
                         "the final repair refresh hides the crest span through its explicit actor binding")
        events = list(flatten(box["script"]))
        sets = {(e["args"]["variable"], e["args"]["value"]["value"]) for e in events
                if e["command"] == "EVENT_SET_VALUE"}
        self.assertIn((climb.VAR_LINE_LIVE, 1), sets)
        self.assertIn((climb.VAR_CHAIN_LIVE, 5), sets)
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_HIDE" for e in events))
        self.assertTrue(any(e["command"] == "EVENT_ACTOR_COLLISIONS_DISABLE" for e in events))
        self.assertIn(["All 5 lines live!\nGo see Amara."], texts(box["script"]))

    def test_crest_span_keeps_first_pass_cycle_but_final_repair_gates_every_phase(self):
        arc = Fixture.by_symbol["crest_span_arc_01"]
        outer = arc["updateScript"][0]
        self.assertEqual(outer["args"]["condition"]["valueB"]["value"], 4)
        waits = [e["args"]["frames"]["value"] for e in flatten(arc["updateScript"])
                 if e["command"] == "EVENT_WAIT"]
        self.assertEqual([n for n in waits if n in (rosa.ARC_WARNING_FRAMES,
                                                     rosa.ARC_ACTIVE_FRAMES,
                                                     rosa.ARC_REST_FRAMES)],
                         [rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES])
        gates = [e for e in flatten(arc["updateScript"])
                 if e["command"] == "EVENT_IF"
                 and e["args"]["condition"]["valueA"].get("value") == climb.LINES[-1]["live_var"]]
        self.assertEqual(len(gates), 4, "after delay, warning, active and rest: queued phases cannot revive the span")
        for gate in gates:
            safe_commands = [e["command"] for e in flatten(gate["children"]["true"])]
            self.assertIn("EVENT_ACTOR_COLLISIONS_DISABLE", safe_commands)
            self.assertIn("EVENT_ACTOR_HIDE", safe_commands)

    def test_chain_refresh_immediately_hides_span_after_line_five_and_on_reentry(self):
        refresh = crest.CHAIN.chain_refresh_events("reentry")
        [cleanup] = [e for e in refresh if e["id"] == shared.resource_id("event:reentry:crest-span-safe")]
        self.assertEqual(cleanup["args"]["condition"]["valueA"]["value"], climb.LINES[-1]["live_var"])
        self.assertEqual([e["command"] for e in cleanup["children"]["true"]], [
            "EVENT_ACTOR_COLLISIONS_DISABLE", "EVENT_ACTOR_HIDE",
        ])
        self.assertEqual(cleanup["children"]["true"][0]["args"]["actorId"],
                         crest.CHAIN.actor_id(f"span-arc:{crest.SPAN_ARC_FIRST_NUMBER}"))

    def test_amaras_door_needs_all_five_lines_and_is_once_only(self):
        door = Fixture.triggers_by_symbol["trigger_marta_arrival"]
        self.assertEqual(rect(door), climb.CREST_DOOR_RECT)
        [gate] = door["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"]["value"], climb.VAR_CHAIN_LIVE)
        self.assertEqual(gate["args"]["condition"]["valueB"]["value"], 5)
        [once] = gate["children"]["true"]
        self.assertEqual(once["args"]["condition"]["valueA"]["value"], crest.VAR_DOOR)
        self.assertEqual(once["children"]["false"], [])
        self.assertEqual(texts(once["children"]["true"]), [
            ["Amara:\nPower's back!\nMy fridge hums."], tickets.closed_lines(1),
        ])
        [hint] = gate["children"]["false"]
        self.assertEqual(hint["args"]["condition"]["valueA"]["value"], climb.VAR_CARRYING_CABLE)
        self.assertEqual(texts(hint["children"]["true"]), [["Still no power.\nFix all 5 lines!"]])

    def test_amara_talk_and_thanks_moved_up_with_her(self):
        amara = Fixture.by_symbol["marta_checkpoint"]
        self.assertEqual((amara["x"], amara["y"]), climb.CREST_AMARA)
        self.assertEqual(amara["spriteSheetId"], opening.resource_id("sprite:opening_marta"))
        talk = amara["script"][0]
        line = talk["children"]["true"][0]
        self.assertEqual(line["args"]["condition"]["valueA"]["value"], climb.VAR_CHAIN_LIVE)
        self.assertEqual(texts(line["children"]["true"]), [["Amara:\nPower's up here!\nTry my door."]])
        self.assertEqual(texts(line["children"]["false"]), [["Amara:\nStorm cut five\nlines below me!"]])
        self.assertEqual(texts(talk["children"]["false"]), [["Amara:\nFood is saved.\nThanks, lineman!"]])

    def test_porch_exit_opens_work_order_two_after_amaras_door(self):
        trigger = Fixture.triggers_by_symbol["trigger_crest_porch_exit"]
        self.assertEqual(rect(trigger), climb.CREST_PORCH_EXIT)
        [gate] = trigger["script"]
        self.assertEqual(gate["args"]["condition"]["valueA"]["value"], "0")
        go = gate["children"]["true"]
        self.assertEqual([e["command"] for e in go], ["EVENT_OVERLAY_SET_SCANLINE_CUTOFF", "EVENT_OVERLAY_HIDE",
                                                      "EVENT_SET_VALUE", "EVENT_SWITCH_SCENE"])
        self.assertEqual((go[2]["args"]["variable"], go[2]["args"]["value"]["value"]), (tickets.VAR_TICKET, 2))
        self.assertEqual(go[3]["args"]["sceneId"], tickets.WORK_ORDER_SCENE_ID)
        nudge = gate["children"]["false"][0]
        self.assertEqual(nudge["command"], "EVENT_ACTOR_SET_POSITION")
        self.assertLess(nudge["args"]["x"]["value"] * 8 + 16, climb.CREST_PORCH_EXIT[0] * 8)
        self.assertEqual(texts(gate["children"]["false"]), [["Amara needs\npower first."]])

    def test_back_exit_returns_to_the_summit_ungated(self):
        trigger = Fixture.triggers_by_symbol["trigger_crest_back_exit"]
        self.assertEqual(rect(trigger), climb.CREST_BACK_EXIT)
        cutoff, hide, switch = trigger["script"]
        self.assertEqual(cutoff["args"]["y"]["value"], 150)
        self.assertEqual(hide["command"], "EVENT_OVERLAY_HIDE")
        self.assertEqual(switch["args"]["sceneId"], scene_links.scene_id(climb.CLIMB_SCENE))
        self.assertEqual((switch["args"]["x"]["value"], switch["args"]["y"]["value"]), climb.SUMMIT_ARRIVAL)
        self.assertEqual(switch["args"]["direction"], "left")

    def test_respawn_drops_any_cable_and_uses_the_crest_checkpoint(self):
        hit = Fixture.resource["playerHit1Script"]
        drops = [e for e in hit if e["command"] == "EVENT_IF"
                 and e["args"]["condition"]["valueA"]["value"] == climb.VAR_CARRYING_CABLE]
        self.assertEqual(len(drops), 5, "a cable from any line goes home (Abe)")
        self.assertFalse([e for e in flatten(drops) if e["command"] == "EVENT_ACTOR_SET_STATE"
                          and e["args"]["actorId"] != "player"], "no pole stands on the crest")
        check = next(e for e in hit if e["command"] == "EVENT_IF"
                     and e["args"]["condition"]["valueA"]["value"] == climb.VAR_LINE_LIVE)
        self.assertEqual(check["args"]["condition"]["valueA"]["value"], climb.VAR_LINE_LIVE)
        positions = [(e["args"]["x"]["value"], e["args"]["y"]["value"]) for e in flatten([check])
                     if e["command"] == "EVENT_ACTOR_SET_POSITION"]
        self.assertEqual(positions, [climb.LINES[-1]["checkpoint"], climb.CREST_START])

    def test_hazards(self):
        a = Fixture.by_symbol
        arc = a["crest_span_arc_01"]
        self.assertEqual(arc["spriteSheetId"], rosa.ARC_SPRITE_ID)
        upstream = arc["updateScript"][0]
        self.assertEqual(upstream["args"]["condition"]["type"], "gte")
        self.assertEqual(upstream["args"]["condition"]["valueB"]["value"], 4)
        self.assertEqual((arc["x"], arc["y"]), (11, 13))
        whip = a["crest_whip_01"]
        self.assertEqual((whip["x"], whip["y"], whip["collisionGroup"]), (29, 8, "1"))
        board = a["climb_crest_board_01"]
        self.assertEqual((board["x"], board["y"]), (24, 9))
        board_trigger = Fixture.triggers_by_symbol["climb_crest_trigger_cracked_board_01"]
        self.assertEqual(rect(board_trigger), hazards.board_trigger_rect((9, 24, 26)))

    def test_in_play_text_lifts_the_hud_cutoff_first(self):
        scripts = [Fixture.script, *[x["script"] for x in Fixture.actors], *[t["script"] for t in Fixture.triggers],
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
        self.assertGreaterEqual(checked, 8)
        lines = [part for s in scripts for t in texts(s) for page in t for part in page.split("\n")]
        self.assertTrue(all(len(part) <= shared.MAX_DIALOGUE_CHARS for part in lines), lines)


if __name__ == "__main__":
    unittest.main()
