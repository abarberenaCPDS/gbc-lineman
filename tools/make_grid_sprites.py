"""Generate the grid-repair sprite candidates: cable end, junction box, service gate.

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_grid_sprites.py

This generator owns only the ``grid_cable_end``, ``grid_junction_box`` and
``service_gate`` PNGs and their native GB Studio sidecars. Each frame is drawn
from ASCII rows: ``.`` is transparent, ``1`` is light metal, ``2`` is the small
accent (lights only) and ``3`` is the dark outline. The three opaque indices map
to the strict source proxies used by ``make_opening_characters.py`` (white,
gray 160, black). Transparent pixels are RGBA alpha 0 so native transparency
survives and the static analyzer can count the opaque colors.

All sprites use climb slot ``climb.GRID_SPRITE_PALETTE_SLOT`` and stable IDs
from ``climb.grid_resource_id``.
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
import climb  # noqa: E402

PALETTE_INDEX = climb.GRID_SPRITE_PALETTE_SLOT
TRANSPARENT = (0, 255, 0, 0)
PROXY = {
    1: (255, 255, 255, 255),  # light metal
    2: (160, 160, 160, 255),  # accent (cyan/amber in hardware palettes)
    3: (0, 0, 0, 255),        # dark outline
}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}
ENGINE_SLOTS = 8
MAX_ACCENT_PIXELS = 4  # accent is reserved for small lights/sparks
EXPECTED_SIZE = {
    "grid_cable_end": (16, 16),
    "grid_junction_box": (16, 16),
    "service_gate": (16, 32),
}

# Stub on top, snapped at the right; the cable hangs from its underside and
# ends in a plug whose bare conductors fray at the bottom.
CABLE_ROWS = [
    "................",
    "..33333333......",
    "..311111113.....",
    "..33333333......",
    ".......3........",
    ".......3........",
    ".......3........",
    "........3.......",
    "........3.......",
    "........3.......",
    "......3333......",
    "......3113......",
    "......3113......",
    "......3333......",
    ".......11.......",
    "........1.......",
]
CABLE_FRAME_EDITS = (
    [((10, 11), "2")],                     # frame 0: spark beside the plug
    [((10, 12), "2"), ((5, 14), "2")],     # frame 1: spark moves to the fray
)

# Insulator post on top of a grey box; the indicator window is the 2x2 at
# x=7..8, y=9..10 and is dark when dead.
BOX_ROWS = [
    "......3333......",
    ".....311113.....",
    "......3113......",
    "....31111113....",
    "....31111113....",
    "...3333333333...",
    "...3111111113...",
    "...3311111133...",
    "...3111111113...",
    "...3111331113...",
    "...3111331113...",
    "...3311111133...",
    "...3111111113...",
    "...3333333333...",
    "....3......3....",
    "................",
]
BOX_LIVE_A = [((7, 9), "2"), ((8, 9), "2"), ((7, 10), "2"), ((8, 10), "2")]
BOX_LIVE_B = [((7, 9), "2"), ((8, 9), "2")]  # pulse: only the top row lit


def _gate_rows(closed: bool) -> list[str]:
    """Gate art covering 24 rows; it is bottom-aligned into the 16x32 canvas."""
    grid = [["."] * 16 for _ in range(24)]
    for y in range(24):
        grid[y][0] = "3"
        grid[y][1] = "1"
        grid[y][14] = "1"
        grid[y][15] = "3"
    if closed:
        for x in (4, 7, 10):
            for y in range(3, 21):
                grid[y][x] = "3"
        for x in (5, 8, 11):
            for y in range(3, 21):
                grid[y][x] = "1"
        for x in range(16):
            grid[11][x] = "3"
        for x in range(1, 15):
            grid[12][x] = "1"
        # Amber warning lamp in a dark housing, on the upper bars.
        for x in range(6, 10):
            grid[4][x] = "3"
            grid[6][x] = "3"
        grid[5][6] = "3"
        grid[5][7] = "2"
        grid[5][8] = "2"
        grid[5][9] = "3"
        for x in range(16):
            grid[21][x] = "3"
        for x in range(1, 15):
            grid[22][x] = "1"
    # Header and floor frame both states; open leaves only this thin frame.
    for x in range(16):
        grid[0][x] = "3"
        grid[2][x] = "3"
        grid[23][x] = "3"
    for x in range(1, 15):
        grid[1][x] = "1"
    return ["".join(row) for row in grid]


GATE_CLOSED_ROWS = _gate_rows(True)
GATE_OPEN_ROWS = _gate_rows(False)


def _patch(rows: list[str], edits: Iterable[tuple[tuple[int, int], str]]) -> list[str]:
    grid = [list(row) for row in rows]
    for (x, y), glyph in edits:
        grid[y][x] = glyph
    return ["".join(row) for row in grid]


def _render(rows: list[str], canvas_w: int, canvas_h: int) -> Image.Image:
    """Bottom-align ASCII rows into a transparent canvas."""
    if len(rows) > canvas_h:
        raise ValueError(f"{len(rows)} art rows exceed canvas height {canvas_h}")
    padded = ["." * canvas_w] * (canvas_h - len(rows)) + list(rows)
    image = Image.new("RGBA", (canvas_w, canvas_h), TRANSPARENT)
    for y, row in enumerate(padded):
        if len(row) != canvas_w:
            raise ValueError(f"row {y} has width {len(row)}, expected {canvas_w}")
        for x, glyph in enumerate(row):
            if glyph not in GLYPH:
                raise ValueError(f"unknown glyph {glyph!r} at {x},{y}")
            image.putpixel((x, y), GLYPH[glyph])
    return image


def _sheet(frames: list[Image.Image], canvas_w: int, canvas_h: int) -> Image.Image:
    result = Image.new("RGBA", (canvas_w * len(frames), canvas_h), TRANSPARENT)
    for index, frame in enumerate(frames):
        if frame.size != (canvas_w, canvas_h):
            raise ValueError(f"frame {index} has {frame.size}, expected {(canvas_w, canvas_h)}")
        result.paste(frame, (index * canvas_w, 0))
    return result


def _index_of(pixel: tuple[int, int, int, int]) -> int:
    if pixel[3] == 0:
        return 0
    for index, proxy in PROXY.items():
        if pixel == proxy:
            return index
    raise ValueError(f"non-proxy pixel {pixel}")


def _is_opaque(pixel: tuple[int, int, int, int]) -> bool:
    return pixel[3] != 0


def _source_regions(canvas_h: int) -> list[tuple[int, int]]:
    if canvas_h == 32:
        # Same tall-object mapping as make_opening_characters.py: GB Studio's
        # 8x16 OBJ y is the negation of tile.y, so source rows 0..15 sit at
        # object y=16 and rows 16..31 at y=0, keeping source order on screen.
        return [(16, 0), (0, 16)]
    if canvas_h == 16:
        return [(0, 0)]
    raise ValueError(f"unsupported canvas height {canvas_h}")


def _grid_id(key: str) -> str:
    return climb.grid_resource_id(key)


def _frame_tiles(
    name: str,
    frame_index: int,
    state_index: int,
    animation_index: int,
    animation_frame_index: int,
    sheet: Image.Image,
    canvas_w: int,
    canvas_h: int,
) -> list[dict]:
    frame_x = frame_index * canvas_w
    tiles: list[dict] = []
    for y, source_y in _source_regions(canvas_h):
        for x in range(0, canvas_w, 8):
            crop = sheet.crop((frame_x + x, source_y, frame_x + x + 8, source_y + 16))
            if not any(_is_opaque(pixel) for pixel in crop.get_flattened_data()):
                continue
            key = (f"{name}:state:{state_index}:animation:{animation_index}:"
                   f"frame:{animation_frame_index}:object:{x}:{source_y}")
            tiles.append({
                "id": _grid_id(key + ":tile"),
                "x": x,
                "y": y,
                "sliceX": frame_x + x,
                "sliceY": source_y,
                "flipX": False,
                "flipY": False,
                "palette": 0,
                "paletteIndex": PALETTE_INDEX,
                "objPalette": "OBP0",
                "priority": False,
            })
    return tiles


def _crop_signature(crop: Image.Image) -> bytes:
    return bytes(_index_of(pixel) for pixel in crop.get_flattened_data())


def _bounds(sheet: Image.Image, canvas_w: int, canvas_h: int) -> tuple[int, int, int, int]:
    """Tight bounds over every frame, anchored like the opening worker sprites.

    The sprite origin sits 8 rows above the canvas bottom (y=canvas_h-8), which
    gives boundsY = top_row - (canvas_h - 8) exactly as the worker sidecars do.
    """
    xs: list[int] = []
    ys: list[int] = []
    for y in range(sheet.height):
        for x in range(sheet.width):
            if _is_opaque(sheet.getpixel((x, y))):
                xs.append(x % canvas_w)
                ys.append(y)
    if not xs:
        raise AssertionError("sprite has no opaque pixels")
    origin = canvas_h - 8
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    return (left, top - origin, right - left + 1, bottom - top + 1)


def _sidecar(
    name: str,
    sheet: Image.Image,
    canvas_w: int,
    canvas_h: int,
    states: list[dict],
    anim_speed: int,
) -> dict:
    state_data: list[dict] = []
    tile_signatures: set[bytes] = set()
    for state_index, state in enumerate(states):
        authored_animations = state["animations"]
        if len(authored_animations) != ENGINE_SLOTS:
            raise ValueError(f"{name}/{state['name']}: expected exactly 8 animation slots")
        animations: list[dict] = []
        for animation_index, frame_indices in enumerate(authored_animations):
            animation_frames: list[dict] = []
            for animation_frame_index, frame_index in enumerate(frame_indices):
                if not 0 <= frame_index < sheet.width // canvas_w:
                    raise ValueError(f"{name}: source frame {frame_index} is outside the sheet")
                tiles = _frame_tiles(
                    name, frame_index, state_index, animation_index,
                    animation_frame_index, sheet, canvas_w, canvas_h,
                )
                for tile in tiles:
                    crop = sheet.crop((
                        tile["sliceX"], tile["sliceY"],
                        tile["sliceX"] + 8, tile["sliceY"] + 16,
                    ))
                    tile_signatures.add(_crop_signature(crop))
                frame_key = (f"{name}:state:{state_index}:animation:{animation_index}:"
                             f"frame:{animation_frame_index}")
                animation_frames.append({"id": _grid_id(frame_key), "tiles": tiles})
            if not animation_frames:
                blank_key = f"{name}:state:{state_index}:animation:{animation_index}:empty-frame"
                animation_frames.append({"id": _grid_id(blank_key), "tiles": []})
            animation_key = f"{name}:state:{state_index}:animation:{animation_index}"
            animations.append({"id": _grid_id(animation_key), "frames": animation_frames})
        state_data.append({
            "id": _grid_id(f"{name}:state:{state_index}"),
            "name": state["name"],
            "animationType": state["animationType"],
            "flipLeft": False,
            "animations": animations,
        })

    bounds = _bounds(sheet, canvas_w, canvas_h)
    return {
        "_resourceType": "sprite",
        "id": _grid_id(f"sprite:{name}"),
        "name": name,
        "symbol": f"sprite_{name}",
        "filename": f"{name}.png",
        "width": sheet.width,
        "height": sheet.height,
        "checksum": "",
        "numTiles": len(tile_signatures),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": canvas_w,
        "canvasHeight": canvas_h,
        "boundsX": bounds[0],
        "boundsY": bounds[1],
        "boundsWidth": bounds[2],
        "boundsHeight": bounds[3],
        "animSpeed": anim_speed,
        "spriteMode": "8x16",
        "states": state_data,
    }


def _empty_animations(first: list[int]) -> list[list[int]]:
    return [first] + [[] for _ in range(ENGINE_SLOTS - 1)]


def _cable_end_asset() -> tuple[str, Image.Image, dict]:
    name = "grid_cable_end"
    frames = [
        _render(_patch(CABLE_ROWS, CABLE_FRAME_EDITS[0]), 16, 16),
        _render(_patch(CABLE_ROWS, CABLE_FRAME_EDITS[1]), 16, 16),
    ]
    sheet = _sheet(frames, 16, 16)
    states = [
        {"name": "Dangling", "animationType": "fixed",
         "animations": _empty_animations([0, 1])},
    ]
    return name, sheet, _sidecar(name, sheet, 16, 16, states, anim_speed=12)


def _junction_box_asset() -> tuple[str, Image.Image, dict]:
    name = "grid_junction_box"
    base = BOX_ROWS
    frames = [
        _render(base, 16, 16),                          # frame 0: dead
        _render(_patch(base, BOX_LIVE_A), 16, 16),      # frame 1: live, lamp on
        _render(_patch(base, BOX_LIVE_B), 16, 16),      # frame 2: live, pulse
    ]
    sheet = _sheet(frames, 16, 16)
    states = [
        {"name": "Dead", "animationType": "fixed",
         "animations": _empty_animations([0])},
        {"name": "Live", "animationType": "fixed",
         "animations": _empty_animations([1, 2])},
    ]
    return name, sheet, _sidecar(name, sheet, 16, 16, states, anim_speed=12)


def _gate_asset() -> tuple[str, Image.Image, dict]:
    name = "service_gate"
    frames = [
        _render(GATE_CLOSED_ROWS, 16, 32),
        _render(GATE_OPEN_ROWS, 16, 32),
    ]
    sheet = _sheet(frames, 16, 32)
    states = [
        {"name": "Closed", "animationType": "fixed",
         "animations": _empty_animations([0])},
        {"name": "Open", "animationType": "fixed",
         "animations": _empty_animations([1])},
    ]
    return name, sheet, _sidecar(name, sheet, 16, 32, states, anim_speed=12)


def _validate(name: str, image: Image.Image, meta: dict) -> None:
    canvas_w, canvas_h = meta["canvasWidth"], meta["canvasHeight"]
    if (canvas_w, canvas_h) != EXPECTED_SIZE[name]:
        raise AssertionError(f"{name}: unexpected canvas {canvas_w}x{canvas_h}")
    if image.size != (meta["width"], meta["height"]):
        raise AssertionError(f"{name}: sheet dimensions disagree with metadata")
    if image.mode != "RGBA" or image.height != canvas_h or image.width % canvas_w:
        raise AssertionError(f"{name}: sheet is not aligned RGBA frames")
    opaque = {pixel for pixel in image.get_flattened_data() if _is_opaque(pixel)}
    if not opaque or not opaque <= set(PROXY.values()) or len(opaque) > 3:
        raise AssertionError(f"{name}: opaque pixels must be 1-3 proxy colors")
    if meta["_resourceType"] != "sprite" or meta["spriteMode"] != "8x16":
        raise AssertionError(f"{name}: not a native 8x16 sprite sidecar")
    if meta["id"] != _grid_id(f"sprite:{name}"):
        raise AssertionError(f"{name}: non-deterministic resource identity")
    if len(meta["states"]) == 0:
        raise AssertionError(f"{name}: no states")
    tile_ids: set[str] = set()
    for state in meta["states"]:
        if len(state["animations"]) != ENGINE_SLOTS:
            raise AssertionError(f"{name}: animation slots must be 8")
        for animation in state["animations"]:
            for frame in animation["frames"]:
                for tile in frame["tiles"]:
                    if tile["paletteIndex"] != PALETTE_INDEX:
                        raise AssertionError(f"{name}: tile not on grid palette slot")
                    if tile["id"] in tile_ids:
                        raise AssertionError(f"{name}: duplicate tile id")
                    tile_ids.add(tile["id"])
                    if (tile["sliceX"] < 0 or tile["sliceX"] + 8 > image.width
                            or tile["sliceY"] < 0 or tile["sliceY"] + 16 > image.height):
                        raise AssertionError(f"{name}: tile slice outside sheet")
                    if canvas_h == 32:
                        expected = (16, 0) if tile["sliceY"] == 0 else (0, 16)
                        if (tile["y"], tile["sliceY"]) != expected:
                            raise AssertionError(f"{name}: incorrect tall-object Y/source mapping")
                    elif tile["y"] != 0:
                        raise AssertionError(f"{name}: unexpected object Y offset")
    if (meta["boundsX"], meta["boundsY"], meta["boundsWidth"], meta["boundsHeight"]) != _bounds(
            image, canvas_w, canvas_h):
        raise AssertionError(f"{name}: bounds do not match the art")
    frame_count = image.width // canvas_w
    frames = [
        image.crop((index * canvas_w, 0, (index + 1) * canvas_w, canvas_h))
        for index in range(frame_count)
    ]
    for index, frame in enumerate(frames):
        accents = sum(1 for pixel in frame.get_flattened_data() if pixel == PROXY[2])
        if accents > MAX_ACCENT_PIXELS:
            raise AssertionError(f"{name}: frame {index} has {accents} accent pixels")

    def frame_bytes(index: int) -> bytes:
        return frames[index].tobytes()

    states = {state["name"]: state for state in meta["states"]}
    if name == "grid_cable_end":
        if list(states) != ["Dangling"]:
            raise AssertionError("cable end must expose one Dangling state")
        if len(states["Dangling"]["animations"][0]["frames"]) != 2 or frame_bytes(0) == frame_bytes(1):
            raise AssertionError("cable end needs two distinct Dangling frames")
    elif name == "grid_junction_box":
        if list(states) != ["Dead", "Live"]:
            raise AssertionError("junction box must expose Dead and Live states")
        if len(states["Dead"]["animations"][0]["frames"]) != 1:
            raise AssertionError("Dead must be one frame")
        if len(states["Live"]["animations"][0]["frames"]) != 2:
            raise AssertionError("Live must be a two-frame pulse")
        dead, live_a, live_b = frame_bytes(0), frame_bytes(1), frame_bytes(2)
        if len({dead, live_a, live_b}) != 3:
            raise AssertionError("junction box Dead/Live frames must all differ")
    elif name == "service_gate":
        if list(states) != ["Closed", "Open"]:
            raise AssertionError("gate must expose Closed and Open states")
        if frame_bytes(0) == frame_bytes(1):
            raise AssertionError("Closed and Open gate frames must differ")
        open_opaque = sum(1 for pixel in frames[1].get_flattened_data() if _is_opaque(pixel))
        closed_opaque = sum(1 for pixel in frames[0].get_flattened_data() if _is_opaque(pixel))
        if open_opaque >= closed_opaque:
            raise AssertionError("Open gate must be lighter than Closed")


def make_assets() -> Iterable[tuple[str, Image.Image, dict]]:
    """Return each owned resource as ``(name, image, native sidecar)``."""
    assets = [
        _cable_end_asset(),
        _junction_box_asset(),
        _gate_asset(),
    ]
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
        sidecar_path = Path(str(png_path) + ".gbsres")
        _check_ownership(name, png_path, sidecar_path, meta)
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
