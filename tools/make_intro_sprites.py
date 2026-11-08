"""Generate the intro cinematic sprites: rain, lightning bolt, utility pole and hero.

Run with the managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_intro_sprites.py [--hero-variant neighborhood|classic] [--preview]

Writes ``assets/sprites/intro_{rain,bolt,pole,hero}.png`` and the reusable
``neighborhood_hero.png`` plus native GB Studio sidecars.
IDs, sizes, pole states and palette slots come from ``tools/intro.py``.

Art is procedural/ASCII: ``.`` transparent, ``1``/``2``/``3`` are the proxy colours
(white, gray 160, black) = hardware index 1/2/3 of the intro sprite palette named in
``intro.SPRITE_SLOTS`` (rain, bolt, pole). Sidecar tiles carry ``paletteIndex`` = that
OBJ slot; the scene worker must create the palette resources and may re-assign them.
Frames sit side by side in the PNG; each 8px column is one 8x16 OBJ per 16 rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import uuid
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
OUT_DIR = ROOT / "assets" / "sprites"
sys.path.insert(0, str(TOOLS_DIR))
import intro  # noqa: E402
import neighborhood_hero  # noqa: E402

W = 16
ENGINE_SLOTS = 8
TRANSPARENT = (0, 255, 0, 0)
PROXY = {1: (255, 255, 255, 255), 2: (160, 160, 160, 255), 3: (0, 0, 0, 255)}
GLYPH = {".": TRANSPARENT, "1": PROXY[1], "2": PROXY[2], "3": PROXY[3]}


def _grid(h: int) -> list[list[str]]:
    return [["."] * W for _ in range(h)]


def _rows(g: list[list[str]]) -> list[str]:
    return ["".join(r) for r in g]


def _put(g, x, y, c, over=True):
    if 0 <= y < len(g) and 0 <= x < W and (over or g[y][x] == "."):
        g[y][x] = c


# ---------------------------------------------------------------- rain (16x16)
# Three rigid diagonal streaks (6 rows, lean 1px per 2 rows); each frame moves them
# down 4 rows with wrap, so 4 frames loop seamlessly over the 16-row canvas.
RAIN_STREAKS = [(3, 0), (8, 5), (12, 10)]   # (x at head, y of head in frame 0)
RAIN_LEN = 6
RAIN_STEP = 4


def rain_frame(f: int) -> list[str]:
    g = _grid(16)
    for x0, y0 in RAIN_STREAKS:
        for k in range(RAIN_LEN):
            y = (y0 + f * RAIN_STEP + k) % 16
            _put(g, x0 + k // 2, y, "1" if k >= RAIN_LEN - 3 else "2")
    return _rows(g)


# ---------------------------------------------------------------- bolt (16x32)
BOLT_CENTERS = [8, 8, 9, 9, 10, 10, 11, 11, 10, 9, 8, 7, 6, 5, 5, 6, 7, 8, 9, 10, 11,
                11, 10, 9, 8, 7, 6, 6, 7, 7, 8, 8]


def bolt_frame(f: int) -> list[str]:
    g = _grid(32)
    for y, cx in enumerate(BOLT_CENTERS):
        wide = 2 if f == 0 else 3
        for x in range(cx - wide, cx + wide):
            _put(g, x, y, "2")
        # bright core: 2px in frame A, 3px in the flickered frame B
        for x in range(cx - 1, cx + (1 if f == 0 else 2)):
            _put(g, x, y, "1")
    if f == 1:   # flicker: a short side branch
        for k in range(5):
            _put(g, 11 + k // 2 + 1, 13 + k, "3", over=False)
            _put(g, 10 + k // 2 + 1, 13 + k, "1")
    return _rows(g)


# ---------------------------------------------------------------- pole (16x32)
ARM_X0, ARM_X1 = 3, 12
BREAK_Y = 14


def _pole_top(g, shear_div, y_from, y_to, dx=0):
    """Draw the standing pole's upper part rows y_from..y_to, sheared right going up."""
    for y in range(y_from, y_to + 1):
        s = (BREAK_Y - y) // shear_div if shear_div else 0
        ox = s + dx
        if y >= 6:   # trunk
            _put(g, 6 + ox, y, "3"); _put(g, 7 + ox, y, "2")
            _put(g, 8 + ox, y, "2"); _put(g, 9 + ox, y, "3")
        if y in (5, 6):   # crossarm
            for x in range(ARM_X0, ARM_X1 + 1):
                _put(g, x + ox, y, "3" if y == 6 else "2")
        if y == 4:
            for x in range(ARM_X0, ARM_X1 + 1):
                _put(g, x + ox, y, "3")
        if y in (2, 3):   # insulators
            for x in (ARM_X0 + 1, 7, 8, ARM_X1 - 1):
                if x in (7, 8) and y == 3:
                    _put(g, x + ox, y, "2")
                else:
                    _put(g, x + ox, y, "3")
    return


