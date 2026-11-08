"""The scene link table (tools/scene_links.py) against the contracts, the spec maps and the
generated exit triggers.

Run: "$PY" -m unittest discover -s tools -p test_scene_links.py (stdlib only).
"""
from __future__ import annotations

import json
import unittest

import climb  # noqa: F401  (import order: climb before hazards/tickets)
import grid_chain
import kiko
import opening
import redesign_maps
import ridge
import rosa
import scene_links
import scenes
import tickets

LAYOUTS = ("today", "redesign")


def walk(events):
    for entry in events:
        yield entry
        for branch in entry.get("children", {}).values():
            yield from walk(branch)


def grids(layout: str) -> dict[str, list[list[int]]]:
    """Collision grid per folder for one layout (storm_report and the work order have none)."""
    out = {"service_opening": opening.collision_grid()}
    if layout == "today":
        legacy = {"storm_climb": climb.collision_grid, "wind_ridge": ridge.collision_grid,
                  "signal_hill": rosa.collision_grid, "pine_hollow": kiko.collision_grid}
        # A migrated job's contract describes the redesign, not today's grid.
        out.update({folder: grid() for folder, grid in legacy.items()
                    if not scene_links.migrated(scene_links.job_of(folder))})
    else:
        out.update({folder: spec.grid for folder, spec in redesign_maps.load().items()})
    return out


def hero_box(tile):
    x, y = tile
    return {(tx, ty) for tx in (x, x + 1) for ty in (y - 2, y - 1, y)}


def rect_tiles(rect):
    x, y, w, h = rect
    return {(tx, ty) for tx in range(x, x + w) for ty in range(y, y + h)}


class TableTests(unittest.TestCase):
    def test_both_layouts_symmetric(self):
        for layout in LAYOUTS:
            table = scene_links.table(layout)
            pairs = {(link.source, link.target) for link in table}
            for link in table:
                with self.subTest(layout=layout, link=(link.source, link.target)):
                    if link.internal:
                        self.assertIn((link.target, link.source), pairs, "internal links go both ways")
                        back = next(item for item in table
                                    if (item.source, item.target) == (link.target, link.source))
                        self.assertTrue(back.internal)
                    elif link.ticket is None and link.target != scene_links.REPORT:
                        self.assertIn((link.target, link.source), pairs, "a direct link has a way back")

    def test_gates(self):
        for layout in LAYOUTS:
            for link in scene_links.table(layout):
                with self.subTest(layout=layout, link=(link.source, link.target)):
                    if link.internal:
                        self.assertIsNone(link.gate, "internal exits are ungated")
                        self.assertIsNone(link.ticket)
                    if link.ticket is not None or link.target == scene_links.REPORT:
                        self.assertIsNotNone(link.gate, "a hand-off waits for the neighbour's house")
                    if link.gate is not None:
                        self.assertTrue(link.gate.isdigit() and int(link.gate) < 512)
                    self.assertEqual(link.fade, "2", "every link fades (Abe)")

    def test_hand_offs_follow_the_jobs(self):
        for layout in LAYOUTS:
            hand_offs = [link for link in scene_links.table(layout) if link.ticket is not None]
            self.assertEqual([link.ticket for link in hand_offs], [1, 2, 3, 4])
            for link in hand_offs:
                with self.subTest(layout=layout, ticket=link.ticket):
                    self.assertEqual(link.target, scene_links.JOB_SCENES[link.ticket][0])
                    self.assertEqual(scene_links.job_of(link.source), link.ticket - 1)
                    if layout == "redesign":
                        self.assertEqual(link.source, scene_links.JOB_SCENES[link.ticket - 1][-1])
                    self.assertEqual(link.entry, scene_links.job_start(link.ticket, layout))

    def test_entries_stand_two_columns_inside_and_clear_of_exits(self):
        for layout in LAYOUTS:
            table = scene_links.table(layout)
            grid_by_folder = grids(layout)
            for link in table:
                if link.target not in grid_by_folder:
                    continue
                target = link.target
                entry = link.entry
                grid = grid_by_folder[target]
                with self.subTest(layout=layout, link=(link.source, target)):
                    self.assertTrue(grid_chain.stands(grid, *entry), f"entry {entry} does not stand")
                    self.assertTrue(2 <= entry[0] <= len(grid[0]) - 3, f"entry {entry} too near the edge")
                    for exit_ in scene_links.from_scene(target, table):
                        self.assertFalse(hero_box(entry) & rect_tiles(exit_.rect),
                                         f"entry {entry} inside exit {exit_.rect}")

    def test_internal_exits_are_edge_columns(self):
        widths = {folder: spec.width for folder, spec in redesign_maps.load().items()}
        for link in scene_links.table("redesign"):
            if not link.internal:
                continue
            x, _, w, h = link.rect
            with self.subTest(link=(link.source, link.target)):
                self.assertEqual((w, h), (1, 3))
                # The map edge, or the last open column inside a shaft's right wall.
                self.assertTrue(x <= 1 or x >= widths[link.source] - 3)

    def test_redesign_matches_the_spec_maps(self):
        specs = redesign_maps.load()
        for folder, spec in specs.items():
            with self.subTest(folder=folder):
                self.assertEqual([link.rect for link in scene_links.from_scene(folder, scene_links.table("redesign"))],
                                 [rect for _, rect in spec.triggers])
                arrivals = {link.entry for link in scene_links.into_scene(folder, scene_links.table("redesign"))}
                # The map's S (and e) tiles are arrivals; back links into a map without
                # an "e" land on a tile chosen here (checked by the entry test above).
                self.assertLessEqual(set(spec.entries), arrivals)
                if folder == scene_links.JOB_SCENES[spec.job][0]:
                    self.assertEqual(spec.start, scene_links.REDESIGN_START[spec.job])

    def test_registry(self):
        for layout in LAYOUTS:
            for link in scene_links.table(layout):
                for folder in (link.source, link.target):
                    self.assertEqual(scenes.REGISTRY[folder]["tag"], scenes.GAME)

    def test_exit_events(self):
        def event(command, args, key):
            return {"command": command, "args": args, "id": key}

        def set_value(variable, value, key):
            return event("EVENT_SET_VALUE", {"variable": variable, "value": {"type": "number", "value": value}}, key)

        def number(value):
            return {"type": "number", "value": value}

        hand_off = scene_links.link("storm_climb", "wind_ridge", scene_links.table("today"))
        self.assertEqual(scene_links.exit_events(hand_off, "summit-exit", event=event, set_value=set_value,
                                                 number=number),
                         tickets.to_work_order(2, "summit-exit", event, set_value, number))
        street = scene_links.link("storm_climb", "service_opening", scene_links.table("today"))
        switch = scene_links.exit_events(street, "street-exit", event=event, set_value=set_value, number=number)
        self.assertEqual(switch[0]["args"], {"x": number(16), "y": number(9), "direction": "left",
                                             "sceneId": opening.resource_id("scene:service-opening"),
                                             "fadeSpeed": "2"})


