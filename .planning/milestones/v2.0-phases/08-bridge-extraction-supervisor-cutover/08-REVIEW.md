---
phase: 08-bridge-extraction-supervisor-cutover
reviewed: 2026-04-15T00:00:00Z
depth: standard
files_reviewed: 9
files_reviewed_list:
  - bot/main.py
  - bot/modules_runtime/telegram_bridge.py
  - bot/modules/context.py
  - bot/modules/lifecycle.py
  - bot/modules/manifest.py
  - bot/modules/registry.py
  - bot/modules/supervisor.py
  - bot/modules/__init__.py
  - bot/dashboard/jobs.py
findings:
  critical: 0
  warning: 4
  info: 4
  total: 8
status: issues_found
---

# Phase 08: Code Review Report

**Reviewed:** 2026-04-15T00:00:00Z
**Depth:** standard
**Files Reviewed:** 9
**Status:** issues_found

## Summary

Phase 08 extracts the Telegram bridge into a supervisor-managed module and rewrites the boot sequence in `main.py`. The architecture is sound: the `Supervisor` → `AppContext` → `Registry` → `telegram_bridge` adapter chain wires together correctly. Security posture is good — the `runtime_entry` namespace guard (`bot.*` only) prevents arbitrary module injection, token values are never logged, and all registry writes are atomic. No critical bugs were found.

Four warnings stand out: a race condition in `jobs.py`'s lock-check pattern, a missing `return type annotation` on a public-facing helper, a silent data-loss path in `lifecycle.uninstall` when `module_dir` does not exist, and a `supervisor._handles` / `_runtime_entries` private-attribute access from `lifecycle.uninstall` that couples two modules through internals. Four info-level items cover dead-code duplication, a missing `__init__.py` check, and minor quality gaps.

---

## Warnings

### WR-01: TOCTOU race in `jobs.py` — lock check is not atomic

**File:** `bot/dashboard/jobs.py:146-157` and `160-177`

**Issue:** `start_install` and `start_uninstall` check `_lock.locked()` and then immediately call `asyncio.create_task(...)` without holding the lock. Between the `if _lock.locked()` check and the task being scheduled, another coroutine can pass the same check and enqueue a second concurrent job. The actual `async with _lock:` inside the worker prevents the subprocess calls from overlapping, but two `JobState` objects are created, both marked `"running"`, and both are stored in `_jobs` — so the API reports two concurrent jobs and the second one will wait silently inside the worker, appearing stale to the caller.

**Fix:** Remove the pre-check and instead use `acquire(blocking=False)` (i.e., `_lock.locked()` is never atomic-safe in asyncio). The idiomatic asyncio pattern is to `try: _lock.acquire_nowait()` (not available on `asyncio.Lock`) — the correct alternative is to replace the bare `asyncio.Lock` with a flag protected by the lock itself, or restructure so the task immediately acquires the lock before creating the `JobState`:

```python
# Preferred: attempt acquire before creating the job
async def start_install(module_name, module_dir, hub_dir, *, config=None):
    if not await _lock.acquire():          # should never block — Lock.acquire() always returns True
        ...                                # unreachable; use the pattern below instead
    ...

# Correct pattern: use a separate boolean flag under lock
_running: bool = False

async def start_install(...) -> JobState:
    async with _lock:
        if _running:
            raise InProgressError("another module operation in progress")
        # ... create job, set _running = True, schedule task
```

Or at minimum, document that the TOCTOU window is accepted (one extra queued job) and ensure the second job transitions to `"failed"` immediately when it cannot acquire, rather than waiting silently.

---

### WR-02: Silent data loss in `lifecycle.uninstall` when `module_dir` does not exist

**File:** `bot/modules/lifecycle.py:365-382`

**Issue:** When `module_dir.is_dir()` is `False`, `manifest` is set to `None` (line 365) and the `uninstall.sh` script is silently skipped entirely. Control then falls through to `remove_entry` (registry cleanup), config/state purge, and the MODS-05 leakage check is also skipped (manifest is None). This means a module whose on-disk directory has been manually removed can be uninstalled without running its cleanup script, with no warning to the caller. Owned paths that the script would have cleaned up (e.g., symlinks, hub-dir entries) are silently leaked. This can leave the system in a dirty state.

**Fix:** Log a `WARNING` (at minimum) when `module_dir` is missing, to make it explicit that the uninstall script was skipped. Consider raising `FileNotFoundError` unless a `force=True` flag is passed:

```python
if not module_dir.is_dir():
    logger.warning(
        "module %r: module_dir %s does not exist — uninstall.sh skipped. "
        "Owned paths will not be verified.",
        name, module_dir,
    )
    manifest = None
else:
    manifest = validate_manifest(module_dir)
```

---

### WR-03: `lifecycle.uninstall` reaches into `Supervisor` private attributes

**File:** `bot/modules/lifecycle.py:350-363`

**Issue:** `uninstall()` directly reads `supervisor._runtime_entries` (line 353) and mutates `supervisor._handles` and `supervisor._runtime_entries` (lines 362–363). This couples `lifecycle` to `Supervisor` internals and bypasses any invariants the `Supervisor` class might enforce in the future (e.g., lock-protected mutations, event emission). If `Supervisor` is refactored, these silent mutations will break without a compiler/type-checker warning.

**Fix:** Add a `remove_module(name: str)` method to `Supervisor` that encapsulates retrieving the runtime entry, calling `on_stop`, and clearing the internal dicts. `lifecycle.uninstall` calls this method instead of reaching into private state:

