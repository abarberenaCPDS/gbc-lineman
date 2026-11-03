"""Generate the work-order / storm-report card background (``tickets.py`` contract).

A clipboard with a ruled paper work order, CFE bolt badge and stamp box on a dark
desk, in tile rows 0..CARD_ROWS-1; rows below are a flat UI-slot fill under the
dialogue box. No baked text: the ticket words are dialogue. Same approach as
``make_intro_art.py``: 4-index canvas + BG palette slot per tile, written as the
grayscale index proxy PNG + sidecar. Positions derive from the tile constants.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

import intro
import tickets
from make_climb_scene import collision_rle

ROOT = tickets.ROOT
BG_DIR = ROOT / "assets/backgrounds"
PREVIEW_DIR = ROOT / "build" / "ticket-art"
TILE = intro.TILE
MAP_W, MAP_H = tickets.MAP_W, tickets.MAP_H
WIDTH, HEIGHT = MAP_W * TILE, MAP_H * TILE
CARD_ROWS = tickets.CARD_ROWS
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)
UI_SLOT = 7
MAX_UNIQUE_TILES = 60

# BG palette ids per slot at scene start (8 entries, last "default-ui").
BACKGROUND_PALETTE_NAMES = ["night", "timber", "gold", "metal", "window_lit",
                            "night", "night", "ui"]
BACKGROUND_PALETTE_IDS = [intro.palette_id(n) for n in BACKGROUND_PALETTE_NAMES[:7]] + ["default-ui"]
S_NIGHT, S_TIMBER, S_PAPER, S_METAL, S_BADGE = 0, 1, 2, 3, 4

# Layout in tiles (inclusive).
BOARD = (2, 0, 17, CARD_ROWS - 1)
PAPER = (3, 2, 16, CARD_ROWS - 1)
CLIP = (7, 0, 12, 1)
BADGE = (4, 3, 5, 4)
HEADER_RULE_ROW = 4           # thick rule right of the badge
LINES = range(6, CARD_ROWS - 3)   # ruled lines, one per tile row
STAMP = (11, 9, 15, 11)


class Card:
    def __init__(self):
        self.idx = Image.new("L", (WIDTH, HEIGHT), 0)
        self.slots = [[S_NIGHT] * MAP_W for _ in range(MAP_H)]
        self.d = ImageDraw.Draw(self.idx)

    def tiles(self, box, slot, v=None):
        x0, y0, x1, y1 = box
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                self.slots[ty][tx] = slot
        if v is not None:
            self.d.rectangle((x0 * TILE, y0 * TILE, x1 * TILE + 7, y1 * TILE + 7), fill=v)

    def px(self, box):
        x0, y0, x1, y1 = box
        return x0 * TILE, y0 * TILE, x1 * TILE + 7, y1 * TILE + 7

    def rgb(self) -> Image.Image:
        pals = [[bytes.fromhex(c) for c in intro.BG_PALETTES[n]] for n in BACKGROUND_PALETTE_NAMES]
        out = Image.new("RGB", self.idx.size)
        src, dst = self.idx.load(), out.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                dst[x, y] = tuple(pals[self.slots[y // TILE][x // TILE]][src[x, y]])
        return out

    def proxy(self) -> Image.Image:
        assert self.idx.getextrema()[1] <= 3
        lut = list(NATIVE_PROXY_BY_INDEX) + [0] * 252
        return self.idx.point(lut).convert("RGB")


def build() -> Card:
    c = Card()
    # Dark desk: night index 1 with a soft darker edge, all card rows.
    c.tiles((0, 0, MAP_W - 1, CARD_ROWS - 1), S_NIGHT, 1)
    # Clipboard board (timber): dark rim, tan face.
    bx0, by0, bx1, by1 = c.px(BOARD)
    c.tiles(BOARD, S_TIMBER, 2)
    c.d.rectangle((bx0, by0, bx0 + 3, by1), fill=1)
    c.d.rectangle((bx1 - 3, by0, bx1, by1), fill=1)
    c.d.rectangle((bx0, by0, bx0 + 1, by1), fill=0)
    c.d.rectangle((bx1 - 1, by0, bx1, by1), fill=0)
    # Paper: cream with a darker edge and a bolder bottom run under the dialogue box.
    c.tiles(PAPER, S_PAPER, 3)
    px0, py0, px1, py1 = c.px(PAPER)
    c.d.rectangle((px0, py0, px1, py0 + 1), fill=2)
    c.d.rectangle((px0, py0, px0 + 1, py1), fill=2)
    c.d.rectangle((px1 - 1, py0, px1, py1), fill=2)
    c.d.rectangle((px0 + 2, py0 + 2, px1 - 2, py0 + 2), fill=3)
    # Metal clip: rounded plate with a dark slot.
    c.tiles(CLIP, S_METAL, 1)
    cx0, cy0, cx1, cy1 = c.px(CLIP)
    c.d.rectangle((cx0, cy0, cx1, cy1), fill=2)
    c.d.rectangle((cx0 + 2, cy0, cx1 - 2, cy1 - 2), fill=3)
    c.d.rectangle((cx0 + 8, cy0 + 4, cx1 - 8, cy0 + 7), fill=0)
    c.d.rectangle((cx0, cy1 - 1, cx1, cy1), fill=1)
    # Header rule right of the badge (gold index 1 = brown ink, 2px).
    hy = HEADER_RULE_ROW * TILE + 3
    c.d.rectangle(((BADGE[2] + 2) * TILE, hy, (PAPER[2] - 1) * TILE + 7, hy + 1), fill=1)
    # Ruled lines: 1px mid-tone, one per tile row, inside the paper margins.
    for ty in LINES:
        y = ty * TILE + 7
        c.d.rectangle(((PAPER[0] + 1) * TILE, y, (PAPER[2] - 1) * TILE + 7, y), fill=2)
    # Badge: amber disc with a dark lightning bolt (window_lit slot, 16x16).
    c.tiles(BADGE, S_BADGE, 0)
    ox, oy = BADGE[0] * TILE, BADGE[1] * TILE
    c.d.ellipse((ox, oy, ox + 15, oy + 15), fill=2)
    c.d.ellipse((ox + 2, oy + 2, ox + 13, oy + 13), fill=3)
    bolt = [(9, 2), (4, 9), (7, 9), (6, 14), (12, 6), (9, 6), (11, 2)]
    c.d.polygon([(ox + x, oy + y) for x, y in bolt], fill=1)
    # Stamp box: 2px brown border, blank inside, in the paper slot.
    sx0, sy0, sx1, sy1 = c.px(STAMP)
    sx0 += 2; sy0 += 2; sx1 -= 2; sy1 -= 1
    c.d.rectangle((sx0, sy0, sx1, sy1), outline=1, width=2)
    # Dialogue area: flat UI slot, index 0.
    c.tiles((0, CARD_ROWS, MAP_W - 1, MAP_H - 1), UI_SLOT, 0)
    return c


def unique_tiles(card: Card, rows: range = range(MAP_H)) -> int:
    px = card.idx.load()
    seen = {(card.slots[ty][tx],
             tuple(px[tx * TILE + x, ty * TILE + y] for y in range(TILE) for x in range(TILE)))
            for ty in rows for tx in range(MAP_W)}
    return len(seen)


def write(card: Card) -> int:
    n = unique_tiles(card)
    assert n <= MAX_UNIQUE_TILES, n
    BG_DIR.mkdir(parents=True, exist_ok=True)
    out = BG_DIR / f"{tickets.BACKGROUND_NAME}.png"
    card.proxy().save(out, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background", "id": tickets.BACKGROUND_ID,
        "name": tickets.BACKGROUND_NAME, "symbol": f"bg_{tickets.BACKGROUND_NAME}",
        "filename": out.name, "width": MAP_W, "height": MAP_H,
        "imageWidth": WIDTH, "imageHeight": HEIGHT, "autoColor": False,
        "tileColors": collision_rle(card.slots, MAP_W, MAP_H),
    }
    Path(str(out) + ".gbsres").write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    return n


def main() -> None:
    card = build()
    n = write(card)
    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    card.rgb().resize((WIDTH * 4, HEIGHT * 4), Image.NEAREST).save(PREVIEW_DIR / "ticket_preview.png")
    print(f"generated assets/backgrounds/{tickets.BACKGROUND_NAME}.png: {n} unique tiles")


if __name__ == "__main__":
    main()
