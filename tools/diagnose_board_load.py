#!/usr/bin/env python3
"""Prepare matched standing-board load fixtures; never build or launch them.

Run from the intended worktree, or pass --project-root. Both copies preserve
all other hazards. Only the board warning timer is extended so native timing
can be sampled while the player remains alive on board 2.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

BASELINE_TAG = "v0.20.0-dev"
EXTENDED_WARNING = 10000
SCENE = "storm_climb"
BOARD_SYMBOLS = ("board_01", "board_02", "board_03")
SEEDS = {"16": 0, "40": 1, "41": 1, "44": 2, "6": 3, "50": 1, "51": 1}


def events(script: list[dict[str, Any]]):
    for event in script:
        yield event
        for children in event.get("children", {}).values():
            yield from events(children)


def extend_original(resource: dict[str, Any]) -> None:
    matches = [event for event in events(resource["updateScript"])
               if event["command"] == "EVENT_WAIT"
               and event["args"].get("units") == "frames"
               and event["args"].get("frames") == {"type": "number", "value": 50}]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one original warning WAIT50 in {resource['symbol']}")
    matches[0]["args"]["frames"]["value"] = EXTENDED_WARNING


def extend_candidate(resource: dict[str, Any]) -> None:
    # Final event-driven boards use the same native wait as the baseline.
    extend_original(resource)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    root = arguments.project_root.resolve()
    if not (root / "mr-cfe.gbsproj").is_file():
        parser.error("Select the campaign worktree with --project-root or the working directory")
    sys.path.insert(0, str(root / "tools"))
    diagnostics = importlib.import_module("make_campaign_diagnostics")
    if diagnostics.ROOT.resolve() != root:
        raise RuntimeError("Imported diagnostics helper belongs to another worktree")

    fixtures = [
        ("board-load-original", True),
        ("board-load-candidate", False),
    ]
    for name, original in fixtures:
        destination = diagnostics.fixture(name, SCENE, 11, 14, dict(SEEDS))
        actor_directory = destination / "project/scenes" / SCENE / "actors"
        for symbol in BOARD_SYMBOLS:
            relative = Path("project/scenes") / SCENE / "actors" / f"{symbol}.gbsres"
            if original:
                contents = subprocess.run(
                    ["git", "show", f"{BASELINE_TAG}:{relative.as_posix()}"],
                    cwd=root, check=True, capture_output=True, text=True,
                ).stdout
                resource = json.loads(contents)
                extend_original(resource)
            else:
                resource = json.loads((root / relative).read_text())
                extend_candidate(resource)
            (actor_directory / f"{symbol}.gbsres").write_text(json.dumps(resource, indent=2) + "\n")
        print(destination / "mr-cfe.gbsproj")
    print("Prepared matched load fixtures; all other hazards remain active. No builds or emulator actions ran.")


if __name__ == "__main__":
    main()
