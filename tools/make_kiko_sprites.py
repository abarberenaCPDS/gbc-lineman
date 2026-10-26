"""Generate Kiko and the family's electric stove for the Pine Hollow repair job.

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_kiko_sprites.py

This generator owns only ``assets/sprites/kiko.png`` and ``assets/sprites/kiko_stove.png``
plus their native GB Studio sidecars. Stable IDs, the sprite palette slots, the hardware
colours and the state names come from ``tools/kiko.py``. The live arc is Rosa's
``live_arc`` and is not generated here.

Art is drawn from ASCII rows: ``.`` is transparent, and ``1``, ``2``, ``3`` are the three
opaque proxy colours (white, gray 160, black). Proxy index N maps to hardware index N of
the palette the scene worker builds: ``kiko.KIKO_SPRITE_HARDWARE`` for Kiko and the grid
sprite palette for the stove. Index 0 is always transparent. Both sheets stand on the
shared feet row 15, like the other 8x16 sprites in this job.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
OUT_DIR = ROOT / "assets" / "sprites"
sys.path.insert(0, str(TOOLS_DIR))
import kiko  # noqa: E402

CANVAS = 16
ENGINE_SLOTS = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {
    1: (255, 255, 255, 255),  # hardware index 1
    2: (160, 160, 160, 255),  # hardware index 2
    3: (0, 0, 0, 255),        # hardware index 3
}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}

# Grid sprite palette (slot kiko.GRID_SPRITE_PALETTE_SLOT). Kept in step with
# make_climb_scene.GRID_SPRITE_HARDWARE; test_kiko_sprites.py cross-checks it.
GRID_SPRITE_HARDWARE = ["000000", "C7DCE1", "38C8D8", "142332"]
MAX_ACCENT_PIXELS = 4  # the cyan accent is reserved for small lights and airflow

EMPTY = "." * CANVAS

# ---------------------------------------------------------------------------
# Row helpers. Each takes a 10-pixel inner span (x3..x12 for the head and torso),
# so the head, jacket and arms line up on the same centre line.
# ---------------------------------------------------------------------------


def _head(inner: str) -> str:
    assert len(inner) == 10, inner
    return "..." + inner + "..."


def _torso(inner: str) -> str:
    """Mustard jacket with a dark outline on the left side (x2) and right (x13)."""
    assert len(inner) == 10, inner
    return "..3" + inner + "3.."


def _torso_arm_up(inner: str) -> str:
    """Jacket with the right arm raised: sleeve at x14, outline at x13 and x15."""
    assert len(inner) == 10, inner
    return "..3" + inner + "323"


# ---------------------------------------------------------------------------
# Kiko: a child, front view, on a 16x32 canvas like the 24px adults (8x16 sprite mode),
# figure 20 rows tall standing on canvas row 31. Rows below are the 20 figure rows; the
# 12 empty rows above are added by _kiko_frame. Taller than the old 16px kid, shorter
# than the 24px adults. Eyes are two dark pixels stacked on skin (never a band); the
# only blink is one idle frame where the eyes close to a single dark pixel row.
# 1 = skin, 2 = mustard-yellow jacket, 3 = hair, outline, trousers, shoes, bowl rim.
# Waiting (hungry): an empty bowl held at the belly, open mouth, eyes open (A) or blinking (B).
# Relieved (happy): a grin, the bowl raised in the right hand; B closes the eyes, lifts a foot.
# ---------------------------------------------------------------------------
KIKO_CANVAS_H = 32
KIKO_FIGURE_H = 20


def _kiko_frame(figure: list[str]) -> list[str]:
    assert len(figure) == KIKO_FIGURE_H, len(figure)
    return [EMPTY] * (KIKO_CANVAS_H - KIKO_FIGURE_H) + figure


def _arm(inner: str) -> str:
    """Head row with the raised right arm: sleeve at x14, outline at x15."""
    return "..." + inner + ".23"


_TUFTS = "....3.33.3.3...."
_CAP = _head("3333333333")
_FOREHEAD = _head("3311111133")
_EYES = _head("3113113113")
_CHEEKS = _head("3111111113")
_MOUTH_OPEN = _head("3111331113")
_GRIN = _head("3113333113")
_CHIN = _head("3111111113")
_JAW = "....33111133...."
_LEGS = "....33....33...."
_FEET = "...333....333..."
_FEET_LIFTED = "...33.....333..."

_WAIT_BOWL_RIM = "2223333222"
_WAIT_BOWL_BASE = "2231111322"
_WAIT_BOWL_RIM_B = "2222333322"
_WAIT_BOWL_BASE_B = "2223111132"
_JACKET = "2222222222"
_JACKET_ZIP = "2222322222"

_BOWL_TOP = "............3333"
_BOWL_MID = "............3113"


def _wait(blink: bool) -> list[str]:
    rim, base = ((_WAIT_BOWL_RIM_B, _WAIT_BOWL_BASE_B) if blink
                 else (_WAIT_BOWL_RIM, _WAIT_BOWL_BASE))
    return _kiko_frame([
        _TUFTS,                                  # 0
        _CAP,                                    # 1
        _CAP,                                    # 2
        _FOREHEAD,                               # 3
        _CHEEKS if blink else _EYES,             # 4 eyes (open), skin when blinking
        _EYES,                                   # 5 eyes (a single dark row when blinking)
        _CHEEKS,                                 # 6
        _MOUTH_OPEN,                             # 7 hungry open mouth
        _CHIN,                                   # 8
        _JAW,                                    # 9
        _torso(_JACKET),                         # 10
        _torso(_JACKET_ZIP),                     # 11
        _torso(_JACKET),                         # 12
        _torso(rim),                             # 13 empty bowl at the belly
        _torso(base),                            # 14
        _torso(_JACKET),                         # 15
        _LEGS,                                   # 16
        _LEGS,                                   # 17
        _LEGS,                                   # 18
        _FEET,                                   # 19
    ])


def _overlay(base: str, over: str) -> str:
    return "".join(o if o != "." else b for b, o in zip(base, over))


def _relieved(shut: bool) -> list[str]:
    return _kiko_frame([
        _overlay(_TUFTS, _BOWL_TOP),             # 0 bowl raised above the head
        _overlay(_CAP, _BOWL_MID),               # 1
        _arm("3333333333"),                      # 2
        _arm("3311111133"),                      # 3
        _arm("3111111113" if shut else "3113113113"),   # 4
        _arm("3113113113"),                      # 5 eyes (closed: one dark row)
        _arm("3111111113"),                      # 6
        _arm("3113333113"),                      # 7 grin
        _arm("3111111113"),                      # 8
        "....33111133..23",                      # 9
        _torso_arm_up(_JACKET),                  # 10
        _torso_arm_up(_JACKET_ZIP),              # 11
        _torso_arm_up(_JACKET),                  # 12
        _torso_arm_up(_JACKET),                  # 13
        _torso_arm_up(_JACKET),                  # 14
        _torso_arm_up(_JACKET),                  # 15
        _LEGS,                                   # 16
        _FEET_LIFTED if shut else _LEGS,         # 17
        _LEGS,                                   # 18
        _FEET,                                   # 19
    ])


KIKO_WAIT_A = _wait(False)
KIKO_WAIT_B = _wait(True)
KIKO_REL_A = _relieved(False)
KIKO_REL_B = _relieved(True)
KIKO_FRAMES = [KIKO_WAIT_A, KIKO_WAIT_B, KIKO_REL_A, KIKO_REL_B]
KIKO_STATE_FRAMES = {"Waiting": [0, 1], "Relieved": [2, 3]}

# ---------------------------------------------------------------------------
# Electric stove with a pot, on the porch: a shared grid sprite like the workstation and
# the concentrator. 1 = pale housing, 2 = cyan airflow and burner glow (grid accent),
# 3 = dark outline. Off: cold burners (dark rings), no steam. On: a two-frame loop where
# the lit burner and the steam puff alternate: A has the left burner glowing and a low
# steam puff, B has the right burner glowing and the puff rising one row higher.
# ---------------------------------------------------------------------------


# Pot and stove body, rim to cooktop (rows 2-7), shared by every frame.
_POT_TO_COOKTOP = [
    "....3333333333..",          # 2 pot rim
    "....3111111113..",          # 3 pot wall
    "....3111111113..",          # 4 pot wall
    "....3333333333..",          # 5 pot base
    "..333333333333..",          # 6 stove top edge
    "..3" + "1" * 10 + "3..",    # 7 cooktop
]
# Oven and feet (rows 9-15), shared by every frame.
_STOVE_LOWER = [
    "..3" + "1131111311" + "3..",  # 9 control panel with two knobs
    "..3" + "1111111111" + "3..",  # 10 panel
    "..3" + "3333333333" + "3..",  # 11 oven door top edge
    "..3" + "1111111111" + "3..",  # 12 oven window
    "..3" + "1111111111" + "3..",  # 13 oven window
    "..3" + "3333333333" + "3..",  # 14 oven door bottom edge
    "...33......33...",            # 15 feet on the shared feet row
]
# Burner rings sit on row 8 at x4-5 and x10-11. Cold: dark rings. Lit: cyan glow.
_BURNER_OFF = "1331111331"
_BURNER_LEFT_GLOW = "1221111331"
_BURNER_RIGHT_GLOW = "1331111221"


def _stove_frame(steam: tuple[str, str], burner_inner: str) -> list[str]:
    """A 16-row stove: steam on rows 0-1, pot and cooktop 2-7, burners 8, oven 9-15."""
    frame = [steam[0], steam[1], *_POT_TO_COOKTOP, "..3" + burner_inner + "3..", *_STOVE_LOWER]
    assert len(frame) == CANVAS, len(frame)
    return frame


# Off: cold, no steam. On: the two-frame loop alternates the glowing burner and the
# steam puff: A glows the left burner with a low puff, B glows the right burner and the
# puff has risen a row. Accent pixels per frame: A 4, B 3 (budget MAX_ACCENT_PIXELS).
STOVE_OFF = _stove_frame((EMPTY, EMPTY), _BURNER_OFF)
STOVE_ON_A = _stove_frame((EMPTY, "......2.2......."), _BURNER_LEFT_GLOW)
STOVE_ON_B = _stove_frame((".......2........", EMPTY), _BURNER_RIGHT_GLOW)
STOVE_FRAMES = [STOVE_OFF, STOVE_ON_A, STOVE_ON_B]
STOVE_STATE_FRAMES = {"Off": [0], "On": [1, 2]}

# ---------------------------------------------------------------------------
# Rendering and sidecars
# ---------------------------------------------------------------------------


def _render(rows: list[str]) -> Image.Image:
    height = len(rows)
    if height not in (CANVAS, KIKO_CANVAS_H):
        raise ValueError(f"expected {CANVAS} or {KIKO_CANVAS_H} rows, got {height}")
    image = Image.new("RGBA", (CANVAS, height), TRANSPARENT)
    for y, row in enumerate(rows):
        if len(row) != CANVAS:
            raise ValueError(f"row {y} has width {len(row)}, expected {CANVAS}")
        for x, glyph in enumerate(row):
            if glyph not in GLYPH:
                raise ValueError(f"unknown glyph {glyph!r} at {x},{y}")
            image.putpixel((x, y), GLYPH[glyph])
    return image


def _sheet(frames: list[Image.Image]) -> Image.Image:
    result = Image.new("RGBA", (CANVAS * len(frames), frames[0].height), TRANSPARENT)
    for index, frame in enumerate(frames):
        result.paste(frame, (index * CANVAS, 0))
    return result


def _is_opaque(pixel: tuple[int, int, int, int]) -> bool:
    return pixel[3] != 0


def _bounds(sheet: Image.Image) -> tuple[int, int, int, int]:
    """Tight bounds over every frame, using the worker sidecars' origin (canvas bottom - 8)."""
    xs: list[int] = []
    ys: list[int] = []
    for y in range(sheet.height):
        for x in range(sheet.width):
            if _is_opaque(sheet.getpixel((x, y))):
                xs.append(x % CANVAS)
                ys.append(y)
    if not xs:
        raise AssertionError("sprite has no opaque pixels")
    origin = sheet.height - 8
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    return (left, top - origin, right - left + 1, bottom - top + 1)


