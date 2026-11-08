"""Logo, intro cinematic and title - deterministic contract (v0.9 front end).

Flow: logo -> intro story (A/START skips) -> title -> Service Opening. All three
are 20x18-tile scenes; the player is hidden in each and every visible
character is an ordinary actor. Only the text-free logo is a LOGO scene: text
drawn in a LOGO scene overwrites background tiles in VRAM (exact ROM a8e4f0ad,
captions corrupted the story's sky and houses), so the story, which draws its
captions on the overlay, is a TOPDOWN scene on a screen-sized map, where the
camera cannot move. The title draws no runtime text at all (see TITLE_ROWS).

The game's start scene (``project/settings.gbsres``) belongs to this module:
``make_intro_scene.py`` writes it from :func:`settings_start`, and no other
active generator may. Test ROMs pass ``--test-start`` to that generator
instead of hand-editing the settings file.

Generators reading this module: ``make_intro_art.py`` (three backgrounds),
``make_intro_sprites.py`` (rain, bolt, pole) and ``make_intro_scene.py``
(scenes, scripts, palettes, settings start).

Units are 8x8 tiles. Actor positions are the sprite canvas's bottom-left tile
(feet row), which is exactly GB Studio's actor tile (checked in exact ROM
c816d5e4: the emulator_inspect OAM view already reports screen pixels). Palette ramps run darkest first, matching
``opening.BG_PALETTES``.
"""

from __future__ import annotations

import uuid as _uuid
from pathlib import Path

import opening
import scenes

TILE = 8
MAP_W, MAP_H = 20, 18
ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"

MAX_CAPTION_CHARS = 17          # generator convention (18 is the hard limit at x=1)
FPS = 60

_INTRO_NAMESPACE = _uuid.UUID("5b1f0c7e-8a2d-5e43-9c61-7d0e3a4b2f98")


def resource_id(key: str) -> str:
    """Stable IDs for every resource the intro generates."""
    return str(_uuid.uuid5(_INTRO_NAMESPACE, "mr-cfe:intro:" + key))


def read_version() -> str:
    """SemVer tag shown on the title, e.g. ``v0.9.0-dev``."""
    return "v" + VERSION_FILE.read_text().strip()


def dev_label() -> str | None:
    """The version for on-screen display in dev builds; None for releases.

    Abe (2026-10-27): dev builds must say so on screen, and test builds often
    start mid-game, so the title's version tag is never seen.
    """
    version = read_version()
    return version if "-dev" in version else None


HUD_COLUMNS = 20


def dev_hud_events(event, key: str) -> list[dict]:
    """Right-aligned dev label on the HUD's second row (empty in releases).

    ``event(command, args, key)`` is the calling scene's builder, so the event
    ID stays in that scene's namespace.
    """
    label = dev_label()
    if label is None:
        return []
    return [event("EVENT_TEXT_DRAW",
                  {"text": label, "x": HUD_COLUMNS - len(label), "y": 1, "location": "overlay"},
                  f"{key}:dev-label")]


# ---------------------------------------------------------------------------
# Scenes (editor placement above the job row; indices after Pine Hollow's 6)
# ---------------------------------------------------------------------------
LOGO_SCENE_ID = resource_id("scene:logo")
STORY_SCENE_ID = resource_id("scene:story")
TITLE_SCENE_ID = resource_id("scene:title")
SCENES = [
    # (scene id, folder, name, background file stem, index, editor x, y)
    (LOGO_SCENE_ID, "intro_logo", "Abe's Games Logo", "intro_logo", 7, *scenes.editor_position("intro_logo")),
    (STORY_SCENE_ID, "intro_story", "Intro Story", "intro_story", 8, *scenes.editor_position("intro_story")),
    (TITLE_SCENE_ID, "title", "Title", "title", 9, *scenes.editor_position("title")),
]
# The title is TOPDOWN too: as a LOGO scene, its high background tiles (the
# baked text band) were overwritten by engine UI tiles (exact ROM 3eb072a3).
SCENE_TYPES = {LOGO_SCENE_ID: "LOGO", STORY_SCENE_ID: "TOPDOWN", TITLE_SCENE_ID: "TOPDOWN"}
BACKGROUND_IDS = {stem: resource_id(f"background:{stem}") for _, _, _, stem, *_ in SCENES}

# Where START on the title sends the player.
OPENING_SCENE_ID = opening.resource_id("scene:service-opening")
OPENING_START = opening.START            # Tutorial contract owns the arrival.
OPENING_DIRECTION = "right"
FADE_SPEED = "2"


