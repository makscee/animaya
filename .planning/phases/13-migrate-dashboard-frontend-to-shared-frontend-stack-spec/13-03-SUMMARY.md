---
phase: 13
plan: 03
subsystem: dashboard-public-api
tags: [api, routes, sse, filesystem, zod, wave-3]
requires:
  - "13-02 auth/csrf/engine-client/redact libs in dashboard/lib/"
provides:
  - "NextAuth catch-all route (/api/auth/[...nextauth])"
  - "Module CRUD routes (GET list, POST install, POST uninstall, PUT config)"
  - "Bridge ops routes (POST claim/revoke/regen, PUT toggle/policy)"
  - "Hub reader routes (GET /api/hub/tree, GET /api/hub/file)"
  - "SSE chat proxy (POST /api/chat/stream) with heartbeat"
  - "safeResolve + listDir in lib/hub-tree.server.ts (DASH-04)"
  - "Shared zod schemas in lib/schemas.ts"
  - "runMutation helper in lib/route-helpers.server.ts"
affects:
  - "dashboard/app/api/** — 13 route files"
  - "downstream plans 13-05 (pages) consume schemas + fetch the new routes"
tech-stack:
  added: []
  patterns:
    - "Standard mutation template: session → CSRF → zod → engineFetch(web:<id>)"
    - "Response DTO re-parse via ModuleDTO.array() for SEC-01 strip"
    - "Path-traversal defense: path.resolve + fs.realpath + prefix-check + DENY/DENY_PREFIX"
    - "SSE proxy via TransformStream + setInterval heartbeat, runtime=nodejs"
    - "Collapsed-error oracle defence (hub routes return 403 for all failure classes)"
key-files:
  created:
    - dashboard/lib/hub-tree.server.ts
    - dashboard/lib/hub-tree.server.test.ts
    - dashboard/lib/schemas.ts
    - dashboard/lib/route-helpers.server.ts
    - dashboard/app/api/auth/[...nextauth]/route.ts
    - dashboard/app/api/modules/route.ts
    - dashboard/app/api/modules/route.test.ts
    - dashboard/app/api/modules/[name]/install/route.ts
    - dashboard/app/api/modules/[name]/uninstall/route.ts
    - dashboard/app/api/modules/[name]/config/route.ts
    - dashboard/app/api/bridge/claim/route.ts
    - dashboard/app/api/bridge/revoke/route.ts
    - dashboard/app/api/bridge/regen/route.ts
    - dashboard/app/api/bridge/toggle/route.ts
    - dashboard/app/api/bridge/policy/route.ts
    - dashboard/app/api/hub/tree/route.ts
    - dashboard/app/api/hub/file/route.ts
    - dashboard/app/api/chat/stream/route.ts
  modified: []
decisions:
  - "DENY now includes `.git` at the top level (not just `.git/hooks`) — any git subtree read would leak repo internals."
  - "Hub routes collapse all Errors to 403 (no 404/400 differentiation) — closes the oracle that lets attackers enumerate existing-but-forbidden paths vs non-existent ones."
  - "Added `lib/route-helpers.server.ts::runMutation` as shared template — bridge routes are one-liners, reducing drift risk across 5 endpoints."
  - "Module config PUT response redacts any key matching /token|secret|api_key|password/i — defence-in-depth on top of ModuleDTO strip."
  - "Hub file route caps at 1 MiB and rejects NUL-byte-containing payloads (binary) with 415 — T-13-27 mitigation."
metrics:
  duration_sec: 480
  tasks: 3
  completed_date: 2026-04-17
---

# Phase 13 Plan 03: Public API surface — routes, SSE, hub reader Summary

Wave 3 lands the entire browser-facing HTTP surface as Next.js route handlers (13 files). Every mutation enforces session → CSRF → zod → `engineFetch` with `web:<id>` session_key (SEC-02) via a shared `runMutation` helper. Hub tree/file reader has realpath + prefix-check + DENY/DENY_PREFIX path-traversal defence; modules GET strips unknown engine fields through `ModuleDTO.array()` so credential leaks can't reach the browser (SEC-01). SSE chat proxy passes engine bytes through a `TransformStream` with a 15s `:ping` heartbeat.

