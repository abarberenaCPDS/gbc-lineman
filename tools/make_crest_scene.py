"""Generate job 1B, the crest (``climb_crest``, 56x18), from ``climb.py``'s CREST section.

Run after ``make_climb_art.py`` (it renders ``climb_crest.png``) and
``make_climb_scene.py`` (palettes, variables). The crest is the end of carry 5
(docs/LEVEL_REDESIGN.md §2, 1B): transformer 5, Amara, her house and door
(Amara's checkpoint, var 0), and the porch exit to work order 2.

It shares job 1's grid chain (``make_climb_scene.make_chain``): the same IDs,
chain palettes and box scripts, with this scene's local parts only (transformer
5 here, every pole in the climb). Event and actor keys of this scene start with
``climb_crest:`` in the climb's ID namespace, except the resources that moved up
from the climb with stable IDs (Amara, her door, her zone, transformer 5's zone).
No music event: the climb's fresh start owns the job track (spec §3 rule 6).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))

import climb  # noqa: E402  (job 1 contract: CREST section)
import completion  # noqa: E402  (Amara's household completion cue)
import grid_chain  # noqa: E402
import hazards  # noqa: E402
import make_climb_scene as shared  # noqa: E402  (job 1 chain and generic helpers)
import opening  # noqa: E402
import rosa  # noqa: E402  (span arc timings and sprite)
import scene_links  # noqa: E402
import scenes  # noqa: E402
import tickets  # noqa: E402  (Amara's work order closes at her door)

FOLDER = climb.CREST_SCENE
SCENE_DIR = shared.PROJECT_DIR / "project" / "scenes" / FOLDER
KEY = f"{FOLDER}:"                 # event/actor key prefix in the climb's ID namespace
SYMBOL = "crest_"
SCENE_INDEX = 12
SCENE_ID = scenes.REGISTRY[FOLDER]["id"]
BACKGROUND_ID = shared.resource_id("background:climb-crest")
VAR_DOOR = shared.VARIABLE_CHECKPOINTS_REACHED      # var 0: Amara's door reached
SUMMIT = shared.LINE_BY_KEY["summit"]
# Span arcs are numbered across the job (1A has span arc 1), so actor IDs stay unique.
SPAN_ARC_FIRST_NUMBER = len(climb.span_arc_lanes()) + 1


class CrestChain(shared.ClimbChain):
    """Crest-only chain behavior for the repaired downed span pilot."""

    def _span_final_repair_guard(self, number: int, phase: str, continuation: list[dict[str, Any]]):
        key = f"span-arc:{number}:final-repair-{phase}"
        safe = [
            self.event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, f"{key}:disable"),
            self.event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, f"{key}:hide"),
            self.wait_event(1, f"{key}:tick"),
        ]
        return self.if_value(climb.LINES[-1]["live_var"], 1, key, safe, continuation)

    def span_arc_actor(self, number, lane, start_delay, sprite_id, live_after, *, timings, symbol, name):
        actor = super().span_arc_actor(number, lane, start_delay, sprite_id, live_after,
                                       timings=timings, symbol=symbol, name=name)
        warning, active, rest = timings
        key = f"span-arc:{number}"

        def own(command, suffix, **args):
            return self.event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

        # Recheck after every wait. A box script also hides/disables immediately;
        # these gates prevent an already queued phase from turning it back on.
        # Preserve the original direction trick and its start-delay semantics.
        first_true = [own("EVENT_ACTOR_SET_DIRECTION", "started", direction={"type": "direction", "value": "up"})]
        if start_delay:
            first_true.append(self.wait_event(start_delay, f"{key}:start-delay"))
        cycle = [self.branch_event("EVENT_IF_ACTOR_DIRECTION",
                                   {"actorId": "$self$", "direction": {"type": "direction", "value": "down"}},
                                   f"{key}:first-cycle", first_true),
                 self._span_final_repair_guard(number, "after-delay", [
                     own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
                     own("EVENT_ACTOR_SHOW", "warning-visible"),
                     self.wait_event(warning, f"{key}:warning-time"),
                     self._span_final_repair_guard(number, "after-warning", [
                         own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
                         own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
                         self.wait_event(active, f"{key}:arc-time"),
                         self._span_final_repair_guard(number, "after-active", [
                             own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
                             own("EVENT_ACTOR_HIDE", "rest-hidden"),
                             self.wait_event(rest, f"{key}:rest-time"),
                             self._span_final_repair_guard(number, "after-rest", []),
                         ]),
                     ]),
                 ])]
        cycle.insert(0, own("EVENT_ACTOR_COLLISIONS_DISABLE", "cycle-safe"))
        actor["updateScript"] = [self.if_at_least(self.chain_var, live_after, f"{key}:upstream", cycle, [
            own("EVENT_ACTOR_COLLISIONS_DISABLE", "dead-safe"),
            own("EVENT_ACTOR_HIDE", "dead-hidden"),
            self.wait_event(1, f"{key}:dead-tick"),
        ])]
        return actor

    def chain_refresh_events(self, key):
        events = super().chain_refresh_events(key)
        # This runs synchronously on the final box repair and on scene entry.
        span_actor_id = self.actor_id(f"span-arc:{SPAN_ARC_FIRST_NUMBER}")
        events.append(self.if_value(climb.LINES[-1]["live_var"], 1, f"{key}:crest-span-safe", [
            self.event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": span_actor_id},
                       f"{key}:crest-span-disable"),
            self.event("EVENT_ACTOR_HIDE", {"actorId": span_actor_id},
                       f"{key}:crest-span-hide"),
        ]))
        return events

    def box_script_actor_bindings(self, line):
        bindings = super().box_script_actor_bindings(line)
        if line["number"] == climb.LINE_COUNT:
            bindings.append((self.actor_id(f"span-arc:{SPAN_ARC_FIRST_NUMBER}"), "Downed Span Arc (crest) 1"))
        return bindings


CHAIN = CrestChain(
    rid=shared.resource_id, lines=shared.LINES, chain_var=climb.VAR_CHAIN_LIVE,
    lines_var=climb.VAR_LINES_LIVE, carrying_var=shared.VAR_CARRYING_CABLE_ID,
    near_var=shared.VAR_NEAR_ID, line_bg_slot=climb.LINE_BG_SLOT,
    line_bg_slot_2=climb.LINE_BG_SLOT_2, text=shared.CLIMB_TEXT, say=shared.say,
    hud=shared.hud_events, background_boxes=True, scene=FOLDER,
)

event = shared.event
if_value = shared.if_value
set_value = shared.set_value
say = shared.say
short_lines = shared.short_lines


def k(key: str) -> str:
    return KEY + key


# ---------------------------------------------------------------------------
# Amara (moved up from the summit with her stable IDs)
# ---------------------------------------------------------------------------
MARTA_ACTOR_KEY = "marta-checkpoint"


def marta_actor_id() -> str:
    return shared.resource_id(f"actor:{MARTA_ACTOR_KEY}")


def marta_talk_events(key: str) -> list[dict[str, Any]]:
    return [if_value(VAR_DOOR, 0, f"{key}:talk", [
        if_value(climb.VAR_CHAIN_LIVE, climb.LINE_COUNT, f"{key}:talk-line", [
            *say(short_lines("Power's up here!\nTry my door."), f"{key}:talk-live", "marta"),
        ], [
            *say(short_lines("Storm cut five\nlines below me!"), f"{key}:talk-dead", "marta"),
        ]),
    ], [
        *say(short_lines("Food is saved.\nThanks, lineman!"), f"{key}:talk-after", "marta"),
    ])]


def amara_actor(marta_sprite_id: str) -> dict[str, Any]:
    """Amara on her porch: Waiting until her door is reached (the init has the last word)."""
    key = MARTA_ACTOR_KEY
    x, y = climb.CREST_AMARA
    actor = shared.actor_resource(
        index=0, symbol="marta_checkpoint", name="Amara (Crest Checkpoint)", x=x, y=y,
        sprite_id=marta_sprite_id, key=key, script=marta_talk_events(key),
        start_script=[shared.actor_state("$self$", "Waiting", f"{key}:waiting")],
    )
    actor["animate"] = True        # her Waiting/Powered states carry idle frames
    return actor


def door_state_events(key: str) -> list[dict[str, Any]]:
    """Window palette and Amara from var 0: the door survives trips down the climb."""
    return [if_value(VAR_DOOR, 1, f"{key}:door", [
        shared.background_palette_state(True, f"{key}:window-warm"),
        shared.actor_state(marta_actor_id(), "Powered", f"{key}:marta-powered"),
    ], [
        shared.background_palette_state(False, f"{key}:window-cold"),
        shared.actor_state(marta_actor_id(), "Waiting", f"{key}:marta-waiting"),
    ])]


# ---------------------------------------------------------------------------
# Actors
# ---------------------------------------------------------------------------
def span_arc_actors() -> list[dict[str, Any]]:
    out = []
    number = SPAN_ARC_FIRST_NUMBER
    for span in climb.CREST_FALLEN_SPANS:
        for lane, delay in zip(span["arcs"], span["delays"]):
            out.append(CHAIN.span_arc_actor(
                number, lane, delay, rosa.ARC_SPRITE_ID, span["live_after"],
                timings=(rosa.ARC_WARNING_FRAMES, rosa.ARC_ACTIVE_FRAMES, rosa.ARC_REST_FRAMES),
                symbol=f"{SYMBOL}span_arc_{number - SPAN_ARC_FIRST_NUMBER + 1:02d}",
                name=f"Downed Span Arc (crest) {number - SPAN_ARC_FIRST_NUMBER + 1}"))
            number += 1
    return out


def build_actors(sprite_ids: dict[str, str]) -> list[dict[str, Any]]:
    """Amara, the gust, the span arc, the whip, the hidden cable, then the board (draws on top)."""
    actors = [amara_actor(sprite_ids["marta"])]
    actors += [shared.timed_gust_actor(index, lane, sprite_ids["gust"], KEY, SYMBOL,
                                       timings=climb.CREST_GUST_TIMINGS)
               for index, lane in enumerate(climb.CREST_GUST_LANES, start=1)]
    actors += span_arc_actors()
    actors += [shared.whip_actor(number, lane, delay, 0, KEY, SYMBOL)
               for number, (lane, delay) in enumerate(zip(climb.CREST_WHIP_LANES,
                                                          climb.CREST_WHIP_START_DELAYS), start=1)]
    hazard = shared.hazard_actors(0, FOLDER)
    actors += [a for a in hazard if "hidden_cable" in a["symbol"]]
    actors += [a for a in hazard if "board" in a["symbol"]]
    if len(actors) != climb.crest_actor_count():
        raise ValueError(f"{len(actors)} crest actors, contract says {climb.crest_actor_count()}")
    for position, actor in enumerate(actors):
        actor["_index"] = position
    return actors


# ---------------------------------------------------------------------------
# Triggers
# ---------------------------------------------------------------------------
def trigger(key: str, name: str, symbol: str, rect: tuple[int, int, int, int],
            script: list[dict[str, Any]], trigger_id: str | None = None) -> dict[str, Any]:
    x, y, width, height = rect
    return {
        "_resourceType": "trigger", "id": trigger_id or shared.resource_id(f"trigger:{k(key)}"),
        "name": name, "prefabId": "", "x": x, "y": y, "symbol": symbol, "prefabScriptOverrides": {},
        "width": width, "height": height, "script": script, "leaveScript": [], "_index": 0,
    }


def back_exit_trigger() -> dict[str, Any]:
    """Back down to the climb's summit (ungated; a carried cable stays in hand)."""
    link = scene_links.link(FOLDER, climb.CLIMB_SCENE, scene_links.table("redesign"))
    assert link.rect == climb.CREST_BACK_EXIT and link.entry == climb.SUMMIT_ARRIVAL and link.gate is None
    return trigger("back-exit", "Back Exit (to Storm Climb)", "trigger_crest_back_exit", link.rect,
                   shared.exit_switch_events(link, k("back-exit")))


