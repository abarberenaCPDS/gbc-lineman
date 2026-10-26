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


def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == 18 and all(len(row) == 20 for row in grid)
    for x, y in (START, PANEL, MARTA):
        assert grid[y][x] == 0 and grid[y + 1][x] == 15
    assert all(len(colors) == 4 for _, colors in BG_PALETTES + SPRITE_PALETTES)
    assert len(BG_PALETTES) == 7  # UI slot 7 reserved
    assert all(set(colors) <= set("0123456789ABCDEF") for _, ramp in BG_PALETTES for colors in ramp)


_self_check()
