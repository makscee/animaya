---
phase: 01-install-foundation
plan: 02
subsystem: core
tags: [skeleton, entry-point, env-validation, claude-md, tdd]
requires: []
provides: [bot-entry-point, claude-md-assembler]
affects: [bot/main.py, bot/__main__.py]
tech-stack:
  added: []
  patterns: [async-main, module-injection-markers, tdd-red-green]
key-files:
  created:
    - tests/test_skeleton.py
  modified:
    - bot/__main__.py
    - bot/main.py
decisions:
  - "async def main() so Phase 2 can add async Telegram handlers without refactoring"
  - "DEFAULT_DATA_PATH uses ~/hub/knowledge/animaya per D-06, not /data Docker default"
  - "module-prompts-start/end markers give Phase 3 assembler clear injection points"
  - "assemble_claude_md() is public (no underscore) so Phase 3 can import and extend it"
metrics:
  duration: ~5min
  completed: "2026-04-13T18:59:02Z"
  tasks_completed: 2
  files_changed: 3
requirements:
  - INST-01
  - INST-02
  - INST-03
  - INST-04
---

# Phase 1 Plan 02: Bot Skeleton Entry Point Summary

**One-liner:** Async skeleton entry point with env validation, data dir creation, and CLAUDE.md stub with module injection markers — no v1 imports.

## What Was Built

Rewrote `bot/__main__.py` and `bot/main.py` as a Phase 1 skeleton. The new main validates required env vars (exits 1 if missing), creates the data directory (defaulting to `~/hub/knowledge/animaya`), writes a stub `CLAUDE.md` with `<!-- module-prompts-start/end -->` markers for Phase 3, then blocks on `asyncio.Event().wait()`. No Telegram, dashboard, features, or memory imports.

Created `tests/test_skeleton.py` with 9 tests covering all skeleton behaviors via TDD (RED then GREEN).

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Failing tests for skeleton | b6dda92 | tests/test_skeleton.py |
| 1 (GREEN) | Implement Phase 1 skeleton | 19564d1 | bot/__main__.py, bot/main.py |

## Verification

- `python -c "from bot.main import main, assemble_claude_md"` — imports without error
- `python -m pytest tests/test_skeleton.py -x -q` — 9 passed
- `grep -c "from bot.bridge|from bot.dashboard|from bot.features|from bot.memory" bot/main.py` — returns 0

## Deviations from Plan

**1. [Rule 3 - Blocking issue] Installed pytest into venv**
- **Found during:** RED phase test run
- **Issue:** No pytest available on system Python 3.12; system packages locked (PEP 668)
- **Fix:** Created `.venv` with python3.12, installed `pytest` and `pytest-asyncio` into it
- **Files modified:** .venv/ (not committed — gitignored)
- **Commit:** N/A (infrastructure only)

## Known Stubs

- `bot/main.py`: `assemble_claude_md()` writes static CLAUDE.md content with no modules. Intentional Phase 1 stub — Phase 3 module system will dynamically merge installed module prompts.

## Threat Flags

No new threat surface introduced beyond what is in the plan's threat model (T-01-05, T-01-06, T-01-07).

## Self-Check: PASSED

- bot/__main__.py: FOUND
- bot/main.py: FOUND
- tests/test_skeleton.py: FOUND
- Commit b6dda92: FOUND
- Commit 19564d1: FOUND
- All 9 tests pass
- No v1 module imports in bot/main.py