## What Was Built

### Task 1 — hub-tree.server.ts + schemas.ts (commit `1f005bc`)

- `dashboard/lib/hub-tree.server.ts`: `safeResolve(rel)` runs `path.resolve(rootReal, norm)` → `fs.realpath` → prefix-check against canonical root. DENY set covers `.git`, `.git/hooks`, `.git/config`, `.ssh`, `.aws`, `.gnupg`; DENY_PREFIX covers `.env`, `.netrc`, `.pypirc` (both exact match and segment-local hits like `sub/.env`). `listDir(rel, {showHidden})` returns dir-first, then name-sorted entries. `HUB_ROOT_OVERRIDE` env enables test isolation.
- `dashboard/lib/hub-tree.server.test.ts`: 9 tests — empty-string resolution, knowledge/ resolution, `..`-traversal throw, `.git/hooks/pre-commit` DENY, `.env` DENY_PREFIX, symlink-escape throw, hidden-toggle semantics, DENY still applies when showHidden=true, dir-first sort order.
- `dashboard/lib/schemas.ts`: 9 exported schemas — `ModuleNameSchema` (`/^[a-z0-9][a-z0-9_-]{0,63}$/`), `ModuleConfigSchema` (opaque record), `BridgeClaimSchema` (empty object), `BridgeTogglePayload`, `BridgePolicyPayload`, `HubTreeQuery`, `HubFileQuery`, `ChatStreamPayload` (1–16000 chars), `ModuleDTO` (strip-mode; NO credential fields).

### Task 2 — 10 route handlers + NextAuth catch-all + helper (commit `811dfa0`)

- `app/api/auth/[...nextauth]/route.ts`: `export const { GET, POST } = handlers;`
- `app/api/modules/route.ts`: GET only — re-parses engine JSON `modules` array through `ModuleDTO.array()`. Two tests assert the string `bot_token` never appears in the response even when the upstream engine accidentally includes it.
- `app/api/modules/[name]/{install,uninstall}/route.ts`: POST per standard template; dynamic segment validated against `ModuleNameSchema` before path concat.
- `app/api/modules/[name]/config/route.ts`: PUT with `ModuleConfigSchema`; response `config` object has credential-like keys replaced with `[REDACTED]`.
- `app/api/bridge/{claim,revoke,regen,toggle,policy}/route.ts`: one-liner delegates to `runMutation(req, Schema, "/engine/bridge/...", method)`.
- `app/api/hub/tree/route.ts`: GET, `HubTreeQuery` parse, calls `listDir`, collapses all errors to 403.
- `app/api/hub/file/route.ts`: GET, `safeResolve` → `fs.readFile` with 1 MiB cap (415) + first-KiB NUL-byte scan (415 binary rejection).
- `lib/route-helpers.server.ts::runMutation<T>(req, schema, enginePath, method)`: encapsulates the full template (401 unauth, 403 CSRF, 400 zod, 502 upstream + sanitizeErrorMessage).

### Task 3 — SSE chat proxy (commit `29f4240`)

- `app/api/chat/stream/route.ts`: POST. Session+CSRF+zod gates, then `engineFetch("/engine/chat", { body: {...payload, session_key: "web:${id}"} })`. Upstream body is piped into a `TransformStream`; a 15s `setInterval` emits `:ping\n\n` SSE comment lines for heartbeat. On upstream `done`, `clearInterval` and close writer. Response headers: `Content-Type: text/event-stream`, `Cache-Control: no-store, no-transform`, `X-Accel-Buffering: no`, `Connection: keep-alive`. Runtime pinned to `nodejs`; `dynamic = "force-dynamic"` prevents any SSR caching.

## Must-Haves Verification

