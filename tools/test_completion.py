"""Focused source and asset checks for the household-completion sting."""

import json
import sys
import wave
from pathlib import Path
import unittest

sys.dont_write_bytecode = True
import completion
import make_sfx


ROOT = Path(__file__).resolve().parent.parent
WAV_PATH = ROOT / "assets" / "sounds" / "home_complete.wav"
SIDECAR_PATH = Path(str(WAV_PATH) + ".gbsres")


class CompletionSoundTests(unittest.TestCase):
    def test_signature_is_short_e_g_b_and_padded(self):
        self.assertEqual([part[1] for part in completion.SEGMENTS if part[0] == "square"],
                         [659, 784, 988])
        data = completion.synth()
        self.assertLessEqual(len(data) / make_sfx.RATE, 0.300)
        self.assertEqual(len(data) % 32, 0)
        self.assertEqual(data, completion.synth())

    def test_asset_format_bytes_and_sidecar_id(self):
        with wave.open(str(WAV_PATH), "rb") as wav:
            self.assertEqual((wav.getnchannels(), wav.getsampwidth(), wav.getframerate()),
                             (1, 1, 8000))
            self.assertEqual(wav.readframes(wav.getnframes()), completion.synth())
            self.assertLessEqual(wav.getnframes() / 8000, 0.300)
        sidecar = json.loads(SIDECAR_PATH.read_text())
        self.assertEqual(sidecar["id"], completion.sound_id())
        self.assertEqual(sidecar["symbol"], "sound_home_complete")
        self.assertEqual(sidecar["filename"], "home_complete.wav")


if __name__ == "__main__":
    unittest.main()
