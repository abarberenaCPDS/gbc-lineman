"""3B signal_gully: the mandatory Down+A descent (docs/LEVEL_REDESIGN.md §7 WP3 acceptance).

Run: python3 -m unittest discover -s tools -p test_rosa_gully.py (stdlib + contracts).

The route model is test_routes' (walk, step off, jump: rise up to 4 rows in this
shaft, run 4). Its falls pass through one-way timber, i.e. drop-through is
enabled. With drop-through disabled, a fall may cross only open air: the hero
can still walk off the arrival shelf onto deck 9 (T3), but nothing below deck 9
is reachable, so every target past T3 needs a Down+A tap.
"""
import unittest

import grid_chain
import rosa
import shaft
import test_routes

GULLY = rosa.GULLY


def no_drop_neighbours(grid, standable, x, y, max_rise):
    """test_routes.neighbours without drop-through: a fall crosses only empty tiles."""
    return [(tx, ty) for tx, ty in test_routes.neighbours(grid, standable, x, y, max_rise=max_rise)
            if ty <= y or all(grid[r][tx] == shaft.COL_EMPTY for r in range(y + 1, ty + 1))]


def reach(route, source, drop_through):
    graph = test_routes.Routes(route)
    if drop_through:
        return graph.reach(source), graph
    rise = route.get("max_rise", test_routes.MAX_RISE)
    seen, todo = {source}, [source]
    while todo:
        x, y = todo.pop()
        for nxt in no_drop_neighbours(graph.grid, graph.standable, x, y, rise):
            if nxt not in seen:
                seen.add(nxt)
                todo.append(nxt)
    return seen, graph


class DropThroughRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.route = next(r for r in rosa.ROUTE_SCENES if r["folder"] == GULLY)
        cls.start = rosa.GULLY_START
        cls.with_drop, cls.graph = reach(cls.route, cls.start, True)
        cls.without_drop, _ = reach(cls.route, cls.start, False)
        lines = {line["key"]: line for line in rosa.lines_here(GULLY)}
        cls.deep_targets = {
            "pole 4": {lines["east"]["pole"]},
            "T4 zone": cls.graph.zone(lines["east"]),
            "checkpoint 4": {lines["east"]["checkpoint"]},
            "pole 5": {lines["house"]["pole"]},
            "floor exit": cls.graph.exit_tiles(rosa.downstream_exit(GULLY)),
        }

    def test_every_deck_is_wall_to_wall(self):
        grid = rosa.collision_grid(GULLY)
        for row in [*rosa.GULLY_DECK_ROWS, rosa.GULLY_FLOOR]:
            self.assertTrue(all(grid[row][x] != shaft.COL_EMPTY for x in range(1, rosa.GULLY_W - 1)), row)
            self.assertTrue(all(grid[row][x] == shaft.COL_TOP for x in range(*shaft.DECK_WALK)), row)

    def test_every_target_is_reachable_with_drop_through(self):
        for name, tiles in self.deep_targets.items():
            with self.subTest(target=name):
                self.assertTrue(tiles and tiles & self.with_drop)
        middle = next(line for line in rosa.lines_here(GULLY) if line["key"] == "middle")
        self.assertTrue(self.graph.zone(middle) & self.with_drop)

    def test_without_drop_through_nothing_past_t3_is_reachable(self):
        for name, tiles in self.deep_targets.items():
            with self.subTest(target=name):
                self.assertFalse(tiles & self.without_drop)
        # Walking off the arrival shelf reaches deck 9 (T3), and no lower row.
        middle = next(line for line in rosa.lines_here(GULLY) if line["key"] == "middle")
        self.assertTrue(self.graph.zone(middle) & self.without_drop)
        self.assertEqual(max(y for _, y in self.without_drop), rosa.GULLY_DECK_ROWS[-1] - 1)

    def test_each_deck_needs_its_own_tap(self):
        """Every deck row below the arrival is crossed only through one-way timber."""
        rows = sorted({y for _, y in self.with_drop})
        for deck in sorted(rosa.GULLY_DECK_ROWS):
            above = {p for p in self.with_drop if p[1] < deck}
            below = {p for p in self.with_drop if p[1] > deck}
            crossings = [(p, q) for p in above for q in self.graph.adj[p] if q in below]
            with self.subTest(deck=deck):
                self.assertTrue(crossings)
                grid = self.graph.grid
                self.assertTrue(all(any(grid[deck][x] == shaft.COL_TOP for x in (p[0], q[0]))
                                    for p, q in crossings), "a deck is crossed only through timber")
        self.assertIn(self.route["entries"][1][1], rows)

    def test_the_way_back_up_reaches_the_hill_exit(self):
        """Going back up uses the climb's moves (the 4-row leap onto the arrival shelf)."""
        hill_exit = next(link.rect for link in rosa.links(GULLY) if link.target == rosa.HILL)
        tiles = self.graph.exit_tiles(hill_exit)
        for source in (rosa.LINES[-1]["pole"], self.route["entries"][1]):
            with self.subTest(source=source):
                self.assertTrue(tiles & self.graph.reach(source))

    def test_oam_window_without_culling(self):
        self.assertFalse(self.route["culled"])
        self.assertLessEqual(test_routes.oam_window(self.route) + shaft.HERO_OBJ, shaft.OAM_LIMIT)
        self.assertLessEqual(test_routes.worst_scanline(self.route), grid_chain.SCANLINE_OBJ_LIMIT)

    def test_no_culling_thread_in_the_scene(self):
        import make_rosa_scene as scene
        script = scene.GULLY_SCENE.build_scene("music", {"death": "d", "connect": "c", "pickup": "p"})["script"]
        self.assertFalse(any(e["command"] == "EVENT_THREAD_START" for e in script))


if __name__ == "__main__":
    unittest.main()
