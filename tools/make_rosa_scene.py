"""Generate the deterministic Signal Hill scene (Rosa's repair job) from ``rosa.py``.

Run with ``python3 tools/make_rosa_scene.py`` from any working directory.
This writes only the Signal Hill scene resources, the Rosa and live-arc sprite
palettes and the Rosa variable registrations. The authored geometry, positions,
arc and gust timings and stable IDs live in the sibling ``rosa.py`` contract
module.

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
SCENE_DIR = PROJECT_DIR / "project" / "scenes" / "signal_hill"
CLIMB_SCENE = PROJECT_DIR / "project" / "scenes" / "storm_climb" / "scene.gbsres"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

# Editor placement and scene index: free in the project (wind_ridge is index 4 at 400,360).
SCENE_EDITOR_POSITION = (800, 360)
SCENE_INDEX = 5
MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import rosa  # noqa: E402  (Rosa's job contract: geometry, IDs, timings)
except ModuleNotFoundError as error:
    if error.name in {"climb", "opening", "rosa", "make_climb_scene"}:
        raise SystemExit(
            f"cannot generate signal_hill: tools/{error.name}.py is missing"
        ) from error
    raise

MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
VAR_CARRYING_CABLE = rosa.VAR_CARRYING_CABLE
VAR_LINE_LIVE = rosa.VAR_LINE_LIVE
VAR_HOME_POWERED = rosa.VAR_HOME_POWERED
ROSA_KEY = "rosa"
WORKSTATION_KEY = "workstation"
CABLE_KEY = "cable-end"
JUNCTION_KEY = "junction-box"
CABLE_SPRITE_KEY = "sprite:grid_cable_end"
JUNCTION_SPRITE_KEY = "sprite:grid_junction_box"
ROSA_SYMBOL = "signal_rosa"
WORKSTATION_SYMBOL = "signal_workstation"
CABLE_SYMBOL = "signal_cable_end"
JUNCTION_SYMBOL = "signal_junction_box"
DOOR_TRIGGER_SYMBOL = "trigger_signal_rosa_door"


# ---------------------------------------------------------------------------
# IDs and palette resources
# ---------------------------------------------------------------------------
def rosa_palette_id() -> str:
    return rosa.resource_id("palette:sprite:rosa")


def arc_palette_id() -> str:
    return rosa.resource_id("palette:sprite:arc")


def actor_id(key: str) -> str:
    return rosa.resource_id(f"actor:{key}")


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = "Signal Hill " + kind + " " + name
    return {
        "_resourceType": "palette",
        "id": rosa.resource_id(f"palette:{kind}:{name.replace(' ', '_').lower()}"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def rosa_palettes() -> list[tuple[str, dict[str, Any]]]:
    rosa_sprite = palette_resource("sprite", "rosa",
                                   shared.editor_sprite_colors(rosa.ROSA_SPRITE_HARDWARE))
    arc_sprite = palette_resource("sprite", "arc",
                                  shared.editor_sprite_colors(rosa.ARC_SPRITE_HARDWARE))
    return [
        ("project/palettes/signal_hill_sprite_rosa.gbsres", rosa_sprite),
        ("project/palettes/signal_hill_sprite_arc.gbsres", arc_sprite),
    ]


def metal_palette_id(live: bool) -> str:
    # Reuses the climb's metal palettes (already on disk); this job writes none.
    return climb.grid_resource_id("palette:bg:metal_live" if live else "palette:bg:metal_dead")


# ---------------------------------------------------------------------------
# Event builders (rosa-scoped IDs; EVENT_TEXT args copied from the climb)
# ---------------------------------------------------------------------------
def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": rosa.resource_id(f"event:{key}")}


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
        event("EVENT_TEXT_DRAW", {"text": rosa.HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
              f"{key}:counter"),
    ]


def say(lines: list[str], key: str) -> list[dict[str, Any]]:
    """In-play dialogue: lift the HUD's 16px cutoff so the box shows, then redraw the HUD.

    Exact-ROM play showed text behind the cutoff staying invisible while the
    script waited for A, freezing the player.
    """
    return [
        cutoff_event(150, f"{key}:say-cutoff"),
        text_event(lines, key),
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
    """Swap only Rosa's window slot (cold -> powered_window)."""
    name = "powered_window" if powered else "window"
    return background_palette_event({
        rosa.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}"),
    }, key)


