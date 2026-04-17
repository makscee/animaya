# Phase 13: Migrate dashboard frontend to shared frontend-stack-spec - Pattern Map

**Mapped:** 2026-04-17
**Files analyzed:** ~45 new files + ~12 deletions
**Analogs found:** 42 / 45 (near-total coverage from `homelab/apps/admin`)

All new dashboard files map into a fresh top-level `dashboard/` directory that replaces `bot/dashboard/` (FastAPI+Jinja). The primary analog source is `/Users/admin/hub/workspace/homelab/apps/admin/` — the reference implementation of `frontend-stack-spec.md`. For Telegram HMAC logic, Animaya's own `bot/dashboard/auth.py` is the canonical analog.

## File Classification

### New files (Next.js app)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `dashboard/package.json` | config | n/a | `homelab/apps/admin/package.json` | exact (spec-verbatim, rename scope + port) |
| `dashboard/tsconfig.json` | config | n/a | `homelab/apps/admin/tsconfig.json` | exact (verbatim) |
| `dashboard/next.config.mjs` | config | n/a | `homelab/apps/admin/next.config.mjs` | role-match (no bun:sqlite shim needed) |
| `dashboard/postcss.config.mjs` | config | n/a | `homelab/apps/admin/postcss.config.mjs` | exact (1-line) |
| `dashboard/eslint.config.mjs` | config | n/a | `homelab/apps/admin/eslint.config.mjs` | exact (verbatim) |
| `dashboard/bunfig.toml` | config | n/a | `homelab/apps/admin/bunfig.toml` | exact |
| `dashboard/components.json` | config | n/a | `homelab/apps/admin/components.json` | exact |
| `dashboard/test-setup.ts` | config | n/a | `homelab/apps/admin/test-setup.ts` | exact |
| `dashboard/auth.ts` | provider | request-response | `homelab/apps/admin/auth.ts` | role-match (replace GitHub with custom Telegram) |
| `dashboard/auth.config.ts` | config | n/a | `homelab/apps/admin/auth.config.ts` | role-match (swap provider, pages) |
| `dashboard/middleware.ts` | middleware | request-response | `homelab/apps/admin/middleware.ts` | role-match (add DASHBOARD_TOKEN bypass, swap allowlist) |
| `dashboard/app/layout.tsx` | component | n/a | `homelab/apps/admin/app/layout.tsx` | exact |
| `dashboard/app/globals.css` | config | n/a | `homelab/apps/admin/app/globals.css` | exact (verbatim per spec §4) |
| `dashboard/app/error.tsx` | component | n/a | `homelab/apps/admin/app/error.tsx` | exact |
| `dashboard/app/not-found.tsx` | component | n/a | `homelab/apps/admin/app/not-found.tsx` | exact |
| `dashboard/app/(auth)/layout.tsx` | component | n/a | `homelab/apps/admin/app/(auth)/layout.tsx` | exact |
| `dashboard/app/(auth)/page.tsx` (home) | component | request-response | `homelab/apps/admin/app/(auth)/page.tsx` | role-match |
| `dashboard/app/(auth)/chat/page.tsx` | component | streaming | `homelab/apps/admin/app/(auth)/page.tsx` + SSE pattern | partial (chat+tree is new) |
| `dashboard/app/(auth)/_components/chat-panel.tsx` | component | streaming (SSE) | none exact — use SSE Pattern 4 + `homelab/.../_components/*` style | partial |
| `dashboard/app/(auth)/_components/hub-tree.tsx` | component | request-response | none exact — tree from scratch following admin component style | partial |
| `dashboard/app/(auth)/_components/tool-use-event.tsx` | component | n/a | `homelab/apps/admin/components/ui/card.tsx` | role-match (presentation only) |
| `dashboard/app/(auth)/_lib/use-sse.ts` | hook | streaming | none (discretion per CONTEXT) | no analog |
| `dashboard/app/(auth)/modules/page.tsx` | component | request-response | `homelab/apps/admin/app/(auth)/tokens/page.tsx` | role-match (list view with SWR) |
| `dashboard/app/(auth)/modules/[name]/page.tsx` | component | request-response | `homelab/apps/admin/app/(auth)/tokens/[id]/` area | role-match |
| `dashboard/app/(auth)/bridge/page.tsx` | component | request-response | `homelab/apps/admin/app/(auth)/tokens/page.tsx` | role-match (form-heavy page) |
| `dashboard/app/(auth)/bridge/_components/config-form.tsx` | component | request-response | `homelab/apps/admin/components/ui/form.tsx` + admin token add form | role-match |
| `dashboard/app/(public)/layout.tsx` | component | n/a | `homelab/apps/admin/app/(public)/layout.tsx` | exact |
| `dashboard/app/(public)/login/page.tsx` | component | request-response | `homelab/apps/admin/app/(public)/login/page.tsx` | role-match (Telegram Widget instead of GH button) |
| `dashboard/app/(public)/403/page.tsx` | component | n/a | `homelab/apps/admin/app/(public)/403/page.tsx` | exact |
| `dashboard/app/api/auth/[...nextauth]/route.ts` | route | request-response | `homelab/apps/admin/app/api/auth/[...nextauth]/route.ts` | exact |
| `dashboard/app/api/chat/stream/route.ts` | route | streaming (SSE) | `homelab/apps/admin/app/api/tokens/route.ts` (shape) + RESEARCH Pattern 4 | partial (SSE unique) |
| `dashboard/app/api/hub/tree/route.ts` | route | request-response | `homelab/apps/admin/app/api/tokens/route.ts` | role-match |
| `dashboard/app/api/hub/file/route.ts` | route | file-I/O | `homelab/apps/admin/app/api/tokens/route.ts` | role-match |
| `dashboard/app/api/modules/route.ts` | route | request-response | `homelab/apps/admin/app/api/tokens/route.ts` | exact |
| `dashboard/app/api/modules/[name]/install/route.ts` | route | request-response | `homelab/apps/admin/app/api/tokens/[id]/route.ts` | role-match |
| `dashboard/app/api/modules/[name]/uninstall/route.ts` | route | request-response | same as above | role-match |
| `dashboard/app/api/modules/[name]/config/route.ts` | route | request-response | same as above | role-match |
| `dashboard/app/api/bridge/claim/route.ts` etc | route | request-response | `homelab/apps/admin/app/api/tokens/route.ts` | role-match |
| `dashboard/components/ui/*.tsx` (19 files) | component | n/a | `homelab/apps/admin/components/ui/*.tsx` | exact (copy verbatim per D-14) |
| `dashboard/components/layout/topbar.tsx` | component | n/a | `homelab/apps/admin/components/layout/topbar.tsx` | exact |
| `dashboard/components/layout/sidebar.tsx` | component | n/a | `homelab/apps/admin/components/layout/sidebar.tsx` | exact |
| `dashboard/lib/utils.ts` | utility | n/a | `homelab/apps/admin/lib/utils.ts` | exact (6-line `cn()`) |
| `dashboard/lib/csrf.server.ts` | utility | request-response | `homelab/apps/admin/lib/csrf.server.ts` | exact (rename `hla-csrf` → `an-csrf`) |
| `dashboard/lib/csrf.shared.ts` | utility | n/a | `homelab/apps/admin/lib/csrf.shared.ts` | exact |
| `dashboard/lib/csrf-cookie.server.ts` | utility | n/a | `homelab/apps/admin/lib/csrf-cookie.server.ts` | exact |
| `dashboard/lib/engine.server.ts` | service | request-response | `homelab/apps/admin/lib/audit.server.ts` (fetch wrapper style) | partial (new loopback client) |
| `dashboard/lib/owner.server.ts` | service | file-I/O | `homelab/apps/admin/lib/auth-allowlist.server.ts` | role-match |
| `dashboard/lib/telegram-widget.server.ts` | utility | n/a | `bot/dashboard/auth.py` (HMAC logic) | role-match cross-language port |
| `dashboard/lib/hub-tree.server.ts` | service | file-I/O | RESEARCH Pattern 5 (realpath+DENY) | no direct analog |
| `dashboard/lib/dashboard-token.server.ts` | utility | n/a | inline in `bot/dashboard/deps.py` | role-match |
| `dashboard/playwright.config.ts` | config | n/a | none (new; Wave 0) | no analog |
| `dashboard/tests/e2e/*.spec.ts` | test | n/a | none (new) | no analog |
| `dashboard/lib/*.test.ts` | test | n/a | `homelab/apps/admin/lib/csrf.server.test.ts` | role-match |

