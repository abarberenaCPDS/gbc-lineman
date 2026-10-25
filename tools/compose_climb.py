"""Compose an original climb theme and optionally render it with local uge-builder.

python3 tools/compose_climb.py --render

Uses only the already-installed Docker image (no network/pull). Instrument
patching applies only to this generator's v6 output and is checked by the
repo's independent uge_report decoder. Legacy tracks are left unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from make_climb_scene import resource_id, write_json
import uge_report

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets/music"
NAME = "cfe_storm_climb"

# Eight four-bar sections: statement, answer, variation, lift, breathing bridge,
# bridge answer, reprise, turnaround. Rhythm, not high-register repetition,
# carries the momentum. No notes are copied from the legacy reference hook.
PHRASES = [
    ["E5", "G5", "B5", "A5", "G5", "F#5"],
    ["E5", "G5", "C6", "B5", "G5", "E5"],
    ["D5", "G5", "B5", "A5", "G5", "D5"],
    ["F#5", "A5", "D6", "B5", "A5", "F#5"],
    ["G5", "B5", "E6", "D6", "B5", "G5"],
    ["A5", "G5", "E5", "D5", "E5", "F#5"],
    ["C5", "E5", "A5", "G5", "E5", "D5"],
    ["F#5", "D#5", "B4", "D#5", "F#5", "B5"],
]
SECTIONS = [(0, 1, 2, 3), (0, 1, 4, 5), (4, 1, 2, 3), (4, 5, 4, 7),
            (6, 1, 6, 7), (6, 5, 2, 7), (0, 1, 4, 5), (4, 5, 6, 7)]
CHORDS = [
    (("E3", "B3"), ("G4", "B4")),
    (("C3", "G3"), ("E4", "G4")),
    (("G3", "D4"), ("B4", "D5")),
    (("D3", "A3"), ("F#4", "A4")),
]


def note(row, pitch, inst, volume=None):
    result = {"row": row, "note": pitch, "inst": inst, "fx": 0, "fxp": 0}
    if volume is not None:
        result.update(fx=0xC, fxp=volume)
    return result


def cut(row):
    return {"row": row, "note": None, "inst": 0, "fx": 0xE, "fxp": 0}


def song():
    patterns = {}
    orders = [[], [], [], []]
    for section, phrase_ids in enumerate(SECTIONS):
        parts = [[], [], [], []]
        bridge = section in (4, 5)
        for bar, phrase_id in enumerate(phrase_ids):
            offset = bar * 16
            for row, pitch in zip((0, 3, 6, 8, 10, 13), PHRASES[phrase_id]):
                # Leave audible air in the bridge, not just a louder reprise.
                if not bridge or row in (0, 6, 10):
                    parts[0].append(note(offset + row, pitch, 2, 9 if not bridge else 7))
            parts[0].append(cut(offset + 15))
            bass, harmony = CHORDS[bar]
            if bridge:
                bass, harmony = [(("A3", "E4"), ("C5", "E5")), CHORDS[1], CHORDS[2],
                                 (("B3", "F#4"), ("D#5", "F#5"))][bar]
            if phrase_id == 7:
                bass, harmony = ("B3", "F#4"), ("D#5", "F#5")
            elif phrase_id == 6:
                bass, harmony = ("A3", "E4"), ("C5", "E5")
            for row, pitch in zip((2, 6, 10, 14), harmony * 2):
                parts[1].append(note(offset + row, pitch, 1, 4 if bridge else 5))
                parts[1].append(cut(offset + row + 1))
            for row, pitch in zip((0, 6, 10, 14), (bass[0], bass[1], bass[0], bass[1])):
                parts[2].append(note(offset + row, pitch, 1))
            parts[2].append(cut(offset + 15))
            beats = ((0, "B5", 1, 7), (4, "D#7", 2, 5),
                     (8, "B5", 1, 6), (12, "D#7", 2, 5))
            for row, pitch, inst, volume in beats:
                if bridge and row not in (0, 12):
                    continue
                parts[3].extend([note(offset + row, pitch, inst, volume), cut(offset + row + 1)])
        for channel, events in enumerate(parts):
            key = section + channel * 100
            orders[channel].append(key)
            patterns[str(key)] = sorted(events, key=lambda e: e["row"])
    result = {
        "name": "Storm Climb - Lights Uphill", "artist": "abe",
        "comment": "Original E-minor adventure theme: A/A'/lift/bridge/reprise; 32 bars, ~51.4s. Human mix review pending.",
        "ticks_per_row": 6, "orders": orders, "patterns": patterns,
        "waves": {"0": [4, 5, 6, 7, 8, 9, 10, 11, 12, 11, 10, 9, 8, 7, 6, 5] * 2},
    }
    validate(result)
    return result


def validate(value):
    assert len(value["orders"]) == 4 and all(len(seq) == 8 for seq in value["orders"])
    for events in value["patterns"].values():
        rows = [e["row"] for e in events]
        assert len(rows) == len(set(rows)) and all(0 <= r < 64 for r in rows)
        for item in events:
            pitch = item["note"]
            if pitch is not None:
                normalized = pitch[0] + (pitch[1:] if "#" in pitch else "-" + pitch[1:])
                assert normalized in uge_report.NOTE_NAMES, pitch


def refine_instruments(path):
    data = bytearray(path.read_bytes())
    assert struct.unpack_from("<i", data)[0] == 6, "only hUGETracker v6 is supported"
    # See uge_report's documented TInstrumentV3 offsets. Less piercing pulse
    # lead, quieter harmony/bass, short noise envelopes leave SFX headroom.
    for slot, volume, decay, duty in ((0, 6, 2, 1), (1, 10, 2, 2)):
        offset = uge_report.INSTR_BASE + slot * uge_report.INSTR_SIZE
        data[offset + 265] = volume
        struct.pack_into("<i", data, offset + 266, 1)
        data[offset + 270] = decay
        data[offset + 283] = duty
    wave = uge_report.INSTR_BASE + 15 * uge_report.INSTR_SIZE
    struct.pack_into("<i", data, wave + 284, 2)  # half-level wave bass
    for slot in (30, 31):
        offset = uge_report.INSTR_BASE + slot * uge_report.INSTR_SIZE
        data[offset + 265] = 7
        struct.pack_into("<i", data, offset + 266, 1)
        data[offset + 270] = 2
    path.write_bytes(data)
    decoded = uge_report.parse(str(path))
    assert decoded["trailing_bytes"] == 0
    assert decoded["instruments"][1]["initial_volume"] == 10
    assert decoded["instruments"][15]["output_level"] == 2
    assert decoded["orders"][0][:-1] == list(range(8))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true", help="use installed uge-builder Docker image, offline")
    args = parser.parse_args()
    source = MUSIC / f"{NAME}.json"
    source.write_text(json.dumps(song(), indent=2) + "\n")
    if args.render:
        subprocess.run([
            "docker", "run", "--rm", "--pull=never", "--network=none",
            "--mount", f"type=bind,source={MUSIC},target=/music", "uge-builder",
            "uge_gen", f"/music/{NAME}.json", f"/music/{NAME}.uge",
        ], check=True)
        destination = MUSIC / f"{NAME}.uge"
        refine_instruments(destination)
        write_json(Path(str(destination) + ".gbsres"), {
            "_resourceType": "music", "id": resource_id("music:storm-climb"),
            "name": NAME, "filename": destination.name, "symbol": "song_cfe_storm_climb",
            "settings": {}, "type": "uge",
        })
        print(f"rendered {destination.relative_to(ROOT)} sha256={hashlib.sha256(destination.read_bytes()).hexdigest()}")
    else:
        print(f"wrote {source.relative_to(ROOT)}; use --render to build the native UGE")


if __name__ == "__main__":
    main()