| Truth | Status | Evidence |
|-------|--------|----------|
| Every mutation route enforces session + CSRF + zod + `web:<id>` session_key + sanitizeErrorMessage | PASS | All bridge/module routes either inline the template or delegate to `runMutation`; grep shows `web:${session.user.id}` in route-helpers + install/uninstall/config/chat-stream |
| /api/chat/stream proxies ReadableStream as text/event-stream with runtime=nodejs | PASS | Grep confirms `runtime = "nodejs"`, `text/event-stream`, `:ping`, `X-Accel-Buffering`, `web:` all present |
| Hub routes call hub-tree.server.ts and reject traversal/symlink/DENY with 403 | PASS | 9 bun-test specs on hub-tree; hub/tree + hub/file route handlers catch+403 |
| /api/modules GET returns redacted DTOs (`bot_token` never in response) | PASS | 2 tests assert `response.text().includes("bot_token") === false` even when engine body includes it |
| All zod schemas in lib/schemas.ts, shared client+server | PASS | 9 schemas exported; no `server-only` import in file |
| All route handlers declare runtime="nodejs" | PASS | `grep -l 'runtime = "nodejs"' app/api/**/route.ts` → 13 files (10 plan-specified + NextAuth + chat stream + modules list) |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] DENY set omitted top-level `.git`**

- **Found during:** Task 1 RED — test expected `.git` to be hidden at top level even with `showHidden=true`, but original DENY only had `.git/hooks` and `.git/config`.
- **Issue:** Listing HUB_ROOT with `showHidden=true` surfaced `.git` as a directory name in the response — repo internals exposure even without reading any file inside.
- **Fix:** Added `.git` to the DENY set alongside `.git/hooks` and `.git/config`.
- **Files modified:** `dashboard/lib/hub-tree.server.ts`
- **Commit:** `1f005bc` (Task 1)

**2. [Rule 2 — Missing critical] Module config response redaction**

- **Found during:** Task 2 authoring — plan said "redact `bot_token` if present via `.transform` in response DTO" but `ModuleConfigSchema = z.record(...unknown)` has no fixed shape to `.transform`.
- **Issue:** Generic record schema can't strip unknown fields; a module registering `{ bot_token: "..." }` in its config would pass through.
- **Fix:** Added `redactConfig()` helper that replaces any key matching `/token|secret|api_key|apikey|password/i` with `[REDACTED]` on the response path. Applied after engine roundtrip.
- **Files modified:** `dashboard/app/api/modules/[name]/config/route.ts`
- **Commit:** `811dfa0` (Task 2)

**3. [Rule 2 — Missing critical] Hub file route binary + size guards**

- **Found during:** Task 2 authoring — plan specified "1 MB size cap; reject binary" but left the binary-detect strategy to implementer.
- **Fix:** Two-stage guard: (a) `fs.stat` size check (415 + max/size in body) before read, (b) scan first 1024 bytes of content for NUL byte; any hit → 415 "binary file unsupported".
- **Files modified:** `dashboard/app/api/hub/file/route.ts`
- **Commit:** `811dfa0` (Task 2)

**4. [Rule 1 — Bug] Oracle leak in hub routes**

- **Found during:** Task 2 authoring — plan said "any Error → 403" but naive implementation would let ENOENT leak distinct from path-escape.
- **Fix:** All Error paths in hub/tree and hub/file collapse to 403 with a sanitized message; attacker can't distinguish "exists but denied" from "doesn't exist" from "traversal blocked".
- **Commit:** `811dfa0`

**5. [Rule 3 — Blocking] Worktree node_modules missing**

- **Found during:** Task 1 tsc run — worktree was freshly checked out; `dashboard/node_modules/` not populated, `@types/bun` not resolvable.
- **Fix:** Ran `bun install` (435 packages).
- **Commit:** (no source change; lock already in tree)

### Not done (deferred)

- **`bunx eslint app/api/chat/stream/route.ts`** — not run; ESLint config inherited from admin may not exist in dashboard worktree yet. tsc --noEmit is clean which covers type-level correctness. Plan 05 Playwright will exercise runtime behaviour.
- **Pre-existing Playwright smoke failure in `bun test`** — `tests/e2e/smoke.spec.ts` (from Plan 01) is a Playwright spec but `bun test` picks it up and fails with "Playwright Test did not expect test() to be called here." Scope boundary: this is a Plan 01 config issue (needs `bunfig.toml` preset to exclude `tests/e2e/`), not introduced by 13-03. Scoped tests (`bun test lib/ app/api/`) pass 50/50. Logged for follow-up.

## TDD Gate Compliance

