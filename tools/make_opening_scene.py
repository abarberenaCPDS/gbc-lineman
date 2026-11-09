"""Generate the isolated M-V1 opening without overwriting the climb.

Run after make_opening_art.py and make_opening_characters.py. Scene selection
remains an explicit MCP settings_update so regeneration never changes the
user's launch scene unexpectedly. Assets and palettes use opening.py IDs.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import climb
import intro
import opening
import scenes
import tickets
import voices
from make_climb_scene import collision_rle

ROOT = Path(__file__).resolve().parent.parent
SCENE_DIR = ROOT / "project/scenes/service_opening"
EXIT_SYMBOL = "trigger_service_exit"
RESTORED = opening.VAR_SERVICE_RESTORED


def event(command: str, args: dict[str, Any], key: str, **children: list) -> dict:
    result = {"id": opening.resource_id("event:" + key), "command": command, "args": args}
    if children:
        result["children"] = children
    return result


def number(value: int) -> dict:
    return {"type": "number", "value": value}


def if_value(variable: str, value: int, key: str, yes: list, no: list | None = None) -> dict:
    return event("EVENT_IF", {"condition": {
        "type": "eq", "valueA": {"type": "variable", "value": variable},
        "valueB": number(value),
    }}, key, true=yes, false=no or [])


def set_value(variable: str, value: int, key: str) -> dict:
    return event("EVENT_SET_VALUE", {"variable": variable, "value": number(value)}, key)


def write_owned(path: Path, resource: dict) -> None:
    contents = json.dumps(resource, indent=2) + "\n"
    if path.exists():
        current = json.loads(path.read_text())
        if current.get("id") != resource.get("id"):
            raise FileExistsError(f"refusing to replace unrelated resource {path}")
        if path.read_text() == contents:
            return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents)
    print(f"wrote {path.relative_to(ROOT)}")


def palette(kind: str, name: str, colors: list[str]) -> dict:
    title = "Service Opening " + kind + " " + name.title()
    # GB Studio 4.3.2 getSpritePalette() expands editor colors as [p0,p0,p1,p3].
    # opening.py stores intended hardware indices [transparent,light,mid,dark],
    # so serialize editor [light,mid,dark,dark], not a transparent placeholder.
    if kind == "sprite":
        colors = editor_sprite_colors(colors)
    return {"_resourceType": "palette", "id": opening.resource_id(f"palette:{kind}:{name}"),
            "name": title, "colors": colors, "defaultName": title, "defaultColors": colors}


def editor_sprite_colors(hardware: list[str]) -> list[str]:
    return [hardware[1], hardware[2], hardware[3], hardware[3]]


def write_palettes() -> tuple[list[str], list[str]]:
    backgrounds, sprites = [], []
    for kind, ramps, ids in (("bg", opening.BG_PALETTES, backgrounds),
                             ("sprite", opening.SPRITE_PALETTES, sprites)):
        for name, colors in ramps:
            resource = palette(kind, name, colors)
            write_owned(ROOT / f"project/palettes/service_opening_{kind}_{name}.gbsres", resource)
            ids.append(resource["id"])
    resource = palette("bg", "powered_window", opening.POWERED_WINDOW)
    write_owned(ROOT / "project/palettes/service_opening_bg_powered_window.gbsres", resource)
    sprite_slots = sprites + ["default-sprite"] * 5
    sprite_slots[5] = intro.palette_id("rain")
    sprite_slots[7] = intro.palette_id("pole")
    return backgrounds + ["default-ui"], sprite_slots


def write_variables() -> None:
    # Var 5 (the retired Opening Hero Size) keeps its existing entry; nothing
    # reads it now, and test_climb still checks that entry.
    path = ROOT / "project/variables.gbsres"
    data = json.loads(path.read_text())
    for key, name, symbol in opening.VARIABLES:
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in data["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            data["variables"].append(value)
    contents = json.dumps(data, indent=2) + "\n"
    if path.read_text() != contents:
        path.write_text(contents)
        print("registered opening variables without changing existing variables")


GATE_SPRITE_ID = climb.grid_resource_id("sprite:service_gate")
GATE_SPRITE_PATH = ROOT / "assets/sprites/service_gate.png.gbsres"


def actor(key: str, name: str, position: tuple[int, int], sprite_name: str, index: int,
          sprite_id: str | None = None) -> dict:
    return {
        "_resourceType": "actor", "id": opening.resource_id("actor:" + key),
        "_index": index, "symbol": "opening_" + key, "name": name, "prefabId": "",
        "coordinateType": "tiles", "x": position[0], "y": position[1],
        "frame": 0, "animate": True,
        "spriteSheetId": sprite_id or opening.resource_id("sprite:" + sprite_name), "paletteId": "",
        "direction": "left", "moveSpeed": 1, "animSpeed": 15,
        "isPinned": False, "persistent": False, "collisionGroup": "",
        "collisionExtraFlags": [], "prefabScriptOverrides": {},
        "script": [], "startScript": [], "updateScript": [],
        "hit1Script": [], "hit2Script": [], "hit3Script": [],
    }


def actor_state(actor_id: str, state: str, key: str, loop: bool = True) -> dict:
    return event("EVENT_ACTOR_SET_STATE", {
        "actorId": actor_id, "spriteStateId": state, "loopAnim": loop,
    }, key)


def actor_speed(actor_id: str, speed: int, key: str) -> dict:
    return event("EVENT_ACTOR_SET_ANIMATION_SPEED", {"actorId": actor_id, "speed": speed}, key)


def wait(frames: int, key: str) -> dict:
    return event("EVENT_WAIT", {"units": "frames", "frames": number(frames)}, key)


def palette_state(powered: bool, key: str) -> dict:
    args = {f"palette{index}": "keep" for index in range(8)}
    args["palette3"] = opening.resource_id("palette:bg:" + ("powered_window" if powered else "window"))
    return event("EVENT_PALETTE_SET_BACKGROUND", args, key)


def dialogue(text: str, key: str) -> dict:
    if any(len(line) > 17 for line in text.split("\n")):
        raise ValueError(f"dialogue line too wide for generator convention: {text!r}")
    return event("EVENT_TEXT", {
        "text": [text], "avatarId": "", "minHeight": 4, "maxHeight": 5,
        "textX": 1, "textY": 1, "textHeight": 3, "position": "bottom",
        "clearPrevious": True, "showFrame": True, "speedIn": -1, "speedOut": -1,
        "closeWhen": "key", "closeButton": "a", "closeDelayUnits": "frames",
        "closeDelayFrames": 8,
    }, key)


def spoken(speaker: str, text: str, key: str) -> list[dict]:
    """A character's box: name line, that character's blip, then the narrator's again."""
    return [
        event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(speaker), f"{key}:voice"),
        dialogue(voices.labeled(speaker, [text])[0], key),
        event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(None), f"{key}:narrator"),
    ]


