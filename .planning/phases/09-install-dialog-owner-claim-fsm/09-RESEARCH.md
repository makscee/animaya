# Phase 9: Install Dialog & Owner-Claim FSM — Research

**Researched:** 2026-04-16
**Domain:** FastAPI dashboard extension, HMAC-based pairing FSM, token redaction, Telegram getMe validation
**Confidence:** HIGH — all findings verified against live codebase; no external library versions needed beyond what is already installed

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Phase 8 Integration Fixes (prerequisites)**
- D-9.0a: Store `Supervisor` instance on `app.state.supervisor` in `main.py:_run()`.
- D-9.0b: Fix `jobs._run_uninstall()` to pass `supervisor=app.state.supervisor` to `lifecycle.uninstall()`.
- D-9.0c: Fix `AppContext.dashboard_app` typing — use `TYPE_CHECKING` import or Protocol instead of `object | None`.

**Token Install UX**
- D-9.1: Token entry on existing module config page (`/modules/telegram-bridge/config`). Single form, one input.
- D-9.2: Backend validates via `getMe` before persisting. Invalid → error, no state written. Valid → write token to `config.json`, start bridge via supervisor, redirect.
- D-9.3: Route is `POST /api/modules/telegram-bridge/install` with body `{"token": "..."}`. Validation is synchronous before enqueuing install job.

**getMe Validation**
- D-9.4: Direct `httpx.AsyncClient.get("https://api.telegram.org/bot{token}/getMe")`. Parse `ok == true`. Extract `result.username`.
- D-9.5: Timeout 10 seconds. Network error/timeout → "Could not reach Telegram API", not a validation failure.

**Pairing Code Mechanics**
- D-9.6: `secrets.SystemRandom().randint(100000, 999999)`. Store HMAC-SHA256 hash in state.json, never plaintext.
- D-9.7: Code displayed on config page. HTMX `hx-get` polls `/api/modules/telegram-bridge/claim-status` every 5 seconds.
- D-9.8: TTL 10 minutes, max 5 attempts. After expiry/exhaustion, user must click "Regenerate".
- D-9.9: Bridge handler checks `claim_status == "pending"`, validates with `hmac.compare_digest`, on match sets `claim_status = "claimed"` + `owner_id = sender.id`.

**FSM State Structure**
- D-9.10: `state.json` schema: `claim_status`, `owner_id`, `pairing_code_hash`, `pairing_code_salt`, `pairing_code_expires`, `pairing_attempts`.
- D-9.11: FSM transitions: unclaimed → pending (generate code) → claimed (valid code) → unclaimed (revoke); pending → unclaimed (expire/exhaust).

**Dashboard Auth Migration**
- D-9.12: Replace `TELEGRAM_OWNER_ID` env gate. New: read `owner_id` from state.json. If not claimed → dashboard open. If claimed → `require_owner` validates session user_id == state.json owner_id.
- D-9.13: Remove `_owner_ids()` / `_owner_ids_from_env()` from `deps.py` and `telegram.py`. Add `get_owner_id()` reading from state.json.
- D-9.14: Update all tests that mock `TELEGRAM_OWNER_ID` to use state.json fixtures.

**Token Redaction (SEC-01)**
- D-9.15: `GET /api/modules/telegram-bridge` returns `{"has_token": true}`, not the actual token.
- D-9.16: Token never logged. Use `token[:4]...` pattern for debug logging if needed.

### Claude's Discretion
- HMAC key derivation details (salt generation, key source)
- Exact HTMX template structure for pairing code countdown
- Error message wording
- Whether to show bot username after getMe validation
- Test partitioning between unit and integration tests

