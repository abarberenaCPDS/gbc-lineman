"""Copy the GB Studio project into build/release-project/ without lab and legacy scenes.

Usage (managed Python, from anywhere):
  python tools/make_release.py              # refuses while VERSION contains -dev
  python tools/make_release.py --allow-dev  # dev-tagged release copy, for rehearsal

The source tree is never modified: storm_night stays in it (make_climb_scene.py
uses it as a template); only the copy loses the lab and legacy scene folders.
After the copy, every remaining file is scanned for ids of removed scenes and
the script fails if any reference survives. Prints the CLI build command; it
does not run the build.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import scenes

ROOT = scenes.ROOT
VERSION_FILE = ROOT / "VERSION"
RELEASE_DIR = ROOT / "build" / "release-project"
ROM_OUT = ROOT / "build" / "rom" / "lineman-release.gbc"
PROJECT_FILE = "mr-cfe.gbsproj"
COPY_FILES = (PROJECT_FILE,)
COPY_DIRS = ("project", "assets")
# Editor backups and local-only state never ship.
IGNORE = shutil.ignore_patterns("*.bak", "__pycache__", ".DS_Store", "user_*.gbsres")
CLI = Path.home() / "Library/Application Support/modretro-chromatic/toolchain/.local/vendor/gb-studio/out/cli/gb-studio-cli.js"


def read_version() -> str:
    return VERSION_FILE.read_text(encoding="utf-8").strip()


def copy_project() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)
    for name in COPY_FILES:
        shutil.copy2(ROOT / name, RELEASE_DIR / name)
    for name in COPY_DIRS:
        shutil.copytree(ROOT / name, RELEASE_DIR / name, ignore=IGNORE)


def strip_removed_scenes() -> list[str]:
    removed = []
    for folder, entry in scenes.REGISTRY.items():
        if entry["tag"] in (scenes.LAB, scenes.LEGACY):
            target = RELEASE_DIR / "project" / "scenes" / folder
            if target.exists():
                shutil.rmtree(target)
                removed.append(folder)
    return removed


def find_dangling_references(removed_ids: list[str]) -> list[tuple[str, str]]:
    needles = [(scene_id.encode("ascii"), scene_id) for scene_id in removed_ids]
    hits = []
    for path in sorted(RELEASE_DIR.rglob("*")):
        if not path.is_file():
            continue
        data = path.read_bytes()
        for needle, scene_id in needles:
            if needle in data:
                hits.append((str(path.relative_to(RELEASE_DIR)), scene_id))
    return hits


def build_command(copy: Path) -> str:
    return (
        f'TMPDIR="$(getconf DARWIN_USER_TEMP_DIR)gbsb-cfe" node "{CLI}" -v make:rom '
        f'"{copy / PROJECT_FILE}" "{ROM_OUT}"'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--allow-dev", action="store_true", help="allow a -dev VERSION for this release copy")
    args = parser.parse_args()

    version = read_version()
    if "-dev" in version and not args.allow_dev:
        raise SystemExit(f"refusing release: VERSION is {version!r}; pass --allow-dev to rehearse")

    copy_project()
    removed = strip_removed_scenes()
    removed_ids = scenes.ids(scenes.LAB) + scenes.ids(scenes.LEGACY)
    hits = find_dangling_references(removed_ids)
    if hits:
        for path, scene_id in hits:
            print(f"dangling reference to {scene_id}: {path}", file=sys.stderr)
        raise SystemExit(f"release copy at {RELEASE_DIR} still references {len(hits)} removed scene id(s)")

    ROM_OUT.parent.mkdir(parents=True, exist_ok=True)
    print(f"VERSION {version}")
    print(f"removed scenes: {', '.join(removed) or 'none'}")
    print(f"release copy: {RELEASE_DIR}")
    print("build command:")
    print(build_command(RELEASE_DIR))


if __name__ == "__main__":
    main()
