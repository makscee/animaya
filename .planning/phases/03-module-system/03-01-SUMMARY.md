---
phase: 03-module-system
plan: 01
subsystem: module-system
tags: [pydantic, schema, manifest, strict-mode]
requirements: [MODS-01]
requires:
  - pydantic>=2.0 (added Plan 00)
  - tests/modules/ fixtures (added Plan 00)
provides:
  - bot.modules package (public API scaffold)
  - bot.modules.validate_manifest(module_dir) loader
  - bot.modules.ModuleManifest strict pydantic v2 BaseModel
  - bot.modules.ModuleScripts sub-schema
affects:
  - bot/ tree (new bot/modules/ subpackage)
tech_stack:
  added:
    - pydantic v2 ConfigDict(extra="forbid") strict schema
  patterns:
    - Field(pattern=...) inline regex instead of separate validator
    - default_factory=list/ModuleScripts for mutable defaults
    - Exceptions propagate (FileNotFoundError, JSONDecodeError, ValidationError)
key_files:
  created:
    - bot/modules/__init__.py
    - bot/modules/manifest.py
  modified: []
decisions:
  - Used Field(pattern=SEMVER_PREFIX_PATTERN) at field level (RESEARCH Pattern 1) rather than a @field_validator method — simpler, zero custom code
  - default_factory=ModuleScripts for scripts field (not bare default) — avoids mutable-default trap even though ModuleScripts is BaseModel (defensive, per RESEARCH Pitfall 5)
  - owned_paths REQUIRED (D-08 explicit) — no default, forcing manifest authors to declare leakage surface up front
carry_forward_threats:
  - T-03-01-02 (path traversal in owned_paths) → Plan 03 lifecycle must reject absolute paths and ".." segments
  - T-03-01-05 (name/folder mismatch) → Plan 03 install must assert manifest.name == module_dir.name
metrics:
  duration_min: 2
  tasks_completed: 1
  files_created: 2
  files_modified: 0
  completed_date: 2026-04-14
---

# Phase 3 Plan 01: ModuleManifest Schema (MODS-01) Summary

Implements the strict pydantic v2 `ModuleManifest` contract that every Phase 3 module lifecycle operation (install, uninstall, assemble) validates against. Ships `bot/modules/` package skeleton; flips Plan 00's 4 manifest test stubs from SKIPPED to PASSED.

## What Was Built

1. **`bot/modules/manifest.py`** (~100 lines) —
   - `ModuleScripts(BaseModel)`: strict sub-schema for lifecycle script filenames (`install.sh`, `uninstall.sh` defaults). D-09.
   - `ModuleManifest(BaseModel)`: strict top-level schema with required fields `manifest_version` (int, ge=1), `name` (non-empty str), `version` (semver-prefix regex), `system_prompt_path` (non-empty str), `owned_paths` (list[str], required); optional `scripts`, `depends` (default []), `config_schema` (default None). D-08 + D-09 + D-10.
   - `validate_manifest(module_dir)`: loader reading `manifest.json`, raising `FileNotFoundError` / `json.JSONDecodeError` / `pydantic.ValidationError` with explicit docstring contract. T-03-01-03 mitigation.
   - Module-level `logger = logging.getLogger(__name__)` per project convention.

2. **`bot/modules/__init__.py`** (~15 lines) — Public API re-exports `ModuleManifest`, `ModuleScripts`, `validate_manifest`; `__all__` declared. Docstring enumerates what later plans will add (registry, install/uninstall, assembler).

## Verification

