# Level redesign: multi-scene jobs (spec, 2026-10-30)

Status: **design spec, not implemented.** Target: the round after 0.18.0-dev.
Author: art-direction / level-design pass requested by Abe ("multi-level and
multi-scene ... make the game layout much more efficient ... leverage the
assets we've created so far"). Implementation follows §7; nothing here is
verified in a ROM yet.

Every map below was checked by a scratch validator that applies the contracts'
own rules (`grid_chain.stands`, three-tile standing gaps between lanes, 5-tile
landing clearance, head room, transformer footing, `test_routes` jump model:
rise 3 per tap, run 4) plus actor, trigger, OAM-window and scanline budgets.
WP0 ports those rules into the shared tests (§7), so the maps stay checked when
they become contract data.

## 0. Measured baseline (2026-10-30, worktree `feat/wind-ridge-lines`)

Counted from `project/scenes/*/actors|triggers` and MCP
`graphics_analyze_scene` (summary, after `project_refresh` strong).

| Scene | Size | Actors | Triggers | BG tiles (eff.) | BG slots | OBJ slots | Sprite tiles (meta) |
|---|---|---|---|---|---|---|---|
| service_opening | 20x18 | 3 | 1 | - | - | - | - |
| storm_climb | 20x36 | 15 | 25 | 88 | 7 | 7 | 160 |
| wind_ridge | 100x30 | 18 | 15 | **283** | 7 | 8 | 168 |
| signal_hill | 100x18 | 20 | 15 | 86 | 6 | 8 | 167 |
| pine_hollow | 100x18 | 20 | 15 | 185 | 6 | 8 | 168 |

Engine facts that shape this spec (read from the vendored GBVM,
`appData/engine/gbvm/src/core/actor.c` and `include/actor.h`):

- `MAX_ACTORS 21` (20 + hero). `MAX_ACTORS_ACTIVE 12` is defined but never
  enforced; the real limits are OAM (40 objects) and VM time per frame (B-18).
- An actor stays **active** while its 16px cell is within 48 px (6 tiles) of
  the screen on every side: a horizontal scene keeps a ~32-column window
  active, a vertical one a ~30-row window. Active actors draw even off screen.
  A screen-sized scene therefore has *every* actor active at once.
- Sprite VRAM is the quiet limit: each job scene already references ~160-168
  stored sprite tiles against a 128-192 pair budget (the 24px hero alone is 61).
  **No new sprite sheets in any scene**; new content is background art,
  palettes and placement.
- Static OAM estimates of 61-65 objects per horizontal scene today are
  "everything at once"; the per-window numbers in §5 are what matters.

## 1. Design pillars and difficulty curve

**Pillars**

1. *Read the line, then run it.* Each scene opens on a view of where the wire
   must go (pole left, transformer ahead). Wires stay continuous across scene
   edges, so the player always sees where power stops.
2. *One cable, one gauntlet.* Every carry crosses at least one hazard on the
   route, never an optional one. Hazards guard jumps and landings, not dead
   floor.
3. *Shapes, not just length.* Each job alternates scene shapes (vertical
   shaft, horizontal run, short finale), so a 5-line job feels like a journey
   rather than a longer corridor.
4. *Teach, then combine.* Each job adds exactly one new idea; everything
   learned before returns in tighter combinations.
5. *Budget per scene.* Splitting a job over 2-3 scenes gives every scene its
   own 20 actors, 30 triggers, 384 BG tiles and 8+8 palettes. Each scene uses
   about half of its budget, which leaves headroom and keeps VM load low (B-18).

**Curve**

| Step | New idea (one at a time) | Combines | Hazards | Scenes |
|---|---|---|---|---|
| Opening (service_opening) | walk, A-tap, B on a panel | - | 0 | 1 (unchanged) |
| Amara (job 1) | one hazard per climb shelf: board, hidden cable, whip, span arc, gust; **the cable crosses a scene edge** (short, last line only) | gust + arc on the crest | 14 (was 9) | 2 |
| Hiroshi (job 2) | **long cross-scene carry** (line 3 rides from the ridge into the saddle); gusts guard the taps | board on every landing; floor gust punishes a fall | 16 (was 11) | 2 |
| Priya (job 3) | **Down+A descent is mandatory**: the gully is one-way timber all the way down, carried cable in hand; two cross-scene carries | live arc + span arc on one floor, whip over the descent | 20 (was 13) | 3 |
| Emil (job 4) | **the long climb out**: carry 5 rises two decks *and* crosses an edge; tightest timings | everything on every shelf, two hidden cables in one shaft | 27 (was 13) | 3 |

Timing tiers stay where the contracts already have them, ramping job by job
(frames at 60 fps):

| Job | Gust warn/active/rest | Arc warn/active/rest | Whip sway/swing/hang | Hidden cable dark/warn/arc |
|---|---|---|---|---|
| Amara (`climb.py`) | 50/22/80 | 48/24/80 (`rosa.ARC_*`) | 40/22/62 | 150/20/24 |
| Hiroshi (`ridge.py`) | 48/22/70 | 42/24/60 | 40/22/62 | 150/20/24 |
| Priya (`rosa.py`) | 44/22/62 | 40/24/52 | 36/22/54 | 140/20/24 (new) |
| Emil (`kiko.py`) | 44/24/58 | 36/26/48 | 36/24/46 | 120/20/26 (new) |

Per-job cable timings need `hazards.cable_update_script` to take them as
arguments; today they are module constants.

## 2. Scene breakdown

### Flow

```text
logo -> story -> title -> service_opening --awning--> [WO 1]
  -> 1A storm_climb (20x36) --summit--> 1B climb_crest (56x18) --porch--> [WO 2]
  -> 2A wind_ridge (64x18) --F ledge--> 2B ridge_saddle (64x18) --porch--> [WO 3]
  -> 3A signal_hill (64x18) --summit--> 3B signal_gully (20x36, down) --floor--> 3C signal_porch (40x18) --porch--> [WO 4]
  -> 4A pine_hollow (64x18) --shelf--> 4B pine_ladder (20x36, up) --top--> 4C pine_rim (56x18) --porch--> storm_report -> title
```

Existing scene IDs keep their folders and roles as the job's **entry scene**,
so `tickets.TICKETS[n]["scene_id"/"start"]` needs no change. `wind_ridge`
shrinks from 100x30 to 64x18 under the same scene and background IDs. Six new
scenes: `climb_crest`, `ridge_saddle`, `signal_gully`, `signal_porch`,
`pine_ladder`, `pine_rim`.

Internal exits (between scenes of one job) are ungated, both directions. Each
pair is a 1x3 trigger on the edge column and an entry tile at least 2 columns
inside the destination, never inside the destination's own exit (B-05 and the
`147c23be` loop lesson). Exits stay first in trigger order. The exit to the
next job's work order keeps today's gate (the neighbour's home variable) and
its text-only refusal.

### Map legend (tile scale, rows top-down, column ruler on top)

`#` solid rock · `=` one-way timber · `b` cracked board (plank row) ·
`~` gust lane · `w` whip lane · `z` arc lane (fallen span or free live arc) ·
`h` hidden cable lane (all lanes on the hero's **chest** row, 2 rows above the
surface) · `1`-`5` pole Pn feet tile, `|` its 32px body · `A`-`E` transformer
T1-T5 feet tile, `t` its 16x24 background art · `c` checkpoint (respawn once
that line is live) · `N` neighbour · `o` house device · `H` house · `d` door ·
`S` start (entry from upstream) · `e` entry from downstream · `X` exit
trigger. HUD covers rows 0-1. Run scenes: floor row 15 (feet 14), step 12 (11),
high 9 (8), top 6 (5). Shafts reuse the climb's deck rows (decks 27/21/15/9 with
slabs x1-5 and x14-18 and a one-way walk x6-13; ledges 30/24/18/12).

