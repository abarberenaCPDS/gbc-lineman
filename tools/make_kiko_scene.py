"""Generate Emil's run scenes, 4A ``pine_hollow`` and 4C ``pine_rim``, from ``kiko.py``.

Run with ``python3 tools/make_kiko_scene.py`` from any working directory. 4B
``pine_ladder`` is built by ``make_ladder_scene.py`` on the same builders
(this module), plus the shaft's culling thread.

This writes the two scenes' resources, Emil's sprite palette, the job's chain
palettes (one set for all three scenes), the box scripts of the lines whose box
stands in these scenes, and the job variable registrations. Geometry,
positions, hazard timings and stable IDs live in ``kiko.py``; links in
``scene_links.py``; boards and hidden cables in ``hazards.py``.

Multi-scene rules (docs/LEVEL_REDESIGN.md §3, grid_chain "Multi-scene jobs"):
the entry scene (4A) resets the job once, when the work order left var 16 at 4,
and plays the music and intro lines only then; every scene restores a cable
carried across an edge (var 6) and sets its poles from the variables; each
scene's respawn is its furthest repaired checkpoint, else its upstream entry.
Event IDs stay unique per scene: 4A keeps the job's original keys, 4B and 4C
prefix theirs (``scene_rid``).

Generic GB Studio helpers (collision RLE, sidecar lookup, JSON writing, the
dialogue length check) are reused from ``make_climb_scene``.
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Iterator

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
CLIMB_SCENE = PROJECT_DIR / "project" / "scenes" / "storm_climb" / "scene.gbsres"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites, near variable)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import kiko  # noqa: E402  (Emil's job contract: geometry, IDs, timings)
    import make_climb_scene as shared  # noqa: E402  (generic helpers, ClimbChain)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import ridge  # noqa: E402  (shared whipping-wire assets)
    import voices  # noqa: E402  (speaker names and text blips)
    import rosa  # noqa: E402  (Signal Hill owns the live arc palette this job reuses)
    import scene_links  # noqa: E402  (every exit and entry)
    import scenes  # noqa: E402  (scene registry: ids, names, editor positions)
    import tickets  # noqa: E402  (work orders: CLOSED box)
    import hazards  # noqa: E402  (board/hidden-cable placement and timings)
except ModuleNotFoundError as error:
    if error.name in {"tickets", "intro", "voices", "climb", "kiko", "opening", "ridge", "rosa", "make_climb_scene",
                      "hazards", "grid_chain", "scene_links", "scenes"}:
        raise SystemExit(f"cannot generate Emil's scenes: tools/{error.name}.py is missing") from error
    raise

HOLLOW, LADDER, RIM = kiko.HOLLOW, kiko.LADDER, kiko.RIM
MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
VAR_CARRYING_CABLE = kiko.VAR_CARRYING_CABLE
VAR_HOME_POWERED = kiko.VAR_HOME_POWERED
VAR_LINES_LIVE = kiko.VAR_LINES_LIVE
VAR_CHAIN_LIVE = kiko.VAR_CHAIN_LIVE
KIKO_KEY = "kiko"
STOVE_KEY = "stove"
KIKO_SYMBOL = "pine_kiko"
STOVE_SYMBOL = "pine_stove"
DOOR_TRIGGER_SYMBOL = "trigger_pine_home_door"
REPORT_REFUSAL = "Power Emil's\nhouse first."

# Per-scene namespaces: event/actor/trigger key prefix and symbol prefix. 4A keeps
# the job's original (empty) key prefix and "pine_" symbols.
KEY_PREFIX = {HOLLOW: "", LADDER: "ladder:", RIM: "rim:"}
SYMBOL_PREFIX = {HOLLOW: "pine_", LADDER: "ladder_", RIM: "rim_"}
SCENE_INDEX = {HOLLOW: 6, LADDER: 16, RIM: 17}

# The grid chain, upstream first (kiko.LINES). The feeder keeps the legacy pole
# key and symbol; coordinates move to pole_at/box_at ("pole"/"box" are actor keys).
_LINE_NAMES = {
    "feeder": {"pole": "pole", "pole_symbol": "kiko_storm_pole", "pole_name": "Storm Pole"},
    "house": {"box": "junction-box", "box_symbol": "pine_junction_box",
              "box_name": "Transformer (house)"},
}
LINES = []
for _line in kiko.LINES:
    _key = _line["key"]
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"],
                  "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"box:{_key}",
                  "pole_symbol": f"kiko_{_key}_pole", "cable_symbol": f"pine_{_key}_cable_end",
                  "box_symbol": f"pine_{_key}_box", "pole_name": f"Storm Pole ({_key})",
                  "cable_name": f"Cable End ({_key})", "box_name": f"Transformer ({_key})",
                  **_LINE_NAMES.get(_key, {})})


# ---------------------------------------------------------------------------
# Scope: which scene the builders are writing (event IDs, actor/trigger keys)
# ---------------------------------------------------------------------------
_current = [HOLLOW]


@contextmanager
def scene_scope(folder: str) -> Iterator[None]:
    previous = _current[0]
    _current[0] = folder
    try:
        yield
    finally:
        _current[0] = previous


def current() -> str:
    return _current[0]


def kp() -> str:
    """Key prefix of the scene being built."""
    return KEY_PREFIX[current()]


def sp() -> str:
    """Symbol prefix of the scene being built."""
    return SYMBOL_PREFIX[current()]


def scene_rid(folder: str) -> Callable[[str], str]:
    """kiko.resource_id with the scene's prefix on event keys only (palettes, actors, scripts unchanged)."""
    prefix = KEY_PREFIX[folder]

    def rid(key: str) -> str:
        if prefix and key.startswith("event:"):
            key = "event:" + prefix + key[len("event:"):]
        return kiko.resource_id(key)
    return rid