def sound(asset_name: str, key: str) -> dict:
    metadata = json.loads((ROOT / f"assets/sounds/{asset_name}.wav.gbsres").read_text())
    return event("EVENT_SOUND_PLAY_EFFECT", {
        "units": "time", "type": metadata["id"], "priority": "high",
        "wait": False, "pitch": 4, "frequency": 200, "duration": 0.1, "effect": 0,
    }, key)


def choose_hero(key: str) -> list[dict]:
    """Show the 24px electrician with its default state and animation speed."""
    sprite = json.loads((ROOT / "assets/sprites/opening_worker24.png.gbsres").read_text())
    return [
        event("EVENT_PLAYER_SET_SPRITE", {"spriteSheetId": sprite["id"]}, f"{key}:sheet"),
        actor_state("player", "", f"{key}:default"),
        actor_speed("player", sprite.get("animSpeed", 15), f"{key}:speed"),
    ]


def gate_id() -> str:
    return opening.resource_id("actor:service_gate")


def service_gate_actor() -> dict:
    gate = actor("service_gate", "Service gate - awning", opening.GATE, "service_gate", 2,
                 sprite_id=GATE_SPRITE_ID)
    gate["startScript"] = [if_value(RESTORED, 0, "gate:entry", [
        actor_state("$self$", "Closed", "gate:closed"),
    ], [actor_state("$self$", "Open", "gate:open")])]
    return gate


