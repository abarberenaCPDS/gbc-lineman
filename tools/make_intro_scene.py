"""Generate the logo, intro story and title scenes from ``intro.py``.

Run with ``"$PY" tools/make_intro_scene.py`` from any working directory, where PY
is the managed toolchain Python. This writes the intro palettes, the three intro
scenes with their story actors, and the start fields of ``project/settings.gbsres``.
Authored timings, captions, positions and stable IDs live in the sibling
``intro.py`` contract module; this file only turns them into GB Studio events.

Background and sprite art come from ``make_intro_art.py`` and
``make_intro_sprites.py``. This generator only references their IDs and warns
when those sidecars are not on disk yet.

Test ROMs use ``--test-start SCENE_ID X Y DIRECTION`` to point the start at another
scene; SCENE_ID may be a registry folder name (``--test-start lab_movement_room 2 14
right``). That writes a temporary override to ``settings.gbsres``: never commit it,
and regenerate without the flag before committing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
PALETTE_DIR = PROJECT_DIR / "project" / "palettes"
SCENES_DIR = PROJECT_DIR / "project" / "scenes"
SETTINGS_PATH = PROJECT_DIR / "project" / "settings.gbsres"
CONNECT_SOUND = "assets/sounds/connect.wav.gbsres"
DIRECTIONS = ("up", "down", "left", "right")

sys.path.insert(0, str(TOOLS_DIR))
try:
    import intro  # noqa: E402  (sole source of truth for this scene set)
    import make_climb_scene as shared  # noqa: E402  (generic helpers only)
    import scenes  # noqa: E402  (registry: folder name -> scene id for --test-start)
except ModuleNotFoundError as error:
    if error.name in {"intro", "make_climb_scene", "climb", "opening", "ridge", "scenes"}:
        raise SystemExit(
            f"cannot generate the intro scenes: tools/{error.name}.py is missing"
        ) from error
    raise

# Inputs: the story skips on A or START; the title starts on START only.
STORY_SKIP_INPUTS = ["a", "start"]
TITLE_START_INPUTS = ["start"]
THREAD_HANDLE = "T0"           # GB Studio temp variable holding the thread handle
SHAKE_THREAD_HANDLE = "T1"     # the story thread's own temp for its shake threads
EMPTY_ROW = [0] * intro.MAP_W
EMPTY_COLLISIONS = [list(EMPTY_ROW) for _ in range(intro.MAP_H)]
# Story and title caption/text draws use BG slot 7 (UI), which every scene keeps.
DEFAULT_SPRITE_PALETTE = "default-sprite"
# Background palette slot holding the sky (see intro.SKY_SLOT).
SKY = intro.SKY_SLOT
# Shot cues are placed at these frame offsets; see shot_cues().
SNAP_CONNECT_AT = 0

# Palette slot lists per background stem (intro.SCENES order).
SLOTS_BY_STEM = {
    "intro_logo": intro.LOGO_SLOTS,
    "intro_story": intro.STORY_SLOTS,
    "title": intro.TITLE_SLOTS,
}


# ---------------------------------------------------------------------------
# Event builders. Keys are human labels; the event ID is intro.resource_id("event:<key>").
# ---------------------------------------------------------------------------
def ev(command: str, args: dict[str, Any], key: str,
       children: dict[str, list[dict[str, Any]]] | None = None) -> dict[str, Any]:
    node: dict[str, Any] = {"command": command, "args": args,
                            "id": intro.resource_id(f"event:{key}")}
    if children is not None:
        node["children"] = children
    return node


def num(value: int) -> dict[str, Any]:
    return shared.number(value)


def if_value(variable: str, value: int, key: str, yes: list[dict[str, Any]],
             no: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return ev("EVENT_IF", {"condition": {
        "type": "eq", "valueA": {"type": "variable", "value": variable}, "valueB": num(value),
    }}, key, children={"true": yes, "false": no or []})


def set_value(variable: str, value: int, key: str) -> dict[str, Any]:
    return ev("EVENT_SET_VALUE", {"variable": variable, "value": num(value)}, key)


def music_play(theme: str, key: str) -> dict[str, Any]:
    return ev("EVENT_MUSIC_PLAY", {"musicId": intro.THEME_IDS[theme]}, key)


def text_sound(key: str) -> dict[str, Any]:
    return ev("EVENT_TEXT_SET_SOUND_EFFECT", dict(intro.TEXT_SOUND), key)


def theme_audition(key: str) -> list[dict[str, Any]]:
    """SELECT on the title: play the next intro-theme candidate (a -> b -> c -> a)."""
    branches: list[dict[str, Any]] = []
    for index in reversed(range(len(intro.THEMES))):
        nxt = (index + 1) % len(intro.THEMES)
        events = [set_value(intro.VAR_THEME, nxt, f"{key}:{index}:set"),
                  music_play(intro.THEMES[nxt], f"{key}:{index}:play")]
        branches = [if_value(intro.VAR_THEME, index, f"{key}:{index}", events, branches)]
    return branches


def wait(frames: int, key: str) -> dict[str, Any]:
    if frames <= 0:
        raise ValueError(f"wait for {key} must be positive, got {frames}")
    return ev("EVENT_WAIT", {"units": "frames", "frames": num(frames)}, key)


def hide_player(key: str) -> dict[str, Any]:
    return ev("EVENT_ACTOR_HIDE", {"actorId": "player"}, key)


def actor_show(actor: str, key: str) -> dict[str, Any]:
    return ev("EVENT_ACTOR_SHOW", {"actorId": actor}, key)


def actor_hide(actor: str, key: str) -> dict[str, Any]:
    return ev("EVENT_ACTOR_HIDE", {"actorId": actor}, key)


def actor_state(actor: str, state: str, key: str, loop: bool = True) -> dict[str, Any]:
    return ev("EVENT_ACTOR_SET_STATE", {
        "actorId": actor, "spriteStateId": state, "loopAnim": loop,
    }, key)


def actor_move(actor: str, tile: tuple[int, int], key: str) -> dict[str, Any]:
    """Blocking walk: the script waits until the actor arrives."""
    return ev("EVENT_ACTOR_MOVE_TO", {
        "actorId": actor, "x": num(tile[0]), "y": num(tile[1]), "units": "tiles",
        "collideWith": [], "lockDirection": [], "moveType": "horizontal",
    }, key)


def text_draw(text: str, x: int, y: int, location: str, key: str) -> dict[str, Any]:
    return ev("EVENT_TEXT_DRAW", {"text": text, "x": x, "y": y, "location": location}, key)


def overlay_show(color: str, x: int, y: int, key: str) -> dict[str, Any]:
    return ev("EVENT_OVERLAY_SHOW", {"color": color, "x": x, "y": y}, key)


def overlay_hide(key: str) -> dict[str, Any]:
    return ev("EVENT_OVERLAY_HIDE", {}, key)


def palette_slots(slots: dict[int, str], key: str) -> dict[str, Any]:
    """Swap the named BG slots (palette names from intro.BG_PALETTES); the rest keep."""
    args: dict[str, Any] = {f"palette{index}": "keep" for index in range(8)}
    for slot, name in slots.items():
        args[f"palette{slot}"] = intro.palette_id(name)
    return ev("EVENT_PALETTE_SET_BACKGROUND", args, key)


def sound(sound_type: str, key: str, duration: float = 0.5) -> dict[str, Any]:
    """Built-in ``crash`` or a project sound ID. ``wait`` is off so the script keeps its timing."""
    return ev("EVENT_SOUND_PLAY_EFFECT", {
        "units": "time", "type": sound_type, "priority": "high", "pitch": 4,
        "frequency": 200, "duration": duration, "wait": False, "effect": 0,
    }, key)


def camera_shake(frames: int, magnitude: int, key: str) -> dict[str, Any]:
    """Blocking: GB Studio invokes camera_shake_frames until the shake ends.

    The story runs it in its own thread (shake_thread) to keep its timing."""
    return ev("EVENT_CAMERA_SHAKE", {
        "units": "frames", "frames": frames, "shakeDirection": "horizontal",
        "magnitude": num(magnitude),
    }, key)


def fade_out(key: str) -> dict[str, Any]:
    return ev("EVENT_FADE_OUT", {"speed": intro.FADE_SPEED}, key)


def switch_scene(scene_id: str, x: int, y: int, direction: str, key: str) -> dict[str, Any]:
    return ev("EVENT_SWITCH_SCENE", {
        "sceneId": scene_id, "x": num(x), "y": num(y),
        "direction": direction, "fadeSpeed": intro.FADE_SPEED,
    }, key)


def input_script_set(inputs: list[str], then: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return ev("EVENT_SET_INPUT_SCRIPT", {"input": inputs, "override": True}, key,
              children={"true": then})


def input_script_remove(inputs: list[str], key: str) -> dict[str, Any]:
    return ev("EVENT_REMOVE_INPUT_SCRIPT", {"input": inputs}, key)


def leave_to_title(key: str) -> list[dict[str, Any]]:
    """Story exit (skip or the last shot): drop the skip input, fade, hide the
    caption overlay (the window layer survives a scene switch: exact ROM
    ba3a3c63 showed the last caption over the title), go to the title."""
    return [
        input_script_remove(STORY_SKIP_INPUTS, f"{key}:remove-input"),
        fade_out(f"{key}:fade"),
        overlay_hide(f"{key}:hide-overlay"),
        switch_scene(intro.TITLE_SCENE_ID, 0, 0, "right", f"{key}:to-title"),
    ]


def thread_start(body: list[dict[str, Any]], key: str) -> dict[str, Any]:
    """Run ``body`` in its own unlocked thread.

    GB Studio compiles every scene start script with VM_LOCK, and button
    scripts never fire while the VM is locked: with the story timeline and the
    title blink loop in the start script, A/START did nothing (exact ROM
    04c6c4a4). The start script registers the buttons, starts this thread and
    ends, which unlocks input.
    """
    return ev("EVENT_THREAD_START", {"variable": THREAD_HANDLE}, key, children={"true": body})


def shake_thread(frames: int, magnitude: int, key: str) -> dict[str, Any]:
    """Camera shake in a short thread of its own, so the story timeline does not stall."""
    return ev("EVENT_THREAD_START", {"variable": SHAKE_THREAD_HANDLE}, key,
              children={"true": [camera_shake(frames, magnitude, f"{key}:shake")]})


def loop(body: list[dict[str, Any]], key: str) -> dict[str, Any]:
    return ev("EVENT_LOOP", {}, key, children={"true": body})


def timeline(total: int, cues: list[tuple[int, list[dict[str, Any]]]], key: str,
             walk: int = 0) -> list[dict[str, Any]]:
    """Events at frame offsets inside one shot. EVENT_WAIT fills the gaps so the shot lasts ``total``.

    Every event listed here must be non-blocking except the shot's own walk,
    which sits at offset 0 and holds the thread ``walk`` frames; the waits
    leave those out so the shot stays on the music's bar grid.
    """
    offsets = [at for at, _ in cues]
    if offsets != sorted(offsets) or len(set(offsets)) != len(offsets):
        raise ValueError(f"{key}: cue offsets must be strictly increasing")
    if offsets and not (0 <= offsets[0] and offsets[-1] < total):
        raise ValueError(f"{key}: cue outside the {total}-frame shot")
    out: list[dict[str, Any]] = []
    now = 0
    for at, events in cues:
        if at > now:
            out.append(wait(at - now, f"{key}:to{at}"))
            now = at
        out.extend(events)
        if at == 0:
            now += walk
    if total > now:
        out.append(wait(total - now, f"{key}:tail"))
    return out


# ---------------------------------------------------------------------------
# Actor resources
# ---------------------------------------------------------------------------
def actor_id(key: str) -> str:
    return intro.resource_id(f"actor:{key}")


def actor_resource(*, index: int, symbol: str, name: str, key: str, sprite_id: str,
                   x: int, y: int, direction: str = "down",
                   start_script: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "_resourceType": "actor",
        "id": actor_id(key),
        "_index": index,
        "symbol": symbol,
        "prefabId": "",
        "name": name,
        "coordinateType": "tiles",
        "x": x,
        "y": y,
        "frame": 0,
        "animate": True,
        "spriteSheetId": sprite_id,
        "paletteId": "",
        "direction": direction,
        "moveSpeed": 1,
        "animSpeed": 15,
        "isPinned": False,
        "persistent": False,
        "collisionGroup": "",
        "collisionExtraFlags": [],
        "prefabScriptOverrides": {},
        "script": [],
        "startScript": start_script or [],
        "updateScript": [],
        "hit1Script": [],
        "hit2Script": [],
        "hit3Script": [],
    }


def story_actors() -> list[dict[str, Any]]:
    """Rain, bolt, pole and hero, in editor order. Rain, bolt and hero start hidden."""
    actors: list[dict[str, Any]] = []
    for position, drop in enumerate(intro.RAIN):
        x, y = drop
        key = f"rain:{position}"
        actors.append(actor_resource(
            index=len(actors), symbol=f"intro_rain_{position}", name=f"Rain {position}",
            key=key, sprite_id=intro.RAIN_SPRITE_ID, x=x, y=y,
            start_script=[actor_hide("$self$", f"{key}:hidden")],
        ))
    bolt_x, bolt_y = intro.BOLT
    actors.append(actor_resource(
        index=len(actors), symbol="intro_bolt", name="Lightning Bolt", key="bolt",
        sprite_id=intro.BOLT_SPRITE_ID, x=bolt_x, y=bolt_y,
        start_script=[actor_hide("$self$", "bolt:hidden")],
    ))
    for key, position in zip(pole_keys(), intro.POLES):
        pole_x, pole_y = position
        symbol = "intro_" + key.replace(":", "_")
        actors.append(actor_resource(
            index=len(actors), symbol=symbol, name="Power Pole " + key, key=key,
            sprite_id=intro.POLE_SPRITE_ID, x=pole_x, y=pole_y,
            start_script=[actor_state("$self$", "Standing", f"{key}:standing")],
        ))
    hero_x, hero_y = intro.HERO_ENTER
    actors.append(actor_resource(
        index=len(actors), symbol="intro_hero", name="Electrician", key="hero",
        sprite_id=intro.HERO_SPRITE_ID, x=hero_x, y=hero_y, direction="right",
        start_script=[actor_hide("$self$", "hero:hidden")],
    ))
    return actors


def rain_ids() -> list[str]:
    return [actor_id(f"rain:{position}") for position in range(len(intro.RAIN))]


# ---------------------------------------------------------------------------
# Scene scripts
# ---------------------------------------------------------------------------
def logo_script() -> list[dict[str, Any]]:
    return [
        hide_player("logo:hide-player"),
        text_sound("logo:text-voice"),
        set_value(intro.VAR_THEME, intro.THEMES.index(intro.DEFAULT_THEME), "logo:theme-index"),
        wait(intro.LOGO_HOLD_FRAMES, "logo:hold"),
        fade_out("logo:fade"),
        switch_scene(intro.STORY_SCENE_ID, 0, 0, "right", "logo:to-story"),
    ]


def pole_keys() -> list[str]:
    """Actor keys for intro.POLES; the struck pole keeps the original "pole" ID."""
    return ["pole" if p == intro.POLE else f"pole:{i}" for i, p in enumerate(intro.POLES)]


def shot_cues(name: str) -> list[tuple[int, list[dict[str, Any]]]]:
    """Cues per shot plus its thunder, merged by frame offset (timeline() adds waits)."""
    merged: dict[int, list[dict[str, Any]]] = {}
    for at, events in _shot_cues(name):
        merged.setdefault(at, []).extend(events)
    for index, (shot, at, seconds) in enumerate(intro.THUNDER):
        if shot == name:
            merged.setdefault(at, []).append(
                sound("crash", f"story:{name}:thunder{index}", seconds))
    return sorted(merged.items())


def _shot_cues(name: str) -> list[tuple[int, list[dict[str, Any]]]]:
    key = f"story:{name}"
    bolt = actor_id("bolt")
    hero = actor_id("hero")
    if name == "dusk":
        return []
    if name == "storm":
        return [(0, [
            palette_slots({SKY: "sky_storm"}, f"{key}:sky"),
            *[actor_show(rain, f"{key}:rain-show{i}") for i, rain in enumerate(rain_ids())],
        ])]
    if name == "lightning":
        flash = intro.FLASH_FRAMES
        cues: list[tuple[int, list[dict[str, Any]]]] = []
        for n, at in enumerate(intro.STRIKES):
            k = f"{key}:strike{n}"
            cues += [
                (at, [actor_show(bolt, f"{k}:bolt-show"),
                      palette_slots({SKY: "sky_flash"}, f"{k}:flash0"),
                      shake_thread(intro.SHAKE_FRAMES, intro.SHAKE_MAGNITUDE, f"{k}:shake-thread")]),
                (at + flash, [palette_slots({SKY: "sky_storm"}, f"{k}:storm0")]),
                (at + 2 * flash, [palette_slots({SKY: "sky_flash"}, f"{k}:flash1")]),
                (at + 3 * flash, [palette_slots({SKY: "sky_storm"}, f"{k}:storm1")]),
                (at + intro.SHAKE_FRAMES, [actor_hide(bolt, f"{k}:bolt-hide")]),
            ]
        return cues
    if name == "snap":
        connect = shared.sidecar_id(CONNECT_SOUND, "sound")
        struck_first = sorted(zip(pole_keys(), intro.POLES), key=lambda kp: kp[1] != intro.POLE)
        cues = [(SNAP_CONNECT_AT + n * intro.SNAP_GAP, [
            actor_state(actor_id(pole_key), "Snapped+Cable", f"{key}:{pole_key}-snapped"),
            sound(connect, f"{key}:{pole_key}-spark"),
        ]) for n, (pole_key, _) in enumerate(struck_first)]
        for index, slot in enumerate(intro.WINDOW_SLOTS, start=1):
            cues.append((intro.WINDOW_OFF_GAP * index, [
                palette_slots({slot: "window_dark"}, f"{key}:window{slot}"),
            ]))
        return cues
    if name == "morning":
        return [(0, [
            *[actor_hide(rain, f"{key}:rain-hide{i}") for i, rain in enumerate(rain_ids())],
            palette_slots({SKY: "sky_morning"}, f"{key}:sky"),
        ])]
    if name in ("dark", "offline"):
        return []
    if name == "hero":
        return [(0, [
            actor_state(hero, "Walk", f"{key}:hero-walking"),
            actor_show(hero, f"{key}:hero-show"),
            actor_move(hero, intro.HERO_STOP, f"{key}:hero-walk"),
            actor_state(hero, "Idle", f"{key}:hero-idle"),
        ])]
    if name == "mission":
        return []
    raise ValueError(f"no cues for shot {name!r}")


def story_script() -> list[dict[str, Any]]:
    # Restart the theme with the first shot on every pass (title attract loop
    # included), so the song's sections land on their shots.
    shots: list[dict[str, Any]] = [music_play(intro.DEFAULT_THEME, "story:theme")]
    for name, lines, frames in intro.SHOTS:
        caption = text_draw(intro.caption_text(lines), *intro.CAPTION_TEXT, "overlay",
                            f"story:{name}:caption")
        shots.append(caption)
        walk = intro.HERO_WALK_FRAMES if name == "hero" else 0
        shots.extend(timeline(frames - intro.SHOT_OVERHEAD_FRAMES, shot_cues(name),
                              f"story:{name}", walk))
    shots.extend(leave_to_title("story:end"))
    return [
        hide_player("story:hide-player"),
        input_script_set(STORY_SKIP_INPUTS, leave_to_title("story:skip"), "story:skip-input"),
        overlay_show(intro.CAPTION_OVERLAY_COLOR, *intro.CAPTION_OVERLAY, "story:caption-overlay"),
        thread_start(shots, "story:timeline"),
    ]


def title_script() -> list[dict[str, Any]]:
    return [
        hide_player("title:hide-player"),
        overlay_hide("title:hide-overlay"),
        *([input_script_set(["select"], theme_audition("title:audition"),
                            "title:audition-input")] if intro.AUDITION_THEMES else []),
        input_script_set(TITLE_START_INPUTS, [
            input_script_remove(TITLE_START_INPUTS, "title:start:remove-input"),
            *([input_script_remove(["select"], "title:start:remove-audition")]
              if intro.AUDITION_THEMES else []),
            fade_out("title:start:fade"),
            switch_scene(intro.OPENING_SCENE_ID, *intro.OPENING_START,
                         intro.OPENING_DIRECTION, "title:start:to-opening"),
        ], "title:start-input"),
        thread_start([
            # Unrolled, not EVENT_LOOP: a fixed number of blinks, then replay the story.
            *[event for n in range(intro.TITLE_IDLE_BLINKS) for event in (
                palette_slots({intro.PRESS_SLOT: "ui"}, f"title:blink{n}:on-palette"),
                wait(intro.BLINK_FRAMES, f"title:blink{n}:on"),
                palette_slots({intro.PRESS_SLOT: "press_off"}, f"title:blink{n}:off-palette"),
                wait(intro.BLINK_FRAMES, f"title:blink{n}:off"),
            )],
            input_script_remove(TITLE_START_INPUTS, "title:idle:remove-input"),
            *([input_script_remove(["select"], "title:idle:remove-audition")]
              if intro.AUDITION_THEMES else []),
            fade_out("title:idle:fade"),
            switch_scene(intro.STORY_SCENE_ID, 0, 0, "right", "title:idle:to-story"),
        ], "title:blink-thread"),
    ]


# ---------------------------------------------------------------------------
# Palettes
# ---------------------------------------------------------------------------
def palette_resource(kind: str, name: str, colors: list[str]) -> dict[str, Any]:
    title = f"Intro {kind} {name}"
    return {
        "_resourceType": "palette",
        "id": intro.palette_id(name),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def palette_files() -> list[tuple[Path, dict[str, Any]]]:
    files: list[tuple[Path, dict[str, Any]]] = []
    for name, colors in intro.BG_PALETTES.items():
        files.append((PALETTE_DIR / f"intro_bg_{name}.gbsres",
                      palette_resource("bg", name, colors)))
    for name, hardware in intro.SPRITE_PALETTES.items():
        files.append((PALETTE_DIR / f"intro_sprite_{name}.gbsres",
                      palette_resource("sprite", name,
                                       shared.editor_sprite_colors(hardware))))
    return files


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------
def background_palette_ids(stem: str) -> list[str]:
    slots = SLOTS_BY_STEM[stem]
    if len(slots) != 8 or slots[7] != "ui":
        raise ValueError(f"{stem}: background slots must be 8 entries with UI in slot 7")
    return [intro.palette_id(name) for name in slots]


def sprite_palette_ids() -> list[str]:
    ids = [DEFAULT_SPRITE_PALETTE] * 8
    for name, slot in intro.SPRITE_SLOTS.items():
        ids[slot] = intro.palette_id(name)
    return ids


def scene_resource(scene_id: str, folder: str, name: str, stem: str, index: int,
                   x: int, y: int, script: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "_resourceType": "scene",
        "id": scene_id,
        "_index": index,
        "name": name,
        "symbol": "scene_" + folder,
        "backgroundId": intro.BACKGROUND_IDS[stem],
        "tilesetId": "",
        "width": intro.MAP_W,
        "height": intro.MAP_H,
        "type": intro.SCENE_TYPES[scene_id],
        "colorModeOverride": "none",
        "paletteIds": background_palette_ids(stem),
        "spritePaletteIds": sprite_palette_ids(),
        "collisions": shared.collision_rle(EMPTY_COLLISIONS, intro.MAP_W, intro.MAP_H),
        "autoFadeSpeed": 1,
        "x": x,
        "y": y,
        "script": script,
        "playerHit1Script": [],
        "playerHit2Script": [],
        "playerHit3Script": [],
        "playerSpriteSheetId": intro.HERO_SPRITE_ID,
    }


def build_scenes() -> dict[str, tuple[dict[str, Any], list[dict[str, Any]]]]:
    """folder -> (scene resource, actor resources). Scripts are built fresh each call."""
    scripts = {
        intro.LOGO_SCENE_ID: logo_script(),
        intro.STORY_SCENE_ID: story_script(),
        intro.TITLE_SCENE_ID: title_script(),
    }
    actors = {intro.STORY_SCENE_ID: story_actors()}
    built: dict[str, tuple[dict[str, Any], list[dict[str, Any]]]] = {}
    for scene_id, folder, name, stem, index, x, y in intro.SCENES:
        scene = scene_resource(scene_id, folder, name, stem, index, x, y, scripts[scene_id])
        built[folder] = (scene, actors.get(scene_id, []))
    return built


def settings_update(test_start: tuple[str, int, int, str] | None) -> dict[str, Any]:
    data = shared.load_json(SETTINGS_PATH)
    data.update(intro.settings_start(test_start))
    return data


# ---------------------------------------------------------------------------
# Checks run before anything is written
# ---------------------------------------------------------------------------
def check_captions(shots: list[tuple[str, list[str], int]] = intro.SHOTS) -> None:
    for name, lines, _ in shots:
        for line in lines:
            if len(line) > intro.MAX_CAPTION_CHARS:
                raise ValueError(f"shot {name}: caption line over {intro.MAX_CAPTION_CHARS} chars: {line!r}")


def walk(events: list[dict[str, Any]]):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def check_unique_ids(resources: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for resource in resources:
        ids = [resource["id"]]
        for block in ("script", "startScript", "updateScript", "playerHit1Script"):
            ids.extend(entry["id"] for entry in walk(resource.get(block, [])))
        for identifier in ids:
            if identifier in seen:
                raise ValueError(f"duplicate resource or event id {identifier} in {resource.get('symbol', resource.get('name'))}")
            seen.add(identifier)


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other workers produce these art files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def warn_missing_art() -> None:
    for stem in intro.BACKGROUND_IDS:
        warn_if_missing_asset(intro.BACKGROUND_IDS[stem], "backgrounds", f"intro background {stem}")
    warn_if_missing_asset(intro.RAIN_SPRITE_ID, "sprites", "intro rain sprite")
    warn_if_missing_asset(intro.BOLT_SPRITE_ID, "sprites", "intro bolt sprite")
    warn_if_missing_asset(intro.POLE_SPRITE_ID, "sprites", "intro pole sprite")
    warn_if_missing_asset(intro.HERO_SPRITE_ID, "sprites", "intro hero sprite")


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def write_settings(test_start: tuple[str, int, int, str] | None) -> None:
    data = settings_update(test_start)
    contents = json.dumps(data, indent=2) + "\n"
    if SETTINGS_PATH.read_text(encoding="utf-8") != contents:
        SETTINGS_PATH.write_text(contents, encoding="utf-8")
        print("updated settings start fields in project/settings.gbsres")
    else:
        print("unchanged project/settings.gbsres")


def resolve_scene_id(value: str) -> str:
    """A registry folder name (e.g. lab_movement_room) or a raw scene id."""
    if value in scenes.REGISTRY:
        return scenes.REGISTRY[value]["id"]
    return value


def parse_test_start(values: list[str] | None) -> tuple[str, int, int, str] | None:
    if values is None:
        return None
    scene, x, y, direction = values
    if direction not in DIRECTIONS:
        raise SystemExit(f"--test-start direction must be one of {DIRECTIONS}")
    return resolve_scene_id(scene), int(x), int(y), direction


def write_variables() -> None:
    """Register the intro variables without changing any existing entry."""
    path = PROJECT_DIR / "project" / "variables.gbsres"
    data = shared.load_json(path)
    for key, name, symbol in intro.VARIABLES:
        value = {"id": key, "name": name, "symbol": symbol}
        existing = next((v for v in data["variables"] if v["id"] == key), None)
        if existing is not None and existing != value:
            raise ValueError(f"variable {key} is already owned by {existing}")
        if existing is None:
            data["variables"].append(value)
    shared.write_json(path, data)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--test-start", nargs=4, metavar=("SCENE_ID_OR_FOLDER", "X", "Y", "DIRECTION"),
        help="temporary test-ROM start override; SCENE_ID_OR_FOLDER may be a registry folder "
             "name such as lab_movement_room (never commit the settings file)",
    )
    args = parser.parse_args(argv)
    test_start = parse_test_start(args.test_start)

    check_captions()
    built = build_scenes()
    check_unique_ids([scene for scene, _ in built.values()]
                     + [actor for _, actors in built.values() for actor in actors])
    warn_missing_art()

    for path, palette in palette_files():
        shared.write_json(path, palette)
    for folder, (scene, actors) in built.items():
        shared.write_json(SCENES_DIR / folder / "scene.gbsres", scene)
        for actor in actors:
            shared.write_json(SCENES_DIR / folder / "actors" / f"{actor['symbol']}.gbsres", actor)
    write_settings(test_start)
    write_variables()
    if test_start is not None:
        print("WARNING: settings.gbsres now holds a test-start override; do not commit it")
    print(f"generated {len(built)} intro scenes, {len(palette_files())} palettes, "
          f"{len(intro.SHOTS)} shots, {sum(len(a) for _, a in built.values())} story actors")


if __name__ == "__main__":
    main()
