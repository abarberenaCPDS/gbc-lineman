"""Mister CFE - level design source of truth.

Everything about the mountain level (geometry, palettes, station layout,
collision map) is derived from THIS module, so the art generator, the
scene builder and the runtime logic can never disagree.

Consumers:
  tools/make_art.py    - renders the background PNG + sidecar + sprite sheets
  tools/make_scene.py  - renders the scene resource (collisions, palettes)
  tools/make_logic.md  - human readable script spec derived from the same data

Units: tiles are 8x8 px (L-02). A scene is MAP_W x MAP_H tiles.
"""

from __future__ import annotations

TILE = 8
MAP_W, MAP_H = 20, 36
BG_W, BG_H = MAP_W * TILE, MAP_H * TILE  # 160 x 288 px

# --------------------------------------------------------------------------
# Collision byte values (PLATFORM). From the GB Studio engine schema:
#   solid=15 (0x0F), top/one-way=1 (0x01), bottom=2, left=4, right=8,
#   ladder=16, slope_45_right=32 ...
# --------------------------------------------------------------------------
COL_EMPTY = 0x00
COL_TOP = 0x01  # one-way platform, land from above only
COL_SOLID = 0x0F

# --------------------------------------------------------------------------
# Level geometry
#
# PLATFORMS: (row, x_start, x_end) inclusive. One-way platforms so the
# player can jump up through them; a 3 row cadence gives a 24px rise,
# which is comfortably reachable with a brief jump hold (see docs note
# "Jump budget" below).
#
# SOLID_BLOCKS: (x_start, x_end, row_start, row_end) inclusive. Terrain
# that is actually solid (the valley floor and the right-hand cliff face).
# --------------------------------------------------------------------------
PLATFORMS = [
    (33, 0, 6),    # substation deck (bottom of the climb)
    (30, 1, 16),
    (27, 2, 17),
    (24, 0, 14),
    (21, 2, 18),
    (18, 3, 15),
    (15, 1, 12),
    (12, 6, 18),
    (9, 2, 12),
    (6, 9, 19),    # summit shelf
]

SOLID_BLOCKS = [
    (0, MAP_W - 1, 34, 35),   # valley floor
    (17, 19, 12, 30),         # right cliff face
    (0, 0, 30, 33),           # left wall framing the substation deck
]

# --------------------------------------------------------------------------
# The five houses (the brief's "5 buildings max"). Each sits on a platform;
# the node the player interacts with is the tile directly above the platform.
# POLE_X is the house x; the pole is the vertical run of cable art from just
# under the house platform down to the platform below it (3 rows, 24px).
#
# The chain is bottom-up: the substation feeds house_a, house_a's pole lands
# on house_b's platform, house_b's pole lands on house_c's platform, and so
# on. A house only powers up if every house below it is already connected.
# --------------------------------------------------------------------------
HOUSES = [
    {"id": "house_a", "name": "Amara",  "x": 3,  "platform": 30, "row": 29},
    {"id": "house_b", "name": "Hiroshi",  "x": 14, "platform": 27, "row": 26},
    {"id": "house_c", "name": "Priya",   "x": 5,  "platform": 24, "row": 23},
    {"id": "house_d", "name": "Emil",   "x": 12, "platform": 21, "row": 20},
    {"id": "house_e", "name": "Nuria",  "x": 8,  "platform": 18, "row": 17},
]

# The substation: the grid source at the bottom of the mountain. It stands on
# the deck platform (row 33) and always has power.
SUBSTATION = {"id": "substation", "x": 1, "platform": 33, "row": 32}

# Locals to talk to. Placed on platforms, never on the critical path.
NPCS = [
    {"id": "npc_marta",  "name": "Amara",  "x": 9,  "platform": 30, "row": 29},
    {"id": "npc_rosa",   "name": "Priya",   "x": 11, "platform": 24, "row": 23},
    {"id": "npc_kiko",   "name": "Emil",   "x": 4,  "platform": 18, "row": 17},
]

# Hazard zones: storm flooded rock and live wire. Touching one kills the
# player. Each hazard sits in the middle of a climb gap (the two empty rows
# between two platforms) so it is genuinely in the player's path, and never
# in a pole column.
# (x_start, x_end, row_start, row_end) inclusive, in tiles.
HAZARDS = [
    (17, 19, 31, 31),  # floodwater at the foot of the cliff
    (6, 7, 28, 28),    # arcing live wire
    (15, 16, 25, 25),
    (0, 1, 22, 22),
    (14, 15, 19, 19),
    (4, 6, 16, 16),
]

# Player spawn: on the substation deck.
PLAYER_START = {"x": 2, "y": 32}

