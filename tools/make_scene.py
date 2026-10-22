"""Create the deterministic GB Studio scene scaffold from ``level.py``.

Run with ``python3 tools/make_scene.py`` from any working directory. Resource
IDs are stable, so rerunning this script updates only the resources it owns.
"""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENE_DIR_NAME = "storm_night"
UUID_NAMESPACE = uuid.UUID("717f5b5a-4e17-5f80-ae10-6afbdd2827db")
MAX_DIALOGUE_CHARS = 17
STORM_SECONDS = 90

VARIABLES = {
    "connected": ("Connected Houses", "var_connected_houses"),
    "game_state": ("Game State", "var_game_state"),
    "storm_seconds": ("Storm Seconds", "var_storm_seconds"),
}

sys.path.insert(0, str(TOOLS_DIR))
import level  # noqa: E402  (the sibling module is the authoritative source)


def resource_id(name: str) -> str:
    return str(uuid.uuid5(UUID_NAMESPACE, f"modretro-chromatic:mr-cfe:{name}"))


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        data = json.load(source)
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    contents = json.dumps(data, indent=2) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == contents:
        return
    path.write_text(contents, encoding="utf-8")


def remove_owned_resource(path: Path, expected_id: str) -> None:
    if not path.exists():
        return
    data = load_json(path)
    if data.get("id") != expected_id:
        raise FileExistsError(f"refusing to remove unowned resource {path}")
    path.unlink()


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    display_kind = "BG" if kind == "bg" else "Sprite"
    display_name = f"Storm Night {display_kind} {name.title()}"
    return {
        "_resourceType": "palette",
        "id": resource_id(f"palette:{kind}:{name}"),
        "name": display_name,
        "colors": colors,
        "defaultName": display_name,
        "defaultColors": colors,
    }


def build_palettes() -> tuple[list[str], list[str], list[tuple[str, dict[str, Any]]]]:
    background_ids: list[str] = []
    sprite_ids: list[str] = []
    resources: list[tuple[str, dict[str, Any]]] = []
    for name, colors in level.BG_PALETTES:
        palette = palette_resource("bg", name, list(colors))
        background_ids.append(palette["id"])
        resources.append((f"storm_night_bg_{name}.gbsres", palette))
    for name, colors in level.SPRITE_PALETTES:
        palette = palette_resource("sprite", name, list(colors))
        sprite_ids.append(palette["id"])
        resources.append((f"storm_night_sprite_{name}.gbsres", palette))
    if len(background_ids) != 7 or len(sprite_ids) != 7:
        raise ValueError("expected exactly 7 custom background and sprite palettes")
    return background_ids, sprite_ids, resources


def short_lines(*lines: str) -> list[str]:
    for line in lines:
        if any(len(part) > MAX_DIALOGUE_CHARS for part in line.split("\n")):
            raise ValueError(f"dialogue line exceeds {MAX_DIALOGUE_CHARS} chars: {line!r}")
    return list(lines)


def sidecar_id(relative_path: str, resource_type: str) -> str:
    path = PROJECT_DIR / relative_path
    data = load_json(path)
    if data.get("_resourceType") != resource_type:
        raise ValueError(f"{path} is not a {resource_type} resource")
    asset_id = data.get("id")
    if not isinstance(asset_id, str) or not asset_id:
        raise ValueError(f"{path} has no resource ID")
    return asset_id


def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": resource_id(key)}