def _rid(name: str, key: str) -> str:
    return kiko.resource_id(f"{name}:{key}")


def _sidecar(
    name: str,
    sprite_id: str,
    sheet: Image.Image,
    states: list[tuple[str, list[int]]],
    palette_index: int,
    anim_speed: int,
) -> dict:
    height = sheet.height
    state_data: list[dict] = []
    tile_signatures: set[bytes] = set()
    for state_index, (state_name, frame_indices) in enumerate(states):
        animations: list[dict] = []
        for animation_index in range(ENGINE_SLOTS):
            # Only the first slot plays; the rest stay empty like the other sprite sidecars.
            authored = frame_indices if animation_index == 0 else []
            animation_frames: list[dict] = []
            for animation_frame_index, frame_index in enumerate(authored):
                frame_x = frame_index * CANVAS
                tiles: list[dict] = []
                for slice_y in range(0, height, 16):
                    for x in range(0, CANVAS, 8):
                        crop = sheet.crop((frame_x + x, slice_y, frame_x + x + 8, slice_y + 16))
                        if not any(_is_opaque(pixel) for pixel in crop.get_flattened_data()):
                            continue
                        key = (f"state:{state_index}:animation:{animation_index}:"
                               f"frame:{animation_frame_index}:object:{x}")
                        if slice_y:
                            pass  # the bottom 16 rows keep the original 16px tile ids
                        elif height > 16:
                            key += ":top"
                        tiles.append({
                            "id": _rid(name, key + ":tile"),
                            "x": x,
                            # tile y counts UP from the canvas bottom (GB Studio)
                            "y": height - 16 - slice_y,
                            "sliceX": frame_x + x,
                            "sliceY": slice_y,
                            "flipX": False,
                            "flipY": False,
                            "palette": 0,
                            "paletteIndex": palette_index,
                            "objPalette": "OBP0",
                            "priority": False,
                        })
                        tile_signatures.add(bytes(
                            _shade(pixel) for pixel in crop.get_flattened_data()))
                frame_key = f"state:{state_index}:animation:{animation_index}:frame:{animation_frame_index}"
                animation_frames.append({"id": _rid(name, frame_key), "tiles": tiles})
            if not animation_frames:
                blank = f"state:{state_index}:animation:{animation_index}:empty-frame"
                animation_frames.append({"id": _rid(name, blank), "tiles": []})
            animations.append({
                "id": _rid(name, f"state:{state_index}:animation:{animation_index}"),
                "frames": animation_frames,
            })
        state_data.append({
            "id": _rid(name, f"state:{state_index}"),
            "name": state_name,
            "animationType": "fixed",
            "flipLeft": False,
            "animations": animations,
        })

    bounds = _bounds(sheet)
    return {
        "_resourceType": "sprite",
        "id": sprite_id,
        "name": name,
        "symbol": f"sprite_{name}",
        "filename": f"{name}.png",
        "width": sheet.width,
        "height": sheet.height,
        "checksum": "",
        "numTiles": len(tile_signatures),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": CANVAS,
        "canvasHeight": height,
        "boundsX": bounds[0],
        "boundsY": bounds[1],
        "boundsWidth": bounds[2],
        "boundsHeight": bounds[3],
        "animSpeed": anim_speed,
        "spriteMode": "8x16",
        "states": state_data,
    }


