"""Authoritative design source for "Mister CFE: After the Storm".

Data only: map grid, palette ramps, house/resident/connector placements and the
interaction copy. Every generator (art, sprites, scene, audio) imports this so
the visual, spatial and scripted layers cannot drift.

Run directly to validate the design and the reachability of every objective:

    python3 tools/village.py
"""

from __future__ import annotations

TILE = 8
WIDTH = 32
HEIGHT = 32

# ---------------------------------------------------------------------------
# Palette ramps
#
# Four colors per palette, ordered LIGHTEST -> DARKEST. Background tiles index
# them '0'..'3'. Sprite palettes use the same order but index 0 is the
# transparent color, so sprites draw only with '1'..'3'.
#
# Art direction: blue hour in a mountain village just after a storm. The
# environment is cool slate-teal; amber appears only where power is restored.
# Ramps are deliberately wide (near-white -> near-black) to reproduce the
# high-contrast, big-silhouette look of the sample project's `platform_path`
# and `parallax` scenes.
# ---------------------------------------------------------------------------

BG_PALETTES = [
    ("ground", ["#C7D0C8", "#8CA394", "#52705F", "#273B31"]),
    ("path", ["#DECDA6", "#B79B6E", "#7F6440", "#3B2E1E"]),
    ("rock", ["#C2C6D2", "#8C93A6", "#5A6076", "#2A2E40"]),
    ("water", ["#CFE2E4", "#8FB4BC", "#4E7A8A", "#22394A"]),
    ("house", ["#EFE2CC", "#D0A87C", "#9A6E4E", "#4A2A2E"]),
    ("roof", ["#C4AEC0", "#8E6E86", "#5C4058", "#2A1C2E"]),
    ("pine", ["#AFC0AC", "#6E8C74", "#3A5A48", "#1A2E26"]),
    ("lit", ["#FFF4CC", "#FFC659", "#C27A18", "#4A2A0C"]),
]

SPRITE_PALETTES = [
    ("hero", ["#000000", "#20283C", "#3E5A80", "#F0C070"]),
    ("folk_a", ["#000000", "#3A2438", "#8E4A58", "#F0C8A0"]),
    ("folk_b", ["#000000", "#24343A", "#4E8A7A", "#EFE0C0"]),
    ("folk_c", ["#000000", "#3A3018", "#8A6A2E", "#F0D8B0"]),
    ("prop", ["#000000", "#2A3448", "#7E8FA8", "#F0E4C4"]),
    ("glow", ["#000000", "#C27A18", "#FFC659", "#FFF4CC"]),
]

# Background palette slots 0..6 hold the ramps above; slot 7 is the UI palette.
UI_PALETTE = "default-ui"
UI_SPRITE_PALETTE = "default-sprite"

# ---------------------------------------------------------------------------
# Map
#
# One character per 8x8 tile. Each row is four 8-character chunks so the grid
# can be counted by eye.
#
#   '#'  cliff / rock wall     solid
#   'T'  pine tree             solid
#   'b'  boulder               solid
#   '~'  stream water          solid
#   '='  bridge                walkable
#   '.'  trodden path          walkable
#   ','  grass                 walkable
#   '"'  tall grass            walkable, hides a pickup
#   'o'  pebbles               walkable
#   '1'..'5'  house anchor: a 5x4 cottage is stamped from this cell
# ---------------------------------------------------------------------------

MAP = [
    #            x0-7      x8-15     x16-23    x24-31
    "########" "########" "########" "########",  # y00
    "########" "########" "########" "########",  # y01
    "##TT,,,," ",,,,,,,," ",,,,,,,," ",~~~,,##",  # y02
    "##T,,,,," ",,,,,,,," ",,,,,,,," ",~~~,,##",  # y03
    "##,,4,,," ",,,,,,,," ",,,,,,,," ",~~~,,##",  # y04
    "##,,4,,," ",,,,,,,," ",,,,5,,," ",~~~,,##",  # y05
    "##,,4,,," ",,,TT,,," ",,,,5,,," ",~~~,,##",  # y06
    "##,,4,,," ",,,,,,,," ",,,,5,,," ",~~~,,##",  # y07
    "##,,,,.." "........" ",,,,,,.." ",~~~,,##",  # y08
    "##,,,,,," ",,,,,,.." "........" ",~~~,,##",  # y09
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y10
    "##,,,,,o" ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y11
    "##,,,,,," ",,,,,,.." ",3,,,,,," ",~~~,,##",  # y12
    "#,2,,,,," ",,,,,,.." ",3,,,,,," ",~~~,,##",  # y13
    "#,2,,,,," ",,,,,,.." ",3,,,,,," ",~~~,,##",  # y14
    "#,2,,,,," ",,,,,,.." ",3,,,,,," ",~~~,,##",  # y15
    "##,,,,,," ",,,,,,.." ",......." ",~~~,,##",  # y16
    "##,,,b,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y17
    "##,,,,,," ",,,,,,.." "........" ".===..##",  # y18
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y19
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y20
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y21
    "##,1,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y22
    "##,1,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y23
    "##,1,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y24
    "##,1,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y25
    "##,,,..." "........" ",,,,,,,," ",~~~,,##",  # y26
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y27
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y28
    "##,,,,,," ",,,,,,.." ",,,,,,,," ",~~~,,##",  # y29
    "########" "########" "########" "########",  # y30
    "########" "########" "########" "########",  # y31
]

