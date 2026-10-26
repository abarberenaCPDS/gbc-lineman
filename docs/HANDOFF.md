# Session handoff: Mister CFE (2026-10-26)

Start a new session with: **"Read docs/HANDOFF.md and continue."**
Once this handoff's work is done, replace or delete this file. `PROJECT_PLAN.md` remains the
long-term status record.

## Read first

`AGENTS.md`, `CLAUDE.md`, `docs/PROJECT_PLAN.md` (top, "First repair job: Marta's line",
progress log), `docs/redesign-brief.md`, `docs/action-climb-acceptance.md`, `docs/MCP_TOOLKIT.md`.
VERSION is `0.5.0-dev`; check `git log`/`git status` before editing. This is a local-only repo:
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

1. ✅ **Done 2026-10-26: native Live Wire branches + re-entry.** All five branches passed
   on ROM `b187d1e4…` (`artifacts/playtests/live-wire-branches`). Abe chose to keep the
   climb 24px-only. A new street exit (bottom deck, left edge) returns to the opening.
   Re-entry exposed a freeze (the HUD's 16px scanline cutoff hid modal text); it is fixed
   in `make_climb_scene.py` with tests, and passed on ROM `1769ebc6…`
   (`artifacts/playtests/live-wire-reentry`). Details: `PROJECT_PLAN.md`, Marta's line.
   - Gotcha: the overlay scanline cutoff **survives scene switches**. Any exit from a
     HUD scene must lift it (150) and hide the overlay; any scene-init text must lift it.
   - Debris 3 timing: read `actors[4]` at WRAM 4863 (flag, x u16, y u16). Cross while
     it rests at y=160 with flag 0x26 (collision bit 0x08 clear).
2. **Browser:** export `build/web-live-wire` (web ROM `6831f908…`) is served by
   `web_preview` (process-local URL; use `recover` if it expired). Give Abe a short test
   script that covers the same branches. Record his verdict as "human browser" in
   `PROJECT_PLAN.md` and the acceptance matrix; never claim it yourself.
3. **Stream to the Chromatic:** Abe plans to ask for this. Use the MCP `play` tool.
   - Rediscover its signature first.
   - Run `device` discovery and confirm the exact device with Abe.
   - Build or `rom_inspect` the exact ROM to stream, and report its sha256.
   - Watch the stream with `device_capture`, in the built-in browser only.

   Streaming plays the emulator on the host and sends video and audio to the device. It does not
   run the cartridge, writes nothing, and the tools can't send button presses to the stream. So
   it is evidence of readability and audio on the real screen and speaker, not of hardware
   execution. Record it in the docs as "Chromatic stream (host-emulated)", separate from
   "hardware/cartridge". Get Abe's OK before any device access, and never fall back to `flash`
   without the step below.
4. **Hardware / cartridge:** only with Abe's separate, explicit, informed consent.
   1. `rom_inspect` the exact ROM (path, size, sha256).
   2. Discover the device.
   3. Flash it.
   4. Watch the play with `device_capture`.

   Flashing erases whatever is on the cartridge. If he declines, leave hardware marked untested.
5. **Docs and commit:** update the acceptance matrix and `PROJECT_PLAN.md`, keeping source,
   native, browser, Chromatic-stream and hardware results separate. Bump `VERSION` per SemVer and commit.
6. **Next job:** plan and build Tomás's repair job with up to 5 parallel workers.

The Down+A multi-shelf drop stays deferred unless Abe asks for it.

## Other open limitations (backlog, not blocking this session)

- Only gust lane 1 is active; lanes 2–8 are inert placeholders.
- Holding A for 10 frames or more can rise two shelves. A long hold from shelf 12 at x ≥ 75 can still touch the arrival trigger.
- Coyote time is enabled but its timing is untested. The Down+A multi-shelf drop is deferred.
- Progress isn't saved: vars 0/6/7 reset on every climb entry, and battery-save persistence is untested.
- The game has no title screen or ending, only one of five households, and no connector collectibles yet.
- Art polish:
  - The junction box's Dead state is barely darker than Live.
  - The pole crossarm doesn't line up with the cable attach point.
  - The route tiles shift tint slightly.
  - There's no separate fall or landing pose.
- The project file says GB Studio 4.2.0, but the managed CLI that builds it is 4.3.2.
- Audio has never been heard on a Chromatic, and nothing has run from a cartridge.
