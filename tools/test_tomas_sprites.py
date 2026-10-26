"""Tomás and oxygen concentrator sprite checks; run with managed Python (Pillow).

    cd tools && "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" -m unittest test_tomas_sprites
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import make_tomas_sprites as mt
import ridge

ROOT = Path(__file__).resolve().parent.parent
SPRITE_DIR = ROOT / "assets" / "sprites"
TOMAS = "tomas"
CONCENTRATOR = "oxygen_concentrator"
NAMES = (TOMAS, CONCENTRATOR)


def _load(name: str) -> tuple[Image.Image, dict]:
    png = SPRITE_DIR / f"{name}.png"
    meta = json.loads((SPRITE_DIR / f"{name}.png.gbsres").read_text(encoding="utf-8"))
    return Image.open(png).convert("RGBA"), meta


def _frames(image: Image.Image) -> list[bytes]:
    return [
        image.crop((index * 16, 0, (index + 1) * 16, 16)).tobytes()
        for index in range(image.width // 16)
    ]


def _state_frame_counts(meta: dict) -> dict:
    return {s["name"]: len(s["animations"][0]["frames"]) for s in meta["states"]}


class ContractTests(unittest.TestCase):
    def test_palette_slots_and_hardware_match_contract(self):
        self.assertEqual(ridge.TOMAS_SPRITE_PALETTE_SLOT, 1)
        self.assertEqual(ridge.GRID_SPRITE_PALETTE_SLOT, 2)
        self.assertEqual(len(ridge.TOMAS_SPRITE_HARDWARE), 4)
        self.assertEqual(ridge.TOMAS_SPRITE_HARDWARE[0], "000000")

    def test_grid_palette_copy_matches_climb_scene(self):
        import make_climb_scene
        self.assertEqual(mt.GRID_SPRITE_HARDWARE, make_climb_scene.GRID_SPRITE_HARDWARE)

    def test_ids_come_from_ridge(self):
        self.assertEqual(ridge.TOMAS_SPRITE_ID, ridge.resource_id("sprite:tomas"))
        self.assertEqual(ridge.CONCENTRATOR_SPRITE_ID, ridge.resource_id("sprite:oxygen_concentrator"))
        _image, tomas = _load(TOMAS)
        _image, concentrator = _load(CONCENTRATOR)
        self.assertEqual(tomas["id"], ridge.TOMAS_SPRITE_ID)
        self.assertEqual(concentrator["id"], ridge.CONCENTRATOR_SPRITE_ID)
        self.assertNotEqual(tomas["id"], concentrator["id"])

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
        _image, tomas = _load(TOMAS)
        _image, concentrator = _load(CONCENTRATOR)
        self.assertEqual([s["name"] for s in tomas["states"]], ["Waiting", "Relieved"])
        self.assertEqual([s["name"] for s in tomas["states"]], ridge.TOMAS_STATES)
        self.assertEqual([s["name"] for s in concentrator["states"]], ["Off", "On"])
        self.assertEqual([s["name"] for s in concentrator["states"]], ridge.CONCENTRATOR_STATES)

    def test_frame_counts(self):
        _image, tomas = _load(TOMAS)
        _image, concentrator = _load(CONCENTRATOR)
        self.assertEqual(_state_frame_counts(tomas), {"Waiting": 2, "Relieved": 2})
        self.assertEqual(_state_frame_counts(concentrator), {"Off": 1, "On": 2})

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


class FrameTests(unittest.TestCase):
    def test_sheet_geometry(self):
        for name in NAMES:
            image, meta = _load(name)
            self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (16, 16), name)
            self.assertEqual(image.height, 16, name)
            self.assertEqual(image.width % 16, 0, name)
            self.assertEqual((meta["width"], meta["height"]), image.size, name)

    def test_idle_frames_differ_within_each_state(self):
        image, meta = _load(TOMAS)
        frames = _frames(image)
        self.assertNotEqual(frames[0], frames[1], "Waiting breath frames must differ")
        self.assertNotEqual(frames[2], frames[3], "Relieved bob frames must differ")
        self.assertNotEqual(frames[0], frames[2], "Waiting and Relieved must differ")

    def test_concentrator_off_and_on_frames_differ(self):
        image, _meta = _load(CONCENTRATOR)
        off, on_a, on_b = _frames(image)
        self.assertNotEqual(off, on_a)
        self.assertNotEqual(off, on_b)
        self.assertNotEqual(on_a, on_b, "On must blink")

    def test_all_frames_stand_on_the_shared_feet_row(self):
        for name in NAMES:
            image, _meta = _load(name)
            for index in range(image.width // 16):
                frame = image.crop((index * 16, 0, index * 16 + 16, 16))
                rows = {y for y in range(16) for x in range(16) if frame.getpixel((x, y))[3]}
                self.assertEqual(max(rows), 15, f"{name} frame {index} floats off the feet row")


class PaletteTests(unittest.TestCase):
    def test_tile_palette_indices(self):
        for name, slot in ((TOMAS, ridge.TOMAS_SPRITE_PALETTE_SLOT),
                           (CONCENTRATOR, ridge.GRID_SPRITE_PALETTE_SLOT)):
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
            self.assertTrue(opaque <= set(mt.PROXY.values()), name)
            self.assertLessEqual(len(opaque), 3, f"{name} must use at most three opaque indices")
            self.assertTrue(any(pixel[3] == 0 for pixel in pixels), f"{name} has no transparency")

    def test_concentrator_accent_budget(self):
        image, _meta = _load(CONCENTRATOR)
        for index, frame in enumerate(_frames(image)):
            accents = sum(1 for i in range(0, len(frame), 4)
                          if tuple(frame[i:i + 4]) == mt.PROXY[2])
            self.assertLessEqual(accents, mt.MAX_ACCENT_PIXELS, f"frame {index}")


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

    def test_tomas_is_close_to_marta_framing(self):
        _image, tomas = _load(TOMAS)
        _image, marta = _load_marta()
        self.assertEqual(tomas["boundsY"], marta["boundsY"])
        self.assertEqual(tomas["boundsHeight"], marta["boundsHeight"])
        self.assertLessEqual(abs(tomas["boundsWidth"] - marta["boundsWidth"]), 4)

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


def _load_marta() -> tuple[Image.Image, dict]:
    return _load("opening_marta")


class RegenerationTests(unittest.TestCase):
    def test_regeneration_is_deterministic_and_matches_committed_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = mt.OUT_DIR
            mt.OUT_DIR = Path(tmp)
            try:
                mt.main()
                first = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
                mt.main()
                second = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            finally:
                mt.OUT_DIR = original
        self.assertEqual(first, second)
        self.assertEqual(sorted(first), sorted(
            f"{name}{ext}" for name in NAMES for ext in (".png", ".png.gbsres")))
        for name in NAMES:
            for ext in (".png", ".png.gbsres"):
                self.assertEqual(first[f"{name}{ext}"], (SPRITE_DIR / f"{name}{ext}").read_bytes(),
                                 f"{name}{ext} is stale; rerun make_tomas_sprites.py")

    def test_ownership_refuses_a_different_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "tomas.png"
            sidecar_path = Path(str(png_path) + ".gbsres")
            png_path.write_bytes(b"placeholder")
            sidecar_path.write_text(json.dumps({"id": "not-ours", "name": "tomas"}), encoding="utf-8")
            _name, _image, meta = next(a for a in mt.make_assets() if a[0] == TOMAS)
            with self.assertRaises(FileExistsError):
                mt._check_ownership(TOMAS, png_path, sidecar_path, meta)

    def test_ownership_refuses_an_unpaired_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "oxygen_concentrator.png"
            png_path.write_bytes(b"placeholder")
            _name, _image, meta = next(a for a in mt.make_assets() if a[0] == CONCENTRATOR)
            with self.assertRaises(FileExistsError):
                mt._check_ownership(CONCENTRATOR, png_path, Path(str(png_path) + ".gbsres"), meta)


if __name__ == "__main__":
    unittest.main()
