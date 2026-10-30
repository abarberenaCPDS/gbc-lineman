"""Vertical shaft template: the climb's 20x36 deck geometry and its actor-culling thread.

Stdlib only (no Pillow). ``climb.py`` (1A storm_climb) re-exports everything
here unchanged; the redesign's other shafts, 3B ``signal_gully`` (down) and 4B
``pine_ladder`` (up), build on the same template (docs/LEVEL_REDESIGN.md §2).

Geometry (tile units, rows top-down, PLATFORM collision bytes):

  DECK0_ROW 33          bottom deck (one-way timber over bedrock rows 34-35)
  DECK_ROWS             27, 21, 15, 9: a rock slab at each end (SLAB_LEFT /
                        SLAB_RIGHT, two rows deep) and a one-way walk between
                        them (DECK_WALK); a full-height jump at a deck end bonks
                        the slab above, so routes rise through the middle
  LEDGE_ROWS            30, 24, 18, 12: one-way ledges between the decks

  deck_solid_blocks()   the slab rectangles for a list of deck rows
  collision_grid()      row-major collision bytes from platforms and solid blocks

A contract keeps its own PLATFORMS / SOLID_BLOCKS (walls, summit, arrival
shelf) and calls ``collision_grid(MAP_W, MAP_H, PLATFORMS, SOLID_BLOCKS)``.

Culling thread. GB Studio keeps actors active ~6 rows above and ~8 rows below
the screen and every active actor draws (OAM) even off screen, so a 36-row
shaft with more than ~36 OBJs in its 30-row active window needs the thread
(spec §5: 1A and 4B). The thread estimates the camera top row ``u`` from the
hero's tile y inside the platform camera's 16px deadzone (u in [y-10, y-6]);
an actor stays active only while the clamped camera top
``s = clamp(u, 0, camera_max_top)`` satisfies
``anchor - CULL_BELOW <= s <= anchor + CULL_ABOVE``. That covers GB Studio's
own row refresh region (s-1 .. s+19) plus one row of estimate error, so the
engine never re-activates an actor the thread just deactivated.

  cull_range(anchor, camera_max_top)          the (lo, hi) camera-estimate band
  cull_condition(anchor, camera_max_top)      that band as a GB Studio script value
  cull_thread_event(actors, builders=...)     the EVENT_THREAD_START; actors are
                                              actor resources (``y`` is the anchor)

The thread's scratch variables 46-49 (``VAR_CULL_*``) are safe to share
between shafts: only one scene runs at a time. Timed hazards in a culled scene
must start every live cycle safe (``make_climb_scene.ClimbChain``): the
thread can deactivate an actor mid-cycle and its update script restarts on
reactivation.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Sequence

# Collision bytes used by GB Studio PLATFORM scenes.
COL_EMPTY = 0x00
COL_TOP = 0x01  # one-way surface: land from above, jump through from below
COL_SOLID = 0x0F

MAP_W, MAP_H = 20, 36

DECK0_ROW = 33
DECK_ROWS = [27, 21, 15, 9]            # slabs + middle walk
LEDGE_ROWS = [30, 24, 18, 12]
SLAB_LEFT = (1, 5)                     # x range of each deck's left rock slab
SLAB_RIGHT = (14, 18)
DECK_WALK = (6, 13)                    # one-way timber walk between the slabs

# ---------------------------------------------------------------------------
# Culling thread constants (see the module docstring).
# ---------------------------------------------------------------------------
CAMERA_ROWS = 18
CAMERA_DEADZONE_ROWS = (10, 6)         # u in [y - 10, y - 6]
CULL_ABOVE = 2                         # active while s <= anchor + 2
CULL_BELOW = 22                        # active while s >= anchor - 22
CULL_WAIT_FRAMES = 8                   # the loop is idle unless the clamped camera row changed
CULL_THREAD_HANDLE = "T0"
OAM_LIMIT = 40
HERO_OBJ = 4                           # opening_worker24: 16x32, four 8x16 OBJs
HERO_COLUMNS = 2
VAR_CULL_X = "46"          # culling thread scratch: hero tile x
VAR_CULL_Y = "47"          # culling thread: hero tile y
VAR_CULL_CAM = "48"        # culling thread: estimated camera top row (unclamped)
VAR_CULL_TOP = "49"        # culling thread: clamped camera top last applied (-1 = none yet)


def camera_max_top(map_h: int = MAP_H) -> int:
    return map_h - CAMERA_ROWS


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------
def deck_solid_blocks(deck_rows: Iterable[int] = DECK_ROWS, slab_left: tuple[int, int] = SLAB_LEFT,
                      slab_right: tuple[int, int] = SLAB_RIGHT) -> list[tuple[int, int, int, int]]:
    """(x0, x1, row0, row1) slabs at both ends of every deck, two rows deep."""
    blocks = []
    for row in deck_rows:
        blocks.append((slab_left[0], slab_left[1], row, row + 1))
        blocks.append((slab_right[0], slab_right[1], row, row + 1))
    return blocks


def collision_grid(map_w: int, map_h: int, platforms: Iterable[tuple[int, int, int]],
                   solid_blocks: Iterable[tuple[int, int, int, int]]) -> list[list[int]]:
    """Row-major PLATFORM collision bytes: one-way ``platforms`` (row, x0, x1), then solid blocks on top."""
    grid = [[COL_EMPTY for _ in range(map_w)] for _ in range(map_h)]
    for row, x0, x1 in platforms:
        for x in range(x0, x1 + 1):
            grid[row][x] = COL_TOP
    for x0, x1, row0, row1 in solid_blocks:
        for row in range(row0, row1 + 1):
            for x in range(x0, x1 + 1):
                grid[row][x] = COL_SOLID
    return grid


# ---------------------------------------------------------------------------
# Culling thread
# ---------------------------------------------------------------------------
def cull_range(anchor_row: int, max_top: int) -> tuple[int, int]:
    """(lo, hi) of the unclamped camera estimate u for which the actor stays active.

    -128 / 127 mean "no bound" on that side (the actor is active at that end of the map).
    """
    lo = anchor_row - CULL_BELOW
    hi = anchor_row + CULL_ABOVE
    return (-128 if lo <= 0 else lo, 127 if hi >= max_top else hi)


def _number(value: int) -> dict[str, Any]:
    return {"type": "number", "value": value}


def _var(variable_id: str) -> dict[str, Any]:
    return {"type": "variable", "value": variable_id}


def _op(kind: str, a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {"type": kind, "valueA": a, "valueB": b}


def cull_condition(anchor: int, max_top: int, var_top: str = VAR_CULL_TOP) -> dict[str, Any] | None:
    """Script value on the clamped camera top: true while the actor on ``anchor`` should be active.

    None when the actor is active everywhere (no thread branch needed).
    """
    lo, hi = cull_range(anchor, max_top)
    parts = []
    if lo > -128:
        parts.append(_op("gte", _var(var_top), _number(lo)))
    if hi < 127:
        parts.append(_op("lte", _var(var_top), _number(hi)))
    if not parts:
        return None
    return parts[0] if len(parts) == 1 else _op("and", parts[0], parts[1])


def cull_thread_event(actors: Sequence[dict[str, Any]], *, event: Callable[..., dict[str, Any]],
                      branch_event: Callable[..., dict[str, Any]],
                      set_value: Callable[..., dict[str, Any]],
                      wait_event: Callable[..., dict[str, Any]], max_top: int,
                      key: str = "cull", handle: str = CULL_THREAD_HANDLE,
                      variables: tuple[str, str, str, str] = (VAR_CULL_X, VAR_CULL_Y, VAR_CULL_CAM, VAR_CULL_TOP),
                      wait_frames: int = CULL_WAIT_FRAMES) -> dict[str, Any]:
    """Every ``wait_frames``: track the camera; only when its clamped top row
    changed, (de)activate each actor once. Idle cost: one position read, one
    expression and one compare per loop.

    ``event(command, args, key)``, ``branch_event(command, args, key, true, false)``,
    ``set_value(variable, value, key)`` and ``wait_event(frames, key)`` are the
    scene's builders (event IDs stay in its namespace). ``actors`` are actor
    resources: ``y`` is the anchor row, ``symbol`` names the branch, ``id`` is activated.
    """
    var_x, var_y, var_cam, var_top = variables
    above, below = CAMERA_DEADZONE_ROWS
    hero_y = _var(var_y)

    def get_position(suffix: str) -> dict[str, Any]:
        return event("EVENT_ACTOR_GET_POSITION", {
            "actorId": "player", "vectorX": var_x, "vectorY": var_y, "units": "tiles",
        }, f"{key}:{suffix}")

    track = event("EVENT_SET_VALUE", {
        "variable": var_cam,
        "value": _op("max", _op("sub", hero_y, _number(above)),
                     _op("min", _var(var_cam), _op("sub", hero_y, _number(below)))),
    }, f"{key}:camera-track")
    clamped = _op("max", _number(0), _op("min", _number(max_top), _var(var_cam)))
    apply = [event("EVENT_SET_VALUE", {"variable": var_top, "value": clamped}, f"{key}:apply-top")]
    for actor in actors:
        condition = cull_condition(int(actor["y"]), max_top, var_top)
        if condition is None:
            continue
        name = actor["symbol"]
        apply.append(branch_event("EVENT_IF", {"condition": condition}, f"{key}:{name}", [
            event("EVENT_ACTOR_ACTIVATE", {"actorId": actor["id"]}, f"{key}:{name}:on"),
        ], [
            event("EVENT_ACTOR_DEACTIVATE", {"actorId": actor["id"]}, f"{key}:{name}:off"),
        ]))
    changed = branch_event("EVENT_IF", {"condition": _op("ne", clamped, _var(var_top))},
                           f"{key}:changed", apply)
    body = [get_position("hero-position"), track, changed, wait_event(wait_frames, f"{key}:wait")]
    start = [
        get_position("start-position"),
        event("EVENT_SET_VALUE", {
            "variable": var_cam, "value": _op("sub", hero_y, _number((above + below) // 2)),
        }, f"{key}:camera-start"),
        set_value(var_top, -1, f"{key}:top-start"),
        {**event("EVENT_LOOP", {}, f"{key}:loop"), "children": {"true": body}},
    ]
    return {**event("EVENT_THREAD_START", {"variable": handle}, f"{key}:thread"),
            "children": {"true": start}}
