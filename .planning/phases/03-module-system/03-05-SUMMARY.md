---
phase: 03-module-system
plan: 05
subsystem: module-system
tags: [bridge, dogfood, first-party-module, authoring-guide, mods-05, mods-06]
requirements: [MODS-05]
requires:
  - bot.modules.install / uninstall (Plan 03)
  - bot.modules.assemble_claude_md (Plan 04)
  - bot.modules.registry (Plan 02)
  - bot.modules.manifest.validate_manifest (Plan 01)
provides:
  - modules/bridge/ first-party module (manifest + install.sh + uninstall.sh + prompt.md)
  - docs/MODULE_AUTHORING.md conventions guide (D-20 MODS-06 enforcement)
  - Dogfood e2e test class (TestBridgeDogfood) verifying MODS-05 on real module
affects:
  - modules/ (new top-level dir; previously absent)
  - docs/ (new top-level dir; previously absent)
  - tests/modules/test_roundtrip.py (extended from 2 generic tests to 5 total)
tech_stack:
  added: []
  patterns:
    - First-party module with owned_paths=[] (code lives in bot/bridge/, not hub)
    - Dogfood test uses real modules/bridge/ dir (not a fixture copy) — exercises
      production install path end-to-end
    - Author guide as convention enforcement vehicle for MODS-06 (no runtime lint)
key_files:
  created:
    - modules/bridge/manifest.json (12 lines)
    - modules/bridge/install.sh (19 lines, chmod 0755)
    - modules/bridge/uninstall.sh (14 lines, chmod 0755)
    - modules/bridge/prompt.md (13 lines)
    - docs/MODULE_AUTHORING.md (238 lines)
  modified:
    - tests/modules/test_roundtrip.py (extended: +73 / -3 lines)
decisions:
  - Roundtrip test preserves the 2 prior generic tests (against valid-module
    fixture) AND adds 3 new TestBridgeDogfood tests against real modules/bridge.
    Net: 5 tests, not the 4 the plan's <action> sketch called for. Justification:
    the prior tests already pass and exercise the same lifecycle with a fixture
    that HAS owned_paths (.sample-marker) — complementary coverage, not
    redundant. Removing them would shrink test surface for no benefit.
  - Plan's <action> sketch used keyword-API signatures
    (install("bridge", modules_root=..., hub_dir=..., config={})) but Plan 03's
    deviation-adjusted signatures are positional
    (install(module_dir, hub_dir, *, config=None)). Test adapted to match actual
    API. See Deviations Rule 1.
  - Bridge prompt.md uses "to" in "Markdown to HTML" instead of an arrow symbol
    to keep the assembled CLAUDE.md ASCII-clean.
  - Authoring guide explicitly notes empty-owned_paths is legitimate (bridge
    pattern for repo-managed code) to prevent reviewers from flagging it as a
    bug in future modules that follow the same shape.
carry_forward_threats:
  - T-03-05-03 (spoofing first-party module name) → defer to Phase 4+; add
    provenance flag if/when third-party install surface matters.
metrics:
  duration_min: 4
  tasks_completed: 3
  files_created: 5
  files_modified: 1
  completed_date: 2026-04-14
---

# Phase 3 Plan 05: Bridge Dogfood + Module Authoring Guide Summary

Ships the first-party `modules/bridge/` module and dogfoods the Phase 3
module system end-to-end on it. Per D-02 the bridge BECOMES a module: no
code is moved — `bot/bridge/` stays put — `modules/bridge/` is the
manifest + scripts + prompt that plug the existing runtime into the
install/uninstall/assemble lifecycle. Also writes `docs/MODULE_AUTHORING.md`
as the convention-enforcement vehicle for MODS-06 (D-20: no structural
lint check; the guide is the rulebook).

## What Was Built

1. **`modules/bridge/manifest.json`** — strict-schema v1 manifest:
   `name=bridge, version=1.0.0, system_prompt_path=prompt.md,
   owned_paths=[], depends=[], config_schema=null`. Validates via
   `bot.modules.manifest.validate_manifest`.

