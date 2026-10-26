#!/usr/bin/env python3
"""Who is talking: speaker names and per-character text blips.

Abe on the cart (2026-10-26): dialogue did not say who was speaking. A
character's page starts with its name on its own line ("Marta:"), so the two
17-char lines below it keep their width, and the typed-character blip
(EVENT_TEXT_SET_SOUND_EFFECT) switches to that character's pitch for the box.
Unnamed boxes are narration and hints in the narrator blip (intro.TEXT_SOUND),
which every voiced box restores afterwards because the blip persists.
"""

from __future__ import annotations

from typing import Any

import intro

MAX_LINES = 3  # name + two lines fits the smallest in-play box (opening: textHeight 3)

# name shown in the box, blip frequency in Hz (narrator is 880)
SPEAKERS: dict[str, tuple[str, int]] = {
    "marta": ("Marta", 660),   # warm, middle
    "tomas": ("Tomas", 440),   # oldest, lowest
    "rosa": ("Rosa", 990),     # quick, bright
    "kiko": ("Kiko", 1320),    # the kid, highest
}


def name(speaker: str) -> str:
    return SPEAKERS[speaker][0]


def labeled(speaker: str, pages: list[str]) -> list[str]:
    """Prefix every page with the speaker's name line."""
    label = f"{name(speaker)}:"
    result = []
    for page in pages:
        text = f"{label}\n{page}"
        if text.count("\n") + 1 > MAX_LINES:
            raise ValueError(f"{speaker} page has too many lines for the box: {page!r}")
        result.append(text)
    return result


def sound_args(speaker: str | None) -> dict[str, Any]:
    """EVENT_TEXT_SET_SOUND_EFFECT args; None is the narrator."""
    args = dict(intro.TEXT_SOUND)
    if speaker is not None:
        args["frequency"] = SPEAKERS[speaker][1]
    return args


def check() -> None:
    frequencies = [hz for _, hz in SPEAKERS.values()] + [intro.TEXT_SOUND["frequency"]]
    assert len(set(frequencies)) == len(frequencies), "each voice needs its own pitch"
    assert all(200 <= hz <= 2000 for hz in frequencies), "blips stay in a pleasant range"
    assert all(len(f"{name}:") <= 17 for name, _ in SPEAKERS.values())


check()
