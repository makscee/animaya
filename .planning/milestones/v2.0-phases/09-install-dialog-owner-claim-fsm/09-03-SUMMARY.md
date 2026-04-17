---
phase: 09-install-dialog-owner-claim-fsm
plan: "03"
subsystem: dashboard-auth
tags: [auth, state-json, owner-gate, revoke, sec-01, claim-04]
dependency_graph:
  requires: [09-01, 09-02]
  provides: [state-json-auth, revoke-endpoint, open-bootstrap, owner-seed-migration]
  affects: [dashboard-routes, telegram-bridge, main-boot]
tech_stack:
  added: []
  patterns:
    - open-bootstrap (no owner = open access, D-9.12)
    - state.json-backed auth replacing env var gate
    - one-shot owner seed migration for existing deployments (T-09-13)
key_files:
  created: []
  modified:
    - bot/dashboard/deps.py
    - bot/dashboard/app.py
    - bot/dashboard/bridge_routes.py
    - bot/bridge/telegram.py
    - bot/main.py
    - bot/dashboard/templates/login.html
    - scripts/setup.sh
    - README.md
    - tests/dashboard/conftest.py
    - tests/dashboard/test_auth.py
    - tests/dashboard/test_bridge_install.py
    - tests/dashboard/test_main_wiring.py
    - tests/test_main_boot.py
    - tests/test_skeleton.py
decisions:
  - "open-bootstrap: unclaimed dashboard returns 0 (open access) so install page is reachable before first claim"
  - "owner seed migration: _seed_owner_from_env() is idempotent -- skips if owner already exists"
  - "app.py login route uses get_owner_id(hub_dir) from state.json -- not env var"
  - "test_auth.py stub app sets app.state.hub_dir explicitly for require_owner dependency"
metrics:
  duration: ~35 minutes
  completed: "2026-04-16"
  tasks_completed: 2
  tasks_total: 3
  files_modified: 14
---

# Phase 9 Plan 03: Auth Migration & Test Fixture Migration Summary

**One-liner:** State.json-backed owner auth replacing TELEGRAM_OWNER_ID env gate, with open-bootstrap, revoke endpoint, and one-shot seed migration.

## What Was Built

### Task 1: Auth migration (production code)

**deps.py rewritten** — `require_owner` now accepts `Request` and reads `hub_dir` from `request.app.state.hub_dir`. Calls `get_owner_id(hub_dir)` from `telegram_bridge_state`. Returns `0` (open access) when no owner has claimed; raises 302/403 when owner is claimed and session doesn't match.

**telegram.py owner gate rewritten** — `_owner_gate` reads `state.json` via `read_state(module_dir)` from `context.bot_data.get("module_dir")`. No env var dependency. Allows all messages when `claim_status != "claimed"`.

**main.py** — Removed `TELEGRAM_OWNER_ID` from `REQUIRED_ENV_VARS`. Added `_seed_owner_from_env(hub_dir)` one-shot migration helper that reads `TELEGRAM_OWNER_ID` env (if set) and writes `owner_id` into `state.json` only if no owner exists yet. Runs at boot after token seed.

**bridge_routes.py** — Added `POST /api/modules/telegram-bridge/revoke` endpoint. Protected by `Depends(require_owner)` (T-09-12). Clears all ownership/pairing fields, writes unclaimed state, returns `pairing_code_unclaimed.html` fragment.

**app.py** — Login route updated to use `get_owner_id(hub_dir)` from state.json (not `_owner_ids()` from env).

**scripts/setup.sh** — Removed `TELEGRAM_OWNER_ID` check block.

**README.md** — Removed `TELEGRAM_OWNER_ID` row from environment variables table.

### Task 2: Test fixture migration + new tests

**conftest.py** — `owner_id` fixture now delegates to `claimed_bridge_state`, which writes `state.json` + `registry.json` entries into `temp_hub_dir`. No env var set.

**test_auth.py** — Updated `_stub_app()` to accept `hub_dir` and set `app.state.hub_dir`. All `require_owner` tests pass `temp_hub_dir`. Added `test_require_owner_open_bootstrap_no_owner`.

