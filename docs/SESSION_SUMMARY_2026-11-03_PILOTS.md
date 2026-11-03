# Session summary — safe-span and ending reprise pilots


## Continuation: R8 and R10 candidates — November 3, 2026

Abe referenced the live “Review handoff documentation” task and said “let's
implement.” Main read thread `01a19fea-b3d5-7192-aa34-afa209da1f8c`, confirmed it
was the same experience review, and continued from existing commit `32f3ba1`
without duplicating R1–R4/R7. Continued in the sibling worktree on
`feat/experience-feedback`; main checkout and its uncommitted files remain intact.

### Implemented

- **R8:** one crest span now becomes persistently safe when line 5 is repaired.
  Its threshold (four upstream lines) and warning/active/rest waits remain the
  first-pass challenge. A crest-only chain subclass immediately disables/hides
  the arc on repair and scene entry. Guards after waits prevent queued phases
  from reactivating it. The final box's custom script explicitly binds the arc
  actor, including its native call-site argument. Other spans, hidden cables,
  gusts, geometry, and accepted art remain unchanged. Existing powered-wire
  feedback remains; no new visual safety marker was added or recognition claimed.
- **R10:** a separate two-section, eight-second D-major ending reprise reuses
  Intro B's accepted hero/mission motifs and ends on tonic D. After the report
  and existing victory request, it starts and carries into the title. Idle story
  replay still restarts normal Intro B; fresh opening still starts gameplay music.
  No extra blocking wait, new story shot, or gameplay arrangement change.
  New `ending.py`/`compose_ending.py` own its stable asset ID and deterministic
  source/rendering. `make_project.py tickets --render-music --verify` renders it
  through the installed offline Docker image. This is an audition candidate,
  not a human listening verdict.

### Verification

- **512 tests pass**, including rendered-note/instrument/effect/order comparison,
  cue flow, safe-span phase guards, and final-box actor bindings.
- All eight profiles regenerated; repeat generation leaves **645 asset/resource
  files byte-identical**. Re-rendering the ending produces the same UGE SHA-256:
  `50656dfdb935faad26242423a33a70705da5aa5258152c6d0d362bd2a4576181`.
- Baseline hashes confirm **38 existing music/engine/settings files unchanged**.
  Normal logo start restored; VERSION remains `0.19.0-dev`; tags unchanged.
- MCP health: **0 errors / 0 warnings / 0 info**, 20 scenes, 164 actors,
  97 triggers, 127 palettes, 96 assets, 50 variables.
- Final native ROM: `build/rom/lineman-experience-pilots.gbc`, 524288 bytes,
  valid header, SHA-256
  `a61696cebd77482bea71cf8443133d9b9f0d4816830046e915ec5ffe2d216a83`.
  Exact-ROM source debug confirms Abe's Games Logo at frame 120.
- Web export: `build/web-experience-pilots`, ROM SHA-256
  `98c45eae463a3702d2b218fe3ef4ff563317f1bf98a367db5f3a1bfde618372d`.
  CLI build succeeded; live preview replacement did **not** complete (see below).
  Builds emitted only upstream Node DEP0190.

### Native evidence

Fixtures use production generators, with temporary seeded progress/test starts;
all production resources/settings were restored. They are targeted checks, not
full-job completion or human acceptance.

- **Span:** ROM `a68e1af661a096cfbeb61ec53d13ab655ebedbb4d213110b0700a4c908057225`;
  `artifacts/playtests/experience-span-pilot`, session
  `861c649118c24501a8207a873597244d`, three retained branches. A temporary SELECT
  handler invokes the production final-box custom script with its actual actor
  binding; it bypasses the physical B-zone approach so repairs can be tested
  beside the arc during each phase. Rest trial: repair at 180, safe at 191.
  Warning trial: repair at 260, safe thereafter. Active trial (branch 3): arc flag
  `0x28` at frame 310 becomes hidden/noncolliding `0x22` at 321 and stays so at
  782. Walk crosses the floor span (822–838) without respawn, then real back exit
  and reentry preserve line 5/count 5 and flag `0x22` at 1272. Sampled OAM peak
  2/line at reentry, zero over-limit lines. Branch 1 retains an incidental hit on
  the separate hidden cable after walking too far; it is not span-pass evidence.
  After the connection cue, sampled music mute flags returned to zero.
- **Ending:** ROM `c6537df215b1a881cb9cb5a9afa71dffa113d26dbcfa522c95d6533f5c3c59c3`;
  `artifacts/playtests/experience-ending-pilot`, session
  `bec13e48a0ab480dad406769c55c04c7`, branch 1. Fixture starts at the report
  with gameplay music seeded. Gameplay pointer bank `05:50af` at frame 180;
  title inherits ending pointer `08:483f` at 1989, remains through 2589;
  title idle replay enters Intro Story with normal Intro B `02:7835` at 2989.
  Sampled mute flags zero. Pointer/counter traces establish native cue selection
  and continuity, not a pleasant loop seam or audible quality.

Main serialized project/build/emulator work. Both coding workers could probe MCP
but their isolated sessions had no selected project; main performed project and
runtime verification. Fixture wrapper and logs are retained locally in
`build/experience-pilots-evidence/` (ignored).

### Preview state and remaining checks

Before replacement, saved the old Chrome player at frame **10600**, state ID
`07c33040fc5e3b34c4a9a8d190abf6eb73d11368a0ba637eb6ea26a42139ea97`.
It belongs to the old web ROM `3f53f857...`; it cannot be restored onto the new ROM.
The previous `build/web-experience` export was retained.

The plugin then returned **“Browser recording close acknowledgement is UNKNOWN.”**
The old listener remains open with `closureState=unresolved`, still serving the
first prototype at:

http://127.0.0.1:56988/aac254e162594eccf2a143c73c41faeb4d9e65a2a2865320c3fa0ff5085c6a2e/

The captured player is paused. This URL is **not** the new R8/R10 candidate.
Status was inspected; the uncertain close was not retried or bypassed. Chrome
automation host is unavailable. Preserve the saved state, old export and any
recording ownership; resolve the original preview close/plugin state before
serving the verified new export. No new live URL is claimed.

Human comparison of repaired-span feedback and ending music remains open, as do
R5/R6/R9 recognition investigations, ten-retry listening, full-game flow and
physical-device acceptance. Warning audio, extra marks, broad art changes,
lighter gameplay arrangements, and a shared-soup rewrite were not added.
