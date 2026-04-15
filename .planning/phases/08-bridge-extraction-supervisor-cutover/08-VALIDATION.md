---
phase: 8
slug: bridge-extraction-supervisor-cutover
status: audited
nyquist_compliant: true
wave_0_complete: true
last_audit: 2026-04-16
created: 2026-04-15
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ (asyncio_mode = "auto") |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `python -m pytest tests/ -v -k "not telethon"` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30s quick / ~120s full (incl. Telethon smoke) |

---

## Sampling Rate

- **After every task commit:** Run quick command
- **After every plan wave:** Run full command
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds (quick), 120 seconds (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| T1-P01 | 01 | 1 | BRDG-01 | T-08-02 (runtime_entry injection) | Validated dotted bot.* path; rejects os.system | unit | pytest tests/modules/test_bridge_module.py -x | ✅ | ✅ |
| T2-P01 | 01 | 1 | BRDG-01 | T-08-03 (errored module blocks boot) | Exception isolation per module | unit | pytest tests/modules/test_supervisor.py -x | ✅ | ✅ |
| T3a-P01 | 01 | 1 | BRDG-03 | T-08-04 (zombie polling) | on_stop order assertions; uninstall wiring | unit | pytest tests/modules/test_supervisor_cutover.py -x | ✅ | ✅ |
| T3b-P01 | 01 | 1 | BRDG-04 | T-08-01 (token in logs) | Token not in REQUIRED_ENV_VARS; config.json canonical | unit | pytest tests/modules/test_bridge_config_source.py -x | ✅ | ✅ |

*Populated by planner. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_bridge_module.py` — 12 tests for BRDG-01 (lifecycle, registry, isolation) ✅
- [x] `tests/test_supervisor_cutover.py` — 13 tests for BRDG-03 (install/uninstall/stop order) ✅
- [x] `tests/test_bridge_config_source.py` — 5 tests for BRDG-04 (config.json canonical, token seed) ✅
- [x] `tests/conftest.py` — shared fixtures ✅
- [x] Telethon harness — moved to Manual-Only (requires live LXC + Telegram API)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Telegram round-trip on animaya-dev LXC | BRDG-01 | Requires live Telegram API + LXC access | `ssh root@tower 'pct exec 205 -- sudo -u animaya systemctl restart animaya'` then send test message via test bot token |
| SC#3 Telethon e2e bridge lifecycle | BRDG-01 | Requires live LXC 205, real Telegram bot token, network access | Install bridge → send msg → confirm reply → uninstall → confirm silence → reinstall → confirm reply. Use `~/hub/telethon` harness |
| Dashboard module install/uninstall via UI | BRDG-01 | Requires live deployed instance with Caddy | Open dashboard → modules page → install/uninstall telegram-bridge → verify /api/modules response |
| Boot order log verification | BRDG-01 | Requires live LXC + journalctl | Deploy, restart, verify log sequence: assemble_claude_md → migrate → uvicorn → supervisor start |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references (SC#3 moved to Manual-Only)
- [x] No watch-mode flags
- [x] Feedback latency < 120s (1.64s full suite)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ validated

---

## Validation Audit 2026-04-16

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 0 |
| Escalated to manual-only | 1 |

**Details:**
- SC#3 Telethon e2e (`tests/telethon/test_bridge_lifecycle_e2e.py`) — moved to Manual-Only. Requires live LXC 205 + Telegram API; cannot run in CI.
- T3a-P01, T3b-P01 status updated ⬜→✅ (xfail markers removed in Plan 02/03, all tests green).
- Full suite: 90 passed, 0 failed, 1.64s runtime.
