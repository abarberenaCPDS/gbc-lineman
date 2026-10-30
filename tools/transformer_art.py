"""One background transformer for every job (stdlib only; contracts and art generators import it).

Abe (0.17.0-dev playtest): the climb's transformer "may need an update, use the
one from Hiroshi's scene". This is a 16x24 background condensation of the job
transformer sprite's Live frame (``make_transformer_sprite.py``): terminal cap
and bushing insulator with its wire clamp, collar and lid, then a banded can
with side lugs, two ribs and the lamp housing, a cross bracket, a short post
and its foot.

Palettes are per 8x8 tile on the GBC, so the top row of tiles sits in its
stage's wire slot and holds only two colours: ``W`` (the stage colour, which
the chain palette swaps dead -> live, so cap, bushing, clamp, collar and lid
glow when power reaches the box) on that slot's index 0. The lamp lives inside
the can, whose tiles must keep the hardware ramp, so it stays an unlit lens.
The can and post rows are hardware: ``L`` light, ``G`` grey, ``D`` dark, ``.``
the slot's index 0. Each scene maps those codes to indexes of its own hardware
slot (``paint``'s ``body_index``).

Wires end in either top tile: the clamp bar spans both tiles at the wire's
pixel rows (3-4 inside a tile), so a wire dropping or running into the box
always meets it.
"""

from __future__ import annotations

TILE = 8
W, H = 2, 3              # tiles: two columns, three rows standing on the box tile

ART = [
    # top row: stage wire slot
    "......WWWW......",   # terminal cap
    "......WWWW......",
    ".......WW.......",   # bushing neck
    "...WWWWWWWWWW...",   # wire clamp (meets a wire at pixel rows 3-4 of either tile)
    "...WWWWWWWWWW...",
    "......WWWW......",   # insulator shed
    "...WWWWWWWWWW...",   # collar
    ".WWWWWWWWWWWWWW.",   # lid
    # can and post: hardware slot
    "DDLLLLLLLLLLLLDD",   # side lugs
    ".DLLLLLLLLLLLGD.",
    ".DDDDDDDDDDDDDD.",   # rib
    ".DLLLLDDDDLLLLD.",   # lamp housing
    ".DLLLLDGGDLLLGD.",   # lamp lens
    ".DLLLLDGGDLLLLD.",
    ".DLLLLDDDDLLLGD.",
    ".DLLLLLLLLLLLLD.",
    ".DDDDDDDDDDDDDD.",   # rib
    "DDLLLLLLLLLLLGDD",   # side lugs
    "DDLLLLLLLLLLLLDD",
    ".DDDDDDDDDDDDDD.",   # can bottom
    "..DDDDDDDDDDDD..",   # cross bracket
    "......DLLD......",   # post
    "......DLLD......",
    "....DDDDDDDD....",   # foot
]
STAGE_CODE = "W"
BODY_CODES = ("L", "G", "D")
assert len(ART) == H * TILE and all(len(row) == W * TILE for row in ART)
assert all(set(row) <= {".", "W"} for row in ART[:TILE]), "the top tile row is two-colour (wire slot)"
assert all(set(row) <= {".", *BODY_CODES} for row in ART[TILE:]), "the body rows are hardware only"


def tiles(box: tuple[int, int]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    """(stage-slot tiles, hardware-slot tiles) of a background transformer standing on ``box``."""
    x, y = box
    top = [(x + dx, y - H + 1) for dx in range(W)]
    body = [(x + dx, y - dy) for dy in range(H - 1) for dx in range(W)]
    return top, body


def all_tiles(box: tuple[int, int]) -> list[tuple[int, int]]:
    top, body = tiles(box)
    return top + body


def origin(box: tuple[int, int]) -> tuple[int, int]:
    """Top-left world pixel of the art."""
    x, y = box
    return x * TILE, (y - H + 1) * TILE


def stage_pixels(box: tuple[int, int]) -> set[tuple[int, int]]:
    """World pixels painted in the stage colour (cap, bushing, clamp, collar, lid)."""
    left, top = origin(box)
    return {(left + dx, top + dy) for dy, row in enumerate(ART) for dx, code in enumerate(row)
            if code == STAGE_CODE}


def paint(pixels, box: tuple[int, int], *, stage_rgb, body_rgb: dict[str, tuple[int, int, int]]) -> None:
    """Paint the art into a PIL pixel access; '.' pixels keep whatever is there (each slot's index 0)."""
    left, top = origin(box)
    for dy, row in enumerate(ART):
        for dx, code in enumerate(row):
            if code == STAGE_CODE:
                pixels[left + dx, top + dy] = stage_rgb
            elif code in body_rgb:
                pixels[left + dx, top + dy] = body_rgb[code]
