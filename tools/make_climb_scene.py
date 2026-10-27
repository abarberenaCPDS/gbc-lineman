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
# Amara stands on the summit shelf (row 6) two tiles left of House A. She has
# no collision, so the 24px hero's respawn tile and landing stay unobstructed.
MARTA_SHELF_POSITION = (8, 5)
# Opening Amara's tiles reference OBJ palette slot 1, which is free in Storm
# Climb (cracked boards use 4, gust 5, player 0). The old houses sprite used slot 2.
MARTA_SPRITE_PALETTE_SLOT = 1
# Background slot 3 is the summit window family; the opening's repair swaps it.
SUMMIT_WINDOW_BG_SLOT = 3
# Live Wire repair job: variables 6 (carrying cable) and 7 (line live) are
# project-global; both reset on every scene entry.
CABLE_ACTOR_KEY = "cable-end"
JUNCTION_ACTOR_KEY = "junction-box"
# Grid sprite palette (OBJ slot climb.GRID_SPRITE_PALETTE_SLOT). Index 0 is the
# transparent placeholder, as in opening.SPRITE_PALETTES.
GRID_SPRITE_HARDWARE = ["000000", "C7DCE1", "38C8D8", "142332"]
CABLE_ACTOR_SYMBOL = "grid_cable_end"
JUNCTION_ACTOR_SYMBOL = "grid_junction_box"
# The broken pole is the intro's animated pole sprite (Snapped until the line is
# live, then Standing). Its tiles carry OBJ slot intro.SPRITE_SLOTS["pole"], so
# the scene uses the intro pole palette there; no climb sprite uses that slot.
POLE_ACTOR_KEY = "pole"
POLE_ACTOR_SYMBOL = "climb_storm_pole"
# Two-digit variable tokens only: GB Studio drops a single leading zero.
HUD_TEXT = "LINE %D1$07$/1 HOME %D1$00$/1"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (sibling module owns all authored climb data)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import voices  # noqa: E402  (speaker names and text blips)
    import ridge  # noqa: E402  (Hiroshi's job contract: summit exit target)
    import tickets  # noqa: E402  (work orders: summit exit, CLOSED box)
    import hazards  # noqa: E402  (cracked boards and hidden cables: placement and timings)
    import rosa  # noqa: E402  (Signal Hill owns the live arc sprite and palette)
except ModuleNotFoundError as error:
    if error.name in {"tickets", "voices", "climb", "intro", "opening", "ridge", "hazards", "rosa"}:
        raise SystemExit(
            f"cannot generate storm_climb: tools/{error.name}.py is missing; "
            "it must provide the climb/opening data API"
        ) from error
    raise

POLE_SPRITE_PALETTE_SLOT = intro.SPRITE_SLOTS["pole"]
VAR_CARRYING_CABLE_ID = climb.VAR_CARRYING_CABLE
VAR_LINE_LIVE_ID = climb.VAR_LINE_LIVE
LINE_BG_SLOT = climb.LINE_BG_SLOT
GRID_SPRITE_PALETTE_SLOT = climb.GRID_SPRITE_PALETTE_SLOT


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


