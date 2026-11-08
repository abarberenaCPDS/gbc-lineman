"""Work-order and storm-report checks: python3 -m unittest discover -s tools -p test_tickets.py

Checks the contract in tickets.py and the scenes and variable that
make_ticket_scene.py writes. Run the generator first; the file-level tests read
project/ as it is on disk.
"""
import json
import unittest
from pathlib import Path

import make_climb_scene
import make_ticket_scene as scene
import tickets

PROJECT = Path(__file__).resolve().parent.parent / "project"
SCENE_PATHS = {
    tickets.WORK_ORDER_SCENE_ID: PROJECT / "scenes" / "work_order" / "scene.gbsres",
    tickets.REPORT_SCENE_ID: PROJECT / "scenes" / "storm_report" / "scene.gbsres",
}


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def commands(events, name):
    return [entry for entry in walk(events) if entry["command"] == name]


def text_pages(events):
    return [page for entry in commands(events, "EVENT_TEXT") for page in entry["args"]["text"]]


def branch_for(script, number):
    """The true branch of the work_order `variable 16 == number` EVENT_IF.

    Ticket 1 has no IF of its own: it is the innermost else (the fallback).
    """
    if number == 1:
        node = next(e for e in script if e["command"] == "EVENT_IF")
        while True:
            inner = [e for e in node["children"]["false"] if e["command"] == "EVENT_IF"]
            if not inner:
                return node["children"]["false"]
            node = inner[0]
    for entry in walk(script):
        if entry["command"] != "EVENT_IF":
            continue
        condition = entry["args"]["condition"]
        if (condition["valueA"] == {"type": "variable", "value": tickets.VAR_TICKET}
                and condition["valueB"] == {"type": "number", "value": number}):
            return entry["children"]["true"]
    raise AssertionError(f"no branch for ticket {number}")


class ContractTests(unittest.TestCase):
    def test_climb_scene_id_matches_generator(self):
        self.assertEqual(tickets.CLIMB_SCENE_ID, make_climb_scene.resource_id("scene:storm-climb"))

    def test_text_fits_the_box(self):
        pages = list(tickets.REPORT_PAGES)
        for ticket in tickets.TICKETS.values():
            pages.extend(ticket["pages"])
        for number in tickets.TICKETS:
            pages.extend(tickets.closed_lines(number))
        for page in pages:
            lines = page.split("\n")
            self.assertLessEqual(len(lines), 3, page)
            for line in lines:
                self.assertLessEqual(len(line), tickets.MAX_CHARS, line)

    def test_job_destinations_and_the_report_exit_on_pine_rim(self):
        import kiko
        import rosa
        import scene_links
        self.assertEqual(tickets.TICKETS[3]["start"], rosa.START)
        self.assertEqual(tickets.TICKETS[4]["start"], kiko.START)
        # The report exit is 4C's porch-end exit (scene_links), gated on Emil's house.
        link = scene_links.link(kiko.RIM, scene_links.REPORT, scene_links.table("redesign"))
        self.assertEqual(tickets.REPORT_EXIT, link.rect)
        self.assertEqual(tickets.REPORT_EXIT, (kiko.RIM_W - 2, 9, 1, 3))
        self.assertEqual(tickets.REPORT_EXIT_GATE_VAR, link.gate)
        self.assertEqual(tickets.REPORT_EXIT_GATE_VAR, kiko.VAR_HOME_POWERED)

    def test_generator_text_check_passes(self):
        scene.check_text()


class SceneBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = scene.build_scenes()

    def test_town_and_report_have_their_native_dimensions(self):
        self.assertEqual(set(self.built), {"work_order", "storm_report"})
        for folder, resource in self.built.items():
            self.assertEqual(resource["type"], "TOPDOWN", folder)
            expected = (32, 32) if folder == "work_order" else (20, 18)
            self.assertEqual((resource["width"], resource["height"]), expected, folder)
        self.assertEqual(self.built["work_order"]["id"], tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(self.built["storm_report"]["id"], tickets.REPORT_SCENE_ID)
        self.assertEqual(self.built["work_order"]["name"], "Lakeside Town")
        self.assertEqual(self.built["storm_report"]["name"], "Storm Report")

    def test_report_hides_player_and_overlay_first(self):
        for folder, resource in [("storm_report", self.built["storm_report"])]:
            first = [entry["command"] for entry in resource["script"][:3]]
            self.assertEqual(first[:2], ["EVENT_ACTOR_HIDE", "EVENT_OVERLAY_HIDE"], folder)
            self.assertEqual(resource["script"][0]["args"], {"actorId": "player"}, folder)
            narrator = resource["script"][2]
            self.assertEqual(narrator["command"], "EVENT_TEXT_SET_SOUND_EFFECT", folder)
            self.assertEqual(narrator["args"], scene.voices.sound_args(None), folder)

    def test_no_text_draw_anywhere(self):
        for folder, resource in self.built.items():
            self.assertEqual(commands(resource["script"], "EVENT_TEXT_DRAW"), [], folder)

    def test_palette_ids_have_eight_slots(self):
        for folder, resource in self.built.items():
            self.assertEqual(len(resource["paletteIds"]), 8, folder)
            self.assertEqual(len(resource["spritePaletteIds"]), 8, folder)

    def test_event_ids_unique_within_scenes(self):
        ids = []
        for resource in self.built.values():
            ids.extend(entry["id"] for entry in walk(resource["script"]))
        self.assertEqual(len(ids), len(set(ids)))


class WorkOrderTests(unittest.TestCase):
    def test_town_has_no_automatic_dispatch_or_progress_reset(self):
        import make_dispatch_hub as hub
        script = scene.build_scenes()["work_order"]["script"]
        self.assertFalse(any(e["command"] in {"EVENT_SWITCH_SCENE", "EVENT_TEXT"}
                             for e in script))
        writes = commands(script, "EVENT_SET_VALUE")
        self.assertEqual({e["args"]["variable"] for e in writes}, {"27"})
        self.assertEqual(tickets.HERO_POSITION, hub.START)
        x, y = tickets.HERO_POSITION
        self.assertEqual(hub.collision_grid()[y][x:x+2], [0, 0])

    def test_each_available_trail_reaches_its_original_job(self):
        script = scene.build_scenes()["work_order"]["script"]
        switches = commands(script, "EVENT_SWITCH_SCENE")
        self.assertEqual(len(switches), 4)
        for target in tickets.TICKETS.values():
            switch = next(e["args"] for e in switches if e["args"]["sceneId"] == target["scene_id"])
            self.assertEqual((switch["x"]["value"], switch["y"]["value"]), tuple(target["start"]))
        # The modal work-order context is still available at the selected trail.
        pages = text_pages(script)
        for target in tickets.TICKETS.values():
            for page in target["pages"]:
                self.assertIn(page, pages)


class StormReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = scene.build_scenes()["storm_report"]["script"]

    def test_report_text_is_all_pages_in_one_box(self):
        texts = commands(self.script, "EVENT_TEXT")
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0]["args"]["text"], tickets.REPORT_PAGES)

    def test_victory_sound_plays_after_the_report(self):
        sounds = commands(self.script, "EVENT_SOUND_PLAY_EFFECT")
        victory_id = make_climb_scene.sidecar_id("assets/sounds/victory.wav.gbsres", "sound")
        self.assertEqual([s["args"]["type"] for s in sounds], [victory_id])
        order = [entry["command"] for entry in self.script]
        self.assertLess(order.index("EVENT_TEXT"), order.index("EVENT_SOUND_PLAY_EFFECT"))

    def test_report_ends_by_switching_to_title(self):
        last = self.script[-1]
        self.assertEqual(last["command"], "EVENT_SWITCH_SCENE")
        self.assertEqual(last["args"]["sceneId"], tickets.TITLE_SCENE_ID)
        self.assertEqual(last["args"]["fadeSpeed"], "2")

    def test_title_inherits_the_resolved_ending_reprise(self):
        # The report cue is followed by the resolved reprise; title inherits it.
        import intro
        import ending
        music = commands(self.script, "EVENT_MUSIC_PLAY")
        self.assertEqual([m["args"]["musicId"] for m in music], [ending.MUSIC_ID])
        self.assertEqual(self.script[-2]["command"], "EVENT_MUSIC_PLAY")
        self.assertNotEqual(ending.MUSIC_ID, intro.THEME_IDS[intro.DEFAULT_THEME])

    def test_report_narration_and_victory_cue_still_precede_reprise(self):
        import ending
        report = next(i for i, entry in enumerate(self.script)
                      if entry["command"] == "EVENT_TEXT")
        cue = next(i for i, entry in enumerate(self.script)
                   if entry["command"] == "EVENT_SOUND_PLAY_EFFECT")
        reprise = next(i for i, entry in enumerate(self.script)
                       if entry["command"] == "EVENT_MUSIC_PLAY")
        switch = next(i for i, entry in enumerate(self.script)
                      if entry["command"] == "EVENT_SWITCH_SCENE")
        self.assertLess(report, cue)
        self.assertLess(cue, reprise)
        self.assertLess(reprise, switch)
        self.assertEqual(self.script[reprise]["args"]["musicId"], ending.MUSIC_ID)


class FileTests(unittest.TestCase):
    def test_scene_files_match_build(self):
        built = scene.build_scenes()
        for folder, resource in built.items():
            path = PROJECT / "scenes" / folder / "scene.gbsres"
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), resource, folder)

    def test_variable_sixteen_registered_and_others_untouched(self):
        data = json.loads((PROJECT / "variables.gbsres").read_text(encoding="utf-8"))
        entries = {v["id"]: v for v in data["variables"]}
        self.assertEqual(entries["16"], {"id": "16", "name": "Work Order", "symbol": "var_work_order"})
        before = json.loads(json.dumps(data))
        merged = scene.merged_variables(before)
        self.assertEqual(merged, before)  # idempotent once registered


if __name__ == "__main__":
    unittest.main()
