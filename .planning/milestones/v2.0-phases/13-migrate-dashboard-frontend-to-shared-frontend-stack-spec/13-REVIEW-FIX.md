---
phase: 13-migrate-dashboard-frontend-to-shared-frontend-stack-spec
fixed_at: 2026-04-17T22:10:00Z
review_path: .planning/phases/13-migrate-dashboard-frontend-to-shared-frontend-stack-spec/13-REVIEW.md
iteration: 1
findings_in_scope: 9
fixed: 9
skipped: 0
status: all_fixed
---

# Phase 13: Code Review Fix Report

**Fixed at:** 2026-04-17T22:10:00Z
**Source review:** .planning/phases/13-migrate-dashboard-frontend-to-shared-frontend-stack-spec/13-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 9 (2 Critical + 7 Warning)
- Fixed: 9
- Skipped: 0

## Fixed Issues

### CR-01: DASHBOARD_TOKEN middleware bypass could mint web:<id> session_key from stale cookie

**Files modified:** `dashboard/middleware.ts`
**Commit:** e0480a4
**Applied fix:** In the DASHBOARD_TOKEN fast-path, strip both `authjs.session-token` and `__Secure-authjs.session-token` cookies from the forwarded request headers and set `x-animaya-ops: 1` so downstream `auth()` returns null. This prevents a stale browser session cookie from being reused to forge a `web:<ownerId>` `session_key` on a request that middleware never re-gated for owner equality. Note: requires human verification because the DASHBOARD_TOKEN is intended for scripted ops and the behavioural change (no session ambient) may affect any existing ops scripts that relied on implicit session identity.

### CR-02: _strip_secrets only scrubbed top-level bot_token/token — nested secrets leaked

**Files modified:** `bot/engine/modules_rpc.py`, `dashboard/lib/redact.server.ts`, `dashboard/app/api/modules/route.ts`, `dashboard/lib/schemas.ts`
**Commit:** 79162f0
**Applied fix:** Replaced the Python `_strip_secrets` implementation with a recursive `_scrub_mapping` walker keyed on the regex `(token|secret|api_key|apikey|password|credential|oauth)` (case-insensitive), applied at every nesting level and to list-of-dict values. Added a matching TypeScript `deepRedact` helper in `lib/redact.server.ts` and applied it to the engine response in `app/api/modules/route.ts`. Corrected the misleading docstring on `ModuleDTO` in `lib/schemas.ts` to accurately describe Zod's strip semantics and to point to the explicit redactors (this also resolves IN-06).

### WR-01: SSE proxy did not propagate client disconnect to engine — owner-lock wedge risk

**Files modified:** `dashboard/app/api/chat/stream/route.ts`
**Commit:** e6074f5
**Applied fix:** Introduced an `AbortController` passed to `engineFetch` via `RequestInit.signal`. The Next.js request's `req.signal` abort event now aborts the upstream controller, clears the heartbeat interval, and tears down the writer. The forwarding loop also aborts the upstream on a `writer.write()` failure (client-side cancel mid-frame), ensuring the engine-side `acquire_for_session` lock is released promptly instead of being held until Claude naturally finishes.

### WR-02: owner_lock registry could grow unbounded from malformed session_keys

**Files modified:** `bot/engine/owner_lock.py`
**Commit:** 2ecfd2d
**Applied fix:** Added strict validator `_SESSION_KEY_RE = r"^(tg|web|ops):[A-Za-z0-9_\-]{1,64}$"` and raised `InvalidSessionKeyError` for any non-matching input. This bounds `_locks` to well-formed keys only and prevents a buggy caller (or a loopback-neighbour exploit) from filling the dict. Existing tests use only valid keys (`tg:owner-1`, `tg:123`, `web:123`, `tg:boom`), so no test regressions expected.

### WR-03: safeResolve silently fell through to the lexical path when canonicalisation failed

**Files modified:** `dashboard/lib/hub-tree.server.ts`
**Commit:** bd16860
**Applied fix:** Removed the `@ts-expect-error`-masked `canonical = joined` fallback. `canonical` is now typed `string | undefined` and an explicit `throw new Error("path cannot be canonicalized")` fires if the ancestor-walk never finds an existing directory. Since `fs.realpath(root)` at the top of the function already throws for a missing root, this preserves the symlink-escape guarantee without adding new failure modes for legitimate inputs.

### WR-04 + WR-05: Telegram widget accepted arbitrary id strings and future auth_date timestamps

**Files modified:** `dashboard/lib/telegram-widget.server.ts`
**Commit:** 40dc03f
**Applied fix:** (WR-04) `obj.id` is now validated: numbers must be finite; strings must match `^-?\d+$` — otherwise the payload is rejected. (WR-05) Added the symmetric future-timestamp rejection: `authDate - now > 60` fails the check, complementing the existing one-day past-skew window. Both checks retain fail-closed semantics and run before HMAC verification.

### WR-06: useSSE retry timer was not cancellable on abort — could race with new turn

**Files modified:** `dashboard/app/(auth)/_lib/use-sse.ts`
**Commit:** 8984b11
**Applied fix:** Replaced the plain `setTimeout` sleep with a `Promise<boolean>` that races `setTimeout(delay)` against a `ctrl.signal` `abort` event listener. On abort, `clearTimeout` fires and the promise resolves `true`, causing `send()` to return before calling `attempt()` a second time. Prevents the orphaned retry from double-posting when the user starts a new turn mid-backoff.

### WR-07: bridge_rpc and modules_rpc called request.json() without a size cap

**Files modified:** `bot/engine/bridge_rpc.py`, `bot/engine/modules_rpc.py`
**Commit:** b3db4e7
**Applied fix:** Added a local `_read_json_bounded(request)` helper to both RPC modules that inspects the `Content-Length` header against a 1 MiB cap and raises `HTTPException(413, "payload too large")` before reading the body. All four mutable endpoints (`/toggle`, `/policy`, `/{name}/install`, `/{name}/config`) now use the bounded reader. The install path preserves its prior "empty body → empty dict" tolerance by re-raising `HTTPException` but swallowing other parse errors.

---

_Fixed: 2026-04-17T22:10:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
