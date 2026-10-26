"""Write the one-line platform engine patch (B-07) as a local engine overlay.

GB Studio copies its default engine, then copies ``assets/engine`` over it, so
this overlay holds only ``src/states/platform.c``: the vendor file with a shorter
drop-through window. Abe chose this over slower falling or two-shelf drops
(2026-10-26). Rerun after a GB Studio upgrade; ``test_engine_patch`` fails when
the vendor file and the overlay drift apart.

Why: Down+A arms ``plat_drop_timer`` for ``DROP_FRAMES_MAX`` frames, and one-way
shelves are ignored until it runs out. At default gravity the hero falls about
0.22 * f * (f + 1) px in f frames: 15 frames is ~52 px, two climb shelves (24 px
apart). 7 frames is ~12 px: clear of the current shelf (8 px), short of the next.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
VENDOR_ENGINE = (Path.home() / "Library" / "Application Support" / "modretro-chromatic" / "toolchain"
                 / ".local" / "vendor" / "gb-studio" / "appData" / "engine")
VENDOR_PLATFORM = VENDOR_ENGINE / "gbvm" / "src" / "states" / "platform.c"
OVERLAY_PLATFORM = PROJECT_DIR / "assets" / "engine" / "src" / "states" / "platform.c"

DROP_FRAMES = 7
VENDOR_LINE = "#define DROP_FRAMES_MAX 15"
PATCHED_LINE = (f"#define DROP_FRAMES_MAX {DROP_FRAMES}"
                "  // mr-cfe B-07: one shelf per Down+A (tools/make_engine_patch.py)")


def drop_distance_px(frames: int, gravity: int) -> float:
    """Pixels fallen from rest in ``frames`` frames (platform.c VEL_TO_SUBPX, 32 subpx/px)."""
    subpx = sum(((gravity * f) >> 8) << 1 for f in range(1, frames + 1))
    return subpx / 32


def default_gravity() -> int:
    fields = json.loads((VENDOR_ENGINE / "engine.json").read_text(encoding="utf-8"))["fields"]
    return next(int(f["defaultValue"]) for f in fields if f.get("key") == "plat_grav")


def patched_source(vendor: str) -> str:
    if vendor.count(VENDOR_LINE) != 1:
        raise SystemExit(f"{VENDOR_PLATFORM} no longer has exactly one {VENDOR_LINE!r}; re-check B-07")
    return vendor.replace(VENDOR_LINE, PATCHED_LINE)


def main() -> None:
    contents = patched_source(VENDOR_PLATFORM.read_text(encoding="utf-8"))
    OVERLAY_PLATFORM.parent.mkdir(parents=True, exist_ok=True)
    if OVERLAY_PLATFORM.exists() and OVERLAY_PLATFORM.read_text(encoding="utf-8") == contents:
        print(f"unchanged {OVERLAY_PLATFORM.relative_to(PROJECT_DIR)}")
        return
    OVERLAY_PLATFORM.write_text(contents, encoding="utf-8")
    print(f"wrote {OVERLAY_PLATFORM.relative_to(PROJECT_DIR)} (DROP_FRAMES_MAX {DROP_FRAMES})")


if __name__ == "__main__":
    main()
