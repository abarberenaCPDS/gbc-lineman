"""Generate the isolated M-V1 service-opening background.

The image and tile-palette map are authored together so every native 8x8 tile
uses exactly one of the seven opening palettes.  This owns only
assets/backgrounds/service_opening.png and its GB Studio sidecar.
"""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw

import level
import opening


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/backgrounds/service_opening.png"
SIDECAR = Path(str(OUTPUT) + ".gbsres")
WIDTH, HEIGHT = opening.MAP_W * opening.TILE, opening.MAP_H * opening.TILE
PALETTES = [[tuple(bytes.fromhex(color)) for color in colors]
            for _, colors in opening.BG_PALETTES]
# GB Studio's tileDataIndexFn maps brighter green values to lower native
# indices.  Opening palette ramps are intentionally ordered dark -> light, so
# the native source PNG uses inverse grayscale proxies to preserve that index
# ordering: author index 0 (dark) -> native 0, ..., index 3 (light) -> native 3.
NATIVE_PROXY_BY_INDEX = (255, 170, 85, 0)


def _assign(slots: list[list[int]], slot: int, cells) -> None:
    for tx, ty in cells:
        slots[ty][tx] = slot


def _tile_rect(slots: list[list[int]], slot: int, x0: int, x1: int,
               y0: int, y1: int) -> None:
    _assign(slots, slot, ((x, y) for y in range(y0, y1 + 1)
                          for x in range(x0, x1 + 1)))


def _slots() -> list[list[int]]:
    slots = [[0] * opening.MAP_W for _ in range(opening.MAP_H)]

    # Cold distant ridges: stepped silhouettes, with deep valley gaps left as
    # night sky.  These are tile-sized regions, not a repeated green shelf.
    ridge_rows = {
        3: [(4, 7), (13, 16)],
        4: [(2, 9), (11, 18)],
        5: [(0, 10), (11, 19)],
        6: [(0, 5), (13, 19)],
        7: [(0, 5), (13, 19)],
        8: [(0, 5), (12, 19)],
        9: [(0, 3), (12, 19)],
    }
    for ty, spans in ridge_rows.items():
        for x0, x1 in spans:
            for tx in range(x0, x1 + 1):
                slots[ty][tx] = 1

    # Distant pines occupy only the empty left-side backdrop, well clear of
    # the start, cabinet, resident and traversable ledges.
    _tile_rect(slots, 4, 0, 1, 9, 12)
    _tile_rect(slots, 4, 2, 3, 9, 11)

    # A gabled timber service house; its right-hand eave is the upper walk's
    # attachment.  Facade is backdrop and contains no extra platform tops.
    _tile_rect(slots, 2, 6, 12, 6, 8)
    _tile_rect(slots, 2, 7, 11, 8, 15)

    # Cable climbs from the cabinet over the clear gap to a snapped eave
    # bracket.  Those whole tiles use metal colors, avoiding palette bleed.
    _tile_rect(slots, 5, 5, 5, 10, 11)
    _tile_rect(slots, 5, 6, 6, 9, 10)

    # Only the actual window cells and terminal indicator use slot 3.  The
    # window palette can therefore be swapped without warming the whole scene.
    _assign(slots, 3, [(8, 9), (10, 9)])

    # Cabinet at x=16..39, y=96..127.
    _tile_rect(slots, 5, 2, 4, 12, 15)
    _assign(slots, 3, [(4, 14)])

    # Actual collision shelves: timber deck surfaces at exactly y=80 and
    # y=104.  Their posts are narrow verticals, not extra horizontal ledges.
    _tile_rect(slots, 2, 11, 18, 10, 10)
    _tile_rect(slots, 2, 12, 12, 11, 12)
    _tile_rect(slots, 2, 18, 18, 11, 12)
    _tile_rect(slots, 2, 13, 16, 13, 13)
    _tile_rect(slots, 2, 13, 13, 14, 15)
    _tile_rect(slots, 2, 16, 16, 14, 15)

    # Right-hand solid rock and the grounded soil floor match collision_grid.
    _tile_rect(slots, 1, 17, 19, 13, 15)
    _tile_rect(slots, 6, 0, 19, 16, 17)

    # The broken insulator is attached to the right roof corner, not a ledge.
    _assign(slots, 5, [(12, 8)])
    return slots


