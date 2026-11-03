"""Resolved ending music candidate for the storm report to title handoff."""
from __future__ import annotations

import uuid

import intro

_NAMESPACE = uuid.UUID("ca08ea76-b925-53ef-a38d-5f470462bc62")

NAME = "cfe_ending_reprise"
MUSIC_ID = str(uuid.uuid5(_NAMESPACE, "mr-cfe:ending-reprise:music"))
TITLE_SCENE_ID = intro.TITLE_SCENE_ID
SECTIONS = 2
TICKS_PER_ROW = 4
ROWS_PER_BAR = 16
BAR_SECONDS = ROWS_PER_BAR * TICKS_PER_ROW / intro.MUSIC_TICK_HZ
DURATION_SECONDS = SECTIONS * 4 * BAR_SECONDS

assert MUSIC_ID not in intro.THEME_IDS.values()
assert DURATION_SECONDS == 8