# ---------------------------------------------------------------------------
# IDs and palette resources
# ---------------------------------------------------------------------------
def kiko_palette_id() -> str:
    return kiko.resource_id("palette:sprite:kiko")


def arc_palette_id() -> str:
    # Signal Hill owns this palette resource; Emil's scenes reuse the same ID.
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
    """Emil's sprite palette and the job's chain palettes (the arc palette is Signal Hill's)."""
    kiko_sprite = palette_resource("sprite", "kiko", shared.editor_sprite_colors(kiko.KIKO_SPRITE_HARDWARE))
    chain = grid_chain.chain_palette_resources(kiko.resource_id, label="Pine Hollow",
                                               file_prefix="pine_hollow", palettes=kiko.CHAIN_PALETTES)
    return [("project/palettes/pine_hollow_sprite_kiko.gbsres", kiko_sprite), *chain]


# ---------------------------------------------------------------------------
# Event builders (scene-scoped IDs; EVENT_TEXT args copied from the climb)
# ---------------------------------------------------------------------------
def event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": scene_rid(current())(f"event:{key}")}


def branch_event(command: str, args: dict[str, Any], key: str, true_events: list[dict[str, Any]],
                 false_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {**event(command, args, key), "children": {"true": true_events, "false": false_events or []}}


def if_value(variable_id: str, value: int, key: str, true_events: list[dict[str, Any]],
             false_events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return branch_event("EVENT_IF", {"condition": {
        "type": "eq",
        "valueA": {"type": "variable", "value": variable_id},
        "valueB": shared.number(value),
    }}, key, true_events, false_events)


def set_value(variable_id: str, value: int, key: str) -> dict[str, Any]:
    return event("EVENT_SET_VALUE", {"variable": variable_id, "value": shared.number(value)}, key)


def set_position(x: int, y: int, key: str) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_POSITION", {
        "units": "tiles", "actorId": "player", "x": shared.number(x), "y": shared.number(y),
    }, key)


