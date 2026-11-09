"""Static route audit for every job scene (stdlib + contract modules), data-driven.

Run: "$PY" -m unittest discover -s tools -p test_routes.py

Sources, in this order:

1. ``ROUTE_SCENES`` of each job contract (``climb``, ``ridge``, ``rosa``, ``kiko``):
   a list of route-scene dicts (schema below). Every rule runs on them.
2. Today's single-scene levels (Wind Ridge, Signal Hill, Pine Hollow) for a
   contract that has no ``ROUTE_SCENES`` yet: the legacy rules only (reach,
   line order, exit, safe ground), exactly as before the redesign.
3. The redesign spec's own maps (``redesign_maps``, docs/LEVEL_REDESIGN.md §2):
   every rule, and the OAM window / scanline numbers must equal the spec's.

Route-scene schema (a contract builds one dict per scene folder; tuples in tiles):

  folder     scene folder, e.g. "climb_crest"
  grid       collision grid (rows of shaft.COL_* bytes)
  start      upstream entry tile (route source and respawn fallback)
  entries    every link entry tile into the scene (default [start])
  lines      this scene's parts of the job's lines: grid_chain.scene_lines(LINES, folder);
             each {"key", "number", "pole"?, "box"?, "checkpoint"?, "reach"?}
  lanes      [(kind, chest row, x0, x1)], kind "gust" | "whip" | "arc" | "cable";
             span arcs and hidden cables included
  boards     [(plank row, x0, x1)] (hazards.placement)
  exit       downstream exit trigger rect (x, y, w, h), or None
  exits      every link trigger rect of the scene (default [exit])
  npcs       [(x, feet)] neighbours (4 OBJ, 2 columns); devices: [(x, feet)] (2 OBJ)
  max_rise   rows one jump climbs (default 3; 4 where a shaft keeps the summit leap)
  culled     True when a culling thread owns the OAM budget (shaft.py); the
             32-column / 30-row window rule is then the job's own culling test

Movement model (coarse, like opening.reachable; jump arcs are not traced):
  * walk one tile sideways, or step off an edge and fall (drop-through is enabled, so falls are free)
  * jump: rise up to ``max_rise`` tiles (a short A tap clears one 3-tile shelf), travel up to MAX_RUN tiles
  * a jump is blocked by a solid tile in a crossed column at the body band of the lower foot row
  * the hero is 24px: feet row and two above; one-way (COL_TOP) tiles are passable from below,
    and the body may overlap one (route_stands); props use grid_chain.stands
Hazards are timed, so the route search ignores them; the hazard check asks for safe ground instead.

Spec rules (docs/LEVEL_REDESIGN.md, "every map below was checked by"):
  lane spacing         chest-row lanes on one row leave >= LANE_GAP open columns between them
  respawn clearance    the start and every checkpoint keep >= RESPAWN_CLEAR columns from any
                       chest-row lane whose feet row is within RESPAWN_ROWS rows
  head room            nothing over a pole's top row (feet - 3) or a transformer's (feet - 2),
                       both columns; hazard lanes are open air over a surface (chest row + 2)
  transformer footing  both box columns stand on support
  entries              every entry stands (grid_chain.stands), two columns inside the map,
                       outside every exit trigger
  OAM window           worst OBJ sum over a 32-column (run) or 30-row (shaft) window,
                       hero excluded, + HERO_OBJ <= OAM_LIMIT unless culled
  scanline             worst OBJ columns on one tile row of a 20-column screen + hero (2) <= 10
"""
from __future__ import annotations

import unittest
from collections import deque

import climb
import grid_chain
import hazards
import kiko
import redesign_maps
import ridge
import rosa
import scene_links
import shaft

MAX_RISE = 3       # tiles a jump climbs: one A tap per 3-tile shelf, as the contracts assume
MAX_RUN = 4        # tiles a jump or step-off travels sideways (run-jump gaps up to 4)
SAFE_WINDOW = 4    # a safe tile lies within this many columns on each side of a hazard range
SAFE_RISE = 3      # ...at a feet row at most one tap away from the hazard's feet row
LANE_GAP = 3
RESPAWN_CLEAR = 5
RESPAWN_ROWS = 2
WINDOW_COLUMNS = 32
WINDOW_ROWS = 30
LANE_KINDS = ("gust", "whip", "arc", "cable")
# OBJ footprint per kind: (columns, rows above and including the anchor, 8x16 OBJs).
FOOTPRINTS = {"pole": (2, 4, 4), "npc": (2, 4, 4), "whip": (2, 4, 4), "gust": (3, 2, 3),
              "board": (3, 2, 3), "arc": (2, 2, 2), "cable": (2, 2, 2), "device": (2, 2, 2)}


