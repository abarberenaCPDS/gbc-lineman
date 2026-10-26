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
    "intro_pole": (intro.POLE_SPRITE_ID, {"Standing": 1, "Snapped": 3}),
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
        self.assertEqual(len(set(pole)), 4)

    def test_palette_slots(self):
        for name, slot in (("intro_rain", "rain"), ("intro_bolt", "bolt"), ("intro_pole", "pole")):
            for s in _meta(name)["states"]:
                for fr in s["animations"][0]["frames"]:
                    for t in fr["tiles"]:
                        self.assertEqual(t["paletteIndex"], intro.SPRITE_SLOTS[slot])


if __name__ == "__main__":
    unittest.main()