def porch_exit_trigger() -> dict[str, Any]:
    """On to Hiroshi's work order once Amara's door is reached (var 0, the summit's old gate).

    Refused: step back three tiles first (ROM 147c23be: leftover momentum kept
    the hero in the exit and the text looped), then explain.
    """
    link = scene_links.link(FOLDER, "wind_ridge", scene_links.table("redesign"))
    assert link.rect == climb.CREST_PORCH_EXIT and link.gate == VAR_DOOR and link.ticket == 2
    x, _, _, _ = link.rect
    wait = [
        shared.set_position(x - climb.CREST_EXIT_NUDGE_TILES, climb.CREST_DOOR[1], k("porch-exit:nudge-back")),
        *say(short_lines("Amara needs\npower first."), k("porch-exit:not-yet")),
    ]
    go = shared.exit_switch_events(link, k("porch-exit"))
    return trigger("porch-exit", "Porch Exit (to Work Order 2)", "trigger_crest_porch_exit", link.rect,
                   [if_value(link.gate, 1, k("porch-exit:gate"), go, wait)])


def door_trigger(connect_sound_id: str) -> dict[str, Any]:
    """Amara's door: once all five lines are live, her checkpoint (var 0), once only.

    Keeps the summit door's stable ID. Without power the hint stays quiet while
    a cable is carried past the door.
    """
    script = [if_value(climb.VAR_CHAIN_LIVE, climb.LINE_COUNT, "checkpoint-arrival:line", [
        if_value(VAR_DOOR, 0, "checkpoint-arrival", [
            set_value(VAR_DOOR, 1, "checkpoint-arrival:set"),
            shared.sound_event(completion.sound_id(), "checkpoint-arrival:sfx"),
            shared.background_palette_state(True, "checkpoint-arrival:summit-lit"),
            shared.actor_state(marta_actor_id(), "Powered", "checkpoint-arrival:marta-powered"),
            shared.cutoff_event(150, "checkpoint-arrival:cutoff"),
            # Second page: Amara's work order closes (tickets.py).
            *say(short_lines("Power's back!\nMy fridge hums."),
                  "checkpoint-arrival:text", "marta"),
            *say(tickets.closed_lines(1), "checkpoint-arrival:closed"),
        ]),
    ], [
        if_value(shared.VAR_CARRYING_CABLE_ID, 0, "checkpoint-arrival:hint", [
            *say(short_lines("Still no power.\nFix all 5 lines!"), "checkpoint-arrival:no-power"),
        ]),
    ])]
    return trigger("door", "Amara Arrival Checkpoint", "trigger_marta_arrival", climb.CREST_DOOR_RECT, script,
                   trigger_id=shared.resource_id("trigger:gust-lane:100"))


