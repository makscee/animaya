# Phase 9: Install Dialog & Owner-Claim FSM - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning
**Mode:** auto (all decisions auto-selected from recommended defaults)

<domain>
## Phase Boundary

Owner installs and claims the Telegram bridge entirely from the dashboard -- no `.env` edits, no systemd restarts, no env-var owner gate. After Phase 9, TELEGRAM_OWNER_ID is removed from the codebase and ownership is managed through a 6-digit pairing-code FSM stored in module state.json.

Requirements: BRDG-02, CLAIM-01, CLAIM-02, CLAIM-03, CLAIM-04, SEC-01

</domain>

<decisions>
## Implementation Decisions

### Phase 8 Integration Fixes (prerequisites)
- **D-9.0a:** Store `Supervisor` instance on `app.state.supervisor` in `main.py:_run()` so dashboard routes can access the live supervisor for lifecycle operations (audit gap: BRDG-03, BRDG-04).
- **D-9.0b:** Fix `jobs._run_uninstall()` to pass `supervisor=app.state.supervisor` to `lifecycle.uninstall()` so `on_stop` fires before script execution (audit gap: broken E2E flow).
- **D-9.0c:** Fix `AppContext.dashboard_app` typing -- use `TYPE_CHECKING` import or Protocol instead of `object | None` (tech debt from Phase 8 audit).

### Token Install UX
- **D-9.1:** Token entry lives on the existing module config page (`/modules/telegram-bridge/config`). Single form with one text input + "Install" button. No multi-step wizard -- keep it simple.
- **D-9.2:** On submit, backend validates token via Telegram `getMe` before persisting. If invalid: return error message, no state written. If valid: write token to `config.json`, start bridge via supervisor, redirect to config page showing "Running" status.
- **D-9.3:** Install route is `POST /api/modules/telegram-bridge/install` with body `{"token": "..."}`. Existing `start_install` job pattern in `jobs.py` is extended -- validation happens synchronously before enqueuing the install job.

### getMe Validation
- **D-9.4:** Direct `httpx.AsyncClient.get(f"https://api.telegram.org/bot{token}/getMe")` -- no python-telegram-bot import needed. httpx is already a dependency. Parse response JSON: `ok == true` means valid. Extract `result.username` for display confirmation.
- **D-9.5:** Timeout: 10 seconds. On network error or timeout: return "Could not reach Telegram API" error, not a validation failure.

### Pairing Code Mechanics
- **D-9.6:** Generate 6-digit numeric code via `secrets.SystemRandom().randint(100000, 999999)`. Store HMAC-SHA256 hash in state.json (never store plaintext code server-side after initial display).
- **D-9.7:** Code displayed on module config page after install. HTMX `hx-get` polls `/api/modules/telegram-bridge/claim-status` every 5 seconds to update countdown and detect claim completion.
- **D-9.8:** TTL: 10 minutes from generation. Max attempts: 5. After expiry or exhaustion, code invalidated -- user must click "Regenerate" button.
- **D-9.9:** Telegram-side: user sends the 6-digit code as a message to the bot. Bridge handler checks `claim_status == "pending"`, validates with `hmac.compare_digest`, and on match sets `claim_status = "claimed"` + `owner_id = sender.id`.

### FSM State Structure
- **D-9.10:** `state.json` for telegram-bridge module:
  ```json
  {
    "claim_status": "unclaimed | pending | claimed",
    "owner_id": null | 123456789,
    "pairing_code_hash": null | "hmac_hex_string",
    "pairing_code_salt": null | "random_hex",
    "pairing_code_expires": null | "2026-04-16T12:10:00Z",
    "pairing_attempts": 0
  }
  ```
- **D-9.11:** FSM transitions:
  - `unclaimed` -- fresh install or after revoke. No owner_id, no code.
  - `unclaimed -> pending` -- dashboard clicks "Generate pairing code". Code hash + TTL written.
  - `pending -> claimed` -- valid code received via Telegram. owner_id set.
  - `claimed -> unclaimed` -- dashboard clicks "Revoke ownership". owner_id cleared.
  - `pending -> unclaimed` -- code expires or max attempts reached. Auto-transition.

### Dashboard Auth Migration
- **D-9.12:** Replace `TELEGRAM_OWNER_ID` env var gate entirely. New auth flow:
  1. Read owner_id from telegram-bridge module's state.json.
  2. If module not installed OR claim_status != "claimed": dashboard is open (no owner gate). This allows initial setup.
  3. If claimed: `require_owner` dependency validates session cookie user_id matches state.json owner_id.
