---
phase: 4
slug: first-party-modules
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-14
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

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

*To be filled by gsd-planner per Validation Architecture in 04-RESEARCH.md (13 tests mapped across IDEN-*, MEMO-*, GITV-* requirements).*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/modules/test_identity.py` — stubs for IDEN-01..04
- [ ] `tests/modules/test_memory.py` — stubs for MEMO-01..04
- [ ] `tests/modules/test_git_versioning.py` — stubs for GITV-01..03
- [ ] `tests/modules/conftest.py` — shared fixtures (tmp hub root, fake Claude query, git repo init)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Onboarding end-to-end via real Telegram | IDEN-01 | Requires live bot + user | Install identity module, send /start, verify identity saved & appears next message |
| Dashboard identity reconfigure flow | IDEN-04 | Requires browser + live session | Edit identity in dashboard, send next Telegram message, confirm new identity in reply |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