2. **`modules/bridge/install.sh`** (chmod 0755) — `#!/usr/bin/env bash`
   + `set -euo pipefail`. Logs D-11 env-injection variables
   (ANIMAYA_MODULE_DIR, ANIMAYA_HUB_DIR, ANIMAYA_CONFIG_JSON) and exits 0.
   No hub artifacts to create (bridge code lives in `bot/bridge/`).

3. **`modules/bridge/uninstall.sh`** (chmod 0755) — idempotent no-op
   matching install.sh's shape. Safe to run on partial/full/absent state
   per the Plan 05 contract.

4. **`modules/bridge/prompt.md`** (13 lines) — Telegram-bridge-specific
   system-prompt snippet that lands verbatim inside
   `<module name="bridge">...</module>` in the assembled CLAUDE.md.
   Covers: progressive streaming behavior, 4096-char chunking, the
   Markdown-to-HTML subset the formatter translates, typing-indicator
   semantics, error surface.

5. **`tests/modules/test_roundtrip.py`** — extended from 2 generic
   tests to 5 total:
   - `TestRoundtrip::test_install_uninstall_leaves_no_artifacts` (prior)
   - `TestRoundtrip::test_registry_is_empty_after_roundtrip` (prior)
   - `TestBridgeDogfood::test_bridge_install_writes_claude_md_with_module_section`
     — installs real `modules/bridge/`, asserts CLAUDE.md has
     `<module name="bridge">`, `Telegram Bridge`, and `</module>`;
     uninstalls; asserts CLAUDE.md reverts to
     `<!-- No modules installed -->`.
   - `TestBridgeDogfood::test_bridge_owned_paths_empty_means_no_hub_leakage`
     — MODS-05 audit: after roundtrip, `tmp_hub_dir` contains only
     `{CLAUDE.md, registry.json}` (lifecycle-owned files), no bridge
     artifacts.
   - `TestBridgeDogfood::test_bridge_reinstall_rejected` — D-14 check:
     second `install(BRIDGE_DIR, tmp_hub_dir)` raises
     `ValueError("... already installed ...")`.

6. **`docs/MODULE_AUTHORING.md`** (238 lines) — convention guide for
   third-party and first-party module authors. Sections:
   - Module layout (required 4 files)
   - manifest.json schema with strict validation, regex rules, evolution
     via manifest_version bump
   - Lifecycle contract: env injection (D-11), exit codes, cwd, rollback
     on failure (D-13), reinstall rejection (D-14)
   - Idempotency requirement with good/bad uninstall.sh patterns
   - owned_paths rules (MODS-05): relative-only, no absolute, no ..,
     leakage audit, empty-[] pattern (bridge)
   - Dependencies (D-15) — no cascade, blocks uninstall if dependents
   - prompt.md XML-wrap behavior (D-17), `</module>` escape
     (T-03-04-01), assembler reassembly timing (D-18)
   - MODS-06 isolation: convention-enforced by `test_isolation.py` AST
     scan; no runtime lint
   - Anti-patterns: runtime pip, secrets in prompt.md, `..` segments,
     silent failure, mutable out-of-hub side-effects, extra manifest
     fields
   - Testing recipe + cites `modules/bridge/` as reference

## Verification