class TodayTests(unittest.TestCase):
    """While a job is not migrated, its rows equal the contracts' constants."""

    def test_constants_shared_with_tickets(self):
        self.assertEqual(scene_links.VAR_TICKET, tickets.VAR_TICKET)
        self.assertEqual(scene_links.VAR_TICKET, grid_chain.VAR_TICKET)
        self.assertEqual(scene_links.WORK_ORDER_POSITION, tickets.HERO_POSITION)
        self.assertEqual(scene_links.scene_id(scene_links.WORK_ORDER), tickets.WORK_ORDER_SCENE_ID)
        self.assertEqual(scene_links.scene_id(scene_links.REPORT), tickets.REPORT_SCENE_ID)
        for number, ticket in tickets.TICKETS.items():
            with self.subTest(ticket=number):
                self.assertEqual(ticket["start"], scene_links.job_start(number))
                self.assertEqual(ticket["scene_id"], scene_links.scene_id(scene_links.JOB_SCENES[number][0]))

    def test_today_rows_match_the_contracts(self):
        expected = {
            ("service_opening", "storm_climb"): (opening.EXIT, "4"),
            ("storm_climb", "service_opening"): (climb.STREET_EXIT, None),
        }
        if not scene_links.migrated(1):
            expected[("storm_climb", "wind_ridge")] = (ridge.CLIMB_SUMMIT_EXIT, ridge.CLIMB_EXIT_GATE_VAR)
        if not scene_links.migrated(2):
            expected[("wind_ridge", "signal_hill")] = (rosa.RIDGE_EXIT, rosa.RIDGE_EXIT_GATE_VAR)
        if not scene_links.migrated(3):
            expected[("signal_hill", "pine_hollow")] = (kiko.HILL_EXIT, kiko.HILL_EXIT_GATE_VAR)
        if not scene_links.migrated(4):
            expected[("pine_hollow", "storm_report")] = (tickets.REPORT_EXIT, tickets.REPORT_EXIT_GATE_VAR)
        current = {(link.source, link.target): link for link in scene_links.links()}
        for pair, (rect, gate) in expected.items():
            with self.subTest(link=pair):
                self.assertEqual(current[pair].rect, tuple(rect))
                self.assertEqual(current[pair].gate, gate)
        self.assertEqual(current[("storm_climb", "service_opening")].entry, opening.EXIT_NUDGE)

    def test_links_follow_migration(self):
        for job in range(1, 5):
            rows = (scene_links.REDESIGN if scene_links.migrated(job) else scene_links.TODAY)[job]
            current = [link for link in scene_links.links() if scene_links.job_of(link.source) == job]
            self.assertEqual([(link.source, link.rect, link.target) for link in current],
                             [(link.source, link.rect, link.target) for link in rows])


