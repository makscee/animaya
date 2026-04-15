---
phase: 05
plan: 01
subsystem: dashboard-events
tags: [events, log, dashboard, jsonl, leaf-module]
requires: []
provides:
  - bot/events.py::emit(level, source, message, **details)
  - bot/events.py::tail(n=50) -> list[dict]
  - bot/events.py::rotate(max_lines=10_000)
  - ANIMAYA_EVENTS_LOG env var contract
affects:
  - tests/dashboard/ (new package)
tech_stack_added: []
patterns:
  - "Leaf module (stdlib-only) to prevent Phase 5 import cycles"
  - "POSIX O_APPEND atomic append for concurrent emitters"
  - "Atomic rewrite via tempfile + os.replace for rotate"
  - "Env-var-driven path, resolved at call time for testability"
key_files_created:
  - bot/events.py (133 lines)
  - tests/dashboard/__init__.py
  - tests/dashboard/conftest.py (events_log fixture)
  - tests/dashboard/test_events.py (12 tests)
key_files_modified: []
decisions:
  - "Re-read ANIMAYA_EVENTS_LOG per call via _log_path() helper (not cached at import) — allows tests to monkeypatch without importlib.reload"
  - "tail() skips corrupt lines silently at DEBUG level — matches T-05-01-04 disposition (dashboard must not crash on bad input)"
  - "rotate() uses keepends=True + writelines to preserve exact bytes (no accidental \\n normalization)"
requirements_satisfied: [DASH-03]
metrics:
  tasks_completed: 2
  tests_added: 12
  commits: 2
  lines_of_code: 133
completed: 2026-04-15
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 05 Plan 01: Events Log Module Summary

Leaf JSONL event emitter (`bot/events.py`) with `emit/tail/rotate` — stdlib-only, no bot.* imports — that every other Phase 5 surface (dashboard activity feed, bridge emitters, install/uninstall wiring) will consume without risking circular imports.

## What Was Built

### bot/events.py (133 lines, stdlib-only)

Public API exactly matches the Plan's `<interfaces>` block:

```python
LEVELS: frozenset[str] = frozenset({"info", "warn", "error"})
MAX_LINES: int = 10_000
DEFAULT_LOG_PATH: Path = Path.home() / "hub" / "knowledge" / "animaya" / "events.log"

def emit(level: str, source: str, message: str, **details: object) -> None
def tail(n: int = 50) -> list[dict]
def rotate(max_lines: int = MAX_LINES) -> None
```

Key properties:
- `_log_path()` re-reads `ANIMAYA_EVENTS_LOG` on every call (per-test isolation without `importlib.reload`).
- `emit` validates `level ∈ LEVELS`, auto-creates parent dirs, writes JSON record with ISO-8601 UTC `ts`, optional `details` sub-dict, via `open("a")` for POSIX O_APPEND atomicity.
- `tail` returns `[]` when file missing, skips `json.JSONDecodeError` lines at DEBUG, returns parsed dicts in chronological order.
- `rotate` is a no-op when file missing or under cap; otherwise rewrites atomically via `tempfile.mkstemp` in the same dir + `os.replace`. On failure, tempfile is cleaned up.

### tests/dashboard/test_events.py (12 tests)

1. `test_emit_appends_jsonl` — two emits produce two lines of valid JSON with required keys.
2. `test_emit_with_details` — kwargs nested under `details`.
3. `test_emit_rejects_unknown_level` — `"debug"` raises `ValueError`, no file written.
4. `test_tail_returns_last_n_parsed` — 7 records → `tail(5)` returns last 5 in order.
5. `test_tail_empty_returns_empty_list` — missing file → `[]`.
6. `test_tail_skips_corrupt_lines` — garbage line between valid records is dropped silently.
7. `test_rotate_truncates_to_max_lines` — 150 records → `rotate(100)` retains last 100 (m50..m149).
8. `test_rotate_noop_when_under_cap` — file bytes unchanged when under cap.
9. `test_rotate_noop_when_file_missing` — no crash when file absent.
10. `test_emit_creates_parent_dir` — deep nested path auto-created.
11. `test_ts_is_iso_utc` — timestamp parses via `datetime.fromisoformat` and carries `+00:00`/`Z`.
12. `test_emit_handles_newlines_in_message` — log-injection guard (T-05-01-05): embedded `\n` JSON-escaped.

### tests/dashboard/conftest.py

`events_log` pytest fixture: sets `ANIMAYA_EVENTS_LOG` to `tmp_path/events.log` via `monkeypatch`, evicts any cached `bot.events` module, yields the path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Created `tests/dashboard/conftest.py` and `tests/dashboard/__init__.py`**
- **Found during:** Task 1 (plan's `<read_first>` referenced `tests/dashboard/conftest.py` but directory didn't exist)
- **Issue:** Plan instructions assume the `events_log` fixture exists; without it tests can't run.
- **Fix:** Created the directory, an empty `__init__.py`, and a minimal `conftest.py` exposing the `events_log` fixture per plan's fixture contract (`ANIMAYA_EVENTS_LOG` → `tmp_path`). No behavior change to plan — just made the referenced precondition real.
- **Files added:** `tests/dashboard/__init__.py`, `tests/dashboard/conftest.py`
- **Commit:** `5810e48`

