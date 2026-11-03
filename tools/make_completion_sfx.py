#!/usr/bin/env python3
"""Generate the deterministic household-completion WAV and GB Studio sidecar.

Run with ``python3 tools/make_completion_sfx.py``. The WAV is mono unsigned
8-bit at 8000 Hz, padded to 32 samples, and under 300 ms. Existing paired
assets are regenerated only after their sidecar is verified as generator-owned.
"""

import json
import sys
import wave
from pathlib import Path

sys.dont_write_bytecode = True
import completion
import make_sfx


ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "assets" / "sounds"
NAME = completion.NAME
WAV_PATH = SOUNDS / f"{NAME}.wav"
SIDECAR_PATH = Path(str(WAV_PATH) + ".gbsres")


def validate_sidecar():
    if not SIDECAR_PATH.is_file():
        raise FileNotFoundError(f"owned sidecar is missing: {SIDECAR_PATH}")
    resource = json.loads(SIDECAR_PATH.read_text())
    expected = {
        "_resourceType": "sound",
        "id": completion.sound_id(),
        "name": NAME,
        "symbol": f"sound_{NAME}",
        "filename": f"{NAME}.wav",
        "type": "wav",
    }
    if resource != expected:
        raise ValueError(f"existing {NAME} sidecar does not match the generator-owned resource")


def write_sidecar():
    SIDECAR_PATH.write_text(json.dumps({
        "_resourceType": "sound",
        "id": completion.sound_id(),
        "name": NAME,
        "symbol": f"sound_{NAME}",
        "filename": f"{NAME}.wav",
        "type": "wav",
    }, indent=2) + "\n")


def generate():
    SOUNDS.mkdir(parents=True, exist_ok=True)
    wav_exists, sidecar_exists = WAV_PATH.exists(), SIDECAR_PATH.exists()
    if wav_exists != sidecar_exists:
        raise FileExistsError("refusing partial home_complete asset; inspect WAV and sidecar first")
    if sidecar_exists:
        validate_sidecar()
    data = completion.synth()
    if len(data) / make_sfx.RATE > 0.300 or len(data) % 32:
        raise ValueError("home_complete duration/padding is outside its source contract")
    with wave.open(str(WAV_PATH), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(1)
        wav.setframerate(make_sfx.RATE)
        wav.writeframes(data)
    if not sidecar_exists:
        write_sidecar()
    return len(data) / make_sfx.RATE


if __name__ == "__main__":
    print(f"wrote assets/sounds/{NAME}.wav ({generate():.3f} s) + verified sidecar")
