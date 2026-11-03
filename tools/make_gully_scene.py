"""Generate 3B ``signal_gully`` (Priya's job, 20x36, descending) from ``rosa.py``.

Run with ``python3 tools/make_gully_scene.py`` (after ``make_rosa_scene.py``,
which writes the job's shared palettes and variables). docs/LEVEL_REDESIGN.md
§2 Job 3: the hero enters at the top-left carrying cable 3, plugs it into T3 on
deck 9, then drops deck by deck with Down+A (every deck is slab plus one-way
timber wall to wall; B-07 keeps each tap to one shelf): pole 4 on deck 15, T4
on deck 27, pole 5 on the floor, whose cable leaves through the bottom-right
exit into 3C. Going back up uses the climb's moves (the 4-row leap onto the
arrival shelf).

The geometry is the climb's shaft template (``shaft.py`` decks and slabs, via
``rosa.collision_grid``); the scene, actors, triggers and scripts come from
``make_rosa_scene.RosaScene`` with the gully's namespace. The worst OAM window
is 32+4 objects (spec §5), so no culling thread.
"""

from __future__ import annotations

import make_rosa_scene as job


def main() -> None:
    music_id, audio_ids, sprite_ids = job.load_ids()
    job.write_variables()
    job.write_scene(job.GULLY, music_id, audio_ids, sprite_ids)


if __name__ == "__main__":
    main()
