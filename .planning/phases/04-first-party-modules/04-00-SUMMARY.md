---
phase: 04-first-party-modules
plan: 0
subsystem: test-infrastructure
tags: [testing, fixtures, xfail, validation, identity, memory, git-versioning]
dependency_graph:
  requires: []
  provides:
    - tests/modules/conftest.py (Phase 4 fixtures)
    - tests/modules/test_identity.py
    - tests/modules/test_memory.py
    - tests/modules/test_git_versioning.py
    - tests/modules/test_claude_query_injection.py
  affects:
    - .planning/phases/04-first-party-modules/04-VALIDATION.md
tech_stack:
  added: []
  patterns:
    - xfail(strict=False) Wave 0 stubs for TDD red phase
    - pytest fixture composition (tmp_hub_knowledge -> tmp_hub_with_identity)
    - AsyncIterator factory fixture for SDK mock
key_files:
  created:
    - tests/modules/test_identity.py
    - tests/modules/test_memory.py
    - tests/modules/test_git_versioning.py
    - tests/modules/test_claude_query_injection.py
    - .planning/phases/04-first-party-modules/04-00-SUMMARY.md
  modified:
    - tests/modules/conftest.py
    - .planning/phases/04-first-party-modules/04-VALIDATION.md
decisions:
  - A1=claude-haiku-4-5 (memory consolidation model; overridable per-install)
  - A2=~/hub (git repo root for git-versioning; path-scoped to knowledge/)
  - A7=depends:["identity"] (memory requires identity installed first)
  - D-05=sentinel file at ${IDENTITY_DIR}/.pending-onboarding
metrics:
  duration: ~10 minutes
  completed: 2026-04-15
  tasks_completed: 3
  tasks_total: 3
  files_created: 5
  files_modified: 2
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 4 Plan 0: Test Infrastructure — Summary

Phase 4 Wave 0 test scaffold: 4 xfail stub files covering all 13 IDEN/MEMO/GITV requirements, shared conftest fixtures, and locked research assumptions.

## What Was Built

### Locked Assumptions

| Key | Value | Notes |
|-----|-------|-------|
| A1 | `claude-haiku-4-5` | Memory consolidation model; overridable via `config_schema.consolidation_model.default` |
| A2 | `~/hub` | Git repo root; git-versioning uses `git -C ~/hub -- knowledge/` |
| A7 | `depends: ["identity"]` | Memory manifest requires identity first; blocks identity uninstall while memory present |
| D-05 | sentinel file `.pending-onboarding` | Created by install.sh, cleared by onboarding state-machine, removed by uninstall.sh |

### Fixture API (tests/modules/conftest.py additions)

| Fixture | Returns | Purpose |
|---------|---------|---------|
| `PLACEHOLDER_MARKER` | `str` | `<!-- animaya:placeholder -->` constant |
| `tmp_hub_knowledge` | `Path` | `tmp_path/hub/knowledge/` root |
| `tmp_hub_with_identity` | `Path` | `tmp_hub_knowledge` + `identity/{USER.md,SOUL.md,.pending-onboarding}` |
| `tmp_hub_with_memory` | `Path` | `tmp_hub_knowledge` + `memory/{CORE.md,README.md}` |
| `tmp_hub_git_repo` | `Path` | Fresh git repo at `tmp_path/hub/` with `Animaya Bot` identity configured |
| `fake_claude_query` | `Callable[[str], AsyncIterator]` | Factory yielding a single `AssistantMessage` with given text |

All fixtures derive from `tmp_path` only — never touch `Path.home()`.

### Test Stub Inventory (14 stubs across 4 files)

| File | Class | Test | Req ID |
|------|-------|------|--------|
| test_identity.py | TestIdentityInstall | test_install_creates_user_soul_sentinel | IDEN-02 |
| test_identity.py | TestIdentityOnboarding | test_sentinel_present_after_install_cleared_after_qa | IDEN-01 |
| test_identity.py | TestIdentityReconfigure | test_identity_command_reruns_onboarding | IDEN-04 |
| test_memory.py | TestMemoryInstall | test_install_creates_memory_dir_with_core_md | MEMO-01 |
| test_memory.py | TestMemoryPersist | test_write_to_memory_facts_persists | MEMO-01 |
| test_memory.py | TestMemoryGitCommit | test_memory_write_followed_by_commit_tick | MEMO-02 |
| test_memory.py | TestConsolidation | test_consolidate_runs_with_haiku_model | MEMO-03 |
| test_git_versioning.py | TestCommitLoop | test_commit_loop_creates_commit_after_changes | GITV-01 |
| test_git_versioning.py | TestCommitSkipEmpty | test_no_diff_tick_does_not_commit | GITV-01 |
| test_git_versioning.py | TestCommitLock | test_concurrent_commits_serialize | GITV-02 |
| test_git_versioning.py | TestCommitScoping | test_path_scoped_add_excludes_out_of_scope | GITV-03 |
| test_claude_query_injection.py | TestIdentityInjection | test_build_options_contains_identity_user_xml | IDEN-03 |
| test_claude_query_injection.py | TestIdentityInjection | test_build_options_contains_identity_soul_xml | IDEN-03 |
| test_claude_query_injection.py | TestMemoryCoreInjection | test_build_options_contains_memory_core_xml | MEMO-04 |

### Validation State

- `nyquist_compliant: true` — confirmed in 04-VALIDATION.md frontmatter
- `wave_0_complete: true` — flipped in Task 3
- 13 per-task rows in Per-Task Verification Map, all `⬜ pending`
- All 6 Wave 0 Requirements checkboxes ticked `[x]`

### Final pytest Result

```
27 passed, 14 xfailed in 1.65s
```

Phase 3 tests remain fully green; 14 new xfail stubs correctly registered.

## Deviations from Plan

None — plan executed exactly as written.

Note: VALIDATION.md already had `nyquist_compliant: true` (set by planner) and all 13 rows pre-populated; Task 3 only needed to flip `wave_0_complete` and tick the Wave 0 Requirements checkboxes.

## Known Stubs

All 14 test methods are intentional Wave 0 stubs. Bodies will be implemented in plans 04-01 (identity), 04-02 (git-versioning), and 04-03 (memory).

## Threat Flags

None — only test infrastructure files modified; no new network endpoints, auth paths, or schema changes introduced.

## Self-Check: PASSED

- tests/modules/conftest.py — FOUND
- tests/modules/test_identity.py — FOUND
- tests/modules/test_memory.py — FOUND
- tests/modules/test_git_versioning.py — FOUND
- tests/modules/test_claude_query_injection.py — FOUND
- Commits: f6ebfc7 (conftest), d47b743 (stubs), 2c89c9c (validation)
