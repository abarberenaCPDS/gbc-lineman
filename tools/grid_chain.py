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
  LINE_BG_SLOT                      background palette slot that holds the wires
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

Box reach: box_reach_trigger(line, symbol=, index=, connect_sound_id=) returns the
trigger for one line (call it once per line, after the job's own triggers). It sits
three tiles before the box (reach_rect), so walking up with that line's cable plugs
it in without a B press; any other visit does nothing. A box's B press and its
reach trigger share box_connect_events, so the two paths cannot disagree.

Palette resources: chain_palettes() gives {stages: colours}; chain_palette_resources()
turns them into project/palettes files. The scene sets the background slot to
chain_palette_id(0) at init and to chain_palette_id(n) as the chain lights.

Test helpers: scanline_load() counts OBJ columns per tile row (SCANLINE_OBJ_LIMIT
is the budget); the camera window is SCREEN_TILES wide and clamps at both map edges.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

import climb

Event = dict[str, Any]
Rid = Callable[[str], str]

MAX_STAGES = 3            # metal slot indexes 1..3 carry the stages; index 0 is the placeholder
SCREEN_TILES = 20         # PLATFORM camera window width; the camera clamps at both map edges
SCANLINE_OBJ_LIMIT = 10   # 8x16 OBJs per tile row the tests allow on screen at once

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
    assert 1 <= len(stage_color_index) <= MAX_STAGES, "one to three chain stages"
    assert len(set(stage_color_index)) == len(stage_color_index), "stage colours must be distinct"
    assert all(1 <= index <= MAX_STAGES for index in stage_color_index), "stage colours use metal indexes 1-3"


def chain_palette(stages_live: int, *, metal_dead: Sequence[str], wire_live: str, wire_dead: str,
                  stage_color_index: Sequence[int]) -> list[str]:
    """Metal slot colours with the first ``stages_live`` stages lit."""
    colors = list(metal_dead)
    for stage, index in enumerate(stage_color_index, start=1):
        colors[index] = wire_live if stage <= stages_live else wire_dead
    return colors


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
                            palettes: dict[int, list[str]]) -> list[tuple[str, dict[str, Any]]]:
    """(project path, palette resource) for each chain palette."""
    return [(f"project/palettes/{file_prefix}_bg_{chain_palette_name(stages)}.gbsres",
             palette_resource(rid, label, "bg", chain_palette_name(stages), colors))
            for stages, colors in palettes.items()]


def chain_palette_id(rid: Rid, stages_live: int) -> str:
    return rid(f"palette:bg:{chain_palette_name(stages_live)}")


