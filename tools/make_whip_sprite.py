"""Generate the whipping live-wire hazard sprite (``assets/sprites/whip_wire.png`` + sidecar).

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_whip_sprite.py

Contract (id, states, canvas, palette slot, hardware colours) comes from ``tools/ridge.py``.
Canvas 16x32 = two stacked 8x16 OBJ rows per column. The wire hangs from the top edge; the
chest row of the placement (tile row 13) is canvas rows 16..23. Glyphs: ``.`` transparent,
``1`` spark (proxy white), ``2`` sheath (proxy gray 160), ``3`` dark outline (proxy black).
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
import ridge  # noqa: E402

NAME = "whip_wire"
W, H = ridge.WHIP_CANVAS
ENGINE_SLOTS = 8
ANIM_SPEED = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {1: (255, 255, 255, 255), 2: (160, 160, 160, 255), 3: (0, 0, 0, 255)}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}

ANCHOR_X = W // 2                    # wire leaves the clamp here
CLAMP_ROWS = 3                       # dark clamp block at the canvas top edge
CHEST_TOP = H - 16                   # tile row 13 = canvas rows 16..23 (rows 11..14 span 32 px)
STATE_FRAMES = {"Hang": [0, 1], "Sway": [2, 3], "Swing": [4, 5]}


def _grid() -> list[list[str]]:
    return [["."] * W for _ in range(H)]


def _put(g, x: int, y: int, ch: str) -> None:
    if 0 <= x < W and 0 <= y < H:
        g[y][x] = ch


def _line(pts: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Integer pixels along a polyline (Bresenham per segment)."""
    out: list[tuple[int, int]] = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            out.append((x0, y0))
            if (x0, y0) == (x1, y1):
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy
    return out


def _spark(g, cx: int, cy: int, big: bool) -> None:
    """Plus-shaped spark; ``big`` adds a 2x2 core and long arms (all index 1)."""
    cells = [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]
    if big:
        cells += [(1, 1), (2, 0), (-2, 0), (0, 2), (0, -2)]
    for dx, dy in cells:
        _put(g, cx + dx, cy + dy, "1")