def text_event(lines: list[str], key: str) -> dict[str, Any]:
    return event("EVENT_TEXT", {
        "text": lines, "avatarId": "", "minHeight": 4, "maxHeight": 7, "textX": 1, "textY": 1,
        "textHeight": 5, "position": "bottom", "clearPrevious": True, "showFrame": True,
        "speedIn": -1, "speedOut": -1, "closeWhen": "key", "closeButton": "a",
        "closeDelayUnits": "time", "closeDelayTime": 0.5, "closeDelayFrames": 30,
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

    A speaker names the box and gives it that character's blip (voices.py).
    """
    if speaker is None:
        return [cutoff_event(150, f"{key}:say-cutoff"), text_event(lines, key), *hud_events(f"{key}:say-hud")]
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
    return background_palette_event({kiko.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}")}, key)


def actor_state(target: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return event("EVENT_ACTOR_SET_STATE", {"actorId": target, "spriteStateId": state, "loopAnim": loop}, key)


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


# ---------------------------------------------------------------------------
# The grid chain, one per scene (same LINES; poles and boxes local, refresh global)
# ---------------------------------------------------------------------------
def _make_chain(folder: str) -> grid_chain.GridChain:
    # The shaft's span arcs start every live cycle safe (its culling thread restarts them).
    cls = shared.ClimbChain if kiko.SCENES[folder].shaft else grid_chain.GridChain
    for text in kiko.CHAIN_TEXT.values():
        short_lines(text)
    return cls(
        rid=scene_rid(folder), lines=LINES, chain_var=VAR_CHAIN_LIVE, lines_var=VAR_LINES_LIVE,
        carrying_var=VAR_CARRYING_CABLE, near_var=climb.VAR_NEAR, line_bg_slot=kiko.LINE_BG_SLOT,
        text=kiko.CHAIN_TEXT, say=say, hud=hud_events, bare_event_key="feeder" if folder == HOLLOW else None,
        background_boxes=kiko.BACKGROUND_BOXES, scene=folder,
    )


CHAINS = {folder: _make_chain(folder) for folder in kiko.SCENE_ORDER}


def chain() -> grid_chain.GridChain:
    return CHAINS[current()]


def chain_palette_id(stages_live: int) -> str:
    return CHAINS[HOLLOW].chain_palette_id(stages_live)


def box_script_resources(folder: str, audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    with scene_scope(folder):
        return chain().box_script_resources(label="Pine Hollow", file_prefix="pine_hollow",
                                            connect_sound_id=audio_ids["connect"])


def respawn_events(key: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Death sound, shock, then drop any cable (home to its pole, wherever it stands), then respawn.

    Respawn (rule 4): this scene's furthest repaired checkpoint, else its
    upstream entry; on the rim, the tile in front of the door once Emil's house
    is powered.
    """
    scene = kiko.SCENES[current()]
    respawn = chain().checkpoint_chain(key, scene.start)
    if scene.house:
        door_x, door_y = scene.house["door"]
        respawn = [if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check", respawn, [
            set_position(door_x - 1, door_y, f"{key}:respawn-door"),
        ])]
    return [
        sound_event(death_sound_id, f"{key}:death-sfx"),
        *shock.shock_events(key),
        *chain().cable_drop_events(key),
        set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        *respawn,
    ]


# ---------------------------------------------------------------------------
# Scene init
# ---------------------------------------------------------------------------
INTRO_LINES = [f"{voices.name('kiko')}'s house is\ndark and hungry!", "Fix 5 lines,\nthen soup!", "Dinner's cold..."]


