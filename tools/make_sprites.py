"""Generate the Mister CFE sprite art and GB Studio sprite sidecars.

Palette colors and palette-slot ordering come from ``tools/level.py``. Run
with the project's managed Python (which provides Pillow):

    python tools/make_sprites.py

All IDs are UUID5 values, so a repeated run produces stable resource files.
Existing unrelated files are never replaced; an existing generated output is
recognized by its deterministic resource ID before it is refreshed.
"""

from __future__ import annotations

import hashlib
import json
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from PIL import Image, ImageDraw

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))
import level  # noqa: E402 (palette and scene source of truth)

OUT_DIR = PROJECT_DIR / "assets" / "sprites"
NAMESPACE = uuid.UUID("c31813d9-75ae-55dd-b5dc-fde97dc6516a")
TILE = level.TILE
FRAME_W, FRAME_H = 16, 16
ENGINE_ANIMATION_SLOTS = 8
TRANSPARENT = (0, 0, 0, 0)
SPRITE_PALETTES = {
    name: tuple(
        tuple(int(color[i : i + 2], 16) for i in (0, 2, 4)) + (255,)
        for color in colors
    )
    for name, colors in level.SPRITE_PALETTES
}
PALETTE_SLOTS = {name: i for i, (name, _colors) in enumerate(level.SPRITE_PALETTES)}


def stable_id(key: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"modretro-chromatic:mr-cfe:sprite:{key}"))


def new_frame_sheet(frame_count: int) -> Image.Image:
    return Image.new("RGBA", (FRAME_W * frame_count, FRAME_H), TRANSPARENT)


def ink(draw: ImageDraw.ImageDraw, x: int, y: int, palette: str, color: int) -> None:
    draw.point((x, y), fill=SPRITE_PALETTES[palette][color])


def rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    palette: str,
    color: int,
) -> None:
    draw.rectangle(box, fill=SPRITE_PALETTES[palette][color])


def line(
    draw: ImageDraw.ImageDraw,
    coords: tuple[int, ...],
    palette: str,
    color: int,
) -> None:
    draw.line(coords, fill=SPRITE_PALETTES[palette][color], width=1)


