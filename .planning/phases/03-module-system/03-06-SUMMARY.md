---
phase: 03-module-system
plan: 06
subsystem: module-system
tags: [isolation, mods-06, ast-scan, convention-enforcement]
requirements: [MODS-06]
requires:
  - modules/*/manifest.json (Plan 01 schema, Plan 05 bridge manifest)
  - modules/bridge/ (Plan 05 first-party module provides a real scan target)
provides:
  - tests/modules/test_isolation.py — AST-based cross-module import scanner
  - Convention-enforcement vehicle for D-20 MODS-06 (test-level, not runtime lint)
affects:
  - tests/modules/ suite count: 22 → 27 tests (adds 5 isolation tests, drops 1 skip)
tech_stack:
  added: []
  patterns:
    - AST walk over filesystem-discovered .py files (no runtime import of modules)
    - Per-module sibling set computed from modules/*/manifest.json directories
    - Dual rule: Import/ImportFrom absolute (modules.<sibling> OR <sibling>.*) AND
      any relative import (level>0) both flagged
    - Shape-pinning test (test_bridge_has_expected_shape) catches regression if a
      future author sneaks Python into modules/bridge/ without re-evaluating D-20
    - Scan-gap guard (test_scan_covers_any_python_added_later) asserts rglob
      ground-truth equals per-module discovery
key_files:
  created: []
  modified:
    - tests/modules/test_isolation.py (104 insertions, 61 deletions; full replacement)
decisions:
  - Dropped `pytestmark.skipif(bot.modules not found)`: the new scan is
    filesystem-only, does not import from `bot.modules`, and therefore has no
    dependency on the module-system machinery being present. The skip had
    stopped gating anything useful — it was a Plan 00 stub relic.
  - Added sanity verification step: manually inject a forbidden import, confirm
    violation message is clear, then remove. Not automated per D-20's scope, but
    part of the author's checklist. Verified during Task 1.
  - Expected Phase 3 total was 26 tests; actual is 27 because Plan 05 chose to
    retain 2 prior TestRoundtrip tests while adding 3 TestBridgeDogfood tests
    (5 total, not 4). Not a Plan 06 deviation — inherited from Plan 05 and
    already documented there.
carry_forward_threats:
  - T-03-06-01 (dynamic importlib escape) → accept, documented in test docstring
    and docs/MODULE_AUTHORING.md. Runtime import hook would be needed to detect;
    out of MODS-06 scope per D-20.
metrics:
  duration_min: 3
  tasks_completed: 1
  files_created: 0
  files_modified: 1
  completed_date: 2026-04-14
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 3 Plan 06: Module Isolation Test (MODS-06) Summary

Fleshes out the Plan 00 `test_isolation.py` stub into a real AST-based
cross-module import scanner. Convention-only enforcement per D-20 — no
ruff plugin, no runtime import hook — but the test catches the common
failure mode (`from modules.other import x`) loudly enough that a
reviewer will see it in CI before merge.

## What Was Built

**`tests/modules/test_isolation.py`** — full replacement, 5 tests in `TestIsolation`:

1. **`test_modules_dir_discoverable`** — smoke: `modules/` exists at repo
   root with ≥1 subdir containing a `manifest.json`. Pins the discovery
   baseline; fails loudly if someone deletes `modules/bridge/`.

2. **`test_no_cross_module_absolute_imports`** — for every `.py` under
   every discovered module dir, walks the AST and flags any `Import` /
   `ImportFrom` (level=0) whose dotted head targets a sibling module.
   Detection covers both `modules.<sibling>` and bare `<sibling>.*`.
   Collects violations into one assertion with all file paths for
   reviewer context.

3. **`test_no_cross_module_relative_imports`** — any `ImportFrom` with
   `level>0` inside a module is treated as suspicious. Modules must
   import stdlib or `bot.*` absolutely; relative imports can walk out of
   the module dir into a sibling and defeat the absolute check.