def _shade(pixel: tuple[int, int, int, int]) -> int:
    if pixel[3] == 0:
        return 0
    for index, proxy in PROXY.items():
        if pixel == proxy:
            return index
    raise ValueError(f"non-proxy pixel {pixel}")


def _kiko_asset() -> tuple[str, Image.Image, dict]:
    name = "kiko"
    sheet = _sheet([_render(rows) for rows in KIKO_FRAMES])
    states = [(state, KIKO_STATE_FRAMES[state]) for state in kiko.KIKO_STATES]
    meta = _sidecar(name, kiko.KIKO_SPRITE_ID, sheet, states,
                    kiko.KIKO_SPRITE_PALETTE_SLOT, anim_speed=20)
    return name, sheet, meta


def _stove_asset() -> tuple[str, Image.Image, dict]:
    name = "kiko_stove"
    sheet = _sheet([_render(rows) for rows in STOVE_FRAMES])
    states = [(state, STOVE_STATE_FRAMES[state]) for state in kiko.STOVE_STATES]
    meta = _sidecar(name, kiko.STOVE_SPRITE_ID, sheet, states,
                    kiko.GRID_SPRITE_PALETTE_SLOT, anim_speed=12)
    return name, sheet, meta


def _frame_bytes(sheet: Image.Image, index: int) -> bytes:
    return sheet.crop((index * CANVAS, 0, (index + 1) * CANVAS, sheet.height)).tobytes()


