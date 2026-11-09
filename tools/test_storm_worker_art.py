"""Native Storm Worker sprite art and gameplay contract."""
import unittest

import make_opening_characters as art


class StormWorkerArtTest(unittest.TestCase):
    def test_jacket_band_and_hat_in_all_normal_poses(self):
        # These pixels are in body-space, after the fixed 8px canvas inset.
        for pose, count in (("idle", 2), ("walk", 4), ("jump", 1),
                            ("repair", 2), ("carry_idle", 2),
                            ("carry_walk", 4), ("carry_jump", 1)):
            for phase in range(count):
                with self.subTest(pose=pose, phase=phase):
                    frame = art._worker_frame(24, pose, "right", phase)
                    self.assertEqual(frame.size, (16, 32))
                    self.assertEqual(frame.getpixel((6, 9)), art.PROXY[1])
                    stripe = [frame.getpixel((x, y)) for y in (20, 21) for x in range(4, 12)]
                    if not pose.startswith("carry_"):
                        self.assertGreaterEqual(stripe.count(art.PROXY[1]), 8)
                    else:
                        # Coil and gripping glove occlude the vest stripe.
                        self.assertGreaterEqual(stripe.count(art.PROXY[1]), 2)
                    boots = [frame.getpixel((x, y)) for y in range(29, 32) for x in range(2, 14)]
                    self.assertGreaterEqual(boots.count(art.PROXY[2]), 4)
                    self.assertLessEqual(set(frame.get_flattened_data()), set(art.PROXY.values()))
                    left = art._worker_frame(24, pose, "left", phase)
                    self.assertEqual(left.tobytes(), frame.transpose(art.Image.Transpose.FLIP_LEFT_RIGHT).tobytes())

    def test_resource_contract(self):
        name, sheet, meta = art._worker_asset("opening_worker24", 24)
        art._validate(name, sheet, meta)
        self.assertEqual([s["name"] for s in meta["states"]],
                         ["Default", "Repair", "Carry", "Shock"])
        self.assertEqual((meta["canvasWidth"], meta["canvasHeight"]), (16, 32))
        self.assertEqual((meta["boundsX"], meta["boundsY"],
                          meta["boundsWidth"], meta["boundsHeight"]), (2, -16, 12, 24))
        self.assertEqual(meta["animSpeed"], 10)
        self.assertEqual([s["animationType"] for s in meta["states"]],
                         ["platform_player", "fixed", "platform_player", "fixed"])
        self.assertEqual(len(meta["states"][3]["animations"][0]["frames"]), 3)


if __name__ == "__main__":
    unittest.main()
