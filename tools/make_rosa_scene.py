"""Generate the deterministic Signal Hill scene (Priya's repair job) from ``rosa.py``.

Run with ``python3 tools/make_rosa_scene.py`` from any working directory.
This writes only the Signal Hill scene resources, Priya and hazard sprite
palettes, the chain's background palettes and job variable registrations.
Geometry, positions, hazard timings and stable IDs live in
the sibling ``rosa.py`` contract module.

The grid chain's events, actors and palettes come from the reusable
``grid_chain`` module, built here with Signal Hill's ID function, lines,
variables, dialogue and HUD. The boxes are background transformers
(``rosa.BACKGROUND_BOXES``, drawn by ``make_rosa_art.py``), so each line has one
pole actor and the freed actors are spent on hazards.

Generic GB Studio helpers (collision RLE, sidecar lookup, JSON writing, the
dialogue length check) are reused from ``make_climb_scene``.
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
WHIP_SPRITE = "assets/sprites/whip_wire.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import ridge  # noqa: E402  (whip sprite: Wind Ridge's asset, reused here)
    import voices  # noqa: E402  (speaker names and text blips)
    import rosa  # noqa: E402  (Priya's job contract: geometry, IDs, timings)
    import tickets  # noqa: E402  (work orders: exit to ticket 4, CLOSED box)
    import kiko  # noqa: E402  (Emil's job contract: the porch exit leads there)
    import hazards  # noqa: E402  (hidden cable, cracked board and whip helpers)
except ModuleNotFoundError as error:
    if error.name in {"grid_chain", "intro", "tickets", "voices", "climb", "opening", "ridge", "rosa",
                       "kiko", "make_climb_scene", "hazards"}:
        raise SystemExit(
            f"cannot generate signal_hill: tools/{error.name}.py is missing"
        ) from error
    raise

MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
VAR_CARRYING_CABLE = rosa.VAR_CARRYING_CABLE
VAR_LINE_LIVE = rosa.VAR_LINE_LIVE
VAR_HOME_POWERED = rosa.VAR_HOME_POWERED
VAR_LINES_LIVE = rosa.VAR_LINES_LIVE
VAR_CHAIN_LIVE = rosa.VAR_CHAIN_LIVE
ROSA_KEY = "rosa"
WORKSTATION_KEY = "workstation"
POLE_KEY = "pole"
POLE_SYMBOL = "rosa_storm_pole"
ROSA_SYMBOL = "signal_rosa"
WORKSTATION_SYMBOL = "signal_workstation"
DOOR_TRIGGER_SYMBOL = "trigger_signal_rosa_door"

# The grid chain, upstream first (rosa.LINES). The house line keeps the original
# job's keys, symbols and names (stable IDs); the feeder line is new.
_LINE_NAMES = {
    "feeder": {"pole": "pole:feeder", "cable": "cable-end:feeder", "box": "transformer:feeder",
               "pole_symbol": "rosa_feeder_pole", "cable_symbol": "signal_feeder_cable_end",
               "box_symbol": "signal_feeder_transformer", "pole_name": "Feeder Pole",
               "cable_name": "Cable End (feeder)", "box_name": "Transformer (feeder)"},
    "house": {"pole": POLE_KEY, "cable": "cable-end", "box": "junction-box",
              "pole_symbol": POLE_SYMBOL, "cable_symbol": "signal_cable_end",
              "box_symbol": "signal_junction_box", "pole_name": "Storm Pole",
              "cable_name": "Dangling Cable End", "box_name": "Junction Box (Signal Hill)"},
}
LINES = []
for _line in rosa.LINES:
    # Coordinates move to pole_at/box_at: "pole"/"box" are actor keys here.
    _key = _line["key"]
    _kind = "Transformer" if _line["box_kind"] == "transformer" else "Junction Box"
    _default = {
        "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"box:{_key}",
        "pole_symbol": f"signal_{_key}_pole", "cable_symbol": f"signal_{_key}_cable_end",
        "box_symbol": f"signal_{_key}_box", "pole_name": f"Storm Pole ({_key})",
        "cable_name": f"Cable End ({_key})", "box_name": f"{_kind} ({_key})",
    }
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"],
                  **_default, **_LINE_NAMES.get(_key, {})})
LINE_BY_KEY = {line["key"]: line for line in LINES}

# Dialogue for the chain's cable ends and boxes (grid_chain.GridChain text keys).
ROSA_TEXT = {
    "pickup": "Got the cable!\nFind its box.",
    "hands_full": "Hands full!\nOne cable a trip.",
    "already": "Already fixed.",
    "all_live": "All 5 lines live!\nGo see Priya.",
    "lit": "Power flows on!\nKeep going.",
    "dark": "Fixed. No power\nfrom upstream.",
    "no_cable": "No cable yet.\nFind its pole.",
    "wrong_cable": "Wrong cable\nfor this box.",
}


# ---------------------------------------------------------------------------
# IDs and palette resources
# ---------------------------------------------------------------------------
def rosa_palette_id() -> str:
    return rosa.resource_id("palette:sprite:rosa")


def arc_palette_id() -> str:
    return rosa.resource_id("palette:sprite:arc")


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    return grid_chain.palette_resource(rosa.resource_id, "Signal Hill", kind, name, colors)


def rosa_palettes() -> list[tuple[str, dict[str, Any]]]:
    rosa_sprite = palette_resource("sprite", "rosa",
                                   shared.editor_sprite_colors(rosa.ROSA_SPRITE_HARDWARE))
    arc_sprite = palette_resource("sprite", "arc",
                                  shared.editor_sprite_colors(rosa.ARC_SPRITE_HARDWARE))
    chain = grid_chain.chain_palette_resources(rosa.resource_id, label="Signal Hill",
                                               file_prefix="signal_hill", palettes=rosa.CHAIN_PALETTES)
    return [
        ("project/palettes/signal_hill_sprite_rosa.gbsres", rosa_sprite),
        ("project/palettes/signal_hill_sprite_arc.gbsres", arc_sprite),
        *chain,
    ]


def chain_palette_id(stages_live: int) -> str:
    return grid_chain.chain_palette_id(rosa.resource_id, stages_live)


# ---------------------------------------------------------------------------
# Dialogue and HUD builders (Signal Hill-scoped IDs; EVENT_TEXT args copied from the climb)
# ---------------------------------------------------------------------------
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


# The reusable grid chain (tools/grid_chain.py) with Signal Hill's IDs, lines,
# variables, dialogue and HUD. The aliases below keep this file's call sites.
CHAIN = grid_chain.GridChain(
    rid=rosa.resource_id, lines=LINES, chain_var=VAR_CHAIN_LIVE, lines_var=VAR_LINES_LIVE,
    carrying_var=VAR_CARRYING_CABLE, near_var=climb.VAR_NEAR, line_bg_slot=rosa.LINE_BG_SLOT,
    text=ROSA_TEXT, say=say, hud=hud_events, bare_event_key="house",
    background_boxes=rosa.BACKGROUND_BOXES,
)
event = CHAIN.event
branch_event = CHAIN.branch_event
if_value = CHAIN.if_value
set_value = CHAIN.set_value
set_position = CHAIN.set_position
background_palette_event = CHAIN.background_palette_event
sound_event = CHAIN.sound_event
wait_event = CHAIN.wait_event
actor_state = CHAIN.actor_state
actor_id = CHAIN.actor_id
actor_resource = CHAIN.actor_resource
chain_refresh_events = CHAIN.chain_refresh_events
cable_drop_events = CHAIN.cable_drop_events
pole_actor = CHAIN.pole_actor


def box_script_resources(audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return CHAIN.box_script_resources(label="Signal Hill", file_prefix="signal_hill",
                                      connect_sound_id=audio_ids["connect"])


def window_palette_event(powered: bool, key: str) -> dict[str, Any]:
    """Swap only Priya's window slot (cold -> powered_window)."""
    name = "powered_window" if powered else "window"
    return background_palette_event({
        rosa.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}"),
    }, key)


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Death sound, then drop any cable, then respawn.

    The cable drop runs before repositioning so the carrier's hands are empty
    wherever the checkpoint sends them. Checkpoints, furthest first: the tile in
    front of Priya's door once her power is on, then the checkpoint of the
    furthest repaired line, else START.
    """
    door_x, door_y = rosa.HOUSE_DOOR
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *shock.shock_events(key),
        *cable_drop_events(key),
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check", CHAIN.checkpoint_chain(key, rosa.START), [
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
                                 npc_events=rosa_talk_events("b-press:npc"),
                                 npc_actor_id=actor_id(ROSA_KEY), override=True),
        set_value(VAR_LINE_LIVE, 0, "init-line-live"),
        set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
        set_value(rosa.VAR_FEEDER_LIVE, 0, "init-feeder-live"),
        set_value(rosa.VAR_WEST_LIVE, 0, "init-west-live"),
        set_value(rosa.VAR_MIDDLE_LIVE, 0, "init-middle-live"),
        set_value(rosa.VAR_EAST_LIVE, 0, "init-east-live"),
        set_value(VAR_LINES_LIVE, 0, "init-lines-live"),
        set_value(VAR_CHAIN_LIVE, 0, "init-chain-live"),
        set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        window_palette_event(False, "init-window-cold"),
        *chain_refresh_events("init-chain"),
        # Pinned Snapped+Cable on every entry: each pole's own start script reads its
        # line variable, and the order between the scripts is unspecified.
        *[actor_state(actor_id(line["pole"]), "Snapped+Cable",
                      "init-pole-snapped" if line["key"] == "house" else f"init-{line['key']}-pole-snapped")
          for line in LINES],
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-signal-hill-music"),
        # Intro boxes after the music cue; say() lifts the cutoff a previous visit may have left.
        *say(short_lines("Priya's offline.\nDeadline: now!"), "intro"),
        *say(short_lines("Sparks bite. Hop!"), "spark"),
    ]


# ---------------------------------------------------------------------------
# Actors and triggers
# ---------------------------------------------------------------------------
def rosa_talk_events(key: str) -> list[dict[str, Any]]:
    """Priya's talk tree, dispatched by the scene's single B input script."""
    return [if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
        *say(short_lines("Back online!\nYou're a star!"), f"{key}:thanks", "rosa"),
    ], [
        if_value(VAR_LINES_LIVE, rosa.LINE_COUNT, f"{key}:lines", [
            *say(short_lines("Five lines live!\nTry my door."), f"{key}:live", "rosa"),
        ], [
            *say(short_lines("No wifi, no work.\nSend help!"), f"{key}:dead", "rosa"),
        ]),
    ])]


def rosa_actor(index: int) -> dict[str, Any]:
    """Priya outside her door: Waiting until her house is powered, then Relieved."""
    key = ROSA_KEY
    x, y = rosa.ROSA
    script = rosa_talk_events(f"{key}:actor-talk")
    return actor_resource(
        index=index, symbol=ROSA_SYMBOL, name="Priya (Signal Hill)", x=x, y=y,
        sprite_id=rosa.ROSA_SPRITE_ID, key=key, script=script,
        start_script=[actor_state("$self$", "Waiting", f"{key}:waiting")],
    )


def workstation_actor(index: int) -> dict[str, Any]:
    """Computer and router on Priya's porch table: Off until the door switches them On."""
    key = WORKSTATION_KEY
    x, y = rosa.WORKSTATION
    return actor_resource(
        index=index, symbol=WORKSTATION_SYMBOL, name="Priya Workstation", x=x, y=y,
        sprite_id=rosa.WORKSTATION_SPRITE_ID, key=key,
        start_script=[actor_state("$self$", "Off", f"{key}:off")],
    )