def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Live Wire variables without changing any existing entry.

    Mirrors make_opening_scene.write_variables: an existing ID with a different
    name or symbol is refused rather than silently renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (
        (VAR_CARRYING_CABLE_ID, "Carrying Cable", "var_carrying_cable"),
        (VAR_LINE_LIVE_ID, "Line Live", "var_line_live"),
        *hazards.VARIABLES,
    ):
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in merged["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            merged["variables"].append(value)
    return merged


def write_variables() -> None:
    path = PROJECT_DIR / "project" / "variables.gbsres"
    data = load_json(path)
    merged = merged_variables(data)
    contents = json.dumps(merged, indent=2) + "\n"
    if path.read_text(encoding="utf-8") != contents:
        path.write_text(contents, encoding="utf-8")
        print("registered storm_climb variables without changing existing variables")


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = "Storm Climb " + kind + " " + name
    return {
        "_resourceType": "palette",
        "id": climb.grid_resource_id(f"palette:{kind}:{name.replace(' ', '_').lower()}"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def editor_sprite_colors(hardware: list[str]) -> list[str]:
    # GB Studio expands editor colors as [p0,p0,p1,p3]; serialize [light,mid,dark,dark]
    # so the intended hardware indices survive, as make_opening_scene does.
    return [hardware[1], hardware[2], hardware[3], hardware[3]]


def grid_palettes() -> list[tuple[str, dict[str, Any]]]:
    """Return (project-relative path, palette resource) for the Live Wire palettes."""
    sprite = palette_resource("sprite", "grid", editor_sprite_colors(GRID_SPRITE_HARDWARE))
    dead = palette_resource("bg", "metal dead", list(climb.METAL_DEAD))
    live = palette_resource("bg", "metal live", list(climb.METAL_LIVE))
    return [
        ("project/palettes/storm_climb_sprite_grid.gbsres", sprite),
        ("project/palettes/storm_climb_bg_metal_dead.gbsres", dead),
        ("project/palettes/storm_climb_bg_metal_live.gbsres", live),
    ]


def grid_sprite_palette_id() -> str:
    return climb.grid_resource_id("palette:sprite:grid")


def metal_palette_id(live: bool) -> str:
    return climb.grid_resource_id("palette:bg:metal_live" if live else "palette:bg:metal_dead")


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


def say(lines: list[str], key: str, speaker: str | None = None) -> list[dict[str, Any]]:
    """In-play dialogue: lift the HUD's 16px window cutoff so the box is visible,
    then restore the HUD. Exact-ROM play showed text behind the cutoff staying
    invisible while the script waited for A, freezing the player. A speaker
    names the box and gives it that character's blip (voices.py)."""
    if speaker is None:
        return [
            cutoff_event(150, f"{key}:say-cutoff"),
            text_event(lines, key),
            *hud_events(f"{key}:say-hud"),
        ]
    # The cutoff stays directly before the text; the voice wraps both.
    return [
        event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(speaker), f"{key}:voice"),
        cutoff_event(150, f"{key}:say-cutoff"),
        text_event(voices.labeled(speaker, lines), key),
        event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(None), f"{key}:narrator"),
        *hud_events(f"{key}:say-hud"),
    ]


def hud_events(key: str) -> list[dict[str, Any]]:
    return [
        cutoff_event(16, f"{key}:cutoff"),
        event("EVENT_OVERLAY_SHOW", {"color": "black", "x": 0, "y": 0}, f"{key}:show"),
        event(
            "EVENT_TEXT_DRAW",
            {"text": HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
            f"{key}:counter",
        ),
        *intro.dev_hud_events(event, key),
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


def background_palette_state(powered: bool, key: str) -> dict[str, Any]:
    """Swap only the summit window slot; every other BG slot is kept as-is.

    Mirrors make_opening_scene.palette_state so both scenes use one repair
    language (window cold -> powered_window warm).
    """
    return background_palette_event({
        SUMMIT_WINDOW_BG_SLOT: opening.resource_id(
            "palette:bg:" + ("powered_window" if powered else "window")
        ),
    }, key)


def background_palette_event(slots: dict[int, str], key: str) -> dict[str, Any]:
    """Set only the listed BG slots; every other slot is kept as-is."""
    args: dict[str, Any] = {f"palette{index}": "keep" for index in range(8)}
    for slot, palette_id in slots.items():
        args[f"palette{slot}"] = palette_id
    return event("EVENT_PALETTE_SET_BACKGROUND", args, key)


def line_palette_state(live: bool, key: str) -> dict[str, Any]:
    """Swap only BG slot 5 (the drawn cable route) between dead and live metal."""
    return background_palette_event({LINE_BG_SLOT: metal_palette_id(live)}, key)


def cable_actor_id() -> str:
    return resource_id(f"actor:{CABLE_ACTOR_KEY}")


def junction_actor_id() -> str:
    return resource_id(f"actor:{JUNCTION_ACTOR_KEY}")


def pole_actor_id() -> str:
    return resource_id(f"actor:{POLE_ACTOR_KEY}")


def cable_drop_events(key: str) -> list[dict[str, Any]]:
    """A carried cable falls back to the storm pole when the carrier is hit."""
    return [if_value(VAR_CARRYING_CABLE_ID, 1, f"{key}:cable-drop", [
        set_value(VAR_CARRYING_CABLE_ID, 0, f"{key}:cable-clear"),
        event("EVENT_ACTOR_SHOW", {"actorId": cable_actor_id()}, f"{key}:cable-show"),
        actor_state(cable_actor_id(), "Dangling", f"{key}:cable-dangling"),
        *hud_events(f"{key}:cable-hud"),
    ])]


def actor_state(actor_id: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_STATE", {
        "actorId": actor_id, "spriteStateId": state, "loopAnim": loop,
    }, key)


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Shared checkpoint-aware reset for trigger and actor collisions.

    The cable drop runs before repositioning so the carrier's hands are empty
    wherever the checkpoint sends them.
    """
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *cable_drop_events(key),
        # The respawn teleports the hero without a leave event: forget the board.
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        if_value(VARIABLE_CHECKPOINTS_REACHED, 0, f"{key}:respawn-check", [
            set_position(*climb.START, f"{key}:respawn-start"),
        ], [
            set_position(climb.HOUSE_A["x"], climb.HOUSE_A["y"], f"{key}:respawn-house"),
        ]),
    ]


def wait_event(frames: int, key: str) -> dict[str, Any]:
    # Official eventWait.js accepts script-value frames, not plain integers.
    return event("EVENT_WAIT", {"units": "frames", "frames": number(frames)}, key)


# ---------------------------------------------------------------------------
# Cracked boards and hidden cables (hazards.py owns placement, IDs and timings)
# ---------------------------------------------------------------------------
HAZARD_PALETTE_PATH = "project/palettes/hazards_sprite_board.gbsres"
# Board triggers come after every exit and door trigger (first match wins).
BOARD_TRIGGER_BASE_INDEX = 102


def rosa_arc_palette_id() -> str:
    return rosa.resource_id("palette:sprite:arc")


def board_palette_resource() -> dict[str, Any]:
    title = "Hazards sprite board"
    colors = editor_sprite_colors(hazards.BOARD_SPRITE_HARDWARE)
    return {
        "_resourceType": "palette",
        "id": hazards.BOARD_PALETTE_ID,
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def hazard_palettes() -> list[tuple[str, dict[str, Any]]]:
    """Written by every scene with boards; the content is identical, so writes are idempotent."""
    return [(HAZARD_PALETTE_PATH, board_palette_resource())]


def board_actor(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y = hazards.board_actor_position(board)
    actor = actor_resource(
        index=index,
        symbol=f"board_{number:02d}",
        name=f"Cracked Board {number}",
        x=x,
        y=y,
        sprite_id=hazards.BOARD_SPRITE_ID,
        key=key,
        start_script=hazards.board_start_script(key, event),
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["updateScript"] = hazards.board_update_script(
        number, key, event, wait_event, if_value, set_value)
    return actor


def hidden_cable_actor(number: int, lane: tuple[int, int, int], start_delay: int,
                       index: int) -> dict[str, Any]:
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the live arc sprite is exactly two tiles wide")
    key = f"hidden-cable:{number}"
    actor = actor_resource(
        index=index,
        symbol=f"hidden_cable_{number:02d}",
        name=f"Hidden Cable {number}",
        x=x0,
        y=row,
        sprite_id=rosa.ARC_SPRITE_ID,
        key=key,
        start_script=hazards.cable_start_script(key, event),
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["animSpeed"] = 8
    actor["updateScript"] = hazards.cable_update_script(
        key, start_delay, event, wait_event, branch_event)
    return actor


def hazard_actors(first_index: int) -> list[dict[str, Any]]:
    boards = hazards.BOARDS["storm_climb"]
    cables = hazards.HIDDEN_CABLES["storm_climb"]
    delays = hazards.CABLE_START_DELAYS["storm_climb"]
    actors: list[dict[str, Any]] = []
    for number, board in enumerate(boards, start=1):
        actors.append(board_actor(number, board, first_index + len(actors)))
    for number, (lane, delay) in enumerate(zip(cables, delays), start=1):
        actors.append(hidden_cable_actor(number, lane, delay, first_index + len(actors)))
    return actors


def board_trigger(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y, width, height = hazards.board_trigger_rect(board)
    on_script, leave_script = hazards.board_trigger_scripts(number, f"{key}:trigger", set_value)
    return {
        "_resourceType": "trigger",
        "id": resource_id(f"trigger:{key}"),
        "name": f"Cracked Board {number} Stand",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": f"trigger_cracked_board_{number:02d}",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": on_script,
        "leaveScript": leave_script,
        "_index": index,
    }


def hazard_triggers() -> list[dict[str, Any]]:
    return [
        board_trigger(number, board, BOARD_TRIGGER_BASE_INDEX + number - 1)
        for number, board in enumerate(hazards.BOARDS["storm_climb"], start=1)
    ]


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
        event(
            "EVENT_PLAYER_SET_SPRITE",
            {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
            "init-player-sprite",
        ),
        event(
            "EVENT_ACTOR_SET_DIRECTION",
            {"actorId": "player", "direction": {"type": "direction", "value": "right"}},
            "init-player-direction",
        ),
        set_value(VARIABLE_CHECKPOINTS_REACHED, 0, "init-checkpoints-reached"),
        # Live Wire starts every entry with an empty hand and a dead line.
        set_value(VAR_CARRYING_CABLE_ID, 0, "init-carrying-cable"),
        set_value(VAR_LINE_LIVE_ID, 0, "init-line-live"),
        # Standing on a cracked board is tracked by its trigger; a fresh entry starts off it.
        set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        # Explicit cold summit window on every entry, matching the var 0 reset.
        background_palette_state(False, "init-summit-window-cold"),
        line_palette_state(False, "init-line-dead"),
        # The pole's start script also reads var 7, and the order between it and
        # this script is unspecified. Pin Snapped here so a stale live flag from a
        # previous visit can never leave the pole Standing on a dead line.
        actor_state(pole_actor_id(), "Snapped", "init-pole-snapped"),
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-village-music"),
        # The overlay scanline cutoff survives scene switches: lift it so the
        # intro box is visible even when a previous visit left the HUD's 16px.
        cutoff_event(150, "intro-controls:say-cutoff"),
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


MARTA_ACTOR_KEY = "marta-checkpoint"


def marta_actor_id() -> str:
    return resource_id(f"actor:{MARTA_ACTOR_KEY}")


def checkpoint_actor(index: int, marta_sprite_id: str) -> dict[str, Any]:
    """Amara on the summit shelf: Waiting until the arrival checkpoint.

    The start script is unconditional. The scene script resets var 0 on every
    entry, but actor start scripts give no ordering guarantee against it, so a
    conditional here could read a stale value from a previous visit.
    """
    key = MARTA_ACTOR_KEY
    x, y = MARTA_SHELF_POSITION
    actor = actor_resource(
        index=index,
        symbol="marta_checkpoint",
        name="Amara (Summit Checkpoint)",
        x=x,
        y=y,
        sprite_id=marta_sprite_id,
        key=key,
        script=[if_value(VARIABLE_CHECKPOINTS_REACHED, 0, f"{key}:talk", [
            if_value(VAR_LINE_LIVE_ID, 0, f"{key}:talk-line", [
                *say(short_lines("Storm broke the\nline below."), f"{key}:talk-dead", "marta"),
            ], [
                *say(short_lines("Line's live!\nGo to my door."), f"{key}:talk-live", "marta"),
            ]),
        ], [
            *say(short_lines("Food is saved.\nThank you, CFE!"), f"{key}:talk-after", "marta"),
        ])],
        start_script=[actor_state("$self$", "Waiting", f"{key}:waiting")],
    )
    # Match the opening's Amara, whose Waiting/Powered states carry idle frames.
    actor["animate"] = True
    return actor


def cable_end_actor(index: int, sprite_id: str, pickup_sound_id: str) -> dict[str, Any]:
    """Dangling cable on the storm-snapped pole (shelf 21). B picks it up.

    Only a visible cable can be picked up, and it is hidden once carried. The
    start script is unconditional, like Amara's, because scene init resets
    var 6 and 7 on every entry.
    """
    key = CABLE_ACTOR_KEY
    x, y = climb.DAMAGED_POLE
    pickup = [if_value(VAR_CARRYING_CABLE_ID, 0, f"{key}:empty-hands", [
        if_value(VAR_LINE_LIVE_ID, 0, f"{key}:line-dead", [
            set_value(VAR_CARRYING_CABLE_ID, 1, f"{key}:carry"),
            event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:hide"),
            sound_event(pickup_sound_id, f"{key}:sfx"),
            *say(short_lines("Got the cable!\nTake it up top."), f"{key}:text"),
        ]),
    ])]
    actor = actor_resource(
        index=index,
        symbol=CABLE_ACTOR_SYMBOL,
        name="Dangling Cable End",
        x=x,
        y=y,
        sprite_id=sprite_id,
        key=key,
        script=pickup,
        start_script=[actor_state("$self$", "Dangling", f"{key}:dangling")],
    )
    actor["animate"] = True
    return actor


def junction_box_actor(index: int, sprite_id: str, connect_sound_id: str) -> dict[str, Any]:
    """Dead junction box on shelf 15. Plugging in the carried cable energizes it."""
    key = JUNCTION_ACTOR_KEY
    x, y = climb.JUNCTION_BOX
    plug = [if_value(VAR_LINE_LIVE_ID, 1, f"{key}:live", [
        *say(short_lines("Line is live."), f"{key}:already-live"),
    ], [
        if_value(VAR_CARRYING_CABLE_ID, 1, f"{key}:has-cable", [
            set_value(VAR_CARRYING_CABLE_ID, 0, f"{key}:clear-cable"),
            set_value(VAR_LINE_LIVE_ID, 1, f"{key}:set-live"),
            actor_state("$self$", "Live", f"{key}:live-state"),
            actor_state(pole_actor_id(), "Standing", f"{key}:pole-standing"),
            line_palette_state(True, f"{key}:metal-live"),
            sound_event(connect_sound_id, f"{key}:sfx"),
            *say(short_lines("Line is live!\nOn to Amara's."), f"{key}:text"),
        ], [
            *say(short_lines("No cable yet.\nCheck the pole."), f"{key}:no-cable"),
        ]),
    ])]
    actor = actor_resource(
        index=index,
        symbol=JUNCTION_ACTOR_SYMBOL,
        name="Junction Box (Shelf 15)",
        x=x,
        y=y,
        sprite_id=sprite_id,
        key=key,
        script=plug,
        start_script=[actor_state("$self$", "Dead", f"{key}:dead")],
    )
    actor["animate"] = True
    return actor


def pole_actor(index: int, sprite_id: str) -> dict[str, Any]:
    """The snapped storm pole on shelf 21, using the intro pole sprite.

    Snapped while the line is dead, Standing once the junction box makes it live.
    Non-colliding and not interactive: the cable-end pickup owns the B press.
    """
    key = POLE_ACTOR_KEY
    x, y = climb.DAMAGED_POLE
    actor = actor_resource(
        index=index,
        symbol=POLE_ACTOR_SYMBOL,
        name="Storm Pole",
        x=x,
        y=y,
        sprite_id=sprite_id,
        key=key,
        start_script=[
            # Off, so B finds the cable end on this tile instead of the pole.
            event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:no-collision"),
            if_value(VAR_LINE_LIVE_ID, 1, f"{key}:line-check", [
                actor_state("$self$", "Standing", f"{key}:standing"),
            ], [
                actor_state("$self$", "Snapped", f"{key}:snapped"),
            ]),
        ],
    )
    actor["animate"] = True
    return actor


def arrival_rect() -> tuple[int, int, int, int]:
    """Return (x, y, width, height) for the arrival trigger.

    Only the top row of a 24px hero standing on the summit shelf (row 3) is
    covered, at the doorway columns 11-13. Exact-ROM play showed a rows 3-5
    trigger firing early: an 8-frame jump from shelf 12 put the head in
    row 4. Landing straight up from shelf 9's safe takeoff (x72) stays left
    of column 11, so the reward plays on reaching Amara's door.
    """
    house = climb.HOUSE_A
    return int(house["x"]), int(house["y"]) - 2, 3, 1


def build_checkpoint_trigger(death_sound_id: str, connect_sound_id: str) -> dict[str, Any]:
    x, y, width, height = arrival_rect()
    # Keep the original stable trigger key (100) so the resource ID and file
    # path are unchanged; only its geometry, name and script are new.
    checkpoint = trigger_resource(100, (y, x, x + width - 1), death_sound_id)
    checkpoint.update({
        "name": "Amara Arrival Checkpoint",
        "symbol": "trigger_marta_arrival",
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        # Amara's door needs the line live. Without it nothing is saved and the
        # checkpoint stays unset, so the reward can still fire later.
        "script": [if_value(VAR_LINE_LIVE_ID, 1, "checkpoint-arrival:line", [
            if_value(VARIABLE_CHECKPOINTS_REACHED, 0, "checkpoint-arrival", [
                set_value(VARIABLE_CHECKPOINTS_REACHED, 1, "checkpoint-arrival:set"),
                sound_event(connect_sound_id, "checkpoint-arrival:sfx"),
                background_palette_state(True, "checkpoint-arrival:summit-lit"),
                actor_state(marta_actor_id(), "Powered", "checkpoint-arrival:marta-powered"),
                cutoff_event(150, "checkpoint-arrival:cutoff"),
                # Second page: Amara's work order closes (tickets.py).
                text_event([*short_lines("Power's back!\nMy fridge hums."), *tickets.closed_lines(1)],
                           "checkpoint-arrival:text"),
                *hud_events("checkpoint-arrival:hud"),
            ]),
        ], [
            *say(short_lines("Still no power.\nFix the line!"), "checkpoint-arrival:no-power"),
        ])],
    })
    return checkpoint


def street_exit_trigger() -> dict[str, Any]:
    """Back to the service opening, two tiles before its awning exit.

    Re-entering the climb runs scene init again: vars 0/6/7 reset while the
    opening's var 4 (service restored) keeps the gate open. The HUD's 16px
    scanline cutoff survives the switch, so it is lifted and the overlay hidden
    first; exact-ROM play showed the opening's controls box invisible and
    waiting for A otherwise.
    """
    x, y, width, height = climb.STREET_EXIT
    arrive_x, arrive_y = opening.EXIT_NUDGE
    return {
        "_resourceType": "trigger",
        "id": resource_id("trigger:street-exit"),
        "name": "Street Exit (to Service Opening)",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": "trigger_street_exit",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": [
            cutoff_event(150, "street-exit:cutoff"),
            event("EVENT_OVERLAY_HIDE", {}, "street-exit:hud-hide"),
            event("EVENT_SWITCH_SCENE", {
            "x": number(arrive_x), "y": number(arrive_y), "direction": "left",
            "sceneId": opening.resource_id("scene:service-opening"), "fadeSpeed": "2",
            }, "street-exit:to-opening"),
        ],
        "leaveScript": [],
        "_index": 100,
    }


SUMMIT_EXIT_NUDGE_TILES = 3


def summit_exit_trigger() -> dict[str, Any]:
    """Right end of the summit shelf leads on to Hiroshi's Wind Ridge.

    Gated on Amara's checkpoint (var 0) so the jobs stay in order; before
    that the hero is told why and nudged back onto the shelf. Like the street
    exit, it lifts the HUD cutoff and hides the overlay before switching.
    """
    x, y, width, height = ridge.CLIMB_SUMMIT_EXIT
    go = [
        cutoff_event(150, "summit-exit:cutoff"),
        event("EVENT_OVERLAY_HIDE", {}, "summit-exit:hud-hide"),
        # Hiroshi's work order first; its card switches on to Wind Ridge's start.
        *tickets.to_work_order(2, "summit-exit", event, set_value, number),
    ]
    # Exact ROM 147c23be: a two-tile nudge after the text left the 24px hero's
    # box (x+2..x+14) touching the exit after leftover momentum, so the text
    # looped. Step back three tiles first, then explain.
    wait = [
        set_position(x - SUMMIT_EXIT_NUDGE_TILES, climb.HOUSE_A["y"], "summit-exit:nudge-back"),
        *say(short_lines("Amara needs\npower first."), "summit-exit:not-yet"),
    ]
    return {
        "_resourceType": "trigger",
        "id": resource_id("trigger:summit-exit"),
        "name": "Summit Exit (to Wind Ridge)",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": "trigger_summit_exit",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": [if_value(ridge.CLIMB_EXIT_GATE_VAR, 1, "summit-exit:gate", go, wait)],
        "leaveScript": [],
        "_index": 101,
    }


def timed_gust_actor(index: int, lane: tuple[int, int, int], sprite_id: str) -> dict[str, Any]:
    """Warning has no collision; burst hits through the shared group-1 reset."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 3:
        raise ValueError("the authored gust sprite is exactly three tiles wide")
    key = f"timed-gust:{index}"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    actor = actor_resource(
        index=index,
        symbol=f"gust_{index:02d}",
        name=f"Telegraphed Gust {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["animSpeed"] = 8
    actor["updateScript"] = [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "warning-safe"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait_event(climb.GUST_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "burst-state", spriteStateId="Burst", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "burst-active"),
        wait_event(climb.GUST_ACTIVE_FRAMES, f"{key}:burst-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(climb.GUST_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor


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
        "script": [sound_event(death_sound_id, f"{key}:death-sfx"), *cable_drop_events(key), respawn],
        "leaveScript": [],
        "_index": index - 1,
    }


def gust_marker_triggers(death_sound_id: str) -> list[dict[str, Any]]:
    markers = [
        trigger_resource(index, lane, death_sound_id)
        for index, lane in enumerate(climb.GUST_LANES, start=1)
    ]
    for lane_index, trigger in enumerate(markers):
        # Keep stable resource IDs, but no instant reset scripts. The 24px
        # collider made adjacent static lanes an unavoidable vertical squeeze.
        status = "timed actor-owned" if lane_index in climb.TIMED_GUST_LANE_INDICES else "inactive preview"
        trigger["name"] = f"Gust Lane {lane_index + 1} ({status})"
        trigger["script"] = []
    return markers


def build_scene(music_id: str) -> dict[str, Any]:
    if int(climb.MAP_W) != 20 or int(climb.MAP_H) != 36:
        raise ValueError("storm_climb must match the Storm Night 20x36 scene schema")
    scene = load_json(REFERENCE_SCENE)
    sprite_palette_ids = scene.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Storm Climb reference scene must have eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[MARTA_SPRITE_PALETTE_SLOT] = opening.resource_id("palette:sprite:marta")
    sprite_palette_ids[GRID_SPRITE_PALETTE_SLOT] = grid_sprite_palette_id()
    sprite_palette_ids[POLE_SPRITE_PALETTE_SLOT] = intro.palette_id("pole")
    # Boards take the retired debris slot; hidden cables take the live-arc slot.
    if hazards.BOARDS["storm_climb"]:
        sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    if hazards.HIDDEN_CABLES["storm_climb"]:
        sprite_palette_ids[rosa.ARC_SPRITE_PALETTE_SLOT] = rosa_arc_palette_id()
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Storm Climb background palettes must preserve the UI in slot 7")
    # Slot 5 starts dead; the scene init and the junction box swap it at runtime.
    background_palette_ids[LINE_BG_SLOT] = metal_palette_id(False)
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
            "paletteIds": background_palette_ids,
            "spritePaletteIds": sprite_palette_ids,
            "script": scene_script(music_id),
            "playerHit1Script": respawn_events("debris-hit", sidecar_id("assets/sounds/death.wav.gbsres", "sound")),
        }
    )
    return scene


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other workers produce these art files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def remove_retired_debris_actors(scene_dir: Path = SCENE_DIR, prefix: str = "") -> None:
    """Falling debris is retired; delete the generated actor files it left behind.

    ``prefix`` is the scene's symbol prefix (``ridge_``, ``pine_``) when it has one.
    """
    for path in sorted((scene_dir / "actors").glob(f"{prefix}debris_*.gbsres")):
        path.unlink()
        print(f"removed retired {path.relative_to(PROJECT_DIR)}")


def main() -> None:
    music_id = sidecar_id("assets/music/cfe_storm_climb.uge.gbsres", "music")
    sprite_ids = {
        "marta": sidecar_id("assets/sprites/opening_marta.png.gbsres", "sprite"),
        "gust": sidecar_id("assets/sprites/climb_gust.png.gbsres", "sprite"),
    }
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")
    warn_if_missing_asset(rosa.ARC_SPRITE_ID, "sprites", "live arc sprite")
    if sprite_ids["marta"] != opening.resource_id("sprite:opening_marta"):
        raise ValueError("opening_marta sidecar no longer matches opening.py identity")
    audio_ids = {
        "death": sidecar_id("assets/sounds/death.wav.gbsres", "sound"),
        "connect": sidecar_id("assets/sounds/connect.wav.gbsres", "sound"),
        "pickup": sidecar_id("assets/sounds/pickup.wav.gbsres", "sound"),
    }

    scene = build_scene(music_id)
    actors = [checkpoint_actor(0, sprite_ids["marta"])]
    actors.extend(
        timed_gust_actor(index + 1, climb.GUST_LANES[index], sprite_ids["gust"])
        for index in climb.TIMED_GUST_LANE_INDICES
    )
    # The pole sits on the cable end's tile. Actors draw in descending index
    # order (higher index = lower OAM = on top), so the pole goes first and the
    # cable stays visible above it (cart bug B-13).
    actors.append(pole_actor(len(actors), intro.POLE_SPRITE_ID))
    actors.append(cable_end_actor(len(actors), climb.grid_resource_id("sprite:grid_cable_end"),
                                  audio_ids["pickup"]))
    actors.append(junction_box_actor(len(actors), climb.grid_resource_id("sprite:grid_junction_box"),
                                     audio_ids["connect"]))
    # Cracked boards and hidden cables go last: the highest indexes draw on top.
    actors.extend(hazard_actors(len(actors)))
    triggers = gust_marker_triggers(audio_ids["death"])
    triggers.append(build_checkpoint_trigger(audio_ids["death"], audio_ids["connect"]))
    triggers.append(street_exit_trigger())
    triggers.append(summit_exit_trigger())
    triggers.extend(hazard_triggers())

    write_variables()
    for relative_path, palette in grid_palettes() + hazard_palettes():
        write_json(PROJECT_DIR / relative_path, palette)
    remove_retired_debris_actors()
    write_json(SCENE_DIR / "scene.gbsres", scene)
    for actor in actors:
        write_json(SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres", actor)
    for trigger in triggers:
        write_json(SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres", trigger)
    print(
        f"generated storm_climb: {climb.MAP_W}x{climb.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{len(hazards.BOARDS['storm_climb'])} cracked boards, "
        f"{len(hazards.HIDDEN_CABLES['storm_climb'])} hidden cable; "
        f"{len(climb.TIMED_GUST_LANE_INDICES)} telegraphed gust; "
        "remaining gust markers are inert until their routes are tested"
    )


if __name__ == "__main__":
    main()
