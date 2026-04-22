---
phase: 14
plan: 04
subsystem: dashboard-auth
tags: [voidnet, meta-endpoint, docs, middleware]
requires:
  - 14-03
provides:
  - integration-v1-meta-endpoint
  - dashboard-env-contract-doc
affects:
  - dashboard/app/api/integration/v1/meta/route.ts
  - dashboard/middleware.ts
  - dashboard/DASHBOARD.md
tech-stack:
  added: []
  patterns:
    - "Next.js App Router route handler reading package.json via node:fs (bundler-safe fallback for JSON imports)"
    - "Scoped JSON 401/403 branch in Edge middleware for /api/integration/v1/* (API semantics over browser redirect)"
key-files:
  created:
    - dashboard/app/api/integration/v1/meta/route.ts
    - dashboard/DASHBOARD.md
  modified:
    - dashboard/middleware.ts
decisions:
  - "Used fs.readFileSync(package.json) instead of import-with-assertion for version read — compatible across bundler configs and nodejs runtime"
  - "Handler contains no auth logic; middleware is the sole gate (matches RESEARCH.md Meta endpoint guidance)"
  - "JSON 401/403 branch scoped to exact prefix /api/integration/v1/ — other API routes and all page routes retain existing /login redirect behavior (zero regression)"
metrics:
  duration: "~4 min"
  completed: "2026-04-22"
---

# Phase 14 Plan 04: Meta endpoint + DASHBOARD.md env contract Summary

Shipped `GET /api/integration/v1/meta` returning the locked shape
`{version, supported_auth_modes:["telegram","voidnet"], dashboard_port:8090}`
and added `dashboard/DASHBOARD.md` documenting the voidnet env contract
(`VOIDNET_HMAC_SECRET` + `OWNER_TELEGRAM_ID` pairing invariant + signed
request contract). Middleware was tweaked so integration paths emit JSON
401/403 instead of browser redirects when unauthenticated, closing the last
two E2E tests (6 and 7).

## Meta Route

- Path: `dashboard/app/api/integration/v1/meta/route.ts`
- Runtime: `nodejs`
- Auth: none in handler — middleware voidnet branch (or DASHBOARD_TOKEN, or
  Telegram session with owner match) gates the request upstream.
- Version read: `readFileSync(process.cwd()/package.json)`. No
  import-assertion fallback was needed — chose fs at authoring time to avoid
  any bundler variance; build verified clean.

## Middleware Scoped JSON 401/403

- Telegram session gate `if (!token)` — added `if (pathname.startsWith("/api/integration/v1/"))` branch returning `NextResponse.json({error:"unauthorized",code:"NO_SESSION"},{status:401})`.
- Owner gate `if (!isOwnerTelegramIdEdge(...))` — same prefix branch returning `{error:"forbidden",code:"NOT_OWNER"}` 403.
- All other paths: unchanged `/login` and `/403` redirects.

## DASHBOARD.md Contents

- `# Dashboard` top-level header.
- `## Environment` section covering AUTH_SECRET, OWNER_TELEGRAM_ID, NEXT_PUBLIC_TELEGRAM_BOT_USERNAME, DASHBOARD_TOKEN, DASHBOARD_PORT.
- `## Environment: voidnet integration` with three subsections:
  - `### VOIDNET_HMAC_SECRET` — activation semantics + backward compat note.
  - `### OWNER_TELEGRAM_ID pairing invariant` — pairing rule + `VOIDNET_OWNER_MISMATCH` reject on mismatch.
  - `### Signed request contract` — headers, signature formula, replay window, error codes.

Grep verification:
- `grep -q VOIDNET_HMAC_SECRET dashboard/DASHBOARD.md` → PASS
- `grep -q OWNER_TELEGRAM_ID dashboard/DASHBOARD.md` → PASS
- `grep -q 'pairing' dashboard/DASHBOARD.md` → PASS

## E2E Pass Matrix (final)

| # | Test | Result |
|---|------|--------|
| 1 | valid voidnet headers → session minted | PASS |
| 2 | tampered signature → 401 VOIDNET_SIG_INVALID | PASS |
| 3 | stale timestamp → 401 VOIDNET_STALE | PASS |
| 4 | owner mismatch → 403 VOIDNET_OWNER_MISMATCH | PASS |
| 5 | no voidnet headers → Telegram redirect unchanged | PASS |
| 6 | GET /api/integration/v1/meta valid sig → 200 shape | PASS |
| 7 | GET /api/integration/v1/meta without sig → 401 | PASS |

**Full suite:** 21/21 Playwright GREEN, 60/60 `bun test` GREEN.

## Per-Task Validation Map

| Task ID | Description | Artifact | Status |
|---------|-------------|----------|--------|
| 14-01-1..3 | Voidnet helpers + E2E scaffold | Plans 01 commits | PASS |
| 14-02-1..2 | voidnet-auth.server.ts (HMAC verify) | Plan 02 commits | PASS |
| 14-03-1   | middleware voidnet branch + JWT mint | Plan 03 commit de6fb52 | PASS |
| 14-04-1   | /api/integration/v1/meta route handler | commit ede4181 | PASS |
| 14-04-2   | middleware JSON 401/403 + DASHBOARD.md | commit b2e8bac | PASS |

## Deviations from Plan

None. The Task 1 action spec allowed a fallback to `readFileSync` if the
JSON-import-assertion syntax failed; I chose the fallback pre-emptively (not
a deviation — the plan explicitly authorized either form, and the fs approach
avoids any bundler-specific risk).

## Auth Gates

None.

## Threat Flags

None — all surface introduced is covered by the plan's threat model
(T-14-04, T-14-09, T-14-10, T-14-11).

## Self-Check: PASSED

- FOUND: dashboard/app/api/integration/v1/meta/route.ts
- FOUND: dashboard/DASHBOARD.md
- FOUND: commit ede4181 (Task 1)
- FOUND: commit b2e8bac (Task 2)
- All acceptance criteria pass; 7/7 voidnet E2E GREEN; 21/21 Playwright GREEN; 60/60 bun test GREEN.
- 14-VALIDATION.md frontmatter updated: `status: complete`, `nyquist_compliant: true`, `wave_0_complete: true`.