### Modified files (Python engine + deploy)

| File | Role | Data Flow | Closest Analog | Match Quality |
|------|------|-----------|----------------|---------------|
| `bot/dashboard/app.py` | service | request-response | current FastAPI app; **demoted to loopback-only** | self-reference |
| `bot/dashboard/*_routes.py` | route | — | **deleted** or collapsed into internal RPC | self-reference |
| `bot/dashboard/auth.py` | — | — | **deleted** (HMAC ported to TS) | self-reference |
| `bot/dashboard/forms.py` | — | — | **deleted** (replaced by zod) | self-reference |
| `bot/dashboard/templates/*` | — | — | **deleted** | self-reference |
| `bot/dashboard/static/*` | — | — | **deleted** | self-reference |
| `bot/main.py` | config | n/a | current startup (supervises subprocesses) | self-reference — add `next start` spawn + internal port env |
| `docker/Dockerfile.bot` | config | n/a | `homelab/apps/admin/` Bun install recipe (implicit) | partial |
| `docker/docker-compose.yml` | config | n/a | current compose | self-reference |
| `pyproject.toml` | config | n/a | self | self-reference — drop `itsdangerous`, `jinja2`, `fastapi` HTTP deps (keep FastAPI as internal shim) |

## Pattern Assignments

### `dashboard/package.json` (config)