def line_palette_event(live: bool, key: str) -> dict[str, Any]:
    """Swap only BG slot 5 (the drawn cable route) between dead and live metal."""
    return background_palette_event({rosa.LINE_BG_SLOT: metal_palette_id(live)}, key)


def actor_state(target: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_STATE", {
        "actorId": target, "spriteStateId": state, "loopAnim": loop,
    }, key)


def cable_drop_events(key: str) -> list[dict[str, Any]]:
    """A carried cable falls back to the pole when the carrier is hit."""
    return [if_value(VAR_CARRYING_CABLE, 1, f"{key}:cable-drop", [
        set_value(VAR_CARRYING_CABLE, 0, f"{key}:cable-clear"),
        event("EVENT_ACTOR_SHOW", {"actorId": actor_id(CABLE_KEY)}, f"{key}:cable-show"),
        actor_state(actor_id(CABLE_KEY), "Dangling", f"{key}:cable-dangling"),
        *hud_events(f"{key}:cable-hud"),
    ])]


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Death sound, then drop any cable, then respawn.

    The cable drop runs before repositioning so the carrier's hands are empty
    wherever the checkpoint sends them. Before Rosa's power is on the hero
    returns to START; afterwards, to the tile in front of the door.
    """
    door_x, door_y = rosa.HOUSE_DOOR
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *cable_drop_events(key),
        if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check", [
            set_position(*rosa.START, f"{key}:respawn-start"),
        ], [
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
        window_palette_event(False, "init-window-cold"),
        line_palette_event(False, "init-line-dead"),
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-signal-hill-music"),
        # Intro boxes after the music cue; say() lifts the cutoff a previous visit may have left.
        *say(short_lines("Rosa's offline!\nHer work is due."), "intro"),
        *say(short_lines("Mind the sparks!"), "spark"),
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


def rosa_actor(index: int) -> dict[str, Any]:
    """Rosa outside her door: Waiting until her house is powered, then Relieved."""
    key = ROSA_KEY
    x, y = rosa.ROSA
    script = [if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
        *say(short_lines("I'm back online!\nThank you!"), f"{key}:thanks"),
    ], [
        if_value(VAR_LINE_LIVE, 1, f"{key}:line", [
            *say(short_lines("Line's live!\nTry my door."), f"{key}:live"),
        ], [
            *say(short_lines("No internet...\nI can't work."), f"{key}:dead"),
        ]),
    ])]
    return actor_resource(
        index=index, symbol=ROSA_SYMBOL, name="Rosa (Signal Hill)", x=x, y=y,
        sprite_id=rosa.ROSA_SPRITE_ID, key=key, script=script,
        start_script=[actor_state("$self$", "Waiting", f"{key}:waiting")],
    )


def workstation_actor(index: int) -> dict[str, Any]:
    """Computer and router on Rosa's porch table: Off until the door switches them On."""
    key = WORKSTATION_KEY
    x, y = rosa.WORKSTATION
    return actor_resource(
        index=index, symbol=WORKSTATION_SYMBOL, name="Rosa Workstation", x=x, y=y,
        sprite_id=rosa.WORKSTATION_SPRITE_ID, key=key,
        start_script=[actor_state("$self$", "Off", f"{key}:off")],
    )


