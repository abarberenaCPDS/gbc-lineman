"""Compose the three intro-theme candidates and optionally render them.

python3 tools/compose_intro.py --render

Each variant follows the intro story in eight 4-bar sections: dusk, dusk
answer, storm, storm answer, the snap, grey morning, the electrician's rise,
the mission. They differ in key, tempo and groove so Abe can pick by ear:

  a  "Evening on the Hill"   D major lullaby that darkens to D minor, tpr 5
  b  "Storm Front"           driving D minor with drums, lifts to D major, tpr 4
  c  "Bring the Power Home"  C major march with an A minor storm, tpr 5

Rendering uses only the installed uge-builder Docker image (offline), then the
climb's instrument refinement (same instrument slots) and the repo's own
uge_report decoder. Stable music IDs come from tools/intro.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import intro
from compose_climb import cut, note, refine_instruments, validate
from make_climb_scene import write_json

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets/music"

# Instruments (as in the climb): channel 0 lead uses inst 2, channel 1 harmony
# inst 1, channel 2 wave bass inst 1, channel 3 noise inst 1 (kick) / 2 (hat).
LEAD, HARM, BASS = 2, 1, 1
KICK, HAT = (1, "B5"), (2, "D#7")


def bar(spec: str) -> list[tuple[int, str]]:
    """'0:F#5 4:A5' -> [(0, 'F#5'), (4, 'A5')] (rows within a 16-row bar)."""
    return [(int(row), pitch) for row, pitch in (item.split(":") for item in spec.split())]


def section(phrases, chords, style):
    """One 64-row pattern per channel. ``chords`` are (bass, (h1, h2, h3)) per bar."""
    parts = [[], [], [], []]
    for b, (phrase, (bass, triad)) in enumerate(zip(phrases, chords)):
        o = b * 16
        lead_volume = {"calm": 8, "storm": 10, "sombre": 6, "anthem": 11, "march": 10}[style]
        for row, pitch in phrase:
            parts[0].append(note(o + row, pitch, LEAD, lead_volume))
        if not any(row == 15 for row, _ in phrase):
            parts[0].append(cut(o + 15))
        # Harmony
        if style in ("calm", "sombre"):
            rows = range(0, 16, 2) if style == "calm" else (0, 8)
            for i, row in enumerate(rows):
                parts[1].append(note(o + row, triad[i % 3], HARM, 4 if style == "calm" else 3))
        elif style == "storm":
            for row in (2, 6, 10, 14):
                parts[1].append(note(o + row, triad[row // 4 % 3], HARM, 5))
                parts[1].append(cut(o + row + 1))
        else:  # anthem / march: held chord tones on the beat
            for i, row in enumerate((0, 4, 8, 12)):
                parts[1].append(note(o + row, triad[i % 3], HARM, 5))
            parts[1].append(cut(o + 15))
        # Bass (wave channel)
        root, fifth = bass
        bass_rows = {"calm": ((0, root), (8, fifth)), "sombre": ((0, root),),
                     "storm": tuple((r, root if r % 4 == 0 else fifth) for r in range(0, 16, 2)),
                     "anthem": ((0, root), (4, fifth), (8, root), (12, fifth)),
                     "march": ((0, root), (6, fifth), (8, root), (14, fifth))}[style]
        for row, pitch in bass_rows:
            parts[2].append(note(o + row, pitch, BASS))
        parts[2].append(cut(o + 15))
        # Noise
        hits = {"calm": ((8, HAT, 3),), "sombre": (),
                "storm": ((0, KICK, 7), (4, HAT, 5), (8, KICK, 6), (10, HAT, 4),
                          (12, HAT, 5), (14, HAT, 4)),
                "anthem": ((0, KICK, 7), (4, HAT, 5), (8, KICK, 6), (12, HAT, 5)),
                "march": ((0, KICK, 7), (6, HAT, 4), (8, KICK, 6), (12, HAT, 5),
                          (14, HAT, 4))}[style]
        for row, (inst, pitch), volume in hits:
            parts[3].extend([note(o + row, pitch, inst, volume), cut(o + row + 1)])
    return parts


def song(name, title, comment, tpr, sections):
    patterns, orders = {}, [[], [], [], []]
    for index, parts in enumerate(sections):
        for channel, events in enumerate(parts):
            key = index + channel * 100
            orders[channel].append(key)
            patterns[str(key)] = sorted(events, key=lambda e: e["row"])
    result = {"name": title, "artist": "abe", "comment": comment, "ticks_per_row": tpr,
              "orders": orders, "patterns": patterns,
              "waves": {"0": [4, 5, 6, 7, 8, 9, 10, 11, 12, 11, 10, 9, 8, 7, 6, 5] * 2}}
    validate(result)
    return name, result


# Chords: (bass (root, fifth), triad for harmony)
D = (("D3", "A3"), ("D4", "F#4", "A4"))
G = (("G3", "D4"), ("G4", "B4", "D5"))
A = (("A3", "E4"), ("A4", "C#5", "E5"))
Bm = (("B3", "F#4"), ("B4", "D5", "F#5"))
Dm = (("D3", "A3"), ("D4", "F4", "A4"))
Bb = (("A#3", "F4"), ("A#4", "D5", "F5"))
C = (("C3", "G3"), ("C4", "E4", "G4"))
Gm = (("G3", "D4"), ("G4", "A#4", "D5"))
F = (("F3", "C4"), ("F4", "A4", "C5"))
Am = (("A3", "E4"), ("A4", "C5", "E5"))
Em = (("E3", "B3"), ("E4", "G4", "B4"))
Dmaj_hi = (("D3", "A3"), ("F#4", "A4", "D5"))


def variant_a():
    p = [bar("0:F#5 4:A5 8:D6 12:C#6"), bar("0:B5 4:A5 8:F#5 12:E5"),
         bar("0:G5 4:B5 8:E6 12:D6"), bar("0:C#6 6:A5 10:E5"),
         bar("0:D5 2:F5 4:A5 6:F5 8:D6 10:C6 12:A5 14:F5"),
         bar("0:C5 2:E5 4:G5 6:E5 8:A#5 10:A5 12:G5 14:E5"),
         bar("0:F5 8:E5 12:D5"), bar("0:D5 2:F#5 4:A5 8:D6 10:E6 12:F#6")]
    return song("cfe_intro_a", "Intro A - Evening on the Hill",
                "D major lullaby, storm in D minor, sombre morning, mission rise; tpr 5.", 5, [
        section([p[0], p[1], p[2], p[3]], [D, Bm, G, A], "calm"),
        section([p[0], p[1], p[2], p[3]], [D, Bm, G, A], "calm"),
        section([p[4], p[5], p[4], p[5]], [Dm, C, Dm, C], "storm"),
        section([p[4], p[5], p[4], p[6]], [Dm, C, Bb, A], "storm"),
        section([p[6], p[6], p[6], p[3]], [Dm, Bb, Gm, A], "sombre"),
        section([p[6], p[1], p[6], p[3]], [Bm, G, Bm, A], "sombre"),
        section([p[7], p[2], p[7], p[3]], [D, G, D, A], "anthem"),
        section([p[0], p[2], p[7], p[3]], [Dmaj_hi, G, D, A], "anthem"),
    ])


def variant_b():
    p = [bar("0:D5 2:D5 4:F5 6:D5 8:A5 10:G5 12:F5 14:E5"),
         bar("0:D5 3:F5 6:A5 8:C6 11:A5 14:G5"),
         bar("0:A#5 2:A5 4:G5 6:F5 8:E5 10:F5 12:G5 14:A5"),
         bar("0:D6 4:C6 6:A5 8:F5 12:E5"),
         bar("0:A5 4:A5 6:A#5 8:A5 12:G5"),
         bar("0:F5 8:E5"),
         bar("0:D5 2:F#5 4:A5 6:D6 8:C#6 10:A5 12:B5 14:C#6"),
         bar("0:D6 4:F#6 8:E6 10:D6 12:A5")]
    return song("cfe_intro_b", "Intro B - Storm Front",
                "Driving D minor storm groove with drums, Picardy lift to D major; tpr 4.", 4, [
        section([p[1], p[3], p[1], p[5]], [Dm, F, Dm, A], "calm"),
        section([p[0], p[2], p[0], p[3]], [Dm, Bb, Dm, A], "storm"),
        section([p[0], p[2], p[4], p[3]], [Dm, Bb, Gm, A], "storm"),
        section([p[0], p[1], p[4], p[3]], [Dm, F, Gm, A], "storm"),
        section([p[5], p[5], p[5], p[5]], [Dm, Bb, Gm, A], "sombre"),
        section([p[1], p[5], p[1], p[5]], [Dm, C, Bb, A], "sombre"),
        section([p[6], p[7], p[6], p[7]], [D, G, D, A], "anthem"),
        section([p[6], p[7], p[6], p[7]], [D, Bm, G, A], "anthem"),
    ])


def variant_c():
    p = [bar("0:C5 3:C5 4:E5 6:G5 8:C6 12:G5"),
         bar("0:A5 3:G5 4:F5 6:E5 8:D5 12:G5"),
         bar("0:E5 3:E5 4:G5 6:C6 8:E6 10:D6 12:C6 14:B5"),
         bar("0:D6 3:C6 4:B5 6:A5 8:G5"),
         bar("0:A5 2:C6 4:E6 6:C6 8:A5 10:B5 12:C6 14:B5"),
         bar("0:G5 2:B5 4:D6 6:B5 8:G5 10:F5 12:E5 14:D5"),
         bar("0:E5 8:D5 12:C5"),
         bar("0:G5 3:G5 4:C6 6:E6 8:G6 12:E6")]
    return song("cfe_intro_c", "Intro C - Bring the Power Home",
                "C major march, A minor storm, hushed morning, anthem finale; tpr 5.", 5, [
        section([p[0], p[1], p[2], p[3]], [C, F, C, G], "march"),
        section([p[0], p[1], p[2], p[3]], [C, F, Am, G], "march"),
        section([p[4], p[5], p[4], p[5]], [Am, G, Am, Em], "storm"),
        section([p[4], p[5], p[4], p[3]], [Am, G, F, G], "storm"),
        section([p[6], p[6], p[6], p[6]], [Am, F, C, G], "sombre"),
        section([p[6], p[1], p[6], p[3]], [Am, F, C, G], "sombre"),
        section([p[7], p[2], p[7], p[3]], [C, F, C, G], "anthem"),
        section([p[7], p[1], p[2], p[0]], [C, F, G, C], "anthem"),
    ])


VARIANTS = {"a": variant_a, "b": variant_b, "c": variant_c}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true",
                        help="use the installed uge-builder Docker image, offline")
    args = parser.parse_args()
    for key, build in VARIANTS.items():
        name, data = build()
        assert name == intro.THEME_FILES[key]
        (MUSIC / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
        if not args.render:
            print(f"wrote assets/music/{name}.json")
            continue
        subprocess.run([
            "docker", "run", "--rm", "--pull=never", "--network=none",
            "--mount", f"type=bind,source={MUSIC},target=/music", "uge-builder",
            "uge_gen", f"/music/{name}.json", f"/music/{name}.uge",
        ], check=True)
        destination = MUSIC / f"{name}.uge"
        refine_instruments(destination)
        write_json(Path(str(destination) + ".gbsres"), {
            "_resourceType": "music", "id": intro.THEME_IDS[key], "name": name,
            "filename": destination.name, "symbol": f"song_{name}", "settings": {},
            "type": "uge",
        })
        print(f"rendered assets/music/{name}.uge "
              f"sha256={hashlib.sha256(destination.read_bytes()).hexdigest()[:12]}")


if __name__ == "__main__":
    main()
