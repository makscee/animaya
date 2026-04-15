---
phase: 03-module-system
plan: 04
subsystem: module-system
tags: [assembler, claude-md, templates, xml-wrap, atomic-write, d18]
requirements: [MODS-04]
requires:
  - bot.modules.manifest (Plan 01: validate_manifest)
  - bot.modules.registry (Plan 02: read_registry)
  - bot.modules.lifecycle (Plan 03: install records module_dir)
  - bot/templates/CLAUDE.md (base template)
  - tests/modules/test_assembler.py (Plan 00 stubs)
provides:
  - bot.modules.assemble_claude_md(hub_dir, *, modules_root=, repo_root=, output_path=, template_path=) -> str
  - Reassembly hook at install() end (D-18)
  - Reassembly hook at uninstall() end (D-18, before leakage raise)
affects:
  - bot/modules/ (new assembler.py; __init__.py export extended)
  - bot/main.py (stub replaced by import from assembler)
  - bot/modules/lifecycle.py (install/uninstall both call assembler; install
    records module_dir in registry entry)
tech_stack:
  added: []
  patterns:
    - Atomic write via temp + os.replace (mirrors registry.py)
    - Graceful degradation (D-18): registry-read / manifest / prompt failures
      produce per-section placeholder comments and WARNINGs, never raise
    - XML wrap `<module name="X">...</module>` at section boundaries (D-17)
    - `</module>` escape-on-ingest prevents one module from closing another's
      section tag (T-03-04-01 mitigation)
    - ISO-8601 lexicographic sort on installed_at for install order (D-16)
    - Module-dir resolution prefers entry["module_dir"] (recorded at install
      time) before falling back to modules_root / name — supports test
      fixtures installed outside DEFAULT_MODULES_ROOT
key_files:
  created:
    - bot/modules/assembler.py
  modified:
    - bot/modules/__init__.py
    - bot/modules/lifecycle.py
    - bot/main.py
decisions:
  - Return type str (content), not Path — tests assert on output substrings.
  - Record module_dir in registry entry so assembler can locate prompt.md for
    modules installed outside DEFAULT_MODULES_ROOT (test fixtures, dev loops).
  - Accept inline prompt via entry["prompt"] for lightweight / test entries
    that skip the full manifest+folder round-trip.
  - Place reassembly call in uninstall() BEFORE the leakage-check raise so a
    leaking uninstall still writes a CLAUDE.md reflecting registry truth.
  - Reassembly failures during install/uninstall are caught+logged, never
    raised — D-18 says assembler must not crash boot or break lifecycle ops.
carry_forward_threats:
  - T-03-04-02 (prompt impersonates core) → accepted; defence relies on XML
    wrap visibility to Claude + module-author trust boundary.
  - T-03-04-05 (huge prompt.md DoS) → accepted; Phase 5 dashboard install
    path should add a size cap.
  - T-03-04-06 (secrets in prompt.md) → accepted; documented in Plan 05
    module-authoring guide.
metrics:
  duration_min: 4
  tasks_completed: 2
  files_created: 1
  files_modified: 3
  completed_date: 2026-04-14
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 3 Plan 04: CLAUDE.md Assembler (MODS-04) Summary

Implements the assembler that merges the core base template with installed
modules' prompts into a single CLAUDE.md at every bot startup and at the end
of every install/uninstall (D-18). Enforces D-16 install order, D-17 XML
section wrap, and D-19 base-first structure with preserved Phase 1 markers.
Flips the 3 Plan 00 assembler test stubs from FAIL to PASS, and unexpectedly
flips the 2 roundtrip tests from skip to PASS as a side effect of recording
`module_dir` in the registry entry.

## What Was Built

