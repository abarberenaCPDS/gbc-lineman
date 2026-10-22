"""Deterministically render the storm-night mountain background.

The level module is the source of truth for dimensions, palette colors, and
collision/feature placement. Run from any directory with the project's
toolchain Python:

    python tools/make_art.py
"""

from __future__ import annotations

import json
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
assert PALETTE_SLOTS == {
    "sky": 0,
    "rock": 1,
    "timber": 2,
    "glow": 3,
    "moss": 4,
    "hazard": 5,
    "cable": 6,
}


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
    """Quiet cave void with a few broad, dim blue stone silhouettes."""
    tile = Tile("sky", 0)
    for py in range(level.TILE):
        wy = y * level.TILE + py
        for px in range(level.TILE):
            wx = x * level.TILE + px
            # A distant arch and low cavern shoulders add depth without
            # turning the playable negative space into a patterned sky.
            arch = 105 + int(17 * abs((wx - 74) / 74))
            left_shoulder = wx < 31 and wy > 136 + (wx // 3)
            right_shoulder = wx > 125 and wy > 118 + ((159 - wx) // 3)
            if (wy > arch and wy < 193) or left_shoulder or right_shoulder:
                tile.set(px, py, 1)

    # Tiny, deliberate cave glints: one pixel at most in a tile, never rain.
    if variant(x, y, 17, 4) == 0 and y not in (6, 7, 8, 9):
        tile.set((x * 3 + y) % 8, (x + y * 5) % 8, 2)
    return tile


BRIDGE_SEGMENTS = (
    (33, 0, 6),
    (21, 13, 18),
    (18, 3, 5),
    (12, 14, 16),
)


def is_bridge(row: int, x: int) -> bool:
    return any(
        row == bridge_row and x0 <= x <= x1
        for bridge_row, x0, x1 in BRIDGE_SEGMENTS
    )


def make_platform_tile(x: int, y: int) -> Tile:
    """A one-way ledge: vivid moss lip, quiet dark face, readable underside."""
    tile = Tile("moss", 0)
    for px in range(8):
        tile.set(px, 0, 3 if px % 5 else 2)
        tile.set(px, 1, 2 if px % 3 else 1)
    tile.rect(0, 2, 7, 7, 0)
    style = variant(x, y, 4, 7)
    if style in (0, 2):
        tile.set(1 + style, 3, 1)
        tile.set(2 + style, 4, 2)
    if style == 3:
        tile.set(6, 5, 1)
    return tile


def make_bridge_tile(x: int, y: int) -> Tile:
    """Chunky, hand-built plank deck with beam shadow and occasional pegs."""
    tile = Tile("timber", 0)
    tile.rect(0, 0, 7, 0, 3)
    tile.rect(0, 1, 7, 1, 2)
    tile.rect(0, 2, 7, 2, 1)
    tile.rect(0, 3, 7, 3, 0)
    tile.rect(0, 4, 7, 4, 1)
    tile.rect(0, 5, 7, 7, 0)
    style = variant(x, y, 4, 13)
    if style in (0, 2):
        seam = 2 + style
        tile.rect(seam, 0, seam, 2, 1)
        tile.set((seam + 1) % 8, 1, 3)
    if style == 1:
        tile.set(1, 0, 2)
        tile.set(6, 0, 2)
    if (x + y) % 3 == 0:
        tile.set((x * 3) % 8, 2, 3)
    return tile


def make_solid_tile(x: int, y: int, top: bool, left: bool, right: bool) -> Tile:
    """Vertical cave walls and floor, with restrained green edge lighting."""
    if top or left or right:
        tile = Tile("moss", 0)
        if top:
            tile.rect(0, 0, 7, 0, 3)
            tile.set((x + 2) % 8, 1, 2)
        if left:
            for py in range(1, 8):
                tile.set(0, py, 3 if py % 3 == 0 else 2)
        if right:
            for py in range(1, 8):
                tile.set(7, py, 3 if py % 3 == 0 else 2)
        tile.set((x * 3 + y) % 8, 5, 1)
        return tile

    tile = Tile("rock", 0)
    tile.rect(0, 0, 7, 7, 1)
    style = variant(x, y, 5, 9)
    if style in (0, 3):
        tile.rect(1, 3, 3, 3, 0)
        tile.set(3, 4, 2)
    elif style == 1:
        tile.set(5, 2, 2)
        tile.set(4, 3, 1)
    return tile


def make_hazard_tile(x: int, y: int, flood: bool) -> Tile:
    if flood:
        tile = Tile("cable", 0)
        tile.rect(0, 6, 7, 7, 1)
        wave = variant(x, y, 4, 15)
        for px in range(8):
            if (px + wave) % 4 in (0, 1):
                tile.set(px, 5, 2)
        tile.set((x + y) % 8, 4, 3)
        return tile

    # Small, sharp spike clusters read as hazards without filling their gap.
    tile = Tile("hazard", 0)
    for center, height in ((1, 2), (4, 4), (7, 3)):
        for rise in range(height):
            py = 6 - rise
            half_width = max(0, (rise - 1) // 2)
            for px in range(
                max(0, center - half_width), min(7, center + half_width) + 1
            ):
                tile.set(px, py, 3 if rise == height - 1 else 2)
    tile.rect(0, 7, 7, 7, 1)
    return tile


def make_house_wall(x: int, y: int) -> Tile:
    tile = Tile("timber", 0)
    tile.rect(0, 0, 7, 7, 1)
    style = variant(x, y, 4, 22)
    # Upright corner posts and a few broad, quiet plank seams.
    if x in (13, 18):
        tile.rect(0 if x == 13 else 6, 0, 1 if x == 13 else 7, 7, 3)
    else:
        tile.set(0, 2 + style, 2)
        tile.rect(2, 5 + (style % 2), 5, 5 + (style % 2), 0)
    return tile


def make_house_roof(x: int, y: int) -> Tile:
    tile = Tile("rock", 0)
    tile.rect(0, 3, 7, 7, 1)
    tile.rect(0, 2, 7, 2, 2)
    tile.rect(0, 1, 7, 1, 1)
    tile.set((x + y) % 8, 0, 2)
    tile.set((x * 3 + 2) % 8, 3, 3)
    return tile


def make_window_tile() -> Tile:
    tile = Tile("glow", 0)
    tile.rect(1, 1, 6, 6, 1)
    tile.rect(2, 2, 5, 5, 3)
    tile.rect(3, 2, 4, 5, 2)
    tile.set(3, 3, 3)
    return tile


def make_door_tile(side: str) -> Tile:
    tile = Tile("timber", 1)
    tile.rect(0, 0, 7, 0, 2)
    tile.rect(0, 1, 0, 7, 2)
    tile.rect(7, 1, 7, 7, 2)
    if side == "left":
        tile.rect(1, 1, 3, 7, 0)
        tile.set(3, 4, 3)
    else:
        tile.rect(4, 1, 6, 7, 0)
        tile.set(4, 4, 3)
    return tile


def make_pine_tile(tile_x: int, tile_y: int, origin_x: int, origin_y: int) -> Tile:
    """One 8x8 slice of a low-contrast, three-tile distant pine silhouette."""
    tile = Tile("moss", 0)
    for py in range(8):
        world_y = (tile_y - origin_y) * 8 + py
        for px in range(8):
            world_x = (tile_x - origin_x) * 8 + px
            if world_y < 19:
                half = min(11, 1 + world_y * 3 // 5)
                inside = abs(world_x - 11) <= half
                branch_edge = abs(world_x - 11) == half
                if inside:
                    tile.set(px, py, 2 if branch_edge and world_y % 3 == 0 else 1)
            elif world_y < 24 and 10 <= world_x <= 12:
                tile.set(px, py, 1)
    return tile


def put_cable_scene(tiles: list[list[Tile]]) -> None:
    """Paint one little pole-to-pole cyan span in otherwise open cave space."""
    cable_cells: dict[tuple[int, int], Tile] = {}

    def cable_pixel(px: int, py: int, color: int) -> None:
        tx, ty = px // 8, py // 8
        if not (0 <= tx < level.MAP_W and 0 <= ty < level.MAP_H):
            return
        key = (ty, tx)
        if key not in cable_cells:
            cable_cells[key] = Tile("cable", 0)
        cable_cells[key].set(px % 8, py % 8, color)

    # Slim timber poles and short crossarms, entirely above the row-9 ledge.
    for pole_x in (8, 48):
        tx = pole_x // 8
        for ty in (6, 7, 8):
            tile = Tile("timber", 0)
            pole_px = pole_x % 8
            tile.rect(max(0, pole_px - 1), 0, min(7, pole_px), 7, 1)
            if ty == 6:
                tile.rect(max(0, pole_px - 3), 1, min(7, pole_px + 3), 1, 2)
                tile.set(pole_px, 0, 3)
            tiles[ty][tx] = tile

    # Fine sagging conductor; individual pixels quantize cleanly at 8x8.
    for px in range(9, 48):
        py = 57 + ((px - 9) * (px - 9)) // 900
        cable_pixel(px, py, 2)
        if px in (10, 47):
            cable_pixel(px, py + 1, 1)

    # Two compact star glints, echoing the reference cable scenes.
    gx, gy = 30, 58
    for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
        cable_pixel(gx + dx, gy + dy, 3 if (dx, dy) == (0, 0) else 2)
    cable_pixel(43, 58, 3)
    cable_pixel(42, 58, 2)
    cable_pixel(44, 58, 2)

    for (ty, tx), tile in cable_cells.items():
        tiles[ty][tx] = tile

    # The left pole shares a tile with the cable; ink its fine dark silhouette
    # into those cable tiles instead of letting either graphic erase the other.
    for ty in (7, 8):
        key = (ty, 1)
        tile = cable_cells.get(key, Tile("cable", 0))
        for py in range(8):
            tile.set(0, py, 1)
            tile.set(1, py, 1)
        tiles[ty][1] = tile


def decorate_house(tiles: list[list[Tile]]) -> None:
    """Small timber hut on the open summit shelf, with two lit windows."""
    for x in range(14, 18):
        tiles[1][x] = make_house_roof(x, 1)
    for x in range(13, 19):
        tiles[2][x] = make_house_roof(x, 2)
    for y in (3, 4, 5):
        for x in range(13, 19):
            tiles[y][x] = make_house_wall(x, y)
    tiles[4][14] = make_window_tile()
    tiles[4][17] = make_window_tile()
    tiles[5][15] = make_door_tile("left")
    tiles[5][16] = make_door_tile("right")


def decorate_pines(tiles: list[list[Tile]]) -> None:
    """A single small stand of distant pines, clear of every collision row."""
    for ty in range(12, 15):
        for tx in range(0, 3):
            tiles[ty][tx] = make_pine_tile(tx, ty, 0, 12)


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
                row_tiles.append(make_bridge_tile(x, y) if is_bridge(y, x) else make_platform_tile(x, y))
            elif (y, x) in solid:
                top = (y - 1, x) not in solid
                left = (y, x - 1) not in solid
                right = (y, x + 1) not in solid
                row_tiles.append(make_solid_tile(x, y, top, left, right))
            elif (y, x) in hazard_cells:
                row_tiles.append(make_hazard_tile(x, y, hazard_cells[(y, x)]))
            else:
                row_tiles.append(make_sky_tile(x, y))
        tiles.append(row_tiles)

    decorate_house(tiles)
    decorate_pines(tiles)
    put_cable_scene(tiles)
    art_only_cells = (
        [(x, y) for y in range(1, 6) for x in range(13, 19)]
        + [(x, y) for y in range(12, 15) for x in range(3)]
        + [(x, y) for y in range(6, 9) for x in range(1, 7)]
    )
    assert all(collision[y][x] == level.COL_EMPTY for x, y in art_only_cells)

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
    assert set(tile_colors) <= set(range(7)), "UI palette slot 7 is reserved"
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
