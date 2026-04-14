---
phase: 4
slug: first-party-modules
status: planner-locked
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-14
updated: 2026-04-15
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> `wave_0_complete` flips to `true` after plan 04-00 task 3 executes.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x (pytest-asyncio auto mode) |
| **Config file** | pyproject.toml (`[tool.pytest.ini_options]`) |
| **Quick run command** | `python -m pytest tests/modules/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/modules/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

13 tests mapped across IDEN/MEMO/GITV requirements (RESEARCH.md §Validation Architecture).

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1.1 | 04-01 | 1 | IDEN-02 | T-04-01-02 | install.sh creates only USER.md/SOUL.md/sentinel under owned identity/ path | unit | `python -m pytest tests/modules/test_identity.py::TestIdentityInstall -x -q` | ✅ Wave 0 | ⬜ pending |
| T1.2 | 04-01 | 1 | IDEN-01 | T-04-01-01 | sentinel cleared only after Q&A completes; survives bot restart | integration | `python -m pytest tests/modules/test_identity.py::TestIdentityOnboarding -x -q` | ✅ Wave 0 | ⬜ pending |
| T1.3 | 04-01 | 1 | IDEN-03 | T-04-01-03 | build_options injects USER.md/SOUL.md inside `<identity-*>` blocks; escapes closing tags | unit | `python -m pytest tests/modules/test_claude_query_injection.py::TestIdentityInjection -x -q` | ✅ Wave 0 | ⬜ pending |
| T1.4 | 04-01 | 1 | IDEN-04 | T-04-01-01 | `/identity` reuses same onboarding state-machine; overwrites files atomically | integration | `python -m pytest tests/modules/test_identity.py::TestIdentityReconfigure -x -q` | ✅ Wave 0 | ⬜ pending |
| T2.1 | 04-02 | 1 | GITV-01 | T-04-02-01 | commit_loop commits when knowledge/ has diff | integration | `python -m pytest tests/modules/test_git_versioning.py::TestCommitLoop -x -q` | ✅ Wave 0 | ⬜ pending |
| T2.2 | 04-02 | 1 | GITV-01 | T-04-02-02 | no-diff tick is no-op (no empty commit) | unit | `python -m pytest tests/modules/test_git_versioning.py::TestCommitSkipEmpty -x -q` | ✅ Wave 0 | ⬜ pending |
| T2.3 | 04-02 | 1 | GITV-02 | T-04-02-01 | concurrent commits serialize via asyncio.Lock | unit | `python -m pytest tests/modules/test_git_versioning.py::TestCommitLock -x -q` | ✅ Wave 0 | ⬜ pending |
| T2.4 | 04-02 | 1 | GITV-03 | T-04-02-04 | path-scoped `git add -- knowledge/` excludes out-of-scope files | integration | `python -m pytest tests/modules/test_git_versioning.py::TestCommitScoping -x -q` | ✅ Wave 0 | ⬜ pending |
| T3.1 | 04-03 | 2 | MEMO-01 | T-04-03-01 | install.sh creates memory/CORE.md + README.md under owned memory/ path | unit | `python -m pytest tests/modules/test_memory.py::TestMemoryInstall -x -q` | ✅ Wave 0 | ⬜ pending |
| T3.2 | 04-03 | 2 | MEMO-01 | T-04-03-02 | Claude Write to knowledge/memory/ persists; path traversal blocked | integration | `python -m pytest tests/modules/test_memory.py::TestMemoryPersist -x -q` | ✅ Wave 0 | ⬜ pending |
| T3.3 | 04-03 | 2 | MEMO-02 | T-04-02-01 | memory write followed by commit tick produces commit (cross-plan with git-versioning) | integration | `python -m pytest tests/modules/test_memory.py::TestMemoryGitCommit -x -q` | ✅ Wave 0 | ⬜ pending |
| T3.4 | 04-03 | 2 | MEMO-03 | T-04-03-05 | consolidation query uses claude-haiku-4-5 + continue_conversation=False | unit | `python -m pytest tests/modules/test_memory.py::TestConsolidation -x -q` | ✅ Wave 0 | ⬜ pending |
| T3.5 | 04-03 | 2 | MEMO-04 | T-04-01-03 | build_options injects CORE.md inside `<memory-core>` block | unit | `python -m pytest tests/modules/test_claude_query_injection.py::TestMemoryCoreInjection -x -q` | ✅ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/modules/test_identity.py` — stubs for IDEN-01..04
- [ ] `tests/modules/test_memory.py` — stubs for MEMO-01..04
- [ ] `tests/modules/test_git_versioning.py` — stubs for GITV-01..03
- [ ] `tests/modules/test_claude_query_injection.py` — stubs for IDEN-03 + MEMO-04
- [ ] `tests/modules/conftest.py` — shared fixtures (`tmp_hub_with_identity`, `tmp_hub_with_memory`, `tmp_hub_git_repo`, `fake_claude_query`)
- [ ] User confirms locked assumptions A1 (`claude-haiku-4-5`), A2 (`~/hub/`), A7 (`memory depends:[identity]`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Onboarding end-to-end via real Telegram | IDEN-01 | Requires live bot + user | Install identity, send any message, complete 3-Q Q&A, verify identity persisted + injected on next message |
| Dashboard identity reconfigure flow | IDEN-04 | Phase 5 dashboard scope | Send `/identity` from Telegram (Phase 4 path); dashboard variant deferred |
| Real Haiku consolidation against deployed bot | MEMO-03 | Requires Anthropic API + real conversation | Send 10 messages to deployed bot; observe `scheduled memory consolidation` log; `cat ~/hub/knowledge/memory/CORE.md` shows extracted facts |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planner-locked 2026-04-15
