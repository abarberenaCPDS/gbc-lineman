"""Feedback control-flow regressions: teaching, recovery, and persistent repairs.

These execute native event branches, not the engine; native verification remains
necessary for input release, respawn timing and audio-channel recovery.
"""
import json
from pathlib import Path
import unittest
import completion
import grid_chain as gc
from test_grid_chain import chain, line


def run(events, variables):
    """Execute the subset used here and retain all reached non-control events."""
    reached = []
    for e in events:
        command, args = e["command"], e["args"]
        if command == "EVENT_IF":
            cond = args["condition"]
            a = variables.get(cond["valueA"]["value"], 0)
            b = cond["valueB"]["value"]
            hit = {"eq": a == b, "ne": a != b, "gte": a >= b}[cond["type"]]
            reached.extend(run(e["children"]["true" if hit else "false"], variables))
        elif command == "EVENT_SET_VALUE":
            variables[args["variable"]] = args["value"]["value"]
        elif command == "EVENT_INC_VALUE":
            variables[args["variable"]] = variables.get(args["variable"], 0) + 1
        else:
            reached.append(e)
    return reached


def dialogue(events):
    return [e["args"]["text"] for e in events if e["command"] == "EVENT_TEXT"]


def fixture(scene="climb_crest", pole="storm_climb"):
    lines = [dict(line(i), pole_scene=pole, box_scene=scene) for i in (1, 2, 3)]
    c = chain(lines, scene=scene, background_boxes=True)
    c.say = lambda pages, key: [c.event("EVENT_TEXT", {"text": pages}, key)]
    c.hud = lambda key: [c.event("HUD_TEST", {}, key)]
    return c


