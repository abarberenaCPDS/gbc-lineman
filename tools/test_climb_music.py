"""Storm Climb music checks (split from test_climb.py): canonical JSON and the rendered UGE."""
import json
from pathlib import Path
import unittest

import compose_climb
import uge_report


class ClimbMusicTests(unittest.TestCase):
    def test_climb_theme_structure_is_deterministic(self):
        music = compose_climb.song()
        compose_climb.validate(music)
        self.assertEqual(music, compose_climb.song())
        self.assertEqual(len(music["patterns"]), 32)
        self.assertEqual(music["ticks_per_row"], 6)
        self.assertTrue(all(len(sequence) == 8 for sequence in music["orders"]))

    def test_music_bridge_is_less_dense_than_opening(self):
        patterns = compose_climb.song()["patterns"]
        count = lambda key: sum(e["note"] is not None for e in patterns[str(key)])
        self.assertLess(count(4), count(0))

    def test_climb_music_json_is_regenerated_from_canonical_source(self):
        path = Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.json"
        self.assertEqual(json.loads(path.read_text()), compose_climb.song())

    def test_climb_uge_patterns_and_orders_match_canonical_json(self):
        source = compose_climb.song()
        binary = uge_report.parse(str(Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.uge"))

        self.assertEqual(binary["version"], 6)
        self.assertEqual(binary["ticks_per_row"], source["ticks_per_row"])
        self.assertEqual(binary["trailing_bytes"], 0)
        self.assertEqual(len(binary["patterns"]), 32)
        self.assertEqual(
            binary["orders"], [sequence + [0] for sequence in source["orders"]]
        )

        total_events = 0
        for key, events in source["patterns"].items():
            expected = {}
            for event in events:
                pitch = event["note"]
                note_code = (
                    uge_report.NO_NOTE
                    if pitch is None
                    else uge_report.NOTE_NAMES.index(
                        pitch[0] + (pitch[1:] if "#" in pitch else "-" + pitch[1:])
                    )
                )
                expected[event["row"]] = {
                    "note": note_code,
                    "inst": event["inst"],
                    "vol": 0,
                    "fx": event["fx"],
                    "fxp": event["fxp"],
                }
            self.assertEqual(len(expected), len(events), f"duplicate source row in {key}")
            actual = {event["row"]: {k: v for k, v in event.items() if k != "row"}
                      for event in binary["patterns"][int(key)]}
            self.assertEqual(actual, expected, f"pattern {key} differs from JSON")
            total_events += len(actual)

        self.assertEqual(total_events, 840)

    def test_climb_uge_instrument_envelopes_and_volume_effects(self):
        binary = uge_report.parse(str(Path(compose_climb.MUSIC) / f"{compose_climb.NAME}.uge"))
        instruments = binary["instruments"]

        # Global IDs are one-based; slot 16 is the first wave instrument.
        self.assertEqual((instruments[0]["initial_volume"],
                          instruments[0]["vol_sweep_direction"],
                          instruments[0]["vol_sweep_amount"]), (6, "down", 2))
        self.assertEqual((instruments[1]["initial_volume"],
                          instruments[1]["vol_sweep_direction"],
                          instruments[1]["vol_sweep_amount"]), (10, "down", 2))
        self.assertEqual(instruments[15]["type_name"], "wave")
        self.assertEqual(instruments[15]["output_level"], 2)
        self.assertTrue(all(instruments[index]["type_name"] == "noise"
                            and instruments[index]["initial_volume"] == 7
                            and instruments[index]["vol_sweep_direction"] == "down"
                            and instruments[index]["vol_sweep_amount"] == 2
                            for index in (30, 31)))

        for cells in binary["patterns"].values():
            for cell in cells:
                if cell["fx"] == 0xC:
                    self.assertLessEqual(cell["fxp"], 15)

    def test_b_major_turnaround_phrase_has_matching_backing(self):
        source = compose_climb.song()

        def pitch_class(pitch):
            return pitch[:-1]

        for section, phrase_ids in enumerate(compose_climb.SECTIONS):
            for bar, phrase_id in enumerate(phrase_ids):
                if phrase_id != 7:
                    continue
                first_row = bar * 16
                last_row = first_row + 16
                melody = {
                    pitch_class(event["note"])
                    for event in source["patterns"][str(section)]
                    if first_row <= event["row"] < last_row and event["note"] is not None
                }
                backing = {
                    pitch_class(event["note"])
                    for channel in (1, 2)
                    for event in source["patterns"][str(section + channel * 100)]
                    if first_row <= event["row"] < last_row and event["note"] is not None
                }
                with self.subTest(section=section, bar=bar + 1):
                    self.assertTrue(
                        melody <= backing,
                        f"B-major phrase {sorted(melody)} is not supported by "
                        f"accompaniment {sorted(backing)}",
                    )



if __name__ == "__main__":
    unittest.main()