### Job 1 - Amara's hilltop (2 scenes)

Keep the climb Abe loved almost as it is. Lines 1-4, their transformers and
all nine hazards stay where they are in `climb.py`. Only the summit changes:
Amara, her house, T5 and her door move up into a new finale scene. Line 5's
pole stays on the L8 deck (2,8). Its cable is the game's **first cross-scene
carry**: about one screen up through the summit exit, then across a windy
crest to Amara's porch. That adds a fifth "deck" of difficulty without
crowding the shaft.

#### 1A storm_climb (20x36)

```text
    0         1         
    01234567890123456789
 0  #..................#
 1  #..................#
 2  #................X.#
 3  #................X.#
 4  #................X.#
 5  #.|....==========..#
 6  #.|..............tt#
 7  #.|.....~~~......tt#
 8  #.5............c.Dt#
 9  ######=====bbb######
10  ######..ww....######
11  #...............|..#
12  #.tt..=======...|..#
13  #.tt............|..#
14  #.Ctc...........4..#
15  ######===bbb==######
16  ######..~~~...######
17  #.|................#
18  #.|....=======..tt.#
19  #.|....zz.......tt.#
20  #.3...........c.Bt.#
21  ######========######
22  ######...ww...######
23  #...............|..#
24  #.tt..=======...|..#
25  #.tt............|..#
26  #.Atc...........2..#
27  ######=bbb====######
28  ######...hh...######
29  #....|.............#
30  X....|.=======.....#
31  X....|.............#
32  X.S..1.............#
33  ===================#
34  ####################
35  ####################
```

Lines: L1 pole (5, 32) box (2, 26) checkpoint (4, 26); L2 pole (16, 26) box (16, 20) checkpoint (14, 20); L3 pole (2, 20) box (2, 14) checkpoint (4, 14); L4 pole (16, 14) box (17, 8) checkpoint (15, 8); L5 pole (2, 8).  
Hazards (9): board r27 x7-9, board r15 x9-11, board r9 x11-13, cable r28 x9-10, whip r22 x9-10, whip r10 x8-9, gust r16 x8-10, gust r7 x8-10, arc r19 x7-8.  
Triggers: to service_opening (0, 30, 1, 3), to climb_crest (17, 2, 1, 3).  
Validator: OK; actors 14 {'pole': 5, 'board': 3, 'cable': 1, 'whip': 2, 'gust': 2, 'arc': 1}; zone/exit/board triggers 22; worst OAM window 47+4 hero; worst scanline 9 (hero incl.).

1A changes from today: remove Amara's actor, house art, T5 art and door
trigger, and drop her NPC zone. The summit exit `(17,2,1,3)` now switches to
1B `(3,8)` instead of the Ridge work order (no gate). Stage 5's wire leaves the
top-right toward the crest. The culling thread stays (worst window 47+4 OBJ
without it). The 4-row summit leap is unchanged (`max_rise 4` there, as today).

#### 1B climb_crest (56x18)

```text
    0         1         2         3         4         5     
    01234567890123456789012345678901234567890123456789012345
 0  ........................................................
 1  ........................................................
 2  #......................................................#
 3  #......................................................#
 4  #......................................................#
 5  #.............................................HHHH.....#
 6  #X............................................HHHH.....#
 7  #X...............................ww...........HHHH.....#
 8  #X.S..........................................HHHH.....#
 9  #######..................=bbb=========.tt.....HHHH....X#
10  #######..............~~~...............tt.....HHHH....X#
11  #######................................Etc...NHdHH....X#
12  #######.............#####.............##################
13  #######....zz...hh..#####.............##################
14  #######.............#####.............##################
15  ########################################################
16  ########################################################
17  ########################################################
```

