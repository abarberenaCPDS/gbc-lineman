"""Deterministically render the storm-night mountain background.

The level module is the source of truth for dimensions, palette colors, and
collision/feature placement. Run from any directory with the project's
toolchain Python:

    python tools/make_art.py
"""

from __future__ import annotations

import json
import math
import sys
import uuid
from pathlib import Path

from PIL import Image

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
import level  # noqa: E402  (the sibling module is the authoritative source)


ASSET_NAME = "storm_night"
ASSET_PATH = PROJECT_DIR / "assets" / "backgrounds" / f"{ASSET_NAME}.png"
SIDECAR_PATH = Path(f"{ASSET_PATH}.gbsres")
UUID_NAMESPACE = uuid.UUID("717f5b5a-4e17-5f80-ae10-6afbdd2827db")

PALETTES = {
    name: tuple(tuple(int(color[i : i + 2], 16) for i in (0, 2, 4)) for color in colors)
    for name, colors in level.BG_PALETTES
}
PALETTE_SLOTS = {name: index for index, (name, _colors) in enumerate(level.BG_PALETTES)}


class Tile:
    """A single 8x8 tile encoded as indices into one GB Studio palette."""

    def __init__(self, palette: str, fill: int = 0) -> None:
        self.palette_name = palette
        self.palette = PALETTE_SLOTS[palette]
        self.pixels = [[fill for _ in range(level.TILE)] for _ in range(level.TILE)]

    def set(self, x: int, y: int, color: int) -> None:
        if 0 <= x < level.TILE and 0 <= y < level.TILE:
            self.pixels[y][x] = color

    def rect(self, x0: int, y0: int, x1: int, y1: int, color: int) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, color)

    def pattern(self) -> tuple[int, ...]:
        return tuple(pixel for row in self.pixels for pixel in row)


def variant(x: int, y: int, count: int, salt: int = 0) -> int:
    """Small coordinate hash: deterministic art variation without RNG state."""
    return (x * 73 + y * 151 + x * y * 17 + salt * 199 + 29) % count


def make_sky_tile(x: int, y: int) -> Tile:
    # Storm clouds deepen toward the horizon, while the ridges remain legible
    # as layered silhouettes in the same sky palette.
    base = 0 if y < 5 else 1 if y < 10 else 2
    tile = Tile("sky", base)

    # Broken cloud bands, with finite patterns so the map stays comfortably
    # below the 384 unique-background-tile hardware budget.
    cloud = variant(x, y, 7, 2)
    if y in (2, 3, 7, 8, 11) and cloud in (0, 1, 2, 4):
        start = (x * 3 + cloud) % 5
        tile.rect(start, 1, min(7, start + 2 + cloud % 2), 1, 2)
        if cloud % 3 == 0:
            tile.set((start + 1) % 8, 2, 1)

    # Sparse stars / rain flecks. Diagonal rain uses muted sky tones to keep
    # every tile within this palette's four-color limit.
    fleck = variant(x, y, 11, 5)
    if y < 9 and fleck in (0, 4):
        tile.set((x * 5 + y * 3) % 8, (x + y * 2) % 8, 3)
    elif fleck in (1, 6, 9):
        px = (x * 3 + y * 5) % 8
        py = (x * 7 + y) % 8
        tile.set(px, py, 1)
        if (x + y) % 3 == 0:
            tile.set((px + 1) % 8, (py + 2) % 8, 1)

    # Two distant ridge silhouettes. Their scalloped edges create a readable
    # mountain horizon without obscuring the playable platform silhouettes.
    world_top = y * level.TILE
    for py in range(level.TILE):
        world_y = world_top + py
        # Smooth, overlapping silhouettes create broad mountain peaks rather
        # than a noisy horizontal band. The ridge line rises into the sky and
        # stays behind the foreground platform art.
        ridge_a = 58 + int(19 * abs(math.sin((x + 1) * 0.37))) + (x % 3)
        ridge_b = 92 + int(22 * abs(math.sin((x + 4) * 0.27))) + (x % 2)
        if world_y >= ridge_a:
            tile.rect(0, py, 7, py, 2)
            if world_y == ridge_a:
                tile.set((x * 3 + py) % 8, py, 3)
        if world_y >= ridge_b:
            tile.rect(0, py, 7, py, 1)

    return tile


