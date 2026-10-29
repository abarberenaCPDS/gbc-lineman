"""Generate the deterministic Signal Hill scene (Priya's repair job) from ``rosa.py``.

Run with ``python3 tools/make_rosa_scene.py`` from any working directory.
This writes only the Signal Hill scene resources, the Priya and live-arc sprite
palettes, the chain's background palettes and the Priya variable registrations.
The authored geometry, positions, arc and gust timings and stable IDs live in
the sibling ``rosa.py`` contract module.

The grid chain's events, actors and palettes come from the reusable
``grid_chain`` module, built here with Signal Hill's ID function, lines,
variables, dialogue and HUD. The transformer sprite is Wind Ridge's asset.

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

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import ridge  # noqa: E402  (transformer sprite: Wind Ridge's asset, reused here)
    import voices  # noqa: E402  (speaker names and text blips)
    import rosa  # noqa: E402  (Priya's job contract: geometry, IDs, timings)
    import tickets  # noqa: E402  (work orders: exit to ticket 4, CLOSED box)
    import kiko  # noqa: E402  (Emil's job contract: the porch exit leads there)
except ModuleNotFoundError as error:
    if error.name in {"grid_chain", "intro", "tickets", "voices", "climb", "opening", "ridge", "rosa",
                      "kiko", "make_climb_scene"}:
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
JUNCTION_SPRITE_KEY = "sprite:grid_junction_box"
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
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"], **_LINE_NAMES[_line["key"]]})
LINE_BY_KEY = {line["key"]: line for line in LINES}

# Dialogue for the chain's cable ends and boxes (grid_chain.GridChain text keys).
ROSA_TEXT = {
    "pickup": "Got the cable!\nFind its box.",
    "hands_full": "Hands full!\nOne cable a trip.",
    "already": "Already fixed.",
    "all_live": "Both lines live!\nGo see Priya.",
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
box_actor = CHAIN.box_actor


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
        *cable_drop_events(key),
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
        CHAIN.input_script_event(connect_sound_id=audio_ids["connect"], pickup_sound_id=audio_ids["pickup"]),
        set_value(VAR_LINE_LIVE, 0, "init-line-live"),
        set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
        set_value(rosa.VAR_FEEDER_LIVE, 0, "init-feeder-live"),
        set_value(VAR_LINES_LIVE, 0, "init-lines-live"),
        set_value(VAR_CHAIN_LIVE, 0, "init-chain-live"),
        window_palette_event(False, "init-window-cold"),
        *chain_refresh_events("init-chain"),
        # Pinned Snapped+Cable on every entry: each pole's own start script reads its
        # line variable, and the order between the scripts is unspecified.
        *[actor_state(actor_id(line["pole"]), "Snapped+Cable",
                      "init-pole-snapped" if line["key"] == "house" else f"init-{line['key']}-pole-snapped")
          for line in LINES],
        event("EVENT_MUSIC_PLAY", {"musicId": music_id}, "play-signal-hill-music"),
        # Intro boxes after the music cue; say() lifts the cutoff a previous visit may have left.
        *say(short_lines("Priya's offline!\nHer work is due."), "intro"),
        *say(short_lines("Mind the sparks!"), "spark"),
    ]


# ---------------------------------------------------------------------------
# Actors and triggers
# ---------------------------------------------------------------------------
def rosa_actor(index: int) -> dict[str, Any]:
    """Priya outside her door: Waiting until her house is powered, then Relieved."""
    key = ROSA_KEY
    x, y = rosa.ROSA
    script = [if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
        *say(short_lines("I'm back online!\nThank you!"), f"{key}:thanks", "rosa"),
    ], [
        if_value(VAR_LINES_LIVE, rosa.LINE_COUNT, f"{key}:lines", [
            *say(short_lines("Lines are live!\nTry my door."), f"{key}:live", "rosa"),
        ], [
            *say(short_lines("No internet...\nI can't work."), f"{key}:dead", "rosa"),
        ]),
    ])]
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
    guard keeps that from repeating the reward or the text. Both lines must be
    repaired (the HUD count) before the house can power on.
    """
    x, y, width, height = rosa.DOOR_TRIGGER
    script = [if_value(VAR_LINES_LIVE, rosa.LINE_COUNT, "door:lines", [
        if_value(VAR_HOME_POWERED, 0, "door:power-on", [
            set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
            sound_event(connect_sound_id, "door:sfx"),
            window_palette_event(True, "door:window-warm"),
            actor_state(actor_id(ROSA_KEY), "Relieved", "door:rosa-relieved"),
            actor_state(actor_id(WORKSTATION_KEY), "On", "door:workstation-on"),
            *say(short_lines("Router's on!\nI'm online again."), "door:text", "rosa"),
            *say(tickets.closed_lines(3), "door:closed"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix both lines!"), "door:no-power"),
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
def build_scene(music_id: str, audio_ids: dict[str, str]) -> dict[str, Any]:
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
    sprite_palette_ids[intro.SPRITE_SLOTS["pole"]] = intro.palette_id("pole")
    background_palette_ids = [
        opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES
    ] + ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Signal Hill background palettes must preserve the UI in slot 7")
    background_palette_ids[rosa.LINE_BG_SLOT] = chain_palette_id(0)

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
    box_sprites = {"junction": climb.grid_resource_id(JUNCTION_SPRITE_KEY),
                   "transformer": ridge.TRANSFORMER_SPRITE_ID}
    actors = [rosa_actor(0), workstation_actor(1)]
    for line in LINES:
        # The snapped cable is part of the pole sprite; each line has one pole
        # actor and one box actor.
        actors += [
            pole_actor(line, 0, intro.POLE_SPRITE_ID),
            box_actor(line, 0, box_sprites[line["box_kind"]]),
        ]
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
                timings=(rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES),
                symbol=f"signal_span_arc_{number:02d}", name=f"Downed Span Arc {number}",
            ))
    expected_actor_count = (2 + 2 * len(LINES) + len(rosa.ARC_LANES) + len(rosa.GUST_LANES)
                            + sum(len(span["arcs"]) for span in rosa.FALLEN_SPANS))
    if len(actors) != expected_actor_count:
        raise ValueError(f"{len(actors)} actors built, expected {expected_actor_count}")
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
    # B-press zones come after the exit and the door: box zones, then poles (no
    # neighbour zone: Priya's talk stays native, see docs/BUGS.md B-06).
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
    for key, name, symbol in (*rosa.VARIABLES, climb.NEAR_VARIABLE):
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
    warn_if_missing_asset(ridge.TRANSFORMER_SPRITE_ID, "sprites", "transformer sprite")

    scene = build_scene(music_id, audio_ids)
    actors = build_actors(sprite_ids, audio_ids)
    triggers = build_triggers(audio_ids)

    write_variables()
    for relative_path, palette in rosa_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    shared.write_json(SCENE_DIR / "scene.gbsres", scene)
    # The snapped cable is now part of each pole; retire only those former actors.
    retired = {f"{line['cable_symbol']}.gbsres" for line in LINES}
    for stale in (SCENE_DIR / "actors").glob("*.gbsres"):
        if stale.name in retired:
            stale.unlink()
            print(f"removed retired actor {stale.name}")
    for actor in actors:
        shared.write_json(SCENE_DIR / "actors" / f"{actor['symbol']}.gbsres", actor)
    for trigger in triggers:
        shared.write_json(SCENE_DIR / "triggers" / f"{trigger['symbol']}.gbsres", trigger)
    print(
        f"generated signal_hill: {rosa.MAP_W}x{rosa.MAP_H} PLATFORM, "
        f"{len(actors)} actors, {len(triggers)} triggers; "
        f"{rosa.LINE_COUNT} lines, {len(rosa.ARC_LANES)} live arcs, delays {rosa.ARC_START_DELAYS}; "
        f"{len(rosa.GUST_LANES)} gust, delays {rosa.GUST_START_DELAYS}"
    )


if __name__ == "__main__":
    main()