def pole_actor_id() -> str:
    return actor_id(POLE_KEY)


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Priya's door: powering the house is a once-only checkpoint (var 11).

    Only the top row of a standing 24px hero covers the door columns, so the
    respawn tile in front of the door also lands on this trigger. The var 11
    guard keeps that from repeating the reward or the text. All five lines must
    be repaired (the HUD count) before the house can power on.
    """
    x, y, width, height = rosa.DOOR_TRIGGER
    script = [if_value(VAR_LINES_LIVE, rosa.LINE_COUNT, "door:lines", [
        if_value(VAR_HOME_POWERED, 0, "door:power-on", [
            set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
            sound_event(connect_sound_id, "door:sfx"),
            window_palette_event(True, "door:window-warm"),
            actor_state(actor_id(ROSA_KEY), "Relieved", "door:rosa-relieved"),
            actor_state(actor_id(WORKSTATION_KEY), "On", "door:workstation-on"),
            *say(short_lines("Router's alive!\nEmail, here I go!"), "door:text", "rosa"),
            *say(tickets.closed_lines(3), "door:closed"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix all 5 lines!"), "door:no-power"),
    ])]
    return {
        "_resourceType": "trigger",
        "id": rosa.resource_id("trigger:rosa-door"),
        "name": "Priya Door Checkpoint",
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


def hollow_exit_trigger() -> dict[str, Any]:
    """Right end of Priya's porch leads on to Emil's Pine Hollow.

    Gated on Priya's checkpoint (var 11). The refusal only explains: a nudge
    plus leftover momentum re-entered the summit exit and looped its text
    (exact ROM 147c23be). Lifts the HUD cutoff and hides the overlay first.
    """
    x, y, width, height = kiko.HILL_EXIT
    go = [
        cutoff_event(150, "hollow-exit:cutoff"),
        event("EVENT_OVERLAY_HIDE", {}, "hollow-exit:hud-hide"),
        # Emil's work order first; its card switches on to Pine Hollow's start.
        *tickets.to_work_order(4, "hollow-exit", event, set_value, shared.number),
    ]
    wait = say(short_lines("Power Priya's\nhouse first."), "hollow-exit:not-yet")
    return {
        "_resourceType": "trigger",
        "id": rosa.resource_id("trigger:hollow-exit"),
        "name": "Hollow Exit (to Pine Hollow)",
        "prefabId": "",
        "x": x,
        "y": y,
        "symbol": "trigger_signal_hollow_exit",
        "prefabScriptOverrides": {},
        "width": width,
        "height": height,
        "script": [if_value(kiko.HILL_EXIT_GATE_VAR, 1, "hollow-exit:gate", go, wait)],
        "leaveScript": [],
        "_index": 1,
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
        wait_event(rosa.JOB_ARC_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        wait_event(rosa.JOB_ARC_ACTIVE_FRAMES, f"{key}:arc-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        wait_event(rosa.JOB_ARC_REST_FRAMES, f"{key}:rest-time"),
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


def whip_actor(number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
    """Wind-whipped wire: safe sway telegraph, then a brief collision swing."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != ridge.WHIP_CANVAS[0] // 8:
        raise ValueError("the whip lane is the sprite's width")
    key = f"whip:{number}"
    return actor_resource(
        index=0, symbol=f"signal_whip_{number:02d}", name=f"Whipping Live Wire {number}",
        x=x0, y=row + 1, sprite_id=ridge.WHIP_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.whip_start_script(key, event),
        update_script=hazards.whip_update_script(
            key, start_delay, rosa.WHIP_SWAY_FRAMES, rosa.WHIP_SWING_FRAMES, rosa.WHIP_HANG_FRAMES,
            event, wait_event, branch_event),
        collision_group="1",
    )