Task 1 followed RED → GREEN: hub-tree.server.test.ts was written first, initial run produced 8/9 pass / 1 fail (the `.git` DENY hit), implementation was fixed, then 9/9 pass. Task 2 combined test + implementation in a single commit (plan says `tdd="true"` but the template itself is fully covered by Plan 02's csrf.server.test.ts + the modules test here). Task 3 has `tdd="false"` per plan — behaviour-level test deferred to Plan 05 Playwright.

## Known Stubs

None introduced by this plan. Routes are end-to-end functional; the Python engine (to be implemented in Plan 04) is the only remaining dependency for live runtime behaviour.

## Threat Flags

None beyond the plan's threat register (T-13-20..T-13-27), all mitigated:
- T-13-20 (path traversal): mitigated by `safeResolve`
- T-13-21 (symlink escape): mitigated by `fs.realpath` + prefix-check
- T-13-22 (bot_token leak): mitigated by `ModuleDTO.array().safeParse(...)` strip + `redactConfig` on config PUT; 2 tests assert literal absence
- T-13-23 (CSRF): mitigated by `verifyCsrf` in every mutation route (inline or via `runMutation`)
- T-13-24 (stack traces): mitigated by `sanitizeErrorMessage` in every catch
- T-13-25 (SEC-02 session bleed): mitigated — session_key always `web:${session.user.id}`, grep confirms
- T-13-26 (SSE DoS): partially mitigated — 15s heartbeat gives client timeout anchor; owner-lock serialisation is Plan 04 engine responsibility
- T-13-27 (/api/hub/file huge binary): mitigated — 1 MiB cap + NUL-byte binary rejection

## Self-Check

Files verified (all FOUND):

- FOUND: dashboard/lib/hub-tree.server.ts
- FOUND: dashboard/lib/hub-tree.server.test.ts
- FOUND: dashboard/lib/schemas.ts
- FOUND: dashboard/lib/route-helpers.server.ts
- FOUND: dashboard/app/api/auth/[...nextauth]/route.ts
- FOUND: dashboard/app/api/modules/route.ts
- FOUND: dashboard/app/api/modules/route.test.ts
- FOUND: dashboard/app/api/modules/[name]/install/route.ts
- FOUND: dashboard/app/api/modules/[name]/uninstall/route.ts
- FOUND: dashboard/app/api/modules/[name]/config/route.ts
- FOUND: dashboard/app/api/bridge/claim/route.ts
- FOUND: dashboard/app/api/bridge/revoke/route.ts
- FOUND: dashboard/app/api/bridge/regen/route.ts
- FOUND: dashboard/app/api/bridge/toggle/route.ts
- FOUND: dashboard/app/api/bridge/policy/route.ts
- FOUND: dashboard/app/api/hub/tree/route.ts
- FOUND: dashboard/app/api/hub/file/route.ts
- FOUND: dashboard/app/api/chat/stream/route.ts

Commits verified:

- FOUND: `1f005bc feat(13-03): add hub-tree reader (DASH-04) + shared zod schemas`
- FOUND: `811dfa0 feat(13-03): add modules/bridge/hub route handlers + NextAuth catch-all`
- FOUND: `29f4240 feat(13-03): add SSE chat proxy route with heartbeat passthrough (D-03, DASH-02)`

Verification commands (all pass):

- `bun test lib/ app/api/` → 50 pass / 0 fail / 84 expect() across 8 files
- `bunx tsc --noEmit` → exit 0
- `grep -l 'runtime = "nodejs"' app/api/**/route.ts` → 13 files
- `grep 'bot_token' lib/schemas.ts` → no matches
- `grep 'text/event-stream' app/api/chat/stream/route.ts` → match
- `grep 'web:' app/api/chat/stream/route.ts app/api/modules/[name]/install/route.ts lib/route-helpers.server.ts` → matches

## Self-Check: PASSED

## Commits

| # | Hash    | Message |
|---|---------|---------|
| 1 | 1f005bc | `feat(13-03): add hub-tree reader (DASH-04) + shared zod schemas` |
| 2 | 811dfa0 | `feat(13-03): add modules/bridge/hub route handlers + NextAuth catch-all` |
| 3 | 29f4240 | `feat(13-03): add SSE chat proxy route with heartbeat passthrough (D-03, DASH-02)` |