def _validate(name: str, image: Image.Image, meta: dict) -> None:
    if image.mode != "RGBA" or image.size != (meta["width"], meta["height"]):
        raise AssertionError(f"{name}: sheet is not RGBA with matching metadata size")
    height = image.height
    if height not in (CANVAS, KIKO_CANVAS_H) or image.width % CANVAS:
        raise AssertionError(f"{name}: sheet is not aligned to {CANVAS}-wide frames")
    opaque = {pixel for pixel in image.get_flattened_data() if _is_opaque(pixel)}
    if not opaque or not opaque <= set(PROXY.values()):
        raise AssertionError(f"{name}: opaque pixels must be proxy colours")
    if meta["_resourceType"] != "sprite" or meta["spriteMode"] != "8x16":
        raise AssertionError(f"{name}: not a native 8x16 sprite sidecar")
    frame_count = image.width // CANVAS
    frames = [_frame_bytes(image, index) for index in range(frame_count)]
    for index in range(frame_count):
        frame = image.crop((index * CANVAS, 0, (index + 1) * CANVAS, height))
        ys = [y for y in range(height) for x in range(CANVAS) if _is_opaque(frame.getpixel((x, y)))]
        if not ys:
            raise AssertionError(f"{name}: frame {index} is empty")
        if max(ys) != height - 1:
            raise AssertionError(f"{name}: frame {index} does not stand on the shared feet row")
        accents = sum(1 for pixel in frame.get_flattened_data() if pixel == PROXY[2])
        if name == "kiko_stove" and accents > MAX_ACCENT_PIXELS:
            raise AssertionError(f"{name}: frame {index} has {accents} accent pixels")
    for state in meta["states"]:
        if len(state["animations"]) != ENGINE_SLOTS:
            raise AssertionError(f"{name}: animation slots must be 8")
    tile_ids: set[str] = set()
    for state in meta["states"]:
        for animation in state["animations"]:
            for frame in animation["frames"]:
                for tile in frame["tiles"]:
                    if tile["id"] in tile_ids:
                        raise AssertionError(f"{name}: duplicate tile id")
                    tile_ids.add(tile["id"])
                    if (tile["sliceX"] < 0 or tile["sliceX"] + 8 > image.width
                            or tile["sliceY"] % 16 or tile["sliceY"] + 16 > height
                            or tile["y"] != height - 16 - tile["sliceY"]):
                        raise AssertionError(f"{name}: tile slice outside its object")
    states_by_name = {state["name"]: state for state in meta["states"]}
    if name == "kiko":
        if list(states_by_name) != list(kiko.KIKO_STATES):
            raise AssertionError("Kiko states must match kiko.KIKO_STATES in order")
        if len(states_by_name["Waiting"]["animations"][0]["frames"]) != 2:
            raise AssertionError("Waiting must be a two-frame loop")
        if len(states_by_name["Relieved"]["animations"][0]["frames"]) != 2:
            raise AssertionError("Relieved must be a two-frame loop")
        if frames[0] == frames[1] or frames[2] == frames[3]:
            raise AssertionError("Kiko idle frames must differ within each state")
        if frames[0] == frames[2]:
            raise AssertionError("Kiko Waiting and Relieved must differ")
    elif name == "kiko_stove":
        if list(states_by_name) != list(kiko.STOVE_STATES):
            raise AssertionError("stove states must match kiko.STOVE_STATES")
        if len(states_by_name["Off"]["animations"][0]["frames"]) != 1:
            raise AssertionError("Off must be one frame")
        if len(states_by_name["On"]["animations"][0]["frames"]) != 2:
            raise AssertionError("On must be a two-frame loop")
        if frames[0] in (frames[1], frames[2]) or frames[1] == frames[2]:
            raise AssertionError("stove Off/On frames must differ and the On loop must alternate")
        off_frame = image.crop((0, 0, CANVAS, height))
        if any(pixel == PROXY[2] for pixel in off_frame.get_flattened_data()):
            raise AssertionError("stove Off must be cold: no glowing or airflow pixels")
    if (meta["boundsX"], meta["boundsY"], meta["boundsWidth"], meta["boundsHeight"]) != _bounds(image):
        raise AssertionError(f"{name}: bounds do not match the art")


