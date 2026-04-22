# Phase 14: VoidNet Integration Auth — Pattern Map

**Mapped:** 2026-04-22
**Files analyzed:** 7 new/modified files
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `dashboard/lib/voidnet-auth.server.ts` (NEW) | verifier/utility | request-response (pure) | `dashboard/lib/telegram-widget.server.ts` | exact (HMAC verifier) |
| `dashboard/lib/voidnet-auth.server.test.ts` (NEW) | test (unit) | request-response | `dashboard/lib/telegram-widget.server.test.ts` | exact |
| `dashboard/middleware.ts` (MODIFY) | middleware | request-response, Edge | self (in-place) | self |
| `dashboard/auth.config.ts` / `auth.ts` (LIKELY NO-OP) | config | n/a | self | N/A — research concludes no change needed (middleware mints JWT with `next-auth/jwt` `encode()`) |
| `dashboard/app/api/integration/v1/meta/route.ts` (NEW) | route handler | request-response | `dashboard/app/api/hub/tree/route.ts` | role-match (auth-gated GET) |
| `dashboard/tests/e2e/voidnet.spec.ts` (NEW) | test (E2E) | request-response | `dashboard/tests/e2e/dashboard-token.spec.ts` | exact (header-based auth bypass E2E) |
| `dashboard/DASHBOARD.md` or `README.md` (MODIFY) | doc | n/a | existing env block in same doc | self |

## Pattern Assignments

### `dashboard/lib/voidnet-auth.server.ts` (verifier, Edge-safe)

**Primary analog:** `dashboard/lib/telegram-widget.server.ts`
**CRITICAL DIVERGENCE:** telegram-widget uses `node:crypto` (`import "server-only"` + `import crypto from "node:crypto"`). Voidnet verifier runs in **Edge middleware** — MUST use `crypto.subtle` (WebCrypto) and MUST NOT import `server-only` or `node:crypto`. Research RESEARCH.md Pattern 1 + Common Pitfalls 3.

**Imports pattern to REPLACE (do NOT copy from telegram-widget lines 1-2):**

```typescript
// telegram-widget.server.ts lines 1-2 — DO NOT COPY, it's Node-only:
//   import "server-only";
//   import crypto from "node:crypto";
// Voidnet replacement (Edge-safe, no imports beyond types):
const enc = new TextEncoder();
```

**Result-union return type pattern** — mirror telegram-widget's fail-closed `| null` shape, but expand to `{ok, claims} | {ok:false, status, error, code}` to carry the HTTP status + error code (phase requires `{error, code}` JSON body with distinct 401 vs 403):

```typescript
// Shape chosen to satisfy CONTEXT "error JSON {error, code}" + REQ-5 owner-mismatch=403
export type VoidnetClaims = {
  userId: string;
  handle: string;
  telegramId: string;
  timestamp: number;
};

export type VerifyResult =
  | { ok: true; claims: VoidnetClaims }
  | { ok: false; status: 401 | 403; error: string; code: string };
```

**Validation pattern** (copy structural style from telegram-widget lines 38-63 — guard-clauses returning early on each field):

Telegram-widget excerpt to mirror (lines 41-63):
```typescript
  const hash = obj.hash;
  if (typeof hash !== "string" || hash.length === 0) return null;

  const authDate = Number(obj.auth_date);
  if (!Number.isFinite(authDate)) return null;
  const now = Math.floor(Date.now() / 1000);
  if (now - authDate > 86400) return null;
  if (authDate - now > 60) return null;

  if (typeof obj.id === "number") {
    if (!Number.isFinite(obj.id)) return null;
  } else if (typeof obj.id === "string") {
    if (!/^-?\d+$/.test(obj.id)) return null;
  } else {
    return null;
  }
```

Voidnet equivalent (regex constants + per-header guard clauses, but `return fail(status, error, code)` instead of `return null`):

