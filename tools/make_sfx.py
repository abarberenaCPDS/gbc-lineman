#!/usr/bin/env python3
"""Repeatable SFX generator for Mister CFE (gb-mr-cfe).

Writes 8-bit mono 8000 Hz WAVs + GB Studio sound sidecars under assets/sounds/:
    jump, death, connect, cut, pickup, victory

Pipeline: docs/500-music-and-sfx.md "Generator: synthesize WAV SFX (stdlib Python)"
- WAV: 8-bit mono, 8000 Hz (device plays at 8192 Hz, so pitches are pre-scaled
  by RATE/DEVICE = 8000/8192 so they sound true on hardware [field:FN-09])
- Samples reduced to 4 bits at build time; length padded to a multiple of 32
  samples; effects kept under 0.5 s so channel-3 dropouts are brief
- Deterministic: fixed namespace + uuid5 ids, seeded noise; re-running is
  byte-identical and never breaks references
- Sidecar: _resourceType sound, type "wav", stable symbol (referenced by
  EVENT_SOUND_PLAY_EFFECT; an unknown sound id plays nothing)

Does not touch scenes, settings, art or tools/level.py. Does not overwrite
existing assets (refuses if a target already exists).
"""
import json
import random
import uuid
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOUNDS = ROOT / "assets" / "sounds"

RATE = 8000      # WAV sample rate (GB Studio resamples other rates to 8000 [L-47])
DEVICE = 8192    # hardware playback rate: pre-scale pitches by RATE/DEVICE (FN-09)
SCALE = RATE / DEVICE
NS = uuid.UUID("7e3a9c1f-4b2d-4a8e-9f0c-123456789abc")  # fixed namespace per game

SFX = [
    # name, segments: (kind, start_hz, end_hz, seconds, volume 0..1)
    # kind: "square" | "noise" | "silence"
    ("jump", [("square", 554, 1109, 0.11, 0.70)]),                                      # bright upward leap
    ("death", [("noise", 0, 0, 0.16, 0.60), ("square", 220, 110, 0.14, 0.50)]),         # hit + falling tone
    ("connect", [("square", 880, 880, 0.06, 0.65), ("silence", 0, 0, 0.04, 0.0),
                 ("square", 1047, 1047, 0.10, 0.65)]),                                  # two-note "power restored"
    ("cut", [("noise", 0, 0, 0.04, 0.70), ("square", 1175, 587, 0.06, 0.60)]),          # sharp snap
    ("pickup", [("square", 784, 1047, 0.10, 0.60)]),                                    # rising chirp
    ("shock", [("noise", 0, 0, 0.10, 0.70), ("square", 1500, 600, 0.06, 0.70),
               ("square", 700, 1600, 0.06, 0.70), ("noise", 0, 0, 0.06, 0.60),
               ("square", 1400, 400, 0.12, 0.60)]),                                 # crackling electric zap
    ("victory", [("square", 523, 523, 0.08, 0.70), ("square", 659, 659, 0.08, 0.70),
                 ("square", 784, 784, 0.08, 0.70), ("square", 1047, 1047, 0.16, 0.70)]), # C-E-G-C fanfare
]


def synth(segments):
    out, phase = bytearray(), 0.0
    for kind, f0, f1, secs, vol in segments:
        n = int(RATE * secs)
        for i in range(n):
            f = (f0 + (f1 - f0) * i / max(n - 1, 1)) * SCALE
            if kind == "square":
                s = 1 if (phase % 1.0) < 0.5 else -1
            elif kind == "noise":
                s = random.choice((-1, 1))
            else:  # silence
                s = 0
            phase = (phase + f / RATE) % 1.0
            env = 1 - i / n if n else 0                                # linear decay per segment
            out.append(int(128 + 127 * vol * env * s))                 # unsigned 8-bit, silence = 128
    out += bytes([128]) * (-len(out) % 32)                              # pad to a multiple of 32 samples
    return bytes(out)


def write_sfx(name, segments):
    wav_path = SOUNDS / f"{name}.wav"
    res_path = SOUNDS / f"{name}.wav.gbsres"
    if wav_path.exists() or res_path.exists():
        raise FileExistsError(f"refusing to overwrite existing asset: {wav_path} / {res_path}")
    data = synth(segments)
    with wave.open(str(wav_path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(RATE)
        w.writeframes(data)
    res_path.write_text(json.dumps({
        "_resourceType": "sound",
        "id": str(uuid.uuid5(NS, f"sound/{name}")),
        "name": name,
        "symbol": f"sound_{name}",
        "filename": f"{name}.wav",
        "type": "wav",
    }, indent=2) + "\n")
    return len(data) / RATE


def main():
    random.seed(1)                                                      # deterministic noise
    total = 0.0
    for name, segments in SFX:
        if (SOUNDS / f"{name}.wav").exists():
            print(f"skip assets/sounds/{name}.wav (exists)")
            continue
        dur = write_sfx(name, segments)
        total += dur
        print(f"wrote assets/sounds/{name}.wav ({dur:.2f} s) + sidecar")
    print(f"total SFX: {len(SFX)} files, {total:.2f} s")


if __name__ == "__main__":
    main()
