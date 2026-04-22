---
phase: 14
plan: 03
subsystem: dashboard-auth
tags: [voidnet, middleware, session-mint, edge, next-auth]
requires:
  - 14-01
  - 14-02
provides:
  - voidnet-middleware-branch
  - synthetic-nextauth-session
affects:
  - dashboard/middleware.ts
  - dashboard/lib/voidnet-auth.server.ts
tech-stack:
  added: []
  patterns:
    - "next-auth/jwt encode() with cookie-name salt for synthetic session mint"
    - "Edge middleware third auth mode (DASHBOARD_TOKEN → voidnet HMAC → Telegram JWT)"
key-files:
  created: []
  modified:
    - dashboard/middleware.ts
    - dashboard/lib/voidnet-auth.server.ts
decisions:
  - "Voidnet branch placed AFTER DASHBOARD_TOKEN bypass and BEFORE PUBLIC_PATHS check, per SPEC precedence"
  - "encode() salt hardcoded to cookie name per isProd branch (Pitfall 1: salt must equal cookie name)"
  - "src: 'voidnet' field kept as debug-only marker; downstream MUST NOT branch on it"
  - "ESLint disable for `server-only/server-only` rule in voidnet-auth.server.ts — file runs in Edge runtime and cannot import server-only (Rule 3 blocking issue for Next build)"
metrics:
  duration: "~6 min"
  completed: "2026-04-22"
---

# Phase 14 Plan 03: Middleware voidnet branch + JWT mint Summary

Wired voidnet header verification into `dashboard/middleware.ts` as a third auth mode. Valid voidnet headers mint a synthetic NextAuth v5 session JWT in-process via `next-auth/jwt` `encode()` using `AUTH_SECRET` and a cookie-name-matched salt; the cookie is set on the response and the request passes through with `x-user-telegram-id` propagated. Invalid headers return fixed-shape `{error, code}` JSON (401 for schema/stale/sig, 403 for owner mismatch). Telegram and DASHBOARD_TOKEN paths are untouched.

## Insertion Layout (post-edit middleware.ts)

- Imports: lines 1–6 (added `encode`, `verifyVoidnetHeaders`, `VoidnetClaims`)
- `mintVoidnetSession` helper: lines 61–77 (module scope, below `applySecurityHeaders`)
- Voidnet branch: lines 120–159 (inside `middleware()`, after DASHBOARD_TOKEN bypass closes at line 117, before PUBLIC_PATHS block at line 161)
- All existing blocks (DASHBOARD_TOKEN bypass, public paths, Telegram `getToken`, owner gate, CSRF cookie, matcher) unchanged.

## Insertion Order Verification

`DASHBOARD_TOKEN bypass` → `VoidNet HMAC header auth` → `Public paths` → Telegram session gate — verified via grep; meets REQ-SPEC-03 precedence.

## E2E Pass Matrix

| # | Test | Result |
|---|------|--------|
| 1 | valid voidnet headers → session minted | PASS |
| 2 | tampered signature → 401 VOIDNET_SIG_INVALID | PASS |
| 3 | stale timestamp → 401 VOIDNET_STALE | PASS |
| 4 | owner mismatch → 403 VOIDNET_OWNER_MISMATCH | PASS |
| 5 | no voidnet headers → Telegram redirect unchanged | PASS |
| 6 | GET /api/integration/v1/meta valid sig → 200 | FAIL (expected — Plan 04) |
| 7 | GET /api/integration/v1/meta without sig → 401 | FAIL (expected — Plan 04) |

Plus: `auth.spec.ts` + `dashboard-token.spec.ts` all GREEN (no regressions). `bun test` 60/60 GREEN.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Next build blocked by `server-only/server-only` ESLint rule on `voidnet-auth.server.ts`**
- **Found during:** Task 1 verification (`bun run build` required for Playwright webServer)
- **Issue:** Next.js lint rule forces files with `.server` suffix to `import "server-only"`, but `voidnet-auth.server.ts` runs in the Edge runtime where `server-only` throws at module eval. Plan 02 chose the `.server` suffix to block client bundling; the lint rule is incompatible with Edge usage.
- **Fix:** Added file-level `/* eslint-disable server-only/server-only */` with a comment explaining the Edge runtime constraint. Did not rename the file (would ripple into Plan 02's artifact contract and Plan 04's import path).
- **Files modified:** `dashboard/lib/voidnet-auth.server.ts` (comment + disable directive only; no behavior change)
- **Commit:** de6fb52

## Auth Gates

None.

## Threat Flags

None — voidnet branch surface is the target of this plan's threat model (T-14-01 through T-14-07); no new surface outside model introduced.

## Self-Check: PASSED

- FOUND: dashboard/middleware.ts (voidnet branch present)
- FOUND: dashboard/lib/voidnet-auth.server.ts (eslint-disable directive present)
- FOUND: commit de6fb52 in git log
- All acceptance greps pass; 5/7 voidnet E2E GREEN, 60/60 bun tests GREEN, auth + dashboard-token E2E GREEN.
