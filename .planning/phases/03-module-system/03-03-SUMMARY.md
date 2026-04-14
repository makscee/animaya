---
phase: 03-module-system
plan: 03
subsystem: module-system
tags: [lifecycle, install, uninstall, subprocess, rollback, path-traversal]
requirements: [MODS-02]
requires:
  - bot.modules.manifest (Plan 01: ModuleManifest, validate_manifest)
  - bot.modules.registry (Plan 02: read/add/remove/get_entry, list_installed)
  - tests/modules/test_lifecycle.py + conftest fixtures (Plan 00)
provides:
  - bot.modules.install(module_dir, hub_dir, *, config) -> dict
  - bot.modules.uninstall(name, hub_dir, module_dir) -> None
  - bot.modules.lifecycle.DEFAULT_MODULES_ROOT / DEFAULT_HUB_DIR
  - bot.modules.lifecycle.NAME_PATTERN (^[a-z][a-z0-9_-]*$)
  - python -m bot.modules {install,uninstall,list} internal CLI
affects:
  - bot/modules/ (lifecycle.py new; __init__.py extended; __main__.py new)
tech_stack:
  added:
    - subprocess (stdlib) for install.sh / uninstall.sh invocation
  patterns:
    - Env-injection contract (ANIMAYA_MODULE_DIR/HUB_DIR/CONFIG_JSON) via os.environ.copy() + subprocess.run(env=...)
    - Auto-rollback on non-zero rc: best-effort uninstall.sh + owned_paths leakage audit
    - Path containment via Path.resolve() + relative_to() for T-03-01-02 traversal defense
    - argparse subcommands for internal CLI (D-03 / D-04: not user-facing)
key_files:
  created:
    - bot/modules/lifecycle.py (~237 lines)
    - bot/modules/__main__.py (~79 lines)
  modified:
    - bot/modules/__init__.py (install/uninstall re-export; docstring plan status)
decisions:
  - install() signature takes module_dir Path (not name) to match test contract;
    CLI resolves name → DEFAULT_MODULES_ROOT/name bridge. Plan's <interfaces>
    block used name+modules_root; tests (authoritative per plan behavior
    section) use positional path. Deviation Rule 1 applied.
  - Leakage check: rollback path LOGS only (best-effort per D-13);
    uninstall() path RAISES (authoritative per MODS-05).
  - hub_dir.mkdir(parents=True, exist_ok=True) before running install.sh so
    scripts can write to ${ANIMAYA_HUB_DIR} without pre-arranging the dir.
  - Containment check uses Path.relative_to() for cross-platform correctness
    (avoids str.startswith() edge cases with symlinks / case-insensitive FS).
carry_forward_threats:
  - T-03-03-05 (ANIMAYA_CONFIG_JSON secret leakage via ps/env) → Phase 4 modules
    that accept secrets in config_schema MUST document this. Phase 3 modules
    pass empty config, so surface is latent.
  - T-03-03-07 (install.sh DoS — no timeout) → Phase 5 dashboard install endpoint
    SHOULD add subprocess timeout.
  - T-03-03-09 (os.environ.copy() leaks TELEGRAM_BOT_TOKEN + CLAUDE_CODE_OAUTH_TOKEN
    into install.sh) → Phase 4+ should consider an allowlist. For Phase 3,
    bridge module legitimately needs DATA_PATH from bot env; documented in
    module-authoring guide (Plan 05).
metrics:
  duration_min: 3
  tasks_completed: 2
  files_created: 2
  files_modified: 1
  completed_date: 2026-04-14
---

# Phase 3 Plan 03: Install/Uninstall Lifecycle (MODS-02) Summary

Implements the end-to-end install and uninstall orchestration — every
Phase 3+ module lifecycle operation flows through this path. Wires D-11
env injection, D-12 registry-after-script-success ordering, D-13
auto-rollback on install failure, D-14 no-reinstall, and D-15
dependency rules. Closes three carry-forward threats from Plans 01 & 02.

## What Was Built