### Deferred Ideas (OUT OF SCOPE)
- QR-code pairing alternative
- Multi-owner / team-bot support
- Retry-with-backoff on on_start failure
- SUMMARY frontmatter `requirements_completed` field fix
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BRDG-02 | Install dialog captures bot token and validates via Telegram `getMe` before persisting to module config | httpx already present; direct API call pattern confirmed; D-9.3/9.4/9.5 fully specified |
| CLAIM-01 | Install emits 6-digit pairing code with 10-min TTL, capped at 5 attempts, verified with `hmac.compare_digest` | `secrets`, `hmac` from stdlib; HTMX polling pattern in existing dashboard |
| CLAIM-02 | Dashboard can regenerate the pairing code on demand, invalidating any prior code | Single POST endpoint to reset pairing fields in state.json; state machine transition already defined |
| CLAIM-03 | Owner can revoke ownership from dashboard; module returns to pending-claim state | Transition `claimed → unclaimed` in D-9.11; requires clearing owner_id and pairing fields |
| CLAIM-04 | Owner `user_id` persisted only in module `state.json`; `TELEGRAM_OWNER_ID` env gate removed | Five files contain `TELEGRAM_OWNER_ID` references; all identified below |
| SEC-01 | Bot token never leaves server — redacted in API responses and logs | `has_token: bool` pattern; no Pydantic `SecretStr` needed — manual exclusion is simpler given existing dict-based config storage |
</phase_requirements>

---

## Summary

Phase 9 is a pure extension of the Phase 8 module system. There are no new library dependencies — every capability needed (httpx, hmac, secrets, HTMX, FastAPI, Jinja2) is already installed. The work splits into four coherent areas: (1) three Phase 8 integration fixes on `main.py`, `jobs.py`, and `context.py`; (2) the token install flow — a new `POST /api/modules/telegram-bridge/install` endpoint with synchronous `getMe` validation before the existing job queue; (3) the pairing-code FSM — new state.json file, HMAC storage, HTMX polling endpoint, and a new message handler branch in the bridge; (4) auth migration — replacing the `TELEGRAM_OWNER_ID` env gate in `deps.py` and `telegram.py` with a `get_owner_id()` state.json reader, and updating five test files.

The single most important architectural insight is that `state.json` for the telegram-bridge module is already purged on uninstall by `lifecycle.uninstall()` (verified in code). No special uninstall hook is needed for Phase 9 — owner state is automatically cleaned up.

The single most important pitfall is the open-dashboard bootstrap problem: `require_owner` must return a passable result when state.json does not exist or `claim_status != "claimed"`, or the owner can never complete the install flow in the first place (they need to reach the config page unauthenticated to enter the token).

**Primary recommendation:** Wire the three Phase 8 fixes first (Wave 0), then build the install+getMe flow (Wave 1), then the pairing FSM + bridge handler (Wave 2), then auth migration + token redaction (Wave 3).

---

## Standard Stack

All dependencies are already installed. No `pip install` or `npm install` needed.

### Core (already present)
| Library | Purpose | Verified |
|---------|---------|---------|
| `httpx` | Async HTTP for `getMe` call | [VERIFIED: imports in bot/features/audio.py, bot/features/image_gen.py] |
| `hmac` (stdlib) | Timing-safe digest comparison | [VERIFIED: Python 3.12 stdlib] |
| `secrets` (stdlib) | Cryptographically secure random int | [VERIFIED: Python 3.12 stdlib] |
| `hashlib` (stdlib) | SHA256 for HMAC | [VERIFIED: Python 3.12 stdlib] |
| `json` (stdlib) | state.json read/write | [VERIFIED: used throughout codebase] |
| `FastAPI` 0.115.0 | Route registration | [VERIFIED: pyproject.toml] |
| `httpx.AsyncClient` | Async HTTP within FastAPI route | [VERIFIED: existing usage pattern] |
| `Jinja2` | HTMX fragment templates | [VERIFIED: bot/dashboard/templates/] |
| `python-telegram-bot` | Bridge message handler extension | [VERIFIED: existing bridge] |

### HMAC Key Derivation (Claude's Discretion)

The CONTEXT.md leaves HMAC key derivation to Claude. Recommended approach:

```python
import hmac, hashlib, secrets, os

salt = secrets.token_hex(16)  # random per code generation
key = os.environ.get("SESSION_SECRET", "").encode()  # reuse existing secret
code_hash = hmac.new(key, (salt + str(code)).encode(), hashlib.sha256).hexdigest()
```

Store `pairing_code_hash` and `pairing_code_salt` in state.json. On verification:

```python
expected = hmac.new(key, (salt + candidate_code).encode(), hashlib.sha256).hexdigest()
hmac.compare_digest(expected, stored_hash)  # timing-safe
```

