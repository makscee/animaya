---
phase: 05
plan: 02
subsystem: dashboard-auth
tags: [auth, security, telegram, session, htmx-gated]
requires:
  - itsdangerous (already in pyproject deps)
  - fastapi (already in pyproject deps)
  - TELEGRAM_BOT_TOKEN env (Phase 2)
  - SESSION_SECRET env (new, Phase 5)
  - TELEGRAM_OWNER_ID env (new, Phase 5)
provides:
  - bot.dashboard.auth.verify_telegram_payload
  - bot.dashboard.auth.issue_session_cookie
  - bot.dashboard.auth.read_session_cookie
  - bot.dashboard.auth.clear_session_cookie_kwargs
  - bot.dashboard.auth.SESSION_COOKIE_NAME
  - bot.dashboard.auth.SESSION_MAX_AGE_SECONDS
  - bot.dashboard.auth.AUTH_DATE_FRESHNESS_SECONDS
  - bot.dashboard.deps.require_owner
affects:
  - Plans 05-03..05-06 (import require_owner on every protected route)
tech-stack:
  added: []
  patterns:
    - HMAC-SHA256 Telegram Login Widget verification
    - itsdangerous URLSafeTimedSerializer for signed session cookies
    - Fail-closed env-var dependency (missing SESSION_SECRET / empty owner list)
key-files:
  created:
    - bot/dashboard/deps.py
    - tests/dashboard/__init__.py
    - tests/dashboard/conftest.py
    - tests/dashboard/test_auth.py
  modified:
    - bot/dashboard/auth.py (full rewrite per D-22)
decisions:
  - Rewrote bot/dashboard/auth.py from scratch (D-22) — v1 DASHBOARD_TOKEN decorator dropped
  - SESSION_SECRET chosen over reusing DASHBOARD_TOKEN (distinct responsibility — addresses 05-CONTEXT open question)
  - 5-minute future-clock-skew tolerance added to freshness check (T-05-02-02 defense)
  - read_session_cookie catches RuntimeError from _serializer() so runtime verify never crashes when SESSION_SECRET is unset (still fails closed)
metrics:
  duration: "~12 min"
  tasks: 2
  tests_added: 14
  files_created: 4
  files_modified: 1
  completed: 2026-04-15
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 05 Plan 02: Dashboard Authentication Summary

itsdangerous-signed session cookies plus Telegram Login Widget HMAC verification, gated behind a single `require_owner` FastAPI dependency the rest of Phase 5 can import.

## What Was Built

1. **Telegram Login Widget verification** (`bot.dashboard.auth.verify_telegram_payload`)
   - Implements the documented algorithm: `secret = sha256(bot_token).digest()`; `expected = HMAC-SHA256(secret, "\\n".join(sorted("k=v"))).hexdigest()`.
   - Timing-safe `hmac.compare_digest` comparison (T-05-02-09).
   - Rejects empty `bot_token`, missing `hash`, stale `auth_date` (>24 h) and implausibly-future `auth_date` (>5 min ahead).

2. **Signed session cookie** (`issue_session_cookie` / `read_session_cookie`)
   - `itsdangerous.URLSafeTimedSerializer` with server-only `SESSION_SECRET`, salt `animaya-dashboard`.
   - Payload: `{user_id, auth_date, hash}` — no PII.
   - 30-day sliding TTL; `max_age` configurable per call.
   - `issue_session_cookie` raises `RuntimeError` when `SESSION_SECRET` is unset (fail closed, T-05-02-07).
   - `clear_session_cookie_kwargs()` returns the canonical delete-cookie kwargs (`httpOnly`, `SameSite=Lax`, `Secure`).

3. **`require_owner` FastAPI dependency** (`bot.dashboard.deps`)
   - Reads `animaya_session` cookie via `Cookie(alias=SESSION_COOKIE_NAME)`.
   - 302→`/login` on missing cookie or failed signature/expiry.
   - 403 when verified `user_id` not in `TELEGRAM_OWNER_ID` allowlist (comma-separated int list).
   - Empty allowlist = everyone denied (T-05-02-06).

## Env Var Contract

