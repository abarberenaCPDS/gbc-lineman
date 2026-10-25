"""Generate the deterministic Storm Climb scene from ``climb.py``.

Run with ``python3 tools/make_climb_scene.py`` from any working directory.
Resource and event IDs are stable; this generator writes only its own scene
resources. The authored climb data remains in the sibling ``climb.py`` module.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENE_DIR = PROJECT_DIR / "project" / "scenes" / "storm_climb"
REFERENCE_SCENE = PROJECT_DIR / "project" / "scenes" / "storm_night" / "scene.gbsres"
UUID_NAMESPACE = uuid.UUID("ae862b93-7877-5c2c-9a11-e71c74d4769f")
MAX_DIALOGUE_CHARS = 17
VARIABLE_CHECKPOINTS_REACHED = "0"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (sibling module owns all authored climb data)
except ModuleNotFoundError as error:
    if error.name == "climb":
        raise SystemExit(
            "cannot generate storm_climb: tools/climb.py is missing; "
            "it must provide the climb data API"
        ) from error
    raise


def resource_id(key: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, f"modretro-chromatic:mr-cfe:storm_climb:{key}"))


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def sidecar_id(relative_path: str, resource_type: str) -> str:
    path = PROJECT_DIR / relative_path
    data = load_json(path)
    if data.get("_resourceType") != resource_type:
        raise ValueError(f"{path} is not a {resource_type} resource")
    asset_id = data.get("id")
    if not isinstance(asset_id, str) or not asset_id:
        raise ValueError(f"{path} has no resource ID")
    return asset_id


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(data, indent=2) + "\n"
    if path.exists():
        current = load_json(path)
        if current.get("id") != data.get("id"):
            raise FileExistsError(f"refusing to overwrite an unowned resource: {path}")
        if path.read_text(encoding="utf-8") == contents:
            print(f"unchanged {path.relative_to(PROJECT_DIR)}")
            return
    path.write_text(contents, encoding="utf-8")
    print(f"wrote {path.relative_to(PROJECT_DIR)}")


def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": resource_id(f"event:{key}")}


def branch_event(
    command: str,
    args: dict[str, Any],
    key: str,
    true_events: list[dict[str, Any]],
    false_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        **event(command, args, key),
        "children": {"true": true_events, "false": false_events or []},
    }


def number(value: int) -> dict[str, Any]:
    return {"type": "number", "value": value}


def variable_value(variable_id: str) -> dict[str, Any]:
    return {"type": "variable", "value": variable_id}


def if_value(
    variable_id: str,
    value: int,
    key: str,
    true_events: list[dict[str, Any]],
    false_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return branch_event(
        "EVENT_IF",
        {
            "condition": {
                "type": "eq",
                "valueA": variable_value(variable_id),
                "valueB": number(value),
            }
        },
        key,
        true_events,
        false_events,
    )


def short_lines(*lines: str) -> list[str]:
    for line in lines:
        if any(len(part) > MAX_DIALOGUE_CHARS for part in line.split("\n")):
            raise ValueError(f"dialogue line exceeds {MAX_DIALOGUE_CHARS} chars: {line!r}")
    return list(lines)


def text_event(lines: list[str], key: str) -> dict[str, Any]:
    return event(
        "EVENT_TEXT",
        {
            "text": lines,
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
        },
        key,
    )


def cutoff_event(y: int, key: str) -> dict[str, Any]:
    return event(
        "EVENT_OVERLAY_SET_SCANLINE_CUTOFF",
        {"units": "pixels", "y": number(y)},
        key,
    )


def hud_events(key: str) -> list[dict[str, Any]]:
    return [
        cutoff_event(16, f"{key}:cutoff"),
        event("EVENT_OVERLAY_SHOW", {"color": "black", "x": 0, "y": 0}, f"{key}:show"),
        event(
            "EVENT_TEXT_DRAW",
            {"text": "CLIMBS %D1$0$ / 1", "x": 0, "y": 0, "location": "overlay"},
            f"{key}:counter",
        ),
    ]


def sound_event(sound_id: str, key: str) -> dict[str, Any]:
    return event(
        "EVENT_SOUND_PLAY_EFFECT",
        {
            "units": "time",
            "type": sound_id,
            "priority": "high",
            "pitch": 4,
            "frequency": 200,
            "duration": 0.5,
            "wait": True,
            "effect": 0,
        },
        key,
    )


def set_value(variable_id: str, value: int, key: str) -> dict[str, Any]:
    return event("EVENT_SET_VALUE", {"variable": variable_id, "value": number(value)}, key)


def set_position(x: int, y: int, key: str) -> dict[str, Any]:
    return event(
        "EVENT_ACTOR_SET_POSITION",
        {"units": "tiles", "actorId": "player", "x": number(x), "y": number(y)},
        key,
    )


def collision_rle(grid: list[list[int]], width: int, height: int) -> str:
    if len(grid) != height or any(len(row) != width for row in grid):
        raise ValueError(f"climb collision grid must be {width}x{height}")
    values = [int(cell) for row in grid for cell in row]
    out: list[str] = []
    last: int | None = None
    count = 0
    for value in values:
        if value < 0 or value > 255:
            raise ValueError(f"collision value outside byte range: {value}")
        if value != last:
            if last is not None:
                out.append("!" if count == 1 else f"{count:x}+")
            out.append(f"{value:02x}")
            last, count = value, 1
        else:
            count += 1
    if last is not None:
        out.append("!" if count == 1 else f"{count:x}+")
    return "".join(out)


def scene_script(music_id: str) -> list[dict[str, Any]]:
    return [
        set_value(VARIABLE_CHECKPOINTS_REACHED, 0, "init-checkpoints-reached"),
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-village-music"),
        text_event(short_lines("A: jump\nDown+A: drop"), "intro-controls"),
        *hud_events("initial-hud"),
    ]


def actor_resource(
    *,
    index: int,
    symbol: str,
    name: str,
    x: int,
    y: int,
    sprite_id: str,
    key: str,
    script: list[dict[str, Any]] | None = None,
    start_script: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "_resourceType": "actor",
        "id": resource_id(f"actor:{key}"),
        "_index": index,
        "symbol": symbol,
        "prefabId": "",
        "name": name,
        "coordinateType": "tiles",
        "x": x,
        "y": y,
        "frame": 0,
        "animate": False,
        "spriteSheetId": sprite_id,
        "paletteId": "",
        "direction": "down",
        "moveSpeed": 1,
        "animSpeed": 15,
        "isPinned": False,
        "persistent": False,
        "collisionGroup": "",
        "collisionExtraFlags": [],
        "prefabScriptOverrides": {},
        "script": script or [],
        "startScript": start_script or [],
        "updateScript": [],
        "hit1Script": [],
        "hit2Script": [],
        "hit3Script": [],
    }


def checkpoint_actor(index: int, houses_sprite_id: str, place_sound_id: str) -> dict[str, Any]:
    house = climb.HOUSE_A
    key = "marta-checkpoint"
    activated = [
        set_value(VARIABLE_CHECKPOINTS_REACHED, 1, f"{key}:set-reached"),
        sound_event(place_sound_id, f"{key}:place-sfx"),
        cutoff_event(150, f"{key}:dialogue-cutoff"),
        text_event(short_lines("Marta's home!"), f"{key}:dialogue"),
        *hud_events(f"{key}:hud"),
    ]
    return actor_resource(
        index=index,
        symbol="marta_checkpoint",
        name="Marta's Home Checkpoint",
        x=int(house["x"]),
        y=int(house["y"]),
        sprite_id=houses_sprite_id,
        key=key,
        script=[],
        start_script=[
            event(
                "EVENT_ACTOR_SET_STATE",
                {"actorId": "$self$", "spriteStateId": "Marta", "loopAnim": True},
                f"{key}:set-marta-state",
            )
        ],
    )


def debris_actor(index: int, debris: dict[str, Any], sprite_id: str) -> dict[str, Any]:
    row_top = int(debris["row_top"])
    x = int(debris["x"])
    row_bottom = int(debris["row_bottom"])
    if row_bottom < row_top:
        raise ValueError(f"debris {index} has row_bottom above row_top")
    # The reference scene exposes no wait or actor-move command. Preserve the
    # known actor schema and hazard sprite rather than emitting unverified GBVM
    # events; the cycle/movement needs a follow-up using verified commands.
    start_script = [
        event(
            "EVENT_ACTOR_SET_STATE",
            {"actorId": "$self$", "spriteStateId": "floodwater", "loopAnim": True},
            f"debris:{index}:set-state",
        ),
        event("EVENT_ACTOR_SHOW", {"actorId": "$self$"}, f"debris:{index}:show"),
    ]
    return actor_resource(
        index=index,
        symbol=f"debris_{index:02d}",
        name=f"Falling Debris {index}",
        x=x,
        y=row_top,
        sprite_id=sprite_id,
        key=f"debris:{index}",
        start_script=start_script,
    )


def trigger_resource(index: int, lane: tuple[int, int, int], death_sound_id: str) -> dict[str, Any]:
    row, x_start, x_end = (int(value) for value in lane)
    if x_end < x_start:
        raise ValueError(f"gust lane {index} has reversed x bounds")
    key = f"gust-lane:{index}"
    start = climb.START
    house = climb.HOUSE_A
    respawn = if_value(
        VARIABLE_CHECKPOINTS_REACHED,
        0,
        f"{key}:respawn-start-check",
        [set_position(int(start[0]), int(start[1]), f"{key}:respawn-start")],
        [set_position(int(house["x"]), int(house["y"]), f"{key}:respawn-house-a")],
    )
    # Storm Night trigger coordinates and dimensions are tile-based in the
    # native resource schema, so retain that representation here.
    return {
        "_resourceType": "trigger",
        "id": resource_id(f"trigger:{key}"),
        "name": f"Gust Lane {index}",
        "prefabId": "",
        "x": x_start,
        "y": row,
        "symbol": f"trigger_gust_lane_{index:02d}",
        "prefabScriptOverrides": {},
        "width": x_end - x_start + 1,
        "height": 1,
        "script": [sound_event(death_sound_id, f"{key}:death-sfx"), respawn],
        "leaveScript": [],
        "_index": index - 1,
    }


def build_scene(music_id: str) -> dict[str, Any]:
    if int(climb.MAP_W) != 20 or int(climb.MAP_H) != 36:
        raise ValueError("storm_climb must match the Storm Night 20x36 scene schema")
    scene = load_json(REFERENCE_SCENE)
    scene.update(
        {
            "id": resource_id("scene:storm-climb"),
            "_index": 0,
            "name": "Storm Climb",
            "width": int(climb.MAP_W),
            "height": int(climb.MAP_H),
            "collisions": collision_rle(climb.collision_grid(), int(climb.MAP_W), int(climb.MAP_H)),
            "symbol": "scene_storm_climb",
            "backgroundId": resource_id("background:storm-climb"),
            "script": scene_script(music_id),
        }
    )
    return scene


def main() -> None:
    music_id = sidecar_id("assets/music/cfe_village_1.uge.gbsres", "music")
    sprite_ids = {
        "hazard": sidecar_id("assets/sprites/hazard.png.gbsres", "sprite"),
        "houses": sidecar_id("assets/sprites/houses.png.gbsres", "sprite"),
    }
    audio_ids = {
        "death": sidecar_id("assets/sounds/death.wav.gbsres", "sound"),
        "place": sidecar_id("assets/sounds/place.wav.gbsres", "sound"),
    }

    scene = build_scene(music_id)
    actors = [checkpoint_actor(0, sprite_ids["houses"], audio_ids["place"])]
    triggers = [
        trigger_resource(index, lane, audio_ids["death"])
        for index, lane in enumerate(climb.GUST_LANES, start=1)
    ]
    checkpoint = trigger_resource(100, (climb.HOUSE_A["y"], climb.HOUSE_A["x"], climb.HOUSE_A["x"] + 1), audio_ids["death"])
    checkpoint.update({
        "name": "Marta Arrival Checkpoint",
        "symbol": "trigger_marta_arrival",
        "script": [if_value(VARIABLE_CHECKPOINTS_REACHED, 0, "checkpoint-arrival", [
            set_value(VARIABLE_CHECKPOINTS_REACHED, 1, "checkpoint-arrival:set"),
            sound_event(audio_ids["place"], "checkpoint-arrival:sfx"),
            cutoff_event(150, "checkpoint-arrival:cutoff"),
            text_event(short_lines("Marta's home!"), "checkpoint-arrival:text"),
            *hud_events("checkpoint-arrival:hud"),
        ])],
    })
    triggers.append(checkpoint)

    write_json(SCENE_DIR / "scene.gbsres", scene)
    for actor in actors:
        write_json(SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres", actor)
    for trigger in triggers:
        write_json(SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres", trigger)
    print(
        f"generated storm_climb: {climb.MAP_W}x{climb.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} gust triggers; "
        "movement prototype; timed debris/wind pending"
    )


if __name__ == "__main__":
    main()