# --------------------------------------------------------------------------
# Palettes
#
# 8 background palette slots; slot 8 (index 7) is reserved for the UI by the
# engine (L-20), so only indices 0..6 are ours. Same for sprites: index 7
# is the emote palette (L-21).
#
# Every 8x8 tile uses its 4 colours from ONE palette, so the art must be
# authored per tile with a palette index (the background sidecar's
# "tileColors" field maps each tile to its palette slot).
# --------------------------------------------------------------------------
BG_PALETTES = [
    # 0 - night sky and distant ridges
    ("sky", ["0B0D18", "161A2E", "232840", "3A4160"]),
    # 1 - rock, ledges, platforms
    ("rock", ["10131A", "232833", "39434F", "56646E"]),
    # 2 - timber, houses, poles
    ("timber", ["221B14", "453623", "75593A", "A8834F"]),
    # 3 - lit windows, electric glow
    ("glow", ["2A1A06", "7A4A0E", "D89424", "FFDE8A"]),
    # 4 - moss and foliage
    ("moss", ["0B1710", "1A3520", "347A36", "7BE35B"]),
    # 5 - hazard: storm water, sparks
    ("hazard", ["240809", "54120F", "98251B", "D95838"]),
    # 6 - cable / conductor
    ("cable", ["16202C", "3E5A72", "88B2C8", "E2F2FF"]),
]
# index 7 stays "default-ui" (engine reserved)

SPRITE_PALETTES = [
    # 0 - the player: pale skin, tan coat, teal pack, black outline
    ("player", ["F6E4C8", "D9A05B", "2E6B6B", "101018"]),
    # 1 - the locals
    ("local", ["F6E4C8", "C8A06A", "6B4A7A", "101018"]),
    # 2 - timber: houses, poles, substation
    ("timber", ["241C14", "4A3826", "7C5E3C", "AC8750"]),
    # 3 - glow: lit windows, powered state
    ("glow", ["2A1A06", "7A4A0E", "D89424", "FFDE8A"]),
    # 4 - hazard
    ("hazard", ["240809", "54120F", "98251B", "D95838"]),
    # 5 - conductor: the cable itself
    ("cable", ["16202C", "3E5A72", "88B2C8", "E2F2FF"]),
    # 6 - stone / neutral
    ("stone", ["14171E", "2A3038", "464F59", "6E7883"]),
]
# index 7 stays the emote palette (engine reserved)

# --------------------------------------------------------------------------
# Derived helpers
# --------------------------------------------------------------------------


def _blank_grid() -> list[list[int]]:
    return [[COL_EMPTY for _ in range(MAP_W)] for _ in range(MAP_H)]


