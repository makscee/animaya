---
phase: 05
plan: 03
subsystem: dashboard-shell
tags: [dashboard, fastapi, jinja, htmx, login, telegram-widget, css]
requires:
  - bot.dashboard.auth (Plan 05-02)
  - bot.dashboard.deps.require_owner (Plan 05-02)
  - TELEGRAM_BOT_USERNAME env (new in Phase 5)
  - itsdangerous, fastapi, jinja2, starlette (already in pyproject)
provides:
  - bot.dashboard.app.build_app
  - bot.dashboard.app.templates  (module-level Jinja2Templates instance)
  - bot/dashboard/static/style.css (voidnet token + primitives + animaya extensions)
  - bot/dashboard/static/favicon.svg
  - bot/dashboard/templates/base.html
  - bot/dashboard/templates/login.html
  - bot/dashboard/templates/_home_placeholder.html
affects:
  - Plans 05-04 / 05-05 / 05-06 import `templates` and register `home_routes` / `module_routes`
  - Plan 05-04 will replace the placeholder `/` route via `home_routes.register(app, templates)`
tech-stack:
  added:
    - HTMX 2.0.3 (CDN, version-pinned)
    - Telegram Login Widget (CDN, first-party)
  patterns:
    - FastAPI app-factory with try/except ImportError hooks for downstream plans
    - Starlette 1.0 `TemplateResponse(request, name, context)` signature
    - 303 See Other for POST→GET redirect after auth callback
    - voidnet design tokens (CSS custom properties) — single source of truth
key-files:
  created:
    - bot/dashboard/app.py
    - bot/dashboard/static/style.css
    - bot/dashboard/static/favicon.svg
    - bot/dashboard/templates/base.html
    - bot/dashboard/templates/login.html
    - bot/dashboard/templates/_home_placeholder.html
    - tests/dashboard/_helpers.py
    - tests/dashboard/test_app_shell.py
    - tests/dashboard/test_login.py
  modified:
    - tests/dashboard/conftest.py  (TestClient now disables follow_redirects)
decisions:
  - Module-level `templates = Jinja2Templates(directory=...)` so Plans 05-04/05/06 reuse one instance
  - Optional `home_routes` / `module_routes` registered via try/except ImportError so the shell stays usable in isolation
  - Placeholder `/` route lives in `_register_home_placeholder`; Plan 05-04 will override it (FastAPI honors first-added; Plan 05-04 must register before this stub OR remove it)
  - HTMX pinned to 2.0.3 via unpkg; SRI integrity hash deferred (T-05-03-07 hardening follow-up)
  - 303 (See Other) used for /auth/telegram and /logout — semantically correct for POST-then-redirect-to-GET
  - `_owner_ids` reused from `bot.dashboard.deps` (single source of allowlist parsing)
metrics:
  duration: "~10 min"
  tasks: 3
  tests_added: 14
  files_created: 9
  files_modified: 1
  completed: 2026-04-15
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 05 Plan 03: Dashboard Shell Summary

FastAPI app factory wiring `/login`, `/auth/telegram`, `/logout`, `/static/*`, and a placeholder `/` behind the `require_owner` dependency — the chassis every Phase-5 page extends.

## What Was Built

1. **`build_app(hub_dir) -> FastAPI` factory** (`bot/dashboard/app.py`)
   - Disables OpenAPI/docs/redoc (T-05-03-05).
   - Mounts `/static` for the CSS/favicon.
   - Registers auth routes (`/login`, `/auth/telegram`, `/logout`) and a home placeholder.
   - Calls optional `home_routes.register(app, templates)` (Plan 05-04) and `module_routes.register(app, templates)` (Plan 05-05) under `ImportError` guards so the shell is usable in isolation.

2. **Telegram Login Widget callback** (`POST /auth/telegram`)
   - Parses `multipart`/`form-urlencoded`, calls `verify_telegram_payload(payload, TELEGRAM_BOT_TOKEN)`.
   - On HMAC failure, distinguishes stale (auth_date age > 24 h → `?error=stale`) from invalid (`?error=invalid`).
   - On valid HMAC, checks `_owner_ids()` allowlist (`?error=forbidden` if non-owner).
   - On success, mints `animaya_session` cookie via `issue_session_cookie` and redirects to `/` with `303` and the canonical security flags (`httpOnly`, `Secure`, `SameSite=Lax`).

