"""Generate the two developer LAB scenes: a hazard gallery and a movement room.

Run with the managed Python: ``tools/make_project.py lab --verify``. Both scenes
are tagged ``lab`` in tools/scenes.py: developer test rooms that no game scene
can reach (no EVENT_SWITCH_SCENE anywhere in them) and that the release copy
leaves out.

Layouts are tile data below, 40x18 PLATFORM rooms. Solid floor starts at row
15, so the hero stands on row 14. Cracked boards and hidden cables are placed by
hazards.py; the live arc and timed gust reuse rosa's and climb's timings. The
whipping live wire uses hazards.py's whip scripts (the same ones Wind Ridge
runs), under its own lab palette. Event and actor IDs come from make_climb_scene's
helpers under ``lab_*`` keys, so they never collide with storm_climb's or Wind
Ridge's. A separately owned 40x18 crop of Pine Hollow's art keeps these rooms
independent of the wider gameplay map (the reference art is not collision-aligned).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

TOOLS_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TOOLS_DIR.parent
SCENES_DIR = PROJECT_DIR / "project" / "scenes"
CLIMB_SCENE = SCENES_DIR / "storm_climb" / "scene.gbsres"
DEATH_SOUND = "assets/sounds/death.wav.gbsres"
GUST_SPRITE = "assets/sprites/climb_gust.png.gbsres"
WHIP_SPRITE = "assets/sprites/whip_wire.png.gbsres"
WHIP_PALETTE_PATH = "project/palettes/lab_sprite_whip.gbsres"
# Same hardware colours and OBJ slot as Wind Ridge's whip (ridge.py contract).
WHIP_SPRITE_HARDWARE = ["000000", "FFF4A8", "8A97A6", "1B2028"]  # spark, sheath, dark
WHIP_SPRITE_PALETTE_SLOT = 6
WHIP_CANVAS_TILES = (2, 4)           # 16x32 px: two tiles wide, four tall

WIDTH, HEIGHT = 40, 18
GROUND_ROW = 15          # first solid floor row; the hero stands on row 14
START = (2, 14)

GALLERY = "lab_hazard_gallery"
ROOM = "lab_movement_room"
SCENE_INDEX = {GALLERY: 10, ROOM: 11}   # unused editor-order slots (0-9 are taken)

sys.path.insert(0, str(TOOLS_DIR))
try:
    import climb  # noqa: E402  (collision bytes, line palette slot)
    import hazards  # noqa: E402  (cracked board / hidden cable placement, timings, VAR_ON_BOARD)
    from level import decode_rle  # noqa: E402
    import make_climb_scene as shared  # noqa: E402  (generic GB Studio helpers only)
    import opening  # noqa: E402  (worker sprite, shared background palettes)
    import shock  # noqa: E402  (electrocution beat before the respawn)
    import rosa  # noqa: E402  (live arc sprite and palette)
    import scenes  # noqa: E402  (registry: ids, names, editor positions)
except ModuleNotFoundError as error:
    if error.name in {"climb", "hazards", "level", "make_climb_scene", "opening", "rosa", "scenes"}:
        raise SystemExit(f"cannot generate lab scenes: tools/{error.name}.py is missing") from error
    raise

COL_EMPTY = climb.COL_EMPTY
COL_TOP = climb.COL_TOP      # one-way: land from above, drop through with Down+A
COL_SOLID = climb.COL_SOLID
BACKGROUND_NAME = "lab_pine_reference"
BACKGROUND_ID = hazards.resource_id("background:" + BACKGROUND_NAME)
# Wind Ridge's whip timings: the climb gust's warning, burst and rest.
WHIP_SWAY_FRAMES = climb.GUST_WARNING_FRAMES
WHIP_SWING_FRAMES = climb.GUST_ACTIVE_FRAMES
WHIP_HANG_FRAMES = climb.GUST_REST_FRAMES

# ---------------------------------------------------------------------------
# Layouts
#
# shelves: (x0, x1, row0, row1, collision) inclusive. Shelves are one tile
# thick; every rise is three tiles (one A tap), like storm_climb's shelves.
# pits: (x0, x1) floor gaps, cut through the two floor rows above the bottom
# row, which stays solid so a fall lands in the gap instead of off the map.
# ---------------------------------------------------------------------------
ROOMS: dict[str, dict[str, Any]] = {
    GALLERY: {
        "entry": "LAB: hazards",
        "shelves": [(6, 8, 12, 12, COL_SOLID)],          # cracked board shelf (hazards.BOARDS)
        "pits": [],
        "arc_lane": (13, 21, 22),                       # live arc, chest row 13 on the floor
        "gust_lane": (13, 28, 30),                      # timed gust, chest row 13 on the floor
        "whip_lane": (13, 35, 36),                      # whipping wire, 7 tiles past the gust
        "whip_delay": 60,                               # frames before its first sway
    },
    ROOM: {
        "entry": "LAB: movement",
        "shelves": [
            (8, 10, 12, 12, COL_SOLID),                  # first short-A-tap rise
            (13, 15, 9, 9, COL_SOLID),                   # second rise, two tiles across a gap
            (18, 20, 12, 12, COL_TOP),                   # drop-through shelf
        ],
        # Gap ladder: widths 1, 2, 3, 4 with landings between them.
        "pits": [(22, 22), (25, 26), (29, 31), (34, 37)],
        "arc_lane": None,
        "gust_lane": None,
        "whip_lane": None,
        "whip_delay": 0,
    },
}


def collision_grid(folder: str) -> list[list[int]]:
    room = ROOMS[folder]
    grid = [[COL_EMPTY] * WIDTH for _ in range(HEIGHT)]
    for row in range(GROUND_ROW, HEIGHT):
        for x in range(WIDTH):
            grid[row][x] = COL_SOLID
    for row in range(2, GROUND_ROW):                     # side walls, below the HUD rows
        grid[row][0] = COL_SOLID
        grid[row][WIDTH - 1] = COL_SOLID
    for x0, x1, row0, row1, value in room["shelves"]:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = value
    for x0, x1 in room["pits"]:
        for row in range(GROUND_ROW, HEIGHT - 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_EMPTY
    return grid


def hazard_lanes(folder: str) -> list[tuple[int, int, int]]:
    room = ROOMS[folder]
    lanes = [lane for lane in (room["arc_lane"], room["gust_lane"], room["whip_lane"]) if lane is not None]
    return lanes + [(row, x0, x1) for row, x0, x1 in hazards.HIDDEN_CABLES[folder]]


def check_layout(folder: str) -> None:
    """Fail before writing if a layout cannot be played as described."""
    grid = collision_grid(folder)
    assert (WIDTH, HEIGHT) == (40, 18), "lab rooms use a fixed 40x18 reference crop"
    assert grid[START[1] + 1][START[0]] == COL_SOLID and grid[START[1]][START[0]] == COL_EMPTY
    for row, x0, x1 in hazards.BOARDS[folder]:
        assert all(grid[row][x] != COL_EMPTY and grid[row - 1][x] == COL_EMPTY
                   for x in range(x0, x1 + 1)), f"board {(row, x0, x1)} must sit on a shelf"
    for row, x0, x1 in hazard_lanes(folder):
        # Chest row L: the hero's feet are L + 1, the surface under them L + 2.
        assert all(grid[r][x] == COL_EMPTY for r in (row - 1, row, row + 1) for x in range(x0, x1 + 1)), (
            f"lane {(row, x0, x1)} must be clear air for a standing hero")
        assert all(grid[row + 2][x] != COL_EMPTY for x in range(x0, x1 + 1)), (
            f"lane {(row, x0, x1)} must stand on a surface two rows below its chest row")
    for x0, x1 in ROOMS[folder]["pits"]:
        assert 1 <= x1 - x0 + 1 <= 4, "gap ladder widths are 1 to 4 tiles"


# ---------------------------------------------------------------------------
# Events and actors (lab-scoped keys; event builders come from make_climb_scene)
# ---------------------------------------------------------------------------
def live_arc_actor(folder: str, index: int, lane: tuple[int, int, int], sprite_id: str) -> dict[str, Any]:
    """Visible live arc: warning sparks (safe), arc (group 1 hits), dark wire (safe)."""
    row, x0, x1 = lane
    if x1 - x0 + 1 != 2:
        raise ValueError("the live arc sprite is exactly two tiles wide")
    key = f"{folder}:live-arc"

    def own(command: str, suffix: str, **args: Any) -> dict[str, Any]:
        return shared.event(command, {"actorId": "$self$", **args}, f"{key}:{suffix}")

    actor = shared.actor_resource(
        index=index,
        symbol=f"{folder}_live_arc_{index:02d}",
        name="Live Arc (Lab)",
        x=x0,
        y=row,
        sprite_id=sprite_id,
        key=key,
        start_script=[own("EVENT_ACTOR_COLLISIONS_DISABLE", "initial-safe")],
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["animSpeed"] = 8
    actor["updateScript"] = [
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "warning-safe"),
        own("EVENT_ACTOR_SET_STATE", "warning-state", spriteStateId="Warning", loopAnim=True),
        own("EVENT_ACTOR_SHOW", "warning-visible"),
        shared.wait_event(rosa.ARC_WARNING_FRAMES, f"{key}:warning-time"),
        own("EVENT_ACTOR_SET_STATE", "arc-state", spriteStateId="Arc", loopAnim=True),
        own("EVENT_ACTOR_COLLISIONS_ENABLE", "arc-active"),
        shared.wait_event(rosa.ARC_ACTIVE_FRAMES, f"{key}:arc-time"),
        own("EVENT_ACTOR_COLLISIONS_DISABLE", "rest-safe"),
        own("EVENT_ACTOR_HIDE", "rest-hidden"),
        shared.wait_event(rosa.ARC_REST_FRAMES, f"{key}:rest-time"),
    ]
    return actor


def whip_actor(folder: str, index: int, lane: tuple[int, int, int], start_delay: int,
               sprite_id: str) -> dict[str, Any]:
    """Whipping live wire: hangs sparking, sways (safe warning), whips (group-1 hits), hangs.

    Always visible. Placed with its 16x32 canvas bottom on the row above the
    lane's surface, exactly as Wind Ridge places its whips.
    """
    row, x0, x1 = lane
    if x1 - x0 + 1 != WHIP_CANVAS_TILES[0]:
        raise ValueError("the whip lane is the sprite's width")
    key = f"{folder}:whip"
    actor = shared.actor_resource(
        index=index,
        symbol=f"{folder}_whip_{index:02d}",
        name="Whipping Live Wire (Lab)",
        x=x0,
        y=row + 1,
        sprite_id=sprite_id,
        key=key,
        start_script=hazards.whip_start_script(key, shared.event),
    )
    actor["collisionGroup"] = "1"
    actor["animate"] = True
    actor["animSpeed"] = 8
    actor["updateScript"] = hazards.whip_update_script(
        key, start_delay, WHIP_SWAY_FRAMES, WHIP_SWING_FRAMES, WHIP_HANG_FRAMES,
        shared.event, shared.wait_event, shared.branch_event)
    return actor


def hazard_actors(folder: str, gust_sprite_id: str, whip_sprite_id: str) -> list[dict[str, Any]]:
    """Boards and hidden cables (shared, scene-keyed), then the arc, the gust and the whip."""
    actors = shared.hazard_actors(0, folder)
    room = ROOMS[folder]
    if room["arc_lane"] is not None:
        actors.append(live_arc_actor(folder, len(actors), room["arc_lane"], rosa.ARC_SPRITE_ID))
    if room["gust_lane"] is not None:
        actors.append(shared.timed_gust_actor(
            len(actors), room["gust_lane"], gust_sprite_id,
            key_prefix=f"{folder}:", symbol_prefix=f"{folder}_"))
    if room["whip_lane"] is not None:
        actors.append(whip_actor(folder, len(actors), room["whip_lane"], room["whip_delay"], whip_sprite_id))
    return actors


def whip_palette() -> dict[str, Any]:
    """The lab's own whip palette (hazards namespace, lab-only file)."""
    colors = shared.editor_sprite_colors(WHIP_SPRITE_HARDWARE)
    title = "Lab sprite whip"
    return {
        "_resourceType": "palette",
        "id": hazards.resource_id("palette:sprite:whip"),
        "name": title,
        "colors": colors,
        "defaultName": title,
        "defaultColors": colors,
    }


