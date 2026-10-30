"""The redesign's tile maps (docs/LEVEL_REDESIGN.md §2), parsed as data. Stdlib only.

The spec's ASCII maps are the agreed layout for WP1-WP4. This module reads them
straight from the document so the shared validators (test_routes.py,
test_scene_links.py) can check the spec itself, and so a job worker can derive
contract data from the same source instead of retyping coordinates:

    import redesign_maps
    crest = redesign_maps.load()["climb_crest"]
    crest.grid            # collision bytes (shaft.COL_*), MAP_H rows of MAP_W
    crest.lines           # [{"number", "pole"?, "box"?, "checkpoint"?}] as printed under the map
    crest.lanes           # [(kind, chest row, x0, x1)]: kind gust / whip / arc / cable
    crest.boards          # [(plank row, x0, x1)]
    crest.triggers        # [(label, (x, y, w, h))] in the spec's order
    crest.start, crest.entries, crest.npcs, crest.devices, crest.validator

Map legend (spec §2): ``#`` solid, ``=`` one-way timber, ``b`` cracked board
(a plank on a one-way row); every other character is open air for collision
(``S`` upstream entry, ``e`` downstream entry, ``X`` exit trigger, ``1``-``5``
pole feet, ``A``-``E`` transformer feet, ``N`` neighbour, ``o`` device, ...).
Once a job's contract holds its maps, its own tests take over; these maps stay
the reference the contracts are compared with.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import shaft

SPEC = Path(__file__).resolve().parent.parent / "docs" / "LEVEL_REDESIGN.md"

_HEADING = re.compile(r"^#### (\d[ABC]) (\w+) \((\d+)x(\d+)")
_POINT = r"\((\d+), (\d+)\)"
_LINE = re.compile(rf"L(\d) (?:pole {_POINT})?\s*(?:box {_POINT})?\s*(?:checkpoint {_POINT})?")
_HAZARD = re.compile(r"(board|cable|whip|gust|arc) r(\d+) x(\d+)-(\d+)")
_TRIGGER = re.compile(r"((?:back )?to [\w ]+?) \((\d+), (\d+), (\d+), (\d+)\)")
_VALIDATOR = re.compile(r"worst OAM window (\d+)\+4 hero; worst scanline (\d+)")


@dataclass
class SpecScene:
    code: str                     # "1A"
    folder: str
    width: int
    height: int
    rows: list[str]
    grid: list[list[int]] = field(default_factory=list)
    lines: list[dict] = field(default_factory=list)
    lanes: list[tuple[str, int, int, int]] = field(default_factory=list)
    boards: list[tuple[int, int, int]] = field(default_factory=list)
    triggers: list[tuple[str, tuple[int, int, int, int]]] = field(default_factory=list)
    validator: dict = field(default_factory=dict)

    def cells(self, char: str) -> list[tuple[int, int]]:
        return [(x, y) for y, row in enumerate(self.rows) for x, c in enumerate(row) if c == char]

    @property
    def start(self) -> tuple[int, int]:
        return self.cells("S")[0]

    @property
    def entries(self) -> list[tuple[int, int]]:
        return self.cells("S") + self.cells("e")

    @property
    def npcs(self) -> list[tuple[int, int]]:
        return self.cells("N")

    @property
    def devices(self) -> list[tuple[int, int]]:
        return self.cells("o")

    @property
    def job(self) -> int:
        return int(self.code[0])

    @property
    def vertical(self) -> bool:
        return self.height > 18


def _grid(rows: list[str]) -> list[list[int]]:
    collision = {"#": shaft.COL_SOLID, "=": shaft.COL_TOP, "b": shaft.COL_TOP}
    return [[collision.get(c, shaft.COL_EMPTY) for c in row] for row in rows]


def parse(text: str) -> dict[str, SpecScene]:
    out: dict[str, SpecScene] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        match = _HEADING.match(lines[i])
        if not match:
            i += 1
            continue
        code, folder, width, height = match.group(1), match.group(2), int(match.group(3)), int(match.group(4))
        while not lines[i].startswith("```text"):
            i += 1
        block = []
        i += 1
        while not lines[i].startswith("```"):
            block.append(lines[i])
            i += 1
        rows = [row[4:4 + width] for row in block[2:]]
        assert len(rows) == height and all(len(row) == width for row in rows), f"{folder} map size"
        scene = SpecScene(code, folder, width, height, rows, _grid(rows))
        i += 1
        while i < len(lines) and not lines[i].startswith("#"):
            line = lines[i]
            if line.startswith("Lines:"):
                for part in line[len("Lines:"):].split(";"):
                    m = _LINE.search(part)
                    if m:
                        entry = {"number": int(m.group(1))}
                        for name, gx in (("pole", 2), ("box", 4), ("checkpoint", 6)):
                            if m.group(gx) is not None:
                                entry[name] = (int(m.group(gx)), int(m.group(gx + 1)))
                        scene.lines.append(entry)
            elif line.startswith("Hazards"):
                for kind, row, x0, x1 in _HAZARD.findall(line):
                    lane = (int(row), int(x0), int(x1))
                    if kind == "board":
                        scene.boards.append(lane)
                    else:
                        scene.lanes.append((kind, *lane))
            elif line.startswith("Triggers:"):
                for label, *rect in _TRIGGER.findall(line):
                    scene.triggers.append((label.strip(), tuple(int(v) for v in rect)))
            elif line.startswith("Validator:"):
                m = _VALIDATOR.search(line)
                scene.validator = {"window": int(m.group(1)), "scanline": int(m.group(2))}
            i += 1
        out[folder] = scene
    return out


@lru_cache(maxsize=1)
def load() -> dict[str, SpecScene]:
    """Every §2 scene map by folder, in play order."""
    return parse(SPEC.read_text(encoding="utf-8"))
