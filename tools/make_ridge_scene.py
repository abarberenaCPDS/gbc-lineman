"""Generate the deterministic Wind Ridge scene (Hiroshi's repair job) from ``ridge.py``.

Run with ``python3 tools/make_ridge_scene.py`` from any working directory.
This writes only the Wind Ridge scene resources, the Hiroshi sprite palette and
the Ridge variable registrations. The authored geometry, positions, gust
timings and stable IDs live in the sibling ``ridge.py`` contract module.

Generic GB Studio helpers (collision RLE, sidecar lookup, JSON writing, the
dialogue length check) are reused from ``make_climb_scene``. Event builders are
local because the climb versions derive event IDs from the climb namespace.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENE_DIR = PROJECT_DIR / "project" / "scenes" / "wind_ridge"
CLIMB_SCENE = PROJECT_DIR / "project" / "scenes" / "storm_climb" / "scene.gbsres"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

# Editor placement and scene index: free in the project (climb and night sit at 0,0).
SCENE_EDITOR_POSITION = (400, 360)
SCENE_INDEX = 4
MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import voices  # noqa: E402  (speaker names and text blips)
    import ridge  # noqa: E402  (Hiroshi's job contract: geometry, IDs, timings)
    import rosa  # noqa: E402  (Priya's job contract: the ridge exit leads there)
    import tickets  # noqa: E402  (work orders: hill exit, CLOSED box)
    import hazards  # noqa: E402  (cracked boards: placement, IDs and timings)
except ModuleNotFoundError as error:
    if error.name in {"tickets", "voices", "climb", "intro", "opening", "ridge", "rosa", "make_climb_scene",
                      "hazards"}:
        raise SystemExit(
            f"cannot generate wind_ridge: tools/{error.name}.py is missing"
        ) from error
    raise

MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
VAR_CARRYING_CABLE = ridge.VAR_CARRYING_CABLE
VAR_LINE_LIVE = ridge.VAR_LINE_LIVE
VAR_HOME_POWERED = ridge.VAR_HOME_POWERED
VAR_FEEDER_LIVE = ridge.VAR_FEEDER_LIVE
VAR_LINES_LIVE = ridge.VAR_LINES_LIVE
CABLE_KEY = "cable-end"
JUNCTION_KEY = "junction-box"
POLE_KEY = "pole"
POLE_SYMBOL = "ridge_storm_pole"
TOMAS_KEY = "tomas"
CONCENTRATOR_KEY = "oxygen-concentrator"
CABLE_SPRITE_KEY = "sprite:grid_cable_end"
JUNCTION_SPRITE_KEY = "sprite:grid_junction_box"
CABLE_SYMBOL = "ridge_cable_end"
JUNCTION_SYMBOL = "ridge_junction_box"
TOMAS_SYMBOL = "ridge_tomas"
CONCENTRATOR_SYMBOL = "ridge_oxygen_concentrator"
DOOR_TRIGGER_SYMBOL = "trigger_ridge_tomas_door"
WHIP_SPRITE = "assets/sprites/whip_wire.png.gbsres"
ARC_SPRITE = "assets/sprites/live_arc.png.gbsres"

# The grid chain, upstream first (ridge.LINES). The house line keeps the
# original job's keys and symbols (stable IDs, test_poles); the feeder keeps the
# two-line prototype's; the middle line is new.
_LINE_NAMES = {
    "house": {"pole": POLE_KEY, "cable": CABLE_KEY, "box": JUNCTION_KEY,
              "pole_symbol": POLE_SYMBOL, "cable_symbol": CABLE_SYMBOL, "box_symbol": JUNCTION_SYMBOL},
}
LINES = []
for _line in ridge.LINES:
    _key = _line["key"]
    # Coordinates move to pole_at/box_at: "pole"/"box" are actor keys here.
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"], **_LINE_NAMES.get(_key, {
        "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"junction-box:{_key}",
        "pole_symbol": f"ridge_{_key}_pole", "cable_symbol": f"ridge_{_key}_cable_end",
        "box_symbol": f"ridge_{_key}_box",
    })})
LINE_BY_KEY = {line["key"]: line for line in LINES}


# ---------------------------------------------------------------------------
# IDs and palette resources
# ---------------------------------------------------------------------------
def tomas_palette_id() -> str:
    return ridge.resource_id("palette:sprite:tomas")



def actor_id(key: str) -> str:
    return ridge.resource_id(f"actor:{key}")


def pole_actor_id() -> str:
    return actor_id(POLE_KEY)


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = "Wind Ridge " + kind + " " + name
    return {
        "_resourceType": "palette",
        "id": ridge.resource_id(f"palette:{kind}:{name.replace(' ', '_').lower()}"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def tomas_palettes() -> list[tuple[str, dict[str, Any]]]:
    sprite = palette_resource("sprite", "tomas",
                              shared.editor_sprite_colors(ridge.TOMAS_SPRITE_HARDWARE))
    whip = palette_resource("sprite", "whip", shared.editor_sprite_colors(ridge.WHIP_SPRITE_HARDWARE))
    if whip["id"] != ridge.WHIP_PALETTE_ID:
        raise ValueError("whip palette id must match ridge.WHIP_PALETTE_ID")
    chain = [(f"project/palettes/wind_ridge_bg_{chain_palette_name(stages)}.gbsres",
              palette_resource("bg", chain_palette_name(stages), colors))
             for stages, colors in ridge.CHAIN_PALETTES.items()]
    return [("project/palettes/wind_ridge_sprite_tomas.gbsres", sprite),
            ("project/palettes/wind_ridge_sprite_whip.gbsres", whip), *chain]


def chain_palette_name(stages_live: int) -> str:
    return f"chain_{stages_live}_live"


def chain_palette_id(stages_live: int) -> str:
    return ridge.resource_id(f"palette:bg:{chain_palette_name(stages_live)}")


# ---------------------------------------------------------------------------
# Event builders (ridge-scoped IDs; EVENT_TEXT args copied from the climb)
# ---------------------------------------------------------------------------
def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": ridge.resource_id(f"event:{key}")}


def branch_event(command: str, args: dict[str, Any], key: str,
                 true_events: list[dict[str, Any]],
                 false_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        **event(command, args, key),
        "children": {"true": true_events, "false": false_events or []},
    }


def if_value(variable_id: str, value: int, key: str,
             true_events: list[dict[str, Any]],
             false_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return branch_event(
        "EVENT_IF",
        {"condition": {
            "type": "eq",
            "valueA": {"type": "variable", "value": variable_id},
            "valueB": shared.number(value),
        }},
        key, true_events, false_events,
    )


def set_value(variable_id: str, value: int, key: str) -> dict[str, Any]:
    return event("EVENT_SET_VALUE", {"variable": variable_id, "value": shared.number(value)}, key)


def set_position(x: int, y: int, key: str) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_POSITION", {
        "units": "tiles", "actorId": "player", "x": shared.number(x), "y": shared.number(y),
    }, key)


def text_event(lines: list[str], key: str) -> dict[str, Any]:
    return event("EVENT_TEXT", {
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
    }, key)


def cutoff_event(y: int, key: str) -> dict[str, Any]:
    return event("EVENT_OVERLAY_SET_SCANLINE_CUTOFF", {"units": "pixels", "y": shared.number(y)}, key)


def hud_events(key: str) -> list[dict[str, Any]]:
    return [
        cutoff_event(16, f"{key}:cutoff"),
        event("EVENT_OVERLAY_SHOW", {"color": "black", "x": 0, "y": 0}, f"{key}:show"),
        event("EVENT_TEXT_DRAW", {"text": ridge.HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
              f"{key}:counter"),
        *intro.dev_hud_events(event, key),
    ]


def say(lines: list[str], key: str, speaker: str | None = None) -> list[dict[str, Any]]:
    """In-play dialogue: lift the HUD's 16px cutoff so the box shows, then redraw the HUD.

    Exact-ROM play showed text behind the cutoff staying invisible while the
    script waited for A, freezing the player. A speaker names the box and gives
    it that character's blip (voices.py).
    """
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


def sound_event(sound_id: str, key: str) -> dict[str, Any]:
    return event("EVENT_SOUND_PLAY_EFFECT", {
        "units": "time", "type": sound_id, "priority": "high", "pitch": 4,
        "frequency": 200, "duration": 0.5, "wait": True, "effect": 0,
    }, key)


def wait_event(frames: int, key: str) -> dict[str, Any]:
    return event("EVENT_WAIT", {"units": "frames", "frames": shared.number(frames)}, key)


def background_palette_event(slots: dict[int, str], key: str) -> dict[str, Any]:
    args: dict[str, Any] = {f"palette{index}": "keep" for index in range(8)}
    for slot, palette_id in slots.items():
        args[f"palette{slot}"] = palette_id
    return event("EVENT_PALETTE_SET_BACKGROUND", args, key)


def window_palette_event(powered: bool, key: str) -> dict[str, Any]:
    """Swap only the Hiroshi window slot (cold -> powered_window)."""
    name = "powered_window" if powered else "window"
    return background_palette_event({
        ridge.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}"),
    }, key)


def if_at_least(variable_id: str, value: int, key: str,
                true_events: list[dict[str, Any]],
                false_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return branch_event(
        "EVENT_IF",
        {"condition": {
            "type": "gte",
            "valueA": {"type": "variable", "value": variable_id},
            "valueB": shared.number(value),
        }},
        key, true_events, false_events,
    )


def chain_refresh_events(key: str) -> list[dict[str, Any]]:
    """Light the wires as far as the chain is continuous, and each box with them.

    The wire palette (BG slot 5) shows how many leading lines are repaired; a
    box is Live only when every line up to and including its own is.
    """
    def lit(stages: int) -> list[dict[str, Any]]:
        out = [set_value(ridge.VAR_CHAIN_LIVE, stages, f"{key}:stages-{stages}"),
               background_palette_event({ridge.LINE_BG_SLOT: chain_palette_id(stages)},
                                        f"{key}:palette-{stages}")]
        for line in LINES:
            state = "Live" if line["number"] <= stages else "Dead"
            out.append(actor_state(actor_id(line["box"]), state, f"{key}:box-{stages}-{line['key']}"))
        return out

    events = lit(len(LINES))
    for line in reversed(LINES):
        events = [if_value(line["live_var"], 1, f"{key}:{line['key']}", events, lit(line["number"] - 1))]
    return events


def actor_state(target: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_STATE", {
        "actorId": target, "spriteStateId": state, "loopAnim": loop,
    }, key)


def cable_drop_events(key: str) -> list[dict[str, Any]]:
    """A carried cable falls back to its own pole when the carrier is hit."""
    events = []
    for line in LINES:
        # The house line keeps the original event keys (stable IDs).
        tag = key if line["key"] == "house" else f"{key}:{line['key']}"
        events.append(if_value(VAR_CARRYING_CABLE, line["number"], f"{tag}:cable-drop", [
            set_value(VAR_CARRYING_CABLE, 0, f"{tag}:cable-clear"),
            event("EVENT_ACTOR_SHOW", {"actorId": actor_id(line["cable"])}, f"{tag}:cable-show"),
            actor_state(actor_id(line["cable"]), "Dangling", f"{tag}:cable-dangling"),
            *hud_events(f"{tag}:cable-hud"),
        ]))
    return events


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Death sound, then drop any cable, then respawn.

    The cable drop runs before repositioning so the carrier's hands are empty
    wherever the checkpoint sends them. Checkpoints, furthest first: Hiroshi's
    door once his power is on, then the box of the furthest repaired line, else START.
    """
    door_x, door_y = ridge.HOUSE_DOOR
    chosen = [set_position(*ridge.START, f"{key}:respawn-start")]
    for line in LINES:
        chosen = [if_value(line["live_var"], 1, f"{key}:respawn-{line['key']}-check", [
            set_position(*line["checkpoint"], f"{key}:respawn-{line['key']}"),
        ], chosen)]
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *cable_drop_events(key),
        # The respawn teleports the hero without a leave event: forget the board.
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check", chosen, [
            set_position(door_x - 1, door_y, f"{key}:respawn-door"),
        ]),
    ]


