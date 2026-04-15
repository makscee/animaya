---
phase: 03-module-system
plan: 02
subsystem: module-system
tags: [registry, json, atomic-write, persistence]
requirements: [MODS-03]
requires:
  - bot.modules (Plan 01 package skeleton)
  - tests/modules/test_registry.py (Plan 00 stubs)
provides:
  - bot.modules.read_registry(hub_dir) -> dict
  - bot.modules.write_registry(hub_dir, data) — atomic temp+os.replace
  - bot.modules.list_installed(hub_dir) -> list[str] (install-order sort)
  - bot.modules.get_entry(hub_dir, name) -> dict | None
  - bot.modules.add_entry(hub_dir, entry) — rejects duplicate name (D-14)
  - bot.modules.remove_entry(hub_dir, name) — KeyError on missing
affects:
  - bot/modules/ (new registry.py; extended __init__.py exports)
tech_stack:
  added: []
  patterns:
    - Atomic JSON write via sibling temp file + os.replace (RESEARCH Pattern 2)
    - Missing-file graceful return (empty registry) for first-install bootstrap
    - Stdlib exceptions (ValueError, KeyError) rather than custom classes
    - ISO-8601 lexicographic sort for temporal install order (D-16)
key_files:
  created:
    - bot/modules/registry.py
  modified:
    - bot/modules/__init__.py
decisions:
  - Use os.replace (not os.rename) for cross-platform atomic semantics
  - Use target.with_suffix(target.suffix + ".tmp") so temp is sibling of
    registry.json (same filesystem → atomic rename guarantee)
  - Validate structure on read (modules key + list type); raise ValueError
    early on corruption instead of silent fallthrough
  - add_entry enforces full D-07 + A2 key set (name, version, manifest_version,
    installed_at, config, depends) — fails fast before partial writes
carry_forward_threats:
  - T-03-02-03 (concurrent-writer DoS) → Phase 5 dashboard write path needs
    file locking (fcntl.flock or filelock lib)
  - T-03-02-04 (config snapshot stores user input verbatim) → Phase 4 identity
    module planning must specify redaction if any module accepts secrets in
    config_schema
  - T-03-02-05 (malicious module name with path separators) → Plan 03 install
    flow must validate name regex ^[a-z][a-z0-9_-]*$ before add_entry
metrics:
  duration_min: 2
  tasks_completed: 1
  files_created: 1
  files_modified: 1
  completed_date: 2026-04-14
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 3 Plan 02: Registry Layer (MODS-03) Summary

Implements the durable JSON registry at `<hub_dir>/registry.json` that Plans 03
(install/uninstall) and 04 (CLAUDE.md assembler) depend on. Atomic writes
survive crashes mid-write; missing-file reads return empty for first-boot
bootstrapping. Flips the 4 Plan 00 registry test stubs from FAIL to PASS.

## What Was Built

1. **`bot/modules/registry.py`** (~120 lines) — Pure-function registry module:
   - `read_registry(hub_dir) -> dict` — graceful missing-file fallback
     (`{"modules": []}`); raises `ValueError` on structurally broken JSON.
   - `write_registry(hub_dir, data)` — atomic: writes `registry.json.tmp`
     then `os.replace(tmp, target)`. Auto-creates hub_dir parents.
   - `list_installed(hub_dir)` — names in install order via ISO-8601
     lexicographic sort on `installed_at`.
   - `get_entry(hub_dir, name)` — single-entry lookup, returns None if absent.
   - `add_entry(hub_dir, entry)` — enforces D-07 + A2 required keys; rejects
     duplicate names with `ValueError`.
   - `remove_entry(hub_dir, name)` — `KeyError` on missing (fail-loud).
   - Module-level `logger = logging.getLogger(__name__)` per convention.

2. **`bot/modules/__init__.py`** — Extended Plan 01's re-exports with the full
   registry API. `__all__` now lists 9 names spanning MODS-01 + MODS-03.

## Verification