def player_frame(sheet: Image.Image, index: int, pose: str, facing: str, phase: int = 0) -> None:
    """Draw the side-on CFE lineworker in a compact 16x16 silhouette."""
    frame = Image.new("RGBA", (FRAME_W, FRAME_H), TRANSPARENT)
    d = ImageDraw.Draw(frame)
    p = "player"
    outline, vest, workwear, light = 3, 1, 2, 0

    # Hardhat, brim and profile: the cream pixels are also the face, but a
    # one-pixel dark contour keeps the helmet distinct at native 1x.
    rect(d, (5, 1, 10, 4), p, outline)
    rect(d, (6, 1, 9, 2), p, light)
    rect(d, (6, 3, 10, 3), p, light)
    rect(d, (4, 4, 11, 4), p, outline)
    rect(d, (7, 4, 11, 7), p, outline)
    rect(d, (8, 5, 10, 6), p, light)
    ink(d, 10, 5, p, outline)
    ink(d, 8, 7, p, vest)  # reflective collar/neck

    # Orange high-vis vest over dark workwear, with an explicit seam and belt.
    rect(d, (4, 7, 11, 11), p, outline)
    rect(d, (5, 8, 10, 10), p, vest)
    rect(d, (7, 8, 7, 10), p, outline)
    rect(d, (5, 11, 10, 11), p, outline)
    rect(d, (8, 11, 8, 11), p, vest)  # belt buckle

    if pose == "idle":
        # A relaxed, slightly staggered stance; one hand rests by the tool belt.
        rect(d, (3, 8, 4, 10), p, outline)
        ink(d, 3, 9, p, workwear)
        rect(d, (11, 8, 12, 10), p, outline)
        ink(d, 12, 9, p, workwear)
        rect(d, (5, 12, 7, 14), p, outline)
        rect(d, (6, 12, 6, 13), p, workwear)
        rect(d, (8, 12, 10, 14), p, outline)
        rect(d, (9, 12, 9, 13), p, workwear)
        rect(d, (4, 14, 7, 15), p, outline)
        rect(d, (9, 14, 12, 15), p, outline)
        ink(d, 5, 14, p, workwear)
        ink(d, 10, 14, p, workwear)
        ink(d, 11, 10, p, vest)  # small insulated tool grip
    elif pose == "run":
        # Opposed arm/leg swings give a clear walk cycle without broad jitter.
        if phase == 0:
            rect(d, (2, 8, 4, 9), p, outline)
            ink(d, 2, 9, p, workwear)
            rect(d, (11, 9, 13, 10), p, outline)
            ink(d, 13, 9, p, workwear)
            rect(d, (4, 12, 7, 14), p, outline)
            rect(d, (5, 12, 6, 13), p, workwear)
            rect(d, (2, 14, 6, 15), p, outline)
            rect(d, (9, 12, 11, 13), p, outline)
            ink(d, 10, 12, p, workwear)
            rect(d, (10, 13, 13, 14), p, outline)
        else:
            rect(d, (3, 9, 5, 10), p, outline)
            ink(d, 3, 9, p, workwear)
            rect(d, (11, 8, 13, 9), p, outline)
            ink(d, 13, 8, p, workwear)
            rect(d, (4, 12, 6, 13), p, outline)
            ink(d, 5, 12, p, workwear)
            rect(d, (2, 13, 5, 14), p, outline)
            rect(d, (8, 12, 11, 14), p, outline)
            rect(d, (9, 12, 10, 13), p, workwear)
            rect(d, (9, 14, 13, 15), p, outline)
    elif pose == "jump":
        # Lifted arms and tucked knees read as a jump; boots separate in flight.
        rect(d, (3, 5, 5, 7), p, outline)
        rect(d, (4, 5, 4, 6), p, workwear)
        rect(d, (10, 5, 12, 7), p, outline)
        rect(d, (11, 5, 11, 6), p, workwear)
        rect(d, (4, 12, 7, 13), p, outline)
        rect(d, (5, 12, 6, 12), p, workwear)
        rect(d, (8, 12, 11, 13), p, outline)
        rect(d, (9, 12, 10, 12), p, workwear)
        rect(d, (2, 13, 6, 14), p, outline)
        rect(d, (9, 13, 13, 14), p, outline)
    elif pose == "climb":
        # Alternating reaches and bent knees suggest climbing without loose parts.
        if phase == 0:
            rect(d, (3, 5, 5, 7), p, outline)
            rect(d, (4, 5, 4, 6), p, workwear)
            rect(d, (11, 8, 13, 10), p, outline)
            ink(d, 12, 9, p, workwear)
            rect(d, (5, 12, 7, 14), p, outline)
            ink(d, 6, 12, p, workwear)
            rect(d, (8, 12, 10, 13), p, outline)
            ink(d, 9, 12, p, workwear)
            rect(d, (4, 14, 7, 15), p, outline)
            rect(d, (8, 13, 12, 14), p, outline)
        else:
            rect(d, (3, 8, 5, 10), p, outline)
            ink(d, 4, 9, p, workwear)
            rect(d, (10, 5, 12, 7), p, outline)
            rect(d, (11, 5, 11, 6), p, workwear)
            rect(d, (5, 12, 7, 13), p, outline)
            ink(d, 6, 12, p, workwear)
            rect(d, (8, 12, 10, 14), p, outline)
            ink(d, 9, 12, p, workwear)
            rect(d, (4, 13, 8, 14), p, outline)
            rect(d, (8, 14, 12, 15), p, outline)

    if facing == "left":
        frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    sheet.paste(frame, (index * FRAME_W, 0))


def make_player() -> tuple[Image.Image, list[dict]]:
    # One 16x16 cell per pose; animation arrays below map directly to the
    # seven platform_player animation slots defined by GB Studio.
    sheet = new_frame_sheet(10)
    player_frame(sheet, 0, "idle", "right")
    player_frame(sheet, 1, "idle", "left")
    player_frame(sheet, 2, "jump", "right")
    player_frame(sheet, 3, "jump", "left")
    player_frame(sheet, 4, "run", "right", 0)
    player_frame(sheet, 5, "run", "right", 1)
    player_frame(sheet, 6, "run", "left", 0)
    player_frame(sheet, 7, "run", "left", 1)
    player_frame(sheet, 8, "climb", "right", 0)
    player_frame(sheet, 9, "climb", "right", 1)
    animation_frames = [[0], [1], [2], [3], [4, 5], [6, 7], [8, 9]]
    return sheet, [
        {
            "name": "",
            "animationType": "platform_player",
            "flipLeft": False,
            "palette": "player",
            "animations": animation_frames,
        }
    ]


