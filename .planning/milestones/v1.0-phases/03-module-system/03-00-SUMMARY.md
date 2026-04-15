---
phase: 03-module-system
plan: 00
subsystem: module-system
tags: [infra, test-scaffold, pydantic, fixtures]
requires:
  - FastAPI>=0.115 (transitive pydantic already present)
  - pytest>=8.0, pytest-asyncio>=0.23 (from [dev])
provides:
  - pydantic>=2.0 direct dependency
  - tests/modules/ package with 4 shared fixtures
  - tests/modules/fixtures/{valid-module,invalid-manifest}/
  - 6 test stubs covering 21 tests (all skip-until-bot.modules)
affects:
  - pyproject.toml [project].dependencies
  - tests/ tree (new tests/modules/ subtree, no touch to existing tests)
tech_stack:
  added:
    - pydantic 2.13.0 (declared explicitly)
  patterns:
    - pytestmark = skipif(find_spec) for conditional collection
    - copytree-based fixture dirs into tmp_path
    - ANIMAYA_HUB_DIR / ANIMAYA_MODULE_DIR env convention for shell scripts
key_files:
  created:
    - tests/modules/__init__.py
    - tests/modules/conftest.py
    - tests/modules/fixtures/valid-module/manifest.json
    - tests/modules/fixtures/valid-module/install.sh
    - tests/modules/fixtures/valid-module/uninstall.sh
    - tests/modules/fixtures/valid-module/prompt.md
    - tests/modules/fixtures/invalid-manifest/manifest.json
    - tests/modules/test_manifest.py
    - tests/modules/test_registry.py
    - tests/modules/test_lifecycle.py
    - tests/modules/test_assembler.py
    - tests/modules/test_roundtrip.py
    - tests/modules/test_isolation.py
  modified:
    - pyproject.toml
decisions:
  - Switched from importorskip to pytestmark=skipif to satisfy collection-count acceptance
metrics:
  duration_min: 8
  tasks_completed: 3
  files_created: 13
  files_modified: 1
  completed_date: 2026-04-14
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 3 Plan 00: Wave 0 Infrastructure Summary

Adds pydantic>=2.0 as a direct dependency and scaffolds `tests/modules/` with shared fixtures, fixture module directories, and six test stubs (21 tests total) that collect now and activate as each Wave 1-3 plan lands.

## What Was Built

1. **pydantic as direct dep** — `pydantic>=2.0` appended to `[project].dependencies` in `pyproject.toml`. Was transitively pulled by FastAPI but per D-10 and RESEARCH §Pitfall 1, direct declaration is the correct fix. `pip install -e ".[dev]"` installed `pydantic 2.13.0`; strict-mode API (`ConfigDict(extra='forbid')`) verified importable.

2. **Test package scaffold** — `tests/modules/` Python package with:
   - `__init__.py` (package marker)
   - `conftest.py` defining four session-independent fixtures: `tmp_hub_dir`, `valid_module_dir`, `invalid_manifest_dir`, `sample_manifest_dict`.
   - `fixtures/valid-module/` with strict-schema-valid `manifest.json`, `prompt.md`, and executable `install.sh` / `uninstall.sh` shell scripts that use `ANIMAYA_HUB_DIR` / `ANIMAYA_MODULE_DIR` env vars and the `.sample-marker` file convention for lifecycle assertions.
   - `fixtures/invalid-manifest/manifest.json` carrying an `unexpected_field` to exercise pydantic strict rejection.

3. **Six test stubs** — 21 real-assertion tests covering manifest (4), registry (4), lifecycle (6), assembler (3), roundtrip (2), and isolation (2). Each file uses `pytestmark = pytest.mark.skipif(not find_spec('bot.modules'))` so tests COLLECT today (21 collected / 21 skipped) and automatically activate as each wave implements `bot.modules.*`.

## Verification

```
$ python -c "import pydantic; print(pydantic.VERSION)"
2.13.0

$ python -m pytest tests/modules/ --collect-only -q | tail -1
21 tests collected in 0.03s

$ python -m pytest tests/modules/ -q
sssssssssssssssssssss                                                    [100%]
21 skipped in 0.02s
```

All three Wave 0 verification criteria pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocker] Switched from `pytest.importorskip` to `pytestmark = skipif`**

- **Found during:** Task 3 verification
- **Issue:** Plan text (line 253, 289) instructed `pytest.importorskip("bot.modules", ...)` at module top. This causes pytest to skip the module BEFORE collection, so `--collect-only` reported 0 tests. Acceptance criteria (line 301) required `>= 17 collected tests`.
- **Fix:** Replaced with `_HAS_MODS = importlib.util.find_spec("bot.modules") is not None; pytestmark = pytest.mark.skipif(not _HAS_MODS, reason=...)`. Tests now collect and skip cleanly; once `bot.modules` lands, assertions activate unchanged.
- **Files modified:** all six `tests/modules/test_*.py`
- **Commit:** `0a81c41`

### Auth Gates

None.

### Deferred Issues

None.

## Commits

- `6d1f869` feat(03-00): add pydantic>=2.0 as direct dependency
- `4ce9fa4` test(03-00): scaffold tests/modules/ package with fixtures
- `0a81c41` test(03-00): add 6 Wave 1-3 test stubs (21 tests, all skip until bot.modules lands)

## Downstream Effects

- **Wave 1 (Plans 01-02):** Once `bot.modules.__init__` exports `ModuleManifest`, `validate_manifest`, `read_registry`, `write_registry`, `list_installed`, the 8 manifest+registry tests flip to PASS automatically.
- **Wave 2 (Plans 03-05):** Adding `install` / `uninstall` activates the 6 lifecycle + 2 roundtrip tests.
- **Wave 3 (Plan 06):** Adding `assemble_claude_md` activates the 3 assembler tests.
- **Always:** The 2 isolation tests enforce AST-level no-cross-module-imports from now through every future module.

## Self-Check: PASSED

Verified:
- `pyproject.toml` modified (`grep 'pydantic>=2.0'` matches).
- 13 new files all exist on disk under `tests/modules/` and `tests/modules/fixtures/`.
- Shell scripts executable (`0o755`), correct shebang, `set -euo pipefail` present.
- Three commits present in `git log` (`6d1f869`, `4ce9fa4`, `0a81c41`).
- `pytest --collect-only` reports 21 tests, `pytest` reports 21 skipped, no errors.
