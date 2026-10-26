"""Generate a deterministic, three-object warning/burst gust sprite.

The 24x16 authored frame is three native 8x16 objects wide. Only source rows
8..15 contain pixels; GB Studio's 8x16 object offset places that art at actor
Y, matching the authored 24x8 collision footprint. Run with managed Python.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "assets/sprites/climb_gust.png"
METADATA = Path(str(OUTPUT) + ".gbsres")

TRANSPARENT = (0, 255, 0)
OUTLINE = (255, 255, 255)  # sprite index 1; palette's darkest opaque color
MID = (160, 160, 160)     # sprite index 2; palette's middle opaque color
BRIGHT = (0, 0, 0)        # sprite index 3; palette's brightest opaque color
PROXY_COLORS = {TRANSPARENT, OUTLINE, MID, BRIGHT}

FRAME_WIDTH = 24
FRAME_HEIGHT = 16
OBJECT_WIDTH = 8
OBJECTS_PER_FRAME = FRAME_WIDTH // OBJECT_WIDTH
ANIMATION_SLOTS = 8
PALETTE_INDEX = 5

# Deliberately distinct from the opening and debris generators' UUID namespaces.
UUID_NAMESPACE = uuid.UUID("de2ae4e1-0c11-5e56-a040-9cbf14bbf677")


def resource_id(key: str) -> str:
    return str(uuid.uuid5(
        UUID_NAMESPACE, f"modretro-chromatic:mr-cfe:storm_climb_gust:{key}"
    ))


def _draw_warning(phase: int) -> Image.Image:
    image = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (*TRANSPARENT, 0))
    draw = ImageDraw.Draw(image)
    if phase == 0:
        # A quiet, curled cross-breeze, with a small floating forecast mote.
        draw.line(((5, 12), (8, 10), (11, 10), (13, 11)), fill=OUTLINE, width=3)
        draw.line(((5, 12), (8, 10), (11, 10), (13, 11)), fill=MID, width=1)
        draw.line(((11, 13), (14, 13), (16, 12), (18, 12)), fill=OUTLINE, width=3)
        draw.line(((11, 13), (14, 13), (16, 12), (18, 12)), fill=BRIGHT, width=1)
        draw.point((20, 10), fill=MID)
    elif phase == 1:
        # Same harmless breeze, gently shifted and curling the other way.
        draw.line(((4, 11), (7, 11), (9, 12), (12, 12)), fill=OUTLINE, width=3)
        draw.line(((4, 11), (7, 11), (9, 12), (12, 12)), fill=BRIGHT, width=1)
        draw.line(((9, 14), (12, 14), (15, 13), (18, 13)), fill=OUTLINE, width=3)
        draw.line(((9, 14), (12, 14), (15, 13), (18, 13)), fill=MID, width=1)
        draw.point((20, 11), fill=BRIGHT)
    else:
        raise ValueError(f"unknown warning phase: {phase}")
    return image


def _draw_burst(phase: int) -> Image.Image:
    image = Image.new("RGBA", (FRAME_WIDTH, FRAME_HEIGHT), (*TRANSPARENT, 0))
    draw = ImageDraw.Draw(image)
    if phase == 0:
        # A sharp, forward-driving wind/lightning slash, outlined for contrast.
        draw.polygon(
            ((1, 13), (6, 10), (12, 11), (17, 9), (23, 10), (17, 13),
             (11, 12), (5, 15)),
            fill=OUTLINE,
        )
        draw.polygon(
            ((2, 13), (7, 11), (12, 12), (17, 10), (21, 10), (16, 12),
             (11, 13), (5, 14)),
            fill=MID,
        )
        draw.polygon(((10, 8), (14, 8), (12, 11), (15, 11), (9, 15), (11, 12), (8, 12)),
                     fill=BRIGHT)
    elif phase == 1:
        # The second frame kicks upward: changed silhouette and displaced bolt.
        draw.polygon(
            ((0, 12), (5, 11), (10, 12), (15, 9), (22, 9), (18, 12),
             (13, 13), (8, 14), (3, 14)),
            fill=OUTLINE,
        )
        draw.polygon(
            ((2, 12), (6, 12), (10, 13), (15, 10), (20, 10), (17, 12),
             (12, 13), (8, 13)),
            fill=MID,
        )
        draw.polygon(((14, 8), (18, 8), (15, 10), (18, 10), (11, 15), (13, 11), (10, 12)),
                     fill=BRIGHT)
    else:
        raise ValueError(f"unknown burst phase: {phase}")
    return image


def make_sheet() -> Image.Image:
    """Return four fixed animation frames packed left-to-right."""
    frames = [
        _draw_warning(0), _draw_warning(1),
        _draw_burst(0), _draw_burst(1),
    ]
    sheet = Image.new("RGBA", (FRAME_WIDTH * len(frames), FRAME_HEIGHT), (*TRANSPARENT, 0))
    for index, frame in enumerate(frames):
        sheet.paste(frame, (index * FRAME_WIDTH, 0))
    return sheet


def _tile_signature(image: Image.Image, frame_index: int, object_index: int) -> bytes:
    x = frame_index * FRAME_WIDTH + object_index * OBJECT_WIDTH
    return image.crop((x, 0, x + OBJECT_WIDTH, FRAME_HEIGHT)).tobytes()


def sprite_resource(checksum: str, image: Image.Image) -> dict:
    states = []
    for state_index, (name, first_frame) in enumerate((("Warning", 0), ("Burst", 2))):
        animations = []
        for slot in range(ANIMATION_SLOTS):
            animation_key = f"state:{name}:slot:{slot}"
            frames = []
            frame_indices = range(first_frame, first_frame + 2) if slot == 0 else ()
            for phase, sheet_frame in enumerate(frame_indices):
                tiles = []
                for object_index in range(OBJECTS_PER_FRAME):
                    tiles.append({
                        "id": resource_id(
                            f"tile:{name}:slot:{slot}:frame:{phase}:object:{object_index}"
                        ),
                        "x": object_index * OBJECT_WIDTH,
                        "y": 0,
                        "sliceX": sheet_frame * FRAME_WIDTH + object_index * OBJECT_WIDTH,
                        "sliceY": 0,
                        "flipX": False,
                        "flipY": False,
                        "palette": 0,
                        "paletteIndex": PALETTE_INDEX,
                        "objPalette": "OBP0",
                        "priority": False,
                    })
                frames.append({
                    "id": resource_id(f"frame:{name}:slot:{slot}:phase:{phase}"),
                    "tiles": tiles,
                })
            if not frames:
                frames.append({
                    "id": resource_id(f"frame:{name}:slot:{slot}:empty"),
                    "tiles": [],
                })
            animations.append({
                "id": resource_id(animation_key),
                "frames": frames,
            })
        states.append({
            "id": resource_id(f"state:{name}"),
            "name": name,
            "animationType": "fixed",
            "flipLeft": False,
            "animations": animations,
        })

    unique_tiles = {
        _tile_signature(image, frame, obj)
        for frame in range(image.width // FRAME_WIDTH)
        for obj in range(OBJECTS_PER_FRAME)
    }
    return {
        "_resourceType": "sprite",
        "id": resource_id("sprite:climb-gust"),
        "name": "climb_gust",
        "symbol": "sprite_climb_gust",
        "filename": OUTPUT.name,
        "width": image.width,
        "height": image.height,
        "checksum": checksum,
        "numTiles": len(unique_tiles),
        "canvasOriginX": 0,
        "canvasOriginY": 0,
        "canvasWidth": FRAME_WIDTH,
        "canvasHeight": FRAME_HEIGHT,
        "boundsX": 0,
        "boundsY": 0,
        "boundsWidth": FRAME_WIDTH,
        "boundsHeight": 8,
        "animSpeed": 8,
        "spriteMode": "8x16",
        "states": states,
    }


def validate(image: Image.Image, resource: dict) -> None:
    if image.size != (FRAME_WIDTH * 4, FRAME_HEIGHT):
        raise AssertionError("gust sheet must contain four 24x16 frames")
    if set(image.convert("RGB").get_flattened_data()) - PROXY_COLORS:
        raise AssertionError("gust sheet contains colors outside the strict sprite proxy palette")
    if image.mode == "RGBA" and any(
        ((r, g, b) == TRANSPARENT) != (a == 0)
        for r, g, b, a in image.get_flattened_data()
    ):
        raise AssertionError("gust transparency must be alpha zero on keyed-green pixels only")
    if resource["width"] != image.width or resource["height"] != image.height:
        raise AssertionError("metadata dimensions disagree with PNG")
    if resource["spriteMode"] != "8x16" or resource["canvasWidth"] != FRAME_WIDTH:
        raise AssertionError("gust metadata must use the 24x16, 8x16-object frame contract")
    if (resource["boundsX"], resource["boundsY"], resource["boundsWidth"],
            resource["boundsHeight"]) != (0, 0, 24, 8):
        raise AssertionError("gust collision bounds must be x0/y0/24x8")
    if resource["numTiles"] != len({
        _tile_signature(image, frame, obj)
        for frame in range(4) for obj in range(OBJECTS_PER_FRAME)
    }):
        raise AssertionError("numTiles must equal unique referenced 8x16 tile count")

    state_frames: dict[str, list[Image.Image]] = {}
    for state_index, state in enumerate(resource["states"]):
        if len(state["animations"]) != ANIMATION_SLOTS:
            raise AssertionError(f"{state['name']} must expose all eight native animation slots")
        animation = state["animations"][0]
        if len(animation["frames"]) != 2:
            raise AssertionError(f"{state['name']} must have two fixed animation frames")
        frames = []
        for phase, frame in enumerate(animation["frames"]):
            if len(frame["tiles"]) != OBJECTS_PER_FRAME:
                raise AssertionError("each gust frame must use no more than three OAM objects")
            for object_index, tile in enumerate(frame["tiles"]):
                if tile["paletteIndex"] != PALETTE_INDEX:
                    raise AssertionError("gust tiles must use sprite palette slot 5")
                if tile["sliceX"] % FRAME_WIDTH != object_index * OBJECT_WIDTH:
                    raise AssertionError("tile source slices must align to 8px object columns")
            sheet_frame = state_index * 2 + phase
            frame_image = image.crop((sheet_frame * FRAME_WIDTH, 0,
                                      (sheet_frame + 1) * FRAME_WIDTH, FRAME_HEIGHT))
            if any(frame_image.getpixel((x, y))[:3] != TRANSPARENT
                   for y in range(8) for x in range(FRAME_WIDTH)):
                raise AssertionError("upper half of every frame must be transparent")
            opaque = [
                (x, y) for y in range(FRAME_HEIGHT) for x in range(FRAME_WIDTH)
                if frame_image.getpixel((x, y))[:3] != TRANSPARENT
            ]
            if not opaque:
                raise AssertionError("gust animation frame cannot be empty")
            if any(not (0 <= x < 24 and 8 <= y < 16) for x, y in opaque):
                raise AssertionError("gust pixels spill outside the 24x8 actor-aligned bounds")
            frames.append(frame_image)
        if frames[0].tobytes() == frames[1].tobytes():
            raise AssertionError(f"{state['name']} animation frames must be visually distinct")
        for empty_animation in state["animations"][1:]:
            if any(frame["tiles"] for frame in empty_animation["frames"]):
                raise AssertionError("non-default animation slots must remain empty")
        state_frames[state["name"]] = frames

    if [state["name"] for state in resource["states"]] != ["Warning", "Burst"]:
        raise AssertionError("gust states must be named Warning and Burst in order")
    warning_area = sum(
        pixel[:3] != TRANSPARENT
        for frame in state_frames["Warning"]
        for pixel in frame.get_flattened_data()
    )
    burst_area = sum(
        pixel[:3] != TRANSPARENT
        for frame in state_frames["Burst"]
        for pixel in frame.get_flattened_data()
    )
    if not (0 < warning_area < burst_area):
        raise AssertionError("Warning must have a smaller raw opaque pixel area than Burst")


def _write_owned(image_bytes: bytes, resource: dict) -> None:
    """Refuse to replace a pre-existing asset not owned by this generator."""
    expected_id = resource_id("sprite:climb-gust")
    if METADATA.exists():
        try:
            current = json.loads(METADATA.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise FileExistsError(f"refusing to overwrite unreadable sidecar: {METADATA}") from error
        if current.get("_resourceType") != "sprite" or current.get("id") != expected_id:
            raise FileExistsError(f"refusing to overwrite an unowned resource: {METADATA}")
    elif OUTPUT.exists():
        raise FileExistsError(f"refusing to overwrite PNG without its owned sidecar: {OUTPUT}")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(image_bytes)
    contents = json.dumps(resource, indent=2) + "\n"
    METADATA.write_text(contents, encoding="utf-8")


def main() -> None:
    image = make_sheet()
    validate(image, sprite_resource("", image))
    # RGBA PNG output is deterministic for a fixed Pillow version and options.
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    image_bytes = buffer.getvalue()
    checksum = hashlib.sha1(image_bytes).hexdigest()
    resource = sprite_resource(checksum, image)
    validate(image, resource)
    _write_owned(image_bytes, resource)
    print(f"generated climb_gust: Warning + Burst, {resource['numTiles']} unique tiles, 24x8 bounds")


if __name__ == "__main__":
    main()