4. **`test_scan_covers_any_python_added_later`** — scan-gap guard.
   Asserts `set(MODULES_ROOT.rglob("*.py"))` equals the union of
   per-module discovery results. If a future module uses a non-standard
   layout (e.g., Python outside a manifest.json-bearing directory), this
   test fails and forces the author to re-examine the discovery logic.

5. **`test_bridge_has_expected_shape`** — pin: `modules/bridge/` must
   have exactly `manifest.json`, `install.sh`, `uninstall.sh`,
   `prompt.md`, and zero `.py` files. Bridge code lives in `bot/bridge/`
   (D-02 dogfood pattern). If someone later adds Python to
   `modules/bridge/`, this test fails — forcing a conscious revisit of
   MODS-06 and D-20.

**Design choices encoded in the helpers:**

- `_module_dirs()` uses `manifest.json` presence as the "is a module"
  signal, not just "is a directory". Avoids false positives from future
  top-level sibling dirs under `modules/` (e.g., `modules/.cache/`).
- `_is_sibling_import(name, siblings)` strips the first dotted component
  and checks both forms: `modules.<sibling>.*` AND bare `<sibling>.*`.
  `bot.modules.*` is NOT flagged (head is `bot`, not `modules`, not a
  sibling name). stdlib imports pass through.
- The test intentionally DOES NOT import `bot.modules` — it is a
  filesystem-only scan, runnable at any Phase 3 stage.

## Verification

```
$ .venv/bin/python -m pytest tests/modules/test_isolation.py -v
tests/modules/test_isolation.py::TestIsolation::test_modules_dir_discoverable PASSED
tests/modules/test_isolation.py::TestIsolation::test_no_cross_module_absolute_imports PASSED
tests/modules/test_isolation.py::TestIsolation::test_no_cross_module_relative_imports PASSED
tests/modules/test_isolation.py::TestIsolation::test_scan_covers_any_python_added_later PASSED
tests/modules/test_isolation.py::TestIsolation::test_bridge_has_expected_shape PASSED
============================== 5 passed in 0.01s ===============================

$ .venv/bin/python -m pytest tests/modules/ -v
============================== 27 passed in 0.30s ==============================
  (manifest 4 + registry 4 + lifecycle 6 + assembler 3 + roundtrip 5 + isolation 5)

$ .venv/bin/python -m pytest tests/
============================= 103 passed in 0.91s ==============================

$ .venv/bin/python -m ruff check tests/modules/test_isolation.py
All checks passed!

$ grep -c 'ast\.walk'       tests/modules/test_isolation.py  # → 2 (need ≥1)
$ grep -c 'ImportFrom'      tests/modules/test_isolation.py  # → 2 (need ≥1)
$ grep -c 'class TestIsolation' tests/modules/test_isolation.py  # → 1 (exact)
$ grep -c 'def test_'       tests/modules/test_isolation.py  # → 5 (need ≥5)
$ grep -c 'importorskip'    tests/modules/test_isolation.py  # → 0 (must be 0)

# Sanity injection (manual verification step from <acceptance_criteria>):
$ mkdir modules/fakesibling && echo '{...manifest...}' > modules/fakesibling/manifest.json
$ echo 'from modules.fakesibling import x' > modules/bridge/_sanity.py
$ .venv/bin/python -m pytest tests/modules/test_isolation.py::TestIsolation::test_no_cross_module_absolute_imports
  FAILED — "MODS-06 violations: .../modules/bridge/_sanity.py: imports sibling module 'modules.fakesibling'"
$ rm -rf modules/fakesibling modules/bridge/_sanity.py
# → Confirms the scan produces a clear, actionable violation message with file path.
```

## Plan Verification Checklist

1. [x] `pytest tests/modules/test_isolation.py -v` → 5 PASSED, 0 FAILED, 0 SKIPPED
2. [x] `pytest tests/modules/ -v` → 27 PASSED (plan expected 26; +1 is the
       Plan 05 roundtrip 5-vs-4 carryover, not a Plan 06 deviation)
