# Session handoff: Lineman — post-playtest feedback (2026-10-29)

> Historical feedback from October 29, 2026, with the game name updated to Lineman. Build names and worktree paths below identify that session; use [HANDOFF](HANDOFF.md) for the latest state.

Start a new session in the worktree `../gb-mr-cfe-wind-ridge` with:
**"Read docs/HANDOFF_FEEDBACK.md and start the next round."**
`docs/PROJECT_PLAN.md` is the long-term record (progress log, newest first); the previous
round's handoff is `docs/HANDOFF.md`.

## Read first

`AGENTS.md`, `CLAUDE.md`, top of `docs/PROJECT_PLAN.md`, `docs/BUGS.md` (B-17 fixed via
custom scripts, pending hardware confirmation of the box plug-in), `docs/MCP_TOOLKIT.md`
§5 (engine facts, OBJ palette slot map) and §8 (budget, worker rules). Load the
`chromatic-budget-playtest` skill before emulator work or spawning workers. Local-only repo;
one-line Conventional Commits, no AI attribution.

## State

- **2026-10-29 update — round implemented (0.17.0-dev, uncommitted):** all required items 1–5 and nice-to-haves 6–8 are built; see the newest `PROJECT_PLAN.md` log row. B-17 verified natively; B-18 (climb lag) fixed. Awaiting Abe's browser play of preview `e9bfa694…`. Open questions were decided by main (vertical bottom→top chain, brief shock flash, global difficulty with Pine hardest, carry variant C) — revisit if Abe disagrees.
- Branch `feat/wind-ridge-lines`, VERSION **0.16.0-dev** (working tree; not yet committed).
  `.mcp.json` is copied into the worktree (gitignored); `project_select` the worktree's
  `mr-cfe.gbsproj` first. If the MCP is missing, Abe runs `/mcp` to reconnect.
- Cart flashed and booted successfully with `build/rom/mr-cfe-0.16.0-dev.gbc`
  (524288 B, SHA256 `80fdc1b365e7acad8e1e5fdecf3f0e89f4d0b9223da54a8a63af4b32516cb7df`);
  Abe played it and gave the feedback below. Web preview was served at
  `http://127.0.0.1:53769/df4544eaf6828cb5af05bbe4c2d8b4dcd7ecb367f262624b1040461cbe6b7526/`
  (may have expired; reopen via `web_preview` recover/open).
- Phase 3 landed in the working tree: 5 lines per horizontal job (Wind Ridge, Signal Hill,
  Pine Hollow), full obstacle kit, dual wire BG slots, 100-tile maps, 13 triggers each,
  20 actors each, 474 tests pass. Storm Climb still has 1 line. Service opening (tutorial)
  untouched and obstacle-free.
- Phase 3 open item: B-17 (box plug-in) was broken on the first flash (deprecated
  `EVENT_ACTOR_INVOKE` used a shifted actor index). Fixed in source with 15 canonical
  synchronous custom scripts (`EVENT_CALL_CUSTOM_EVENT`); builds and tests pass. **Hardware
  confirmation of the plug-in on the flashed cart is still pending** — Abe's playtest feedback
  below does not mention it, so treat it as unverified and re-check first thing.
- Cart: physical hardware now runs 0.16.0-dev. Streams go through MCP `play`
  (`device list_devices` → `play`, `saveMode: none`); no stop command (kill the
  `chromatic-cli live-demo` pid if Abe says cancel). Flashing is destructive and needs a
  fresh device token + explicit consent.
- Names: Amara/Hiroshi/Priya/Emil on screen; code keys stay `marta`/`tomas`/`rosa`/`kiko`.
- Versioning (Abe): bump VERSION per landed phase. Phase 3 → 0.16.0-dev (in tree). This
  next round → propose **0.17.0-dev** when it lands. Bump in its own `chore(release)` commit,
  regenerate every profile (HUD label + title tag read VERSION), before any build/stream.

## Abe's feedback on 0.16.0-dev (verbatim intent, paraphrased)

### Required (gameplay)

1. **Amara's scene (storm_climb) is too thin.** It must get **all the obstacles we've designed**
   (cracked boards, hidden cables, timed gusts, fallen-span arcs, whipping cut cables) and the
   hero must **connect 5 lines before the scene/puzzle is complete**. Lines must show
   **continuity** (wire routes lighting up as the chain repairs) and include **transformers
   and swinging cut cables** to raise the challenge. (Today: 1 line, 3 cracked boards,
   1 hidden cable, 1 timed gust, no spans/whips/transformers beyond the single pole.)
2. **Hiroshi's scene (wind_ridge):** 5 lines is right; **increase difficulty**. **Change the
   transformer style near Hiroshi's house** to match the better-looking one (Priya's style)
   so all transformers are consistent. The **transformer/line is too close to Hiroshi's
   character — space it a bit.**
3. **Priya's scene (signal_hill):** the **transformer style here is the liked one — use it in
   all scenes** for consistency. The **swinging cut cables are good; add more of them** to
   raise difficulty. The **transformer is too close to Priya — add spacing.**
4. **Emil's scene (pine_hollow):** **too easy — increase difficulty.** Apply the same spacing
   fix (transformer/line too close to Emil).
5. **Music bug:** when a mission completes, the flow returns to the **intro screen but the
   music is not the intro's**. Fix the music selection on that transition.