# ---------------------------------------------------------------------------
# The chain: events, actors and their IDs
# ---------------------------------------------------------------------------
class GridChain:
    """Script and actor builders for one scene's grid chain (see the module docstring)."""

    def __init__(self, *, rid: Rid, lines: Sequence[dict[str, Any]], chain_var: str, lines_var: str,
                 carrying_var: str, line_bg_slot: int, text: dict[str, str],
                 say: Callable[..., list[Event]], hud: Callable[[str], list[Event]],
                 bare_event_key: str | None = None) -> None:
        self.rid = rid
        self.lines = list(lines)
        self.chain_var = chain_var
        self.lines_var = lines_var
        self.carrying_var = carrying_var
        self.line_bg_slot = line_bg_slot
        self.text = dict(text)
        self.say = say
        self.hud = hud
        self.bare_event_key = bare_event_key

    # -- IDs -----------------------------------------------------------------
    def actor_id(self, key: str) -> str:
        return self.rid(f"actor:{key}")

    def chain_palette_id(self, stages_live: int) -> str:
        return chain_palette_id(self.rid, stages_live)

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
                   self.background_palette_event({self.line_bg_slot: self.chain_palette_id(stages)},
                                                 f"{key}:palette-{stages}")]
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

    def cable_drop_events(self, key: str) -> list[Event]:
        """A carried cable falls back to its own pole when the carrier is hit."""
        events = []
        for line in self.lines:
            tag = key if line["key"] == self.bare_event_key else f"{key}:{line['key']}"
            events.append(self.if_value(self.carrying_var, line["number"], f"{tag}:cable-drop", [
                self.set_value(self.carrying_var, 0, f"{tag}:cable-clear"),
                self.actor_state("player", "", f"{tag}:hero-empty-hands"),
                self.event("EVENT_ACTOR_SHOW", {"actorId": self.actor_id(line["cable"])}, f"{tag}:cable-show"),
                self.actor_state(self.actor_id(line["cable"]), "Dangling", f"{tag}:cable-dangling"),
                *self.hud(f"{tag}:cable-hud"),
            ]))
        return events

    # -- chain actors ----------------------------------------------------------
    def cable_end_actor(self, line: dict[str, Any], index: int, sprite_id: str,
                        pickup_sound_id: str) -> dict[str, Any]:
        """Dangling cable on its snapped pole. B picks it up with empty hands while its line is dead."""
        key = line["cable"]
        x, y = line["pole_at"]
        pickup = [self.if_value(self.carrying_var, 0, f"{key}:empty-hands", [
            self.if_value(line["live_var"], 0, f"{key}:line-dead", [
                self.set_value(self.carrying_var, line["number"], f"{key}:carry"),
                self.actor_state("player", "Carry", f"{key}:hero-carry"),
                self.event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:hide"),
                self.sound_event(pickup_sound_id, f"{key}:sfx"),
                *self.say([self.text["pickup"]], f"{key}:text"),
            ]),
        ], [
            *self.say([self.text["hands_full"]], f"{key}:hands-full"),
        ])]
        return self.actor_resource(
            index=index, symbol=line["cable_symbol"], name=line["cable_name"],
            x=x, y=y, sprite_id=sprite_id, key=key, script=pickup,
            start_script=[self.actor_state("$self$", "Dangling", f"{key}:dangling")],
        )

    def pole_actor(self, line: dict[str, Any], index: int, sprite_id: str) -> dict[str, Any]:
        """A snapped pole: Standing once its line is repaired.

        Non-colliding and not interactive; the cable-end pickup owns the B press.
        """
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
                    self.actor_state("$self$", "Snapped", f"{key}:snapped"),
                ]),
            ],
        )

    def box_connect_events(self, line: dict[str, Any], key: str, connect_sound_id: str) -> list[Event]:
        """Plug the carried cable in: the line goes live, the chain refreshes, the box reports.

        Shared by the box's B press (``box_actor``) and its reach trigger
        (``box_reach_trigger``); ``key`` namespaces the event IDs of that caller.
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

    def box_reach_trigger(self, line: dict[str, Any], *, symbol: str, index: int,
                          connect_sound_id: str, name: str | None = None) -> dict[str, Any]:
        """Walking up to a box with its cable plugs it in (no B press needed).

        The trigger covers the three tiles before the box (``reach_rect``), or the
        line's own ``reach`` rect when the tiles before the box are rock. Its
        enter script runs the box's own connect path, and only when the hero
        carries this line's cable and the line is still dead; any other visit
        does nothing, so the box's B press (``box_actor``) stays the only text.
        """
        key = f"reach:{line['box']}"
        x, y, width, height = line.get("reach") or reach_rect(line["box_at"])
        script = [self.if_value(self.carrying_var, line["number"], f"{key}:has-cable", [
            self.if_value(line["live_var"], 0, f"{key}:dead", self.box_connect_events(
                line, key, connect_sound_id)),
        ])]
        return {
            "_resourceType": "trigger",
            "id": self.rid(f"trigger:reach:{line['box']}"),
            "name": name or f"Reach {line['box_name']}",
            "prefabId": "",
            "x": x,
            "y": y,
            "symbol": symbol,
            "prefabScriptOverrides": {},
            "width": width,
            "height": height,
            "script": script,
            "leaveScript": [],
            "_index": index,
        }

    def box_actor(self, line: dict[str, Any], index: int, sprite_id: str,
                  connect_sound_id: str) -> dict[str, Any]:
        """A box (transformer or junction). Only its own line's cable plugs in.

        Plugging in repairs the line and stands its pole up; whether power reaches
        it depends on the lines upstream (chain_refresh_events).
        """
        key = line["box"]
        x, y = line["box_at"]
        plug = [self.if_value(line["live_var"], 1, f"{key}:live", [
            *self.say([self.text["already"]], f"{key}:already-live"),
        ], [
            self.if_value(self.carrying_var, line["number"], f"{key}:has-cable", [
                *self.box_connect_events(line, key, connect_sound_id),
            ], [
                self.if_value(self.carrying_var, 0, f"{key}:no-cable-check", [
                    *self.say([self.text["no_cable"]], f"{key}:no-cable"),
                ], [
                    *self.say([self.text["wrong_cable"]], f"{key}:wrong-cable"),
                ]),
            ]),
        ])]
        return self.actor_resource(
            index=index, symbol=line["box_symbol"], name=line["box_name"], x=x, y=y,
            sprite_id=sprite_id, key=key, script=plug,
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
    """(x, y, width, height) tiles of a box's reach trigger: three tiles ending at the box, feet row and two above."""
    x, y = box
    return (x - 3, y - 2, 3, 3)


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
def chain_sprites(lines: Sequence[dict[str, Any]]) -> list[tuple[tuple[int, int], int, int]]:
    """((feet tile), OBJ columns, OBJ tile rows) for each pole, cable end and box.

    Storm pole (2x4 intro sprite) and cable end (2x2) share the pickup tile. A
    transformer is 2x4; a junction box 2x2.
    """
    sprites = []
    for line in lines:
        sprites += [(line["pole_at"], 2, 4), (line["pole_at"], 2, 2)]
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