def scene_script(folder: str) -> list[dict[str, Any]]:
    key = f"{folder}:init"
    return [
        shared.event("EVENT_PLAYER_SET_SPRITE",
                     {"spriteSheetId": opening.resource_id("sprite:opening_worker24")}, f"{key}:sprite"),
        shared.event("EVENT_ACTOR_SET_DIRECTION",
                     {"actorId": "player", "direction": {"type": "direction", "value": "right"}},
                     f"{key}:direction"),
        shared.set_value(hazards.VAR_ON_BOARD, 0, f"{key}:on-board"),
        # The overlay cutoff survives scene switches; lift it so the sign shows.
        shared.cutoff_event(150, f"{key}:cutoff"),
        shared.text_event(shared.short_lines(ROOMS[folder]["entry"]), f"{key}:sign"),
    ]


def respawn_events(folder: str, death_sound_id: str) -> list[dict[str, Any]]:
    """Group-1 hits (boards, cables, arcs, gusts) send the hero back to the room start."""
    key = f"{folder}:respawn"
    return [
        *shock.shock_events(key),
        # The respawn teleports the hero without a leave event: forget the board.
        shared.set_value(hazards.VAR_ON_BOARD, 0, f"{key}:clear-board"),
        shared.set_position(*START, f"{key}:start"),
    ]


