---
phase: 14
plan: 02
subsystem: dashboard-auth
tags: [voidnet, auth, verifier, edge, hmac, wave-1]
requires:
  - 14-01 (RED unit tests)
provides:
  - Edge-safe voidnet header verifier (verifyVoidnetHeaders)
  - Shared edgeConstantTimeEqual helper (lib/ct-compare)
affects:
  - dashboard/lib/
  - dashboard/middleware.ts
tech-stack:
  added: []
  patterns: [WebCrypto HMAC-SHA256 via crypto.subtle, constant-time hex compare]
key-files:
  created:
    - dashboard/lib/voidnet-auth.server.ts
    - dashboard/lib/ct-compare.ts
  modified:
    - dashboard/middleware.ts
decisions:
  - Check order locked as schema -> replay -> HMAC -> owner so malformed-schema requests cannot reach owner comparison
  - Owner gate fails closed when OWNER_TELEGRAM_ID env is unset (`!ownerTelegramId` branch returns 403 VOIDNET_OWNER_MISMATCH)
  - Verifier returns generic error strings only; never echoes header values or computed HMAC (T-14-04 mitigation)
metrics:
  tasks: 2
  completed_date: 2026-04-22
requirements: [REQ-SPEC-01, REQ-SPEC-02, REQ-SPEC-05]
---

# Phase 14 Plan 02: Wave 1 Verifier Impl + ct-compare Factoring Summary

One-liner: Edge-safe HMAC-SHA256 verifier for X-Voidnet-* headers, implemented with `crypto.subtle`, reusing a factored constant-time compare helper; flips all 14 Plan 01 RED unit tests to GREEN without touching the Node runtime.

## Files Created

- `dashboard/lib/ct-compare.ts` — 12 lines. Exports `edgeConstantTimeEqual(a, b)`. Length-guarded XOR loop; shared between middleware (DASHBOARD_TOKEN bypass) and the new voidnet verifier.
- `dashboard/lib/voidnet-auth.server.ts` — 98 lines. Exports `verifyVoidnetHeaders`, `VoidnetClaims`, `VerifyResult`. Pure function: no I/O, no module state, no `server-only`, no `node:crypto`. Uses `crypto.subtle.importKey` + `crypto.subtle.sign` for HMAC-SHA256, returns hex lowercase.

## Files Modified

- `dashboard/middleware.ts` — Removed inline `edgeConstantTimeEqual` block (lines 55-69 in original). Added `import { edgeConstantTimeEqual } from "@/lib/ct-compare"`. DASHBOARD_TOKEN bypass at line 91 unchanged.

## Verification Results

- `bun test lib/voidnet-auth.server.test.ts`: **14 pass / 0 fail / 32 expect()** — all Plan 01 RED tests GREEN.
- `bun test` (full suite): **60 pass / 0 fail / 110 expect()** across 9 files. No regressions from ct-compare factoring.
- `grep -n 'server-only\|node:crypto' dashboard/lib/voidnet-auth.server.ts`: only matches are doc comments forbidding them; no actual imports. Edge-safe confirmed.
- `grep -c 'VOIDNET_SCHEMA\|VOIDNET_STALE\|VOIDNET_SIG_INVALID\|VOIDNET_OWNER_MISMATCH'`: 8 (each code appears in constant string + fail() call — 4 distinct codes × 2 occurrences).
- Canonical message format `${userId}|${handle}|${telegramId}|${ts}` present verbatim.
- `import { edgeConstantTimeEqual } from "@/lib/ct-compare"` present in both middleware.ts and voidnet-auth.server.ts.

## Threat Mitigation Applied

| Threat ID | Mitigation | Evidence |
|-----------|------------|----------|
| T-14-01 (replay) | ±60s window check returns VOIDNET_STALE | Lines 78-80 of voidnet-auth.server.ts |
| T-14-02 (forged HMAC) | crypto.subtle HMAC-SHA256 + constant-time compare | Lines 83-89 |
| T-14-03 (owner spoof) | Owner check runs AFTER sig verify; fail-closed on unset env | Lines 91-92 |
| T-14-04 (error leak) | Fixed generic error strings; never echo headers/HMACs; never throws | fail() helper, Lines 30-32 |
| T-14-08 (timing) | edgeConstantTimeEqual XOR loop; hex length uniform via HEX64_RE | ct-compare.ts |

## Deviations from Plan

None — plan executed exactly as written. Skeleton in the plan's `<action>` block was adopted verbatim with only documentation comments added.

## Commits

- `b0f5959` refactor(14-02): factor edgeConstantTimeEqual into lib/ct-compare
- `d3b42ce` feat(14-02): implement Edge-safe voidnet header verifier

## Threat Flags

None — this plan adds a pure verifier module with no new network surface, no I/O, no schema changes. All new trust-boundary logic was explicitly modeled in the plan's threat_model (T-14-01..04, T-14-08).

## Self-Check: PASSED

- FOUND: dashboard/lib/ct-compare.ts
- FOUND: dashboard/lib/voidnet-auth.server.ts
- FOUND: commit b0f5959 (refactor)
- FOUND: commit d3b42ce (feat)
- FOUND: 14/14 unit tests GREEN for voidnet-auth.server.test.ts
- FOUND: 60/60 full bun test suite GREEN
- CONFIRMED: zero `server-only` or `node:crypto` imports in voidnet-auth.server.ts
