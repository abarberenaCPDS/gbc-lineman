"""Generate the work-order and storm-report scenes from ``tickets.py``.

Run with ``"$PY" tools/make_ticket_scene.py`` from any working directory, where PY
is the managed toolchain Python. This writes ``project/scenes/work_order/scene.gbsres``,
``project/scenes/storm_report/scene.gbsres`` and registers variable 16 in
``project/variables.gbsres`` without changing existing variables.

Authored pages, destinations, start tiles and stable IDs live in the sibling
``tickets.py`` contract module; this file only turns them into GB Studio events.
Card art comes from ``make_ticket_art.py``; this generator only references its
background ID and warns when that sidecar is not on disk yet.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENES_DIR = PROJECT_DIR / "project" / "scenes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"
VICTORY_SOUND = "assets/sounds/victory.wav.gbsres"
DEFAULT_SPRITE_PALETTE = "default-sprite"
FADE_SPEED = "2"
EMPTY_ROW = [0] * 20

sys.path.insert(0, str(TOOLS_DIR))
try:
    import intro  # noqa: E402  (palette names, title scene, hero sprite)
    import ending  # noqa: E402  (resolved reprise music contract)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import tickets  # noqa: E402  (sole source of truth for this scene set)
    import voices  # noqa: E402  (narrator blip)
except ModuleNotFoundError as error:
    if error.name in {"intro", "ending", "make_climb_scene", "tickets", "voices", "climb", "opening",
                      "ridge", "kiko", "rosa"}:
        raise SystemExit(
            f"cannot generate the ticket scenes: tools/{error.name}.py is missing"
        ) from error
    raise


# ---------------------------------------------------------------------------
# Background palette slots
# ---------------------------------------------------------------------------
def background_palette_ids() -> list[str]:
    """Card-art slots from make_ticket_art.py when it exists, else the intro story slots."""
    if importlib.util.find_spec("make_ticket_art") is not None:
        art = importlib.import_module("make_ticket_art")
        ids = getattr(art, "BACKGROUND_PALETTE_IDS", None)
        if ids is not None:
            if len(ids) != 8:
                raise ValueError("make_ticket_art.BACKGROUND_PALETTE_IDS must have 8 entries")
            return list(ids)
    return [intro.palette_id(name) for name in intro.STORY_SLOTS]


def sprite_palette_ids() -> list[str]:
    ids = [DEFAULT_SPRITE_PALETTE] * 8
    for name, slot in intro.SPRITE_SLOTS.items():
        ids[slot] = intro.palette_id(name)
    return ids


# ---------------------------------------------------------------------------
# Event builders. Event IDs come from tickets.resource_id("event:<key>").
# ---------------------------------------------------------------------------
def ev(command: str, args: dict[str, Any], key: str,
       children: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"command": command, "args": args,
                            "id": tickets.resource_id(f"event:{key}")}
    if children is not None:
        node["children"] = children
    return node


def num(value: int) -> dict[str, Any]:
    return shared.number(value)


def if_value(variable: str, value: int, key: str, yes: list[dict[str, Any]],
             no: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return ev("EVENT_IF", {"condition": {
        "type": "eq", "valueA": {"type": "variable", "value": variable}, "valueB": num(value),
    }}, key, children={"true": yes, "false": no or []})


def hide_player(key: str) -> dict[str, Any]:
    return ev("EVENT_ACTOR_HIDE", {"actorId": "player"}, key)


def overlay_hide(key: str) -> dict[str, Any]:
    return ev("EVENT_OVERLAY_HIDE", {}, key)


def text_sound(key: str) -> dict[str, Any]:
    return ev("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(None), key)


def fade_out(key: str) -> dict[str, Any]:
    return ev("EVENT_FADE_OUT", {"speed": FADE_SPEED}, key)


def switch_scene(scene_id: str, x: int, y: int, direction: str, key: str) -> dict[str, Any]:
    return ev("EVENT_SWITCH_SCENE", {
        "sceneId": scene_id, "x": num(x), "y": num(y),
        "direction": direction, "fadeSpeed": FADE_SPEED,
    }, key)


def dialogue(pages: list[str], key: str) -> dict[str, Any]:
    """Bottom dialogue box over the card art; every page in one box, closed by A."""
    return ev("EVENT_TEXT", {
        "text": list(pages),
        "avatarId": "",
        "minHeight": 4,
        "maxHeight": 7,
        "textX": 1,
        "textY": 1,
        "textHeight": 5,
        "position": "bottom",
        "clearPrevious": True,
        "showFrame": True,
        "speedIn": -1,
        "speedOut": -1,
        "closeWhen": "key",
        "closeButton": "a",
        "closeDelayUnits": "time",
        "closeDelayTime": 0.5,
        "closeDelayFrames": 30,
    }, key)


def victory_sound(sound_id: str, key: str) -> dict[str, Any]:
    return ev("EVENT_SOUND_PLAY_EFFECT", {
        "units": "time", "type": sound_id, "priority": "high", "pitch": 4,
        "frequency": 200, "duration": 0.5, "wait": True, "effect": 0,
    }, key)


# ---------------------------------------------------------------------------
# Scene scripts
# ---------------------------------------------------------------------------
def setup(key: str) -> list[dict[str, Any]]:
    """Hide the hero and any HUD left by the previous scene; set the narrator blip."""
    return [
        hide_player(f"{key}:hide-player"),
        overlay_hide(f"{key}:hide-overlay"),
        text_sound(f"{key}:narrator"),
    ]


def ticket_exit(number: int) -> list[dict[str, Any]]:
    """Dispatch card for one ticket, then the job's start tile, facing right."""
    ticket = tickets.TICKETS[number]
    key = f"work-order:ticket{number}"
    x, y = ticket["start"]
    return [
        dialogue(ticket["pages"], f"{key}:card"),
        fade_out(f"{key}:fade"),
        switch_scene(ticket["scene_id"], x, y, "right", f"{key}:to-job"),
    ]


