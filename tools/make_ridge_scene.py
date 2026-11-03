"""Generate Hiroshi's two ridge scenes (job 2) from ``ridge.py``.

Run with ``python3 tools/make_ridge_scene.py`` from any working directory.
This writes ``project/scenes/wind_ridge`` (2A) and ``project/scenes/ridge_saddle``
(2B), the job's palettes, box scripts and the Ridge variable registrations. The
authored geometry, positions, timings and stable IDs live in ``ridge.py``; the
links between scenes in ``scene_links.py`` (the redesign table).

Generic GB Studio helpers (collision RLE, sidecar lookup, JSON writing, the
dialogue length check) are reused from ``make_climb_scene``. Each scene builds
its own ``grid_chain.GridChain(scene=...)`` from the job's full LINES (§3: lines
are global, actors are local). 2A is the job's entry scene: it alone resets the
job on a fresh start and plays the music and intro lines (§3 rules 1 and 6).
Both scenes restore a carried cable across the edge (rule 2) and respawn at
their own furthest checkpoint, else their upstream entry (rule 4).

IDs: 2A keeps the 100x30 level's IDs where the resource survives (scene,
background, Hiroshi, poles, box scripts). 2B prefixes its event keys with
``saddle:`` so event IDs stay unique per scene; hazards are numbered job-wide.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENES_DIR = PROJECT_DIR / "project" / "scenes"
CLIMB_SCENE = SCENES_DIR / "storm_climb" / "scene.gbsres"
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"
WHIP_SPRITE = "assets/sprites/whip_wire.png.gbsres"
ARC_SPRITE = "assets/sprites/live_arc.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import completion  # noqa: E402  (Hiroshi's household completion cue)
    import climb  # noqa: E402  (shared palettes, grid sprites and climb timings)
    import intro  # noqa: E402  (intro pole sprite and palette identities)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import voices  # noqa: E402  (speaker names and text blips)
    import ridge  # noqa: E402  (Hiroshi's job contract: geometry, IDs, timings)
    import rosa  # noqa: E402  (live arc sprite and palette)
    import tickets  # noqa: E402  (CLOSED box)
    import hazards  # noqa: E402  (cracked boards and hidden cables: placement, IDs, timings)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import scene_links  # noqa: E402  (every link between scenes)
    import scenes  # noqa: E402  (scene registry: IDs and editor positions)
except ModuleNotFoundError as error:
    if error.name in {"tickets", "voices", "climb", "intro", "opening", "ridge", "rosa", "make_climb_scene",
                      "hazards", "grid_chain", "scene_links", "scenes"}:
        raise SystemExit(f"cannot generate the ridge scenes: tools/{error.name}.py is missing") from error
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
CABLE_SYMBOL = "ridge_cable_end"
JUNCTION_SYMBOL = "ridge_junction_box"
TOMAS_SYMBOL = "ridge_tomas"
CONCENTRATOR_SYMBOL = "ridge_oxygen_concentrator"
DOOR_TRIGGER_SYMBOL = "trigger_ridge_tomas_door"
# Scene _index for the editor (2A keeps its slot).
SCENE_INDEX = {ridge.RIDGE: 4, ridge.SADDLE: 12}
SCENE_SYMBOL = {ridge.RIDGE: "scene_wind_ridge", ridge.SADDLE: "scene_ridge_saddle"}
EXIT_SYMBOL = {
    (ridge.RIDGE, ridge.SADDLE): ("trigger_ridge_saddle_exit", "trigger:saddle-exit", "Saddle Exit (to Ridge Saddle)"),
    (ridge.SADDLE, ridge.RIDGE): ("trigger_saddle_ridge_exit", "trigger:saddle-back-exit", "Ridge Exit (back to Wind Ridge)"),
    (ridge.SADDLE, "signal_hill"): ("trigger_ridge_hill_exit", "trigger:hill-exit", "Hill Exit (to Signal Hill)"),
}

# The grid chain, upstream first (ridge.LINES). The house line keeps the original
# job's keys, symbols and names (stable IDs, test_poles); the others are per key.
_LINE_NAMES = {
    "house": {"pole": POLE_KEY, "cable": CABLE_KEY, "box": JUNCTION_KEY,
              "pole_symbol": POLE_SYMBOL, "cable_symbol": CABLE_SYMBOL, "box_symbol": JUNCTION_SYMBOL,
              "pole_name": "Storm Pole", "cable_name": "Dangling Cable End",
              "box_name": "Junction Box (Ridge House)"},
}
LINES = []
for _line in ridge.LINES:
    _key = _line["key"]
    _kind = "Transformer" if _line["box_kind"] == "transformer" else "Junction Box"
    _default = {
        "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"junction-box:{_key}",
        "pole_symbol": f"ridge_{_key}_pole", "cable_symbol": f"ridge_{_key}_cable_end",
        "box_symbol": f"ridge_{_key}_box",
        "pole_name": f"Storm Pole ({_key})", "cable_name": f"Cable End ({_key})",
        "box_name": f"{_kind} ({_key})",
    }
    # Coordinates move to pole_at/box_at: "pole"/"box" are actor keys here.
    LINES.append({**_line, "pole_at": _line["pole"], "box_at": _line["box"], **_default,
                  **_LINE_NAMES.get(_key, {})})
LINE_BY_KEY = {line["key"]: line for line in LINES}

# Dialogue for the chain's poles and boxes (grid_chain.GridChain text keys).
RIDGE_TEXT = {
    "pickup": "Got the cable!\nFind its box.",
    "hands_full": "Hands full!\nOne cable a trip.",
    "already": "Already fixed.",
    "all_live": "All 5 lines live!\nGo see Hiroshi.",
    "lit": "Power flows on!\nKeep going.",
    "dark": "Fixed. No power\nfrom upstream.",
    "no_cable": "No cable yet.\nFind its pole.",
    "wrong_cable": "Wrong cable\nfor this box.",
}


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


def saddle_rid(key: str) -> str:
    """2B's IDs: its event keys get a ``saddle:`` prefix; everything else is job-wide."""
    return ridge.resource_id(("saddle:" + key) if key.startswith("event:") else key)


