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

Multi-scene jobs (docs/LEVEL_REDESIGN.md §7): the profiles already list the new
scene generators (make_crest_scene.py, make_gully_scene.py, make_ladder_scene.py).
A listed generator that does not exist yet is skipped while scenes.py marks its
scene ``planned``; any other missing script is an error. --verify also runs the
shared route, link and chain tests.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import scenes  # noqa: E402  (stdlib registry: planned scenes and their generators)

PROFILES = {
    "climb": ("make_climb_art.py", "make_grid_sprites.py", "make_climb_gust.py", "make_climb_scene.py",
              "make_crest_scene.py", "make_engine_fields.py", "make_engine_patch.py"),
    "ridge": ("make_ridge_art.py", "make_tomas_sprites.py", "make_whip_sprite.py", "make_transformer_sprite.py", "make_grid_sprites.py", "make_climb_gust.py", "make_ridge_scene.py", "make_climb_scene.py"),
    "rosa": ("make_rosa_art.py", "make_rosa_sprites.py", "make_grid_sprites.py", "make_climb_gust.py", "make_rosa_scene.py",
             "make_gully_scene.py", "make_ridge_scene.py"),
    "kiko": ("make_kiko_art.py", "make_kiko_sprites.py", "make_grid_sprites.py", "make_climb_gust.py", "make_kiko_scene.py",
             "make_ladder_scene.py", "make_rosa_scene.py"),
    "intro": ("make_intro_art.py", "make_intro_sprites.py", "make_intro_scene.py"),
    "opening": ("make_opening_art.py", "make_opening_characters.py", "make_grid_sprites.py", "make_opening_scene.py"),
    "tickets": ("make_ticket_art.py", "make_ticket_scene.py"),
    # Developer lab rooms: reuse the storm_climb template and existing art only.
    "lab": ("make_lab_scene.py",),
}


# Generators of scenes registered ahead of their work package (scenes.py "planned").
PLANNED_GENERATORS = {entry["generator"] for folder, entry in scenes.REGISTRY.items()
                      if scenes.planned(folder) and not scenes.present(folder)}
SHARED_TESTS = ["test_routes.py", "test_scene_links.py", "test_grid_chain.py",
                "test_experience.py", "test_completion.py", "test_shock.py", "test_hero_integration.py",
                "test_board_timing.py"]


def run(*arguments: str) -> None:
    print("+ " + " ".join(arguments), flush=True)
    subprocess.run([sys.executable, *arguments], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile", choices=PROFILES, help="explicit output owner; no implicit active-profile guessing")
    parser.add_argument("--render-music", action="store_true", help="offline local uge-builder render before scene generation")
    parser.add_argument("--fixtures", action="store_true", help="opening only: authored size/power comparison PNGs")
    parser.add_argument("--verify", action="store_true", help="run focused profile unit tests after generation")
    parser.add_argument("--intro-hero", choices=("storm", "neighborhood", "classic"),
                        help="intro only: hero art variant; default is Storm Worker")
    args = parser.parse_args()
    if args.intro_hero and args.profile != "intro":
        parser.error("--intro-hero applies only to the intro profile")
    if args.fixtures and args.profile != "opening":
        parser.error("--fixtures applies only to the opening profile")
    try:
        import PIL  # noqa: F401
    except ImportError:
        parser.error("Pillow is required; use the managed toolchain Python, not an unprepared system interpreter")
    if args.render_music:
        composer = {"intro": "compose_intro.py", "tickets": "compose_ending.py"}.get(
            args.profile, "compose_climb.py")
        run("tools/" + composer, "--render")
    elif args.profile != "lab" and not (ROOT / "assets/music/cfe_storm_climb.uge.gbsres").exists():
        parser.error("native music is missing; use --render-music with the installed uge-builder image")
    if args.profile == "tickets":
        if not (ROOT / "assets/music/cfe_ending_reprise.uge.gbsres").exists():
            parser.error("ending music is missing; use tickets --render-music with the installed uge-builder image")
        run("tools/compose_ending.py")
    if args.profile in {"climb", "ridge", "rosa", "kiko"}:
        run("tools/make_completion_sfx.py")
    for script in PROFILES[args.profile]:
        if not (ROOT / "tools" / script).is_file():
            if script in PLANNED_GENERATORS:
                print(f"skip tools/{script} (planned scene, not written yet)", flush=True)
                continue
            parser.error(f"tools/{script} is missing")
        if script == "make_intro_sprites.py" and args.intro_hero:
            run("tools/" + script, "--hero-variant", args.intro_hero)
        else:
            run("tools/" + script)
    if args.fixtures:
        run("tools/preview_opening.py")
    if args.verify:
        patterns = {"climb": ["test_climb*.py", "test_crest*.py", "test_engine_*.py", "test_scenes.py", *SHARED_TESTS],
                    "opening": ["test_opening.py", "test_storm_worker_art.py", "test_hero_integration.py", "test_scenes.py"],
                    "ridge": ["test_ridge*.py", "test_tomas_sprites.py", "test_climb.py", "test_scenes.py", *SHARED_TESTS],
                    "rosa": ["test_rosa*.py", "test_ridge.py", "test_scenes.py", *SHARED_TESTS],
                    "kiko": ["test_kiko*.py", "test_rosa.py", "test_scenes.py", *SHARED_TESTS],
                    "intro": ["test_intro*.py", "test_opening.py", "test_scenes.py"],
                    "tickets": ["test_tickets.py", "test_dispatch_hub.py", "test_ending.py", "test_scenes.py"],
                    "lab": ["test_lab*.py", "test_scenes.py"]}
        for pattern in patterns[args.profile]:
            if not any((ROOT / "tools").glob(pattern)):
                continue        # e.g. test_crest*.py before its work package lands
            run("-m", "unittest", "discover", "-s", "tools", "-p", pattern)
    print("Regeneration complete. Refresh, build and playtest through MCP; only the intro profile writes the launch scene.")


if __name__ == "__main__":
    main()