Lines: L5 box (39, 11) checkpoint (41, 11).  
Hazards (5): arc r13 x11-12 [span live_after=4], cable r13 x16-17, gust r10 x21-23, board r9 x26-28, whip r7 x33-34.  
Neighbour (45, 11), house x46-49 door (47, 11).  
Triggers: back to storm_climb (1, 6, 1, 3), to work order 2 (54, 9, 1, 3).  
Validator: OK; actors 6 {'npc': 1, 'arc': 1, 'cable': 1, 'gust': 1, 'board': 1, 'whip': 1}; zone/exit/board triggers 6; worst OAM window 16+4 hero; worst scanline 9 (hero incl.).

1B is the end of carry 5. The fallen span on the floor goes live once lines
1-4 are repaired, so it always arcs during this carry. Then a hidden cable
before rock B, a gust on top of rock B guarding the tap onto catwalk C, a board
on C's landing and a whip at C's end, then the drop onto the porch. Amara's
house reuses the climb's house drawing (`make_climb_art._draw_house`) at porch
height. Door = Amara's checkpoint (var 0). The porch exit to WO 2 is gated on
var 0, as the summit exit is today.

### Job 2 - Hiroshi's ridge (2 scenes)

The theme is wind. Gusts guard every tap, and a fall to the floor runs into a
floor gust. The new idea is the **long cross-scene carry**: line 3's pole stands
on rock C in 2A. Its transformer is the first thing in 2B, past a hidden cable
at the bottom of the arrival drop.

#### 2A wind_ridge (64x18)

```text
    0         1         2         3         4         5         6   
    0123456789012345678901234567890123456789012345678901234567890123
 0  ................................................................
 1  ................................................................
 2  #..............................................................#
 3  #..............................................................#
 4  #..............................................................#
 5  #...................|..........................................#
 6  #...............tt..|.........................................X#
 7  #...............tt..|.....................hh...~~~...ww.......X#
 8  #.....|.........Atc.2...................|.....................X#
 9  #.....|..bbb===######...............tt..|.===============.bbb=.#
10  #.....|........######...............tt..|......................#
11  #.....1........######...............Btc.3......................#
12  #....###.......######..............######......................#
13  #....###....ww.######.....zz...hh..######........~~~...........#
14  #.S..###.......######..............######......................#
15  ################################################################
16  ################################################################
17  ################################################################
```

Lines: L1 pole (6, 11) box (16, 8) checkpoint (18, 8); L2 pole (20, 8) box (36, 11) checkpoint (38, 11); L3 pole (40, 11).  
Hazards (9): board r9 x9-11, whip r13 x12-13, arc r13 x26-27 [span1 live_after=1], cable r13 x31-32, cable r7 x42-43, gust r7 x47-49, whip r7 x53-54, gust r13 x49-51, board r9 x58-60.  
Triggers: to ridge_saddle (62, 6, 1, 3).  
Validator: OK; actors 12 {'pole': 3, 'board': 2, 'whip': 2, 'arc': 1, 'cable': 2, 'gust': 2}; zone/exit/board triggers 8; worst OAM window 21+4 hero; worst scanline 9 (hero incl.).

2A notes: the scene is 64x18 (was 100x30). Without the 12 rows of sky it drops
well under the 283 tiles it uses today. Only the high catwalks lead to the F
ledge and the exit `(62,6,1,3)`; the floor under D1 is a fall penalty with a
gust and a way back up onto rock C.

#### 2B ridge_saddle (64x18)

```text
    0         1         2         3         4         5         6   
    0123456789012345678901234567890123456789012345678901234567890123
 0  ................................................................
 1  ................................................................
 2  #....................................|.........................#
 3  #................................tt..|.........................#
 4  #................................tt..|.........................#
 5  #................................Dtc.5....................HHHH.#
 6  #X..............................######....................HHHH.#
 7  #X........................~~~...######.....ww.............HHHH.#
 8  #XS...............|.............######....................HHHH.#
 9  #####.........tt..|.=bbb========######bbb=======....tt....HHHHX#
10  #####.........tt..|.............######..............tt....HHHHX#
11  #####.........Ctc.4.............######.............cEt....NdoHX#
12  #####........######.............######............##############
13  #####....hh..######.............######....zz...~~~##############
14  #####........######.............######............##############
15  ################################################################
16  ################################################################
17  ################################################################
```

Lines: L3 box (14, 11) checkpoint (16, 11); L4 pole (18, 11) box (33, 5) checkpoint (35, 5); L5 pole (37, 5) box (52, 11) checkpoint (51, 11).  
Hazards (7): cable r13 x9-10, board r9 x21-23, gust r7 x26-28, board r9 x38-40, whip r7 x43-44, arc r13 x42-43 [span2 live_after=4], gust r13 x47-49.  
Neighbour (58, 11), device (60, 11), house x58-61 door (59, 11).  
Triggers: back to wind_ridge (1, 6, 1, 3), to work order 3 (62, 9, 1, 3).  
Validator: OK; actors 11 {'pole': 2, 'npc': 1, 'device': 1, 'cable': 1, 'board': 2, 'gust': 2, 'whip': 1, 'arc': 1}; zone/exit/board triggers 10; worst OAM window 26+4 hero; worst scanline 10 (hero incl.).

2B notes: the arrival rock is at feet 8 (same tier as F). Line 4 climbs to the
summit D; line 5 drops onto catwalk E (board on the landing, whip). Its floor
alternative has fallen span 2 (live after 4) and a gust in front of the porch.
Hiroshi's porch keeps today's layout rules: box, 4 clear tiles, Hiroshi, door,
concentrator, and the exit sorted before the door (B-05).

