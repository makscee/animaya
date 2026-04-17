# Phase 13: Migrate dashboard frontend to shared frontend-stack-spec - Research

**Researched:** 2026-04-17
**Domain:** Frontend migration (FastAPI+Jinja -> Next.js 15.5.15 / React 19.2.5 / Tailwind v4 / Bun) following `~/hub/knowledge/references/frontend-stack-spec.md`
**Confidence:** HIGH (spec, reference implementation, and current code all on-disk)

## Summary

This phase replaces the entire Animaya HTTP surface. Today that surface is a FastAPI app (`bot/dashboard/*`) rendering Jinja templates with HTMX fragments, an `itsdangerous`-signed cookie for Telegram Login Widget auth, and a not-yet-implemented SSE chat. It must become a Next.js 15.5.15 app under Bun, structured exactly like `/Users/admin/hub/workspace/homelab/apps/admin` (the spec's reference implementation): App Router with `(auth)` / `(public)` route groups, shadcn/ui primitives pulled verbatim from admin, Tailwind v4 CSS-first, slate palette, dark-only theme, next-auth v5 beta.31 with a **custom Telegram Login Widget provider**, double-submit CSRF middleware (`an-csrf`), and `*.server.ts` modules gated by the inline ESLint rule. FastAPI is demoted to an internal loopback engine; Next.js is the only process bound to port 8090.

Two project-specific twists the spec does not cover: (1) Telegram Login Widget is not in `next-auth/providers` -- a custom provider must wrap Telegram's HMAC-SHA256 check (ported from `bot/dashboard/auth.py`); (2) Phase 12 SSE chat and Hub file tree are built **in this phase** under Next.js route handlers -- Phase 13 lands before Phase 12 per D-09.

**Primary recommendation:** Port `homelab/apps/admin` verbatim where possible (deps, configs, `components/ui/*`, `middleware.ts` shape, `auth.ts/auth.config.ts` split). Diverge only on: (a) custom Telegram credentials provider, (b) `DASHBOARD_TOKEN` header/query bypass in middleware, (c) SSE route handler proxying to internal Python loopback, (d) OWNER.md-backed `signIn` gate, (e) CSRF cookie renamed `an-csrf`. Everything else is a file-copy + find/replace exercise.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Backend & Deploy**
- D-01: Next.js owns the entire public HTTP surface (SSR + route handlers + SSE). FastAPI demoted to an internal engine process (bot runtime, Claude Code SDK bridge, module registry). No FastAPI route is reachable from outside the container after this phase.
- D-02: Next.js runs as a separate Bun process inside the bot container. Start script matches the spec verbatim: `next start -p 8090 -H 127.0.0.1`. Caddy / Voidnet reverse proxy keeps pointing at port 8090.
- D-03: Phase 12 SSE chat is served by a Next.js route handler (`/api/chat/stream` or equivalent), NOT by the current FastAPI SSE bus. The Python engine exposes a local-loopback endpoint the route handler proxies to.
- D-04: Next.js takes port 8090. The Python engine moves to an internal loopback port (exact number — Claude's discretion).

**Auth**
- D-05: Auth primitive = `next-auth` `5.0.0-beta.31` with a custom Telegram Login Widget provider.
- D-06: `DASHBOARD_TOKEN` env override is preserved. Middleware checks header/query token first, falls back to the next-auth session. Required for scripted ops and token-based deploys.
- D-07: Owner identity is sourced from `OWNER.md` (Phase 11 output). `signIn` rejects Telegram IDs that don't match the recorded owner. No first-login-wins fallback in this phase.

**Migration**
- D-08: Big-bang cutover. Phase ends with `bot/dashboard/templates/`, `bot/dashboard/static/`, and every FastAPI HTTP route under `bot/dashboard/*_routes.py` / `bot/dashboard/app.py` deleted or reduced to internal engine RPC only. Jinja + `itsdangerous` auth + `StaticFiles` mount all go.
- D-09: ROADMAP REORDER — Phase 13 must land before Phase 12. Phase 12 (SSE chat + Hub file tree) is built natively in Next.js.
- D-10: Feature parity, design flexible. Every capability of the current dashboard plus Phase 12 chat+tree is reproduced, but visual design may change where it improves UX. No new capabilities slip in under "redesign."
- D-11: Test surface = Playwright E2E against live `next start`. Existing pytest dashboard HTTP tests are retired as part of the cutover; pytest remains for Python engine / bot runtime.

**UI Style & Components**
- D-12: `~/hub/knowledge/voidnet/ui-spec.md` declared obsolete. A new shared UI style spec is authored IN this phase, extracted from `/Users/admin/hub/workspace/homelab/apps/admin` (tokens, Tailwind config, theme behavior). Target location: `~/hub/knowledge/references/ui-style-spec.md` (final name Claude's discretion). Animaya consumes the spec from that path.
- D-13: Full Radix primitive set from the spec installed up front (alert-dialog, avatar, dialog, dropdown-menu, label, progress, select, slot, tooltip) plus `lucide-react`. No on-demand drip.
- D-14: `components/ui/*` ported from `homelab/apps/admin` verbatim (Button, Card, Dialog, Form, Input, etc.) using `cva` + `tailwind-merge` + `clsx` patterns.
- D-15: Forms = `react-hook-form` + `zod` + `@hookform/resolvers` for all non-trivial forms (bridge_config, module config, login if it has inputs).

### Claude's Discretion
- Internal loopback port number for the Python engine.
- Exact shape of the Hub file-tree React component (tree state, dotfile toggle, expansion persistence).
- SSE reconnection strategy and tool-use inline rendering layout (constrained by Phase 12 success criteria).
- Error boundary placement and loading-state patterns.
- Whether Phase 12's owner-lock coordination lives in Next.js middleware or the engine RPC.
- Exact filename of the new shared UI style spec.

### Deferred Ideas (OUT OF SCOPE)
- Cleanup of obsolete `~/hub/knowledge/voidnet/ui-spec.md` (separate hub-repo task).
- Post-parity visual polish (motion, accessibility beyond Radix defaults, token refinement).
- Voidnet admin adopting the new shared UI style spec.
- Migrating homelab/apps/admin onto the new shared spec file.
- Replacing `DASHBOARD_TOKEN` bypass with a proper service-account auth model.
</user_constraints>

<phase_requirements>
## Phase Requirements

Phase 13 has no dedicated `REQ-*` IDs in REQUIREMENTS.md. It inherits and must satisfy:

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Unified chat + Hub file tree page | App Router `(auth)/chat/page.tsx` with split layout; tree component (§Discretion) |
| DASH-02 | SSE chat with inline tool-use | Next.js route handler streaming via Web Streams API; Python engine loopback |
| DASH-03 | Hub file tree (collapsible, dotfiles-hidden, read-only) | Server Component + client tree, path-validated server action |
| DASH-04 | Path traversal / symlink / DENY set | Server-only `hub-tree.server.ts` with `Path.resolve().is_relative_to` equivalent (Node `path.resolve` + `fs.realpath`) |
| SEC-01 | Bot-token redaction preserved | Port `SecretStr` handling into zod schemas returning redacted DTOs |
| SEC-02 | Session keys namespaced `tg:<id>` / `web:<id>` | Route handler injects `web:` prefix before calling engine RPC |
| (from CONTEXT D-07) | Owner gate via `OWNER.md` | `lib/owner.server.ts` reads `~/hub/knowledge/animaya/OWNER.md`, compared in `signIn` callback |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Public HTTP surface (auth, pages, APIs) | Next.js (Node/Bun server) | — | D-01: only process bound to :8090 |
| Session / cookies / CSRF | Next.js middleware | next-auth JWT | Edge-safe middleware per spec §8 |
| Telegram Login Widget HMAC check | Next.js custom credentials provider | — | No stock provider exists; must port `bot/dashboard/auth.py` logic |
| Claude Code SDK invocation | Python engine (loopback) | Next.js route handler (proxy) | Python already owns SDK; no JS port |
| SSE stream to browser | Next.js route handler (Web Streams) | Python engine (async generator via loopback HTTP) | D-03 |
| Module install/uninstall | Next.js route handler (server action) | Python engine RPC | D-01 |
| Hub file tree walk + validation | Next.js `*.server.ts` (filesystem) | — | Filesystem is local to container; no round-trip needed |
| Git auto-commit (`/data` writer thread) | Python engine | — | Unchanged (`bot/features/git_versioning.py`) |
| Tool-use inline render | React client component | — | Client-only state; SSE events drive it |
| Owner-claim FSM, pairing code | Python engine | Next.js route handler (thin proxy) | Logic stays in module runtime; dashboard just displays |

## Standard Stack

### Core (verbatim from frontend-stack-spec.md §2)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| next | 15.5.15 | SSR, route handlers, App Router | spec-pinned [CITED: frontend-stack-spec.md §2] |
| react / react-dom | 19.2.5 | UI | spec-pinned |
| next-auth | 5.0.0-beta.31 | Session, auth callbacks | spec-pinned; D-05 |
| @auth/core | ^0.34.3 | next-auth runtime | spec-pinned |
| tailwindcss | ^4.2.2 | Styling (CSS-first, no JS config) | spec-pinned |
| @tailwindcss/postcss | ^4.2.2 | Tailwind PostCSS plugin | spec-pinned |
| typescript | ^6.0.3 | Type checking | spec-pinned |
| eslint | ^10.2.0 | Flat config, inline `server-only` rule | spec-pinned |
| @radix-ui/react-* (9 pkgs) | per spec | Primitives behind shadcn | D-13 |
| class-variance-authority | ^0.7.1 | Component variants | D-14 |
| tailwind-merge | ^3.0.0 | `cn()` helper | D-14 |
| clsx | ^2.1.1 | `cn()` helper | D-14 |
| lucide-react | ^1.8.0 | Icons | spec §10 |
| react-hook-form | ^7.72.1 | Forms | D-15 |
| zod | ^4.3.6 | Validation at trust boundaries | D-15 |
| @hookform/resolvers | ^5.2.2 | RHF <-> zod glue | D-15 |
| swr | ^2.4.1 | Client polling (modules list, status) | spec §9 |
| sonner | ^2.0.7 | Toasts | spec §5 |
| next-themes | ^0.4.6 | Theme surface (installed, unused) | spec §12 |
| server-only | ^0.0.1 | Marker for `*.server.ts` | spec §6 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| recharts | ^3.8.1 | Charts | Only if Phase 13 surfaces any metrics; likely unused at this phase |
| @types/bun | ^1.3.12 | Bun types in tsconfig | Required by spec §7 |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom Telegram provider | `TeaByte/telegram-auth-nextjs` (third-party) | Third-party package not in spec -> violates spec §2 "no latest, no drift"; reject. Port HMAC check inline. |
| Web Streams SSE | `sse-starlette` (current plan-v12) | D-03 mandates Next.js owns SSE; Python only exposes internal HTTP. |
| `@vercel/ai` / SDK | — | Not in spec; Claude SDK is Python-only; use raw `ReadableStream`. |
| tailwindcss-animate | — | Removed in spec §14; do not install. |

**Installation (one shot, matches admin `package.json`):**
```bash
cd dashboard && bun install
# deps must match spec §2 verbatim -- no drift
```

**Version verification:**
Spec was last updated from homelab/apps/admin on 2026-04-17 (today). Admin `package.json` matches spec §2 exactly [VERIFIED: file read 2026-04-17]. Treat spec as authoritative; do **not** bump versions without updating the spec first (spec §15).

## Architecture Patterns

### System Architecture Diagram

```
 Internet
    |
    v
 Caddy (Voidnet, external) --(443 -> :8090)-->
    |
    v
 +------------------------------------------------+
 |  Animaya container                             |
 |                                                |
 |   Next.js (Bun) :8090  <-- public surface      |
 |     |                                          |
 |     |  middleware.ts                           |
 |     |   - DASHBOARD_TOKEN header/query bypass  |
 |     |   - next-auth JWT check                  |
 |     |   - an-csrf double-submit cookie         |
 |     |   - x-user-login header injection        |
 |     v                                          |
 |   Route handlers / Server Components           |
 |     |                                          |
 |     +--- fs: ~/hub/ (tree walk, read-only)     |
 |     |                                          |
 |     +--- loopback HTTP --> Python engine :ZZZZ |
 |                                |               |
 |                                v               |
 |                         FastAPI (internal)     |
 |                          - Claude Code SDK     |
 |                          - module registry     |
 |                          - owner-claim FSM     |
 |                          - SSE generator       |
 |                          - git auto-commit     |
 |                                                |
 +------------------------------------------------+
```

Data flow (SSE chat turn): browser POST `/api/chat/stream` -> Next.js handler validates session + CSRF -> opens ReadableStream, proxies to `POST http://127.0.0.1:ZZZZ/engine/chat` -> Python engine runs Claude SDK, yields events -> Next.js relays SSE frames (injects `web:<user_id>` session key) -> browser renders tool-use + text.

### Recommended Project Structure

```
dashboard/                              # NEW top-level dir (replaces bot/dashboard/)
├── app/
│   ├── (auth)/
│   │   ├── _components/                # chat-panel.tsx, hub-tree.tsx, tool-use-event.tsx
│   │   ├── _lib/                       # client hooks (use-sse.ts)
│   │   ├── layout.tsx                  # TopBar + Sidebar
│   │   ├── page.tsx                    # Home (status strip, activity feed)
│   │   ├── chat/page.tsx               # DASH-01 unified page
│   │   ├── modules/page.tsx            # Modules list (replaces modules.html)
│   │   ├── modules/[name]/page.tsx     # Module detail
│   │   └── bridge/page.tsx             # Bridge settings (Phase 10 surface)
│   ├── (public)/
│   │   ├── login/page.tsx              # Telegram Login Widget
│   │   └── 403/page.tsx
│   ├── api/
│   │   ├── auth/[...nextauth]/route.ts # next-auth handlers
│   │   ├── chat/stream/route.ts        # SSE proxy
│   │   ├── hub/tree/route.ts           # Tree fetch (server-only fs)
│   │   ├── hub/file/route.ts           # Single-file read
│   │   ├── modules/route.ts            # list
│   │   ├── modules/[name]/install/route.ts
│   │   ├── modules/[name]/uninstall/route.ts
│   │   ├── modules/[name]/config/route.ts
│   │   └── bridge/*                    # claim/revoke/regen/toggle/policy
│   ├── globals.css                     # spec §4 verbatim, an- palette if needed
│   ├── layout.tsx                      # <html className="dark">
│   ├── error.tsx
│   └── not-found.tsx
├── components/
│   ├── ui/                             # shadcn verbatim from admin
│   └── layout/                         # topbar.tsx, sidebar.tsx, nav-items.ts
├── lib/
│   ├── utils.ts                        # cn() per spec §9
│   ├── engine.server.ts                # Python loopback HTTP client
│   ├── owner.server.ts                 # reads OWNER.md
│   ├── hub-tree.server.ts              # DASH-04 validation
│   ├── csrf.server.ts
│   ├── csrf-cookie.server.ts
│   ├── telegram-widget.server.ts       # HMAC check (port of auth.py)
│   └── dashboard-token.server.ts       # D-06 override check
├── types/
├── middleware.ts
├── auth.ts
├── auth.config.ts
├── bunfig.toml
├── components.json                     # spec §5 verbatim
├── eslint.config.mjs                   # spec §7 verbatim
├── next.config.mjs                     # output: 'standalone'
├── package.json                        # spec §2 verbatim
├── postcss.config.mjs                  # spec §3 one-liner
└── tsconfig.json                       # spec §7 verbatim
```

### Pattern 1: Server-only modules
**What:** Files ending `.server.ts` must `import "server-only";` at top (enforced by inline ESLint rule).
**When:** Any filesystem, secret, env-key, or Python-loopback access.
**Example:**
```ts
// lib/engine.server.ts
import "server-only";
const ENGINE_URL = process.env.ANIMAYA_ENGINE_URL ?? "http://127.0.0.1:8091";
export async function engineFetch(path: string, init?: RequestInit) {
  return fetch(`${ENGINE_URL}${path}`, { cache: "no-store", ...init });
}
```

### Pattern 2: Custom Telegram Login Widget provider (port `bot/dashboard/auth.py`)
**What:** `next-auth` has no stock Telegram provider; Telegram returns `{ id, first_name, auth_date, hash, ... }` after widget OAuth. Validation = HMAC-SHA256 with the bot token's SHA256 as the secret [CITED: core.telegram.org/widgets/login].
**When:** Only place raw Telegram widget data is trusted.
**Example:**
```ts
// auth.ts (excerpt)
import Credentials from "next-auth/providers/credentials";
import { verifyTelegramWidget } from "@/lib/telegram-widget.server";
import { readOwnerId } from "@/lib/owner.server";

providers: [
  Credentials({
    id: "telegram",
    name: "Telegram",
    credentials: {}, // payload comes via form POST from widget callback
    async authorize(raw) {
      const payload = verifyTelegramWidget(raw, process.env.TELEGRAM_BOT_TOKEN!);
      if (!payload) return null;
      const ownerId = await readOwnerId(); // OWNER.md, Phase 11
      if (String(payload.id) !== String(ownerId)) return null; // D-07
      return { id: String(payload.id), name: payload.first_name };
    },
  }),
]
```

### Pattern 3: `DASHBOARD_TOKEN` bypass in middleware (D-06)
```ts
// middleware.ts (excerpt)
const url = new URL(req.url);
const token = req.headers.get("x-dashboard-token") ?? url.searchParams.get("token");
if (token && token === process.env.DASHBOARD_TOKEN) {
  return NextResponse.next(); // bypass auth
}
// ... otherwise fall through to getToken({ ... })
```

### Pattern 4: SSE route handler proxying to Python engine
```ts
// app/api/chat/stream/route.ts
export const runtime = "nodejs"; // not edge; need server-only + long streams
export async function POST(req: Request) {
  const session = await auth(); if (!session) return new Response("", { status: 401 });
  const body = await req.json();
  const upstream = await engineFetch("/engine/chat", {
    method: "POST",
    body: JSON.stringify({ ...body, session_key: `web:${session.user.id}` }), // SEC-02
  });
  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-store" },
  });
}
```

### Pattern 5: Hub file-tree path validation (DASH-04)
```ts
// lib/hub-tree.server.ts
import "server-only";
import path from "node:path"; import fs from "node:fs/promises";
const HUB_ROOT = path.resolve(process.env.HOME!, "hub");
const DENY = [".git/hooks", ".ssh"]; const DENY_PREFIX = [".env"];
export async function safeResolve(rel: string): Promise<string> {
  const abs = path.resolve(HUB_ROOT, rel);
  const real = await fs.realpath(abs);           // rejects symlink escapes
  if (!real.startsWith(HUB_ROOT + path.sep) && real !== HUB_ROOT) throw new Error("escape");
  for (const seg of real.slice(HUB_ROOT.length).split(path.sep)) {
    if (DENY.some((d) => real.includes(`${path.sep}${d}`))) throw new Error("deny");
    if (DENY_PREFIX.some((p) => seg.startsWith(p))) throw new Error("deny");
  }
  return real;
}
```

### Anti-Patterns to Avoid
- **Leaving any FastAPI HTTP route public.** D-01 / D-08 forbid it. FastAPI binds only to loopback.
- **`tailwind.config.ts` file.** Spec §3: Tailwind v4 is CSS-first; `components.json` references it only for shadcn CLI. File must not exist.
- **`autoprefixer`, `tailwindcss-animate`, `eslint-plugin-server-only`.** Spec §14 forbids.
- **Edge runtime for SSE.** Use `runtime = "nodejs"` in chat route -- streaming lifetimes and `server-only` modules are incompatible with Edge.
- **Polling Claude SDK from JS.** Python engine stays the only SDK client; JS only proxies bytes.
- **`npm install` or `npm run`.** Bun is the package manager (spec §1).
- **Skipping `trustHost: true`.** Without it, next-auth rejects requests behind Caddy (spec §8).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Session cookies | Custom JWT | `next-auth@5.0.0-beta.31` | D-05 |
| CSRF | Custom token store | Double-submit cookie per spec §9 (`an-csrf`) | Already-validated pattern in admin |
| Form state + validation | `useState` hell | `react-hook-form` + `zod` + `@hookform/resolvers` | D-15, spec §9 |
| Markdown rendering in chat | Hand parser | Existing choice in admin (inspect) or `react-markdown` -- pick one that admin uses; if none, `react-markdown` is acceptable but propose in plan | Telegram bridge already uses `bot/bridge/formatting.py` -- JS side needs equivalent for chat |
| Icons | Inline SVG | `lucide-react` | Spec §10 |
| Toasts | Custom | `sonner` | Spec §5 |
| Dropdowns/Modals | Custom | Radix primitives through `components/ui/*` | Spec §5 / D-14 |
| Class composition | String concat | `cn()` (`clsx` + `twMerge`) | Spec §9 |
| File-walk | `readdir` + manual join | Still `fs/promises` but centralized in `hub-tree.server.ts` with `realpath` | DASH-04 safety |

**Key insight:** The spec is prescriptive; each "don't hand-roll" above already has an approved library pinned. Deviating is a spec violation.

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `/data/sessions/{session_id}.json` (chat history, used by current dashboard `/api/chat/history`); `.embeddings.json` under `/data/memory/`; git repo at `/data/.git` | Read-only access from Next.js route handlers; schema stays identical. No data migration. |
| Live service config | `config.json` per module in `/data/modules/<id>/config.json`; `state.json` per module (owner_id, pairing code) | Next.js does NOT own these files -- Python engine remains writer. Next.js reads via engine RPC only. |
| OS-registered state | None. Bot runs as a single `python -m bot` process. After this phase: two processes (Bun + Python) inside the LXC -- supervisor (Phase 8) must start both. | **New:** add a `next start` invocation to the supervisor startup hook. Document in deploy. |
| Secrets / env vars | `TELEGRAM_BOT_TOKEN` (still required for widget HMAC), `CLAUDE_CODE_OAUTH_TOKEN`, `DASHBOARD_TOKEN` (D-06), `GOOGLE_API_KEY`, `STT_API_KEY`, `EMBEDDING_API_KEY`. Plus new: `AUTH_SECRET` (next-auth), `ANIMAYA_ENGINE_URL` or `ANIMAYA_ENGINE_PORT`. | Document `AUTH_SECRET` requirement in CLAUDE.md env list; generate at install time (`openssl rand -base64 32`). |
| Build artifacts / installed packages | `bot/dashboard/templates/` (delete), `bot/dashboard/static/` (delete), `bot.egg-info/` if stale after layout change. `.next/` build output new. `node_modules/` new. `bun.lockb` new (committed). | `docker/Dockerfile.bot` gains a Bun layer + `bun install` + `bun run build`; final image includes `.next/standalone` + `node_modules` (or standalone self-contains). Delete `bot/dashboard/templates/` + `bot/dashboard/static/` from the repo at cutover. |

**Critical cross-process concern:** the current dashboard uses an in-process `SSE event bus` and per-user `asyncio.Lock`. After D-03 those no longer serialize with Telegram turns because they're in different processes. Phase 12's owner-lock (DASH-02 success criterion "concurrent Telegram + dashboard turns serialize cleanly") therefore MUST live in the Python engine (not Next.js), exposed via the loopback. Flag as Claude's-discretion bullet.

## Common Pitfalls

### Pitfall 1: Telegram widget origin / domain mismatch
**What goes wrong:** Widget login callback `data-auth-url` must match the registered domain in `@BotFather /setdomain`. If the LXC's hostname / Caddy domain changes, widget stops returning payloads.
**Why:** Telegram validates the origin server-side before callback.
**How to avoid:** Install step must prompt for the public hostname, call `@BotFather /setdomain`, and persist it to the bridge module config.
**Warning sign:** Widget iframe loads, button click is a no-op.

### Pitfall 2: `middleware.ts` Edge runtime and server-only
**What goes wrong:** Importing any `*.server.ts` or `node:fs` from middleware breaks the Edge build.
**Why:** Middleware runs on the Edge runtime; `server-only` and Node APIs are banned there.
**How to avoid:** Middleware only calls `getToken()` and compares strings. `DASHBOARD_TOKEN` override is also a header/env compare. Any fs / engine call happens in route handlers (Node runtime).

### Pitfall 3: SSE over Caddy closes early
**What goes wrong:** Caddy's default idle timeout cuts long streams.
**How to avoid:** Confirm the existing Voidnet Caddy config allows SSE (check `flush_interval` / `transport http { read_timeout 0 }`). Add heartbeat `:ping\n\n` every 15 s in the route handler.

### Pitfall 4: `next start` bound to `0.0.0.0`
**What goes wrong:** Container exposes Next.js to LAN, bypassing Caddy's TLS.
**How to avoid:** Scripts in `package.json` MUST be spec-verbatim: `-H 127.0.0.1`. Caddy forwards to `127.0.0.1:8090` inside the container.

### Pitfall 5: next-auth beta breaking changes
**What goes wrong:** 5.0.0-beta.31 cookie name / callback signatures change between betas.
**How to avoid:** Pin exactly `5.0.0-beta.31` (spec). Do not `bun add next-auth@latest`. [CITED: authjs.dev/getting-started/migrating-to-v5]

### Pitfall 6: OWNER.md format drift
**What goes wrong:** Phase 11 hasn't shipped; OWNER.md format isn't locked. `readOwnerId()` could read a stale schema.
**How to avoid:** Phase 13 planning must review Phase 11's committed OWNER.md format; if Phase 11 hasn't landed yet at planning time, define the contract here and cross-link.

### Pitfall 7: Tailwind v4 `@tailwind base/components/utilities` directives leaking into globals
**What goes wrong:** Copying Animaya's old `style.css` into `globals.css` will include v3-style directives. v4 rejects them silently in some places.
**How to avoid:** `globals.css` is spec §4 verbatim -- nothing else. Port any bespoke Animaya CSS (minimal: see `bot/dashboard/static/style.css` is ~light) into component-level classes.

### Pitfall 8: Retiring pytest dashboard tests too early
**What goes wrong:** D-11 retires pytest HTTP tests, but some currently cover Phase 8/9 bridge behavior (pairing FSM). Deleting them without Playwright coverage loses regression protection.
**How to avoid:** Map each pytest test in `tests/dashboard/**` to a Playwright replacement (or an engine-level pytest that stays). Explicit retire list in the plan.

## Code Examples

All examples above (Patterns 1-5) are verified from:
- `frontend-stack-spec.md` (sections 2-9) [CITED]
- `homelab/apps/admin/auth.ts`, `middleware.ts`, `components/ui/*` [VERIFIED: file read]

Additional verified snippet -- `postcss.config.mjs` (spec §3):
```js
export default { plugins: { '@tailwindcss/postcss': {} } };
```

`lib/utils.ts` (spec §9):
```ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
export function cn(...inputs: ClassValue[]) { return twMerge(clsx(inputs)); }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Jinja + HTMX fragments | Next.js RSC + Server Actions / SWR | This phase | Full rewrite of view layer |
| `tailwind.config.ts` JS config | Tailwind v4 CSS-first (`@theme` in globals.css) | Tailwind v4 (2024) | No JS config file; plugins via PostCSS only |
| `eslint-plugin-server-only` | Inline flat-config rule (spec §7) | ESLint 10 | Plugin broken on ESLint 10 |
| `itsdangerous` signed cookie | `next-auth` JWT + middleware | This phase | Session crypto managed by NextAuth |
| FastAPI SSE event bus | Next.js route handler proxying Python loopback generator | D-03 | Two processes; loopback HTTP |
| `bot/dashboard/templates/*.html` | `dashboard/app/**/page.tsx` | This phase | Template files deleted |
| `bot/dashboard/static/style.css` | `dashboard/app/globals.css` (spec §4) | This phase | Replaced verbatim |

**Deprecated / outdated:**
- `bot/dashboard/auth.py` -- HMAC logic ported into `lib/telegram-widget.server.ts`; file deleted.
- `bot/dashboard/forms.py` -- replaced by zod schemas.
- `itsdangerous` pip dep -- removable from `pyproject.toml` after cutover.
- `~/hub/knowledge/voidnet/ui-spec.md` -- declared obsolete (D-12).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Telegram widget HMAC algorithm: SHA-256 of bot-token-sha256, comparing against `hash` field, with sorted `key=value\n` data-check-string | Pattern 2 / Pitfall 1 | Wrong algo -> every owner login fails. **Verify by reading `bot/dashboard/auth.py`** before implementation (current code is the canonical implementation). [CITED: core.telegram.org/widgets/login but not re-verified against Animaya code in this research] |
| A2 | Caddy's Voidnet config allows long-lived SSE streams without buffering | Pitfall 3 | SSE breaks in prod. Validate by smoke test before Phase 12 kicks off. |
| A3 | OWNER.md format = plain text with Telegram `user_id` on a known line (Phase 11 output) | D-07, Pitfall 6 | `readOwnerId()` parse fails. Confirm with Phase 11 artifact when available. |
| A4 | Python engine already exposes (or can trivially expose) a loopback HTTP surface for Next.js route handlers | Architecture diagram, D-03 | Requires a small new FastAPI shim (internal) -- plan must include it. Not a blocker; 1-task effort. |
| A5 | Phase 13 lands before Phase 12 per D-09; Phase 12's "0 plans" state in ROADMAP needs updating post-13 | Summary | ROADMAP.md Phase 12 section needs re-authoring after Phase 13 completes; non-blocking but track as follow-up. |
| A6 | Bun works fine in a Debian-slim Python container | Runtime State / Docker | Bun releases Linux binaries and has a Docker install recipe; verified on admin's deploy. If container is extremely locked-down, fallback is Node 22 + `npm ci` (spec §1 allows Node >=20 for start). |
| A7 | `next-auth@5.0.0-beta.31` Credentials provider accepts an arbitrary `authorize` payload (no OAuth dance) for Telegram Widget POSTs | Pattern 2 | If beta.31 changed Credentials semantics, need different shape. Validate with a smoke test during Wave 0. [CITED: authjs.dev docs, but beta version may drift] |

## Open Questions

1. **Markdown renderer for chat messages in React.**
   - What we know: Telegram uses `bot/bridge/formatting.py` (markdown -> Telegram HTML). Admin's `components/ui/*` inventory has no markdown renderer.
   - What's unclear: Which renderer the spec prefers.
   - Recommendation: Propose `react-markdown` + `remark-gfm` in the plan; flag as a minor spec extension (document in the new `ui-style-spec.md` if adopted).

2. **How `AUTH_SECRET` is provisioned.**
   - What we know: next-auth v5 requires `AUTH_SECRET`.
   - What's unclear: install-time generation vs. env-required-at-boot.
   - Recommendation: Generate in the install script (Animaya install on Claude Box), persist to `.env`.

3. **Where the new shared UI style spec lives exactly.**
   - D-12 allows Claude's discretion on filename.
   - Recommendation: `~/hub/knowledge/references/ui-style-spec.md` (parallels `frontend-stack-spec.md`). Content: dark-only theme rule, slate palette HSL table, typography default stack, `.dark` class strategy, shadcn component inventory. Reference it from Animaya's `globals.css` via comment header and from the new dashboard README.

4. **Playwright harness integration with existing Telethon smoke (reference_telethon_harness memory).**
   - Both test Telegram + dashboard flows; must they share a session?
   - Recommendation: Keep Playwright for dashboard-only flows; Telethon handles Telegram. Cross-UI scenarios (SEC-02) need both -- orchestrate sequentially in CI.

5. **Phase 12 owner-lock location (D-12 discretion).**
   - Recommendation: lives in Python engine (asyncio.Lock keyed by owner_id), exposed via engine RPC. Next.js just awaits the upstream. Keeps dashboard stateless and scales if multiple Next.js workers ever appear.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Next.js build/start | ✓ (Dockerfile.bot has Node 22) | 22 | — |
| Bun | Package manager (spec §1) | ✗ in current Dockerfile.bot | — | Install via `curl -fsSL https://bun.sh/install` in a Dockerfile stage. Fallback to `npm` violates spec. |
| Python 3.12 | Engine | ✓ | 3.12-slim | — |
| Caddy | Public TLS | ✓ (Voidnet, external) | — | — |
| `@BotFather` `/setdomain` | Telegram widget callback | N/A (runtime config) | — | Manual install step |

**Missing dependencies with no fallback:** Bun in the bot container. Must be added to `docker/Dockerfile.bot`.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (new; spec D-11) for E2E + Bun test (`bun test`) for unit tests in dashboard; pytest retained for Python engine only |
| Config file | `dashboard/playwright.config.ts` (new, Wave 0); `bunfig.toml` present in admin and copy-ported |
| Quick run command | `cd dashboard && bun test -t "<filter>"` (unit) or `bunx playwright test --grep "<filter>"` (E2E subset) |
| Full suite command | `cd dashboard && bun test && bunx playwright test && (cd .. && pytest tests/ -v)` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| D-01 | No FastAPI route reachable on :8090 | E2E | `bunx playwright test tests/e2e/surface.spec.ts` | Wave 0 |
| D-05 / D-07 | Only owner Telegram ID can sign in | E2E | `bunx playwright test tests/e2e/auth.spec.ts` | Wave 0 |
| D-06 | `DASHBOARD_TOKEN` header bypasses session | integration | `bunx playwright test tests/e2e/dashboard-token.spec.ts` | Wave 0 |
| DASH-01 | Unified chat + tree page at `/chat` | E2E | `bunx playwright test -g "unified page"` | Wave 0 |
| DASH-02 | SSE stream delivers tool-use events inline | E2E | `bunx playwright test -g "sse chat"` | Wave 0 |
| DASH-03 | Tree hides dotfiles, collapses dirs | E2E | `bunx playwright test -g "hub tree"` | Wave 0 |
| DASH-04 | Path traversal / symlink / DENY set -> 403 | unit (server-only) | `bun test lib/hub-tree.server.test.ts` | Wave 0 |
| SEC-01 | Token redacted in `/api/modules` response | unit | `bun test app/api/modules/route.test.ts` | Wave 0 |
| SEC-02 | `web:` session key passed to engine | integration | `bun test lib/engine.server.test.ts` | Wave 0 |
| Telegram HMAC | `verifyTelegramWidget` round-trip | unit | `bun test lib/telegram-widget.server.test.ts` | Wave 0 |
| Form parity | `react-hook-form` + zod validates bridge_config | unit | `bun test app/(auth)/bridge/_components/config-form.test.tsx` | Wave 0 |

### Sampling Rate
- **Per task commit:** `bun test` (dashboard unit) + `pytest tests/engine/` (if Python touched)
- **Per wave merge:** add `bunx playwright test` (E2E)
- **Phase gate:** full suite green + manual LXC smoke (Telethon + browser) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `dashboard/playwright.config.ts` — Playwright runner config
- [ ] `dashboard/tests/e2e/fixtures.ts` — shared fixtures (mock Telegram widget callback, seeded OWNER.md, `DASHBOARD_TOKEN`)
- [ ] `dashboard/bunfig.toml` — Bun test preload (mock `server-only`) ported from admin
- [ ] `dashboard/test-setup.ts` — test setup mirror of admin's
- [ ] Install step: `bunx playwright install chromium` in CI image
- [ ] Retirement plan: enumerate `tests/dashboard/**/*.py` files to delete (pytest HTTP tests) vs. migrate to engine-level pytest

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | next-auth v5 JWT; custom Telegram provider with HMAC-SHA256; OWNER.md allowlist |
| V3 Session Management | yes | next-auth JWT session, `__Secure-authjs.session-token`, 8h maxAge, `httpOnly`, `sameSite: lax` (spec §8) |
| V4 Access Control | yes | Middleware enforces owner-only; allowlist of public routes; `DASHBOARD_TOKEN` as service bypass (D-06) -- scoped to ops use |
| V5 Input Validation | yes | `zod ^4.3.6` at every trust boundary (request bodies, env parsing, engine responses) |
| V6 Cryptography | yes | `hmac.compare_digest` semantics via Node `crypto.timingSafeEqual` in `verifyTelegramWidget` |
| V7 Data Protection | yes | Bot token never in client, never in logs (SEC-01); `SecretStr`-equivalent = zod `.transform` producing redacted DTOs server-side |
| V8 Communication | yes | `trustHost: true` + `secure` cookies + HSTS (2y, preload, spec §8); CSP (nonce-aware) |
| V10 Malicious Code | partial | `server-only` ESLint rule prevents server modules from leaking to client; pin `bun.lockb` |
| V12 File and Resources | yes | DASH-04: `realpath` + prefix check + DENY set in `hub-tree.server.ts` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal into `/etc/passwd` via tree API | Info Disclosure | `realpath` check, prefix-match `HUB_ROOT`, DENY set |
| Symlink escape from `~/hub/` | Info Disclosure | `fs.realpath` rejects follow-out paths |
| CSRF on module install / bridge revoke | Tampering | Double-submit `an-csrf` cookie + `x-csrf-token` header (spec §9) |
| Telegram widget replay | Spoofing | `auth_date` freshness check (<= 24h) + nonce stored per login attempt |
| Token leaking into logs | Info Disclosure | Zod DTO layer redacts; grep-log test in CI (already pattern from SEC-01) |
| SSE accumulation / resource exhaustion | DoS | Per-session concurrency limit (owner-lock in Python engine); idle heartbeat with timeout |
| `DASHBOARD_TOKEN` brute force | Spoofing | Constant-time compare; rate-limit in middleware (log + 429) |
| Cross-UI session bleed (Telegram vs web) | Info Disclosure | SEC-02 namespaced session keys (`tg:` / `web:`) enforced in route handler |
| Radix dialog portal leaking events | minor | Radix handles focus trap / escape; keep version pinned |

## Project Constraints (from CLAUDE.md)

- **Simplest solution first.** No new abstractions unless required. Pattern patches at least-invasive layer.
- **GSD workflow enforcement.** Cannot Edit/Write outside a GSD command -- all this work happens under `/gsd-execute-phase 13`.
- **Python 3.12, type hints everywhere** (engine stays; spec applies to dashboard).
- **Package name `bot`** for Python; for JS use `@animaya/dashboard` scope or no scope.
- **Self-dev constraint:** bots install pip packages only by editing `/data/bot.Dockerfile`. JS deps go in `dashboard/package.json` (developer-authored, not self-dev).
- **Ruff 100 char line length** for any Python engine changes (minimal scope here).
- **No containers inside LXC** (project constraint) -- both processes (Bun, Python) run natively inside the LXC/Docker container.
- **Hub-compatible:** module data in `~/hub/knowledge/animaya/` -- DASH-03 tree must expose it.
- **Verify Bevy/egui/SpacetimeDB APIs before using** (from global CLAUDE.md) -- n/a this phase.
- **Never trust Docker build cache** -- Dockerfile.bot changes must be smoke-tested with `--no-cache`.
- **Bug fixes must run full relevant suite** -- Playwright + pytest both before phase close.

## Sources

### Primary (HIGH confidence)
- `/Users/admin/hub/knowledge/references/frontend-stack-spec.md` (read 2026-04-17) -- the pinned spec
- `/Users/admin/hub/workspace/homelab/apps/admin/package.json` (read 2026-04-17) -- confirms version parity with spec
- `/Users/admin/hub/workspace/homelab/apps/admin/components/ui/` -- 19 shadcn primitives ready to copy
- `/Users/admin/hub/workspace/animaya/bot/dashboard/*.py` (routes, auth, forms -- enumerated)
- `/Users/admin/hub/workspace/animaya/bot/dashboard/templates/` (HTML inventory -- 10 pages, 13 fragments)
- `/Users/admin/hub/workspace/animaya/docker/Dockerfile.bot` / `docker-compose.yml` -- current deploy
- `.planning/phases/13-*/13-CONTEXT.md` -- locked decisions (D-01 .. D-15)
- `.planning/REQUIREMENTS.md` (DASH-01..04, SEC-01, SEC-02)
- `.planning/ROADMAP.md` Phase 12 success criteria

### Secondary (MEDIUM confidence)
- [Telegram Login Widget spec](https://core.telegram.org/widgets/login) -- HMAC algorithm
- [Auth.js (next-auth v5) migration guide](https://authjs.dev/getting-started/migrating-to-v5)
- [Auth.js upgrade guide](https://authjs.dev/guides/upgrade-to-v5)

### Tertiary (LOW confidence)
- [TeaByte/telegram-auth-nextjs](https://github.com/TeaByte/telegram-auth-nextjs) -- reference impl for Telegram provider shape (NOT to be installed; spec forbids non-pinned deps)
- Next-auth v5 beta release notes (beta-to-beta API changes documented inconsistently; validate via Wave 0 smoke)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- spec is authoritative, admin matches it verbatim, versions verified on disk today
- Architecture: HIGH for on-disk artifacts; MEDIUM for Python-engine loopback shape (A4 -- new code needed)
- Pitfalls: HIGH for stack-specific (Tailwind v4, next-auth cookie names); MEDIUM for Caddy SSE behavior (A2)
- Auth: MEDIUM -- Telegram widget provider is project-specific; HMAC details need verification against `bot/dashboard/auth.py` at plan time (A1)
- OWNER.md integration: MEDIUM -- Phase 11 format not locked at time of research (A3)

**Research date:** 2026-04-17
**Valid until:** 2026-05-17 (30 days; stable spec, but next-auth v5 betas move quickly -- re-verify A7 if planning slips)
