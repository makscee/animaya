---
phase: 09-install-dialog-owner-claim-fsm
plan: "02"
subsystem: dashboard
tags: [bridge, pairing-code, fsm, hmac, htmx, security, telegram]
dependency_graph:
  requires:
    - bot.modules.telegram_bridge_state (read_state, write_state) — Plan 01
    - bot.dashboard.bridge_routes (register) — Plan 01 stub extended
  provides:
    - bot.modules.telegram_bridge_state (generate_pairing_code, verify_pairing_code, check_expiry)
    - bot.dashboard.bridge_routes (claim-status FSM, generate-code, regenerate endpoints)
    - bot.bridge.telegram (_claim_handler at group=-2)
    - _fragments/pairing_code_{pending,claimed,unclaimed}.html
  affects:
    - bot.modules_runtime.telegram_bridge (module_dir stored in bot_data)
    - bot.dashboard.templates._fragments.bridge_install_form (claim-status hx-get block)
tech_stack:
  added: []
  patterns:
    - HMAC-SHA256 with per-code salt; plaintext code never persisted (T-09-08)
    - hmac.compare_digest for timing-safe verification (T-09-06)
    - PTB TypeHandler at group=-2 for claim processing before owner gate
    - HTMX hx-trigger="every 5s" polling with outerHTML swap
    - hx-trigger="load" for initial claim-status fetch on config page
key_files:
  created:
    - bot/dashboard/templates/_fragments/pairing_code_pending.html
    - bot/dashboard/templates/_fragments/pairing_code_claimed.html
    - bot/dashboard/templates/_fragments/pairing_code_unclaimed.html
  modified:
    - bot/modules/telegram_bridge_state.py
    - bot/bridge/telegram.py
    - bot/modules_runtime/telegram_bridge.py
    - bot/dashboard/bridge_routes.py
    - bot/dashboard/static/style.css
    - bot/dashboard/templates/_fragments/bridge_install_form.html
    - tests/modules/test_bridge_state.py
    - tests/dashboard/test_bridge_install.py
decisions:
  - "Plaintext code returned once in HTTP response body only — never written to disk (T-09-08)"
  - "hmac.compare_digest used for timing-safe HMAC comparison (T-09-06)"
  - "check_expiry called on every claim-status poll to auto-transition expired codes"
  - "module_dir injected into bot_data before polling starts so handlers can access state.json"
  - "test_claim_status_pending uses session_secret fixture (not monkeypatch.setenv) to avoid overwriting auth secret"
metrics:
  duration: "~30 min"
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 2
  files_created: 3
  files_modified: 8
---

# Phase 09 Plan 02: Pairing Code FSM Summary

**One-liner:** HMAC-backed pairing code FSM with HTMX polling UI — 6-digit code generated in dashboard, verified via Telegram, stored as SHA-256 hash with per-code salt, never plaintext on disk.

---

## Tasks Completed

### Task 1: Pairing code generation/verification + bridge claim handler

**Commit:** `9f58c85`

**`bot/modules/telegram_bridge_state.py` additions:**

- `generate_pairing_code(module_dir)` — generates 100000–999999 code via `secrets.SystemRandom`, hashes with HMAC-SHA256 keyed by `SESSION_SECRET` + per-code salt, writes only the hash to `state.json`. Returns plaintext code for one-time display.
- `verify_pairing_code(candidate, state)` — checks attempt cap (>=5 → False), TTL expiry, then `hmac.compare_digest` against stored hash.
- `check_expiry(state)` — auto-transitions expired pending codes to `unclaimed`, clearing all pairing fields. Caller writes state if changed.

**`bot/bridge/telegram.py` additions:**

- `_claim_handler` — async handler at `group=-2`, processes exactly 6-digit text messages. Increments attempts before verify, handles exhausted attempts (transition to unclaimed + message), incorrect codes (countdown reply), and success (write claimed state + `ApplicationHandlerStop`).
- Registered in `build_app()` via `app.add_handler(TypeHandler(Update, _claim_handler), group=-2)`.

**`bot/modules_runtime/telegram_bridge.py`:**

- Stores `module_dir` in `tg_app.bot_data["module_dir"]` after `build_app()` so `_claim_handler` can access `state.json`.

**Tests:** 7 new unit tests (16 total in `tests/modules/test_bridge_state.py`) — all pass.

---

### Task 2: HTMX pairing templates + dashboard FSM endpoints

**Commit:** `43a7c6d`

**`bot/dashboard/bridge_routes.py` (stub replaced):**

