"""Generate the isolated M-V1 opening character sprite candidates.

Run with the project's managed Python (Pillow):

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        tools/make_opening_characters.py

This generator owns only the four ``opening_*`` sprite PNGs and their native
GB Studio sidecars.  Sprite colors are strict source proxies: white, gray 160,
and black map to opaque indices 1, 2, and 3; green is transparent.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
OUT_DIR = ROOT / "assets" / "sprites"
sys.path.insert(0, str(TOOLS_DIR))
import opening  # noqa: E402

TRANSPARENT = (0, 255, 0)
PROXY = {
    0: TRANSPARENT,
    1: (255, 255, 255),
    2: (160, 160, 160),
    3: (0, 0, 0),
}
PALETTE_INDEX = {"worker": 0, "marta": 1, "terminal": 2}
ENGINE_SLOTS = 8


def _draw_index(draw: ImageDraw.ImageDraw, xy: tuple[int, int], shade: int) -> None:
    draw.point(xy, fill=PROXY[shade])


def _rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    shade: int,
) -> None:
    draw.rectangle(box, fill=PROXY[shade])


def _poly(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], shade: int) -> None:
    draw.polygon(points, fill=PROXY[shade])


CARRY_VARIANT = "C"  # chosen from docs/carry-variants.png
SHOCK_FRAMES = 3


def _carry_art(variant: str, pose: str, phase: int, rect, point) -> None:
    """24px carry overlay. Shades: 1 pale, 2 orange, 3 dark; rect/point are body-space."""
    dy = -1 if pose == "jump" else 0
    if variant == "old":
        # Forward arm held steady at chest height gripping a cable end:
        # chunky pale plug head over the glove, dark cable drooping in
        # front, and a slack tail trailing behind the hips.
        dy = -1 if pose == "jump" else 0
        # Arm reaches out past the jacket at waist height; the plug sits
        # outside the silhouette and the cable runs down the open air
        # in front of the legs and lies along the ground.
        rect((9, 12 + dy, 11, 13 + dy), 3)
        rect((10, 12 + dy, 10, 12 + dy), 2)
        rect((12, 11 + dy, 14, 11 + dy), 3)    # plug top edge
        rect((11, 12 + dy, 11, 14 + dy), 3)    # plug back edge / wrist
        rect((12, 12 + dy, 14, 14 + dy), 1)    # 3x3 plug head
        rect((12, 15 + dy, 14, 15 + dy), 3)    # plug bottom edge
        point(15, 12 + dy, 3)                  # prongs
        point(15, 14 + dy, 3)
        rect((14, 16 + dy, 14, 21), 3)         # cable drops outside body
        rect((14, 22, 15, 22), 3)              # and lies along the ground
    elif variant == "A":
        # Coil slung over the back shoulder, plug held up at the front shoulder.
        rect((0, 9, 4, 17), 3)
        rect((1, 10, 3, 16), 2)
        for row in (11, 13, 15):
            rect((1, row, 3, row), 3)
        rect((1, 10 + (phase % 2), 1, 10 + (phase % 2)), 1)
        rect((9, 10 + dy, 11, 11 + dy), 3)       # forearm up from the elbow
        rect((11, 7 + dy, 12, 10 + dy), 3)
        rect((11, 3 + dy, 14, 3 + dy), 3)
        rect((11, 4 + dy, 14, 7 + dy), 1)         # plug head
        rect((11, 8 + dy, 14, 8 + dy), 3)
        point(15, 4 + dy, 3)
        point(15, 6 + dy, 3)
    elif variant == "B":
        # Plug in the leading hand; a bright cable drags back to the pole.
        rect((9, 11 + dy, 11, 12 + dy), 3)
        rect((11, 10 + dy, 14, 14 + dy), 3)
        rect((12, 11 + dy, 14, 13 + dy), 1)
        point(15, 11 + dy, 3)
        point(15, 13 + dy, 3)
        for i, (x, y) in enumerate(((2, 14), (1, 15), (1, 16), (0, 17), (0, 18),
                                    (0, 19), (0, 20), (0, 21))):
            rect((x, y, x + 2, y), 3)
        for x, y in ((3, 14), (2, 15), (2, 16), (1, 17), (1, 18), (1, 19), (1, 20), (1, 21)):
            point(x, y, 1)
            point(x - 1 if x > 1 else 0, y, 1)
        rect((0, 22, 3, 22), 3)
    else:
        # Plug held straight overhead with a flickering spark.
        rect((12, 0 + dy, 13, 11), 3)
        rect((12, 1 + dy, 12, 10), 2)
        rect((10, -6 + dy, 14, -6 + dy), 3)
        rect((10, -5 + dy, 14, -1 + dy), 3)
        rect((11, -4 + dy, 13, -2 + dy), 1)
        point(11, -7 + dy, 3)
        point(13, -7 + dy, 3)
        if phase % 2:
            point(9, -4 + dy, 2)
            point(15, -3 + dy, 2)
            point(12, -8 + dy, 2)
        else:
            point(9, -2 + dy, 2)
            point(15, -5 + dy, 2)
            point(10, -7 + dy, 2)


def _shock_frame(phase: int) -> Image.Image:
    """Skeleton-flash electrocution: negative-colour hero, jitter, zap bolts."""
    base = _worker_frame(24, "idle", "right", 0)
    swap = {PROXY[1]: PROXY[3], PROXY[3]: PROXY[1]}
    out = Image.new("RGB", base.size, TRANSPARENT)
    shift = (0, 1, -1)[phase]
    for y in range(base.height):
        for x in range(base.width):
            pixel = base.getpixel((x, y))
            if pixel == TRANSPARENT:
                continue
            if phase != 1:
                pixel = swap.get(pixel, pixel)
            if 0 <= x + shift < base.width:
                out.putpixel((x + shift, y), pixel)
    draw = ImageDraw.Draw(out)
    bolts = (
        (((1, 9), (0, 11), (2, 12), (0, 15)), ((14, 12), (15, 14), (13, 15), (15, 18)), ((8, 1), (6, 3), (9, 4), (7, 6))),
        (((0, 14), (2, 16), (0, 18), (2, 21)), ((15, 8), (13, 10), (15, 12), (13, 14)), ((6, 0), (9, 2), (7, 4), (9, 6))),
        (((2, 8), (0, 10), (2, 13), (0, 16)), ((13, 17), (15, 19), (13, 21), (15, 23)), ((9, 1), (7, 3), (10, 5), (8, 7))),
    )[phase]
    for bolt in bolts:
        draw.line(bolt, fill=PROXY[1] if phase != 1 else PROXY[2])
        for x, y in bolt[1:3]:
            draw.point((x, y), fill=PROXY[2] if phase != 1 else PROXY[1])
    return out


def _worker_frame(
    body_height: int,
    pose: str,
    facing: str,
    phase: int = 0,
    variant: str | None = None,
) -> Image.Image:
    """Draw a compact side-profile electrician, anchored to the same feet."""
    if body_height not in (16, 24):
        raise ValueError(f"unsupported worker body height: {body_height}")
    if pose == "shock":
        return _shock_frame(phase)
    image = Image.new("RGB", (16, 32 if body_height == 24 else 16), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    top = 8 if body_height == 24 else 0
    carry = pose.startswith("carry_")
    if carry:
        pose = pose[len("carry_"):]

    def rect(box: tuple[int, int, int, int], shade: int) -> None:
        _rect(draw, (box[0], box[1] + top, box[2], box[3] + top), shade)

    def poly(points: list[tuple[int, int]], shade: int) -> None:
        _poly(draw, [(x, y + top) for x, y in points], shade)

    def point(x: int, y: int, shade: int) -> None:
        _draw_index(draw, (x, y + top), shade)

    if body_height == 24:
        # Rounded hardhat, short brim, cheek/face profile and a visible ear.
        poly([(5, 0), (10, 0), (12, 2), (12, 3), (13, 3), (13, 4),
              (3, 4), (3, 3), (4, 3), (4, 1)], 3)
        poly([(6, 1), (9, 1), (11, 2), (11, 3), (5, 3), (5, 2)], 1)
        rect((3, 4, 13, 4), 3)  # dark brim separates helmet from face
        rect((7, 5, 11, 7), 3)
        rect((8, 5, 10, 7), 1)
        point(10, 6, 3)  # eye in profile
        point(11, 6, 3)  # nose/visor edge
        rect((7, 8, 9, 9), 3)  # neck and collar

        # Jacket outline and hi-vis orange panels; a broken pale reflective band
        # gives the jacket a recognizable workwear cue at native resolution.
        poly([(5, 8), (10, 8), (12, 10), (12, 15), (11, 17),
              (4, 17), (3, 15), (3, 10)], 3)
        rect((5, 9, 10, 15), 2)
        rect((4, 10, 4, 14), 2)
        rect((11, 10, 11, 14), 2)
        rect((6, 11, 7, 11), 1)
        rect((9, 12, 10, 12), 1)
        rect((5, 16, 10, 17), 3)  # tool belt
        rect((7, 16, 8, 16), 1)  # buckle

        # Rear arm hangs close; the leading arm swings or reaches with the pose.
        if pose == "walk":
            rear_x = (3, 4, 5, 4)[phase]
            front_x = (11, 12, 11, 10)[phase]
            rect((rear_x, 10, rear_x + 1, 14), 3)
            rect((rear_x, 11, rear_x, 13), 2)
            if not carry:
                rect((front_x, 10, front_x + 1, 13), 3)
                rect((front_x, 11, front_x, 12), 2)
                point(front_x + 1, 14, 1)
        elif pose == "jump":
            poly([(4, 10), (5, 8), (6, 9), (5, 13), (4, 14), (3, 13)], 3)
            point(4, 11, 2)
            if not carry:
                poly([(10, 9), (11, 8), (13, 10), (13, 12), (12, 13), (10, 11)], 3)
                point(12, 10, 2)
        elif pose == "repair":
            rect((3, 10, 4, 14), 3)
            rect((3, 11, 3, 13), 2)
            if phase == 0:
                # Reach forward and lower the insulated spanner onto the panel.
                poly([(10, 10), (12, 11), (13, 13), (13, 15),
                      (12, 16), (10, 14)], 3)
                rect((11, 11, 11, 13), 2)
                rect((12, 14, 12, 15), 1)
                rect((11, 15, 13, 15), 1)  # spanner jaw
            else:
                # Raise the elbow and twist the tool through a separate arc.
                poly([(10, 10), (11, 8), (13, 7), (13, 9),
                      (12, 11), (11, 13), (10, 12)], 3)
                rect((11, 9, 11, 10), 2)
                rect((12, 6, 13, 8), 1)
                rect((11, 6, 13, 6), 1)  # raised spanner jaw
        else:
            rect((3, 10, 4, 14), 3)
            rect((3, 11, 3, 13), 2)
            if not carry:
                rect((11, 10, 12, 13), 3)
                point(11, 11, 2)
                point(12, 14, 1)  # glove
            if pose == "idle" and phase:
                # One-pixel vest glint is a quiet breathing beat; feet stay put.
                point(8, 13, 1)

        if carry:
            _carry_art(variant or CARRY_VARIANT, pose, phase, rect, point)

        # Legs and sturdy boots.  Four walk poses move through a full stride
        # without alternating between two exaggerated stamping poses.
        if pose == "walk":
            legs = (
                ((5, 18, 7, 21), (9, 18, 11, 21), (2, 22, 6, 23), (10, 22, 13, 23)),
                ((5, 18, 7, 21), (9, 18, 10, 20), (4, 22, 7, 23), (9, 21, 12, 23)),
                ((5, 18, 7, 21), (9, 18, 11, 21), (3, 22, 6, 23), (10, 22, 13, 23)),
                ((6, 18, 8, 20), (9, 18, 11, 21), (4, 21, 7, 23), (9, 22, 12, 23)),
            )[phase]
            for box in legs:
                rect(box, 3)
            rect((5, 19, 6, 20), 2)
            rect((10, 19, 10, 20), 2)
        elif pose == "jump":
            poly([(5, 18), (7, 18), (8, 20), (7, 21), (4, 20)], 3)
            poly([(9, 18), (11, 18), (12, 20), (11, 21), (8, 20)], 3)
            rect((3, 21, 6, 22), 3)
            rect((10, 21, 13, 22), 3)
        else:
            rect((5, 18, 7, 21), 3)
            rect((9, 18, 11, 21), 3)
            rect((4, 22, 7, 23), 3)
            rect((9, 22, 12, 23), 3)
            rect((5, 23, 6, 23), 1)
            rect((10, 23, 11, 23), 1)
            if pose == "walk":
                # Subtle sole changes preserve the fixed floor/feet anchor.
                point(6 + (phase % 2), 23, 1)
                point(10 + (phase % 2), 23, 1)
    else:
        # Small fixture: preserve the same silhouette cues while reserving
        # enough pixels for a clean hat, profile, high-vis torso and boots.
        poly([(6, 0), (9, 0), (11, 2), (11, 3), (12, 3), (12, 4),
              (4, 4), (4, 3), (5, 3), (5, 1)], 3)
        poly([(7, 1), (9, 1), (10, 2), (10, 3), (6, 3), (6, 2)], 1)
        rect((4, 4, 12, 4), 3)  # crisp helmet brim
        rect((8, 5, 11, 6), 3)
        rect((8, 5, 9, 6), 1)
        point(10, 5, 3)
        point(11, 5, 3)
        point(8, 7, 3)
        poly([(5, 6), (10, 6), (12, 8), (11, 11), (5, 11), (4, 9)], 3)
        rect((6, 7, 10, 10), 2)
        point(6, 8, 1)
        point(9, 9, 1)
        rect((5, 11, 10, 12), 3)
        point(7, 11, 1)

        if pose == "walk":
            # Alternating near/far limb silhouettes with two in-between poses.
            arm_boxes = (
                ((3, 7, 4, 10), (11, 8, 12, 10)),
                ((3, 8, 4, 10), (10, 7, 12, 9)),
                ((4, 8, 5, 10), (11, 7, 12, 10)),
                ((3, 7, 5, 9), (10, 8, 12, 10)),
            )[phase]
            for arm in arm_boxes[:1 if carry else 2]:
                rect(arm, 3)
            legs = (
                ((5, 12, 7, 14), (9, 12, 11, 13), (2, 14, 6, 15), (10, 14, 13, 15)),
                ((5, 12, 7, 13), (9, 12, 11, 14), (4, 14, 7, 15), (9, 14, 12, 15)),
                ((5, 12, 7, 14), (9, 12, 11, 13), (3, 14, 6, 15), (10, 14, 13, 15)),
                ((5, 12, 7, 13), (9, 12, 11, 14), (4, 14, 7, 15), (9, 14, 12, 15)),
            )[phase]
            for leg in legs:
                rect(leg, 3)
            point(6 + phase % 2, 15, 1)
            point(10 + phase % 2, 15, 1)
        elif pose == "jump":
            poly([(4, 7), (5, 5), (6, 6), (5, 9), (4, 10), (3, 9)], 3)
            if not carry:
                poly([(10, 6), (11, 5), (13, 7), (12, 9), (10, 8)], 3)
            poly([(5, 12), (7, 12), (8, 13), (7, 14), (4, 13)], 3)
            poly([(9, 12), (11, 12), (12, 13), (11, 14), (8, 13)], 3)
            rect((3, 14, 6, 14), 3)
            rect((10, 14, 13, 14), 3)
            point(4, 15, 1)
            point(12, 15, 1)
        elif pose == "repair":
            rect((3, 8, 4, 10), 3)
            if phase == 0:
                # Reach out and down; pale pixels make the spanner legible.
                poly([(10, 8), (12, 8), (13, 9), (13, 11),
                      (12, 12), (10, 10)], 3)
                rect((11, 9, 12, 9), 2)
                rect((12, 11, 13, 12), 1)
                point(13, 13, 1)
            else:
                # Elbow raised, with the spanner lifted for a small twist.
                poly([(10, 8), (11, 6), (13, 6), (13, 8),
                      (12, 9), (10, 10)], 3)
                rect((11, 7, 12, 7), 2)
                rect((12, 5, 13, 6), 1)
                point(13, 5, 1)
            rect((5, 12, 7, 14), 3)
            rect((9, 12, 11, 14), 3)
            rect((3, 14, 7, 15), 3)
            rect((9, 14, 13, 15), 3)
            point(5, 15, 1)
            point(11, 15, 1)
        else:
            rect((3, 8, 4, 10), 3)
            rect((3, 9, 3, 9), 2)
            if not carry:
                rect((11, 8, 12, 10), 3)
                point(12, 11, 1)
            rect((5, 12, 7, 14), 3)
            rect((9, 12, 11, 14), 3)
            rect((3, 14, 7, 15), 3)
            rect((9, 14, 13, 15), 3)
            point(5, 15, 1)
            point(11, 15, 1)

        if carry:
            dy = -1 if pose == "jump" else 0
            # Arm reaches out past the jacket; plug sits outside the silhouette.
            rect((9, 8 + dy, 11, 9 + dy), 3)
            rect((10, 8 + dy, 10, 8 + dy), 2)
            rect((12, 7 + dy, 14, 7 + dy), 3)    # plug top edge
            rect((11, 8 + dy, 11, 10 + dy), 3)   # plug back edge / wrist
            rect((12, 8 + dy, 14, 10 + dy), 1)   # 3x3 plug head
            rect((12, 11 + dy, 14, 11 + dy), 3)  # plug bottom edge
            point(15, 8 + dy, 3)                 # prongs
            point(15, 10 + dy, 3)
            rect((14, 12 + dy, 14, 14 + dy), 3)  # cable drops outside body
            rect((14, 15, 15, 15), 3)            # and lies along the ground

        if pose == "idle" and phase:
            # One-pixel reflective glint is the quiet breathing beat; feet,
            # helmet and collision bounds remain unchanged.
            point(8, 8, 1)

    if facing == "left":
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    elif facing != "right":
        raise ValueError(f"unsupported facing: {facing}")
    return image


MARTA_ROWS = (
    "......3333......",
    ".....333333.....",
    "....33222233....",
    "...3321111233...",
    "...3311111133...",
    "...3313113133...",
    "...3313113133...",
    "....33111133....",
    ".....311113.....",
    "......3333......",
    "...3322222233...",
    "..332222222233..",
    "..322223322223..",
    "..322223322223..",
    "..322221122223..",
    "..322221122223..",
    "..332222222233..",
    "...3222222223...",
    "...3222222223...",
    "..322222222223..",
    "..322222222223..",
    "..333333333333..",
    "....311331133...",
    "...3333..3333...",
)


def _marta_frame(powered: bool, phase: int = 0) -> Image.Image:
    """24px older neighbour on a 16x32 canvas, feet on the bottom row.

    Hood (3) frames a skin (1) face with two-pixel-tall eyes and a mouth;
    the shawl (2) and clasped hands read at 1x. Three inks only.
    """
    grid = [list(row) for row in MARTA_ROWS]

    def put(x: int, y: int, shade: int) -> None:
        grid[y][x] = str(shade)

    # Mouth: flat worried line (row 8 is the chin row).
    put(7, 8, 3)
    put(8, 8, 3)
    if powered:
        # Relieved: closed happy eyes, wide smile, open raised arms.
        for x in (6, 9):
            put(x, 5, 1)
        put(6, 8, 3)
        put(9, 8, 3)
        for x in (7, 8):
            put(x, 14, 2)
            put(x, 15, 2)
        for x, y in ((1, 9), (2, 9), (1, 10), (2, 10), (13, 9), (14, 9), (13, 10), (14, 10)):
            put(x, y, 1)
        for x, y in ((2, 11), (13, 11), (2, 12), (13, 12)):
            put(x, y, 3)
    elif phase:
        # Blink: top eye row closes, bottom row stays.
        put(6, 5, 1)
        put(9, 5, 1)
    image = Image.new("RGB", (16, 32), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ".":
                _draw_index(draw, (x, y + 8), int(ch))
    return image


def _terminal_frame(on: bool) -> Image.Image:
    image = Image.new("RGB", (8, 16), TRANSPARENT)
    draw = ImageDraw.Draw(image)
    # A compact status/tool badge whose visible ink lives only in the lower
    # half of the hardware's 8x16 object.
    _poly(draw, [(3, 9), (5, 9), (7, 11), (7, 14), (5, 15), (2, 15),
                 (0, 13), (0, 11)], 3)
    _poly(draw, [(3, 10), (5, 10), (6, 11), (6, 13), (5, 14), (2, 14),
                 (1, 13), (1, 11)], 1)
    if on:
        _rect(draw, (3, 11, 5, 13), 2)
        _draw_index(draw, (4, 11), 1)
    else:
        _rect(draw, (3, 11, 5, 13), 3)
        _rect(draw, (4, 12, 4, 12), 1)
    return image


def _sheet(frames: list[Image.Image], frame_width: int, frame_height: int) -> Image.Image:
    result = Image.new("RGB", (frame_width * len(frames), frame_height), TRANSPARENT)
    for index, frame in enumerate(frames):
        if frame.size != (frame_width, frame_height):
            raise ValueError(f"frame {index} has {frame.size}, expected {(frame_width, frame_height)}")
        result.paste(frame, (index * frame_width, 0))
    return result


def _source_regions(canvas_height: int) -> list[tuple[int, int]]:
    if canvas_height == 32:
        # GB Studio's 8x16 OBJ y position is the negation of tile.y.  Keeping
        # source row 0 at object y=16 and row 16 at object y=0 places the two
        # object bands in source order without changing the feet anchor.
        return [(16, 0), (0, 16)]
    return [(0, 0)]


def _frame_tiles(
    name: str,
    frame_index: int,
    state_index: int,
    animation_index: int,
    animation_frame_index: int,
    palette_index: int,
    sheet: Image.Image,
    canvas_width: int,
    canvas_height: int,
) -> list[dict]:
    frame_x = frame_index * canvas_width
    tiles: list[dict] = []
    for y, source_y in _source_regions(canvas_height):
        for x in range(0, canvas_width, 8):
            crop = sheet.crop((frame_x + x, source_y, frame_x + x + 8, source_y + 16))
            if not any(pixel != TRANSPARENT for pixel in crop.get_flattened_data()):
                continue
            key = (f"{name}:state:{state_index}:animation:{animation_index}:"
                   f"frame:{animation_frame_index}:object:{x}:{source_y}")
            tiles.append({
                "id": opening.resource_id(key + ":tile"),
                "x": x,
                "y": y,
                "sliceX": frame_x + x,
                "sliceY": source_y,
                "flipX": False,
                "flipY": False,
                "palette": 0,
                "paletteIndex": palette_index,
                "objPalette": "OBP0",
                "priority": False,
            })
    return tiles


def _sidecar(
    name: str,
    sheet: Image.Image,
    canvas_width: int,
    canvas_height: int,
    bounds: tuple[int, int, int, int],
    palette_index: int,
    states: list[dict],
    anim_speed: int,
) -> dict:
    state_data: list[dict] = []
    tile_signatures: set[bytes] = set()
    for state_index, state in enumerate(states):
        animations: list[dict] = []
        authored_animations = state["animations"]
        if len(authored_animations) != ENGINE_SLOTS:
            raise ValueError(f"{name}/{state['name']}: expected exactly 8 animation slots")
        for animation_index, frame_indices in enumerate(authored_animations):
            animation_frames: list[dict] = []
            for animation_frame_index, frame_index in enumerate(frame_indices):
                if not 0 <= frame_index < sheet.width // canvas_width:
                    raise ValueError(f"{name}: source frame {frame_index} is outside the sheet")
                tiles = _frame_tiles(
                    name, frame_index, state_index, animation_index,
                    animation_frame_index, palette_index, sheet,
                    canvas_width, canvas_height,
                )
                for tile in tiles:
                    crop = sheet.crop((
                        tile["sliceX"], tile["sliceY"],
                        tile["sliceX"] + 8, tile["sliceY"] + 16,
                    ))
                    tile_signatures.add(bytes(
                        shade
                        for pixel in crop.get_flattened_data()
                        for shade, proxy in PROXY.items()
                        if pixel == proxy
                    ))
                frame_key = (f"{name}:state:{state_index}:animation:{animation_index}:"
                             f"frame:{animation_frame_index}")
                animation_frames.append({
                    "id": opening.resource_id(frame_key),
                    "tiles": tiles,
                })
            if not animation_frames:
                blank_key = f"{name}:state:{state_index}:animation:{animation_index}:empty-frame"
                animation_frames.append({
                    "id": opening.resource_id(blank_key),
                    "tiles": [],
                })
            animation_key = f"{name}:state:{state_index}:animation:{animation_index}"
            animations.append({
                "id": opening.resource_id(animation_key),
                "frames": animation_frames,
            })
        state_data.append({
            "id": opening.resource_id(f"{name}:state:{state_index}"),
            "name": state["name"],
            "animationType": state["animationType"],
            "flipLeft": False,
            "animations": animations,
        })

    return {
        "_resourceType": "sprite",
        "id": opening.resource_id(f"sprite:{name}"),
        "name": name,
        "symbol": f"sprite_{name}",
        "filename": f"{name}.png",
        "width": sheet.width,
        "height": sheet.height,
        "checksum": "",
        "numTiles": len(tile_signatures),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": canvas_width,
        "canvasHeight": canvas_height,
        "boundsX": bounds[0],
        "boundsY": bounds[1],
        "boundsWidth": bounds[2],
        "boundsHeight": bounds[3],
        "animSpeed": anim_speed,
        "spriteMode": "8x16",
        "states": state_data,
    }


def _worker_asset(name: str, body_height: int) -> tuple[str, Image.Image, dict]:
    frame_height = 32 if body_height == 24 else 16
    frames: list[Image.Image] = []
    source: dict[tuple[str, str, int], int] = {}

    def add(pose: str, facing: str, phase: int = 0) -> int:
        key = (pose, facing, phase)
        if key not in source:
            source[key] = len(frames)
            frames.append(_worker_frame(body_height, pose, facing, phase))
        return source[key]

    idle_right = [add("idle", "right", 0), add("idle", "right", 1)]
    idle_left = [add("idle", "left", 0), add("idle", "left", 1)]
    jump_right = [add("jump", "right")]
    jump_left = [add("jump", "left")]
    walk_right = [add("walk", "right", phase) for phase in range(4)]
    walk_left = [add("walk", "left", phase) for phase in range(4)]
    climb_placeholder = [idle_right[0]]  # Native climbing slot; no fall slot exists.
    repair = [add("repair", "right", phase) for phase in range(2)]
    c_idle_right = [add("carry_idle", "right", p) for p in range(2)]
    c_idle_left = [add("carry_idle", "left", p) for p in range(2)]
    c_jump_right = [add("carry_jump", "right")]
    c_jump_left = [add("carry_jump", "left")]
    c_walk_right = [add("carry_walk", "right", p) for p in range(4)]
    c_walk_left = [add("carry_walk", "left", p) for p in range(4)]
    shock = [add("shock", "right", p) for p in range(SHOCK_FRAMES)] if body_height == 24 else []
    carry_state = {
        "name": "Carry",
        "animationType": "platform_player",
        "animations": [
            c_idle_right, c_idle_left, c_jump_right, c_jump_left,
            c_walk_right, c_walk_left, [c_idle_right[0]], [],
        ],
    }
    shock_state = {
        "name": "Shock",
        "animationType": "fixed",
        "animations": [shock, [], [], [], [], [], [], []],
    }
    default = {
        "name": "Default",
        "animationType": "platform_player",
        "animations": [
            idle_right, idle_left, jump_right, jump_left,
            walk_right, walk_left, climb_placeholder, [],
        ],
    }
    repair_state = {
        "name": "Repair",
        "animationType": "fixed",
        "animations": [repair, [], [], [], [], [], [], []],
    }
    sheet = _sheet(frames, 16, frame_height)
    bounds = (2, -8, 12, 16) if body_height == 16 else (2, -16, 12, 24)
    meta = _sidecar(
        name, sheet, 16, frame_height, bounds, PALETTE_INDEX["worker"],
        [default, repair_state, carry_state] + ([shock_state] if shock else []), anim_speed=10,
    )

    # Validate rendered source pixels, not merely different metadata IDs.
    def source_frame_bytes(frame_index: int) -> bytes:
        return sheet.crop((frame_index * 16, 0, (frame_index + 1) * 16, frame_height)).tobytes()

    def require_distinct(label: str, frame_indices: list[int]) -> None:
        rendered = [source_frame_bytes(index) for index in frame_indices]
        if len(rendered) != len(set(rendered)):
            raise AssertionError(f"{name}: {label} contains identical assembled frames")

    require_distinct("idle right", idle_right)
    require_distinct("idle left", idle_left)
    require_distinct("walk right", walk_right)
    require_distinct("walk left", walk_left)
    require_distinct("carry idle right", c_idle_right)
    require_distinct("carry idle left", c_idle_left)
    require_distinct("carry walk right", c_walk_right)
    require_distinct("carry walk left", c_walk_left)
    for d, c in zip(idle_right + jump_right + walk_right + idle_left + jump_left + walk_left,
                    c_idle_right + c_jump_right + c_walk_right + c_idle_left + c_jump_left + c_walk_left):
        if source_frame_bytes(d) == source_frame_bytes(c):
            raise AssertionError(f"{name}: Carry frame identical to Default")
    if source_frame_bytes(repair[0]) == source_frame_bytes(repair[1]):
        raise AssertionError(f"{name}: Repair phases render identical pixels")
    return name, sheet, meta


def _marta_asset() -> tuple[str, Image.Image, dict]:
    frames = [_marta_frame(False, 0), _marta_frame(False, 1), _marta_frame(True)]
    sheet = _sheet(frames, 16, 32)
    states = [
        {
            "name": "Waiting",
            "animationType": "fixed",
            "animations": [[0, 1], [], [], [], [], [], [], []],
        },
        {
            "name": "Powered",
            "animationType": "fixed",
            "animations": [[2], [], [], [], [], [], [], []],
        },
    ]
    meta = _sidecar(
        "opening_marta", sheet, 16, 32, (2, -16, 12, 24),
        PALETTE_INDEX["marta"], states, anim_speed=12,
    )
    return "opening_marta", sheet, meta


def _terminal_asset() -> tuple[str, Image.Image, dict]:
    frames = [_terminal_frame(False), _terminal_frame(True)]
    sheet = _sheet(frames, 8, 16)
    states = [
        {"name": "Off", "animationType": "fixed", "animations": [[0], [], [], [], [], [], [], []]},
        {"name": "On", "animationType": "fixed", "animations": [[1], [], [], [], [], [], [], []]},
    ]
    meta = _sidecar(
        "opening_terminal", sheet, 8, 16, (0, 0, 8, 8),
        PALETTE_INDEX["terminal"], states, anim_speed=15,
    )
    return "opening_terminal", sheet, meta


def _validate(name: str, image: Image.Image, meta: dict) -> None:
    canvas_w, canvas_h = meta["canvasWidth"], meta["canvasHeight"]
    if image.size != (meta["width"], meta["height"]):
        raise AssertionError(f"{name}: sheet dimensions disagree with metadata")
    if image.width % canvas_w or image.height != canvas_h:
        raise AssertionError(f"{name}: sheet is not aligned to its native frame")
    if set(image.get_flattened_data()) - set(PROXY.values()):
        raise AssertionError(f"{name}: PNG contains non-proxy pixels")
    for y in range(0, image.height, 8):
        for x in range(0, image.width, 8):
            colors = set(image.crop((x, y, x + 8, y + 8)).get_flattened_data())
            if len(colors) > 4:
                raise AssertionError(f"{name}: tile ({x // 8},{y // 8}) exceeds 4 colors")
    if len(meta["states"]) != (4 if name == "opening_worker24" else 3 if name.startswith("opening_worker") else 2) or any(len(state["animations"]) != 8 for state in meta["states"]):
        raise AssertionError(f"{name}: expected three states with eight native animation slots")
    if meta["_resourceType"] != "sprite" or meta["spriteMode"] != "8x16":
        raise AssertionError(f"{name}: not a native 8x16 sprite sidecar")
    if meta["id"] != opening.resource_id(f"sprite:{name}"):
        raise AssertionError(f"{name}: non-deterministic resource identity")
    for state in meta["states"]:
        for animation in state["animations"]:
            for frame in animation["frames"]:
                for tile in frame["tiles"]:
                    if meta["canvasHeight"] == 32:
                        expected = (16, 0) if tile["sliceY"] == 0 else (0, 16)
                        if (tile["y"], tile["sliceY"]) != expected:
                            raise AssertionError(f"{name}: incorrect tall-object Y/source mapping")
                    elif tile["y"] != 0:
                        raise AssertionError(f"{name}: unexpected object Y offset")
    if name == "opening_terminal":
        if any(image.getpixel((x, y)) != TRANSPARENT for y in range(8) for x in range(image.width)):
            raise AssertionError("terminal art must be confined to the lower 8 source rows")
        if meta["boundsY"] != 0 or (meta["boundsWidth"], meta["boundsHeight"]) != (8, 8):
            raise AssertionError("terminal bounds must describe its visible 8x8 lower icon")
    if name == "opening_worker24" and (meta["boundsY"], meta["boundsHeight"]) != (-16, 24):
        raise AssertionError("24px worker bounds must retain the feet anchor")
    if name.startswith("opening_worker"):
        expected_counts = [2, 2, 1, 1, 4, 4, 1, 0]
        if [len(animation["frames"]) if animation["frames"][0]["tiles"] else 0
            for animation in meta["states"][0]["animations"]] != expected_counts:
            raise AssertionError(f"{name}: Default state does not preserve native platform slots")
        if [len(animation["frames"]) if animation["frames"][0]["tiles"] else 0
            for animation in meta["states"][1]["animations"]] != [2, 0, 0, 0, 0, 0, 0, 0]:
            raise AssertionError(f"{name}: Repair must be a two-frame fixed state")
        expected_objects = 2 if canvas_h == 16 else 4
        for state in meta["states"]:
            for animation in state["animations"]:
                for frame in animation["frames"]:
                    if frame["tiles"] and len(frame["tiles"]) != expected_objects:
                        raise AssertionError(f"{name}: pose exceeds/undershoots object budget")
        frame_count = image.width // canvas_w
        body_top = 0 if canvas_h == 16 else 8
        body_bottom = canvas_h - 1
        for frame_index in range(frame_count):
            frame = image.crop((frame_index * canvas_w, 0,
                                (frame_index + 1) * canvas_w, canvas_h))
            points = [
                (x, y)
                for y in range(canvas_h)
                for x in range(canvas_w)
                if frame.getpixel((x, y)) != TRANSPARENT
            ]
            if not points:
                raise AssertionError(f"{name}: empty source pose {frame_index}")
            xs, ys = zip(*points)
            # The last 14 frames are Carry; the held plug/cable may extend
            # past the 12px body (art only; collision bounds are unchanged).
            shock_n = SHOCK_FRAMES if canvas_h == 32 else 0
            is_carry = frame_count - 14 - shock_n <= frame_index < frame_count - shock_n
            is_shock = frame_index >= frame_count - shock_n
            max_x = 15 if (is_carry or is_shock) else 13
            if min(xs) < (0 if (is_carry or is_shock) else 2) or max(xs) > max_x:
                raise AssertionError(f"{name}: artwork escaped its 12-pixel body width")
            if min(ys) < (0 if (is_carry or is_shock) else body_top) or max(ys) > body_bottom:
                raise AssertionError(f"{name}: artwork escaped the body region/feet anchor")
            if canvas_h == 32 and max(ys) < body_bottom - 1:
                raise AssertionError(f"{name}: tall candidate lost its lower-foot placement")
    elif name == "opening_marta":
        if (canvas_h, meta["boundsY"], meta["boundsHeight"]) != (32, -16, 24):
            raise AssertionError("Amara must be a bottom-anchored 24px figure on a 16x32 canvas")
        waiting = meta["states"][0]["animations"]
        powered = meta["states"][1]["animations"]
        if len(waiting[0]["frames"]) != 2 or len(powered[0]["frames"]) != 1:
            raise AssertionError("Amara needs a two-frame Waiting idle and one Powered pose")
    elif name == "opening_terminal":
        if any(len(state["animations"][0]["frames"]) != 1 for state in meta["states"]):
            raise AssertionError("terminal Off/On states must each use one fixed icon frame")


def make_assets() -> Iterable[tuple[str, Image.Image, dict]]:
    """Return each owned resource as ``(name, image, native sidecar)``."""
    assets = [
        _worker_asset("opening_worker24", 24),
        _marta_asset(),
        _terminal_asset(),
    ]
    for name, image, meta in assets:
        _validate(name, image, meta)
    return assets


def _check_ownership(name: str, png_path: Path, sidecar_path: Path, meta: dict) -> None:
    if not png_path.exists() and not sidecar_path.exists():
        return
    if not png_path.exists() or not sidecar_path.exists():
        raise FileExistsError(f"Refusing to replace an unpaired owned sprite: {png_path}")
    existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if existing.get("id") != meta["id"] or existing.get("name") != name:
        raise FileExistsError(f"Refusing to replace a different sprite resource: {sidecar_path}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    assets = list(make_assets())
    # Preflight every destination before writing any of them, so a collision
    # on a later resource cannot leave a partially refreshed asset set.
    for name, _image, meta in assets:
        png_path = OUT_DIR / f"{name}.png"
        sidecar_path = Path(str(png_path) + ".gbsres")
        _check_ownership(name, png_path, sidecar_path, meta)
    for name, image, meta in assets:
        png_path = OUT_DIR / f"{name}.png"
        sidecar_path = Path(str(png_path) + ".gbsres")
        image.save(png_path, format="PNG", optimize=False)
        meta["checksum"] = hashlib.sha1(png_path.read_bytes()).hexdigest()
        sidecar_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
        with Image.open(png_path) as check:
            if check.mode != "RGB" or check.size != image.size:
                raise AssertionError(f"{name}: persisted PNG failed dimension/mode check")
        reread = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if reread != meta or reread["checksum"] != hashlib.sha1(png_path.read_bytes()).hexdigest():
            raise AssertionError(f"{name}: persisted sidecar/checksum validation failed")
        print(f"generated assets/sprites/{name}.png + .gbsres ({image.width}x{image.height})")


if __name__ == "__main__":
    main()
