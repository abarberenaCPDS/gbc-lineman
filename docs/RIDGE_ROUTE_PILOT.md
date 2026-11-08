## Human verdict — November 8

Low rock ceilings rejected as cumbersome and inappropriate for Wind/Hiroshi.
Spacing was only a modest improvement. Do not integrate revision 3. Preserve
jump physics; redesign terrain and placement through MAP_DESIGN_PLAN.md.
The following source/runtime evidence is historical, not player acceptance.

---

## Preview connection restored — November 8

User restarted the MCP connection; fresh selection succeeded. Revision3 cached
web export opened successfully and its opening briefing was visibly verified in
Chrome (tab2125938238). Listener15a91173ce4e657ec61ba9b517f1c9a6 is open.
[Play revision3](http://127.0.0.1:55358/be7a6938267af796deffbe9339cb59396018cd10f9ddc2c8915505a8759028fc/). This supersedes the preview restart blocker below.
Human route acceptance remains pending; browser gameplay was not automated.

---

# Wind Ridge 64×36 route pilot

November 8, 2026. **Revision 3 native regression passed; browser export built, preview restart pending.**
Revision 1 and 2 runtime evidence is retained below and does not validate revision 3.
Production geometry remains unchanged. This tests one response to the bypass
feedback before extending a redesign across all jobs.

## Revision 3 — wider Saddle waiting area

Revision2 reached the household, but its intermediate rest zone was too precise:
waiting at actor origin363px still overlapped the gust. This revision changes
only the copied Saddle final crossing; Wind geometry and physics stay identical.

| Feature | Revision 3 coordinates |
| --- | --- |
| Fallen-span arc | Chest31, columns41–42 |
| Final gust | Chest31, columns49–51 |
| Rock arch | Columns40–49, solid rows2–28 |
| Porch start | Column54, surface30 |
| T5 / checkpoint | `(54,29)` / `(56,29)` |
| Hiroshi / concentrator | Unchanged `(58,29)` / `(60,29)` |

The unchanged hero bounds are origin+2 through origin+13 inclusive. The gap
between the arc and gust now admits safe actor origins342–378px, a36px movement
window instead of12px. It includes the previously failing363px pose and leaves
room for the measured23px neutral-release drift. For regression, approaching from
the left can release by352px; approaching from the right can release by368px.
These are diagnostic landmarks, not instructions a human should need to memorize.

The first stationary safe approach remains in front of the arc, around
origin312px; the arc begins328px. However, moving pole5 pickup followed by neutral
release needs a focused native check: pole origin296px has only19px before body
contact begins at315px, less than the measured23px full-speed drift. The wider
middle rest zone does not by itself establish entry fairness. The roof still covers the first gust column, preventing a high
leap across the entire field. Beyond the gust, clear origin414–418px fits before
the porch wall; tile-origin416px is a stable stop. Roof ends400px, so this exit
pose has enough head clearance for the next three-tile rise. On the reverse
trip, wait on the upper porch before descending; the4px exit pose is a wall-stop
location, not a forgiving place to brake while moving left. Native movement,
warning visibility, and comfortable stopping remain the acceptance checks.

The shifted box occupies54–55, with clear columns56–57 before Hiroshi58; the
checkpoint at56 does not overlap either the box actor (background-only) or the
resident. Door, household effects and outgoing trigger retain revision2 positions.

Eight focused tests pass, including the body-width/rest-gap calculation and a
23px stopping-distance lower bound in both directions. Both coarse route audits
pass. Normal plus all three diagnostic cases have been regenerated; manifest
revision and scene names are3. Wind remains243 unique indexed tiles, Saddle235;
actor counts remain7/9. All16 previously present build/export evidence files were
hash-identical after regeneration: the fixture copier changes assets/resources,
not the retained ROM/export directories. Native revision3 results belong below
in a separate evidence section when main completes them.

## Revision 3 native regression — November 8

Official native build: `build/diagnostics/ridge-route-pilot/build/rom/ridge-route-v3.gbc`,
524288 bytes, valid GBC-only header. SHA-256
`858497f67af1e9b145a8006d196f55872e914faa8692873c311de638261beb5b`.
The full Python suite passed after the new rest-gap regression was added.

Recording: `artifacts/playtests/ridge-route-v3-rest-return`,6237 frames, passed for
this bounded regression. Session `98efefca578c4a5fb4721ba936bcf0e1`; digest
`5e31fd3092385ef613229f9a20717bc1495a9fad516f23075667d5becb3c99af`.
Used the same native input sequence as revision2 up to final cable5, with no
memory writes, state restores, or extra progression seeds. A checkpoint was saved
at frame3231 for later focused checks but was not restored during this run.

- Forward rest: after52 right frames, released at345.3px, coasted to367.7px,
  and waited240frames. Cable5 and four repairs remained intact at3523.
- A24-frame held jump beneath the arch remained visible and returned to the
  rest floor. This checks ceiling contact appearance, not every hazard phase.
- Crossed the gust, stopped naturally at the porch wall, jumped to T5 and
  repaired the fifth line at3822. Hiroshi dialogue completed; home9=1,
  lines18=5, ticket16=0.
- Porch OAM sample at3822:13 visible objects, peak6 on any scanline, zero
  over the hardware limit10. This is one sampled state, not an exhaustive budget.
- Reverse departure reached the middle pad and coasted to349.1px;240 neutral
  frames preserved completion. Continued back through Saddle into Wind at5966;
  home and five repaired lines remained set. The subsequent Wind reverse gust
  caught the player and respawned at its checkpoint. Do not claim a no-hit full
  return to the route start.

Remaining focused checks: moving pole5 pickup and release near the first arc,
active-gust hop attempts across phases, and human challenge/readability acceptance.
The revised route is ready for a human preview, not production integration.

Official web export built separately at `build/web-route-v3` inside the fixture.
Its ROM SHA-256 is `e6eb92216931448aeaf1dc2f925e4fa816d3efffebe6dd0fec7fd6570ca4a6c9`;
this differs from the native cartridge and is not native playtest evidence.
Abe explicitly authorized discarding the old player/unresolved close. The old
visible tab was closed and public preview status now has no players, but public
close still returns UNKNOWN. There is no public reset command. Codex's app UI
refuses automated access to its own settings, so a user reconnection of the
`lineman-workspace` MCP is pending. Native recording finalized; emulator closed.

## Revision 2 — focused hazard and framing corrections

The recorded first pilot allowed a long jump over the entire gust group, and
high summit jumps obscured the carried hero under the HUD. Abe also identified
the final Saddle lower hazards as wasted beneath the preferred upper catwalk.
This revision changes both copied ridge scenes, before any hub work.

- **Wind gust crossing:** remove the optional upper shelves. A visibly drawn
  rock arch occupies x29–32, rows2–16, above the gust floor21. Four clear rows
  remain beneath it: a24px hero can make a small hop, but the roof is intended
  to prevent vaulting the entire gust collision band (8px high at chest level). The gust remains x31–33,
  chest19. Origin29 is a safe waiting position. Roof ends32; floor continues
  through35, leaving a stable clear exit pose before the next rise at36.
  The live wire follows the underside rather than cutting through solid rock.
- **Wind summit framing:** highest terrain is now surface15 across x42–62;
  the hidden cable moves to chest13 at58–59. Return entry is `(56,14)`;
  outgoing trigger is `(62,12,1,3)`. This allows the full held-jump rise and
  Carry sprite above the hero without reaching the16px HUD at camera-top clamp.
- **Saddle final crossing:** remove the x38–47 upper catwalk and upper whip.
  Lower T4 to ordinary step height and put mandatory pole5 on the floor, so
  collecting the final cable establishes a low approach. Retain the existing
  fallen-span arc and gust, rather than add more hazard actors. A visible rock
  arch constrains the long leap; an exit run-up remains before the porch rise.
- **Saddle framing:** the copied scene is also64×36. Relative scene content
  moves18rows down; the original high summit is additionally lowered6rows.
  All actors, collisions, wires, windows, triggers, checkpoints and paired
  scene links move consistently. Production and other jobs stay unchanged.

| Saddle feature | Revision 2 tile coordinates |
| --- | --- |
| Incoming entry / upstream trigger | `(2,26)` / `(1,24,1,3)` |
| T3 / pole4 | `(14,29)` / `(18,29)` |
| Upstream catwalk and gust | Surface27 x20–31; gust chest25 x26–28 |
| T4 / checkpoint / final pole5 | `(33,29)` / `(35,29)` / `(37,32)` |
| Final arch | x40–47, solid rows2–28; passage29–32 |
| Fallen-span arc / gust | Chest31 x42–43 / chest31 x47–49 |
| Safe intermediate wait | Actor origins44/45, feet32 |
| Clear exit run-up | Floor33 through51; origins50+ beyond the gust |
| Porch T5 / checkpoint | `(52,29)` / `(54,29)` |
| Hiroshi / concentrator | `(58,29)` / `(60,29)` |
| Downstream exit | `(62,27,1,3)`, normal next-job destination unchanged |

`signal_porch` was reviewed as a reference: its pickup/approach, floor hazards
and final raised porch make the hazard placement relate to the destination.
This pilot adopts that structural relationship, preserving existing art and
hazard vocabulary. It does not copy Priya's scene or assume its human acceptance
proves the Ridge changes.

### Focused cases

Generate the normal route with the command below, or add `--case gust`,
`--case summit`, or `--case saddle`. These write separate ignored project copies
under `build/diagnostics/ridge-route-pilot-<case>/`. Every copy records its exact
seed in `route-pilot.json`. Only the selected starting scene applies that seed,
once behind registered fixture flag55. Returning between scenes must preserve
progress. No physics or hidden collision-bound changes are used.

| Case | Start | Explicit seeded progress | First runtime checks |
| --- | --- | --- | --- |
| normal route | Wind `(2,32)` | Ticket2 only, no repaired lines | Two repairs, cable3 crossing and return, both safe recoveries |
| gust | Wind `(27,23)` | Line1 live, carry2 | Full held-A, short hop, warning/rest crossing, roof exit to T2 |
| summit | Wind `(54,14)` | Lines1–2 live, carry3 | Max jump with Carry at camera-top clamp; cable lane; scene transition |
| saddle | Saddle `(37,32)` | Lines1–4 live, carry5 | Old long-jump bypass, safe wait between hazards, exit run-up, T5/house, reverse return |

### Revision 2 source verification

Seven focused tests pass: production/all unrelated scenes byte-identical;
both scene dimensions and terrace geometry; seed guard; relocated checkpoints;
arch clearance and exit runway; exact paired scene destinations; all ten coarse
route-audit rule groups for each scene. These checks do not replace native arcs.
Generated source art uses243 unique indexed tiles in Wind and242 in Saddle,
both below256; actor counts7 and9 respectively. Author previews are
`route-pilot-author.png` and `saddle-pilot-author.png` inside each fixture.
Native/compiler/browser evidence for revision2 must be recorded separately.
Carry art extends8px above the body collision bounds: inspect whether a hop
under either arch makes the cable touch or overlap the ceiling artwork. At rest
the full Carry silhouette fits the32px passage; this is a visual runtime gate.

## Revision 2 native results — November 8

The full normal-route fixture built as a valid 524288-byte GBC cartridge,
SHA-256 `cb5003ad5e8097f2da974a81431a7476f8e0419d9d2acb98a4e8426531ce7649`.
Its filename is `build/rom/ridge-route-v2-gust.gbc` inside the normal fixture;
despite the filename, it is **not the gust-seeded case**. Project switching to
that case was refused by an unresolved browser close acknowledgement, and the
build used the still-selected normal fixture. Source debugging confirmed the
normal route and its actual progression. All 550 Python tests pass.

Retained recordings:

- `artifacts/playtests/ridge-route-v2-full`: 2910 frames, needs-review. First
  two repairs, gust arch exit, maximum held jump with Carry at summit, and
  Saddle entry retaining cable3. Subsequent overshoot/drop/wrong-cable play is
  retained rather than presented as a clean completion.
- `artifacts/playtests/ridge-route-v2-saddle-route`: 5351 frames, needs-review.
  Full route reached five repaired lines and Hiroshi home powered. Final values:
  carry6=0, home9=1, ticket16=0, lines18=5, chain20=5. Recording digest
  `212e75ecba849763af60376506dca3f9190cb79888b32d23418eb4060f201229`.

The summit Carry jump stayed below the HUD (samples1775–1803 in the first
recording). The final Saddle held-right+A attempt was constrained by the arch,
then lost the cable to the gust by frame3554; four completed repairs survived.
A later floor crossing preserved cable5, reached the clear exit at frame4094,
and repaired T5. The porch jump and house dialogue completed normally.

This establishes completion and a failed simple bypass attempt, not universal
bypass prevention or human enjoyment. Intermediate waiting proved less forgiving
than desired: improve the rest-area margin in the next tuning pass. Full reverse
traversal, isolated active-gust hop tests, and Carry ceiling-contact inspection
remain open. Do not call the route accepted from a successful run alone.

The revision1 browser export remains open and unchanged. Its listener reports
`closureState: unresolved` and `Browser recording close acknowledgement is UNKNOWN`.
No forced close or uncertain retry was performed. Native emulator recordings
were finalized and the owned native session closed. Resolve the preview lifecycle
before switching fixtures or publishing revision2; do not label the old URL as new.

## Revision 1 design (superseded)

Wind Ridge rises from floor row 33 to the existing Saddle exit at row 9. Required
repair endpoints move up with the route. Solid, contiguous terraces replace the
continuous lower bypass: walking along the bottom now meets the next rise rather
than carrying the player beneath whole hazard groups. Falling or walking back
lands on the previous broad terrace; there are no deep pockets between columns.
The first catwalk retains a shallow, quiet recovery floor. The under-catwalk
whip and redundant lower gust/fallen span are removed from this fixture.

| Section | Native tile coordinates | Purpose |
| --- | --- | --- |
| Entry / pole 1 | Start `(2,32)`; pole `(6,29)` on rock row 30 | Safe pickup and first short rise. |
| First crossing | Catwalk row 27, x9–14; cracked x9–11 | Cross promptly, or recover on the shallow floor. |
| Repair 1 / pole 2 | Box `(16,26)`, checkpoint `(18,26)`, pole `(20,26)` | Broad safe terrace and mandatory repair. |
| Main ascent | Rock rows 24 at x23–28, 21 at x29–34; gust chest row 19, x31–33 | Short taps and visible timing; safe wait at origin x29 on row20 or the preceding terrace. |
| Optional staging path | One-way ledges row21 x26–28 and row18 x27–30; cracked x27–29 | Climb above the gust via an extra jump and a board that cannot be used for prolonged waiting. A skilled long jump might skip both; native testing must establish the actual tradeoff. |
| Repair 2 / pole 3 | Box `(36,17)`, checkpoint `(38,17)`, pole `(40,17)` | Safe repair/rest before carrying cable into Saddle. |
| Upper ascent | Rock rows15 x42–47,12 x48–53; whip chest13 x45–46 | New height guides a meaningful crossing. Wait at origins42/43; jumping over the wire remains valid. |
| Exit shelf | Rock row9 x54–62; hidden cable chest7 x58–59 | Last crossing before Saddle. Return entry `(56,8)` remains supported and outside the cable footprint. |

Coordinates above are actor origins/feet rows, matching the project contract.
The ordinary route uses three-tile rises and broad solid steps. Longer jumps
are a faster, more demanding option, not prohibited exploits. The pilot should
fail human acceptance if holding right+A trivializes all meaningful choices;
static reachability does not settle that question. The optional boards are a
staging route, not a claim that their hazard is unavoidable.

Ridge Saddle remains **64×18 and unchanged**. The five-line chain retains all
IDs and flags; line 3 still crosses the scene boundary. This pilot addresses the
Wind Ridge form of the reported weakness; it does not claim to fix all four
screenshots or the later jobs yet.

## Generate and verify

```sh
PY="$HOME/Library/Application Support/modretro-chromatic/toolchain/.local/pyboy-venv/bin/python"
"$PY" tools/make_ridge_route_pilot.py
"$PY" -m unittest discover -s tools -p test_ridge_route_pilot.py -v
```

Select and build:
`build/diagnostics/ridge-route-pilot/mr-cfe.gbsproj` using its absolute path.
Only main owns MCP selection, compilation, emulator controls and preview updates.
The generator copies production assets/resources, changes only copied Wind Ridge
outputs and registers fixture-only variable55. That flag seeds the job ticket
once; returning from Saddle must not restart the job. No production resource,
movement setting, hero, sound or launch setting is changed.

Authored inspection image: `build/diagnostics/ridge-route-pilot/route-pilot-author.png`.
Contract manifest: `build/diagnostics/ridge-route-pilot/route-pilot.json`.
The exported PNG is the native grayscale proxy, not the authored RGB image.

## Evidence and remaining gates

- Source geometry audit passes reach/order/exit/safe-ground/spacing/respawn/
  headroom/footing/entries/static OAM budget checks. The coarse route model does
  not trace native jump arcs or timed hazards.
- Four focused fixture tests pass: production hashes unchanged; all other scene
  bytes unchanged; only Wind Ridge becomes64×36; first-entry seed is guarded;
  native respawn events use the relocated checkpoints and return shelf remains.
- Generated art: **238 unique indexed tiles**, below the256 source budget;
  **8 actors**. Compiler-effective tile count and runtime OAM still require build.
- Native/browser checks pending: first two repairs; short-tap main path;
  long-held-A easiest route; optional shelf entry/escape/board reentry; safe
  floor recovery; cross-scene cable3 carry and return; shock/checkpoint recovery;
  camera readability at160×144. Preserve failed attempts as evidence.
- Human feel, audio and physical Chromatic acceptance remain open.

## Recorded native pass — November 8

Native ROM: `build/diagnostics/ridge-route-pilot/build/rom/ridge-route-pilot.gbc`,
SHA256 `4cfa148192798d02fb8d98b7fd783c0829a14660fcf221bcd7d088d55aa0ed8c`.
Official build succeeded, valid 512 KiB GBC cartridge; only known Node DEP0190
warning. Matching source-debug artifacts captured. PyBoy2.7.0 recording
`artifacts/playtests/ridge-route-pilot-first`, session
`32b71004f9164615ad40c663a7c0f354`, frames0–3103, stopped as **needs-review**.
Digest `fb0ac143e37b197fc04bf1d5a900ca185829c3e63066765342dcce8946eedf94`.
No rewinds, memory writes or seeded progress beyond the fixture's documented
initial ticket. Native session closed after recording.

| Native frame | Observed result |
| --- | --- |
| 452 | Briefing dismissed; lines/chain0, carry0, fixture guard1. |
| 543 | Picked cable1. Missed crossing later fell onto quiet recovery floor without cable loss. |
| 773 | Recovered onto first catwalk. |
| 969 | Repair1 succeeds; lines/chain1, carry0. |
| 1164 | Cable2 picked. |
| 1264 | Holding right+A100 frames stops on first main terrace; does not automatically climb whole route. |
| 1301 /1345 | Two-frame tap fails at next rise; eight-frame tap plus movement succeeds. Timing/approach matter. |
| 1422 | Long jump passes gust and optional shelves, lands near pole3; returned to repair2. |
| 1562 | Repair2 succeeds; lines/chain2. |
| 1666 | Cable3 picked. |
| 1746 | Upper wire catches attempted long jump; carry0, both repairs retained, checkpoint(38,17). |
| 1959 | Deliberate ascent/jump clears wire carrying3; upper terrace reached. |
| 2101 /2191 | Ridge Saddle entered; carry3 and both repairs preserved. |
| 2223 | Returned to Wind Ridge: carry3, lines/chain2, ticket0; no reseed or repeated briefing. |
| 2432 | Reverse descent reaches repair terrace carrying3. |
| 2532 /2609 | Optional board shelf reached, then promptly escaped with carry3 intact. |
| 2953–3103 | Standing on cracked optional shelf produces warning/shock, carry0, checkpoint and two repairs retained. |

Sampled OAM at3103:12 visible objects, peak6 per scanline, zero lines over10.
This single sample is not an exhaustive flicker test. First missed jump/dialogue
input attempts are retained; those early inputs are not a clean speedrun script.

### Design concerns retained

- Long jumps skip the gust group and its optional board route. The terrain closes
  the free walking lane, but this is still not proof of an interesting easiest path.
- High jumps near the summit briefly obscure the hero under the HUD/top edge.
  Camera/headroom needs another design pass if distracting in human play.
- An eight-frame tap succeeded where two frames failed; do not promise all steps
  clear with any short tap. The first-route control feel needs human assessment.
- Only this Wind Ridge pilot changed. Later Saddle hazards, full campaign,
  listening and hardware acceptance remain outside this pass.

### Browser handoff

<http://127.0.0.1:61898/2d527650a503ba30b61142f180b9856cad91ca402209a8f11ece43ccf633cb87/>

Opened and visually verified in user-requested Chrome at the Hiroshi briefing.
Web ROM SHA `888c3906d0e7b0e1e19814addc371415cd393bcf6fc1e19b2b037283045d5eb0`;
web export is separate from the recorded native cartridge. Browser gameplay
inputs have not been replayed. Use arrows to move, Z for A/jump/dialogue, X for
B/pickup/repair. Preview kept open for human review; production unchanged.