def local_frame(sheet: Image.Image, index: int, variant: str) -> None:
    d = ImageDraw.Draw(sheet)
    ox = index * FRAME_W
    p = "local"
    # Different rain hats, faces and shawls distinguish the three locals.
    hat = {"marta": (4, 10), "rosa": (5, 9), "kiko": (3, 11)}[variant]
    rect(d, (ox + hat[0], 1, ox + hat[1], 2), p, 3)
    rect(d, (ox + 4, 2, ox + 11, 4), p, 3)
    rect(d, (ox + 5, 3, ox + 10, 6), p, 0)
    rect(d, (ox + 4, 4, ox + 4, 5), p, 3)
    rect(d, (ox + 11, 4, ox + 11, 5), p, 3)
    ink(d, ox + (9 if variant != "rosa" else 6), 4, p, 3)
    rect(d, (ox + 6, 6, ox + 9, 7), p, 1)
    rect(d, (ox + 5, 7, ox + 10, 8), p, 3)
    rect(d, (ox + 4, 8, ox + 11, 11), p, 1)
    rect(d, (ox + 3, 9, ox + 4, 10), p, 3)
    rect(d, (ox + 11, 9, ox + 12, 10), p, 3)
    # Purple shawl/scarf details are intentionally kept to the lower tile.
    rect(d, (ox + 5, 8, ox + 6, 10), p, 2)
    rect(d, (ox + 9, 8, ox + 10, 10), p, 2)
    rect(d, (ox + 5, 11, ox + 10, 13), p, 3)
    rect(d, (ox + 5, 12, ox + 7, 14), p, 1)
    rect(d, (ox + 8, 12, ox + 10, 14), p, 1)
    rect(d, (ox + 4, 15, ox + 7, 15), p, 3)
    rect(d, (ox + 8, 15, ox + 11, 15), p, 3)


def house_frame(sheet: Image.Image, index: int, kind: int, powered: bool = False) -> None:
    d = ImageDraw.Draw(sheet)
    ox = index * FRAME_W
    p = "timber"
    # Each half uses at most three opaque palette colors (plus transparency).
    # Roof silhouette is slightly varied per house, with small chimney/eave.
    ridge = [2, 2, 3, 3, 2][kind]
    rect(d, (ox + 2, ridge + 2, ox + 13, 6), p, 2)
    line(d, (ox + 1, 7, ox + 6, ridge), p, 0)
    line(d, (ox + 8, ridge, ox + 14, 7), p, 3)
    ink(d, ox + 7, ridge, p, 2)
    # Dark eaves and a warm timber face keep the roofline legible at 1x.
    rect(d, (ox + 3, 6, ox + 12, 13), p, 0)
    rect(d, (ox + 4, 7, ox + 11, 13), p, 2)
    rect(d, (ox + 3, 7, ox + 3, 12), p, 2)
    rect(d, (ox + 12, 7, ox + 12, 12), p, 2)
    left_window_color = 3 if powered else 0
    rect(d, (ox + 5, 8, ox + 6, 10), p, 3)
    rect(d, (ox + 5, 9, ox + 5, 9), p, left_window_color)
    rect(d, (ox + 9, 8, ox + 10, 10), p, 3)
    rect(d, (ox + 10, 9, ox + 10, 9), p, 0)
    rect(d, (ox + 7, 10, ox + 8, 13), p, 0)
    rect(d, (ox + 7, 11, ox + 8, 13), p, 2)
    ink(d, ox + 8, 12, p, 3)  # door latch
    # Distinct front details: awning, gable stripe, rain barrel, or antenna.
    if kind == 0:
        line(d, (ox + 9, 5, ox + 12, 5), p, 3)
    elif kind == 1:
        rect(d, (ox + 12, 3, ox + 13, 5), p, 2)
    elif kind == 2:
        rect(d, (ox + 2, 12, ox + 3, 14), p, 0)
    elif kind == 3:
        line(d, (ox + 2, 5, ox + 5, 2), p, 1)
    else:
        rect(d, (ox + 9, 3, ox + 11, 4), p, 3)

    if powered:
        # The bright window adds a fourth opaque shade in this 8x8 tile. Swap
        # its darkest remaining pixels to palette shade 1, which quantizes to
        # the same hardware shade, so the tile stays within four RGBA colors.
        dark = SPRITE_PALETTES[p][0]
        mid = SPRITE_PALETTES[p][1]
        for y in range(8, 16):
            for x in range(ox, ox + 8):
                if sheet.getpixel((x, y)) == dark:
                    sheet.putpixel((x, y), mid)