class FeedbackTests(unittest.TestCase):
    def test_remote_loss_queues_hint_and_preserves_repaired_lines(self):
        for pole in gc.RETURN_DESTINATIONS:
            c = fixture(pole=pole)
            state = {"carrying": 3, "live-1": 1, "lines-live": 1}
            lost = run(c.cable_drop_events("hit"), state)
            self.assertEqual(dialogue(lost), [])  # show after caller repositions
            self.assertEqual(state["carrying"], 0)
            self.assertEqual(state["live-1"], 1)
            self.assertEqual(state["lines-live"], 1)
            shown = dialogue(run(c.recovery_hint_events("hit"), state))
            self.assertIn(gc.RETURN_DESTINATIONS[pole], str(shown))
            self.assertTrue(all(len(row) <= 17 for page in shown for text in page for row in text.splitlines()))
            self.assertEqual(state[gc.VAR_RETURN_HINT_PENDING], 0)
            self.assertEqual(state[gc.VAR_RETURN_HINT_SHOWN], 1)

    def test_local_or_empty_loss_never_points_to_another_scene(self):
        for carrying in (0, 3):
            c = fixture(scene="storm_climb")
            state = {"carrying": carrying}
            reached = run(c.cable_drop_events("hit") + c.recovery_hint_events("hit"), state)
            self.assertEqual(dialogue(reached), [])
            self.assertEqual(state.get(gc.VAR_RETURN_HINT_SHOWN, 0), 0)

    def test_remote_hint_once_across_reentry_but_reset_for_new_job(self):
        state = {"carrying": 3}
        c = fixture()
        events = c.cable_drop_events("hit") + c.recovery_hint_events("hit")
        self.assertEqual(len(dialogue(run(events, state))), 1)
        state["carrying"] = 3
        self.assertEqual(dialogue(run(fixture().cable_drop_events("again") + fixture().recovery_hint_events("again"), state)), [])
        run(c.line_reset_events(), state)
        state["carrying"] = 3
        self.assertEqual(len(dialogue(run(events, state))), 1)

    def test_pickup_teaches_once_and_keeps_carry_and_sound_on_later_pickups(self):
        c = fixture(scene="storm_climb")
        state = {}
        first = run(c.pickup_press_events(c.lines[0], "first", "pickup"), state)
        self.assertEqual(len(dialogue(first)), 1)
        state["carrying"] = 0
        second = run(c.pickup_press_events(c.lines[1], "second", "pickup"), state)
        self.assertEqual(dialogue(second), [])
        self.assertEqual(state["carrying"], 2)
        self.assertTrue(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" for e in second))
        self.assertTrue(any(e["command"] == "HUD_TEST" for e in second))
        self.assertIn("Carry", str(second))

    def test_connections_keep_first_teaching_dark_exception_and_final_direction(self):
        c = fixture()
        state = {"carrying": 1}
        first = run(c.box_press_events(c.lines[0], "one", "connect"), state)
        self.assertEqual(dialogue(first), [["Lit."]])
        state["carrying"] = 2
        second = run(c.box_press_events(c.lines[1], "two", "connect"), state)
        self.assertEqual(dialogue(second), [])
        self.assertEqual(state["lines-live"], 2)
        self.assertTrue(any(e["command"] == "HUD_TEST" for e in second))
        state["carrying"] = 3
        last = run(c.box_press_events(c.lines[2], "three", "connect"), state)
        self.assertEqual(dialogue(last), [["All live."]])
        # Repairing downstream first must still explain why it stays dark.
        self.assertEqual(dialogue(run(c.box_press_events(c.lines[1], "dark", "connect"), {"carrying": 2})), [["Dark."]])

    def test_errors_and_already_live_are_still_modal(self):
        c = fixture()
        for state, expected in (({}, "No cable."), ({"carrying": 2}, "Wrong cable."), ({"live-1": 1}, "Already live.")):
            self.assertEqual(dialogue(run(c.box_press_events(c.lines[0], "error", "connect"), state)), [[expected]])

    def test_fresh_job_resets_feedback_but_internal_entry_does_not(self):
        c = fixture()
        state = {v: 1 for v, _, _ in gc.VARIABLES}
        state[gc.VAR_TICKET] = 0
        run(c.job_reset_events(1), state)
        self.assertTrue(all(state[v] == 1 for v, _, _ in gc.VARIABLES))
        state[gc.VAR_TICKET] = 1
        run(c.job_reset_events(1), state)
        self.assertTrue(all(state[v] == 0 for v, _, _ in gc.VARIABLES))


class HouseholdRewardTests(unittest.TestCase):
    def test_each_home_reveals_device_plays_one_distinct_cue_and_closes_once(self):
        root = Path(__file__).resolve().parent.parent
        cases = [
            ("climb_crest", "trigger_marta_arrival", {"44": 5}, "0", "Amara:", "Powered"),
            ("ridge_saddle", "trigger_ridge_tomas_door", {"18": 5}, "9", "Hiroshi:", "On"),
            ("signal_porch", "trigger_signal_rosa_door", {"22": 5}, "11", "Priya:", "On"),
            ("pine_rim", "trigger_pine_home_door", {"25": 5}, "13", "Emil:", "On"),
        ]
        for folder, symbol, state, home, speaker, device in cases:
            with self.subTest(home=speaker):
                path = root / "project/scenes" / folder / "triggers" / (symbol + ".gbsres")
                script = json.loads(path.read_text())["script"]
                first = run(script, state)
                effects = [e["args"]["type"] for e in first if e["command"] == "EVENT_SOUND_PLAY_EFFECT"]
                self.assertEqual(effects, [completion.sound_id()])
                self.assertEqual(state[home], 1)
                self.assertIn(speaker, str(dialogue(first)))
                self.assertIn("CLOSED.", str(dialogue(first)))
                self.assertIn(device, [e["args"]["spriteStateId"] for e in first if e["command"] == "EVENT_ACTOR_SET_STATE"])
                # Reentry must preserve device progress without another reward.
                second = run(script, state)
                self.assertEqual(dialogue(second), [])
                self.assertFalse(any(e["command"] == "EVENT_SOUND_PLAY_EFFECT" for e in second))
                # Each named speech restores the narrator before CLOSED.
                sounds = [e for e in first if e["command"] == "EVENT_TEXT_SET_SOUND_EFFECT"]
                self.assertTrue(sounds)
                import voices
                self.assertEqual(sounds[-1]["args"], voices.sound_args(None))


if __name__ == "__main__":
    unittest.main()