SOLID_TILES = set("#Tb~")

HOUSE_W = 5
HOUSE_H = 4
DOOR_OFFSET = 2  # door column, relative to the house's left edge

# Repaired bottom-up: the substation at the foot of the village feeds house a,
# then each home further up the slope in turn.
HOUSES = [
    {
        "key": "a",
        "anchor": (3, 22),
        "name": "Marta's House",
        "resident": "Marta",
        "colour": "folk_a",
        "ask": ["Marta: The line", "broke last night.", "A connector fell", "in the tall grass", "south of here."],
        "thanks": ["Marta: Lights!", "And the kettle", "can boil again.", "Thank you."],
        "connector": (9, 28),
        "resident_at": (8, 26),
    },
    {
        "key": "b",
        "anchor": (2, 13),
        "name": "Rosa's House",
        "resident": "Rosa",
        "colour": "folk_b",
        "ask": ["Rosa: My radio", "is dead. My spare", "connector rolled", "across the bridge", "in the flood."],
        "thanks": ["Rosa: Warm light,", "and music on the", "radio again.", "Good neighbours."],
        "connector": (29, 17),
        "resident_at": (7, 16),
    },
    {
        "key": "c",
        "anchor": (17, 12),
        "name": "Kiko's House",
        "resident": "Kiko",
        "colour": "folk_c",
        "ask": ["Kiko: The pole", "fell on washing.", "I saw a connector", "roll east along", "the river bank."],
        "thanks": ["Kiko: I can dry", "my shirts again.", "Soup later, yes?"],
        "connector": (24, 12),
        "resident_at": (22, 15),
    },
    {
        "key": "d",
        "anchor": (4, 4),
        "name": "Tino's House",
        "resident": "Tino",
        "colour": "folk_a",
        "ask": ["Tino: This house", "needs juice. One", "connector waits", "up the slope by", "the pines."],
        "thanks": ["Tino: The lamp", "works. My maps", "are readable", "again."],
        "connector": (13, 6),
        "resident_at": (9, 7),
    },
    {
        "key": "e",
        "anchor": (19, 5),
        "name": "Beto's House",
        "resident": "Beto",
        "colour": "folk_b",
        "ask": ["Beto: One house", "left on the line.", "The connector is", "up on the north", "ridge. Then rest."],
        "thanks": ["Beto: The whole", "mountain is lit.", "Listen to it hum."],
        "connector": (21, 3),
        "resident_at": (17, 8),
    },
]

SUBSTATION = {
    "pos": (12, 28),
    "intro": [
        "The substation is",
        "cold and silent.",
        "Five homes up the",
        "slope are dark.",
        "",
        "B: talk, pick up,",
        "place and link.",
    ],
    "win": [
        "The mountain hums",
        "again. Rain on",
        "the roofs, light",
        "in every window.",
        "",
        "Thank you,",
        "Mister CFE.",
    ],
}

PLAYER_SPAWN = (14, 28)

# Music stages keyed by number of repaired houses (0..5).
MUSIC_STAGES = [0, 0, 0, 1, 1, 2]

# Decorative tall grass cells that hide each connector, for the art layer.
TALL_GRASS = [(8, 28), (9, 28), (29, 16), (24, 13), (13, 5), (21, 2)]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def house(key: str) -> dict:
    for item in HOUSES:
        if item["key"] == key:
            return item
    raise KeyError(key)