1. **`bot/modules/lifecycle.py`** (~237 lines) —
   - `install(module_dir, hub_dir, *, config=None) -> dict`:
     validate_manifest → name regex → name/folder match → owned_paths
     traversal defense → D-14 re-install reject → D-15 dep check → run
     install.sh with ANIMAYA_MODULE_DIR/HUB_DIR/CONFIG_JSON env → on
     rc==0 write registry entry; on rc!=0 rollback + raise RuntimeError.
   - `uninstall(name, hub_dir, module_dir) -> None`:
     name validation → registry lookup (KeyError if missing) → dependents
     check (D-15 reverse) → run uninstall.sh → remove_entry → MODS-05
     authoritative leakage check (RuntimeError on leak).
   - `_rollback_after_failed_install()`: best-effort uninstall.sh +
     leakage audit that logs (doesn't raise).
   - `_validate_name`, `_validate_owned_paths`, `_resolve_owned_path`:
     three-layer defense closing T-03-01-02, T-03-01-05, T-03-02-05.
   - `_run_script()`: single source of subprocess.run() behavior; env
     copy + injection, bash executor, cwd=module_dir, rc captured.
   - `DEFAULT_MODULES_ROOT` / `DEFAULT_HUB_DIR` module constants.

2. **`bot/modules/__main__.py`** (~79 lines) — Internal CLI:
   - argparse with `install`, `uninstall`, `list` subcommands.
   - Bridges CLI name-based UX (`install bridge`) to path-based
     lifecycle API (`install(DEFAULT_MODULES_ROOT / "bridge", ...)`).
   - `--config-json` flag for install; stored in registry entry.
   - Exit 0 on success, 1 on ValueError / KeyError / RuntimeError /
     FileNotFoundError. Pattern matches `bot/main.py`.
   - `main(argv=None)` testable; `if __name__ == "__main__": sys.exit(main())`.

3. **`bot/modules/__init__.py`** — Extended re-exports:
   - Added `install`, `uninstall` to imports + `__all__`.
   - Docstring now marks Plan 03 done; Plan 04 (assembler) pending.

## Verification

```
$ .venv/bin/python -m pytest tests/modules/test_lifecycle.py -v
tests/modules/test_lifecycle.py::TestLifecycle::test_install_runs_script_and_updates_registry PASSED
tests/modules/test_lifecycle.py::TestLifecycle::test_install_rejects_already_installed PASSED
tests/modules/test_lifecycle.py::TestLifecycle::test_install_failure_triggers_rollback PASSED
tests/modules/test_lifecycle.py::TestLifecycle::test_uninstall_removes_registry_entry PASSED
tests/modules/test_lifecycle.py::TestLifecycle::test_uninstall_of_uninstalled_module_rejected PASSED
tests/modules/test_lifecycle.py::TestLifecycle::test_missing_dependency_rejected PASSED
============================== 6 passed in 0.26s ===============================

$ .venv/bin/python -m pytest tests/modules/test_manifest.py tests/modules/test_registry.py tests/modules/test_lifecycle.py -v
============================== 14 passed in 0.21s ==============================

$ .venv/bin/python -m ruff check bot/modules/
All checks passed!

$ .venv/bin/python -c "from bot.modules import install, uninstall; print('ok')"
ok

$ .venv/bin/python -m bot.modules --help
usage: python -m bot.modules [-h] {install,uninstall,list} ...
positional arguments:
  {install,uninstall,list}
    install             Install a module
    uninstall           Uninstall a module
    list                List installed modules
```

All Task 1 + Task 2 acceptance criteria verified.

## Plan Verification Checklist

1. [x] `pytest tests/modules/test_lifecycle.py -v` → 6 passed
2. [x] `pytest tests/modules/ -v` (manifest + registry + lifecycle) → 14 passed
       (roundtrip / assembler / isolation still skipped — Wave 3 scope)
3. [x] `python -m bot.modules --help` works; subcommands exposed
4. [x] `ruff check bot/modules/` clean
5. [x] Carry-forwards T-03-01-02 (path traversal), T-03-01-05 (name/folder),
       and T-03-02-05 (name regex) closed here
6. [x] Error-message substrings present in source:
       `"already installed"`, `"missing dependency"`, `"not installed"`,
       `"install.sh failed"` — all verified

## Threat Surface Status

| Threat ID | Category | Disposition | Notes |
|-----------|----------|-------------|-------|
| T-03-03-01 | EoP via path traversal | mitigated | `_validate_owned_paths` + `_resolve_owned_path` containment; closes carry-forward T-03-01-02. |
| T-03-03-02 | Spoofing via name/folder mismatch | mitigated | `install()` asserts `module_dir.name == manifest.name`; closes T-03-01-05. |
| T-03-03-03 | Tampering via malicious name | mitigated | `NAME_PATTERN` regex enforced before any FS/subprocess ops; closes T-03-02-05. |
| T-03-03-04 | Command injection via install.sh | accept | Modules are trusted code (D-02). Documented in module-authoring guide (Plan 05). |
| T-03-03-05 | Config secret leakage via ANIMAYA_CONFIG_JSON env | defer → carry-forward | Phase 3 modules pass {}. Phase 4 must document. |
| T-03-03-06 | Rollback failure + undetected leakage | mitigated | `_rollback_after_failed_install` logs leakage even if uninstall.sh fails. Test verifies rollback path. |
| T-03-03-07 | DoS via long-running install.sh | accept → carry-forward | No timeout in Phase 3. Phase 5 dashboard should add. |
| T-03-03-08 | Repudiation (no audit trail) | accept | `installed_at` + hub git-versioning suffices for solo-user model. |
| T-03-03-09 | EoP via env leakage into install.sh | defer → carry-forward | Bridge module needs bot env in Phase 3. Allowlist is Phase 4+. |

No new threat surface introduced beyond the declared boundary (module
author → bot via manifest.json + install.sh).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Public API signature: path-based not name-based**

- **Found during:** Task 1 planning (reading tests/modules/test_lifecycle.py)
- **Issue:** Plan `<interfaces>` block specified
  `install(name, *, modules_root=None, hub_dir=None, config=None)` but
  test file (authoritative per `<behavior>` section) calls
  `mods.install(valid_module_dir, tmp_hub_dir)` positionally with a
  module directory Path, and `mods.uninstall("sample", tmp_hub_dir,
  valid_module_dir)` with name + hub_dir + module_dir.
- **Fix:** Implemented signatures matching the test contract:
  `install(module_dir, hub_dir, *, config=None) -> dict` and
  `uninstall(name, hub_dir, module_dir) -> None`. All semantic
  requirements (validation, rollback, dep check, env injection, registry
  ordering, leakage check) preserved.
- **Files modified:** bot/modules/lifecycle.py, bot/modules/__main__.py
- **Commits:** 6cb9163 (lifecycle), 9c7d5af (CLI bridges name → path via
  `DEFAULT_MODULES_ROOT / name` so D-03 `setup.sh install bridge`
  pattern still works).
- **Why not Rule 4 (architectural):** Same public-API functions
  provided; only the positional/keyword surface changed. Tests anchor
  the contract. No downstream plan depends on the name-based call
  shape — Plan 04 (assembler) reads via `list_installed()` +
  `get_entry()`, and Plan 05 (bridge dogfood) uses the CLI which
  preserves the name-based UX.

**2. [Rule 3 - Unblock] `hub_dir.mkdir(parents=True, exist_ok=True)` before install.sh**

- **Found during:** Task 1 running tests
- **Issue:** Test fixture `tmp_hub_dir` creates the hub dir, so tests
  pass without this, but real-world first-install would fail if
  `hub_dir` doesn't exist yet — install.sh does `touch
  "${ANIMAYA_HUB_DIR}/.sample-marker"` which requires parent dir.
- **Fix:** Create hub_dir with parents before `_run_script()` in
  `install()`. Idempotent; no-op if already exists.
- **Rationale:** Matches `registry.write_registry` which also auto-creates
  parents. Ensures bootstrap works end-to-end.

### Auth Gates

None — fully offline test suite with bash subprocess.

### Deferred Issues

None for this plan. Remaining `tests/modules/` failures (assembler 3,
roundtrip 2, isolation 2) test APIs owned by Plans 04-06 and are not in
scope. 11 of 21 Plan 00 stubs now pass permanently (manifest 4 +
registry 4 + lifecycle 3 visible-as-passed; wait, actually all 6
lifecycle tests now PASSED, so total active-and-green is 14 of 21).

## Commits

- `6cb9163` feat(03-03): add install/uninstall lifecycle with rollback + dep check (MODS-02)
- `9c7d5af` feat(03-03): add python -m bot.modules internal CLI (D-03/D-04)

## Downstream Effects

- **Plan 04 (MODS-04, assembler):** Can rely on `list_installed()`
  returning names of fully-installed modules (install.sh succeeded AND
  registry entry written atomically). No half-installed modules to
  defend against.
- **Plan 05 (MODS-06, bridge dogfood):** `python -m bot.modules install
  bridge` pattern ready. setup.sh can shell out to it.
- **Plan 06 (integration tests):** roundtrip test can exercise full
  install → list → get_entry → uninstall flow via public API.
- **Test activation:** 6 additional Plan 00 stubs now PASS permanently
  (total active-and-green: 14 of 21). Remaining 7 await Plans 04-06.

## Self-Check: PASSED

Verified on disk:
- `bot/modules/lifecycle.py` exists (237 lines) — FOUND.
- `bot/modules/__main__.py` exists (79 lines) — FOUND.
- `bot/modules/__init__.py` updated — FOUND (`install` and `uninstall`
  in imports and `__all__`).
- Commit `6cb9163` present in `git log --oneline` — FOUND.
- Commit `9c7d5af` present in `git log --oneline` — FOUND.
- All 6 lifecycle tests PASSED; 14 total module-suite tests PASSED;
  ruff clean on first run after implementation; import smoke test ok;
  CLI help output shows all 3 subcommands.
- Error-message substrings `"already installed"`, `"missing dependency"`,
  `"not installed"`, `"install.sh failed"` grep-verified present in
  lifecycle.py source.
- Env-injection strings `ANIMAYA_MODULE_DIR`, `ANIMAYA_HUB_DIR`,
  `ANIMAYA_CONFIG_JSON` grep-verified present in lifecycle.py source.
