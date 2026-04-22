---
phase: 14
plan: 01
subsystem: dashboard-auth
tags: [voidnet, auth, hmac, edge, test-fixtures, wave-0]
requires: []
provides:
  - voidnet verifier unit-test contract (RED until Plan 02)
  - next-auth/jwt encode/decode smoke (GREEN — locks A1/A3)
  - voidnet E2E spec + signer helper (RED until Plan 03)
  - playwright webServer env: VOIDNET_HMAC_SECRET=test-voidnet-secret
affects:
  - dashboard/lib/
  - dashboard/tests/e2e/
  - dashboard/playwright.config.ts
tech-stack:
  added: []
  patterns: [bun:test HMAC signer, Playwright extraHTTPHeaders, next-auth/jwt encode/decode]
key-files:
  created:
    - dashboard/lib/voidnet-auth.server.test.ts
    - dashboard/lib/voidnet-jwt-roundtrip.test.ts
    - dashboard/tests/e2e/_voidnet-helpers.ts
    - dashboard/tests/e2e/voidnet.spec.ts
  modified:
    - dashboard/playwright.config.ts
decisions:
  - Canonical HMAC message locked as `${userId}|${handle}|${telegramId}|${timestamp}` via hand-verified vector in unit tests
  - Auth.js v5 decode() throws on salt mismatch (not null-return); Pitfall 1 guard accepts either throw or null
  - OWNER=111111 mirrored from existing playwright.config.ts webServer.env (no new value introduced)
metrics:
  tasks: 3
  completed_date: 2026-04-22
---

# Phase 14 Plan 01: Wave 0 Test Fixtures + JWT Roundtrip Smoke Summary

One-liner: Establishes failing unit + E2E test contract and a GREEN next-auth/jwt
interop smoke so Waves 1-3 implementations cannot drift from spec on canonical
HMAC message, error codes, ±60s replay window, or Auth.js session-cookie salt.

## Files Created

- `dashboard/lib/voidnet-auth.server.test.ts` — 14 RED unit tests covering VOIDNET_SCHEMA (6 sub-cases), VOIDNET_STALE (±61s reject, ±59s accept), VOIDNET_SIG_INVALID, VOIDNET_OWNER_MISMATCH, and a canonical-vector lock test.
- `dashboard/lib/voidnet-jwt-roundtrip.test.ts` — 2 GREEN tests locking A1/A3 (next-auth/jwt encode+decode roundtrip preserves sub/telegramId/name under matching salt; mismatched salt cannot decrypt).
- `dashboard/tests/e2e/_voidnet-helpers.ts` — `voidnetHeaders({telegramId?, tamper?, offset?})` Playwright signer helper, SECRET + OWNER constants mirror playwright.config.ts.
- `dashboard/tests/e2e/voidnet.spec.ts` — 7 RED Playwright cases covering REQ-3 (valid + tampered + fallback), REQ-5 (owner mismatch 403), REQ-7 (meta auth + shape).

## Files Modified

- `dashboard/playwright.config.ts` — added `VOIDNET_HMAC_SECRET: "test-voidnet-secret"` to `webServer.env`. Existing `OWNER_TELEGRAM_ID: "111111"` preserved.

## JWT Roundtrip Smoke Result

GREEN. `bun test lib/voidnet-jwt-roundtrip.test.ts` → 2 pass / 0 fail / 6 expect calls.

Implication: Plan 02 can rely on `next-auth/jwt` `encode()` with `salt` matching
the session-cookie name (`__Secure-authjs.session-token` prod / `authjs.session-token`
dev). No fallback to direct `jose` needed.

## Unit Tests RED (expected)

`bun test lib/voidnet-auth.server.test.ts` → `Cannot find module './voidnet-auth.server'`.
All 14 tests in `verifyVoidnetHeaders` describe block report RED with "Unhandled
error between tests" because the verifier module doesn't exist yet. This is the
Wave 0 signal per RESEARCH.md — Plan 02 creates `voidnet-auth.server.ts` and
tests flip GREEN.

## E2E Spec Status

7 cases created but not yet runnable to GREEN. `bunx playwright test voidnet`
will fail because middleware voidnet path ships in Plan 03. `VOIDNET_HMAC_SECRET`
is live in webServer env so Plan 03 can exercise the full middleware path
without further config changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Test bug] JWT salt-mismatch test expected null but Auth.js v5 throws**

- **Found during:** Task 2 initial run (1 pass / 1 fail).
- **Issue:** `next-auth/jwt` `decode()` throws `JWEDecryptionFailed` when salts
  differ rather than returning null. Plan text specified `expect(decoded).toBeNull()`.
- **Fix:** Changed the Pitfall 1 guard to accept either a throw OR a null return —
  both prove "wrong salt cannot decrypt". Still fully validates Pitfall 1
  (mismatched salt produces no usable session).
- **Files modified:** `dashboard/lib/voidnet-jwt-roundtrip.test.ts`
- **Commit:** 8ec9fe4

## Commits

- `edf12b1` test(14-01): add voidnet verifier unit test scaffold (RED)
- `8ec9fe4` test(14-01): add next-auth/jwt encode/decode roundtrip smoke
- (Task 3 commit — see git log) test(14-01): add voidnet E2E spec + signer helper + playwright env

## Threat Flags

None — this plan only creates tests and injects a test-only secret into
Playwright's webServer env. No new network endpoints, auth paths, or schema
changes. Secret is fixture-only and never committed as a real secret.

## Self-Check: PASSED

- FOUND: dashboard/lib/voidnet-auth.server.test.ts
- FOUND: dashboard/lib/voidnet-jwt-roundtrip.test.ts
- FOUND: dashboard/tests/e2e/_voidnet-helpers.ts
- FOUND: dashboard/tests/e2e/voidnet.spec.ts
- FOUND: commit edf12b1, 8ec9fe4, and Task 3 commit in git log
- VOIDNET_HMAC_SECRET present in dashboard/playwright.config.ts
- OWNER_TELEGRAM_ID (111111) matches OWNER constant in _voidnet-helpers.ts