### Job 3 - Priya's signal hill (3 scenes)

Up the hill, over the top, down the gully. The new idea is the **mandatory
Down+A descent with a cable in hand**. Every deck in 3B is slab + one-way walk
across the full width, so the only way down is a drop-through tap. B-07's
one-shelf drop (`DROP_FRAMES_MAX` 7) keeps each tap to one shelf. 3A keeps
Priya's own hazard, the free-standing live arc, and the upper walk U doubles the
floor route (whip above, span arc and hidden cable below).

#### 3A signal_hill (64x18)

```text
    0         1         2         3         4         5         6   
    0123456789012345678901234567890123456789012345678901234567890123
 0  ................................................................
 1  ................................................................
 2  #..............................................................#
 3  #.............................................................X#
 4  #......................................................ww.....X#
 5  #.................|...........................................X#
 6  #.............tt..|...............................##############
 7  #.............tt..|.......ww.................~~~..##############
 8  #...|.........Atc.2...................|...........##############
 9  #...|..bbb===######============...tt..|=bbb=======##############
10  #...|........######...............tt..|...........##############
11  #...1........######...............Btc.3...........##############
12  #..###.......######..............######...........##############
13  #..###....zz.######.....zz...hh..######...........##############
14  #.S###.......######..............######...........##############
15  ################################################################
16  ################################################################
17  ################################################################
```

Lines: L1 pole (4, 11) box (14, 8) checkpoint (16, 8); L2 pole (18, 8) box (34, 11) checkpoint (36, 11); L3 pole (38, 11).  
Hazards (8): board r9 x7-9, arc r13 x10-11 [live arc], whip r7 x26-27, arc r13 x24-25 [span1 live_after=1], cable r13 x29-30, board r9 x40-42, gust r7 x45-47, whip r4 x55-56.  
Triggers: to signal_gully (62, 3, 1, 3).  
Validator: OK; actors 11 {'pole': 3, 'board': 2, 'arc': 2, 'whip': 2, 'cable': 1, 'gust': 1}; zone/exit/board triggers 8; worst OAM window 22+4 hero; worst scanline 9 (hero incl.).
#### 3B signal_gully (20x36)

```text
    0         1         
    01234567890123456789
 0  #..................#
 1  #..................#
 2  X..................#
 3  X..................#
 4  X.S................#
 5  #=========.........#
 6  #...............tt.#
 7  #...............tt.#
 8  #.............c.Ct.#
 9  ######========######
10  ######..ww....######
11  #.|................#
12  #.|...=======......#
13  #.|................#
14  #.4................#
15  ######==bbb===######
16  ######...~~~..######
17  #..................#
18  #......=======.....#
19  #......zz..........#
20  #..................#
21  ######========######
22  ######....hh..######
23  #..................#
24  #.....=======...tt.#
25  #...............tt.#
26  #.............c.Dt.#
27  ######===bbb==######
28  ######.ww.....######
29  #..|...............#
30  #..|...=======.....X
31  #..|........~~~....X
32  #..5.............e.X
33  #==================#
34  ####################
35  ####################
```

Lines: L3 box (16, 8) checkpoint (14, 8); L4 pole (2, 14) box (16, 26) checkpoint (14, 26); L5 pole (3, 32).  
Hazards (8): whip r10 x8-9, board r15 x8-10, gust r16 x9-11, arc r19 x7-8 [span3 live_after=3], cable r22 x10-11, board r27 x9-11, whip r28 x7-8, gust r31 x12-14.  
Triggers: back to signal_hill (0, 2, 1, 3), to signal_porch (19, 30, 1, 3).  
Validator: OK; actors 10 {'pole': 2, 'whip': 2, 'board': 2, 'gust': 2, 'arc': 1, 'cable': 1}; zone/exit/board triggers 8; worst OAM window 32+4 hero; worst scanline 8 (hero incl.).

3B notes: enter at the top-left (2,4) carrying cable 3. Walk off the arrival
shelf onto deck 9, where T3 stands on the right slab. Then drop through, deck
by deck: pole 4 is on deck 15's left slab and T4 on deck 27's right slab. Pole
5 waits on the floor at the bottom-left, and its cable leaves through the
bottom-right exit `(19,30,1,3)` into 3C. Going back up uses the climb's own
moves (4-row leap onto the arrival shelf). Worst OAM window 32+4, so no
culling thread is needed.

#### 3C signal_porch (40x18)

```text
    0         1         2         3         
    0123456789012345678901234567890123456789
 0  ........................................
 1  ........................................
 2  #......................................#
 3  #......................................#
 4  #......................................#
 5  #...............................HHHH...#
 6  #...............................HHHH...#
 7  #...............................HHHH...#
 8  #...............................HHHH...#
 9  #.......=bbb=====.........tt....HHHH..X#
10  #....................~~~..tt....HHHH..X#
11  #.........................Etc...NdoH..X#
12  #X................######################
13  #X.....zz.....ww..######################
14  #XS...............######################
15  ########################################
16  ########################################
17  ########################################
```

Lines: L5 box (26, 11) checkpoint (28, 11).  
Hazards (4): arc r13 x7-8 [span5 live_after=4], board r9 x9-11, whip r13 x14-15, gust r10 x21-23.  
Neighbour (32, 11), device (34, 11), house x32-35 door (33, 11).  
Triggers: back to signal_gully (1, 12, 1, 3), to work order 4 (38, 9, 1, 3).  
Validator: OK; actors 6 {'npc': 1, 'device': 1, 'arc': 1, 'board': 1, 'whip': 1, 'gust': 1}; zone/exit/board triggers 5; worst OAM window 18+4 hero; worst scanline 9 (hero incl.).

