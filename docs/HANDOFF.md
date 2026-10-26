# Session handoff: Mister CFE (2026-10-25)

Start a new session with: **"Read docs/HANDOFF.md and continue."**
Once this handoff's work is done, replace or delete this file. `PROJECT_PLAN.md` remains the
long-term status record.

## Read first

`AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_PLAN.md` (top, "First repair job: Marta's line",
progress log), `docs/redesign-brief.md`, `docs/action-climb-acceptance.md`, `docs/MCP_TOOLKIT.md`.
VERSION is `0.4.0-dev`; check `git log`/`git status` before editing. This is a local-only repo:
never add a remote. Use one-line Conventional Commits with no AI attribution.

## Current state

The first repair job (Marta's line) is complete and passed on ROM `a17ead01…`
(recording `artifacts/playtests/marta-line-v2`). The route:

1. Repair the panel; the service gate opens.
2. Enter Storm Climb and climb to shelf 21.
3. Press B at the snapped pole (`DAMAGED_POLE`) to take the cable.
4. Carry it past debris 3 and up to the junction box on shelf 15 (`JUNCTION_BOX`).
5. Press B to plug it in. The line glows (metal BG slot 5, colour index 1).
6. Reach Marta's door for the fridge payoff. The HUD ends at `LINE 1/1 HOME 1/1`.

Abe's verdict: **"I love it."**

Approved game structure: each household is a repair job of 2–3 linked scenes that combines
three phases:

- **Storm Run:** the climb.
- **Live Wire:** carry the snapped cable to a junction box.
- **Blackout Grid:** power visibly returns.

Next households, in order: Tomás (medical device), Rosa (online work),
Kiko's family (stove), Nuria (finale: lights and heat).

## Working rules learned

- **MCP:** use the ModRetro Chromatic MCP directly. In a new session the server may have
  restarted, so call `session_status` and, if needed, `project_select` the `.gbsproj`.
  Workers rely on main's selection.
- **Subagents:** up to 5 in parallel, each with its own files.
  - Coding workers prefer GPT-6 Luna and fall back to Haiku 5.5 (Agent `model: "haiku"`).
  - Every worker makes only read-only MCP calls and reports them.
  - Main owns builds, the emulator, the preview and commits.
- **Regenerate** with the managed Python:
  - `tools/make_project.py opening --fixtures --verify`
  - `tools/make_project.py climb --verify`

  The shared contract is `tools/climb.py`: `grid_resource_id`, `DAMAGED_POLE`,
  `JUNCTION_BOX`, and variables 6 (carrying) and 7 (line live).
- **Native play:**
  - Build with `rom_build` (`captureDebugArtifacts: true`), then `emulator_run` with
    `debugMode: "source"` and recording on.
  - Player position: WRAM offset 4640 (0xD220). `pos.x`/`pos.y` are u16 little-endian; pixels = value >> 5.
  - Actors are 56 bytes each from 0xD21F. Debris 3 is `actors[4]` (offset 4863) and debris 4 is
    `actors[5]` (offset 4919). Flag `0x08` means collision is on.
  - 8-frame A taps climb exactly one shelf.
  - Known-safe takeoff x: ≈71 for 30→18, ≈94 for 18→12, ≈72 for 12→6.
  - Debris 3 hurts at x43–61 and debris 4 at x51–69.
  - Recordings stop at 15 minutes of wall-clock time.
- **Gotchas:**
  - In text, use two-digit variable tokens (`$00$`, not `$0$`).
  - In-play text must go through `say()`, which lifts the 16px HUD window cutoff. Without it the
    text is invisible and the game appears frozen.
  - If the emulator lease is blocked, look for a stale MCP process (e.g. under `opencode serve`)
    and ask Abe before stopping it.
  - Preview URLs are process-local. Reopen an existing export with `web_preview` `recover`.

## Required work for this session, in order

1. **Test on the exact ROM** (recorded PyBoy, source debug) every Live Wire branch that hasn't been covered yet:
   1. **Cable drop on a hit.** Take the cable, then get hit by debris 3 (or the lane-1 gust) while var6=1. Check that:
      - var6 = 0;
      - the cable end is visible again in state "Dangling" at `DAMAGED_POLE`;
      - the HUD is redrawn;
      - the respawn depends on the checkpoint (back to start if var0 = 0).

      Then pick the cable up again and finish the job.
   2. **Junction box texts.** "No cable yet.\nCheck the pole." when var6 = 0 and var7 = 0, and
      "Line is live." on a second press after plugging in.
   3. **Unpowered door.** "Still no power.\nFix the line!" at Marta's door when var7 = 0. Check that
      var0 stays 0 and that the reward still fires later once the line is live.
   4. **16px hero.** Press SELECT in the opening (var5 = 1), then play the full arc. The climb
      currently forces the 24px sprite. Ask Abe whether to keep that or carry the choice through,
      then test whichever he picks.
   5. **Scene re-entry.** Go back from the climb to the opening (add a generator-owned exit if none
      exists), then enter the climb again. Check that var4 persists, var0/6/7 reset as designed,
      the gate stays Open, the HUD is correct and nothing gets stuck.

   Fix any defect in the generators (never hand-edit `.gbsres`), add regression tests, rebuild
   and test again.
2. **Browser:** rebuild the web export and serve it with `web_preview`. Give Abe a short test
   script that covers the same branches. Record his verdict as "human browser" in
   `PROJECT_PLAN.md` and the acceptance matrix; never claim it yourself.
3. **Hardware:** only with Abe's separate, explicit, informed consent.
   1. `rom_inspect` the exact ROM (path, size, sha256).
   2. Discover the device.
   3. Flash it.
   4. Watch the play with `device_capture`.

   If he declines, leave hardware marked untested.
4. **Docs and commit:** update the acceptance matrix and `PROJECT_PLAN.md`, keeping source,
   native, browser and hardware results separate. Bump `VERSION` per SemVer and commit.
5. **Next job:** plan and build Tomás's repair job with up to 5 parallel workers.

The Down+A multi-shelf drop stays deferred unless Abe asks for it.