def build_triggers(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    """Exits first (first match wins), the door, the board, then the B zones."""
    triggers = [back_exit_trigger(), porch_exit_trigger(), door_trigger(audio_ids["connect"])]
    triggers += shared.hazard_triggers(FOLDER)
    triggers += [CHAIN.box_zone_trigger(line, symbol=line["box_zone_symbol"], index=0)
                 for line in CHAIN.box_lines()]
    triggers.append(shared.zone_trigger(
        name="Amara Zone", symbol="trigger_marta_zone", index=0,
        rect=grid_chain.npc_zone_rect(climb.CREST_AMARA), value=grid_chain.NPC_ZONE,
        trigger_key="npc-zone:marta"))
    grid_chain.check_scene_limits(climb.crest_actor_count(), len(triggers))
    for position, item in enumerate(triggers):
        item["_index"] = position
    return triggers


# ---------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------
def scene_script(audio_ids: dict[str, str]) -> list[dict[str, Any]]:
    """Not the job's entry scene: no reset, no music, no intro (spec §3 rules 1, 2, 6)."""
    return [
        event("EVENT_PLAYER_SET_SPRITE",
              {"spriteSheetId": opening.resource_id("sprite:opening_worker24")}, k("init-player-sprite")),
        set_value(shared.VAR_NEAR_ID, grid_chain.NEAR_NONE, k("init-near")),
        CHAIN.input_script_event(pickup_sound_id=audio_ids["pickup"], key=k("b-press")),
        set_value(hazards.VAR_ON_BOARD, 0, k("init-on-board")),
        *door_state_events(k("init")),
        *CHAIN.chain_refresh_events(k("init-chain")),
        *CHAIN.carry_restore_events(k("carry-restore")),
        *shared.hud_events(k("initial-hud")),
    ]


def build_scene(audio_ids: dict[str, str]) -> dict[str, Any]:
    scene = shared.load_json(shared.REFERENCE_SCENE)
    background_palette_ids, sprite_palette_ids = shared.scene_palettes()
    editor_x, editor_y = scenes.editor_position(FOLDER)
    scene.update({
        "id": SCENE_ID,
        "_index": SCENE_INDEX,
        "name": scenes.REGISTRY[FOLDER]["name"],
        "type": "PLATFORM",
        "x": editor_x,
        "y": editor_y,
        "width": climb.CREST_W,
        "height": climb.CREST_H,
        "collisions": shared.collision_rle(climb.crest_collision_grid(), climb.CREST_W, climb.CREST_H),
        "symbol": f"scene_{FOLDER}",
        "backgroundId": BACKGROUND_ID,
        "paletteIds": background_palette_ids,
        "spritePaletteIds": sprite_palette_ids,
        "script": scene_script(audio_ids),
        "playerHit1Script": shared.respawn_events(k("hit"), audio_ids["death"], chain=CHAIN,
                                                  start=climb.CREST_START),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def box_script_resources(audio_ids: dict[str, str]) -> list[tuple[str, dict[str, Any]]]:
    """Transformer 5's box script (project/scripts/storm_climb_box_summit.gbsres, same ID)."""
    return CHAIN.box_script_resources(label="Storm Climb", file_prefix="storm_climb",
                                      connect_sound_id=audio_ids["connect"])


def main() -> None:
    if SCENE_ID != shared.resource_id(f"scene:{FOLDER}"):
        raise ValueError("climb_crest's registry id must be make_climb_scene.resource_id('scene:climb_crest')")
    _, sprite_ids, audio_ids = shared.load_ids()
    background = Path(str(shared.PROJECT_DIR / "assets/backgrounds/climb_crest.png") + ".gbsres")
    if shared.load_json(background).get("id") != BACKGROUND_ID:
        raise ValueError("run make_climb_art.py first: climb_crest.png's sidecar is missing or not ours")
    actors = build_actors(sprite_ids)
    triggers = build_triggers(audio_ids)
    scene = build_scene(audio_ids)
    for relative_path, script in box_script_resources(audio_ids):
        shared.write_json(shared.PROJECT_DIR / relative_path, script)
    shared.write_json(SCENE_DIR / "scene.gbsres", scene)
    for folder, items in (("actors", actors), ("triggers", triggers)):
        keep = {f"{item['symbol']}.gbsres" for item in items}
        for stale in sorted((SCENE_DIR / folder).glob("*.gbsres")):
            if stale.name not in keep:
                stale.unlink()
                print(f"removed retired {folder[:-1]} {stale.name}")
        for item in items:
            shared.write_json(SCENE_DIR / folder / f"{item['symbol']}.gbsres", item)
    print(f"generated {FOLDER}: {climb.CREST_W}x{climb.CREST_H} PLATFORM, {len(actors)} actors, "
          f"{len(triggers)} triggers; transformer 5, Amara's porch and door")


if __name__ == "__main__":
    main()
