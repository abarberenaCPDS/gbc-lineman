import json
import sys
import unittest
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import intro  # noqa: E402

SPR = TOOLS.parent / "assets" / "sprites"
CASES = {
    "intro_rain": (intro.RAIN_SPRITE_ID, {"Default": 4}),
    "intro_bolt": (intro.BOLT_SPRITE_ID, {"Default": 2}),
    "intro_pole": (intro.POLE_SPRITE_ID,
                   {"Standing": 1, "Snapped+Cable": 3, "Snapped": 3}),
    "intro_hero": (intro.HERO_SPRITE_ID, {s: len(xs) for s, xs in intro.HERO_STATES.items()}),
}


def _meta(name):
    return json.loads((SPR / f"{name}.png.gbsres").read_text())


def _frames(name):
    im = Image.open(SPR / f"{name}.png").convert("RGBA")
    w = _meta(name)["canvasWidth"]
    return [im.crop((x, 0, x + w, im.height)) for x in range(0, im.width, w)]


class IntroSpriteTests(unittest.TestCase):
    def test_ids_sizes_states(self):
        for name, (sid, states) in CASES.items():
            m = _meta(name)
            self.assertEqual(m["id"], sid)
            w, h = intro.SPRITE_SIZES[sid]
            self.assertEqual((m["canvasWidth"], m["canvasHeight"]), (w * 8, h * 8))
            self.assertEqual(m["spriteMode"], "8x16")
            self.assertEqual([s["name"] for s in m["states"]], list(states))
            for s in m["states"]:
                self.assertEqual(len(s["animations"][0]["frames"]), states[s["name"]])
                for fr in s["animations"][0]["frames"]:
                    self.assertTrue(fr["tiles"])
        self.assertEqual([s["name"] for s in _meta("intro_pole")["states"]], intro.POLE_STATES)

    def test_tile_y_counts_up_from_the_canvas_bottom(self):
        # GB Studio convention, as in the approved opening_worker24 sidecar.
        worker = json.loads((SPR / "opening_worker24.png.gbsres").read_text())
        top = [t for t in worker["states"][0]["animations"][0]["frames"][0]["tiles"]
               if t["sliceY"] == 0]
        self.assertTrue(top and all(t["y"] == 16 for t in top))
        for name in CASES:
            m = _meta(name)
            for state in m["states"]:
                for fr in state["animations"][0]["frames"]:
                    for t in fr["tiles"]:
                        self.assertEqual(t["y"], m["canvasHeight"] - 16 - t["sliceY"], name)

    def test_frames_visible_and_sized(self):
        for name, (_, states) in CASES.items():
            frames = _frames(name)
            self.assertEqual(len(frames), sum(states.values()))
            for f in frames:
                self.assertGreaterEqual(sum(1 for p in f.get_flattened_data() if p[3]), 12)

    def test_frames_differ_within_looping_states(self):
        rain = [f.tobytes() for f in _frames("intro_rain")]
        self.assertEqual(len(set(rain)), 4)
        bolt = [f.tobytes() for f in _frames("intro_bolt")]
        self.assertEqual(len(set(bolt)), 2)
        pole = [f.tobytes() for f in _frames("intro_pole")]
        self.assertEqual(len(set(pole)), 7)

    def test_pole_cable_state_has_wire_and_plug(self):
        meta = _meta("intro_pole")
        frames = _frames("intro_pole")
        offsets = {}
        offset = 0
        for state in meta["states"]:
            offsets[state["name"]] = offset
            offset += len(state["animations"][0]["frames"])

        cable_start = offsets["Snapped+Cable"]
        snapped_start = offsets["Snapped"]
        for f in range(3):
            cable = frames[cable_start + f]
            snapped = frames[snapped_start + f]
            self.assertNotEqual(cable.tobytes(), snapped.tobytes())
            # The cable-only pixels are the dangling wire and its plug tip.
            cable_pixels = [
                (x, y) for y in range(7, 18) for x in range(16)
                if cable.getpixel((x, y))[3] and not snapped.getpixel((x, y))[3]
            ]
            self.assertGreaterEqual(len(cable_pixels), 9)
            self.assertTrue(any(y == 16 for _, y in cable_pixels), "missing plug tip")
            self.assertTrue(any(y == 17 for _, y in cable_pixels), "missing plug prongs")

    def test_palette_slots(self):
        for name, slot in (("intro_rain", "rain"), ("intro_bolt", "bolt"), ("intro_pole", "pole")):
            for s in _meta(name)["states"]:
                for fr in s["animations"][0]["frames"]:
                    for t in fr["tiles"]:
                        self.assertEqual(t["paletteIndex"], intro.SPRITE_SLOTS[slot])


if __name__ == "__main__":
    unittest.main()