# ---------------------------------------------------------------------------
# Scene init
# ---------------------------------------------------------------------------
def scene_script(music_id: str) -> list[dict[str, Any]]:
    return [
        event("EVENT_PLAYER_SET_SPRITE",
              {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
              "init-player-sprite"),
        event("EVENT_ACTOR_SET_DIRECTION",
              {"actorId": "player", "direction": {"type": "direction", "value": "right"}},
              "init-player-direction"),
        set_value(VAR_CARRYING_CABLE, 0, "init-carrying-cable"),
        set_value(VAR_LINE_LIVE, 0, "init-line-live"),
        set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
        set_value(VAR_FEEDER_LIVE, 0, "init-feeder-live"),
        set_value(VAR_LINES_LIVE, 0, "init-lines-live"),
        set_value(ridge.VAR_MIDDLE_LIVE, 0, "init-middle-live"),
        set_value(ridge.VAR_CHAIN_LIVE, 0, "init-chain-live"),
        # Standing on a cracked board is tracked by its trigger; a fresh entry starts off it.
        set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        window_palette_event(False, "init-window-cold"),
        *chain_refresh_events("init-chain"),
        # Pinned Snapped on every entry: each pole's own start script reads its
        # line variable, and the order between the scripts is unspecified.
        *[actor_state(actor_id(line["pole"]), "Snapped",
                      "init-pole-snapped" if line["key"] == "house" else f"init-{line['key']}-pole-snapped")
          for line in LINES],
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-ridge-music"),
        # Intro box after the music cue; say() lifts the cutoff the previous visit may have left.
        *say(short_lines("Hiroshi needs his\noxygen machine!"), "intro"),
        *say(short_lines("Three lines down.\nOne cable a trip."), "intro-lines"),
    ]


# ---------------------------------------------------------------------------
# Actors and triggers
# ---------------------------------------------------------------------------
def actor_resource(*, index: int, symbol: str, name: str, x: int, y: int, sprite_id: str,
                   key: str, animate: bool = True, anim_speed: int = 15,
                   script: list[dict[str, Any]] | None = None,
                   start_script: list[dict[str, Any]] | None = None,
                   update_script: list[dict[str, Any]] | None = None,
                   collision_group: str = "") -> dict[str, Any]:
    return {
        "_resourceType": "actor",
        "id": actor_id(key),
        "_index": index,
        "symbol": symbol,
        "prefabId": "",
        "name": name,
        "coordinateType": "tiles",
        "x": x,
        "y": y,
        "frame": 0,
        "animate": animate,
        "spriteSheetId": sprite_id,
        "paletteId": "",
        "direction": "down",
        "moveSpeed": 1,
        "animSpeed": anim_speed,
        "isPinned": False,
        "persistent": False,
        "collisionGroup": collision_group,
        "collisionExtraFlags": [],
        "prefabScriptOverrides": {},
        "script": script or [],
        "startScript": start_script or [],
        "updateScript": update_script or [],
        "hit1Script": [],
        "hit2Script": [],
        "hit3Script": [],
    }


def tomas_actor(index: int) -> dict[str, Any]:
    """Hiroshi outside his door: Waiting until the house is powered, then Relieved."""
    key = TOMAS_KEY
    x, y = ridge.TOMAS
    script = [if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
        *say(short_lines("Thanks, friend!\nBreathing easy."), f"{key}:thanks", "tomas"),
    ], [
        if_value(VAR_LINES_LIVE, ridge.LINE_COUNT, f"{key}:line", [
            *say(short_lines("Line's live!\nTry my door."), f"{key}:live", "tomas"),
        ], [
            *say(short_lines("The line's dead!\nMy machine's off."), f"{key}:dead", "tomas"),
        ]),
    ])]
    return actor_resource(
        index=index, symbol=TOMAS_SYMBOL, name="Hiroshi (Wind Ridge)", x=x, y=y,
        sprite_id=ridge.TOMAS_SPRITE_ID, key=key, script=script,
        start_script=[actor_state("$self$", "Waiting", f"{key}:waiting")],
    )


