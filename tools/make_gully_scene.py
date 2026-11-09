"""Generate 3B ``signal_gully`` (Priya's job, 20x36, descending) from ``rosa.py``.

Run with ``python3 tools/make_gully_scene.py`` (after ``make_rosa_scene.py``,
which writes the job's shared palettes and variables). docs/LEVEL_REDESIGN.md
§2 Job 3: the hero enters at the top-left carrying cable 3, plugs it into T3 on
deck 9, then uses a deliberate Down+A drop followed by alternating eroded
banks and catch shelves. The first bridge remains wall to wall; lower openings
allow visible falls and recovery. Pole 4 is on deck15, T4 on deck27 and pole5
on the dry floor; cable5 leaves through the bottom-right exit into3C.

Geometry comes from rosa.collision_grid. Actors and scripts come from
make_rosa_scene.RosaScene; current route and budget gates are in test_routes.
"""

from __future__ import annotations

import make_rosa_scene as job


def main() -> None:
    music_id, audio_ids, sprite_ids = job.load_ids()
    job.write_variables()
    job.write_scene(job.GULLY, music_id, audio_ids, sprite_ids)


if __name__ == "__main__":
    main()