def substation_art(sheet: Image.Image) -> None:
    d = ImageDraw.Draw(sheet)
    p = "timber"
    # Compact transformer shed / power cabinet with a readable lit status lamp.
    rect(d, (2, 3, 13, 14), p, 0)
    rect(d, (3, 4, 12, 13), p, 2)
    rect(d, (1, 4, 14, 5), p, 2)
    rect(d, (3, 2, 7, 3), p, 2)
    rect(d, (8, 2, 12, 3), p, 3)
    rect(d, (4, 6, 7, 12), p, 0)
    rect(d, (8, 6, 11, 12), p, 0)
    rect(d, (5, 7, 10, 11), p, 0)
    rect(d, (6, 8, 7, 8), p, 2)
    rect(d, (8, 8, 9, 8), p, 3)  # powered indicator
    rect(d, (6, 10, 9, 10), p, 2)
    rect(d, (5, 12, 6, 12), p, 3)  # latch and lower vents
    rect(d, (8, 12, 10, 12), p, 0)
    rect(d, (8, 13, 10, 13), p, 0)
    # Insulator caps read as hardware, not extra palette colors.
    rect(d, (4, 1, 5, 2), p, 2)
    rect(d, (10, 1, 11, 2), p, 2)


def cable_frame(sheet: Image.Image, index: int, kind: str, glint: int | None = None) -> None:
    d = ImageDraw.Draw(sheet)
    ox = index * FRAME_W
    p = "cable"
    if kind == "span":
        line(d, (ox + 7, 0, ox + 7, 15), p, 1)
        line(d, (ox + 8, 0, ox + 8, 15), p, 2)
        rect(d, (ox + 6, 3, ox + 9, 4), p, 3)
        rect(d, (ox + 6, 12, ox + 9, 13), p, 3)
        if glint is not None:
            # A tiny four-point glint sits on the conductor and pulses between
            # cyan and ice-white in the existing span animation.
            ink(d, ox + 7, 6, p, glint)
            rect(d, (ox + 6, 7, ox + 8, 7), p, glint)
            rect(d, (ox + 5, 8, ox + 9, 8), p, glint)
            rect(d, (ox + 6, 9, ox + 8, 9), p, glint)
            ink(d, ox + 7, 10, p, glint)
    elif kind == "junction":
        line(d, (ox + 7, 0, ox + 7, 15), p, 1)
        line(d, (ox + 8, 0, ox + 8, 15), p, 2)
        line(d, (ox + 2, 7, ox + 13, 7), p, 2)
        rect(d, (ox + 5, 5, ox + 10, 10), p, 3)
        rect(d, (ox + 6, 6, ox + 9, 9), p, 1)
    else:  # insulated connector / cable end
        line(d, (ox + 7, 0, ox + 7, 9), p, 1)
        line(d, (ox + 8, 0, ox + 8, 9), p, 2)
        rect(d, (ox + 4, 9, ox + 11, 13), p, 1)
        rect(d, (ox + 5, 10, ox + 10, 12), p, 3)
        rect(d, (ox + 6, 14, ox + 9, 15), p, 2)