**test_bridge_install.py** — Fixed `test_claim_status_claimed` to use `owner_id` fixture. Added:
- `test_revoke_endpoint` — verifies revoke transitions state to unclaimed
- `test_open_bootstrap_no_owner` — verifies 200 when no owner claimed (D-9.12)
- `test_auth_gate_with_owner_no_cookie` — verifies 302 when owner claimed + no cookie
- `test_auth_gate_with_owner_wrong_cookie` — verifies 403 when wrong user_id
- `test_token_not_in_logs_after_install` — SEC-01 verification

**test_skeleton.py** — Added `test_no_telegram_owner_id_in_deps` and `test_no_telegram_owner_id_in_bridge` (CLAIM-04 grep tests).

**test_main_boot.py, test_main_wiring.py** — Removed `TELEGRAM_OWNER_ID` from env setup calls and parametrize lists.

### Task 3: Human verification checkpoint (not yet completed)

Human verification of full install + claim + revoke flow is pending.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] app.py imported _owner_ids which no longer exists**
- **Found during:** Task 1 execution — first test run
- **Issue:** `bot/dashboard/app.py` imported `_owner_ids` from `deps.py` (deleted function) and used it in login route
- **Fix:** Updated `app.py` to import `get_owner_id` from `telegram_bridge_state` and use it directly in login route
- **Files modified:** `bot/dashboard/app.py`
- **Commit:** b97db01

**2. [Rule 1 - Bug] test_auth.py stub app missing hub_dir**
- **Found during:** Task 2 test run
- **Issue:** `_stub_app()` created a FastAPI app without `app.state.hub_dir`, causing `AttributeError` when `require_owner` accessed it
- **Fix:** Updated `_stub_app` to accept `hub_dir: Path` parameter and set `app.state.hub_dir`; updated all test functions to pass `temp_hub_dir`
- **Files modified:** `tests/dashboard/test_auth.py`
- **Commit:** 6558e53

**3. [Rule 1 - Bug] test_claim_status_claimed used mismatched owner_id**
- **Found during:** Task 2 test run
- **Issue:** Test seeded state with `owner_id: 12345` but `auth_client` cookie had `owner_id=111222333` → 403
- **Fix:** Updated test to use `owner_id` fixture value (from `claimed_bridge_state`) for consistent matching
- **Files modified:** `tests/dashboard/test_bridge_install.py`
- **Commit:** 6558e53

**4. [Rule 2 - Missing] Stale TELEGRAM_OWNER_ID in login.html template**
- **Found during:** Acceptance criteria verification
- **Issue:** Template error message still referenced `TELEGRAM_OWNER_ID` by name
- **Fix:** Updated error text to describe actual misconfiguration condition (no DASHBOARD_TOKEN or no claimed owner)
- **Files modified:** `bot/dashboard/templates/login.html`
- **Commit:** b97db01

## Known Stubs

None — all new functionality is wired to real state.json I/O.

## Threat Flags

No new trust boundaries introduced beyond those in the plan's threat model (T-09-11 through T-09-15). All mitigations applied:
- T-09-12: revoke endpoint guarded by `Depends(require_owner)` ✓
- T-09-13: `_seed_owner_from_env` skips if owner already exists ✓
- T-09-14: token never logged; grep tests enforce no raw token in logs ✓

## Test Results

306 tests passed (0 failures, 12 deprecation warnings).

## Self-Check

- [x] `bot/dashboard/deps.py` does NOT contain `TELEGRAM_OWNER_ID`
- [x] `bot/bridge/telegram.py` does NOT contain `TELEGRAM_OWNER_ID`
- [x] `bot/main.py` REQUIRED_ENV_VARS does NOT contain `TELEGRAM_OWNER_ID`
- [x] `bot/main.py` contains `def _seed_owner_from_env(`
- [x] `bot/dashboard/bridge_routes.py` contains `/api/modules/telegram-bridge/revoke` route
- [x] `scripts/setup.sh` does NOT contain `TELEGRAM_OWNER_ID`
- [x] `README.md` does NOT contain `TELEGRAM_OWNER_ID`
- [x] `tests/dashboard/conftest.py` contains `def claimed_bridge_state(`
- [x] `tests/test_skeleton.py` contains `test_no_telegram_owner_id_in_deps` and `test_no_telegram_owner_id_in_bridge`
- [x] 306 tests pass

## Self-Check: PASSED
