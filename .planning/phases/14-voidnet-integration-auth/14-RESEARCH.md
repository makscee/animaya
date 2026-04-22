# Phase 14: VoidNet Integration Auth — Research

**Researched:** 2026-04-22
**Domain:** Next.js middleware, NextAuth v5 (beta.31), Edge runtime WebCrypto HMAC
**Confidence:** HIGH

## Summary

This is a middleware-only phase that adds a third auth carrier (HMAC-signed voidnet headers) to `dashboard/middleware.ts` alongside the existing Telegram-widget/JWT and `DASHBOARD_TOKEN` paths. Every architectural decision is already locked in CONTEXT.md (headers, signature format, replay window, activation semantics, error shape). Research therefore focused on mechanics: (1) which runtime `middleware.ts` executes in, (2) the idiomatic NextAuth v5 pattern for materialising a session from a middleware-attested claim, and (3) the concrete WebCrypto HMAC shape.

**Primary recommendation:** Stay on the Edge runtime. Verify HMAC with `crypto.subtle` in a dedicated `dashboard/lib/voidnet-auth.edge.ts` (Edge-safe, no `server-only`). Skip the NextAuth `signIn` round-trip entirely — on valid voidnet headers, middleware mints a NextAuth JWT in-process using `encode()` from `next-auth/jwt`, sets the session cookie on the response, and forwards the request. Downstream `auth()` / `getToken()` sees a normal session with the same `{telegramId, sub}` shape Telegram-login produces. No changes to `auth.config.ts` credentials providers needed — the synthetic JWT is signed with `AUTH_SECRET` so Auth.js accepts it natively.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Auth carrier:** HMAC-signed request headers injected by voidnet-api on every proxied request. No OAuth round-trip, no browser cookies involving Animaya.
- **Headers:** `X-Voidnet-User-Id` (i64), `X-Voidnet-Handle` (3–32 chars, `^[a-z][a-z0-9-]+$`), `X-Voidnet-Telegram-Id` (i64, must equal `OWNER_TELEGRAM_ID`), `X-Voidnet-Timestamp` (unix-seconds), `X-Voidnet-Signature` (hex HMAC-SHA256).
- **Signature formula:** `hmac_sha256(VOIDNET_HMAC_SECRET, "{user_id}|{handle}|{telegram_id}|{timestamp}")` hex-encoded. Field order and separator fixed.
- **Replay window:** ±60 seconds.
- **Activation:** `VOIDNET_HMAC_SECRET` env presence toggles voidnet mode; unset = legacy Telegram flow unchanged.
- **Owner invariant:** validated `X-Voidnet-Telegram-Id` must equal `OWNER_TELEGRAM_ID`; mismatch → 403, no silent fallback.
- **Session shape:** NextAuth JWT identical to Telegram-login output for that `telegram_id` (same fields — `telegramId`, `sub`, `name`).
- **Error body:** JSON `{error, code}` matching existing `/api` convention.
- **`/api/integration/v1/meta` auth:** requires valid voidnet HMAC (not public).
- **Single secret only** — rotation deferred (brief downtime acceptable).
- **SSE/streaming:** voidnet-api re-injects headers per request; verifier runs on every request; no persistence issue.

### Claude's Discretion
- Choice between custom credentials-provider vs direct JWT encode in middleware (both valid per NextAuth v5 docs).
- Placement of verifier module (`dashboard/lib/voidnet-auth.*.ts`) — Edge-friendly suffix optional.
- Test strategy for Edge runtime (bun:test vs node:test vs Playwright for middleware).
- Internal structure of error codes (`VOIDNET_SIG_INVALID`, `VOIDNET_STALE`, etc.).