def hazard_frame(sheet: Image.Image, index: int, kind: str) -> None:
    d = ImageDraw.Draw(sheet)
    ox = index * FRAME_W
    p = "hazard"
    if kind == "flood":
        # Choppy storm pool with a dark hollow and red-orange warning ripple.
        rect(d, (ox + 2, 8, ox + 13, 12), p, 1)
        line(d, (ox + 1, 8, ox + 4, 7, ox + 7, 8, ox + 10, 7, ox + 14, 8), p, 2)
        rect(d, (ox + 3, 10, ox + 5, 11), p, 0)
        rect(d, (ox + 10, 9, ox + 12, 10), p, 3)
        line(d, (ox + 3, 13, ox + 6, 14, ox + 10, 13, ox + 13, 14), p, 2)
    else:  # live wire: bold, outlined warning bolt
        d.polygon(
            [
                (ox + 7, 1), (ox + 12, 1), (ox + 9, 6), (ox + 13, 6),
                (ox + 5, 15), (ox + 7, 9), (ox + 3, 9),
            ],
            fill=SPRITE_PALETTES[p][3],
            outline=SPRITE_PALETTES[p][0],
        )
        d.polygon(
            [
                (ox + 8, 3), (ox + 10, 3), (ox + 8, 7), (ox + 10, 7),
                (ox + 6, 12), (ox + 7, 8), (ox + 6, 8),
            ],
            fill=SPRITE_PALETTES[p][2],
        )


@dataclass(frozen=True)
class Asset:
    name: str
    sheet: Image.Image
    states: list[dict]
    anim_speed: int | None = 15


def single_frame_states(
    names: list[str], palette: str, source_frames: list[int]
) -> list[dict]:
    return [
        {
            "name": name,
            "animationType": "fixed",
            "flipLeft": False,
            "palette": palette,
            "animations": [[source_frame]],
        }
        for name, source_frame in zip(names, source_frames, strict=True)
    ]


def make_assets() -> list[Asset]:
    player, player_states = make_player()

    locals_sheet = new_frame_sheet(3)
    for i, name in enumerate(("marta", "rosa", "kiko")):
        local_frame(locals_sheet, i, name)

    house_names = ["Marta", "Tomas", "Rosa", "Kiko", "Nuria"]
    houses_sheet = new_frame_sheet(len(house_names) * 2)
    for i in range(5):
        house_frame(houses_sheet, i, i)
        house_frame(houses_sheet, i + len(house_names), i, powered=True)

    station_sheet = new_frame_sheet(1)
    substation_art(station_sheet)

    cable_sheet = new_frame_sheet(4)
    cable_names = ["span", "junction", "connector"]
    cable_frame(cable_sheet, 0, "span", glint=2)
    cable_frame(cable_sheet, 1, "junction")
    cable_frame(cable_sheet, 2, "connector")
    cable_frame(cable_sheet, 3, "span", glint=3)
    cable_states = single_frame_states(cable_names, "cable", [0, 1, 2])
    cable_states[0]["animations"] = [[0, 3]]

    hazard_sheet = new_frame_sheet(2)
    hazard_names = ["floodwater", "live_wire"]
    for i, name in enumerate(("flood", "arc")):
        hazard_frame(hazard_sheet, i, name)

    return [
        Asset("player_platform", player, player_states, 10),
        Asset(
            "locals",
            locals_sheet,
            single_frame_states(["Marta", "Rosa", "Kiko"], "local", [0, 1, 2]),
        ),
        Asset(
            "houses",
            houses_sheet,
            single_frame_states(
                house_names
                + [f"{name} Powered" for name in house_names],
                "timber",
                list(range(len(house_names) * 2)),
            ),
        ),
        Asset(
            "substation",
            station_sheet,
            single_frame_states(["Substation"], "timber", [0]),
        ),
        Asset(
            "cable",
            cable_sheet,
            cable_states,
        ),
        Asset(
            "hazard",
            hazard_sheet,
            single_frame_states(hazard_names, "hazard", [0, 1]),
        ),
    ]


def indexed_sprite_value(pixel: tuple[int, int, int, int]) -> int:
    """Mirror GB Studio's sprite palette bucketing for 2bpp budget checks."""
    r, g, b, a = pixel
    if (g > 249 and r < 180 and b < 20) or (b >= 200 and g < 20) or a < 200:
        return 0
    if g >= 205:
        return 1
    if g >= 130:
        return 2
    return 3


def frame_has_ink(frame: Image.Image) -> bool:
    return frame.getbbox() is not None


def tile_signature(tile: Image.Image) -> tuple[int, ...]:
    return tuple(
        indexed_sprite_value(px)
        for px in tile.convert("RGBA").get_flattened_data()
    )