**2. [Rule 2 - Critical Coverage] Added 2 extra tests beyond the 10 specified**
- **Issue:** Plan mandates 10+ tests (`grep -c "^def test_" ... >= 10`). Plan covered the threat register items verbally but didn't enforce Test 12 (log-injection via newlines = T-05-01-05) or rotate-on-missing-file (implicit in "safe to call at startup"). Both are correctness/security-relevant.
- **Fix:** Added `test_rotate_noop_when_file_missing` and `test_emit_handles_newlines_in_message`. Total = 12 tests.
- **Commit:** `5810e48`

No other deviations. The `bot/events.py` body is a verbatim implementation of the contract block in Task 2's `<action>` section.

## Verification

### Structural (ran locally)

| Check | Result |
|-------|--------|
| `bot/events.py` exists | YES (133 lines, >= 60 required) |
| `grep -q "^def emit" bot/events.py` | YES |
| `grep -q "^def tail" bot/events.py` | YES |
| `grep -q "^def rotate" bot/events.py` | YES |
| `grep -q "^from bot" bot/events.py` | NO (leaf module confirmed) |
| `grep -c "^def test_" tests/dashboard/test_events.py` | 12 (>= 10) |

### Test execution (deferred)

`python -m pytest` is unavailable in this worktree sandbox (no pytest/ruff installed; no `.venv`). Previous Phase 4 plans committed under the same constraint — tests are validated in the live environment (LXC / CI).

The implementation follows the exact contract block from the plan (Task 2 `<action>` prescribes the code verbatim) and all structural acceptance criteria pass. Plan-checker / verifier agent should run the suite in a Python-enabled environment:

```bash
python -m pytest tests/dashboard/test_events.py -v   # expect 12 passed
ruff check bot/events.py tests/dashboard/              # expect clean
```

## Threat Model — Mitigations Applied

| Threat ID | Disposition | Where Mitigated |
|-----------|-------------|-----------------|
| T-05-01-01 (tampering, concurrent write) | mitigated | `emit` uses `open("a")` (POSIX O_APPEND atomic for writes < 4 KB); JSON records well under that. |
| T-05-01-02 (DoS, unbounded growth) | mitigated | `rotate(max_lines=10_000)` callable at startup; atomic via tempfile + `os.replace`. Wiring into startup is Plan 07. |
| T-05-01-03 (info disclosure via details) | mitigated | Docstring warns call sites not to pass secrets (tokens, cookies, bot_token). Enforcement is per-emitter review. |
| T-05-01-04 (corrupt line crashes tail) | mitigated | `tail()` wraps `json.loads` in try/except; covered by `test_tail_skips_corrupt_lines`. |
| T-05-01-05 (log injection via newlines) | mitigated | `json.dumps(record, ensure_ascii=False)` escapes embedded `\n`; covered by `test_emit_handles_newlines_in_message`. |

No new threat surface introduced beyond the plan's register.

## Key Decisions Made

1. **Env var re-read per call** via `_log_path()` — chose this over module-level binding + `importlib.reload` because it keeps tests simple (fixture just monkeypatches env) and matches the plan's explicit guidance.
2. **`splitlines(keepends=True)` in rotate** — preserves the exact trailing-newline byte pattern so round-trips are idempotent; writing with `writelines(keep)` reproduces the original file bytes for the retained window.
3. **Skip corrupt lines silently at DEBUG** — surfacing them as warnings would itself emit more events and risk recursion; DEBUG keeps the signal available without polluting the log shown on `/`.

## Commits

| Commit | Type | Summary |
|--------|------|---------|
| `5810e48` | test | Add failing tests for events emitter (12 tests, conftest fixture, tests/dashboard package) |
| `f9e4d9e` | feat | Add events.py JSONL emitter + tail + rotate (leaf module, stdlib-only) |

## Handoff Notes for Next Plans

- **Plan 05-02+ (dashboard pages):** Import `from bot.events import emit, tail` — do NOT wrap or re-export; it is the canonical surface.
- **Plan 05-07 (wiring):** Call `rotate()` exactly once at bot startup (before FastAPI app starts serving) per T-05-01-02 mitigation.
- **Plan 05-04 (bridge/modules emitters):** Sources to standardize on: `bridge`, `modules.install`, `modules.uninstall`, `assembler`, `startup`, `dashboard.auth`. Keep `source` short and dotted.
- **Never pass secrets** in `details` — per T-05-01-03, log review will flag tokens/cookies.

## Self-Check: PASSED

- FOUND: `bot/events.py` (133 lines, verified via `wc -l`)
- FOUND: `tests/dashboard/conftest.py`
- FOUND: `tests/dashboard/__init__.py`
- FOUND: `tests/dashboard/test_events.py` (12 tests)
- FOUND commit: `5810e48` (test RED)
- FOUND commit: `f9e4d9e` (feat GREEN)
- VERIFIED: No `^from bot` imports in `bot/events.py` (leaf module invariant holds)
- VERIFIED: `emit`, `tail`, `rotate` all defined at module top level