def tomas_palette_id() -> str:
    return ridge.resource_id("palette:sprite:tomas")


def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    return grid_chain.palette_resource(ridge.resource_id, "Wind Ridge", kind, name, colors)


def tomas_palettes() -> list[tuple[str, dict[str, Any]]]:
    """Job-wide palettes: Hiroshi, the whip, and the chain (one set for both scenes, §3 rule 5)."""
    sprite = palette_resource("sprite", "tomas", shared.editor_sprite_colors(ridge.TOMAS_SPRITE_HARDWARE))
    whip = palette_resource("sprite", "whip", shared.editor_sprite_colors(ridge.WHIP_SPRITE_HARDWARE))
    if whip["id"] != ridge.WHIP_PALETTE_ID:
        raise ValueError("whip palette id must match ridge.WHIP_PALETTE_ID")
    chain = grid_chain.chain_palette_resources(ridge.resource_id, label="Wind Ridge",
                                               file_prefix="wind_ridge", palettes=ridge.CHAIN_PALETTES)
    return [("project/palettes/wind_ridge_sprite_tomas.gbsres", sprite),
            ("project/palettes/wind_ridge_sprite_whip.gbsres", whip), *chain]


def chain_palette_id(stages_live: int, slot: int = ridge.LINE_BG_SLOT) -> str:
    return grid_chain.chain_palette_id(ridge.resource_id, stages_live, slot)


