# v0.21.0 — campaign checkpoint

November 8, 2026. Local release of campaign fixes and the dispatch-map work.
Includes isolated route/hub generators, tests, human feedback and terrain planning.
Rejected prototype roofs remain isolated and are not included in the campaign.

Version updated from 0.20.1-dev to 0.21.0. Title art regenerated; release HUD drops
only the development version label. A structural comparison of all 42 changed
scene/script resources confirms no other content change from regeneration.
551 tests pass. Physics, collision bounds and terrain are unchanged.

Release copy excludes lab and legacy scenes. Official CLI build succeeded;
cartridge header and native opening boot verified. ROM: `build/rom/lineman-v0.21.0.gbc`,
524288 bytes, SHA-256 `73566216b9547e564a26695e212916c09eb5d2131fdbd00de3f4cf395ec7958a`.
Abe reports manually flashing the prior full-campaign 0.20.1-dev build; that is
user-reported installation, not approval of all gameplay or this new ROM.
The v0.21.0 flash was explicitly authorized, including data loss, for Player 01;
its original operation is `b63e040532cd93b44124771faf83502ce902ce75cc720ad0bad881abff35b558`.
Outcome will be recorded after the original operation completes.

Worktree audit: experience-feedback has no unmerged commits or dirty files.
Campaign work is merged into main for this release. Existing local OpenCode
configuration remains uncommitted as previously requested. The historical review
stash is retained; its project-plan entry already exists in current docs.
No remote push or stable-tag move is part of this checkpoint.