1. **`bot/modules/assembler.py`** (~188 lines) — Pure-function assembler:
   - `assemble_claude_md(hub_dir, *, modules_root=None, repo_root=None,
     output_path=None, template_path=None) -> str`
   - Reads base template (`bot/templates/CLAUDE.md`), appends
     `<!-- module-prompts-start --> ... <!-- module-prompts-end -->` with
     per-module sections inside.
   - Empty registry → body is `<!-- No modules installed -->`.
   - Populated registry → body is `\n\n`-joined `<module name="X">...</module>`
     sections in ISO-8601 install order (D-16).
   - `_escape_module_content` replaces `</module>` with `&lt;/module&gt;` so a
     malicious prompt cannot close another module's section (T-03-04-01).
   - `_load_prompt_for_entry` degrades gracefully (D-18): module dir missing,
     manifest invalid, prompt file missing each produce a placeholder comment
     + WARNING log rather than raising.
   - `_resolve_module_dir` prefers `entry["module_dir"]` (written at install
     time) before falling back to `modules_root / entry["name"]`. This lets
     the assembler find modules installed to ad-hoc paths (tests, dev loops).
   - Inline `entry["prompt"]` is honored as a lightweight path for registry
     entries that skip the on-disk manifest round-trip (used by the
     install-order test).
   - Atomic write via `_atomic_write` (temp + `os.replace`), same crash-safety
     pattern as `bot/modules/registry.py`.

2. **`bot/modules/__init__.py`** — Added `assemble_claude_md` to imports
   and `__all__`; docstring Plan-04 line flipped from "pending" to done.

3. **`bot/modules/lifecycle.py`** —
   - `install()` now records `"module_dir": str(module_dir)` in the registry
     entry so the assembler can resolve the prompt file later.
   - `install()` calls `assemble_claude_md(hub_dir)` after `add_entry` (D-18).
   - `uninstall()` calls `assemble_claude_md(hub_dir)` after `remove_entry`
     and **before** the MODS-05 leakage raise, so a leaking uninstall still
     produces a CLAUDE.md reflecting registry truth.
   - Both call sites wrap the assembler in try/except; failures log a warning
     and do not propagate (D-18: assembler must not break lifecycle ops).

4. **`bot/main.py`** —
   - Removed the Phase 1 local `assemble_claude_md(data_path)` stub.
   - `from bot.modules.assembler import assemble_claude_md` at top.
   - `__all__` explicitly re-exports the name so
     `from bot.main import assemble_claude_md` in `tests/test_skeleton.py`
     keeps working, and `patch("bot.main.assemble_claude_md", ...)` behaves
     identically.

## Verification

```
$ .venv/bin/python -m pytest tests/modules/test_assembler.py -v
tests/modules/test_assembler.py::TestAssembler::test_assembler_writes_base_only_when_empty_registry PASSED
tests/modules/test_assembler.py::TestAssembler::test_assembler_merges_installed_module_prompt PASSED
tests/modules/test_assembler.py::TestAssembler::test_assembler_preserves_install_order PASSED
============================== 3 passed in 0.18s ==============================

$ .venv/bin/python -m pytest tests/modules/ tests/test_skeleton.py -v
============================== 31 passed, 2 skipped in 1.08s =================
  (test_assembler 3 + test_lifecycle 6 + test_manifest 4 + test_registry 4
   + test_roundtrip 2 + test_skeleton 12)

$ .venv/bin/python -m ruff check bot/modules/
All checks passed!

$ .venv/bin/python -c "import bot.main; print('ok')"
ok

$ .venv/bin/python -c "from bot.modules import assemble_claude_md; print('ok')"
ok
```

All 5 verification steps from the plan pass. All 9 acceptance criteria for
Task 1 and all 9 acceptance criteria for Task 2 verified.

## Plan Verification Checklist

1. [x] `pytest tests/modules/test_assembler.py -v` → 3 PASSED, 0 FAILED
2. [x] `pytest tests/test_skeleton.py -v` → 12 PASSED (Phase 1/2 regression)
3. [x] `pytest tests/modules/test_lifecycle.py -v` → 6 PASSED (install/uninstall
       still green with embedded reassembly call)
4. [x] `python -c "import bot.main"` succeeds (no circular-import error;
       DAG: manifest → registry → assembler → lifecycle → __init__ → main)
5. [x] `ruff check bot/modules/` clean
6. [x] `grep 'def assemble_claude_md' bot/modules/assembler.py` → 1 match
7. [x] `grep 'module-prompts-start' bot/modules/assembler.py` → match
       (preserves Phase 1 markers)
8. [x] `grep 'sorted.*installed_at' bot/modules/assembler.py` → match (D-16)
9. [x] `grep '<module name=' bot/modules/assembler.py` → match (D-17)
10. [x] `grep '_escape_module_content\|&lt;/module&gt;' bot/modules/assembler.py`
        → match (T-03-04-01 injection defense)
