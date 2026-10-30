"""Reusable grid chain for PLATFORM job scenes (Wind Ridge; Signal Hill and Pine Hollow next).

A grid chain is one left-to-right run of power: an edge feeds pole 1, line 1
runs to box 1 (a transformer), box 1 feeds pole 2, and so on to a house junction
box. Each line is repaired by carrying its pole's dangling cable end to its box.
A box is Live only when every line up to and including its own is repaired; the
wires (background palette) and the fallen-span arcs follow the same count.

This module holds the generic parts: chain palettes, the chain's script events
(refresh, cable drop, checkpoint respawn), its actor builders (cable end, pole,
box, span arc), and the scanline/camera helpers the tests use. Coordinates,
resource IDs, symbols, names, dialogue, HUD and other hazards stay in the job's
contract module and scene generator.

Contract module (tools/<job>.py: geometry and IDs, no Pillow). It must define:

  resource_id(key) -> str           stable uuid per key; every chain event, actor and
                                    palette ID is derived from it
  LINES                             upstream first; each dict has
                                      key         short name, e.g. "feeder"
                                      pole        (x, y) feet tile of the pole
                                      box         (x, y) feet tile of the box
                                      box_kind    "transformer" or "junction"
                                      checkpoint  (x, y) respawn tile once the line is repaired
                                      live_var    project variable set when the line is repaired
                                      number      1-based position (also the carried-cable value)
  STAGE_COLOR_INDEX                 metal-slot colour index per stage, 1..3, distinct; one per line
  METAL_DEAD                        the metal slot's four colours (index 0 is a placeholder)
  WIRE_LIVE, WIRE_DEAD              colours a stage takes when lit and unlit
  WIRE_ROUTES                       [(stage, polyline of (x, y) cells)] for the background art
  FALLEN_SPANS                      [{"columns": (x0, x1), "live_after": k, "arcs": [(row, x0, x1)],
                                      "delays": [frames]}]; the span lies under LINES[k] (0-based)
                                      and goes live once k leading lines are repaired
  VAR_CHAIN_LIVE                    variable: how many leading lines are repaired (0..N)
  VAR_CARRYING_CABLE                variable: which line's cable the hero carries (0 = none)
  VAR_LINES_LIVE                    variable: HUD count of repaired lines
  LINE_BG_SLOT                      primary background palette slot that holds the wires
  MAP_W, GROUND_ROW, HUD_ROWS       used by the self-check helpers only

Scene module (tools/make_<job>_scene.py) builds one GridChain from the contract:

  rid               the contract's resource_id
  lines             the contract LINES plus scene-side fields: pole/box/cable (actor keys),
                    pole_at/box_at (tiles), pole_symbol/cable_symbol/box_symbol,
                    pole_name/cable_name/box_name (display names)
  chain_var, lines_var, carrying_var, line_bg_slot
                    the contract variables above
  text              dialogue: pickup, hands_full (cable end); already, all_live, lit, dark,
                    no_cable, wrong_cable (box). Each is one box string ("\\n" between lines,
                    at most MAX_DIALOGUE_CHARS per line; the scene validates).
  say, hud          the scene's own dialogue and HUD builders: say(lines, key, speaker=None)
                    and hud(key), both returning event lists
  bare_event_key    optional line key whose cable-drop events keep an un-suffixed key
                    (legacy event IDs); None for new jobs
  background_boxes  opt-in: the boxes are background art (transformer_art.py), not actors.
                    The chain refresh then only sets the stage count and swaps the wire
                    palettes (a box's top tile row sits in its stage's wire slot and lights
                    with it), and the box scripts bind only the line's pole. No box actor
                    exists, which frees one actor per line (see "Background boxes" below).

B-press model (Abe: "there should be an action, like pressing the button"): nothing
connects, picks up or drops on contact. Walking into a zone only records where the
hero stands in one project variable, ``near_var`` (climb.VAR_NEAR):

  0                 no zone (a carried cable drops back to its pole on B)
  line number       pole zone (pole_zone_rect): the cable-end pickup
  BOX_ZONE + number box zone (reach_rect, or the line's own "reach"): plug in
  NPC_ZONE          a neighbour's zone: explicit scene-side talk dispatch

``pole_zone_trigger``, ``box_zone_trigger`` and ``npc_zone_trigger`` return the
zone triggers (call once each, after the job's own triggers; box zones first, so
where zones overlap a box wins over a pole and a pole over a neighbour). The enter
script sets the value; the leave script clears it only while it still holds this
zone's value, so the order of enter and leave in a same-frame hand-over does not
matter. ``input_script_event`` is the one B input script: it runs the zone's pickup,
drop, or explicit neighbour-talk branch. Box plug-in branches call canonical
project custom scripts instead of inlining their large refresh bodies in the
shared B input script; each box remains individually gated by its own zone.

Palette resources: chain_palettes() gives {stages: colours} for up to three lines,
or {stages: {slot: colours}} for four to six. chain_palette_resources() turns
these into project/palettes files. chain_palette_id() accepts a slot (default 5).

Background boxes (opt-in, ``background_boxes=True``; the climb and Wind Ridge use it).
A job converts in four steps, everything else (pole actors, zones, B dispatcher,
box custom scripts, the synchronous EVENT_CALL_CUSTOM_EVENT) stays as it is:

  1. art generator: reserve ``transformer_art.tiles(box)`` for every line, the top
     tiles in the line's stage wire slot (``stage_slot``), the body tiles in a
     hardware-like slot, and ``transformer_art.paint`` them; count the art's stage
     pixels as that stage's own wire pixels in any stray-colour check
  2. contract: keep wire routes ending in one of the two top tiles (``box[1] - 2``),
     not the sprite's pole-style top (``box[1] - 3``); drop the box actors from
     the actor count and the OBJ budget (``chain_sprites(..., background_boxes=True)``)
  3. scene generator: ``GridChain(..., background_boxes=True)`` and stop adding
     ``box_actor``; the generator's stale-file sweep deletes the old box actor files
  4. tests: boxes no longer have actor states; the refresh is checked by its palettes

Test helpers: scanline_load() counts OBJ columns per tile row (SCANLINE_OBJ_LIMIT
is the budget); the camera window is SCREEN_TILES wide and clamps at both map edges.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

import climb

Event = dict[str, Any]
Rid = Callable[[str], str]

MAX_STAGES = 6            # two BG slots each carry three stages; colour 0 is a placeholder
LINE_BG_SLOT_1 = 5
LINE_BG_SLOT_2 = 6
MAX_ACTORS = 20
MAX_TRIGGERS = 30
SCREEN_TILES = 20         # PLATFORM camera window width; the camera clamps at both map edges
SCANLINE_OBJ_LIMIT = 10   # 8x16 OBJs per tile row the tests allow on screen at once

# Values of the ``near`` variable (see the module docstring). Pole zones use the
# line number (1..N), box zones BOX_ZONE + line number; NPC_ZONE is shared.
NEAR_NONE = 0
BOX_ZONE = 100
NPC_ZONE = 200
CARRY_TEXT_DROPPED = "Cable dropped."

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP
COL_SOLID = climb.COL_SOLID


def number(value: int) -> dict[str, Any]:
    """GB Studio number literal (the same shape as make_climb_scene.number)."""
    return {"type": "number", "value": value}


# ---------------------------------------------------------------------------
# Chain palettes (background wires and boxes)
# ---------------------------------------------------------------------------
def chain_palette_name(stages_live: int) -> str:
    return f"chain_{stages_live}_live"


def check_stage_colors(stage_color_index: Sequence[int]) -> None:
    assert 1 <= len(stage_color_index) <= MAX_STAGES, "one to six chain stages"
    assert all(1 <= index <= 3 for index in stage_color_index), "stage colours use indexes 1-3 per slot"
    for start in (0, 3):
        slot_colors = stage_color_index[start:start + 3]
        assert len(set(slot_colors)) == len(slot_colors), "stage colours must be distinct within each slot"


def chain_palette(stages_live: int, *, metal_dead: Sequence[str], wire_live: str, wire_dead: str,
                  stage_color_index: Sequence[int]) -> list[str] | dict[int, list[str]]:
    """Wire-slot colours with the first ``stages_live`` stages lit.

    One to three stages retain the historical single-palette list result. For
    four to six, return {BG slot: colours} for both wire slots.
    """
    check_stage_colors(stage_color_index)
    assert 0 <= stages_live <= len(stage_color_index), "live stage count is out of range"

    def slot_colors(start: int, end: int) -> list[str]:
        colors = list(metal_dead)
        for stage in range(start + 1, end + 1):
            index = stage_color_index[stage - 1]
            colors[index] = wire_live if stage <= stages_live else wire_dead
        return colors

    if len(stage_color_index) <= 3:
        return slot_colors(0, len(stage_color_index))
    return {
        LINE_BG_SLOT_1: slot_colors(0, 3),
        LINE_BG_SLOT_2: slot_colors(3, len(stage_color_index)),
    }


def chain_palettes(*, metal_dead: Sequence[str], wire_live: str, wire_dead: str,
                   stage_color_index: Sequence[int]) -> dict[int, list[str]]:
    """{stages_live: colours} for every count from 0 to the number of stages."""
    check_stage_colors(stage_color_index)
    return {stages: chain_palette(stages, metal_dead=metal_dead, wire_live=wire_live,
                                  wire_dead=wire_dead, stage_color_index=stage_color_index)
            for stages in range(len(stage_color_index) + 1)}


def palette_resource(rid: Rid, label: str, kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = f"{label} {kind} {name}"
    return {
        "_resourceType": "palette",
        "id": rid(f"palette:{kind}:{name.replace(' ', '_').lower()}"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def chain_palette_resources(rid: Rid, *, label: str, file_prefix: str,
                            palettes: dict[int, list[str] | dict[int, list[str]]]
                            ) -> list[tuple[str, dict[str, Any]]]:
    """(project path, palette resource) for every stage count and wire slot."""
    resources = []
    for stages, palette in palettes.items():
        slot_colors = ({LINE_BG_SLOT_1: palette} if isinstance(palette, list) else palette)
        for slot, colors in slot_colors.items():
            suffix = "" if slot == LINE_BG_SLOT_1 else f"_slot_{slot}"
            name = f"{chain_palette_name(stages)}{suffix}"
            resources.append((f"project/palettes/{file_prefix}_bg_{name}.gbsres",
                              palette_resource(rid, label, "bg", name, colors)))
    return resources


def chain_palette_id(rid: Rid, stages_live: int, slot: int = LINE_BG_SLOT_1) -> str:
    """Stable palette ID for a stage count and wire slot (slot 5 stays compatible)."""
    name = chain_palette_name(stages_live)
    if slot != LINE_BG_SLOT_1:
        name += f"_slot_{slot}"
    return rid(f"palette:bg:{name}")


def chain_palette_ids(rid: Rid, stages_live: int,
                      slots: Sequence[int] = (LINE_BG_SLOT_1, LINE_BG_SLOT_2)) -> dict[int, str]:
    """Palette IDs by BG slot, convenient for scenes that use both wire slots."""
    return {slot: chain_palette_id(rid, stages_live, slot) for slot in slots}


# ---------------------------------------------------------------------------
# The chain: events, actors and their IDs
# ---------------------------------------------------------------------------
class GridChain:
    """Script and actor builders for one scene's grid chain (see the module docstring)."""

    def __init__(self, *, rid: Rid, lines: Sequence[dict[str, Any]], chain_var: str, lines_var: str,
                 carrying_var: str, near_var: str, line_bg_slot: int, text: dict[str, str],
                 say: Callable[..., list[Event]], hud: Callable[[str], list[Event]],
                 bare_event_key: str | None = None, line_bg_slot_2: int | None = None,
                 background_boxes: bool = False) -> None:
        self.rid = rid
        self.lines = list(lines)
        assert 1 <= len(self.lines) <= MAX_STAGES, "a grid chain has one to six lines"
        self.chain_var = chain_var
        self.lines_var = lines_var
        self.carrying_var = carrying_var
        self.near_var = near_var
        self.line_bg_slot = line_bg_slot
        self.line_bg_slot_2 = line_bg_slot_2 if line_bg_slot_2 is not None else LINE_BG_SLOT_2
        self.text = dict(text)
        self.say = say
        self.hud = hud
        self.bare_event_key = bare_event_key
        self.background_boxes = background_boxes

    # -- IDs -----------------------------------------------------------------
    def actor_id(self, key: str) -> str:
        return self.rid(f"actor:{key}")

    def chain_palette_id(self, stages_live: int) -> str:
        return chain_palette_id(self.rid, stages_live)

    def chain_palette_ids(self, stages_live: int) -> dict[int, str]:
        slots = [self.line_bg_slot]
        if len(self.lines) > 3:
            slots.append(self.line_bg_slot_2)
        return {slot: chain_palette_id(self.rid, stages_live, slot) for slot in slots}

    # -- generic events --------------------------------------------------------
    def event(self, command: str, args: dict[str, Any], key: str) -> Event:
        return {"command": command, "args": args, "id": self.rid(f"event:{key}")}

    def branch_event(self, command: str, args: dict[str, Any], key: str,
                     true_events: list[Event], false_events: list[Event] | None = None) -> Event:
        return {
            **self.event(command, args, key),
            "children": {"true": true_events, "false": false_events or []},
        }

    def if_value(self, variable_id: str, value: int, key: str,
                 true_events: list[Event], false_events: list[Event] | None = None) -> Event:
        return self.branch_event(
            "EVENT_IF",
            {"condition": {
                "type": "eq",
                "valueA": {"type": "variable", "value": variable_id},
                "valueB": number(value),
            }},
            key, true_events, false_events,
        )

    def if_at_least(self, variable_id: str, value: int, key: str,
                    true_events: list[Event], false_events: list[Event] | None = None) -> Event:
        return self.branch_event(
            "EVENT_IF",
            {"condition": {
                "type": "gte",
                "valueA": {"type": "variable", "value": variable_id},
                "valueB": number(value),
            }},
            key, true_events, false_events,
        )

    def if_actor_distance(self, actor_id: str, other_actor_id: str, distance: int, key: str,
                          true_events: list[Event], false_events: list[Event] | None = None) -> Event:
        """GB Studio's native actor-distance predicate; no scratch variables required."""
        return self.branch_event(
            "EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR",
            {"actorId": actor_id, "operator": "<=", "distance": number(distance),
             "otherActorId": other_actor_id},
            key, true_events, false_events,
        )

    def set_value(self, variable_id: str, value: int, key: str) -> Event:
        return self.event("EVENT_SET_VALUE", {"variable": variable_id, "value": number(value)}, key)

    def set_position(self, x: int, y: int, key: str) -> Event:
        return self.event("EVENT_ACTOR_SET_POSITION", {
            "units": "tiles", "actorId": "player", "x": number(x), "y": number(y),
        }, key)

    def background_palette_event(self, slots: dict[int, str], key: str) -> Event:
        args: dict[str, Any] = {f"palette{index}": "keep" for index in range(8)}
        for slot, palette_id in slots.items():
            args[f"palette{slot}"] = palette_id
        return self.event("EVENT_PALETTE_SET_BACKGROUND", args, key)

    def sound_event(self, sound_id: str, key: str) -> Event:
        return self.event("EVENT_SOUND_PLAY_EFFECT", {
            "units": "time", "type": sound_id, "priority": "high", "pitch": 4,
            "frequency": 200, "duration": 0.5, "wait": True, "effect": 0,
        }, key)

    def wait_event(self, frames: int, key: str) -> Event:
        return self.event("EVENT_WAIT", {"units": "frames", "frames": number(frames)}, key)

    def actor_state(self, target: str, state: str, key: str, loop: bool = True) -> Event:
        return self.event("EVENT_ACTOR_SET_STATE", {
            "actorId": target, "spriteStateId": state, "loopAnim": loop,
        }, key)

    def actor_resource(self, *, index: int, symbol: str, name: str, x: int, y: int, sprite_id: str,
                       key: str, animate: bool = True, anim_speed: int = 15,
                       script: list[Event] | None = None,
                       start_script: list[Event] | None = None,
                       update_script: list[Event] | None = None,
                       collision_group: str = "") -> dict[str, Any]:
        return {
            "_resourceType": "actor",
            "id": self.actor_id(key),
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

    # -- chain events ----------------------------------------------------------
    def chain_refresh_events(self, key: str) -> list[Event]:
        """Light the wires as far as the chain is continuous, and each box with them.

        The wire palette shows how many leading lines are repaired; a box is Live
        only when every line up to and including its own is.
        """
        def lit(stages: int) -> list[Event]:
            out = [self.set_value(self.chain_var, stages, f"{key}:stages-{stages}"),
                   self.background_palette_event(self.chain_palette_ids(stages),
                                                 f"{key}:palette-{stages}")]
            if self.background_boxes:
                return out          # the wire palettes are the boxes' Dead/Live
            for line in self.lines:
                state = "Live" if line["number"] <= stages else "Dead"
                out.append(self.actor_state(self.actor_id(line["box"]), state,
                                            f"{key}:box-{stages}-{line['key']}"))
            return out

        events = lit(len(self.lines))
        for line in reversed(self.lines):
            events = [self.if_value(line["live_var"], 1, f"{key}:{line['key']}", events,
                                    lit(line["number"] - 1))]
        return events

    def checkpoint_chain(self, key: str, start: tuple[int, int]) -> list[Event]:
        """Respawn target: the furthest repaired line's checkpoint, else ``start``."""
        chosen = [self.set_position(*start, f"{key}:respawn-start")]
        for line in self.lines:
            chosen = [self.if_value(line["live_var"], 1, f"{key}:respawn-{line['key']}-check", [
                self.set_position(*line["checkpoint"], f"{key}:respawn-{line['key']}"),
            ], chosen)]
        return chosen

    def cable_drop_events(self, key: str, text: str | None = None) -> list[Event]:
        """A carried cable falls back to its own pole: when the carrier is hit, or on B away from every zone.

        ``text`` adds one line of dialogue after the drop (the B press says so).
        """
        events = []
        for line in self.lines:
            tag = key if line["key"] == self.bare_event_key else f"{key}:{line['key']}"
            events.append(self.if_value(self.carrying_var, line["number"], f"{tag}:cable-drop", [
                self.set_value(self.carrying_var, 0, f"{tag}:cable-clear"),
                self.actor_state("player", "", f"{tag}:hero-empty-hands"),
                self.actor_state(self.actor_id(line["pole"]), "Snapped+Cable", f"{tag}:pole-cable"),
                *self.hud(f"{tag}:cable-hud"),
                *(self.say([text], f"{tag}:dropped") if text else []),
            ]))
        return events

    # -- B press: zones, and the one input script that acts on them -----------
    def zone_trigger(self, *, name: str, symbol: str, index: int, rect: tuple[int, int, int, int],
                     value: int, trigger_key: str) -> dict[str, Any]:
        """A zone trigger: entering sets ``near_var`` to ``value``; leaving clears it if it still holds it."""
        x, y, width, height = rect
        key = f"zone:{trigger_key}"
        return {
            "_resourceType": "trigger",
            "id": self.rid(f"trigger:{trigger_key}"),
            "name": name,
            "prefabId": "",
            "x": x,
            "y": y,
            "symbol": symbol,
            "prefabScriptOverrides": {},
            "width": width,
            "height": height,
            "script": [self.set_value(self.near_var, value, f"{key}:enter")],
            "leaveScript": [self.if_value(self.near_var, value, f"{key}:leave", [
                self.set_value(self.near_var, NEAR_NONE, f"{key}:clear"),
            ])],
            "_index": index,
        }

    def pole_zone_trigger(self, line: dict[str, Any], *, symbol: str, index: int) -> dict[str, Any]:
        """Standing at a pole arms its cable end's pickup (value: the line number)."""
        return self.zone_trigger(name=f"Pole Zone ({line['key']})", symbol=symbol, index=index,
                                 rect=pole_zone_rect(line["pole_at"]), value=line["number"],
                                 trigger_key=f"pole-zone:{line['key']}")

    def box_zone_trigger(self, line: dict[str, Any], *, symbol: str, index: int) -> dict[str, Any]:
        """Standing at a box arms its plug-in (value: BOX_ZONE + the line number).

        The zone is ``reach_rect`` (three tiles before the box), or the line's own
        ``reach`` rect when the tiles before the box are rock.
        """
        rect = tuple(line.get("reach") or reach_rect(line["box_at"]))
        return self.zone_trigger(name=f"Box Zone {line['box_name']}", symbol=symbol, index=index,
                                 rect=rect, value=BOX_ZONE + line["number"],
                                 trigger_key=f"reach:{line['box']}")

    def npc_zone_trigger(self, *, npc_at: tuple[int, int], name: str, symbol: str, index: int,
                         trigger_key: str) -> dict[str, Any]:
        """A neighbour's zone: B does nothing here, so the neighbour's own talk runs natively."""
        return self.zone_trigger(name=name, symbol=symbol, index=index, rect=npc_zone_rect(npc_at),
                                 value=NPC_ZONE, trigger_key=trigger_key)

    def pickup_press_events(self, line: dict[str, Any], key: str, pickup_sound_id: str) -> list[Event]:
        """B in a pole zone: with empty hands and a dead line, carry the cable; otherwise say why not."""
        return [self.if_value(self.carrying_var, 0, f"{key}:empty-hands", [
            self.if_value(line["live_var"], 0, f"{key}:line-dead", [
                self.set_value(self.carrying_var, line["number"], f"{key}:carry"),
                self.actor_state("player", "Carry", f"{key}:hero-carry"),
                self.actor_state(self.actor_id(line["pole"]), "Snapped", f"{key}:pole-snapped"),
                self.sound_event(pickup_sound_id, f"{key}:sfx"),
                *self.say([self.text["pickup"]], f"{key}:text"),
            ]),
        ], [
            *self.say([self.text["hands_full"]], f"{key}:hands-full"),
        ])]

    def box_press_events(self, line: dict[str, Any], key: str, connect_sound_id: str) -> list[Event]:
        """A box actor's invoked script: plug in the cable or report why it cannot."""
        return [self.if_value(line["live_var"], 1, f"{key}:live", [
            *self.say([self.text["already"]], f"{key}:already-live"),
        ], [
            self.if_value(self.carrying_var, line["number"], f"{key}:has-cable", [
                *self.box_connect_events(line, f"{key}:connect", connect_sound_id),
            ], [
                self.if_value(self.carrying_var, 0, f"{key}:no-cable-check", [
                    *self.say([self.text["no_cable"]], f"{key}:no-cable"),
                ], [
                    *self.say([self.text["wrong_cable"]], f"{key}:wrong-cable"),
                ]),
            ]),
        ])]

    def input_script_event(self, *, pickup_sound_id: str, key: str = "b-press",
                           npc_events: list[Event] | None = None,
                           npc_actor_id: str | None = None, npc_distance: int = 1,
                           override: bool = False) -> Event:
        """The B input script, attached once per scene at init.

        Box and pole zones take priority. Outside those zones, a nearby
        ``npc_actor_id`` runs ``npc_events`` before NPC_ZONE/drop fallback.
        Without an actor ID, NPC_ZONE may dispatch talk. Any other place drops
        a carried cable. Set
        ``override=True`` with explicit NPC dispatch to suppress native actor B
        interaction. Distance tests use GB Studio's actor predicate and require
        no scratch/project variables.
        """
        drop = self.if_at_least(self.carrying_var, 1, f"{key}:drop",
                                self.cable_drop_events(f"{key}:drop", CARRY_TEXT_DROPPED), [])
        npc_zone_events = [] if npc_actor_id else (npc_events or [])
        body: list[Event] = [self.if_value(self.near_var, NPC_ZONE, f"{key}:npc", npc_zone_events, [drop])]
        if npc_actor_id and npc_events:
            body = [self.if_actor_distance("player", npc_actor_id, npc_distance, f"{key}:npc-near",
                                           npc_events, body)]
        for line in reversed(self.lines):
            prefix = f"{key}:{line['key']}"
            body = [self.if_value(self.near_var, BOX_ZONE + line["number"], f"{prefix}:box",
                                  [self.box_script_call_event(line, f"{prefix}:call-box")], body)]
            body = [self.if_value(self.near_var, line["number"], f"{prefix}:pole",
                                  self.pickup_press_events(line, f"{prefix}:pole", pickup_sound_id), body)]
        return {
            **self.event("EVENT_SET_INPUT_SCRIPT", {"input": ["b"], "override": override}, key),
            "children": {"true": body},
        }

    # -- chain actors ----------------------------------------------------------
    def cable_end_actor(self, line: dict[str, Any], index: int, sprite_id: str) -> dict[str, Any]:
        """Deprecated compatibility stub; the cable is now a pole sprite state."""
        key = line["cable"]
        x, y = line["pole_at"]
        return self.actor_resource(
            index=index, symbol=line["cable_symbol"], name=line["cable_name"],
            x=x, y=y, sprite_id=sprite_id, key=key,
            start_script=[self.event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:deprecated-hide")],
        )

    def pole_actor(self, line: dict[str, Any], index: int, sprite_id: str) -> dict[str, Any]:
        """A non-colliding pole with the cable folded into its sprite states."""
        key = line["pole"]
        x, y = line["pole_at"]
        return self.actor_resource(
            index=index, symbol=line["pole_symbol"], name=line["pole_name"], x=x, y=y,
            sprite_id=sprite_id, key=key,
            start_script=[
                # Off, so B finds the cable end on this tile instead of the pole.
                self.event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:no-collision"),
                self.if_value(line["live_var"], 1, f"{key}:line-check", [
                    self.actor_state("$self$", "Standing", f"{key}:standing"),
                ], [
                    self.actor_state("$self$", "Snapped+Cable", f"{key}:snapped-cable"),
                ]),
            ],
        )

    def box_connect_events(self, line: dict[str, Any], key: str, connect_sound_id: str) -> list[Event]:
        """Plug the carried cable in: the line goes live, the chain refreshes, the box reports.

        Called only from the box actor's ``box_press_events`` script; ``key``
        namespaces the event IDs of that caller.
        """
        # After chain_refresh_events, the chain variable says how far power reaches.
        done = [self.if_value(self.chain_var, len(self.lines), f"{key}:all", [
            *self.say([self.text["all_live"]], f"{key}:text-all"),
        ], [
            self.if_at_least(self.chain_var, line["number"], f"{key}:lit", [
                *self.say([self.text["lit"]], f"{key}:text-lit"),
            ], [
                *self.say([self.text["dark"]], f"{key}:text-dark"),
            ]),
        ])]
        return [
            self.set_value(self.carrying_var, 0, f"{key}:clear-cable"),
            self.actor_state("player", "", f"{key}:hero-empty-hands"),
            self.set_value(line["live_var"], 1, f"{key}:set-live"),
            self.event("EVENT_INC_VALUE", {"variable": self.lines_var}, f"{key}:count"),
            self.actor_state(self.actor_id(line["pole"]), "Standing", f"{key}:pole-standing"),
            *self.chain_refresh_events(f"{key}:chain"),
            self.sound_event(connect_sound_id, f"{key}:sfx"),
            *done,
        ]

    def box_script_id(self, line: dict[str, Any]) -> str:
        return self.rid(f"script:box:{line['key']}")

    def box_script_actor_bindings(self, line: dict[str, Any]) -> list[tuple[str, str]]:
        """Actor references needed by this box's script, in stable positional order."""
        if self.background_boxes:
            return [(self.actor_id(line["pole"]), line["pole_name"])]
        bindings = [(self.actor_id(other["box"]), other["box_name"]) for other in self.lines]
        bindings.append((self.actor_id(line["pole"]), line["pole_name"]))
        unique: dict[str, str] = {}
        for actor_id, name in bindings:
            unique.setdefault(actor_id, name)
        return list(unique.items())

    def box_script_call_event(self, line: dict[str, Any], key: str) -> Event:
        """Call the canonical per-box custom script synchronously."""
        args: dict[str, Any] = {"customEventId": self.box_script_id(line)}
        for index, (actor_id, _name) in enumerate(self.box_script_actor_bindings(line)):
            args[f"$actor[{index}]$"] = actor_id
        return self.event("EVENT_CALL_CUSTOM_EVENT", args, key)

    def box_script_resources(self, *, label: str, file_prefix: str, connect_sound_id: str
                              ) -> list[tuple[str, dict[str, Any]]]:
        """Separate project script resources, one compiled bank object per box handler."""
        resources = []
        for line in self.lines:
            name = f"{label} Box {line['key'].title()}"
            bindings = self.box_script_actor_bindings(line)
            actor_args = {actor_id: str(index) for index, (actor_id, _name) in enumerate(bindings)}
            script_events = self.box_press_events(line, f"box-script:{line['key']}", connect_sound_id)

            def bind_actor_args(events: list[Event]) -> None:
                for event in events:
                    args = event.get("args", {})
                    for field in ("actorId", "otherActorId"):
                        if args.get(field) in actor_args:
                            args[field] = actor_args[args[field]]
                    for children in event.get("children", {}).values():
                        bind_actor_args(children)

            bind_actor_args(script_events)
            script = {
                "_resourceType": "script",
                "id": self.box_script_id(line),
                "name": name,
                "symbol": f"script_{file_prefix}_{line['key']}",
                "description": f"Plug in the {line['key']} cable and refresh the grid chain.",
                "variables": {},
                "actors": {
                    str(index): {"id": str(index), "name": actor_name}
                    for index, (_actor_id, actor_name) in enumerate(bindings)
                },
                "script": script_events,
            }
            resources.append((f"project/scripts/{file_prefix}_box_{line['key']}.gbsres", script))
        return resources

    def box_actor(self, line: dict[str, Any], index: int, sprite_id: str) -> dict[str, Any]:
        """A visual box actor; its B handler is a separate project script resource.

        Plugging in repairs the line and stands its pole up; whether power reaches
        it depends on the lines upstream (chain_refresh_events). The external
        script object keeps all box branches out of the shared input bank.
        """
        if self.background_boxes:
            raise ValueError("this chain's boxes are background art; it has no box actors")
        key = line["box"]
        x, y = line["box_at"]
        return self.actor_resource(
            index=index, symbol=line["box_symbol"], name=line["box_name"], x=x, y=y,
            sprite_id=sprite_id, key=key,
            start_script=[self.actor_state("$self$", "Dead", f"{key}:dead")],
        )

    def span_arc_actor(self, number: int, lane: tuple[int, int, int], start_delay: int,
                       sprite_id: str, live_after: int, *, timings: tuple[int, int, int],
                       symbol: str, name: str) -> dict[str, Any]:
        """Fallen-span arc: dark and safe until ``live_after`` lines are repaired, then its arc cycle.

        ``timings`` is (warning, active, rest) frames. The first live cycle waits
        ``start_delay`` once (the direction trick used by the gusts).
        """
        warning_frames, active_frames, rest_frames = timings
        row, x0, x1 = lane
        if x1 - x0 + 1 != 2:
            raise ValueError("the authored live arc sprite is exactly two tiles wide")
        key = f"span-arc:{number}"

        def own(command: str, suffix: str, **args: Any) -> Event:
            return self.event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        first_cycle_true = [
            own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"}),
        ]
        if start_delay > 0:
            first_cycle_true.append(self.wait_event(start_delay, f"{key}:start-delay"))
        cycle = [
            self.branch_event("EVENT_IF_ACTOR_DIRECTION",
                              {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                              f"{key}:first-cycle", first_cycle_true),
            own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
            own("EVENT_ACTOR_SHOW", "warning-visible"),
            self.wait_event(warning_frames, f"{key}:warning-time"),
            own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
            own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
            self.wait_event(active_frames, f"{key}:arc-time"),
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
            own("EVENT_ACTOR_HIDE", "rest-hidden"),
            self.wait_event(rest_frames, f"{key}:rest-time"),
        ]
        update = [self.if_at_least(self.chain_var, live_after, f"{key}:upstream", cycle, [
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "dead-safe"),
            own("EVENT_ACTOR_HIDE", "dead-hidden"),
            self.wait_event(1, f"{key}:dead-tick"),
        ])]
        return self.actor_resource(
            index=0, symbol=symbol, name=name, x=x0, y=row, sprite_id=sprite_id, key=key, anim_speed=8,
            start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe"),
                          own("EVENT_ACTOR_HIDE", "initial-hidden")],
            update_script=update, collision_group="1",
        )


# ---------------------------------------------------------------------------
# Self-check helpers (contract modules call these from their _self_check)
# ---------------------------------------------------------------------------
def reach_rect(box: tuple[int, int]) -> tuple[int, int, int, int]:
    """(x, y, width, height) tiles of a box's zone: the three tiles before the box plus its two columns.

    Feet row and two above. A hero standing on the box (its own columns) is in
    the zone, so the box's B action wins where it stands.
    """
    x, y = box
    return (x - 3, y - 2, 5, 3)


def pole_zone_rect(pole: tuple[int, int]) -> tuple[int, int, int, int]:
    """Pickup zone of a pole: its feet tile and the tile on either side, feet row and two above."""
    x, y = pole
    return (x - 1, y - 2, 3, 3)


def npc_zone_rect(npc: tuple[int, int]) -> tuple[int, int, int, int]:
    """A neighbour's zone: two tiles, the one before the neighbour and its own, feet row and two above."""
    x, y = npc
    return (x - 1, y - 2, 2, 3)


def stands(grid: list[list[int]], x: int, y: int) -> bool:
    """A 24px actor at feet tile (x, y): three clear rows, support below."""
    return (all(grid[r][x] == COL_EMPTY for r in (y, y - 1, y - 2))
            and grid[y + 1][x] in (COL_TOP, COL_SOLID))


def check_props(grid: list[list[int]], props: Iterable[tuple[int, int]],
                hazard_cells: set[tuple[int, int]], hud_rows: int) -> None:
    """Every prop tile is on the map, stands on support and is clear of hazard cells."""
    map_h, map_w = len(grid), len(grid[0])
    for x, y in props:
        assert 0 < x < map_w - 1 and hud_rows + 2 <= y < map_h - 1, f"bounds {(x, y)}"
        assert stands(grid, x, y), f"actor tile {(x, y)} must stand clear on support"
        assert all(abs(x - hx) > 1 or abs(y - hy) > 2 for hy, hx in hazard_cells), (
            f"prop {(x, y)} too close to a hazard")


def check_chain_order(lines: Sequence[dict[str, Any]]) -> None:
    """Contract LINES: pole k < box k < pole k+1, numbered 1..N, one live variable each."""
    xs = []
    for line in lines:
        xs += [line["pole"][0], line["box"][0]]
    assert xs == sorted(xs) and len(set(xs)) == len(xs), "chain order"
    assert [line["number"] for line in lines] == list(range(1, len(lines) + 1))
    assert len({line["live_var"] for line in lines}) == len(lines), "one live variable per line"


def check_scene_limits(actor_count: int, trigger_count: int) -> None:
    """Assert scene resource counts stay within GB Studio's practical budgets."""
    assert actor_count <= MAX_ACTORS, f"scene has {actor_count} actors; limit is {MAX_ACTORS}"
    assert trigger_count <= MAX_TRIGGERS, f"scene has {trigger_count} triggers; limit is {MAX_TRIGGERS}"


def check_spans(spans: Sequence[dict[str, Any]], lines: Sequence[dict[str, Any]]) -> None:
    """Each fallen span's arcs sit inside its columns, and the span lies on its line's carry path."""
    for span in spans:
        c0, c1 = span["columns"]
        assert all(c0 <= x0 and x1 <= c1 for _, x0, x1 in span["arcs"])
        assert len(span["delays"]) == len(span["arcs"])
        line = lines[span["live_after"]]
        assert line["pole"][0] < c0 and c1 < line["box"][0], "span on its line's carry path"


def check_wire_routes(routes: Sequence[tuple[int, list[tuple[int, int]]]], stage_count: int,
                      map_w: int, top_row: int, bottom_row: int) -> None:
    """Routes stay on the map between top_row and bottom_row, use every stage, and form one continuous chain."""
    for stage, route in routes:
        assert 1 <= stage <= stage_count, stage
        assert all(top_row <= y < bottom_row and 0 <= x < map_w for x, y in route), route
    for (_, a), (_, b) in zip(routes, routes[1:]):
        assert set(a) & set(b), "consecutive wire routes share a cell (continuity)"
    assert routes[0][1][0][0] == 0, "power enters at the left edge"
    assert {stage for stage, _ in routes} == set(range(1, stage_count + 1))


# ---------------------------------------------------------------------------
# Test helpers: camera window and OBJ load per tile row
# ---------------------------------------------------------------------------
def chain_sprites(lines: Sequence[dict[str, Any]], background_boxes: bool = False
                  ) -> list[tuple[tuple[int, int], int, int]]:
    """((feet tile), OBJ columns, OBJ tile rows) for each pole and (actor) box."""
    sprites = []
    for line in lines:
        sprites += [(line["pole_at"], 2, 4)]
        if not background_boxes:
            sprites += [(line["box_at"], 2, 4 if line["box_kind"] == "transformer" else 2)]
    return sprites


def screen_left(hero_x: int, map_width: int, view_width: int = SCREEN_TILES) -> int:
    """Left tile of the camera window around the hero (clamped at both edges)."""
    return min(max(hero_x - 10, 0), map_width - view_width)


def scanline_load(sprites: Iterable[tuple[tuple[int, int], int, int]], map_width: int,
                  hero_x: int, hero_feet: int, hero_size: tuple[int, int] = (3, 3)) -> dict[int, int]:
    """OBJ columns per tile row on screen for the hero and ``sprites`` ((x, feet), width, height)."""
    left = screen_left(hero_x, map_width)
    load: dict[int, int] = {}
    for (x, feet), width, height in [((hero_x, hero_feet), *hero_size), *sprites]:
        if x + width <= left or x >= left + SCREEN_TILES:
            continue  # off screen: not drawn
        for row in range(feet - height + 1, feet + 1):
            load[row] = load.get(row, 0) + width
    return load


def actors_near(sprites: Iterable[tuple[tuple[int, int], int, int]], map_width: int, hero_x: int,
                margin: int = 2, width: int = 24) -> list[int]:
    """Feet-tile x of each sprite within the camera window, widened by ``margin`` on the left."""
    left = screen_left(hero_x, map_width) - margin
    return [x for (x, _), _, _ in sprites if left <= x < left + width]
