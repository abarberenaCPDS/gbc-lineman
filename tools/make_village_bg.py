"""Deterministically render the village background (256x256 px, 32x32 tiles).

`tools/village.py` is the authoritative source for the map grid, the house
placements and the eight background palette ramps; nothing here invents
gameplay data. Every tile is an explicit hand-authored 8x8 character grid of
palette indices ('0' lightest .. '3' darkest), so each pixel is a deliberate
decision: no procedural noise, only repeated authored tiles. The one derived
16x16 element (the conifer crown) is authored row by row as well and simply
split into four 8x8 tiles.

Palette slots follow `village.BG_PALETTES` order:

    0 ground (grass, tufts, flowers, stones, damp patches)
    1 path   (road, verges, corners, worn dirt, bridge deck, fences)
    2 rock   (cliff mass, rim, strata, outcrop ledges, well)
    3 water  (stream, banks, ripples)
    4 house  (cottage plaster, timber, door, windows, laundry)
    5 roof   (shingles, ridge, chimney, eave)
    6 pine   (cliff scrub; the large conifer is composed in the ground ramp)
    7       - reserved for the UI palette, never painted by this file

Run with the toolchain Python (Pillow is required):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_village_bg.py

Outputs (relative to the project root):

    assets/backgrounds/village.png
    assets/backgrounds/village.png.gbsres

plus review renders in the evidence directory (`VILLAGE_EVIDENCE_DIR`; it
defaults to `<system temp>/opencode/art`):

    village_map_1x.png          the whole 256x256 map at 1x
    village_map_2x.png          the same at 2x nearest-neighbour
    village_screen_160x144.png  one real screen at 1x, on the main path
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
import village  # noqa: E402  (authoritative map, houses, palettes)

ASSET_NAME = "village"
ASSET_PATH = PROJECT_DIR / "assets" / "backgrounds" / f"{ASSET_NAME}.png"
SIDECAR_PATH = Path(f"{ASSET_PATH}.gbsres")
UUID_NAMESPACE = uuid.UUID("717f5b5a-4e17-5f80-ae10-6afbdd2827db")
SYMBOL = "bg_village"

EVIDENCE_DIR = Path(
    os.environ.get(
        "VILLAGE_EVIDENCE_DIR",
        str(Path(tempfile.gettempdir()) / "opencode" / "art"),
    )
)

TILE = village.TILE
MAP_W, MAP_H = village.WIDTH, village.HEIGHT
BG_W, BG_H = MAP_W * TILE, MAP_H * TILE
MAX_UNIQUE_TILES = 384  # L-03, color-only build

# Side indices used by the path, rim and verge orientation tables.
NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
SIDE_STEPS = ((0, -1), (1, 0), (0, 1), (-1, 0))

# Slots 0..6 only. Slot 7 stays the UI palette and must never be painted here.
PALETTE_SLOTS = {name: index for index, (name, _colors) in enumerate(village.BG_PALETTES)}
PALETTE_RGB = {
    name: tuple(
        tuple(int(color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4)) for color in colors
    )
    for name, colors in village.BG_PALETTES
}
assert PALETTE_SLOTS["lit"] == 7, "village.BG_PALETTES slot order changed"


# ---------------------------------------------------------------------------
# Tile primitives
# ---------------------------------------------------------------------------


class Tile:
    """One 8x8 tile: a palette name plus eight strings of palette indices."""

    __slots__ = ("palette", "rows")

    def __init__(self, palette: str, rows: tuple[str, ...]) -> None:
        if len(rows) != TILE:
            raise ValueError(f"{palette}: {len(rows)} rows")
        for row in rows:
            if len(row) != TILE:
                raise ValueError(f"{palette}: bad row {row!r}")
            if any(char not in "0123" for char in row):
                raise ValueError(f"{palette}: bad index in {row!r}")
        if palette not in PALETTE_SLOTS:
            raise KeyError(palette)
        if PALETTE_SLOTS[palette] > 6:
            raise ValueError(f"{palette} is the reserved UI slot")
        self.palette = palette
        self.rows = rows

    @property
    def slot(self) -> int:
        return PALETTE_SLOTS[self.palette]

    def pattern(self) -> tuple[int, ...]:
        return tuple(int(char) for row in self.rows for char in row)

    def key(self) -> tuple[int, tuple[int, ...]]:
        return (self.slot, self.pattern())

    def mirror(self) -> "Tile":
        return Tile(self.palette, tuple(row[::-1] for row in self.rows))

    def rotate_cw(self) -> "Tile":
        rows = tuple("".join(self.rows[TILE - 1 - x][y] for x in range(TILE)) for y in range(TILE))
        return Tile(self.palette, rows)

    def flip_v(self) -> "Tile":
        return Tile(self.palette, tuple(reversed(self.rows)))

    def merge(self, *overlays: "Overlay") -> "Tile":
        """Draw hand-authored overlays over this tile; '.' means keep."""
        grid = [list(row) for row in self.rows]
        for overlay in overlays:
            for y, row in enumerate(overlay.rows):
                for x, char in enumerate(row):
                    if char != ".":
                        grid[y][x] = char
        return Tile(self.palette, tuple("".join(row) for row in grid))


class Overlay:
    """A transparent-by-'.' 8x8 stamp used to compose edge blends."""

    __slots__ = ("rows",)

    def __init__(self, rows: tuple[str, ...]) -> None:
        if len(rows) != TILE or any(len(row) != TILE for row in rows):
            raise ValueError("bad overlay shape")
        for row in rows:
            if any(char not in ".0123" for char in row):
                raise ValueError(f"bad overlay row {row!r}")
        self.rows = rows

    def rotate_cw(self) -> "Overlay":
        rows = tuple("".join(self.rows[TILE - 1 - x][y] for x in range(TILE)) for y in range(TILE))
        return Overlay(rows)

    def mirror(self) -> "Overlay":
        return Overlay(tuple(row[::-1] for row in self.rows))

    def flip_v(self) -> "Overlay":
        return Overlay(tuple(reversed(self.rows)))

    def turn(self, quarter_turns: int) -> "Overlay":
        overlay = self
        for _ in range(quarter_turns % 4):
            overlay = overlay.rotate_cw()
        return overlay


def make(palette: str, *rows: str) -> Tile:
    return Tile(palette, tuple(rows))


def stamp(*rows: str) -> Overlay:
    return Overlay(tuple(rows))


def quarter_turns(factory, name: str) -> dict[int, object]:
    """{0: N-facing, 1: E-facing, 2: S-facing, 3: W-facing}."""
    base = factory()
    return {turn: (base if isinstance(base, Tile) else base).turn(turn) if hasattr(base, "turn")
            else _rotate(base, turn) for turn in range(4)}


def _rotate(base, turn: int):
    rotated = base
    for _ in range(turn % 4):
        rotated = rotated.rotate_cw()
    return rotated


def four_way(factory) -> tuple[object, object, object, object]:
    """Author one orientation; return (N, E, S, W) by quarter-turn rotation."""
    base = factory()
    return (_rotate(base, 0), _rotate(base, 1), _rotate(base, 2), _rotate(base, 3))


def stable(x: int, y: int, count: int, salt: int = 0) -> int:
    """Coordinate hash for deliberate-but-varied placement of authored variants."""
    return (x * 37 + y * 71 + x * y * 13 + salt * 101 + 17) % count


# ---------------------------------------------------------------------------
# Ground palette: grass, tufts, flowers, stones, damp patches
#
# Base value is '1' (sage). Interest is added in small authored clusters that
# read at 1:1: a 3px tuft stroke, a three-blade clump, a 2x2 pale bloom on a
# dark stem, a pebble with a shaded underside, a damp hollow. Single stray
# pixels are avoided - a lone bright dot reads as glitter, not as grass - and
# the field stays calm because ~40% of cells are plain.
# ---------------------------------------------------------------------------

GRASS_CALM = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
)

# Long grass brushed flat: a 3px stroke with one darker pixel, no outline.
GRASS_STROKE_H = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11222111",
    "11111111",
    "11111111",
    "11111111",
)

GRASS_STROKE_V = make(
    "ground",
    "11111111",
    "11111111",
    "11111211",
    "11111211",
    "11111211",
    "11111111",
    "11111111",
    "11111111",
)

GRASS_STROKE_D = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11121111",
    "11122111",
    "11111111",
    "11111111",
    "11111111",
)

# A clump of blades read as dark green strokes against the sage field: no pale
# tips, because a lone bright pixel in a flat field reads as grit, not grass.
GRASS_TUFT_A = make(
    "ground",
    "11111111",
    "11111111",
    "11221111",
    "12222111",
    "11221121",
    "11122221",
    "11221122",
    "11111111",
)

GRASS_TUFT_B = make(
    "ground",
    "11111111",
    "11111111",
    "11221211",
    "12222211",
    "11211221",
    "11211122",
    "11111111",
    "11111111",
)

# A pale bloom with a dark centre on a stem. The bloom is a full 3x3 with a
# dark middle, so it reads as a flower at 1:1 instead of as a bright chip.
FLOWER_A = make(
    "ground",
    "11111111",
    "11000111",
    "11020111",
    "11000111",
    "11112111",
    "11122111",
    "11321111",
    "11111111",
)

FLOWER_B = make(
    "ground",
    "11111111",
    "11100011",
    "11102011",
    "11100011",
    "11112111",
    "11132111",
    "11111111",
    "11111111",
)

# A single stone bedded in the grass: pale cap with its own dark bed under it.
PEBBLES_A = make(
    "ground",
    "11111111",
    "11111111",
    "11200011",
    "11200011",
    "11222211",
    "11111111",
    "11111111",
    "11111111",
)

PEBBLES_B = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11110011",
    "11100011",
    "11122211",
    "11111111",
    "11111111",
)

# Damp hollow: dark green, no highlight, low contrast on purpose.
DAMP_A = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11112211",
    "11123211",
    "11122211",
    "11111111",
    "11111111",
)

DAMP_B = make(
    "ground",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
    "11112211",
    "11112231",
    "11111111",
    "11111111",
)

# Grass thinning into bare earth, stamped on grass cells next to the road so
# the verge is not a hard tile edge.
WORN_GRASS = make(
    "ground",
    "11111111",
    "11211111",
    "11121111",
    "11112111",
    "11111211",
    "11211111",
    "11111111",
    "11111111",
)

# Turf lifted over a cliff lip: two ragged rows of blades, drawn as an overlay
# on the grass cell that touches the rock so the overhang crosses the tile seam.
TURF_OVERHANG_N = stamp(
    "00201020",
    "12212121",
    "21111212",
    "........",
    "........",
    "........",
    "........",
    "........",
)

TURF_OVERHANG_E = TURF_OVERHANG_N.rotate_cw()
TURF_OVERHANG_S = TURF_OVERHANG_N.flip_v()
TURF_OVERHANG_W = TURF_OVERHANG_N.rotate_cw().rotate_cw().rotate_cw()

# Worn grass against a road: a short scuff of blades, one per side.
WEAR_N = stamp(
    "..2.2...",
    "12121211",
    "........",
    "........",
    "........",
    "........",
    "........",
    "........",
)
WEAR_E = WEAR_N.rotate_cw()
WEAR_S = WEAR_N.flip_v()
WEAR_W = WEAR_N.rotate_cw().rotate_cw().rotate_cw()

# Stream bank: reed clumps leaning out of the grass at the water line, pale
# tips over dark stems. Stamped on the grass cell so the shore has a soft edge
# instead of grass meeting water on a tile seam.
SHORE_N = stamp(
    "..0..0..",
    "..2..2..",
    ".121.12.",
    "11211211",
    "........",
    "........",
    "........",
    "........",
)
SHORE_E = SHORE_N.rotate_cw()
SHORE_S = SHORE_N.flip_v()
SHORE_W = SHORE_N.rotate_cw().rotate_cw().rotate_cw()

GRASS_PLAIN_POOL = (GRASS_CALM, GRASS_CALM, GRASS_CALM, GRASS_STROKE_H, GRASS_STROKE_V)
# Weighted so the field stays a field: half of it plain, most of the rest a
# single soft stroke, and only a small share carrying a pale accent. Keep the
# bright details uncommon: at 1:1 a field of pale chips reads as glitter.
GRASS_POOL = (
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_CALM,
    GRASS_STROKE_H,
    GRASS_STROKE_V,
    GRASS_STROKE_D,
    GRASS_STROKE_H,
    GRASS_STROKE_V,
    GRASS_TUFT_A,
    GRASS_TUFT_B,
    GRASS_TUFT_A,
    DAMP_A,
    DAMP_B,
    FLOWER_A,
    FLOWER_B,
    PEBBLES_A,
)


# ---------------------------------------------------------------------------
# Path palette: trodden road, verges, corners, end caps, worn dirt
#
# The road is two tiles wide almost everywhere, so most cells are interior fill
# and only the outer ring wears a verge. The verge is a *broken* 1px brown lip
# with a worn tan row under it - a solid dark ring turned every road into a
# trench. Corners and dead ends are authored separately so a turn is a turn and
# not two straight lips crossing.
# ---------------------------------------------------------------------------

PATH_FILL_H = (
    make(
        "path",
        "11111111",
        "11111111",
        "11101111",
        "11121111",
        "11111111",
        "11111111",
        "11111111",
        "11211111",
    ),
    make(
        "path",
        "11111111",
        "11111111",
        "11111111",
        "11211111",
        "11111111",
        "11111111",
        "11101111",
        "11121111",
    ),
    make(
        "path",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11011111",
        "11121111",
        "11111111",
        "11111121",
    ),
)

PATH_FILL_V = (
    make(
        "path",
        "11111111",
        "11111211",
        "11111211",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ),
    make(
        "path",
        "11111111",
        "11111111",
        "11111111",
        "11121111",
        "11121111",
        "11111111",
        "11111111",
        "11111101",
    ),
    make(
        "path",
        "11111111",
        "11111111",
        "11101111",
        "11121111",
        "11111111",
        "11111111",
        "11111111",
        "11111111",
    ),
)

# Verge: row 0 a broken brown lip ('3' dashes inside '2'), row 1 a worn tan
# seam, row 2 two stray specks. Three phases of the same lip, hashed per cell,
# so the road edge does not stitch itself into a dotted line.
VERGE_LIP = stamp(
    "23223232",
    "12211221",
    "11121112",
    "........",
    "........",
    "........",
    "........",
    "........",
)
VERGE_SOFT = stamp(
    "32233223",
    "12112112",
    "11111111",
    "........",
    "........",
    "........",
    "........",
    "........",
)
VERGE_WIDE = stamp(
    "23232232",
    "11221121",
    "11111211",
    "........",
    "........",
    "........",
    "........",
    "........",
)


def side_set(base: Overlay) -> dict[int, Overlay]:
    """{N, E, S, W} for one authored edge stamp."""
    return {
        NORTH: base,
        EAST: base.rotate_cw(),
        SOUTH: base.flip_v(),
        WEST: base.rotate_cw().rotate_cw().rotate_cw(),
    }


VERGES = (side_set(VERGE_LIP), side_set(VERGE_SOFT), side_set(VERGE_WIDE))

# Outer corner (path cell with grass on two adjacent sides): the lip wraps the
# corner and rounds the inner shoulder so junctions stop looking sheared off.
CORNER_NW = stamp(
    "23223232",
    "12211221",
    "22111111",
    "23111111",
    "22111111",
    "23111111",
    "22111111",
    "22111111",
)
CORNER_NE = CORNER_NW.mirror()
CORNER_SE = CORNER_NE.flip_v()
CORNER_SW = CORNER_NW.flip_v()

# Dead end: three lipped sides and a rounded, wider flare where the road stops.
END_E = make(
    "path",
    "23223232",
    "12211221",
    "11111122",
    "11111131",
    "11101122",
    "11111132",
    "11111122",
    "23223232",
)
END_N = END_E.rotate_cw()
END_W = END_E.rotate_cw().rotate_cw()
END_S = END_E.rotate_cw().rotate_cw().rotate_cw()

# A lone worn patch of bare earth, used where the road ends so the stop reads
# as "the track fades out" instead of "the texture ran out".
WORN_DIRT = (
    make(
        "path",
        "11111111",
        "11211111",
        "11121111",
        "11112111",
        "11101111",
        "11211111",
        "11111111",
        "11111111",
    ),
    make(
        "path",
        "11111111",
        "11111111",
        "11112111",
        "11121111",
        "11211111",
        "11111111",
        "11111111",
        "11111111",
    ),
)


# ---------------------------------------------------------------------------
# Rock palette: cliff face, rim, strata, outcrop ledges, scrub
#
# The border ring is a 2-tile-thick rock wall. The village-facing ring carries
# the lit face and the rim: a broken dark lip, a pale overhanging crest, then
# one or two irregular beds separated by a groove. The outer ring is quieter and
# a full value darker, so the wall has depth away from the village, and it keeps
# one joint or one slab per tile - a line every 4px is what made the old wall
# read as brickwork. Three rim heights, outcrop ledges and green scrub break up
# the run so no two stretches repeat the same rhythm.
# ---------------------------------------------------------------------------

# Lit face: beds, a groove and a crack, authored for the north-facing rim. Two
# variants put the groove at different depths so the seams do not line up.
ROCK_FACE = (
    # Two long courses, joint in the upper one: strata, not masonry.
    make(
        "rock",
        "00002000",
        "11112111",
        "11222111",
        "22223222",
        "00000000",
        "11111111",
        "11111111",
        "22222222",
    ),
    # Courses offset by a row, joint low.
    make(
        "rock",
        "11111111",
        "00000000",
        "11111111",
        "21111112",
        "11111111",
        "00200000",
        "11211111",
        "33233333",
    ),
    # One thick course with a chip out of the lip.
    make(
        "rock",
        "11111111",
        "11111111",
        "00000000",
        "11111111",
        "11212111",
        "22232222",
        "11111111",
        "11111111",
    ),
)

# Mass behind the face: one value darker, one form per tile.
ROCK_MASS = (
    # flat bed with a lit seam
    make(
        "rock",
        "22222222",
        "22222222",
        "21111112",
        "22222222",
        "22222222",
        "22222222",
        "22222222",
        "22222222",
    ),
    # vertical joint
    make(
        "rock",
        "22222222",
        "22322222",
        "22322222",
        "22322222",
        "22322222",
        "22222222",
        "22111122",
        "22222222",
    ),
    # rounded slab
    make(
        "rock",
        "22222222",
        "21112222",
        "21112222",
        "22222222",
        "22333322",
        "22222222",
        "22222222",
        "22222222",
    ),
    # long bed with a chip
    make(
        "rock",
        "22222222",
        "22222222",
        "22222222",
        "22222222",
        "11111111",
        "22222222",
        "22212122",
        "22222222",
    ),
)

# Village-facing rim, authored for the north side (rock below the grass). Three
# heights so the cliff lip steps along its run instead of ruling a straight line.
ROCK_RIM_LOW = stamp(
    "33333333",
    "00110011",
    "11111111",
    "22223222",
    "11111111",
    "11112111",
    "11222111",
    "........",
)
ROCK_RIM_STEP = stamp(
    "33333333",
    "22222222",
    "00110011",
    "11111111",
    "22223222",
    "11111111",
    "11112111",
    "........",
)
ROCK_RIM_HIGH = stamp(
    "33333333",
    "00001100",
    "11111111",
    "11111111",
    "22222222",
    "11111111",
    "11222111",
    "........",
)


def rim_set(base: Overlay) -> dict[int, Overlay]:
    """{N, E, S, W} for one authored rim height."""
    return {
        NORTH: base,
        EAST: base.rotate_cw(),
        SOUTH: base.flip_v(),
        WEST: base.rotate_cw().rotate_cw().rotate_cw(),
    }


ROCK_RIMS = (rim_set(ROCK_RIM_LOW), rim_set(ROCK_RIM_STEP), rim_set(ROCK_RIM_HIGH))

# Outcrop ledge: a rounded boulder swelling out of the wall, lit on top with a
# hard shadow underneath. Placed every few cells so the run varies.
ROCK_BUMP_N = stamp(
    "........",
    "00110011",
    "00111100",
    "01122210",
    "11222211",
    "33333333",
    "........",
    "........",
)
ROCK_BUMPS = rim_set(ROCK_BUMP_N)

# Scrub growing out of the cliff face: vegetation, so it is drawn in the pine
# ramp (slot 6) and replaces the rim on the odd cell rather than sitting on it.
ROCK_SCRUB = (
    make(
        "pine",
        "22222222",
        "21122112",
        "21222212",
        "22222222",
        "23222232",
        "22333222",
        "33323333",
        "33333333",
    ),
    make(
        "pine",
        "22222222",
        "22112221",
        "22222222",
        "22222222",
        "23222222",
        "32232223",
        "33333333",
        "33333333",
    ),
)


# ---------------------------------------------------------------------------
# Water palette: stream body, banks and ripples
#
# Water is '2' with 4-6px horizontal ripple runs ('1') carrying a '0' glint on
# some of them; '3' marks the trough under a run and the wet edge of the banks.
# Long strokes, few of them: the old stream was speckled with dashes and read
# as static rather than current.
# ---------------------------------------------------------------------------

WATER_MID = (
    make(
        "water",
        "22222222",
        "22222222",
        "11111111",
        "22333322",
        "22222222",
        "22211122",
        "22222222",
        "22222222",
    ),
    make(
        "water",
        "22222222",
        "22111112",
        "22233322",
        "22222222",
        "22222222",
        "11111111",
        "22333322",
        "22222222",
    ),
    make(
        "water",
        "22222222",
        "22222222",
        "22222222",
        "11101111",
        "22333322",
        "22222222",
        "22201112",
        "22222222",
    ),
    make(
        "water",
        "22222222",
        "22222222",
        "22211112",
        "22233322",
        "22222222",
        "22222222",
        "11111111",
        "22333322",
    ),
)

WATER_BANK_W = (
    make(
        "water",
        "32222222",
        "31111112",
        "32333322",
        "32222222",
        "32211122",
        "32222222",
        "32222222",
        "32222222",
    ),
    make(
        "water",
        "32222222",
        "31111112",
        "32333322",
        "32222222",
        "32222222",
        "32111122",
        "32222222",
        "32222222",
    ),
)

WATER_BANK_E = (
    WATER_BANK_W[0].mirror(),
    WATER_BANK_W[1].mirror(),
)

# Water in the bridge's shade: the deck throws the stream into near-dark.
WATER_SHADOW = make(
    "water",
    "33333333",
    "32333322",
    "33333333",
    "33333333",
    "33322333",
    "33333333",
    "33333333",
    "33333332",
)


# ---------------------------------------------------------------------------
# Bridge: far rail, planked deck, near rail, shadow under the deck
# ---------------------------------------------------------------------------

BRIDGE_MID = make(
    "path",
    "33333333",
    "22222222",
    "23222232",
    "12121212",
    "11111111",
    "23222232",
    "22222222",
    "33333333",
)

# The two bridge ends have an end post on top of the continuous guard rails.
# Each middle segment repeats the rails, posts and planking; the water tile
# below the deck is separately shaded by build_water.
BRIDGE_LEFT = make(
    "path",
    "33333333",
    "22222222",
    "33222232",
    "12121212",
    "11111111",
    "33222232",
    "22222222",
    "33333333",
)

BRIDGE_RIGHT = BRIDGE_LEFT.mirror()


# ---------------------------------------------------------------------------
# Rock palette, continued: single boulder outcrop
# ---------------------------------------------------------------------------

BOULDER = make(
    "rock",
    "33333333",
    "30011133",
    "30001133",
    "30111233",
    "32222233",
    "32222233",
    "32223333",
    "33333333",
)


# ---------------------------------------------------------------------------
# House palette: cottage plaster, timber, door, windows, yard props
#
# The 5x4 footprint holds a 4x4 cottage plus a one-tile yard strip down one
# side, so every cottage is asymmetric the way a real row of houses is. The
# door always sits over the doorstep that `village.house_door()` reports (the
# walkable cell below footprint column 2), so moving the yard from side to side
# is what shifts the door towards one end of the wall.
# ---------------------------------------------------------------------------

# --- roof (slot 5) -------------------------------------------------------

# Ridge band: dark outline, bright ridge, two shingle beds.
ROOF_PEAK_WIDE_L = make(
    "roof",
    "33333333",
    "00000000",
    "11111111",
    "11121112",
    "22222222",
    "11111111",
    "12111211",
    "22222222",
)

ROOF_PEAK_WIDE_R = make(
    "roof",
    "33333333",
    "11111111",
    "11111111",
    "12111211",
    "22222222",
    "11111111",
    "11121112",
    "22222222",
)

# Narrow pitch: the lit ridge only runs a few pixels in from the hip, so the
# roof reads as steeper than its neighbour's.
ROOF_PEAK_NARROW_L = make(
    "roof",
    "33333333",
    "22200000",
    "11111111",
    "11121112",
    "22222222",
    "11111111",
    "12111211",
    "22222222",
)

ROOF_PEAK_NARROW_R = ROOF_PEAK_NARROW_L.mirror()

# Hip end of the ridge: the roof turns away from the light, one value darker.
ROOF_END_L = make(
    "roof",
    "33333333",
    "22222222",
    "11211111",
    "11121112",
    "22222222",
    "11111111",
    "12111211",
    "22222222",
)

ROOF_END_R = ROOF_END_L.mirror()

# Ridge tile carrying the chimney: pale cap, brick body with mortar courses,
# then the roof continues under the stack's shadow.
ROOF_CHIMNEY_L = make(
    "roof",
    "33000033",
    "32111123",
    "32000023",
    "33111133",
    "22222222",
    "11111111",
    "12111211",
    "22222222",
)

ROOF_CHIMNEY_R = ROOF_CHIMNEY_L.mirror()

# Eave band: two shingle beds, bright lip, dark shadow where it meets the wall.
EAVE_MID_A = make(
    "roof",
    "22222222",
    "11111111",
    "11121112",
    "22222222",
    "11111111",
    "12111211",
    "00000000",
    "33333333",
)

EAVE_MID_B = make(
    "roof",
    "22222222",
    "11111111",
    "12111211",
    "22222222",
    "11111111",
    "11121112",
    "00000000",
    "33333333",
)

EAVE_END_L = make(
    "roof",
    "32222222",
    "31111111",
    "31112111",
    "32222222",
    "31111111",
    "31211121",
    "30000000",
    "33333333",
)

EAVE_END_R = EAVE_END_L.mirror()

# --- cottage wall (slot 4) ------------------------------------------------

# Corner post: dark outline, timber beam, plaster panel. The wall is only 16px
# tall, so it carries no speckle: the window, the door and the stone footing do
# all the work.
WALL_POST_L = make(
    "house",
    "33333333",
    "32111111",
    "32000000",
    "32000000",
    "32000000",
    "32000000",
    "32000000",
    "32000000",
)

WALL_POST_R = WALL_POST_L.mirror()

WALL_POST_L_BASE = make(
    "house",
    "32000000",
    "32000000",
    "32000000",
    "32000000",
    "31111111",
    "32222222",
    "31112211",
    "33333333",
)

WALL_POST_R_BASE = WALL_POST_L_BASE.mirror()

# Six-pane window: brown frame, tan glass, dark mullion cross, tan sill. The
# glass has to sit a value below the cream plaster or the window disappears
# into the wall.
WINDOW = make(
    "house",
    "00000000",
    "02222220",
    "02111120",
    "02133120",
    "02111120",
    "02222220",
    "01111110",
    "00000000",
)

WALL_UNDER = make(
    "house",
    "01111110",
    "00000000",
    "00000000",
    "00000000",
    "31111111",
    "32222222",
    "31112211",
    "33333333",
)

# Plaster below a boxed window: the flower box already closes the seam, so this
# one starts flush rather than doubling the sill line.
WALL_BOX_UNDER = make(
    "house",
    "00000000",
    "00000000",
    "00000000",
    "00000000",
    "31111111",
    "32222222",
    "31112211",
    "33333333",
)

# Same window with a flower box under the sill: three pale blooms over a plank.
WINDOW_BOX = make(
    "house",
    "00000000",
    "02222220",
    "02111120",
    "02133120",
    "02111120",
    "01111110",
    "02020200",
    "02222220",
)

# Plank door: lit lintel, dark frame, cross rail, knob, stone threshold.
DOOR_TOP = make(
    "house",
    "00000000",
    "22222220",
    "03333330",
    "03222230",
    "03200230",
    "03333330",
    "03222230",
    "03222230",
)

DOOR_BASE = make(
    "house",
    "03222230",
    "03222230",
    "03333330",
    "03222230",
    "02222220",
    "00000000",
    "01111110",
    "33333333",
)

# --- yard props -----------------------------------------------------------
#
# Each prop is a full 8x8 stamp in one material, because a tile carries one
# palette: the hedge, the garden and the laundry are ground-palette so the
# grass around them is the field's own grass, the woodpile is tan logs, the well
# is stone and the barrel is timber.

# A rounded shrub: the strip's back cell, so the yard starts with something
# low and soft instead of a green wall beside the roof.
BUSH = make(
    "ground",
    "11111111",
    "11111111",
    "11222211",
    "12202221",
    "22222222",
    "33222233",
    "11333311",
    "11111111",
)

HEDGE_HIGH = make(
    "ground",
    "01100110",
    "12222221",
    "12222221",
    "22022022",
    "22222222",
    "32222223",
    "33222233",
    "11333311",
)

HEDGE_LOW = make(
    "ground",
    "11111111",
    "01101110",
    "12222221",
    "12221221",
    "22222222",
    "33222333",
    "11111111",
    "11111111",
)

GARDEN = make(
    "path",
    "11001111",
    "22222222",
    "11101101",
    "22222222",
    "11001111",
    "22222222",
    "11101101",
    "33333333",
)

WOODPILE = make(
    "path",
    "33333333",
    "31113111",
    "30103010",
    "31113111",
    "32222223",
    "31113111",
    "30103010",
    "31113111",
)

# A stone drum seen from above: pale rim, dark shaft, and the water surface
# catching one glint, so it reads as a well rather than a drain.
WELL = make(
    "rock",
    "11111111",
    "11222211",
    "12111121",
    "12333321",
    "12303321",
    "12111121",
    "11222211",
    "11111111",
)

LAUNDRY = make(
    "ground",
    "11111111",
    "11111111",
    "33333333",
    "10001000",
    "10001000",
    "12221222",
    "11111111",
    "11111111",
)

FLOWERBED = make(
    "ground",
    "11111111",
    "11001100",
    "11001100",
    "12111211",
    "11111111",
    "11111111",
    "11111111",
    "11111111",
)

BARREL = make(
    "path",
    "11111111",
    "11333311",
    "13222231",
    "13201231",
    "13201231",
    "13222231",
    "11333311",
    "11111111",
)

YARD_PROPS = {
    "garden": GARDEN,
    "woodpile": WOODPILE,
    "well": WELL,
    "laundry": LAUNDRY,
    "flowerbed": FLOWERBED,
    "barrel": BARREL,
}


# ---------------------------------------------------------------------------
# Conifer
#
# The crown is authored once, row by row, as a 16x16 grid and then split into
# its four 8x8 tiles, so the silhouette cannot drift across the seam that made
# the old tree read as a dagger: a narrow spire, three branch tiers that flare
# out and then tuck back in (the notch), a pale rim down the lit left edge, and
# a dark 1px outline all the way round.
#
# Palette note: the crown is drawn in the *ground* ramp, not the pine ramp.
# One tile carries one palette, so a crown tile with pine colours must fill the
# air around the branches with a pine-ramp approximation of grass - the pale
# wedges that broke the old silhouette. The crown is therefore an overlay
# stamped onto ordinary grass tiles: the air around the branches is literally
# the field, and the tree reads as a dark green shape with a lit left rim
# (outline '3', body '2', highlight '0'). Slot 6 still earns its keep on the
# scrub that grows out of the cliff face.
# ---------------------------------------------------------------------------

CONIFER_ROWS = (
    ".......33.......",
    "......3023......",
    "......3023......",
    ".....302223.....",
    "....30222223....",
    "......3023......",
    "....30222223....",
    "...3022222223...",
    "..302222222223..",
    "...3022222223...",
    "..302222222223..",
    ".30222222222223.",
    ".30222222222223.",
    "...3022222223...",
    ".30222222222223.",
    "..302222222223..",
)


def crown_piece(top: int, left: int) -> Overlay:
    """One 8x8 quadrant of the authored crown, transparent outside the tree."""
    return stamp(*[row[left : left + 8] for row in CONIFER_ROWS[top : top + 8]])


CONIFER_TL = crown_piece(0, 0)
CONIFER_TR = crown_piece(0, 8)
CONIFER_BL = crown_piece(8, 0)
CONIFER_BR = crown_piece(8, 8)

# Trunk: a 4px column two rows under the crown, one root step each side and a
# dark contact shadow, stamped as an overlay so the grass under it is the
# field's own grass. A tall flared skirt made the tree read as a dress.
CONIFER_TRUNK_L = stamp(
    "......32",
    "......32",
    "......32",
    "......32",
    ".....332",
    "....3322",
    "..333333",
    "........",
)
CONIFER_TRUNK_R = CONIFER_TRUNK_L.mirror()

# Fallback for a 'T' cell with no room for a full 2x2 crown: a seedling, still
# drawn in the ground ramp so it sits on the field without a pale box.
SEEDLING = make(
    "ground",
    "11111111",
    "11132111",
    "11302111",
    "13211111",
    "11221111",
    "11321111",
    "11111111",
    "11111111",
)


# ---------------------------------------------------------------------------
# Tall grass: three blade clusters rooted on the bottom rows with light tips
# ---------------------------------------------------------------------------

TALL_GRASS_A = make(
    "ground",
    "11111111",
    "11011011",
    "12112121",
    "12112121",
    "12212221",
    "12212221",
    "13313331",
    "13313331",
)

TALL_GRASS_B = make(
    "ground",
    "11111111",
    "11101101",
    "12112121",
    "12212221",
    "12212221",
    "12312321",
    "13313331",
    "11311331",
)


# ---------------------------------------------------------------------------
# Raster helpers
# ---------------------------------------------------------------------------


class Canvas:
    """32x32 grid of tiles plus the house/path/rock bookkeeping."""

    def __init__(self) -> None:
        self.grid: list[list[Tile | None]] = [[None] * MAP_W for _ in range(MAP_H)]
        self.house_cells = village.house_tiles()
        self.tall_grass_cells = set(village.TALL_GRASS)

    def put(self, x: int, y: int, tile: Tile) -> None:
        self.grid[y][x] = tile

    def char(self, x: int, y: int) -> str:
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return "#"
        return village.MAP[y][x]

    def is_pathlike(self, x: int, y: int) -> bool:
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return False
        if (x, y) in self.house_cells:
            return False
        return village.MAP[y][x] in ".="

    def is_rock(self, x: int, y: int) -> bool:
        # Out of bounds counts as rock so the border ring has no rim on the
        # outside edge of the map.
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return True
        return village.MAP[y][x] == "#"

    def is_water(self, x: int, y: int) -> bool:
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return False
        return village.MAP[y][x] == "~"

    def is_tree_ground(self, x: int, y: int) -> bool:
        """Cells a crown may cover: plain grass or another pine cell."""
        if not (0 <= x < MAP_W and 0 <= y < MAP_H):
            return False
        if (x, y) in self.house_cells or (x, y) in self.tall_grass_cells:
            return False
        return village.MAP[y][x] in ",T"

    def side_mask(self, x: int, y: int, test) -> list[int]:
        return [side for side, (dx, dy) in enumerate(SIDE_STEPS) if test(x + dx, y + dy)]


# ---------------------------------------------------------------------------
# Layer builders
# ---------------------------------------------------------------------------


def grass_at(x: int, y: int, salt: int = 0) -> Tile:
    return GRASS_POOL[stable(x, y, len(GRASS_POOL), salt=salt)]


TURF_BY_SIDE = {
    NORTH: TURF_OVERHANG_N,
    EAST: TURF_OVERHANG_E,
    SOUTH: TURF_OVERHANG_S,
    WEST: TURF_OVERHANG_W,
}
WEAR_BY_SIDE = {NORTH: WEAR_N, EAST: WEAR_E, SOUTH: WEAR_S, WEST: WEAR_W}
SHORE_BY_SIDE = {NORTH: SHORE_N, EAST: SHORE_E, SOUTH: SHORE_S, WEST: SHORE_W}


def build_ground(canvas: Canvas) -> None:
    """Grass everywhere, with authored blends against the cliff and the road."""
    for y in range(MAP_H):
        for x in range(MAP_W):
            tile = grass_at(x, y)
            if canvas.char(x, y) == ",":
                rock_sides = canvas.side_mask(x, y, canvas.is_rock)
                if rock_sides:
                    tile = GRASS_CALM.merge(*[TURF_BY_SIDE[s] for s in rock_sides[:2]])
                else:
                    water_sides = canvas.side_mask(x, y, canvas.is_water)
                    if water_sides and stable(x, y, 3, salt=67) != 0:
                        tile = GRASS_CALM.merge(SHORE_BY_SIDE[water_sides[0]])
                    else:
                        path_sides = canvas.side_mask(x, y, canvas.is_pathlike)
                        if path_sides:
                            # Worn grass, but two sides at most so the tile set
                            # and the wear both stay legible.
                            tile = GRASS_CALM.merge(
                                *[WEAR_BY_SIDE[s] for s in path_sides[:2]]
                            )
            canvas.put(x, y, tile)


def build_rock(canvas: Canvas) -> None:
    """Border ring: lit face + rim where it faces the village, dark mass behind.

    The rim height and the face's strata both vary along the run, outcrop ledges
    are stamped every few cells and scrub replaces the rim on the odd cell, so
    no two stretches of wall repeat the same rhythm.
    """
    for y in range(MAP_H):
        for x in range(MAP_W):
            if village.MAP[y][x] != "#":
                continue
            open_sides = canvas.side_mask(x, y, lambda nx, ny: not canvas.is_rock(nx, ny))
            if not open_sides:
                canvas.put(x, y, ROCK_MASS[stable(x, y, len(ROCK_MASS), salt=3)])
                continue
            if stable(x, y, 9, salt=23) == 0:
                canvas.put(x, y, ROCK_SCRUB[stable(x, y, len(ROCK_SCRUB), salt=29)])
                continue
            face = ROCK_FACE[stable(x, y, len(ROCK_FACE), salt=41)]
            rims = ROCK_RIMS[stable(x, y, len(ROCK_RIMS), salt=43)]
            overlays = [rims[side] for side in open_sides[:2]]
            if stable(x, y, 5, salt=31) == 0:
                overlays.append(ROCK_BUMPS[open_sides[0]])
            canvas.put(x, y, face.merge(*overlays))


def build_water(canvas: Canvas) -> None:
    bridge_cells = {
        (x, y) for y in range(MAP_H) for x in range(MAP_W) if village.MAP[y][x] == "="
    }
    for y in range(MAP_H):
        for x in range(MAP_W):
            if village.MAP[y][x] != "~":
                continue
            # The deck shades the water on its south side, matching the light
            # that crests the cliff rims from the north.
            if (x, y - 1) in bridge_cells:
                canvas.put(x, y, WATER_SHADOW)
                continue
            west_land = village.MAP[y][x - 1] != "~"
            east_land = village.MAP[y][x + 1] != "~"
            if west_land:
                canvas.put(x, y, WATER_BANK_W[stable(x, y, 2, salt=2)])
            elif east_land:
                canvas.put(x, y, WATER_BANK_E[stable(x, y, 2, salt=2)])
            else:
                canvas.put(x, y, WATER_MID[stable(x, y, len(WATER_MID), salt=5)])


def build_bridge(canvas: Canvas) -> None:
    cells = [
        (x, y) for y in range(MAP_H) for x in range(MAP_W) if village.MAP[y][x] == "="
    ]
    if not cells:
        return
    xs = sorted({x for x, _y in cells})
    for x, y in cells:
        if x == xs[0]:
            canvas.put(x, y, BRIDGE_LEFT)
        elif x == xs[-1]:
            canvas.put(x, y, BRIDGE_RIGHT)
        else:
            canvas.put(x, y, BRIDGE_MID)


# Corner stamps keyed by the pair of sides that face open ground.
CORNER_BY_SIDES = {
    frozenset((NORTH, WEST)): CORNER_NW,
    frozenset((NORTH, EAST)): CORNER_NE,
    frozenset((SOUTH, EAST)): CORNER_SE,
    frozenset((SOUTH, WEST)): CORNER_SW,
}
# END_OPEN is authored for a road that continues to the west; rotate for the
# other three.
END_OPEN = {
    WEST: END_E,
    NORTH: END_E.rotate_cw(),
    EAST: END_E.rotate_cw().rotate_cw(),
    SOUTH: END_E.rotate_cw().rotate_cw().rotate_cw(),
}


def build_path(canvas: Canvas) -> None:
    """Road fill plus a verge that turns corners and closes dead ends."""
    for y in range(MAP_H):
        for x in range(MAP_W):
            if village.MAP[y][x] != ".":
                continue
            mask = [side for side in range(4) if canvas.is_pathlike(
                x + SIDE_STEPS[side][0], y + SIDE_STEPS[side][1]
            )]
            open_sides = [side for side in range(4) if side not in mask]
            vertical = NORTH in mask or SOUTH in mask
            fill_pool = PATH_FILL_V if vertical else PATH_FILL_H
            base = fill_pool[stable(x, y, len(fill_pool), salt=7)]
            verges = VERGES[stable(x, y, len(VERGES), salt=61)]

            if not mask:
                canvas.put(x, y, WORN_DIRT[stable(x, y, len(WORN_DIRT), salt=13)])
                continue
            if not open_sides:
                canvas.put(x, y, base)
                continue
            if len(open_sides) == 1:
                canvas.put(x, y, base.merge(verges[open_sides[0]]))
                continue
            if len(open_sides) == 2:
                pair = frozenset(open_sides)
                if pair in CORNER_BY_SIDES:
                    canvas.put(x, y, base.merge(CORNER_BY_SIDES[pair]))
                else:
                    canvas.put(x, y, base.merge(*[verges[side] for side in open_sides]))
                continue
            # Three open sides: a dead end. The road continues on the fourth.
            through = mask[0]
            canvas.put(x, y, END_OPEN[through])


# ---------------------------------------------------------------------------
# Cottages: a 4x4 cottage plus a one-tile yard strip, varied by house key
# ---------------------------------------------------------------------------

# yard side, chimney cell, ridge width, hedge height and the two yard props.
# Deterministic per key (village.HOUSES), so the five homes never repeat.
HOUSE_STYLE = {
    "a": {"yard": "left", "chimney": 1, "ridge": "wide", "hedge": "high",
          "props": ("garden", "well")},
    "b": {"yard": "right", "chimney": 2, "ridge": "narrow", "hedge": "low",
          "props": ("woodpile", "laundry")},
    "c": {"yard": "right", "chimney": 1, "ridge": "narrow", "hedge": "high",
          "props": ("woodpile", "garden")},
    "d": {"yard": "left", "chimney": 2, "ridge": "wide", "hedge": "low",
          "props": ("laundry", "well")},
    "e": {"yard": "right", "chimney": 2, "ridge": "wide", "hedge": "high",
          "props": ("flowerbed", "barrel")},
}


def cottage_rows(style: dict, window_top: Tile, window_base: Tile) -> list[list[Tile]]:
    """The 4x4 cottage as four rows of four tiles, door over the doorstep."""
    if style["ridge"] == "wide":
        peaks = [ROOF_PEAK_WIDE_L, ROOF_PEAK_WIDE_R]
    else:
        peaks = [ROOF_PEAK_NARROW_L, ROOF_PEAK_NARROW_R]
    ridge = list(peaks)
    chimney = style["chimney"]
    ridge[chimney - 1] = ROOF_CHIMNEY_L if chimney == 1 else ROOF_CHIMNEY_R
    roof_top = [ROOF_END_L, ridge[0], ridge[1], ROOF_END_R]
    roof_eave = [EAVE_END_L, EAVE_MID_A, EAVE_MID_B, EAVE_END_R]

    # Door cell index: the doorstep is footprint column 2, so a left-hand yard
    # puts the door second in the row and a right-hand yard puts it third.
    door_index = 1 if style["yard"] == "left" else 2
    if door_index == 1:
        inner_top, inner_base = [DOOR_TOP, window_top], [DOOR_BASE, window_base]
    else:
        inner_top, inner_base = [window_top, DOOR_TOP], [window_base, DOOR_BASE]
    wall_top = [WALL_POST_L, *inner_top, WALL_POST_R]
    wall_base = [WALL_POST_L_BASE, *inner_base, WALL_POST_R_BASE]
    return [roof_top, roof_eave, wall_top, wall_base]


def build_houses(canvas: Canvas) -> None:
    for house in village.HOUSES:
        key = house["key"]
        style = HOUSE_STYLE[key]
        x0, y0 = house["anchor"]
        left_yard = style["yard"] == "left"
        x_start = x0 + 1 if left_yard else x0
        yard_x = x0 if left_yard else x0 + 4

        window_top = WINDOW_BOX if key in "ad" else WINDOW
        window_base = WALL_BOX_UNDER if key in "ad" else WALL_UNDER
        rows = cottage_rows(style, window_top, window_base)
        for dy, row in enumerate(rows):
            for dx, tile in enumerate(row):
                canvas.put(x_start + dx, y0 + dy, tile)

        hedge_top = HEDGE_HIGH if style["hedge"] == "high" else HEDGE_LOW
        strip = [
            BUSH,
            hedge_top,
            YARD_PROPS[style["props"][0]],
            YARD_PROPS[style["props"][1]],
        ]
        for dy, tile in enumerate(strip):
            # Mirror the hedge so its outline always faces away from the wall.
            canvas.put(yard_x, y0 + dy, tile if left_yard else tile.mirror())


def build_tall_grass(canvas: Canvas) -> None:
    variants = (TALL_GRASS_A, TALL_GRASS_B)
    for index, (x, y) in enumerate(sorted(village.TALL_GRASS, key=lambda c: (c[1], c[0]))):
        canvas.put(x, y, variants[index % len(variants)])


def build_pebbles(canvas: Canvas) -> None:
    for y in range(MAP_H):
        for x in range(MAP_W):
            if village.MAP[y][x] == "o":
                canvas.put(x, y, (PEBBLES_A, PEBBLES_B)[stable(x, y, 2, salt=19)])


def build_boulder(canvas: Canvas) -> None:
    for y in range(MAP_H):
        for x in range(MAP_W):
            if village.MAP[y][x] == "b":
                canvas.put(x, y, BOULDER)


def build_trees(canvas: Canvas) -> None:
    """Stamp 2x2 crowns plus a trunk row where the map asks for a pine.

    The trunk hangs under the middle of the 16px crown instead of under one
    quadrant, and a tree claims its whole footprint so neighbouring 'T' cells
    become grass under the crown rather than stacking a second tree on the same
    block. Tall-grass cells are never covered: they hide pickups.
    """
    cells = [
        (x, y) for y in range(MAP_H) for x in range(MAP_W) if village.MAP[y][x] == "T"
    ]
    occupied: set[tuple[int, int]] = set()
    for x, y in cells:
        if (x, y) in occupied:
            continue
        placed = False
        for cx, cy in ((x, y), (x - 1, y), (x, y - 2), (x - 1, y - 2)):
            if cx < 0 or cy < 0 or cx + 1 >= MAP_W or cy + 2 >= MAP_H:
                continue
            canopy = [(cx, cy), (cx + 1, cy), (cx, cy + 1), (cx + 1, cy + 1)]
            if any(not canvas.is_tree_ground(px, py) for px, py in canopy):
                continue
            trunk = [(cx, cy + 2), (cx + 1, cy + 2)]
            if any(
                not canvas.is_tree_ground(tx, ty) or (tx, ty) in occupied
                for tx, ty in trunk
            ):
                continue
            tiles = (CONIFER_TL, CONIFER_TR, CONIFER_BL, CONIFER_BR)
            for (px, py), overlay in zip(canopy, tiles):
                canvas.put(px, py, grass_at(px, py, salt=23).merge(overlay))
            for (tx, ty), overlay in zip(trunk, (CONIFER_TRUNK_L, CONIFER_TRUNK_R)):
                canvas.put(tx, ty, grass_at(tx, ty, salt=17).merge(overlay))
            for py in range(cy, cy + 3):
                for px in (cx, cx + 1):
                    occupied.add((px, py))
            placed = True
            break
        if not placed:
            canvas.put(x, y, SEEDLING)
            occupied.add((x, y))


def build() -> Canvas:
    canvas = Canvas()
    build_ground(canvas)
    build_rock(canvas)
    build_water(canvas)
    build_bridge(canvas)
    build_path(canvas)
    build_houses(canvas)
    build_tall_grass(canvas)
    build_pebbles(canvas)
    build_boulder(canvas)
    build_trees(canvas)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if canvas.grid[y][x] is None:
                raise AssertionError(f"empty tile at {x},{y}")
    return canvas


def render(canvas: Canvas) -> tuple[Image.Image, list[int], int]:
    image = Image.new("RGB", (BG_W, BG_H))
    tile_slots: list[int] = []
    unique: set[tuple[int, tuple[int, ...]]] = set()
    for y in range(MAP_H):
        for x in range(MAP_W):
            tile = canvas.grid[y][x]
            colors = PALETTE_RGB[tile.palette]
            tile_slots.append(tile.slot)
            unique.add(tile.key())
            for py in range(TILE):
                for px in range(TILE):
                    image.putpixel(
                        (x * TILE + px, y * TILE + py),
                        colors[int(tile.rows[py][px])],
                    )
    if image.size != (BG_W, BG_H):
        raise AssertionError("bad image size")
    if len(tile_slots) != MAP_W * MAP_H:
        raise AssertionError("bad tile count")
    if len(unique) > MAX_UNIQUE_TILES:
        raise AssertionError(f"{len(unique)} unique tiles exceeds L-03 ({MAX_UNIQUE_TILES})")
    return image, tile_slots, len(unique)


# ---------------------------------------------------------------------------
# Sidecar (same schema as the project's working storm_night background)
# ---------------------------------------------------------------------------


def rle(values: list[int]) -> str:
    """GB Studio compress8bitNumberArray encoding: value then count ('+'/'!')."""
    out: list[str] = []
    last = -1
    count = 0
    for value in values:
        if value != last:
            if count == 1:
                out.append("!")
            elif count > 0:
                out.append(f"{count:x}+")
            count = 0
            last = value
            out.append(f"{value % 256:02x}")
        count += 1
    if count == 1:
        out.append("!")
    elif count > 0:
        out.append(f"{count:x}+")
    return "".join(out)


def decode_rle(text: str) -> list[int]:
    values: list[int] = []
    i = 0
    while i < len(text):
        value = int(text[i : i + 2], 16)
        i += 2
        if i >= len(text):
            values.append(value)
            break
        if text[i] == "!":
            count = 1
            i += 1
        else:
            end = text.index("+", i)
            count = int(text[i:end], 16)
            i = end + 1
        values.extend([value] * count)
    return values


def sidecar_resource(tile_slots: list[int]) -> dict:
    encoded = rle(tile_slots)
    if decode_rle(encoded) != tile_slots:
        raise AssertionError("tileColors RLE does not round-trip")
    return {
        "_resourceType": "background",
        "id": str(uuid.uuid5(UUID_NAMESPACE, f"modretro-chromatic:mr-cfe:{ASSET_NAME}")),
        "name": ASSET_NAME,
        "symbol": SYMBOL,
        "tileColors": encoded,
        "filename": f"{ASSET_NAME}.png",
        "width": MAP_W,
        "height": MAP_H,
        "imageWidth": BG_W,
        "imageHeight": BG_H,
        "autoColor": False,
    }


def write_sidecar(resource: dict) -> None:
    if SIDECAR_PATH.exists():
        existing = json.loads(SIDECAR_PATH.read_text(encoding="utf-8"))
        if existing.get("id") != resource["id"]:
            raise SystemExit(
                f"refusing to overwrite {SIDECAR_PATH.name}: it belongs to "
                f"id {existing.get('id')} (expected {resource['id']})"
            )
    SIDECAR_PATH.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Review evidence
# ---------------------------------------------------------------------------


def write_evidence(image: Image.Image) -> list[Path]:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    map_1x = image.copy()
    path_1x = EVIDENCE_DIR / "village_map_1x.png"
    map_1x.save(path_1x, format="PNG", optimize=False)
    written.append(path_1x)

    map_2x = image.resize((BG_W * 2, BG_H * 2), Image.NEAREST)
    path_2x = EVIDENCE_DIR / "village_map_2x.png"
    map_2x.save(path_2x, format="PNG", optimize=False)
    written.append(path_2x)

    # Exactly one hardware screen, 160x144 = 20x18 tiles, on the main path.
    box = (8 * TILE, 12 * TILE, 8 * TILE + 160, 12 * TILE + 144)
    screen = image.crop(box)
    path_screen = EVIDENCE_DIR / "village_screen_160x144.png"
    screen.save(path_screen, format="PNG", optimize=False)
    written.append(path_screen)

    return written


def main() -> None:
    ASSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas = build()
    image, tile_slots, unique_count = render(canvas)
    image.save(ASSET_PATH, format="PNG", optimize=False)
    write_sidecar(sidecar_resource(tile_slots))
    evidence = write_evidence(image)
    print(
        f"generated {ASSET_PATH.relative_to(PROJECT_DIR)}: "
        f"{image.width}x{image.height}px, {MAP_W}x{MAP_H} tiles, "
        f"{unique_count}/{MAX_UNIQUE_TILES} unique tiles"
    )
    counts: dict[int, int] = {}
    for slot in tile_slots:
        counts[slot] = counts.get(slot, 0) + 1
    print(f"cells per slot: {dict(sorted(counts.items()))}")
    for path in evidence:
        print(f"evidence: {path}")


if __name__ == "__main__":
    main()