# ---------------------------------------------------------------------------
# Movement graph
# ---------------------------------------------------------------------------
def _open(grid, cols, rows) -> bool:
    return all(grid[r][c] != climb.COL_SOLID for c in cols for r in rows)


def route_stands(grid, x: int, y: int) -> bool:
    """The hero can stand at feet tile (x, y): open feet tile, support below, and no
    rock in the two body rows above. Unlike grid_chain.stands (props), the body may
    overlap one-way timber: a shaft ledge sits three rows under the deck above."""
    return (grid[y][x] == climb.COL_EMPTY and grid[y + 1][x] in (climb.COL_TOP, climb.COL_SOLID)
            and grid[y - 1][x] != climb.COL_SOLID and grid[y - 2][x] != climb.COL_SOLID)


def standable(grid) -> set[tuple[int, int]]:
    return {(x, y) for x in range(1, len(grid[0]) - 1) for y in range(2, len(grid) - 1)
            if route_stands(grid, x, y)}


def neighbours(grid, standable_tiles, x, y, max_rise: int = MAX_RISE) -> list[tuple[int, int]]:
    out = []
    for dx in range(-MAX_RUN, MAX_RUN + 1):
        tx = x + dx
        for ty in range(y - max_rise, len(grid) - 1):
            if (tx, ty) not in standable_tiles or (dx == 0 and ty == y):
                continue
            if ty < y and not _open(grid, [x], range(ty - 2, y - 2)):
                continue                                  # no head room while rising
            if ty > y and not _open(grid, [tx], range(y - 2, ty + 1)):
                continue                                  # the fall column is solid
            lo = min(y, ty)
            if not _open(grid, range(min(x, tx) + 1, max(x, tx)), range(lo - 2, lo + 1)):
                continue                                  # a crossed column blocks the arc
            out.append((tx, ty))
    return out


class Routes:
    """Standable tiles and the jump graph of one route scene."""

    def __init__(self, scene: dict) -> None:
        self.scene = scene
        self.grid = scene["grid"]
        self.standable = standable(self.grid)
        rise = scene.get("max_rise", MAX_RISE)
        self.adj = {p: neighbours(self.grid, self.standable, *p, max_rise=rise) for p in self.standable}

    def reach(self, source) -> set[tuple[int, int]]:
        assert source in self.standable, f"{self.scene['folder']}: {source} is not a standable tile"
        seen, todo = {source}, deque([source])
        while todo:
            for nxt in self.adj[todo.popleft()]:
                if nxt not in seen:
                    seen.add(nxt)
                    todo.append(nxt)
        return seen

    def can_reach(self, targets) -> set[tuple[int, int]]:
        """Reverse search: positions from which at least one target can be reached."""
        previous = {p: [] for p in self.standable}
        for source, destinations in self.adj.items():
            for destination in destinations:
                previous[destination].append(source)
        seen = set(targets) & self.standable
        todo = deque(seen)
        while todo:
            for source in previous[todo.popleft()]:
                if source not in seen:
                    seen.add(source)
                    todo.append(source)
        return seen

    def zone(self, line) -> set[tuple[int, int]]:
        x, y, w, h = line.get("reach") or grid_chain.reach_rect(line["box"])
        return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)} & self.standable

    def exit_tiles(self, rect) -> set[tuple[int, int]]:
        """Standable tiles where the 16px hero (feet tile and the next) touches ``rect`` or walks into it."""
        x, y, w, h = rect
        return {(tx, ty) for tx, ty in self.standable
                if x - 2 <= tx <= x + w            # hero columns tx..tx+1 touch the rect, +-1 column
                and ty >= y and ty - 2 <= y + h - 1}   # hero rows ty-2..ty overlap the rect rows