def repair_script() -> list[dict]:
    marta_id = opening.resource_id("actor:marta")
    # An ordinary actor interaction is natively locked; input/physics remain
    # paused while these two authored repair poses are displayed.
    work = [
        actor_state("player", "Repair", "repair:pose-state", False),
        actor_speed("player", 255, "repair:pause-animation"),
        event("EVENT_ACTOR_SET_FRAME", {"actorId": "player", "frame": number(0)}, "repair:pose0"),
        wait(8, "repair:wait0"),
        event("EVENT_ACTOR_SET_FRAME", {"actorId": "player", "frame": number(1)}, "repair:pose1"),
        wait(8, "repair:wait1"),
        set_value(opening.VAR_CARRYING_CABLE, 0, "repair:consume-cable"),
        set_value(RESTORED, 1, "repair:record-power"),
        palette_state(True, "repair:local-amber"),
        actor_state(marta_id, "Powered", "repair:marta-relieved"),
        actor_state("$self$", "On", "repair:terminal-lit"),
        actor_state(opening.resource_id("actor:tutorial_cable"), "Standing", "repair:pole-restored"),
        # The gate opens on the same beat as the existing connect sound; no second sound.
        actor_state(gate_id(), "Open", "repair:gate-open"),
        sound("connect", "repair:connect-sound"),
        dialogue("Breeze ahead.\nWait for calm.", "repair:wind-tip"),
        actor_state("player", "", "repair:resume-default"),
        actor_speed("player", hero_speed(24), "repair:resume-speed"),
    ]
    return [if_value(RESTORED, 0, "repair:once", work)]


def cable_actor() -> dict:
    """The cable end is an explicit B pickup; the existing pole art supplies its cue."""
    cable = actor("tutorial_cable", "Loose service cable", opening.CABLE, "unused", 3,
                  sprite_id=json.loads((ROOT / "assets/sprites/intro_pole.png.gbsres").read_text())["id"])
    cable["startScript"] = [if_value(RESTORED, 1, "cable:restored", [
        actor_state("$self$", "Standing", "cable:upright"),
    ], [if_value(opening.VAR_CARRYING_CABLE, 1, "cable:carried", [
        actor_state("$self$", "Snapped", "cable:empty"),
    ], [actor_state("$self$", "Snapped+Cable", "cable:initial")])])]
    pickup = if_value(opening.VAR_CARRYING_CABLE, 0, "cable:pickup", [
        set_value(opening.VAR_CARRYING_CABLE, 1, "cable:carry-value"),
        actor_state("$self$", "Snapped", "cable:empty-pole"),
        actor_state("player", "Carry", "cable:hero-carry"),
        sound("pickup", "cable:pickup-sound"),
        dialogue("Got the cable!\nB at the panel.", "cable:pickup-text"),
    ], [dialogue("Cable is in hand.", "cable:already-held")])
    cable["script"] = [if_value(RESTORED, 0, "cable:unrepaired", [pickup], [
        dialogue("Service is on.", "cable:service-on"),
    ])]
    return cable


def repair_interaction() -> list[dict]:
    return [if_value(RESTORED, 0, "repair:not-restored", [
        if_value(opening.VAR_CARRYING_CABLE, 1, "repair:has-cable", repair_script(), [
            dialogue("B: pick up cable.\nThen B at panel.", "repair:needs-cable"),
        ]),
    ], [dialogue("Lights are on.", "repair:already-restored")])]


def wind_actor() -> dict:
    """Telegraphed, recoverable gust; its collision is active only during Burst."""
    gust_id = json.loads((ROOT / "assets/sprites/climb_gust.png.gbsres").read_text())["id"]
    breeze = actor("tutorial_wind", "Gentle breeze", opening.WIND, "unused", 4,
                   sprite_id=gust_id)
    breeze["collisionGroup"] = "1"
    breeze["startScript"] = [event("EVENT_ACTOR_COLLISIONS_DISABLE", {
        "actorId": "$self$",
    }, "wind:always-safe"), event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, "wind:initially-hidden")]
    breeze["updateScript"] = [if_value(RESTORED, 1, "wind:after-repair", [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, "wind:warning-safe"),
        actor_state("$self$", "Warning", "wind:warning"),
        event("EVENT_ACTOR_SHOW", {"actorId": "$self$"}, "wind:warning-visible"),
        wait(40, "wind:warning-time"),
        actor_state("$self$", "Burst", "wind:burst"),
        event("EVENT_ACTOR_COLLISIONS_ENABLE", {"actorId": "$self$"}, "wind:burst-active"),
        wait(20, "wind:burst-time"),
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": "$self$"}, "wind:calm-safe"),
        event("EVENT_ACTOR_HIDE", {"actorId": "$self$"}, "wind:calm"),
        wait(60, "wind:rest-time"),
    ], [wait(30, "wind:disabled-wait")])]
    return breeze


