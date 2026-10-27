"""Retired: the climb debris sprite (``climb_debris``) is no longer generated.

It was unused once falling debris was removed from the climb. This module
stays as a no-op so the climb profile in ``make_project.py`` still runs its
generator step; delete it together with that list entry when next touched.
"""
from __future__ import annotations


def main() -> None:
    print("make_climb_sprites: no sprites to generate (climb_debris retired)")


if __name__ == "__main__":
    main()