# ---------------------------------------------------------------------------
# Rules: each returns a list of problems (empty when the scene passes)
# ---------------------------------------------------------------------------
def _lane_feet(scene) -> list[tuple[int, int, int]]:
    """(feet row, x0, x1) of every hazard: chest-row lanes + 1, boards (plank row) - 1."""
    lanes = [(row + 1, x0, x1) for _, row, x0, x1 in scene.get("lanes", [])]
    lanes += [(row - 1, x0, x1) for row, x0, x1 in scene.get("boards", [])]
    return lanes


def reach_problems(scene, routes: Routes) -> list[str]:
    name, out = scene["folder"], []
    seen = routes.reach(scene["start"])
    for line in scene["lines"]:
        key = line.get("key", line["number"])
        if "pole" in line and line["pole"] not in seen:
            out.append(f"{name}: {key} pole stand unreachable from start")
        if "box" in line and not routes.zone(line) & seen:
            out.append(f"{name}: {key} box zone unreachable from start")
        if "checkpoint" in line and line["checkpoint"] not in seen:
            out.append(f"{name}: {key} checkpoint unreachable from start")
    return out


def order_problems(scene, routes: Routes) -> list[str]:
    """Each carry walks forwards: pole -> box zone (or the downstream exit), checkpoint -> next pole."""
    name, out = scene["folder"], []
    lines = scene["lines"]
    exit_tiles = routes.exit_tiles(scene["exit"]) if scene.get("exit") else set()
    for k, line in enumerate(lines):
        key = line.get("key", line["number"])
        if "pole" in line:
            seen = routes.reach(line["pole"])
            if "box" in line:
                if not routes.zone(line) & seen:
                    out.append(f"{name}: {key} box zone not walkable from its pole {line['pole']}")
                if "checkpoint" in line and line["checkpoint"] not in seen:
                    out.append(f"{name}: {key} checkpoint not walkable from its pole {line['pole']}")
            elif scene.get("exit") and not exit_tiles & seen:
                out.append(f"{name}: {key} cable cannot leave through the exit from its pole")
        if "checkpoint" in line and k + 1 < len(lines) and "pole" in lines[k + 1]:
            nxt = lines[k + 1]
            if nxt["pole"] not in routes.reach(line["checkpoint"]):
                out.append(f"{name}: checkpoint {line['checkpoint']} of {key} cannot reach the "
                           f"{nxt.get('key', nxt['number'])} pole {nxt['pole']}")
    return out


def exit_problems(scene, routes: Routes) -> list[str]:
    name, rect = scene["folder"], scene.get("exit")
    if rect is None:
        return []
    tiles = routes.exit_tiles(rect)
    if not tiles:
        return [f"{name}: exit rect {rect} has no standable approach"]
    checkpoints = [line["checkpoint"] for line in scene["lines"] if "checkpoint" in line]
    source = checkpoints[-1] if checkpoints else scene["start"]
    if not tiles & routes.reach(source):
        return [f"{name}: exit {rect} unreachable from {source}"]
    return []


def safe_ground_problems(scene, routes: Routes) -> list[str]:
    name, out = scene["folder"], []
    lanes = _lane_feet(scene)
    hazard_cells = {(x, f) for f, x0, x1 in lanes for x in range(x0, x1 + 1)}
    seen = routes.reach(scene["start"])
    for f, x0, x1 in lanes:
        sides = {"left": range(x0 - SAFE_WINDOW, x0), "right": range(x1 + 1, x1 + 1 + SAFE_WINDOW)}
        for side, xs in sides.items():
            safe = [(x, y) for x in xs for y in range(f - SAFE_RISE, f + SAFE_RISE + 1)
                    if (x, y) in seen and (x, y) not in hazard_cells]
            if not safe:
                out.append(f"{name}: hazard columns {x0}-{x1} (feet row {f}) leave no reachable safe "
                           f"ground on the {side} within {SAFE_WINDOW} tiles")
    return out


