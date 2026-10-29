"""Focused tests for grid-chain palette, actor, and scene-budget support."""

import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grid_chain


def rid(key):
    return f"id:{key}"


def line(number=1, *, box_kind="transformer", live=0):
    suffix = str(number)
    return {
        "key": f"line-{suffix}",
        "number": number,
        "live_var": f"live-{suffix}",
        "pole": f"pole-{suffix}",
        "pole_at": (number * 4, 10),
        "pole_symbol": f"POLE_{suffix}",
        "pole_name": f"Pole {suffix}",
        "cable": f"cable-{suffix}",
        "cable_symbol": f"CABLE_{suffix}",
        "cable_name": f"Cable {suffix}",
        "box": f"box-{suffix}",
        "box_at": (number * 4 + 3, 10),
        "box_symbol": f"BOX_{suffix}",
        "box_name": f"Box {suffix}",
        "box_kind": box_kind,
        "checkpoint": (number * 4, 10),
        "live": live,
    }


def chain(lines):
    return grid_chain.GridChain(
        rid=rid,
        lines=lines,
        chain_var="chain-live",
        lines_var="lines-live",
        carrying_var="carrying",
        near_var="near",
        line_bg_slot=grid_chain.LINE_BG_SLOT_1,
        text={
            "pickup": "Picked up.", "hands_full": "Hands full.", "already": "Already live.",
            "all_live": "All live.", "lit": "Lit.", "dark": "Dark.",
            "no_cable": "No cable.", "wrong_cable": "Wrong cable.",
        },
        say=lambda *_args, **_kwargs: [],
        hud=lambda _key: [],
    )


def walk_events(events):
    for event in events:
        yield event
        for branch in event.get("children", {}).values():
            yield from walk_events(branch)


def sprite_profiles(project_dir):
    """Index real sprite sidecars by ID and stem, retaining frame OBJ tiles and bounds."""
    profiles = {}
    for path in (project_dir / "assets" / "sprites").glob("*.png.gbsres"):
        data = json.loads(path.read_text(encoding="utf-8"))
        frames = []
        for state in data.get("states", []):
            for animation in state.get("animations", []):
                for frame in animation.get("frames", []):
                    frames.append(tuple((tile["x"], tile["y"]) for tile in frame.get("tiles", [])))
        profiles[data["id"]] = profile = {
            "name": path.name.removesuffix(".png.gbsres"),
            "canvas": (data["canvasWidth"], data["canvasHeight"]),
            "bounds": (data["boundsX"], data["boundsY"],
                       data["boundsWidth"], data["boundsHeight"]),
            "frames": frames,
        }
        profiles[profile["name"]] = profile
    return profiles


def actor_profile(actor, profiles):
    """Resolve fake test sprite IDs to the real shared hazard art; otherwise use the actor ID."""
    symbol = actor["symbol"]
    fallback = None
    if "gust" in symbol:
        fallback = "climb_gust"
    elif "whip" in symbol:
        fallback = "whip_wire"
    elif "board" in symbol:
        fallback = "cracked_board"
    elif "arc" in symbol or "hidden_cable" in symbol:
        fallback = "live_arc"
    profile = profiles.get(fallback) if fallback else profiles.get(actor["spriteSheetId"])
    if profile is None:
        raise AssertionError(f"no sprite sidecar for {symbol} ({actor['spriteSheetId']})")
    return profile


