---
phase: 9
slug: install-dialog-owner-claim-fsm
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | BRDG-02 | — | Token validated via getMe before persist | integration | `python -m pytest tests/ -k test_install` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLAIM-01 | — | 6-digit pairing code generated with TTL | unit | `python -m pytest tests/ -k test_pairing` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLAIM-02 | — | Pairing binds owner_id to state.json | integration | `python -m pytest tests/ -k test_claim` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLAIM-03 | — | Rate limit 5 attempts, hmac.compare_digest | unit | `python -m pytest tests/ -k test_rate_limit` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | CLAIM-04 | — | Revoke returns to pending-claim | integration | `python -m pytest tests/ -k test_revoke` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | SEC-01 | — | Token never in GET response or logs | integration | `python -m pytest tests/ -k test_redaction` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_install_dialog.py` — stubs for BRDG-02 token install flow
- [ ] `tests/test_pairing.py` — stubs for CLAIM-01..04 pairing FSM
- [ ] `tests/test_token_redaction.py` — stubs for SEC-01 redaction checks

*Existing pytest infrastructure covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dashboard UI shows pairing code with countdown | CLAIM-01 | Visual UI verification | Open dashboard, install bridge, verify 6-digit code displays with TTL timer |
| Telegram bot responds after pairing complete | CLAIM-02 | End-to-end across services | Send pairing code from Telegram, verify bot acknowledges ownership |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