def scene_script(music_id: str, audio_ids: dict[str, str],
                 extra: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The scene being built's init, in the order of grid_chain's "Multi-scene jobs" rules 1, 2 and 6."""
    folder = current()
    scene = kiko.SCENES[folder]
    entry = folder == kiko.SCENE_ORDER[0]
    events: list[dict[str, Any]] = [
        event("EVENT_PLAYER_SET_SPRITE", {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
              "init-player-sprite"),
    ]
    if entry:
        # Rule 1: a fresh job (the work order left var 16 at 4) zeroes the job's variables once.
        events += chain().job_reset_events(kiko.JOB, extra=[
            set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
            event("EVENT_ACTOR_SET_DIRECTION", {"actorId": "player",
                                                "direction": {"type": "direction", "value": "right"}},
                  "init-player-direction"),
        ])
    npc = {}
    if scene.house:
        npc = {"npc_events": kiko_talk_events("b-press:npc"), "npc_actor_id": actor_id(KIKO_KEY)}
    events += [
        set_value(climb.VAR_NEAR, grid_chain.NEAR_NONE, "init-near"),
        # B: pick up, plug in, drop or talk, by the zone the hero stands in (grid_chain).
        chain().input_script_event(pickup_sound_id=audio_ids["pickup"], override=True, **npc),
        set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
    ]
    if scene.house:
        events.append(if_value(VAR_HOME_POWERED, 1, "init-home", [
            window_palette_event(True, "init-window-warm"),
            actor_state(actor_id(KIKO_KEY), "Relieved", "init-kiko-relieved"),
            actor_state(actor_id(STOVE_KEY), "On", "init-stove-on"),
        ], [
            window_palette_event(False, "init-window-cold"),
            actor_state(actor_id(KIKO_KEY), "Waiting", "init-kiko-waiting"),
            actor_state(actor_id(STOVE_KEY), "Off", "init-stove-off"),
        ]))
    events += [
        *chain().chain_refresh_events("init-chain"),
        *chain().pole_init_events("init-pole"),
        *chain().carry_restore_events("init-carry"),
        *hud_events("init-hud"),
    ]
    if entry:
        # Rule 6: music and intro lines on a fresh start only (an edge never restarts the track).
        intro_say = [e for n, text in enumerate(INTRO_LINES)
                     for e in say(short_lines(text), "intro" if n == 0 else f"intro-{n}")]
        events += chain().fresh_start_events(kiko.JOB, [chain().music_event(music_id), *intro_say])
    return events + list(extra or [])


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
def actor_resource(**kwargs: Any) -> dict[str, Any]:
    return chain().actor_resource(**kwargs)


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


def kiko_actor() -> dict[str, Any]:
    """Emil outside his house: Waiting until the house is powered, then Relieved."""
    x, y = kiko.KIKO
    return actor_resource(
        index=0, symbol=KIKO_SYMBOL, name="Emil (Pine Rim)", x=x, y=y, sprite_id=kiko.KIKO_SPRITE_ID,
        key=KIKO_KEY, script=kiko_talk_events(f"{KIKO_KEY}:actor-talk"),
        start_script=[if_value(VAR_HOME_POWERED, 1, f"{KIKO_KEY}:home-check",
                               [actor_state("$self$", "Relieved", f"{KIKO_KEY}:relieved")],
                               [actor_state("$self$", "Waiting", f"{KIKO_KEY}:waiting")])],
    )


def stove_actor() -> dict[str, Any]:
    """Electric stove on the porch: Off until the door switches it On."""
    x, y = kiko.STOVE
    return actor_resource(
        index=0, symbol=STOVE_SYMBOL, name="Electric Stove", x=x, y=y, sprite_id=kiko.STOVE_SPRITE_ID,
        key=STOVE_KEY,
        start_script=[if_value(VAR_HOME_POWERED, 1, f"{STOVE_KEY}:home-check",
                               [actor_state("$self$", "On", f"{STOVE_KEY}:on")],
                               [actor_state("$self$", "Off", f"{STOVE_KEY}:off")])],
    )


def pole_actor(line: dict[str, Any]) -> dict[str, Any]:
    """The chain's pole actor, its start script deterministic from the variables (rule 2):
    live -> Standing; carried -> Snapped; else Snapped+Cable (a culled pole re-runs it)."""
    c = chain()
    actor = c.pole_actor(line, 0, intro.POLE_SPRITE_ID)
    key = line["pole"]
    actor["startScript"] = [
        c.event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:no-collision"),
        c.if_value(line["live_var"], 1, f"{key}:line-check", [
            c.actor_state("$self$", "Standing", f"{key}:standing"),
        ], [
            c.if_value(VAR_CARRYING_CABLE, line["number"], f"{key}:carried-check", [
                c.actor_state("$self$", "Snapped", f"{key}:snapped"),
            ], [
                c.actor_state("$self$", "Snapped+Cable", f"{key}:snapped-cable"),
            ]),
        ]),
    ]
    return actor


def _first_cycle(key: str, start_delay: int, hide: bool) -> dict[str, Any]:
    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    first = [own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"})]
    if hide:
        first.append(own("EVENT_ACTOR_HIDE", "delay-hidden"))
    if start_delay > 0:
        first.append(wait_event(start_delay, f"{key}:start-delay"))
    return branch_event("EVENT_IF_ACTOR_DIRECTION",
                        {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                        f"{key}:first-cycle", first)


def gust_actor(index: int, lane: tuple[int, int, int], start_delay: int, sprite_id: str) -> dict[str, Any]:
    """Timed wind lane: safe warning, active burst, hidden rest (every cycle starts safe)."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 3:
        raise ValueError("the authored gust sprite is exactly three tiles wide")
    key = f"{kp()}gust:{index}"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    update = [
        _first_cycle(key, start_delay, hide=True),
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
        index=0, symbol=f"{sp()}gust_{index:02d}", name=f"Telegraphed Gust {index}",
        x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
        update_script=update, collision_group="1",
    )


def whip_actor(number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
    row, x0, x1 = lane
    if x1 - x0 + 1 != kiko.WHIP_COLUMNS:
        raise ValueError("the whip lane is the sprite's width")
    key = f"{kp()}whip:{number}"
    return actor_resource(
        index=0, symbol=f"{sp()}whip_{number:02d}", name=f"Whipping Live Wire {number}",
        x=x0, y=row + 1, sprite_id=kiko.WHIP_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.whip_start_script(key, event),
        update_script=hazards.whip_update_script(
            key, start_delay, kiko.WHIP_SWAY_FRAMES, kiko.WHIP_SWING_FRAMES, kiko.WHIP_HANG_FRAMES,
            event, wait_event, branch_event),
        collision_group="1",
    )


def hidden_cable_actor(number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
    """Buried line: no wire art, dark, a brief spark, then the arc (group 1); job 4's timings."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the live arc sprite is exactly two tiles wide")
    key = f"{kp()}hidden-cable:{number}"
    return actor_resource(
        index=0, symbol=f"{sp()}hidden_cable_{number:02d}", name=f"Hidden Cable {number}",
        x=x0, y=row, sprite_id=kiko.ARC_SPRITE_ID, key=key, anim_speed=8,
        start_script=hazards.cable_start_script(key, event),
        update_script=hazards.cable_update_script(key, start_delay, event, wait_event, branch_event,
                                                  timings=hazards.cable_timings(current())),
        collision_group="1",
    )


def board_actor(number: int, board: tuple[int, int, int]) -> dict[str, Any]:
    """Cracked board whose idle plank is background art: the actor only shows while it creaks."""
    key = f"{kp()}board:{number}"
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
        index=0, symbol=f"{sp()}board_{number:02d}", name=f"Cracked Board {number}",
        x=x, y=y, sprite_id=hazards.BOARD_SPRITE_ID, key=key,
        start_script=[*hazards.board_start_script(key, event), own("EVENT_ACTOR_HIDE", "init-hidden")],
        update_script=[if_value(hazards.VAR_ON_BOARD, number, f"{key}:on-check", creak,
                                [wait_event(1, f"{key}:idle-tick")])],
        collision_group="1",
    )
    actor["animate"] = True
    return actor


def span_numbers(folder: str) -> list[int]:
    """Job-wide span-arc numbers (1-based, play order) of ``folder``'s span arcs: their keys stay unique."""
    numbers, n = {}, 0
    for f in kiko.SCENE_ORDER:
        for span in kiko.SCENES[f].spans:
            for _ in span["arcs"]:
                n += 1
                numbers.setdefault(f, []).append(n)
    return numbers.get(folder, [])


def span_arc_actors() -> list[dict[str, Any]]:
    scene = kiko.SCENES[current()]
    lanes = [(lane, delay, span["live_after"]) for span in scene.spans
             for lane, delay in zip(span["arcs"], span["delays"])]
    return [chain().span_arc_actor(
        number, lane, delay, kiko.ARC_SPRITE_ID, live_after,
        timings=(kiko.ARC_WARNING_FRAMES, kiko.ARC_ACTIVE_FRAMES, kiko.ARC_REST_FRAMES),
        symbol=f"{sp()}span_arc_{number:02d}", name=f"Downed Span Arc {number}",
    ) for number, (lane, delay, live_after) in zip(span_numbers(current()), lanes)]


def build_actors(folder: str, sprite_ids: dict[str, str]) -> list[dict[str, Any]]:
    """Neighbours, poles, then hazards; editor order is list order (boards last draw on top)."""
    scene = kiko.SCENES[folder]
    with scene_scope(folder):
        actors = [kiko_actor(), stove_actor()] if scene.house else []
        actors += [pole_actor(line) for line in LINES if line["pole_scene"] == folder]
        actors += [gust_actor(n, lane, delay, sprite_ids["gust"])
                   for n, (lane, delay) in enumerate(zip(scene.gust_lanes, scene.gust_delays), start=1)]
        actors += span_arc_actors()
        actors += [whip_actor(n, lane, delay)
                   for n, (lane, delay) in enumerate(zip(scene.whip_lanes, scene.whip_delays), start=1)]
        actors += [hidden_cable_actor(n, lane, delay)
                   for n, (lane, delay) in enumerate(zip(scene.cables, scene.cable_delays), start=1)]
        actors += [board_actor(n, board) for n, board in enumerate(scene.boards, start=1)]
    if len(actors) != scene.actor_count() or len(actors) > kiko.MAX_SCENE_ACTORS:
        raise ValueError(f"{folder}: {len(actors)} actors (contract {scene.actor_count()})")
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------
def exit_trigger(link: scene_links.Link) -> dict[str, Any]:
    """A scene_links exit: lift the HUD cutoff, hide the overlay, then switch (or refuse at the gate).

    The storm-report exit keeps its legacy key, sorts before the door (BUGS B-05)
    and is gated on Emil's house with a text-only refusal.
    """
    report = link.target == scene_links.REPORT
    key = "report-exit" if report else f"{kp()}exit:{link.target}"
    go = [
        cutoff_event(150, f"{key}:cutoff"),
        event("EVENT_OVERLAY_HIDE", {}, f"{key}:hud-hide"),
        *scene_links.exit_events(link, key, event=event, set_value=set_value, number=shared.number),
    ]
    script = go if link.gate is None else [
        if_value(link.gate, 1, f"{key}:gate", go, say(short_lines(REPORT_REFUSAL), f"{key}:not-yet"))]
    x, y, width, height = link.rect
    name = scenes.REGISTRY[link.target]["name"]
    return {
        "_resourceType": "trigger", "id": kiko.resource_id(f"trigger:{key}"),
        "name": f"{'Report' if report else 'Exit'} (to {name})", "prefabId": "", "x": x, "y": y,
        "symbol": f"trigger_{sp()}{'report_exit' if report else 'exit_' + link.target}",
        "prefabScriptOverrides": {}, "width": width, "height": height,
        "script": script, "leaveScript": [], "_index": 0,
    }


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Emil's door: powering the house is a once-only checkpoint (var 13); it needs all five lines.

    Only the top row of a standing 24px hero covers the door columns, so the
    respawn tile in front of the door also lands on this trigger; the var 13
    guard keeps that from repeating the reward or the text.
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
            *say(tickets.closed_lines(kiko.JOB), "door:closed"),
        ]),
    ], [
        *say(short_lines("Still no power.\nFix all 5 lines!"), "door:no-power"),
    ])]
    return {
        "_resourceType": "trigger", "id": kiko.resource_id("trigger:kiko-door"),
        "name": "Emil Door Checkpoint", "prefabId": "", "x": x, "y": y, "symbol": DOOR_TRIGGER_SYMBOL,
        "prefabScriptOverrides": {}, "width": width, "height": height,
        "script": script, "leaveScript": [], "_index": 0,
    }


