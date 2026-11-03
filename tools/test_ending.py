"""Deterministic ending-reprise composition and transition checks."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import compose_ending
import ending
import intro
import make_ticket_scene
import make_intro_scene
import make_opening_scene
import uge_report
from compose_intro import variant_b


def walk(events):
    for event in events:
        yield event
        for branch in event.get("children", {}).values():
            yield from walk(branch)


class EndingMusicTests(unittest.TestCase):
    def test_rendered_score_matches_source_notes_effects_and_orders(self):
        name, score = compose_ending.candidate()
        path = Path(__file__).resolve().parent.parent / "assets/music" / (name + ".uge")
        self.assertTrue(path.is_file(), "run make_project.py tickets --render-music")
        decoded = uge_report.parse(str(path))
        self.assertEqual(decoded["trailing_bytes"], 0)
        self.assertEqual(decoded["ticks_per_row"], score["ticks_per_row"])
        for channel, order in enumerate(score["orders"]):
            self.assertEqual(decoded["orders"][channel][:-1], order)
        for key, events in score["patterns"].items():
            actual = {event["row"]: event for event in decoded["patterns"][int(key)]}
            for event in events:
                pitch = event["note"]
                code = uge_report.NO_NOTE
                if pitch is not None:
                    normalized = pitch[0] + (pitch[1:] if "#" in pitch else "-" + pitch[1:])
                    code = uge_report.NOTE_NAMES.index(normalized)
                with self.subTest(pattern=key, row=event["row"]):
                    cell = actual[event["row"]]
                    self.assertEqual((cell["note"], cell["inst"], cell["fx"], cell["fxp"]),
                                     (code, event["inst"], event["fx"], event["fxp"]))

    def test_two_sections_eight_seconds_and_four_channel_orders(self):
        name, song = compose_ending.candidate()
        self.assertEqual(name, ending.NAME)
        self.assertEqual(song["ticks_per_row"], 4)
        self.assertEqual(len(song["orders"]), 4)
        self.assertEqual([len(order) for order in song["orders"]], [2] * 4)
        self.assertEqual(ending.DURATION_SECONDS, 8)

    def test_final_bar_and_loop_start_resolve_to_d_tonic(self):
        _, score = compose_ending.candidate()
        final_bar = 3 * 16
        lead = score["patterns"]["1"]
        bass = score["patterns"]["201"]
        harmony = score["patterns"]["101"]
        self.assertIn({"row": final_bar + 12, "note": "D5", "inst": 2,
                       "fx": 0xC, "fxp": 11}, lead)
        self.assertIn("D3", [e["note"] for e in bass if e["row"] == final_bar])
        self.assertEqual(score["patterns"]["0"][0]["note"], "D5")
        self.assertTrue(any(e["note"] in {"D4", "F#4", "A4"}
                            for e in harmony if e["row"] >= final_bar))

    def test_intro_b_source_is_not_mutated(self):
        original = variant_b()
        expected = copy.deepcopy(original)
        compose_ending.candidate()
        self.assertEqual(original, expected)

    def test_music_sidecar_identity_is_stable_and_separate(self):
        self.assertEqual(ending.MUSIC_ID,
                         "0c1ebc02-30c2-5324-be3e-c3b6d97cff2a")
        self.assertNotIn(ending.MUSIC_ID, intro.THEME_IDS.values())

    def test_report_requests_reprise_after_cue_and_title_inherits_it(self):
        script = make_ticket_scene.storm_report_script()
        commands = [event["command"] for event in script]
        cue = commands.index("EVENT_SOUND_PLAY_EFFECT")
        reprise = commands.index("EVENT_MUSIC_PLAY")
        title = commands.index("EVENT_SWITCH_SCENE")
        self.assertLess(commands.index("EVENT_TEXT"), cue)
        self.assertLess(cue, reprise)
        self.assertLess(reprise, title)
        self.assertEqual(script[reprise]["args"]["musicId"], ending.MUSIC_ID)
        # The title scene is intentionally silent; replay enters story, which
        # starts the default Intro B explicitly, and the opening starts gameplay music.
        self.assertEqual(script[title]["args"]["sceneId"], ending.TITLE_SCENE_ID)
        self.assertEqual(intro.DEFAULT_THEME, "b")
        self.assertEqual(intro.THEME_IDS[intro.DEFAULT_THEME], intro.THEME_IDS["b"])

    def test_story_replay_and_fresh_opening_keep_their_own_tracks(self):
        story = make_intro_scene.story_script()
        story_music = [event for event in walk(story)
                       if event["command"] == "EVENT_MUSIC_PLAY"]
        self.assertEqual(story_music[0]["args"]["musicId"], intro.THEME_IDS["b"])

        opening = make_opening_scene.build_scene([], [])
        opening_music = [event for event in walk(opening["script"])
                         if event["command"] == "EVENT_MUSIC_PLAY"]
        climb_sidecar = json.loads(
            (make_opening_scene.ROOT / "assets/music/cfe_storm_climb.uge.gbsres")
            .read_text(encoding="utf-8"))
        self.assertEqual([event["args"]["musicId"] for event in opening_music],
                         [climb_sidecar["id"]])


if __name__ == "__main__":
    unittest.main()