**Analog:** `/Users/admin/hub/workspace/homelab/apps/admin/package.json` (lines 1-55)

Copy verbatim with 3 deltas:
- `"name": "@animaya/dashboard"` (line 2)
- `"dev"` / `"start"` scripts: `-p 8090 -H 127.0.0.1` (spec verbatim)
- Add 0 dependencies — dep list matches spec §2 = admin verbatim (D-13)

### `dashboard/middleware.ts` (middleware, request-response)

**Analog:** `homelab/apps/admin/middleware.ts` (full file)

**Shape to copy** (lines 52-118): public-path allowlist → getToken → redirect to `/login` or `/403` → issue CSRF cookie → apply security headers.

**Deltas:**
1. Insert `DASHBOARD_TOKEN` bypass at top of handler (per RESEARCH Pattern 3):
```ts
const token = req.headers.get("x-dashboard-token") ?? url.searchParams.get("token");
if (token && process.env.DASHBOARD_TOKEN && token === process.env.DASHBOARD_TOKEN) {
  return applySecurityHeaders(NextResponse.next({ request: { headers: requestHeaders } }), nonce);
}
```
2. Rename CSRF cookie `hla-csrf` → `an-csrf` (line 103, 108)
3. Replace `isLoginAllowedEdge` with `isOwnerTelegramIdEdge(token.sub)` reading `process.env.OWNER_TELEGRAM_ID` (Phase 11 contract).
4. Adjust CSP `img-src` — remove `avatars.githubusercontent.com`; allow Telegram CDN if widget renders avatar inline, else `'self' data:` only.
5. `x-user-login` → `x-user-telegram-id`.

### `dashboard/auth.ts` (provider, request-response)

**Analog:** `homelab/apps/admin/auth.ts` (lines 1-41)

**Shape to copy:** `NextAuth({...authConfig, callbacks, cookies})` with `__Secure-authjs.session-token` cookie (lines 27-40 verbatim).

**Deltas:**
- `signIn` callback reads `payload.id` (from Credentials authorize) and compares to `await readOwnerId()` (per RESEARCH Pattern 2 + D-07).
- `jwt`/`session` callbacks set `token.telegramId` / `session.user.id` instead of `login`.

### `dashboard/auth.config.ts` (config)

**Analog:** `homelab/apps/admin/auth.config.ts` (lines 1-20)