def frame_meta(
    resource_key: str,
    frame_index: int,
    palette_index: int,
    sheet: Image.Image,
) -> dict:
    frame_x = frame_index * FRAME_W
    tiles = []
    for tile_x in (0, 8):
        crop = sheet.crop((frame_x + tile_x, 0, frame_x + tile_x + 8, FRAME_H))
        if not frame_has_ink(crop):
            continue
        tiles.append(
            {
                "id": stable_id(f"{resource_key}:tile:{frame_index}:{tile_x}"),
                "x": tile_x,
                "y": 0,
                "sliceX": frame_x + tile_x,
                "sliceY": 0,
                "flipX": False,
                "flipY": False,
                "palette": 0,
                "paletteIndex": palette_index,
                "objPalette": "OBP0",
                "priority": False,
            }
        )
    return {"id": stable_id(f"{resource_key}:frame:{frame_index}"), "tiles": tiles}


def build_sidecar(asset: Asset) -> tuple[dict, int, set[tuple[int, ...]], int]:
    resource_id = stable_id(f"resource:{asset.name}")
    source_frame_count = asset.sheet.width // FRAME_W
    states = []
    all_tile_signatures: set[tuple[int, ...]] = set()
    tile_reference_count = 0

    for state_index, state in enumerate(asset.states):
        palette_index = PALETTE_SLOTS[state["palette"]]
        animations = []
        for animation_index in range(ENGINE_ANIMATION_SLOTS):
            source_frames = (
                state["animations"][animation_index]
                if animation_index < len(state["animations"])
                else []
            )
            metasprite_frames = []
            for animation_frame_index, source_frame in enumerate(source_frames):
                if not 0 <= source_frame < source_frame_count:
                    raise ValueError(f"{asset.name}: source frame {source_frame} outside sheet")
                metasprite = frame_meta(asset.name, source_frame, palette_index, asset.sheet)
                metasprite_frames.append(metasprite)
                for tile in metasprite["tiles"]:
                    crop = asset.sheet.crop(
                        (tile["sliceX"], 0, tile["sliceX"] + 8, FRAME_H)
                    )
                    all_tile_signatures.add(tile_signature(crop))
                    tile_reference_count += 1
            if not metasprite_frames:
                # GB Studio sprite states expose eight engine-facing animation
                # slots. Keep unused slots as one blank frame, as in the
                # authored resources, rather than truncating the state.
                metasprite_frames.append(
                    {
                        "id": stable_id(
                            f"{asset.name}:state:{state_index}:animation:{animation_index}:empty-frame"
                        ),
                        "tiles": [],
                    }
                )
            animations.append(
                {
                    "id": stable_id(f"{asset.name}:state:{state_index}:animation:{animation_index}"),
                    "frames": metasprite_frames,
                }
            )
        states.append(
            {
                "id": stable_id(f"{asset.name}:state:{state_index}"),
                "name": state["name"],
                "animationType": state["animationType"],
                "flipLeft": state["flipLeft"],
                "animations": animations,
            }
        )

    sidecar = {
        "_resourceType": "sprite",
        "id": resource_id,
        "name": asset.name,
        "symbol": f"sprite_{asset.name}",
        "states": states,
        "numTiles": len(all_tile_signatures),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": FRAME_W,
        "canvasHeight": FRAME_H,
        "boundsX": 0,
        "boundsY": -8,
        "boundsWidth": FRAME_W,
        "boundsHeight": FRAME_H,
        "animSpeed": asset.anim_speed,
        "filename": f"{asset.name}.png",
        "width": asset.sheet.width,
        "height": asset.sheet.height,
        "spriteMode": "8x16",
        "checksum": "",
    }
    return sidecar, len(all_tile_signatures), all_tile_signatures, tile_reference_count