def make_assets() -> Iterable[tuple[str, Image.Image, dict]]:
    """Return each owned resource as ``(name, image, native sidecar)``."""
    assets = [_kiko_asset(), _stove_asset()]
    for name, image, meta in assets:
        _validate(name, image, meta)
    return assets


def _check_ownership(name: str, png_path: Path, sidecar_path: Path, meta: dict) -> None:
    if not png_path.exists() and not sidecar_path.exists():
        return
    if not png_path.exists() or not sidecar_path.exists():
        raise FileExistsError(f"Refusing to replace an unpaired owned sprite: {png_path}")
    existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if existing.get("id") != meta["id"] or existing.get("name") != name:
        raise FileExistsError(f"Refusing to replace a different sprite resource: {sidecar_path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = list(make_assets())
    # Preflight every destination before writing any of them.
    for name, _image, meta in assets:
        png_path = OUT_DIR / f"{name}.png"
        _check_ownership(name, png_path, Path(str(png_path) + ".gbsres"), meta)
    for name, image, meta in assets:
        png_path = OUT_DIR / f"{name}.png"
        sidecar_path = Path(str(png_path) + ".gbsres")
        image.save(png_path, format="PNG", optimize=False)
        meta["checksum"] = hashlib.sha1(png_path.read_bytes()).hexdigest()
        sidecar_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        with Image.open(png_path) as check:
            if check.mode != "RGBA" or check.size != image.size:
                raise AssertionError(f"{name}: persisted PNG failed dimension/mode check")
        reread = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if reread != meta or reread["checksum"] != hashlib.sha1(png_path.read_bytes()).hexdigest():
            raise AssertionError(f"{name}: persisted sidecar/checksum validation failed")
        print(f"generated assets/sprites/{name}.png + .gbsres ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
