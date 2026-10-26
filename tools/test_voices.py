#!/usr/bin/env python3
"""Speaker names and voices (Abe on the cart: "who is speaking?")."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import intro
import voices

ROOT = Path(__file__).resolve().parent.parent
# Every in-play character: the actor and door resources whose boxes they speak.
SPOKEN = {
    "marta": ["service_opening/actors/marta", "storm_climb/actors/marta_checkpoint"],
    "tomas": ["wind_ridge/actors/ridge_tomas", "wind_ridge/triggers/trigger_ridge_tomas_door"],
    "rosa": ["signal_hill/actors/signal_rosa", "signal_hill/triggers/trigger_signal_rosa_door"],
    "kiko": ["pine_hollow/actors/pine_kiko", "pine_hollow/triggers/trigger_pine_home_door"],
}


def sequences(events):
    yield events
    for event in events:
        for branch in event.get("children", {}).values():
            if branch:
                yield from sequences(branch)


class VoiceTests(unittest.TestCase):
    def test_labeled_puts_the_name_on_its_own_line(self):
        self.assertEqual(voices.labeled("rosa", ["No internet...\nI can't work."]),
                         ["Rosa:\nNo internet...\nI can't work."])
        with self.assertRaises(ValueError):
            voices.labeled("kiko", ["one\ntwo\nthree"])

    def test_narrator_keeps_the_intro_blip(self):
        self.assertEqual(voices.sound_args(None), intro.TEXT_SOUND)

    def test_every_character_box_is_named_voiced_and_restored(self):
        for speaker, resources in SPOKEN.items():
            label = f"{voices.name(speaker)}:\n"
            boxes = 0
            for resource in resources:
                data = json.loads((ROOT / f"project/scenes/{resource}.gbsres").read_text())
                for events in sequences(data["script"]):
                    sounds = [i for i, e in enumerate(events)
                              if e["command"] == "EVENT_TEXT_SET_SOUND_EFFECT"]
                    for i, entry in enumerate(events):
                        if entry["command"] != "EVENT_TEXT" or not entry["args"]["text"][0].startswith(label):
                            continue
                        boxes += 1
                        before = [j for j in sounds if j < i][-1]
                        after = [j for j in sounds if j > i][0]
                        self.assertEqual(events[before]["args"], voices.sound_args(speaker), resource)
                        self.assertEqual(events[after]["args"], intro.TEXT_SOUND, resource)
            self.assertGreaterEqual(boxes, 3, speaker)


if __name__ == "__main__":
    unittest.main()
