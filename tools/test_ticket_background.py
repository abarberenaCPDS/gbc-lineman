import json
import unittest

from PIL import Image

import intro
import make_ticket_art as art
import tickets


class TicketBackgroundTests(unittest.TestCase):
    def setUp(self):
        self.card = art.build()

    def test_size_and_sidecar(self):
        png = art.BG_DIR / "ticket_card.png"
        self.assertEqual(Image.open(png).size, (160, 144))
        side = json.loads((png.parent / "ticket_card.png.gbsres").read_text())
        self.assertEqual(side["id"], tickets.BACKGROUND_ID)
        self.assertEqual((side["width"], side["height"]), (20, 18))

    def test_palette_slots(self):
        ids = art.BACKGROUND_PALETTE_IDS
        self.assertEqual(len(ids), 8)
        self.assertEqual(ids[-1], "default-ui")
        for n in art.BACKGROUND_PALETTE_NAMES[:7]:
            self.assertIn(n, intro.BG_PALETTES)
        used = {s for row in self.card.slots for s in row}
        self.assertTrue(used <= set(range(8)))
        self.assertTrue(all(s == art.UI_SLOT for row in self.card.slots[art.CARD_ROWS:] for s in row))

    def test_dialogue_rows_cheap(self):
        self.assertEqual(art.unique_tiles(self.card, range(art.CARD_ROWS, art.MAP_H)), 1)
        self.assertLess(art.unique_tiles(self.card), 150)

    def test_matches_committed(self):
        png = Image.open(art.BG_DIR / "ticket_card.png").convert("RGB")
        self.assertEqual(list(png.getdata()), list(self.card.proxy().getdata()))
        side = json.loads((art.BG_DIR / "ticket_card.png.gbsres").read_text())
        from make_climb_scene import collision_rle
        self.assertEqual(side["tileColors"], collision_rle(self.card.slots, 20, 18))


if __name__ == "__main__":
    unittest.main()