- **D-9.13:** Remove `_owner_ids()` / `_owner_ids_from_env()` from `bot/dashboard/deps.py` and `bot/bridge/telegram.py`. Replace with `get_owner_id()` that reads from state.json.
- **D-9.14:** Update all tests that mock `TELEGRAM_OWNER_ID` to use state.json fixtures instead.

### Token Redaction (SEC-01)
- **D-9.15:** `GET /api/modules/telegram-bridge` returns `{"has_token": true}` instead of the actual token value. Token field excluded from all API responses.
- **D-9.16:** Token never logged -- use `token[:4]...` pattern if debug logging needed. Grep verification after full install+claim+uninstall cycle.

### Claude's Discretion
- HMAC key derivation details (salt generation, key source)
- Exact HTMX template structure for pairing code countdown
- Error message wording for invalid tokens, expired codes, max attempts
- Whether to show bot username after getMe validation (nice-to-have, not required)
- Test partitioning between unit and integration tests

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Module System (Phase 8 foundation)
- `.planning/phases/08-bridge-extraction-supervisor-cutover/08-CONTEXT.md` -- All Phase 8 decisions (D-8.1 through D-8.7); supervisor, AppContext, lifecycle contracts
- `bot/modules/supervisor.py` -- Supervisor.start_all/stop_all, _load_module_config, handle storage
- `bot/modules/lifecycle.py` -- install(), async uninstall(), _seed_bridge_token(), owned_paths cleanup

### Dashboard (existing patterns)
- `bot/dashboard/module_routes.py` -- POST /modules/{name}/install, /uninstall, GET /config endpoints
- `bot/dashboard/jobs.py` -- start_install/start_uninstall job queue with asyncio.Lock
- `bot/dashboard/auth.py` -- URLSafeTimedSerializer session cookie pattern, require_owner dependency
- `bot/dashboard/deps.py` -- _owner_ids() env var gate (TO BE REPLACED)

### Bridge (owner gate to replace)
- `bot/bridge/telegram.py` -- _owner_ids_from_env() filter (TO BE REPLACED)

### Audit (integration fixes)
- `.planning/v2.0-MILESTONE-AUDIT.md` -- Integration gaps: supervisor not on app.state, uninstall without supervisor arg

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bot/dashboard/module_routes.py`: Install/uninstall endpoints already exist -- extend with token validation
- `bot/dashboard/auth.py`: Session cookie signing with URLSafeTimedSerializer -- reuse for owner auth
- `bot/dashboard/jobs.py`: Async job queue with lock -- extend for validated install flow
- `bot/modules/lifecycle.py`: install()/uninstall() with config injection -- extend for getMe validation
- httpx already imported in multiple modules -- use for Telegram API calls

### Established Patterns
- Module config stored in `<module_dir>/config.json` (supervisor loads via `_load_module_config`)
- Module state in `<module_dir>/state.json` (purged on uninstall per D-8.6)
- HTMX for dashboard interactivity (vendored htmx 2.0.8)
- FastAPI dependency injection for auth (`require_owner`)
- Registry entry has `config: dict` field for module settings

### Integration Points
- `POST /api/modules/telegram-bridge/install` -- extend existing route
- `bot/modules_runtime/telegram_bridge.py:on_start()` -- already reads `config["token"]`
- `app.state.supervisor` -- NEW: must be set in main.py (D-9.0a)
- `require_owner` dependency -- refactor to read state.json instead of env var

</code_context>

<specifics>
## Specific Ideas

- Requirements spec is very precise: hmac.compare_digest for timing-safe comparison, 5 attempts max, 10-minute TTL -- follow exactly.
- Token seeding (D-8.4) already exists -- Phase 9 adds the dashboard UI path but doesn't change the env fallback for existing deployments.
- The pairing code UX is one-directional: dashboard shows code, user types it in Telegram. No QR code in v2.0 (deferred).

</specifics>

<deferred>
## Deferred Ideas

- QR-code pairing alternative to 6-digit (listed in REQUIREMENTS.md Future Requirements)
- Multi-owner / team-bot support
- Retry-with-backoff on on_start failure (from Phase 8 deferred ideas)
- SUMMARY frontmatter `requirements_completed` field fix (Phase 8 tech debt -- cosmetic)

</deferred>

---

*Phase: 09-install-dialog-owner-claim-fsm*
*Context gathered: 2026-04-16*