class SceneBuilder:
    """Scripts, actors and triggers of one ridge scene (``ridge.LAYOUTS[folder]``)."""

    def __init__(self, folder: str) -> None:
        self.folder = folder
        self.layout = ridge.LAYOUTS[folder]
        self.entry = folder == ridge.SCENE_ORDER[0]
        self.rid = ridge.resource_id if self.entry else saddle_rid
        self.scene_dir = SCENES_DIR / folder
        self.chain = grid_chain.GridChain(
            rid=self.rid, lines=LINES, chain_var=ridge.VAR_CHAIN_LIVE, lines_var=ridge.VAR_LINES_LIVE,
            carrying_var=VAR_CARRYING_CABLE, near_var=climb.VAR_NEAR, line_bg_slot=ridge.LINE_BG_SLOT,
            text=RIDGE_TEXT, say=self.say, hud=self.hud_events, bare_event_key="house",
            background_boxes=ridge.BACKGROUND_BOXES, scene=folder,
        )
        chain = self.chain
        self.branch_event = chain.branch_event
        self.if_value = chain.if_value
        self.set_value = chain.set_value
        self.set_position = chain.set_position
        self.background_palette_event = chain.background_palette_event
        self.sound_event = chain.sound_event
        self.wait_event = chain.wait_event
        self.actor_state = chain.actor_state
        self.actor_id = chain.actor_id
        self.actor_resource = chain.actor_resource

    # -- event builders (scene-scoped IDs; EVENT_TEXT args copied from the climb) --
    def event(self, command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
        return {"command": command, "args": args, "id": self.rid(f"event:{key}")}

    def text_event(self, lines: list[str], key: str) -> dict[str, Any]:
        return self.event("EVENT_TEXT", {
            "text": lines, "avatarId": "", "minHeight": 4, "maxHeight": 7, "textX": 1, "textY": 1,
            "textHeight": 5, "position": "bottom", "clearPrevious": True, "showFrame": True,
            "speedIn": -1, "speedOut": -1, "closeWhen": "key", "closeButton": "a",
            "closeDelayUnits": "time", "closeDelayTime": 0.5, "closeDelayFrames": 30,
        }, key)

    def cutoff_event(self, y: int, key: str) -> dict[str, Any]:
        return self.event("EVENT_OVERLAY_SET_SCANLINE_CUTOFF", {"units": "pixels", "y": shared.number(y)}, key)

    def hud_events(self, key: str) -> list[dict[str, Any]]:
        return [
            self.cutoff_event(16, f"{key}:cutoff"),
            self.event("EVENT_OVERLAY_SHOW", {"color": "black", "x": 0, "y": 0}, f"{key}:show"),
            self.event("EVENT_TEXT_DRAW", {"text": ridge.HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
                       f"{key}:counter"),
            *intro.dev_hud_events(self.event, key),
        ]

    def say(self, lines: list[str], key: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """In-play dialogue: lift the HUD's 16px cutoff so the box shows, then redraw the HUD.

        Exact-ROM play showed text behind the cutoff staying invisible while the
        script waited for A, freezing the player. A speaker names the box and gives
        it that character's blip (voices.py).
        """
        if speaker is None:
            return [self.cutoff_event(150, f"{key}:say-cutoff"), self.text_event(lines, key),
                    *self.hud_events(f"{key}:say-hud")]
        return [
            self.event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(speaker), f"{key}:voice"),
            self.cutoff_event(150, f"{key}:say-cutoff"),
            self.text_event(voices.labeled(speaker, lines), key),
            self.event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(None), f"{key}:narrator"),
            *self.hud_events(f"{key}:say-hud"),
        ]

    def window_palette_event(self, powered: bool, key: str) -> dict[str, Any]:
        """Swap only the Hiroshi window slot (cold -> powered_window)."""
        name = "powered_window" if powered else "window"
        return self.background_palette_event({ridge.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}")}, key)

    # -- scene scripts ----------------------------------------------------------
    def respawn_events(self, key: str, death_sound_id: str) -> list[dict[str, Any]]:
        """One shock cue, drop any cable (home to its pole, any scene), then respawn.

        Respawn (§3 rule 4): Hiroshi's door once his power is on (2B), else the
        checkpoint of the furthest repaired line whose checkpoint is in this
        scene, else this scene's upstream entry.
        """
        chosen = self.chain.checkpoint_chain(key, self.layout.START)
        if self.layout.HOUSE:
            door_x, door_y = ridge.HOUSE_DOOR
            chosen = [self.if_value(VAR_HOME_POWERED, 0, f"{key}:respawn-check", chosen, [
                self.set_position(door_x - 1, door_y, f"{key}:respawn-door"),
            ])]
        return [
            *shock.shock_events(key),
            *self.chain.cable_drop_events(key),
            # The respawn teleports the hero without a leave event: forget the board.
            self.set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
            *chosen,
            *self.chain.recovery_hint_events(key),
        ]

    def scene_script(self, music_id: str, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
        """Scene init in §3 order: sprite, (entry: job reset), B script, chain, poles, carry, HUD,
        (entry: music and intro lines on a fresh start)."""
        chain = self.chain
        script = [self.event("EVENT_PLAYER_SET_SPRITE",
                             {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
                             "init-player-sprite")]
        if self.entry:
            script += chain.job_reset_events(ridge.JOB, extra=[
                self.set_value(VAR_HOME_POWERED, 0, "init-home-powered"),
                self.event("EVENT_ACTOR_SET_DIRECTION",
                           {"actorId": "player", "direction": {"type": "direction", "value": "right"}},
                           "init-player-direction"),
            ])
        script += [
            self.set_value(climb.VAR_NEAR, grid_chain.NEAR_NONE, "init-near"),
            # B: pick up, plug in, drop or talk, by the zone the hero stands in (grid_chain).
            chain.input_script_event(
                pickup_sound_id=audio_ids["pickup"],
                npc_events=self.tomas_talk_events("b-press:npc") if self.layout.HOUSE else None,
                npc_actor_id=self.actor_id(TOMAS_KEY) if self.layout.HOUSE else None, override=True),
            # Standing on a cracked board is tracked by its trigger; an entry starts off it.
            self.set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        ]
        if self.layout.HOUSE:
            script.append(self.if_value(VAR_HOME_POWERED, 1, "init-window", [
                self.window_palette_event(True, "init-window-warm"),
            ], [self.window_palette_event(False, "init-window-cold")]))
        script += [
            *chain.chain_refresh_events("init-chain"),
            *chain.pole_init_events("init-poles"),
            *chain.carry_restore_events("init-carry"),
            *self.hud_events("init-hud"),
        ]
        if self.entry:
            script += chain.fresh_start_events(ridge.JOB, [
                chain.music_event(music_id, "play-ridge-music"),
                *self.say(short_lines("Hiroshi's oxygen\nmachine is off!"), "intro"),
                *self.say(short_lines("Fix all 5 lines.\nOne cable a trip."), "intro-lines"),
            ])
        return script

    # -- Hiroshi and his porch (2B) ------------------------------------------------
    def tomas_talk_events(self, key: str) -> list[dict[str, Any]]:
        """Hiroshi's dialogue tree, also used by the B dispatcher."""
        return [self.if_value(VAR_HOME_POWERED, 1, f"{key}:home", [
            *self.say(short_lines("Ahh, fresh air.\nNice work."), f"{key}:thanks", "tomas"),
        ], [
            self.if_value(VAR_LINES_LIVE, ridge.LINE_COUNT, f"{key}:lines", [
                *self.say(short_lines("Five lines live!\nTry my door."), f"{key}:live", "tomas"),
            ], [
                *self.say(short_lines("Dead line. Dry\nas my jokes."), f"{key}:dead", "tomas"),
            ]),
        ])]

    def tomas_actor(self) -> dict[str, Any]:
        """Hiroshi outside his door: Waiting until the house is powered, then Relieved."""
        key = TOMAS_KEY
        x, y = ridge.TOMAS
        return self.actor_resource(
            index=0, symbol=TOMAS_SYMBOL, name="Hiroshi (Ridge Saddle)", x=x, y=y,
            sprite_id=ridge.TOMAS_SPRITE_ID, key=key, script=self.tomas_talk_events(f"{key}:actor-talk"),
            start_script=[self.if_value(VAR_HOME_POWERED, 1, f"{key}:powered", [
                self.actor_state("$self$", "Relieved", f"{key}:relieved"),
            ], [self.actor_state("$self$", "Waiting", f"{key}:waiting")])],
        )

    def concentrator_actor(self) -> dict[str, Any]:
        """Oxygen concentrator on the porch: Off until the door powers it On."""
        key = CONCENTRATOR_KEY
        x, y = ridge.CONCENTRATOR
        return self.actor_resource(
            index=0, symbol=CONCENTRATOR_SYMBOL, name="Oxygen Concentrator", x=x, y=y,
            sprite_id=ridge.CONCENTRATOR_SPRITE_ID, key=key,
            start_script=[self.if_value(VAR_HOME_POWERED, 1, f"{key}:powered", [
                self.actor_state("$self$", "On", f"{key}:on"),
            ], [self.actor_state("$self$", "Off", f"{key}:off")])],
        )

    def door_trigger(self, connect_sound_id: str) -> dict[str, Any]:
        """Hiroshi's door: powering the house is a once-only checkpoint (var 9).

        Only the top row of a standing 24px hero covers the door columns, so the
        respawn tile in front of the door also lands on this trigger. The var 9
        guard keeps that from repeating the reward or the text.
        """
        x, y, width, height = ridge.DOOR_TRIGGER
        script = [self.if_value(VAR_LINES_LIVE, ridge.LINE_COUNT, "door:line", [
            self.if_value(VAR_HOME_POWERED, 0, "door:power-on", [
                self.set_value(VAR_HOME_POWERED, 1, "door:set-powered"),
                self.sound_event(completion.sound_id(), "door:sfx"),
                self.window_palette_event(True, "door:window-warm"),
                self.actor_state(self.actor_id(TOMAS_KEY), "Relieved", "door:tomas-relieved"),
                self.actor_state(self.actor_id(CONCENTRATOR_KEY), "On", "door:concentrator-on"),
                *self.say(short_lines("It hums again.\nBreathing easier."), "door:text", "tomas"),
                *self.say(tickets.closed_lines(2), "door:closed"),
            ]),
        ], [
            *self.say(short_lines("Still no power.\nFix every line!"), "door:no-power"),
        ])]
        return self.trigger("trigger:tomas-door", "Hiroshi Door Checkpoint", DOOR_TRIGGER_SYMBOL,
                            (x, y, width, height), script)

    def trigger(self, key: str, name: str, symbol: str, rect: tuple[int, int, int, int],
                script: list[dict[str, Any]], leave: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        x, y, width, height = rect
        return {
            "_resourceType": "trigger", "id": self.rid(key), "name": name, "prefabId": "",
            "x": x, "y": y, "symbol": symbol, "prefabScriptOverrides": {},
            "width": width, "height": height, "script": script, "leaveScript": leave or [], "_index": 0,
        }

    def exit_trigger(self, link: scene_links.Link) -> dict[str, Any]:
        """A scene_links exit: lift the HUD cutoff, hide the overlay, then switch (or open the work order).

        A gated exit's refusal only explains: it never moves the hero, because a
        nudge plus leftover momentum re-entered the summit exit and looped its
        text (exact ROM 147c23be).
        """
        symbol, key, name = EXIT_SYMBOL[(link.source, link.target)]
        tag = key.removeprefix("trigger:")
        go = [
            self.cutoff_event(150, f"{tag}:cutoff"),
            self.event("EVENT_OVERLAY_HIDE", {}, f"{tag}:hud-hide"),
            *scene_links.exit_events(link, tag, event=self.event, set_value=self.set_value,
                                     number=shared.number),
        ]
        if link.gate is not None:
            wait = self.say(short_lines("Power Hiroshi's\nhouse first."), f"{tag}:not-yet")
            script = [self.if_value(link.gate, 1, f"{tag}:gate", go, wait)]
        else:
            script = go
        return self.trigger(key, name, symbol, link.rect, script)

    # -- hazards (job-wide numbering: ridge.Layout.first_hazard) -------------------
    def board_actor(self, number: int, board: tuple[int, int, int]) -> dict[str, Any]:
        """Cracked board whose idle plank is background art: the actor only shows while it creaks."""
        key = f"board:{number}"
        x, y = hazards.board_actor_position(board)
        event, wait_event = self.event, self.wait_event

        def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
            return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        give_way = [
            own("EVENT_ACTOR_SET_STATE", "break-state", spriteStateId="Break", loopAnim=False),
            own("EVENT_ACTOR_COLLISIONS_ENABLE", "break-hit"),
            wait_event(hazards.BREAK_FRAMES, f"{key}:break-time"),
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "break-safe"),
            # The respawn teleports the hero without a leave event; clear it here.
            self.set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear"),
            wait_event(hazards.BOARD_REST_FRAMES, f"{key}:rest-time"),
        ]
        creak = [
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "creak-safe"),
            own("EVENT_ACTOR_SET_STATE", "creak-state", spriteStateId="Creak", loopAnim=True),
            own("EVENT_ACTOR_SHOW", "creak-visible"),
            wait_event(hazards.CREAK_FRAMES, f"{key}:creak-time"),
            self.if_value(hazards.VAR_ON_BOARD, number, f"{key}:still-on", give_way, []),
            own("EVENT_ACTOR_SET_STATE", "idle-state", spriteStateId="Idle", loopAnim=True),
            own("EVENT_ACTOR_HIDE", "idle-hidden"),
        ]
        actor = self.actor_resource(
            index=0, symbol=f"ridge_board_{number:02d}", name=f"Cracked Board {number}",
            x=x, y=y, sprite_id=hazards.BOARD_SPRITE_ID, key=key,
            start_script=[*hazards.board_start_script(key, event), own("EVENT_ACTOR_HIDE", "init-hidden")],
            update_script=[self.if_value(hazards.VAR_ON_BOARD, number, f"{key}:on-check", creak,
                                         [wait_event(1, f"{key}:idle-tick")])],
            collision_group="1",
        )
        actor["animate"] = True
        return actor

    def board_trigger(self, number: int, board: tuple[int, int, int]) -> dict[str, Any]:
        key = f"board:{number}"
        on_script, leave_script = hazards.board_trigger_scripts(number, f"{key}:trigger", self.set_value)
        return self.trigger(f"trigger:{key}", f"Cracked Board {number} Stand",
                            f"trigger_ridge_cracked_board_{number:02d}", hazards.board_trigger_rect(board),
                            on_script, leave_script)

    def gust_actor(self, number: int, lane: tuple[int, int, int], start_delay: int,
                   sprite_id: str) -> dict[str, Any]:
        """Timed wind lane: warning (no collision), burst (hits via group 1), rest.

        The start delay runs once: the first-cycle branch (the actor starts facing
        "down") hides the gust, waits ``start_delay`` frames and turns it "up".
        """
        row, x0, x1 = lane
        if x1 - x0 + 1 != 3:
            raise ValueError("the authored gust sprite is exactly three tiles wide")
        if start_delay < 0:
            raise ValueError("gust start delay must be non-negative")
        key = f"gust:{number}"
        event, wait_event = self.event, self.wait_event

        def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
            return event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        first_cycle_true = [
            own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
            own("EVENT_ACTOR_HIDE", "delay-hidden"),
        ]
        if start_delay > 0:
            first_cycle_true.append(wait_event(start_delay, f"{key}:start-delay"))
        first_cycle = self.branch_event(
            "EVENT_IF_ACTOR_DIRECTION",
            {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
            f"{key}:first-cycle", first_cycle_true,
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
        return self.actor_resource(
            index=0, symbol=f"ridge_gust_{number:02d}", name=f"Telegraphed Gust {number}",
            x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
            start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
            update_script=update, collision_group="1",
        )

    def whip_actor(self, number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
        """Wind-whipped live wire: hangs sparking, sways (safe warning), whips (hits), hangs.

        Always visible. Placed with its 16x32 canvas bottom on the surface row above the lane.
        """
        row, x0, x1 = lane
        if x1 - x0 + 1 != ridge.WHIP_CANVAS[0] // 8:
            raise ValueError("the whip lane is the sprite's width")
        key = f"whip:{number}"
        return self.actor_resource(
            index=0, symbol=f"ridge_whip_{number:02d}", name=f"Whipping Live Wire {number}",
            x=x0, y=row + 1, sprite_id=ridge.WHIP_SPRITE_ID, key=key, anim_speed=8,
            start_script=hazards.whip_start_script(key, self.event),
            update_script=hazards.whip_update_script(
                key, start_delay, ridge.WHIP_SWAY_FRAMES, ridge.WHIP_SWING_FRAMES, ridge.WHIP_HANG_FRAMES,
                self.event, self.wait_event, self.branch_event),
            collision_group="1",
        )

    def hidden_cable_actor(self, number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
        """Buried live cable: hidden, briefly sparks, then arcs (OBJ palette slot 3)."""
        row, x0, x1 = lane
        if x1 - x0 + 1 != 2:
            raise ValueError("the live arc sprite is exactly two tiles wide")
        key = f"hidden-cable:{number}"
        return self.actor_resource(
            index=0, symbol=f"ridge_hidden_cable_{number:02d}", name=f"Hidden Cable {number}",
            x=x0, y=row, sprite_id=rosa.ARC_SPRITE_ID, key=key, anim_speed=8,
            start_script=hazards.cable_start_script(key, self.event),
            update_script=hazards.cable_update_script(key, start_delay, self.event, self.wait_event,
                                                      self.branch_event, timings=ridge.CABLE_TIMINGS),
            collision_group="1",
        )

    def span_arc_actor(self, number: int, lane: tuple[int, int, int], start_delay: int,
                       sprite_id: str, live_after: int) -> dict[str, Any]:
        """Downed-span arc on the ridge's arc timings (grid_chain.GridChain.span_arc_actor)."""
        return self.chain.span_arc_actor(
            number, lane, start_delay, sprite_id, live_after,
            timings=(ridge.JOB_ARC_WARNING_FRAMES, ridge.JOB_ARC_ACTIVE_FRAMES, ridge.JOB_ARC_REST_FRAMES),
            symbol=f"ridge_span_arc_{number:02d}", name=f"Downed Span Arc {number}",
        )

    def boards(self) -> list[tuple[int, tuple[int, int, int]]]:
        first = self.layout.first_hazard["board"]
        return list(enumerate(self.layout.BOARDS, start=first))

    # -- resources ------------------------------------------------------------------
    def build_scene(self, music_id: str, audio_ids: dict[str, str]) -> dict[str, Any]:
        layout = self.layout
        template = shared.load_json(CLIMB_SCENE)
        sprite_palette_ids = template.get("spritePaletteIds")
        if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
            raise ValueError("the ridge scenes need the climb scene's eight sprite palette slots")
        sprite_palette_ids = list(sprite_palette_ids)
        sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
        sprite_palette_ids[ridge.TOMAS_SPRITE_PALETTE_SLOT] = tomas_palette_id()
        sprite_palette_ids[ridge.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
        # The intro pole sprite's tiles carry OBJ slot intro.SPRITE_SLOTS["pole"].
        sprite_palette_ids[shared.POLE_SPRITE_PALETTE_SLOT] = intro.palette_id("pole")
        # live_arc tiles carry slot 3 (Signal Hill's palette); the whip is ours, slot 6.
        sprite_palette_ids[ridge.ARC_SPRITE_PALETTE_SLOT] = rosa.resource_id("palette:sprite:arc")
        sprite_palette_ids[ridge.WHIP_SPRITE_PALETTE_SLOT] = ridge.WHIP_PALETTE_ID
        sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
        background_palette_ids = [opening.resource_id(f"palette:bg:{name}")
                                  for name, _ in opening.BG_PALETTES] + ["default-ui"]
        if len(background_palette_ids) != 8 or background_palette_ids[7] != "default-ui":
            raise ValueError("ridge background palettes must preserve the UI in slot 7")
        for slot, palette_id in self.chain.chain_palette_ids(0).items():
            background_palette_ids[slot] = palette_id
        scene = dict(template)
        x, y = scenes.editor_position(self.folder)
        scene.update({
            "id": layout.SCENE_ID,
            "_index": SCENE_INDEX[self.folder],
            "name": layout.NAME,
            "type": "PLATFORM",
            "width": ridge.MAP_W,
            "height": ridge.MAP_H,
            "x": x,
            "y": y,
            "collisions": shared.collision_rle(layout.collision_grid(), ridge.MAP_W, ridge.MAP_H),
            "symbol": SCENE_SYMBOL[self.folder],
            "backgroundId": layout.BACKGROUND_ID,
            "paletteIds": background_palette_ids,
            "spritePaletteIds": sprite_palette_ids,
            "script": self.scene_script(music_id, audio_ids),
            # shock.shock_events builds its own IDs from the key: one key per scene.
            "playerHit1Script": self.respawn_events("player-hit" if self.entry else "saddle-player-hit",
                                                    audio_ids["death"]),
            "playerHit2Script": [],
            "playerHit3Script": [],
        })
        return scene

    def build_actors(self, sprite_ids: dict[str, str]) -> list[dict[str, Any]]:
        layout = self.layout
        actors = [self.tomas_actor(), self.concentrator_actor()] if layout.HOUSE else []
        # The snapped cable is part of the pole sprite; the boxes are background transformers.
        actors += [self.chain.pole_actor(line, 0, intro.POLE_SPRITE_ID) for line in self.chain.pole_lines()]
        actors += [self.gust_actor(number, lane, delay, sprite_ids["gust"])
                   for number, (lane, delay) in enumerate(zip(layout.GUST_LANES, layout.GUST_START_DELAYS),
                                                          start=layout.first_hazard["gust"])]
        number = layout.first_hazard["span"]
        for span in layout.FALLEN_SPANS:
            for lane, delay in zip(span["arcs"], span["delays"]):
                actors.append(self.span_arc_actor(number, lane, delay, sprite_ids["arc"], span["live_after"]))
                number += 1
        actors += [self.whip_actor(number, lane, delay)
                   for number, (lane, delay) in enumerate(zip(layout.WHIP_LANES, layout.WHIP_START_DELAYS),
                                                          start=layout.first_hazard["whip"])]
        actors += [self.hidden_cable_actor(number, lane, delay)
                   for number, (lane, delay) in enumerate(zip(layout.HIDDEN_CABLES, layout.CABLE_START_DELAYS),
                                                          start=layout.first_hazard["cable"])]
        # Cracked boards come last: the highest indexes draw on top.
        actors += [self.board_actor(number, board) for number, board in self.boards()]
        if len(actors) > ridge.MAX_SCENE_ACTORS:
            raise ValueError(f"{len(actors)} actors exceed the engine's {ridge.MAX_SCENE_ACTORS}")
        for position, actor in enumerate(actors):
            actor["_index"] = position
        return actors

    def build_triggers(self, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
        # Exits first: the engine fires only the first trigger whose tiles the hero's box
        # overlaps, and a door-first order made the next job unreachable (ROM 6bfec7b4).
        triggers = [self.exit_trigger(link) for link in self.layout.links]
        if self.layout.HOUSE:
            triggers.append(self.door_trigger(audio_ids["connect"]))
        triggers += [self.board_trigger(number, board) for number, board in self.boards()]
        triggers += [self.chain.box_zone_trigger(line, symbol=f"trigger_ridge_{line['key']}_reach", index=0)
                     for line in self.chain.box_lines()]
        triggers += [self.chain.pole_zone_trigger(line, symbol=f"trigger_ridge_{line['key']}_pole_zone", index=0)
                     for line in self.chain.pole_lines()]
        for index, trigger in enumerate(triggers):
            trigger["_index"] = index
        return triggers

    def box_script_resources(self, audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
        return self.chain.box_script_resources(label="Wind Ridge", file_prefix="wind_ridge",
                                               connect_sound_id=audio_ids["connect"])


BUILDERS = {folder: SceneBuilder(folder) for folder in ridge.SCENE_ORDER}


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the Ridge variables without changing any existing entry.

    Same rule as make_climb_scene.merged_variables: an existing ID with a
    different name or symbol is refused rather than renamed.
    """
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*ridge.VARIABLES, *hazards.VARIABLES, *grid_chain.VARIABLES, climb.NEAR_VARIABLE):
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in merged["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            merged["variables"].append(value)
    return merged


def write_variables() -> None:
    data = shared.load_json(VARIABLES_PATH)
    contents = json.dumps(merged_variables(data), indent=2) + "\n"
    if VARIABLES_PATH.read_text(encoding="utf-8") != contents:
        VARIABLES_PATH.write_text(contents, encoding="utf-8")
        print("registered ridge variables without changing existing variables")


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other generators produce these art files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def audio_and_sprite_ids() -> tuple[str, dict[str, str], dict[str, str]]:
    music_id = shared.sidecar_id(MUSIC_SIDECAR, "music")
    audio_ids = {
        "death": shared.sidecar_id(DEATH_SOUND, "sound"),
        "connect": shared.sidecar_id(CONNECT_SOUND, "sound"),
        "pickup": shared.sidecar_id(PICKUP_SOUND, "sound"),
    }
    sprite_ids = {"gust": shared.sidecar_id(GUST_SPRITE, "sprite"), "arc": shared.sidecar_id(ARC_SPRITE, "sprite")}
    return music_id, audio_ids, sprite_ids


def all_box_script_resources(audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    return [item for builder in BUILDERS.values() for item in builder.box_script_resources(audio_ids)]


def main() -> None:
    music_id, audio_ids, sprite_ids = audio_and_sprite_ids()
    warn_if_missing_asset(ridge.WHIP_SPRITE_ID, "sprites", "whipping wire sprite")
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")
    warn_if_missing_asset(ridge.TOMAS_SPRITE_ID, "sprites", "Hiroshi sprite")
    warn_if_missing_asset(ridge.CONCENTRATOR_SPRITE_ID, "sprites", "oxygen concentrator sprite")
    for layout in ridge.LAYOUTS.values():
        warn_if_missing_asset(layout.BACKGROUND_ID, "backgrounds", f"{layout.folder} background")

    write_variables()
    for relative_path, palette in tomas_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for relative_path, script in all_box_script_resources(audio_ids):
        shared.write_json(PROJECT_DIR / relative_path, script)
    for folder, builder in BUILDERS.items():
        scene = builder.build_scene(music_id, audio_ids)
        actors = builder.build_actors(sprite_ids)
        triggers = builder.build_triggers(audio_ids)
        shared.write_json(builder.scene_dir / "scene.gbsres", scene)
        # This generator owns both scene folders: drop actors/triggers it no longer makes.
        for kind, items in (("actors", actors), ("triggers", triggers)):
            keep = {f"{item['symbol']}.gbsres" for item in items}
            (builder.scene_dir / kind).mkdir(parents=True, exist_ok=True)
            for stale in (builder.scene_dir / kind).glob("*.gbsres"):
                if stale.name not in keep:
                    stale.unlink()
                    print(f"removed retired {folder} {kind[:-1]} {stale.name}")
            for item in items:
                shared.write_json(builder.scene_dir / kind / f"{item['symbol']}.gbsres", item)
        layout = builder.layout
        print(f"generated {folder}: {ridge.MAP_W}x{ridge.MAP_H} PLATFORM, {len(actors)} actors, "
              f"{len(triggers)} triggers; lines {[line['number'] for line in layout.LINES]}, "
              f"{len(layout.GUST_LANES)} gusts, {len(layout.span_arc_lanes())} span arcs, "
              f"{len(layout.WHIP_LANES)} whips, {len(layout.HIDDEN_CABLES)} hidden cables, "
              f"{len(layout.BOARDS)} cracked boards")


if __name__ == "__main__":
    main()