def house_rect(key: str) -> tuple[int, int, int, int]:
    x, y = house(key)["anchor"]
    return x, y, HOUSE_W, HOUSE_H


def house_tiles() -> set[tuple[int, int]]:
    cells: set[tuple[int, int]] = set()
    for item in HOUSES:
        x0, y0, w, h = house_rect(item["key"])
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                cells.add((x, y))
    return cells


def house_door(key: str) -> tuple[int, int]:
    """The walkable doorstep in front of a cottage."""
    x0, y0, _w, h = house_rect(key)
    return x0 + DOOR_OFFSET, y0 + h


def is_solid(x: int, y: int) -> bool:
    if not (0 <= x < WIDTH and 0 <= y < HEIGHT):
        return True
    if (x, y) in house_tiles():
        return True
    return MAP[y][x] in SOLID_TILES


def collision_rows() -> list[str]:
    return ["".join("1" if is_solid(x, y) else "0" for x in range(WIDTH)) for y in range(HEIGHT)]


def validate() -> list[str]:
    problems: list[str] = []
    if len(MAP) != HEIGHT:
        problems.append(f"map has {len(MAP)} rows, expected {HEIGHT}")
    for y, row in enumerate(MAP):
        if len(row) != WIDTH:
            problems.append(f"row {y} has {len(row)} columns, expected {WIDTH}")

    for item in HOUSES:
        key = item["key"]
        x0, y0, w, h = house_rect(key)
        if x0 < 1 or y0 < 1 or x0 + w > WIDTH - 1 or y0 + h > HEIGHT - 1:
            problems.append(f"house {key} leaves the map")
        door = house_door(key)
        if is_solid(*door):
            problems.append(f"house {key} doorstep {door} is blocked")
        if is_solid(*item["resident_at"]):
            problems.append(f"resident {key} at {item['resident_at']} stands in scenery")
        if is_solid(*item["connector"]):
            problems.append(f"connector {key} at {item['connector']} is inside scenery")

    for x, y in TALL_GRASS:
        if MAP[y][x] != ",":
            problems.append(f"tall grass {x},{y} sits on {MAP[y][x]!r}, not grass")

    if is_solid(*PLAYER_SPAWN):
        problems.append(f"player spawn {PLAYER_SPAWN} is blocked")
    if is_solid(*SUBSTATION["pos"]):
        problems.append(f"substation {SUBSTATION['pos']} is blocked")

    anchors = [item["anchor"] for item in HOUSES]
    if len(set(anchors)) != len(anchors):
        problems.append("two houses share an anchor")
    return problems


def reachable() -> set[tuple[int, int]]:
    from collections import deque

    seen = {PLAYER_SPAWN}
    queue = deque([PLAYER_SPAWN])
    while queue:
        x, y = queue.popleft()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) not in seen and not is_solid(nx, ny):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


MAX_COPY_CHARS = 17


def validate_copy() -> list[str]:
    """Dialogue boxes are 144px wide with the default font: ~17 characters."""
    problems: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    for item in HOUSES:
        blocks.append((f"{item['key']} ask", item["ask"]))
        blocks.append((f"{item['key']} thanks", item["thanks"]))
    blocks.append(("substation intro", SUBSTATION["intro"]))
    blocks.append(("substation win", SUBSTATION["win"]))
    for label, lines in blocks:
        for line in lines:
            if len(line) > MAX_COPY_CHARS:
                problems.append(f"{label}: {len(line)} chars > {MAX_COPY_CHARS}: {line!r}")
    return problems


def validate_reachability() -> list[str]:
    seen = reachable()
    problems: list[str] = []
    for item in HOUSES:
        key = item["key"]
        checks = {
            "doorstep": house_door(key),
            "resident": item["resident_at"],
            "connector": item["connector"],
        }
        for label, cell in checks.items():
            if cell not in seen:
                problems.append(f"{label} for house {key} at {cell} is unreachable from spawn")
    if SUBSTATION["pos"] not in seen:
        problems.append("substation is unreachable from spawn")
    return problems


if __name__ == "__main__":
    issues = validate() + validate_copy() + validate_reachability()
    if issues:
        for issue in issues:
            print("FAIL:", issue)
        raise SystemExit(1)
    print(
        f"village ok: {WIDTH}x{HEIGHT} tiles, {len(HOUSES)} houses, "
        f"{len(BG_PALETTES)} bg / {len(SPRITE_PALETTES)} sprite palettes, "
        f"{len(reachable())} walkable tiles"
    )