3C is the end of carry 5 across the creek bed: span arc, board, floor whip,
then a gust on the rock that guards the tap onto the porch. Priya, workstation,
door and exit follow today's porch pattern.

### Job 4 - Emil's pine hollow (3 scenes, hardest)

Tightest timings, every hazard kind on every scene, two hidden cables in one
shaft. The new idea is **the long climb out**: 4B is a climb-style shaft. Line
4 rises two decks (whip, span arc, gust, board on the way), and line 5's pole
on deck 15 carries its cable up two more shelves and over the 4-row leap,
through the top exit into 4C.

#### 4A pine_hollow (64x18)

```text
    0         1         2         3         4         5         6   
    0123456789012345678901234567890123456789012345678901234567890123
 0  ................................................................
 1  ................................................................
 2  #..............................................................#
 3  #..............................................................#
 4  #..............................................................#
 5  #.....................|........................................#
 6  #.................tt..|........................................#
 7  #............hh...tt..|.....................~~~....ww..........#
 8  #....|............Atc.2..................|.....................#
 9  #....|..bbb=====#######..............tt..|.=============......X#
10  #....|..........#######..............tt..|....................X#
11  #....1..........#######..............Btc.3....................X#
12  #...###.........#######.............######...............=bbb=.#
13  #...###.........#######....zz...ww..######.....~~~...zz........#
14  #.S.###.........#######.............######.....................#
15  ################################################################
16  ################################################################
17  ################################################################
```

Lines: L1 pole (5, 11) box (18, 8) checkpoint (20, 8); L2 pole (22, 8) box (37, 11) checkpoint (39, 11); L3 pole (41, 11).  
Hazards (9): board r9 x8-10, cable r7 x13-14, arc r13 x27-28 [span1 live_after=1], whip r13 x32-33, gust r7 x44-46, whip r7 x51-52, gust r13 x47-49, arc r13 x53-54 [span2 live_after=2], board r12 x58-60.  
Triggers: to pine_ladder (62, 9, 1, 3).  
Validator: OK; actors 12 {'pole': 3, 'board': 2, 'cable': 1, 'arc': 2, 'whip': 2, 'gust': 2}; zone/exit/board triggers 8; worst OAM window 26+4 hero; worst scanline 10 (hero incl.).
#### 4B pine_ladder (20x36)

```text
    0         1         
    01234567890123456789
 0  #..................#
 1  #..................#
 2  #................X.#
 3  #..........hh....X.#
 4  #..............e.X.#
 5  #......==========..#
 6  #..................#
 7  #.......~~~........#
 8  #..................#
 9  ######=====bbb######
10  ######..ww....######
11  #...............|..#
12  #.tt..=======...|..#
13  #.tt............|..#
14  #.Dtc...........5..#
15  ######===bbb==######
16  ######..~~~...######
17  #..................#
18  #......=======.....#
19  #......zz..........#
20  #..................#
21  ######========######
22  ######...ww...######
23  #...............|..#
24  #.tt..=======...|..#
25  #.tt............|..#
26  #.Ctc...........4..#
27  ######=bbb====######
28  ######..hh....######
29  #..................#
30  X......=======.....#
31  X...........ww.....#
32  X.S................#
33  #==================#
34  ####################
35  ####################
```

Lines: L3 box (2, 26) checkpoint (4, 26); L4 pole (16, 26) box (2, 14) checkpoint (4, 14); L5 pole (16, 14).  
Hazards (11): cable r28 x8-9, whip r31 x12-13, board r27 x7-9, whip r22 x9-10, gust r16 x8-10, arc r19 x7-8 [span4 live_after=3], board r15 x9-11, whip r10 x8-9, gust r7 x8-10, board r9 x11-13, cable r3 x11-12.  
Triggers: back to pine_hollow (0, 30, 1, 3), to pine_rim (17, 2, 1, 3).  
Validator: OK; actors 13 {'pole': 2, 'cable': 2, 'whip': 3, 'board': 3, 'gust': 2, 'arc': 1}; zone/exit/board triggers 9; worst OAM window 41+4 hero; worst scanline 8 (hero incl.).

4B notes: worst window 41+4 OBJ. It reuses the climb's culling thread
(`climb.CULL_*`, vars 46-49 are scratch and safe to share because only one
scene runs at a time). `make_climb_scene`'s culled-hazard variant (every live cycle starts safe)
applies to its timed hazards.

#### 4C pine_rim (56x18)

```text
    0         1         2         3         4         5     
    01234567890123456789012345678901234567890123456789012345
 0  ........................................................
 1  ........................................................
 2  #......................................................#
 3  #......................................................#
 4  #......................................................#
 5  #..............................................HHHH....#
 6  #X......................#####..................HHHH....#
 7  #X.............hh...~~~.#####....ww............HHHH....#
 8  #X.S....................#####..................HHHH....#
 9  ######..=bbb===========.#####==========..tt....HHHH...X#
10  ######..................#####............tt....HHHH...X#
11  ######..................#####............Etc...NdoH...X#
12  ######..................#####...........################
13  ######.....zz.....ww....#####.....~~~...################
14  ######..................#####...........################
15  ########################################################
16  ########################################################
17  ########################################################
```

Lines: L5 box (41, 11) checkpoint (43, 11).  
Hazards (7): arc r13 x11-12 [span5 live_after=4], board r9 x9-11, cable r7 x15-16, gust r7 x20-22, whip r13 x18-19, whip r7 x33-34, gust r13 x34-36.  
Neighbour (47, 11), device (49, 11), house x47-50 door (48, 11).  
Triggers: back to pine_ladder (1, 6, 1, 3), to storm report (54, 9, 1, 3).  
Validator: OK; actors 9 {'npc': 1, 'device': 1, 'arc': 1, 'board': 1, 'cable': 1, 'gust': 2, 'whip': 2}; zone/exit/board triggers 5; worst OAM window 21+4 hero; worst scanline 9 (hero incl.).