def pole_standing() -> list[str]:
    g = _grid(32)
    _pole_top(g, 0, 2, 31)
    for y in range(BREAK_Y + 1, 32):
        pass
    _put(g, 5, 31, "3"); _put(g, 10, 31, "3")   # base flare
    _put(g, 5, 30, "3"); _put(g, 10, 30, "3")
    return _rows(g)


SPARKS = [
    [(8, 15), (9, 14), (10, 15), (7, 14), (11, 13)],
    [(9, 15), (10, 14), (7, 15), (8, 13), (6, 14), (11, 15)],
    [(8, 14), (10, 15), (11, 14), (9, 13), (7, 15)],
]
WIRE_SWAY = [0, 1, 0]


def pole_snapped(f: int, cable: bool = True) -> list[str]:
    g = _grid(32)
    # lower stump with a jagged break (rows 17-18), gap above it holds the sparks
    for y in range(BREAK_Y + 3, 32):
        _put(g, 6, y, "3"); _put(g, 7, y, "2"); _put(g, 8, y, "2"); _put(g, 9, y, "3")
    _put(g, 5, 31, "3"); _put(g, 10, 31, "3"); _put(g, 5, 30, "3"); _put(g, 10, 30, "3")
    _put(g, 7, 17, "."); _put(g, 9, 17, "."); _put(g, 6, 16, "3"); _put(g, 8, 16, "2")
    # upper piece, tipped over to the right, hanging above the gap
    g2 = _grid(32)
    _pole_top(g2, 3, 2, BREAK_Y - 1)
    for y in range(32):
        for x in range(W):
            if g2[y][x] != ".":
                _put(g, x, y + 1, g2[y][x])
    if cable:
        # dangling wire from the crossarm end to near the ground, ending in a plug
        wx = ARM_X1 + (BREAK_Y - 3) // 3
        wx = min(wx, 14)
        for y in range(7, 16):
            sway = WIRE_SWAY[f] if y > 11 else 0
            _put(g, min(wx + (1 if y > 13 else 0) - sway, 15), y, "3")
        # compact plug head and its two prongs at the cable end
        end_x = min(wx + 1 - WIRE_SWAY[f], 15)
        _put(g, end_x, 16, "2")
        _put(g, max(end_x - 1, 0), 16, "2")
        _put(g, end_x, 17, "3")
        _put(g, max(end_x - 1, 0), 17, "3")
    # sparks at the break
    for x, y in SPARKS[f]:
        _put(g, x, y, "1")
    return _rows(g)


ASSETS = {
    "intro_rain": dict(sprite_id=intro.RAIN_SPRITE_ID, h=16, slot="rain", speed=6,
                       states=[("Default", [rain_frame(f) for f in range(4)])]),
    "intro_bolt": dict(sprite_id=intro.BOLT_SPRITE_ID, h=32, slot="bolt", speed=4,
                       states=[("Default", [bolt_frame(0), bolt_frame(1)])]),
    "intro_pole": dict(sprite_id=intro.POLE_SPRITE_ID, h=32, slot="pole", speed=6,
                       states=[("Standing", [pole_standing()]),
                               ("Snapped+Cable", [pole_snapped(f, cable=True) for f in range(3)]),
                               ("Snapped", [pole_snapped(f, cable=False) for f in range(3)])]),
    "intro_hero": dict(sprite_id=intro.HERO_SPRITE_ID, h=32, slot="worker", speed=10,
                       states=[]),
    "neighborhood_hero": dict(sprite_id=intro.NEIGHBORHOOD_HERO_SPRITE_ID, h=32,
                              slot="worker", speed=10, states=[]),
}


# ---------------------------------------------------------------- rendering
def _rid(name: str, key: str) -> str:
    return str(uuid.uuid5(uuid.UUID("5b1f0c7e-8a2d-5e43-9c61-7d0e3a4b2f98"),
                          f"mr-cfe:intro:sprite-sidecar:{name}:{key}"))


def _render(rows: list[str], h: int) -> Image.Image:
    assert len(rows) == h and all(len(r) == W for r in rows)
    im = Image.new("RGBA", (W, h), TRANSPARENT)
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            im.putpixel((x, y), GLYPH[c])
    return im


def _opaque(p):
    return p[3] != 0