3. **`GET /logout`** — clears cookie via `clear_session_cookie_kwargs()` and redirects to `/login`.

4. **`GET /` placeholder** — `_home_placeholder.html` rendered behind `Depends(require_owner)`. Plan 05-04 will overwrite.

5. **Templates** (`bot/dashboard/templates/`)
   - `base.html` — DOCTYPE, viewport, favicon, stylesheet, HTMX 2.0.3 (deferred), `<h1 class=gradient>Animaya</h1>`, nav with active-state, `#status-toast` slot, `{% block content %}`.
   - `login.html` — login card, per-error copy (invalid/stale/forbidden/misconfigured/default), Telegram Login Widget script (only when `TELEGRAM_BOT_USERNAME` is set).
   - `_home_placeholder.html` — minimal placeholder panel with the authenticated user_id.

6. **Static assets** (`bot/dashboard/static/`)
   - `style.css` (356 lines): voidnet token block (`--accent`, `--bg-base`, `--err`, `--ok`, …) + primitives (`.container`, `.card`, `.panel`, `.stats/.stat`, `.badge*`, `.dot*`, `.btn*`, `.login-box`, `.activity-item`, `.field`, `.error/.success`) + animaya extensions (`.dot-warn`, `.progress-indeterminate` with `@keyframes animaya-progress-sweep`, `.modules-grid`, `pre.job-log`).
   - `favicon.svg` — 32×32 rounded square, accent gradient "A" mark.

## Cookie Flag Contract

Every set/clear of `animaya_session` uses:

| Flag | Value | Why |
|------|-------|-----|
| HttpOnly | true | T-05-03-06 — JS can't read session token |
| Secure   | true | Caddy terminates TLS; cookie never crosses plaintext |
| SameSite | Lax  | T-05-03-10 — blocks cross-site state-changing POSTs |
| Path     | /    | Single SPA-ish surface; no nested apps |
| Max-Age  | 30 days | `SESSION_MAX_AGE_SECONDS` per Plan 05-02 D-03 |

## Template Structure (consumed by Plans 05-04/05/06)

```python
from bot.dashboard.app import templates  # Jinja2Templates instance

# Plan 05-04 example
def register(app, templates):
    @app.get("/")
    async def home(request: Request, uid: int = Depends(require_owner)):
        return templates.TemplateResponse(request, "home.html", {"uid": uid})
```

The factory calls `home_routes.register` and `module_routes.register` if importable — so Plans 04/05 only need to ship a module that defines `register(app, templates) -> None`.

## CSS Token Provenance

All colors/spacing in `style.css` derive from `~/hub/knowledge/voidnet/ui-spec.md` §2 (Design Tokens). The animaya extensions (`.dot-warn`, `.progress-indeterminate`, `.modules-grid`, `pre.job-log`) are documented in `05-UI-SPEC.md` and use only existing tokens — no new color values introduced.

## Threat Coverage (STRIDE — see `<threat_model>` in PLAN)

