# Music notes — Mister CFE: After the Storm

## Decoded reference: `Rulz_FastPaceSpeedRace.uge`

Decoded from the supplied v6 file with `tools/uge_report.py`, using the v6
layout in hUGETracker `src/song.pas` / `src/hugedatatypes.pas`. The tracker
tempo formula is `59.7275 VBlank Hz / ticks-per-row / 4 rows-per-beat`: its
6 ticks per row is approximately **149.32 BPM**. There are 16 patterns arranged
as four orders per channel (25.72 seconds per order pass). The four channels
are the usual square 1, square 2, wave and noise, but the wave channel is not a
low bass part here.

- **Square 1 — octave-jumping riff:** 56 note events (2.18/s) across the order pass.
  Repeated F5/F3 (and earlier F#5/F#3, C#5/C#3) pairs jump two octaves between
  alternating hits. Slide-down effects (`2xx`, chiefly `227`/`298`) and a few
  note cuts (`E00`) articulate the line.
- **Square 2 — high arpeggio / hook:** 97 notes (3.77/s), mostly fast repeated chord
  tones. The clearest eight-note phrase, at rows 32–39 of pattern 5 and repeated
  in pattern 9, is **F5–C6–F6–F5–Eb6–C6–Eb6–F6**. A slide-down setup followed
  by the busy phrase and its 16th-note-grid repetition give it a strong racing pulse. There
  are 32 `206` slide-down effect cells before the busy phrase.
- **Wave — upper-register arpeggio ostinato, not conventional bass:** 256
  notes, almost one per row (9.95 note events/s). It cycles
  **F4–C5–F5–F4–Eb5–C5–Eb5–F5**, with a brief G-based variation. It does not
  octave-jump as the square-1 riff does.
- **Noise — drum/rhythm part:** 64 hits (2.49/s). B5-rate hits establish four-row
  quarter-note pulses; D#7-rate hits enter on alternating two-row steps for a
  busier second half, then the ending returns to quarter notes. These note
  numbers are noise frequencies, not pitched melody. Noise instrument 2 has
  volume 11, a downward envelope and a six-step noise macro.

The tonal center is **F**, with a minor/modal color: the hook emphasizes F, C
and Eb, while the accompanying lines add G, Ab and Bb; brief F#/C# notes are
chromatic riff accents. It is safer to describe the complete file as
F-centered minor/Dorian coloring than to claim a single strict scale, since the
octave riff includes those chromatic notes. The texture is dense and
syncopated: rapid repeated arpeggios and noise hits carry the motion, while
the alternating two-octave square riff supplies the distinctive hook. Effects
are mostly slides, note cuts and two `B02` order jumps; no tempo changes.

## Shared motif and new arrangements

All five new source files use 6 ticks per row, the same ~149.32 BPM, and the
same F-centered minor/Dorian pitch language. The core village hook is the
reference's eight-note phrase:

> **F5 – C6 – F6 – F5 – Eb6 – C6 – Eb6 – F6**
> Intervals: **+7, +5, −7, +10, −3, +3, +2 semitones**.

The three village loops each have three 64-row sections (about **19.29 seconds**
per loop). A hook phrase occupies rows 0–14 and uses a note cut on row 15, so
the answer or rest is audible rather than a sustained blur. The intro and win
stings each use one 64-row order (about **6.43 seconds**).

| Track | Arrangement |
| --- | --- |
| `cfe_village_1` | Two separated statements per section; the wave channel supplies only well-spaced F/Eb/Bb/C anchors, while 2–3 noise punctuations leave the village quiet. |
| `cfe_village_2` | Three call-and-response phrases per section; square 2 adds eight harmonic shells, the wave adds a restrained root/fifth path, and there are only eight drum answers per section. |
| `cfe_village_3` | Four one-bar phrases per section: the unchanged F hook alternates with rising/falling answers, an independent 12-note counterline and a 16-step walking bass. Noise uses 9–10 selected low accents/light pickups—not a hit every beat. |
| `cfe_intro` | Slower-spaced statement of the same motif, then a held F tonic. |
| `cfe_win` | Restates the motif, adds a short C–Eb–F cadence and lands on a held F tonic. |

## SFX pipeline note

The project’s working `tools/make_sfx.py` pipeline writes mono unsigned 8-bit
WAV at 8000 Hz, pads to 32-sample boundaries, and GB Studio reduces samples to
4-bit during the build. `tools/make_repair_sfx.py` now verifies the existing
pickup/place/sparkle sidecars and IDs before replacing only their WAV payloads:
pickup is a low-level two-step lift (0.092 s), place is a soft 0.072 s impact
and settle, and sparkle is three short pings (0.108 s). No sound asset is added.