def build(name: str):
    a = ASSETS[name]
    h = a["h"]
    frames: list[list[str]] = []
    states: list[tuple[str, list[int]]] = []
    for sname, fr in a["states"]:
        states.append((sname, list(range(len(frames), len(frames) + len(fr)))))
        frames += fr
    sheet = Image.new("RGBA", (W * len(frames), h), TRANSPARENT)
    for i, rows in enumerate(frames):
        sheet.paste(_render(rows, h), (i * W, 0))

    xs, ys = [], []
    for y in range(h):
        for x in range(sheet.width):
            if _opaque(sheet.getpixel((x, y))):
                xs.append(x % W); ys.append(y)
    origin = h - 8
    bounds = (min(xs), min(ys) - origin, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

    sigs = set()
    state_data = []
    for si, (sname, idxs) in enumerate(states):
        anims = []
        for ai in range(ENGINE_SLOTS):
            authored = idxs if ai == 0 else []
            afs = []
            for fi, frame_index in enumerate(authored):
                fx = frame_index * W
                tiles = []
                for x in range(0, W, 8):
                    for y in range(0, h, 16):
                        crop = sheet.crop((fx + x, y, fx + x + 8, y + 16))
                        if not any(_opaque(p) for p in crop.get_flattened_data()):
                            continue
                        # GB Studio measures a tile's y up from the canvas
                        # bottom (worker24: top slice at y=16); y=sliceY drew
                        # 32px sprites with swapped halves (ROM 23b2fc03).
                        tiles.append({
                            "id": _rid(name, f"s{si}:a{ai}:f{fi}:x{x}:y{y}"),
                            "x": x, "y": h - 16 - y, "sliceX": fx + x, "sliceY": y,
                            "flipX": False, "flipY": False, "palette": 0,
                            "paletteIndex": intro.SPRITE_SLOTS[a["slot"]],
                            "objPalette": "OBP0", "priority": False,
                        })
                        sigs.add(crop.tobytes())
                afs.append({"id": _rid(name, f"s{si}:a{ai}:f{fi}"), "tiles": tiles})
            if not afs:
                afs.append({"id": _rid(name, f"s{si}:a{ai}:empty"), "tiles": []})
            anims.append({"id": _rid(name, f"s{si}:a{ai}"), "frames": afs})
        state_data.append({"id": _rid(name, f"s{si}"), "name": sname,
                           "animationType": "fixed", "flipLeft": False,
                           "animations": anims})
    meta = {
        "_resourceType": "sprite", "id": a["sprite_id"], "name": name,
        "symbol": f"sprite_{name}", "filename": f"{name}.png",
        "width": sheet.width, "height": sheet.height, "checksum": "",
        "numTiles": len(sigs), "canvasOriginX": 0, "canvasOriginY": 0,
        "canvasWidth": W, "canvasHeight": h,
        "boundsX": bounds[0], "boundsY": bounds[1],
        "boundsWidth": bounds[2], "boundsHeight": bounds[3],
        "animSpeed": a["speed"], "spriteMode": "8x16", "states": state_data,
    }
    return sheet, meta, frames


def preview(path: Path) -> None:
    pal = {"1": (255, 255, 255), "2": (160, 160, 160), "3": (60, 60, 60)}
    cell, bg, S = 18, (20, 24, 40), 4
    items = []
    for name in ASSETS:
        _, _, frames = build(name)
        items += [(name, f) for f in frames]
    sheet = Image.new("RGB", (cell * len(items), 34), bg)
    for i, (_, rows) in enumerate(items):
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c != ".":
                    sheet.putpixel((i * cell + 1 + x, 1 + y), pal[c])
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.resize((sheet.width * S, sheet.height * S), Image.NEAREST).save(path)


def configure_heroes(variant: str) -> None:
    def states(frames):
        return [("Idle", list(frames[:2])), ("Walk", list(frames[2:]))]
    ASSETS["intro_hero"]["states"] = states(neighborhood_hero.VARIANTS[variant])
    ASSETS["neighborhood_hero"]["states"] = states(neighborhood_hero.NEIGHBORHOOD_FRAMES)


configure_heroes(intro.DEFAULT_HERO_VARIANT)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hero-variant", choices=intro.HERO_VARIANTS,
                        default=intro.DEFAULT_HERO_VARIANT)
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()
    configure_heroes(args.hero_variant)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ASSETS:
        sheet, meta, _ = build(name)
        png = OUT_DIR / f"{name}.png"
        side = Path(str(png) + ".gbsres")
        if side.exists():
            if json.loads(side.read_text())["id"] != meta["id"]:
                raise FileExistsError(f"refusing to replace a different sprite: {side}")
        sheet.save(png, format="PNG", optimize=False)
        meta["checksum"] = hashlib.sha1(png.read_bytes()).hexdigest()
        side.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        print(f"generated assets/sprites/{name}.png + .gbsres ({sheet.width}x{sheet.height})")
    if args.preview:
        preview(ROOT / "build" / "intro_preview" / "sprites.png")


if __name__ == "__main__":
    main()
