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
    """The true branch of the work_order `variable 16 == number` EVENT_IF."""
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

    def test_tickets_cover_one_to_four(self):
        self.assertEqual(sorted(tickets.TICKETS), [1, 2, 3, 4])
        self.assertEqual(tickets.VAR_TICKET, "16")
        self.assertEqual(tickets.VARIABLES, [("16", "Work Order", "var_work_order")])

    def test_generator_text_check_passes(self):
        scene.check_text()


class SceneBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = scene.build_scenes()

    def test_scenes_are_topdown_20_by_18_with_contract_ids(self):
        self.assertEqual(set(self.built), {"work_order", "storm_report"})
        for folder, resource in self.built.items():
            self.assertEqual(resource["type"], "TOPDOWN", folder)
            self.assertEqual((resource["width"], resource["height"]), (20, 18), folder)
            self.assertEqual(resource["backgroundId"], tickets.BACKGROUND_ID, folder)
        self.assertEqual(self.built["work_order"]["id"], tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(self.built["storm_report"]["id"], tickets.REPORT_SCENE_ID)
        self.assertEqual(self.built["work_order"]["name"], "Work Order")
        self.assertEqual(self.built["storm_report"]["name"], "Storm Report")

    def test_scenes_hide_player_and_overlay_first(self):
        for folder, resource in self.built.items():
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
    @classmethod
    def setUpClass(cls):
        cls.script = scene.build_scenes()["work_order"]["script"]

    def test_each_ticket_shows_its_card_then_switches_to_its_job(self):
        for number, ticket in tickets.TICKETS.items():
            branch = branch_for(self.script, number)
            texts = commands(branch, "EVENT_TEXT")
            self.assertEqual(len(texts), 1, number)
            self.assertEqual(texts[0]["args"]["text"], ticket["pages"], number)
            self.assertEqual(texts[0]["args"]["closeWhen"], "key", number)
            self.assertEqual(texts[0]["args"]["closeButton"], "a", number)
            self.assertEqual(texts[0]["args"]["position"], "bottom", number)
            switches = commands(branch, "EVENT_SWITCH_SCENE")
            self.assertEqual(len(switches), 1, number)
            args = switches[0]["args"]
            self.assertEqual(args["sceneId"], ticket["scene_id"], number)
            self.assertEqual((args["x"]["value"], args["y"]["value"]), tuple(ticket["start"]), number)
            self.assertEqual(args["direction"], "right", number)
            self.assertEqual(args["fadeSpeed"], "2", number)

    def test_destinations_are_the_job_scenes(self):
        self.assertEqual(tickets.TICKETS[1]["scene_id"], tickets.CLIMB_SCENE_ID)
        destinations = {n: t["scene_id"] for n, t in tickets.TICKETS.items()}
        self.assertEqual(len(set(destinations.values())), 4)

    def test_fallback_goes_to_ticket_one_destination(self):
        top = [entry for entry in self.script if entry["command"] == "EVENT_IF"]
        self.assertEqual(len(top), 1)
        node = top[0]
        while True:
            false = node["children"]["false"]
            inner = [e for e in false if e["command"] == "EVENT_IF"]
            if not inner:
                break
            node = inner[0]
        switches = commands(false, "EVENT_SWITCH_SCENE")
        self.assertEqual(len(switches), 1)
        self.assertEqual(switches[0]["args"]["sceneId"], tickets.TICKETS[1]["scene_id"])
        self.assertEqual(commands(false, "EVENT_TEXT"), [])

    def test_variable_branches_only_test_ticket_variable(self):
        for entry in walk(self.script):
            if entry["command"] == "EVENT_IF":
                self.assertEqual(entry["args"]["condition"]["valueA"]["value"], tickets.VAR_TICKET)


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


class FileTests(unittest.TestCase):
    def test_scene_files_match_build(self):
        built = scene.build_scenes()
        for folder, resource in built.items():
            path = PROJECT / "scenes" / folder / "scene.gbsres"
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), resource, folder)

    def test_scene_files_do_not_change_when_rebuilt(self):
        first = {f: json.dumps(r, indent=2) for f, r in scene.build_scenes().items()}
        second = {f: json.dumps(r, indent=2) for f, r in scene.build_scenes().items()}
        self.assertEqual(first, second)

    def test_variable_sixteen_registered_and_others_untouched(self):
        data = json.loads((PROJECT / "variables.gbsres").read_text(encoding="utf-8"))
        entries = {v["id"]: v for v in data["variables"]}
        self.assertEqual(entries["16"], {"id": "16", "name": "Work Order", "symbol": "var_work_order"})
        before = json.loads(json.dumps(data))
        merged = scene.merged_variables(before)
        self.assertEqual(merged, before)  # idempotent once registered

    def test_profile_is_registered(self):
        import make_project
        self.assertEqual(make_project.PROFILES["tickets"],
                         ("make_ticket_art.py", "make_ticket_scene.py"))


if __name__ == "__main__":
    unittest.main()