class _Canvas:
    """Pixel painter that clips motifs to tiles assigned the requested slot."""

    def __init__(self, image: Image.Image, slots: list[list[int]]):
        self.image = image
        self.slots = slots

    def _apply(self, slot: int, painter) -> None:
        layer = Image.new("RGBA", self.image.size, (0, 0, 0, 0))
        painter(ImageDraw.Draw(layer))
        px = self.image.load()
        over = layer.load()
        for y in range(HEIGHT):
            for x in range(WIDTH):
                rgba = over[x, y]
                if rgba[3]:
                    if self.slots[y // 8][x // 8] == slot:
                        px[x, y] = rgba[:3]

    @staticmethod
    def _rgb(color):
        return tuple(color) + (255,)

    def rect(self, slot: int, box, color, outline=None, width=1) -> None:
        fill = self._rgb(color)
        edge = self._rgb(outline) if outline is not None else None
        self._apply(slot, lambda d: d.rectangle(box, fill=fill, outline=edge,
                                                 width=width))

    def line(self, slot: int, points, color, width=1) -> None:
        rgba = self._rgb(color)
        self._apply(slot, lambda d: d.line(points, fill=rgba, width=width))

    def polygon(self, slot: int, points, color) -> None:
        rgba = self._rgb(color)
        self._apply(slot, lambda d: d.polygon(points, fill=rgba))

    def point(self, slot: int, xy, color) -> None:
        rgba = self._rgb(color)
        self._apply(slot, lambda d: d.point(xy, fill=rgba))


def make_background() -> tuple[Image.Image, list[list[int]]]:
    """Return the native 160x144 RGB background and row-major palette slots."""
    slots = _slots()
    image = Image.new("RGB", (WIDTH, HEIGHT))
    pixels = image.load()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            color = PALETTES[slot][0]
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    pixels[x, y] = color
    c = _Canvas(image, slots)
    p = PALETTES

    # Angular blue-violet mountain layers.  Broad planes and a few ridge
    # accents establish depth without dithering or noisy weather texture.
    c.polygon(1, [(-2, 60), (-2, 49), (15, 42), (27, 48), (42, 36),
                  (58, 44), (77, 37), (95, 46), (112, 39), (129, 47),
                  (145, 40), (162, 47), (162, 76), (-2, 76)], p[1][1])
    c.polygon(1, [(-2, 66), (9, 57), (22, 61), (37, 50), (52, 57),
                  (67, 51), (82, 61), (98, 54), (112, 60), (129, 50),
                  (143, 58), (162, 52), (162, 82), (-2, 82)], p[1][0])
    c.polygon(1, [(1, 53), (14, 47), (25, 51), (41, 39), (52, 45),
                  (44, 43), (31, 55), (20, 53), (9, 59)], p[1][2])
    c.polygon(1, [(79, 44), (94, 39), (106, 43), (116, 39), (108, 47),
                  (96, 45), (87, 49)], p[1][2])
    c.polygon(1, [(126, 53), (141, 43), (153, 46), (143, 49),
                  (136, 57)], p[1][2])
    # Thin exposed ridgelines catch the same cool light as the hardware.
    c.line(1, [(15, 43), (20, 42), (24, 45)], p[1][3])
    c.line(1, [(42, 37), (47, 39), (51, 43)], p[1][3])
    c.line(1, [(94, 40), (98, 40)], p[1][3])
    c.line(1, [(141, 42), (145, 41)], p[1][3])

    # Sparse stars and a few short rain slashes, all kept to open night sky.
    for x, y, color_index in [(11, 15, 2), (30, 8, 3), (73, 23, 2),
                              (103, 12, 3), (145, 22, 2), (154, 9, 2),
                              (20, 30, 2), (124, 28, 3)]:
        c.point(0, (x, y), p[0][color_index])
    c.line(0, [(52, 18), (50, 21)], p[0][1])
    c.line(0, [(89, 28), (87, 31)], p[0][1])
    c.line(0, [(136, 14), (134, 17)], p[0][1])
    c.line(0, [(7, 35), (5, 38)], p[0][1])

    # Distant spruce silhouettes at left, framed away from the playable spawn.
    c.polygon(4, [(1, 98), (5, 89), (3, 89), (8, 80), (7, 80),
                  (11, 72), (15, 81), (13, 81), (18, 91), (15, 91),
                  (20, 100), (13, 100), (13, 105), (7, 105), (7, 100)], p[4][1])
    c.polygon(4, [(3, 97), (8, 91), (6, 91), (11, 84), (9, 84),
                  (12, 79), (15, 87), (13, 87), (17, 95), (13, 94),
                  (19, 101), (8, 101)], p[4][2])
    c.line(4, [(10, 74), (11, 72), (12, 75)], p[4][3])
    c.rect(4, (10, 99, 12, 103), p[4][1])
    c.polygon(4, [(18, 94), (22, 86), (21, 86), (25, 78), (24, 78),
                  (28, 71), (32, 79), (30, 79), (35, 88), (32, 88),
                  (38, 96), (33, 96), (33, 100), (23, 100), (23, 96)], p[4][1])
    c.polygon(4, [(20, 93), (25, 87), (23, 87), (28, 80), (26, 80),
                  (29, 76), (33, 83), (31, 83), (36, 92), (32, 91),
                  (37, 97), (24, 97)], p[4][2])
    c.line(4, [(27, 81), (28, 79), (29, 82)], p[4][3])

    # Timber house: deep gable and broad fascia, lit from upper-left.  Eaves
    # remain architectural backdrop, not platform-shaped collision cues.
    c.polygon(2, [(47, 68), (56, 58), (72, 48), (88, 57), (104, 67),
                  (101, 72), (95, 69), (88, 64), (72, 56), (57, 66),
                  (52, 72)], p[2][0])
    c.polygon(2, [(51, 66), (57, 61), (72, 51), (87, 60), (101, 68),
                  (96, 68), (87, 63), (72, 55), (57, 65)], p[2][1])
    c.line(2, [(54, 64), (71, 51), (74, 52)], p[2][3], 2)
    c.line(2, [(74, 56), (88, 63), (98, 69)], p[2][2])
    c.line(2, [(49, 69), (56, 68), (61, 69)], p[2][2])

    # Facade boards and heavy corner posts.  Left lower wall is intentionally
    # quiet behind Amara's resident/start zone.
    c.rect(2, (56, 65, 95, 127), p[2][1])
    for y in (72, 94, 110):
        c.line(2, [(57, y), (63, y)], p[2][2])
        c.line(2, [(74, y), (78, y)], p[2][2])
        c.line(2, [(89, y), (94, y)], p[2][2])
    c.rect(2, (56, 65, 59, 126), p[2][0])
    c.rect(2, (60, 65, 62, 126), p[2][2])
    c.rect(2, (90, 66, 94, 126), p[2][0])
    c.line(2, [(90, 67), (90, 125)], p[2][3])
    c.rect(2, (75, 91, 77, 126), p[2][0])
    # Recessed service door on the far half of the facade, below the walk.
    c.rect(2, (80, 100, 88, 126), p[2][0])
    c.line(2, [(81, 101), (87, 101)], p[2][3])
    c.line(2, [(86, 108), (86, 112)], p[2][2])
    c.rect(2, (78, 98, 90, 100), p[2][2])
    # A few restrained plank seams, never a continuous shelf edge.
    c.line(2, [(63, 91), (68, 91)], p[2][0])
    c.line(2, [(80, 95), (85, 95)], p[2][0])
    c.line(2, [(64, 108), (69, 108)], p[2][2])

    # Dark slot-3 windows: only these two cells become warm in the powered
    # variant.  Cool edge reflections imply glass without adding a global glow.
    for x0, y0 in [(64, 72), (80, 72)]:
        c.rect(3, (x0, y0, x0 + 7, y0 + 7), p[3][0])
        c.line(3, [(x0 + 1, y0 + 1), (x0 + 5, y0 + 1)], p[3][1])
        c.line(3, [(x0 + 1, y0 + 2), (x0 + 1, y0 + 5)], p[3][2])
        c.line(3, [(x0 + 4, y0 + 2), (x0 + 6, y0 + 2)], p[3][3])
        c.point(3, (x0 + 5, y0 + 5), p[3][2])

    # Cold metal cabinet and door at the exact substation footprint.  Top and
    # left bevels receive the light; no painted person occupies its panel.
    c.rect(5, (16, 96, 39, 127), p[5][0])
    c.line(5, [(16, 96), (37, 96)], p[5][3])
    c.line(5, [(16, 97), (16, 125)], p[5][3])
    c.line(5, [(38, 97), (38, 125)], p[5][1])
    c.rect(5, (18, 98, 37, 100), p[5][2])
    c.line(5, [(17, 100), (17, 124)], p[5][3], 2)
    c.line(5, [(19, 102), (36, 102)], p[5][1])
    c.line(5, [(20, 104), (20, 123)], p[5][1])
    c.line(5, [(29, 104), (29, 125)], p[5][1])
    c.line(5, [(18, 126), (38, 126)], p[5][2])
    for x, y in [(22, 106), (26, 106), (22, 110), (26, 110),
                 (22, 115), (26, 115), (22, 119), (26, 119)]:
        c.point(5, (x, y), p[5][1])
    c.line(5, [(32, 106), (36, 106)], p[5][2])
    c.line(5, [(32, 109), (36, 109)], p[5][1])
    # Slot-3 status glass, aligned to the interactive terminal actor.
    c.rect(3, (32, 112, 39, 119), p[3][0])
    c.line(3, [(33, 113), (37, 113)], p[3][1])
    c.point(3, (35, 115), p[3][3])
    c.line(3, [(34, 116), (36, 116)], p[3][2])
    c.line(3, [(33, 118), (35, 118)], p[3][1])

    # Cable run, restrained but legible against the sky; snapped support sits
    # just short of the roof.  Parallel pixel accents keep it from reading as
    # a bright lightning bolt.
    c.line(5, [(37, 99), (40, 95), (43, 92), (45, 88), (49, 85),
               (51, 81), (54, 78)], p[5][1])
    c.line(5, [(38, 99), (41, 95), (44, 92), (46, 88)], p[5][2])
    c.line(5, [(49, 84), (51, 80), (54, 77)], p[5][2])
    c.line(5, [(51, 77), (55, 77)], p[5][3])
    c.rect(5, (52, 74, 54, 76), p[5][2])
    c.line(5, [(55, 73), (57, 71)], p[5][1])
    # Roof-corner broken bracket: a bent arm and empty insulator fork.
    c.rect(5, (97, 63, 102, 65), p[5][1])
    c.line(5, [(99, 64), (99, 68), (102, 70)], p[5][3])
    c.line(5, [(102, 70), (104, 68)], p[5][1])
    c.point(5, (101, 67), p[5][0])
    c.line(5, [(98, 61), (101, 61)], p[5][2])

    # Upper catwalk, exactly on row 10 / y=80.  Narrow boards and two visible
    # timber legs make the underside open for drop-through movement.
    c.rect(2, (88, 80, 151, 83), p[2][1])
    c.line(2, [(89, 80), (149, 80)], p[2][3], 1)
    for x in (96, 112, 128, 144):
        c.line(2, [(x, 81), (x + 5, 81)], p[2][2])
    c.line(2, [(96, 84), (96, 102)], p[2][0], 2)
    c.line(2, [(97, 84), (97, 102)], p[2][2])
    c.line(2, [(144, 84), (144, 102)], p[2][0], 2)
    c.line(2, [(145, 84), (145, 102)], p[2][2])
    c.line(2, [(96, 103), (101, 103)], p[2][1])
    c.line(2, [(144, 103), (149, 103)], p[2][1])

    # Lower catwalk exactly meets the cliff at y=104; its supports end at the
    # grounded floor.  No unrelated facade or timber trim forms another top.
    c.rect(2, (104, 104, 135, 107), p[2][1])
    c.line(2, [(105, 104), (134, 104)], p[2][3])
    c.line(2, [(109, 105), (113, 105)], p[2][2])
    c.line(2, [(121, 105), (125, 105)], p[2][2])
    c.line(2, [(109, 108), (109, 127)], p[2][0], 2)
    c.line(2, [(111, 108), (111, 127)], p[2][2])
    c.line(2, [(128, 108), (128, 127)], p[2][0], 2)
    c.line(2, [(130, 108), (130, 127)], p[2][2])
    c.line(2, [(109, 125), (112, 125)], p[2][3])
    c.line(2, [(128, 125), (131, 125)], p[2][3])

    # Rock face at x=136..159, y=104..127.  The ledge lip is one continuous
    # walkable top with the adjacent timber deck, while vertical strata stay
    # angular and clearly solid beneath it.
    c.rect(1, (136, 104, 159, 127), p[1][1])
    c.line(1, [(136, 104), (159, 104)], p[1][3])
    c.line(1, [(136, 106), (159, 106)], p[1][2])
    c.polygon(1, [(136, 109), (143, 109), (149, 115), (145, 119),
                  (140, 116), (136, 118)], p[1][0])
    c.polygon(1, [(151, 107), (159, 107), (159, 117), (155, 114)], p[1][2])
    c.line(1, [(143, 121), (148, 118), (152, 120), (155, 118)], p[1][0], 2)
    c.line(1, [(138, 123), (142, 121)], p[1][2])
    c.line(1, [(153, 126), (158, 123)], p[1][2])

    # Foreground platform is a grounded soil cut, not a luminous shelf.  A
    # single top seam and a few large strata keep the material quiet at 1x.
    c.rect(6, (0, 128, 159, 143), p[6][1])
    c.line(6, [(0, 128), (159, 128)], p[6][3])
    c.line(6, [(0, 130), (159, 130)], p[6][2])
    for x in (8, 31, 56, 76, 100, 121, 151):
        c.line(6, [(x, 135), (x + 3, 135)], p[6][0])
    c.polygon(6, [(18, 138), (21, 136), (25, 136), (28, 139),
                  (24, 141), (19, 141)], p[6][2])
    c.polygon(6, [(88, 132), (91, 131), (94, 132), (92, 134)], p[6][1])
    c.polygon(6, [(137, 138), (140, 136), (144, 137), (147, 140),
                  (142, 141), (138, 140)], p[6][2])

    # Validate the promised per-cell palette contract before returning.
    rgb_to_slot = [{color for color in palette} for palette in PALETTES]
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            allowed = rgb_to_slot[slot]
            for y in range(ty * 8, ty * 8 + 8):
                for x in range(tx * 8, tx * 8 + 8):
                    color = image.getpixel((x, y))
                    if color not in allowed:
                        raise AssertionError(
                            f"tile ({tx},{ty}) slot {slot} has illegal color {color}")
    return image, slots


def _gb_studio_native_index(green: int) -> int:
    """Mirror GB Studio src/shared/lib/tiles/tileData.ts::tileDataIndexFn."""
    if green < 65:
        return 3
    if green < 130:
        return 2
    if green < 205:
        return 1
    return 0


def encode_native_background(
    image: Image.Image, slots: list[list[int]]
) -> Image.Image:
    """Encode author RGB art as exact grayscale indices for GB Studio.

    ``make_background`` remains the palette-colored authoring API.  The PNG
    written by ``main`` must instead quantize to the correct manual-palette
    index using GB Studio's brightness thresholds; the per-tile palette slots
    remain in the sidecar and are not encoded into the pixels.
    """
    if image.mode != "RGB" or image.size != (WIDTH, HEIGHT):
        raise ValueError(f"expected RGB {(WIDTH, HEIGHT)} author image")
    if len(slots) != opening.MAP_H or any(len(row) != opening.MAP_W for row in slots):
        raise ValueError(f"expected {opening.MAP_W}x{opening.MAP_H} palette grid")

    palette_indices = [
        {color: index for index, color in enumerate(palette)}
        for palette in PALETTES
    ]
    proxy = Image.new("RGB", image.size)
    source_pixels = image.load()
    proxy_pixels = proxy.load()
    for y in range(HEIGHT):
        ty = y // opening.TILE
        for x in range(WIDTH):
            tx = x // opening.TILE
            slot = slots[ty][tx]
            if not 0 <= slot < len(PALETTES):
                raise ValueError(f"invalid palette slot {slot} at tile ({tx},{ty})")
            color = source_pixels[x, y]
            try:
                intended_index = palette_indices[slot][color]
            except KeyError as exc:
                raise ValueError(
                    f"color {color} at ({x},{y}) is not in palette slot {slot}"
                ) from exc
            gray = NATIVE_PROXY_BY_INDEX[intended_index]
            native_index = _gb_studio_native_index(gray)
            if native_index != intended_index:
                raise AssertionError(
                    f"author index {intended_index} encoded as native index {native_index}"
                )
            proxy_pixels[x, y] = (gray, gray, gray)

    # In-memory round trip: quantize every proxy pixel with GB Studio's source
    # thresholds, decode that native index through its own tile palette, and
    # require byte-for-byte equality with the author RGB image.
    roundtrip = Image.new("RGB", image.size)
    roundtrip_pixels = roundtrip.load()
    for y in range(HEIGHT):
        for x in range(WIDTH):
            slot = slots[y // opening.TILE][x // opening.TILE]
            native_index = _gb_studio_native_index(proxy_pixels[x, y][1])
            roundtrip_pixels[x, y] = PALETTES[slot][native_index]
    if roundtrip.tobytes() != image.tobytes():
        raise AssertionError("native grayscale proxy failed RGB palette round-trip")
    return proxy


def _unique_indexed_tiles(image: Image.Image,
                          slots: list[list[int]]) -> int:
    unique = set()
    for ty, row in enumerate(slots):
        for tx, slot in enumerate(row):
            pattern = tuple(image.getpixel((tx * 8 + x, ty * 8 + y))
                            for y in range(8) for x in range(8))
            unique.add((slot, pattern))
    return len(unique)


def _check_owned_outputs() -> None:
    expected_id = opening.resource_id("background:service-opening")
    if SIDECAR.exists():
        try:
            resource = json.loads(SIDECAR.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"refusing to overwrite unreadable sidecar: {SIDECAR}") from exc
        if resource.get("id") != expected_id:
            raise RuntimeError(f"refusing to overwrite unowned sidecar: {SIDECAR}")
    elif OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite PNG without its owned sidecar: {OUTPUT}")


def main() -> None:
    _check_owned_outputs()
    author_image, slots = make_background()
    image = encode_native_background(author_image, slots)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUTPUT, format="PNG", optimize=False)
    resource = {
        "_resourceType": "background",
        "id": opening.resource_id("background:service-opening"),
        "name": "service_opening",
        "symbol": "bg_service_opening",
        "filename": "service_opening.png",
        "width": opening.MAP_W,
        "height": opening.MAP_H,
        "imageWidth": image.width,
        "imageHeight": image.height,
        "autoColor": False,
        "tileColors": level.rle([slot for row in slots for slot in row]),
    }
    SIDECAR.write_text(json.dumps(resource, indent=2) + "\n", encoding="utf-8")
    print(f"generated {OUTPUT.relative_to(ROOT)}: {image.width}x{image.height}px, "
          f"{opening.MAP_W}x{opening.MAP_H} tiles, "
          f"{_unique_indexed_tiles(image, slots)} unique indexed tiles")


if __name__ == "__main__":
    main()
