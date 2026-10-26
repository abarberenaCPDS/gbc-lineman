# Session handoff: Mister CFE (2026-10-26, after Rosa's job)

Start a new session with: **"Read docs/HANDOFF.md and continue."**
Once this handoff's work is done, replace or delete this file. `PROJECT_PLAN.md` remains the
long-term status record.

## Read first

`AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_PLAN.md` (top, "Second repair job: Tomás's Wind
Ridge", progress log), `docs/redesign-brief.md`, `docs/action-climb-acceptance.md`,
`docs/MCP_TOOLKIT.md`. VERSION is `0.7.0-dev`. Local-only repo: never add a remote.
One-line Conventional Commits, no AI attribution.

## Current state

- Marta's line: complete. Abe: "I love it." / "I like it so far" (web `6831f908…`).
- Tomás's job (Wind Ridge): built and native-verified on exact ROMs (see PROJECT_PLAN).
  Contract `tools/ridge.py`; regenerate with
  `tools/make_project.py ridge --verify` (managed Python). Vars 8 (line live) and 9
  (home powered); the climb's summit exit (17,3) leads there only after var0=1.
- Release ROM `build/rom/mr-cfe.gbc` `54570c84…` (start scene: the opening).
- Browser export `build/web-tomas` (web ROM `1996a02b…`) is built but **not served**:
  `web_preview open` refused because the old Live Wire preview has an unresolved
  browser-recording close acknowledgement. Check `web_preview status`; ask Abe before
  doing anything that could discard a recording, then open `build/web-tomas`.
- Abe deferred cartridge flashing ("will flash later"). Hardware and Chromatic
  stream remain untested.

## Update: Rosa's job (Signal Hill) built

- Abe on Tomás's job: "works awesome" (browser) and "gameplay is awesome" (Chromatic stream).
- Rosa's job: contract `tools/rosa.py`, profile `tools/make_project.py rosa --verify`;
  vars 10/11; entry from the right end of Tomás's porch after var9=1. Full loop passed
  natively (`3dd78a6e…`); landing defect fixed (`089f7a44…`). Release ROM `31fd2ac6…`.
- Browser: `build/web-rosa` (web ROM `530b763a…`) served by a plain local server at
  http://127.0.0.1:50734/ because the MCP preview server is stuck on an unresolved
  browser-recording acknowledgement (restart the MCP server to clear it).
- Open: Abe's browser verdict on Rosa's job; native check of the ridge→hill exit and an
  arc hit; the arc Warning sparks may be too faint; next household Kiko's family (stove).
- Landing rule learned: walking/holding right off a 3-tile step lands up to ~42px past
  the edge; keep hazards ≥ 9 tiles from a step you walk off.

## Required work, in order

1. **Browser:** serve `build/web-tomas` and give Abe this script, then record his
   verdict as "human browser" (never claim it yourself):
   1. Repair the panel (B), take the awning exit, climb to shelf 21, take the cable,
      plug in on shelf 15, reach Marta's door (fridge payoff).
   2. Walk right off the summit: Wind Ridge. Hop the plateau, B at the pole.
   3. Cross the falling rock and the two wind lanes (time the gaps or tap A to hop).
   4. Hop onto Tomás's porch, B at the box (line glows), walk into the door.
   5. Expect warm windows, Tomás relieved, the concentrator on, `LINE 1/1 HOME 1/1`.
   6. Optional: walk into the door before plugging in; get hit while carrying.
2. Native check still open: the summit exit's **open** branch (var0=1 → ridge) on the
   release ROM (only tests cover it); the ridge respawn at the door after var9=1.
3. Stream / hardware: only when Abe asks, with explicit consent (flash erases the cart).
4. Next household: Rosa (online work: computer + router lights).

## Gotchas learned this session

- **10 sprites per scanline.** 24px gusts are 3 OBJs, the hero is 3, props are 2.
  Keep props off hazard rows; `test_house_view_stays_within_ten_sprites_per_scanline`
  shows the pattern. Use `emulator_inspect` view `oam` with `includeScanlineSummary`.
- **Trigger nudges.** The 24px hero's box spans x+2..x+14 and drifts ~2px after a
  stop. Nudge ≥3 tiles, and before the modal text, or the trigger re-fires and loops.
- **Recording quota.** `emulator_run` recording refused even after archiving six old
  recordings (archives went to `/Users/abe/src/artifacts/recording-archives`). Ask Abe
  before deleting anything; unrecorded native runs were used meanwhile.
- **Gust stagger** only offsets first activation: actors run update scripts only on
  screen, so both ridge gusts can be visible at once.
- **Test start scenes:** temporary `project/settings.gbsres` edits for test ROMs;
  always `git checkout project/settings.gbsres` before the release build.
- Interaction (B) picks the actor in front of the hero; keep the box, NPC and door
  at least a tile apart or B hits the wrong one.
- Earlier gotchas (HUD cutoff survives scene switches, `say()` for in-play text,
  two-digit variable tokens) still apply.