`SESSION_SECRET` is already required at boot — reusing it avoids a new env var. [ASSUMED: no dedicated `PAIRING_HMAC_KEY` env var is required; SESSION_SECRET is sufficient for this use case]

---

## Architecture Patterns

### Recommended File Layout for New Code

```
bot/
├── modules/
│   └── telegram_bridge_state.py   — state.json read/write helpers (get_claim_state, set_claim_state, get_owner_id)
├── dashboard/
│   ├── deps.py                    — replace _owner_ids() with get_owner_id() from state.json
│   └── bridge_routes.py           — new file: install, claim-status, regenerate, revoke endpoints
└── bridge/
    └── telegram.py                — replace _parse_owner_ids()/_owner_gate() with state.json reader
modules/
└── telegram-bridge/
    └── (no new files — state.json is written at runtime, not shipped)
```

Alternatively, bridge_routes can be added to `module_routes.py` directly. Preferred: separate `bridge_routes.py` to avoid growing module_routes further and to isolate the telegram-specific logic.

### Pattern 1: Synchronous getMe Validation Before Job Enqueue

The existing install endpoint calls `start_install()` directly. For the telegram-bridge, validation must happen **before** the job:

```python
# bot/dashboard/bridge_routes.py
@app.post("/api/modules/telegram-bridge/install")
async def install_bridge(request: Request, _uid: int = Depends(require_owner)):
    body = await request.json()
    token = body.get("token", "").strip()
    if not token:
        return error_fragment("Token is required")
    
    # Synchronous getMe validation (D-9.4)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        data = resp.json()
    except (httpx.TimeoutException, httpx.RequestError):
        return error_fragment("Could not reach Telegram API")
    
    if not data.get("ok"):
        return error_fragment("Invalid bot token")
    
    # Only reach here if token is valid
    # Write token to config.json, then enqueue install job
    ...
```

[VERIFIED: httpx.AsyncClient timeout parameter confirmed via existing usage in bot/features/audio.py]

### Pattern 2: state.json Atomic Write

Match the existing pattern from `main.py:_seed_telegram_bridge_token()`:

```python
import json
from pathlib import Path

def write_state(module_dir: Path, state: dict) -> None:
    state_path = module_dir / "state.json"
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(state_path)
```

[VERIFIED: atomic write pattern used in main.py lines 92-94]

### Pattern 3: HTMX Polling for Claim Status

The dashboard already vendors htmx 2.0.8. The polling fragment pattern (hx-get + hx-trigger="every 5s") is already used in job status polling (`_fragments/module_card_running.html`). Reuse the same pattern:

```html
<!-- pairing_code_pending.html fragment -->
<div id="claim-status"
     hx-get="/api/modules/telegram-bridge/claim-status"
     hx-trigger="every 5s"
     hx-target="#claim-status"
     hx-swap="outerHTML">
  <p>Code: <strong>{{ code }}</strong></p>
  <p>Expires in: <span id="countdown">{{ ttl_seconds }}</span>s</p>
  <button hx-post="/api/modules/telegram-bridge/regenerate">Regenerate</button>
</div>
```

When claim-status returns a "claimed" fragment, the HTMX swap replaces the polling div — polling stops automatically.

[VERIFIED: htmx vendored at bot/dashboard/static/, job polling template in _fragments/module_card_running.html]

### Pattern 4: FSM State Transitions in state.json

`lifecycle.uninstall()` already purges `state.json` at lines 396-402 of `lifecycle.py`. Phase 9 just needs to write and read it — no uninstall hook changes needed.

State file location: `{module_dir}/state.json` where `module_dir` is the value in the registry entry (e.g. `~/animaya/modules/telegram-bridge/`).

### Pattern 5: require_owner with Open Bootstrap

Current `require_owner` in `deps.py` reads `TELEGRAM_OWNER_ID` — fails closed (403) when env is unset. After migration it must be open when no owner is claimed:

