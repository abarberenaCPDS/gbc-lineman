"""Static route audit for the three horizontal job levels (stdlib + contract modules).

Run: "$PY" -m unittest discover -s tools -p test_routes.py

Movement model (coarse, like opening.reachable; jump arcs are not traced):
  * walk one tile sideways, or step off an edge and fall (drop-through is enabled, so falls are free)
  * jump: rise up to MAX_RISE tiles (a short A tap clears one 3-tile shelf) and travel up to MAX_RUN tiles
  * a jump is blocked by a solid tile in a crossed column at the body band of the lower foot row
  * the hero is 24px: feet row and two above; one-way (COL_TOP) tiles are passable from below
Hazards are timed, so the route search ignores them; the hazard check asks for safe ground instead.
"""
from __future__ import annotations

import unittest
from collections import deque

import climb
import grid_chain
import hazards
import kiko
import rosa
import ridge

MAX_RISE = 3       # tiles a jump climbs: one A tap per 3-tile shelf, as the contracts assume
MAX_RUN = 4        # tiles a jump or step-off travels sideways (run-jump gaps up to 4)
SAFE_WINDOW = 4    # a safe tile lies within this many columns on each side of a hazard range
SAFE_RISE = 3      # ...at a feet row at most one tap away from the hazard's feet row


def _open(grid, cols, rows) -> bool:
    return all(grid[r][c] != climb.COL_SOLID for c in cols for r in rows)


def _standable(grid) -> set[tuple[int, int]]:
    return {(x, y) for x in range(1, len(grid[0]) - 1) for y in range(2, len(grid) - 1)
            if grid_chain.stands(grid, x, y)}


def _neighbours(grid, standable, x, y) -> list[tuple[int, int]]:
    out = []
    for dx in range(-MAX_RUN, MAX_RUN + 1):
        tx = x + dx
        for ty in range(y - MAX_RISE, len(grid) - 1):
            if (tx, ty) not in standable or (dx == 0 and ty == y):
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


def _case(name: str, module, hazard_key: str, exit_rect) -> type[unittest.TestCase]:
    class Case(unittest.TestCase):
        @classmethod
        def setUpClass(cls) -> None:
            cls.grid = module.collision_grid()
            cls.standable = _standable(cls.grid)
            cls.adj = {p: _neighbours(cls.grid, cls.standable, *p) for p in cls.standable}

        def reach(self, source) -> set[tuple[int, int]]:
            self.assertIn(source, self.standable, f"{name}: {source} is not a standable tile")
            seen, todo = {source}, deque([source])
            while todo:
                for nxt in self.adj[todo.popleft()]:
                    if nxt not in seen:
                        seen.add(nxt)
                        todo.append(nxt)
            return seen

        def zone(self, line) -> set[tuple[int, int]]:
            x, y, w, h = line.get("reach") or grid_chain.reach_rect(line["box"])
            return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)} & self.standable

        def test_pole_box_and_checkpoint_reachable_from_start(self) -> None:
            seen = self.reach(module.START)
            for line in module.LINES:
                key = line["key"]
                self.assertIn(line["pole"], seen, f"{name}: {key} pole stand unreachable from start")
                self.assertTrue(self.zone(line) & seen, f"{name}: {key} box zone unreachable from start")
                self.assertIn(line["checkpoint"], seen, f"{name}: {key} checkpoint unreachable from start")

        def test_line_order_walks_forwards(self) -> None:
            lines = module.LINES
            for k, line in enumerate(lines):
                key = line["key"]
                seen = self.reach(line["pole"])
                self.assertTrue(self.zone(line) & seen,
                                f"{name}: {key} box zone not walkable from its pole {line['pole']}")
                self.assertIn(line["checkpoint"], seen,
                              f"{name}: {key} checkpoint not walkable from its pole {line['pole']}")
                if k + 1 < len(lines):
                    nxt = lines[k + 1]
                    self.assertIn(nxt["pole"], self.reach(line["checkpoint"]),
                                  f"{name}: checkpoint {line['checkpoint']} of {key} cannot reach "
                                  f"the {nxt['key']} pole {nxt['pole']}")

        def test_exit_reachable_after_last_checkpoint(self) -> None:
            if exit_rect is None:
                self.skipTest(f"{name} has no exit trigger of its own")
            x, y, w, h = exit_rect
            exit_tiles = {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)} & self.standable
            self.assertTrue(exit_tiles, f"{name}: exit rect {exit_rect} holds no standable tile")
            seen = self.reach(module.LINES[-1]["checkpoint"])
            self.assertTrue(exit_tiles & seen, f"{name}: exit {exit_rect} unreachable from the last checkpoint")

        def test_hazards_leave_safe_ground_on_both_sides(self) -> None:
            lanes = [(row + 1, x0, x1) for row, x0, x1 in module.hazard_lanes()]           # chest row -> feet
            lanes += [(row + 1, x0, x1) for row, x0, x1 in hazards.HIDDEN_CABLES[hazard_key]]
            lanes += [(row - 1, x0, x1) for row, x0, x1 in hazards.BOARDS[hazard_key]]    # plank row -> feet
            hazard_cells = {(x, f) for f, x0, x1 in lanes for x in range(x0, x1 + 1)}
            seen = self.reach(module.START)
            for f, x0, x1 in lanes:
                sides = {"left": range(x0 - SAFE_WINDOW, x0), "right": range(x1 + 1, x1 + 1 + SAFE_WINDOW)}
                for side, xs in sides.items():
                    safe = [(x, y) for x in xs for y in range(f - SAFE_RISE, f + SAFE_RISE + 1)
                            if (x, y) in seen and (x, y) not in hazard_cells]
                    self.assertTrue(safe, f"{name}: hazard columns {x0}-{x1} (feet row {f}) leave no "
                                          f"reachable safe ground on the {side} within {SAFE_WINDOW} tiles")

    Case.__name__ = Case.__qualname__ = name
    return Case


WindRidgeRoute = _case("WindRidgeRoute", ridge, "wind_ridge", rosa.RIDGE_EXIT)
SignalHillRoute = _case("SignalHillRoute", rosa, "signal_hill", kiko.HILL_EXIT)
PineHollowRoute = _case("PineHollowRoute", kiko, "pine_hollow", None)

if __name__ == "__main__":
    unittest.main()
