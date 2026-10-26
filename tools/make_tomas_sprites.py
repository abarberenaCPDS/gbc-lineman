"""Generate Tomás and his oxygen concentrator for the Wind Ridge repair job.

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_tomas_sprites.py

This generator owns only ``assets/sprites/tomas.png`` and
``assets/sprites/oxygen_concentrator.png`` plus their native GB Studio sidecars.
Stable IDs, the sprite palette slots and the state names come from ``tools/ridge.py``.

Art is drawn from ASCII rows: ``.`` is transparent, and ``1``, ``2``, ``3`` are the
three opaque proxy colours (white, gray 160, black). Proxy index N maps to hardware
index N of the palette the scene worker builds: ``ridge.TOMAS_SPRITE_HARDWARE`` for
Tomás and the grid sprite palette for the concentrator. Index 0 is always
transparent. Tomás uses the same proxy scheme as the 24px workers in ``make_opening_characters.py``
(16x32 canvas, tile y counting up from the bottom); the concentrator follows the grid sprites
in ``make_grid_sprites.py``.
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
import ridge  # noqa: E402

CANVAS = 16  # canvas width, and the concentrator canvas height
TOMAS_CANVAS_H = 32  # Tomás uses the 16x32 opening_worker24 format
ENGINE_SLOTS = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {
    1: (255, 255, 255, 255),  # hardware index 1
    2: (160, 160, 160, 255),  # hardware index 2
    3: (0, 0, 0, 255),        # hardware index 3
}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}

# Grid sprite palette (slot ridge.GRID_SPRITE_PALETTE_SLOT). Kept in step with
# make_climb_scene.GRID_SPRITE_HARDWARE; test_tomas_sprites.py cross-checks it.
GRID_SPRITE_HARDWARE = ["000000", "C7DCE1", "38C8D8", "142332"]
MAX_ACCENT_PIXELS = 4  # the cyan accent is reserved for small lights and airflow

# ---------------------------------------------------------------------------
# Tomás: oldest villager, a 23-24px figure on a 16x32 canvas (the opening_worker24
# format), feet on the canvas bottom row, a bit stooped (head forward/left, rounded
# back). Drawn as 24 rows and padded with 8 blank rows on top.
# 1 = skin, 2 = cardigan green, 3 = hair, outline, trousers, shoes, nasal tube.
# Waiting: open mouth, hand to chest (A raised, B lowered for a slow breath).
# Relieved: smile; A stands square, B lifts his head a pixel (easy breathing).
# Nasal hose: prongs under the nose, tube hooked at the ear and down to the floor.
# ---------------------------------------------------------------------------
def _row(*parts: tuple[int, str]) -> str:
    cells = ["."] * CANVAS
    for start, text in parts:
        cells[start:start + len(text)] = text
    return "".join(cells)


def _tomas_frame(smile: bool, hand: int = 2, relaxed: bool = False, lift: bool = False):
    """Head forward-left of a rounded back; bald crown, ears, moustache, nasal tube."""
    tube = (13, "3")  # nasal tube drops to the floor on the right (reads as a cane too)
    head = [
        _row((2, "333333")),                  # thin outline over a bald crown
        _row((1, "2"), (2, "111111"), (8, "2")),  # thinning hair wisps (gray)
        _row((1, "2"), (2, "111111"), (8, "2")),
        _row((1, "11111111")),
        _row((1, "11311311")),                # eyes: two dark dots on skin
        _row((0, "1113113111")),              # ears out to each side
        _row((0, "1111111111"), (10, "3")),   # tube hooks over the ear
        _row((1, "11333311"), (10, "3")),     # moustache
        _row((1, "11111111"), (10, "3")),
        _row((1, "11311311") if smile else (1, "11133111"), (10, "3")),  # mouth
        _row((2, "333333"), (10, "3")),       # chin
    ]
    body = [
        _row((3, "3"), (4, "222222"), (10, "3333")),     # shoulders, tube turns down
        _row((3, "3"), (4, "22222222"), (12, "33")),     # rounded back bulges right
        _row((3, "3"), (4, "22222222"), (12, "33")),
        _row((3, "3"), (4, "2222222"), (11, "3"), tube),
        _row((3, "3"), (4, "2222222"), (11, "3"), tube),
        _row((3, "3"), (4, "2222222"), (11, "3"), tube),
        _row((3, "3"), (4, "2222222"), (11, "3"), tube),
        _row((3, "333333333"), tube),            # cardigan hem
        _row((4, "333"), (8, "333"), tube),
        _row((4, "333"), (8, "333"), tube),
        _row((4, "333"), (8, "333"), tube),
        _row((3, "333"), (8, "3333"), tube),     # shoes
    ]
    if relaxed:  # arms at his sides, hands visible
        body[3] = _row((3, "1"), (4, "2222222"), (11, "1"), tube)
        body[4] = _row((3, "1"), (4, "2222222"), (11, "1"), tube)
    else:  # hand to chest
        body[hand] = _row((3, "3"), (4, "22"), (6, "11"), (8, "222"), (11, "3"), tube)
    rows = [_row()] + head + body
    if lift:  # head up one pixel, neck shown
        rows = rows[1:12] + [_row((4, "11"))] + rows[12:]
    return [_row()] * 8 + rows


TOMAS_WAIT_A = _tomas_frame(False, hand=3)
TOMAS_WAIT_B = _tomas_frame(False, hand=4)
TOMAS_REL_A = _tomas_frame(True, relaxed=True)
TOMAS_REL_B = _tomas_frame(True, relaxed=True, lift=True)
TOMAS_FRAMES = [TOMAS_WAIT_A, TOMAS_WAIT_B, TOMAS_REL_A, TOMAS_REL_B]
TOMAS_STATE_FRAMES = {"Waiting": [0, 1], "Relieved": [2, 3]}

# ---------------------------------------------------------------------------
# Oxygen concentrator: boxy home unit on two wheels, with a hose down the right.
# 1 = light housing, 2 = cyan indicator/airflow (grid accent), 3 = dark outline.
# ---------------------------------------------------------------------------
CONC_OFF = [
    "................",
    "......3333......",  # carry handle
    "......3..3......",
    "..333333333333..",
    "..311111111113..",
    "..313311111113..",  # indicator window: dark when off
    "..313311111113..",
    "..333333333333..",
    "..313131313113..",  # vent slits
    "..311111111113..",
    "..313131313113..",
    "..333333333333..",
    "...3333333333...",
    "...33......33...",  # wheels
    "...33......33...",
    "...33......33...",
]
HOSE_X = 14
HOSE_ROWS = range(6, 11)
def _lit(rows: list[str], edits: list[tuple[int, int]]) -> list[str]:
    grid = [list(row) for row in rows]
    for x, y in edits:
        grid[y][x] = "2"
    return ["".join(row) for row in grid]


CONC_FRAMES = [
    CONC_OFF,
    _lit(CONC_OFF, [(4, 5), (5, 5)]),           # frame 1: top indicator lit
    _lit(CONC_OFF, [(4, 6), (5, 6), (15, 9)]),  # frame 2: bottom indicator lit, airflow puff
]
CONC_STATE_FRAMES = {"Off": [0], "On": [1, 2]}


def _with_hose(rows: list[str]) -> list[str]:
    grid = [list(row) for row in rows]
    for y in HOSE_ROWS:
        grid[y][HOSE_X] = "3"
    return ["".join(row) for row in grid]


CONC_FRAMES = [_with_hose(frame) for frame in CONC_FRAMES]

# ---------------------------------------------------------------------------
# Rendering and sidecars
# ---------------------------------------------------------------------------


def _render(rows: list[str]) -> Image.Image:
    height = len(rows)
    if height not in (CANVAS, TOMAS_CANVAS_H):
        raise ValueError(f"unexpected row count {height}")
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
    return ridge.resource_id(f"{name}:{key}")


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
                for slice_y, x in ((sy, x) for sy in range(0, sheet.height, 16)
                                   for x in range(0, CANVAS, 8)):
                    crop = sheet.crop((frame_x + x, slice_y, frame_x + x + 8, slice_y + 16))
                    if not any(_is_opaque(pixel) for pixel in crop.get_flattened_data()):
                        continue
                    key = (f"state:{state_index}:animation:{animation_index}:"
                           f"frame:{animation_frame_index}:object:{x}")
                    if slice_y:
                        key += f":row:{slice_y}"
                    tiles.append({
                        "id": _rid(name, key + ":tile"),
                        "x": x,
                        "y": sheet.height - 16 - slice_y,  # tile y counts up from the bottom
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


def _tomas_asset() -> tuple[str, Image.Image, dict]:
    name = "tomas"
    sheet = _sheet([_render(rows) for rows in TOMAS_FRAMES])
    states = [(state, TOMAS_STATE_FRAMES[state]) for state in ridge.TOMAS_STATES]
    meta = _sidecar(name, ridge.TOMAS_SPRITE_ID, sheet, states,
                    ridge.TOMAS_SPRITE_PALETTE_SLOT, anim_speed=20)
    return name, sheet, meta


def _concentrator_asset() -> tuple[str, Image.Image, dict]:
    name = "oxygen_concentrator"
    sheet = _sheet([_render(rows) for rows in CONC_FRAMES])
    states = [(state, CONC_STATE_FRAMES[state]) for state in ridge.CONCENTRATOR_STATES]
    meta = _sidecar(name, ridge.CONCENTRATOR_SPRITE_ID, sheet, states,
                    ridge.GRID_SPRITE_PALETTE_SLOT, anim_speed=12)
    return name, sheet, meta


def _frame_bytes(sheet: Image.Image, index: int) -> bytes:
    return sheet.crop((index * CANVAS, 0, (index + 1) * CANVAS, sheet.height)).tobytes()


def _validate(name: str, image: Image.Image, meta: dict) -> None:
    if image.mode != "RGBA" or image.size != (meta["width"], meta["height"]):
        raise AssertionError(f"{name}: sheet is not RGBA with matching metadata size")
    if image.height not in (CANVAS, TOMAS_CANVAS_H) or image.width % CANVAS:
        raise AssertionError(f"{name}: sheet is not aligned to {CANVAS}x{CANVAS} frames")
    opaque = {pixel for pixel in image.get_flattened_data() if _is_opaque(pixel)}
    if not opaque or not opaque <= set(PROXY.values()):
        raise AssertionError(f"{name}: opaque pixels must be proxy colours")
    if meta["_resourceType"] != "sprite" or meta["spriteMode"] != "8x16":
        raise AssertionError(f"{name}: not a native 8x16 sprite sidecar")
    frame_count = image.width // CANVAS
    frames = [_frame_bytes(image, index) for index in range(frame_count)]
    for index in range(frame_count):
        frame = image.crop((index * CANVAS, 0, (index + 1) * CANVAS, image.height))
        ys = [y for y in range(image.height) for x in range(CANVAS) if _is_opaque(frame.getpixel((x, y)))]
        if not ys or max(ys) != image.height - 1:
            raise AssertionError(f"{name}: frame {index} does not stand on the shared feet row")
        accents = sum(1 for pixel in frame.get_flattened_data() if pixel == PROXY[2])
        if name == "oxygen_concentrator" and accents > MAX_ACCENT_PIXELS:
            raise AssertionError(f"{name}: frame {index} has {accents} accent pixels")
    tile_ids: set[str] = set()
    for state in meta["states"]:
        if len(state["animations"]) != ENGINE_SLOTS:
            raise AssertionError(f"{name}: animation slots must be 8")
        for animation in state["animations"]:
            for frame in animation["frames"]:
                for tile in frame["tiles"]:
                    if tile["id"] in tile_ids:
                        raise AssertionError(f"{name}: duplicate tile id")
                    tile_ids.add(tile["id"])
                    if (tile["sliceX"] < 0 or tile["sliceX"] + 8 > image.width
                            or tile["sliceY"] + 16 > image.height
                            or tile["y"] != image.height - 16 - tile["sliceY"]):
                        raise AssertionError(f"{name}: tile slice outside its object")
    states_by_name = {state["name"]: state for state in meta["states"]}
    if name == "tomas":
        if list(states_by_name) != list(ridge.TOMAS_STATES):
            raise AssertionError("Tomás states must match ridge.TOMAS_STATES in order")
        if frames[0] == frames[1] or frames[2] == frames[3]:
            raise AssertionError("Tomás idle frames must differ within each state")
    elif name == "oxygen_concentrator":
        if list(states_by_name) != list(ridge.CONCENTRATOR_STATES):
            raise AssertionError("concentrator states must match ridge.CONCENTRATOR_STATES")
        if len(states_by_name["Off"]["animations"][0]["frames"]) != 1:
            raise AssertionError("Off must be one frame")
        if len(states_by_name["On"]["animations"][0]["frames"]) != 2:
            raise AssertionError("On must be a two-frame blink")
        if frames[1] == frames[2] or frames[0] in (frames[1], frames[2]):
            raise AssertionError("concentrator Off/On frames must differ")
    if (meta["boundsX"], meta["boundsY"], meta["boundsWidth"], meta["boundsHeight"]) != _bounds(image):
        raise AssertionError(f"{name}: bounds do not match the art")


def make_assets() -> Iterable[tuple[str, Image.Image, dict]]:
    """Return each owned resource as ``(name, image, native sidecar)``."""
    assets = [_tomas_asset(), _concentrator_asset()]
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