```python
def get_owner_id(hub_dir: Path) -> int | None:
    """Return owner_id from telegram-bridge state.json, or None if unclaimed."""
    from bot.modules.registry import get_entry
    entry = get_entry(hub_dir, "telegram-bridge")
    if entry is None:
        return None
    module_dir = Path(entry["module_dir"])
    state_path = module_dir / "state.json"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if state.get("claim_status") != "claimed":
        return None
    return state.get("owner_id")

def require_owner(
    request: Request,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> int:
    hub_dir: Path = request.app.state.hub_dir
    owner_id = get_owner_id(hub_dir)
    if owner_id is None:
        return 0  # open — no owner claimed yet; allow access for initial setup
    # ... existing cookie validation, compare against owner_id ...
```

`hub_dir` is already on `app.state.hub_dir` (confirmed in `module_routes.py` line 38).

### Anti-Patterns to Avoid

- **Writing token to registry.json instead of config.json:** The supervisor reads config from `module_dir/config.json` (confirmed in `supervisor.py:_load_module_config`). Token must go to `config.json`, not the registry `config` field.
- **Storing plaintext pairing code:** D-9.6 is explicit — only HMAC hash stored server-side. Never write the 6-digit code to disk.
- **Logging token value:** `main.py` already demonstrates the "log path, not token" pattern. Extend to all new endpoints.
- **Using `==` for code comparison:** `hmac.compare_digest` is mandatory (CLAIM-01). Direct string comparison is vulnerable to timing attacks.
- **Blocking the event loop during getMe:** Use `httpx.AsyncClient` (async), not `httpx.get()` (sync), inside a FastAPI async route.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Timing-safe comparison | Custom constant-time comparison | `hmac.compare_digest` | stdlib, well-tested, CLAIM-01 explicit requirement |
| Cryptographic random | `random.randint` | `secrets.SystemRandom().randint` | `random` is not cryptographically secure |
| Atomic file write | Open/write without tmp | tmp+replace pattern (already in codebase) | Prevents partial-write corruption on crash |
| HTTP client | `urllib.request` | `httpx.AsyncClient` | Already a dependency; non-blocking in async context |
| Session signing | Custom cookie encoding | `URLSafeTimedSerializer` (itsdangerous) | Already in `auth.py`; do not duplicate |

---

## Common Pitfalls

### Pitfall 1: Open Bootstrap vs Closed Auth

**What goes wrong:** After removing `TELEGRAM_OWNER_ID`, `require_owner` reads state.json and finds no owner → returns 403 → owner can never reach the config page to install the token.

**Why it happens:** `require_owner` is applied to all module routes including `GET /modules/telegram-bridge/config` (confirmed in `module_routes.py` lines 70-85, 142-173).

**How to avoid:** When `get_owner_id()` returns `None` (no owner claimed), `require_owner` must allow access rather than deny it. This is the "open" state in the FSM. Document the threat model: dashboard is open until claimed.

**Warning signs:** Test `GET /modules/telegram-bridge/config` with no state.json returns 403 instead of 200.

### Pitfall 2: Token Written to Wrong Location

**What goes wrong:** Token written to registry entry `config` dict (in registry.json) instead of `module_dir/config.json`. Supervisor loads from `module_dir/config.json` first (lines 26-31 of `supervisor.py`), so registry config is a fallback. If only registry is updated, the seeded token from `main.py` pattern is fine for env seeds but a fresh Phase 9 install that writes to registry.json only will work until next boot — then supervisor overwrites with the (empty) config.json.

**How to avoid:** Write token to `module_dir/config.json` directly, matching the `_seed_telegram_bridge_token` pattern in `main.py:75-94`.

**Warning signs:** Bridge starts after install, but fails to start after restart.

### Pitfall 3: supervisor Not on app.state (D-9.0a)

**What goes wrong:** `install_endpoint` calls `supervisor.start_module(...)` but `app.state.supervisor` is None because `main.py` never assigned it. All current code builds `supervisor` as a local in `_run()` and never attaches it.

**Why it happens:** This is explicitly an audit gap (D-9.0a). Phase 8 shipped the Supervisor class but `main.py` never does `app.state.supervisor = supervisor`.

**How to avoid:** Wave 0 of Phase 9 must add `dashboard_app.state.supervisor = supervisor` to `_run()` immediately after creating the Supervisor instance (line 187 of `main.py`).