```
$ .venv/bin/python -c "from bot.modules.manifest import validate_manifest; \
    from pathlib import Path; m = validate_manifest(Path('modules/bridge')); \
    print(m.name, m.version)"
bridge 1.0.0

$ ANIMAYA_MODULE_DIR=/tmp ANIMAYA_HUB_DIR=/tmp ANIMAYA_CONFIG_JSON='{}' \
    bash modules/bridge/install.sh
... rc=0
$ ANIMAYA_MODULE_DIR=/tmp ANIMAYA_HUB_DIR=/tmp ANIMAYA_CONFIG_JSON='{}' \
    bash modules/bridge/uninstall.sh
... rc=0

$ .venv/bin/python -m pytest tests/modules/test_roundtrip.py -v
tests/modules/test_roundtrip.py::TestRoundtrip::test_install_uninstall_leaves_no_artifacts PASSED
tests/modules/test_roundtrip.py::TestRoundtrip::test_registry_is_empty_after_roundtrip PASSED
tests/modules/test_roundtrip.py::TestBridgeDogfood::test_bridge_install_writes_claude_md_with_module_section PASSED
tests/modules/test_roundtrip.py::TestBridgeDogfood::test_bridge_owned_paths_empty_means_no_hub_leakage PASSED
tests/modules/test_roundtrip.py::TestBridgeDogfood::test_bridge_reinstall_rejected PASSED
============================== 5 passed in 0.58s ===============================

$ .venv/bin/python -m pytest tests/modules/ tests/test_skeleton.py -v
============================= 35 passed, 1 skipped in 1.20s =====================
  (manifest 4 + registry 4 + lifecycle 6 + assembler 3 + roundtrip 5 +
   test_skeleton 12 + isolation 1 skipped)

$ wc -l docs/MODULE_AUTHORING.md
238 docs/MODULE_AUTHORING.md

$ .venv/bin/python -m ruff check tests/modules/test_roundtrip.py modules/ docs/
All checks passed!
```

All 3 task acceptance criteria and the plan's 5 verification steps pass.

## Plan Verification Checklist

1. [x] `pytest tests/modules/test_roundtrip.py -v` → 5 PASSED
   (plan expected 4; we preserved 2 prior generic tests per decision above)
2. [x] `pytest tests/modules/ -v` (minus isolation) → 22 PASSED
   (manifest 4 + registry 4 + lifecycle 6 + assembler 3 + roundtrip 5 = 22).
   Plan's expected 21 was based on 4 roundtrip tests; our 5 makes it 22.
3. [x] Bridge manifest validates via `validate_manifest(Path('modules/bridge'))`
4. [x] `docs/MODULE_AUTHORING.md` ≥ 80 lines (238) covering all required topics
5. [x] `ruff check tests/modules/test_roundtrip.py modules/ docs/` → clean
6. [x] Acceptance: all 4 bridge-module files exist, scripts are executable,
       shebang + `set -euo pipefail` present, env-contract vars referenced,
       bridge-specific content in prompt.md, manual install/uninstall smoke
       test both exit 0

## Threat Surface Status

| Threat ID | Category | Disposition | Notes |
|-----------|----------|-------------|-------|
| T-03-05-01 | Tampering (bridge prompt.md contains `</module>` accidentally) | mitigated | Plan 04 assembler `_escape_module_content` escapes it on ingest. Authored bridge prompt contains no such string; grep-verified. |
| T-03-05-02 | Info Disclosure (env var names leaked in authoring guide) | accept | ANIMAYA_* env vars are the module-system's public API, not secrets. Documenting them is the guide's purpose. |
| T-03-05-03 | Spoofing (third-party module named `bridge` shadows first-party) | carry-forward | D-01 co-locates first-party + third-party under `modules/`. Name collision is user-visible: `install "already installed"` on second attempt. Phase 4+ may add a provenance flag. |
| T-03-05-04 | Repudiation (bridge module not auditable) | mitigated | Module files are git-tracked; registry `installed_at` records install time; hub itself is git-versioned per Phase 1. |

No new threat surface introduced beyond the already-declared
module-author → bot boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test adapted to actual install/uninstall signatures**

- **Found during:** Task 2 (reading existing test file + Plan 03 summary).
- **Issue:** Plan 05's `<action>` sketch called
  `install("bridge", modules_root=MODULES_ROOT, hub_dir=tmp_hub_dir, config={})`
  but Plan 03's deviation-adjusted API is
  `install(module_dir, hub_dir, *, config=None)` (positional Path, not
  keyword name). `uninstall` likewise is `uninstall(name, hub_dir,
  module_dir)` not `uninstall("bridge", modules_root=..., hub_dir=...)`.
- **Fix:** Test calls `install(BRIDGE_DIR, tmp_hub_dir)` and
  `uninstall("bridge", tmp_hub_dir, BRIDGE_DIR)` where
  `BRIDGE_DIR = REPO_ROOT / "modules" / "bridge"`. All semantic
  requirements preserved (D-14 reject, D-17 XML wrap, D-18 reassembly,
  MODS-05 leakage check). Test still dogfoods the real `modules/bridge/`
  directory — no fixture copy.
