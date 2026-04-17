---
phase: 13
plan: 02
subsystem: dashboard-auth-core
tags: [auth, security, middleware, wave-2]
requires:
  - "13-01 scaffold (dashboard/ skeleton, shadcn primitives, bun-test preload)"
provides:
  - "verifyTelegramWidget() — HMAC port of bot/dashboard/auth.py widget check"
  - "readOwnerId() — OWNER.md telegram_id reader with cache + test override"
  - "dashboardTokenMatches() — Node constant-time compare"
  - "isOwner() — pure D-07 gate"
  - "CSRF helpers (csrf.{shared,server,-cookie.server}.ts) rebranded an-csrf"
  - "engineFetch() — loopback client to Python engine (127.0.0.1:8091)"
  - "sanitizeErrorMessage() — TG/OAuth/hex scrub"
  - "NextAuth v5 Credentials(telegram) provider + signIn owner gate"
  - "Edge-safe middleware: DASHBOARD_TOKEN bypass + session + owner + CSRF + security headers"
affects:
  - "dashboard/ — auth.ts, auth.config.ts, middleware.ts, lib/*.server.ts"
  - "downstream plans 13-03..06 consume all lib/*.server.ts helpers + auth()"
tech-stack:
  added:
    - "next-auth@5.0.0-beta.31 Credentials provider usage (already pinned in 13-01)"
  patterns:
    - "verbatim port pattern (csrf.* from homelab/apps/admin, 3-constant delta)"
    - "Edge-safe XOR compare for DASHBOARD_TOKEN (no node:crypto in middleware)"
    - "OWNER_MD_PATH env override for tests, HOME-relative default for install"
    - "Fail-closed: null/missing → reject in every auth path"
key-files:
  created:
    - dashboard/lib/telegram-widget.server.ts
    - dashboard/lib/telegram-widget.server.test.ts
    - dashboard/lib/dashboard-token.server.ts
    - dashboard/lib/owner.server.ts
    - dashboard/lib/owner.server.test.ts
    - dashboard/lib/owner-gate.server.ts
    - dashboard/lib/owner-gate.server.test.ts
    - dashboard/lib/csrf.shared.ts
    - dashboard/lib/csrf.server.ts
    - dashboard/lib/csrf.server.test.ts
    - dashboard/lib/csrf-cookie.server.ts
    - dashboard/lib/engine.server.ts
    - dashboard/lib/engine.server.test.ts
    - dashboard/lib/redact.server.ts
    - dashboard/lib/redact.server.test.ts
    - dashboard/types/next-auth.d.ts
    - dashboard/auth.config.ts
    - dashboard/auth.ts
    - dashboard/middleware.ts
  modified:
    - dashboard/bun.lock (bun install refresh)
decisions:
  - "OWNER.md contract: ^telegram_id:\\s*<digits>$ line (case-insensitive). Phase 11 must honor; readOwnerId() returns null on parse fail for fail-closed signIn"
  - "OWNER_MD_PATH env override added to owner.server.ts — simplifies bun-test isolation without mocking fs"
  - "Edge middleware uses OWNER_TELEGRAM_ID env (not filesystem OWNER.md) — Edge rule. Installer populates env from OWNER.md at startup"
  - "Session cookie name switches between __Secure-authjs.session-token (prod) and authjs.session-token (dev). Matches admin behavior and Auth.js default; secure:true gated on NODE_ENV=production to avoid local-HTTP cookie drop"
  - "Edge XOR compare for DASHBOARD_TOKEN accepted as T-13-16. Documented in middleware comment"
metrics:
  duration_sec: 420
  tasks: 3
  completed_date: 2026-04-17
---

# Phase 13 Plan 02: Auth core — Telegram HMAC + NextAuth v5 + Edge middleware Summary

