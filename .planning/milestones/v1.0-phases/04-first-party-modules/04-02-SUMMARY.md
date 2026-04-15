---
phase: 04-first-party-modules
plan: 2
subsystem: git-versioning-module
tags: [git-versioning, asyncio, commit-loop, post_init, path-scoped, single-committer]
dependency_graph:
  requires: [04-00, 04-01]
  provides: [git-versioning-module-lifecycle, git-versioning-runtime, post_init-wiring]
  affects: [bot/main.py, bot/bridge/telegram.py]
tech_stack:
  added: []
  patterns:
    - asyncio.create_subprocess_exec for non-blocking git operations
    - asyncio.Lock single-committer pattern (D-12)
    - path-scoped git add -- knowledge/ (GITV-03)
    - Application.post_init for background task lifecycle
key_files:
  created:
    - modules/git-versioning/manifest.json
    - modules/git-versioning/install.sh
    - modules/git-versioning/uninstall.sh
    - modules/git-versioning/prompt.md
    - modules/git-versioning/README.md
    - bot/modules_runtime/git_versioning.py
  modified:
    - bot/main.py
    - bot/bridge/telegram.py
    - tests/modules/test_git_versioning.py
decisions:
  - "HUB_ROOT = ~/hub/ (locked assumption A2); KNOWLEDGE_REL = knowledge/"
  - "build_app post_init kwarg uses object|None type (not Callable/Awaitable) to avoid ruff F821 on string annotations"
  - "owned_paths=[] in manifest; git history is module asset not file asset; uninstall preserves history (D-14)"
  - "commit_loop final-commit-on-cancel via CancelledError handler"
metrics:
  duration: ~20 min
  completed: 2026-04-15
  tasks_completed: 3
  tasks_total: 3
  files_created: 7
  files_modified: 3
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 4 Plan 2: Git-Versioning Module Summary

**One-liner:** Asyncio commit loop with single-committer Lock auto-commits `~/hub/knowledge/` on a configurable interval via Application.post_init, with path-scoped git operations and no-op uninstall preserving history.

---

## What Was Built

### Task 1: modules/git-versioning/ package

Five files under `modules/git-versioning/`:

| File | Purpose |
|------|---------|
| `manifest.json` | Phase 3 manifest: `name=git-versioning`, `owned_paths=[]`, `config_schema.interval_seconds` default 300 |
| `install.sh` | Idempotent `git init` at `~/hub/`; sets `Animaya Bot` identity; initial empty commit for valid HEAD |
| `uninstall.sh` | No-op — prints message, preserves all git history (D-14) |
| `prompt.md` | Static module doc explaining auto-commit behavior to Claude |
| `README.md` | Documents owned_paths rationale, config, and runtime wiring |

**Locked path:** `GIT_REPO_ROOT="${HOME}/hub"` hardcoded in install.sh (A2; not derived from env var).

### Task 2: bot/modules_runtime/git_versioning.py

Exports:
- `HUB_ROOT: Path` — `Path.home() / "hub"` (production default)
- `KNOWLEDGE_REL = "knowledge/"` — path-scope constant for all git operations
- `_COMMIT_LOCK = asyncio.Lock()` — single-committer in-process lock (D-12)
- `commit_if_changed(repo_root)` — path-scoped status check, `git add -- knowledge/`, commit with `animaya: auto-commit {ISO}` message; returns `True` if committed, `False` if no-op
- `commit_loop(interval, repo_root)` — background task: sleep → commit_if_changed per tick; final commit on `CancelledError`

**Non-blocking:** all git calls via `asyncio.create_subprocess_exec` with 30s timeout.

### Task 3: bot/main.py + bot/bridge/telegram.py wired

- `build_app(token, post_init=None)` — `post_init` kwarg passes to `ApplicationBuilder.post_init()`
- `_post_init(application)` defined inside `main()`:
  - calls `get_entry(data_path, "git-versioning")` — only spawns loop when module installed
  - reads `interval_seconds` from entry config (default 300)
  - calls `application.create_task(commit_loop(...), name="git-autocommit")`
- No `asyncio.create_task` at sync scope (no RuntimeError)

---

## Test Results: 4/4 GITV Tests Green

```
tests/modules/test_git_versioning.py::TestCommitLoop::test_commit_loop_creates_commit_after_changes PASSED
tests/modules/test_git_versioning.py::TestCommitSkipEmpty::test_no_diff_tick_does_not_commit PASSED
tests/modules/test_git_versioning.py::TestCommitLock::test_concurrent_commits_serialize PASSED
tests/modules/test_git_versioning.py::TestCommitScoping::test_path_scoped_add_excludes_out_of_scope PASSED
```

Full modules suite: **39 passed, 4 xfailed** (MEMO stubs only).

---

## Locked Paths

| Constant | Value | Source |
|----------|-------|--------|
| `HUB_ROOT` | `Path.home() / "hub"` | `bot/modules_runtime/git_versioning.py` |
| `KNOWLEDGE_REL` | `"knowledge/"` | `bot/modules_runtime/git_versioning.py` |
| `GIT_REPO_ROOT` | `"${HOME}/hub"` | `modules/git-versioning/install.sh` |

---

## Commit Message Format

```
animaya: auto-commit {ISO timestamp}
```

Example: `animaya: auto-commit 2026-04-15T10:23:45+00:00`

Author identity fixed at `Animaya Bot <bot@animaya.local>` via env vars in `_run_git()`.

---

## Threat Mitigations Confirmed

| Threat ID | Mitigation | Status |
|-----------|-----------|--------|
| T-04-02-01 | asyncio.Lock in-process; git .git/index.lock surface failures | In place |
| T-04-02-02 | `asyncio.wait_for(proc.communicate(), timeout=30)` + exception-per-tick | In place |
| T-04-02-03 | Commit message is timestamp only; author is fixed bot persona | In place |
| T-04-02-04 | Path-spec `-- knowledge/` at git layer; symlinks tracked as links | Accepted |
| T-04-02-05 | install.sh hardcodes `${HOME}/hub`; does not use env-controlled path | In place |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff F821 on string-annotated Callable/Awaitable in build_app signature**
- **Found during:** Task 3 ruff check
- **Issue:** Plan specified `post_init: "Callable[[Application], Awaitable[None]] | None"` with an inline `from typing import Awaitable, Callable` inside the function. Ruff F821 flagged `Callable`/`Awaitable` as undefined names in the annotation string, and F401 for unused imports (since string annotations aren't resolved at runtime).
- **Fix:** Changed type to `object | None` — sufficient for runtime `post_init is not None` check; IDEs infer the type from usage. Removed inline import.
- **Files modified:** `bot/bridge/telegram.py`
- **Commit:** 3636bd7

---

## Known Stubs

None — all files created in this plan have real implementations.

---

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers.

---

## Self-Check: PASSED

- modules/git-versioning/manifest.json — FOUND
- modules/git-versioning/install.sh — FOUND
- modules/git-versioning/uninstall.sh — FOUND
- modules/git-versioning/prompt.md — FOUND
- modules/git-versioning/README.md — FOUND
- bot/modules_runtime/git_versioning.py — FOUND
- bot/main.py (modified) — FOUND
- bot/bridge/telegram.py (modified) — FOUND
- commit 2eb91ad (Task 1) — FOUND
- commit 1182b0b (Task 2) — FOUND
- commit 3636bd7 (Task 3) — FOUND
- 4/4 GITV tests green — PASSED
- 39 passed, 4 xfailed (full modules suite) — PASSED