def background_palette_ids() -> list[str]:
    """Opening's background set with the cable route left dead (as Pine Hollow does)."""
    background = [opening.resource_id(f"palette:bg:{name}") for name, _ in opening.BG_PALETTES] + ["default-ui"]
    if len(background) != 8 or background[7] != "default-ui":
        raise ValueError("lab background palettes must preserve the UI in slot 7")
    background[climb.LINE_BG_SLOT] = shared.metal_palette_id(False)
    return background


def build_scene(folder: str, death_sound_id: str) -> dict[str, Any]:
    entry = scenes.REGISTRY[folder]
    template = shared.load_json(CLIMB_SCENE)
    sprite_palette_ids = template.get("spritePaletteIds")
    if not isinstance(sprite_palette_ids, list) or len(sprite_palette_ids) != 8:
        raise ValueError("lab scenes need the climb scene's eight sprite palette slots")
    sprite_palette_ids = list(sprite_palette_ids)
    sprite_palette_ids[0] = opening.resource_id("palette:sprite:worker")
    if hazards.BOARDS[folder]:
        sprite_palette_ids[hazards.BOARD_SPRITE_PALETTE_SLOT] = hazards.BOARD_PALETTE_ID
    if hazards.HIDDEN_CABLES[folder] or ROOMS[folder]["arc_lane"] is not None:
        sprite_palette_ids[rosa.ARC_SPRITE_PALETTE_SLOT] = rosa.resource_id("palette:sprite:arc")
    if ROOMS[folder]["whip_lane"] is not None:
        sprite_palette_ids[WHIP_SPRITE_PALETTE_SLOT] = whip_palette()["id"]
    editor_x, editor_y = scenes.editor_position(folder)
    scene = dict(template)
    scene.update({
        "id": entry["id"],
        "_index": SCENE_INDEX[folder],
        "name": entry["name"],
        "type": "PLATFORM",
        "width": WIDTH,
        "height": HEIGHT,
        "x": editor_x,
        "y": editor_y,
        "collisions": shared.collision_rle(collision_grid(folder), WIDTH, HEIGHT),
        "symbol": f"scene_{folder}",
        "backgroundId": BACKGROUND_ID,
        "paletteIds": background_palette_ids(),
        "spritePaletteIds": sprite_palette_ids,
        "script": scene_script(folder),
        "playerHit1Script": respawn_events(folder, death_sound_id),
        "playerHit2Script": [],
        "playerHit3Script": [],
    })
    return scene