def lane_spacing_problems(scene) -> list[str]:
    out, by_row = [], {}
    for kind, row, x0, x1 in scene.get("lanes", []):
        by_row.setdefault(row, []).append((x0, x1, kind))
    for row, lanes in by_row.items():
        lanes.sort()
        for (a0, a1, ak), (b0, b1, bk) in zip(lanes, lanes[1:]):
            if b0 - a1 - 1 < LANE_GAP:
                out.append(f"{scene['folder']}: {ak} {a0}-{a1} and {bk} {b0}-{b1} on row {row} "
                           f"leave {b0 - a1 - 1} columns (< {LANE_GAP})")
    return out


def respawn_problems(scene) -> list[str]:
    out = []
    points = [("start", scene["start"])]
    points += [(f"checkpoint {line.get('key', line['number'])}", line["checkpoint"])
               for line in scene["lines"] if "checkpoint" in line]
    for label, (x, feet) in points:
        for kind, row, x0, x1 in scene.get("lanes", []):
            if abs(row + 1 - feet) > RESPAWN_ROWS:
                continue
            distance = x0 - x if x < x0 else (x - x1 if x > x1 else 0)
            if distance < RESPAWN_CLEAR:
                out.append(f"{scene['folder']}: {label} {(x, feet)} is {distance} columns from {kind} "
                           f"{x0}-{x1} (row {row}); keep {RESPAWN_CLEAR}")
    return out


def head_room_problems(scene) -> list[str]:
    grid, name, out = scene["grid"], scene["folder"], []

    def clear(x, row) -> bool:
        return all(grid[row][c] == shaft.COL_EMPTY for c in (x, x + 1))

    for line in scene["lines"]:
        if "pole" in line:
            x, y = line["pole"]
            if not clear(x, y - 3):
                out.append(f"{name}: pole {line['pole']} top stands under a platform")
        if "box" in line:
            x, y = line["box"]
            if not clear(x, y - 2):
                out.append(f"{name}: transformer {line['box']} top stands under a platform")
    for kind, row, x0, x1 in scene.get("lanes", []):
        cols = range(x0, x1 + 1)
        if not all(grid[row][x] == shaft.COL_EMPTY for x in cols):
            out.append(f"{name}: {kind} lane {x0}-{x1} row {row} is in rock")
        if not all(grid[row + 2][x] in (shaft.COL_TOP, shaft.COL_SOLID) for x in cols):
            out.append(f"{name}: {kind} lane {x0}-{x1} row {row} has no surface at row {row + 2}")
    return out


def footing_problems(scene) -> list[str]:
    grid, name, out = scene["grid"], scene["folder"], []
    supported = (shaft.COL_TOP, shaft.COL_SOLID)
    for line in scene["lines"]:
        if "box" in line:
            x, y = line["box"]
            if not all(grid[y + 1][c] in supported for c in (x, x + 1)):
                out.append(f"{name}: transformer {line['box']} lacks footing under both columns")
        if "pole" in line and not grid_chain.stands(grid, *line["pole"]):
            out.append(f"{name}: pole {line['pole']} does not stand")
        if "checkpoint" in line and not grid_chain.stands(grid, *line["checkpoint"]):
            out.append(f"{name}: checkpoint {line['checkpoint']} does not stand")
    for x, y in [*scene.get("npcs", []), *scene.get("devices", [])]:
        if not grid_chain.stands(grid, x, y):
            out.append(f"{name}: prop {(x, y)} does not stand")
    return out


def _hero_box(tile) -> set[tuple[int, int]]:
    x, y = tile
    return {(tx, ty) for tx in (x, x + 1) for ty in (y - 2, y - 1, y)}


def _rect_tiles(rect) -> set[tuple[int, int]]:
    x, y, w, h = rect
    return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)}


def entry_problems(scene) -> list[str]:
    grid, name, out = scene["grid"], scene["folder"], []
    width = len(grid[0])
    exits = scene.get("exits") or ([scene["exit"]] if scene.get("exit") else [])
    for tile in scene.get("entries") or [scene["start"]]:
        x, y = tile
        if not grid_chain.stands(grid, x, y):
            out.append(f"{name}: entry {tile} does not stand")
        if not 2 <= x <= width - 3:
            out.append(f"{name}: entry {tile} is not two columns inside the map")
        for rect in exits:
            if _hero_box(tile) & _rect_tiles(rect):
                out.append(f"{name}: entry {tile} lies inside exit {rect}")
    return out


