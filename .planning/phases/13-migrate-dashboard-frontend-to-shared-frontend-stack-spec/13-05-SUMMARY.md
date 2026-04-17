---
phase: 13
plan: 05
subsystem: dashboard-frontend
tags: [pages, ui, react, e2e, playwright, sse, rhf, zod]
requires:
  - 13-01 shared UI spec + scaffolded Next.js app
  - 13-02 next-auth Credentials + middleware gate (session / DASHBOARD_TOKEN)
  - 13-03 API route handlers (NOT merged on this branch — forward-compat; UI targets stable URLs)
  - 13-04 FastAPI loopback engine (started by mock sidecar in E2E)
provides:
  - Full Next.js page tree under (auth)/ and (public)/ covering every legacy Jinja page
  - Unified chat + Hub tree surface (DASH-01)
  - SSE streaming chat w/ inline tool_use/tool_result Cards (DASH-02)
  - Collapsible Hub tree with dotfile toggle (DASH-03)
  - Telegram Login Widget embed → next-auth Credentials signIn (D-05)
  - react-hook-form + zodResolver wiring for bridge + module config (D-15)
  - Playwright E2E suite (7 specs, 14 tests) green
affects:
  - dashboard/app/(auth)/** (new route group)
  - dashboard/app/(public)/** (new route group)
  - dashboard/components/layout/** (sidebar, topbar, nav-items)
  - dashboard/lib/schemas.ts (shared zod schemas for forms + API handlers)
  - dashboard/tests/e2e/** (mock engine, 7 specs, global setup/teardown)
tech-stack:
  added:
    - react-markdown ^10 (XSS-safe assistant markdown)
    - remark-gfm ^4 (tables/strikethrough)
  patterns:
    - Client components only at interactive boundaries (forms, streams, tree)
    - SSE-over-POST via fetch ReadableStream + TextDecoder (EventSource is GET-only)
    - Double-submit CSRF cookie (an-csrf) mirrored into x-csrf-token header
    - localStorage for non-sensitive UI prefs only (T-13-42)
key-files:
  created:
    - dashboard/app/(auth)/layout.tsx
    - dashboard/app/(auth)/page.tsx
    - dashboard/app/(auth)/_lib/use-sse.ts
    - dashboard/app/(auth)/_components/chat-panel.tsx
    - dashboard/app/(auth)/_components/tool-use-event.tsx
    - dashboard/app/(auth)/_components/hub-tree.tsx
    - dashboard/app/(auth)/chat/page.tsx
    - dashboard/app/(auth)/chat/chat-with-tree.tsx
    - dashboard/app/(auth)/modules/page.tsx
    - dashboard/app/(auth)/modules/modules-list.tsx
    - dashboard/app/(auth)/modules/[name]/page.tsx
    - dashboard/app/(auth)/modules/[name]/module-detail.tsx
    - dashboard/app/(auth)/bridge/page.tsx
    - dashboard/app/(auth)/bridge/_components/config-form.tsx
    - dashboard/app/(public)/layout.tsx
    - dashboard/app/(public)/login/page.tsx
    - dashboard/app/(public)/login/telegram-login.tsx
    - dashboard/app/(public)/403/page.tsx
    - dashboard/components/layout/{sidebar,topbar,nav-items}.ts(x)
    - dashboard/lib/schemas.ts
    - dashboard/tests/e2e/_mock-engine.ts
    - dashboard/tests/e2e/{global-setup,global-teardown}.ts
    - dashboard/tests/e2e/{surface,auth,dashboard-token,chat,hub-tree,modules,bridge}.spec.ts
  modified:
    - dashboard/playwright.config.ts (globalSetup/globalTeardown)
    - dashboard/bunfig.toml (restrict bun test root to lib/)
    - dashboard/package.json + bun.lock (react-markdown + remark-gfm)
  deleted:
    - dashboard/app/page.tsx (moved into (auth) route group)
    - dashboard/tests/e2e/smoke.spec.ts (superseded by surface.spec.ts)
decisions:
  - D-05 Telegram Login Widget: used the client-callback variant
    (`data-onauth="onTelegramAuth(user)"` + client `signIn("telegram", payload)`)
    rather than `data-auth-url` GET-redirect — next-auth v5 Credentials flow
    requires a CSRF-authenticated POST to /api/auth/callback/credentials,
    which signIn() provides internally. Documented in login.tsx + telegram-login.tsx.
  - D-10 parity: every current Jinja page has a React replacement
    (home / modules / module_detail / bridge_config / login / 403).
  - Open Q1 (13-RESEARCH): chose react-markdown + remark-gfm. No rehype-raw,
    no dangerouslySetInnerHTML anywhere (T-13-40 mitigation).
  - SSE transport: POST-body SSE via fetch ReadableStream (not EventSource)
    because the engine endpoint takes a JSON body and must attach CSRF.
  - bun test root: `root = "lib"` in bunfig.toml so Playwright specs aren't
    accidentally executed as bun unit tests.
metrics:
  tasks_completed: 3
  files_created: 27
  files_modified: 3
  e2e_tests_green: 14
  bun_tests_green: 35
  duration_min: ~35
  completed: 2026-04-17
---

# Phase 13 Plan 05: Pages + E2E Summary

Every legacy FastAPI/Jinja dashboard page now has a Next.js App Router
replacement under `(auth)/`, plus the new unified chat+tree surface
(DASH-01/02/03) and a Telegram Login Widget sign-in flow. A Playwright E2E
suite (7 specs, 14 tests) locks the behaviour in: owner-only auth,
DASHBOARD_TOKEN bypass, no public `/engine/*` proxy, SSE streaming with
inline tool Cards + retry, dotfile toggle persistence, module install CSRF
roundtrip, and bridge policy zod shape.

## Objective Recap

Wave 4 ports every current FastAPI/Jinja page into React (parity per D-10),
implements the new unified chat+tree page (DASH-01), embeds the Telegram
Login Widget, and locks the Playwright E2E suite covering auth + SSE + tree
+ modules + bridge. Legacy Jinja is untouched — Plan 06 handles cutover.

## Tasks

### Task 1 — Chrome + public pages — commit ed25898

Copied `(auth)` / `(public)` layouts from homelab/apps/admin, rebuilt the
sidebar nav with Animaya items (Home / Chat / Modules / Bridge), and
authored the Telegram Login Widget page via a small client wrapper that
bridges Telegram's global `onTelegramAuth(user)` callback into
`next-auth/react`'s `signIn("telegram", payload)`. This keeps the CSRF
requirements of next-auth@5.0.0-beta.31's Credentials callback satisfied
(the widget's `data-auth-url` GET-redirect would NOT carry CSRF).

### Task 2 — Chat + Tree + Modules + Bridge pages — commit 2b6244a

Built `use-sse` hook (POST-body SSE, fetch ReadableStream, CSRF header,
abort, exponential-backoff retry), `ToolUseEvent` (react-markdown + lucide
icon Cards, no raw HTML), `ChatPanel` (transcript + Textarea), `HubTree`
(SWR tree, localStorage for open-state + hidden toggle), `ChatWithTree`
(split layout + read-only file viewer), modules list (SWR + toast) and
detail (rhf + zodResolver + JSON config editor), bridge config form
(rhf + zodResolver for toggle + policy, claim/revoke/regen actions).
Created `lib/schemas.ts` as the single source of truth for zod payloads
shared with Plan 13-03 route handlers.

### Task 3 — Playwright E2E suite — commit 81c6a58

Seven specs (14 tests). `_mock-engine.ts` stands up a tiny Node HTTP
server on 127.0.0.1:8091 (started via `globalSetup`, closed via
`globalTeardown`) so the D-01 loopback-surface assertion has a real
counterpart. All other specs intercept `/api/*` via `page.route()` — Plan
13-03's route handlers are not yet merged on this branch, so we exercise
the UI contract directly against mocked responses.

## Verification

| Gate                                | Result |
|-------------------------------------|--------|
| `bun run build`                     | pass   |
| `bunx tsc --noEmit`                 | clean  |
| `bun test` (lib unit tests)         | 35 pass |
| `bunx playwright test` (7 specs)    | 14 pass |
| Login page contains `telegram-widget` hook | yes |
| Bridge form uses `zodResolver`       | yes (D-15) |
| Chat page imports `useSSE`           | yes |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking] Created `lib/schemas.ts` locally**
- **Found during:** Task 2.
- **Issue:** Plan refers to `lib/schemas.ts` as the zod source of truth for
  both Plan 13-03 handlers and Plan 13-05 forms. 13-03 is not merged on
  this branch, so `lib/schemas.ts` did not exist. Task 2 cannot complete
  without it.
- **Fix:** Authored the file with `ChatSendPayload`, `ModuleConfigSchema`,
  `BridgeTogglePayload`, `BridgePolicyPayload`, `BridgeClaimPayload`.
  Stable shapes — 13-03 will import the same types when that wave merges.
- **Files:** `dashboard/lib/schemas.ts`.
- **Commit:** 2b6244a.

**2. [Rule 3 — Blocking] lucide `Bash` icon not exported; swap for `Terminal`**
- **Found during:** Task 2 build.
- **Issue:** `lucide-react@1.8.0` does not export `Bash`; build failed.
- **Fix:** Aliased `Bash: Terminal` in the tool-icon map.
- **Commit:** 2b6244a.

**3. [Rule 3 — Blocking] bun test picked up Playwright specs**
- **Found during:** Post-Task-3 verification.
- **Issue:** `bun test` globbed `tests/e2e/*.spec.ts` and crashed on
  Playwright's `test.use()`. Plan's verification requires bun test clean.
- **Fix:** `bunfig.toml: root = "lib"` restricts bun unit tests to
  `dashboard/lib`, leaving Playwright specs to `bunx playwright test`.
- **Commit:** 81c6a58.

**4. [Rule 1 — Bug] Module config zod `.default({})` broke rhf resolver types**
- **Found during:** Task 2 build.
- **Issue:** `z.record(...).default({})` made the input type optional;
  `zodResolver` disagreed with `useForm<ModuleConfigPayload>` generic.
- **Fix:** Dropped the default; form provides `{ config: {} }` via
  `defaultValues`.
- **Commit:** 2b6244a.

### Auth gates

None. The plan targets anonymous local development only.

## Known Stubs

- **Home page `/engine/status` status strip:** omitted intentionally per
  plan task 1 ("if such an endpoint is cheap — else omit"). Home shows
  static quick-link Cards. Plan 06 can wire live counters when the engine
  contract stabilises.
- **Module detail form:** uses a generic JSON config textarea because
  module DTOs don't yet advertise a declarative field list. When 13-03's
  module DTO surface includes a `schema` field, we can render typed
  inputs via `useForm` dynamically.

## Threat Flags

None — all new surface was enumerated in the plan's threat model.

## Self-Check: PASSED

- [x] `dashboard/app/(auth)/chat/page.tsx` — FOUND
- [x] `dashboard/app/(auth)/_components/chat-panel.tsx` — FOUND
- [x] `dashboard/app/(auth)/_components/hub-tree.tsx` — FOUND
- [x] `dashboard/app/(auth)/_lib/use-sse.ts` — FOUND
- [x] `dashboard/app/(auth)/modules/page.tsx` — FOUND
- [x] `dashboard/app/(auth)/modules/[name]/page.tsx` — FOUND
- [x] `dashboard/app/(auth)/bridge/page.tsx` — FOUND
- [x] `dashboard/app/(auth)/bridge/_components/config-form.tsx` — FOUND
- [x] `dashboard/app/(public)/login/page.tsx` — FOUND (+ telegram-login.tsx client wrapper)
- [x] `dashboard/app/(public)/403/page.tsx` — FOUND
- [x] `dashboard/components/layout/{sidebar,topbar,nav-items}.ts(x)` — FOUND
- [x] `dashboard/lib/schemas.ts` — FOUND
- [x] 7 Playwright specs under `dashboard/tests/e2e/` — FOUND
- [x] Commit ed25898 (Task 1) — FOUND
- [x] Commit 2b6244a (Task 2) — FOUND
- [x] Commit 81c6a58 (Task 3) — FOUND