**Warning signs:** `AttributeError: 'State' object has no attribute 'supervisor'` at runtime.

### Pitfall 4: jobs._run_uninstall Missing supervisor Arg (D-9.0b)

**What goes wrong:** Uninstall from dashboard does not stop the running Telegram polling loop. The supervisor stops on bot shutdown but not during a dashboard-triggered uninstall.

**Why it happens:** `_run_uninstall` in `jobs.py` (lines 223-257) calls `bot_modules.uninstall(name, hub_dir, module_dir)` without `supervisor=` — but `lifecycle.uninstall()` accepts an optional `supervisor` parameter (line 312).

**How to avoid:** Wave 0 fix — change `_run_uninstall` to pass `supervisor=app.state.supervisor` (requires `_run_uninstall` to accept the app or supervisor reference).

### Pitfall 5: Pairing Code Expiry Check Race

**What goes wrong:** TTL checked at message receipt but not at "Regenerate" time. An expired code that hasn't been regenerated can be left in `pending` state in state.json indefinitely (until next bot restart or explicit regenerate).

**How to avoid:** The HTMX poll endpoint (`/api/modules/telegram-bridge/claim-status`) must also check expiry on each poll and transition `pending → unclaimed` when TTL has passed, not just when the bridge message handler checks it.

### Pitfall 6: Test Fixtures Use TELEGRAM_OWNER_ID

**What goes wrong:** After removing `TELEGRAM_OWNER_ID` from `deps.py`, all tests that mock it via `monkeypatch.setenv("TELEGRAM_OWNER_ID", "...")` will no longer gate access — all routes become open. Existing tests that expect 403 for non-owner will pass erroneously.

**Files to update:** [VERIFIED by grep]
- `tests/test_skeleton.py`
- `tests/test_main_boot.py`
- `tests/dashboard/conftest.py` — `owner_id` fixture (line 51-54) and `client` fixture (line 82-105)
- `tests/dashboard/test_main_wiring.py`
- `tests/dashboard/test_app_shell.py`

**How to avoid:** Replace `owner_id` fixture with a `claimed_bridge_state` fixture that writes a state.json with `claim_status: "claimed"` and `owner_id: 111222333` to the test module_dir.

---

## Code Examples

### getMe Validation (D-9.4, D-9.5)
```python
# Source: D-9.4/9.5 decisions, httpx usage pattern from bot/features/audio.py
import httpx

async def validate_bot_token(token: str) -> tuple[bool, str | None, str | None]:
    """Returns (is_valid, username_or_none, error_message_or_none)."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
        data = resp.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        return False, None, "Could not reach Telegram API"
    if not data.get("ok"):
        description = data.get("description", "Invalid token")
        return False, None, description
    username = data.get("result", {}).get("username")
    return True, username, None
```

### HMAC Pairing Code Generation (D-9.6)
```python
# Source: D-9.6, Python 3.12 stdlib hmac/secrets docs
import hmac
import hashlib
import secrets
import os
from datetime import datetime, timezone, timedelta

def generate_pairing_code(module_dir: Path) -> dict:
    """Generate a pairing code and return the state.json update dict."""
    code = secrets.SystemRandom().randint(100000, 999999)
    salt = secrets.token_hex(16)
    key = os.environ.get("SESSION_SECRET", "").encode()
    digest = hmac.new(key, (salt + str(code)).encode(), hashlib.sha256).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    # Display code once; never write plaintext to disk
    return {
        "display_code": code,  # returned to caller for display only
        "state": {
            "claim_status": "pending",
            "owner_id": None,
            "pairing_code_hash": digest,
            "pairing_code_salt": salt,
            "pairing_code_expires": expires,
            "pairing_attempts": 0,
        },
    }

def verify_pairing_code(candidate: str, state: dict) -> bool:
    """Verify candidate code against stored HMAC hash. Returns True on match."""
    from datetime import datetime, timezone
    # Check expiry
    expires_str = state.get("pairing_code_expires")
    if expires_str:
        expires = datetime.fromisoformat(expires_str)
        if datetime.now(timezone.utc) > expires:
            return False
    # Check attempt cap
    if state.get("pairing_attempts", 0) >= 5:
        return False
    salt = state.get("pairing_code_salt", "")
    stored_hash = state.get("pairing_code_hash", "")
    key = os.environ.get("SESSION_SECRET", "").encode()
    expected = hmac.new(key, (salt + candidate).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, stored_hash)
```

