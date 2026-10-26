"""Generate the cracked-board hazard sprite (``assets/sprites/cracked_board.png`` + sidecar).

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_hazard_sprites.py

Contract (id, states, canvas, bounds, palette slot) comes from ``tools/hazards.py``.
Canvas 24x16 = three 8x16 OBJs; the plank sits in the bottom 8 px, the top 8 px is empty
except the Creak splinter ticks. Glyphs: ``.`` transparent, ``1``/``2``/``3`` are proxy
colours (white, gray 160, black) = hardware indexes 1..3 of ``BOARD_SPRITE_HARDWARE``
(pale wood, mid wood, dark crack/outline). The art is built from small ASCII-grid helpers.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
OUT_DIR = ROOT / "assets" / "sprites"
sys.path.insert(0, str(TOOLS_DIR))
import hazards  # noqa: E402

W, H = hazards.BOARD_CANVAS
ENGINE_SLOTS = 8
ANIM_SPEED = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {1: (255, 255, 255, 255), 2: (160, 160, 160, 255), 3: (0, 0, 0, 255)}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}

PLANK_TOP = 10                      # plank rows 10..15 (6 px) on the shelf row
COLUMN = "312223"  # dark top edge, pale highlight, mid body x3, dark underside
CRACK_X = 11                        # crack falls between x=11 and x=12
STATE_FRAMES = {"Idle": [0], "Creak": [1, 2], "Break": [3, 4]}


def _grid() -> list[list[str]]:
    return [["."] * W for _ in range(H)]


def _put(g: list[list[str]], x: int, y: int, ch: str) -> None:
    if 0 <= x < W and 0 <= y < H:
        g[y][x] = ch


def _column(g, x: int, dy: int = 0, skip_ends: bool = True) -> None:
    for i, ch in enumerate(COLUMN):
        _put(g, x, PLANK_TOP + dy + i, ch)


def _rows(g) -> list[str]:
    return ["".join(r) for r in g]


def _nails(g, xs, dy=0):
    for x in xs:
        _put(g, x, PLANK_TOP + 2 + dy, "3")


def _grain(g, dy=0, shift=0):
    # short pale grain streaks on the body so the wood reads as weathered
    for x, y in ((3, 3), (4, 3), (7, 4), (8, 4), (16, 3), (17, 3), (20, 4)):
        _put(g, x + shift, PLANK_TOP + y + dy, "1")


def _plank(dx: int = 0, sag: int = 0, crack: bool = True) -> list[str]:
    """Whole plank, optionally shifted ``dx`` and with the middle sagging ``sag`` px."""
    g = _grid()
    for x in range(1, W - 1):
        sx = x + dx
        mid = 6 <= x <= 17
        _column(g, sx, sag if mid else 0)
    # rounded ends: drop the top-corner pixel of each end column
    for x in (1, W - 2):
        _put(g, x + dx, PLANK_TOP, ".")
    _grain(g, 0, dx)
    _nails(g, (3, 20), 0)
    for x in (3, 20):
        _put(g, x + dx, PLANK_TOP + 2, "3")
    if crack:
        # jagged dark crack from top edge to underside, two px wide in places
        for (cx, cy) in ((11, 0), (12, 1), (11, 2), (12, 3), (11, 4), (12, 5), (12, 0),
                         (11, 1), (12, 2), (11, 3)):
            _put(g, cx + dx, PLANK_TOP + cy + (sag if 6 <= cx <= 17 else 0), "3")
    return _rows(g)


def _overlay(rows: list[str], marks: dict[tuple[int, int], str]) -> list[str]:
    g = [list(r) for r in rows]
    for (x, y), ch in marks.items():
        _put(g, x, y, ch)
    return _rows(g)


def _ticks(points: list[tuple[int, int]]) -> dict[tuple[int, int], str]:
    """Splinter ticks: 3 px dark slivers with a pale tip, readable at 1x."""
    marks = {}
    for x, y in points:
        marks[(x, y)] = "1"
        marks[(x, y + 1)] = "3"
        marks[(x, y + 2)] = "3"
    return marks


def _broken(drop: int) -> list[str]:
    """Two halves hinged at the crack, inner ends tilting down by ``drop`` px."""
    g = _grid()
    left_w, right_w = 10, 10  # columns 0..9 and 14..23? gap of 4 would be wide; use 2 px gap
    for x in range(1, CRACK_X + 1):          # left half: x 1..11, inner end at 11
        d = (x - 1) * drop // (CRACK_X - 1)
        _column(g, x, d)
    for x in range(CRACK_X + 1, W - 1):      # right half: x 12..22, inner end at 12
        d = (W - 2 - x) * drop // (W - 2 - CRACK_X - 1)
        _column(g, x, d)
    # the dark gap/crack: broken ends show dark so the split reads
    for x, side in ((CRACK_X, -1), (CRACK_X + 1, 1)):
        d = (CRACK_X - 1) * drop // (CRACK_X - 1) if side < 0 else drop
        for i in range(6):
            _put(g, x, PLANK_TOP + d + i, "3")
    # a dark sliver between halves above the drop for contrast
    for dx_, d in ((3, 0), (20, 0)):
        pass
    for x in (3, 20):
        dd = (x - 1) * drop // (CRACK_X - 1) if x <= CRACK_X else (W - 2 - x) * drop // (W - 2 - CRACK_X - 1)
        _put(g, x, PLANK_TOP + 2 + dd, "3")
    return _rows(g)


def build_frames() -> list[list[str]]:
    idle = _plank()
    creak_a = _overlay(_plank(sag=1), _ticks([(8, 5), (12, 4), (16, 5)]))
    creak_b = _overlay(_plank(dx=1, sag=0), _ticks([(10, 5), (14, 4), (18, 6)]))
    break_a = _broken(2)
    break_b = _broken(5)
    return [idle, creak_a, creak_b, break_a, break_b]


def _render(rows: list[str]) -> Image.Image:
    img = Image.new("RGBA", (W, H), TRANSPARENT)
    for y, row in enumerate(rows):
        if len(row) != W:
            raise ValueError(f"row {y} width {len(row)}")
        for x, ch in enumerate(row):
            img.putpixel((x, y), GLYPH[ch])
    return img


def _sheet(frames: list[Image.Image]) -> Image.Image:
    sheet = Image.new("RGBA", (W * len(frames), H), TRANSPARENT)
    for i, f in enumerate(frames):
        sheet.paste(f, (i * W, 0))
    return sheet


def _rid(key: str) -> str:
    return hazards.resource_id(f"{hazards.BOARD_SPRITE_NAME}:{key}")


def _opaque(p) -> bool:
    return p[3] != 0


def _shade(p) -> int:
    if p[3] == 0:
        return 0
    for i, proxy in PROXY.items():
        if p == proxy:
            return i
    raise ValueError(f"non-proxy pixel {p}")


def _sidecar(sheet: Image.Image) -> dict:
    states_meta = []
    signatures: set[bytes] = set()
    for si, state in enumerate(hazards.BOARD_STATES):
        anims = []
        for ai in range(ENGINE_SLOTS):
            authored = STATE_FRAMES[state] if ai == 0 else []
            frames = []
            for fi, frame_index in enumerate(authored):
                fx = frame_index * W
                tiles = []
                for x in range(0, W, 8):
                    crop = sheet.crop((fx + x, 0, fx + x + 8, H))
                    if not any(_opaque(p) for p in crop.get_flattened_data()):
                        continue
                    tiles.append({
                        "id": _rid(f"state:{si}:animation:{ai}:frame:{fi}:object:{x}:tile"),
                        "x": x,
                        "y": 0,  # tile y counts UP from the canvas bottom; one row of 8x16
                        "sliceX": fx + x,
                        "sliceY": 0,
                        "flipX": False,
                        "flipY": False,
                        "palette": 0,
                        "paletteIndex": hazards.BOARD_SPRITE_PALETTE_SLOT,
                        "objPalette": "OBP0",
                        "priority": False,
                    })
                    signatures.add(bytes(_shade(p) for p in crop.get_flattened_data()))
                frames.append({"id": _rid(f"state:{si}:animation:{ai}:frame:{fi}"), "tiles": tiles})
            if not frames:
                frames.append({"id": _rid(f"state:{si}:animation:{ai}:empty-frame"), "tiles": []})
            anims.append({"id": _rid(f"state:{si}:animation:{ai}"), "frames": frames})
        states_meta.append({
            "id": _rid(f"state:{si}"),
            "name": state,
            "animationType": "fixed",
            "flipLeft": False,
            "animations": anims,
        })
    bx, by, bw, bh = hazards.BOARD_BOUNDS
    return {
        "_resourceType": "sprite",
        "id": hazards.BOARD_SPRITE_ID,
        "name": hazards.BOARD_SPRITE_NAME,
        "symbol": f"sprite_{hazards.BOARD_SPRITE_NAME}",
        "filename": f"{hazards.BOARD_SPRITE_NAME}.png",
        "width": sheet.width,
        "height": sheet.height,
        "checksum": "",
        "numTiles": len(signatures),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": W,
        "canvasHeight": H,
        "boundsX": bx,
        "boundsY": by,
        "boundsWidth": bw,
        "boundsHeight": bh,
        "animSpeed": ANIM_SPEED,
        "spriteMode": "8x16",
        "states": states_meta,
    }


def make_asset() -> tuple[Image.Image, dict]:
    frames = build_frames()
    sheet = _sheet([_render(r) for r in frames])
    opaque = {p for p in sheet.get_flattened_data() if _opaque(p)}
    if not opaque <= set(PROXY.values()):
        raise AssertionError("opaque pixels must be proxy colours")
    return sheet, _sidecar(sheet)


def _check_ownership(png_path: Path, sidecar_path: Path, meta: dict) -> None:
    if not png_path.exists() and not sidecar_path.exists():
        return
    if not png_path.exists() or not sidecar_path.exists():
        raise FileExistsError(f"Refusing to replace an unpaired owned sprite: {png_path}")
    existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if existing.get("id") != meta["id"] or existing.get("name") != meta["name"]:
        raise FileExistsError(f"Refusing to replace a different sprite resource: {sidecar_path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet, meta = make_asset()
    png_path = OUT_DIR / f"{hazards.BOARD_SPRITE_NAME}.png"
    sidecar_path = Path(str(png_path) + ".gbsres")
    _check_ownership(png_path, sidecar_path, meta)
    sheet.save(png_path, format="PNG", optimize=False)
    meta["checksum"] = hashlib.sha1(png_path.read_bytes()).hexdigest()
    sidecar_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"generated assets/sprites/{png_path.name} + .gbsres ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
