"""Generate a two-state warning/rock sprite with stable GB Studio IDs.

Uses the managed Python (Pillow). Transparent pixels are GB Studio green;
visible pixels use GB Studio's three grayscale indices, recolored by sprite
palette slot 4. The source gray mapping is counterintuitive: white maps to
palette color 1 (the darkest opaque hazard shade), while black maps to color 3
(the brightest). Both states occupy only the lower 8 rows of an 8x16 tile, so
their visible art aligns with the 8x8 actor bounds.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

from make_climb_scene import resource_id, write_json

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/sprites/climb_debris.png"
TRANSPARENT = (0, 255, 0)
# GB Studio's spriteDataIndexFn assigns g>=205 to pixel index 1, 130<=g<205
# to index 2, and g<130 to index 3 (index 0 is transparent). The scene's
# hazard palette is [240809, 54120F, 98251B, D95838], so these source colors
# intentionally map to the three *opaque* hardware colors in reverse order.
OUTLINE = (255, 255, 255)  # index 1 -> darkest opaque shade, #54120F
MID = (160, 160, 160)      # index 2 -> mid shade, #98251B
BRIGHT = (0, 0, 0)         # index 3 -> brightest shade, #D95838


def sprite_resource(checksum: str) -> dict:
    states = []
    for column, name in enumerate(("Warning", "Rock")):
        animations = []
        for direction in range(8):
            key = f"debris:{name}:{direction}"
            tiles = [{
                "id": resource_id(key + ":tile"), "x": 0, "y": 0,
                "sliceX": column * 8, "sliceY": 0,
                "flipX": False, "flipY": False, "palette": 0,
                "paletteIndex": 4, "objPalette": "OBP0", "priority": False,
            }] if direction == 0 else []
            animations.append({
                "id": resource_id(key + ":animation"),
                "frames": [{"id": resource_id(key + ":frame"), "tiles": tiles}],
            })
        states.append({
            "id": resource_id("debris-state:" + name), "name": name,
            "animationType": "fixed", "flipLeft": False, "animations": animations,
        })
    return {
        "_resourceType": "sprite", "id": resource_id("sprite:climb-debris"),
        "name": "climb_debris", "symbol": "sprite_climb_debris",
        "filename": OUTPUT.name, "width": 16, "height": 16,
        "checksum": checksum, "numTiles": 2,
        "canvasOriginX": 0, "canvasOriginY": 0,
        "canvasWidth": 8, "canvasHeight": 16,
        "boundsX": 0, "boundsY": 0, "boundsWidth": 8, "boundsHeight": 8,
        "animSpeed": 15, "states": states,
    }


def make_sheet() -> Image.Image:
    """Build and validate both 8x8 icons in their 8x16 hardware tiles."""
    image = Image.new("RGB", (16, 16), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    # Warning: a bright, outlined triangle with a dark exclamation. On this
    # palette, black source pixels are the bright fill and white pixels are
    # the dark outline/glyph (see the palette mapping above).
    draw.polygon(
        ((3, 8), (4, 8), (7, 15), (0, 15)), fill=BRIGHT, outline=OUTLINE
    )
    draw.rectangle((3, 10, 4, 13), fill=OUTLINE)
    draw.rectangle((3, 14, 4, 14), fill=OUTLINE)

    # Rock: a readable faceted boulder. Its opaque outline reaches all four
    # bounds edges (local x/y 0..7); highlights and shadow stay within them.
    draw.polygon(
        (
            (10, 8), (13, 8), (15, 10), (15, 13),
            (13, 15), (10, 15), (8, 13), (8, 10),
        ),
        fill=MID,
        outline=OUTLINE,
    )
    draw.polygon(((10, 9), (12, 9), (13, 11), (10, 11)), fill=BRIGHT)
    draw.line((9, 12, 11, 14, 13, 14), fill=OUTLINE)

    # Verify the generated art's actual source-pixel footprints against the
    # metadata bounds (Pillow boxes are right/bottom exclusive). The top rows
    # must remain transparent: compileSprites.ts emits an 8x16 metasprite Y
    # offset of +8, and hardware OAM's -16 display bias puts source row 8 at
    # actor y, so source rows 8..15 render at actor y..y+7.
    assert image.size == (16, 16)
    assert {image.getpixel((x, y)) for y in range(16) for x in range(16)} <= {
        TRANSPARENT, OUTLINE, MID, BRIGHT,
    }
    assert all(image.getpixel((x, y)) == TRANSPARENT for y in range(8) for x in range(16))

    def opaque_bbox(x0: int) -> tuple[int, int, int, int] | None:
        points = [
            (x, y)
            for y in range(16)
            for x in range(x0, x0 + 8)
            if image.getpixel((x, y)) != TRANSPARENT
        ]
        if not points:
            return None
        xs, ys = zip(*points)
        return min(xs), min(ys), max(xs) + 1, max(ys) + 1

    assert opaque_bbox(0) == (0, 8, 8, 16), (
        "warning art must fit its 8x8 actor bounds"
    )
    assert opaque_bbox(8) == (8, 8, 16, 16), (
        "rock art must exactly match its 8x8 actor bounds"
    )
    return image


def main() -> None:
    image = make_sheet()
    image.save(OUTPUT, optimize=False)
    resource = sprite_resource(hashlib.sha1(OUTPUT.read_bytes()).hexdigest())
    write_json(Path(str(OUTPUT) + ".gbsres"), resource)
    print("generated climb_debris: warning + rock; 8x8 damage bounds")


if __name__ == "__main__":
    main()
