---
phase: 05
slug: web-dashboard
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-15
---

# Phase 05 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio 0.23+ |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `python -m pytest tests/dashboard/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/dashboard/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

*Populated by planner after PLAN.md files are created. Each task must map to a requirement and automated test command or Wave 0 dependency.*

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/dashboard/__init__.py` — package init
- [ ] `tests/dashboard/conftest.py` — FastAPI TestClient fixture + temp data dir fixture
- [ ] `tests/dashboard/test_auth.py` — Telegram Login HMAC verification, session cookie
- [ ] `tests/dashboard/test_modules.py` — install/uninstall job runner (async)
- [ ] `tests/dashboard/test_config_form.py` — form coercion + jsonschema validation
- [ ] `tests/dashboard/test_status.py` — status endpoint + events log
- [ ] Add `python-multipart` + `jsonschema` to `pyproject.toml` dev or runtime deps

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram Login Widget UX flow | Auth | Requires real Telegram account + `/setdomain` set on @BotFather | Open dashboard URL, click login, verify redirect + session |
| Caddy reverse proxy headers | Deployment | Requires live Caddy + Voidnet infra | Deploy to mcow, verify `{slug}.animaya.makscee.ru` serves dashboard |
| HTMX live polling UX | UX | Requires browser DOM rendering | Trigger install, verify status updates without full page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
