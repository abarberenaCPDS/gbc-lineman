"""Generate Priya, her workstation and the live arc for the Signal Hill repair job.

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_rosa_sprites.py

This generator owns only ``assets/sprites/rosa.png``, ``assets/sprites/rosa_workstation.png``
and ``assets/sprites/live_arc.png`` plus their native GB Studio sidecars. Stable IDs, the
sprite palette slots and the state names come from ``tools/rosa.py``.

Art is drawn from ASCII rows: ``.`` is transparent, and ``1``, ``2``, ``3`` are the three
opaque proxy colours (white, gray 160, black). Proxy index N maps to hardware index N of the
palette the scene worker builds: ``rosa.ROSA_SPRITE_HARDWARE`` for Priya,
``rosa.ARC_SPRITE_HARDWARE`` for the arc, and the grid sprite palette for the workstation.
Index 0 is always transparent. Priya and the workstation keep the Hiroshi framing (feet on
row 15); the live arc follows the gust convention: its art lives in canvas rows 8..15, the
one 8px tile row of the hero's chest lane, so its bounds match the hit footprint.
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
import rosa  # noqa: E402

CANVAS = 16
ENGINE_SLOTS = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {
    1: (255, 255, 255, 255),  # hardware index 1
    2: (160, 160, 160, 255),  # hardware index 2
    3: (0, 0, 0, 255),        # hardware index 3
}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}

# Grid sprite palette (slot rosa.GRID_SPRITE_PALETTE_SLOT). Kept in step with
# make_climb_scene.GRID_SPRITE_HARDWARE; test_rosa_sprites.py cross-checks it.
GRID_SPRITE_HARDWARE = ["000000", "C7DCE1", "38C8D8", "142332"]
MAX_ACCENT_PIXELS = 4  # the cyan accent is reserved for small lights and airflow

EMPTY = "." * CANVAS

# ---------------------------------------------------------------------------
# Priya: a villager working online, front view, feet on row 15.
# 1 = skin, 2 = rose cardigan, 3 = long hair, glasses, outline, skirt, shoes.
# Long hair falls past the chin to the shoulders; glasses sit on row 4.
# Waiting: worried mouth (middle higher); A holds a dark phone at her side,
#   B blinks behind her glasses and raises the phone to look at it.
# Relieved: smile (corners higher); A arms at her sides, B raises her right hand to wave.
# ---------------------------------------------------------------------------
_ROSA_HEAD = [
    ".....333333.....",
    "....33333333....",
    "...3333333333...",
    "...3311111133...",  # forehead
    "...3311111133...",
    "...3313113133...",  # eyes: two dark pixels on skin, two rows tall
    "...3313113133...",
    "...3311111133...",  # cheeks
]
_MOUTH_FROWN = [
    "...3311331133...",  # middle higher than corners
    "...3313113133...",
]
_MOUTH_SMILE = [
    "...3313113133...",  # corners higher
    "...3311331133...",
]
_JAW = [
    "...3331111333...",
    "...3322112233...",  # collar
]
_SKIRT_LEGS_SHOES = [
    "....33333333....",  # skirt
    "...3333333333...",
    "..333333333333..",
    "....33....33....",  # stockings
    "....33....33....",
    "...333....333...",  # shoes
]
_ARMS_DOWN = [
    ".3" + "2" * 12 + "3.",
] * 5
_SHOULDERS = ".22332222223322."
ROSA_WAIT_A = _ROSA_HEAD + _MOUTH_FROWN + _JAW + [
    _SHOULDERS,
    "..3222222223....",
    "..3222222223.33.",  # dark phone held at her side
    "..3222222223.33.",
    "..3222222223....",
    "..3222222223....",
] + _SKIRT_LEGS_SHOES
ROSA_WAIT_B = _ROSA_HEAD[:5] + [
    "...3311111133...",  # blink: eyes shut to a single row
    "...3313113133...",
] + _ROSA_HEAD[7:] + _MOUTH_FROWN + _JAW + [
    ".22332222223333.",  # phone raised to chest height
    "..3222222223.33.",
    "..3222222223....",
    "..3222222223....",
    "..3222222223....",
    "..3222222223....",
] + _SKIRT_LEGS_SHOES
ROSA_REL_A = _ROSA_HEAD + _MOUTH_SMILE + _JAW + [_SHOULDERS] + _ARMS_DOWN + _SKIRT_LEGS_SHOES
_REL_B_FACE = [_MOUTH_SMILE[0], _MOUTH_SMILE[1][:13] + ".11"]  # right hand lifting
ROSA_REL_B = _ROSA_HEAD + _REL_B_FACE + [
    _JAW[0][:13] + "22.",  # right forearm raised
    _JAW[1][:13] + "22.",
    _SHOULDERS,
] + _ARMS_DOWN + _SKIRT_LEGS_SHOES
ROSA_TALL = 32  # canvas rows; the 24px figure stands on the bottom 24 of them
ROSA_FRAMES = [ROSA_WAIT_A, ROSA_WAIT_B, ROSA_REL_A, ROSA_REL_B]
ROSA_STATE_FRAMES = {"Waiting": [0, 1], "Relieved": [2, 3]}

# ---------------------------------------------------------------------------
# Workstation: a small porch table with a monitor and a router, 16px wide.
# 1 = pale housing and table top, 2 = cyan router LED (grid accent), 3 = dark outline.
# Off: dark screen, unlit router. On: lit (pale) screen with dark text lines, and the
# router LEDs blink between frames.
# ---------------------------------------------------------------------------
_WS_BEZEL = ".." + "3" + "1" * 8 + "3" + "...."           # monitor frame, pale housing
_WS_SCREEN_OFF = ".." + "3" + "1" + "3" * 6 + "1" + "3" + "...."  # dark screen
_WS_ON_TEXT_A = ".." + "3" + "1" + "3333" + "111" + "3" + "...."  # lit screen, text line
_WS_ON_TEXT_B = ".." + "3" + "1" + "333" + "1111" + "3" + "...."  # lit screen, shorter line
_WS_MONITOR_TOP = ".." + "3" * 10 + "...."
_WS_MONITOR_BOTTOM = ".." + "3" * 10 + "." + "333"         # monitor chin + router top
_WS_ANTENNA_ROW = ".." + "3" + "1" * 8 + "3" + ".." + "3" + "."
_WS_ROUTER_BOTTOM = "...." + "333333" + "..." + "333"     # monitor base + router base
_WS_TABLE_TOP = "1" * CANVAS
_WS_TABLE_EDGE = "3" * CANVAS
_WS_LEGS = "." + "3" + "." * 12 + "3" + "."


def _workstation_rows(screen_on: bool, router_mid: str) -> list[str]:
    """Monitor on a neck and base, a router on the table at the right.

    ``router_mid`` is the router's middle row (x13..15): ``313`` unlit, or with one
    cyan ``2`` LED lit. The table top starts at row 12; the bottom tile holds the table.
    """
    screen_a = _WS_ON_TEXT_A if screen_on else _WS_SCREEN_OFF
    screen_b = _WS_ON_TEXT_B if screen_on else _WS_SCREEN_OFF
    lit = _WS_BEZEL if screen_on else _WS_SCREEN_OFF
    return [
        EMPTY,                              # 0
        _WS_MONITOR_TOP,                    # 1
        _WS_BEZEL,                          # 2
        lit,                                # 3
        screen_a,                           # 4
        lit,                                # 5
        screen_b,                           # 6
        lit,                                # 7
        _WS_ANTENNA_ROW,                    # 8
        _WS_MONITOR_BOTTOM,                 # 9
        "......33" + "....." + router_mid,  # 10 neck + router middle
        _WS_ROUTER_BOTTOM,                  # 11 base + router base
        _WS_TABLE_TOP,                      # 12
        _WS_TABLE_EDGE,                     # 13
        _WS_LEGS,                           # 14
        _WS_LEGS,                           # 15
    ]


WS_OFF = _workstation_rows(False, "313")
WS_ON_A = _workstation_rows(True, "213")  # left LED lit
WS_ON_B = _workstation_rows(True, "312")  # right LED lit
WS_FRAMES = [WS_OFF, WS_ON_A, WS_ON_B]
WS_STATE_FRAMES = {"Off": [0], "On": [1, 2]}

# ---------------------------------------------------------------------------
# Live arc: a downed live wire, two 8x16 objects wide. Rows 8..15 only (one 8px tile row
# on the hero's chest lane). Warning: the dark wire with crackling sparks, two frames.
# Arc: a bright zig-zag core ('1') with a yellow halo ('2'), mirrored on the second frame.
# ---------------------------------------------------------------------------
_ARC_CORE_A = [
    EMPTY,
    "...1....1....1..",
    "..11...11...1.1.",
    ".1..1..1.1..1.1.",
    "1...1.1..1.1...1",
    ".....11....11...",
    ".....1....1.....",
    EMPTY,
]
_ARC_CORE_B = list(reversed(_ARC_CORE_A))

_WIRE = "3" * CANVAS
_WARN_A_BLOCK = [
    EMPTY,
    EMPTY,
    EMPTY,
    "..2.2...........",
    "...1............",
    EMPTY,
    _WIRE,
    EMPTY,
]
_WARN_B_BLOCK = [
    EMPTY,
    EMPTY,
    "............2.2.",
    "...........1....",
    EMPTY,
    EMPTY,
    _WIRE,
    EMPTY,
]


def _halo(core: list[str]) -> list[str]:
    """Surround each core pixel with a yellow ``2`` halo (8-neighbourhood, empty pixels only)."""
    height, width = len(core), len(core[0])
    grid = [list(row) for row in core]
    for y in range(height):
        for x in range(width):
            if core[y][x] != "1":
                continue
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < height and 0 <= nx < width and grid[ny][nx] == ".":
                        grid[ny][nx] = "2"
    return ["".join(row) for row in grid]


ARC_BLOCK_TOP = 8  # canvas row where the art starts (one 8px tile row, rows 8..15)
ARC_FRAMES = [
    _WARN_A_BLOCK,
    _WARN_B_BLOCK,
    _halo(_ARC_CORE_A),
    _halo(_ARC_CORE_B),
]
ARC_FRAMES = [[EMPTY] * ARC_BLOCK_TOP + block for block in ARC_FRAMES]
ARC_STATE_FRAMES = {"Warning": [0, 1], "Arc": [2, 3]}

# ---------------------------------------------------------------------------
# Rendering and sidecars
# ---------------------------------------------------------------------------


def _pad(rows: list[str], height: int) -> list[str]:
    """Top-pad figure rows with transparent rows so the figure stands on the canvas bottom."""
    return [EMPTY] * (height - len(rows)) + rows


def _render(rows: list[str], height: int = CANVAS) -> Image.Image:
    if len(rows) != height:
        raise ValueError(f"expected {height} rows, got {len(rows)}")
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
    return rosa.resource_id(f"{name}:{key}")


def _sidecar(
    name: str,
    sprite_id: str,
    sheet: Image.Image,
    states: list[tuple[str, list[int]]],
    palette_index: int,
    anim_speed: int,
) -> dict:
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
                objects = [(x, slice_y) for x in range(0, CANVAS, 8)
                           for slice_y in range(0, sheet.height, 16)]
                for x, slice_y in objects:
                    crop = sheet.crop((frame_x + x, slice_y, frame_x + x + 8, slice_y + 16))
                    if not any(_is_opaque(pixel) for pixel in crop.get_flattened_data()):
                        continue
                    key = (f"state:{state_index}:animation:{animation_index}:"
                           f"frame:{animation_frame_index}:object:{x}")
                    if slice_y:  # keep the original id for the single (or first) object row
                        key += f":row{slice_y}"
                    tiles.append({
                        "id": _rid(name, key + ":tile"),
                        "x": x,
                        # GB Studio tile y counts UP from the canvas bottom.
                        "y": sheet.height - 16 - slice_y,
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
        "canvasHeight": sheet.height,
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


def _rosa_asset() -> tuple[str, Image.Image, dict]:
    name = "rosa"
    sheet = _sheet([_render(_pad(rows, ROSA_TALL), ROSA_TALL) for rows in ROSA_FRAMES])
    states = [(state, ROSA_STATE_FRAMES[state]) for state in rosa.ROSA_STATES]
    meta = _sidecar(name, rosa.ROSA_SPRITE_ID, sheet, states,
                    rosa.ROSA_SPRITE_PALETTE_SLOT, anim_speed=20)
    return name, sheet, meta


def _workstation_asset() -> tuple[str, Image.Image, dict]:
    name = "rosa_workstation"
    sheet = _sheet([_render(rows) for rows in WS_FRAMES])
    states = [(state, WS_STATE_FRAMES[state]) for state in rosa.WORKSTATION_STATES]
    meta = _sidecar(name, rosa.WORKSTATION_SPRITE_ID, sheet, states,
                    rosa.GRID_SPRITE_PALETTE_SLOT, anim_speed=12)
    return name, sheet, meta


def _arc_asset() -> tuple[str, Image.Image, dict]:
    name = "live_arc"
    sheet = _sheet([_render(rows) for rows in ARC_FRAMES])
    states = [(state, ARC_STATE_FRAMES[state]) for state in rosa.ARC_STATES]
    meta = _sidecar(name, rosa.ARC_SPRITE_ID, sheet, states,
                    rosa.ARC_SPRITE_PALETTE_SLOT, anim_speed=8)
    return name, sheet, meta


def _frame_bytes(sheet: Image.Image, index: int) -> bytes:
    return sheet.crop((index * CANVAS, 0, (index + 1) * CANVAS, sheet.height)).tobytes()


def _validate(name: str, image: Image.Image, meta: dict) -> None:
    if image.mode != "RGBA" or image.size != (meta["width"], meta["height"]):
        raise AssertionError(f"{name}: sheet is not RGBA with matching metadata size")
    height = ROSA_TALL if name == "rosa" else CANVAS
    if image.height != height or image.width % CANVAS:
        raise AssertionError(f"{name}: sheet is not aligned to {CANVAS}x{height} frames")
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
        if name == "live_arc":
            if min(ys) < ARC_BLOCK_TOP:
                raise AssertionError(f"{name}: frame {index} leaves the chest-lane tile row")
        elif max(ys) != height - 1:
            raise AssertionError(f"{name}: frame {index} does not stand on the shared feet row")
        accents = sum(1 for pixel in frame.get_flattened_data() if pixel == PROXY[2])
        if name == "rosa_workstation" and accents > MAX_ACCENT_PIXELS:
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
                            or tile["y"] != height - 16 - tile["sliceY"]
                            or tile["sliceY"] % 16):
                        raise AssertionError(f"{name}: tile slice outside its object")
    states_by_name = {state["name"]: state for state in meta["states"]}
    if name == "rosa":
        if list(states_by_name) != list(rosa.ROSA_STATES):
            raise AssertionError("Priya states must match rosa.ROSA_STATES in order")
        if frames[0] == frames[1] or frames[2] == frames[3]:
            raise AssertionError("Priya idle frames must differ within each state")
        if frames[0] == frames[2]:
            raise AssertionError("Priya Waiting and Relieved must differ")
    elif name == "rosa_workstation":
        if list(states_by_name) != list(rosa.WORKSTATION_STATES):
            raise AssertionError("workstation states must match rosa.WORKSTATION_STATES")
        if len(states_by_name["Off"]["animations"][0]["frames"]) != 1:
            raise AssertionError("Off must be one frame")
        if len(states_by_name["On"]["animations"][0]["frames"]) != 2:
            raise AssertionError("On must be a two-frame blink")
        if frames[0] in (frames[1], frames[2]) or frames[1] == frames[2]:
            raise AssertionError("workstation Off/On frames must differ and LEDs must blink")
    elif name == "live_arc":
        if list(states_by_name) != list(rosa.ARC_STATES):
            raise AssertionError("arc states must match rosa.ARC_STATES")
        if len(states_by_name["Warning"]["animations"][0]["frames"]) != 2:
            raise AssertionError("Warning must be a two-frame loop")
        if len(states_by_name["Arc"]["animations"][0]["frames"]) != 2:
            raise AssertionError("Arc must be a two-frame loop")
        if frames[0] == frames[1] or frames[2] == frames[3]:
            raise AssertionError("arc loop frames must differ within each state")
        if frames[0] in (frames[2], frames[3]) or frames[1] in (frames[2], frames[3]):
            raise AssertionError("Warning and Arc frames must differ")
    if (meta["boundsX"], meta["boundsY"], meta["boundsWidth"], meta["boundsHeight"]) != _bounds(image):
        raise AssertionError(f"{name}: bounds do not match the art")


def make_assets() -> Iterable[tuple[str, Image.Image, dict]]:
    """Return each owned resource as ``(name, image, native sidecar)``."""
    assets = [_rosa_asset(), _workstation_asset(), _arc_asset()]
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