| Var | Required | Source | Purpose |
|-----|----------|--------|---------|
| `TELEGRAM_BOT_TOKEN` | yes (already from Phase 2) | @BotFather | HMAC secret for Login Widget hash |
| `TELEGRAM_OWNER_ID` | yes (new) | `@userinfobot` | Comma-separated allowlist of owner Telegram user IDs |
| `SESSION_SECRET` | yes (new) | `openssl rand -hex 32` | Cookie signing key; must be stable across restarts |

Additional manual step for the operator (not code): `@BotFather → /setdomain → animaya.makscee.ru` so the Login Widget can render.

## Security Properties (STRIDE coverage)

| Threat | Mitigation |
|--------|-----------|
| T-05-02-01 Forgery | HMAC-SHA256 + compare_digest (Tests 1, 2, 5) |
| T-05-02-02 Replay | `auth_date` window ≤ 24 h; future ≤ 5 min (Test 4) |
| T-05-02-03 Cookie tamper | itsdangerous signature verification (Test 8) |
| T-05-02-04 PII leak | Cookie holds only `{user_id, auth_date, hash}` |
| T-05-02-05 Non-owner | `require_owner` allowlist (Test 13) |
| T-05-02-06 Empty allowlist | Empty env → empty set → 403 (default-deny) |
| T-05-02-07 Missing SESSION_SECRET | `_serializer()` raises RuntimeError (Test 10) |
| T-05-02-08 XSS cookie theft | `clear_session_cookie_kwargs` documents `httpOnly+Secure+SameSite=Lax` (applied at set-cookie time by Plan 03) |
| T-05-02-09 Timing leak | `hmac.compare_digest` in both HMAC verify and itsdangerous internals |

## Commits

- `729f9ff` test(05-02): add failing auth tests (RED) — 14 tests
- `3ab2070` feat(05-02): Telegram Login Widget HMAC + itsdangerous session + require_owner

## Verification

- `tests/dashboard/test_auth.py` — 14/14 pass
- `tests/` full suite — 133/133 pass
- `ruff check bot/dashboard/auth.py bot/dashboard/deps.py tests/dashboard/` — clean
- `wc -l bot/dashboard/auth.py` — 147 lines (≥ 100 acceptance)
- `wc -l bot/dashboard/deps.py` — 57 lines (≥ 40 acceptance)

## Deviations from Plan

None — plan executed exactly as written. Two micro-adjustments kept within the plan's own text:

1. The plan sample had `read_session_cookie(token: str, …)`; I widened the type to `str | None` so `Depends(Cookie(default=None))` can flow through without a caller-side `assert`. Behaviour for `None` is identical to the plan's "bad/expired/missing → None" contract.
2. `read_session_cookie` also swallows the `RuntimeError` raised when `SESSION_SECRET` is unset at read time (it still fails closed by returning `None`). This matches the "fail closed" spirit of the threat model (T-05-02-07) and avoids leaking 500s to unauthenticated clients.

Neither changes any test outcome and neither introduces new dependencies or files.

## Deferred Items

None.

## Known Stubs

None.

## Consumers (what Plans 03–06 will import)

```python
from bot.dashboard.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    clear_session_cookie_kwargs,
    issue_session_cookie,
    read_session_cookie,
    verify_telegram_payload,
)
from bot.dashboard.deps import require_owner
```

Every protected route adds `uid: int = Depends(require_owner)`. `/auth/telegram` (Plan 03) calls `verify_telegram_payload` then `issue_session_cookie` and sets the cookie with `httpOnly=True, samesite="lax", secure=True, max_age=SESSION_MAX_AGE_SECONDS`. `/logout` (Plan 03) calls `response.delete_cookie(**clear_session_cookie_kwargs())`.

## Self-Check: PASSED

- bot/dashboard/auth.py — FOUND (147 lines, contains `verify_telegram_payload`, `issue_session_cookie`, `read_session_cookie`, `hmac.compare_digest`, `URLSafeTimedSerializer`)
- bot/dashboard/deps.py — FOUND (57 lines, contains `require_owner`, `TELEGRAM_OWNER_ID`)
- tests/dashboard/test_auth.py — FOUND (14 `def test_` entries)
- tests/dashboard/conftest.py — FOUND (fixtures `session_secret`, `bot_token`, `owner_id`)
- commit 729f9ff — FOUND in git log
- commit 3ab2070 — FOUND in git log