def settings_start(test_start: tuple[str, int, int, str] | None = None) -> dict:
    """Fields this module owns in ``project/settings.gbsres``.

    The release start is the logo. ``test_start`` = (scene id, x, y, direction)
    is a temporary test-ROM override; never commit a settings file built with it.
    """
    scene, x, y, direction = test_start or (LOGO_SCENE_ID, 0, 0, "right")
    return {"startSceneId": scene, "startX": x, "startY": y, "startDirection": direction}


# ---------------------------------------------------------------------------
# Music and the dialogue "voice"
#
# Three intro-theme candidates (tools/compose_intro.py). The story (re)starts
# the chosen theme on its first shot, every pass, and it plays on into the
# title; the logo is silent. The opening
# starts its own track. Until Abe picks one, SELECT on the title auditions the
# next candidate (VAR_THEME holds the index).
# ---------------------------------------------------------------------------
THEMES = ("a", "b", "c")
THEME_FILES = {key: f"cfe_intro_{key}" for key in THEMES}
THEME_IDS = {key: resource_id(f"music:intro-{key}") for key in THEMES}
DEFAULT_THEME = "b"             # Abe: "let's try option B" (A and C stay on disk)
AUDITION_THEMES = False         # True: SELECT on the title cycles the candidates
VAR_THEME = "14"
# Music clock: GB Studio's timer ISR runs hUGE at 64 Hz, the screen at
# 59.7275 Hz. Theme B (tpr 4) plays one 16-row bar per second, and each shot
# is one 4-bar section, so section n of the song starts with shot n.
MUSIC_TICK_HZ = 64
FRAME_HZ = 59.7275
THEME_TPR = 4
BAR_ROWS = 16
SHOT_BARS = 4
SHOT_FRAMES = round(SHOT_BARS * BAR_ROWS * THEME_TPR / MUSIC_TICK_HZ * FRAME_HZ)  # 239
# Measured script cost per shot (caption draw + cues): the hero shot began 36
# frames late after 7 shots on exact ROM d44b642e. Each shot's waits leave it out.
SHOT_OVERHEAD_FRAMES = 5
VARIABLES = [(VAR_THEME, "Intro Theme", "var_intro_theme")]
# EVENT_TEXT_SET_SOUND_EFFECT, set once at boot: a short square-wave blip for
# every typed character, so dialogue "speaks". It persists across scenes.
TEXT_SOUND = {"type": "tone", "frequency": 880, "duration": 0.03, "units": "time"}

# ---------------------------------------------------------------------------
# Shared palettes
# ---------------------------------------------------------------------------
_OPENING = dict(opening.BG_PALETTES)
NIGHT = _OPENING["night"]
STONE = _OPENING["stone"]
TIMBER = _OPENING["timber"]
FOLIAGE = _OPENING["foliage"]
METAL = _OPENING["metal"]
WINDOW_DARK = _OPENING["window"]
WINDOW_LIT = opening.POWERED_WINDOW
GOLD = ["0B101E", "5A3A1E", "C38849", "F1D49A"]       # logo / warm lettering
# BG slot 7 (UI): text draws and the caption overlay. Index 0 is the text
# background (matches the scenes' dark text bands), index 3 the letters.
UI = ["0B101E", "2C4054", "8FA3B8", "F2E6C9"]
PRESS_OFF = [UI[0]] * 4      # the title's PRESS START slot, blinked off

# Story sky (BG slot 0) variants, swapped shot by shot.
SKY_DUSK = ["2A1E3A", "6B3F5E", "D9805A", "F2C27A"]
SKY_STORM = ["0A0E18", "161F2E", "2A3648", "4A5868"]
SKY_FLASH = ["5A6E8A", "A8B8D0", "E0E8F4", "FFFFFF"]
SKY_MORNING = ["2E3438", "565E64", "8A9298", "BCC2C4"]

BG_PALETTES = {
    # name -> colours. make_intro_scene.py writes one palette resource each,
    # id = resource_id(f"palette:bg:{name}").
    "night": NIGHT, "gold": GOLD, "ui": UI,
    "sky_dusk": SKY_DUSK, "sky_storm": SKY_STORM,
    "sky_flash": SKY_FLASH, "sky_morning": SKY_MORNING,
    "foliage": FOLIAGE, "timber": TIMBER, "stone": STONE, "metal": METAL,
    "window_lit": WINDOW_LIT, "window_dark": WINDOW_DARK, "press_off": PRESS_OFF,
}