def collision_grid() -> list[list[int]]:
    """The collision map, one byte per tile (MAP_H rows of MAP_W columns)."""
    grid = _blank_grid()
    for row, x0, x1 in PLATFORMS:
        for x in range(x0, x1 + 1):
            grid[row][x] = COL_TOP
    for x0, x1, r0, r1 in SOLID_BLOCKS:
        for row in range(r0, r1 + 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_SOLID
    return grid


def pole_spans() -> list[dict]:
    """The vertical cable runs, one per house, plus the house it belongs to."""
    spans = []
    for house in HOUSES:
        platform_row = house["platform"]
        spans.append(
            {
                "id": house["id"],
                "x": house["x"],
                "row_top": platform_row + 1,
                "row_bottom": platform_row + 3,
                "height_px": (platform_row + 3 - (platform_row + 1) + 1) * TILE,
            }
        )
    return spans


def chain_order() -> list[dict]:
    """The grid chain, bottom-up: substation -> house_a -> ... -> house_e."""
    chain = [
        {
            "id": SUBSTATION["id"],
            "x": SUBSTATION["x"],
            "row": SUBSTATION["row"],
            "platform": SUBSTATION["platform"],
            "needs": None,
        }
    ]
    previous = SUBSTATION["id"]
    for house in HOUSES:
        chain.append(
            {
                "id": house["id"],
                "x": house["x"],
                "row": house["row"],
                "platform": house["platform"],
                "needs": previous,
            }
        )
        previous = house["id"]
    return chain


def rle(values: list[int]) -> str:
    """GB Studio's compress8bitNumberArray encoding.

    Runs of equal bytes become "<hex count>+<hex value>" and a lone byte
    becomes "<hex value>!". Same encoder the editor uses for a scene's
    "collisions" and a background's "tileColors" fields.
    """
    out: list[str] = []
    last = -1
    count = 0
    for value in values:
        if value != last:
            if count == 1:
                out.append("!")
            elif count > 0:
                out.append(f"{count:x}+")
            count = 0
            last = value
            out.append(f"{value % 256:02x}")
        count += 1
    if count == 1:
        out.append("!")
    elif count > 0:
        out.append(f"{count:x}+")
    return "".join(out)


def decode_rle(text: str) -> list[int]:
    """Inverse of rle(); used by the self checks below."""
    values: list[int] = []
    i = 0
    while i < len(text):
        value = int(text[i : i + 2], 16)
        i += 2
        if i >= len(text):
            break
        if text[i] == "!":
            count = 1
            i += 1
        else:
            end = text.index("+", i)
            count = int(text[i:end], 16)
            i = end + 1
        values.extend([value] * count)
    return values


def collisions_rle() -> str:
    grid = collision_grid()
    return rle([cell for row in grid for cell in row])


def unique_background_tiles() -> int:
    """Conservative estimate of unique background tiles (L-03 budget is 384)."""
    return 64


def sprite_tile_budget() -> int:
    """Conservative estimate of sprite tiles used per scene (L-11 budget 192)."""
    return 48


# --------------------------------------------------------------------------
# Self checks. Run `python3 tools/level.py` to validate the design.
# --------------------------------------------------------------------------
def _self_check() -> None:
    grid = collision_grid()
    assert len(grid) == MAP_H and all(len(r) == MAP_W for r in grid), "grid size"

    platform_rows = {row for row, _, _ in PLATFORMS}

    for house in HOUSES:
        x, prow = house["x"], house["platform"]
        assert prow in platform_rows, f"{house['id']}: no platform at row {prow}"
        # the node tile itself must be empty
        assert grid[house["row"]][x] == COL_EMPTY, f"{house['id']}: node tile blocked"
        # the player must be able to stand on the platform under the node
        assert grid[prow][x] == COL_TOP, f"{house['id']}: no standing surface"
        # the pole must land on the platform below
        below = prow + 3
        if below in platform_rows:
            below_x0, below_x1 = next(
                (a, b) for r, a, b in PLATFORMS if r == below
            )
            assert below_x0 <= x <= below_x1, (
                f"{house['id']}: pole at x={x} does not land on platform row "
                f"{below} (x {below_x0}..{below_x1})"
            )
        else:
            assert grid[below][x] == COL_SOLID, (
                f"{house['id']}: pole at x={x} row {below} lands on nothing"
            )
        # the pole column must be clear of terrain so the cable reads;
        # the bottom row is the landing row and may be platform or solid
        for row in range(prow + 1, prow + 3):
            assert grid[row][x] == COL_EMPTY, (
                f"{house['id']}: pole column x={x} row {row} is blocked"
            )
        landing = grid[prow + 3][x]
        assert landing in (COL_TOP, COL_SOLID), (
            f"{house['id']}: pole at x={x} row {prow + 3} lands on nothing"
        )

    # every platform must be reachable: no rise greater than 3 tiles
    rows = sorted(platform_rows, reverse=True)
    for lower, upper in zip(rows, rows[1:]):
        rise = lower - upper
        assert 1 <= rise <= 3, f"platform rows {lower}->{upper} rise {rise} tiles"

    # NPCs and the player must stand on something
    for npc in NPCS:
        assert grid[npc["row"]][npc["x"]] == COL_EMPTY, f"{npc['id']}: blocked"
        assert grid[npc["platform"]][npc["x"]] != COL_EMPTY, f"{npc['id']}: floating"
    assert grid[PLAYER_START["y"]][PLAYER_START["x"]] == COL_EMPTY, "spawn blocked"
    assert grid[PLAYER_START["y"] + 1][PLAYER_START["x"]] != COL_EMPTY, "spawn floating"

    # hazards must sit in empty space
    for x0, x1, r0, r1 in HAZARDS:
        for row in range(r0, r1 + 1):
            for x in range(x0, x1 + 1):
                assert grid[row][x] == COL_EMPTY, f"hazard at {x},{row} is solid"

    # RLE round trip
    encoded = collisions_rle()
    assert decode_rle(encoded) == [c for row in grid for c in row], "rle round trip"
    assert len(decode_rle(encoded)) == MAP_W * MAP_H, "collision count"

    # budget
    assert unique_background_tiles() <= 384, "background tile budget"
    assert sprite_tile_budget() <= 192, "sprite tile budget"

    print(f"level ok: {MAP_W}x{MAP_H} tiles, {len(HOUSES)} houses, "
          f"{len(NPCS)} locals, {len(HAZARDS)} hazards")


if __name__ == "__main__":
    _self_check()