def concentrator_actor(index: int) -> dict[str, Any]:
    """Oxygen concentrator on the porch: Off until the door powers it On."""
    key = CONCENTRATOR_KEY
    x, y = ridge.CONCENTRATOR
    return actor_resource(
        index=index, symbol=CONCENTRATOR_SYMBOL, name="Oxygen Concentrator", x=x, y=y,
        sprite_id=ridge.CONCENTRATOR_SPRITE_ID, key=key,
        start_script=[actor_state("$self$", "Off", f"{key}:off")],
    )


def cable_end_actor(line: dict[str, Any], index: int, sprite_id: str,
                    pickup_sound_id: str) -> dict[str, Any]:
    """Dangling cable on its snapped pole. B picks it up with empty hands while its line is dead."""
    key = line["cable"]
    x, y = line["pole_at"]
    pickup = [if_value(VAR_CARRYING_CABLE, 0, f"{key}:empty-hands", [
        if_value(line["live_var"], 0, f"{key}:line-dead", [
            set_value(VAR_CARRYING_CABLE, line["number"], f"{key}:carry"),
            event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:hide"),
            sound_event(pickup_sound_id, f"{key}:sfx"),
            *say(short_lines("Got the cable!\nFind its box."), f"{key}:text"),
        ]),
    ], [
        *say(short_lines("Hands full!\nOne cable a trip."), f"{key}:hands-full"),
    ])]
    return actor_resource(
        index=index, symbol=line["cable_symbol"],
        name="Dangling Cable End" if line["key"] == "house" else f"Cable End ({line['key']})",
        x=x, y=y, sprite_id=sprite_id, key=key, script=pickup,
        start_script=[actor_state("$self$", "Dangling", f"{key}:dangling")],
    )


