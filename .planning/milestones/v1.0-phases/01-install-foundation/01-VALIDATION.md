---
phase: 1
slug: install-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INST-01 | — | N/A | integration | `bash setup.sh && systemctl --user status animaya` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-02 | — | N/A | integration | `python -m pytest tests/test_setup.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-03 | — | N/A | integration | `journalctl --user -u animaya --no-pager -n 5` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-04 | — | CLAUDECODE=1 unset before Python | unit | `grep -q 'unset CLAUDECODE' run.sh` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_setup.py` — stubs for INST-01, INST-02, INST-03
- [ ] `tests/conftest.py` — shared fixtures (if needed)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Service survives reboot | INST-03 | Requires actual reboot | `sudo reboot`, verify `systemctl --user status animaya` shows active |
| loginctl enable-linger persists | INST-03 | Requires system-level state | `loginctl show-user $USER --property=Linger` returns `Linger=yes` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