### Bridge Handler: Claim Message (D-9.9)
```python
# Source: D-9.9 decision; extends existing _owner_gate pattern in telegram.py
async def _claim_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle a potential pairing code message. Registered at group=-2."""
    text = (update.message.text or "").strip()
    if not text.isdigit() or len(text) != 6:
        return  # not a pairing code — fall through to normal handlers
    
    # Load state
    state = read_bridge_state(module_dir)
    if state.get("claim_status") != "pending":
        return  # gate open or already claimed — ignore
    
    # Increment attempt counter before verify (prevents enumeration)
    state["pairing_attempts"] = state.get("pairing_attempts", 0) + 1
    write_bridge_state(module_dir, state)
    
    if not verify_pairing_code(text, state):
        if state["pairing_attempts"] >= 5:
            state["claim_status"] = "unclaimed"
            write_bridge_state(module_dir, state)
            await update.message.reply_text("Max attempts reached. Regenerate code from dashboard.")
        return
    
    # Claim!
    user_id = update.effective_user.id
    state.update({
        "claim_status": "claimed",
        "owner_id": user_id,
        "pairing_code_hash": None,
        "pairing_code_salt": None,
        "pairing_code_expires": None,
        "pairing_attempts": 0,
    })
    write_bridge_state(module_dir, state)
    await update.message.reply_text("Ownership claimed. You are now the owner of this bot.")
    raise ApplicationHandlerStop  # prevent further handlers from processing
```

### Token Redaction in Module API (D-9.15)
```python
# Source: D-9.15 decision; pattern for existing module_routes.py dict responses
def _redact_bridge_config(entry: dict) -> dict:
    """Replace raw token with has_token bool in API responses."""
    config = entry.get("config") or {}
    redacted = {k: v for k, v in config.items() if k != "token"}
    redacted["has_token"] = bool(config.get("token"))
    return {**entry, "config": redacted}
```

---

## Runtime State Inventory

> This phase removes `TELEGRAM_OWNER_ID` from the codebase and introduces state.json as the owner store.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `state.json` is new — does not exist yet for any deployment | Write on first pairing code generation; purged by existing `lifecycle.uninstall()` |
| Live service config | No external service config; `TELEGRAM_OWNER_ID` is env var, not external service | Code edit only — remove from `REQUIRED_ENV_VARS` and all readers |
| OS-registered state | None — no task scheduler, pm2, or systemd entries reference `TELEGRAM_OWNER_ID` | None |
| Secrets/env vars | `TELEGRAM_OWNER_ID` read in `deps.py` and `telegram.py`; `SESSION_SECRET` reused as HMAC key | Remove reads; SESSION_SECRET already required — no new env var |
| Build artifacts | None — no compiled binaries or egg-info reference owner ID | None |

**Migration concern for existing deployments:** Any live deployment with `TELEGRAM_OWNER_ID` set will lose owner gating after this phase until the owner completes the pairing-code flow. Mitigation: on first boot after migration, if `TELEGRAM_OWNER_ID` is set and bridge is installed and state.json has no owner, auto-seed owner_id from env (one-shot, same pattern as D-8.4 token seed). [ASSUMED: this migration behaviour is desirable; planner should confirm or add to Wave 0]

---

## Environment Availability

Step 2.6: SKIPPED for library checks — all dependencies (httpx, hmac, secrets, FastAPI, Jinja2, python-telegram-bot) are already installed in the project. No new installs required.

