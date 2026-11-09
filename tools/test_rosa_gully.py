"""3B signal_gully: the first Down+A drop, open banks and floor recovery.

Run: python3 -m unittest discover -s tools -p test_rosa_gully.py (stdlib + contracts).

The static route model uses tile jumps, not native traces. Here we also
restrict it to open-air falls to distinguish the intact bridge's required
Down+A drop from the optional step-off drops in the lower gully.
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

    def test_head_bridge_preserves_the_deliberate_drop(self):
        grid = rosa.collision_grid(GULLY)
        row = rosa.GULLY_HEAD_BRIDGE
        self.assertTrue(all(grid[row][x] != shaft.COL_EMPTY for x in range(1, rosa.GULLY_W - 1)))
        self.assertIn(shaft.COL_TOP, grid[row])

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
        self.assertEqual(max(y for _, y in self.without_drop), rosa.GULLY_HEAD_BRIDGE - 1)

    def test_open_bank_edges_have_catch_shelves(self):
        # The open right lip after pole 4 lands at y17; the left bank below
        # the central bridge lands at y23. Neither needs another Down+A tap.
        for source, opening, catches in (((13, 14), range(14, 18), 17), ((6, 20), range(2, 5), 23)):
            with self.subTest(source=source):
                steps = no_drop_neighbours(self.graph.grid, self.graph.standable,
                                           *source, self.route["max_rise"])
                self.assertTrue(any((x, catches) in steps for x in opening))

    def test_dry_spillway_recovers_to_work_pad_and_floor_exit(self):
        # A long fall down the lower west bank can be recovered from, even
        # before T4. The last carry's floor has no timed threat to its exit.
        pole5 = rosa.LINES[-1]["pole"]
        work_pad = self.deep_targets["T4 zone"]
        floor_path = {(x, rosa.GULLY_FLOOR - 1) for x in range(pole5[0], rosa.GULLY_W - 1)}
        self.assertLessEqual(floor_path, self.graph.standable)
        self.assertFalse(any(row + 1 == pole5[1] for _, row, _, _ in self.route["lanes"]))
        self.assertFalse(any(row - 1 == pole5[1] for row, _, _ in self.route["boards"]))
        self.assertTrue(self.deep_targets["floor exit"] & floor_path)
        self.assertTrue(work_pad & self.graph.reach(pole5))

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
