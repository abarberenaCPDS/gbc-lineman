#!/usr/bin/env python3
"""Write the source JSON and native sidecars for the CFE music set.

The JSON follows hUGETracker/abe/composer/validate.py and uge_gen.lpr. Render
the five JSON files with the `uge-builder` Docker image; this script does not
write binary .uge files.
"""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets" / "music"
TICKS = 6  # ~149.32 BPM at 59.7275 VBlank Hz; same as Fast Pace Speed Race.
MUSIC_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://modretro-chromatic.example/gb-mr-cfe/music")

# The Fast Pace hook is the identity of the set.  Each phrase lasts one bar:
# eight off-beat notes, then an explicit tracker note cut on row 15.  The
# surrounding silent rows give the lead enough air to be remembered.
MOTIF = ["F5", "C6", "F6", "F5", "D#6", "C6", "D#6", "F6"]
MOTIF_OFFSETS = list(range(0, 16, 2))
ANSWER_RISE = ["F5", "C6", "F6", "G6", "F6", "D#6", "C6", "A#5"]
ANSWER_FALL = ["F5", "C6", "D#6", "C6", "A#5", "G5", "F5", "C6"]
CADENCE = ["F5", "C6", "F6", "D#6", "C6", "A#5", "G5", "F5"]

# The existing intro/win IDs are retained so any project references remain
# valid. The new village IDs are UUIDv5, stable across runs.
EXISTING_IDS = {
    "cfe_intro": "ef24b514-07e8-5585-928e-905a3e924b7f",
    "cfe_win": "a0533ba2-661a-5fed-ae5e-55bfc5e0c59f",
}


def ev(row, note, inst, fx=0, fxp=0):
    return {"row": row, "note": note, "inst": inst, "fx": fx, "fxp": fxp}


def add_phrase(pattern, start, notes):
    """Add a one-bar lead phrase and silence its final tracker row."""
    for offset, note in zip(MOTIF_OFFSETS, notes):
        pattern.append(ev(start + offset, note, 2))
    pattern.append(ev(start + 15, None, 0, fx=0xE, fxp=0))


def lead_pattern(stage, section):
    """Return an A/B/C loop section with readable call-and-response rests."""
    layouts = {
        1: (
            ((0, MOTIF), (32, CADENCE)),
            ((16, MOTIF), (48, ANSWER_FALL)),
            ((0, MOTIF), (32, CADENCE)),
        ),
        2: (
            ((0, MOTIF), (24, ANSWER_RISE), (48, CADENCE)),
            ((8, MOTIF), (32, ANSWER_FALL), (48, CADENCE)),
            ((0, MOTIF), (24, ANSWER_RISE), (48, CADENCE)),
        ),
        3: (
            ((0, MOTIF), (16, ANSWER_RISE), (32, MOTIF), (48, CADENCE)),
            ((0, MOTIF), (16, ANSWER_FALL), (32, MOTIF), (48, CADENCE)),
            ((0, MOTIF), (16, ANSWER_RISE), (32, MOTIF), (48, CADENCE)),
        ),
    }
    pattern = []
    for start, notes in layouts[stage][section]:
        add_phrase(pattern, start, notes)
    return pattern


HARMONY_SHELLS = [
    (0, "A#4"), (8, "C5"), (16, "G4"), (24, "A#4"),
    (32, "D4"), (40, "F4"), (48, "G4"), (56, "A#4"),
]
COUNTERLINES = (
    [(0, "A#4"), (6, "C5"), (12, "A#4"), (16, "G4"),
     (22, "A#4"), (28, "D#5"), (32, "D4"), (38, "F4"),
     (44, "A#4"), (48, "G4"), (54, "A#4"), (60, "C5")],
    [(2, "C5"), (8, "A#4"), (14, "G4"), (18, "A#4"),
     (24, "D#5"), (30, "A#4"), (34, "F4"), (40, "D4"),
     (46, "F4"), (50, "G4"), (56, "A#4"), (62, "C5")],
    [(0, "A#4"), (6, "C5"), (12, "A#4"), (16, "G4"),
     (22, "A#4"), (28, "D#5"), (32, "D4"), (38, "F4"),
     (44, "A#4"), (48, "G4"), (54, "A#4"), (60, "C5")],
)