**Delta:** Replace the `GitHub({...})` provider with `Credentials({ id: "telegram", name: "Telegram", credentials: {}, authorize })` per RESEARCH Pattern 2 (lines 254-273 of 13-RESEARCH.md). Keep `session: { strategy: "jwt", maxAge: 60*60*8 }`, `trustHost: true`, `authorized: ({auth}) => !!auth` verbatim.

### `dashboard/lib/telegram-widget.server.ts` (utility)

**Analog:** `/Users/admin/hub/workspace/animaya/bot/dashboard/auth.py` (HMAC logic — not session cookie; read the `verify_telegram_auth` function there)

**Port shape:**
```ts
import "server-only";
import crypto from "node:crypto";

export type TelegramPayload = { id: number; first_name?: string; auth_date: number; hash: string; [k: string]: unknown };

export function verifyTelegramWidget(raw: unknown, botToken: string): TelegramPayload | null {
  // 1. Type-narrow raw → extract `hash`, sort remaining keys, build `key=value\n` data-check-string.
  // 2. secret = crypto.createHash("sha256").update(botToken).digest();
  // 3. expected = crypto.createHmac("sha256", secret).update(dataCheckString).digest("hex");
  // 4. crypto.timingSafeEqual(Buffer.from(expected,"hex"), Buffer.from(hash,"hex"))
  // 5. auth_date freshness: (now - auth_date) <= 86400
}
```

Constant-time compare equivalent to Python `hmac.compare_digest`.

### `dashboard/lib/csrf.server.ts` (utility)

**Analog:** `homelab/apps/admin/lib/csrf.server.ts` (lines 1-100, near-verbatim)

Copy verbatim; only deltas are the 3 constants in `csrf.shared.ts`:
- `CSRF_COOKIE_NAME = "an-csrf"` (was `hla-csrf`)
- `CSRF_HEADER_NAME = "x-csrf-token"` (same)
- `EXPECTED_ORIGIN = process.env.ANIMAYA_PUBLIC_ORIGIN ?? "https://animaya.makscee.ru"`

Preserve the defense-in-depth order (origin → cookie → header → constant-time compare, lines 66-100).

### `dashboard/app/api/*/route.ts` (route, request-response)

**Analog:** `homelab/apps/admin/app/api/tokens/route.ts` (full file, lines 1-84)

**Pattern to copy for every mutation route** (lines 27-84):
```ts
export const runtime = "nodejs";
const InputSchema = z.object({ /* ... */ });
export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  try { verifyCsrf(req); } catch (e) {
    if (e instanceof CsrfError) return NextResponse.json({ error: "forbidden" }, { status: 403 });
    throw e;
  }
  const body = await req.json().catch(() => null);
  const parsed = InputSchema.safeParse(body);
  if (!parsed.success) return NextResponse.json({ error: "invalid input", issues: parsed.error.issues }, { status: 400 });
  try {
    const result = await engineFetch("/engine/<verb>", { method: "POST", body: JSON.stringify({ ...parsed.data, session_key: `web:${session.user.id}` }) });
    // ... return sanitized DTO
  } catch (e) {
    return NextResponse.json({ error: sanitizeErrorMessage(String(e)) }, { status: 400 });
  }
}
```
Always-inject `session_key: web:<id>` at the engine boundary for SEC-02.

### `dashboard/app/api/chat/stream/route.ts` (route, streaming)

**Analog:** RESEARCH Pattern 4 (13-RESEARCH.md lines 287-301) + token route shape above

```ts
export const runtime = "nodejs";
export async function POST(req: Request) {
  const session = await auth();
  if (!session?.user?.id) return new Response("", { status: 401 });
  verifyCsrf(req as NextRequest);
  const body = await req.json();
  const upstream = await engineFetch("/engine/chat", {
    method: "POST",
    body: JSON.stringify({ ...body, session_key: `web:${session.user.id}` }),
  });
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store", "X-Accel-Buffering": "no" },
  });
}
```
Heartbeat `:ping\n\n` every 15s handled upstream or via TransformStream wrapper.

### `dashboard/lib/engine.server.ts` (service, request-response)

**Analog:** RESEARCH Pattern 1 (lines 240-247)