4C: the rim run to Emil's porch, with a floor gust under the second catwalk and
a whip above it. The report exit stays the last trigger to fire before the door
(B-05). `tickets.REPORT_EXIT` must point at 4C (see WP4).

## 3. Cross-scene rules (shared infrastructure)

1. **Job state resets once, at the job's start.** Today every job init zeroes
   its line variables, which would wipe progress on every internal transition.
   New rule: the entry scene resets the job's variables only when
   `tickets.VAR_TICKET` (16) equals the job number, then sets it to 0. The work
   order card leaves var 16 set, so this needs no change to `tickets.py`. Other
   scenes of the job never reset.
2. **Carrying across an edge.** Var 6 survives the switch. Every job scene's
   init: if var 6 != 0, set the hero's `Carry` state after
   `EVENT_PLAYER_SET_SPRITE`. Pole init becomes deterministic from the
   variables: live -> `Standing`; var 6 == this line -> `Snapped`;
   else `Snapped+Cable`. This replaces today's blanket "pin Snapped+Cable on
   every entry".
3. **Lines are global, actors are local.** Each contract line gains
   `"pole_scene"`/`"box_scene"`. `GridChain(scene=...)` builds pole actors,
   pole/box zones and box custom scripts only for its own scene's lines. The
   chain refresh and HUD stay global. `cable_drop_events` clears var 6 for any
   line but sets a pole state only when that pole is in this scene.
   `check_chain_order` compares `(scene order, x)`.
4. **Respawn per scene**: the checkpoint of the furthest repaired line whose
   checkpoint is in this scene, else this scene's upstream entry (`S`). A death
   drops the cable home to its pole even in the other scene; the respawn is
   always within a screen or two of that scene edge.
5. **Wires cross edges.** Each cross-scene stage has an `edge_port` row,
   shared by both scenes' contracts and drawn to the map edge on both sides.
   The job's chain palettes (stages 0-5, BG slots 5 and 6) are one set of
   resources used by all of that job's scenes.
6. **Music and text**: only the fresh job start plays the job track and the
   intro lines. Other scenes do not call `EVENT_MUSIC_PLAY`, which avoids a
   restart on every edge (verify natively; see risks). Exits lift the HUD
   cutoff and hide the overlay before switching, as today.
7. **One link table.** A new stdlib `tools/scene_links.py` owns every scene
   link: (from folder, trigger rect, to folder, entry tile, facing, gate var).
   Exits and entries come from it, so job generators stop importing each
   other's exit constants (`ridge.CLIMB_SUMMIT_EXIT`, `rosa.RIDGE_EXIT`,
   `kiko.HILL_EXIT`). A test checks symmetry, standable entries, the 2-column
   spacing and gate variables.

## 4. Asset reuse plan

Sprites (no new sheets; OBJ slot map unchanged in every scene: 0 hero, 1
neighbour, 2 grid/device, 3 arc, 4 board, 5 gust, 6 whip, 7 pole):

| Asset (assets/sprites) | Generator | Used in |
|---|---|---|
| `opening_worker24.png` (hero, Carry/Shock states) | `make_opening_characters.py` | all |
| `intro_pole.png` (Standing / Snapped / Snapped+Cable) | `make_intro_sprites.py` | every scene with a pole |
| `whip_wire.png` | `make_whip_sprite.py` | all job scenes |
| `climb_gust.png` | `make_climb_gust.py` | all job scenes |
| `live_arc.png` (span arcs, hidden cables, Priya's free arc) | `make_rosa_sprites.py` | all job scenes |
| `cracked_board.png` | `make_hazard_sprites.py` | all job scenes |
| `opening_marta.png` (Amara) | `make_opening_characters.py` | 1B |
| `tomas.png`, `oxygen_concentrator.png` | `make_tomas_sprites.py` | 2B |
| `rosa.png`, `rosa_workstation.png` | `make_rosa_sprites.py` | 3C |
| `kiko.png`, `kiko_stove.png` | `make_kiko_sprites.py` | 4C |

Backgrounds (each job's art generator renders all of its scenes; the
transformer is `tools/transformer_art.py` everywhere):

| Scene | Background | Source to reuse |
|---|---|---|
| 1A | `storm_climb.png` (same id) | `make_climb_art.py`, minus house/T5, plus top-right wire exit |
| 1B | `climb_crest.png` (new) | `make_climb_art` sky, stone, timber, `_draw_house`; run-scene layout from `make_ridge_art.py` |
| 2A, 2B | `wind_ridge.png` (same id, 64x18), `ridge_saddle.png` | `make_ridge_art.py` (porch/house art moves to 2B) |
| 3A, 3C | `signal_hill.png` (same id), `signal_porch.png` | `make_rosa_art.py` (porch/house to 3C) |
| 3B, 4B | `signal_gully.png`, `pine_ladder.png` | climb shaft drawing extracted to `tools/shaft_art.py` (WP0), with each job's palette/motif pass |
| 4A, 4C | `pine_hollow.png` (same id), `pine_rim.png` | `make_kiko_art.py` (porch/house to 4C) |

Palettes: the BG slot layout of `opening.BG_PALETTES` (0 night, 1 stone, 2
timber, 3 window, 4 foliage, 5-6 wire stages, 7 UI) and each job's existing
chain palettes. No new palette resources except the per-job chain palette
reuse in new scenes (same IDs).

**Minimal new art (one Sonnet art worker, one preview sheet each):**

- *Shaft dressing, 3B "signal gully"*: wet slate slabs (stone slot), a
  rope-and-plank look on the one-way walks so "drop through here" reads, and a
  thin radio mast silhouette in the night slot behind the upper decks.
  Avoid faint 2px detail; the drop-through walks must read clearly against the
  slabs.
- *Shaft dressing, 4B "pine ladder"*: pine trunks behind the slabs (foliage
  slot 4) and darker sky, so the hidden-cable sparks pop. The four upper
  timbers use the existing plank tile so boards still hide in the BG.
- *Edge markers (every internal exit)*: a 2x3-tile "path continues" motif
  (timber arch / cave mouth / signpost) plus the wire continuing to the map
  edge on its `edge_port` row. These are BG tiles only.
- *Crest backdrop (1B)*: Amara's house at porch height with the town lights
  below in the night slot. Reuse the title's village-silhouette idea
  (`make_intro_art.make_title`) as a distant row.

## 5. Budget per scene (proposal; validator numbers)

OBJ counts use the contracts' footprints: pole/whip/neighbour 4 objects (2
columns), gust/board 3 (3 columns), arc/cable/device 2. "Window" is the worst
sum over the active-actor window (32 columns, or 30 rows in a shaft), hero
excluded (+4). Scanline is the worst tile row on one 20-column screen, hero (2)
included (limit 10). BG tiles are estimates from the measured baselines;
WP acceptance replaces them with `graphics_analyze_scene` numbers.