def make_rock_tile(x: int, y: int, platform: bool, moss: bool = False) -> Tile:
    tile = Tile("moss" if moss else "rock")
    if platform:
        # Bright wet lip and a darker underside align the art with the exact
        # one-way collision row in level.PLATFORMS.
        tile.rect(0, 0, 7, 0, 3)
        tile.rect(0, 1, 7, 1, 2)
        tile.rect(0, 2, 7, 7, 1)
    else:
        tile.rect(0, 0, 7, 7, 1)
        tile.rect(0, 0, 7, 1, 2)

    # Deliberately repeat a small set of stone cracks and rain sheen patterns.
    style = variant(x, y, 6, 9)
    if style in (0, 3):
        tile.set(1 + style % 3, 3, 0)
        tile.set(2 + style % 3, 4, 2)
    elif style in (1, 5):
        tile.set(5, 2 + style % 3, 3 if platform else 2)
        tile.set(4, 3 + style % 2, 2)
    if moss:
        # Small lush patches stand out against slate; the entire tile still
        # uses only the declared moss palette.
        tile.set(2 + style % 4, 2 + (style // 2), 2)
        tile.set(3 + style % 4, 3 + (style // 2), 3)
    return tile


def make_hazard_tile(x: int, y: int, flood: bool) -> Tile:
    tile = Tile("hazard", 0)
    if flood:
        tile.rect(0, 5, 7, 7, 1)
        wave = variant(x, y, 3, 15)
        for px in range(8):
            if (px + wave) % 4 in (0, 1):
                tile.set(px, 4, 2)
        tile.set((x + y) % 8, 3, 3)
    else:
        # A crackling diagonal live-wire spark, placed in the clear gap between
        # platform rows as specified by level.HAZARDS.
        offset = variant(x, y, 4, 21)
        for i in range(5):
            px = (i + offset) % 8
            py = 1 + i
            tile.set(px, py, 2)
            tile.set(px, py + 1, 1)
        tile.set((offset + 5) % 8, 6, 3)
    return tile


def make_beacon_tile() -> Tile:
    tile = Tile("glow", 0)
    tile.rect(2, 4, 5, 6, 1)
    tile.set(3, 4, 2)
    tile.set(4, 4, 3)
    tile.set(1, 7, 2)
    tile.set(6, 7, 2)
    return tile


def make_background() -> tuple[Image.Image, list[int], int]:
    collision = level.collision_grid()
    platforms = {(row, x) for row, x0, x1 in level.PLATFORMS for x in range(x0, x1 + 1)}
    solid = {
        (row, x)
        for x0, x1, row0, row1 in level.SOLID_BLOCKS
        for row in range(row0, row1 + 1)
        for x in range(x0, x1 + 1)
    }
    hazard_cells: dict[tuple[int, int], bool] = {}
    for x0, x1, row0, row1 in level.HAZARDS:
        is_flood = row0 == row1 == 31
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                hazard_cells[(row, x)] = is_flood

    tiles: list[list[Tile]] = []
    for y in range(level.MAP_H):
        row_tiles: list[Tile] = []
        for x in range(level.MAP_W):
            if (y, x) in platforms:
                row_tiles.append(make_rock_tile(x, y, platform=True, moss=variant(x, y, 13) == 0))
            elif (y, x) in solid:
                row_tiles.append(make_rock_tile(x, y, platform=False, moss=variant(x, y, 13) == 0))
            elif (y, x) in hazard_cells:
                row_tiles.append(make_hazard_tile(x, y, hazard_cells[(y, x)]))
            else:
                row_tiles.append(make_sky_tile(x, y))
        tiles.append(row_tiles)

    # A tiny storm beacon on a distant ridge gives the scene a warm focal point.
    # It is background scenery and does not alter level collision or actors.
    beacon_x, beacon_y = 15, 6
    if collision[beacon_y][beacon_x] == level.COL_EMPTY:
        tiles[beacon_y][beacon_x] = make_beacon_tile()

    image = Image.new("RGB", (level.BG_W, level.BG_H))
    tile_colors: list[int] = []
    unique_tiles: set[tuple[int, tuple[int, ...]]] = set()
    for ty, row in enumerate(tiles):
        for tx, tile in enumerate(row):
            colors = PALETTES[tile.palette_name]
            used = set(tile.pattern())
            assert len(used) <= 4, f"tile ({tx},{ty}) uses {len(used)} colors"
            assert all(0 <= index < len(colors) for index in used)
            tile_colors.append(tile.palette)
            unique_tiles.add((tile.palette, tile.pattern()))
            for py in range(level.TILE):
                for px in range(level.TILE):
                    image.putpixel(
                        (tx * level.TILE + px, ty * level.TILE + py),
                        colors[tile.pixels[py][px]],
                    )

    assert image.size == (level.BG_W, level.BG_H)
    assert len(tile_colors) == level.MAP_W * level.MAP_H
    assert len(unique_tiles) <= 384, f"{len(unique_tiles)} unique tiles exceeds L-03 budget"
    return image, tile_colors, len(unique_tiles)


def write_sidecar(tile_colors: list[int]) -> None:
    resource = {
        "_resourceType": "background",
        "id": str(uuid.uuid5(UUID_NAMESPACE, f"modretro-chromatic:mr-cfe:{ASSET_NAME}")),
        "name": ASSET_NAME,
        "symbol": "bg_storm_night",
        "tileColors": level.rle(tile_colors),
        "filename": f"{ASSET_NAME}.png",
        "width": level.MAP_W,
        "height": level.MAP_H,
        "imageWidth": level.BG_W,
        "imageHeight": level.BG_H,
        "autoColor": False,
    }
    SIDECAR_PATH.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    ASSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    image, tile_colors, unique_count = make_background()
    image.save(ASSET_PATH, format="PNG", optimize=False)
    write_sidecar(tile_colors)
    print(
        f"generated {ASSET_PATH.relative_to(PROJECT_DIR)}: {image.width}x{image.height}px, "
        f"{level.MAP_W}x{level.MAP_H} tiles, {unique_count}/384 unique tiles"
    )


if __name__ == "__main__":
    main()