11. [x] `grep 'os\.replace' bot/modules/assembler.py` → match (atomic write)
12. [x] `grep 'from bot\.modules\.assembler import assemble_claude_md' bot/main.py`
        → match
13. [x] `grep -c 'def assemble_claude_md' bot/main.py` → 0 (local stub removed)
14. [x] `grep 'from bot\.modules\.assembler import assemble_claude_md'
        bot/modules/lifecycle.py` → match
15. [x] `grep -c 'assemble_claude_md(hub_dir' bot/modules/lifecycle.py` → 2
        (one install, one uninstall)

## Threat Surface Status

| Threat ID | Category | Disposition | Notes |
|-----------|----------|-------------|-------|
| T-03-04-01 | Tampering (XML-tag injection across modules) | **mitigated** | `_escape_module_content` rewrites `</module>` → `&lt;/module&gt;` on ingest. Boundary inviolable from within a module's prompt. |
| T-03-04-02 | Spoofing (core-bot impersonation) | accept | Documented trust boundary; XML wrap + base-template language provide defence-in-depth but no structural prevention. |
| T-03-04-03 | Tampering (assembler crash aborts boot, D-18 violation) | **mitigated** | Registry-read, manifest-load, prompt-read all wrapped in `except Exception` with WARNING; per-section placeholder on failure. Lifecycle callers also wrap the assembler call. |
| T-03-04-04 | Tampering (partial-write corruption of CLAUDE.md) | **mitigated** | `_atomic_write` uses sibling temp + `os.replace`, matching registry write pattern. |
| T-03-04-05 | DoS (huge prompt.md) | accept → carry-forward | Phase 3 modules are trusted; Phase 5 dashboard install path should add a size cap. |
| T-03-04-06 | Info Disclosure (secrets in prompt.md) | accept → carry-forward | Documented module-author trust boundary; Plan 05 authoring guide will explicitly forbid secrets in prompts. |

No new threat surface introduced beyond the declared module-author →
CLAUDE.md → Claude boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Return type `str` instead of `Path`**

- **Found during:** Task 1 GREEN run (before first pytest invocation).
- **Issue:** Plan `<interfaces>` block specified
  `assemble_claude_md(...) -> Path`. `tests/modules/test_assembler.py`
  assigns the call result to `output` and then asserts on substrings:
  `"<!-- No modules installed -->" in output`,
  `'<module name="sample">' in output`,
  `output.find('<module name="alpha">') < output.find(...)`. These require
  the return value to be the content string, not the output path.
- **Fix:** Changed signature to `-> str`, returning the assembled content.
  Output is still written atomically to disk at `output_path` (default
  `hub_dir / "CLAUDE.md"`), so production/main.py and install/uninstall
  call-sites that ignore the return value are unaffected.
- **Files:** bot/modules/assembler.py.
- **Commit:** ad6e5d0.
- **Why not Rule 4:** Same semantic operation (rebuild + write). Caller
  surface unchanged in production.

**2. [Rule 3 - Unblock] Record `module_dir` in registry entry**

- **Found during:** Task 1 — analysing `test_assembler_merges_installed_module_prompt`.
- **Issue:** The test copies the valid-module fixture to
  `tmp_path/modules/sample` and calls `install(valid_module_dir, tmp_hub_dir)`.
  With the plan's spec (module_dir resolved via `modules_root / name`, default
  `<repo>/modules`), the assembler could not locate the module's prompt.md
  — the test expects `"sample module" in output.lower()` (the prompt content).
- **Fix:** `install()` now records `"module_dir": str(module_dir)` in the
  registry entry. `assembler._resolve_module_dir` prefers that recorded path,
  falling back to `modules_root / name` for production modules. Also added
  a lightweight inline-prompt path (`entry["prompt"]`) used by the
  install-order test which writes registry entries directly with
  `write_registry`.
- **Files:** bot/modules/lifecycle.py, bot/modules/assembler.py.
- **Commits:** ad6e5d0 (assembler), 8d8581f (lifecycle).
- **Rationale:** Registry entries already hold per-install state (config,
  installed_at); `module_dir` is of a piece with those. Schema is open (extra
  keys permitted by `add_entry`). No user-facing API change.
- **Why not Rule 4:** No new table/service/framework; extending an existing
  dict. Back-compatible with any code that ignores unknown keys.

**3. [Rule 3 - Unblock] Fix one ruff I001 in lifecycle.py**

