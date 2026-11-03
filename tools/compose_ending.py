"""Compose a short D-major resolution from Intro B's hero and mission motifs.

Run ``python3 tools/compose_ending.py`` to write the editable JSON source.
``--render`` uses the installed offline uge-builder, then the established
instrument refinement and decoder validation. Rendering is owned by main.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

import ending
import intro
from compose_climb import refine_instruments, validate
from compose_intro import A, Bm, D, G, section, song
from make_climb_scene import write_json

ROOT = Path(__file__).resolve().parent.parent
MUSIC = ROOT / "assets" / "music"
def _lead_bars(theme: dict, section_index: int) -> list[list[tuple[int, str]]]:
    """Copy one four-bar lead motif from a freshly composed Intro B score."""
    source = theme["patterns"][str(section_index)]
    result: list[list[tuple[int, str]]] = [[] for _ in range(4)]
    for event in source:
        pitch = event["note"]
        if pitch is not None:
            result[event["row"] // 16].append((event["row"] % 16, pitch))
    return result


def candidate() -> tuple[str, dict]:
    """Build two 4-bar sections without modifying Intro B's source score."""
    theme_name, theme_b = intro_variant_b()
    if theme_name != intro.THEME_FILES["b"]:
        raise AssertionError("Intro B source name changed")
    # Intro B's accepted hero and mission sections are indices 7 and 8.
    hero = _lead_bars(theme_b, 7)
    mission = _lead_bars(theme_b, 8)
    # Make the final mission cadence land explicitly on D, retaining the motif's
    # rhythmic contour while resolving its last note to the tonic.
    mission[-1] = [(row, pitch) for row, pitch in mission[-1] if row < 12]
    mission[-1].append((12, "D5"))

    sections = [
        section(hero, [D, G, D, A], "anthem"),
        section(mission, [D, Bm, G, D], "anthem"),
    ]
    result = song(
        ending.NAME,
        "Storm Report - Home",
        "Two-section D-major ending reprise from Intro B hero/mission motifs; 8s, tpr 4.",
        ending.TICKS_PER_ROW,
        sections,
    )
    validate(result[1], ending.SECTIONS)
    return result


def intro_variant_b():
    """Late import keeps this module's public composer helpers explicit."""
    from compose_intro import variant_b

    return variant_b()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--render", action="store_true",
                        help="use installed uge-builder Docker image, offline")
    args = parser.parse_args()
    name, data = candidate()
    (MUSIC / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    if not args.render:
        print(f"wrote assets/music/{name}.json")
        return
    subprocess.run([
        "docker", "run", "--rm", "--pull=never", "--network=none",
        "--mount", f"type=bind,source={MUSIC},target=/music", "uge-builder",
        "uge_gen", f"/music/{name}.json", f"/music/{name}.uge",
    ], check=True)
    destination = MUSIC / f"{name}.uge"
    refine_instruments(destination, ending.SECTIONS)
    write_json(Path(str(destination) + ".gbsres"), {
        "_resourceType": "music", "id": ending.MUSIC_ID, "name": name,
        "filename": destination.name, "symbol": "song_cfe_ending_reprise",
        "settings": {}, "type": "uge",
    })
    print(f"rendered assets/music/{name}.uge sha256="
          f"{hashlib.sha256(destination.read_bytes()).hexdigest()[:12]}")


if __name__ == "__main__":
    main()