def hidden_cable_actor(number: int, lane: tuple[int, int, int], start_delay: int,
                       index: int) -> dict[str, Any]:
    """Buried live cable: hidden, briefly sparks, then arcs (OBJ palette slot 3)."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the live arc sprite is exactly two tiles wide")
    key = f"hidden-cable:{number}"
    return actor_resource(
        index=index, symbol=f"signal_hidden_cable_{number:02d}", name=f"Hidden Cable {number}",
        x=x0, y=row, sprite_id=rosa.ARC_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.cable_start_script(key, event),
        update_script=hazards.cable_update_script(key, start_delay, event, wait_event, branch_event),
        collision_group="1",
    )


def board_actor(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    """Cracked board whose idle plank is background art: the actor only shows while it creaks.

    Wind Ridge's board (make_ridge_scene.board_actor) with Signal Hill's IDs:
    hazards.py timings and trigger, hidden when idle so boards cost no OBJs until
    the hero stands on one.
    """
    key = f"board:{number}"
    x, y = hazards.board_actor_position(board)

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    give_way = [
        own("EVENT_ACTOR_SET_STATE", "break-state", spriteStateId="Break", loopAnim=False),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "break-hit"),
        wait_event(hazards.BREAK_FRAMES, f"{key}:break-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "break-safe"),
        # The respawn teleports the hero without a leave event; clear it here.
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear"),
        wait_event(hazards.BOARD_REST_FRAMES, f"{key}:rest-time"),
    ]
    creak = [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "creak-safe"),
        own("EVENT_ACTOR_SET_STATE", "creak-state", spriteStateId="Creak", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "creak-visible"),
        wait_event(hazards.CREAK_FRAMES, f"{key}:creak-time"),
        if_value(hazards.VAR_ON_BOARD, number, f"{key}:still-on", give_way, []),
        own("EVENT_ACTOR_SET_STATE", "idle-state", spriteStateId="Idle", loopAnim=True),
        own("EVENT_ACTOR_HIDE", "idle-hidden"),
    ]
    actor = actor_resource(
        index=index, symbol=f"signal_board_{number:02d}", name=f"Cracked Board {number}",
        x=x, y=y, sprite_id=hazards.BOARD_SPRITE_ID, key=key,
        start_script=[*hazards.board_start_script(key, event), own("EVENT_ACTOR_HIDE", "init-hidden")],
        update_script=[if_value(hazards.VAR_ON_BOARD, number, f"{key}:on-check", creak,
                                [wait_event(1, f"{key}:idle-tick")])],
        collision_group="1",
    )
    actor["animate"] = True
    return actor


def board_trigger(number: int, board: tuple[int, int, int], index: int) -> dict[str, Any]:
    key = f"board:{number}"
    x, y, width, height = hazards.board_trigger_rect(board)
    on_script, leave_script = hazards.board_trigger_scripts(number, f"{key}:trigger", set_value)
    return {
        "_resourceType": "trigger", "id": rosa.resource_id(f"trigger:{key}"),
        "name": f"Cracked Board {number} Stand", "prefabId": "", "x": x, "y": y,
        "symbol": f"trigger_signal_cracked_board_{number:02d}", "prefabScriptOverrides": {},
        "width": width, "height": height, "script": on_script,
        "leaveScript": leave_script, "_index": index,
    }


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def build_scene(music_id: str, audio_ids: dict[str, str]) -> dict[str, Any]:
    if (rosa.MAP_W, rosa.MAP_H) != (100, 18):
        raise ValueError("signal_hill must match the 100x18 PLATFORM contract")
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Signal Hill needs the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[rosa.ROSA_SPRITE_PALETTE_SLOT] = rosa_palette_id()
    sprite_palette_ids[rosa.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
    sprite_palette_ids[rosa.ARC_SPRITE_PALETTE_SLOT] = arc_palette_id()
    sprite_palette_ids[intro.SPRITE_SLOTS["pole"]] = intro.palette_id("pole")
    sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    sprite_palette_ids[ridge.WHIP_SPRITE_PALETTE_SLOT] = ridge.WHIP_PALETTE_ID
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Signal Hill background palettes must preserve the UI in slot 7")
    for slot, palette_id in CHAIN.chain_palette_ids(0).items():
        background_palette_ids[slot] = palette_id

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
        "script": scene_script(music_id, audio_ids),
        "playerHit1Script": respawn_events("player-hit", audio_ids["death"]),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def build_actors(sprite_ids: dict[str, str], audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    actors = [rosa_actor(0), workstation_actor(1)]
    # The snapped cable is part of the pole sprite; the boxes are background
    # transformers (rosa.BACKGROUND_BOXES), so each line has one pole actor.
    actors += [pole_actor(line, 0, intro.POLE_SPRITE_ID) for line in LINES]
    actors += [
        arc_actor(index, lane, rosa.ARC_START_DELAYS[index - 1], rosa.ARC_SPRITE_ID)
        for index, lane in enumerate(rosa.ARC_LANES, start=1)
    ]
    actors += [
        gust_actor(index, lane, rosa.GUST_START_DELAYS[index - 1], sprite_ids["gust"])
        for index, lane in enumerate(rosa.GUST_LANES, start=1)
    ]
    number = 0
    for span in rosa.FALLEN_SPANS:
        for lane, delay in zip(span["arcs"], span["delays"]):
            number += 1
            actors.append(CHAIN.span_arc_actor(
                number, lane, delay, rosa.ARC_SPRITE_ID, span["live_after"],
                timings=(rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES),
                symbol=f"signal_span_arc_{number:02d}", name=f"Downed Span Arc {number}",
            ))
    actors += [
        whip_actor(index, lane, rosa.WHIP_START_DELAYS[index - 1])
        for index, lane in enumerate(rosa.WHIP_LANES, start=1)
    ]
    for number, (lane, delay) in enumerate(
            zip(hazards.HIDDEN_CABLES["signal_hill"], hazards.CABLE_START_DELAYS["signal_hill"]), start=1):
        actors.append(hidden_cable_actor(number, lane, delay, len(actors)))
    # Cracked boards come last: the highest indexes draw on top.
    for number, board in enumerate(hazards.BOARDS["signal_hill"], start=1):
        actors.append(board_actor(number, board, len(actors)))
    if len(actors) != rosa.actor_count():
        raise ValueError(f"{len(actors)} actors built, expected {rosa.actor_count()}")
    if len(actors) > rosa.MAX_SCENE_ACTORS:
        raise ValueError(f"{len(actors)} actors exceed the engine's {rosa.MAX_SCENE_ACTORS}")
    # Editor order is list order: actors and triggers are indexed by position.
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    # The exit must come first: the engine fires only the first trigger whose
    # tiles the hero's box overlaps, and at the right wall the hero overlaps
    # both the door (x35-37) and the exit (x38), so a door-first order made the
    # next job unreachable (Abe on the flashed cartridge, ROM 6bfec7b4).
    triggers = [hollow_exit_trigger(), door_trigger(audio_ids["connect"])]
    # Preserve the complete 5x3 box zones; Priya talk uses position predicates in B.
    triggers.extend(
        board_trigger(number, board, index=0)
        for number, board in enumerate(hazards.BOARDS["signal_hill"], start=1)
    )
    triggers.extend(
        CHAIN.box_zone_trigger(line, symbol=f"trigger_signal_{line['key']}_reach", index=0)
        for line in LINES
    )
    triggers.extend(
        CHAIN.pole_zone_trigger(line, symbol=f"trigger_signal_{line['key']}_pole_zone", index=0)
        for line in LINES
    )
    for index, trigger in enumerate(triggers):
        trigger["_index"] = index
    return triggers


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Signal Hill variables without changing any existing entry.

    Same rule as make_climb_scene.merged_variables: an existing ID with a
    different name or symbol is refused rather than renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*rosa.VARIABLES, *hazards.VARIABLES, climb.NEAR_VARIABLE):
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
    warn_if_missing_asset(rosa.ROSA_SPRITE_ID, "sprites", "Priya sprite")
    warn_if_missing_asset(rosa.WORKSTATION_SPRITE_ID, "sprites", "Priya workstation sprite")
    warn_if_missing_asset(rosa.ARC_SPRITE_ID, "sprites", "live arc sprite")
    warn_if_missing_asset(ridge.WHIP_SPRITE_ID, "sprites", "whipping wire sprite")
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")

    scene = build_scene(music_id, audio_ids)
    actors = build_actors(sprite_ids, audio_ids)
    triggers = build_triggers(audio_ids)

    write_variables()
    for relative_path, palette in rosa_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for relative_path, script in box_script_resources(audio_ids):
        shared.write_json(PROJECT_DIR / relative_path, script)
    shared.write_json(SCENE_DIR / "scene.gbsres", scene)
    # This generator owns the whole scene folder: drop actors/triggers it no longer
    # makes (the old box actors, cable ends, the retired talk zone).
    for folder, items in (("actors", actors), ("triggers", triggers)):
        keep = {f"{item['symbol']}.gbsres" for item in items}
        for stale in (SCENE_DIR / folder).glob("*.gbsres"):
            if stale.name not in keep:
                stale.unlink()
                print(f"removed retired {folder[:-1]} {stale.name}")
        for item in items:
            shared.write_json(SCENE_DIR / folder / f"{item['symbol']}.gbsres", item)
    print(
        f"generated signal_hill: {rosa.MAP_W}x{rosa.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{rosa.LINE_COUNT} lines, {len(rosa.ARC_LANES)} live arc, {len(rosa.GUST_LANES)} gusts, "
        f"{len(rosa.span_arc_lanes())} span arcs, {len(rosa.WHIP_LANES)} whips, "
        f"{len(hazards.HIDDEN_CABLES['signal_hill'])} hidden cables, "
        f"{len(hazards.BOARDS['signal_hill'])} cracked boards"
    )


if __name__ == "__main__":
    main()