def build_triggers(folder: str) -> list[dict[str, Any]]:
    return shared.hazard_triggers(folder)


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def write_reference_background() -> None:
    """Crop the compiler proxy and its palette map together, without changing Pine Hollow."""
    from PIL import Image

    source = PROJECT_DIR / "assets/backgrounds/pine_hollow.png"
    metadata = shared.load_json(Path(str(source) + ".gbsres"))
    source_width, source_height = metadata["width"], metadata["height"]
    if source_width < WIDTH or source_height < HEIGHT:
        raise ValueError("Pine Hollow reference is smaller than the lab rooms")
    flat = decode_rle(metadata["tileColors"])
    if len(flat) != source_width * source_height:
        raise ValueError("Pine Hollow reference palette map has the wrong size")
    slots = [flat[row * source_width:row * source_width + WIDTH] for row in range(HEIGHT)]
    target = source.with_name(BACKGROUND_NAME + ".png")
    with Image.open(source) as image:
        image.crop((0, 0, WIDTH * 8, HEIGHT * 8)).save(target)
    metadata.update({
        "id": BACKGROUND_ID, "name": BACKGROUND_NAME, "symbol": "bg_" + BACKGROUND_NAME,
        "filename": target.name, "width": WIDTH, "height": HEIGHT,
        "imageWidth": WIDTH * 8, "imageHeight": HEIGHT * 8,
        "tileColors": shared.collision_rle(slots, WIDTH, HEIGHT),
    })
    shared.write_json(Path(str(target) + ".gbsres"), metadata)