- `GET /api/modules/telegram-bridge/claim-status` — reads state, calls `check_expiry` (writes if transitioned), returns appropriate fragment: `pairing_code_pending.html` (with dashes, not plaintext code), `pairing_code_claimed.html`, or `pairing_code_unclaimed.html`.
- `POST /api/modules/telegram-bridge/generate-code` — calls `generate_pairing_code`, returns `pairing_code_pending.html` with plaintext code (one-time display, `pct=100`, `ttl_display="10m 0s"`, `attempts_remaining=5`).
- `POST /api/modules/telegram-bridge/regenerate` — same as generate-code; `generate_pairing_code` overwrites old hash atomically.

**Templates created:**

- `pairing_code_pending.html` — `hx-trigger="every 5s"` polling, progress bar with TTL warning at <120s, attempt counter, Regenerate button.
- `pairing_code_claimed.html` — success alert + Revoke Ownership button with `hx-confirm`.
- `pairing_code_unclaimed.html` — field-help text + Generate Pairing Code button.

**`bot/dashboard/static/style.css`:** Added `.pairing-code` class (monospace, 1.3rem, letter-spacing, user-select: all).

**`bot/dashboard/templates/_fragments/bridge_install_form.html`:** Added `hx-trigger="load"` claim-status div when `has_token=True` so the claim section appears immediately on the config page after bridge install.

**Tests:** 6 new integration tests (12 total in `tests/dashboard/test_bridge_install.py`) — all pass.

---

## Verification

- `pytest tests/modules/test_bridge_state.py -x` — 16 passed
- `pytest tests/dashboard/test_bridge_install.py -x` — 12 passed
- `pytest tests/ -x -q` — 299 passed, 0 failures, 0 regressions

---

## Deviations from Plan

**1. [Rule 1 - Bug] Fixed session_secret fixture conflict in pending test**
- **Found during:** Task 2 test run
- **Issue:** `test_claim_status_pending` called `monkeypatch.setenv("SESSION_SECRET", "test-secret")` which overwrote the `session_secret` fixture's value used by `auth_client` cookie signing, causing 302 redirects.
- **Fix:** Replaced `monkeypatch` parameter with `session_secret: str` fixture (already wired through `auth_client` fixture chain); same fix applied to `test_generate_code` and `test_regenerate_code`.
- **Files modified:** `tests/dashboard/test_bridge_install.py`

---

## Known Stubs

None — all Plan 02 deliverables are fully implemented. The `revoke` endpoint (`hx-post="/api/modules/telegram-bridge/revoke"` in `pairing_code_claimed.html`) is referenced in the template but not yet implemented — this is intentional as revoke was not in the Plan 02 scope.

---

## Threat Flags

None — all threat mitigations from the plan's threat model were implemented:

| Threat | Status |
|--------|--------|
| T-09-06 Elevation of Privilege (brute force) | Mitigated — 5-attempt cap + hmac.compare_digest |
| T-09-07 Elevation of Privilege (expired reuse) | Mitigated — TTL check in verify + check_expiry on every poll |
| T-09-08 Information Disclosure (poll endpoint) | Mitigated — polls return "------" not plaintext code |
| T-09-09 Spoofing (enumeration) | Mitigated — 900k codes, 5 attempts, 10-min TTL |

---

## Self-Check: PASSED

- `bot/modules/telegram_bridge_state.py` — EXISTS, contains `generate_pairing_code`, `verify_pairing_code`, `check_expiry`, `hmac.compare_digest`
- `bot/bridge/telegram.py` — EXISTS, contains `_claim_handler`, `group=-2`
- `bot/modules_runtime/telegram_bridge.py` — EXISTS, contains `bot_data["module_dir"]`
- `bot/dashboard/bridge_routes.py` — EXISTS, contains `claim-status`, `generate-code`, `regenerate` routes
- `bot/dashboard/static/style.css` — EXISTS, contains `.pairing-code {`
- `bot/dashboard/templates/_fragments/pairing_code_pending.html` — EXISTS, contains `hx-trigger="every 5s"`
- `bot/dashboard/templates/_fragments/pairing_code_claimed.html` — EXISTS, contains `Revoke Ownership`
- `bot/dashboard/templates/_fragments/pairing_code_unclaimed.html` — EXISTS, contains `Generate Pairing Code`
- `tests/modules/test_bridge_state.py` — EXISTS, 16 tests
- `tests/dashboard/test_bridge_install.py` — EXISTS, 12 tests
- Commit `9f58c85` — EXISTS (Task 1)
- Commit `43a7c6d` — EXISTS (Task 2)
- 299 tests pass, 0 failures