def wind_recovery_events() -> list[dict]:
    """A gust knocks the player back to the panel without an electrical hit beat."""
    return [
        event("EVENT_ACTOR_COLLISIONS_DISABLE", {"actorId": opening.resource_id("actor:tutorial_wind")},
              "wind-hit:disable"),
        event("EVENT_CAMERA_SHAKE", {
            "units": "frames", "frames": 4, "shakeDirection": "horizontal",
            "magnitude": number(1),
        }, "wind-hit:bump"),
        wait(4, "wind-hit:recover-beat"),
        set_value(opening.VAR_CARRYING_CABLE, 0, "wind-hit:clear-carry"),
        event("EVENT_ACTOR_SET_POSITION", {
            "actorId": "player", "units": "tiles",
            "x": number(opening.PANEL[0]), "y": number(opening.PANEL[1]),
        }, "wind-hit:panel-checkpoint"),
    ]


def field_training() -> list[dict]:
    """Optional B-button field notes; these are never shown during scene entry."""
    pages = [
        "Live arcs: stay\nclear. Wait for\nwarning.",
        "Loose wires whip.\nStay back.",
        "Cracked boards?\nStep around them.",
        "Gust: heed signs.\nMove in calm.",
        "Blown back?\nReturn to panel.",
        "Carry cable.\nB at pole, then\nB at box.",
    ]
    return [event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args("marta"), "training:voice"),
            *[dialogue(page, f"training:page:{i}") for i, page in enumerate(pages)],
            event("EVENT_TEXT_SET_SOUND_EFFECT", voices.sound_args(None), "training:narrator")]


def amara_actor() -> dict:
    """Amara's field guide is available only through her interaction."""
    marta = actor("marta", "Amara - lineman guide", opening.MARTA, "opening_marta", 0)
    marta["startScript"] = [if_value(RESTORED, 0, "marta:entry", [
        actor_state("$self$", "Waiting", "marta:waiting"),
    ], [actor_state("$self$", "Powered", "marta:powered")])]
    marta["script"] = [*field_training(), if_value(RESTORED, 0, "marta:talk", [
        *spoken("marta", "Power's out all\nover. Start here.", "marta:dark-talk"),
    ], spoken("marta", "Panel's alive!\nNow, my hilltop.", "marta:lit-talk"))]
    return marta


def hero_speed(size: int) -> int:
    return json.loads((ROOT / f"assets/sprites/opening_worker{size}.png.gbsres").read_text()).get("animSpeed", 15)


def work_order_events() -> list[dict]:
    """Dispatch Amara once; a street round-trip returns directly to her job.

    var 16 = 1 belongs only to the initial work-order handoff, so the climb's
    fresh-start reset and briefing run once even before any line is repaired.
    The campaign start resets the independent dispatched flag for a new run.
    """
    x, y = climb.START
    resume = event("EVENT_SWITCH_SCENE", {
        "x": number(x), "y": number(y), "direction": "right",
        "sceneId": tickets.CLIMB_SCENE_ID, "fadeSpeed": "2",
    }, "exit:resume-climb")
    return [if_value(opening.VAR_AMARA_DISPATCHED, 0, "exit:first-dispatch", [
        set_value(opening.VAR_AMARA_DISPATCHED, 1, "exit:record-dispatch"),
        *tickets.to_work_order(1, "exit", event, set_value, number),
    ], [resume])]


def exit_trigger() -> dict:
    """Awning exit: opens Amara's work order (then Storm Climb) once Service Restored is set."""
    x, y, w, h = opening.EXIT
    gate = if_value(RESTORED, 1, "exit:gate", work_order_events(), [
        dialogue("Gate's locked.\nFix the panel.", "exit:unpowered"),
        event("EVENT_ACTOR_SET_POSITION", {
            "actorId": "player", "units": "tiles",
            "x": number(opening.EXIT_NUDGE[0]), "y": number(opening.EXIT_NUDGE[1]),
        }, "exit:nudge-back"),
    ])
    return {
        "_resourceType": "trigger", "id": opening.resource_id("trigger:exit"),
        "name": "Awning exit (gated on service restored)", "prefabId": "",
        "x": x, "y": y, "symbol": EXIT_SYMBOL, "prefabScriptOverrides": {},
        "width": w, "height": h, "script": [gate], "leaveScript": [], "_index": 0,
    }