def cable_end_actor(index: int, sprite_id: str, pickup_sound_id: str) -> dict[str, Any]:
    """Dangling cable on the snapped pole. B picks it up while the line is dead."""
    key = CABLE_KEY
    x, y = rosa.DAMAGED_POLE
    pickup = [if_value(VAR_CARRYING_CABLE, 0, f"{key}:empty-hands", [
        if_value(VAR_LINE_LIVE, 0, f"{key}:line-dead", [
            set_value(VAR_CARRYING_CABLE, 1, f"{key}:carry"),
            event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:hide"),
            sound_event(pickup_sound_id, f"{key}:sfx"),
            *say(short_lines("Got the cable!\nTo the box ahead."), f"{key}:text"),
        ]),
    ])]
    return actor_resource(
        index=index, symbol=CABLE_SYMBOL, name="Dangling Cable End", x=x, y=y,
        sprite_id=sprite_id, key=key, script=pickup,
        start_script=[actor_state("$self$", "Dangling", f"{key}:dangling")],
    )


def junction_box_actor(index: int, sprite_id: str, connect_sound_id: str) -> dict[str, Any]:
    """Dead junction box at the foot of Rosa's porch. Plugging in the carried cable lights the line."""
    key = JUNCTION_KEY
    x, y = rosa.JUNCTION_BOX
    plug = [if_value(VAR_LINE_LIVE, 1, f"{key}:live", [
        *say(short_lines("Line is live."), f"{key}:already-live"),
    ], [
        if_value(VAR_CARRYING_CABLE, 1, f"{key}:has-cable", [
            set_value(VAR_CARRYING_CABLE, 0, f"{key}:clear-cable"),
            set_value(VAR_LINE_LIVE, 1, f"{key}:set-live"),
            actor_state("$self$", "Live", f"{key}:live-state"),
            line_palette_event(True, f"{key}:metal-live"),
            sound_event(connect_sound_id, f"{key}:sfx"),
            *say(short_lines("Line is live!\nGo see Rosa."), f"{key}:text"),
        ], [
            *say(short_lines("No cable yet.\nCheck the pole."), f"{key}:no-cable"),
        ]),
    ])]
    return actor_resource(
        index=index, symbol=JUNCTION_SYMBOL, name="Junction Box (Signal Hill)", x=x, y=y,
        sprite_id=sprite_id, key=key, script=plug,
        start_script=[actor_state("$self$", "Dead", f"{key}:dead")],
    )


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Rosa's door: powering the house is a once-only checkpoint (var 11).

    Only the top row of a standing 24px hero covers the door columns, so the
    respawn tile in front of the door also lands on this trigger. The var 11
    guard keeps that from repeating the reward or the text.
    """
    x, y, width, height = rosa.DOOR_TRIGGER
    script = [if_value(VAR_LINE_LIVE, 1, "door:line", [
        if_value(VAR_HOME_POWERED, 0, "door:power-on", [
            set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
            sound_event(connect_sound_id, "door:sfx"),
            window_palette_event(True, "door:window-warm"),
            actor_state(actor_id(ROSA_KEY), "Relieved", "door:rosa-relieved"),
            actor_state(actor_id(WORKSTATION_KEY), "On", "door:workstation-on"),
            *say(short_lines("Router's on!\nI'm online again."), "door:text"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix the line!"), "door:no-power"),
    ])]
    return {
        "_resourceType": "trigger",
        "id": rosa.resource_id("trigger:rosa-door"),
        "name": "Rosa Door Checkpoint",
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


def arc_actor(index: int, lane: tuple[int, int, int], start_delay: int,
              sprite_id: str) -> dict[str, Any]:
    """Live cable lane: warning sparks (no collision), arc (hits via group 1), rest.

    Same start-delay trick as the gust: the first cycle is detected by the
    actor's own direction (it starts "down"), the branch hides the arc and waits
    ``start_delay`` frames once, then sets the direction to "up" so later cycles
    skip the branch.
    """
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the authored live arc sprite is exactly two tiles wide")
    if start_delay < 0:
        raise ValueError("arc start delay must be non-negative")
    key = f"arc:{index}"

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
        wait_event(rosa.ARC_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait_event(rosa.ARC_ACTIVE_FRAMES, f"{key}:arc-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(rosa.ARC_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor_resource(
        index=index, symbol=f"signal_arc_{index:02d}", name=f"Live Arc {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


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
        wait_event(rosa.GUST_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "burst-state", spriteStateId="Burst", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "burst-active"),
        wait_event(rosa.GUST_ACTIVE_FRAMES, f"{key}:burst-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(rosa.GUST_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor_resource(
        index=index, symbol=f"signal_gust_{index:02d}", name=f"Telegraphed Gust {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def build_scene(music_id: str, death_sound_id: str) -> dict[str, Any]:
    if (rosa.MAP_W, rosa.MAP_H) != (40, 18):
        raise ValueError("signal_hill must match the 40x18 PLATFORM contract")
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Signal Hill needs the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[rosa.ROSA_SPRITE_PALETTE_SLOT] = rosa_palette_id()
    sprite_palette_ids[rosa.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
    sprite_palette_ids[rosa.ARC_SPRITE_PALETTE_SLOT] = arc_palette_id()
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Signal Hill background palettes must preserve the UI in slot 7")
    background_palette_ids[rosa.LINE_BG_SLOT] = metal_palette_id(False)

    scene = dict(template)
    scene.update({
        "id": rosa.SCENE_ID,
        "_index": SCENE_INDEX,
        "name": "Signal Hill",
        "type": "PLATFORM",
        "width": rosa.MAP_W,
        "height": rosa.MAP_H,
        "x": SCENE_EDITOR_POSITION[0],
        "y": SCENE_EDITOR_POSITION[1],
        "collisions": shared.collision_rle(rosa.collision_grid(), rosa.MAP_W, rosa.MAP_H),
        "symbol": "scene_signal_hill",
        "backgroundId": rosa.BACKGROUND_ID,
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "script": scene_script(music_id),
        "playerHit1Script": respawn_events("player-hit", death_sound_id),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def build_actors(sprite_ids: dict[str, str], audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    actors = [
        rosa_actor(0),
        workstation_actor(1),
        cable_end_actor(2, climb.grid_resource_id(CABLE_SPRITE_KEY), audio_ids["pickup"]),
        junction_box_actor(3, climb.grid_resource_id(JUNCTION_SPRITE_KEY), audio_ids["connect"]),
    ]
    actors.extend(
        arc_actor(index, lane, rosa.ARC_START_DELAYS[index - 1], rosa.ARC_SPRITE_ID)
        for index, lane in enumerate(rosa.ARC_LANES, start=1)
    )
    actors.extend(
        gust_actor(index, lane, rosa.GUST_START_DELAYS[index - 1], sprite_ids["gust"])
        for index, lane in enumerate(rosa.GUST_LANES, start=1)
    )
    # Editor order is list order: actors and triggers are indexed by position.
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    return [door_trigger(audio_ids["connect"])]


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Signal Hill variables without changing any existing entry.

    Same rule as make_ridge_scene.merged_variables: an existing ID with a
    different name or symbol is refused rather than renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in rosa.VARIABLES:
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
        print("registered signal_hill variables without changing existing variables")


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
    }
    warn_if_missing_asset(rosa.BACKGROUND_ID, "backgrounds", "signal_hill background")
    warn_if_missing_asset(rosa.ROSA_SPRITE_ID, "sprites", "Rosa sprite")
    warn_if_missing_asset(rosa.WORKSTATION_SPRITE_ID, "sprites", "Rosa workstation sprite")
    warn_if_missing_asset(rosa.ARC_SPRITE_ID, "sprites", "live arc sprite")

    scene = build_scene(music_id, audio_ids["death"])
    actors = build_actors(sprite_ids, audio_ids)
    triggers = build_triggers(audio_ids)

    write_variables()
    for relative_path, palette in rosa_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    shared.write_json(SCENE_DIR / "scene.gbsres", scene)
    for actor in actors:
        shared.write_json(SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres", actor)
    for trigger in triggers:
        shared.write_json(SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres", trigger)
    print(
        f"generated signal_hill: {rosa.MAP_W}x{rosa.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{len(rosa.ARC_LANES)} live arcs, delays {rosa.ARC_START_DELAYS}; "
        f"{len(rosa.GUST_LANES)} gust, delays {rosa.GUST_START_DELAYS}"
    )


if __name__ == "__main__":
    main()