def camera_rect(hero_x, hero_y, map_width, map_height):
    """World-pixel viewport for the 20x18 camera, clamped to the map edges."""
    left = min(max(hero_x - grid_chain.SCREEN_TILES // 2, 0),
               max(0, map_width - grid_chain.SCREEN_TILES))
    top = min(max(hero_y - 9, 0), max(0, map_height - 18))
    return (left * 8, top * 8, min(map_width, 20) * 8, min(map_height, 18) * 8)


def sprite_budget(project_dir, actors, hero_at, map_width, map_height, hero_name="opening_worker24",
                  profiles=None):
    """Return per-tile-row OAM pressure and visible active actors using real art bounds."""
    profiles = profiles or sprite_profiles(project_dir)
    hero_profile = profiles[hero_name]
    hero_x, hero_y = hero_at
    vx, vy, vw, vh = camera_rect(hero_x, hero_y, map_width, map_height)
    load = {}

    def add_sprite(actor_x, actor_y, profile):
        px = actor_x * 8
        by_row = {}
        for frame in profile["frames"]:
            frame_rows = {}
            for obj_x, obj_y in frame:
                if px + obj_x < vx + vw and px + obj_x + 8 > vx:
                    # Count each 8x16 OBJ on both of its 8px scanline bands.
                    top_row = actor_y - 1 - obj_y // 8
                    for row in (top_row, top_row + 1):
                        if vy <= row * 8 < vy + vh:
                            frame_rows[row] = frame_rows.get(row, 0) + 1
            for row, count in frame_rows.items():
                by_row[row] = max(by_row.get(row, 0), count)
        for row, count in by_row.items():
            load[row] = load.get(row, 0) + count

    # The player is a 24px 8x16 sprite, not an assumed 3x3 solid rectangle.
    add_sprite(hero_x, hero_y, hero_profile)

    active = []
    for actor in actors:
        profile = actor_profile(actor, profiles)
        add_sprite(actor["x"], actor["y"], profile)
        bx, by, bw, bh = profile["bounds"]
        actor_left = actor["x"] * 8 + bx
        actor_top = actor["y"] * 8 + by
        if (actor_left < vx + vw and actor_left + bw > vx
                and actor_top < vy + vh and actor_top + bh > vy):
            active.append(actor["symbol"])
    return load, active


def actor_states(events, actor_id):
    return [event["args"]["spriteStateId"] for event in walk_events(events)
            if event["command"] == "EVENT_ACTOR_SET_STATE"
            and event["args"].get("actorId") == actor_id]


class ChainPaletteTests(unittest.TestCase):
    METAL = ["placeholder", "metal-1", "metal-2", "metal-3"]
    STAGE_COLORS = [1, 2, 3, 1, 2, 3]

    def palettes(self, count):
        return grid_chain.chain_palettes(
            metal_dead=self.METAL,
            wire_live="wire-live",
            wire_dead="wire-dead",
            stage_color_index=self.STAGE_COLORS[:count],
        )

    def test_stage_color_contract_for_one_through_six_lines(self):
        for count in range(1, grid_chain.MAX_STAGES + 1):
            with self.subTest(count=count):
                grid_chain.check_stage_colors(self.STAGE_COLORS[:count])
                palettes = self.palettes(count)
                self.assertEqual(list(palettes), list(range(count + 1)))
                if count <= 3:
                    self.assertIsInstance(palettes[0], list)
                    self.assertEqual(palettes[0][1:count + 1], ["wire-dead"] * count)
                    self.assertEqual(palettes[count][1:count + 1], ["wire-live"] * count)
                else:
                    self.assertEqual(set(palettes[0]), {
                        grid_chain.LINE_BG_SLOT_1, grid_chain.LINE_BG_SLOT_2,
                    })
                    first, second = palettes[count][grid_chain.LINE_BG_SLOT_1], palettes[count][grid_chain.LINE_BG_SLOT_2]
                    self.assertEqual(first[1:4], ["wire-live"] * 3)
                    self.assertEqual(second[1:count - 2], ["wire-live"] * (count - 3))

    def test_two_slot_palettes_light_stages_four_through_six(self):
        palettes = self.palettes(6)
        for live in range(7):
            with self.subTest(live=live):
                slot1 = palettes[live][grid_chain.LINE_BG_SLOT_1]
                slot2 = palettes[live][grid_chain.LINE_BG_SLOT_2]
                self.assertEqual(slot1[1:4], ["wire-live" if i <= live else "wire-dead" for i in range(1, 4)])
                self.assertEqual(slot2[1:4], ["wire-live" if i + 3 <= live else "wire-dead" for i in range(1, 4)])

    def test_resources_and_ids_cover_both_slots_without_breaking_slot_one_ids(self):
        resources = grid_chain.chain_palette_resources(
            rid, label="Test", file_prefix="test", palettes=self.palettes(6),
        )
        self.assertEqual(len(resources), 14)
        paths = {path for path, _ in resources}
        self.assertIn("project/palettes/test_bg_chain_4_live.gbsres", paths)
        self.assertIn("project/palettes/test_bg_chain_4_live_slot_6.gbsres", paths)
        resource_ids = {resource["id"] for _, resource in resources}
        self.assertIn(rid("palette:bg:chain_4_live"), resource_ids)
        self.assertIn(rid("palette:bg:chain_4_live_slot_6"), resource_ids)
        self.assertEqual(grid_chain.chain_palette_id(rid, 4), rid("palette:bg:chain_4_live"))
        self.assertEqual(grid_chain.chain_palette_ids(rid, 4), {
            5: rid("palette:bg:chain_4_live"),
            6: rid("palette:bg:chain_4_live_slot_6"),
        })

    def test_invalid_palette_contracts_are_rejected(self):
        with self.assertRaises(AssertionError):
            grid_chain.check_stage_colors([1, 2, 3, 4])
        with self.assertRaises(AssertionError):
            grid_chain.check_stage_colors([1, 1])
        with self.assertRaises(AssertionError):
            grid_chain.check_stage_colors([1, 2, 3, 1, 1])


class TwoActorChainTests(unittest.TestCase):
    def setUp(self):
        self.lines = [line()]
        self.chain = chain(self.lines)
        self.item = self.lines[0]
        self.pole_id = rid("actor:pole-1")

    def test_pole_starts_with_folded_cable_or_standing_when_repaired(self):
        actor = self.chain.pole_actor(self.item, 0, "pole-sprite")
        self.assertEqual(actor["collisionGroup"], "")
        commands = list(walk_events(actor["startScript"]))
        self.assertIn("EVENT_ACTOR_COLLISIONS_DISABLE", [event["command"] for event in commands])
        condition = actor["startScript"][1]
        self.assertEqual(condition["children"]["true"][0]["args"]["spriteStateId"], "Standing")
        self.assertEqual(condition["children"]["false"][0]["args"]["spriteStateId"], "Snapped+Cable")

    def test_pickup_changes_pole_to_snapped_without_hiding_cable_actor(self):
        events = self.chain.pickup_press_events(self.item, "pickup", "pickup-sound")
        self.assertIn("Snapped", actor_states(events, self.pole_id))
        self.assertFalse(any(event["command"] == "EVENT_ACTOR_HIDE" for event in walk_events(events)))
        sets = [event for event in walk_events(events) if event["command"] == "EVENT_SET_VALUE"]
        self.assertTrue(any(event["args"]["variable"] == "carrying"
                            and event["args"]["value"]["value"] == 1 for event in sets))

    def test_drop_restores_folded_cable_state_without_showing_cable_actor(self):
        events = self.chain.cable_drop_events("drop")
        self.assertIn("Snapped+Cable", actor_states(events, self.pole_id))
        self.assertFalse(any(event["command"] == "EVENT_ACTOR_SHOW" for event in walk_events(events)))
        self.assertIn("", actor_states(events, "player"))

    def test_connect_sets_live_and_standing_pole(self):
        events = self.chain.box_connect_events(self.item, "connect", "connect-sound")
        self.assertIn("Standing", actor_states(events, self.pole_id))
        self.assertTrue(any(event["command"] == "EVENT_SET_VALUE"
                            and event["args"]["variable"] == "live-1"
                            and event["args"]["value"]["value"] == 1
                            for event in walk_events(events)))
        self.assertTrue(any(event["command"] == "EVENT_INC_VALUE"
                            and event["args"]["variable"] == "lines-live"
                            for event in walk_events(events)))

    def test_chain_refresh_swaps_both_wire_slots_for_six_lines(self):
        six_line_chain = chain([line(i) for i in range(1, 7)])
        events = list(walk_events(six_line_chain.chain_refresh_events("refresh")))
        palettes = [event["args"] for event in events
                    if event["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
        self.assertTrue(palettes)
        self.assertTrue(all(args["palette5"].startswith("id:palette:bg:chain_")
                            and args["palette6"].startswith("id:palette:bg:chain_")
                            for args in palettes))

    def test_chain_sprites_uses_only_pole_and_box_per_line(self):
        lines = [line(1), line(2, box_kind="junction")]
        sprites = grid_chain.chain_sprites(lines)
        self.assertEqual(len(sprites), 4)
        self.assertEqual(sprites, [
            ((4, 10), 2, 4), ((7, 10), 2, 4),
            ((8, 10), 2, 4), ((11, 10), 2, 2),
        ])

    def test_scanline_load_counts_the_two_actor_line(self):
        sprites = grid_chain.chain_sprites([line()])
        self.assertEqual(grid_chain.scanline_load(sprites, 20, 5, 10), {
            7: 4, 8: 7, 9: 7, 10: 7,
        })


class BoxScriptDispatchTests(unittest.TestCase):
    def setUp(self):
        self.lines = [line(i) for i in range(1, 6)]
        self.chain = chain(self.lines)

    def test_global_b_calls_only_the_selected_box_custom_script(self):
        attach = self.chain.input_script_event(pickup_sound_id="pickup", override=True)
        self.assertTrue(attach["args"]["override"])
        events = list(walk_events(attach["children"]["true"]))
        for item in self.lines:
            with self.subTest(line=item["number"]):
                zone = next(e for e in events if e["command"] == "EVENT_IF"
                            and e["args"]["condition"]["valueA"] == {"type": "variable", "value": "near"}
                            and e["args"]["condition"]["valueB"]["value"]
                            == grid_chain.BOX_ZONE + item["number"])
                bindings = self.chain.box_script_actor_bindings(item)
                expected_args = {"customEventId": self.chain.box_script_id(item)}
                expected_args.update({f"$actor[{index}]$": actor_id
                                      for index, (actor_id, _name) in enumerate(bindings)})
                self.assertEqual(zone["children"]["true"], [{
                    "command": "EVENT_CALL_CUSTOM_EVENT",
                    "args": expected_args,
                    "id": rid(f"event:b-press:{item['key']}:call-box"),
                }])
        commands = [e["command"] for e in events]
        self.assertNotIn("EVENT_PALETTE_SET_BACKGROUND", commands,
                         "the large chain refresh must stay out of the shared B script")
        self.assertNotIn("EVENT_INC_VALUE", commands,
                         "box repair logic belongs to per-actor scripts")

    def test_each_canonical_box_script_keeps_its_gate_repair_and_chain_refresh(self):
        resources = self.chain.box_script_resources(
            label="Test Grid", file_prefix="test_grid", connect_sound_id="connect",
        )
        self.assertEqual(len(resources), 5)
        for item, (path, resource) in zip(self.lines, resources):
            with self.subTest(line=item["number"]):
                self.assertEqual(path, f"project/scripts/test_grid_box_{item['key']}.gbsres")
                self.assertEqual(resource["_resourceType"], "script")
                self.assertEqual(resource["id"], rid(f"script:box:{item['key']}"))
                self.assertEqual(resource["variables"], {})
                self.assertEqual(len(resource["actors"]), 6, "box handlers bind all boxes and their pole")
                actor_params = set(resource["actors"])
                [live] = resource["script"]
                self.assertEqual(live["args"]["condition"]["valueA"],
                                 {"type": "variable", "value": item["live_var"]})
                has_cable = next(e for e in live["children"]["false"]
                                 if e["args"]["condition"]["valueA"] ==
                                 {"type": "variable", "value": "carrying"})
                connect = has_cable["children"]["true"]
                self.assertTrue(any(e["command"] == "EVENT_INC_VALUE"
                                    and e["args"]["variable"] == "lines-live"
                                    for e in walk_events(connect)))
                palettes = [e for e in walk_events(connect)
                            if e["command"] == "EVENT_PALETTE_SET_BACKGROUND"]
                self.assertTrue(palettes)
                self.assertTrue(all(e["args"]["palette5"].startswith("id:palette:bg:chain_")
                                    and e["args"]["palette6"].startswith("id:palette:bg:chain_")
                                    for e in palettes))
                actor_targets = {e["args"]["actorId"] for e in walk_events(resource["script"])
                                 if e["command"] == "EVENT_ACTOR_SET_STATE"
                                 and e["args"]["actorId"] != "player"}
                self.assertTrue(actor_targets <= actor_params)


class SceneLimitTests(unittest.TestCase):
    def test_actor_and_trigger_limits_include_boundary(self):
        grid_chain.check_scene_limits(20, 30)
        grid_chain.check_scene_limits(0, 0)
        with self.assertRaises(AssertionError):
            grid_chain.check_scene_limits(21, 30)
        with self.assertRaises(AssertionError):
            grid_chain.check_scene_limits(20, 31)

    def test_grid_chain_accepts_one_to_six_lines_only(self):
        self.assertEqual(len(chain([line(i) for i in range(1, 7)]).lines), 6)
        with self.assertRaises(AssertionError):
            chain([line(i) for i in range(1, 8)])


if __name__ == "__main__":
    unittest.main()
