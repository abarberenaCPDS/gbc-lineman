# 🧭 Git workflow

The authorized GitHub remote is `git@github.com:abarberenaCPDS/gbc-lineman.git`
(`origin`). Do not add or change other remotes unless Abe explicitly requests it. The repository uses one-line Conventional Commit
messages, feature worktrees, and SemVer in the root `VERSION` file.

## ✅ One-line commits

Use `type(scope): imperative summary`, one line, no AI attribution or trailer.

```text
feat(platformer): add sample-inspired cable ledges
fix(audio): soften the connector pickup transient
art(sprites): clarify the worker silhouette
docs: document GBC limits and preview workflow
chore(release): prepare v0.2.0
```

Useful types: `feat`, `fix`, `art`, `audio`, `docs`, `build`, `test`, `chore`.
Keep the subject specific and short; put rationale in project documentation
when it needs to persist.

## 🌿 Worktrees

Create a branch and its worktree from the repository root. Keep each worktree
on its own branch; never check out the same branch in two worktrees.

```sh
git worktree add ../gb-mr-cfe-platformer -b feat/platformer-conversion
git worktree list
```

After merging or completing the branch, remove only the worktree directory you
created (first save or commit any work you want to keep):

```sh
git worktree remove ../gb-mr-cfe-platformer
git branch -d feat/platformer-conversion
```

Use the ModRetro Chromatic MCP `project_select` with the absolute `.gbsproj`
path inside the chosen worktree before authoring or building there. Each
worktree is a separate project copy; do not confuse it with the live preview
from the main project.

## 🔖 SemVer

`VERSION` uses `MAJOR.MINOR.PATCH` with an optional prerelease label.

- `0.x.y` means the game is still pre-1.0 and may change incompatibly.
- Increment `PATCH` for compatible fixes and small polish.
- Increment `MINOR` for compatible new gameplay or content.
- Increment `MAJOR` for a release with incompatible project or gameplay changes.
- Remove `-dev` and create a matching local tag for a release, e.g. `v1.0.0`.

Release example (after updating `VERSION`):

```sh
git add VERSION
git commit -m "chore(release): prepare v1.0.0"
git tag -a v1.0.0 -m "chore(release): v1.0.0"
```

### Stable marker

`stable` is an annotated tag on the last release Abe approved on the cart
(currently `v0.10.3`). Move it only when he approves a newer release:

```sh
git tag -fa stable vX.Y.Z^{commit} -m "stable: vX.Y.Z (ROM <sha>), <Abe's verdict>"
```

## 🧹 Ignored local files

`.gitignore` excludes generated builds and web exports, compiler outputs,
Python caches, GB Studio backups/local settings, and emulator saves/checkpoints.
Do not force-add a save, build artifact, sample, or secret just to silence Git.
