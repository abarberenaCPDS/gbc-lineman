# Session handoff: Mister CFE (2026-10-26) — v0.10.3 stable (stream), v0.10.2 on the cart

Start a new session with: **"Read docs/HANDOFF.md and continue."**
`PROJECT_PLAN.md` is the long-term record (progress log, newest first).

## Read first

`AGENTS.md`, `CLAUDE.md`, the top of `docs/PROJECT_PLAN.md` and its progress log,
`docs/MCP_TOOLKIT.md` §5 (engine facts, including the new OBJ palette slot map and the
stale MCP index) and §8 (budget, worker rules). Load the `chromatic-budget-playtest` skill
before emulator work or spawning workers. VERSION `0.10.3` (tags `v0.10.3`, `stable`). Local-only repo; one-line
Conventional Commits, no AI attribution. Bugs: `docs/BUGS.md`.

## State

- **Committed:** speaker names + voices, 24px neighbours, animated storm poles, renamed
  neighbours, docs (see `git log`). `project/settings.gbsres` starts at the logo
  (`8f0deaff…`); never commit a `--test-start` override.
- **Cart:** v0.10.2 `86d3d954…` flashed 2026-10-26 (attract loop + B-14/B-15 fixes + v0.10.0 hazards/tickets). Flashing:
  later writes to that device need no new data-loss consent (given 2026-10-26), but
  always bind the exact ROM via `rom_inspect` and confirm Abe isn't mid-play.
- **Names:** Marta → **Amara** (Nigeria), Tomás → **Hiroshi** (Japan), Rosa → **Priya**
  (India), Kiko → **Emil** (Denmark). Code keys keep the old names on purpose.

## Done this burst (HANDOFF items 2–5)

2. Speaker names: `tools/voices.py`; `say(lines, key, speaker)` in each job generator.
3. Per-character voice pitch (Amara 660, Hiroshi 440, Priya 990, Emil 1320 Hz; narrator 880).
4. The intro pole sprite is each job's broken pole: Snapped → Standing when the line goes live (OBJ slot 7).
5. Bigger characters: three adults 24px, Emil 20px (a kid; easy to make 24 if Abe prefers).

## Open, in suggested order

0. **Cart verdict on v0.10.2:** Abe: "all looks fantastic" (overall; no per-item notes). If he reports specifics later, the open questions were board creak fairness (50 frames), hidden cables, work orders 1–4, CLOSED boxes, storm report → title. `climb_debris` sprite is unused and can be retired.
1. **Attract loop** shipped in v0.10.2 and covered by that verdict.
2. Names, sizes and poles: covered only by the overall verdict above.
3. Look items for Abe's pass: Emil's raised bowl is thin; Priya lost her glasses, so her
   only props now are long hair and a phone; Hiroshi's tube doubles as his cane. The
   storm pole's dangling wire overlaps the cable-end sprite on the same tile.
4. Known minor: B-06 junction reach. B-07 fixed in v0.10.3 (one shelf per Down+A, engine overlay); approved on stream ("v0.10.3 looks good"), not flashed, so the cart still runs v0.10.2.

Use parallel workers per the skill (art: Sonnet; plumbing: Haiku). Main selects the
project **before** spawning workers, gives plumbing workers the OBJ slot map, and
regenerates every profile + runs the full suite after they finish.

---

# Delta 2026-10-28 — v0.10.4 release build (stream-approved)

**This section is the current state. Everything above still describes 2026-10-26,
VERSION 0.10.3 and cart v0.10.2; it is kept as history, not superseded in place.**

- **VERSION `0.10.4`** (PATCH bump, no `-dev`), committed and tagged `v0.10.4`.
  `stable` still points at `v0.10.3`; move it only when Abe asks explicitly.
- **Abe on the v0.10.4 stream: “the gameplay is good”** — host-emulated stream only
  (Player 01, 120 s, saves off, ROM `f17df37b…`), not a cartridge/hardware verdict.
- **What landed:** the tree Abe approved was a rename/cleanup pass — `intro_logo` →
  `abes_games_logo`, `service_opening` → `service_opening_-_m-v1`, actor files renamed to
  the character names (`intro_hero` → `electrician`, `ridge_tomas` → `hiroshi_(wind_ridge)`,
  `signal_rosa` → `priya_(signal_hill)`, `pine_kiko` → `emil_(pine_hollow)`,
  `marta` → `amara_-_waiting_for_light`, …), plus deletion of the unused legacy `.uge`
  tracks (`cfe_main`, `cfe_lose`, `cfe_win`, `cfe_village_1..3`, `cfe_intro`).
  Resource **ids and symbols are unchanged** (12 scenes · 88 actors · 28 triggers), so
  every script reference still resolves. Title art was regenerated so the baked tag
  reads `v0.10.4`; project health is 0 errors / 0 warnings.
- **Cart:** still v0.10.2 `86d3d954…`. `f17df37b…` (v0.10.4) has **not** been flashed.

## Left to do, in suggested order

0. **Generator/test rename fallout — blocks clean verification.** `tools/test_intro.py`
   (4 errors) and `tools/test_voices.py` (1 error) still hardcode
   `project/scenes/intro_logo/…` and `service_opening/…`, and `intro.SCENES` in
   `tools/intro.py` still lists the old folder names — so `make_intro_scene.py` would
   recreate `intro_logo/` and duplicate the scene. Fix it by resolving scenes and
   resources through the stable `id`/`symbol` instead of folder paths, and update the
   folder names in `intro.py` / the opening generator. Keep `test_intro_background` and
   `test_engine_patch` green. **Do not rerun any scene generator until this is done.**
1. **Flash `f17df37b…`** to the cart when Abe asks — no new data-loss consent is needed
   for that device (given 2026-10-26), but bind the exact ROM via `rom_inspect`, confirm
   he isn't mid-play, and then get a cart verdict on v0.10.4.
2. **`stable` tag** — move to `v0.10.4` only on Abe's explicit approval (then
   `git tag -fa stable v0.10.4^{commit} -m "stable: v0.10.4 (ROM <sha>), <verdict>"`).
3. **Sprite metadata drift from the editor re-save (watch on the cart).** Eleven sprite
   `.gbsres` files had `numTiles` recomputed downward (`opening_worker24` 31 → 17,
   `player_platform` 20 → 12, `opening_worker16` 29 → 16, …) and four scenes had
   `_index` reordered, while the PNG pixel data is unchanged. The approved ROM is built
   from this exact state, so it is correct as committed; treat any sprite-sheet glitch on
   hardware as a suspect here first.
4. **Carried over unchanged:** B-06 junction reach; the look pass (Emil's thin raised
   bowl, Priya’s missing glasses, Hiroshi’s tube doubling as a cane, the pole’s dangling
   wire overlapping the cable-end sprite); `climb_debris` sprite is unused and can be
   retired.