def _wire(pts: list[tuple[int, int]], sparks: list[tuple[int, int, bool]]) -> list[str]:
    g = _grid()
    for x, y in _line(pts):                      # 2 px bold sheath
        _put(g, x, y, "2")
        _put(g, x + 1, y, "2")
    for y in range(CLAMP_ROWS):                  # dark clamp at the top edge
        for x in range(ANCHOR_X - 3, ANCHOR_X + 4):
            _put(g, x, y, "3")
    # dark outline on every transparent pixel touching the sheath
    for y in range(H):
        for x in range(W):
            if g[y][x] == ".":
                near = ((x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if any(0 <= a < W and 0 <= b < H and g[b][a] == "2" for a, b in near):
                    g[y][x] = "3"
    for cx, cy, big in sparks:
        _spark(g, cx, cy, big)
    return ["".join(r) for r in g]


def build_frames() -> list[list[str]]:
    top = (ANCHOR_X - 1, CLAMP_ROWS)
    tip_y = CHEST_TOP + 5                        # chest height (canvas y 21)
    hang_a = _wire([top, (ANCHOR_X - 1, 14), (ANCHOR_X - 1, tip_y)],
                   [(ANCHOR_X, tip_y + 2, False)])
    hang_b = _wire([top, (ANCHOR_X - 1, 14), (ANCHOR_X - 1, tip_y)],
                   [(ANCHOR_X - 2, tip_y + 2, False), (ANCHOR_X + 2, tip_y + 3, False)])
    sway_a = _wire([top, (ANCHOR_X - 3, 12), (ANCHOR_X - 5, tip_y)],
                   [(ANCHOR_X - 4, tip_y + 2, False)])
    sway_b = _wire([top, (ANCHOR_X + 1, 12), (ANCHOR_X + 3, tip_y)],
                   [(ANCHOR_X + 4, tip_y + 2, False)])
    # whip: S-curve out across the full width at chest height, big spark at the tip
    swing_a = _wire([top, (7, 12), (10, CHEST_TOP + 1), (14, CHEST_TOP + 3)],
                    [(13, CHEST_TOP + 5, True), (9, CHEST_TOP + 5, False), (4, CHEST_TOP + 2, False)])
    swing_b = _wire([top, (9, 12), (6, CHEST_TOP + 1), (1, CHEST_TOP + 3)],
                    [(2, CHEST_TOP + 5, True), (6, CHEST_TOP + 5, False), (11, CHEST_TOP + 2, False)])
    return [hang_a, hang_b, sway_a, sway_b, swing_a, swing_b]


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
    return ridge.resource_id(f"{NAME}:{key}")


def _opaque(p) -> bool:
    return p[3] != 0


def _shade(p) -> int:
    if p[3] == 0:
        return 0
    for i, proxy in PROXY.items():
        if p == proxy:
            return i
    raise ValueError(f"non-proxy pixel {p}")


def whip_bounds() -> tuple[int, int, int, int]:
    """Chest row (tile row 13) across the full width, in the rosa convention
    (y relative to canvas bottom - 8, same origin as ``make_rosa_sprites._bounds``)."""
    return (0, CHEST_TOP - (H - 8), W, 8)


def _sidecar(sheet: Image.Image) -> dict:
    states_meta = []
    signatures: set[bytes] = set()
    for si, state in enumerate(ridge.WHIP_STATES):
        anims = []
        for ai in range(ENGINE_SLOTS):
            authored = STATE_FRAMES[state] if ai == 0 else []
            frames = []
            for fi, frame_index in enumerate(authored):
                fx = frame_index * W
                tiles = []
                for x in range(0, W, 8):
                    for slice_y in range(0, H, 16):
                        crop = sheet.crop((fx + x, slice_y, fx + x + 8, slice_y + 16))
                        if not any(_opaque(p) for p in crop.get_flattened_data()):
                            continue
                        key = f"state:{si}:animation:{ai}:frame:{fi}:object:{x}"
                        if slice_y:
                            key += f":row{slice_y}"
                        tiles.append({
                            "id": _rid(key + ":tile"),
                            "x": x,
                            "y": H - 16 - slice_y,  # tile y counts UP from the canvas bottom
                            "sliceX": fx + x,
                            "sliceY": slice_y,
                            "flipX": False,
                            "flipY": False,
                            "palette": 0,
                            "paletteIndex": ridge.WHIP_SPRITE_PALETTE_SLOT,
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
    bx, by, bw, bh = whip_bounds()
    return {
        "_resourceType": "sprite",
        "id": ridge.WHIP_SPRITE_ID,
        "name": NAME,
        "symbol": f"sprite_{NAME}",
        "filename": f"{NAME}.png",
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
    sheet = _sheet([_render(r) for r in build_frames()])
    if not {p for p in sheet.get_flattened_data() if _opaque(p)} <= set(PROXY.values()):
        raise AssertionError("opaque pixels must be proxy colours")
    return sheet, _sidecar(sheet)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet, meta = make_asset()
    png_path = OUT_DIR / f"{NAME}.png"
    sidecar_path = Path(str(png_path) + ".gbsres")
    if sidecar_path.exists():
        existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if existing.get("id") != meta["id"]:
            raise FileExistsError(f"Refusing to replace a different sprite resource: {sidecar_path}")
    sheet.save(png_path, format="PNG", optimize=False)
    meta["checksum"] = hashlib.sha1(png_path.read_bytes()).hexdigest()
    sidecar_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    # one 4x preview sheet for review (gitignored build/)
    prev = ROOT / "build" / "whip_wire_preview.png"
    prev.parent.mkdir(parents=True, exist_ok=True)
    bg = Image.new("RGBA", sheet.size, (70, 90, 110, 255))
    bg.alpha_composite(sheet)
    bg.resize((sheet.width * 4, sheet.height * 4), Image.NEAREST).save(prev)
    print(f"generated assets/sprites/{png_path.name} + .gbsres ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