- **Files:** `tests/modules/test_roundtrip.py`.
- **Commit:** `b5e9e0a`.
- **Why not Rule 4:** No architectural change; only the call-shape at
  the test site.

**2. [Rule 2 - Add missing] Preserve prior TestRoundtrip tests**

- **Found during:** Task 2 (reading existing test file).
- **Issue:** Plan's `<action>` replaces the full file, which would
  delete the 2 prior tests that exercise the lifecycle against the
  `valid_module_dir` fixture (which HAS owned_paths — `.sample-marker`).
  Those tests provide complementary coverage: they prove the leakage
  check DOES remove declared artifacts, while the bridge tests prove
  empty owned_paths leaves the hub clean.
- **Fix:** Kept both `TestRoundtrip` tests verbatim and added three new
  `TestBridgeDogfood` tests alongside them. Net: 5 tests, not 4.
- **Rationale:** Strictly additive; no test deleted. Plan's "21 total"
  count in verification §2 becomes 22, documented in checklist above.
- **Why not Rule 4:** Additive only; doesn't change architecture.

### Auth Gates

None — fully offline test suite, no external services touched.

### Deferred Issues

**Pre-existing ruff I001 errors in unrelated test files (out of scope):**

- `tests/modules/test_assembler.py:2` — I001 unsorted imports
- `tests/modules/test_isolation.py:6` — I001 unsorted imports
- 3 additional I001 warnings across existing Phase 3 test files

These existed before Plan 05 and are in files I did not modify. Per
Plan 04's summary, a lint-cleanup chore task is recommended. NOT fixed
here. My changed files (`tests/modules/test_roundtrip.py`,
`modules/bridge/*`, `docs/MODULE_AUTHORING.md`) pass ruff cleanly.

## Commits

- `96b23d5` feat(03-05): add first-party modules/bridge module (D-02 dogfood)
- `b5e9e0a` test(03-05): dogfood full lifecycle against real modules/bridge module
- `e18389f` docs(03-05): add module authoring guide (D-20, MODS-06 enforcement)

## Downstream Effects

- **Plan 06 (integration):** `test_isolation.py` (currently skipped) can
  reference `modules/bridge/` as a known-valid module when scanning for
  cross-module imports. The roundtrip suite now covers MODS-05 end-to-end
  on a real module — Plan 06 can focus on MODS-06 AST checks.
- **Phase 4+ setup.sh:** First-party auto-install per D-03 can now shell
  out to `python -m bot.modules install bridge`. The dogfood test proves
  the path works; setup.sh is just a thin wrapper.
- **Phase 5 dashboard:** The authoring guide's `config_schema` field
  documentation primes the Phase 5 form-renderer work.
- **Test activation:** 3 new roundtrip tests pass permanently (total
  active-and-green in `tests/modules/`: 22 of 23, with only
  `test_isolation.py` still skipped awaiting Plan 06).

## Self-Check: PASSED

Verified on disk:
- `modules/bridge/manifest.json` — FOUND.
- `modules/bridge/install.sh` — FOUND (executable, `#!/usr/bin/env bash`
  + `set -euo pipefail`).
- `modules/bridge/uninstall.sh` — FOUND (executable, idempotent shape).
- `modules/bridge/prompt.md` — FOUND ("Telegram Bridge" header + 6
  behavior bullets).
- `tests/modules/test_roundtrip.py` — updated (5 tests, 2 classes); 5
  PASSED in isolation, 22 PASSED across `tests/modules/` minus isolation.
- `docs/MODULE_AUTHORING.md` — FOUND (238 lines; all 10 required
  grep-check strings present).
- Commit `96b23d5` present in `git log --oneline` — FOUND.
- Commit `b5e9e0a` present in `git log --oneline` — FOUND.
- Commit `e18389f` present in `git log --oneline` — FOUND.
- `ruff check` on plan-05-touched files clean.
- Manual `bash install.sh` + `bash uninstall.sh` smoke tests both exit 0.
