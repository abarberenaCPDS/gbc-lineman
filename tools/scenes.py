"""Single registry of GB Studio scenes, tagged game / lab / legacy.

Stdlib only: generators and tests import this before any Pillow work.

- ``game``: ships in the ROM; reachable from the launch scene.
- ``lab``: developer test rooms; removed from the release copy.
- ``legacy``: retired Storm Night / village references; removed from the release copy.

``generator`` names the script that owns the scene file (``None`` for legacy
scenes that are kept only as references and edited by hand).

Planned scenes (the multi-scene redesign, docs/LEVEL_REDESIGN.md §2/§7) are
registered ahead of their generators with ``"planned": "<work package>"``.
A planned scene may be absent from project/scenes/ and its generator may not
exist yet; the tests treat it like any other scene as soon as its folder is
generated (activation is "the folder exists", nothing to edit here). Its id is
the owning job's ``resource_id("scene:<folder>")`` (test_scenes checks it), so
a generator writes ``"id": scenes.REGISTRY[folder]["id"]`` or the same derived
value. ``active(folder)`` is false only for a planned scene not generated yet.
Once a work package lands, main may drop its ``planned`` key.
"""

from __future__ import annotations

import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCENES_DIR = ROOT / "project" / "scenes"

GAME = "game"
LAB = "lab"
LEGACY = "legacy"
TAGS = (GAME, LAB, LEGACY)

_NAMESPACE = uuid.UUID("c3a8f5d2-6e1b-5b7a-9d4f-2e8c0a6b1f73")


def _lab_id(folder: str) -> str:
    return str(uuid.uuid5(_NAMESPACE, "mr-cfe:scenes:" + folder))