def build_scene(backgrounds: list[str], sprites: list[str]) -> dict:
    music = json.loads((ROOT / "assets/music/cfe_storm_climb.uge.gbsres").read_text())["id"]
    editor_x, editor_y = scenes.editor_position("service_opening")
    return {
        "_resourceType": "scene", "id": opening.resource_id("scene:service-opening"),
        "_index": 3, "name": "Lineman Training", "symbol": "scene_service_opening",
        "backgroundId": opening.resource_id("background:service-opening"), "tilesetId": "",
        "width": 20, "height": 18, "type": "PLATFORM", "colorModeOverride": "none",
        "paletteIds": backgrounds, "spritePaletteIds": sprites,
        "collisions": collision_rle(opening.collision_grid(), 20, 18),
        "autoFadeSpeed": 1, "x": editor_x, "y": editor_y,
        "script": [
            *choose_hero("entry:24"),
            event("EVENT_ACTOR_SET_DIRECTION", {
                "actorId": "player", "direction": {"type": "direction", "value": "right"},
            }, "entry:face-right"),
            if_value(RESTORED, 0, "entry:power", [palette_state(False, "entry:cold")], [palette_state(True, "entry:powered")]),
            event("EVENT_MUSIC_PLAY", {"musicId": music}, "entry:music"),
            if_value(RESTORED, 0, "entry:tutorial", [
                set_value(opening.VAR_CARRYING_CABLE, 0, "entry:empty-hands"),
                dialogue("LINEMAN TRAINING\nD-pad: move.\nTap A: short hop", "entry:move-and-tap"),
                dialogue("Hold A: rise.\nCheck above.\nB: Amara tips.", "entry:hold-a"),
                dialogue("B: take cable.\nB: fit at panel.", "entry:cable-controls"),
            ]),
            if_value(opening.VAR_CARRYING_CABLE, 0, "entry:restore-carry", [], [
                actor_state("player", "Carry", "entry:carry-pose"),
            ]),
        ],
        "playerHit1Script": wind_recovery_events(), "playerHit2Script": [], "playerHit3Script": [],
    }


def main() -> None:
    # Validate all source assets before writing any scene resources.
    expected = [(ROOT / "assets/backgrounds/service_opening.png.gbsres", "background:service-opening")]
    expected.extend((ROOT / f"assets/sprites/{name}.png.gbsres", "sprite:" + name)
                    for name in ("opening_worker24", "opening_marta", "opening_terminal"))
    for path, key in expected:
        if json.loads(path.read_text())["id"] != opening.resource_id(key):
            raise ValueError(f"unexpected resource identity in {path}")
    backgrounds, sprites = write_palettes()
    write_variables()
    marta = amara_actor()
    terminal = actor("terminal", "Substation repair panel", opening.PANEL, "opening_terminal", 1)
    terminal["startScript"] = [if_value(RESTORED, 0, "terminal:entry", [
        actor_state("$self$", "Off", "terminal:off"),
    ], [actor_state("$self$", "On", "terminal:on")])]
    terminal["script"] = repair_interaction()
    if GATE_SPRITE_PATH.exists():
        # The gate sprite may be generated separately; when present its ID must match.
        sprite_id = json.loads(GATE_SPRITE_PATH.read_text())["id"]
        if sprite_id != GATE_SPRITE_ID:
            raise ValueError(f"{GATE_SPRITE_PATH} id {sprite_id} != {GATE_SPRITE_ID}")
    write_owned(SCENE_DIR / "scene.gbsres", build_scene(backgrounds, sprites))
    write_owned(SCENE_DIR / "actors/marta.gbsres", marta)
    write_owned(SCENE_DIR / "actors/terminal.gbsres", terminal)
    write_owned(SCENE_DIR / "actors/tutorial_cable.gbsres", cable_actor())
    write_owned(SCENE_DIR / "actors/tutorial_wind.gbsres", wind_actor())
    write_owned(SCENE_DIR / "actors/service_gate.gbsres", service_gate_actor())
    write_owned(SCENE_DIR / "triggers" / f"{EXIT_SYMBOL}.gbsres", exit_trigger())
    print("generated isolated M-V1 opening; launch scene unchanged")


if __name__ == "__main__":
    main()