def pole_actor(line: dict[str, Any], index: int, sprite_id: str) -> dict[str, Any]:
    """A snapped pole: intro pole sprite, Standing once its line is repaired.

    Non-colliding and not interactive; the cable-end pickup owns the B press.
    """
    key = line["pole"]
    x, y = line["pole_at"]
    return actor_resource(
        index=index, symbol=line["pole_symbol"],
        name="Storm Pole" if line["key"] == "house" else f"Storm Pole ({line['key']})", x=x, y=y,
        sprite_id=sprite_id, key=key,
        start_script=[
            # Off, so B finds the cable end on this tile instead of the pole.
            event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:no-collision"),
            if_value(line["live_var"], 1, f"{key}:line-check", [
                actor_state("$self$", "Standing", f"{key}:standing"),
            ], [
                actor_state("$self$", "Snapped", f"{key}:snapped"),
            ]),
        ],
    )


def box_actor(line: dict[str, Any], index: int, sprite_id: str, connect_sound_id: str) -> dict[str, Any]:
    """A box (transformer or junction). Only its own line's cable plugs in.

    Plugging in repairs the line and stands its pole up; whether power reaches
    it depends on the lines upstream (chain_refresh_events).
    """
    key = line["box"]
    x, y = line["box_at"]
    # After chain_refresh_events, VAR_CHAIN_LIVE says how far power reaches.
    done = [if_value(ridge.VAR_CHAIN_LIVE, len(LINES), f"{key}:all", [
        *say(short_lines("All lines live!\nGo see Hiroshi."), f"{key}:text-all"),
    ], [
        if_at_least(ridge.VAR_CHAIN_LIVE, line["number"], f"{key}:lit", [
            *say(short_lines("Power flows on!\nKeep going."), f"{key}:text-lit"),
        ], [
            *say(short_lines("Fixed. No power\nfrom upstream."), f"{key}:text-dark"),
        ]),
    ])]
    plug = [if_value(line["live_var"], 1, f"{key}:live", [
        *say(short_lines("Already fixed."), f"{key}:already-live"),
    ], [
        if_value(VAR_CARRYING_CABLE, line["number"], f"{key}:has-cable", [
            set_value(VAR_CARRYING_CABLE, 0, f"{key}:clear-cable"),
            set_value(line["live_var"], 1, f"{key}:set-live"),
            event("EVENT_INC_VALUE", {"variable": VAR_LINES_LIVE}, f"{key}:count"),
            actor_state(actor_id(line["pole"]), "Standing", f"{key}:pole-standing"),
            *chain_refresh_events(f"{key}:chain"),
            sound_event(connect_sound_id, f"{key}:sfx"),
            *done,
        ], [
            if_value(VAR_CARRYING_CABLE, 0, f"{key}:no-cable-check", [
                *say(short_lines("No cable yet.\nFind its pole."), f"{key}:no-cable"),
            ], [
                *say(short_lines("Wrong cable\nfor this box."), f"{key}:wrong-cable"),
            ]),
        ]),
    ])]
    kind = "Transformer" if line["box_kind"] == "transformer" else "Junction Box"
    return actor_resource(
        index=index, symbol=line["box_symbol"],
        name="Junction Box (Ridge House)" if line["key"] == "house" else f"{kind} ({line['key']})",
        x=x, y=y, sprite_id=sprite_id, key=key, script=plug,
        start_script=[actor_state("$self$", "Dead", f"{key}:dead")],
    )


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Hiroshi's door: powering the house is a once-only checkpoint (var 9).

    Only the top row of a standing 24px hero covers the door columns, so the
    respawn tile in front of the door also lands on this trigger. The var 9
    guard keeps that from repeating the reward or the text.
    """
    x, y, width, height = ridge.DOOR_TRIGGER
    script = [if_value(VAR_LINES_LIVE, ridge.LINE_COUNT, "door:line", [
        if_value(VAR_HOME_POWERED, 0, "door:power-on", [
            set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
            sound_event(connect_sound_id, "door:sfx"),
            window_palette_event(True, "door:window-warm"),
            actor_state(actor_id(TOMAS_KEY), "Relieved", "door:tomas-relieved"),
            actor_state(actor_id(CONCENTRATOR_KEY), "On", "door:concentrator-on"),
            *say(short_lines("Power's on!\nI can breathe."), "door:text", "tomas"),
            *say(tickets.closed_lines(2), "door:closed"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix every line!"), "door:no-power"),
    ])]
    return {
        "_resourceType": "trigger",
        "id": ridge.resource_id("trigger:tomas-door"),
        "name": "Hiroshi Door Checkpoint",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": DOOR_TRIGGER_SYMBOL,
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": script,
        "leaveScript": [],
        "_index": 0,
    }


def hill_exit_trigger() -> dict[str, Any]:
    """Right end of Hiroshi's porch leads on to Priya's Signal Hill.

    Gated on Hiroshi's checkpoint (var 9). The refusal only explains: it never
    moves the hero, because a nudge plus leftover momentum re-entered the
    summit exit and looped its text (exact ROM 147c23be). Like the climb
    exits, it lifts the HUD cutoff and hides the overlay before switching.
    """
    x, y, width, height = rosa.RIDGE_EXIT
    go = [
        cutoff_event(150, "hill-exit:cutoff"),
        event("EVENT_OVERLAY_HIDE", {}, "hill-exit:hud-hide"),
        # Priya's work order first; its card switches on to Signal Hill's start.
        *tickets.to_work_order(3, "hill-exit", event, set_value, shared.number),
    ]
    wait = say(short_lines("Power Hiroshi's\nhouse first."), "hill-exit:not-yet")
    return {
        "_resourceType": "trigger",
        "id": ridge.resource_id("trigger:hill-exit"),
        "name": "Hill Exit (to Signal Hill)",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": "trigger_ridge_hill_exit",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": [if_value(rosa.RIDGE_EXIT_GATE_VAR, 1, "hill-exit:gate", go, wait)],
        "leaveScript": [],
        "_index": 1,
    }


# ---------------------------------------------------------------------------
# Cracked boards (hazards.py owns placement, IDs and timings)
# ---------------------------------------------------------------------------
# After the hill exit (0) and Hiroshi's door (1): the first matching trigger wins.
BOARD_TRIGGER_BASE_INDEX = 2


def board_actor(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y = hazards.board_actor_position(board)
    actor = actor_resource(
        index=index, symbol=f"ridge_board_{number:02d}", name=f"Cracked Board {number}",
        x=x, y=y, sprite_id=hazards.BOARD_SPRITE_ID, key=key,
        start_script=hazards.board_start_script(key, event),
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["updateScript"] = hazards.board_update_script(
        number, key, event, wait_event, if_value, set_value)
    return actor


def board_trigger(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y, width, height = hazards.board_trigger_rect(board)
    on_script, leave_script = hazards.board_trigger_scripts(number, f"{key}:trigger", set_value)
    return {
        "_resourceType": "trigger",
        "id": ridge.resource_id(f"trigger:{key}"),
        "name": f"Cracked Board {number} Stand",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": f"trigger_ridge_cracked_board_{number:02d}",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": on_script,
        "leaveScript": leave_script,
        "_index": index,
    }


def gust_actor(index: int, lane: tuple[int, int, int], start_delay: int,
               sprite_id: str) -> dict[str, Any]:
    """Timed wind lane: warning (no collision), burst (hits via group 1), rest.

    The start delay runs once. Update scripts loop, so the first cycle is
    detected by the actor's own direction: it starts "down", the first-cycle
    branch hides the gust, waits ``start_delay`` frames and sets it to "up",
    and later cycles skip the branch. The gust sprite has no directional
    animations, so the change should be invisible; verify in ROM.
    """
    row, x0, x1 = lane
    if x1 - x0 + 1 != 3:
        raise ValueError("the authored gust sprite is exactly three tiles wide")
    if start_delay < 0:
        raise ValueError("gust start delay must be non-negative")
    key = f"gust:{index}"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first_cycle_true = [
        own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
        own("EVENT_ACTOR_HIDE", "delay-hidden"),
    ]
    if start_delay > 0:
        first_cycle_true.append(wait_event(start_delay, f"{key}:start-delay"))
    first_cycle = branch_event(
        "EVENT_IF_ACTOR_DIRECTION",
        {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
        f"{key}:first-cycle",
        first_cycle_true,
    )
    update = [
        first_cycle,
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "warning-safe"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait_event(ridge.GUST_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "burst-state", spriteStateId="Burst", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "burst-active"),
        wait_event(ridge.GUST_ACTIVE_FRAMES, f"{key}:burst-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(ridge.GUST_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor_resource(
        index=index, symbol=f"ridge_gust_{index:02d}", name=f"Telegraphed Gust {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


def span_arc_actor(number: int, lane: tuple[int, int, int], start_delay: int,
                   sprite_id: str, live_after: int) -> dict[str, Any]:
    """Fallen-span arc: dark and safe until lines 1..``live_after`` are repaired, then
    Signal Hill's arc cycle.

    The first live cycle waits ``start_delay`` once (the gust's direction trick).
    """
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the authored live arc sprite is exactly two tiles wide")
    key = f"span-arc:{number}"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first_cycle_true = [
        own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
    ]
    if start_delay > 0:
        first_cycle_true.append(wait_event(start_delay, f"{key}:start-delay"))
    cycle = [
        branch_event("EVENT_IF_ACTOR_DIRECTION",
                     {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                     f"{key}:first-cycle", first_cycle_true),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait_event(rosa.ARC_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait_event(rosa.ARC_ACTIVE_FRAMES, f"{key}:arc-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(rosa.ARC_REST_FRAMES, f"{key}:rest-time"),
    ]
    update = [if_at_least(ridge.VAR_CHAIN_LIVE, live_after, f"{key}:upstream", cycle, [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "dead-safe"),
        own("EVENT_ACTOR_HIDE", "dead-hidden"),
        wait_event(1, f"{key}:dead-tick"),
    ])]
    return actor_resource(
        index=0, symbol=f"ridge_span_arc_{number:02d}", name=f"Downed Span Arc {number}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe"),
                      own("EVENT_ACTOR_HIDE", "initial-hidden")],
        update_script=update, collision_group="1",
    )


def whip_actor(number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
    """Wind-whipped live wire: hangs sparking, sways (safe warning), whips (hits), hangs.

    Always visible. Placed with its 16x32 canvas bottom on the floor's top row.
    """
    row, x0, x1 = lane
    if x1 - x0 + 1 != ridge.WHIP_CANVAS[0] // 8:
        raise ValueError("the whip lane is the sprite's width")
    key = f"whip:{number}"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first_cycle_true = [
        own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
    ]
    if start_delay > 0:
        first_cycle_true.append(wait_event(start_delay, f"{key}:start-delay"))
    update = [
        branch_event("EVENT_IF_ACTOR_DIRECTION",
                     {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                     f"{key}:first-cycle", first_cycle_true),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "sway-safe"),
        own("EVENT_ACTOR_SET_STATE", "sway-state", spriteStateId="Sway", loopAnim=True),
        wait_event(ridge.WHIP_SWAY_FRAMES, f"{key}:sway-time"),
        own("EVENT_ACTOR_SET_STATE", "swing-state", spriteStateId="Swing", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "swing-active"),
        wait_event(ridge.WHIP_SWING_FRAMES, f"{key}:swing-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "hang-safe"),
        own("EVENT_ACTOR_SET_STATE", "hang-state", spriteStateId="Hang", loopAnim=True),
        wait_event(ridge.WHIP_HANG_FRAMES, f"{key}:hang-time"),
    ]
    return actor_resource(
        index=0, symbol=f"ridge_whip_{number:02d}", name=f"Whipping Live Wire {number}",
        x=x0, y=row + 1, sprite_id=ridge.WHIP_SPRITE_ID, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe"),
                      own("EVENT_ACTOR_SET_STATE", "initial-hang", spriteStateId="Hang", loopAnim=True)],
        update_script=update, collision_group="1",
    )


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def build_scene(music_id: str, death_sound_id: str) -> dict[str, Any]:
    if (ridge.MAP_W, ridge.MAP_H) != (100, 30):
        raise ValueError("wind_ridge must match the 100x30 PLATFORM contract")
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Wind Ridge needs the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[ridge.TOMAS_SPRITE_PALETTE_SLOT] = tomas_palette_id()
    sprite_palette_ids[ridge.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
    # The intro pole sprite's tiles carry OBJ slot intro.SPRITE_SLOTS["pole"]; set it
    # here rather than inheriting it from the climb template.
    sprite_palette_ids[shared.POLE_SPRITE_PALETTE_SLOT] = intro.palette_id("pole")
    if hazards.BOARDS["wind_ridge"]:
        sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    # live_arc tiles carry slot 3 (Signal Hill's palette); the whip is ours, slot 6.
    sprite_palette_ids[ridge.ARC_SPRITE_PALETTE_SLOT] = rosa.resource_id("palette:sprite:arc")
    sprite_palette_ids[ridge.WHIP_SPRITE_PALETTE_SLOT] = ridge.WHIP_PALETTE_ID
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Wind Ridge background palettes must preserve the UI in slot 7")
    background_palette_ids[ridge.LINE_BG_SLOT] = chain_palette_id(0)

    scene = dict(template)
    scene.update({
        "id": ridge.SCENE_ID,
        "_index": SCENE_INDEX,
        "name": "Wind Ridge",
        "type": "PLATFORM",
        "width": ridge.MAP_W,
        "height": ridge.MAP_H,
        "x": SCENE_EDITOR_POSITION[0],
        "y": SCENE_EDITOR_POSITION[1],
        "collisions": shared.collision_rle(ridge.collision_grid(), ridge.MAP_W, ridge.MAP_H),
        "symbol": "scene_wind_ridge",
        "backgroundId": ridge.BACKGROUND_ID,
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "script": scene_script(music_id),
        "playerHit1Script": respawn_events("player-hit", death_sound_id),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def build_actors(sprite_ids: dict[str, str], audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    cable_sprite = climb.grid_resource_id(CABLE_SPRITE_KEY)
    box_sprites = {"junction": climb.grid_resource_id(JUNCTION_SPRITE_KEY),
                   "transformer": ridge.TRANSFORMER_SPRITE_ID}
    actors = [tomas_actor(0), concentrator_actor(1)]
    for line in LINES:
        # Pole before its cable end: higher indexes draw on top, so the cable
        # stays visible over the pole on their shared tile (cart bug B-13).
        actors += [
            pole_actor(line, 0, intro.POLE_SPRITE_ID),
            cable_end_actor(line, 0, cable_sprite, audio_ids["pickup"]),
            box_actor(line, 0, box_sprites[line["box_kind"]], audio_ids["connect"]),
        ]
    actors += [
        gust_actor(number, lane, delay, sprite_ids["gust"])
        for number, (lane, delay) in enumerate(zip(ridge.GUST_LANES, ridge.GUST_START_DELAYS), start=1)
    ]
    number = 0
    for span in ridge.FALLEN_SPANS:
        for lane, delay in zip(span["arcs"], span["delays"]):
            number += 1
            actors.append(span_arc_actor(number, lane, delay, sprite_ids["arc"], span["live_after"]))
    actors += [
        whip_actor(number, lane, delay)
        for number, (lane, delay) in enumerate(zip(ridge.WHIP_LANES, ridge.WHIP_START_DELAYS), start=1)
    ]
    # Cracked boards come last: the highest indexes draw on top.
    for number, board in enumerate(hazards.BOARDS["wind_ridge"], start=1):
        actors.append(board_actor(number, board, len(actors)))
    if len(actors) > ridge.MAX_SCENE_ACTORS:
        raise ValueError(f"{len(actors)} actors exceed the engine's {ridge.MAX_SCENE_ACTORS}")
    # Editor order is list order: actors and triggers are indexed by position.
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    # The exit must come first: the engine fires only the first trigger whose
    # tiles the hero's box overlaps, and at the right wall the hero overlaps
    # both the door (x35-37) and the exit (x38), so a door-first order made the
    # next job unreachable (Abe on the flashed cartridge, ROM 6bfec7b4).
    triggers = [hill_exit_trigger(), door_trigger(audio_ids["connect"])]
    triggers.extend(
        board_trigger(number, board, BOARD_TRIGGER_BASE_INDEX + number - 1)
        for number, board in enumerate(hazards.BOARDS["wind_ridge"], start=1)
    )
    for index, trigger in enumerate(triggers):
        trigger["_index"] = index
    return triggers


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Ridge variables without changing any existing entry.

    Same rule as make_climb_scene.merged_variables: an existing ID with a
    different name or symbol is refused rather than renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*ridge.VARIABLES, *hazards.VARIABLES):
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
        print("registered wind_ridge variables without changing existing variables")


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other workers produce these art files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def main() -> None:
    music_id = shared.sidecar_id(MUSIC_SIDECAR, "music")
    audio_ids = {
        "death": shared.sidecar_id(DEATH_SOUND, "sound"),
        "connect": shared.sidecar_id(CONNECT_SOUND, "sound"),
        "pickup": shared.sidecar_id(PICKUP_SOUND, "sound"),
    }
    sprite_ids = {
        "gust": shared.sidecar_id(GUST_SPRITE, "sprite"),
        "arc": shared.sidecar_id(ARC_SPRITE, "sprite"),
    }
    warn_if_missing_asset(ridge.WHIP_SPRITE_ID, "sprites", "whipping wire sprite")
    warn_if_missing_asset(ridge.TRANSFORMER_SPRITE_ID, "sprites", "transformer sprite")
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")
    warn_if_missing_asset(ridge.BACKGROUND_ID, "backgrounds", "wind_ridge background")
    warn_if_missing_asset(ridge.TOMAS_SPRITE_ID, "sprites", "Hiroshi sprite")
    warn_if_missing_asset(ridge.CONCENTRATOR_SPRITE_ID, "sprites", "oxygen concentrator sprite")

    scene = build_scene(music_id, audio_ids["death"])
    actors = build_actors(sprite_ids, audio_ids)
    triggers = build_triggers(audio_ids)

    write_variables()
    for relative_path, palette in tomas_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    shared.remove_retired_debris_actors(SCENE_DIR, prefix="ridge_")
    shared.write_json(SCENE_DIR / "scene.gbsres", scene)
    # This generator owns the whole scene folder: drop actors/triggers it no longer makes.
    for folder, items in (("actors", actors), ("triggers", triggers)):
        keep = {f"{item['symbol']}.gbsres" for item in items}
        for stale in (SCENE_DIR / folder).glob("*.gbsres"):
            if stale.name not in keep:
                stale.unlink()
                print(f"removed retired {folder[:-1]} {stale.name}")
        for item in items:
            shared.write_json(SCENE_DIR / folder / f"{item['symbol']}.gbsres", item)
    print(
        f"generated wind_ridge: {ridge.MAP_W}x{ridge.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{ridge.LINE_COUNT} lines, {len(ridge.GUST_LANES)} gusts, {len(ridge.span_arc_lanes())} span arcs, "
        f"{len(ridge.WHIP_LANES)} whip; "
        f"{len(hazards.BOARDS['wind_ridge'])} cracked board"
    )


if __name__ == "__main__":
    main()
