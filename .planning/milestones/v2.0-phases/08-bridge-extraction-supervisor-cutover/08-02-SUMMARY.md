---
phase: 08
plan: 02
subsystem: modules/bridge
tags: [bridge, modules, lifecycle, migration, supervisor, runtime-adapter]
dependency_graph:
  requires: [08-01]
  provides: [on_start, on_stop, migrate_bridge_rename, async-uninstall]
  affects: [bot/modules/lifecycle.py, bot/modules/registry.py, bot/dashboard/jobs.py]
tech_stack:
  added: []
  patterns: [deferred-import, idempotent-migration, async-uninstall, explicit-ptb-lifecycle]
key_files:
  created:
    - bot/modules_runtime/telegram_bridge.py
    - modules/telegram-bridge/manifest.json
    - modules/telegram-bridge/install.sh
    - modules/telegram-bridge/uninstall.sh
    - modules/telegram-bridge/prompt.md
  modified:
    - bot/modules/registry.py
    - bot/modules/__init__.py
    - bot/modules/lifecycle.py
    - bot/dashboard/jobs.py
    - tests/modules/test_supervisor_cutover.py
    - tests/modules/test_bridge_module.py
    - tests/modules/test_bridge_config_source.py
    - tests/modules/test_isolation.py
    - tests/modules/test_roundtrip.py
    - tests/modules/test_lifecycle.py
    - tests/dashboard/test_event_emitters.py
decisions:
  - Explicit initialize/stop/shutdown sequence (not async-with) to match Supervisor lifecycle
  - Idempotent on_stop via try/except per-step (catches already-stopped PTB Application)
  - migrate_bridge_rename uses atomic write_registry (tmp+replace) for registry safety
  - uninstall() converted to async def with supervisor=None default (backward compatible)
  - jobs.py: replace asyncio.to_thread(uninstall) with direct await (uninstall is now async)
metrics:
  duration: ~45min
  completed: "2026-04-15"
  tasks: 3
  files_changed: 15
---

# Phase 8 Plan 02: Bridge Extraction & Supervisor Cutover Summary

**One-liner:** Telegram bridge extracted into supervisor-compatible runtime adapter (`on_start`/`on_stop`) with explicit PTB lifecycle, `modules/bridge` renamed to `telegram-bridge` via git mv with idempotent registry migration, and `lifecycle.uninstall()` converted to async with `on_stop` pre-step and config/state purge.

## What Was Built

### Task 1: telegram_bridge Runtime Adapter

`bot/modules_runtime/telegram_bridge.py` exposes:

- `async on_start(ctx, config) -> Application` — validates token, deferred-imports `build_app`, calls `initialize()` / `start()` / `updater.start_polling()` explicitly (not `async with`)
- `async on_stop(handle) -> None` — `updater.stop()` → `stop()` → `shutdown()` in documented PTB order; each step wrapped in try/except for idempotency
- `_make_post_init(ctx)` — minimal post_init hook closing over AppContext

