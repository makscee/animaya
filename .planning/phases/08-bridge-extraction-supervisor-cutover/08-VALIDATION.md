---
phase: 8
slug: bridge-extraction-supervisor-cutover
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| T3a-P01 | 01 | 1 | BRDG-03 | T-08-04 (zombie polling) | on_stop order assertions; uninstall wiring | unit (xfail P02) | pytest tests/modules/test_supervisor_cutover.py -x | ✅ | ⬜ |
| T3b-P01 | 01 | 1 | BRDG-04 | T-08-01 (token in logs) | Token not in REQUIRED_ENV_VARS; config.json canonical | unit (xfail P03) | pytest tests/modules/test_bridge_config_source.py -x | ✅ | ⬜ |

*Populated by planner. Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bridge_module.py` — stubs for BRDG-01 (lifecycle: on_start/on_stop contract, registry entry, zero import from core)
- [ ] `tests/test_supervisor_cutover.py` — stubs for BRDG-03 (supervisor installs/uninstalls bridge, shutdown order assertions)
- [ ] `tests/test_bridge_config_source.py` — stubs for BRDG-04 (config.json canonical, TELEGRAM_BOT_TOKEN optional bootstrap)
- [ ] `tests/conftest.py` — shared fixtures: temp `/data`, stub `app_ctx`, PTB Application mock, log capture
- [ ] Telethon harness reuse from `~/hub/telethon` — install → round-trip → uninstall smoke test

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live Telegram round-trip on animaya-dev LXC | BRDG-01 | Requires live Telegram API + LXC access | `ssh root@tower 'pct exec 205 -- sudo -u animaya systemctl restart animaya'` then send test message via test bot token |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 120s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
