#!/usr/bin/env python3
"""Decode a hUGETracker v6 `.uge` file and report its musical grammar.

Usage:
    python3 tools/uge_report.py song.uge [--dump] [--json]

Stdlib Python only (no third-party deps). The layout mirrors
`ReadSongFromStreamV6` in hUGETracker `src/song.pas` and the record
definitions in `src/hugedatatypes.pas`:

  0        Version            Integer (4)   == 6
  4        Name               ShortString (256)
  260      Artist             ShortString (256)
  516      Comment            ShortString (256)
  772      Instruments        45 x TInstrumentV3 (1385 bytes each)
  63097    Waves              16 x 32 nibbles
  63609    TicksPerRow        Integer (4)
  63613    TimerEnabled       Boolean (1)
  63614    TimerDivider       Integer (4)
  63618    PatternCount       Integer (4)
           per pattern: Key (4) + 64 cells x 17 bytes
           orders: 4 x (Len (4) + Len x Key (4))
           routines: 16 x AnsiString (4-byte length prefix + bytes)

TInstrumentV3 field offsets inside one 1385-byte record (FPC `{$mode objfpc}`:
enumerations are 4 bytes, subranges and Booleans are 1 byte, `packed` means
no padding between fields):

  +0    Type_             enum (0=square, 1=wave, 2=noise)
  +4    Name              ShortString (256)
  +260  Length            Integer
  +264  LengthEnabled     Boolean
  +265  InitialVolume     0..15
  +266  VolSweepDirection enum (0=up, 1=down)
  +270  VolSweepAmount    0..7
  +271  SweepTime         Integer
  +275  SweepIncDec       enum
  +279  SweepShift        Integer
  +283  Duty              0..3 (12.5/25/50/75 %)
  +284  OutputLevel       Integer
  +288  Waveform          Integer (index into the wave bank)
  +292  CounterStep       enum (0=fifteen, 1=seven)
  +296  SubpatternEnabled Boolean
  +297  Subpattern        64 cells x 17 bytes

The per-channel instrument number stored in a cell is the *slot inside the
channel's bank*: channels 1/2 use the duty bank, channel 3 the wave bank and
channel 4 the noise bank (`src/utils.pas` `ModInst`/`UnmodInst`).
"""
import argparse
import json
import struct
import sys

NO_NOTE = 90
LAST_NOTE = 72
FIRST_ROW = 0
ROWS = 64

INSTR_SIZE = 1385
INSTR_BASE = 772
WAVES_BASE = INSTR_BASE + 45 * INSTR_SIZE          # 63097
WAVES_SIZE = 16 * 32
TICKS_OFF = WAVES_BASE + WAVES_SIZE                 # 63609
FIXED = TICKS_OFF + 4 + 1 + 4                       # 63618
CELL_SIZE = 17

NOTE_NAMES = [
    "C-3", "C#3", "D-3", "D#3", "E-3", "F-3", "F#3", "G-3", "G#3", "A-3", "A#3", "B-3",
    "C-4", "C#4", "D-4", "D#4", "E-4", "F-4", "F#4", "G-4", "G#4", "A-4", "A#4", "B-4",
    "C-5", "C#5", "D-5", "D#5", "E-5", "F-5", "F#5", "G-5", "G#5", "A-5", "A#5", "B-5",
    "C-6", "C#6", "D-6", "D#6", "E-6", "F-6", "F#6", "G-6", "G#6", "A-6", "A#6", "B-6",
    "C-7", "C#7", "D-7", "D#7", "E-7", "F-7", "F#7", "G-7", "G#7", "A-7", "A#7", "B-7",
    "C-8", "C#8", "D-8", "D#8", "E-8", "F-8", "F#8", "G-8", "G#8", "A-8", "A#8", "B-8",
]

EFFECT_NAMES = {
    0x0: "arpeggio", 0x1: "slide up", 0x2: "slide down", 0x3: "portamento",
    0x4: "vibrato", 0x5: "panning", 0x6: "call routine", 0x7: "note delay",
    0x8: "set panning", 0x9: "sound sweep", 0xA: "volume envelope",
    0xB: "order jump", 0xC: "set volume", 0xD: "pattern jump",
    0xE: "note cut", 0xF: "set speed",
}

