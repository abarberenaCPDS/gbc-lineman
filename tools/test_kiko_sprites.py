"""Kiko and the family's stove sprite checks; run with managed Python (Pillow).

    cd tools && "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" -m unittest test_kiko_sprites
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import make_kiko_sprites as mk
import kiko
import ridge
import rosa

ROOT = Path(__file__).resolve().parent.parent
SPRITE_DIR = ROOT / "assets" / "sprites"
KIKO = "kiko"
STOVE = "kiko_stove"
NAMES = (KIKO, STOVE)
TOMAS = "tomas"
ROSA = "rosa"


def _load(name: str) -> tuple[Image.Image, dict]:
    png = SPRITE_DIR / f"{name}.png"
    meta = json.loads((SPRITE_DIR / f"{name}.png.gbsres").read_text(encoding="utf-8"))
    return Image.open(png).convert("RGBA"), meta


def _frames(image: Image.Image) -> list[bytes]:
    return [
        image.crop((index * 16, 0, (index + 1) * 16, 16)).tobytes()
        for index in range(image.width // 16)
    ]


def _frame_image(image: Image.Image, index: int) -> Image.Image:
    return image.crop((index * 16, 0, (index + 1) * 16, 16))


def _state_frame_counts(meta: dict) -> dict:
    return {s["name"]: len(s["animations"][0]["frames"]) for s in meta["states"]}


def _opaque(frame: Image.Image, x: int, y: int) -> bool:
    return frame.getpixel((x, y))[3] != 0


def _opaque_rows(frame: Image.Image) -> set[int]:
    return {y for y in range(16) for x in range(16) if _opaque(frame, x, y)}


class ContractTests(unittest.TestCase):
    def test_palette_slots_and_hardware_match_contract(self):
        self.assertEqual(kiko.KIKO_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(kiko.GRID_SPRITE_PALETTE_SLOT, 2)
        for hardware in (kiko.KIKO_SPRITE_HARDWARE, mk.GRID_SPRITE_HARDWARE):
            self.assertEqual(len(hardware), 4)
            self.assertEqual(hardware[0], "000000")
        self.assertEqual(kiko.KIKO_SPRITE_HARDWARE, ["000000", "D9A97E", "E0A82E", "2B2420"])

    def test_grid_palette_copy_matches_climb_scene(self):
        import make_climb_scene
        self.assertEqual(mk.GRID_SPRITE_HARDWARE, make_climb_scene.GRID_SPRITE_HARDWARE)

    def test_kiko_palette_is_distinct_from_the_other_villagers(self):
        self.assertNotEqual(kiko.KIKO_SPRITE_HARDWARE, rosa.ROSA_SPRITE_HARDWARE)
        self.assertNotEqual(kiko.KIKO_SPRITE_HARDWARE, ridge.TOMAS_SPRITE_HARDWARE)
        self.assertNotEqual(kiko.KIKO_SPRITE_HARDWARE[2], rosa.ROSA_SPRITE_HARDWARE[2],
                            "Kiko's mustard jacket must not read as Rosa's cardigan")
        self.assertNotEqual(kiko.KIKO_SPRITE_HARDWARE[2], ridge.TOMAS_SPRITE_HARDWARE[2],
                            "Kiko's mustard jacket must not read as Tomás's cardigan")

    def test_ids_come_from_kiko(self):
        self.assertEqual(kiko.KIKO_SPRITE_ID, kiko.resource_id("sprite:kiko"))
        self.assertEqual(kiko.STOVE_SPRITE_ID, kiko.resource_id("sprite:kiko_stove"))
        self.assertNotEqual(kiko.KIKO_SPRITE_ID, kiko.STOVE_SPRITE_ID)
        expected = {KIKO: kiko.KIKO_SPRITE_ID, STOVE: kiko.STOVE_SPRITE_ID}
        for name in NAMES:
            _image, meta = _load(name)
            self.assertEqual(meta["id"], expected[name], name)

    def test_sprite_ids_do_not_collide_with_other_jobs(self):
        other = {rosa.ROSA_SPRITE_ID, rosa.WORKSTATION_SPRITE_ID, rosa.ARC_SPRITE_ID,
                 ridge.TOMAS_SPRITE_ID, ridge.CONCENTRATOR_SPRITE_ID}
        self.assertTrue({kiko.KIKO_SPRITE_ID, kiko.STOVE_SPRITE_ID}.isdisjoint(other))

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
        _image, kiko_meta = _load(KIKO)
        _image, stove_meta = _load(STOVE)
        self.assertEqual([s["name"] for s in kiko_meta["states"]], ["Waiting", "Relieved"])
        self.assertEqual([s["name"] for s in kiko_meta["states"]], kiko.KIKO_STATES)
        self.assertEqual([s["name"] for s in stove_meta["states"]], ["Off", "On"])
        self.assertEqual([s["name"] for s in stove_meta["states"]], kiko.STOVE_STATES)

    def test_frame_counts(self):
        _image, kiko_meta = _load(KIKO)
        _image, stove_meta = _load(STOVE)
        self.assertEqual(_state_frame_counts(kiko_meta), {"Waiting": 2, "Relieved": 2})
        self.assertEqual(_state_frame_counts(stove_meta), {"Off": 1, "On": 2})

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
        expected = {KIKO: (64, 16), STOVE: (48, 16)}
        for name in NAMES:
            image, meta = _load(name)
            self.assertEqual(image.size, expected[name], name)
            self.assertEqual((meta["width"], meta["height"]), image.size, name)
            self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (16, 16), name)
            self.assertEqual(image.width % 16, 0, name)

    def test_kiko_idle_frames_differ_within_each_state(self):
        image, _meta = _load(KIKO)
        frames = _frames(image)
        self.assertNotEqual(frames[0], frames[1], "Waiting frames must differ (blink, bowl shake)")
        self.assertNotEqual(frames[2], frames[3], "Relieved frames must differ (blink, lifted foot)")
        self.assertNotEqual(frames[0], frames[2], "Waiting and Relieved must differ")

    def test_stove_off_and_on_frames_differ(self):
        image, _meta = _load(STOVE)
        off, on_a, on_b = _frames(image)
        self.assertNotEqual(off, on_a)
        self.assertNotEqual(off, on_b)
        self.assertNotEqual(on_a, on_b, "On must alternate the glowing burner and the steam")

    def test_stove_off_is_cold_and_on_glows(self):
        image, _meta = _load(STOVE)
        off = _frame_image(image, 0)
        self.assertFalse(any(pixel == mk.PROXY[2] for pixel in off.get_flattened_data()),
                         "Off must have no glow or steam")
        for index in (1, 2):
            frame = _frame_image(image, index)
            self.assertTrue(any(pixel == mk.PROXY[2] for pixel in frame.get_flattened_data()),
                            f"On frame {index - 1} needs a glowing burner or steam")

    def test_feet_stand_on_the_shared_feet_row(self):
        for name in NAMES:
            image, _meta = _load(name)
            for index in range(image.width // 16):
                rows = _opaque_rows(_frame_image(image, index))
                self.assertEqual(max(rows), 15, f"{name} frame {index} floats off the feet row")

    def test_kiko_is_a_child_with_a_lower_head_and_shorter_body(self):
        kiko_image, _meta = _load(KIKO)
        tomas_image, _ = _load(TOMAS)
        rosa_image, _ = _load(ROSA)
        for index in (0, 1):  # Waiting frames: the bowl does not raise the head line
            kiko_rows = _opaque_rows(_frame_image(kiko_image, index))
            tomas_rows = _opaque_rows(_frame_image(tomas_image, index))
            rosa_rows = _opaque_rows(_frame_image(rosa_image, index))
            self.assertGreater(min(kiko_rows), min(tomas_rows), "Kiko's head must sit lower than Tomás's")
            self.assertGreater(min(kiko_rows), min(rosa_rows), "Kiko's head must sit lower than Rosa's")
            self.assertLess(max(kiko_rows) - min(kiko_rows), max(tomas_rows) - min(tomas_rows),
                            "Kiko must be shorter than Tomás")
            self.assertLess(max(kiko_rows) - min(kiko_rows), max(rosa_rows) - min(rosa_rows),
                            "Kiko must be shorter than Rosa")

    def test_relieved_bowl_is_raised_above_the_head_line(self):
        image, _meta = _load(KIKO)
        for index in (2, 3):
            rows = _opaque_rows(_frame_image(image, index))
            self.assertLessEqual(min(rows), 1, f"Relieved frame {index} must raise the bowl")


class PaletteTests(unittest.TestCase):
    def test_tile_palette_indices(self):
        for name, slot in ((KIKO, kiko.KIKO_SPRITE_PALETTE_SLOT),
                           (STOVE, kiko.GRID_SPRITE_PALETTE_SLOT)):
            _image, meta = _load(name)
            tiles = [tile for state in meta["states"] for animation in state["animations"]
                     for frame in animation["frames"] for tile in frame["tiles"]]
            self.assertTrue(tiles, name)
            for tile in tiles:
                self.assertEqual(tile["paletteIndex"], slot, name)
                self.assertEqual(tile["palette"], 0, name)
                self.assertEqual(tile["objPalette"], "OBP0", name)
                self.assertEqual(tile["y"], 0, name)
                self.assertEqual(tile["sliceY"], 0, name)

    def test_png_colours_are_restricted_to_proxy_palette(self):
        for name in NAMES:
            image, _meta = _load(name)
            self.assertEqual(image.mode, "RGBA")
            pixels = list(image.get_flattened_data())
            opaque = {pixel for pixel in pixels if pixel[3] != 0}
            self.assertTrue(opaque <= set(mk.PROXY.values()), name)
            self.assertLessEqual(len(opaque), 3, f"{name} must use at most three opaque indices")

    def test_index_zero_is_transparent_background(self):
        for name in NAMES:
            image, _meta = _load(name)
            for index in range(image.width // 16):
                frame = _frame_image(image, index)
                self.assertEqual(frame.getpixel((0, 15))[3], 0, f"{name} frame {index} corner")
                self.assertEqual(frame.getpixel((15, 15))[3], 0, f"{name} frame {index} corner")
            pixels = list(image.get_flattened_data())
            self.assertTrue(any(pixel[3] == 0 for pixel in pixels), f"{name} has no transparency")

    def test_stove_accent_budget(self):
        image, _meta = _load(STOVE)
        for index, _frame in enumerate(_frames(image)):
            frame = _frame_image(image, index)
            accents = sum(1 for pixel in frame.get_flattened_data() if pixel == mk.PROXY[2])
            self.assertLessEqual(accents, mk.MAX_ACCENT_PIXELS, f"frame {index}")


class BoundsTests(unittest.TestCase):
    def test_bounds_describe_the_art_and_fit_the_canvas(self):
        for name in NAMES:
            image, meta = _load(name)
            xs, ys = [], []
            for y in range(16):
                for x in range(image.width):
                    if image.getpixel((x, y))[3]:
                        xs.append(x % 16)
                        ys.append(y)
            self.assertEqual(meta["boundsX"], min(xs), name)
            self.assertEqual(meta["boundsY"], min(ys) - 8, name)
            self.assertEqual(meta["boundsWidth"], max(xs) - min(xs) + 1, name)
            self.assertEqual(meta["boundsHeight"], max(ys) - min(ys) + 1, name)
            self.assertGreaterEqual(meta["boundsX"], 0, name)
            self.assertLessEqual(meta["boundsX"] + meta["boundsWidth"], 16, name)
            self.assertGreater(meta["boundsWidth"], 0, name)
            self.assertGreater(meta["boundsHeight"], 0, name)

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
    def _differing_pixels(self, first: Image.Image, second: Image.Image) -> int:
        first_mask = first.getchannel("A")
        second_mask = second.getchannel("A")
        return sum(
            1 for y in range(16) for x in range(16)
            if (first_mask.getpixel((x, y)) != 0) != (second_mask.getpixel((x, y)) != 0)
        )

    def test_kiko_silhouette_differs_from_tomas_and_rosa(self):
        kiko_image, _meta = _load(KIKO)
        for other_name in (TOMAS, ROSA):
            other_image, _other_meta = _load(other_name)
            for index in (0, 2):
                differing = self._differing_pixels(
                    _frame_image(kiko_image, index), _frame_image(other_image, index))
                self.assertGreaterEqual(differing, 20,
                                        f"Kiko frame {index} too close to {other_name}")



class RegenerationTests(unittest.TestCase):
    def test_regeneration_is_deterministic_and_matches_committed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = mk.OUT_DIR
            mk.OUT_DIR = Path(tmp)
            try:
                mk.main()
                first = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
                mk.main()
                second = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            finally:
                mk.OUT_DIR = original
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), sorted(
            f"{name}{ext}" for name in NAMES for ext in (".png", ".png.gbsres")))
        for name in NAMES:
            for ext in (".png", ".png.gbsres"):
                self.assertEqual(first[f"{name}{ext}"], (SPRITE_DIR / f"{name}{ext}").read_bytes(),
                                 f"{name}{ext} is stale; rerun make_kiko_sprites.py")

    def test_ownership_refuses_a_different_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "kiko.png"
            sidecar_path = Path(str(png_path) + ".gbsres")
            png_path.write_bytes(b"placeholder")
            sidecar_path.write_text(json.dumps({"id": "not-ours", "name": KIKO}), encoding="utf-8")
            _name, _image, meta = next(a for a in mk.make_assets() if a[0] == KIKO)
            with self.assertRaises(FileExistsError):
                mk._check_ownership(KIKO, png_path, sidecar_path, meta)

    def test_ownership_refuses_an_unpaired_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "kiko_stove.png"
            png_path.write_bytes(b"placeholder")
            _name, _image, meta = next(a for a in mk.make_assets() if a[0] == STOVE)
            with self.assertRaises(FileExistsError):
                mk._check_ownership(STOVE, png_path, Path(str(png_path) + ".gbsres"), meta)


if __name__ == "__main__":
    unittest.main()