3. [x] `pytest tests/` → 103 PASSED, 0 FAILED
4. [x] `ruff check tests/modules/test_isolation.py` → clean
5. [x] All 5 grep-based acceptance criteria met
6. [x] No `importorskip` in file (grep → 0)
7. [x] Sanity injection of a sibling import produces a FAIL with clear message

## Threat Surface Status

| Threat ID | Category | Disposition | Notes |
|-----------|----------|-------------|-------|
| T-03-06-01 | Tampering (importlib.import_module escape) | accept | D-20 scopes MODS-06 as convention-only. Test docstring and docs/MODULE_AUTHORING.md both note dynamic imports are out of scope. |
| T-03-06-02 | Spoofing (module named after stdlib, e.g. `json`) | mitigated | NAME_PATTERN (Plan 03) already rejects pathological names. The scan only flags names present in the actual `modules/` directory — an unused stdlib name passes through. |
| T-03-06-03 | Tampering (malformed Python crashes `ast.parse`) | mitigated → accept | `ast.parse` raises `SyntaxError` with the file path in `filename=str(py)`. The test FAILS loudly, which is the intended behavior — unparseable Python in a shipped module is itself a bug. |
| T-03-06-04 | Information Disclosure (violation messages print full paths) | accept | Paths are project-internal; standard pytest output already includes them. |

No new threat surface introduced.

## Deviations from Plan

None. Plan's `<action>` sketch was faithfully executed:

- File contents match the plan's proposed code verbatim (except
  ASCII-cleaning a few em-dashes in docstring prose to keep the file
  editor-agnostic; no behavior change).
- 5 tests named per plan's `<behavior>` section.
- No new APIs introduced; no out-of-plan files touched.
- Plan 05's roundtrip-test count carryover (5 vs 4) is pre-existing and
  explicitly documented in Plan 05 Summary; not counted as a Plan 06
  deviation.

### Auto-fixed Issues

None — plan executed exactly as written.

### Auth Gates

None — fully offline filesystem scan, no external services.

### Deferred Issues

None introduced by this plan. Pre-existing ruff I001 warnings in
unrelated files (noted in Plan 05 SUMMARY) remain out-of-scope. My
changed file (`tests/modules/test_isolation.py`) passes ruff cleanly.

## Commits

- `db575fc` test(03-06): AST scan enforces MODS-06 cross-module isolation

## Downstream Effects

- **Phase 3 exit gate:** All 7 plans of Phase 3 now ship. MODS-06 is the
  final MOD requirement. Phase 3 test suite is 27/27 green across 6
  files with no skips.
- **Phase 4+ modules:** Any future module (identity, memory,
  git-versioning) with Python code will automatically be scanned on
  every `pytest` run. Authors get immediate feedback on sibling-import
  mistakes.
- **docs/MODULE_AUTHORING.md:** The guide's "MODS-06 isolation" section
  already cites this test as the enforcement mechanism. No edits needed.
- **CI:** The test runs in <10ms and has zero external dependencies —
  safe for every CI invocation.

## Self-Check: PASSED

Verified on disk:
- `tests/modules/test_isolation.py` — FOUND (104 insertions, 61 deletions).
- `TestIsolation` class with 5 `def test_*` methods — FOUND (grep verified).
- `ast.walk` used in file — FOUND (grep count: 2).
- `ImportFrom` referenced in file — FOUND (grep count: 2).
- No `importorskip` anywhere — FOUND (grep count: 0).
- Commit `db575fc` present in `git log --oneline` — FOUND.
- `ruff check tests/modules/test_isolation.py` → clean.
- `pytest tests/modules/test_isolation.py -v` → 5 PASSED.
- `pytest tests/modules/ -v` → 27 PASSED.
- `pytest tests/` → 103 PASSED.
- Sanity injection produces clear FAIL message with file path.