def sprite_footprints(scene) -> list[tuple[int, int, int, int, int]]:
    """(x, anchor row, columns, rows, OBJ) per actor, the spec's §5 budget model."""
    out = []

    def add(kind, x, anchor):
        cols, rows, obj = FOOTPRINTS[kind]
        out.append((x, anchor, cols, rows, obj))

    for line in scene["lines"]:
        if "pole" in line:
            add("pole", *line["pole"])
    for kind, row, x0, _ in scene.get("lanes", []):
        add(kind, x0, row + 1 if kind == "whip" else row)   # a whip hangs to the standing row
    for row, x0, _ in scene.get("boards", []):
        add("board", x0, row)
    for x, y in scene.get("npcs", []):
        add("npc", x, y)
    for x, y in scene.get("devices", []):
        add("device", x, y)
    return out


def _vertical(scene) -> bool:
    return len(scene["grid"]) > grid_chain.SCREEN_TILES - 2 and len(scene["grid"][0]) == grid_chain.SCREEN_TILES


def oam_window(scene) -> int:
    """Worst OBJ sum over the active-actor window, hero excluded."""
    sprites = sprite_footprints(scene)
    height, width = len(scene["grid"]), len(scene["grid"][0])
    if _vertical(scene):
        return max(sum(obj for _, anchor, _, _, obj in sprites if top <= anchor < top + WINDOW_ROWS)
                   for top in range(height))
    return max(sum(obj for x, _, _, _, obj in sprites if left <= x < left + WINDOW_COLUMNS)
               for left in range(width))


def worst_scanline(scene) -> int:
    """Worst OBJ columns on one tile row of any 20-column screen, hero (2) included."""
    sprites = sprite_footprints(scene)
    height, width = len(scene["grid"]), len(scene["grid"][0])
    best = 0
    for left in range(max(width - grid_chain.SCREEN_TILES, 0) + 1):
        for row in range(height):
            best = max(best, sum(cols for x, anchor, cols, rows, _ in sprites
                                 if x < left + grid_chain.SCREEN_TILES and x + cols > left
                                 and anchor - rows + 1 <= row <= anchor))
    return best + shaft.HERO_COLUMNS


def budget_problems(scene) -> list[str]:
    out = []
    window = oam_window(scene) + shaft.HERO_OBJ
    if not scene.get("culled") and window > shaft.OAM_LIMIT:
        out.append(f"{scene['folder']}: OAM window {window} > {shaft.OAM_LIMIT} without a culling thread")
    scanline = worst_scanline(scene)
    if scanline > grid_chain.SCANLINE_OBJ_LIMIT:
        out.append(f"{scene['folder']}: scanline {scanline} > {grid_chain.SCANLINE_OBJ_LIMIT}")
    return out


LEGACY_RULES = ("reach", "order", "exit", "safe_ground")
ALL_RULES = LEGACY_RULES + ("lane_spacing", "respawn", "head_room", "footing", "entries", "budget")


def problems(scene, rules=ALL_RULES, routes: Routes | None = None) -> dict[str, list[str]]:
    """{rule: problems} for one route scene."""
    routes = routes or Routes(scene)
    checks = {
        "reach": lambda: reach_problems(scene, routes),
        "order": lambda: order_problems(scene, routes),
        "exit": lambda: exit_problems(scene, routes),
        "safe_ground": lambda: safe_ground_problems(scene, routes),
        "lane_spacing": lambda: lane_spacing_problems(scene),
        "respawn": lambda: respawn_problems(scene),
        "head_room": lambda: head_room_problems(scene),
        "footing": lambda: footing_problems(scene),
        "entries": lambda: entry_problems(scene),
        "budget": lambda: budget_problems(scene),
    }
    return {rule: checks[rule]() for rule in rules}


# ---------------------------------------------------------------------------
# Scene sources
# ---------------------------------------------------------------------------
def _legacy_scene(module, folder: str, exit_rect) -> dict:
    """Today's single-scene level as a route scene (contracts without ROUTE_SCENES)."""
    lanes = [("lane", row, x0, x1) for row, x0, x1 in module.hazard_lanes()]
    lanes += [("cable", row, x0, x1) for row, x0, x1 in hazards.HIDDEN_CABLES[folder]]
    return {"folder": folder, "grid": module.collision_grid(), "start": module.START,
            "lines": module.LINES, "lanes": lanes, "boards": hazards.BOARDS[folder], "exit": exit_rect}