**Key resolution (RESEARCH.md Open Question #1):** Used explicit initialize/shutdown, NOT `async with tg_app:`, matching Supervisor lifecycle and avoiding double-shutdown pitfall.

### Task 2: Rename + One-Shot Migration

- `git mv modules/bridge → modules/telegram-bridge` (history preserved via rename detection)
- `manifest.json`: `name: telegram-bridge`, `runtime_entry: bot.modules_runtime.telegram_bridge`
- `install.sh`, `uninstall.sh`: updated log prefix from `[bridge]` to `[telegram-bridge]`
- `bot/modules/registry.py`: added `migrate_bridge_rename(data_path)` — atomic, idempotent, logs WARNING with both names
- `bot/modules/__init__.py`: added `migrate_registry()` public facade + exports `migrate_bridge_rename`

### Task 3: Async lifecycle.uninstall + on_stop Wiring

`lifecycle.uninstall()` converted to `async def` with `supervisor: Supervisor | None = None` parameter:

1. If supervisor provided + handle exists: `importlib.import_module(runtime_entry)` → `await on_stop(handle)` (wrapped try/except/finally — clears handles on success or failure)
2. Run `uninstall.sh` (existing logic)
3. Remove registry entry
4. Rebuild CLAUDE.md
5. Purge `config.json` + `state.json` from module dir

**Callers updated:**
- `bot/dashboard/jobs.py`: `asyncio.to_thread(uninstall, ...)` → `await uninstall(...)`
- `tests/modules/test_lifecycle.py`: 2 sync tests → async
- `tests/dashboard/test_event_emitters.py`: 1 sync test → async
- `tests/modules/test_roundtrip.py`: BRIDGE_DIR updated + uninstall calls → async

## Test Counts

| Before Plan 02 | After Plan 02 |
|---|---|
| 4 xfail (strict) in test_supervisor_cutover.py | 0 xfail — all 13 tests passing |
| 5 tests in test_bridge_module.py | 12 tests (7 new migration tests) |
| 1 xfail in test_bridge_config_source.py | 0 xfail — passes strictly |
| Total: 246 passed, 1 skipped, 4 xfailed | 259 passed, 0 skipped, 4 xfailed (BRDG-04 for Plan 03) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Sync callers of lifecycle.uninstall() updated**
- **Found during:** Task 3 (making uninstall async)
- **Issue:** `jobs.py`, `test_lifecycle.py`, `test_event_emitters.py`, `test_roundtrip.py` all called `uninstall()` synchronously; broke when it became a coroutine
- **Fix:** `jobs.py` changed from `asyncio.to_thread(uninstall, ...)` to `await uninstall(...)`; test files converted to `async def`
- **Files modified:** `bot/dashboard/jobs.py`, `tests/modules/test_lifecycle.py`, `tests/dashboard/test_event_emitters.py`, `tests/modules/test_roundtrip.py`
- **Commit:** 35febef

**2. [Rule 3 - Blocking] test_bridge_config_source.py xfail marker removed**
- **Found during:** Task 2 (migrate_registry now exists)
- **Issue:** `test_bridge_rename_migration_bridge_to_telegram_bridge` was xfail(strict=True); after Plan 02 adds `migrate_registry` it passes, causing strict xfail failure
- **Fix:** Removed `@pytest.mark.xfail` decorator
- **Commit:** 1c06455

**3. [Rule 3 - Blocking] test_isolation.py and test_roundtrip.py updated for rename**
- **Found during:** Task 2 (modules/bridge no longer exists)
- **Issue:** `test_bridge_has_expected_shape` pointed to `modules/bridge/`; `TestBridgeDogfood` used `BRIDGE_DIR = modules/bridge`
- **Fix:** Updated both to use `modules/telegram-bridge`
- **Commits:** 1c06455, 35febef

**4. [Rule 3 - Blocking] Incomplete git rename completion**
- **Found during:** Post-Task 2 verification
- **Issue:** `modules/bridge/manifest.json` remained tracked by git (the original); `modules/telegram-bridge/prompt.md` was untracked
- **Fix:** `git rm modules/bridge/manifest.json` + `git add modules/telegram-bridge/prompt.md`
- **Commit:** 38bb9dc

## Ready Surfaces for Plan 03

| Surface | File | Notes |
|---|---|---|
| `on_start(ctx, config)` | `bot/modules_runtime/telegram_bridge.py` | Ready for Supervisor.start_all() wiring |
| `on_stop(handle)` | `bot/modules_runtime/telegram_bridge.py` | Correct PTB order, idempotent |
| `migrate_bridge_rename(data_path)` | `bot/modules/registry.py` | Idempotent one-shot migration |
| `migrate_registry(data_path)` | `bot/modules/__init__.py` | Public facade, ready for boot sequence |
| `async uninstall(..., supervisor=None)` | `bot/modules/lifecycle.py` | Backward compatible |

Plan 03 task: replace `bot/main.py` inline PTB lifecycle with `Supervisor.start_all()` / `stop_all()` calls and call `migrate_registry()` at boot.

## Known Stubs

None — all surfaces are fully implemented and tested.

## Threat Flags

None — no new network endpoints, auth paths, or schema changes beyond what the plan's threat model covers (T-08-01, T-08-04, T-08-05, T-08-08 all mitigated per plan).

## Self-Check: PASSED

| Check | Result |
|---|---|
| `bot/modules_runtime/telegram_bridge.py` exists | FOUND |
| `modules/telegram-bridge/manifest.json` exists | FOUND |
| `modules/bridge/` does not exist | CONFIRMED |
| No `async with` in on_start | CLEAN |
| Commit 48aa79c (Task 1) | FOUND |
| Commit 1c06455 (Task 2) | FOUND |
| Commit 35febef (Task 3) | FOUND |
| Commit 38bb9dc (rename cleanup) | FOUND |
| 259 tests pass, 0 failures | CONFIRMED |