def palette_id(name: str) -> str:
    assert name in BG_PALETTES or name in SPRITE_PALETTES, name
    kind = "bg" if name in BG_PALETTES else "sprite"
    return resource_id(f"palette:{kind}:{name}")


# Per-scene BG slots 0-7 at scene start (slot 7 is always UI).
LOGO_SLOTS = ["night", "gold", "night", "night", "night", "night", "night", "ui"]
STORY_SLOTS = ["sky_dusk", "foliage", "timber", "window_lit", "window_lit",
               "window_lit", "stone", "ui"]
TITLE_SLOTS = ["night", "gold", "metal", "foliage", "window_lit", "ui", "ui", "ui"]
VERSION_SLOT = 5                # title version tag, baked into the art
PRESS_SLOT = 6                  # title PRESS START, blinked by swapping ui/press_off
SKY_SLOT = 0
WINDOW_SLOTS = (3, 4, 5)       # one per house, darkened one by one in shot 4

# ---------------------------------------------------------------------------
# Logo: "ABE'S GAMES / PRESENT" baked into the art, held ~2 s, then fade.
# ---------------------------------------------------------------------------
LOGO_TEXT_ROWS = {"ABE'S GAMES": (6, 9), "PRESENT": (11, 12)}   # inclusive tile rows
LOGO_HOLD_FRAMES = 120

# ---------------------------------------------------------------------------
# Story background layout (rows 14-17 sit under the caption overlay)
# ---------------------------------------------------------------------------
HORIZON_ROW = 9                 # sky above, hill/houses from here down
GROUND_ROW = 14                 # feet stand on row 13
# Houses: (x0, x1, roof_row, base_row, window tiles, window BG slot)
# Each house's left tile holds its door; a power pole stands right of each house.
HOUSES = [
    (0, 3, 9, 13, [(1, 11), (2, 11)], 3),
    (6, 9, 8, 13, [(7, 10), (8, 10)], 4),
    (12, 15, 9, 13, [(13, 11), (14, 11)], 5),
]
CAPTION_OVERLAY = (0, 14)       # EVENT_OVERLAY_SHOW x, y (tiles); 4 rows tall
CAPTION_TEXT = (1, 1)           # EVENT_TEXT_DRAW x, y inside the overlay
CAPTION_OVERLAY_COLOR = "white"  # fills with UI index 0 (dark): verify in build

# ---------------------------------------------------------------------------
# Story actors and sprites (OBJ palette slots in brackets)
# ---------------------------------------------------------------------------
# The hero uses independent native cels and a fixed-type intro sprite.
# The classic variant preserves the original pixels, independent of gameplay.
HERO_VARIANTS = ("neighborhood", "classic")
DEFAULT_HERO_VARIANT = "neighborhood"
NEIGHBORHOOD_HERO_SPRITE_ID = resource_id("sprite:neighborhood_hero")
HERO_SPRITE_ID = resource_id("sprite:intro_hero")       # 16x32, states below
HERO_STATES = {"Idle": [0, 16], "Walk": [96, 112, 128, 144]}   # facing right
HERO_ENTER = (0, 13)            # hidden until shot 7
HERO_STOP = (18, 13)            # walks past every snapped pole, faces up the hill
HERO_SIZE = (2, 4)              # tiles (w, h) of the 16x32 canvas
HERO_MOVE_SPEED = 1             # px per frame (actor moveSpeed 1)
# The walk blocks the story thread; the hero shot's waits leave this much out.
HERO_WALK_FRAMES = (HERO_STOP[0] - HERO_ENTER[0]) * 8 // HERO_MOVE_SPEED

RAIN_SPRITE_ID = resource_id("sprite:intro_rain")     # 16x16, state Default, loops
BOLT_SPRITE_ID = resource_id("sprite:intro_bolt")     # 16x32, state Default
POLE_SPRITE_ID = resource_id("sprite:intro_pole")     # 16x32, Standing / Snapped+Cable / Snapped
POLE_STATES = ["Standing", "Snapped+Cable", "Snapped"]
SPRITE_SIZES = {RAIN_SPRITE_ID: (2, 2), BOLT_SPRITE_ID: (2, 4),
                POLE_SPRITE_ID: (2, 4), HERO_SPRITE_ID: HERO_SIZE}

