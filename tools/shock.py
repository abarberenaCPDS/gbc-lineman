"""Electrocution beat shared by every scene's hit script (the hero is a lineman).

``shock_events(key)`` returns: hero ``Shock`` sprite state, zap SFX (not
blocking), a 12-frame camera shake plus a 12-frame hold (~0.4 s), then the
hero's default state again. The scene's own respawn events run right after,
so nothing freezes and cable-drop/respawn logic is untouched.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import opening

ROOT = Path(__file__).resolve().parent.parent
SHOCK_SOUND = ROOT / "assets" / "sounds" / "shock.wav.gbsres"
SHAKE_FRAMES = 12   # camera shake blocks the script for this long
SHOCK_FRAMES = 12   # then a short hold: ~0.4 s of Shock in total
SHOCK_ANIM_SPEED = 4
HERO_ANIM_SPEED = 10  # opening_worker24 metadata speed


def sound_id() -> str:
    path = SHOCK_SOUND
    data = json.loads(path.read_text())
    if data.get("_resourceType") != "sound" or not data.get("id"):
        raise ValueError(f"{path} is not a sound resource")
    return data["id"]


def _event(command: str, args: dict[str, Any], key: str) -> dict[str, Any]:
    return {"command": command, "args": args, "id": opening.resource_id(f"event:{key}")}


def shock_events(key: str) -> list[dict[str, Any]]:
    return [
        _event("EVENT_ACTOR_SET_ANIMATION_SPEED",
               {"actorId": "player", "speed": SHOCK_ANIM_SPEED},
               f"{key}:shock-speed"),
        _event("EVENT_ACTOR_SET_STATE",
               {"actorId": "player", "spriteStateId": "Shock", "loopAnim": True},
               f"{key}:shock-state"),
        _event("EVENT_ACTOR_SET_FRAME",
               {"actorId": "player", "frame": {"type": "number", "value": 0}},
               f"{key}:shock-frame"),
        _event("EVENT_SOUND_PLAY_EFFECT", {
            "units": "time", "type": sound_id(), "priority": "high", "pitch": 4,
            "frequency": 200, "duration": 0.5, "wait": False, "effect": 0,
        }, f"{key}:shock-sfx"),
        _event("EVENT_CAMERA_SHAKE",
               {"units": "frames", "frames": SHAKE_FRAMES, "shakeDirection": "horizontal",
                "magnitude": {"type": "number", "value": 2}}, f"{key}:shock-shake"),
        _event("EVENT_WAIT",
               {"units": "frames", "frames": {"type": "number", "value": SHOCK_FRAMES}},
               f"{key}:shock-wait"),
        _event("EVENT_ACTOR_SET_STATE",
               {"actorId": "player", "spriteStateId": "", "loopAnim": True},
               f"{key}:shock-end"),
        _event("EVENT_ACTOR_SET_ANIMATION_SPEED",
               {"actorId": "player", "speed": HERO_ANIM_SPEED},
               f"{key}:shock-speed-restore"),
    ]