BASS_ANCHORS = (
    [(0, "F3"), (12, "C4"), (32, "D#3"), (44, "A#3")],
    [(16, "A#3"), (28, "F3"), (48, "C3"), (60, "E3")],
    [(0, "F3"), (12, "C4"), (32, "D#3"), (60, "E3")],
)
BASS_MID = [
    (0, "F3"), (8, "C4"), (16, "D#3"), (24, "A#3"),
    (32, "A#3"), (40, "F3"), (48, "C3"), (56, "G3"),
]
BASS_WALK = [
    (0, "F3"), (4, "G3"), (8, "A#3"), (12, "C4"),
    (16, "D#4"), (20, "C4"), (24, "A#3"), (28, "G3"),
    (32, "A#3"), (36, "G3"), (40, "F3"), (44, "D#3"),
    (48, "C3"), (52, "D3"), (56, "D#3"), (60, "E3"),
]

DRUMS = {
    1: (
        [(0, "B5"), (32, "D#7")],
        [(16, "B5"), (48, "D#7")],
        [(0, "B5"), (30, "D#7"), (32, "B5")],
    ),
    2: (
        [(0, "B5"), (12, "D#7"), (16, "B5"), (28, "D#7"),
         (32, "B5"), (44, "D#7"), (48, "B5"), (60, "D#7")],
        [(4, "B5"), (16, "D#7"), (20, "B5"), (32, "D#7"),
         (36, "B5"), (48, "D#7"), (52, "B5"), (62, "D#7")],
        [(0, "B5"), (12, "D#7"), (16, "B5"), (28, "D#7"),
         (32, "B5"), (44, "D#7"), (48, "B5"), (60, "D#7")],
    ),
    3: (
        [(0, "B5"), (8, "D#7"), (16, "B5"), (24, "D#7"),
         (30, "D#7"), (32, "B5"), (40, "D#7"), (48, "B5"),
         (56, "D#7"), (62, "D#7")],
        [(0, "B5"), (12, "D#7"), (16, "B5"), (24, "D#7"),
         (32, "B5"), (40, "D#7"), (46, "D#7"), (48, "B5"),
         (60, "D#7")],
        [(0, "B5"), (8, "D#7"), (16, "B5"), (24, "D#7"),
         (30, "D#7"), (32, "B5"), (40, "D#7"), (48, "B5"),
         (56, "D#7"), (62, "D#7")],
    ),
}


def notes(events, inst):
    return [ev(row, note, inst) for row, note in events]


def village_song(stage):
    patterns = {}
    orders = [[0, 1, 2], [10, 11, 12], [20, 21, 22], [30, 31, 32]]
    for section in range(3):
        patterns[str(section)] = lead_pattern(stage, section)
        if stage == 1:
            harmony, bass = [], notes(BASS_ANCHORS[section], 1)
        elif stage == 2:
            harmony, bass = notes(HARMONY_SHELLS, 1), notes(BASS_MID, 1)
        else:
            harmony, bass = notes(COUNTERLINES[section], 1), notes(BASS_WALK, 1)
        patterns[str(10 + section)] = harmony
        patterns[str(20 + section)] = bass
        # Noise is punctuation, not a continuous click track.  B5 is the low
        # accent and D#7 is the lighter response/pickup in the Fast Pace family.
        patterns[str(30 + section)] = notes(DRUMS[stage][section], 2)

    labels = {
        1: "Base state: spacious F-centered hook, bass anchors and isolated noise punctuation.",
        2: "Adds harmonic shells, a mid-tempo bass path and restrained backbeat answers.",
        3: "Full arrangement: F hook, answering counter-line, walking wave bass and selected drum accents.",
    }
    return {
        "name": f"CFE Village {stage}",
        "artist": "abe",
        "comment": f"{labels[stage]} 3 x 64-row loop, ~19.3 seconds at ~149.32 BPM.",
        "ticks_per_row": TICKS,
        "orders": orders,
        "patterns": patterns,
    }