LEGACY = {
    "ridge": lambda: _legacy_scene(ridge, "wind_ridge", rosa.RIDGE_EXIT),
    "rosa": lambda: _legacy_scene(rosa, "signal_hill", kiko.HILL_EXIT),
    "kiko": lambda: _legacy_scene(kiko, "pine_hollow", None),
}
CONTRACTS = {"climb": climb, "ridge": ridge, "rosa": rosa, "kiko": kiko}
SHAFT_RISE = {"storm_climb": 4, "signal_gully": 4, "pine_ladder": 4}   # the summit leap stays
SHAFT_CULLED = {"storm_climb", "pine_ladder"}


def contract_scenes() -> list[tuple[str, dict, tuple[str, ...]]]:
    """(contract, route scene, rules) from each contract's ROUTE_SCENES, else its legacy level."""
    out = []
    for job, module in CONTRACTS.items():
        declared = getattr(module, "ROUTE_SCENES", None)
        if declared is not None:
            out += [(job, scene, ALL_RULES) for scene in declared]
        elif job in LEGACY:
            out.append((job, LEGACY[job](), LEGACY_RULES))
    return out


def spec_scene(spec: redesign_maps.SpecScene) -> dict:
    """A §2 map as a route scene: its downstream exit is the last "to ..." trigger."""
    lines = [{**line, "key": f"L{line['number']}"} for line in spec.lines]
    to = [rect for label, rect in spec.triggers if not label.startswith("back")]
    return {"folder": spec.folder, "grid": spec.grid, "start": spec.start, "entries": spec.entries,
            "lines": lines, "lanes": spec.lanes, "boards": spec.boards, "exit": to[-1] if to else None,
            "exits": [rect for _, rect in spec.triggers], "npcs": spec.npcs, "devices": spec.devices,
            "max_rise": SHAFT_RISE.get(spec.folder, MAX_RISE), "culled": spec.folder in SHAFT_CULLED}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class ContractRoutes(unittest.TestCase):
    """Every contract's route scenes (legacy levels until the contract declares ROUTE_SCENES)."""

    def test_route_scenes(self) -> None:
        scenes = contract_scenes()
        self.assertTrue(scenes)
        for job, scene, rules in scenes:
            routes = Routes(scene)
            for rule, found in problems(scene, rules, routes).items():
                with self.subTest(contract=job, folder=scene["folder"], rule=rule):
                    self.assertEqual(found, [])

    def test_route_scene_schema(self) -> None:
        for job, module in CONTRACTS.items():
            for scene in getattr(module, "ROUTE_SCENES", None) or []:
                with self.subTest(contract=job, folder=scene.get("folder")):
                    self.assertLessEqual({"folder", "grid", "start", "lines", "lanes", "boards", "exit"},
                                         set(scene))
                    self.assertTrue(all(kind in LANE_KINDS for kind, *_ in scene["lanes"]))

    def test_internal_exits_remain_reachable_after_a_fall(self) -> None:
        """A dropped cable must be retrievable from its upstream home scene.

        Symmetric links alone do not prove the hero can climb back to a link.
        Check every reachable standing tile, including lower recovery floors.
        This is the static tap-jump model; native movement still needs testing.
        """
        for _, scene, _ in contract_scenes():
            routes = Routes(scene)
            reachable = set().union(*(routes.reach(entry) for entry in
                                      scene.get("entries", [scene["start"]])))
            for link in scene_links.from_scene(scene["folder"], scene_links.table("redesign")):
                if not link.internal:
                    continue
                with self.subTest(source=link.source, target=link.target):
                    recovery = routes.can_reach(routes.exit_tiles(link.rect))
                    self.assertEqual(sorted(reachable - recovery), [],
                                     "reachable ground strands the player away from an internal exit")

    def test_arrivals_have_full_width_safe_footing(self) -> None:
        for _, scene, _ in contract_scenes():
            grid = scene["grid"]
            for x, y in scene.get("entries", [scene["start"]]):
                with self.subTest(folder=scene["folder"], entry=(x, y)):
                    self.assertTrue(all(grid[y + 1][c] in (shaft.COL_TOP, shaft.COL_SOLID)
                                        for c in (x, x + 1)))
                    body = _hero_box((x, y))
                    for _, row, x0, x1 in scene["lanes"]:
                        self.assertFalse(body & {(c, row) for c in range(x0, x1 + 1)})
                    for row, x0, x1 in scene["boards"]:
                        self.assertFalse(body & {(c, row - 1) for c in range(x0, x1 + 1)})

    def test_recovery_rule_detects_the_original_arrival_traps(self) -> None:
        cases = {"climb_crest": (6, (7, 14), "storm_climb"),
                 "ridge_saddle": (6, (7, 14), "wind_ridge")}
        for _, scene, _ in contract_scenes():
            if scene["folder"] not in cases:
                continue
            x1, floor, target = cases[scene["folder"]]
            grid = [cells[:] for cells in scene["grid"]]
            for row in (9, 10, 11):
                grid[row][1:x1 + 1] = [shaft.COL_SOLID] * x1
            if scene["folder"] == "ridge_saddle":
                # Remove the new recovery step to recreate the original trap.
                for row in (12, 13, 14):
                    grid[row][7:9] = [shaft.COL_EMPTY] * 2
            broken = Routes({**scene, "grid": grid})
            link = scene_links.link(scene["folder"], target, scene_links.table("redesign"))
            with self.subTest(folder=scene["folder"]):
                self.assertIn(floor, broken.reach(scene["start"]))
                self.assertNotIn(floor, broken.can_reach(broken.exit_tiles(link.rect)))