def board_trigger(number: int, board: tuple[int, int, int]) -> dict[str, Any]:
    key = f"{kp()}board:{number}"
    x, y, width, height = hazards.board_trigger_rect(board)
    on_script, leave_script = hazards.board_trigger_scripts(number, f"{key}:trigger", set_value)
    return {
        "_resourceType": "trigger", "id": kiko.resource_id(f"trigger:{key}"),
        "name": f"Cracked Board {number} Stand", "prefabId": "", "x": x, "y": y,
        "symbol": f"trigger_{sp()}cracked_board_{number:02d}", "prefabScriptOverrides": {},
        "width": width, "height": height, "script": on_script, "leaveScript": leave_script, "_index": 0,
    }


def build_triggers(folder: str, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    """Exits first (first match wins; the report exit before the door), boards, then B zones."""
    scene = kiko.SCENES[folder]
    with scene_scope(folder):
        triggers = [exit_trigger(link) for link in scene.links()]
        if scene.house:
            triggers.append(door_trigger(audio_ids["connect"]))
        triggers += [board_trigger(n, board) for n, board in enumerate(scene.boards, start=1)]
        # Box zones before pole zones: where zones overlap a box wins (grid_chain).
        triggers += [chain().box_zone_trigger(line, symbol=f"trigger_pine_{line['key']}_reach", index=0)
                     for line in chain().box_lines()]
        triggers += [chain().pole_zone_trigger(line, symbol=f"trigger_pine_{line['key']}_pole_zone", index=0)
                     for line in chain().pole_lines()]
    if len(triggers) != scene.trigger_count():
        raise ValueError(f"{folder}: {len(triggers)} triggers (contract {scene.trigger_count()})")
    grid_chain.check_scene_limits(scene.actor_count(), len(triggers))
    for index, trigger in enumerate(triggers):
        trigger["_index"] = index
    return triggers


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def build_scene(folder: str, music_id: str, audio_ids: dict[str, str],
                extra_init: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    scene_contract = kiko.SCENES[folder]
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("Emil's scenes need the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    sprite_palette_ids[kiko.KIKO_SPRITE_PALETTE_SLOT] = kiko_palette_id()
    sprite_palette_ids[kiko.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
    sprite_palette_ids[kiko.ARC_SPRITE_PALETTE_SLOT] = arc_palette_id()
    sprite_palette_ids[intro.SPRITE_SLOTS["pole"]] = intro.palette_id("pole")
    sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    sprite_palette_ids[kiko.WHIP_SPRITE_PALETTE_SLOT] = kiko.WHIP_PALETTE_ID
    background_palette_ids = [opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES]
    background_palette_ids += ["default-ui"]
    if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
        raise ValueError("Emil's background palettes must preserve the UI in slot 7")
    for slot, palette_id in CHAINS[folder].chain_palette_ids(0).items():
        background_palette_ids[slot] = palette_id
    registry = scenes.REGISTRY[folder]
    editor_x, editor_y = scenes.editor_position(folder)
    with scene_scope(folder):
        script = scene_script(music_id, audio_ids, extra_init)
        # shock.py derives its own event IDs from the key: scope it per scene.
        hit = respawn_events(f"{kp()}player-hit", audio_ids["death"])
    scene = dict(template)
    scene.update({
        "id": registry["id"],
        "_index": SCENE_INDEX[folder],
        "name": registry["name"],
        "type": "PLATFORM",
        "width": scene_contract.map_w,
        "height": scene_contract.map_h,
        "x": editor_x,
        "y": editor_y,
        "collisions": shared.collision_rle(scene_contract.collision_grid(), scene_contract.map_w,
                                           scene_contract.map_h),
        "symbol": f"scene_{folder}",
        "backgroundId": kiko.BACKGROUND_IDS[folder],
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "script": script,
        "playerHit1Script": hit,
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any], extra: tuple = ()) -> dict[str, Any]:
    """Append the job's variables without changing any existing entry (a renamed ID is refused)."""
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*kiko.VARIABLES, *hazards.VARIABLES, climb.NEAR_VARIABLE, *extra):
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in merged["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            merged["variables"].append(value)
    return merged


def write_variables(extra: tuple = ()) -> None:
    data = shared.load_json(VARIABLES_PATH)
    contents = json.dumps(merged_variables(data, extra), indent=2) + "\n"
    if VARIABLES_PATH.read_text(encoding="utf-8") != contents:
        VARIABLES_PATH.write_text(contents, encoding="utf-8")
        print("registered Emil's job variables without changing existing variables")


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other generators produce these files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def load_ids() -> tuple[str, dict[str, str], dict[str, str]]:
    music_id = shared.sidecar_id(MUSIC_SIDECAR, "music")
    audio_ids = {
        "death": shared.sidecar_id(DEATH_SOUND, "sound"),
        "connect": shared.sidecar_id(CONNECT_SOUND, "sound"),
        "pickup": shared.sidecar_id(PICKUP_SOUND, "sound"),
    }
    sprite_ids = {"gust": shared.sidecar_id(GUST_SPRITE, "sprite")}
    return music_id, audio_ids, sprite_ids


def scene_dir(folder: str) -> Path:
    return PROJECT_DIR / "project" / "scenes" / folder


def write_scene(folder: str, scene: dict[str, Any], actors: list[dict[str, Any]],
                triggers: list[dict[str, Any]], audio_ids: dict[str, str]) -> None:
    for relative_path, palette in kiko_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for relative_path, script in box_script_resources(folder, audio_ids):
        shared.write_json(PROJECT_DIR / relative_path, script)
    directory = scene_dir(folder)
    shared.remove_retired_debris_actors(directory, prefix=SYMBOL_PREFIX[folder])
    shared.write_json(directory / "scene.gbsres", scene)
    # This generator owns the whole scene folder: drop actors/triggers it no longer makes.
    for sub, items in (("actors", actors), ("triggers", triggers)):
        keep = {f"{item['symbol']}.gbsres" for item in items}
        for stale in (directory / sub).glob("*.gbsres"):
            if stale.name not in keep:
                stale.unlink()
                print(f"removed retired {folder} {sub[:-1]} {stale.name}")
        for item in items:
            shared.write_json(directory / sub / f"{item['symbol']}.gbsres", item)
    contract = kiko.SCENES[folder]
    print(f"generated {folder}: {contract.map_w}x{contract.map_h} PLATFORM, {len(actors)} actors, "
          f"{len(triggers)} triggers; {len(contract.gust_lanes)} gusts, {len(contract.span_arc_lanes())} span arcs, "
          f"{len(contract.whip_lanes)} whips, {len(contract.cables)} hidden cables, {len(contract.boards)} boards")


def generate(folder: str, extra_init: Callable[[list[dict[str, Any]]], list[dict[str, Any]]] | None = None,
             extra_variables: tuple = ()) -> None:
    """Build and write one of Emil's scenes. ``extra_init(actors)`` appends init events (4B's culling thread)."""
    music_id, audio_ids, sprite_ids = load_ids()
    warn_if_missing_asset(kiko.BACKGROUND_IDS[folder], "backgrounds", f"{folder} background")
    for resource_id, label in ((kiko.KIKO_SPRITE_ID, "Emil sprite"), (kiko.STOVE_SPRITE_ID, "stove sprite"),
                               (kiko.ARC_SPRITE_ID, "live arc sprite"), (kiko.WHIP_SPRITE_ID, "whip sprite"),
                               (hazards.BOARD_SPRITE_ID, "cracked board sprite")):
        warn_if_missing_asset(resource_id, "sprites", label)
    actors = build_actors(folder, sprite_ids)
    with scene_scope(folder):
        extra = extra_init(actors) if extra_init else None
    scene = build_scene(folder, music_id, audio_ids, extra)
    triggers = build_triggers(folder, audio_ids)
    write_variables(extra_variables)
    write_scene(folder, scene, actors, triggers, audio_ids)


def main() -> None:
    for folder in (HOLLOW, RIM):
        generate(folder)


if __name__ == "__main__":
    main()