```ts
import "server-only";
const ENGINE_URL = process.env.ANIMAYA_ENGINE_URL ?? "http://127.0.0.1:8091";
export async function engineFetch(path: string, init?: RequestInit) {
  return fetch(`${ENGINE_URL}${path}`, { cache: "no-store", ...init });
}
```

### `dashboard/lib/owner.server.ts` (service, file-I/O)

**Analog:** `homelab/apps/admin/lib/auth-allowlist.server.ts` (not fully shown but referenced from auth.ts line 3)

**Shape:**
```ts
import "server-only";
import fs from "node:fs/promises";
import path from "node:path";
const OWNER_PATH = path.resolve(process.env.HOME!, "hub/knowledge/animaya/OWNER.md");
let cached: string | null = null;
export async function readOwnerId(): Promise<string | null> {
  if (cached !== null) return cached;
  try {
    const raw = await fs.readFile(OWNER_PATH, "utf8");
    // Parse Phase 11 OWNER.md format — telegram_id line
    const match = raw.match(/telegram_id:\s*(\d+)/i);
    cached = match ? match[1] : null;
    return cached;
  } catch { return null; }
}
```

### `dashboard/lib/hub-tree.server.ts` (service, file-I/O)

**Analog:** RESEARCH Pattern 5 (13-RESEARCH.md lines 304-320) — no existing TS analog; pattern is from the spec.

Copy the `safeResolve` function verbatim. Also implement `listDir(rel)` returning `{name, type, size}[]` filtered by dotfile flag + DENY set.

### `dashboard/components/ui/*.tsx` (component × 19)

**Analog:** `/Users/admin/hub/workspace/homelab/apps/admin/components/ui/*.tsx` (all of: alert-dialog, alert, avatar, badge, button, card, dialog, dropdown-menu, form, input, label, progress, select, skeleton, sonner, table, textarea, tooltip)

**Pattern:** Copy every file verbatim per D-14. All use `cva` + `cn()` + Radix primitives. No edits.

### `dashboard/app/(auth)/layout.tsx` (component)

**Analog:** `homelab/apps/admin/app/(auth)/layout.tsx` (full file, lines 1-16) — copy verbatim.

### `dashboard/app/(public)/login/page.tsx` (component)

**Analog:** `homelab/apps/admin/app/(public)/login/page.tsx` (lines 1-26)

**Delta:** Replace the `signIn("github", ...)` server action form with a Telegram Login Widget. Telegram's widget script posts to a callback URL → that callback runs `signIn("telegram", { redirect: false, ...payload })`. Widget embed snippet:
```tsx
<script async src="https://telegram.org/js/telegram-widget.js?22"
  data-telegram-login={process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME}
  data-size="large" data-auth-url="/api/auth/callback/telegram" data-request-access="write" />
```

### `dashboard/next.config.mjs` (config)

**Analog:** `homelab/apps/admin/next.config.mjs` (lines 1-46)

**Delta:** Drop the webpack `bun:sqlite` shim (lines 16-43) — Animaya doesn't use SQLite from Bun. Keep:
```js
output: 'standalone',
reactStrictMode: true,
poweredByHeader: false,
```

### `dashboard/eslint.config.mjs`, `tsconfig.json`, `postcss.config.mjs`, `bunfig.toml`, `components.json`, `app/globals.css`, `test-setup.ts`

Copy all verbatim from `homelab/apps/admin/` — zero edits (these are spec-verbatim files per D-12/D-13/D-14).

## Shared Patterns

### Authentication — server components / RSC

**Source:** `homelab/apps/admin/app/api/tokens/route.ts` lines 30-33
**Apply to:** Every `app/api/**/route.ts` and every server action.
```ts
const session = await auth();
if (!session?.user?.id) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
```

### CSRF — double-submit verify

**Source:** `homelab/apps/admin/lib/csrf.server.ts` (verifyCsrf) + `app/api/tokens/route.ts` lines 36-43
**Apply to:** Every mutation route (POST/PUT/DELETE).
```ts
try { verifyCsrf(req); } catch (e) {
  if (e instanceof CsrfError) return NextResponse.json({ error: "forbidden" }, { status: 403 });
  throw e;
}
```

### Input validation — zod at trust boundary