RAIN = [(1, 3), (6, 5), (12, 2), (16, 4), (3, 8), (7, 7), (14, 8), (18, 6)]
POLES = [(4, 13), (10, 13), (16, 13)]   # one right of each house
POLE = POLES[1]                 # the pole the lightning strikes
BOLT = (POLE[0], 9)             # canvas bottom meets the pole's canvas top
SNAP_GAP = 12                   # frames between the poles snapping (struck pole first)

SPRITE_PALETTES = {
    # hardware colours, index 0 transparent
    "worker": opening.SPRITE_PALETTES[0][1],
    "rain": ["000000", "C7DCE1", "7791A3", "2C4054"],
    "bolt": ["000000", "FFFFFF", "F1E27A", "A8B8D0"],
    "pole": ["000000", "F1C879", "8A6A48", "2B2420"],
}
SPRITE_SLOTS = {"worker": 0, "rain": 1, "bolt": 2, "pole": 7}  # pole: the only OBJ slot free in every job scene

# ---------------------------------------------------------------------------
# Shots: (caption lines, frames). Effects per shot live in make_intro_scene.
# ---------------------------------------------------------------------------
SHOTS = [
    ("dusk", ["A quiet evening", "on the hill..."], SHOT_FRAMES),
    ("storm", ["Then a tropical", "storm rolled in."], SHOT_FRAMES),
    ("lightning", ["Lightning struck.", "Ferocious winds."], SHOT_FRAMES),
    ("snap", ["Poles snapped.", "The lines fell."], SHOT_FRAMES),
    ("morning", ["The storm passed.", "The power didn't."], SHOT_FRAMES),
    ("dark", ["Without power:", "no hot meals,"], SHOT_FRAMES),
    ("offline", ["no medical gear,", "no internet."], SHOT_FRAMES),
    ("hero", ["One lineman.", "One mission:"], SHOT_FRAMES),
    ("mission", ["Bring the power", "back home."], SHOT_FRAMES),
]
FLASH_FRAMES = 6                # each lightning flash
WINDOW_OFF_GAP = 50             # frames between houses going dark in shot 4
SHAKE_FRAMES = 45
SHAKE_MAGNITUDE = 3
# Thunder: built-in noise "crash" SFX as (shot, frame offset, seconds). A
# distant rumble as the storm rolls in, then a near double strike.
THUNDER = [("storm", 30, 0.8), ("storm", 150, 0.5),
           ("lightning", 30, 1.2), ("lightning", 80, 1.5), ("snap", 0, 0.6)]
STRIKES = [30, 80]              # lightning-shot frames: bolt, flash, shake


def caption_text(lines: list[str]) -> str:
    """Caption padded to a fixed box so each draw fully overwrites the last."""
    return "\n".join(line.ljust(MAX_CAPTION_CHARS) for line in lines)


# ---------------------------------------------------------------------------
# Title: everything is baked into the art, including the version tag read
# from VERSION at generation time. EVENT_TEXT_DRAW on this background garbled
# the text and stalled the blink loop (exact ROMs 7f850ff5, 8125c692), so
# PRESS START blinks by swapping its own BG slot between "ui" and "press_off".
# ---------------------------------------------------------------------------
TITLE_ROWS = {                  # inclusive tile rows painted in the art
    "ABE'S GAMES PRESENT": (1, 1),
    "MR CFE": (3, 8),
    "After the Storm": (10, 11),
}
TEXT_BAND_ROWS = (13, 17)       # flat UI[0] band
PRESS_START = "PRESS START"
PRESS_START_ROW = 14            # centred, PRESS_SLOT
VERSION_ROW = 16                # right-aligned, VERSION_SLOT
COPYRIGHT = "\u00a92026 ABE'S GAMES"
COPYRIGHT_ROW = 17              # centred, VERSION_SLOT
BLINK_FRAMES = 30               # on, then off, repeating
# Attract loop (Abe, 2026-10-26: "the intro should loop the storm cinematic"):
# PRESS START blinks this many times, then the title fades back into the story,
# whose end returns to the title.
TITLE_IDLE_BLINKS = 15         # 15 x (30 on + 30 off) = 15 s


# ---------------------------------------------------------------------------
def _scanline_peak(actors: list[tuple[str, tuple[int, int]]]) -> int:
    """Worst OBJ count on any 8px row if every listed actor were visible."""
    peak = 0
    for row in range(MAP_H):
        count = 0
        for sprite, (x, y) in actors:
            w, h = SPRITE_SIZES[sprite]
            if y - h + 1 <= row <= y:
                count += w          # one 8x16 OBJ per 8px column
        peak = max(peak, count)
    return peak