# Game ids are the ids already written into scene.gbsres (the generators derive
# the same values; tests compare them against the files).
REGISTRY: dict[str, dict] = {
    "intro_logo": {
        "id": "8f0deaff-d588-56a3-97a8-ea67a2a84555", "name": "Abe's Games Logo",
        "tag": GAME, "editor": (0, -240), "generator": "make_intro_scene.py",
    },
    "intro_story": {
        "id": "a57805cb-ca4c-5b69-8a7b-eb20a18cf415", "name": "Intro Story",
        "tag": GAME, "editor": (240, -240), "generator": "make_intro_scene.py",
    },
    "title": {
        "id": "1688d107-3ca8-5b04-8574-611c1abf292f", "name": "Title",
        "tag": GAME, "editor": (480, -240), "generator": "make_intro_scene.py",
    },
    "work_order": {
        "id": "6d76ca16-f510-5fd7-bb1c-c915a1367045", "name": "Lakeside Town",
        "tag": GAME, "editor": (720, -240), "generator": "make_ticket_scene.py",
    },
    "storm_report": {
        "id": "87eb95ce-7a29-5e5f-a362-e92762f6cb26", "name": "Storm Report",
        "tag": GAME, "editor": (960, -240), "generator": "make_ticket_scene.py",
    },
    "service_opening": {
        "id": "8524d1f9-7d48-5747-9f1b-4392d56fdf02", "name": "Service Opening - M-V1",
        "tag": GAME, "editor": (0, 360), "generator": "make_opening_scene.py",
    },
    "storm_climb": {
        "id": "e8778f37-44a7-5d3a-ad39-49d52fe4c5c7", "name": "Storm Climb",
        "tag": GAME, "editor": (0, 0), "generator": "make_climb_scene.py",
    },
    "wind_ridge": {
        "id": "20ae4686-7e62-5a4d-b3ab-0fddf0ad0d19", "name": "Wind Ridge",
        "tag": GAME, "editor": (400, 360), "generator": "make_ridge_scene.py",
    },
    "signal_hill": {
        "id": "7c856987-bbdf-5d75-a97e-327259a90956", "name": "Signal Hill",
        "tag": GAME, "editor": (800, 360), "generator": "make_rosa_scene.py",
    },
    "pine_hollow": {
        "id": "4d9329db-9c79-52dd-8372-d215a891bcb8", "name": "Pine Hollow",
        "tag": GAME, "editor": (1200, 360), "generator": "make_kiko_scene.py",
    },
    # Multi-scene redesign (planned; docs/LEVEL_REDESIGN.md). Editor positions from §7.
    "climb_crest": {
        "id": "1e6699bd-6450-5e78-ae39-e75a00c5d127", "name": "Climb Crest",
        "tag": GAME, "editor": (240, 0), "generator": "make_crest_scene.py", "planned": "WP1",
    },
    "ridge_saddle": {
        "id": "25260587-51f0-5445-ba85-4b6373ad58a8", "name": "Ridge Saddle",
        "tag": GAME, "editor": (400, 600), "generator": "make_ridge_scene.py", "planned": "WP2",
    },
    "signal_gully": {
        "id": "6714200c-748d-50ea-9ab8-f41beb918c15", "name": "Signal Gully",
        "tag": GAME, "editor": (800, 600), "generator": "make_gully_scene.py", "planned": "WP3",
    },
    "signal_porch": {
        "id": "915170c4-cfb7-50bf-a6ab-e68f626bd6fc", "name": "Signal Porch",
        "tag": GAME, "editor": (800, 960), "generator": "make_rosa_scene.py", "planned": "WP3",
    },
    "pine_ladder": {
        "id": "260e1781-da9f-5323-bc93-5ee7f73af3c7", "name": "Pine Ladder",
        "tag": GAME, "editor": (1200, 600), "generator": "make_ladder_scene.py", "planned": "WP4",
    },
    "pine_rim": {
        "id": "c25308db-8f10-5a6a-ada8-1fa748e4541f", "name": "Pine Rim",
        "tag": GAME, "editor": (1200, 960), "generator": "make_kiko_scene.py", "planned": "WP4",
    },
    "lab_hazard_gallery": {
        "id": _lab_id("lab_hazard_gallery"), "name": "LAB_Hazard Gallery",
        "tag": LAB, "editor": (0, 1200), "generator": "make_lab_scene.py",
    },
    "lab_movement_room": {
        "id": _lab_id("lab_movement_room"), "name": "LAB_Movement Room",
        "tag": LAB, "editor": (400, 1200), "generator": "make_lab_scene.py",
    },
    "storm_night": {
        "id": "5c63c0a8-2c82-5e99-b4fd-2da097e09bd4", "name": "Storm Night",
        "tag": LEGACY, "editor": (0, 2400), "generator": None,
    },
    "after_the_storm_-_village": {
        "id": "cfe-village-topdown-2026", "name": "After the Storm - Village",
        "tag": LEGACY, "editor": (400, 2400), "generator": None,
    },
}


def _check_tag(tag: str) -> None:
    if tag not in TAGS:
        raise ValueError(f"unknown scene tag {tag!r}; expected one of {TAGS}")


def by_tag(tag: str) -> dict[str, dict]:
    """Folder name -> registry entry for every scene with ``tag``."""
    _check_tag(tag)
    return {folder: entry for folder, entry in REGISTRY.items() if entry["tag"] == tag}


def ids(tag: str) -> list[str]:
    """Scene ids for every scene with ``tag``, in registry order."""
    return [entry["id"] for entry in by_tag(tag).values()]


def editor_position(folder: str) -> tuple[int, int]:
    """Editor (x, y) for a registered scene folder."""
    return REGISTRY[folder]["editor"]


def present(folder: str) -> bool:
    """True when the scene folder exists in project/scenes/ with a scene.gbsres."""
    return (SCENES_DIR / folder / "scene.gbsres").is_file()


def planned(folder: str) -> bool:
    """True for a scene registered ahead of its generator (see the module docstring)."""
    return bool(REGISTRY[folder].get("planned"))


def active(folder: str) -> bool:
    """A registered scene that is generated, or not planned (so it must be)."""
    return present(folder) or not planned(folder)


# The redesign's game scenes per job, entry scene first (docs/LEVEL_REDESIGN.md §2).
JOB_SCENES = {
    1: ("storm_climb", "climb_crest"),
    2: ("wind_ridge", "ridge_saddle"),
    3: ("signal_hill", "signal_gully", "signal_porch"),
    4: ("pine_hollow", "pine_ladder", "pine_rim"),
}
