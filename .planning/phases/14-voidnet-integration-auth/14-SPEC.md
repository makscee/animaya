# Phase 14: VoidNet Integration Auth — Specification

**Created:** 2026-04-22
**Ambiguity score:** 0.10
**Requirements:** 8 locked

## Goal

Animaya's Next.js dashboard accepts HMAC-signed voidnet-proxy headers as a first-class auth mode, synthesizing a NextAuth session without showing the Telegram login widget — while standalone deploys (no `VOIDNET_HMAC_SECRET`) continue to use the existing Telegram + DASHBOARD_TOKEN flow unchanged.

## Background

`dashboard/middleware.ts` currently gates traffic through a Telegram Login Widget + `OWNER_TELEGRAM_ID` owner gate, with `DASHBOARD_TOKEN` as a bypass path for deploy scripts. voidnet-api proxies `animaya.makscee.ru/*` → `lxc_ip:8090/*` over Tailscale (Animaya LXCs are NAT'd, no direct browser access). voidnet holds the user session and cannot share cookies across domains, so a new server-to-server auth carrier is required. No voidnet auth code, no `/api/integration/v1/*` endpoints, and no `VOIDNET_HMAC_SECRET` handling exist today.

## Requirements

1. **HMAC header verification**: Dashboard validates signed voidnet headers on every proxied request.
   - Current: No voidnet-auth module exists in `dashboard/lib/`
   - Target: `dashboard/lib/voidnet-auth.server.ts` exposes a pure verifier that parses `X-Voidnet-User-Id`, `X-Voidnet-Handle`, `X-Voidnet-Telegram-Id`, `X-Voidnet-Timestamp`, `X-Voidnet-Signature`, computes `hmac_sha256(VOIDNET_HMAC_SECRET, "{user_id}|{handle}|{telegram_id}|{timestamp}")`, and returns validated claims or an error
   - Acceptance: Unit test with known secret + headers returns parsed claims on match; tampered signature returns error; malformed `X-Voidnet-Handle` (not `[a-z][a-z0-9-]+`, not 3–32 chars) returns error

2. **Timestamp replay window**: Verifier rejects stale or future-dated requests.
   - Current: No timestamp enforcement
   - Target: Requests with `|now - X-Voidnet-Timestamp| > 60s` are rejected
   - Acceptance: Unit test with timestamp 61s in past → error; 61s in future → error; ±59s → accepted

3. **Middleware integration**: Voidnet check runs before Telegram gate in `dashboard/middleware.ts`.
   - Current: Middleware has only Telegram session + `DASHBOARD_TOKEN` paths
   - Target: Middleware checks voidnet headers first. Valid → inject synthetic session claims so `auth()` / `getServerSession()` sees a real user. Headers present but invalid → 401 JSON. Headers absent → fall through to existing Telegram logic
   - Acceptance: E2E with valid headers → request passes, no Telegram redirect; E2E with tampered signature → 401 JSON `{error, code}`; E2E with no voidnet headers → Telegram flow unchanged

4. **NextAuth session synthesis**: Voidnet claims produce a JWT equivalent to Telegram-login session.
   - Current: `dashboard/auth.config.ts` only has Telegram credentials provider
   - Target: Custom `jwt()` callback (or `"voidnet"` credentials provider) turns voidnet claims into a NextAuth JWT with the same shape Telegram login produces for that `telegram_id`. Downstream code must not branch on auth source
   - Acceptance: Integration test: request with voidnet headers → `auth()` returns session with `telegram_id` matching `X-Voidnet-Telegram-Id`, same field shape as Telegram session

5. **Owner invariant enforcement**: `X-Voidnet-Telegram-Id` must equal `OWNER_TELEGRAM_ID`.
   - Current: Owner gate only checks Telegram widget payload
   - Target: If validated voidnet telegram_id ≠ `OWNER_TELEGRAM_ID` env → 403 JSON with explicit reason. No silent fallback to Telegram flow
   - Acceptance: E2E with valid signature but mismatched telegram_id → 403 JSON `{error: "owner mismatch", code}`

6. **Activation on env presence**: `VOIDNET_HMAC_SECRET` unset = standalone mode.
   - Current: No env var checked for voidnet
   - Target: If `VOIDNET_HMAC_SECRET` is unset/empty → voidnet path is skipped entirely; existing Telegram flow runs unchanged (backward compat). If set → voidnet path is active
   - Acceptance: Unit/E2E with secret unset → voidnet headers ignored, Telegram widget still shown; with secret set → voidnet headers enforced

7. **Integration meta endpoint**: voidnet can probe dashboard version + capabilities.
   - Current: No `/api/integration/v1/*` route exists
   - Target: `GET /api/integration/v1/meta` returns `{version, supported_auth_modes: ["telegram","voidnet"], dashboard_port: 8090}`. Requires valid voidnet HMAC headers (not public)
   - Acceptance: Request with valid voidnet signature → 200 JSON with three fields; request without valid signature → 401

8. **Env contract documented**: New env vars recorded in dashboard docs.
   - Current: `VOIDNET_HMAC_SECRET` not documented anywhere
   - Target: `dashboard/DASHBOARD.md` (or `README.md`) documents `VOIDNET_HMAC_SECRET` purpose + the `OWNER_TELEGRAM_ID` pairing invariant
   - Acceptance: Grep of the dashboard doc returns both env names with purpose lines

## Boundaries

**In scope:**
- `dashboard/lib/voidnet-auth.server.ts` — signature + timestamp + claims verifier
- `dashboard/middleware.ts` — voidnet path before Telegram gate
- `dashboard/auth.config.ts` — JWT synthesis from voidnet claims
- `dashboard/app/api/integration/v1/meta/route.ts` — version probe endpoint
- Dashboard doc update for `VOIDNET_HMAC_SECRET` + owner pairing
- Unit tests (verifier) and E2E tests (middleware paths)

**Out of scope:**
- Python bot changes — this phase is dashboard-only; bot does not speak voidnet
- Bridge or module changes — auth is orthogonal to bridge/module surfaces
- DB schema changes — session synthesis is stateless, no schema impact
- HMAC secret rotation (accept current + previous) — deferred; single secret only, brief downtime acceptable on rotation (decision locked round 1)
- `POST /api/integration/v1/update` self-update webhook — moved to Phase 15 per CONTEXT
- OIDC / cookie-domain sharing — CONTEXT explicitly rejects these for this phase
- Reusing `DASHBOARD_TOKEN` for interactive voidnet traffic — CONTEXT rejects (disables NextAuth session subtly)

## Constraints

- HMAC implementation must work in the runtime the existing `middleware.ts` uses. If middleware runs on Edge, verification uses `crypto.subtle`; if Node, `node:crypto`. Planner confirms runtime before coding
- Signature format fixed: `hmac_sha256(secret, "{user_id}|{handle}|{telegram_id}|{timestamp}")` with hex output — do not change field order or separator
- Header names fixed (cross-service contract): `X-Voidnet-User-Id`, `X-Voidnet-Handle`, `X-Voidnet-Telegram-Id`, `X-Voidnet-Timestamp`, `X-Voidnet-Signature`
- Replay window fixed at ±60 seconds
- `X-Voidnet-Handle` validation: 3–32 chars, regex `^[a-z][a-z0-9-]+$`
- Error responses on voidnet failures use JSON shape `{error, code}` matching existing `/api` error convention (decision locked round 1)
- All existing dashboard tests must continue to pass

## Acceptance Criteria

- [ ] `dashboard/lib/voidnet-auth.server.ts` exists and exports a pure verifier; unit tests cover valid sig, tampered sig, bad handle, timestamp out-of-window
- [ ] With `VOIDNET_HMAC_SECRET` set + valid signed headers, dashboard loads without Telegram widget
- [ ] With `VOIDNET_HMAC_SECRET` set + invalid signature → 401 JSON `{error, code}`
- [ ] With `VOIDNET_HMAC_SECRET` set + expired timestamp (>±60s) → 401 JSON `{error, code}`
- [ ] With `VOIDNET_HMAC_SECRET` set + valid sig but `X-Voidnet-Telegram-Id` ≠ `OWNER_TELEGRAM_ID` → 403 JSON
- [ ] With `VOIDNET_HMAC_SECRET` unset → Telegram widget + `OWNER_TELEGRAM_ID` flow behaves identically to pre-phase
- [ ] `auth()` / `getServerSession()` returns session with same field shape whether auth source is Telegram or voidnet
- [ ] `GET /api/integration/v1/meta` with valid voidnet signature → 200 `{version, supported_auth_modes: ["telegram","voidnet"], dashboard_port: 8090}`
- [ ] `GET /api/integration/v1/meta` without valid signature → 401
- [ ] `VOIDNET_HMAC_SECRET` and `OWNER_TELEGRAM_ID` pairing documented in `dashboard/DASHBOARD.md` or `README.md`
- [ ] All existing dashboard unit + E2E tests pass

## Ambiguity Report

| Dimension          | Score | Min  | Status | Notes                                                   |
|--------------------|-------|------|--------|---------------------------------------------------------|
| Goal Clarity       | 0.92  | 0.75 | ✓      | Outcome precise, backward compat explicit               |
| Boundary Clarity   | 0.92  | 0.70 | ✓      | In/out-of-scope both explicit, adjacent phases noted    |
| Constraint Clarity | 0.88  | 0.65 | ✓      | Headers, sig format, window, handle regex all locked    |
| Acceptance Criteria| 0.88  | 0.70 | ✓      | 11 pass/fail criteria covering every requirement        |
| **Ambiguity**      | 0.10  | ≤0.20| ✓      |                                                         |

## Interview Log

| Round | Perspective    | Question summary                            | Decision locked                                    |
|-------|----------------|---------------------------------------------|----------------------------------------------------|
| 0     | Researcher     | Initial scout of CONTEXT.md + middleware    | CONTEXT pre-locks headers/sig/replay/activation    |
| 1     | Seed Closer    | HMAC rotation support?                      | Single secret only; rotation deferred              |
| 1     | Seed Closer    | Error body shape on voidnet failure?        | JSON `{error, code}` matching existing convention  |
| 1     | Seed Closer    | `/api/integration/v1/meta` auth?            | Require voidnet HMAC (not public)                  |

---

*Phase: 14-voidnet-integration-auth*
*Spec created: 2026-04-22*
*Next step: /gsd-discuss-phase 14 — implementation decisions (Edge vs Node runtime for HMAC, session shape details, test harness)*