```
$ .venv/bin/python -m pytest tests/modules/test_manifest.py -v
tests/modules/test_manifest.py::TestManifest::test_valid_manifest_parses PASSED     [ 25%]
tests/modules/test_manifest.py::TestManifest::test_invalid_rejected PASSED          [ 50%]
tests/modules/test_manifest.py::TestManifest::test_missing_required_field_rejected PASSED [ 75%]
tests/modules/test_manifest.py::TestManifest::test_semver_prefix_accepted PASSED    [100%]
============================== 4 passed in 0.10s ===============================

$ .venv/bin/python -c "from bot.modules import ModuleManifest, validate_manifest; print('ok')"
ok

$ .venv/bin/python -m ruff check bot/modules/
All checks passed!

$ .venv/bin/python -c "... model_validate({..., 'bogus':1})" 2>&1 | grep -iE 'extra|forbid|bogus'
    from bot.modules.manifest import ... 'bogus':1
bogus
  Extra inputs are not permitted [type=extra_forbidden, input_value=1, input_type=int]
```

All 8 plan acceptance criteria from `<acceptance_criteria>` pass.

## Carry-Forward Threats

Per `<threat_model>`, two threats flagged `mitigate → defer` by this plan — schema captures the strings but cannot enforce filesystem semantics. Plan 03 (MODS-02 install/uninstall) MUST resolve both:

| Threat ID | Disposition | Required in Plan 03 |
|-----------|-------------|---------------------|
| T-03-01-02 | Elevation of Privilege via `owned_paths` path traversal | Resolve each `owned_paths` entry against `ANIMAYA_HUB_DIR`; reject absolute paths and any `..` segment before any FS touch. |
| T-03-01-05 | Spoofing via `name` ≠ folder name | In install flow, assert `manifest.name == module_dir.name`; fail-fast with clear error. |

No new threat surface introduced beyond Plan 00's declared boundary (module author → bot via manifest.json). T-03-01-01 (unknown fields) and T-03-01-03 (malformed JSON) fully mitigated at this layer.

## Deviations from Plan

None — plan executed exactly as written. Zero auto-fixes applied; all 8 acceptance grep checks passed on first run; all 4 tests passed on first run.

### Auth Gates

None.

### Deferred Issues

None for this plan. Note: `pytest tests/modules/` now shows 16 failures in `test_registry.py`, `test_lifecycle.py`, `test_assembler.py`, `test_roundtrip.py`, `test_isolation.py` — these are EXPECTED. Plan 00's `pytestmark = skipif(not _HAS_MODS)` flipped them from SKIPPED to ACTIVE the moment `bot.modules` imported. They test APIs (`read_registry`, `install`, `uninstall`, `assemble_claude_md`) that this plan explicitly does NOT implement — they are in-scope for Plans 02-06 per the published wave schedule. Not a regression; not in scope here.

## Commits

- `4c619e0` feat(03-01): add strict pydantic ModuleManifest schema (MODS-01)

## Downstream Effects

- **Plan 02 (MODS-03, registry):** Can now import `ModuleManifest` and extend `bot/modules/__init__.py` exports with `read_registry`, `write_registry`, `list_installed`.
- **Plan 03 (MODS-02, lifecycle):** Must consume `validate_manifest(module_dir)` in install flow and add T-03-01-02 + T-03-01-05 enforcement above the schema layer.
- **Plan 04 (MODS-04, assembler):** Reads validated `ModuleManifest.system_prompt_path` to locate each module's prompt.md.
- **Test activation:** 4 of the 21 Plan 00 stubs now PASS permanently. Remaining 17 activate as Plans 02-06 ship.

## Self-Check: PASSED

Verified on disk:
- `bot/modules/__init__.py` exists (19 lines) — FOUND.
- `bot/modules/manifest.py` exists (101 lines) — FOUND.
- Commit `4c619e0` present in `git log --oneline` — FOUND.
- `grep 'extra="forbid"' bot/modules/manifest.py` matches twice (ModuleScripts + ModuleManifest) — FOUND.
- `grep 'class ModuleManifest\|class ModuleScripts' bot/modules/manifest.py` — both found.
- `grep 'logger = logging.getLogger(__name__)' bot/modules/manifest.py` — FOUND.
- All 4 manifest tests PASSED, ruff clean, import smoke test `ok`.