| Scene | Size | Actors (poles/NPC+device/hazards) | Triggers | Window OBJ | Worst scanline | BG tiles (est.) | BG / OBJ slots |
|---|---|---|---|---|---|---|---|
| 1A storm_climb | 20x36 | 14 (5/0/9) | 22 | 47+4, culled | 9 | ~85 | 7 / 7 |
| 1B climb_crest | 56x18 | 6 (0/1/5) | 6 | 16+4 | 9 | ~110 | 7 / 7 |
| 2A wind_ridge | 64x18 | 12 (3/0/9) | 8 | 21+4 | 9 | ~170 | 7 / 7 |
| 2B ridge_saddle | 64x18 | 11 (2/2/7) | 10 | 26+4 | 10 | ~190 | 7 / 8 |
| 3A signal_hill | 64x18 | 11 (3/0/8) | 8 | 22+4 | 9 | ~70 | 6 / 7 |
| 3B signal_gully | 20x36 | 10 (2/0/8) | 8 | 32+4 | 8 | ~110 | 7 / 7 |
| 3C signal_porch | 40x18 | 6 (0/2/4) | 5 | 18+4 | 9 | ~70 | 6 / 8 |
| 4A pine_hollow | 64x18 | 12 (3/0/9) | 8 | 26+4 | 10 | ~150 | 6 / 7 |
| 4B pine_ladder | 20x36 | 13 (2/0/11) | 9 | 41+4, culled | 8 | ~120 | 7 / 7 |
| 4C pine_rim | 56x18 | 9 (0/2/7) | 5 | 21+4 | 9 | ~140 | 6 / 8 |

Every scene stays at 14 actors or fewer (limit 20) and 22 triggers or fewer
(30). The headroom pays for later ideas without another split.

## 6. The Lineman brand

- **Title** (done this round): the wordmark reads **LINEMAN** in its own bold
  4x6 glyphs (`make_intro_art.WORDMARK`, `WORDMARK_FONT`), between the same
  bolts, same slots (gold logotype band, metal subtitle "After the Storm",
  PRESS START blink slot 6, version slot 5). The title is 209 tiles of 256.
  `intro.TITLE_ROWS["MR CFE"]` keeps its key for now (another session owns
  `intro.py`); rename it to `"LINEMAN"` with `test_intro_background.py` later.
- **Story**: "One lineman." (already in `intro.SHOTS`).
- **Player-visible "CFE" left to rewrite** (owner: coordinator):
  `tools/tickets.py:111` "Thank you,\nMister CFE!" (storm report) and
  `tools/make_climb_scene.py:885` "Thank you, CFE!" (Amara; it moves to 1B).
  Suggestions: "Thank you,\nLineman!" and "Thanks, lineman!" (both <= 17
  chars). Legacy only, not shipped: `tools/village.py:194`.
- **HUD**: keep `LINE n/5 HOME n/1`, the line-crew vocabulary itself.
- **Work order card**: the dispatch page could read "LINE CREW\nWO-0412";
  the card's bolt badge already brands it without text.
- **Logo**: Abe's Games logo unchanged.
- Not player-facing but visible on a cart menu/file list: ROM header title
  `MRCFE` (project name) and release file names `mr-cfe-<ver>.gbc`
  (`make_release.py`). Renaming is an open question.

## 7. Implementation plan (work packages)

Phase A is serial (one worker or main). Phase B runs up to five workers in
parallel with disjoint files. Phase C is main only (builds, emulator, preview).

### WP0 - shared infrastructure (first; Luna/Haiku, main reviews)

Files: `tools/grid_chain.py`, `tools/scenes.py`, `tools/hazards.py`, new
`tools/scene_links.py`, new `tools/shaft.py` (climb collision template +
cull-thread builder moved out of `make_climb_scene.py` / `climb.py`, re-exported
there unchanged), new `tools/shaft_art.py` (deck/ledge/slab/post drawing moved
out of `make_climb_art.py`), `tools/test_routes.py` (made data-driven: each
contract exposes `ROUTE_SCENES`; adds the validator rules from this doc:
lane spacing, landing clearance, head room, transformer footing, entry
standability, OAM window, scanline), `tools/test_grid_chain.py`,
`tools/test_scenes.py`, `tools/make_project.py` (profiles list the new
generators).

- grid_chain: rules 1-5 of §3 (`job_reset_events`, `carry_restore_events`,
  `pole_init_events`, scene-local `GridChain`, scene-aware drop/respawn/order checks).