| Threat | Mitigation Implemented |
|--------|------------------------|
| T-05-03-01 Forged callback | `verify_telegram_payload` — sole gate on `/auth/telegram` |
| T-05-03-02 Replay > 24 h | `verify_telegram_payload` rejects → `?error=stale` |
| T-05-03-03 Non-owner login | `_owner_ids()` check before cookie minted |
| T-05-03-04 XSS via error param | Jinja autoescape + finite enum render branches |
| T-05-03-05 Docs leak | `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` |
| T-05-03-06 Cookie theft | HttpOnly+Secure+SameSite=Lax on every set/clear |
| T-05-03-07 Pinned HTMX | `htmx.org@2.0.3`; **SRI follow-up** (see below) |
| T-05-03-08 Telegram CDN | Trust accepted (first-party, required by spec) |
| T-05-03-09 CSRF on login | HMAC hash IS the CSRF token (attacker can't forge) |
| T-05-03-10 CSRF on /logout | GET-only per spec; SameSite=Lax on future POSTs |

## HTMX SRI Follow-up

`base.html` loads HTMX from `https://unpkg.com/htmx.org@2.0.3` with no `integrity=` attribute. Adding the `sha384-…` SRI hash is a hardening follow-up tracked here for Plan 05-07 (Caddy + reverse proxy hardening) or a dedicated security plan. Implementer should:

1. Fetch the manifest (`https://unpkg.com/htmx.org@2.0.3?meta`) or compute `openssl dgst -sha384 -binary htmx.min.js | openssl base64 -A`.
2. Append `integrity="sha384-…" crossorigin="anonymous"` to the `<script>` tag.
3. Repeat for the Telegram Login Widget if/when Telegram publishes a stable hash (currently they do not — script content evolves; SRI not feasible).

## Deviations from Plan

1. **Rule 3 — Starlette 1.0 TemplateResponse signature**. Starlette 1.0.0 (installed) deprecated the legacy `TemplateResponse(name, {"request": …, …})` form in favor of `TemplateResponse(request, name, context)`; the legacy form crashes Jinja's `LRUCache` with `TypeError: cannot use 'tuple' as a dict key (unhashable type: 'dict')`. Both call sites in `_register_auth_routes` and `_register_home_placeholder` use the new positional signature. Functionally identical to plan; no contract change.

2. **Rule 3 — `tests/dashboard/conftest.py` `client` fixture**. The fixture instantiated `TestClient(app)` (default `follow_redirects=True`), which made every `/` test render the `/login` template instead of returning 302. Added `follow_redirects=False`. No fixture-level behavioral change for any other consumer.

3. **Plan said `from bot.dashboard.deps import _owner_ids` inside the handler**. I hoisted it to a module-level import (no `noqa: PLC0415` needed) — single import, kept as-is per `bot.dashboard.deps` already exporting `require_owner`. Same call-site behavior.

## Deferred Items

- HTMX SRI hash (see follow-up above).
- Plan 05-04 must remove or pre-register the home placeholder; otherwise FastAPI honors the first-added route. Approach documented in the placeholder docstring.

## Known Stubs

- `_home_placeholder.html` is an intentional stub to be overwritten by Plan 05-04 (see `decisions:`). The plan explicitly schedules Plan 05-04 to ship the real `/` route.

## Commits

- `(test)` failing tests for app shell and login flow — RED, 14 tests
- `(feat)` dashboard static CSS + favicon + Jinja templates
- `(feat)` FastAPI app factory + Telegram login + session cookie + static + templates — GREEN

## Verification

| Check | Result |
|-------|--------|
| `pytest tests/dashboard/test_app_shell.py tests/dashboard/test_login.py -q` | 14/14 GREEN |
| `pytest tests/ -q` | 159/159 GREEN |
| `ruff check bot/dashboard/app.py tests/dashboard/` | clean |
| `wc -l bot/dashboard/app.py` | 174 (≥ 120) |
| `wc -l bot/dashboard/static/style.css` | 356 (≥ 120) |
| Routes introspection | `['/', '/auth/telegram', '/login', '/logout', '/static']` |

## Self-Check: PASSED

- bot/dashboard/app.py — FOUND (174 lines, contains build_app, templates, verify_telegram_payload, issue_session_cookie, httponly=True, samesite="lax", secure=True)
- bot/dashboard/static/style.css — FOUND (contains --accent, --err, --ok, .container, .card, .panel, .btn, .login-box, .field, .activity-item, .progress-indeterminate)
- bot/dashboard/static/favicon.svg — FOUND (starts with `<?xml`, contains `linearGradient`)
- bot/dashboard/templates/base.html — FOUND (htmx.org, status-toast)
- bot/dashboard/templates/login.html — FOUND (telegram-widget.js, data-telegram-login, error branches)
- bot/dashboard/templates/_home_placeholder.html — FOUND (extends base.html)
- tests/dashboard/_helpers.py — FOUND (_signed_payload, build_client, make_session_cookie)
- tests/dashboard/test_app_shell.py — FOUND (7 def test_)
- tests/dashboard/test_login.py — FOUND (7 def test_)
- All 3 task commits present in `git log`