- **Found during:** Task 2 verification (`ruff check bot/modules/`).
- **Issue:** New assembler import was placed after the manifest/registry
  imports, violating ruff I001 sort rules.
- **Fix:** Moved `from bot.modules.assembler import assemble_claude_md`
  above the `from bot.modules.manifest ...` line (alphabetical).
- **Files:** bot/modules/lifecycle.py.
- **Commit:** folded into 8d8581f.
- **Scope note:** `ruff check bot/` surfaces 10 additional pre-existing
  I001 / E501 / E741 errors in bot/bridge, bot/dashboard, bot/features,
  bot/memory. Per scope boundary, those are out of scope for Plan 04 — NOT
  fixed here. Logged to Deferred Issues below.

### Auth Gates

None — fully offline test suite.

### Deferred Issues

**Pre-existing ruff errors in unrelated files (out of scope):**

- `bot/bridge/telegram.py:516` — I001 unsorted imports (nested in async-with)
- `bot/dashboard/app.py:5, 105, 149, 215, 390` — I001 (top-level) + 3× E501
  (line length)
- `bot/features/self_dev.py:36` — E501
- `bot/memory/core.py:47, 69` — E741 (single-letter `l` var) + E501
- `bot/memory/search.py:70` — E501

These existed before Plan 04 and belong to earlier-phase files. Recommend
a dedicated lint-cleanup chore task or roll into the next plan that touches
those files.

## Commits

- `ad6e5d0` test(03-04): add failing test stubs for assembler (TDD RED) — despite
  the commit subject, this commit actually carries the **GREEN** implementation
  (`bot/modules/assembler.py` + `__init__.py` re-export). The RED was the
  pre-existing failing state from Plan 00. Subject line wording is a minor
  authoring error; content is correct.
- `8d8581f` feat(03-04): wire assembler into bot.main and install/uninstall (D-18)

## Downstream Effects

- **Plan 05 (MODS-06, bridge dogfood):** Can rely on CLAUDE.md being rebuilt
  at install time. Bridge's `setup.sh` installing through
  `python -m bot.modules install bridge` will produce a correct CLAUDE.md
  end-to-end, no extra wiring.
- **Plan 06 (integration tests):** `test_isolation.py` (currently 2 skipped)
  can now exercise module A vs module B CLAUDE.md merge via the public
  assembler API. Roundtrip tests already passing (2 additional stubs
  flipped green as a side effect of `module_dir` recording).
- **Test activation:** 3 assembler stubs pass permanently + 2 roundtrip stubs
  pass as side effect. Total active-and-green: 19 of 21 (manifest 4 +
  registry 4 + lifecycle 6 + assembler 3 + roundtrip 2 = 19).
  Remaining 2 (`test_isolation.py`) await Plan 06.

## Self-Check: PASSED

Verified on disk:
- `bot/modules/assembler.py` exists (188 lines) — FOUND.
- `bot/modules/__init__.py` updated (`assemble_claude_md` in imports and
  `__all__`) — FOUND.
- `bot/modules/lifecycle.py` updated (assembler import + install/uninstall
  call sites) — FOUND.
- `bot/main.py` updated (assembler import, local stub removed,
  `__all__` re-export) — FOUND.
- Commit `ad6e5d0` present in `git log --oneline` — FOUND.
- Commit `8d8581f` present in `git log --oneline` — FOUND.
- `grep 'def assemble_claude_md' bot/modules/assembler.py` — FOUND.
- `grep '_escape_module_content' bot/modules/assembler.py` — FOUND.
- `grep 'os\.replace' bot/modules/assembler.py` — FOUND.
- `grep 'sorted.*installed_at' bot/modules/assembler.py` — FOUND.
- `grep '<module name=' bot/modules/assembler.py` — FOUND.
- `grep -c 'def assemble_claude_md' bot/main.py` → 0 — VERIFIED (stub removed).
- `grep -c 'assemble_claude_md(hub_dir' bot/modules/lifecycle.py` → 2 —
  VERIFIED.
- 3 assembler tests PASSED; 6 lifecycle tests PASSED; 12 test_skeleton tests
  PASSED; 4 manifest + 4 registry tests PASSED; 2 roundtrip tests PASSED
  (bonus). `ruff check bot/modules/` clean. Import smoke tests succeed.