```typescript
const HANDLE_RE = /^[a-z][a-z0-9-]+$/;
const I64_RE = /^-?\d+$/;
const HEX64_RE = /^[0-9a-f]{64}$/;

if (!I64_RE.test(userId)) return fail(401, "bad user_id", "VOIDNET_SCHEMA");
if (handle.length < 3 || handle.length > 32 || !HANDLE_RE.test(handle))
  return fail(401, "bad handle", "VOIDNET_SCHEMA");
// ... etc
if (Math.abs(now - ts) > 60) return fail(401, "timestamp out of window", "VOIDNET_STALE");
```

**HMAC pattern — REPLACE Node `createHmac` with WebCrypto `crypto.subtle`** (from RESEARCH.md Pattern 1, NOT from telegram-widget):

Telegram-widget lines 71-75 (Node — DO NOT COPY VERBATIM):
```typescript
  const secret = crypto.createHash("sha256").update(botToken).digest();
  const expectedHex = crypto
    .createHmac("sha256", secret)
    .update(dataCheckString)
    .digest("hex");
```

Voidnet Edge replacement:
```typescript
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
```

**Signature canonical message format (LOCKED BY CONTEXT — DO NOT VARY):**
```
`${userId}|${handle}|${telegramId}|${ts}`
```

**Constant-time compare — reuse from middleware** (DO NOT copy telegram-widget's `crypto.timingSafeEqual`):

Middleware excerpt (`dashboard/middleware.ts` lines 64-69):
```typescript
function edgeConstantTimeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
```

**Executor note:** RESEARCH.md recommends factoring this into `dashboard/lib/ct-compare.ts` so both middleware and voidnet-auth import it. Planner decides whether to split now or inline.

---

### `dashboard/lib/voidnet-auth.server.test.ts` (unit test)

**Analog:** `dashboard/lib/telegram-widget.server.test.ts`

**Imports pattern** (lines 1-4):
```typescript
import { describe, test, expect } from "bun:test";
import crypto from "node:crypto";
import { verifyVoidnetHeaders } from "./voidnet-auth.server";
// test-side signer is allowed node:crypto — tests run under Bun, not Edge
```

**Signer helper pattern** (mirror telegram-widget lines 8-20 — compute expected HMAC with `node:crypto` so the test cross-verifies against a canonical Python-style vector):

```typescript
const SECRET = "test-voidnet-secret-32-bytes-xxxxx";

function signHeaders(params: {
  userId: string;
  handle: string;
  telegramId: string;
  timestamp: number;
}): Record<string, string> {
  const msg = `${params.userId}|${params.handle}|${params.telegramId}|${params.timestamp}`;
  const hash = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");
  return {
    "x-voidnet-user-id": params.userId,
    "x-voidnet-handle": params.handle,
    "x-voidnet-telegram-id": params.telegramId,
    "x-voidnet-timestamp": String(params.timestamp),
    "x-voidnet-signature": hash,
  };
}
```

**Test case pattern** (mirror telegram-widget lines 22-78):

Test names to include (from SPEC acceptance + RESEARCH Wave-0 gaps):
- "accepts valid headers" → `ok: true`, claims match
- "rejects tampered signature" → `code: "VOIDNET_SIG_INVALID"`, status 401
- "rejects bad handle (too short / bad chars)" → `code: "VOIDNET_SCHEMA"`
- "rejects non-numeric telegram_id / user_id / timestamp" → `code: "VOIDNET_SCHEMA"`
- "rejects timestamp 61s in past" → `code: "VOIDNET_STALE"`
- "rejects timestamp 61s in future" → `code: "VOIDNET_STALE"`
- "accepts timestamp ±59s" → `ok: true`
- "rejects owner mismatch" (telegram_id ≠ OWNER_TELEGRAM_ID) → status 403, `code: "VOIDNET_OWNER_MISMATCH"`
- "cross-verified Python vector" (hand-computed hex vector locking canonical form — mirror telegram-widget lines 67-78)

---

### `dashboard/middleware.ts` (MODIFY)

**Analog:** self.

**Insertion point:** After the `DASHBOARD_TOKEN bypass` block (current lines 80-111) and BEFORE the `Public paths` block (current line 113). Rationale: voidnet auth is activation-gated on `VOIDNET_HMAC_SECRET`; when active, it must gate everything including `/api/*` (meta endpoint) but should not interfere with DASHBOARD_TOKEN ops bypass.

**Activation guard pattern** — mirror DASHBOARD_TOKEN's env + header presence check (middleware.ts lines 84-92):

Existing pattern to mirror structurally:
```typescript
  const dashToken =
    req.headers.get("x-dashboard-token") ??
    req.nextUrl.searchParams.get("token");
  const expectedDashToken = process.env.DASHBOARD_TOKEN;
  if (
    dashToken &&
    expectedDashToken &&
    edgeConstantTimeEqual(dashToken, expectedDashToken)
  ) { ... }
```

Voidnet insertion (from RESEARCH Pattern 3):
```typescript
  // ── VoidNet HMAC header auth ─────────────────────────────────────────
  const voidnetSecret = process.env.VOIDNET_HMAC_SECRET;
  const hasVoidnetSig = req.headers.get("x-voidnet-signature");
  if (voidnetSecret && hasVoidnetSig) {
    const result = await verifyVoidnetHeaders(
      req.headers,
      voidnetSecret,
      process.env.OWNER_TELEGRAM_ID,
    );
    if (!result.ok) {
      return applySecurityHeaders(
        NextResponse.json(
          { error: result.error, code: result.code },
          { status: result.status },
        ),
        nonce,
      );
    }
    const jwt = await mintVoidnetSession(result.claims);
    const passRes = NextResponse.next({ request: { headers: requestHeaders } });
    passRes.cookies.set({
      name: isProd
        ? "__Secure-authjs.session-token"
        : "authjs.session-token",
      value: jwt,
      httpOnly: true,
      sameSite: "lax",
      path: "/",
      secure: isProd,
      maxAge: 60 * 60 * 8,
    });
    return applySecurityHeaders(passRes, nonce);
  }
```

**Cookie-name pattern** — reuse existing `isProd ? "__Secure-authjs.session-token" : "authjs.session-token"` verbatim from lines 132-134. NextAuth v5 `encode()` salt MUST match this cookie name (RESEARCH Pitfall 1).

**JWT minting pattern (NEW helper, lives in middleware.ts or lib):**
```typescript
import { encode } from "next-auth/jwt";

async function mintVoidnetSession(claims: VoidnetClaims): Promise<string> {
  const isProd = process.env.NODE_ENV === "production";
  return encode({
    token: {
      sub: claims.telegramId,
      telegramId: claims.telegramId,
      name: claims.handle,
      src: "voidnet", // debug marker; downstream MUST NOT branch on this
    },
    secret: process.env.AUTH_SECRET!,
    maxAge: 60 * 60 * 8,
    salt: isProd ? "__Secure-authjs.session-token" : "authjs.session-token",
  });
}
```

**CRITICAL:** The `salt` value must exactly match the `cookieName` used by `getToken` at middleware.ts lines 132-134. Mismatch → login loop (RESEARCH Pitfall 1).

---

### `dashboard/app/api/integration/v1/meta/route.ts` (NEW)

**Analog:** `dashboard/app/api/hub/tree/route.ts`

**Imports pattern** (hub/tree lines 1-8):
```typescript
import "server-only";
import { NextRequest, NextResponse } from "next/server";

import { auth } from "@/auth";
```

**Runtime declaration pattern** (hub/tree line 9):
```typescript
export const runtime = "nodejs";
```

(RESEARCH suggests either `"edge"` or `"nodejs"` works; match hub/tree convention `"nodejs"` unless package.json import needs Edge-specific handling.)

**Handler pattern** — simplified from hub/tree (lines 19-47). Middleware already enforces voidnet HMAC gate, so this handler only reads env + returns JSON. **No `auth()` call needed** — middleware either minted a session cookie (voidnet path) or rejected the request (401/403). However, follow hub/tree's defense-in-depth and still verify the request is auth'd:

```typescript
export async function GET(_req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "unauthorized", code: "NO_SESSION" }, { status: 401 });
  }
  const pkg = (await import("@/package.json", { with: { type: "json" } })).default;
  return NextResponse.json({
    version: pkg.version,
    supported_auth_modes: ["telegram", "voidnet"],
    dashboard_port: Number(process.env.DASHBOARD_PORT ?? 8090),
  });
}
```

**Error shape** — hub/tree line 22 `{ error: "unauthorized" }` status 401 is the project convention; extend to `{error, code}` per CONTEXT/SPEC requirement.

---

### `dashboard/tests/e2e/voidnet.spec.ts` (NEW)

**Analog:** `dashboard/tests/e2e/dashboard-token.spec.ts`

**Imports + header-injection pattern** (dashboard-token.spec.ts lines 1, 9-13):
```typescript
import { expect, test } from "@playwright/test";

test("valid DASHBOARD_TOKEN header grants access without session", async ({ browser }) => {
  const ctx = await browser.newContext({
    extraHTTPHeaders: { "x-dashboard-token": "test-dash-token" },
  });
```

Voidnet equivalent — E2E must compute HMAC at test-time (voidnet-api would in prod). Helper module:

```typescript
import crypto from "node:crypto";

const SECRET = process.env.VOIDNET_HMAC_SECRET ?? "test-voidnet-secret";
const OWNER_ID = process.env.OWNER_TELEGRAM_ID ?? "111111"; // matches Playwright webServer env

function voidnetHeaders(opts?: { telegramId?: string; tamper?: boolean; offset?: number }) {
  const telegramId = opts?.telegramId ?? OWNER_ID;
  const userId = "42";
  const handle = "testuser";
  const ts = Math.floor(Date.now() / 1000) + (opts?.offset ?? 0);
  const msg = `${userId}|${handle}|${telegramId}|${ts}`;
  let sig = crypto.createHmac("sha256", SECRET).update(msg).digest("hex");
  if (opts?.tamper) sig = sig.slice(0, -1) + (sig.slice(-1) === "0" ? "1" : "0");
  return {
    "x-voidnet-user-id": userId,
    "x-voidnet-handle": handle,
    "x-voidnet-telegram-id": telegramId,
    "x-voidnet-timestamp": String(ts),
    "x-voidnet-signature": sig,
  };
}
```

**Test cases to include** (mirror dashboard-token.spec.ts structure — REQ-3, REQ-5, REQ-6, REQ-7):

- `"valid voidnet headers grant access without Telegram widget"` — mirror dashboard-token.spec.ts lines 9-20, substituting headers + asserting URL not /login.
- `"tampered signature → 401 JSON {error, code}"` — `await page.request.get("/", { headers: voidnetHeaders({ tamper: true }) })`, assert status 401, JSON body shape.
- `"stale timestamp (>60s) → 401 VOIDNET_STALE"` — `offset: -90`, assert code `VOIDNET_STALE`.
- `"owner mismatch → 403 VOIDNET_OWNER_MISMATCH"` — `telegramId: "999999"`, status 403.
- `"no voidnet headers + no secret → Telegram flow unchanged"` — mirror auth.spec.ts lines 14-18 (`/` → redirect `/login`).
- `"GET /api/integration/v1/meta with valid sig → 200 shape"` — returns `{version, supported_auth_modes:["telegram","voidnet"], dashboard_port:8090}`.
- `"GET /api/integration/v1/meta without sig → 401"`.

**Assertion pattern** (dashboard-token.spec.ts lines 17-19):
```typescript
  expect(res?.status()).toBeLessThan(400);
  await expect(page).not.toHaveURL(/\/login$/);
```

**webServer env:** Planner must ensure `playwright.config.*` webServer env includes `VOIDNET_HMAC_SECRET=test-voidnet-secret` for the test run (mirrors how `DASHBOARD_TOKEN=test-dash-token` is already set — see dashboard-token.spec.ts line 6).

---

### `dashboard/DASHBOARD.md` / `README.md` (MODIFY)

**Analog:** existing env section in whichever file currently documents `DASHBOARD_TOKEN`, `OWNER_TELEGRAM_ID`, `AUTH_SECRET` (see top-level `CLAUDE.md` env block as reference format).

**Content requirement (REQ-8):**

```markdown
### `VOIDNET_HMAC_SECRET`
Shared secret between voidnet-api and this dashboard. Enables voidnet-proxied auth mode:
when set, the dashboard accepts HMAC-signed `X-Voidnet-*` headers injected by voidnet-api
and synthesizes a NextAuth session without the Telegram Login Widget.
Must pair with `OWNER_TELEGRAM_ID` — requests whose `X-Voidnet-Telegram-Id` does not equal
`OWNER_TELEGRAM_ID` are rejected with 403. If unset, voidnet mode is disabled and the
standalone Telegram login flow runs unchanged.
```

**Grep acceptance (from SPEC):** `grep -q VOIDNET_HMAC_SECRET dashboard/DASHBOARD.md && grep -q OWNER_TELEGRAM_ID dashboard/DASHBOARD.md`.

---

## Shared Patterns

### Edge runtime HMAC
**Source:** MDN WebCrypto + existing `middleware.ts` lines 64-75 (uses `crypto.getRandomValues`)
**Apply to:** `voidnet-auth.server.ts`
**Why:** middleware.ts is Edge; `node:crypto` is unavailable. Explicit project comment at middleware.ts line 63 documents the Edge constraint.

```typescript
// Edge-safe WebCrypto HMAC-SHA256 — reuse across any future voidnet-adjacent module:
const enc = new TextEncoder();
async function hmacSha256Hex(secret: string, message: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return Array.from(new Uint8Array(sig), b => b.toString(16).padStart(2, "0")).join("");
}
```

### Constant-time compare (Edge)
**Source:** `dashboard/middleware.ts` lines 64-69
**Apply to:** `voidnet-auth.server.ts` (signature compare). Planner may factor into `dashboard/lib/ct-compare.ts`.

### Error response shape
**Source:** `dashboard/app/api/hub/tree/route.ts` lines 22, 31-34, 42-45 — `NextResponse.json({ error: "..." }, { status: N })`
**Apply to:** meta route + middleware voidnet error responses.
**SPEC extension:** add `code` field, e.g. `{error: "invalid signature", code: "VOIDNET_SIG_INVALID"}`.

### Error codes (Claude's Discretion per CONTEXT)
Use stable constants for codes to make E2E assertions easy:
- `VOIDNET_SCHEMA` — malformed header shape (400-class, returned as 401)
- `VOIDNET_STALE` — timestamp outside ±60s
- `VOIDNET_SIG_INVALID` — HMAC mismatch
- `VOIDNET_OWNER_MISMATCH` — validated telegram_id ≠ OWNER_TELEGRAM_ID (403)

### Security headers wrapper
**Source:** `dashboard/middleware.ts` lines 39-53 (`applySecurityHeaders`)
**Apply to:** every voidnet-path response in middleware (ok path + error path). Mirror DASHBOARD_TOKEN bypass which wraps its `NextResponse.next(...)` in `applySecurityHeaders(passRes, nonce)` (line 110).

### Test signer helper pattern
**Source:** `dashboard/lib/telegram-widget.server.test.ts` lines 8-20
**Apply to:** both `voidnet-auth.server.test.ts` and `tests/e2e/voidnet.spec.ts`. Tests use `node:crypto` to produce the reference HMAC — legitimate because test runners (bun, node under Playwright) are not Edge.

## No Analog Found

No gaps. Every file has a strong project analog and RESEARCH.md supplies Edge-specific primitives where telegram-widget's Node-only pattern diverges.

## Metadata

**Analog search scope:**
- `dashboard/lib/*.server.ts` — HMAC verifier + owner gate + token compare
- `dashboard/middleware.ts` — self, for modification planning
- `dashboard/app/api/*/route.ts` — route handler pattern
- `dashboard/tests/e2e/*.spec.ts` — Playwright E2E structure
- `dashboard/lib/*.test.ts` — bun:test unit pattern

**Files scanned:** 8 (read in full) + 10 (listed)
**Pattern extraction date:** 2026-04-22

## PATTERN MAPPING COMPLETE
