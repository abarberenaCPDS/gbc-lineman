"""Compose explicitly authored (NOT emulator) M-V1 size/power comparisons.

Run with managed Python after the environment and character generators.
PNG proxy colors are mapped to the contract's actual GBC object palettes.
Outputs are ignored artifacts, never scene resources or gameplay evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps

import opening

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "artifacts/visual-opening"


def paint_sprite(canvas: Image.Image, name: str, state_name: str, position: tuple[int, int]) -> int:
    path = ROOT / f"assets/sprites/{name}.png"
    metadata = json.loads(Path(str(path) + ".gbsres").read_text())
    state = next(s for s in metadata["states"] if s["name"] == state_name)
    frame = state["animations"][0]["frames"][0]
    sheet = Image.open(path).convert("RGBA")
    for tile in frame["tiles"]:
        x, y = tile["sliceX"], tile["sliceY"]
        crop = sheet.crop((x, y, x + 8, y + 16))
        pixels = crop.load()
        colors = opening.SPRITE_PALETTES[tile["paletteIndex"]][1]
        for py in range(16):
            for px in range(8):
                r, g, b, a = pixels[px, py]
                if a == 0 or (g > 200 and r < 100 and b < 100):
                    pixels[px, py] = (0, 0, 0, 0)
                else:
                    index = 1 if g >= 205 else 2 if g >= 130 else 3
                    color = colors[index]
                    pixels[px, py] = tuple(int(color[i:i + 2], 16) for i in (0, 2, 4)) + (255,)
        if tile.get("flipX"):
            crop = ImageOps.mirror(crop)
        if tile.get("flipY"):
            crop = ImageOps.flip(crop)
        canvas.paste(crop, (position[0] * 8 + tile["x"], position[1] * 8 - tile["y"] - 8), crop)
    sheet.close()
    return len(frame["tiles"])


def main() -> None:
    from make_opening_art import make_background

    OUT.mkdir(parents=True, exist_ok=True)
    background, slots = make_background()
    cold = opening.BG_PALETTES[3][1]
    warm = opening.POWERED_WINDOW
    fixtures = []
    for size in (24,):
        for powered in (False, True):
            frame = background.copy().convert("RGB")
            if powered:
                mapping = {tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)):
                           tuple(int(warm[n][i:i + 2], 16) for i in (0, 2, 4))
                           for n, c in enumerate(cold)}
                for ty, row in enumerate(slots):
                    for tx, slot in enumerate(row):
                        if slot == 3:
                            for py in range(ty * 8, ty * 8 + 8):
                                for px in range(tx * 8, tx * 8 + 8):
                                    frame.putpixel((px, py), mapping[frame.getpixel((px, py))])
            count = paint_sprite(frame, f"opening_worker{size}", "Default", opening.START)
            count += paint_sprite(frame, "opening_marta", "Powered" if powered else "Waiting", opening.MARTA)
            count += paint_sprite(frame, "opening_terminal", "On" if powered else "Off", opening.PANEL)
            label = f"{size}px hero / {'powered' if powered else 'cold'}"
            frame.save(OUT / f"worker{size}_{'powered' if powered else 'cold'}.png")
            fixtures.append((label, frame, count))
    sheet = Image.new("RGB", (960, 912), "#101820")
    draw = ImageDraw.Draw(sheet)
    for index, (label, frame, count) in enumerate(fixtures):
        x, y = index % 2 * 480, index // 2 * 456
        draw.text((x + 8, y + 4), f"AUTHORED FIXTURE - {label} - {count} objects", fill="white")
        sheet.paste(frame.resize((480, 432), Image.Resampling.NEAREST), (x, y + 24))
    sheet.save(OUT / "size_power_comparison.png")
    print("wrote authored fixtures (not emulator evidence): artifacts/visual-opening/")


if __name__ == "__main__":
    main()