def work_order_script() -> list[dict[str, Any]]:
    # Tickets 2-4 branch on the variable; anything else (1, or never set) is
    # ticket 1, so a test ROM that starts here shows Amara's card.
    branches: list[dict[str, Any]] = ticket_exit(1)
    for number in reversed(range(2, tickets.LAST_TICKET + 1)):
        branches = [if_value(tickets.VAR_TICKET, number, f"work-order:ticket{number}",
                             ticket_exit(number), branches)]
    return [*setup("work-order"), *branches]


def storm_report_script() -> list[dict[str, Any]]:
    return [
        *setup("storm-report"),
        dialogue(tickets.REPORT_PAGES, "storm-report:pages"),
        victory_sound(shared.sidecar_id(VICTORY_SOUND, "sound"), "storm-report:victory"),
        overlay_hide("storm-report:hide-overlay-exit"),
        fade_out("storm-report:fade"),
        # The short resolved reprise carries into the silent title; its idle
        # replay enters the story, which explicitly restarts the normal Intro B.
        ev("EVENT_MUSIC_PLAY", {"musicId": ending.MUSIC_ID},
           "storm-report:ending-reprise"),
        switch_scene(tickets.TITLE_SCENE_ID, 0, 0, "right", "storm-report:to-title"),
    ]


# ---------------------------------------------------------------------------
# Scenes and variables
# ---------------------------------------------------------------------------
def scene_resource(scene_id: str, folder: str, name: str, index: int, x: int, y: int,
                   script: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_resourceType": "scene",
        "id": scene_id,
        "_index": index,
        "name": name,
        "symbol": "scene_" + folder,
        "backgroundId": tickets.BACKGROUND_ID,
        "tilesetId": "",
        "width": tickets.MAP_W,
        "height": tickets.MAP_H,
        "type": "TOPDOWN",
        "colorModeOverride": "none",
        "paletteIds": background_palette_ids(),
        "spritePaletteIds": sprite_palette_ids(),
        "collisions": shared.collision_rle(
            [list(EMPTY_ROW) for _ in range(tickets.MAP_H)], tickets.MAP_W, tickets.MAP_H),
        "autoFadeSpeed": 1,
        "x": x,
        "y": y,
        "script": script,
        "playerHit1Script": [],
        "playerHit2Script": [],
        "playerHit3Script": [],
        "playerSpriteSheetId": intro.HERO_SPRITE_ID,
    }


def build_scenes() -> dict[str, dict[str, Any]]:
    """folder -> scene resource. Scripts are built fresh each call."""
    scripts = {
        tickets.WORK_ORDER_SCENE_ID: work_order_script(),
        tickets.REPORT_SCENE_ID: storm_report_script(),
    }
    built: dict[str, dict[str, Any]] = {}
    for index, (scene_id, folder, name, _stem, x, y) in enumerate(tickets.SCENES):
        built[folder] = scene_resource(scene_id, folder, name, index, x, y, scripts[scene_id])
    import make_dispatch_hub
    built["work_order"] = make_dispatch_hub.build_scene()
    return built


def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the ticket variables without changing any existing entry."""
    merged = json.loads(json.dumps(data))
    for key, name, symbol in tickets.VARIABLES:
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in merged["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            merged["variables"].append(value)
    return merged


def write_variables() -> None:
    data = shared.load_json(VARIABLES_PATH)
    merged = merged_variables(data)
    contents = json.dumps(merged, indent=2) + "\n"
    if VARIABLES_PATH.read_text(encoding="utf-8") != contents:
        VARIABLES_PATH.write_text(contents, encoding="utf-8")
        print("registered work-order variables without changing existing variables")


# ---------------------------------------------------------------------------
# Checks and writing
# ---------------------------------------------------------------------------
def check_text() -> None:
    """Every dialogue page: at most 3 lines, each at most tickets.MAX_CHARS."""
    pages = [*tickets.REPORT_PAGES]
    for ticket in tickets.TICKETS.values():
        pages.extend(ticket["pages"])
    for page in pages:
        lines = page.split("\n")
        if len(lines) > 3:
            raise ValueError(f"dialogue page over 3 lines: {page!r}")
        for line in lines:
            if len(line) > tickets.MAX_CHARS:
                raise ValueError(f"dialogue line over {tickets.MAX_CHARS} chars: {line!r}")


def walk(events: list[dict[str, Any]]):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def check_unique_ids(resources: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for resource in resources:
        identifiers = [resource["id"], *(entry["id"] for entry in walk(resource["script"]))]
        for identifier in identifiers:
            if identifier in seen:
                raise ValueError(f"duplicate resource or event id {identifier}")
            seen.add(identifier)


def warn_missing_art() -> None:
    """make_ticket_art.py writes the card sidecar; this generator only references its ID."""
    for path in sorted((PROJECT_DIR / "assets" / "backgrounds").glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == tickets.BACKGROUND_ID:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no ticket card background sidecar with id {tickets.BACKGROUND_ID} "
          "under assets/backgrounds/ yet")


def main() -> None:
    check_text()
    built = build_scenes()
    check_unique_ids(list(built.values()))
    warn_missing_art()
    for folder, scene in built.items():
        shared.write_json(SCENES_DIR / folder / "scene.gbsres", scene)
    write_variables()
    import make_dispatch_hub
    make_dispatch_hub.write_production()
    print(f"generated {len(built)} ticket scenes")


if __name__ == "__main__":
    main()