def story_actors() -> list[tuple[str, tuple[int, int]]]:
    return ([(RAIN_SPRITE_ID, p) for p in RAIN]
            + [(BOLT_SPRITE_ID, BOLT)] + [(POLE_SPRITE_ID, p) for p in POLES]
            + [(HERO_SPRITE_ID, HERO_STOP)])


def _self_check() -> None:
    for _, lines, frames in SHOTS:
        assert len(lines) == 2 and all(len(l) <= MAX_CAPTION_CHARS for l in lines), lines
        assert frames == SHOT_FRAMES, "one 4-bar music section per shot"
    assert len(SHOTS) == 9 and len({name for name, _, _ in SHOTS}) == 9
    assert all(len(slots) == 8 and slots[7] == "ui"
               for slots in (LOGO_SLOTS, STORY_SLOTS, TITLE_SLOTS))
    assert {h[5] for h in HOUSES} == set(WINDOW_SLOTS)
    for x0, x1, roof, base, windows, _ in HOUSES:
        assert 0 <= x0 < x1 < MAP_W and roof < base < GROUND_ROW
        assert all(x0 <= x <= x1 and roof < y < base for x, y in windows)
    spans = sorted((h[0], h[1]) for h in HOUSES)
    assert all(a[1] < b[0] for a, b in zip(spans, spans[1:])), "houses overlap"
    for px, py in POLES:
        assert py == GROUND_ROW - 1
        assert all(not (x0 <= px + dx <= x1) for x0, x1, *_ in HOUSES for dx in (0, 1))
    pole_cols = sorted(x + dx for x, _ in POLES for dx in (0, 1))
    assert len(pole_cols) == len(set(pole_cols)), "poles overlap"
    assert all(win[0] != h[0] for h in HOUSES for win in h[4]), "windows off the door tile"
    assert all(shot in {n for n, _, _ in SHOTS} for shot, _, _ in THUNDER)
    assert all(0 < secs <= 2 for _, _, secs in THUNDER)
    assert all(b - a > SHAKE_FRAMES for a, b in zip(STRIKES, STRIKES[1:])), "strikes overlap"
    assert BOLT[0] == POLE[0] and BOLT[1] == POLE[1] - SPRITE_SIZES[POLE_SPRITE_ID][1], (
        "bolt strikes the pole top")
    assert all(p[0] < MAP_W and p[1] < MAP_H for _, p in story_actors()), "inside the map"
    assert HERO_STOP[1] == GROUND_ROW - 1 == HERO_ENTER[1]
    assert all(y < CAPTION_OVERLAY[1] for _, (_, y) in story_actors()), "actors above captions"
    assert all(0 <= x and x + SPRITE_SIZES[s][0] <= MAP_W for s, (x, _) in story_actors())
    assert _scanline_peak(story_actors()) <= 10, "over 10 OBJs on a scanline"
    assert CAPTION_OVERLAY[1] + CAPTION_TEXT[1] + 1 < MAP_H
    lo, hi = TEXT_BAND_ROWS
    version = read_version()
    assert lo <= PRESS_START_ROW < VERSION_ROW < COPYRIGHT_ROW <= hi
    assert all(r[1] < lo for r in TITLE_ROWS.values())
    assert version.startswith("v") and version.count(".") >= 2
    assert TITLE_SLOTS[PRESS_SLOT] == TITLE_SLOTS[VERSION_SLOT] == "ui"
    assert PRESS_OFF[0] == UI[0], "blinked-off text must match the band"
    ids = {LOGO_SCENE_ID, STORY_SCENE_ID, TITLE_SCENE_ID, *BACKGROUND_IDS.values(),
           RAIN_SPRITE_ID, BOLT_SPRITE_ID, POLE_SPRITE_ID}
    assert len(ids) == 9, "resource ids collide"
    assert LOGO_HOLD_FRAMES >= 100
    assert 180 <= SHOT_FRAMES <= 240, "shots run 3-4 s"
    assert HERO_WALK_FRAMES < SHOT_FRAMES, "the walk fits inside the hero shot"
    assert DEFAULT_THEME in THEMES and len(set(THEME_IDS.values())) == len(THEMES)
    assert 0 < TEXT_SOUND["duration"] <= 0.05, "a blip, not a beep"


_self_check()
