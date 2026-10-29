"""Generate the deterministic Pine Hollow scene (Emil's repair job) from ``kiko.py``.

Run with ``python3 tools/make_kiko_scene.py`` from any working directory.
This writes only the Pine Hollow scene resources, Emil's and hazard sprite
palettes, the chain palettes and the job variable registrations. Geometry,
positions, hazard timings and stable IDs live in the sibling ``kiko.py``
contract module.

The five-line grid chain comes from the reusable
``grid_chain`` module, built here with Pine Hollow's IDs, lines, variables,
dialogue and HUD. Stable pole and junction-box keys are retained; each cable end
is folded into its pole sprite, with no separate cable actor.

The live arc reuses Signal Hill's arc sprite and arc palette resource (written
by ``make_rosa_scene.py``); this generator only references that palette ID.
The hidden cable, gust, live arcs, fallen spans, whipping wire and cracked board
complete Pine Hollow's obstacle kit. The transformer reuses Wind Ridge's sprite.

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
SCENE_DIR = PROJECT_DIR / "project" / "scenes" / "pine_hollow"
CLIMB_SCENE = PROJECT_DIR / "project" / "scenes" / "storm_climb" / "scene.gbsres"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

# Editor placement and scene index: free in the project (signal_hill is index 5 at 800,360).
SCENE_EDITOR_POSITION = (1200, 360)
SCENE_INDEX = 6
MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import kiko  # noqa: E402  (Emil's job contract: geometry, IDs, timings)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import ridge  # noqa: E402  (shared transformer and whipping-wire assets)
    import voices  # noqa: E402  (speaker names and text blips)
    import rosa  # noqa: E402  (Signal Hill owns the live arc palette this job reuses)
    import tickets  # noqa: E402  (work orders: CLOSED box, report exit)
    import hazards  # noqa: E402  (hidden cable placement, IDs and timings)
except ModuleNotFoundError as error:
    if error.name in {"tickets", "intro", "voices", "climb", "kiko", "opening", "ridge", "rosa", "make_climb_scene",
                      "hazards", "grid_chain"}:
        raise SystemExit(
            f"cannot generate pine_hollow: tools/{error.name}.py is missing"
        ) from error
    raise

MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
VAR_CARRYING_CABLE = kiko.VAR_CARRYING_CABLE
VAR_LINE_LIVE = kiko.VAR_LINE_LIVE
VAR_HOME_POWERED = kiko.VAR_HOME_POWERED
VAR_FEEDER_LIVE = kiko.VAR_FEEDER_LIVE
VAR_LINES_LIVE = kiko.VAR_LINES_LIVE
VAR_CHAIN_LIVE = kiko.VAR_CHAIN_LIVE
KIKO_KEY = "kiko"
STOVE_KEY = "stove"
CABLE_KEY = "cable-end"
JUNCTION_KEY = "junction-box"
POLE_KEY = "pole"
POLE_SYMBOL = "kiko_storm_pole"
JUNCTION_SPRITE_KEY = "sprite:grid_junction_box"
KIKO_SYMBOL = "pine_kiko"
STOVE_SYMBOL = "pine_stove"
CABLE_SYMBOL = "pine_cable_end"
JUNCTION_SYMBOL = "pine_junction_box"
DOOR_TRIGGER_SYMBOL = "trigger_pine_home_door"

# The grid chain, upstream first (kiko.LINES). The feeder keeps the legacy pole
# and cable end (the mesa's actors); the house line keeps the legacy junction box.
_LINE_NAMES = {
    "feeder": {"pole": POLE_KEY, "cable": CABLE_KEY, "pole_symbol": POLE_SYMBOL,
               "cable_symbol": CABLE_SYMBOL, "pole_name": "Storm Pole",
               "cable_name": "Dangling Cable End", "box_name": "Transformer (Pine Hollow)"},
    "house": {"box": JUNCTION_KEY, "box_symbol": JUNCTION_SYMBOL,
              "box_name": "Junction Box (Pine Hollow)"},
}
LINES = []
for _line in kiko.LINES:
    _key = _line["key"]
    _kind = "Transformer" if _line["box_kind"] == "transformer" else "Junction Box"
    _default = {
        "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"box:{_key}",
        "pole_symbol": f"kiko_{_key}_pole", "cable_symbol": f"pine_{_key}_cable_end",
        "box_symbol": f"pine_{_key}_box",
        "pole_name": f"Storm Pole ({_key})", "cable_name": f"Cable End ({_key})",
        "box_name": f"{_kind} ({_key})",
    }
    # Coordinates move to pole_at/box_at: "pole"/"box" are actor keys here.
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"], **_default,
                  **_LINE_NAMES.get(_key, {})})


# ---------------------------------------------------------------------------
# IDs and palette resources
# ---------------------------------------------------------------------------
def kiko_palette_id() -> str:
    return kiko.resource_id("palette:sprite:kiko")


def arc_palette_id() -> str:
    # Signal Hill owns this palette resource; Pine Hollow reuses the same ID.
    return rosa.resource_id("palette:sprite:arc")


def actor_id(key: str) -> str:
    return kiko.resource_id(f"actor:{key}")


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = "Pine Hollow " + kind + " " + name
    return {
        "_resourceType": "palette",
        "id": kiko.resource_id(f"palette:{kind}:{name.replace(' ', '_').lower()}"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def kiko_palettes() -> list[tuple[str, dict[str, Any]]]:
    # The arc palette is Signal Hill's (make_rosa_scene.py); only Emil's and the chain's are written here.
    kiko_sprite = palette_resource("sprite", "kiko",
                                   shared.editor_sprite_colors(kiko.KIKO_SPRITE_HARDWARE))
    chain = grid_chain.chain_palette_resources(kiko.resource_id, label="Pine Hollow",
                                               file_prefix="pine_hollow", palettes=kiko.CHAIN_PALETTES)
    return [("project/palettes/pine_hollow_sprite_kiko.gbsres", kiko_sprite), *chain]


def chain_palette_id(stages_live: int) -> str:
    return CHAIN.chain_palette_id(stages_live)


# ---------------------------------------------------------------------------
# Event builders (kiko-scoped IDs; EVENT_TEXT args copied from the climb)
# ---------------------------------------------------------------------------
def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": kiko.resource_id(f"event:{key}")}


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
        event("EVENT_TEXT_DRAW", {"text": kiko.HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
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
    """Swap only Emil's window slot (cold -> powered_window)."""
    name = "powered_window" if powered else "window"
    return background_palette_event({
        kiko.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}"),
    }, key)