CHANNEL_ROLE = ["square 1 (lead)", "square 2 (harmony)", "wave (bass)", "noise (drums)"]


class UgeError(Exception):
    pass


def shortstr(buf, off):
    ln = buf[off]
    if off + 1 + ln > len(buf):
        raise UgeError(f"short string at {off} runs past end of file")
    return buf[off + 1:off + 1 + ln].decode("latin1")


def note_name(code):
    if code == NO_NOTE:
        return "---"
    if 0 <= code <= 71:
        return NOTE_NAMES[code]
    return f"?{code}"


def parse_instrument(rec):
    inst = {
        "type": rec[0],
        "type_name": ["square", "wave", "noise"][rec[0]] if rec[0] < 3 else "?",
        "name": shortstr(rec, 4),
        "length": struct.unpack_from("<i", rec, 260)[0],
        "length_enabled": bool(rec[264]),
        "initial_volume": rec[265],
        "vol_sweep_direction": "up" if rec[266] == 0 else "down",
        "vol_sweep_amount": rec[270],
        "sweep_time": struct.unpack_from("<i", rec, 271)[0],
        "sweep_incdec": "up" if rec[275] == 0 else "down",
        "sweep_shift": struct.unpack_from("<i", rec, 279)[0],
        "duty": rec[283],
        "output_level": struct.unpack_from("<i", rec, 284)[0],
        "waveform": struct.unpack_from("<i", rec, 288)[0],
        "counter_step": "fifteen" if rec[292] == 0 else "seven",
        "subpattern_enabled": bool(rec[296]),
    }
    sub = []
    for row in range(ROWS):
        off = 297 + row * CELL_SIZE
        note, _i, vol, fx, fxp = struct.unpack_from("<iiiiB", rec, off)
        if note != NO_NOTE or vol or fx:
            sub.append({"row": row, "note": note, "vol": vol, "fx": fx, "fxp": fxp})
    inst["subpattern"] = sub
    return inst


