---
phase: 09-install-dialog-owner-claim-fsm
plan: "01"
subsystem: dashboard
tags: [bridge, install-dialog, token-validation, htmx, security, fsm]
dependency_graph:
  requires: []
  provides:
    - bot.modules.telegram_bridge_state (read_state, write_state, validate_bot_token, redact_bridge_config, get_owner_id)
    - bot.dashboard.bridge_routes (POST /api/modules/telegram-bridge/install, GET /api/modules/telegram-bridge/claim-status stub)
    - token redaction in all module API responses (T-09-01)
    - supervisor on app.state (D-9.0a)
  affects:
    - bot.dashboard.module_routes (redaction wired)
    - bot.dashboard.app (bridge_routes registered)
    - bot.main (supervisor stored on app.state)
    - bot.dashboard.jobs (uninstall passes supervisor)
tech_stack:
  added: []
  patterns:
    - atomic tmp+replace for state.json and config.json writes
    - deferred httpx import inside validate_bot_token
    - HTMX hx-post + hx-ext="json-enc" for token form submission
    - HX-Redirect header for full-page reload on success
key_files:
  created:
    - bot/modules/telegram_bridge_state.py
    - bot/dashboard/bridge_routes.py
    - bot/dashboard/templates/_fragments/bridge_install_form.html
    - bot/dashboard/templates/_fragments/bridge_status_toast.html
    - tests/modules/test_bridge_state.py
    - tests/dashboard/test_bridge_install.py
  modified:
    - bot/main.py
    - bot/modules/context.py
    - bot/dashboard/jobs.py
    - bot/dashboard/module_routes.py
    - bot/dashboard/app.py
decisions:
  - "Token is validated via Telegram getMe before any state is written (T-09-03)"
  - "Token value never logged; only bot username from getMe response (T-09-02)"
  - "install_bridge writes config.json then state.json then enqueues job — order matters for FSM"
  - "redact_bridge_config returns a copy; input dict never mutated"
  - "claim-status endpoint returns empty div stub — FSM logic deferred to Plan 02"
metrics:
  duration: "~25 min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 6
  files_modified: 5
---

# Phase 09 Plan 01: Bridge State Module + Token Install Endpoint Summary

**One-liner:** Telegram bot token install flow with getMe validation, atomic state init, and full token redaction in all API responses.

---

## Tasks Completed

### Task 1: Phase 8 integration fixes + bridge state module

**Commit:** `6af4af3`

**Phase 8 fixes applied:**

- **D-9.0a** (`bot/main.py`): `dashboard_app.state.supervisor = supervisor` stores the Supervisor instance on FastAPI app so bridge routes can access it.
- **D-9.0b** (`bot/dashboard/jobs.py`): `_run_uninstall` now reads `app.state.supervisor` and passes it to `bot_modules.uninstall()` so `on_stop` fires on dashboard-initiated uninstalls.
- **D-9.0c** (`bot/modules/context.py`): Added `from __future__ import annotations` + `TYPE_CHECKING` guard for FastAPI import; `dashboard_app` field typed as `FastAPI | None` without circular import at runtime.

**Bridge state module (`bot/modules/telegram_bridge_state.py`):**

- `read_state(module_dir)` — reads `state.json`; returns `{}` on missing/corrupt file
- `write_state(module_dir, state)` — atomic tmp+replace write to `state.json`
- `validate_bot_token(token)` — async getMe call via httpx with 10s timeout; returns `(ok, username, error)`
- `redact_bridge_config(entry)` — strips `token` key from config dict, adds `has_token: bool`; non-mutating copy
- `get_owner_id(hub_dir)` — reads registry + state.json; returns owner_id only when `claim_status == "claimed"`

**Tests:** 7 unit tests in `tests/modules/test_bridge_state.py` — all pass.

---

### Task 2: Token install endpoint + redaction + install form

**Commit:** `447ce15`

**`bot/dashboard/bridge_routes.py`:**

- `POST /api/modules/telegram-bridge/install` — validates token via `validate_bot_token`, writes `config.json` atomically, initialises `state.json` as unclaimed, enqueues install job via `start_install`, returns `HX-Redirect: /modules/telegram-bridge/config` on success
- `GET /api/modules/telegram-bridge/claim-status` — stub returning empty div (Plan 02 fills FSM logic)
- Never logs the token value; logs only `@username` from getMe response (T-09-02)

**`bot/dashboard/module_routes.py`:** `redact_bridge_config` already imported and called in `config_get` for `telegram-bridge` — token stripped before any template context (T-09-01).

**`bot/dashboard/app.py`:** `_register_bridge_routes_if_available` hook calls `bridge_routes.register(app, templates)`.

**Templates:**

- `_fragments/bridge_install_form.html` — password input, `hx-post`, `hx-ext="json-enc"`, `#status-toast` target
- `_fragments/bridge_status_toast.html` — `<div class="{{ cls }}" role="alert">{{ message }}</div>`

**Tests:** 6 integration tests in `tests/dashboard/test_bridge_install.py` — all pass.

---

## Verification

- `pytest tests/dashboard/test_bridge_install.py tests/modules/test_bridge_state.py -x -v` — 15 passed
- `pytest tests/ -x -q` — 286 passed, 0 failures, 0 regressions

---

## Deviations from Plan

None — plan executed exactly as written. All Task 2 implementation files (bridge_routes.py, module_routes.py redaction, app.py hook, templates) were already present in the wip commit `46c470f` from a prior partial run on the same branch. The test file `tests/dashboard/test_bridge_install.py` was the only missing artifact; created and committed at `447ce15`.

---

## Known Stubs

- `GET /api/modules/telegram-bridge/claim-status` returns `HTMLResponse("")` — intentional stub. Plan 02 implements the full FSM polling logic.

---

## Threat Flags

None — all threat mitigations from the plan's threat model were implemented:

| Threat | Status |
|--------|--------|
| T-09-01 Information Disclosure (GET /api/modules) | Mitigated — redact_bridge_config strips token |
| T-09-02 Information Disclosure (logs) | Mitigated — only username logged, never token |
| T-09-03 Spoofing (POST /install) | Mitigated — getMe validates before any state write |
| T-09-05 Information Disclosure (input field) | Mitigated — type="password" in template |

---

## Self-Check: PASSED

- `bot/modules/telegram_bridge_state.py` — EXISTS
- `bot/dashboard/bridge_routes.py` — EXISTS
- `bot/dashboard/templates/_fragments/bridge_install_form.html` — EXISTS
- `bot/dashboard/templates/_fragments/bridge_status_toast.html` — EXISTS
- `tests/modules/test_bridge_state.py` — EXISTS
- `tests/dashboard/test_bridge_install.py` — EXISTS
- Commit `6af4af3` — EXISTS (Task 1)
- Commit `447ce15` — EXISTS (Task 2)
- 286 tests pass, 0 failures