def branch_event(
    command: str,
    args: dict[str, Any],
    key: str,
    children: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    result = event(command, args, key)
    result["children"] = children
    return result


def number(value: int) -> dict[str, Any]:
    return {"type": "number", "value": value}


def variable_value(variable_id: str) -> dict[str, Any]:
    return {"type": "variable", "value": variable_id}


def comparison(operator: str, variable_id: str, value: int) -> dict[str, Any]:
    return {
        "type": operator,
        "valueA": variable_value(variable_id),
        "valueB": number(value),
    }


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


def storm_counter_event(storm_seconds: str, key: str) -> dict[str, Any]:
    return event(
        "EVENT_TEXT_DRAW",
        {
            "text": f"STORM %D2${storm_seconds.zfill(2)}$",
            "x": 0,
            "y": 0,
            "location": "overlay",
        },
        key,
    )


def overlay_cutoff_event(y: int, key: str) -> dict[str, Any]:
    return event(
        "EVENT_OVERLAY_SET_SCANLINE_CUTOFF",
        {"units": "pixels", "y": number(y)},
        key,
    )


def show_hud_events(storm_seconds: str, key: str) -> list[dict[str, Any]]:
    return [
        overlay_cutoff_event(16, f"{key}:cutoff"),
        event(
            "EVENT_OVERLAY_SHOW",
            {"color": "black", "x": 0, "y": 0},
            f"{key}:overlay",
        ),
        storm_counter_event(storm_seconds, f"{key}:counter"),
    ]


def dialogue_with_hud_events(
    lines: list[str], storm_seconds: str, key: str
) -> list[dict[str, Any]]:
    return [
        overlay_cutoff_event(150, f"{key}:full-overlay"),
        text_event(lines, key),
        *show_hud_events(storm_seconds, f"{key}:restore-hud"),
    ]


def sound_event(sound_id: str, key: str, priority: str = "high") -> dict[str, Any]:
    return event(
        "EVENT_SOUND_PLAY_EFFECT",
        {
            "units": "time",
            "type": sound_id,
            "priority": priority,
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


def if_value(
    variable_id: str,
    operator: str,
    value: int,
    key: str,
    true_events: list[dict[str, Any]],
    false_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return branch_event(
        "EVENT_IF",
        {"condition": comparison(operator, variable_id, value)},
        key,
        {"true": true_events, "false": false_events or []},
    )


def update_variables() -> dict[str, str]:
    path = PROJECT_DIR / "project" / "variables.gbsres"
    data = load_json(path)
    variables = data.setdefault("variables", [])
    if not isinstance(variables, list):
        raise ValueError(f"{path} has malformed variables")

    by_symbol = {
        item.get("symbol"): item
        for item in variables
        if isinstance(item, dict) and isinstance(item.get("symbol"), str)
    }
    used_ids = {
        str(item.get("id"))
        for item in variables
        if isinstance(item, dict) and item.get("id") is not None
    }
    resolved: dict[str, str] = {}
    for name, (display_name, symbol) in VARIABLES.items():
        existing = by_symbol.get(symbol)
        if existing:
            variable_id = str(existing.get("id", ""))
            if not variable_id.isdigit() or not 0 <= int(variable_id) <= 511:
                raise ValueError(f"{path}: {symbol} must use a global variable ID 0..511")
        else:
            variable_id = next(
                (str(index) for index in range(512) if str(index) not in used_ids),
                "",
            )
            if not variable_id:
                raise ValueError(f"{path}: no unused global variable IDs remain")
            variables.append({"id": variable_id, "name": display_name, "symbol": symbol})
            used_ids.add(variable_id)
        resolved[name] = variable_id

    write_json(path, data)
    return resolved


def play_house_script(
    *,
    index: int,
    variable_ids: dict[str, str],
    audio_ids: dict[str, str],
    cable_actor_ids: list[str],
    key: str,
) -> list[dict[str, Any]]:
    connected = variable_ids["connected"]
    game_state = variable_ids["game_state"]
    house_name = str(level.HOUSES[index]["name"])
    connect_events: list[dict[str, Any]] = [
        event("EVENT_INC_VALUE", {"variable": connected}, f"{key}:connect-count"),
        *set_actor_state(f"{house_name} Powered", f"{key}:powered"),
        *[
            event(
                "EVENT_ACTOR_SHOW",
                {"actorId": actor_id},
                f"{key}:show-cable:{segment_index + 1}",
            )
            for segment_index, actor_id in enumerate(cable_actor_ids)
        ],
    ]
    if index == len(level.HOUSES) - 1:
        connect_events.extend(
            [
                set_value(game_state, 1, f"{key}:win-state"),
                event("EVENT_TIMER_DISABLE", {"timer": 1}, f"{key}:stop-storm"),
                sound_event(audio_ids["victory"], f"{key}:victory-sfx"),
                event(
                    "EVENT_MUSIC_PLAY",
                    {"musicId": audio_ids["win_music"]},
                    f"{key}:win-music",
                ),
                *dialogue_with_hud_events(
                    short_lines("Grid restored!\nStorm beaten!"),
                    variable_ids["storm_seconds"],
                    f"{key}:win-text",
                ),
            ]
        )
    else:
        connect_events.append(sound_event(audio_ids["connect"], f"{key}:connect-sfx"))

    cut_events = [
        event("EVENT_DEC_VALUE", {"variable": connected}, f"{key}:cut-count"),
        *set_actor_state(house_name, f"{key}:unpowered"),
        *[
            event(
                "EVENT_ACTOR_HIDE",
                {"actorId": actor_id},
                f"{key}:hide-cable:{segment_index + 1}",
            )
            for segment_index, actor_id in enumerate(cable_actor_ids)
        ],
        sound_event(audio_ids["cut"], f"{key}:cut-sfx"),
    ]
    lower_house = dialogue_with_hud_events(
        short_lines("Link homes below."),
        variable_ids["storm_seconds"],
        f"{key}:lower-first",
    )
    cut_top = dialogue_with_hud_events(
        short_lines("Cut the top wire."),
        variable_ids["storm_seconds"],
        f"{key}:cut-top",
    )
    invalid = [
        if_value(
            connected,
            "lt",
            index,
            f"{key}:needs-lower-house",
            lower_house,
            cut_top,
        )
    ]
    connection_choice = if_value(
        connected,
        "eq",
        index + 1,
        f"{key}:cut-or-invalid",
        cut_events,
        invalid,
    )
    connect_or_not = if_value(
        connected,
        "eq",
        index,
        f"{key}:connect-or-cut",
        connect_events,
        [connection_choice],
    )
    return [
        if_value(
            game_state,
            "eq",
            0,
            f"{key}:only-while-playing",
            [connect_or_not],
        )
    ]


def scene_runtime_script(
    variable_ids: dict[str, str], audio_ids: dict[str, str]
) -> list[dict[str, Any]]:
    connected = variable_ids["connected"]
    game_state = variable_ids["game_state"]
    storm_seconds = variable_ids["storm_seconds"]
    timer_tick = [
        if_value(
            game_state,
            "eq",
            0,
            "storm-tick-playing",
            [
                event("EVENT_DEC_VALUE", {"variable": storm_seconds}, "storm-countdown"),
                storm_counter_event(storm_seconds, "draw-storm-countdown"),
                if_value(
                    storm_seconds,
                    "lte",
                    0,
                    "storm-expired",
                    [
                        set_value(game_state, 2, "storm-lose-state"),
                        event("EVENT_TIMER_DISABLE", {"timer": 1}, "storm-stop-timer"),
                        event(
                            "EVENT_MUSIC_PLAY",
                            {"musicId": audio_ids["lose_music"]},
                            "storm-lose-music",
                        ),
                        *dialogue_with_hud_events(
                            short_lines("The storm wins.\nTry again."),
                            storm_seconds,
                            "storm-lose-text",
                        ),
                    ],
                ),
            ],
        )
    ]
    return [
        set_value(connected, 0, "init-connected-houses"),
        set_value(game_state, 0, "init-game-state"),
        set_value(storm_seconds, STORM_SECONDS, "init-storm-seconds"),
        event(
            "EVENT_MUSIC_PLAY",
            {"musicId": audio_ids["intro_music"]},
            "play-intro-music",
        ),
        text_event(short_lines("B links or cuts.\nLink five. Hurry!"), "intro-controls"),
        event(
            "EVENT_MUSIC_PLAY",
            {"musicId": audio_ids["main_music"]},
            "play-main-music",
        ),
        *show_hud_events(storm_seconds, "show-initial-hud"),
        branch_event(
            "EVENT_SET_INPUT_SCRIPT",
            {"input": ["a"], "override": False},
            "attach-jump-sound",
            {"true": [sound_event(audio_ids["jump"], "jump-sfx", "low")]},
        ),
        branch_event(
            "EVENT_SET_TIMER_SCRIPT",
            {"units": "frames", "timer": 1, "duration": 1, "frames": 60},
            "start-storm-timer",
            {"script": timer_tick},
        ),
    ]


def set_actor_state(state: str, key: str) -> list[dict[str, Any]]:
    return [
        event(
            "EVENT_ACTOR_SET_STATE",
            {"actorId": "$self$", "spriteStateId": state, "loopAnim": True},
            f"{key}:set-state",
        )
    ]


def actor(
    *,
    index: int,
    symbol: str,
    name: str,
    x: int,
    y: int,
    sprite_id: str,
    key: str,
    state: str | None = None,
    dialogue: list[str] | None = None,
    script_events: list[dict[str, Any]] | None = None,
    storm_seconds_id: str | None = None,
    hide_on_start: bool = False,
) -> dict[str, Any]:
    if script_events is not None:
        actor_script = script_events
    elif dialogue:
        if storm_seconds_id is None:
            raise ValueError(f"{key}: dialogue needs the storm counter variable ID")
        actor_script = dialogue_with_hud_events(
            dialogue,
            storm_seconds_id,
            f"{key}:dialogue",
        )
    else:
        actor_script = []
    start_script = set_actor_state(state, key) if state else []
    if hide_on_start:
        start_script.append(
            event(
                "EVENT_ACTOR_HIDE",
                {"actorId": "$self$"},
                f"{key}:hide-on-start",
            )
        )
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
        "script": actor_script,
        "startScript": start_script,
        "updateScript": [],
        "hit1Script": [],
        "hit2Script": [],
        "hit3Script": [],
    }


def trigger(
    *,
    index: int,
    x: int,
    y: int,
    width: int,
    height: int,
    label: str,
    script_events: list[dict[str, Any]],
) -> dict[str, Any]:
    key = f"hazard-trigger:{label}"
    return {
        "_resourceType": "trigger",
        "id": resource_id(key),
        "name": label.replace("_", " ").title(),
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": f"trigger_{label}",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": script_events,
        "leaveScript": [],
        "_index": index,
    }


def build_scene(
    background_id: str,
    sprite_ids: dict[str, str],
    background_palette_ids: list[str],
    sprite_palette_ids: list[str],
    variable_ids: dict[str, str],
    audio_ids: dict[str, str],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    scene_id = resource_id("scene:storm_night")
    # Hardware slots 0..6 are project palettes; slot 7 remains UI / emote.
    background_palette_ids = [*background_palette_ids, "default-ui"]
    sprite_palette_ids = [*sprite_palette_ids, "default-sprite"]
    scene = {
        "_resourceType": "scene",
        "id": scene_id,
        "_index": 0,
        "name": "Storm Night",
        "backgroundId": background_id,
        "tilesetId": "",
        "width": level.MAP_W,
        "height": level.MAP_H,
        "type": "PLATFORM",
        "colorModeOverride": "none",
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "collisions": level.collisions_rle(),
        "autoFadeSpeed": 1,
        "symbol": "scene_storm_night",
        "x": 0,
        "y": 0,
        "script": scene_runtime_script(variable_ids, audio_ids),
        "playerHit1Script": [],
        "playerHit2Script": [],
        "playerHit3Script": [],
    }

    actors: list[dict[str, Any]] = []
    for house_index, house in enumerate(level.HOUSES):
        name = str(house["name"])
        house_id = str(house["id"])
        cable_actor_ids = [
            resource_id(f"actor:cable:{house_id}:{segment_number}")
            for segment_number in (1, 2)
        ]
        actors.append(
            actor(
                index=len(actors),
                symbol=house_id,
                name=f"{name}'s House",
                x=int(house["x"]),
                y=int(house["row"]),
                sprite_id=sprite_ids["houses"],
                key=house_id,
                state=name,
                script_events=play_house_script(
                    index=house_index,
                    variable_ids=variable_ids,
                    audio_ids=audio_ids,
                    cable_actor_ids=cable_actor_ids,
                    key=house_id,
                ),
            )
        )
        for segment_number, cable_actor_id in enumerate(cable_actor_ids, start=1):
            actors.append(
                actor(
                    index=len(actors),
                    symbol=f"cable_{house_id}_{segment_number}",
                    name=f"{name}'s Cable {segment_number}",
                    x=int(house["x"]),
                    y=int(house["platform"]) + segment_number + 1,
                    sprite_id=sprite_ids["cable"],
                    key=f"cable:{house_id}:{segment_number}",
                    state="span",
                    hide_on_start=True,
                )
            )

    for npc in level.NPCS:
        name = str(npc["name"])
        actors.append(
            actor(
                index=len(actors),
                symbol=str(npc["id"]),
                name=name,
                x=int(npc["x"]),
                y=int(npc["row"]),
                sprite_id=sprite_ids["locals"],
                key=str(npc["id"]),
                state=name,
                storm_seconds_id=variable_ids["storm_seconds"],
                dialogue=short_lines(
                    {
                        "Marta": "Marta: Watch out!",
                        "Rosa": "Rosa: Step high!",
                        "Kiko": "Kiko: Stay dry!",
                    }[name]
                ),
            )
        )

    substation = level.SUBSTATION
    actors.append(
        actor(
            index=len(actors),
            symbol="substation",
            name="Substation",
            x=int(substation["x"]),
            y=int(substation["row"]),
            sprite_id=sprite_ids["substation"],
            key="substation",
            storm_seconds_id=variable_ids["storm_seconds"],
            dialogue=short_lines("Grid starts here."),
        )
    )

    triggers: list[dict[str, Any]] = []
    for index, (x0, x1, row0, row1) in enumerate(level.HAZARDS):
        label = f"hazard_{index + 1}"
        triggers.append(
            trigger(
                index=index,
                x=x0,
                y=row0,
                width=x1 - x0 + 1,
                height=row1 - row0 + 1,
                label=label,
                script_events=[
                    sound_event(audio_ids["death"], f"hazard:{label}:death-sfx"),
                    event(
                        "EVENT_ACTOR_SET_POSITION",
                        {
                            "units": "tiles",
                            "actorId": "player",
                            "x": number(int(level.PLAYER_START["x"])),
                            "y": number(int(level.PLAYER_START["y"])),
                        },
                        f"hazard:{label}:respawn",
                    ),
                ],
            )
        )

    return scene, actors, triggers


def update_project_settings(scene_id: str, player_id: str) -> None:
    settings_path = PROJECT_DIR / "project" / "settings.gbsres"
    settings = load_json(settings_path)
    settings.update(
        {
            "startSceneId": scene_id,
            "startX": level.PLAYER_START["x"],
            "startY": level.PLAYER_START["y"],
            "colorMode": "color",
            "defaultSceneTypeId": "PLATFORM",
        }
    )
    default_player_sprites = settings.setdefault("defaultPlayerSprites", {})
    default_player_sprites["PLATFORM"] = player_id
    write_json(settings_path, settings)

    fields_path = PROJECT_DIR / "project" / "engine_field_values.gbsres"
    fields = load_json(fields_path)
    engine_fields = fields.setdefault("engineFieldValues", [])
    if not isinstance(engine_fields, list):
        raise ValueError(f"{fields_path} has malformed engineFieldValues")
    values = {
        "INPUT_PLATFORM_INTERACT": "INPUT_B",
        "FEAT_PLATFORM_RUN": 0,
    }
    found: set[str] = set()
    for field in engine_fields:
        if isinstance(field, dict) and field.get("id") in values:
            field["value"] = values[field["id"]]
            found.add(field["id"])
    for field_id, value in values.items():
        if field_id not in found:
            engine_fields.append({"id": field_id, "value": value})
    write_json(fields_path, fields)


def main() -> None:
    background_id = sidecar_id(
        "assets/backgrounds/storm_night.png.gbsres", "background"
    )
    sprite_ids = {
        name: sidecar_id(f"assets/sprites/{name}.png.gbsres", "sprite")
        for name in ("houses", "locals", "substation", "hazard", "cable", "player_platform")
    }
    variable_ids = update_variables()
    audio_ids = {
        "intro_music": sidecar_id("assets/music/cfe_intro.uge.gbsres", "music"),
        "main_music": sidecar_id("assets/music/cfe_main.uge.gbsres", "music"),
        "win_music": sidecar_id("assets/music/cfe_win.uge.gbsres", "music"),
        "lose_music": sidecar_id("assets/music/cfe_lose.uge.gbsres", "music"),
        "connect": sidecar_id("assets/sounds/connect.wav.gbsres", "sound"),
        "cut": sidecar_id("assets/sounds/cut.wav.gbsres", "sound"),
        "death": sidecar_id("assets/sounds/death.wav.gbsres", "sound"),
        "victory": sidecar_id("assets/sounds/victory.wav.gbsres", "sound"),
        "jump": sidecar_id("assets/sounds/jump.wav.gbsres", "sound"),
    }
    bg_palette_ids, sprite_palette_ids, palettes = build_palettes()
    scene, actors, triggers = build_scene(
        background_id,
        sprite_ids,
        bg_palette_ids,
        sprite_palette_ids,
        variable_ids,
        audio_ids,
    )
    palette_dir = PROJECT_DIR / "project" / "palettes"
    for filename, palette in palettes:
        write_json(palette_dir / filename, palette)
    scene_dir = PROJECT_DIR / "project" / "scenes" / SCENE_DIR_NAME
    for hazard_index in range(1, len(level.HAZARDS) + 1):
        label = f"hazard_{hazard_index}"
        remove_owned_resource(
            scene_dir / "actors" / f"{label}_visual.gbsres",
            resource_id(f"actor:{label}:visual"),
        )
    write_json(scene_dir / "scene.gbsres", scene)
    for item in actors:
        write_json(scene_dir / "actors" / f"{item['symbol']}.gbsres", item)
    for item in triggers:
        write_json(scene_dir / "triggers" / f"{item['symbol']}.gbsres", item)
    update_project_settings(scene["id"], sprite_ids["player_platform"])
    print(
        f"generated {scene_dir.relative_to(PROJECT_DIR)}: "
        f"{level.MAP_W}x{level.MAP_H} PLATFORM, {len(actors)} actors, "
        f"{len(palettes)} custom palettes, "
        f"{len(triggers)} hazard triggers"
    )


if __name__ == "__main__":
    main()
