"""Regenerate an explicit prototype profile; ROM/web builds remain MCP-owned.

Use the managed Python (Pillow). Examples:
  python tools/make_project.py opening --fixtures --verify
  python tools/make_project.py climb --render-music --verify
  python tools/make_project.py ridge --verify
  python tools/make_project.py rosa --verify
  python tools/make_project.py kiko --verify
  python tools/make_project.py intro --verify
  python tools/make_project.py lab --verify

Never invokes the out-of-sync legacy Storm Night generators or touches the user's live browser/emulator state.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
PROFILES = {
    "climb": ("make_climb_art.py", "make_grid_sprites.py", "make_climb_gust.py", "make_climb_scene.py", "make_engine_fields.py", "make_engine_patch.py"),
    "ridge": ("make_ridge_art.py", "make_tomas_sprites.py", "make_whip_sprite.py", "make_transformer_sprite.py", "make_grid_sprites.py", "make_climb_gust.py", "make_ridge_scene.py", "make_climb_scene.py"),
    "rosa": ("make_rosa_art.py", "make_rosa_sprites.py", "make_grid_sprites.py", "make_climb_gust.py", "make_rosa_scene.py", "make_ridge_scene.py"),
    "kiko": ("make_kiko_art.py", "make_kiko_sprites.py", "make_grid_sprites.py", "make_climb_gust.py", "make_kiko_scene.py", "make_rosa_scene.py"),
    "intro": ("make_intro_art.py", "make_intro_sprites.py", "make_intro_scene.py"),
    "opening": ("make_opening_art.py", "make_opening_characters.py", "make_grid_sprites.py", "make_opening_scene.py"),
    "tickets": ("make_ticket_art.py", "make_ticket_scene.py"),
    # Developer lab rooms: reuse the storm_climb template and existing art only.
    "lab": ("make_lab_scene.py",),
}


def run(*arguments: str) -> None:
    print("+ " + " ".join(arguments), flush=True)
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES, help="explicit output owner; no implicit active-profile guessing")
    parser.add_argument("--render-music", action="store_true", help="offline local uge-builder render before scene generation")
    parser.add_argument("--fixtures", action="store_true", help="opening only: authored size/power comparison PNGs")
    parser.add_argument("--verify", action="store_true", help="run focused profile unit tests after generation")
    args = parser.parse_args()
    if args.fixtures and args.profile != "opening":
        parser.error("--fixtures applies only to the opening profile")
    try:
        import PIL  # noqa: F401
    except ImportError:
        parser.error("Pillow is required; use the managed toolchain Python, not an unprepared system interpreter")
    if args.render_music:
        run("tools/compose_intro.py" if args.profile == "intro" else "tools/compose_climb.py",
            "--render")
    elif args.profile != "lab" and not (ROOT / "assets/music/cfe_storm_climb.uge.gbsres").exists():
        parser.error("native music is missing; use --render-music with the installed uge-builder image")
    for script in PROFILES[args.profile]:
        run("tools/" + script)
    if args.fixtures:
        run("tools/preview_opening.py")
    if args.verify:
        patterns = {"climb": ["test_climb*.py", "test_engine_*.py", "test_scenes.py"],
                    "opening": ["test_opening.py", "test_scenes.py"],
                    "ridge": ["test_ridge*.py", "test_tomas_sprites.py", "test_climb.py", "test_scenes.py"],
                    "rosa": ["test_rosa*.py", "test_ridge.py", "test_scenes.py"],
                    "kiko": ["test_kiko*.py", "test_rosa.py", "test_scenes.py"],
                    "intro": ["test_intro*.py", "test_opening.py", "test_scenes.py"],
                    "tickets": ["test_tickets.py", "test_scenes.py"],
                    "lab": ["test_lab*.py", "test_scenes.py"]}
        for pattern in patterns[args.profile]:
            run("-m", "unittest", "discover", "-s", "tools", "-p", pattern)
    print("Regeneration complete. Refresh, build and playtest through MCP; only the intro profile writes the launch scene.")


if __name__ == "__main__":
    main()