- scenes.py: register the six new folders (editor positions proposal:
  climb_crest (240,0), ridge_saddle (400,600), signal_gully (800,600),
  signal_porch (800,960), pine_ladder (1200,600), pine_rim (1200,960)). IDs from
  each job's `resource_id("scene:<folder>")`.
- hazards.py: add the new scene keys with the board / hidden-cable placements
  and delays from §2 (job workers never edit hazards.py). Add per-job cable
  timings as parameters.

Acceptance: every existing profile regenerates **byte-identically** (pure
refactor, new keys unused). Full suite passes. `test_scene_links` symmetry and
spacing tests pass on a links table describing today's game.

### WP1 - Amara (climb profile; Luna/Haiku)

Files: `tools/climb.py` (+ a `CREST` section), `tools/make_climb_scene.py`, new
`tools/make_crest_scene.py`, `tools/test_climb*.py`, new `tools/test_crest.py`.
Art: `tools/make_climb_art.py` (1A edits + 1B) by the art worker.
Acceptance: §2 maps as contract data. 1A keeps lines 1-4 and its hazards
byte-for-byte; climb tests updated for lines 1-4 local + pole 5. Cross-scene
carry test: the init restores Carry and pole 5 `Snapped` when var 6 = 5. 1B
budgets as in §5; the porch exit is gated on var 0.

### WP2 - Hiroshi (ridge profile)

Files: `tools/ridge.py`, `tools/make_ridge_scene.py` (builds both scenes),
`tools/test_ridge.py`, `tools/test_ridge_background.py`. Art:
`tools/make_ridge_art.py` (art worker). Acceptance: 64x18 + 64x18 per §2. The
background ID is kept and the art regenerates at the new size. Wind Ridge's
BG tiles are measured below 200. The `ROUTE_SCENES` checks pass. Var 8/9/17/18/19/20/28/29 meanings
unchanged.

### WP3 - Priya (rosa profile)

Files: `tools/rosa.py`, `tools/make_rosa_scene.py` (3A, 3C) + new
`tools/make_gully_scene.py` (3B, built on `shaft.py`), `tools/test_rosa*.py`.
Art: `tools/make_rosa_art.py` (3A, 3C, and 3B via `shaft_art.py`). Acceptance:
a drop-through route test. From 3B's entry, every line target is reachable only
through one-way tiles (BFS with drop-through disabled fails). OAM window ≤ 40
without culling.

### WP4 - Emil (kiko profile)

Files: `tools/kiko.py`, `tools/make_kiko_scene.py` (4A, 4C) + new
`tools/make_ladder_scene.py` (4B, culling via `shaft.py`), `tools/test_kiko*.py`.
Art: `tools/make_kiko_art.py`. After the dialogue session lands: one-line
change of `tickets.REPORT_EXIT` / gate to 4C geometry (or move it into
`scene_links.py`). Acceptance: the culling OAM model ≤ 40 in 4B, hardest
timings asserted (each timing ≤ Priya's), report exit reachable from the last
checkpoint.

### WP5 - art (one Sonnet worker, after WP1-4 freeze their contracts' geometry)

Files: `make_climb_art.py`, `make_ridge_art.py`, `make_rosa_art.py`,
`make_kiko_art.py`, `shaft_art.py` (dressing only). Briefs in §4. One preview
sheet per job, viewed once. Acceptance: each background's tests pass, and
`graphics_analyze_scene` reports ≤ 384 effective tiles and no new palette slots.
Boards stay hidden planks in the BG. Wires reach the map edge on their
`edge_port` rows.

Ordering: WP0 -> (WP1-WP4 contracts, a short first step) -> WP5 in parallel
with the WP1-WP4 scene generators -> main regenerates every profile, runs the
full suite, `project_refresh` strong, `graphics_analyze_scene` on all 10
scenes, builds, and plays natively:

1. Amara's cross-scene carry, with a death in 1B.
2. One Down+A descent in 3B with a cable in hand.
3. The 4B culling at walk speed.
4. Each work-order hand-off.

Then the web preview for Abe.

## 8. Risks and open questions

**Risks**

- *Music restart on scene switch* is unverified (rule 6 assumes the track keeps
  playing). If it restarts, play only on fresh start (already the plan) and
  confirm natively.
- *Backtracking through the opening* re-runs work order 1 and resets Amara's
  job, as today. Gate the awning exit's ticket on `climb.VAR_CHAIN_LIVE == 0`
  (in `make_opening_scene.py`, owned by the dialogue session now).
- *Hero overlapping a one-way timber at an entry*: entries are placed on solid
  or clear tiles (validated). Native-check every link once.
- *Scanline 10 exactly* in 2B and 4A (one screen position each). It is legal,
  but there is no slack for the shock effect or a creaking board's extra frame.
- *ROM size*: six more scenes and backgrounds (~+60-100 KiB) in a 512 KiB ROM.
  Check the bank report after the first build.
- *Validator vs engine*: the jump model is coarse (no arc trace). Every new tap
  and drop still needs one native pass.

**Open questions for Abe**

1. OK to move Amara's house to a short crest scene above the climb (the climb
   itself stays as he liked it)?
2. Dying in another scene sends the carried cable back to its pole (current
   rule). Keep it, or let the cable stay in hand across scenes (easier)?
3. Scene transitions: keep the 2-speed fade, or a faster cut for internal
   edges?
4. Is **LINEMAN** right for the title (subtitle "After the Storm" kept)?
   Rename the cart header / release file names too?
5. Job lengths grow from 1 to 2-3 scenes (total gameplay area roughly +50%).
   Is that the right size, or should Priya/Emil stay at 2 scenes?