class SpecMapRoutes(unittest.TestCase):
    """The redesign's own maps pass every rule, with the spec's budget numbers."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.specs = redesign_maps.load()

    def test_ten_scenes(self) -> None:
        self.assertEqual(list(self.specs), list(hazards.REDESIGN_SCENES))

    def test_spec_maps_pass_every_rule(self) -> None:
        for folder, spec in self.specs.items():
            scene = spec_scene(spec)
            for rule, found in problems(scene).items():
                with self.subTest(folder=folder, rule=rule):
                    self.assertEqual(found, [])

    def test_budget_model_matches_the_spec(self) -> None:
        for folder, spec in self.specs.items():
            scene = spec_scene(spec)
            with self.subTest(folder=folder):
                self.assertEqual(oam_window(scene), spec.validator["window"])
                self.assertEqual(worst_scanline(scene), spec.validator["scanline"])

    def test_hazard_placements_match_the_maps(self) -> None:
        for folder, spec in self.specs.items():
            boards, cables, delays = hazards.placement(folder, redesign=True)
            with self.subTest(folder=folder):
                expected_boards = {"signal_porch": [(12, 7, 9)],
                                   "climb_crest": [(9, 24, 26)]}.get(folder, spec.boards)
                self.assertEqual(sorted(boards), sorted(expected_boards))
                # The lakeside crest replaces the old redundant ground cable with
                # one readable live-wire crossing and a damaged cabin walkway.
                expected_cables = [] if folder == "climb_crest" else [
                    (row, x0, x1) for kind, row, x0, x1 in spec.lanes if kind == "cable"]
                self.assertEqual(sorted(cables), sorted(expected_cables))
                self.assertEqual(len(delays), len(cables))

    def test_rules_reject_broken_layouts(self) -> None:
        crest = spec_scene(self.specs["climb_crest"])
        crowded = {**crest, "lanes": [*crest["lanes"], ("gust", 13, 19, 21)]}
        self.assertTrue(lane_spacing_problems(crowded))
        near_start = {**crest, "lanes": [*crest["lanes"], ("arc", 7, 6, 7)]}
        self.assertTrue(respawn_problems(near_start))
        in_exit = {**crest, "entries": [(1, 8)]}
        self.assertTrue(entry_problems(in_exit))
        heavy = {**crest, "npcs": [(x, 11) for x in range(8, 40, 3)]}
        self.assertTrue(budget_problems(heavy))
        gully = spec_scene(self.specs["signal_gully"])
        self.assertTrue(budget_problems({**gully, "lanes": [*gully["lanes"]] * 2}))


if __name__ == "__main__":
    unittest.main()