### Nice to have

6. **Electrocution effect** when the hero is hurt and dies (he's a lineman; a shock/death
   animation and/or SFX would fit).
7. **Raise the difficulty level across all scenes** — harder, more challenging, more enjoyable.
8. **Carry-cable readability:** when the hero "carries" a cable, the sprites are not intuitive.
   Propose **3 UI/UX variants** for indicating a carried cable (and optionally sketch a scene).

## Standing constraints to respect

- Service opening (M-V1 tutorial) stays **obstacle-free** and is not an acceptance target for
  difficulty changes.
- Storm Climb is a **vertical 20×36 climb**, not a horizontal map. Adding 5 lines + continuity
  + transformers + whips there is a real design problem (vertical wire routing, scanline
  budget, 20-actor limit). Do not blindly copy the horizontal 5-line layout.
- Consistent OBJ palette slot map across job scenes (0 hero, 1 neighbour, 2 grid props,
  3 live arc/hidden cable, 4 cracked board, 5 gust, 6 whipping wire, 7 storm pole). A reused
  sprite needs the same slot free everywhere.
- Native B talk can double-fire with box actions; the new override-enabled dispatcher with
  explicit nearby-neighbour talk (native `EVENT_IF_ACTOR_DISTANCE_FROM_ACTOR`) is the
  accepted pattern. Do not revert to overlapping trigger zones.
- The engine change is the generated one-line overlay (`tools/make_engine_patch.py`); rerun
  after a GB Studio upgrade, never edit by hand.
- Dialogue ≤ 17 chars per line (`MAX_DIALOGUE_CHARS`).
- Never commit `--test-start` overrides; restore logo start before any commit/build/stream.
- Recording quota is full: use unrecorded native checks unless Abe authorizes archival; never
  remove old evidence.

## Suggested next moves

1. **First, verify B-17 on hardware** (still pending): boot the flashed cart, pick up a cable,
   press B at its box, confirm the line repairs (HUD count +1, chain refresh, "Power flows on").
   If it fails, this is the top priority before any new content.
2. **Design pass (strong model, e.g. Terra or Sonnet):** decide how Storm Climb gets 5 lines
   and continuity in a vertical map; decide transformer art unification (Priya's style everywhere);
   decide where extra whips go in Signal Hill (and possibly Pine Hollow) without breaking the
   10-sprites-per-scanline budget; propose 3 carry-cable UI variants (sketches or preview sheets).
   Get Abe's approval on the design before code.
3. **Implementation (Luna workers, up to 3 in parallel):** contracts first (`tools/climb.py`,
   `tools/ridge.py`, `tools/rosa.py`, `tools/kiko.py`, `tools/hazards.py`), then art generators,
   then scene generators, then tests. Main owns builds/emulator/preview/commits.
4. **Music fix:** find the transition that returns to the intro/title scene and make it use the
   intro theme (`compose_intro.py` / `song_cfe_intro` UGE), not the climb/village theme.
5. **Electrocution effect:** new sprite frames or palette flash + SFX; gate behind the existing
   group-1 contact reset so it doesn't freeze the player.
6. **Difficulty:** tune hazard timings/gaps/counts and landing clearance; re-run the full
   native OAM scanline checks and route playtests.
7. **Version:** bump to `0.17.0-dev` in its own `chore(release)` commit after the round lands,
   regenerate all profiles, then build/stream at Abe's request.

## Verification recipe (native)

`make_intro_scene.py --test-start <folder> X Y right` → `rom_build` with `captureDebugArtifacts`
→ `emulator_run debugMode: source` → keep the override while `emulator_debug` runs → restore
with a plain `make_intro_scene.py`. Each job scene opens with 2-3 dialogue boxes
(A + ~80 frames each). Player position: WRAM offset 4639, `[flags, x u16, y u16]`,
pixels = value >> 5 (y = feet row × 8). Arcs show as OAM palette 3 objects. Text-first;
screenshots only for looks. Each `rom_build` log is ~15k tokens: budget ~6 builds per session.

## Models and tokenomics

- Main session: strong model. Writes contracts, reviews worker output, catches design defects.
- Art/background workers: `openai/gpt-6.1-terra` (or Agent `model: "sonnet"` for first-seen
  visuals like characters/logo), higher effort, one preview sheet each, no render loops.
- Plumbing/scene/test workers: `openai/gpt-6-luna` (else Agent `model: "haiku"`), default
  effort. Up to 3-5 parallel, each owning its own files. Workers never call `project_select`,
  `rom_build`, `emulator_*` or `web_preview`; main owns those.
- Check state as text first (`emulator_inspect` memory/OAM, `emulator_debug` variables); take
  a screenshot only to judge a look.

## Open questions for Abe (decide before coding)

- Storm Climb: should the 5 lines be a vertical chain (power flows top-to-bottom or
  bottom-to-top) or a multi-area route? Wire continuity in a vertical map needs a decision.
- Carry-cable UI: pick among the 3 proposed variants before implementing.
- Electrocution: full death animation or a brief shock flash + SFX?
- Difficulty: should the increase be global (all scenes) or targeted (Emil first, since it's
  "too easy")?
- Music: confirm the intro theme is the desired one on the mission-complete→title transition.