def warn_if_missing_asset(resource_id: str, folder: str, label: str) -> None:
    """Other workers produce these art files; this generator only references their IDs."""
    for path in sorted((PROJECT_DIR / "assets" / folder).glob("*.gbsres")):
        try:
            if shared.load_json(path).get("id") == resource_id:
                return
        except (OSError, ValueError):
            continue
    print(f"warning: no {label} sidecar with id {resource_id} under assets/{folder}/ yet")


def clear_stale(scene_dir: Path) -> None:
    """Remove every actor and trigger file; the generator owns the whole lab folder."""
    for sub in ("actors", "triggers"):
        for path in sorted((scene_dir / sub).glob("*.gbsres")):
            path.unlink()
            print(f"removed stale {path.relative_to(PROJECT_DIR)}")


def main() -> None:
    assert set(ROOMS) == set(scenes.by_tag(scenes.LAB)), "lab rooms must match the lab registry tag"
    death_sound_id = shared.sidecar_id(DEATH_SOUND, "sound")
    gust_sprite_id = shared.sidecar_id(GUST_SPRITE, "sprite")
    whip_sprite_id = shared.sidecar_id(WHIP_SPRITE, "sprite")
    write_reference_background()
    warn_if_missing_asset(hazards.BOARD_SPRITE_ID, "sprites", "cracked board sprite")
    warn_if_missing_asset(rosa.ARC_SPRITE_ID, "sprites", "live arc sprite")
    for folder in ROOMS:
        check_layout(folder)

    shared.write_variables()
    for relative_path, palette in [*shared.hazard_palettes(), (WHIP_PALETTE_PATH, whip_palette())]:
        shared.write_json(PROJECT_DIR / relative_path, palette)
    for folder in ROOMS:
        scene_dir = SCENES_DIR / folder
        actors = hazard_actors(folder, gust_sprite_id, whip_sprite_id)
        triggers = build_triggers(folder)
        if len(actors) > 20:
            raise ValueError(f"{folder}: {len(actors)} actors exceeds the 20-actor limit")
        scene = build_scene(folder, death_sound_id)
        clear_stale(scene_dir)
        shared.write_json(scene_dir / "scene.gbsres", scene)
        for actor in actors:
            shared.write_json(scene_dir / "actors" / f"{actor['symbol']}.gbsres", actor)
        for trigger in triggers:
            shared.write_json(scene_dir / "triggers" / f"{trigger['symbol']}.gbsres", trigger)
        print(f"generated {folder}: {WIDTH}x{HEIGHT} PLATFORM, {len(actors)} actors, "
              f"{len(triggers)} triggers, no scene switches")


if __name__ == "__main__":
    main()
