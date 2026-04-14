---
phase: 02-telegram-bridge
plan: "02"
subsystem: bot-entry-point
tags: [telegram, bridge, main, integration, tdd]
dependency_graph:
  requires: ["02-01"]
  provides: ["telegram-polling-entry-point"]
  affects: ["bot/main.py", "tests/test_skeleton.py"]
tech_stack:
  added: []
  patterns: ["lazy-import-inside-async-fn", "mock-async-app-run_polling"]
key_files:
  modified:
    - bot/main.py
    - tests/test_skeleton.py
decisions:
  - "D-10: Lazy import of build_app inside main() keeps module-level import clean"
  - "D-11: PTB run_polling() handles SIGINT/SIGTERM gracefully — no custom signal wiring needed"
  - "asyncio import removed after asyncio.Event().wait() replaced"
metrics:
  duration: "~10 minutes"
  completed: "2026-04-13"
  tasks_completed: 1
  tasks_total: 2
  files_modified: 2
---

# Phase 2 Plan 02: Wire Telegram Bridge — Summary

**One-liner:** Replaced blocking `asyncio.Event().wait()` with PTB `build_app()` + `await app.run_polling()` in main.py, completing the Telegram bridge integration.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire build_app into main.py and update tests | dfd3b5c | bot/main.py, tests/test_skeleton.py |

## Tasks at Checkpoint

| Task | Name | Status |
|------|------|--------|
| 2 | Verify end-to-end Telegram bridge | awaiting human verification |

## What Was Built

**bot/main.py** — The Phase 1 blocking placeholder (`asyncio.Event().wait()`) is replaced with:
```python
from bot.bridge.telegram import build_app  # lazy import inside main()
token = os.environ["TELEGRAM_BOT_TOKEN"]
app = build_app(token)
await app.run_polling()
```

`assemble_claude_md()` is called before `build_app()` — ensures CLAUDE.md is ready before the bridge starts.

**tests/test_skeleton.py** — Updated with `TestTelegramBridgeIntegration` class (3 new tests):
- `test_main_calls_build_app_with_token` — verifies token passed correctly
- `test_main_awaits_run_polling` — verifies polling is awaited (not event loop blocked)
- `test_assemble_claude_md_before_build_app` — verifies call order via tracked side effects

Old `test_data_dir_created` updated to use mocked `build_app` instead of `asyncio.TimeoutError` pattern.

## Test Results

- 76 tests pass (46 pre-existing + 30 from Plan 01 bridge/formatting tests)
- 12 skeleton tests pass (9 existing + 3 new bridge integration)
- Zero regressions

## Deviations from Plan

None — plan executed exactly as written. The `asyncio` import was removed as a cleanup (Rule 2 — unused import after replacing `asyncio.Event().wait()`).

## Checkpoint: Task 2 (Human Verify)

Task 2 requires a human to verify end-to-end Telegram bot behavior with a real bot token. This cannot be automated.

**What to verify:**
1. `.env` has `TELEGRAM_BOT_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN`
2. `python -m bot` starts without errors
3. `/start` in Telegram returns welcome message
4. Text message gets streamed Claude response with typing indicator
5. Long response (500+ words) arrives as multiple messages
6. Ctrl+C exits cleanly
7. No ImportError/ModuleNotFoundError in logs

## Known Stubs

None that affect this plan's goal. `assemble_claude_md()` produces a minimal static CLAUDE.md (no modules) — this is intentional for Phase 2; Phase 3 adds module prompts.

## Self-Check

- [x] bot/main.py exists and imports cleanly (`from bot.main import main` succeeds)
- [x] Commit dfd3b5c exists in git log
- [x] asyncio.Event().wait() removed from main.py
- [x] 76 tests pass
