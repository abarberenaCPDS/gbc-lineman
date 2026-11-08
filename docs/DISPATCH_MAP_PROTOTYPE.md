# Neighborhood dispatch — one playable state

November 7, 2026 · `feat/campaign-polish` · VERSION `0.20.1-dev`.

The WO-0413 prototype is ready for Abe's review before expansion, as required by
[NEXT_PHASE_PLAN.md](NEXT_PHASE_PLAN.md#2-prototype-a-neighborhood-map-between-jobs).
It replaces the existing `work_order` scene only in an isolated generated project.
Production cards, report and logo launch are unchanged. No new scene is registered.

## Play and review

<http://127.0.0.1:53104/a1d2c88d2f529333b1c836096fa4bde1145df69ae478f1e6657463c431b83e8b/>

One state: Amara restored, Hiroshi next, Priya and Emil still dark. Neighborhood
Hero stands beside the current-job arrow. Press A once to accept WO-0413 and
enter Hiroshi's existing briefing, then A through its two pages to play.
The map's order text appears instantly; no new music/cue or movement system.

![Native prototype, frame120](../artifacts/playtests/dispatch-map-v2/frames/a2e15d95f7ddd8e705723a17f495e8b54dd4856ead153de5a2b650c7b2a9d0c4.png)

Review whether the four names and lit home read clearly at native size, the next
job is obvious, and the map plus existing level briefing feels quick enough.
This is a fixed WO-0413 layout, not the four-state production feature or ending.
The current plan calls for playable approval before those variants are made.

The export listener is live, with no player attached at the last status check.
Codex's built-in browser returned **"The browser access host is unavailable."**
No external browser was used; browser UI, feel and listening remain unverified.
Native emulator evidence below establishes rendering/transition separately.

## State and ownership

- `tools/dispatch_map.py`: one-state geometry, palette and text contract.
- `tools/make_dispatch_map.py`: native index-proxy PNG, five palettes, and isolated
  test project. Reuses the existing work-order scene ID and Neighborhood Hero.
- Household flags0/9/11/13 independently control window-only BG slots3–6.
  Dispatch16 is seeded2 only in the fixture; it never implies a completed home.
  No new globals, source gameplay writes or new campaign completion state.
- BG slots0–2 carry lettering/ground/architecture; UI7 stays reserved. Hero uses
  its existing OBJ0 palette. TOPDOWN scene, hidden player, noncolliding Idle actor,
  overlay reset/cutoff150. Text speed returns to1 before entering the job.
- Production `make_ticket_scene.py` and its work_order/report resources are intact.
  The prototype is generated to `build/diagnostics/dispatch-map/`; `--unlit` makes
  a separate comparison copy. Do not merge its seeded launch into production.

Reproduce from the campaign-polish worktree with managed Python:

```sh
PY="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"
"$PY" tools/make_dispatch_map.py
"$PY" tools/make_dispatch_map.py --unlit
"$PY" -m unittest discover -s tools
```

Select `build/diagnostics/dispatch-map/mr-cfe.gbsproj` through MCP, then build or
preview that selected copy. ROM/web identities are separate. Main owns these
operations. Original assets/resources and production launch stay reproducible.

## Verification

- **537 tests pass**. Four added contracts cover flag-driven lights, unchanged
  progress/exact destination, isolated aligned window tiles and native budget/UI.
- Seven new asset/resource outputs regenerate byte-for-byte. Hash checks confirm
  production work_order, report and launch settings unchanged during generation.
  The prior647 campaign outputs retain their earlier deterministic verification.
- MCP static analysis: **62 effective BG tiles**, all8 BG palette slots used,
  one OBJ palette; metadata estimates stay within engine budgets. Native build
  valid,524288 bytes. Sampled runtime OAM:4 visible objects, peak2 per scanline,
  zero scanlines above10 (first layout, unchanged art/hero in final prototype).
- Final lit fixture at120: homes1/0/0/0, ticket2; Amara's window is warm. A8 then
  neutral140 reaches Wind Ridge268 with home0=1 and ticket2 still present during
  its briefing. Two A8/neutral140 sequences reach gameplay564, ticket16=0,
  lines18=0/chain20=0 and home0=1. Existing job entry consumes the ticket after
  the briefing; the first recording's stop-note said this too early at318.
- Unlit fixture at120 has the same ticket2 but home0=0; Amara's window is dark.
  Pixel comparison differs only inside `(33,41)–(38,46)`, the window interior.
  Thus lighting is driven by completion, independently of dispatch order.
- Independent source review found no blocking issues. It flagged the retained
  two-page level briefing as a pacing question for the human pass.

| Evidence | Recording | ROM SHA-256 |
| --- | --- | --- |
| First layout/OAM/transition | `dispatch-map-first` | `13c96909d6855c7a9880b5f789d26a6282558ed2d5a8382d1e889e81e5d58a18` |
| Final map→briefing→gameplay,0–564 | `dispatch-map-v2` | `c38e235f1d94b0805f0c81d86ec2d55795076496aefde651f17594e674ffd97c` |
| Same state, Amara unlit,0–120 | `dispatch-map-unlit` | `f47ede87ef9398e5078fdadb38c362cd28ddd3d151a76b0dae1192806963510a` |

All recordings are stopped and retained in the worktree's
`artifacts/playtests/`. Native sessions closed; preview remains open.
Latest native ROM: `build/diagnostics/dispatch-map/build/rom/dispatch-map-v2.gbc`.
Web export `build/diagnostics/dispatch-map/build/web-dispatch-map`, ROM SHA
`a531f06e4256fe9d5144345f15a30ed918f21c3ec1739c4fe9d15c2d8149d13f`;
listener `ecaeadfa273d10547c2640a026e39749`.

Full earlier-candidate campaign evidence and final board-regression limits are in
[CAMPAIGN_PLAYTEST.md](CAMPAIGN_PLAYTEST.md). No release tag, merge, push,
stream, flash or physical/human acceptance follows from these automated checks.