### Deferred Ideas (OUT OF SCOPE)
- HMAC secret rotation (accept current + previous).
- `POST /api/integration/v1/update` self-update webhook (Phase 15).
- OIDC / cookie-domain sharing.
- Reusing `DASHBOARD_TOKEN` for interactive voidnet traffic.
- Python bot, bridge, module, or DB schema changes.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| REQ-1 | HMAC header verification in `dashboard/lib/voidnet-auth.server.ts` | Edge WebCrypto `crypto.subtle.importKey` + `sign`/`verify` pattern documented below |
| REQ-2 | ±60 s timestamp replay window | Trivial in Edge: `Math.abs(nowSec - tsSec) > 60` |
| REQ-3 | Middleware integration before Telegram gate | Current `middleware.ts` (Edge) already gates on token; insert voidnet branch after DASHBOARD_TOKEN bypass |
| REQ-4 | Synthesise NextAuth session from voidnet claims | Mint JWT via `next-auth/jwt` `encode()` with same `telegramId` field as Telegram `jwt()` callback; set session cookie on response |
| REQ-5 | Owner invariant enforcement | Compare validated `X-Voidnet-Telegram-Id` to `process.env.OWNER_TELEGRAM_ID` (same Edge env read as existing `isOwnerTelegramIdEdge`) |
| REQ-6 | `VOIDNET_HMAC_SECRET` presence activates mode | Env guard at top of voidnet branch |
| REQ-7 | `GET /api/integration/v1/meta` route | New `app/api/integration/v1/meta/route.ts`; middleware matcher already covers `/api/*` |
| REQ-8 | Document env contract | Append section to `dashboard/DASHBOARD.md` or `README.md` |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HMAC verification | Edge middleware (Next.js) | — | Must run before any page/route handler; no Node-only APIs needed |
| Replay window check | Edge middleware | — | Pure comparison; shared with verifier module |
| Session minting | Edge middleware | Auth.js JWT module | `next-auth/jwt` `encode()` is Edge-compatible (same one `getToken` decodes) |
| Owner enforcement | Edge middleware | Node (`auth.ts` signIn callback for Telegram path) | Voidnet path stays in Edge; Telegram path keeps Node `signIn` gate unchanged |
| Integration meta endpoint | Route Handler (Edge or Node, either works) | — | Middleware enforces auth; handler only reads env + returns JSON |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `next` | 15.5.15 [VERIFIED: dashboard/package.json] | Middleware + App Router host | Already in project |
| `next-auth` | 5.0.0-beta.31 [VERIFIED: dashboard/package.json] | Session JWT encode/decode, credentials provider | Already in project; `getToken` already used in middleware |
| `@auth/core` | ^0.34.3 [VERIFIED: dashboard/package.json] | Underlying auth primitives | Transitive; no direct use expected |
| WebCrypto `crypto.subtle` | runtime [VERIFIED: Edge runtime docs CITED: https://nextjs.org/docs/app/api-reference/edge] | HMAC-SHA256 sign/verify | The only HMAC option in Edge runtime; project already uses `crypto.getRandomValues` in middleware |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `zod` | ^4.3.6 [VERIFIED: dashboard/package.json] | Header-shape validation (handle regex, numeric id) | Optional — regex + `Number.isFinite` also sufficient |
| `bun:test` | built-in [VERIFIED: `"test": "bun test"` in package.json] | Unit tests for verifier | Matches existing `lib/*.server.test.ts` pattern |
| `@playwright/test` | ^1.59.1 [VERIFIED: dashboard/package.json] | E2E tests for middleware paths | Matches existing `tests/e2e/auth.spec.ts` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `crypto.subtle` | `node:crypto` | Requires moving middleware to `runtime: "nodejs"`; slower cold-start and breaks current Edge matcher — reject |
| Credentials provider `"voidnet"` with `authorize()` reading headers | Direct `encode()` in middleware | Provider would require a POST to `/api/auth/callback/credentials` per request — defeats the zero-round-trip contract in CONTEXT. Direct encode is idiomatic per v5 migration docs which explicitly support stateless JWT pre-minting [CITED: authjs.dev migrating-to-v5] |
| Per-request `jose` library | `next-auth/jwt` `encode`/`decode` | `next-auth/jwt` already wraps `jose` with Auth.js cookie defaults — identical result, zero new deps |

**Installation:** No new runtime deps. (`zod` already present if we want schema validation.)

**Version verification:** `next-auth@5.0.0-beta.31` is current beta line; stable v5 has not yet shipped as of 2026-04. `next@15.5.15` is the active Next.js 15 series. [ASSUMED — not re-verified against npm registry in this session; package.json is the ground truth for this project.]

## Architecture Patterns

### System Architecture Diagram

```
                            voidnet-api (Tailscale)
                                     │
                                     │ injects X-Voidnet-* headers
                                     │ on every proxied request
                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│ dashboard/middleware.ts  (Edge runtime)                          │
│                                                                  │
│  request ─▶ nonce + CSP setup                                    │
│              │                                                   │
│              ▼                                                   │
│        DASHBOARD_TOKEN bypass? ──yes──▶ strip session, pass      │
│              │ no                                                │
│              ▼                                                   │
│        VOIDNET_HMAC_SECRET set AND X-Voidnet-* headers present?  │
│              │                                                   │
│      ┌───────┴───────┐                                           │
│      │ yes           │ no                                        │
│      ▼               ▼                                           │
│  voidnet-auth    Telegram JWT gate (existing)                    │
│  verifier         │                                              │
│   ├─ schema       ▼                                              │
│   ├─ HMAC         existing flow unchanged                        │
│   ├─ replay                                                      │
│   └─ owner eq?                                                   │
│      │                                                           │
│   ┌──┴──┐                                                        │
│   ok    fail                                                     │
│   │     └──▶ 401/403 JSON {error, code}                          │
│   ▼                                                              │
│  encode JWT (next-auth/jwt) with                                 │
│  {sub, telegramId, name} — same shape as Telegram path           │
│   │                                                              │
│   ▼                                                              │
│  NextResponse.next() + Set-Cookie                                │
│  (__Secure-authjs.session-token)                                 │
└──────────────────────────────────────────────────────────────────┘
                  │
                  ▼
       Route handlers / pages
       auth() / getToken() reads cookie → normal session
```

### Component Responsibilities

| File | Responsibility |
|------|----------------|
| `dashboard/lib/voidnet-auth.server.ts` (Edge-safe; no `server-only`) | Pure verifier: parse headers → schema check → HMAC verify → replay window → owner eq → return `{ok, claims}` or `{ok: false, error, code}` |
| `dashboard/middleware.ts` | Orchestration: env guard, call verifier, on success `encode()` JWT and set cookie, on fail return JSON error |
| `dashboard/auth.config.ts` | UNCHANGED — Telegram credentials provider stays. JWT shape already carries `telegramId`. |
| `dashboard/auth.ts` | UNCHANGED — `jwt()` callback sets `telegramId = user.id`; our synthetic JWT uses the same field |
| `dashboard/app/api/integration/v1/meta/route.ts` | `GET` handler returning `{version, supported_auth_modes, dashboard_port}`; relies on middleware to have gated |
| `dashboard/lib/voidnet-auth.server.test.ts` | Bun unit tests mirroring `telegram-widget.server.test.ts` |
| `dashboard/tests/e2e/voidnet.spec.ts` | Playwright: valid headers, bad sig, stale timestamp, wrong owner, no-secret fallback |

### Pattern 1: Edge WebCrypto HMAC-SHA256 verify

```typescript
// Source: https://developer.mozilla.org/en-US/docs/Web/API/SubtleCrypto/sign
//         https://nextjs.org/docs/app/api-reference/edge (Edge runtime supports Web Crypto)

const enc = new TextEncoder();

async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig), (b) => b.toString(16).padStart(2, "0")).join("");
}

// Constant-time hex compare (Edge has no timingSafeEqual)
function ctEqHex(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
```

Reuse `edgeConstantTimeEqual` already present in `middleware.ts` (lines 64–69) — factor it into `lib/ct-compare.ts` so both voidnet verifier and middleware share it.

### Pattern 2: Mint NextAuth JWT in middleware (no round-trip)

```typescript
// Source: next-auth v5 JWT module — https://authjs.dev/reference/core/jwt
//         Same encode() that Auth.js uses internally when creating the cookie.
import { encode } from "next-auth/jwt";

const SESSION_MAX_AGE = 60 * 60 * 8; // 8h, matches auth.config.ts

async function mintVoidnetSession(claims: VoidnetClaims): Promise<string> {
  return encode({
    token: {
      sub: String(claims.telegramId),
      telegramId: String(claims.telegramId),
      name: claims.handle,
      // voidnet-origin marker — optional; downstream code MUST NOT branch on it per CONTEXT
      // but it's useful for debug logs.
      src: "voidnet",
    },
    secret: process.env.AUTH_SECRET!,
    maxAge: SESSION_MAX_AGE,
    salt: isProd ? "__Secure-authjs.session-token" : "authjs.session-token",
  });
}
```

**Salt value:** NextAuth v5 uses the cookie name as the JWT salt. This matches exactly what `getToken` in the existing middleware passes as `cookieName`. Keep both in sync.

Set the cookie on `NextResponse.next()`:

```typescript
res.cookies.set({
  name: isProd ? "__Secure-authjs.session-token" : "authjs.session-token",
  value: jwt,
  httpOnly: true,
  sameSite: "lax",
  path: "/",
  secure: isProd,
  maxAge: SESSION_MAX_AGE,
});
```

### Pattern 3: Middleware branch ordering

```typescript
// Insert BEFORE existing public-paths / session-gate blocks, AFTER DASHBOARD_TOKEN bypass.

const voidnetSecret = process.env.VOIDNET_HMAC_SECRET;
const hasVoidnetHeaders = req.headers.get("x-voidnet-signature");
if (voidnetSecret && hasVoidnetHeaders) {
  const result = await verifyVoidnetHeaders(req.headers, voidnetSecret, process.env.OWNER_TELEGRAM_ID);
  if (!result.ok) {
    return applySecurityHeaders(
      NextResponse.json({ error: result.error, code: result.code }, { status: result.status }),
      nonce,
    );
  }
  const jwt = await mintVoidnetSession(result.claims);
  const passRes = NextResponse.next({ request: { headers: requestHeaders } });
  passRes.cookies.set({ /* see Pattern 2 */ });
  return applySecurityHeaders(passRes, nonce);
}
// fall through to existing Telegram logic
```

### Anti-Patterns to Avoid
- **Calling `signIn()` from middleware per request.** Wastes a round-trip and breaks the "no NextAuth dance" contract.
- **Storing voidnet claims in a module-scoped cache.** Edge runtime instances are ephemeral and per-region; stateless encode is the only correct pattern.
- **Decoding JSON bodies in middleware.** Header-only path; body parsing in middleware has known Edge pitfalls with streaming endpoints.
- **Branching downstream code on `src: "voidnet"`.** Explicitly forbidden by CONTEXT: downstream code must treat the session as source-agnostic.
- **Using `node:crypto`.** Forces Node middleware runtime; breaks Edge matcher; explicitly commented against in existing `middleware.ts:63`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JWT encoding / signing | Custom JWS encoder | `next-auth/jwt` `encode()` | Matches exact Auth.js salt/format; one wrong field breaks `getToken` decoding |
| HMAC-SHA256 | Hand-rolled SHA-256 | `crypto.subtle` | WebCrypto is audited, constant-time inside the primitive |
| Hex encoding | Manual byte loop with `toString(16)` | Reuse small helper once — acceptable | Trivial, no library warranted, but co-locate with verifier |
| Constant-time compare | New XOR loop | Reuse `edgeConstantTimeEqual` from middleware | Already reviewed and tracked (T-13-16) |
| Header schema parsing | Ad-hoc regex scattered | One verifier module with Zod or explicit guards | Single point for validation, testable |

**Key insight:** Every primitive we need is already in the project or the runtime. The phase is ~150 LOC of glue + tests.

## Runtime State Inventory

Not a rename/refactor — greenfield middleware logic. Omitted.

## Common Pitfalls

### Pitfall 1: JWT salt mismatch between `encode()` and `getToken()`
**What goes wrong:** `encode()` without the correct `salt` produces a token `getToken` cannot decrypt → user sees login loop.
**Why it happens:** Auth.js v5 derives the encryption key from `AUTH_SECRET + salt`; salt defaults to cookie name.
**How to avoid:** Pass `salt` to `encode()` matching the `cookieName` used by `getToken` (`__Secure-authjs.session-token` in prod, `authjs.session-token` in dev). Cover with integration test that mints then reads back.
**Warning signs:** Downstream `auth()` returns `null` despite cookie being present.

### Pitfall 2: `Math.floor(Date.now() / 1000)` clock drift
**What goes wrong:** Strict ±60s on a machine with 2s drift causes intermittent 401s near the window boundary.
**Why it happens:** LXC clocks drift until ntp re-syncs.
**How to avoid:** Use ±60s (already locked). Add a log at WARN when delta is 45–60s to detect drift early. Do not tighten window.
**Warning signs:** E2E tests pass locally but fail in CI with "VOIDNET_STALE".

### Pitfall 3: Matching wrong signature input string
**What goes wrong:** voidnet-api signs `user_id|handle|telegram_id|timestamp`, dashboard re-builds with different field order or separator → always-401.
**Why it happens:** Easy to reverse fields or use `:` instead of `|`.
**How to avoid:** Locked in CONTEXT. Write one unit test with a hand-computed hex vector (from Python or CLI) to lock the canonical form in CI. Mirror the `telegram-widget.server.test.ts` "cross-verified Python vector" test.
**Warning signs:** All voidnet requests 401 in integration despite valid-looking headers.

### Pitfall 4: Setting session cookie without `httpOnly`/`secure` correctly
**What goes wrong:** In prod, cookie with wrong `Secure` flag is dropped silently behind Caddy.
**Why it happens:** Mismatch between `isProd` detection and reverse-proxy TLS termination.
**How to avoid:** Exactly mirror the existing `auth.ts` `cookies.sessionToken.options` block (httpOnly, sameSite:lax, secure in prod).

### Pitfall 5: Middleware matcher excluding `/api/integration/v1/meta`
**What goes wrong:** New endpoint bypasses voidnet check if matcher is too narrow.
**Why it happens:** Copy-paste of old matcher regex.
**How to avoid:** Current matcher is `/((?!_next/static|_next/image|favicon.ico).*)` — already covers `/api/*`. Do not modify. Add a Playwright test hitting the endpoint without headers.

### Pitfall 6: Leaking stack trace in error JSON
**What goes wrong:** Verifier throws, middleware returns raw `Error.message` with crypto internals.
**Why it happens:** Forgetting to wrap.
**How to avoid:** Verifier returns result object (never throws); middleware only ever emits `{error: <fixed string>, code: <VOIDNET_*>}`.

## Code Examples

### voidnet-auth.server.ts skeleton (Edge-safe)

```typescript
// Source: composed from existing telegram-widget.server.ts + Edge Crypto docs
// NB: NO `import "server-only"` — this runs in Edge middleware.
// NB: NO `node:crypto` — Edge only.

const HANDLE_RE = /^[a-z][a-z0-9-]+$/;
const I64_RE = /^-?\d+$/;

export type VoidnetClaims = {
  userId: string;
  handle: string;
  telegramId: string;
  timestamp: number;
};

export type VerifyResult =
  | { ok: true; claims: VoidnetClaims }
  | { ok: false; status: 401 | 403; error: string; code: string };

export async function verifyVoidnetHeaders(
  h: Headers,
  secret: string,
  ownerTelegramId: string | undefined,
): Promise<VerifyResult> {
  const userId = h.get("x-voidnet-user-id") ?? "";
  const handle = h.get("x-voidnet-handle") ?? "";
  const telegramId = h.get("x-voidnet-telegram-id") ?? "";
  const tsStr = h.get("x-voidnet-timestamp") ?? "";
  const sig = h.get("x-voidnet-signature") ?? "";

  if (!I64_RE.test(userId)) return fail(401, "bad user_id", "VOIDNET_SCHEMA");
  if (handle.length < 3 || handle.length > 32 || !HANDLE_RE.test(handle))
    return fail(401, "bad handle", "VOIDNET_SCHEMA");
  if (!I64_RE.test(telegramId)) return fail(401, "bad telegram_id", "VOIDNET_SCHEMA");
  if (!/^\d+$/.test(tsStr)) return fail(401, "bad timestamp", "VOIDNET_SCHEMA");
  if (!/^[0-9a-f]{64}$/.test(sig)) return fail(401, "bad signature", "VOIDNET_SCHEMA");

  const ts = Number(tsStr);
  const now = Math.floor(Date.now() / 1000);
  if (Math.abs(now - ts) > 60) return fail(401, "timestamp out of window", "VOIDNET_STALE");

  const expected = await hmacSha256Hex(secret, `${userId}|${handle}|${telegramId}|${ts}`);
  if (!ctEqHex(expected, sig)) return fail(401, "invalid signature", "VOIDNET_SIG_INVALID");

  if (!ownerTelegramId || ownerTelegramId !== telegramId)
    return fail(403, "owner mismatch", "VOIDNET_OWNER_MISMATCH");

  return { ok: true, claims: { userId, handle, telegramId, timestamp: ts } };
}

function fail(status: 401 | 403, error: string, code: string): VerifyResult {
  return { ok: false, status, error, code };
}
```

### Meta endpoint

```typescript
// app/api/integration/v1/meta/route.ts
// Middleware gates this; handler just reads env.
import { NextResponse } from "next/server";
import pkg from "@/package.json" assert { type: "json" };

export const runtime = "edge"; // optional; works on node too

export async function GET() {
  return NextResponse.json({
    version: pkg.version,
    supported_auth_modes: ["telegram", "voidnet"],
    dashboard_port: Number(process.env.DASHBOARD_PORT ?? 8090),
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NextAuth v4 `getServerSession` | v5 `auth()` + `getToken()` | next-auth 5.0 beta | Already adopted in this project |
| Node-only middleware | Edge middleware with WebCrypto | Next 13+ | This project already Edge; keep |
| Sharing Auth.js session via signIn round-trip | Pre-mint JWT via `encode()` | Documented in v5 migration guide | Saves one request per voidnet call |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `next-auth/jwt` `encode()` with matching `salt` produces a token `getToken` will accept without any callback wiring | Pattern 2 | If wrong, downstream `auth()` returns null → login loop. Mitigation: integration test mints+reads in one bun test before any E2E. |
| A2 | `@auth/core` 0.34 is compatible with `next-auth@5.0.0-beta.31` for the `encode` interop shown | Standard Stack | Low — both pinned in package.json and `getToken` already works in current middleware |
| A3 | `next-auth/jwt` is importable in the Edge runtime without pulling Node built-ins | Pattern 2 | Medium — verify in Wave 0 by building and running middleware locally. Fallback: use `jose` directly (explicit dep) with the same JWE params Auth.js uses. |
| A4 | `process.env.AUTH_SECRET` is already available to Edge middleware (Next.js exposes all server env to Edge) | Pattern 2 | Low — existing middleware already reads `AUTH_SECRET` at line 130 |

## Open Questions

1. **Do we need `src: "voidnet"` in the JWT for debugging?**
   - What we know: CONTEXT forbids downstream branching on auth source.
   - What's unclear: whether a non-semantic marker for logs is acceptable.
   - Recommendation: include it, forbid reading it in route handlers via an ESLint rule or code review.

2. **Should the meta endpoint also reflect `has_voidnet: boolean` without leaking the secret?**
   - What we know: voidnet-api uses the response to detect version compatibility.
   - What's unclear: voidnet-api may want to assert the LXC is voidnet-aware.
   - Recommendation: defer. `supported_auth_modes` array already signals this.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Edge runtime WebCrypto | HMAC verify | ✓ (used at `middleware.ts:74`) | Next 15 built-in | — |
| `next-auth/jwt` encode | Session mint | ✓ | 5.0.0-beta.31 | `jose` library (already transitive via `@auth/core`) |
| `bun` test runner | Unit tests | ✓ | existing `"test": "bun test"` | — |
| Playwright | E2E | ✓ | 1.59.1 | — |
| `AUTH_SECRET` env | JWT encryption | ✓ (already required per CLAUDE.md) | — | Fail-closed at startup |
| `OWNER_TELEGRAM_ID` env | Owner gate | ✓ (already required) | — | Fail-closed |
| `VOIDNET_HMAC_SECRET` env | Activation | ✗ new | — | Unset → voidnet mode skipped (by design) |

**Missing dependencies with no fallback:** None.
**Missing dependencies with fallback:** None blocking.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Unit framework | `bun:test` (matches `lib/*.test.ts` convention) |
| E2E framework | `@playwright/test` (matches `tests/e2e/*.spec.ts`) |
| Unit config file | `package.json` (`"test": "bun test"`) |
| E2E config file | `dashboard/playwright.config.*` (present — existing) |
| Quick run command | `cd dashboard && bun test lib/voidnet-auth.server.test.ts` |
| Full suite command | `cd dashboard && bun test && bunx playwright test` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| REQ-1 | HMAC verify accepts valid, rejects tampered/malformed | unit | `bun test lib/voidnet-auth.server.test.ts -t "verify"` | ❌ Wave 0 |
| REQ-1 | Handle regex enforced (length + charset) | unit | same file | ❌ Wave 0 |
| REQ-2 | ±60s replay window | unit | same file, "timestamp" cases | ❌ Wave 0 |
| REQ-3 | Middleware routes voidnet-first, falls through otherwise | E2E | `playwright test voidnet.spec.ts -g "no-headers falls through"` | ❌ Wave 0 |
| REQ-3 | Invalid sig → 401 JSON `{error, code}` | E2E | `playwright test voidnet.spec.ts -g "invalid signature"` | ❌ Wave 0 |
| REQ-4 | Voidnet path yields session with `telegramId` matching header | integration | bun test that mints+decodes via `getToken` shim | ❌ Wave 0 |
| REQ-5 | Telegram ID mismatch → 403 JSON | E2E | `playwright test voidnet.spec.ts -g "owner mismatch"` | ❌ Wave 0 |
| REQ-6 | Secret unset → Telegram flow unchanged | E2E | `playwright test voidnet.spec.ts -g "secret unset"` | ❌ Wave 0 |
| REQ-7 | `/api/integration/v1/meta` requires valid sig; returns shape | E2E | `playwright test voidnet.spec.ts -g "meta"` | ❌ Wave 0 |
| REQ-8 | Env doc exists | lint/grep | `grep -q VOIDNET_HMAC_SECRET dashboard/DASHBOARD.md` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `bun test lib/voidnet-auth.server.test.ts` (unit slice, <5 s)
- **Per wave merge:** `bun test && bunx playwright test tests/e2e/voidnet.spec.ts` (full voidnet slice)
- **Phase gate:** `bun test && bunx playwright test` full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `dashboard/lib/voidnet-auth.server.test.ts` — covers REQ-1, REQ-2, REQ-4 (JWT roundtrip)
- [ ] `dashboard/tests/e2e/voidnet.spec.ts` — covers REQ-3, REQ-5, REQ-6, REQ-7
- [ ] Test fixture: hand-computed signature vector (produced by a tiny Python or `openssl` helper) to lock signature canonicalisation. Mirror `telegram-widget.server.test.ts` "cross-verified Python vector" test.
- [ ] No framework install needed.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | HMAC-SHA256 with 256-bit secret; `AUTH_SECRET` for downstream JWT |
| V3 Session Management | yes | `next-auth/jwt` encode/decode; 8h max age; httpOnly + secure cookies |
| V4 Access Control | yes | Owner invariant via `OWNER_TELEGRAM_ID` env comparison |
| V5 Input Validation | yes | Header shape validation (regex + integer check); Zod optional |
| V6 Cryptography | yes | WebCrypto `crypto.subtle.sign` — never hand-roll SHA-256 or HMAC |
| V7 Error Handling & Logging | yes | Fixed `{error, code}` JSON shape; no stack traces leaked |
| V13 API & Web Service | yes | `/api/integration/v1/meta` gated by middleware |

### Known Threat Patterns for Edge-middleware HMAC auth

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Signature forgery | Spoofing | HMAC-SHA256 with server-held `VOIDNET_HMAC_SECRET` (never in client) |
| Replay of captured request | Tampering / Spoofing | ±60s timestamp window signed as part of MAC |
| Owner impersonation via injected telegram_id | Elevation of Privilege | Explicit equality check vs `OWNER_TELEGRAM_ID`; 403, no fallback |
| Secret leak via error body | Information Disclosure | Fixed error shape; verifier never includes secret or computed HMAC in response |
| Timing side-channel on signature compare | Information Disclosure | Constant-time hex compare (reuse existing `edgeConstantTimeEqual`) |
| Accidental NextAuth session session-cookie acceptance from untrusted origin | Spoofing | Cookie is httpOnly + secure + sameSite:lax; browser never talks to dashboard directly (only voidnet-api does) |
| Downstream code branching on auth source leading to bypass | Elevation of Privilege | Contract: synthetic JWT is shape-identical to Telegram JWT; enforced via test comparing both JWTs' keys |

## Sources

### Primary (HIGH confidence)
- [VERIFIED: dashboard/package.json] — pinned versions of next-auth, next, @auth/core, zod, bun:test, playwright
- [VERIFIED: dashboard/middleware.ts] — current Edge runtime, crypto.getRandomValues usage, explicit "no node:crypto" comments
- [VERIFIED: dashboard/auth.ts + auth.config.ts] — JWT callback shape, cookies config, Telegram credentials provider
- [VERIFIED: dashboard/lib/telegram-widget.server.ts] — canonical HMAC-in-this-project pattern to mirror
- [CITED: https://authjs.dev/getting-started/migrating-to-v5] — Edge-compatible `auth.config.ts` proxy pattern
- [CITED: https://authjs.dev/reference/core/jwt] — `encode()`/`decode()` contract
- [CITED: https://nextjs.org/docs/app/api-reference/edge] — Edge runtime WebCrypto availability

### Secondary (MEDIUM confidence)
- [CITED: ctx7 pull of `/nextauthjs/next-auth` credentials docs, 2026-04-22] — current `authorize({request})` signature and Edge middleware proxy pattern

### Tertiary (LOW confidence)
- None.

## Project Constraints (from CLAUDE.md)

- Python 3.12 / TypeScript 5 — phase touches TS only.
- Ruff / ESLint configured — lint must stay green.
- Package import path: `@/lib/...` — follow existing alias.
- No new pip deps — N/A (no Python changes).
- Backward compatibility with standalone Telegram flow is mandatory per CONTEXT and the v2 constraints in CLAUDE.md ("Reversibility" principle).
- Frontend stack spec at `hub/knowledge/standards/frontend-stack-spec.md` — no UI changes in this phase; spec not materially affected.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pinned versions in package.json; patterns mirror existing `telegram-widget.server.ts`.
- Architecture: HIGH — CONTEXT locks every cross-boundary decision; only mechanics remain.
- HMAC mechanics: HIGH — WebCrypto `crypto.subtle` is the Edge-runtime standard and the existing middleware already uses WebCrypto helpers.
- Session synthesis (`encode()`): MEDIUM — documented v5 pattern, but salt/interop with `getToken` should be smoke-tested in Wave 0 (A1, A3 in Assumptions).
- Pitfalls: HIGH — derived from project's own prior pitfall tracking (T-13-16, WR-04, WR-05, CR-01).

**Research date:** 2026-04-22
**Valid until:** 2026-05-22 (next-auth v5 still beta; re-check if stable ships)

## RESEARCH COMPLETE
