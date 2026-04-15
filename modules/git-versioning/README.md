# git-versioning module

Auto-commits changes under `~/hub/knowledge/` on a configurable interval.

## Files

- `manifest.json` — Phase 3 module manifest with `config_schema.interval_seconds` (default 300)
- `install.sh`    — runs `git init` at `~/hub/` if no repo exists; idempotent on existing repos
- `uninstall.sh`  — no-op (preserves history per D-14)
- `prompt.md`     — static module prompt

## owned_paths

Empty. The module's "asset" is the commit loop wired in
`bot/modules_runtime/git_versioning.py`, scheduled via
`bot/main.py` post_init when registry shows the module installed.
Phase 3 leakage check passes vacuously.

## Config

| Key | Default | Description |
|-----|---------|-------------|
| `interval_seconds` | 300 | Commit-loop tick interval |

## Runtime

`bot/modules_runtime/git_versioning.py` provides `commit_loop()` and
`commit_if_changed()`. Single-committer enforced by an in-process
`asyncio.Lock`. Path-scoped `git add -- knowledge/` so the module
only touches its declared scope.
