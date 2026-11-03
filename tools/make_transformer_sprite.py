"""Generate the distribution-transformer sprite (grey can on a short post).

Run with managed Python: tools/make_transformer_sprite.py

Reuses the grid sprite conventions of make_grid_sprites.py (proxy colours,
tall-object Y mapping, 8-slot animations) on GRID_SPRITE_PALETTE_SLOT.
``make_asset(resource_id, name)`` takes the job's ID function, so another
scene's transformer is ``make_asset(other.resource_id)``; the default keeps
Wind Ridge's ``ridge.TRANSFORMER_SPRITE_ID`` (ridge.resource_id("sprite:transformer")).
Glyphs: '.' clear, '1' light metal, '2' accent (indicator only), '3' dark.
Frames: 0 Dead, 1 Live lamp on, 2 Live lamp pulse.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import sys
from pathlib import Path
from typing import Callable

TOOLS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS_DIR))
import make_grid_sprites as mgs  # noqa: E402
import ridge  # noqa: E402

OUT_DIR = TOOLS_DIR.parent / "assets" / "sprites"
NAME = "transformer"
W, H = ridge.TRANSFORMER_CANVAS


@contextlib.contextmanager
def _grid_ids(resource_id: Callable[[str], str]):
    """Let the shared sidecar builder emit this job's ids, then restore it.

    Patching mgs._grid_id for the whole process made grid_cable_end regenerate
    with the wrong ids whenever both modules were imported (the test suite).
    """
    original = mgs._grid_id
    mgs._grid_id = resource_id
    try:
        yield
    finally:
        mgs._grid_id = original


def _base() -> list[list[str]]:
    g = [["."] * W for _ in range(H)]

    def put(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            g[y][x] = c

    put(6, 9, 0, "3"); put(6, 9, 1, "3")            # terminal cap
    for y in range(2, 6):                            # bushing insulator
        g[y][6] = "3"; g[y][9] = "3"; g[y][7] = g[y][8] = "1"
    put(3, 12, 6, "3")                               # collar
    for y in range(7, 24):                           # can body
        put(1, 14, y, "3")
        put(2, 13, y, "1")
        g[y][13] = "3" if y % 2 else "1"             # shaded side
    put(1, 14, 7, "3"); put(1, 14, 23, "3")
    put(2, 13, 10, "3"); put(2, 13, 19, "3")         # ribs
    for y in (8, 9, 20, 21, 22):                     # side lugs
        g[y][0] = "3"; g[y][15] = "3"
    for y in range(11, 15):
        put(6, 9, y, "3")                            # lamp housing
    put(2, 13, 24, "3"); put(2, 13, 25, "3")         # cross bracket
    for y in range(26, 31):                          # wooden post
        g[y][6] = "3"; g[y][9] = "3"; g[y][7] = g[y][8] = "1"
    put(4, 11, 31, "3")                              # foot
    return g


def _frame(state: str, lamp: tuple = ()) -> list[str]:
    g = _base()
    if state == "dead":
        for x, y in [(2, 16), (3, 16), (4, 16), (3, 17), (3, 18), (3, 21), (3, 22)]:
            g[y][x] = "3"                            # scorch + drip
        for x, y in [(10, 1), (11, 2), (12, 3), (12, 4), (11, 5), (10, 5)]:
            g[y][x] = "3"                            # slack lead loop
    else:
        for x in range(10, 16):                      # taut lead
            g[1][x] = "3"
        for x, y in lamp:
            g[y][x] = "2"
    return ["".join(r) for r in g]


FRAMES = [
    _frame("dead"),
    _frame("live", [(7, 12), (8, 12), (7, 13), (8, 13)]),
    _frame("live", [(7, 12), (8, 12)]),
]


def make_asset(resource_id: Callable[[str], str] = ridge.resource_id, name: str = NAME):
    """(sheet, sidecar meta) for a transformer whose sprite ID is ``resource_id("sprite:" + name)``."""
    frames = [mgs._render(rows, W, H) for rows in FRAMES]
    sheet = mgs._sheet(frames, W, H)
    states = [
        {"name": "Dead", "animationType": "fixed", "animations": mgs._empty_animations([0])},
        {"name": "Live", "animationType": "fixed", "animations": mgs._empty_animations([1, 2])},
    ]
    with _grid_ids(resource_id):
        meta = mgs._sidecar(name, sheet, W, H, states, anim_speed=12)
    # Interaction box: lower 16 px, full width (origin is canvas_h - 8 = 24).
    meta.update(boundsX=0, boundsY=16 - (H - 8), boundsWidth=16, boundsHeight=16)
    assert meta["id"] == resource_id(f"sprite:{name}")
    return sheet, meta


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet, meta = make_asset()
    png = OUT_DIR / f"{NAME}.png"
    sheet.save(png, format="PNG", optimize=False)
    meta["checksum"] = hashlib.sha1(png.read_bytes()).hexdigest()
    Path(str(png) + ".gbsres").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(f"generated assets/sprites/{NAME}.png + .gbsres ({sheet.width}x{sheet.height})")


if __name__ == "__main__":
    main()
