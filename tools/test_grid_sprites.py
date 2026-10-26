"""Grid-repair sprite checks; run with managed Python (Pillow) after make_grid_sprites.py.

    "$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python" \
        -m unittest discover -s tools -p test_grid_sprites.py
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import climb
import make_grid_sprites as mg

ROOT = Path(__file__).resolve().parent.parent
SPRITE_DIR = ROOT / "assets" / "sprites"
NAMES = ("grid_cable_end", "grid_junction_box", "service_gate")


def _load(name: str) -> tuple[Image.Image, dict]:
    png = SPRITE_DIR / f"{name}.png"
    meta = json.loads((SPRITE_DIR / f"{name}.png.gbsres").read_text(encoding="utf-8"))
    return Image.open(png).convert("RGBA"), meta


def _frames(image: Image.Image, canvas_w: int) -> list[bytes]:
    return [
        image.crop((index * canvas_w, 0, (index + 1) * canvas_w, image.height)).tobytes()
        for index in range(image.width // canvas_w)
    ]


class GridSpriteTests(unittest.TestCase):
    def test_regeneration_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = mg.OUT_DIR
            mg.OUT_DIR = Path(tmp)
            try:
                mg.main()
                first = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
                mg.main()
                second = {p.name: p.read_bytes() for p in Path(tmp).iterdir()}
            finally:
                mg.OUT_DIR = original
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual(first, second)
        for name in NAMES:
            self.assertEqual(first[f"{name}.png"], (SPRITE_DIR / f"{name}.png").read_bytes(),
                             f"{name}.png is stale; rerun make_grid_sprites.py")
            self.assertEqual(first[f"{name}.png.gbsres"],
                             (SPRITE_DIR / f"{name}.png.gbsres").read_bytes(),
                             f"{name}.png.gbsres is stale; rerun make_grid_sprites.py")

    def test_identity_uses_climb_grid_namespace_and_slot(self):
        for name in NAMES:
            _image, meta = _load(name)
            self.assertEqual(meta["id"], climb.grid_resource_id(f"sprite:{name}"))
            self.assertEqual(meta["name"], name)
            self.assertEqual(meta["symbol"], f"sprite_{name}")
            self.assertEqual(meta["_resourceType"], "sprite")
            self.assertEqual(meta["spriteMode"], "8x16")
            for state in meta["states"]:
                self.assertEqual(state["id"], climb.grid_resource_id(f"{name}:state:"
                                 f"{meta['states'].index(state)}"))
                for animation in state["animations"]:
                    for frame in animation["frames"]:
                        for tile in frame["tiles"]:
                            self.assertEqual(tile["paletteIndex"], climb.GRID_SPRITE_PALETTE_SLOT)
                            self.assertEqual(tile["palette"], 0)
                            self.assertEqual(tile["objPalette"], "OBP0")
                            self.assertTrue(tile["id"])

    def test_states_frames_and_dimensions(self):
        expected = {
            "grid_cable_end": ((16, 16), {"Dangling": 2}),
            "grid_junction_box": ((16, 16), {"Dead": 1, "Live": 2}),
            "service_gate": ((16, 32), {"Closed": 1, "Open": 1}),
        }
        for name, ((width, height), states) in expected.items():
            image, meta = _load(name)
            self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (width, height), name)
            self.assertEqual(image.height, height, name)
            self.assertEqual(image.width % width, 0, name)
            self.assertEqual((meta["width"], meta["height"]), image.size, name)
            # Frame count of each state's first (playing) animation slot.
            self.assertEqual(
                {s["name"]: len(s["animations"][0]["frames"]) for s in meta["states"]},
                states, name)
            self.assertEqual(image.width // width, sum(states.values()), name)

    def test_png_is_rgba_with_native_transparency_and_three_colors(self):
        for name in NAMES:
            image, _meta = _load(name)
            self.assertEqual(image.mode, "RGBA")
            pixels = list(image.get_flattened_data())
            opaque = {p for p in pixels if p[3] != 0}
            self.assertTrue(opaque <= set(mg.PROXY.values()), name)
            self.assertLessEqual(len(opaque), 3, name)
            self.assertTrue(any(p[3] == 0 for p in pixels), f"{name} has no transparency")

    def test_frames_are_distinct_where_states_need_it(self):
        image, _ = _load("grid_cable_end")
        cable = _frames(image, 16)
        self.assertNotEqual(cable[0], cable[1])
        image, _ = _load("grid_junction_box")
        dead, live_a, live_b = _frames(image, 16)
        self.assertEqual(len({dead, live_a, live_b}), 3)
        image, _ = _load("service_gate")
        closed, opened = _frames(image, 16)
        self.assertNotEqual(closed, opened)

    def test_bounds_describe_the_art_and_checksums_match(self):
        for name in NAMES:
            image, meta = _load(name)
            canvas_h = meta["canvasHeight"]
            xs, ys = [], []
            for y in range(image.height):
                for x in range(image.width):
                    if image.getpixel((x, y))[3] != 0:
                        xs.append(x % meta["canvasWidth"])
                        ys.append(y)
            origin = canvas_h - 8
            self.assertEqual(meta["boundsX"], min(xs), name)
            self.assertEqual(meta["boundsY"], min(ys) - origin, name)
            self.assertEqual(meta["boundsWidth"], max(xs) - min(xs) + 1, name)
            self.assertEqual(meta["boundsHeight"], max(ys) - min(ys) + 1, name)
            png_bytes = (SPRITE_DIR / f"{name}.png").read_bytes()
            self.assertEqual(meta["checksum"], hashlib.sha1(png_bytes).hexdigest(), name)

    def test_gate_is_full_body_and_cable_and_box_are_tight(self):
        _image, gate = _load("service_gate")
        self.assertEqual((gate["boundsX"], gate["boundsWidth"]), (0, 16))
        self.assertEqual((gate["boundsY"], gate["boundsHeight"]), (-16, 24))
        _image, cable = _load("grid_cable_end")
        self.assertGreater(cable["boundsWidth"], 0)
        self.assertLess(cable["boundsWidth"] * cable["boundsHeight"], 16 * 16)
        _image, box = _load("grid_junction_box")
        self.assertLess(box["boundsWidth"] * box["boundsHeight"], 16 * 16)

    def test_ownership_refuses_a_different_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "service_gate.png"
            sidecar_path = Path(str(png_path) + ".gbsres")
            png_path.write_bytes(b"placeholder")
            sidecar_path.write_text(json.dumps({"id": "not-ours", "name": "service_gate"}),
                                    encoding="utf-8")
            _name, _image, meta = next(a for a in mg.make_assets() if a[0] == "service_gate")
            with self.assertRaises(FileExistsError):
                mg._check_ownership("service_gate", png_path, sidecar_path, meta)

    def test_ownership_refuses_unpaired_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            png_path = Path(tmp) / "grid_cable_end.png"
            sidecar_path = Path(str(png_path) + ".gbsres")
            png_path.write_bytes(b"placeholder")
            _name, _image, meta = next(a for a in mg.make_assets() if a[0] == "grid_cable_end")
            with self.assertRaises(FileExistsError):
                mg._check_ownership("grid_cable_end", png_path, sidecar_path, meta)


if __name__ == "__main__":
    unittest.main()