```python
# In Supervisor:
async def remove_module(self, name: str) -> None:
    """Stop a running module and remove it from supervisor state."""
    handle = self._handles.get(name)
    if handle is None:
        return
    runtime_entry = self._runtime_entries.get(name)
    if runtime_entry:
        mod = importlib.import_module(runtime_entry)
        await mod.on_stop(handle)
    self._handles.pop(name, None)
    self._runtime_entries.pop(name, None)

# In lifecycle.uninstall:
if supervisor is not None:
    try:
        await supervisor.remove_module(name)
    except Exception:
        logger.exception("module %s on_stop failed — continuing uninstall", name)
```

---

### WR-04: Missing return-type annotation on `_make_post_init`

**File:** `bot/modules_runtime/telegram_bridge.py:72`

**Issue:** `_make_post_init` has a `# type: ignore[return]` suppression comment and no explicit return type annotation. The project convention (CLAUDE.md) requires type hints on all function parameters and returns. More importantly, the suppression silences mypy/pyright for the entire return-type check of this function, hiding any future type error in the returned closure. The `# type: ignore[return]` is likely present because the function body has no explicit `return` on all code paths — the nested `async def _post_init` is defined but the outer function returns `None` unless an explicit `return _post_init` is present.

**Fix:** Add the return statement and type annotation:

```python
from collections.abc import Callable, Coroutine
from typing import Any

def _make_post_init(ctx: AppContext) -> Callable[[Any], Coroutine[Any, Any, None]]:
    async def _post_init(app: Any) -> None:
        logger.info("telegram-bridge post_init (data_path=%s)", ctx.data_path)
    return _post_init   # explicit return — remove # type: ignore[return]
```

---

## Info

### IN-01: Duplicate token-seed implementations

**File:** `bot/main.py:55-100` and `bot/modules/lifecycle.py:269-305`

**Issue:** There are two independent implementations of the "seed TELEGRAM_BOT_TOKEN from env into config" logic: `_seed_telegram_bridge_token` in `main.py` (writes to `module_dir/config.json`) and `seed_bridge_token_from_env` in `lifecycle.py` (writes to the registry entry's config dict). They write to different locations and neither calls the other. The test suite exercises both independently. Having two seed paths means a token seeded into `registry.json` may not appear in `config.json` (the file the supervisor actually passes to `on_start`), and vice versa. The `Supervisor.start_all` reads `entry.get("config", {})` from the registry — so `lifecycle.seed_bridge_token_from_env` is the operative one for runtime. The `main.py` variant writes to `module_dir/config.json`, which is only used for idempotency checks on subsequent boots.

**Suggestion:** Document clearly which path is canonical and whether both are intentionally separate. If `lifecycle.seed_bridge_token_from_env` is the operative path (registry → supervisor), the `main.py` variant should either be removed or call the lifecycle version.

---

### IN-02: `asyncio.Lock` instantiated at module import time in `jobs.py`

**File:** `bot/dashboard/jobs.py:43`

**Issue:** `_lock: asyncio.Lock = asyncio.Lock()` is assigned at module level (import time). In Python 3.10+ this is safe because `asyncio.Lock` no longer binds to the running event loop at construction. However, `_jobs: dict[str, "JobState"] = {}` is also module-level process state — if the dashboard module is ever imported in a subprocess or test process that later runs multiple event loops (e.g., `pytest-asyncio` with `asyncio_mode = "auto"`), stale job state could persist across tests. The existing test isolation appears adequate, but a module-level reset function (or moving the lock/dict into a class) would improve testability.

**Suggestion:** Wrap `_lock` and `_jobs` in a `JobRunner` class, or add a `_reset_for_tests()` function analogous to the existing `_set_retention_for_tests`.

---

### IN-03: `bot/modules_runtime/` package missing `__init__.py`

**File:** `bot/modules_runtime/telegram_bridge.py` (directory level)

**Issue:** `bot/modules_runtime/telegram_bridge.py` is imported via `importlib.import_module("bot.modules_runtime.telegram_bridge")` at runtime. For this to work, `bot/modules_runtime/` must be a Python package (i.e., contain an `__init__.py`). If the file is absent, the import will fail with `ModuleNotFoundError` at startup. The tests currently pass, which suggests the `__init__.py` exists — but it is not listed in the reviewed files and was not confirmed.

**Suggestion:** Verify `bot/modules_runtime/__init__.py` exists and add it to CI file-presence checks or the test suite (similar to `test_telegram_bridge_manifest_declares_runtime_entry` in `test_bridge_module.py`).

---

### IN-04: `test_skeleton.py::TestEnvValidation::test_missing_telegram_token` is misleading after Phase 8

**File:** `tests/test_skeleton.py:31-34`

**Issue:** `test_missing_telegram_token` deletes both `TELEGRAM_BOT_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN` then asserts `SystemExit(1)`. After Phase 8, `TELEGRAM_BOT_TOKEN` is no longer required — so this test passes because `CLAUDE_CODE_OAUTH_TOKEN` is missing, not because `TELEGRAM_BOT_TOKEN` is missing. The test name is now incorrect and would continue passing even if `TELEGRAM_BOT_TOKEN` were accidentally re-added to `REQUIRED_ENV_VARS`.

**Suggestion:** Rename the test to `test_missing_claude_oauth_token` and only delete `CLAUDE_CODE_OAUTH_TOKEN`, making the assertion specific to the variable actually being tested.

---

_Reviewed: 2026-04-15T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