def intro_song():
    # One 64-row phrase gives a 6.43-second one-shot sting with a held tonic tail.
    lead = [ev(i * 4, note, 2) for i, note in enumerate(MOTIF)]
    lead.append(ev(40, "F5", 2))
    bass = [ev(0, "F3", 1), ev(32, "C3", 1)]
    noise = [ev(0, "B5", 2), ev(32, "D#7", 2)]
    return {
        "name": "CFE Intro", "artist": "abe",
        "comment": "6.43-second intro sting: introduces the shared F-Dorian motif and lands on F.",
        "ticks_per_row": TICKS,
        "orders": [[0], [1], [2], [3]],
        "patterns": {"0": lead, "1": [], "2": bass, "3": noise},
    }


def win_song():
    lead = [ev(offset, note, 2) for offset, note in zip(MOTIF_OFFSETS, MOTIF)]
    lead.extend([ev(32, "C6", 2), ev(36, "D#6", 2), ev(40, "F6", 2),
                 ev(48, "C6", 2), ev(56, "F5", 2)])
    harmony = [ev(0, "A#4", 1), ev(16, "G#4", 1), ev(32, "A#4", 1),
               ev(48, "F4", 1)]
    bass = [ev(0, "F3", 1), ev(16, "A#3", 1), ev(32, "C4", 1), ev(48, "F3", 1)]
    drums = [ev(0, "B5", 2), ev(16, "D#7", 2), ev(32, "B5", 2), ev(48, "D#7", 2)]
    return {
        "name": "CFE Win", "artist": "abe",
        "comment": "6.43-second victory flourish: states the shared motif, then resolves to F with a held tonic.",
        "ticks_per_row": TICKS,
        "orders": [[0], [1], [2], [3]],
        "patterns": {"0": lead, "1": harmony, "2": bass, "3": drums},
    }


SONGS = {
    "cfe_village_1": village_song(1),
    "cfe_village_2": village_song(2),
    "cfe_village_3": village_song(3),
    "cfe_intro": intro_song(),
    "cfe_win": win_song(),
}


def write_song(name, song):
    MUSIC.mkdir(parents=True, exist_ok=True)
    json_path = MUSIC / f"{name}.json"
    uge_path = MUSIC / f"{name}.uge"
    sidecar_path = Path(str(uge_path) + ".gbsres")
    if name in EXISTING_IDS:
        if not sidecar_path.exists():
            raise FileNotFoundError(f"expected existing sidecar to preserve ID: {sidecar_path}")
        sidecar = json.loads(sidecar_path.read_text())
        if sidecar.get("id") != EXISTING_IDS[name]:
            raise ValueError(f"existing {name} ID changed; refusing to replace: {sidecar.get('id')}")
    else:
        expected_id = str(uuid.uuid5(MUSIC_NAMESPACE, name))
        if sidecar_path.exists():
            sidecar = json.loads(sidecar_path.read_text())
            if sidecar.get("id") != expected_id or sidecar.get("name") != name:
                raise ValueError(f"existing sidecar is not this generator's asset: {sidecar_path}")
        elif uge_path.exists():
            raise FileExistsError(f"UGE exists without its owned sidecar; refusing: {uge_path}")
        else:
            sidecar = {
                "_resourceType": "music",
                "id": expected_id,
                "name": name,
                "symbol": f"song_{name}",
                "settings": {},
                "filename": f"{name}.uge",
                "type": "uge",
            }
    json_path.write_text(json.dumps(song, indent=2, ensure_ascii=False) + "\n")
    create_sidecar = name not in EXISTING_IDS and not sidecar_path.exists()
    if create_sidecar:
        sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n")
    print(f"wrote {json_path.relative_to(ROOT)}")
    if create_sidecar:
        print(f"wrote {sidecar_path.relative_to(ROOT)} id={sidecar['id']}")
    elif name in EXISTING_IDS:
        print(f"preserved existing sidecar {sidecar_path.relative_to(ROOT)} id={sidecar['id']}")
    else:
        print(f"preserved generated sidecar {sidecar_path.relative_to(ROOT)} id={sidecar['id']}")


def main():
    for name, song in SONGS.items():
        write_song(name, song)


if __name__ == "__main__":
    main()
