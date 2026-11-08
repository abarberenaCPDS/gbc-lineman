"""Focused production checks for lakeside hub dispatch and physics preservation."""
import hashlib
from pathlib import Path
import unittest

import make_dispatch_hub as hub
import make_ticket_scene as ticket


COMPLETIONS = tuple(home[1] for home in hub.contract.HOMES)
PHYSICS_PINS = {
    "project/engine_field_values.gbsres": "fa83412757d818e45e05e3d27ded6740d3a02c3f6e64bff0af388a6e06138926",
    "assets/engine/src/states/platform.c": "26feb227f341e995d6be1a3a557e621007fb6d9431935bdb44f7504b949e593b",
}


def walk(events):
    for event in events:
        yield event
        for branch in event.get("children", {}).values():
            yield from walk(branch)


def execute(events, state):
    """Interpret the hub's equality branches and variable writes for one A press."""
    output = []
    for event in events:
        command, args = event["command"], event.get("args", {})
        if command == "EVENT_IF":
            condition = args["condition"]
            self_value = condition["valueA"]["value"]
            expected = condition["valueB"]["value"]
            branch = "true" if state.get(self_value, 0) == expected else "false"
            output.extend(execute(event.get("children", {}).get(branch, []), state))
        elif command == "EVENT_SET_VALUE":
            raw = args["value"]
            state[args["variable"]] = raw["value"]
            output.append(event)
        else:
            output.append(event)
    return output


class LakesideCampaignTests(unittest.TestCase):
    def setUp(self):
        self.scene = hub.build_scene()
        self.input_event = next(e for e in self.scene["script"]
                                if e["command"] == "EVENT_SET_INPUT_SCRIPT")
        self.interaction = self.input_event["children"]["true"]

    def simulate(self, signed_trail, next_job, completed=()):
        state = {hub.NEAR_VAR: signed_trail, "16": next_job}
        state.update({variable: int(variable in completed) for variable in COMPLETIONS})
        events = execute(self.interaction, state)
        return events, state

    def test_only_the_matching_unfinished_trail_dispatches_next_job(self):
        for next_job in range(1, 5):
            with self.subTest(next_job=next_job):
                for trail in range(1, 5):
                    events, state = self.simulate(trail, next_job)
                    switches = [e for e in events if e["command"] == "EVENT_SWITCH_SCENE"]
                    if trail == next_job:
                        self.assertEqual(len(switches), 1)
                        target = hub.contract.tickets.TICKETS[next_job]
                        self.assertEqual(switches[0]["args"]["sceneId"], target["scene_id"])
                        self.assertEqual(switches[0]["args"]["x"]["value"], target["start"][0])
                        self.assertEqual(switches[0]["args"]["y"]["value"], target["start"][1])
                    else:
                        self.assertEqual(switches, [])
                    self.assertEqual({v: state[v] for v in COMPLETIONS},
                                     {v: 0 for v in COMPLETIONS})
                    self.assertEqual(state["16"], next_job)

    def test_completed_and_later_or_away_interactions_do_not_dispatch(self):
        for n in range(1, 5):
            with self.subTest(completed=n):
                events, state = self.simulate(n, n, completed=(COMPLETIONS[n-1],))
                self.assertFalse(any(e["command"] == "EVENT_SWITCH_SCENE" for e in events))
                self.assertEqual(state[COMPLETIONS[n-1]], 1)
        for trail, next_job in ((1, 2), (2, 3), (3, 4), (4, 1)):
            with self.subTest(trail=trail, next_job=next_job):
                events, _ = self.simulate(trail, next_job)
                self.assertFalse(any(e["command"] == "EVENT_SWITCH_SCENE" for e in events))
        events, _ = self.simulate(0, 1)
        self.assertFalse(any(e["command"] == "EVENT_SWITCH_SCENE" for e in events))

    def test_dispatch_releases_a_override_before_leaving(self):
        self.assertEqual(self.input_event["args"], {"input": ["a"], "override": True})
        events, _ = self.simulate(1, 1)
        commands = [e for e in events if e["command"] in
                    ("EVENT_REMOVE_INPUT_SCRIPT", "EVENT_SWITCH_SCENE")]
        switch_index = next(i for i, e in enumerate(commands)
                            if e["command"] == "EVENT_SWITCH_SCENE")
        releases = [i for i, e in enumerate(commands[:switch_index])
                    if e["command"] == "EVENT_REMOVE_INPUT_SCRIPT"
                    and e.get("args") == {"input": ["a"]}]
        self.assertTrue(releases, "A override must be released before changing scenes")

    def test_arrival_is_walkable_and_production_has_no_diagnostic_seeds(self):
        grid = hub.collision_grid()
        x, y = hub.START
        self.assertTrue(all(grid[y][x + dx] == 0 for dx in (0, 1)))
        self.assertNotIn(hub.FIXTURE_INIT_VAR, {e.get("args", {}).get("variable")
                      for e in walk(self.scene["script"])})
        self.assertFalse(any(e.get("command") == "EVENT_SET_VALUE"
                             and e.get("args", {}).get("variable") in (*COMPLETIONS, "16")
                             for e in walk(self.scene["script"])))

    def test_accepted_platform_physics_files_are_unchanged(self):
        for path, expected in PHYSICS_PINS.items():
            with self.subTest(path=path):
                with (Path(__file__).resolve().parent.parent / path).open("rb") as stream:
                    self.assertEqual(hashlib.sha256(stream.read()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