def verify_asset(asset: Asset, sidecar: dict) -> None:
    image = asset.sheet
    assert image.width % FRAME_W == 0 and image.height == FRAME_H, (
        f"{asset.name}: sheet must be aligned to {FRAME_W}x{FRAME_H} frames"
    )
    # Palette truth and 8x8 color constraints, including transparency as a
    # color. No antialiasing or extra colors are allowed in any hardware tile.
    asset_palettes = {state["palette"] for state in asset.states}
    valid_colors = {TRANSPARENT} | {
        color for name in asset_palettes for color in SPRITE_PALETTES[name]
    }
    assert set(image.get_flattened_data()) <= valid_colors, (
        f"{asset.name}: pixel outside level palettes"
    )
    for y in range(0, image.height, TILE):
        for x in range(0, image.width, TILE):
            crop = image.crop((x, y, x + TILE, y + TILE))
            colors = set(crop.get_flattened_data())
            assert len(colors) <= 4, (
                f"{asset.name}: tile ({x // TILE},{y // TILE}) has {len(colors)} RGBA colors"
            )
    assert sidecar["width"] == image.width and sidecar["height"] == image.height
    assert sidecar["spriteMode"] == "8x16"
    assert sidecar["_resourceType"] == "sprite"
    if asset.name == "player_platform":
        state = sidecar["states"][0]
        assert state["animationType"] == "platform_player"
        assert len(state["animations"]) == ENGINE_ANIMATION_SLOTS
        assert [len(animation["frames"]) for animation in state["animations"]] == [
            1, 1, 1, 1, 2, 2, 2, 1
        ]
        assert len(state["animations"][4]["frames"]) == 2
        assert len(state["animations"][5]["frames"]) == 2
    assert all(
        len(state["animations"]) == ENGINE_ANIMATION_SLOTS for state in sidecar["states"]
    )


def output_exists_belongs_to_us(asset_name: str, png_path: Path, sidecar_path: Path) -> bool:
    if not png_path.exists() and not sidecar_path.exists():
        return False
    if not sidecar_path.exists():
        raise FileExistsError(f"Refusing to replace existing unpaired asset {png_path}")
    existing = json.loads(sidecar_path.read_text(encoding="utf-8"))
    expected_id = stable_id(f"resource:{asset_name}")
    if existing.get("id") != expected_id:
        raise FileExistsError(f"Refusing to replace pre-existing sprite resource {sidecar_path}")
    if not png_path.exists():
        raise FileNotFoundError(f"Generated sidecar exists without PNG: {png_path}")
    return True


def write_asset(asset: Asset) -> tuple[int, set[tuple[int, ...]], int]:
    png_path = OUT_DIR / f"{asset.name}.png"
    sidecar_path = Path(f"{png_path}.gbsres")
    output_exists_belongs_to_us(asset.name, png_path, sidecar_path)
    sidecar, unique_tiles, signatures, tile_references = build_sidecar(asset)
    verify_asset(asset, sidecar)
    asset.sheet.save(png_path, format="PNG", optimize=False)
    sidecar["checksum"] = hashlib.sha1(png_path.read_bytes()).hexdigest()
    sidecar_path.write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    # Re-read the written output to validate persisted file dimensions and JSON.
    with Image.open(png_path) as written:
        assert written.size == (sidecar["width"], sidecar["height"])
        assert written.mode == "RGBA"
    reread = json.loads(sidecar_path.read_text(encoding="utf-8"))
    assert reread == sidecar
    assert sidecar["checksum"] == hashlib.sha1(png_path.read_bytes()).hexdigest()
    print(
        f"generated assets/sprites/{asset.name}.png + sidecar: "
        f"{asset.sheet.width}x{asset.sheet.height}, {unique_tiles} unique 8x16 tiles"
    )
    return unique_tiles, signatures, tile_references


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_resource_tiles = 0
    total_references = 0
    for asset in make_assets():
        count, _signatures, references = write_asset(asset)
        total_resource_tiles += count
        total_references += references
    resource_8x8_equivalent = total_resource_tiles * 2
    assert resource_8x8_equivalent <= 192, (
        f"Conservative sprite tile estimate {resource_8x8_equivalent}/192 exceeds scene budget"
    )
    assert total_references * 2 <= 192, (
        f"Sprite references {total_references * 2}/192 exceed scene budget"
    )
    print(
        f"sprite budget: {total_resource_tiles} per-resource unique 8x16 tiles "
        f"({resource_8x8_equivalent}/192 conservative 8x8 equivalents); "
        f"{total_references} referenced 8x16 tiles "
        f"({total_references * 2}/192 conservative 8x8 equivalents)"
    )


if __name__ == "__main__":
    main()