class GeneratedTriggerTests(unittest.TestCase):
    """Every generated exit trigger is a link, with its rect, target, entry, facing, fade and gate."""

    @staticmethod
    def triggers(folder):
        for path in sorted((scenes.SCENES_DIR / folder / "triggers").glob("*.gbsres")):
            yield path.name, json.loads(path.read_text(encoding="utf-8"))

    def test_generated_exits_match_links(self):
        links = scene_links.links()
        for folder in [f for job in scene_links.JOB_SCENES.values() for f in job]:
            if not scenes.present(folder):
                continue
            exits = {link.rect: link for link in scene_links.from_scene(folder, links)}
            found = set()
            for name, trigger in self.triggers(folder):
                events = list(walk(trigger["script"]))
                switches = [e for e in events if e["command"] == "EVENT_SWITCH_SCENE"]
                if not switches:
                    continue
                rect = (trigger["x"], trigger["y"], trigger["width"], trigger["height"])
                with self.subTest(folder=folder, trigger=name):
                    self.assertIn(rect, exits, "a switching trigger that is not in scene_links")
                    link = exits[rect]
                    found.add(rect)
                    if link.source == "service_opening":
                        # This one handoff has two exclusive routes: first dispatch
                        # opens the canonical card; street reentry resumes the job.
                        self.assertEqual(link.ticket, 1)
                        self.assertEqual(link.target, "storm_climb")
                        gate = trigger["script"][0]
                        [dispatch] = gate["children"]["true"]
                        self.assertEqual(dispatch["command"], "EVENT_IF")
                        self.assertEqual(dispatch["args"]["condition"], {
                            "type": "eq",
                            "valueA": {"type": "variable", "value": opening.VAR_AMARA_DISPATCHED},
                            "valueB": {"type": "number", "value": 0},
                        })
                        first = dispatch["children"]["true"]
                        self.assertEqual([e["command"] for e in first],
                                         ["EVENT_SET_VALUE", "EVENT_SET_VALUE", "EVENT_SWITCH_SCENE"])
                        self.assertEqual(first[0]["args"], {
                            "variable": opening.VAR_AMARA_DISPATCHED,
                            "value": {"type": "number", "value": 1},
                        })
                        self.assertEqual(first[1]["args"], {
                            "variable": scene_links.VAR_TICKET,
                            "value": {"type": "number", "value": link.ticket},
                        })
                        self.assertEqual(first[-1]["args"], {
                            "sceneId": scene_links.scene_id(scene_links.WORK_ORDER),
                            "x": {"type": "number", "value": scene_links.WORK_ORDER_POSITION[0]},
                            "y": {"type": "number", "value": scene_links.WORK_ORDER_POSITION[1]},
                            "direction": "down", "fadeSpeed": link.fade,
                        })
                        [resume] = dispatch["children"]["false"]
                        self.assertEqual(resume["command"], "EVENT_SWITCH_SCENE")
                        self.assertEqual(resume["args"], {
                            "sceneId": scene_links.scene_id(link.target),
                            "x": {"type": "number", "value": link.entry[0]},
                            "y": {"type": "number", "value": link.entry[1]},
                            "direction": link.facing, "fadeSpeed": link.fade,
                        })
                        # The normal table checks below still validate the first
                        # dispatch and its ticket; no third switch is permitted.
                        self.assertEqual(switches, [first[-1], resume])
                        args = first[-1]["args"]
                        self.assertTrue(grid_chain.stands(climb.collision_grid(), *link.entry))
                        for exit_ in scene_links.from_scene(link.target, links):
                            self.assertFalse(hero_box(link.entry) & rect_tiles(exit_.rect))
                    else:
                        self.assertEqual(len(switches), 1)
                        args = switches[0]["args"]
                    self.assertEqual(args["fadeSpeed"], link.fade)
                    if link.ticket is not None:
                        self.assertEqual(args["sceneId"], scene_links.scene_id(scene_links.WORK_ORDER))
                        tickets_set = [e for e in events if e["command"] == "EVENT_SET_VALUE"
                                       and e["args"]["variable"] == scene_links.VAR_TICKET]
                        self.assertEqual([e["args"]["value"]["value"] for e in tickets_set], [link.ticket])
                    else:
                        self.assertEqual(args["sceneId"], scene_links.scene_id(link.target))
                        self.assertEqual((args["x"]["value"], args["y"]["value"]), link.entry)
                        self.assertEqual(args["direction"], link.facing)
                    top = trigger["script"][0]
                    if link.gate is None:
                        self.assertNotEqual(top["command"], "EVENT_IF")
                    else:
                        condition = top["args"]["condition"]
                        self.assertEqual((top["command"], condition["type"]), ("EVENT_IF", "eq"))
                        self.assertEqual(condition["valueA"]["value"], link.gate)
                        self.assertEqual(condition["valueB"]["value"], 1)
            with self.subTest(folder=folder):
                self.assertEqual(found, set(exits), "every link from this scene has its trigger")


if __name__ == "__main__":
    unittest.main()
