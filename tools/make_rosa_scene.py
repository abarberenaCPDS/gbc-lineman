"""Generate Priya's job scenes 3A ``signal_hill`` and 3C ``signal_porch`` from ``rosa.py``.

Run with ``python3 tools/make_rosa_scene.py`` from any working directory. 3B
``signal_gully`` is written by ``make_gully_scene.py`` with the same builders
(``RosaScene``). This writes the two scene folders, Priya and arc sprite
palettes, the chain's background palettes (one set for all three scenes), the
box scripts of the lines whose box stands in 3A or 3C, and the job variables.
Geometry, positions, hazard timings and stable IDs live in ``rosa.py``.

Multi-scene job (docs/LEVEL_REDESIGN.md §3). Each scene builds its own
``grid_chain.GridChain(scene=<folder>)`` from the full ``rosa.LINES``: pole
actors and zones only for poles here, box zones and scripts only for boxes
here, the chain refresh, HUD and palettes global. Scene init:

  3A (entry)   job_reset_events (var 16 == 3: zero the job), B script, chain
               refresh, pole init, carry restore, HUD, then fresh_start_events
               (music and the intro lines only on a fresh start)
  3B, 3C       B script, chain refresh, pole init, carry restore, HUD; never
               music. 3C restores Priya, her workstation and the warm window
               once her house is powered.

Exits come from ``scene_links`` (redesign rows; internal links ungated, with a
fade; 3C's work-order exit gated on var 11) and stay first in trigger order.
A hit drops the carried cable home to its pole, wherever that pole stands, and
respawns at this scene's furthest repaired checkpoint, else its upstream entry.

IDs: 3A keeps every ID it had (no prefix); actors and events of 3B and 3C are
namespaced by their folder (``RosaChain.prefix``). Box scripts, zone triggers
and chain palettes are per line / global and need no prefix.
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
VARIABLES_PATH = PROJECT_DIR / "project" / "variables.gbsres"

MUSIC_SIDECAR = "assets/music/cfe_storm_climb.uge.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
PICKUP_SOUND = "assets/sounds/pickup.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (shared palettes, grid sprites and the near variable)
    import grid_chain  # noqa: E402  (the reusable grid chain: events, actors, palettes)
    import hazards  # noqa: E402  (hidden cable, cracked board and whip helpers)
    import intro  # noqa: E402  (intro pole sprite and palette identities, dev HUD)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import opening  # noqa: E402  (shared approved palette/sprite identities)
    import ridge  # noqa: E402  (whip sprite: Wind Ridge's asset, reused here)
    import rosa  # noqa: E402  (Priya's job contract: geometry, IDs, timings)
    import scene_links  # noqa: E402  (every exit and entry)
    import scenes  # noqa: E402  (scene registry: ids, names, editor positions)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import tickets  # noqa: E402  (work orders: CLOSED box)
    import completion  # noqa: E402  (household completion cue)
    import voices  # noqa: E402  (speaker names and text blips)
except ModuleNotFoundError as error:
    raise SystemExit(f"cannot generate Priya's scenes: tools/{error.name}.py is missing") from error

MAX_DIALOGUE_CHARS = shared.MAX_DIALOGUE_CHARS
HILL, GULLY, PORCH = rosa.HILL, rosa.GULLY, rosa.PORCH
SCENE_INDEX = {HILL: 5, GULLY: 12, PORCH: 13}
SYMBOL_PREFIX = {HILL: "signal", GULLY: "gully", PORCH: "porch"}
ROSA_KEY = "rosa"
WORKSTATION_KEY = "workstation"
ROSA_SYMBOL = "signal_rosa"
WORKSTATION_SYMBOL = "signal_workstation"
DOOR_TRIGGER_SYMBOL = "trigger_signal_rosa_door"
POLE_KEY = "pole"
POLE_SYMBOL = "rosa_storm_pole"

# The grid chain, upstream first (rosa.LINES). The house line keeps the original
# job's keys, symbols and names (stable IDs); the feeder line has its own.
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
    _default = {
        "pole": f"pole:{_key}", "cable": f"cable-end:{_key}", "box": f"box:{_key}",
        "pole_symbol": f"signal_{_key}_pole", "cable_symbol": f"signal_{_key}_cable_end",
        "box_symbol": f"signal_{_key}_box", "pole_name": f"Storm Pole ({_key})",
        "cable_name": f"Cable End ({_key})", "box_name": f"Transformer ({_key})",
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
INTRO_LINES = [("Priya's offline.", "Deadline: now!"), ("Sparks bite. Hop!",)]
DROP_HINT = ("Down + A drops", "through timber.")   # the gully's one new idea


def short_lines(*lines: str) -> list[str]:
    return shared.short_lines(*lines)


def rosa_palette_id() -> str:
    return rosa.resource_id("palette:sprite:rosa")


def arc_palette_id() -> str:
    return rosa.resource_id("palette:sprite:arc")


def rosa_palettes() -> list[tuple[str, dict[str, Any]]]:
    def palette(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
        return grid_chain.palette_resource(rosa.resource_id, "Signal Hill", kind, name, colors)

    chain = grid_chain.chain_palette_resources(rosa.resource_id, label="Signal Hill",
                                               file_prefix="signal_hill", palettes=rosa.CHAIN_PALETTES)
    return [
        ("project/palettes/signal_hill_sprite_rosa.gbsres",
         palette("sprite", "rosa", shared.editor_sprite_colors(rosa.ROSA_SPRITE_HARDWARE))),
        ("project/palettes/signal_hill_sprite_arc.gbsres",
         palette("sprite", "arc", shared.editor_sprite_colors(rosa.ARC_SPRITE_HARDWARE))),
        *chain,
    ]


def chain_palette_id(stages_live: int) -> str:
    return grid_chain.chain_palette_id(rosa.resource_id, stages_live)


class RosaChain(grid_chain.GridChain):
    """The job's grid chain for one scene; actor and event IDs carry the scene's ``prefix``.

    Palettes, box scripts and zone triggers keep the job-wide ``rid`` (they are
    global, or exist for one line in one scene only).
    """

    def __init__(self, *, prefix: str = "", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.prefix = prefix

    def event(self, command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
        return {"command": command, "args": args, "id": self.rid(f"event:{self.prefix}{key}")}

    def actor_id(self, key: str) -> str:
        return self.rid(f"actor:{self.prefix}{key}")


class RosaScene:
    """Builders for one of the job's three scenes (``folder``)."""

    def __init__(self, folder: str) -> None:
        self.folder = folder
        self.layout = rosa.LAYOUTS[folder]
        self.width, self.height = rosa.size(folder)
        self.prefix = "" if folder == HILL else f"{folder}:"
        self.sym = SYMBOL_PREFIX[folder]
        self.chain = RosaChain(
            prefix=self.prefix, rid=rosa.resource_id, lines=LINES, chain_var=rosa.VAR_CHAIN_LIVE,
            lines_var=rosa.VAR_LINES_LIVE, carrying_var=rosa.VAR_CARRYING_CABLE, near_var=climb.VAR_NEAR,
            line_bg_slot=rosa.LINE_BG_SLOT, text=ROSA_TEXT, say=self.say, hud=self.hud_events,
            bare_event_key="house", background_boxes=rosa.BACKGROUND_BOXES, scene=folder,
        )
        c = self.chain
        self.event, self.branch_event, self.if_value = c.event, c.branch_event, c.if_value
        self.set_value, self.set_position, self.sound_event = c.set_value, c.set_position, c.sound_event
        self.wait_event, self.actor_state, self.actor_id = c.wait_event, c.actor_state, c.actor_id
        self.actor_resource = c.actor_resource

    def rid(self, key: str) -> str:
        """A scene-namespaced ID for this generator's own triggers."""
        return rosa.resource_id(f"{self.prefix}{key}")

    # -- dialogue and HUD ------------------------------------------------------
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
            self.event("EVENT_TEXT_DRAW", {"text": rosa.HUD_TEXT, "x": 0, "y": 0, "location": "overlay"},
                       f"{key}:counter"),
            *intro.dev_hud_events(self.event, key),
        ]

    def say(self, lines: list[str], key: str, speaker: str | None = None) -> list[dict[str, Any]]:
        """In-play dialogue: lift the HUD's 16px cutoff so the box shows, then redraw the HUD.

        Text behind the cutoff stays invisible while the script waits for A
        (exact ROM), freezing the player. A speaker names the box and gives it
        that character's blip (voices.py).
        """
        for line in (part for text in lines for part in text.split("\n")):
            if len(line) > MAX_DIALOGUE_CHARS:
                raise ValueError(f"dialogue line over {MAX_DIALOGUE_CHARS} chars: {line!r}")
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
        """Swap only Priya's window slot (cold -> powered_window)."""
        name = "powered_window" if powered else "window"
        return self.chain.background_palette_event({rosa.WINDOW_BG_SLOT: opening.resource_id(f"palette:bg:{name}")},
                                                   key)

    # -- Priya (3C) -------------------------------------------------------------
    def rosa_talk_events(self, key: str) -> list[dict[str, Any]]:
        """Priya's talk tree, dispatched by the scene's single B input script."""
        return [self.if_value(rosa.VAR_HOME_POWERED, 1, f"{key}:home", [
            *self.say(short_lines("Back online!\nYou're a star!"), f"{key}:thanks", "rosa"),
        ], [
            self.if_value(rosa.VAR_LINES_LIVE, rosa.LINE_COUNT, f"{key}:lines", [
                *self.say(short_lines("Five lines live!\nTry my door."), f"{key}:live", "rosa"),
            ], [
                *self.say(short_lines("No wifi, no work.\nSend help!"), f"{key}:dead", "rosa"),
            ]),
        ])]

    def rosa_actor(self, index: int) -> dict[str, Any]:
        """Priya outside her door: Waiting until her house is powered, then Relieved (also on re-entry)."""
        key = ROSA_KEY
        x, y = rosa.ROSA
        return self.actor_resource(
            index=index, symbol=ROSA_SYMBOL, name="Priya (Signal Porch)", x=x, y=y,
            sprite_id=rosa.ROSA_SPRITE_ID, key=key, script=self.rosa_talk_events(f"{key}:actor-talk"),
            start_script=[self.if_value(rosa.VAR_HOME_POWERED, 1, f"{key}:home-check", [
                self.actor_state("$self$", "Relieved", f"{key}:relieved"),
            ], [
                self.actor_state("$self$", "Waiting", f"{key}:waiting"),
            ])],
        )

    def workstation_actor(self, index: int) -> dict[str, Any]:
        """Computer and router on Priya's porch table: Off until the door switches them On."""
        key = WORKSTATION_KEY
        x, y = rosa.WORKSTATION
        return self.actor_resource(
            index=index, symbol=WORKSTATION_SYMBOL, name="Priya Workstation", x=x, y=y,
            sprite_id=rosa.WORKSTATION_SPRITE_ID, key=key,
            start_script=[self.if_value(rosa.VAR_HOME_POWERED, 1, f"{key}:home-check", [
                self.actor_state("$self$", "On", f"{key}:on"),
            ], [
                self.actor_state("$self$", "Off", f"{key}:off"),
            ])],
        )

    def door_trigger(self, connect_sound_id: str) -> dict[str, Any]:
        """Priya's door: powering the house is a once-only checkpoint (var 11).

        Only the top row of a standing 24px hero covers the door columns, so the
        respawn tile in front of the door also lands on this trigger; the var 11
        guard keeps that from repeating the reward. All five lines first.
        """
        x, y, width, height = rosa.DOOR_TRIGGER
        script = [self.if_value(rosa.VAR_LINES_LIVE, rosa.LINE_COUNT, "door:lines", [
            self.if_value(rosa.VAR_HOME_POWERED, 0, "door:power-on", [
                self.set_value(rosa.VAR_HOME_POWERED, 1, "door:set-powered"),
                self.sound_event(completion.sound_id(), "door:sfx"),
                self.window_palette_event(True, "door:window-warm"),
                self.actor_state(self.actor_id(ROSA_KEY), "Relieved", "door:rosa-relieved"),
                self.actor_state(self.actor_id(WORKSTATION_KEY), "On", "door:workstation-on"),
                *self.say(short_lines("Router's alive!\nEmail, here I go!"), "door:text", "rosa"),
                *self.say(tickets.closed_lines(3), "door:closed"),
            ]),
        ], [
            *self.say(short_lines("Still no power.\nFix all 5 lines!"), "door:no-power"),
        ])]
        return self.trigger("rosa-door", "Priya Door Checkpoint", DOOR_TRIGGER_SYMBOL, (x, y, width, height),
                            script)

    # -- triggers ----------------------------------------------------------------
    def trigger(self, key: str, name: str, symbol: str, rect: tuple[int, int, int, int],
                script: list[dict[str, Any]], leave: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        x, y, width, height = rect
        return {
            "_resourceType": "trigger", "id": self.rid(f"trigger:{key}"), "name": name, "prefabId": "",
            "x": x, "y": y, "symbol": symbol, "prefabScriptOverrides": {}, "width": width, "height": height,
            "script": script, "leaveScript": leave or [], "_index": 0,
        }

    def exit_trigger(self, link: scene_links.Link) -> dict[str, Any]:
        """One scene_links exit: lift the HUD cutoff, hide the overlay, then switch (with a fade).

        A gated exit (3C's work order) refuses with text only; a nudge plus
        leftover momentum re-entered an exit and looped (exact ROM 147c23be).
        """
        target = "work_order" if link.ticket is not None else link.target
        key = f"exit:{target}"
        go = [
            self.cutoff_event(150, f"{key}:cutoff"),
            self.event("EVENT_OVERLAY_HIDE", {}, f"{key}:hud-hide"),
            *scene_links.exit_events(link, key, event=self.event, set_value=self.set_value,
                                     number=shared.number),
        ]
        script = go
        if link.gate is not None:
            script = [self.if_value(link.gate, 1, f"{key}:gate", go,
                                    self.say(short_lines("Power Priya's\nhouse first."), f"{key}:not-yet"))]
        name = (f"Exit to Work Order {link.ticket}" if link.ticket is not None
                else f"Exit to {scenes.REGISTRY[link.target]['name']}")
        return self.trigger(key, name, f"trigger_{self.sym}_exit_{target}", link.rect, script)

    def board_trigger(self, number: int, board: tuple[int, int, int]) -> dict[str, Any]:
        key = f"board:{number}"
        on_script, leave_script = hazards.board_trigger_scripts(
            number, f"{key}:trigger", self.set_value, self.event, self.actor_id(key), hide_idle=True)
        return self.trigger(key, f"Cracked Board {number} Stand", f"trigger_{self.sym}_cracked_board_{number:02d}",
                            hazards.board_trigger_rect(board), on_script, leave_script)

    # -- hazard actors -------------------------------------------------------------
    def _first_cycle(self, key: str, start_delay: int, hide: bool = True) -> dict[str, Any]:
        """Run once: the actor starts facing down; the branch waits ``start_delay`` and turns it up."""
        true = [self.event("EVENT_ACTOR_SET_DIRECTION",
                           {"actorId": "$self$", "direction": {"type": "direction", "value": "up"}},
                           f"{key}:started")]
        if hide:
            true.append(self.event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:delay-hidden"))
        if start_delay > 0:
            true.append(self.wait_event(start_delay, f"{key}:start-delay"))
        return self.branch_event("EVENT_IF_ACTOR_DIRECTION",
                                 {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                                 f"{key}:first-cycle", true)

    def _timed_actor(self, *, key: str, symbol: str, name: str, lane: tuple[int, int, int], width: int,
                     start_delay: int, sprite_id: str, states: tuple[str, str],
                     timings: tuple[int, int, int]) -> dict[str, Any]:
        """Warning (no collision), active (hits via group 1), rest: the live arc and the gusts."""
        row, x0, x1 = lane
        if x1 - x0 + 1 != width:
            raise ValueError(f"{name}: the authored sprite is exactly {width} tiles wide")
        if start_delay < 0:
            raise ValueError("start delays are non-negative")
        warning, active, rest = timings

        def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
            return self.event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        update = [
            self._first_cycle(key, start_delay),
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "warning-safe"),
            own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId=states[0], loopAnim=True),
            own("EVENT_ACTOR_SHOW", "warning-visible"),
            self.wait_event(warning, f"{key}:warning-time"),
            own("EVENT_ACTOR_SET_STATE", f"{states[1].lower()}-state", spriteStateId=states[1], loopAnim=True),
            own("EVENT_ACTOR_COLLISIONS_ENABLE", f"{states[1].lower()}-active"),
            self.wait_event(active, f"{key}:{states[1].lower()}-time"),
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
            own("EVENT_ACTOR_HIDE", "rest-hidden"),
            self.wait_event(rest, f"{key}:rest-time"),
        ]
        return self.actor_resource(
            index=0, symbol=symbol, name=name, x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
            start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
            update_script=update, collision_group="1",
        )

    def arc_actor(self, number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
        """Priya's free-standing live arc: sparks (safe), arc (hits), dark."""
        return self._timed_actor(
            key=f"arc:{number}", symbol=f"{self.sym}_arc_{number:02d}", name=f"Live Arc {number}", lane=lane,
            width=2, start_delay=start_delay, sprite_id=rosa.ARC_SPRITE_ID, states=("Warning", "Arc"),
            timings=(rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES))

    def gust_actor(self, number: int, lane: tuple[int, int, int], start_delay: int, sprite_id: str
                   ) -> dict[str, Any]:
        """Timed wind lane: warning (safe), burst (hits), rest."""
        return self._timed_actor(
            key=f"gust:{number}", symbol=f"{self.sym}_gust_{number:02d}", name=f"Telegraphed Gust {number}",
            lane=lane, width=3, start_delay=start_delay, sprite_id=sprite_id, states=("Warning", "Burst"),
            timings=(rosa.GUST_WARNING_FRAMES, rosa.GUST_ACTIVE_FRAMES, rosa.GUST_REST_FRAMES))

    def whip_actor(self, number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
        """Wind-whipped wire: safe sway telegraph, then a brief collision swing."""
        row, x0, x1 = lane
        if x1 - x0 + 1 != ridge.WHIP_CANVAS[0] // 8:
            raise ValueError("the whip lane is the sprite's width")
        key = f"whip:{number}"
        return self.actor_resource(
            index=0, symbol=f"{self.sym}_whip_{number:02d}", name=f"Whipping Live Wire {number}",
            x=x0, y=row + 1, sprite_id=ridge.WHIP_SPRITE_ID, key=key, anim_speed=8,
            start_script=hazards.whip_start_script(key, self.event),
            update_script=hazards.whip_update_script(
                key, start_delay, rosa.WHIP_SWAY_FRAMES, rosa.WHIP_SWING_FRAMES, rosa.WHIP_HANG_FRAMES,
                self.event, self.wait_event, self.branch_event),
            collision_group="1",
        )

    def span_arc_actor(self, number: int, lane: tuple[int, int, int], delay: int, live_after: int
                       ) -> dict[str, Any]:
        return self.chain.span_arc_actor(
            number, lane, delay, rosa.ARC_SPRITE_ID, live_after,
            timings=(rosa.JOB_ARC_WARNING_FRAMES, rosa.JOB_ARC_ACTIVE_FRAMES, rosa.JOB_ARC_REST_FRAMES),
            symbol=f"{self.sym}_span_arc_{number:02d}", name=f"Downed Span Arc {number}")

    def hidden_cable_actor(self, number: int, lane: tuple[int, int, int], start_delay: int) -> dict[str, Any]:
        """Buried live cable: hidden, briefly sparks, then arcs (job 3 timings 140/20/24)."""
        row, x0, x1 = lane
        if x1 - x0 + 1 != 2:
            raise ValueError("the live arc sprite is exactly two tiles wide")
        key = f"hidden-cable:{number}"
        return self.actor_resource(
            index=0, symbol=f"{self.sym}_hidden_cable_{number:02d}", name=f"Hidden Cable {number}",
            x=x0, y=row, sprite_id=rosa.ARC_SPRITE_ID, key=key, anim_speed=8,
            start_script=hazards.cable_start_script(key, self.event),
            update_script=hazards.cable_update_script(key, start_delay, self.event, self.wait_event,
                                                      self.branch_event, timings=rosa.CABLE_TIMINGS),
            collision_group="1",
        )

    def board_actor(self, number: int, board: tuple[int, int, int]) -> dict[str, Any]:
        """Cracked board whose idle plank is background art: the actor only shows while it creaks."""
        key = f"board:{number}"
        x, y = hazards.board_actor_position(board)

        def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
            return self.event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        return self.actor_resource(
            index=0, symbol=f"{self.sym}_board_{number:02d}", name=f"Cracked Board {number}",
            x=x, y=y, sprite_id=hazards.BOARD_SPRITE_ID, key=key,
            start_script=[*hazards.board_start_script(key, self.event), own("EVENT_ACTOR_HIDE", "init-hidden")],
            update_script=hazards.board_update_script(
                number, key, self.event, self.wait_event, self.if_value, self.set_value, board, hide_idle=True),
            collision_group="1",
        )

    # -- scene scripts -------------------------------------------------------------
    def respawn_events(self, key: str, death_sound_id: str) -> list[dict[str, Any]]:
        """One shock cue, drop any cable (home to its pole, any scene), then respawn.

        Respawn (rule 4): the furthest repaired line whose checkpoint is in this
        scene, else this scene's upstream entry. In 3C, once Priya's power is on,
        the tile in front of her door.
        """
        chosen = self.chain.checkpoint_chain(key, self.layout["start"])
        if self.folder == PORCH:
            door_x, door_y = rosa.HOUSE_DOOR
            chosen = [self.if_value(rosa.VAR_HOME_POWERED, 0, f"{key}:respawn-check", chosen, [
                self.set_position(door_x - 1, door_y, f"{key}:respawn-door"),
            ])]
        return [
            *self.shock_events(key),
            *self.chain.cable_drop_events(key),
            self.set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
            *chosen,
            *self.chain.recovery_hint_events(key),
        ]

    def shock_events(self, key: str) -> list[dict[str, Any]]:
        """The electrocution beat; shock.py has its own ID namespace, so 3B/3C prefix the key."""
        key = f"{self.prefix}{key}"
        return shock.shock_events(key)

    def scene_script(self, music_id: str, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
        c = self.chain
        npc = {}
        if self.folder == PORCH:
            npc = {"npc_events": self.rosa_talk_events("b-press:npc"), "npc_actor_id": self.actor_id(ROSA_KEY)}
        script = [
            self.event("EVENT_PLAYER_SET_SPRITE", {"spriteSheetId": opening.resource_id("sprite:opening_worker24")},
                       "init-player-sprite"),
        ]
        if self.folder == HILL:
            script += c.job_reset_events(rosa.JOB, extra=[self.set_value(rosa.VAR_HOME_POWERED, 0,
                                                                         "job-reset:home-powered")])
        script += [
            self.set_value(climb.VAR_NEAR, grid_chain.NEAR_NONE, "init-near"),
            # B: pick up, plug in, drop or talk, by the zone the hero stands in (grid_chain).
            c.input_script_event(pickup_sound_id=audio_ids["pickup"], override=True, **npc),
            self.set_value(hazards.VAR_ON_BOARD, 0, "init-on-board"),
        ]
        if self.folder == PORCH:
            script.append(self.if_value(rosa.VAR_HOME_POWERED, 1, "init-window", [
                self.window_palette_event(True, "init-window-warm"),
            ], [
                self.window_palette_event(False, "init-window-cold"),
            ]))
        script += [
            *c.chain_refresh_events("init-chain"),
            *c.pole_init_events(),
            *c.carry_restore_events(),
            *self.hud_events("init-hud"),
        ]
        if self.folder == HILL:
            intro_text = [event for index, lines in enumerate(INTRO_LINES)
                          for event in self.say(short_lines(*lines), ("intro", "spark")[index])]
            script += c.fresh_start_events(rosa.JOB, [c.music_event(music_id), *intro_text])
        if self.folder == GULLY:
            # The gully's one new idea, until line 3 is repaired (the first descent).
            script.append(self.if_value(rosa.VAR_MIDDLE_LIVE, 0, "drop-hint",
                                        self.say(short_lines(*DROP_HINT), "drop-hint:text")))
        return script

    # -- the scene ----------------------------------------------------------------
    def build_scene(self, music_id: str, audio_ids: dict[str, str]) -> dict[str, Any]:
        template = shared.load_json(CLIMB_SCENE)
        sprite_palette_ids = template.get("spritePaletteIds")
        if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
            raise ValueError("Priya's scenes need the climb scene's eight sprite palette slots")
        sprite_palette_ids = list(sprite_palette_ids)
        sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
        sprite_palette_ids[rosa.ROSA_SPRITE_PALETTE_SLOT] = rosa_palette_id()
        sprite_palette_ids[rosa.GRID_SPRITE_PALETTE_SLOT] = climb.grid_resource_id("palette:sprite:grid")
        sprite_palette_ids[rosa.ARC_SPRITE_PALETTE_SLOT] = arc_palette_id()
        sprite_palette_ids[intro.SPRITE_SLOTS["pole"]] = intro.palette_id("pole")
        sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
        sprite_palette_ids[ridge.WHIP_SPRITE_PALETTE_SLOT] = ridge.WHIP_PALETTE_ID
        background_palette_ids = [opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES]
        background_palette_ids += ["default-ui"]
        if len(background_palette_ids) != 8:
            raise ValueError("background palettes must preserve the UI in slot 7")
        for slot, palette_id in self.chain.chain_palette_ids(0).items():
            background_palette_ids[slot] = palette_id
        entry = scenes.REGISTRY[self.folder]
        x, y = scenes.editor_position(self.folder)
        scene = dict(template)
        scene.update({
            "id": entry["id"],
            "_index": SCENE_INDEX[self.folder],
            "name": entry["name"],
            "type": "PLATFORM",
            "width": self.width,
            "height": self.height,
            "x": x,
            "y": y,
            "collisions": shared.collision_rle(rosa.collision_grid(self.folder), self.width, self.height),
            "symbol": f"scene_{self.folder}",
            "backgroundId": rosa.BACKGROUND_IDS[self.folder],
            "paletteIds": background_palette_ids,
            "spritePaletteIds": sprite_palette_ids,
            "script": self.scene_script(music_id, audio_ids),
            "playerHit1Script": self.respawn_events("player-hit", audio_ids["death"]),
            "playerHit2Script": [],
            "playerHit3Script": [],
        })
        return scene

    def build_actors(self, sprite_ids: dict[str, str]) -> list[dict[str, Any]]:
        layout = self.layout
        actors: list[dict[str, Any]] = []
        if self.folder == PORCH:
            actors += [self.rosa_actor(0), self.workstation_actor(1)]
        # The snapped cable is part of the pole sprite; the boxes are background transformers.
        actors += [self.chain.pole_actor(line, 0, intro.POLE_SPRITE_ID) for line in self.chain.pole_lines()]
        actors += [self.arc_actor(n, lane, delay)
                   for n, (lane, delay) in enumerate(zip(layout["arcs"], layout["arc_delays"]), start=1)]
        actors += [self.gust_actor(n, lane, delay, sprite_ids["gust"])
                   for n, (lane, delay) in enumerate(zip(layout["gusts"], layout["gust_delays"]), start=1)]
        number = 0
        for span in layout["spans"]:
            for lane, delay in zip(span["arcs"], span["delays"]):
                number += 1
                actors.append(self.span_arc_actor(number, lane, delay, span["live_after"]))
        actors += [self.whip_actor(n, lane, delay)
                   for n, (lane, delay) in enumerate(zip(layout["whips"], layout["whip_delays"]), start=1)]
        actors += [self.hidden_cable_actor(n, lane, delay)
                   for n, (lane, delay) in enumerate(zip(layout["cables"], layout["cable_delays"]), start=1)]
        # Cracked boards come last: the highest indexes draw on top.
        actors += [self.board_actor(n, board) for n, board in enumerate(layout["boards"], start=1)]
        if len(actors) != rosa.actor_count(self.folder):
            raise ValueError(f"{len(actors)} actors built, expected {rosa.actor_count(self.folder)}")
        for position, actor in enumerate(actors):
            actor["_index"] = position
        return actors

    def build_triggers(self, audio_ids: dict[str, str]) -> list[dict[str, Any]]:
        # Exits come first: the engine fires only the first trigger whose tiles the
        # hero's box overlaps (at the porch wall the hero overlaps door and exit).
        triggers = [self.exit_trigger(link) for link in rosa.links(self.folder)]
        if self.folder == PORCH:
            triggers.append(self.door_trigger(audio_ids["connect"]))
        triggers += [self.board_trigger(n, board) for n, board in enumerate(self.layout["boards"], start=1)]
        triggers += [self.chain.box_zone_trigger(line, symbol=f"trigger_signal_{line['key']}_reach", index=0)
                     for line in self.chain.box_lines()]
        triggers += [self.chain.pole_zone_trigger(line, symbol=f"trigger_signal_{line['key']}_pole_zone", index=0)
                     for line in self.chain.pole_lines()]
        grid_chain.check_scene_limits(rosa.actor_count(self.folder), len(triggers))
        for index, trigger in enumerate(triggers):
            trigger["_index"] = index
        return triggers

    def box_script_resources(self, audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
        return self.chain.box_script_resources(label="Signal Hill", file_prefix="signal_hill",
                                               connect_sound_id=audio_ids["connect"])


SCENES = {folder: RosaScene(folder) for folder in rosa.SCENE_ORDER}
HILL_SCENE, GULLY_SCENE, PORCH_SCENE = (SCENES[folder] for folder in rosa.SCENE_ORDER)
CHAIN = HILL_SCENE.chain


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def merged_variables(data: dict[str, Any]) -> dict[str, Any]:
    """Append the job's variables without changing any existing entry (refuse a rename)."""
    merged = json.loads(json.dumps(data))
    for key, name, symbol in (*rosa.VARIABLES, *hazards.VARIABLES, *grid_chain.VARIABLES,
                               climb.NEAR_VARIABLE):
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
        print("registered Signal Hill variables without changing existing variables")


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other generators produce these art files; this one only references their IDs."""
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
    for resource_id, folder, label in (
            (rosa.ROSA_SPRITE_ID, "sprites", "Priya sprite"),
            (rosa.WORKSTATION_SPRITE_ID, "sprites", "Priya workstation sprite"),
            (rosa.ARC_SPRITE_ID, "sprites", "live arc sprite"),
            (ridge.WHIP_SPRITE_ID, "sprites", "whipping wire sprite"),
            (hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")):
        warn_if_missing_asset(resource_id, folder, label)
    return music_id, audio_ids, sprite_ids


def write_scene(folder: str, music_id: str, audio_ids: dict[str, str], sprite_ids: dict[str, str]) -> None:
    """Write one scene folder (owned whole: stale actors/triggers are removed) and its box scripts."""
    builder = SCENES[folder]
    warn_if_missing_asset(rosa.BACKGROUND_IDS[folder], "backgrounds", f"{folder} background")
    scene = builder.build_scene(music_id, audio_ids)
    actors = builder.build_actors(sprite_ids)
    triggers = builder.build_triggers(audio_ids)
    for relative_path, script in builder.box_script_resources(audio_ids):
        shared.write_json(PROJECT_DIR / relative_path, script)
    scene_dir = SCENES_DIR / folder
    shared.write_json(scene_dir / "scene.gbsres", scene)
    for kind, items in (("actors", actors), ("triggers", triggers)):
        keep = {f"{item['symbol']}.gbsres" for item in items}
        for stale in (scene_dir / kind).glob("*.gbsres"):
            if stale.name not in keep:
                stale.unlink()
                print(f"removed retired {folder} {kind[:-1]} {stale.name}")
        for item in items:
            shared.write_json(scene_dir / kind / f"{item['symbol']}.gbsres", item)
    layout = rosa.LAYOUTS[folder]
    print(f"generated {folder}: {builder.width}x{builder.height} PLATFORM, {len(actors)} actors, "
          f"{len(triggers)} triggers; poles {len(builder.chain.pole_lines())}, boxes "
          f"{len(builder.chain.box_lines())}; hazards {rosa.hazard_count(folder)} (arcs {len(layout['arcs'])}, "
          f"gusts {len(layout['gusts'])}, span arcs {len(rosa.span_arc_lanes(folder))}, "
          f"whips {len(layout['whips'])}, cables {len(layout['cables'])}, boards {len(layout['boards'])})")


def main() -> None:
    music_id, audio_ids, sprite_ids = load_ids()
    write_variables()
    for relative_path, palette in rosa_palettes() + shared.hazard_palettes():
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for folder in (HILL, PORCH):
        write_scene(folder, music_id, audio_ids, sprite_ids)


if __name__ == "__main__":
    main()
