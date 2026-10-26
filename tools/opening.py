"""Shared art/geometry contract for the isolated M-V1 service-opening fixture.

Only this module owns the opening's palette slots, geometry and stable IDs.
It does not replace the climb's sources or mutate shared legacy palettes.
"""
from __future__ import annotations

import uuid

NAMESPACE = uuid.UUID("2765282c-9a26-5e6d-8c4f-d21f5904a3a9")
MAP_W, MAP_H, TILE = 20, 18, 8
START = (1, 15)
PANEL = (4, 15)
MARTA = (8, 15)
SOLID_BLOCKS = [(0, 19, 16, 17), (17, 19, 13, 15)]
PLATFORMS = [(13, 13, 16), (10, 11, 18)]
SOLID, ONE_WAY = 15, 1
# The right-hand awning (row 10, x11-18) is the one clear onward ledge. Its top
# is the standing row 9; the exit covers the open right edge beyond its end, so
# the hero reaches it by walking across the awning. Rect is (x, y, w, h) tiles.
EXIT = (18, 6, 2, 4)
EXIT_STAND = (17, 9)   # last safe feet tile before the exit, on the awning top
EXIT_NUDGE = (16, 9)   # two tiles back; used when service is not yet restored
GATE = (18, 9)         # service gate actor on the awning end, feet on row 9
BG_PALETTES = [
    ("night", ["0B101E", "172338", "2C4054", "52647B"]),
    ("stone", ["111A24", "263642", "475664", "829091"]),
    ("timber", ["211F26", "453A39", "75604E", "B39B70"]),
    ("window", ["151E2A", "22354A", "3B5870", "718D9C"]),
    ("foliage", ["0F1D23", "243D3C", "46635A", "91A67A"]),
    ("metal", ["17232E", "3D5364", "7791A3", "C7DCE1"]),
    ("earth", ["101920", "263031", "454A40", "78806B"]),
]
POWERED_WINDOW = ["201D23", "704828", "C38849", "F1D49A"]
# Intended hardware indices, not the editor's palette serialization. The scene
# generator adapts these ramps to GB Studio's [p0,p0,p1,p3] object expansion.
SPRITE_PALETTES = [
    ("worker", ["000000", "F2E6C9", "D78B43", "152431"]),
    ("marta", ["000000", "E8C8AB", "8E769B", "1A2637"]),
    ("terminal", ["000000", "C7DCE1", "F1C879", "142332"]),
]


def resource_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, "mr-cfe:service-opening:" + key))


def collision_grid() -> list[list[int]]:
    grid = [[0] * MAP_W for _ in range(MAP_H)]
    for row, x0, x1 in PLATFORMS:
        for x in range(x0, x1 + 1):
            grid[row][x] = 1
    for x0, x1, y0, y1 in SOLID_BLOCKS:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                grid[y][x] = 15
    return grid


def standing(x: int, y: int, body_rows: int = 3, grid: list[list[int]] | None = None) -> bool:
    """True if feet on tile (x, y) rest on ground and the body fits above it.

    body_rows is the hero height in tiles (3 for the 24px default, 2 for 16px).
    One-way platforms count as ground from above but never block the body.
    """
    grid = grid or collision_grid()
    if not (0 <= x < MAP_W and 0 <= y < MAP_H - 1) or y - body_rows + 1 < 0:
        return False
    if grid[y][x] == SOLID or grid[y + 1][x] not in (ONE_WAY, SOLID):
        return False
    return all(grid[y - k][x] != SOLID for k in range(body_rows))


def reachable(start: tuple[int, int], body_rows: int = 3,
              max_rise: int = 3, max_jump_dx: int = 3) -> set[tuple[int, int]]:
    """Standing tiles reachable from start by walking, dropping and jumping.

    This is a coarse model: a jump may rise up to max_rise tiles and travel up to
    max_jump_dx tiles, and its arc is not traced. It guards the authored layout
    against unreachable exits; in-engine jump feel still needs playtesting.
    """
    grid = collision_grid()
    seen = {start}
    todo = [start]
    while todo:
        x, y = todo.pop()
        moves = []
        for dx in (-1, 1):
            nx = x + dx
            if not 0 <= nx < MAP_W:
                continue
            if standing(nx, y, body_rows, grid):
                moves.append((nx, y))
                continue
            # Step off an edge: fall straight down through open tiles to ground.
            for ny in range(y, MAP_H - 1):
                if grid[ny][nx] == SOLID:
                    break
                if standing(nx, ny, body_rows, grid):
                    moves.append((nx, ny))
                    break
        for dx in range(-max_jump_dx, max_jump_dx + 1):
            for rise in range(1, max_rise + 1):
                if standing(x + dx, y - rise, body_rows, grid):
                    moves.append((x + dx, y - rise))
        for move in moves:
            if move not in seen:
                seen.add(move)
                todo.append(move)
    return seen


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == 18 and all(len(row) == 20 for row in grid)
    for x, y in (START, PANEL, MARTA):
        assert grid[y][x] == 0 and grid[y + 1][x] == 15
    assert all(len(colors) == 4 for _, colors in BG_PALETTES + SPRITE_PALETTES)
    assert len(BG_PALETTES) == 7  # UI slot 7 reserved
    assert all(set(colors) <= set("0123456789ABCDEF") for _, ramp in BG_PALETTES for colors in ramp)
    x0, y0, w, h = EXIT
    assert 0 <= x0 and x0 + w <= MAP_W and 0 <= y0 and y0 + h <= MAP_H
    assert h >= 3, "exit must span the 24px hero body"
    tiles = {(x, y) for x in range(x0, x0 + w) for y in range(y0, y0 + h)}
    assert all(grid[y][x] == 0 for x, y in tiles), "exit must sit in open air"
    assert not tiles & {START, PANEL, MARTA}
    sx, sy = EXIT_STAND
    assert sx == x0 - 1 and y0 <= sy - 2 and sy < y0 + h, "stand tile must abut the exit"
    assert standing(sx, sy, 3, grid) and standing(sx, sy, 2, grid)
    nx, ny = EXIT_NUDGE
    assert standing(nx, ny, 3, grid) and x0 - nx >= 2
    gx, gy = GATE
    assert gx == x0 and gy == sy, "gate sits on the awning end beside the exit"
    assert standing(gx, gy, 3, grid), "gate must stand on the awning"


_self_check()
