#!/usr/bin/env python3
"""Refine the owned pickup/place/sparkle SFX without changing asset IDs.

The existing pipeline writes mono unsigned 8-bit WAV at 8000 Hz and pads to
32 samples.  These compact, lower-level two/three-part gestures leave room for
gameplay and remain suitable for GB Studio's 4-bit conversion.
"""
import json
import random
import sys
import wave
from pathlib import Path

sys.dont_write_bytecode = True
import make_sfx

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "assets" / "sounds"
REFINED_SFX = {
    # Short separated tones avoid the old single, hard rising chirp.
    "pickup": [("square", 784, 1047, 0.035, 0.40),
               ("silence", 0, 0, 0.012, 0.0),
               ("square", 1319, 1568, 0.045, 0.36)],
    # A quiet impact plus a falling settle makes placement tangible, not harsh.
    "place": [("noise", 0, 0, 0.012, 0.18),
              ("square", 523, 392, 0.050, 0.38),
              ("silence", 0, 0, 0.010, 0.0)],
    # Three small, separated pings read as a sparkle without a long ring.
    "sparkle": [("square", 1047, 1047, 0.024, 0.34),
                ("silence", 0, 0, 0.008, 0.0),
                ("square", 1319, 1319, 0.024, 0.36),
                ("silence", 0, 0, 0.008, 0.0),
                ("square", 1568, 1568, 0.042, 0.38)],
}
EXPECTED_IDS = {
    "pickup": "09e8b512-afe8-5b4a-a5b1-c53609e43ad6",
    "place": "65c37f2f-2624-54f4-8b2a-392b556aa3a1",
    "sparkle": "ffd6649b-80cd-5798-81ad-0f02363581fa",
}


def check_existing(name):
    path = SOUNDS / f"{name}.wav"
    sidecar = Path(str(path) + ".gbsres")
    if not path.is_file() or not sidecar.is_file():
        raise FileNotFoundError(f"the existing {name} WAV and sidecar are required")
    with wave.open(str(path), "rb") as wav:
        actual = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
        if actual != (1, 1, make_sfx.RATE):
            raise ValueError(f"existing {name} format {actual} != mono/8-bit/{make_sfx.RATE} Hz")
        frames = wav.getnframes()
    resource = json.loads(sidecar.read_text())
    if (resource.get("_resourceType") != "sound" or resource.get("type") != "wav"
            or resource.get("filename") != f"{name}.wav" or resource.get("id") != EXPECTED_IDS[name]):
        raise ValueError(f"existing {name} sidecar does not match the owned project asset")
    print(f"verified assets/sounds/{name}.wav ({frames / make_sfx.RATE:.3f} s, mono/8-bit/8000 Hz; id preserved)")


def write_refined(name, segments):
    wav_path = SOUNDS / f"{name}.wav"
    check_existing(name)
    data = make_sfx.synth(segments)
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(make_sfx.RATE)
        wav.writeframes(data)
    print(f"refined assets/sounds/{name}.wav ({len(data) / make_sfx.RATE:.3f} s; sidecar untouched)")


def main():
    SOUNDS.mkdir(parents=True, exist_ok=True)
    random.seed(1)
    for name, segments in REFINED_SFX.items():
        write_refined(name, segments)
    print("GB Studio build reduces the 8-bit source samples to 4-bit playback.")


if __name__ == "__main__":
    main()