**Source:** `homelab/apps/admin/app/api/tokens/route.ts` lines 15-25, 51-58
**Apply to:** Every route handler + every form submit.
```ts
const Schema = z.object({ /* ... */ });
const parsed = Schema.safeParse(body);
if (!parsed.success) return NextResponse.json({ error: "invalid input", issues: parsed.error.issues }, { status: 400 });
```

### Error redaction

**Source:** `homelab/apps/admin/lib/redact.server.ts` (referenced in tokens/route.ts line 82)
**Apply to:** Every `catch` that returns error text to client.
Port analog (regex-based secret scrub) or write a minimal `sanitizeErrorMessage` that strips Telegram bot tokens + Claude OAuth tokens + long hex sequences.

### Class composition

**Source:** `homelab/apps/admin/lib/utils.ts` (full file, 6 lines)
**Apply to:** Every component.
```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

### `server-only` guard

**Source:** `homelab/apps/admin/eslint.config.mjs` (lines 9-41) + every `*.server.ts` file
**Apply to:** All files ending `.server.ts(x)`. First statement must be `import "server-only";`.

### Security headers + CSP nonce

**Source:** `homelab/apps/admin/middleware.ts` lines 22-50
**Apply to:** Every request through middleware. Keep the same header set (CSP, HSTS 2y preload, X-Frame-Options DENY, X-Content-Type-Options, Referrer-Policy, Permissions-Policy).

### Session-key namespacing (SEC-02)

**Source:** RESEARCH Pattern 4 line 295
**Apply to:** Every engine RPC call from a route handler.
```ts
body: JSON.stringify({ ...parsed.data, session_key: `web:${session.user.id}` })
```

### Telegram widget HMAC (port of `bot/dashboard/auth.py`)

**Source:** `bot/dashboard/auth.py` (HMAC verify function — not the itsdangerous cookie portion)
**Apply to:** `dashboard/lib/telegram-widget.server.ts` only. Node `crypto.createHash("sha256")` + `crypto.createHmac("sha256", secret)` + `crypto.timingSafeEqual`. Mirror Python's sorted `key=value\n` data-check-string construction exactly.

## No Analog Found

| File | Role | Data Flow | Planner Guidance |
|------|------|-----------|-------------------|
| `dashboard/app/(auth)/_components/chat-panel.tsx` | component | streaming | Build from RESEARCH Pattern 4; consume `EventSource` or fetch+ReadableStream; render tool-use events inline with shadcn Card |
| `dashboard/app/(auth)/_components/hub-tree.tsx` | component | request-response | Claude's-discretion per D-12; collapsible tree backed by `/api/hub/tree`; dotfile toggle persisted in localStorage |
| `dashboard/app/(auth)/_components/tool-use-event.tsx` | component | n/a | Presentation only; reuse `components/ui/card.tsx` + `lucide-react` icons |
| `dashboard/app/(auth)/_lib/use-sse.ts` | hook | streaming | Claude's-discretion per CONTEXT; implement fetch+ReadableStream with reconnect-on-close |
| `dashboard/playwright.config.ts` | config | n/a | Standard Playwright init; no admin analog |
| Engine loopback HTTP shim (Python side, e.g. `bot/engine/http.py`) | service | request-response | New FastAPI app bound to `127.0.0.1:<ANIMAYA_ENGINE_PORT>`; reuse existing `bot/dashboard/app.py` handlers' business logic, strip auth (loopback-only trust), reshape to `/engine/*` prefix |
| Shared UI style spec output (`~/hub/knowledge/references/ui-style-spec.md`) | docs | n/a | Extract from `homelab/apps/admin/app/globals.css` + `components.json` + `components/ui/*` inventory |

## Analog Search Scope

**Directories scanned:**
- `/Users/admin/hub/workspace/homelab/apps/admin/` (full tree — primary analog)
- `/Users/admin/hub/workspace/animaya/bot/dashboard/` (legacy being replaced)
- `/Users/admin/hub/knowledge/references/frontend-stack-spec.md` (via RESEARCH.md excerpts)

**Files scanned:** ~60 (admin ui components + lib + app routes + config; animaya dashboard Python modules + templates)

**Pattern extraction date:** 2026-04-17
