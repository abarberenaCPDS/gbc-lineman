"""Render collision-aligned prototype art; no old background is overwritten.

Run using the managed toolchain Python (Pillow required), before
make_climb_scene.py. Red crossed tiles explicitly mark static reset zones;
these are placeholders, not finished wind/debris effects.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

import climb
import level
from make_climb_scene import collision_rle, resource_id

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/storm_climb.png"


def main() -> None:
    palettes = [colors for _, colors in level.BG_PALETTES]
    image = Image.new("RGB", (climb.MAP_W * 8, climb.MAP_H * 8), "#" + palettes[0][0])
    draw = ImageDraw.Draw(image)
    slots = [[0] * climb.MAP_W for _ in range(climb.MAP_H)]
    grid = climb.collision_grid()
    for y, row in enumerate(grid):
        for x, cell in enumerate(row):
            if cell == climb.COL_EMPTY:
                continue
            slot = 4 if cell == climb.COL_TOP else 1
            slots[y][x] = slot
            colors = ["#" + c for c in palettes[slot]]
            px, py = x * 8, y * 8
            draw.rectangle((px, py, px + 7, py + 7), fill=colors[1])
            draw.line((px, py, px + 7, py), fill=colors[3])
            draw.line((px, py + 1, px + 7, py + 1), fill=colors[2])
    for y, x0, x1 in climb.GUST_LANES:
        colors = ["#" + c for c in palettes[5]]
        for x in range(x0, x1 + 1):
            slots[y][x] = 5
            px, py = x * 8, y * 8
            draw.rectangle((px, py, px + 7, py + 7), fill=colors[0])
            draw.line((px + 2, py + 2, px + 5, py + 5), fill=colors[3])
            draw.line((px + 5, py + 2, px + 2, py + 5), fill=colors[3])
    image.save(OUTPUT)
    sidecar = {
        "_resourceType": "background", "id": resource_id("background:storm-climb"),
        "name": "storm_climb", "symbol": "bg_storm_climb", "filename": OUTPUT.name,
        "width": climb.MAP_W, "height": climb.MAP_H,
        "imageWidth": image.width, "imageHeight": image.height, "autoColor": False,
        "tileColors": collision_rle(slots, climb.MAP_W, climb.MAP_H),
    }
    Path(str(OUTPUT) + ".gbsres").write_text(json.dumps(sidecar, indent=2) + "\n")
    print("generated collision-aligned storm_climb prototype background")


if __name__ == "__main__":
    main()
