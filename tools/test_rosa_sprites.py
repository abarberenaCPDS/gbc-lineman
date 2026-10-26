"""Rosa, workstation and live arc sprite checks; run with managed Python (Pillow).

    cd tools && "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" -m unittest test_rosa_sprites
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import make_rosa_sprites as mr
import rosa

ROOT = Path(__file__).resolve().parent.parent
SPRITE_DIR = ROOT / "assets" / "sprites"
ROSA = "rosa"
WORKSTATION = "rosa_workstation"
ARC = "live_arc"
NAMES = (ROSA, WORKSTATION, ARC)
TOMAS = "tomas"


def _load(name: str) -> tuple[Image.Image, dict]:
    png = SPRITE_DIR / f"{name}.png"
    meta = json.loads((SPRITE_DIR / f"{name}.png.gbsres").read_text(encoding="utf-8"))
    return Image.open(png).convert("RGBA"), meta


def _frames(image: Image.Image) -> list[bytes]:
    return [
        image.crop((index * 16, 0, (index + 1) * 16, image.height)).tobytes()
        for index in range(image.width // 16)
    ]


def _frame_image(image: Image.Image, index: int) -> Image.Image:
    return image.crop((index * 16, 0, (index + 1) * 16, image.height))


def _state_frame_counts(meta: dict) -> dict:
    return {s["name"]: len(s["animations"][0]["frames"]) for s in meta["states"]}


def _opaque(frame: Image.Image, x: int, y: int) -> bool:
    return frame.getpixel((x, y))[3] != 0


class ContractTests(unittest.TestCase):
    def test_palette_slots_and_hardware_match_contract(self):
        self.assertEqual(rosa.ROSA_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(rosa.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(rosa.ARC_SPRITE_PALETTE_SLOT, 3)
        for hardware in (rosa.ROSA_SPRITE_HARDWARE, rosa.ARC_SPRITE_HARDWARE, mr.GRID_SPRITE_HARDWARE):
            self.assertEqual(len(hardware), 4)
            self.assertEqual(hardware[0], "000000")

    def test_grid_palette_copy_matches_climb_scene(self):
        import make_climb_scene
        self.assertEqual(mr.GRID_SPRITE_HARDWARE, make_climb_scene.GRID_SPRITE_HARDWARE)

    def test_ids_come_from_rosa(self):
        self.assertEqual(rosa.ROSA_SPRITE_ID, rosa.resource_id("sprite:rosa"))
        self.assertEqual(rosa.WORKSTATION_SPRITE_ID, rosa.resource_id("sprite:rosa_workstation"))
        self.assertEqual(rosa.ARC_SPRITE_ID, rosa.resource_id("sprite:live_arc"))
        ids = {rosa.ROSA_SPRITE_ID, rosa.WORKSTATION_SPRITE_ID, rosa.ARC_SPRITE_ID}
        self.assertEqual(len(ids), 3)
        expected = {ROSA: rosa.ROSA_SPRITE_ID, WORKSTATION: rosa.WORKSTATION_SPRITE_ID,
                    ARC: rosa.ARC_SPRITE_ID}
        for name in NAMES:
            _image, meta = _load(name)
            self.assertEqual(meta["id"], expected[name], name)

    def test_identity_names_and_symbols(self):
        for name in NAMES:
            _image, meta = _load(name)
            self.assertEqual(meta["_resourceType"], "sprite")
            self.assertEqual(meta["name"], name)
            self.assertEqual(meta["symbol"], f"sprite_{name}")
            self.assertEqual(meta["filename"], f"{name}.png")
            self.assertEqual(meta["spriteMode"], "8x16")
            self.assertTrue(meta["checksum"])


class StateTests(unittest.TestCase):
    def test_state_names_and_order(self):
        _image, rosa_meta = _load(ROSA)
        _image, ws_meta = _load(WORKSTATION)
        _image, arc_meta = _load(ARC)
        self.assertEqual([s["name"] for s in rosa_meta["states"]], ["Waiting", "Relieved"])
        self.assertEqual([s["name"] for s in rosa_meta["states"]], rosa.ROSA_STATES)
        self.assertEqual([s["name"] for s in ws_meta["states"]], ["Off", "On"])
        self.assertEqual([s["name"] for s in ws_meta["states"]], rosa.WORKSTATION_STATES)
        self.assertEqual([s["name"] for s in arc_meta["states"]], ["Warning", "Arc"])
        self.assertEqual([s["name"] for s in arc_meta["states"]], rosa.ARC_STATES)

    def test_frame_counts(self):
        _image, rosa_meta = _load(ROSA)
        _image, ws_meta = _load(WORKSTATION)
        _image, arc_meta = _load(ARC)
        self.assertEqual(_state_frame_counts(rosa_meta), {"Waiting": 2, "Relieved": 2})
        self.assertEqual(_state_frame_counts(ws_meta), {"Off": 1, "On": 2})
        self.assertEqual(_state_frame_counts(arc_meta), {"Warning": 2, "Arc": 2})

    def test_each_state_has_eight_animation_slots_and_unique_ids(self):
        for name in NAMES:
            _image, meta = _load(name)
            ids = []
            for state in meta["states"]:
                self.assertEqual(len(state["animations"]), 8, name)
                ids.append(state["id"])
                for animation in state["animations"]:
                    ids.append(animation["id"])
                    ids.extend(frame["id"] for frame in animation["frames"])
                    ids.extend(tile["id"] for frame in animation["frames"] for tile in frame["tiles"])
            self.assertEqual(len(ids), len(set(ids)), f"{name} has duplicate resource ids")


class SheetTests(unittest.TestCase):
    def test_sheet_sizes(self):
        expected = {ROSA: (64, 32), WORKSTATION: (48, 16), ARC: (64, 16)}
        for name in NAMES:
            image, meta = _load(name)
            self.assertEqual(image.size, expected[name], name)
            self.assertEqual((meta["width"], meta["height"]), image.size, name)
            self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (16, image.height), name)
            self.assertEqual(image.width % 16, 0, name)

    def test_rosa_idle_frames_differ_within_each_state(self):
        image, _meta = _load(ROSA)
        frames = _frames(image)
        self.assertNotEqual(frames[0], frames[1], "Waiting frames must differ (blink, phone)")
        self.assertNotEqual(frames[2], frames[3], "Relieved frames must differ (wave)")
        self.assertNotEqual(frames[0], frames[2], "Waiting and Relieved must differ")

    def test_workstation_off_and_on_frames_differ(self):
        image, _meta = _load(WORKSTATION)
        off, on_a, on_b = _frames(image)
        self.assertNotEqual(off, on_a)
        self.assertNotEqual(off, on_b)
        self.assertNotEqual(on_a, on_b, "On must blink the router LEDs")

    def test_arc_loop_frames_differ(self):
        image, _meta = _load(ARC)
        warn_a, warn_b, arc_a, arc_b = _frames(image)
        self.assertNotEqual(warn_a, warn_b, "Warning sparks must crackle")
        self.assertNotEqual(arc_a, arc_b, "Arc must animate")
        self.assertNotEqual(warn_a, arc_a)
        self.assertNotEqual(warn_b, arc_b)

    def test_rosa_and_workstation_stand_on_the_shared_feet_row(self):
        for name in (ROSA, WORKSTATION):
            image, _meta = _load(name)
            for index in range(image.width // 16):
                frame = _frame_image(image, index)
                rows = {y for y in range(frame.height) for x in range(16) if _opaque(frame, x, y)}
                self.assertEqual(max(rows), frame.height - 1, f"{name} frame {index} floats off the feet row")

    def test_arc_art_stays_in_the_chest_lane_tile_row(self):
        image, _meta = _load(ARC)
        for index in range(image.width // 16):
            frame = _frame_image(image, index)
            rows = {y for y in range(16) for x in range(16) if _opaque(frame, x, y)}
            self.assertTrue(rows, f"arc frame {index} is empty")
            self.assertGreaterEqual(min(rows), 8, f"arc frame {index} leaves its 8px lane row")
            self.assertLessEqual(max(rows), 15, f"arc frame {index} overflows the canvas")

    def test_arc_lanes_are_two_tiles_wide_on_the_chest_row(self):
        # The 16px arc sprite must match the lane it hits: two tiles wide, on the chest row.
        for row, x0, x1 in rosa.ARC_LANES:
            self.assertEqual(row, rosa.GROUND_ROW - 2)
            self.assertEqual(x1 - x0 + 1, 2)


class PaletteTests(unittest.TestCase):
    def test_tile_palette_indices(self):
        for name, slot in ((ROSA, rosa.ROSA_SPRITE_PALETTE_SLOT),
                           (WORKSTATION, rosa.GRID_SPRITE_PALETTE_SLOT),
                           (ARC, rosa.ARC_SPRITE_PALETTE_SLOT)):
            _image, meta = _load(name)
            tiles = [tile for state in meta["states"] for animation in state["animations"]
                     for frame in animation["frames"] for tile in frame["tiles"]]
            self.assertTrue(tiles, name)
            for tile in tiles:
                self.assertEqual(tile["paletteIndex"], slot, name)
                self.assertEqual(tile["palette"], 0, name)
                self.assertEqual(tile["objPalette"], "OBP0", name)
                # GB Studio tile y counts up from the canvas bottom.
                self.assertEqual(tile["y"], meta["canvasHeight"] - 16 - tile["sliceY"], name)
                self.assertIn(tile["sliceY"], (0, 16), name)

    def test_png_colours_are_restricted_to_proxy_palette(self):
        for name in NAMES:
            image, _meta = _load(name)
            self.assertEqual(image.mode, "RGBA")
            pixels = list(image.get_flattened_data())
            opaque = {pixel for pixel in pixels if pixel[3] != 0}
            self.assertTrue(opaque <= set(mr.PROXY.values()), name)
            self.assertLessEqual(len(opaque), 3, f"{name} must use at most three opaque indices")

    def test_index_zero_is_transparent_background(self):
        for name in NAMES:
            image, _meta = _load(name)
            for index in range(image.width // 16):
                frame = _frame_image(image, index)
                self.assertEqual(frame.getpixel((0, 0))[3], 0, f"{name} frame {index} corner")
                self.assertEqual(frame.getpixel((15, 0))[3], 0, f"{name} frame {index} corner")
            pixels = list(image.get_flattened_data())
            self.assertTrue(any(pixel[3] == 0 for pixel in pixels), f"{name} has no transparency")

    def test_workstation_accent_budget(self):
        image, _meta = _load(WORKSTATION)
        for index, _frame in enumerate(_frames(image)):
            frame = _frame_image(image, index)
            accents = sum(1 for pixel in frame.get_flattened_data() if pixel == mr.PROXY[2])
            self.assertLessEqual(accents, mr.MAX_ACCENT_PIXELS, f"frame {index}")


class BoundsTests(unittest.TestCase):
    def test_bounds_describe_the_art_and_fit_the_canvas(self):
        for name in NAMES:
            image, meta = _load(name)
            xs, ys = [], []
            for y in range(image.height):
                for x in range(image.width):
                    if image.getpixel((x, y))[3]:
                        xs.append(x % 16)
                        ys.append(y)
            self.assertEqual(meta["boundsX"], min(xs), name)
            self.assertEqual(meta["boundsY"], min(ys) - (image.height - 8), name)
            self.assertEqual(meta["boundsWidth"], max(xs) - min(xs) + 1, name)
            self.assertEqual(meta["boundsHeight"], max(ys) - min(ys) + 1, name)
            self.assertGreaterEqual(meta["boundsX"], 0, name)
            self.assertLessEqual(meta["boundsX"] + meta["boundsWidth"], 16, name)
            self.assertGreater(meta["boundsWidth"], 0, name)
            self.assertGreater(meta["boundsHeight"], 0, name)

    def test_arc_bounds_cover_the_lane_footprint(self):
        # Contact in Arc state must reach the walking hero: the box spans the full 16px
        # width (both 8x16 objects) and exactly the one 8px tile row of the chest lane.
        _image, meta = _load(ARC)
        self.assertEqual((meta["boundsX"], meta["boundsWidth"]), (0, 16))
        self.assertEqual((meta["boundsY"], meta["boundsHeight"]), (0, 8))

    def test_rosa_is_a_standing_figure_with_head_room(self):
        # 24px figure on a 16x32 canvas, like opening_worker24 (bounds y -16, height 24).
        _image, meta = _load(ROSA)
        self.assertEqual(meta["canvasHeight"], 32)
        self.assertEqual(meta["boundsY"] + meta["boundsHeight"], 8)
        self.assertEqual((meta["boundsY"], meta["boundsHeight"]), (-16, 24))

    def test_rosa_face_reads_at_1x(self):
        # Eyes are dark pixels on skin; the mouth sits on skin below them.
        image, _meta = _load(ROSA)
        for index in range(4):
            frame = _frame_image(image, index)
            px = lambda x, y: frame.getpixel((x, y))
            self.assertEqual(px(6, 14)[:3], (0, 0, 0), f"frame {index} left eye")
            self.assertEqual(px(9, 14)[:3], (0, 0, 0), f"frame {index} right eye")
            self.assertEqual(px(7, 14)[:3], (255, 255, 255), f"frame {index} skin between eyes")

    def test_checksums_match_png_bytes(self):
        for name in NAMES:
            _image, meta = _load(name)
            png_bytes = (SPRITE_DIR / f"{name}.png").read_bytes()
            self.assertEqual(meta["checksum"], hashlib.sha1(png_bytes).hexdigest(), name)

    def test_tile_slices_stay_inside_sheet(self):
        for name in NAMES:
            image, meta = _load(name)
            for state in meta["states"]:
                for animation in state["animations"]:
                    for frame in animation["frames"]:
                        for tile in frame["tiles"]:
                            self.assertGreaterEqual(tile["sliceX"], 0, name)
                            self.assertLessEqual(tile["sliceX"] + 8, image.width, name)


class DistinctnessTests(unittest.TestCase):
    def test_rosa_silhouette_differs_from_tomas(self):
        rosa_image, _meta = _load(ROSA)
        tomas_image, _tomas_meta = _load(TOMAS)
        for rosa_index, tomas_index in ((0, 0), (2, 2)):
            rosa_mask = _frame_image(rosa_image, rosa_index).crop((0, 16, 16, 32)).getchannel("A")
            tomas_mask = _frame_image(tomas_image, tomas_index).getchannel("A")
            differing = sum(
                1 for y in range(16) for x in range(16)
                if (rosa_mask.getpixel((x, y)) != 0) != (tomas_mask.getpixel((x, y)) != 0)
            )
            self.assertGreaterEqual(differing, 20, f"Rosa frame {rosa_index} too close to Tomás")

    def test_rosa_has_long_hair_and_tomas_does_not(self):
        rosa_image, _meta = _load(ROSA)
        tomas_image, _tomas_meta = _load(TOMAS)
        for index in (0, 2):
            frame = _frame_image(rosa_image, index)
            self.assertTrue(_opaque(frame, 3, 18), f"Rosa frame {index} lacks hair past the jaw")
            self.assertTrue(_opaque(frame, 12, 18), f"Rosa frame {index} lacks hair past the jaw")
            self.assertFalse(_opaque(_frame_image(tomas_image, index), 12, 18),
                             f"Tomás frame {index} should not have hair past the jaw")


class RegenerationTests(unittest.TestCase):
    def test_regeneration_is_deterministic_and_matches_committed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = mr.OUT_DIR
            mr.OUT_DIR = Path(tmp)
            try:
                mr.main()
                first = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
                mr.main()
                second = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            finally:
                mr.OUT_DIR = original
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), sorted(
            f"{name}{ext}" for name in NAMES for ext in (".png", ".png.gbsres")))
        for name in NAMES:
            for ext in (".png", ".png.gbsres"):
                self.assertEqual(first[f"{name}{ext}"], (SPRITE_DIR / f"{name}{ext}").read_bytes(),
                                 f"{name}{ext} is stale; rerun make_rosa_sprites.py")

    def test_ownership_refuses_a_different_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "rosa.png"
            sidecar_path = Path(str(png_path) + ".gbsres")
            png_path.write_bytes(b"placeholder")
            sidecar_path.write_text(json.dumps({"id": "not-ours", "name": ROSA}), encoding="utf-8")
            _name, _image, meta = next(a for a in mr.make_assets() if a[0] == ROSA)
            with self.assertRaises(FileExistsError):
                mr._check_ownership(ROSA, png_path, sidecar_path, meta)

    def test_ownership_refuses_an_unpaired_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "live_arc.png"
            png_path.write_bytes(b"placeholder")
            _name, _image, meta = next(a for a in mr.make_assets() if a[0] == ARC)
            with self.assertRaises(FileExistsError):
                mr._check_ownership(ARC, png_path, Path(str(png_path) + ".gbsres"), meta)


if __name__ == "__main__":
    unittest.main()