def actor_state(target: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_STATE", {
        "actorId": target, "spriteStateId": state, "loopAnim": loop,
    }, key)


# The reusable grid chain (tools/grid_chain.py) with Pine Hollow's IDs, lines,
# variables, dialogue and HUD. The aliases below keep this file's call sites.
CHAIN = grid_chain.GridChain(
    rid=kiko.resource_id, lines=LINES, chain_var=VAR_CHAIN_LIVE, lines_var=VAR_LINES_LIVE,
    carrying_var=VAR_CARRYING_CABLE, near_var=climb.VAR_NEAR, line_bg_slot=kiko.LINE_BG_SLOT,
    text=kiko.CHAIN_TEXT,
    say=say, hud=hud_events, bare_event_key="feeder",
)
pole_actor = CHAIN.pole_actor
box_actor = CHAIN.box_actor
actor_resource = CHAIN.actor_resource


def box_script_resources(audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return CHAIN.box_script_resources(label="Pine Hollow", file_prefix="pine_hollow",
                                      connect_sound_id=audio_ids["connect"])


def pole_actor_id() -> str:
    return actor_id(POLE_KEY)


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Death sound, then drop any cable, then respawn.

    The cable drop runs before repositioning so the carrier's hands are empty
    wherever the checkpoint sends them. Checkpoints, furthest first: the tile in
    front of the door once Emil's house is powered, then the checkpoint of the
    furthest repaired line, else START.
    """
    door_x, door_y = kiko.HOUSE_DOOR
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *shock.shock_events(key),
        *CHAIN.cable_drop_events(key),
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check",
                 CHAIN.checkpoint_chain(key, kiko.START), [
                     set_position(door_x - 1, door_y, f"{key}:respawn-door"),
                 ]),
    ]


# ---------------------------------------------------------------------------
# Scene init
# ---------------------------------------------------------------------------
def scene_script(music_id: str, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    return [
        event("EVENT_PLAYER_SET_SPRITE",
              {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
              "init-player-sprite"),
        event("EVENT_ACTOR_SET_DIRECTION",
              {"actorId": "player", "direction": {"type": "direction", "value": "right"}},
              "init-player-direction"),
        set_value(VAR_CARRYING_CABLE, 0, "init-carrying-cable"),
        set_value(climb.VAR_NEAR, grid_chain.NEAR_NONE, "init-near"),
        # B: pick up, plug in, drop or talk, by the zone the hero stands in (grid_chain).
        CHAIN.input_script_event(pickup_sound_id=audio_ids["pickup"],
                                 npc_events=kiko_talk_events("b-press:npc"),
                                 npc_actor_id=actor_id(KIKO_KEY), override=True),
        set_value(VAR_LINE_LIVE, 0, "init-line-live"),
        set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
        set_value(VAR_FEEDER_LIVE, 0, "init-feeder-live"),
        set_value(kiko.VAR_WEST_LIVE, 0, "init-west-live"),
        set_value(kiko.VAR_MIDDLE_LIVE, 0, "init-middle-live"),
        set_value(kiko.VAR_EAST_LIVE, 0, "init-east-live"),
        set_value(VAR_LINES_LIVE, 0, "init-lines-live"),
        set_value(VAR_CHAIN_LIVE, 0, "init-chain-live"),
        set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        window_palette_event(False, "init-window-cold"),
        *CHAIN.chain_refresh_events("init-chain"),
        # Pinned Snapped+Cable on every entry: each pole's own start script reads its
        # line variable, and the order between the scripts is unspecified.
        *[actor_state(actor_id(line["pole"]), "Snapped+Cable",
                      "init-pole-snapped" if line["key"] == "feeder" else f"init-{line['key']}-pole-snapped")
          for line in LINES],
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-pine-hollow-music"),
        # Intro boxes after the music cue; say() lifts the cutoff a previous visit may have left.
        *say(short_lines(f"{voices.name('kiko')}'s house is\ndark and hungry!"), "intro"),
        *say(short_lines("Fix 5 lines,\nthen soup!"), "intro-lines"),
        *say(short_lines("Dinner's cold..."), "cold"),
    ]


# ---------------------------------------------------------------------------
# Actors and triggers
# ---------------------------------------------------------------------------
def kiko_talk_events(key: str) -> list[dict[str, Any]]:
    """Emil's talk tree, dispatched by the scene's single B input script."""
    return [if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
        *say(short_lines("Dinner time!\nThank you!"), f"{key}:thanks", "kiko"),
    ], [
        if_value(VAR_LINES_LIVE, kiko.LINE_COUNT, f"{key}:lines", [
            *say(short_lines("All 5 lines live!\nTry our door."), f"{key}:live", "kiko"),
        ], [
            *say(short_lines("Stove's dead.\nMy tummy growls!"), f"{key}:dead", "kiko"),
        ]),
    ])]


def kiko_actor(index: int) -> dict[str, Any]:
    """Emil outside the house: Waiting until the house is powered, then Relieved."""
    key = KIKO_KEY
    x, y = kiko.KIKO
    script = kiko_talk_events(f"{key}:actor-talk")
    return actor_resource(
        index=index, symbol=KIKO_SYMBOL, name="Emil (Pine Hollow)", x=x, y=y,
        sprite_id=kiko.KIKO_SPRITE_ID, key=key, script=script,
        start_script=[actor_state("$self$", "Waiting", f"{key}:waiting")],
    )


def stove_actor(index: int, sprite_id: str) -> dict[str, Any]:
    """Electric stove on the porch: Off until the door switches it On."""
    key = STOVE_KEY
    x, y = kiko.STOVE
    return actor_resource(
        index=index, symbol=STOVE_SYMBOL, name="Electric Stove", x=x, y=y,
        sprite_id=sprite_id, key=key,
        start_script=[actor_state("$self$", "Off", f"{key}:off")],
    )


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Emil's door: powering the house is a once-only checkpoint (var 13).

    Only the top row of a standing 24px hero covers the door columns, so the
    respawn tile in front of the door also lands on this trigger. The var 13
    guard keeps that from repeating the reward or the text. The door needs all
    lines (the HUD count reads 5).
    """
    x, y, width, height = kiko.DOOR_TRIGGER
    script = [if_value(VAR_LINES_LIVE, kiko.LINE_COUNT, "door:lines", [
        if_value(VAR_HOME_POWERED, 0, "door:power-on", [
            set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
            sound_event(connect_sound_id, "door:sfx"),
            window_palette_event(True, "door:window-warm"),
            actor_state(actor_id(KIKO_KEY), "Relieved", "door:kiko-relieved"),
            actor_state(actor_id(STOVE_KEY), "On", "door:stove-on"),
            *say(short_lines("Stove's on!\nSoup party!"), "door:text", "kiko"),
            *say(tickets.closed_lines(4), "door:closed"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix all 5 lines!"), "door:no-power"),
    ])]
    return {
        "_resourceType": "trigger",
        "id": kiko.resource_id("trigger:kiko-door"),
        "name": "Emil Door Checkpoint",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": DOOR_TRIGGER_SYMBOL,
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": script,
        "leaveScript": [],
        "_index": 1,
    }


def report_exit_trigger() -> dict[str, Any]:
    """Right end of Emil's porch leads to the storm report, after his house is powered.

    Sorted before the door (first matching trigger wins, BUGS B-05). Lifts the
    HUD cutoff and hides the overlay before switching, like the other exits.
    """
    x, y, width, height = tickets.REPORT_EXIT
    hx, hy = tickets.HERO_POSITION
    go = [
        cutoff_event(150, "report-exit:cutoff"),
        event("EVENT_OVERLAY_HIDE", {}, "report-exit:hud-hide"),
        event("EVENT_SWITCH_SCENE", {
            "x": shared.number(hx), "y": shared.number(hy), "direction": "down",
            "sceneId": tickets.REPORT_SCENE_ID, "fadeSpeed": "2",
        }, "report-exit:to-report"),
    ]
    wait = say(short_lines("Power Emil's\nhouse first."), "report-exit:not-yet")
    return {
        "_resourceType": "trigger",
        "id": kiko.resource_id("trigger:report-exit"),
        "name": "Report Exit (to Storm Report)",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": "trigger_pine_report_exit",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": [if_value(tickets.REPORT_EXIT_GATE_VAR, 1, "report-exit:gate", go, wait)],
        "leaveScript": [],
        "_index": 0,
    }


def arc_actor(index: int, lane: tuple[int, int, int], start_delay: int,
              sprite_id: str) -> dict[str, Any]:
    """Live cable lane: warning sparks (no collision), arc (hits via group 1), rest.

    Same start-delay trick as the hidden cable: the first cycle is detected by the
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
        wait_event(kiko.ARC_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait_event(kiko.ARC_ACTIVE_FRAMES, f"{key}:arc-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(kiko.ARC_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor_resource(
        index=index, symbol=f"pine_arc_{index:02d}", name=f"Live Arc {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


def hidden_cable_actor(number: int, lane: tuple[int, int, int], start_delay: int,
                       index: int) -> dict[str, Any]:
    """Buried line on the mesa: no wire art, dark, a brief spark, then the arc (group 1)."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the live arc sprite is exactly two tiles wide")
    key = f"hidden-cable:{number}"
    return actor_resource(
        index=index, symbol=f"pine_hidden_cable_{number:02d}", name=f"Hidden Cable {number}",
        x=x0, y=row, sprite_id=rosa.ARC_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.cable_start_script(key, event),
        update_script=hazards.cable_update_script(key, start_delay, event, wait_event, branch_event),
        collision_group="1",
    )


def gust_actor(index: int, lane: tuple[int, int, int], start_delay: int,
               sprite_id: str) -> dict[str, Any]:
    """Timed wind lane: safe warning, active burst, and hidden rest."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 3:
        raise ValueError("the authored gust sprite is exactly three tiles wide")
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
        f"{key}:first-cycle", first_cycle_true,
    )
    update = [
        first_cycle,
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "warning-safe"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        wait_event(kiko.GUST_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "burst-state", spriteStateId="Burst", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "burst-active"),
        wait_event(kiko.GUST_ACTIVE_FRAMES, f"{key}:burst-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(kiko.GUST_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor_resource(
        index=index, symbol=f"pine_gust_{index:02d}", name=f"Telegraphed Gust {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


def whip_actor(number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
    row, x0, x1 = lane
    if x1 - x0 + 1 != ridge.WHIP_CANVAS[0] // 8:
        raise ValueError("the whip lane is the sprite's width")
    key = f"whip:{number}"
    return actor_resource(
        index=0, symbol=f"pine_whip_{number:02d}", name=f"Whipping Live Wire {number}",
        x=x0, y=row + 1, sprite_id=kiko.WHIP_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.whip_start_script(key, event),
        update_script=hazards.whip_update_script(
            key, start_delay, kiko.WHIP_SWAY_FRAMES, kiko.WHIP_SWING_FRAMES, kiko.WHIP_HANG_FRAMES,
            event, wait_event, branch_event),
        collision_group="1",
    )


def board_actor(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y = hazards.board_actor_position(board)
    actor = actor_resource(
        index=index, symbol=f"pine_board_{number:02d}", name=f"Cracked Board {number}",
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
        "_resourceType": "trigger", "id": kiko.resource_id(f"trigger:{key}"),
        "name": f"Cracked Board {number} Stand", "prefabId": "", "x": x, "y": y,
        "symbol": f"trigger_pine_cracked_board_{number:02d}", "prefabScriptOverrides": {},
        "width": width, "height": height, "script": on_script,
        "leaveScript": leave_script, "_index": index,
    }


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def build_scene(music_id: str, audio_ids: dict[str, str]) -> dict[str, Any]:
    if (kiko.MAP_W, kiko.MAP_H) != (100, 18):
        raise ValueError("pine_hollow must match the 100x18 PLATFORM contract")
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Pine Hollow needs the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[kiko.KIKO_SPRITE_PALETTE_SLOT] = kiko_palette_id()
    sprite_palette_ids[kiko.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
    sprite_palette_ids[kiko.ARC_SPRITE_PALETTE_SLOT] = arc_palette_id()
    sprite_palette_ids[intro.SPRITE_SLOTS["pole"]] = intro.palette_id("pole")
    sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    sprite_palette_ids[kiko.WHIP_SPRITE_PALETTE_SLOT] = kiko.WHIP_PALETTE_ID
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Pine Hollow background palettes must preserve the UI in slot 7")
    for slot, palette_id in CHAIN.chain_palette_ids(0).items():
        background_palette_ids[slot] = palette_id

    scene = dict(template)
    scene.update({
        "id": kiko.SCENE_ID,
        "_index": SCENE_INDEX,
        "name": "Pine Hollow",
        "type": "PLATFORM",
        "width": kiko.MAP_W,
        "height": kiko.MAP_H,
        "x": SCENE_EDITOR_POSITION[0],
        "y": SCENE_EDITOR_POSITION[1],
        "collisions": shared.collision_rle(kiko.collision_grid(), kiko.MAP_W, kiko.MAP_H),
        "symbol": "scene_pine_hollow",
        "backgroundId": kiko.BACKGROUND_ID,
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "script": scene_script(music_id, audio_ids),
        "playerHit1Script": respawn_events("player-hit", audio_ids["death"]),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def build_actors(audio_ids: dict[str, str], sprite_ids: dict[str, str] | None = None) -> list[dict[str, Any]]:
    if sprite_ids is None:
        sprite_ids = {"gust": shared.sidecar_id(GUST_SPRITE, "sprite")}
    box_sprites = {"junction": climb.grid_resource_id(JUNCTION_SPRITE_KEY),
                   "transformer": kiko.TRANSFORMER_SPRITE_ID}
    actors = [kiko_actor(0), stove_actor(1, kiko.STOVE_SPRITE_ID)]
    for line in LINES:
        # The snapped cable is part of the pole sprite; each line has one pole
        # actor and one box actor.
        actors += [
            pole_actor(line, 0, intro.POLE_SPRITE_ID),
            box_actor(line, 0, box_sprites[line["box_kind"]]),
        ]
    actors.extend(
        arc_actor(index, lane, kiko.ARC_START_DELAYS[index - 1], kiko.ARC_SPRITE_ID)
        for index, lane in enumerate(kiko.ARC_LANES, start=1)
    )
    actors.extend(
        gust_actor(index, lane, kiko.GUST_START_DELAYS[index - 1], sprite_ids["gust"])
        for index, lane in enumerate(kiko.GUST_LANES, start=1)
    )
    number = 0
    for span in kiko.FALLEN_SPANS:
        for lane, delay in zip(span["arcs"], span["delays"]):
            number += 1
            actors.append(CHAIN.span_arc_actor(
                number, lane, delay, kiko.ARC_SPRITE_ID, span["live_after"],
                timings=(kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES),
                symbol=f"pine_span_arc_{number:02d}", name=f"Downed Span Arc {number}",
            ))
    actors.extend(
        whip_actor(index, lane, kiko.WHIP_START_DELAYS[index - 1])
        for index, lane in enumerate(kiko.WHIP_LANES, start=1)
    )
    # Hidden cables come last: the highest indexes draw on top.
    for number, (lane, delay) in enumerate(
            zip(hazards.HIDDEN_CABLES["pine_hollow"], hazards.CABLE_START_DELAYS["pine_hollow"]),
            start=1):
        actors.append(hidden_cable_actor(number, lane, delay, len(actors)))
    for number, board in enumerate(hazards.BOARDS["pine_hollow"], start=1):
        actors.append(board_actor(number, board, len(actors)))
    if len(actors) > kiko.MAX_SCENE_ACTORS:
        raise ValueError(f"{len(actors)} actors exceed the engine's {kiko.MAX_SCENE_ACTORS}")
    # Editor order is list order: actors and triggers are indexed by position.
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    triggers = [report_exit_trigger(), door_trigger(audio_ids["connect"])]
    triggers.extend(
        board_trigger(number, board, index=0)
        for number, board in enumerate(hazards.BOARDS["pine_hollow"], start=1)
    )
    # Preserve the complete 5x3 box zones; Emil talk uses position predicates in B.
    triggers.extend(
        CHAIN.box_zone_trigger(line, symbol=f"trigger_pine_{line['key']}_reach", index=0)
        for line in LINES
    )
    triggers.extend(
        CHAIN.pole_zone_trigger(line, symbol=f"trigger_pine_{line['key']}_pole_zone", index=0)
        for line in LINES
    )
    for index, trigger in enumerate(triggers):
        trigger["_index"] = index
    return triggers


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Pine Hollow variables without changing any existing entry.

    Same rule as make_ridge_scene.merged_variables: an existing ID with a
    different name or symbol is refused rather than renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*kiko.VARIABLES, *hazards.VARIABLES, climb.NEAR_VARIABLE):
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
        print("registered pine_hollow variables without changing existing variables")


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
    sprite_ids = {"gust": shared.sidecar_id(GUST_SPRITE, "sprite")}
    warn_if_missing_asset(kiko.BACKGROUND_ID, "backgrounds", "pine_hollow background")
    warn_if_missing_asset(kiko.KIKO_SPRITE_ID, "sprites", "Emil sprite")
    warn_if_missing_asset(kiko.STOVE_SPRITE_ID, "sprites", "electric stove sprite")
    warn_if_missing_asset(kiko.ARC_SPRITE_ID, "sprites", "live arc sprite")
    warn_if_missing_asset(kiko.TRANSFORMER_SPRITE_ID, "sprites", "transformer sprite")
    warn_if_missing_asset(kiko.WHIP_SPRITE_ID, "sprites", "whipping wire sprite")
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")

    scene = build_scene(music_id, audio_ids)
    actors = build_actors(audio_ids, sprite_ids)
    triggers = build_triggers(audio_ids)

    write_variables()
    for relative_path, palette in kiko_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for relative_path, script in box_script_resources(audio_ids):
        shared.write_json(PROJECT_DIR / relative_path, script)
    shared.remove_retired_debris_actors(SCENE_DIR, prefix="pine_")
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
        f"generated pine_hollow: {kiko.MAP_W}x{kiko.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{len(kiko.LINES)} lines, {len(hazards.HIDDEN_CABLES['pine_hollow'])} hidden cable, "
        f"{len(kiko.ARC_LANES)} live arc, delays {kiko.ARC_START_DELAYS}"
    )


if __name__ == "__main__":
    main()