```
$ .venv/bin/python -m pytest tests/modules/test_registry.py tests/modules/test_manifest.py -v
tests/modules/test_registry.py::TestRegistry::test_read_missing_registry_returns_empty PASSED
tests/modules/test_registry.py::TestRegistry::test_write_then_read_roundtrip PASSED
tests/modules/test_registry.py::TestRegistry::test_atomic_write_no_partial_file PASSED
tests/modules/test_registry.py::TestRegistry::test_list_installed_returns_names PASSED
tests/modules/test_manifest.py::TestManifest::test_valid_manifest_parses PASSED
tests/modules/test_manifest.py::TestManifest::test_invalid_rejected PASSED
tests/modules/test_manifest.py::TestManifest::test_missing_required_field_rejected PASSED
tests/modules/test_manifest.py::TestManifest::test_semver_prefix_accepted PASSED
============================== 8 passed in 0.14s ===============================

$ .venv/bin/python -c "from bot.modules import read_registry, write_registry, list_installed, get_entry, add_entry, remove_entry; print('ok')"
ok

$ .venv/bin/python -m ruff check bot/modules/
All checks passed!

$ .venv/bin/python -c "...read_registry / add_entry roundtrip..."
roundtrip ok
```

All 4 registry tests + all 4 manifest regression tests pass. Ruff clean.
All 10 acceptance criteria from `<acceptance_criteria>` verified.

## Plan Verification Checklist

1. [x] `pytest tests/modules/test_registry.py -v` shows 4 passed
2. [x] `pytest tests/modules/test_manifest.py -v` still shows 4 passed (no regression)
3. [x] `from bot.modules import read_registry, list_installed, add_entry, remove_entry` works
4. [x] Atomic-write verified by test (no .tmp stragglers)

## Threat Surface Status

All three Plan 02 STRIDE threats mitigated or deferred per plan:

| Threat ID | Status | Notes |
|-----------|--------|-------|
| T-03-02-01 (crash mid-write corruption) | mitigated | os.replace + test_atomic_write_no_partial_file |
| T-03-02-02 (malformed JSON tampering) | mitigated | read_registry validates structure, raises ValueError with path context |
| T-03-02-03 (concurrent writer DoS) | accept → carry-forward | Phase 5 dashboard writes need file lock |
| T-03-02-04 (config snapshot leaks secrets) | defer → carry-forward | Phase 4 identity module planning must specify redaction |
| T-03-02-05 (path-traversal module names) | defer → carry-forward | Plan 03 install must validate name regex ^[a-z][a-z0-9_-]*$ |

No new threat surface introduced. No threat_flags.

## Deviations from Plan

None — plan executed exactly as written. Zero auto-fixes applied. All 4
registry tests and all 4 manifest regression tests passed on first run. Ruff
clean on first run. Acceptance criteria roundtrip one-liner passed on first run.

### Auth Gates

None.

### Deferred Issues

None for this plan. Remaining `tests/modules/` failures (lifecycle 6,
assembler 3, roundtrip 2, isolation 2) test APIs owned by Plans 03-06 and
are not in scope here — same status as end of Plan 01.

## Commits

- `1893091` feat(03-02): add registry.json read/write/query layer (MODS-03)

## Downstream Effects

- **Plan 03 (MODS-02, lifecycle):** install flow will call `validate_manifest`
  then `add_entry(hub_dir, {name, version, manifest_version, installed_at,
  config, depends})`; uninstall will call `remove_entry(hub_dir, name)`.
  Must add name-regex validation (T-03-02-05) before add_entry.
- **Plan 04 (MODS-04, assembler):** will call `list_installed(hub_dir)` to
  enumerate modules in install order, then `get_entry` to look up each
  module's version/config when composing CLAUDE.md sections.
- **Test activation:** 4 additional Plan 00 stubs now PASS permanently
  (total active: 8 of 21). Remaining 13 await Plans 03-06.

## Self-Check: PASSED

Verified on disk:
- `bot/modules/registry.py` exists (~120 lines) — FOUND.
- `bot/modules/__init__.py` updated — FOUND (`grep 'read_registry'` matches).
- Commit `1893091` present in `git log --oneline` — FOUND.
- `grep 'os\.replace' bot/modules/registry.py` — FOUND.
- `grep 'def read_registry\|def write_registry\|def list_installed\|def add_entry\|def remove_entry' bot/modules/registry.py` — all FOUND.
- `grep 'logger = logging.getLogger(__name__)' bot/modules/registry.py` — FOUND.
- All 4 registry tests PASSED; all 4 manifest regression tests PASSED; ruff clean; import smoke test ok; roundtrip ok.