The `api.telegram.org` endpoint is an external dependency reachable at runtime. No test-time availability required — tests should mock `httpx.AsyncClient` to avoid network calls.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BRDG-02 | `POST /api/modules/telegram-bridge/install` with valid token → installs, starts bridge | integration | `pytest tests/dashboard/test_bridge_install.py -x` | ❌ Wave 0 |
| BRDG-02 | Invalid token → 200 with error fragment, no state written | unit | `pytest tests/dashboard/test_bridge_install.py::test_invalid_token -x` | ❌ Wave 0 |
| BRDG-02 | Network error during getMe → error fragment, no state written | unit | `pytest tests/dashboard/test_bridge_install.py::test_getme_network_error -x` | ❌ Wave 0 |
| CLAIM-01 | Pairing code generation → hash stored, plaintext not in state.json | unit | `pytest tests/modules/test_bridge_state.py::test_pairing_code_hash_only -x` | ❌ Wave 0 |
| CLAIM-01 | Correct code within TTL + attempts → claim_status=claimed, owner_id set | unit | `pytest tests/modules/test_bridge_state.py::test_claim_success -x` | ❌ Wave 0 |
| CLAIM-01 | 5 failed attempts → status→unclaimed, further attempts blocked | unit | `pytest tests/modules/test_bridge_state.py::test_max_attempts -x` | ❌ Wave 0 |
| CLAIM-01 | Expired code → claim fails | unit | `pytest tests/modules/test_bridge_state.py::test_expired_code -x` | ❌ Wave 0 |
| CLAIM-02 | Regenerate endpoint → new hash, old hash invalidated | unit | `pytest tests/dashboard/test_bridge_install.py::test_regenerate -x` | ❌ Wave 0 |
| CLAIM-03 | Revoke → claim_status=unclaimed, owner_id=null | unit | `pytest tests/dashboard/test_bridge_install.py::test_revoke -x` | ❌ Wave 0 |
| CLAIM-04 | `TELEGRAM_OWNER_ID` not imported in deps.py or telegram.py | static/grep | `pytest tests/test_skeleton.py::test_no_telegram_owner_id_in_deps -x` | ❌ Wave 0 |
| CLAIM-04 | require_owner allows access when no owner claimed | unit | `pytest tests/dashboard/test_bridge_install.py::test_open_bootstrap -x` | ❌ Wave 0 |
| SEC-01 | `GET /api/modules/telegram-bridge` returns `has_token: true`, no token value | unit | `pytest tests/dashboard/test_bridge_install.py::test_token_redacted_in_api -x` | ❌ Wave 0 |
| SEC-01 | Token not in log output after install+claim+uninstall | integration | manual + grep verification | manual |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/dashboard/test_bridge_install.py` — covers BRDG-02, CLAIM-02, CLAIM-03, CLAIM-04, SEC-01
- [ ] `tests/modules/test_bridge_state.py` — covers CLAIM-01 (HMAC, TTL, attempts)
- [ ] Update `tests/dashboard/conftest.py` — replace `owner_id` fixture with `claimed_bridge_state` fixture
- [ ] Update `tests/test_skeleton.py` — add `test_no_telegram_owner_id_in_deps`
- [ ] Update `tests/test_main_boot.py` — remove `monkeypatch.setenv("TELEGRAM_OWNER_ID", ...)` where no longer applicable
- [ ] Update `tests/dashboard/test_main_wiring.py` and `test_app_shell.py` similarly

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | HMAC-SHA256 with `hmac.compare_digest`; 5-attempt cap; 10-min TTL |
| V3 Session Management | yes | Existing `URLSafeTimedSerializer` session cookie unchanged |
| V4 Access Control | yes | `require_owner` dependency; open bootstrap only before first claim |
| V5 Input Validation | yes | Token stripped/validated via getMe; pairing code validated as 6-digit numeric |
| V6 Cryptography | yes | `secrets.SystemRandom` for code generation; `hmac.compare_digest` for comparison |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Token exfiltration via API | Information Disclosure | `has_token: bool` only in GET responses; D-9.15 |
| Token in logs | Information Disclosure | Never log token; log path only; D-9.16 |
| Brute-force pairing code | Elevation of Privilege | 5-attempt cap → transition to unclaimed; D-9.8 |
| Timing attack on code comparison | Elevation of Privilege | `hmac.compare_digest` required; D-9.9 |
| Expired code reuse | Elevation of Privilege | TTL check before any comparison; D-9.8 |
| Pre-claim dashboard access | Elevation of Privilege | Accepted by design — open state is intentional; docs should note this |
| SSRF via Telegram API URL | Spoofing | Token is the only variable; URL is hardcoded `api.telegram.org`; acceptable |

---

## Open Questions

1. **Auto-seed owner_id from TELEGRAM_OWNER_ID on migration**
   - What we know: Live deployments have TELEGRAM_OWNER_ID set; after Phase 9 it is removed from deps.py.
   - What's unclear: Should Phase 9 auto-migrate existing owner from env → state.json on first boot (matching D-8.4 token seed pattern)?
   - Recommendation: Yes — add a one-shot `seed_owner_from_env()` in `main.py:_run()` alongside the token seed. Planner should confirm.

2. **Where does `module_dir` come from inside the bridge message handler?**
   - What we know: The bridge's `on_start(ctx, config)` receives `ctx.data_path`. Module dir is derivable from `get_entry(ctx.data_path, "telegram-bridge")["module_dir"]`.
   - What's unclear: The bridge handler (`_owner_gate`, `_handle_message`) currently reads env vars directly. After migration it needs access to `module_dir` at message-receive time — this must be captured in `on_start` closure scope and passed into handlers via `bot_data` or closure.
   - Recommendation: In `on_start`, resolve `module_dir` from registry and store on `tg_app.bot_data["module_dir"]` so all handlers can access it.

3. **AppContext.dashboard_app typing (D-9.0c)**
   - What we know: Currently `object | None`. The decision says use `TYPE_CHECKING` import or Protocol.
   - What's unclear: Whether this is a runtime fix or import-time only. Since `context.py` is a frozen dataclass, `TYPE_CHECKING` with `FastAPI` string annotation is the cleanest approach.
   - Recommendation: `from typing import TYPE_CHECKING; if TYPE_CHECKING: from fastapi import FastAPI` + annotate as `"FastAPI | None"`. No runtime impact.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `SESSION_SECRET` is sufficient as HMAC key for pairing codes; no new env var needed | Code Examples / HMAC | Low — worst case add a dedicated env var, update key derivation only |
| A2 | Auto-seeding owner_id from `TELEGRAM_OWNER_ID` on migration is desirable | Runtime State Inventory | Medium — if not done, existing deployments lose owner gating until manual pairing |
| A3 | `require_owner` should return `0` (allow) rather than raise when no owner claimed | Architecture Patterns / Pattern 5 | High — if wrong, fresh installs cannot reach the config page at all |

---

## Sources

### Primary (HIGH confidence)
- Codebase: `bot/dashboard/deps.py` — existing `require_owner` and `_owner_ids()` implementation
- Codebase: `bot/dashboard/jobs.py` — existing `start_install`, `_run_uninstall` patterns
- Codebase: `bot/dashboard/auth.py` — `URLSafeTimedSerializer` session cookie pattern
- Codebase: `bot/modules/lifecycle.py` — `uninstall()` state.json purge (lines 396-402), atomic write pattern
- Codebase: `bot/modules/supervisor.py` — `get_handle()`, `_handles`, `_runtime_entries`
- Codebase: `bot/main.py` — `_seed_telegram_bridge_token()` atomic write pattern; `REQUIRED_ENV_VARS`
- Codebase: `bot/bridge/telegram.py` lines 629-660 — `_parse_owner_ids()` and `_owner_gate()` to be replaced
- Codebase: `tests/dashboard/conftest.py` — `owner_id` fixture and `client` fixture referencing `TELEGRAM_OWNER_ID`
- grep: 5 test files confirmed to reference `TELEGRAM_OWNER_ID`

### Secondary (MEDIUM confidence)
- Python 3.12 docs: `hmac.compare_digest`, `secrets.SystemRandom`, `hashlib.sha256` — stdlib, no version concern
- Telegram Bot API: `getMe` endpoint response shape — well-documented, stable

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present in codebase
- Architecture: HIGH — all patterns verified against live source files
- Pitfalls: HIGH — each pitfall traced to specific line numbers in existing code
- Test map: HIGH — test file names follow established project conventions; file existence verified

**Research date:** 2026-04-16
**Valid until:** 2026-05-16 (stable stdlib + stable codebase; no fast-moving external dependencies)