def parse(path):
    with open(path, "rb") as source:
        buf = source.read()
    if len(buf) < FIXED:
        raise UgeError(f"file too short ({len(buf)} bytes)")
    version = struct.unpack_from("<i", buf, 0)[0]
    if version != 6:
        raise UgeError(f"unsupported .uge version {version} (this tool reads v6)")
    song = {
        "path": path,
        "size": len(buf),
        "version": version,
        "name": shortstr(buf, 4),
        "artist": shortstr(buf, 260),
        "comment": shortstr(buf, 516),
        "ticks_per_row": struct.unpack_from("<i", buf, TICKS_OFF)[0],
        "timer_enabled": bool(buf[TICKS_OFF + 4]),
        "timer_divider": struct.unpack_from("<i", buf, TICKS_OFF + 5)[0],
    }

    instruments = []
    for i in range(45):
        rec = buf[INSTR_BASE + i * INSTR_SIZE: INSTR_BASE + (i + 1) * INSTR_SIZE]
        inst = parse_instrument(rec)
        bank = ["duty", "wave", "noise"][i // 15]
        inst["bank"] = bank
        inst["slot"] = (i % 15) + 1
        inst["global_id"] = i + 1
        instruments.append(inst)
    song["instruments"] = instruments

    waves = []
    for i in range(16):
        waves.append(list(buf[WAVES_BASE + i * 32: WAVES_BASE + (i + 1) * 32]))
    song["waves"] = waves

    off = FIXED
    (pcount,) = struct.unpack_from("<i", buf, off)
    off += 4
    patterns = {}
    for _ in range(pcount):
        (key,) = struct.unpack_from("<i", buf, off)
        off += 4
        cells = []
        for row in range(ROWS):
            note, ins, vol, fx, fxp = struct.unpack_from("<iiiiB", buf, off)
            off += CELL_SIZE
            if note != NO_NOTE or ins or vol or fx or fxp:
                cells.append({"row": row, "note": note, "inst": ins, "vol": vol,
                              "fx": fx, "fxp": fxp})
        patterns[key] = cells
    song["patterns"] = patterns

    orders = []
    for ch in range(4):
        (ln,) = struct.unpack_from("<i", buf, off)
        off += 4
        keys = list(struct.unpack_from(f"<{ln}i", buf, off))
        off += 4 * ln
        orders.append(keys)
    song["orders"] = orders

    routines = []
    for _ in range(16):
        (ln,) = struct.unpack_from("<i", buf, off)
        off += 4
        routines.append(buf[off:off + ln].decode("latin1"))
        off += ln
    song["routines"] = routines
    song["trailing_bytes"] = len(buf) - off
    return song


def channel_stats(song, ch):
    """Per-channel musical statistics over the whole order list."""
    keys = song["orders"][ch]
    played = keys[:-1] if keys and keys[-1] == 0 and len(keys) > 1 else keys
    stats = {
        "channel": ch,
        "role": CHANNEL_ROLE[ch],
        "order": played,
        "patterns_played": len(played),
        "notes": 0,
        "note_range": None,
        "distinct": [],
        "pitch_hist": {},
        "rows_used": 0,
        "instruments": {},
        "effects": {},
        "row_spans": [],
        "sequence": [],
    }
    seq = []
    for key in played:
        cells = song["patterns"].get(key, [])
        notes = [c for c in cells if c["note"] != NO_NOTE]
        stats["notes"] += len(notes)
        if notes:
            lo = min(c["note"] for c in notes)
            hi = max(c["note"] for c in notes)
            stats["note_range"] = (lo, hi) if stats["note_range"] is None else (
                min(stats["note_range"][0], lo), max(stats["note_range"][1], hi))
            for c in notes:
                stats["pitch_hist"][c["note"]] = stats["pitch_hist"].get(c["note"], 0) + 1
        rows = [c["row"] for c in cells]
        if rows:
            stats["rows_used"] = max(stats["rows_used"], max(rows) + 1)
            stats["row_spans"].append((key, min(rows), max(rows)))
        for c in cells:
            if c["inst"]:
                stats["instruments"][c["inst"]] = stats["instruments"].get(c["inst"], 0) + 1
            if c["fx"]:
                key_fx = f"{c['fx']:X}{c['fxp']:02X}"
                stats["effects"][key_fx] = stats["effects"].get(key_fx, 0) + 1
            if c["note"] != NO_NOTE:
                seq.append((c["note"], c["row"]))
    stats["sequence"] = seq
    stats["distinct"] = sorted(stats["pitch_hist"])
    return stats


CHANNEL_BANK = ["duty", "duty", "wave", "noise"]


def used_instruments(song):
    """Map (bank, slot) -> set of channels that play it.

    A cell's instrument number is a slot inside the *channel's* bank, so the
    same slot number means different instruments on different channels.
    """
    used = {}
    for ch in range(4):
        keys = song["orders"][ch]
        played = keys[:-1] if keys and keys[-1] == 0 and len(keys) > 1 else keys
        for key in played:
            for c in song["patterns"].get(key, []):
                if c["inst"]:
                    used.setdefault((CHANNEL_BANK[ch], c["inst"]), set()).add(ch)
    out = []
    for inst in song["instruments"]:
        chans = used.get((inst["bank"], inst["slot"]))
        if chans:
            out.append((inst, sorted(chans)))
    return out


def fmt_instrument(inst, chans):
    bits = []
    if inst["type"] == 0:
        bits.append(f"duty {['12.5', '25', '50', '75'][inst['duty']]}%")
    elif inst["type"] == 1:
        bits.append(f"wave {inst['waveform']}")
    else:
        bits.append(f"noise {inst['counter_step']}")
    bits.append(f"vol {inst['initial_volume']}")
    if inst["vol_sweep_amount"]:
        bits.append(f"env {inst['vol_sweep_direction']} {inst['vol_sweep_amount']}")
    if inst["sweep_time"] or inst["sweep_shift"]:
        bits.append(f"sweep t{inst['sweep_time']} s{inst['sweep_shift']}")
    if inst["output_level"]:
        bits.append(f"out {inst['output_level']}")
    if inst["subpattern_enabled"]:
        bits.append(f"macro[{len(inst['subpattern'])}]")
    return (f"  {inst['bank']} {inst['slot']:2d} {inst['name'] or '(unnamed)':<22} "
            f"ch{','.join(str(c + 1) for c in chans):<5} " + " ".join(bits))


def report(song, dump=False):
    out = []
    p = out.append
    p(f"file        : {song['path']} ({song['size']} bytes)")
    p(f"version     : {song['version']} (v6)")
    p(f"name        : {song['name']}")
    p(f"artist      : {song['artist']}")
    p(f"comment     : {song['comment']}")
    tpr = song["ticks_per_row"]
    bpm = (59.727500569606 / tpr / 4) * 60 if tpr else 0
    p(f"tempo       : ~{bpm:.2f} BPM  (VBlank={59.727500569606:.4f} Hz, 4 rows/beat)")
    p(f"ticks/row   : {tpr}  "
      f"(timer_enabled={song['timer_enabled']}, timer_divider={song['timer_divider']})")
    p(f"patterns    : {len(song['patterns'])}")
    for ch in range(4):
        keys = song["orders"][ch]
        p(f"order ch{ch + 1}  : {keys}  ({CHANNEL_ROLE[ch]})")
    p("")

    p("instruments in use")
    any_used = False
    for inst, chans in used_instruments(song):
        any_used = True
        p(fmt_instrument(inst, chans))
    if not any_used:
        p("  (none)")
    p("")

    p("per-channel statistics")
    allstats = []
    for ch in range(4):
        st = channel_stats(song, ch)
        allstats.append(st)
        p(f"ch{ch + 1} {st['role']}")
        p(f"  patterns played : {st['patterns_played']}  rows used/pattern: "
          f"{st['rows_used']}")
        p(f"  notes           : {st['notes']}")
        seconds = st["patterns_played"] * ROWS * tpr / 59.727500569606
        if seconds:
            p(f"  density         : {st['notes'] / seconds:.2f} note events/s "
              f"over {seconds:.2f} s/order pass")
        if st["note_range"]:
            lo, hi = st["note_range"]
            p(f"  note range      : {note_name(lo)} .. {note_name(hi)} "
              f"(codes {lo}..{hi})")
        p(f"  distinct pitches: {len(st['distinct'])} "
          f"{[note_name(n) for n in st['distinct']]}")
        hist = ", ".join(f"{note_name(k)}:{v}" for k, v in
                         sorted(st["pitch_hist"].items(), key=lambda kv: -kv[1]))
        p(f"  pitch histogram : {hist}")
        if st["instruments"]:
            p(f"  instrument slots: "
              f"{ {k: v for k, v in sorted(st['instruments'].items())} }")
        if st["effects"]:
            p(f"  effects         : "
              f"{ {k: v for k, v in sorted(st['effects'].items())} }")
        else:
            p("  effects         : none")
        p("")
    return out, allstats


def dump(song, allstats):
    out = []
    for ch in range(4):
        keys = song["orders"][ch]
        played = keys[:-1] if keys and keys[-1] == 0 and len(keys) > 1 else keys
        out.append(f"--- channel {ch + 1} ({CHANNEL_ROLE[ch]}) ---")
        for key in played:
            out.append(f"  pattern {key}:")
            for c in song["patterns"].get(key, []):
                out.append(
                    f"    row {c['row']:2d}  {note_name(c['note']):<5} "
                    f"inst {c['inst']:2d}  vol {c['vol']:2d}  "
                    f"fx {c['fx']:X}{c['fxp']:02X}")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("uge")
    ap.add_argument("--dump", action="store_true", help="print every note cell")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)

    try:
        song = parse(args.uge)
    except UgeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    lines, allstats = report(song)
    if args.dump:
        lines += dump(song, allstats)

    if args.json:
        stats = []
        for st in allstats:
            st = dict(st)
            st["sequence"] = [[n, r] for n, r in st["sequence"]]
            stats.append(st)
        print(json.dumps({
            "path": song["path"], "name": song["name"], "artist": song["artist"],
            "comment": song["comment"], "ticks_per_row": song["ticks_per_row"],
            "orders": song["orders"], "pattern_count": len(song["patterns"]),
            "patterns": song["patterns"], "instruments": song["instruments"],
            "channels": stats, "trailing_bytes": song["trailing_bytes"],
        }, indent=2))
    else:
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
