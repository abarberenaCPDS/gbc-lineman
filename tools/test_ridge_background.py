"""Wind Ridge background checks; run with managed Python after regeneration."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from PIL import Image

import climb
import intro
import make_ridge_art as art
import opening
import ridge
from test_opening import decode_rle

ROOT = Path(__file__).resolve().parent.parent
BACKGROUND = ROOT / "assets/backgrounds/wind_ridge.png"
SIDECAR = Path(str(BACKGROUND) + ".gbsres")
GRAYS = {255, 170, 85, 0}


class RidgeBackgroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sidecar = json.loads(SIDECAR.read_text(encoding="utf-8"))
        cls.flat_slots = decode_rle(cls.sidecar["tileColors"])
        cls.slots = [cls.flat_slots[row * ridge.MAP_W:(row + 1) * ridge.MAP_W]
                     for row in range(ridge.MAP_H)]
        with Image.open(BACKGROUND) as image:
            cls.proxy = image.convert("RGB")
            cls.image_size = image.size
        cls.grid = ridge.collision_grid()

    def slot(self, tx: int, ty: int) -> int:
        return self.slots[ty][tx]

    def native(self, tx: int, ty: int, x: int, y: int) -> int:
        gray = self.proxy.getpixel((tx * ridge.TILE + x, ty * ridge.TILE + y))[0]
        return art._gb_studio_native_index(gray)

    def test_size_and_sidecar_identity(self):
        self.assertEqual(self.image_size, (800, 240))
        self.assertEqual(self.sidecar["id"], ridge.BACKGROUND_ID)
        self.assertEqual(self.sidecar["name"], "wind_ridge")
        self.assertEqual((self.sidecar["width"], self.sidecar["height"]), (100, 30))
        self.assertEqual((self.sidecar["imageWidth"], self.sidecar["imageHeight"]), (800, 240))
        self.assertFalse(self.sidecar["autoColor"])
        self.assertEqual(len(self.flat_slots), 100 * 30)

    def test_proxy_is_grayscale_native_indices(self):
        pixels = list(self.proxy.get_flattened_data())
        self.assertTrue(all(r == g == b for r, g, b in pixels), "proxy must be grayscale")
        self.assertTrue({r for r, _, _ in pixels} <= GRAYS)

    def test_committed_art_matches_generator(self):
        image, slots = art.make_background()
        self.assertEqual(slots, self.slots, "run tools/make_ridge_art.py to regenerate")
        proxy = art.encode_native_background(image, slots)
        self.assertEqual(proxy.tobytes(), self.proxy.tobytes())

    def test_palette_slots_avoid_ui_and_stay_in_bg_families(self):
        self.assertEqual(len(opening.BG_PALETTES), 7, "slot 7 is reserved for UI")
        self.assertTrue(all(0 <= slot < 7 for slot in self.flat_slots))

    def test_collision_and_art_alignment(self):
        for ty, row in enumerate(self.grid):
            for tx, cell in enumerate(row):
                slot = self.slot(tx, ty)
                if cell == climb.COL_SOLID:
                    self.assertIn(slot, (art.STONE, art.EARTH), f"solid tile {tx},{ty} not rock")
                elif cell == climb.COL_EMPTY:
                    if (ty, tx) in art.PLACARD_CELLS:
                        self.assertEqual(slot, art.STONE)
                    else:
                        self.assertNotIn(slot, (art.STONE, art.EARTH),
                                         f"open air at {tx},{ty} drawn as rock")
                else:
                    self.assertEqual(slot, art.TIMBER, f"one-way tile {tx},{ty} not timber")

    def test_solid_tiles_read_as_rock(self):
        for ty, row in enumerate(self.grid):
            for tx, cell in enumerate(row):
                if cell != climb.COL_SOLID:
                    continue
                body = sum(self.native(tx, ty, x, y) == 1
                           for y in range(ridge.TILE) for x in range(ridge.TILE))
                self.assertGreaterEqual(body, 40, f"rock tile {tx},{ty} is not solid")

    def test_ledges_are_thin_timber_catwalks(self):
        for row, x0, x1 in ridge.LEDGES:
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.slot(tx, row), art.TIMBER)
                self.assertTrue(all(self.native(tx, row, x, 0) == 3 for x in range(ridge.TILE)),
                                f"ledge lip missing at {tx},{row}")
                body = sum(self.native(tx, row, x, y) == 1
                           for y in (2, 3, 4) for x in range(ridge.TILE))
                self.assertGreaterEqual(body, 12, f"ledge body missing at {tx},{row}")

    def metal_pixels(self, index):
        found = set()
        for ty in range(ridge.MAP_H):
            for tx in range(ridge.MAP_W):
                if self.slot(tx, ty) != climb.LINE_BG_SLOT:
                    continue
                for y in range(ridge.TILE):
                    for x in range(ridge.TILE):
                        if self.native(tx, ty, x, y) == index:
                            found.add((tx * ridge.TILE + x, ty * ridge.TILE + y))
        return found

    def test_no_pole_or_transformer_art(self):
        for line in ridge.LINES:
            for x, y in (line["pole"], line["box"]):
                self.assertEqual(self.grid[y][x], climb.COL_EMPTY)
                self.assertNotEqual(self.slot(x, y), art.TIMBER, f"BG stub at {x},{y}")

    def test_metal_indices_belong_to_their_stage_only(self):
        seen = set()
        for stage in (1, 2, 3):
            index = ridge.STAGE_COLOR_INDEX[stage - 1]
            pixels = self.metal_pixels(index)
            self.assertTrue(pixels, f"stage {stage} has no wire")
            self.assertLessEqual(pixels, art.stage_pixels(stage),
                                 f"index {index} off stage {stage} wire")
            self.assertFalse(pixels & seen)
            seen |= pixels
        self.assertEqual(ridge.STAGE_COLOR_INDEX, [1, 3, 2])

    def test_metal_slot_is_wire_only(self):
        wire = art.wire_tiles()
        for ty in range(ridge.MAP_H):
            for tx in range(ridge.MAP_W):
                if self.slot(tx, ty) == climb.LINE_BG_SLOT:
                    self.assertIn((tx, ty), wire, f"non-wire metal tile {tx},{ty}")
                    self.assertEqual(self.grid[ty][tx], climb.COL_EMPTY)
                    self.assertNotIn((ty, tx), art.PLACARD_CELLS)
        # Every open wire tile carries its wire (nothing occluded away).
        for tx, ty in wire:
            if self.grid[ty][tx] == climb.COL_EMPTY:
                self.assertEqual(self.slot(tx, ty), climb.LINE_BG_SLOT, f"gap at {tx},{ty}")

    def wire_cells(self, stage):
        return {(x // ridge.TILE, y // ridge.TILE) for x, y in
                self.metal_pixels(ridge.STAGE_COLOR_INDEX[stage - 1])}

    def test_routes_are_drawn_and_join(self):
        # Every route cell lies in a metal tile whose pixels carry its stage colour
        # (cells inside the left cliff wall are the power entry).
        for stage, route in ridge.WIRE_ROUTES:
            drawn = self.wire_cells(stage)
            for cell in route:
                if self.grid[cell[1]][cell[0]] != climb.COL_EMPTY:
                    self.assertEqual(cell[0], 0)
                    continue
                # A junction cell shared with another stage shows the later colour.
                joint = any(cell in r for s, r in ridge.WIRE_ROUTES if s != stage)
                self.assertTrue(cell in drawn or joint,
                                f"stage {stage} wire missing at {cell}")
        # Consecutive routes share a drawn cell: no visible gap in the chain.
        for (sa, a), (sb, b) in zip(ridge.WIRE_ROUTES, ridge.WIRE_ROUTES[1:]):
            shared = set(a) & set(b)
            self.assertTrue(any(self.slot(x, y) == climb.LINE_BG_SLOT for x, y in shared),
                            f"routes do not join at {shared}")
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        end = ridge.WIRE_ROUTES[-1][1][-1]
        self.assertEqual(end[0], x0)
        self.assertEqual(end[1], y0 - 1, "line 3 ends on the roof")

    def test_fallen_spans_lie_on_the_floor_row(self):
        row = ridge.GROUND_ROW - 1
        arc_cells = {(r, x) for r, x0, x1 in ridge.span_arc_lanes() for x in range(x0, x1 + 1)}
        for span in ridge.FALLEN_SPANS:
            c0, c1 = span["columns"]
            stage = span["live_after"]
            pts = art._span_pixels(span)
            self.assertTrue(pts <= self.metal_pixels(ridge.STAGE_COLOR_INDEX[stage - 1]) | pts)
            drawn = {(x // ridge.TILE, y // ridge.TILE)
                     for x, y in pts & self.metal_pixels(ridge.STAGE_COLOR_INDEX[stage - 1])}
            self.assertEqual({x for x, y in drawn}, set(range(c0, c1 + 1)))
            self.assertEqual({y for x, y in drawn}, {row})
            for x in range(c0, c1 + 1):
                self.assertEqual(self.slot(x, row), climb.LINE_BG_SLOT)
                self.assertNotEqual(self.slot(x, ridge.GROUND_ROW - 2), climb.LINE_BG_SLOT,
                                    "span wire must stay out of the chest-row arc lane")
        self.assertTrue(arc_cells)

    def test_placards_and_brackets_are_stone_not_metal(self):
        for row, tx in art.PLACARD_CELLS:
            self.assertEqual(self.slot(tx, row), art.STONE)
            self.assertEqual(self.grid[row][tx], climb.COL_EMPTY)
        for row, x0, x1 in ridge.WHIP_LANES:
            for tx in range(x0, x1 + 1):
                self.assertIn((row - 2, tx), art.BRACKET_CELLS)
                self.assertIn((row - 3, tx), art.BRACKET_CELLS)
                # The bracket sits just above the 16x32 canvas (rows row-1..row+2).
                self.assertNotIn((row - 1, tx), art.BRACKET_CELLS)

    def test_catwalk_posts_avoid_hazards_and_reach_the_floor(self):
        posts = art._post_tiles(self.grid)
        self.assertTrue(posts)
        for tx, ty in posts:
            self.assertEqual(self.slot(tx, ty), art.TIMBER)
            self.assertNotIn((ty, tx), art.LANE_CELLS)
            self.assertNotIn((tx, ty), art.wire_tiles())
        for tx in art._post_columns():
            self.assertIn((tx, ridge.GROUND_ROW - 1), posts)

    def test_window_slot_belongs_to_house_windows_alone(self):
        lit = {(tx, ty) for ty in range(ridge.MAP_H) for tx in range(ridge.MAP_W)
               if self.slot(tx, ty) == ridge.WINDOW_BG_SLOT}
        self.assertEqual(lit, set(ridge.HOUSE_WINDOWS))
        self.assertEqual(len(ridge.HOUSE_WINDOWS), len(lit), "each window is one tile")
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        for tx, ty in ridge.HOUSE_WINDOWS:
            self.assertTrue(x0 <= tx <= x1 and y0 <= ty <= y1)

    def test_cabin_sits_in_open_air_with_its_door(self):
        x0, x1, y0, y1 = ridge.HOUSE_RECT
        for ty in range(y0, y1 + 1):
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.grid[ty][tx], climb.COL_EMPTY)
        dx, dy = ridge.HOUSE_DOOR
        self.assertTrue(x0 <= dx <= x1 and y0 <= dy <= y1)
        self.assertEqual(self.slot(dx, dy), art.TIMBER)
        # The doorway is dark timber, not a window.
        self.assertTrue(all(self.native(dx, dy, x, 2) == 0 for x in range(2, 6)))

    def test_hazard_lanes_are_open_air_stone_placards(self):
        for row, x0, x1 in ridge.hazard_lanes():
            for tx in range(x0, x1 + 1):
                self.assertEqual(self.grid[row][tx], climb.COL_EMPTY)
                self.assertEqual(self.slot(tx, row), art.STONE)

    def test_sky_has_depth_across_the_width(self):
        # Upper sky (rows 2-9) shows ridge mass or weather in every screen.
        for screen in range(5):
            tiles = {self.proxy.crop((tx * 8, ty * 8, tx * 8 + 8, ty * 8 + 8)).tobytes()
                     for tx in range(screen * 20, screen * 20 + 20) for ty in range(2, 10)}
            self.assertGreaterEqual(len(tiles), 3, f"flat sky on screen {screen}")

    def test_hud_rows_are_plain_sky(self):
        for ty in range(ridge.HUD_ROWS):
            for tx in range(ridge.MAP_W):
                self.assertEqual(self.slot(tx, ty), art.SKY)
                self.assertTrue(all(self.native(tx, ty, x, y) == 0
                                    for y in range(ridge.TILE) for x in range(ridge.TILE)))

    def test_background_tile_budget(self):
        self.assertLessEqual(art._unique_indexed_tiles(self.proxy, self.slots),
                             art.MAX_UNIQUE_TILES)


if __name__ == "__main__":
    unittest.main()