Wave 2 ships the full auth primitive layer for the new dashboard: a byte-accurate Telegram Login Widget HMAC port (matching Python's `hmac.compare_digest` semantics via `crypto.timingSafeEqual`), a next-auth v5 Credentials provider wired to OWNER.md owner-gate rejection (D-07 no-fallback), a DASHBOARD_TOKEN bypass in Edge middleware (D-06), and the CSRF / engine-loopback / secret-redaction helpers every downstream mutation route will reuse. 35 bun-test specs across 6 files — all green; tsc clean.

## What Was Built

### Task 1 — Telegram HMAC + OWNER.md + DASHBOARD_TOKEN (commit `9b25a70`)

- `dashboard/lib/telegram-widget.server.ts` — `verifyTelegramWidget(raw, botToken)`:
  - Type-narrow unknown payload → extract `hash` → build sorted `key=value\n` data-check-string
  - `secret = SHA-256(bot_token)` (raw 32-byte digest); `expected = HMAC-SHA256(secret, dcs).hex()`
  - `crypto.timingSafeEqual(Buffer.from(expected,"hex"), Buffer.from(hash,"hex"))` with length guard
  - Rejects stale `auth_date` older than 86400s (1 day freshness per Telegram spec)
  - Fail-closed: any type narrowing failure or crypto error → `null`
- `dashboard/lib/dashboard-token.server.ts` — 3-line Node constant-time compare for server-side paths
- `dashboard/lib/owner.server.ts` — caches `readOwnerId()` via `let cached: string | null | undefined`; `OWNER_MD_PATH` env override for tests; parses `^telegram_id:\s*(\d+)$` case-insensitive; exposes `_resetOwnerCache()` for test isolation. Contract documented inline for Phase 11
- `dashboard/types/next-auth.d.ts` — augments `Session.user.id: string` and `JWT.telegramId?: string`
- 15 bun-test specs: valid/tampered/stale/missing/same-length-wrong/cross-bot-token for widget; 4 specs for OWNER.md (+cache invariance); 4 specs for dashboard-token

### Task 2 — CSRF + engine + redact (commit `0f72c05`)

- `dashboard/lib/csrf.{shared,server,-cookie.server}.ts` — verbatim port from `homelab/apps/admin/lib/csrf.*`, 3 constant deltas:
  - `CSRF_COOKIE_NAME = "an-csrf"` (was `hla-csrf`)
  - `EXPECTED_ORIGIN` resolves `NEXT_PUBLIC_ANIMAYA_PUBLIC_ORIGIN` → `ANIMAYA_PUBLIC_ORIGIN` → `https://animaya.makscee.ru`
  - `CSRF_HEADER_NAME = "x-csrf-token"` (unchanged)
  - Defense-in-depth order preserved: Origin/Referer → cookie presence+entropy → header presence → length-guard + XOR constant-time compare
- `dashboard/lib/engine.server.ts` — `engineFetch(path, init?)` always injects `cache: "no-store"`; env-resolved per call (not module-load) so test mocks work; default `http://127.0.0.1:8091`
- `dashboard/lib/redact.server.ts` — three regexes (TG bot token `\d{8,10}:[A-Za-z0-9_-]{35,}`, Claude OAuth `sk-(ant-oat01-)?[A-Za-z0-9_-]{20,}`, long hex `[a-f0-9]{32,}`)
- 16 bun-test specs (7 csrf + 4 engine + 3 redact + 1 shared-neutrality + token/cookie gen)

### Task 3 — NextAuth v5 Credentials(telegram) + Edge middleware (commit `0d56394`)

- `dashboard/lib/owner-gate.server.ts` + test — pure `isOwner(provided, ownerId)` with 4 specs (match / owner-null / mismatch / provided-null-or-empty)
- `dashboard/auth.config.ts` — Credentials provider `id: "telegram"`; `authorize()` reads `TELEGRAM_BOT_TOKEN` → `verifyTelegramWidget` → returns `{id, name}` or `null`. JWT session, 8h maxAge, `trustHost: true`
- `dashboard/auth.ts` — `signIn` reads OWNER.md via `readOwnerId()` and rejects via `isOwner()` (D-07); `jwt` stashes `telegramId`; `session` exposes `session.user.id`; session cookie switches between `__Secure-authjs.session-token` (prod) and `authjs.session-token` (dev), `secure` gated on `NODE_ENV`
- `dashboard/middleware.ts` — Edge-safe:
  1. DASHBOARD_TOKEN bypass (header `x-dashboard-token` or query `?token=`) via length-guarded XOR compare (T-13-16)
  2. Public paths (`/login`, `/403`, `/api/health`, `/api/auth/*`, static) pass through with security headers
  3. `getToken()` check → redirect to `/login` when missing (secureCookie + cookieName env-gated)
  4. Owner gate via `OWNER_TELEGRAM_ID` env (Edge can't touch fs) → redirect `/403` on mismatch
  5. Issues `an-csrf` double-submit cookie when absent (`secure` in prod only)
  6. Applies CSP (Telegram widget origins `https://telegram.org`, `https://t.me`, `https://oauth.telegram.org`), HSTS 2y preload, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
  7. No `node:fs` import; no `*.server.ts` import (Edge-safety asserted by grep)

## Must-Haves Verification

| Truth | Status | Evidence |
|-------|--------|----------|
| Telegram Login Widget HMAC check rejects forged / accepts valid payloads | PASS | 7 widget specs pass; cross-bot-token vector test confirms algorithmic correctness |
| `signIn` callback rejects non-owner Telegram IDs (Phase 11 contract) | PASS | auth.ts uses `isOwner(user.id, await readOwnerId())`; owner-gate tests cover null/mismatch branches |
| DASHBOARD_TOKEN in header or query bypasses redirect (constant-time) | PASS | middleware.ts lines 77-90, grep `x-dashboard-token` OK; XOR compare length-guarded |
| Middleware Edge-safe (no node:fs, no .server.ts imports) | PASS | `! grep node:fs middleware.ts` + `! grep \.server middleware.ts` both empty |
| Session cookie is `__Secure-authjs.session-token`, httpOnly + sameSite lax + secure, 8h maxAge | PASS | auth.ts cookies block + authConfig `maxAge: 60*60*8` |
| All mutation routes can reuse verifyCsrf / engineFetch | PASS | csrf.server.ts exports `verifyCsrf`, `CsrfError`; engine.server.ts exports `engineFetch` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Telegram-token regex missed fixtures with suffix length > 35**

- **Found during:** Task 2 GREEN run — the redact TG-token test expected `[REDACTED_TG_TOKEN]` but received original string.
- **Issue:** Plan text specified `\d{8,10}:[A-Za-z0-9_-]{35}` (exactly 35). Real Telegram bot tokens are exactly 35 chars after the colon, but test fixtures (and any future length drift) have longer suffixes; the `\b` anchor doesn't stop the engine at char 35 because chars 36+ are still word chars, so the `{35}` branch fails.
- **Fix:** Changed to `{35,}` to match 35-or-more. Still `\b`-anchored so random text isn't swept.
- **Files modified:** `dashboard/lib/redact.server.ts`
- **Commit:** `0f72c05` (Task 2)

**2. [Rule 2 — Missing critical] `_resetOwnerCache()` test-hook for cache isolation**

- **Found during:** Task 1 test authoring — the module-level cache makes test-order dependencies ugly.
- **Issue:** Without a reset hook, second test case inherits first case's cached value → flaky.
- **Fix:** Added exported `_resetOwnerCache()` (underscore-prefixed test-only per convention) and call it in `beforeEach`/`afterEach`. Clean test isolation; zero runtime impact.
- **Files modified:** `dashboard/lib/owner.server.ts`, `dashboard/lib/owner.server.test.ts`
- **Commit:** `9b25a70` (Task 1)

**3. [Rule 3 — Blocking] Session cookie name must be dev-gated**

- **Found during:** Middleware authoring — the plan hard-coded `__Secure-authjs.session-token`, but `__Secure-` cookies require HTTPS. Local dev (`bun run dev` on `http://127.0.0.1:8090`) would drop the cookie and every request would 302 to /login.
- **Issue:** Plan's verification criterion says `grep -q "__Secure-authjs.session-token" middleware.ts` — that literal string is present (in the prod branch), but naive prod-only would break `bun run dev`.
- **Fix:** Both auth.ts and middleware.ts pick cookie name + secure flag from `NODE_ENV === "production"`. Matches admin's pattern exactly. Acceptance grep still passes (string literal present).
- **Files modified:** `dashboard/auth.ts`, `dashboard/middleware.ts`
- **Commit:** `0d56394` (Task 3)

## TDD Gate Compliance

All three tasks followed RED → GREEN (no separate REFACTOR commit needed):

- Task 1: tests written first, `bun test` showed 5 fail / 1 error → implementation added → 15 pass
- Task 2: tests written first → 30 pass on first run, 1 fail (Rule 1 fix above) → 31 pass
- Task 3: 4 owner-gate tests written first → implementation added → 4 pass. Middleware is Edge (Playwright covers in Plan 04 per plan direction); heavy grep acceptance instead

Note: commits combined test + implementation per task (single atomic commit). `git log` shows only `feat()` gates, no standalone `test()` gate — plan-level `type: tdd` is not set (plan type is `execute`), so this is acceptable.

## Known Stubs

None. All primitives are fully wired and tested. Middleware's `OWNER_TELEGRAM_ID` env path is a stub for Phase 11's install-time OWNER.md → env export; documented in middleware comment and `~/hub/knowledge/animaya/OWNER.md` contract.

## Threat Flags

No new surface introduced beyond the threat model in 13-02-PLAN.md. T-13-10 through T-13-17 all mitigated (or accepted with documentation for T-13-16).

## Self-Check

Files verified (all FOUND):

- dashboard/lib/telegram-widget.server.ts, .test.ts
- dashboard/lib/dashboard-token.server.ts
- dashboard/lib/owner.server.ts, .test.ts
- dashboard/lib/owner-gate.server.ts, .test.ts
- dashboard/lib/csrf.shared.ts, csrf.server.ts, csrf-cookie.server.ts, csrf.server.test.ts
- dashboard/lib/engine.server.ts, .test.ts
- dashboard/lib/redact.server.ts, .test.ts
- dashboard/types/next-auth.d.ts
- dashboard/auth.config.ts
- dashboard/auth.ts
- dashboard/middleware.ts

Commits verified (animaya repo):

- FOUND: `9b25a70 feat(13-02): add Telegram widget HMAC + OWNER.md + dashboard-token primitives`
- FOUND: `0f72c05 feat(13-02): add CSRF + engine loopback + redact helpers`
- FOUND: `0d56394 feat(13-02): wire NextAuth v5 Telegram provider + Edge middleware (D-06, D-07)`

Verification commands (all pass):

- `bun test lib/` → 35 pass / 0 fail / 56 expect()
- `bunx tsc --noEmit` → exit 0
- `grep -rn 'hla-csrf' dashboard/` → no matches
- `grep 'node:fs' dashboard/middleware.ts` → no matches
- `grep '"next-auth": "5.0.0-beta.31"' dashboard/package.json` → match

## Self-Check: PASSED

## Commits

| # | Hash    | Message |
|---|---------|---------|
| 1 | 9b25a70 | `feat(13-02): add Telegram widget HMAC + OWNER.md + dashboard-token primitives` |
| 2 | 0f72c05 | `feat(13-02): add CSRF + engine loopback + redact helpers` |
| 3 | 0d56394 | `feat(13-02): wire NextAuth v5 Telegram provider + Edge middleware (D-06, D-07)` |
