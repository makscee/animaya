---
phase: 13-migrate-dashboard-frontend-to-shared-frontend-stack-spec
reviewed: 2026-04-17T21:50:00Z
depth: standard
files_reviewed: 66
files_reviewed_list:
  - dashboard/lib/telegram-widget.server.ts
  - dashboard/middleware.ts
  - dashboard/auth.ts
  - dashboard/auth.config.ts
  - dashboard/lib/csrf.server.ts
  - dashboard/lib/csrf.shared.ts
  - dashboard/lib/csrf-cookie.server.ts
  - dashboard/lib/hub-tree.server.ts
  - dashboard/lib/redact.server.ts
  - dashboard/lib/engine.server.ts
  - dashboard/lib/owner.server.ts
  - dashboard/lib/owner-gate.server.ts
  - dashboard/lib/dashboard-token.server.ts
  - dashboard/lib/route-helpers.server.ts
  - dashboard/lib/schemas.ts
  - dashboard/lib/utils.ts
  - dashboard/app/api/auth/[...nextauth]/route.ts
  - dashboard/app/api/bridge/claim/route.ts
  - dashboard/app/api/bridge/policy/route.ts
  - dashboard/app/api/bridge/regen/route.ts
  - dashboard/app/api/bridge/revoke/route.ts
  - dashboard/app/api/bridge/toggle/route.ts
  - dashboard/app/api/chat/stream/route.ts
  - dashboard/app/api/hub/file/route.ts
  - dashboard/app/api/hub/tree/route.ts
  - dashboard/app/api/modules/route.ts
  - dashboard/app/api/modules/[name]/config/route.ts
  - dashboard/app/api/modules/[name]/install/route.ts
  - dashboard/app/api/modules/[name]/uninstall/route.ts
  - dashboard/app/(auth)/_components/chat-panel.tsx
  - dashboard/app/(auth)/_components/hub-tree.tsx
  - dashboard/app/(auth)/_components/tool-use-event.tsx
  - dashboard/app/(auth)/_lib/use-sse.ts
  - dashboard/app/(auth)/bridge/_components/config-form.tsx
  - dashboard/app/(auth)/bridge/page.tsx
  - dashboard/app/(auth)/chat/chat-with-tree.tsx
  - dashboard/app/(auth)/chat/page.tsx
  - dashboard/app/(auth)/layout.tsx
  - dashboard/app/(auth)/modules/[name]/module-detail.tsx
  - dashboard/app/(auth)/modules/[name]/page.tsx
  - dashboard/app/(auth)/modules/modules-list.tsx
  - dashboard/app/(auth)/modules/page.tsx
  - dashboard/app/(auth)/page.tsx
  - dashboard/app/(public)/403/page.tsx
  - dashboard/app/(public)/layout.tsx
  - dashboard/app/(public)/login/page.tsx
  - dashboard/app/(public)/login/telegram-login.tsx
  - dashboard/app/error.tsx
  - dashboard/app/layout.tsx
  - dashboard/app/not-found.tsx
  - dashboard/next.config.mjs
  - dashboard/playwright.config.ts
  - bot/engine/__init__.py
  - bot/engine/bridge_rpc.py
  - bot/engine/chat_stream.py
  - bot/engine/http.py
  - bot/engine/modules_rpc.py
  - bot/engine/owner_lock.py
  - bot/engine/modules_forms.py
  - bot/engine/modules_jobs.py
  - bot/engine/modules_view.py
  - bot/main.py
  - docker/docker-compose.yml
  - docker/Dockerfile.bot
  - scripts/deploy.sh
findings:
  critical: 2
  warning: 7
  info: 6
  total: 15
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-04-17T21:50:00Z
**Depth:** standard
**Files Reviewed:** 66
**Status:** issues_found

## Summary

The Phase 13 migration (FastAPI+Jinja → Next.js 15 / React 19 / Tailwind v4 / Bun, with FastAPI demoted to loopback) is broadly well-executed: defense-in-depth is layered (Telegram HMAC → next-auth signIn owner gate → Edge middleware owner gate → per-route `auth()` + CSRF → Zod → engine `session_key`), secret redaction runs at three layers (engine `_strip_secrets`, route `redactConfig`, client-facing `ModuleDTO` strip), and the loopback-only engine refuses non-127.0.0.1 callers. Naming, typing, and logging conventions track `CLAUDE.md`.

Two critical findings are about trust-boundary bypasses that reach the engine (loopback spoof via `X-Forwarded-For`-like headers is mitigated, but the DASHBOARD_TOKEN middleware bypass skips both CSRF and owner enforcement while still allowing the API to forge a `session_key`). Seven warnings cover missing session upgrades on the SSE proxy, a race in the owner-lock on process restart, a path-resolution corner case in `hub-tree.server.ts`, and several missing guards worth tightening before public exposure.

## Critical Issues

### CR-01: DASHBOARD_TOKEN middleware bypass skips CSRF + owner gate AND downstream routes mint a `web:<id>` session_key from a possibly-absent session

**File:** `dashboard/middleware.ts:84-95`; interaction with `dashboard/lib/route-helpers.server.ts:24-55`, `dashboard/app/api/chat/stream/route.ts:40-76`

**Issue:** When a request presents a valid `x-dashboard-token` / `?token=` header, the middleware short-circuits with `NextResponse.next()` — bypassing both the session gate (line 112) and owner gate (line 133). Downstream route handlers then call `auth()`; if the caller has no next-auth session cookie, `session?.user?.id` is `undefined`, so the route returns 401. That part is correct. HOWEVER: if the caller also holds a valid stale session cookie (a very plausible scenario — deploy scripts reusing a human operator's browser cookie jar), the downstream route will happily forge `session_key: web:<id>` using a session ID that was never re-validated for owner equality for *this* request (middleware skipped the owner check). The bot-side `owner_lock.acquire_for_session` extracts owner from `session_key`, so a non-owner who kept a long-lived cookie from a prior legitimate login could — during the DASHBOARD_TOKEN bypass path — still operate under the real owner's lock namespace. More importantly, the CSRF check in `route-helpers.server.ts:29` is NOT skipped on the bypass path, but in the SSE route the CSRF check still demands `verifyCsrf(req)`, so scripted clients using DASHBOARD_TOKEN cannot call `/api/chat/stream` (the documented `curl -N` recipe on line 32-38 of that route will fail). Either the bypass is intended to bypass everything (then document and implement uniformly), or nothing (then gate the bypass behind an explicit `x-animaya-ops: 1` that flips only specific routes). The current middle-ground silently mixes the two and grants unaudited owner-namespace writes.

**Fix:**
```ts
// dashboard/middleware.ts — after validating dashToken, strip any session
// cookie so downstream auth() returns null and routes uniformly 401, OR
// inject a synthetic header so routes can distinguish ops-token from owner.
if (dashToken && expectedDashToken && edgeConstantTimeEqual(dashToken, expectedDashToken)) {
  requestHeaders.set("x-animaya-ops", "1");
  // Clear session cookie for this request so auth() returns null (prevents
  // cookie-reuse forging web:<id>).
  const cleaned = new Headers(requestHeaders);
  cleaned.set("cookie", (req.headers.get("cookie") ?? "")
    .replace(/(?:^|;\s*)(?:__Secure-)?authjs\.session-token=[^;]+/g, ""));
  const passRes = NextResponse.next({ request: { headers: cleaned } });
  return applySecurityHeaders(passRes, nonce);
}
```
Then in `route-helpers.server.ts`, explicitly accept `x-animaya-ops: 1` with a synthetic `session_key` of `ops:deploy` (and extend `owner_lock._owner_of` to recognize an `ops:` namespace that does NOT collide with `web:<ownerId>`).

---

### CR-02: `modules_rpc._strip_secrets` only scrubs `bot_token` / `token` at top level; nested secret shapes can still leak

**File:** `bot/engine/modules_rpc.py:34-42`; interaction with `dashboard/app/api/modules/[name]/config/route.ts:14-25`

**Issue:** `_strip_secrets()` does `safe.pop("bot_token", None)` and `safe.pop("token", None)` at the top level, then delegates nested config scrubbing to `redact_bridge_config(cfg)` — but ONLY for the telegram-bridge shape. Any other module that places credentials under a different key (e.g., `google_api_key`, `openai_api_key`, `stt_api_key`, `claude_code_oauth_token`, `webhook_secret`, or a nested `auth.token`) will be passed through unchanged to the browser. The Next.js layer `redactConfig` at `modules/[name]/config/route.ts:14-25` DOES match a broader regex (`/token|secret|api_key|apikey|password/i`), but only on the response of the PUT handler — the GET path reaches through `/engine/modules` → route at `dashboard/app/api/modules/route.ts`, which runs `ModuleDTO.array().safeParse()`. Because `ModuleDTO.config` is declared as `ModuleConfigSchema = z.record(z.string(), z.unknown())`, Zod's default `.strip()` policy only drops keys not declared in the schema — but here every key is accepted by `z.record(z.string(), z.unknown())`, so NOTHING is stripped. The schema comment at `dashboard/lib/schemas.ts:75-79` claims "unknown fields are stripped by default, guaranteeing tokens cannot leak" — that is incorrect for the `config` sub-object.

**Fix:**
```python
# bot/engine/modules_rpc.py — generalise secret scrubbing.
_SECRET_KEY_RE = re.compile(r"(token|secret|api_key|apikey|password|credential|oauth)", re.I)

def _scrub_mapping(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if _SECRET_KEY_RE.search(k):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _scrub_mapping(v)
        else:
            out[k] = v
    return out

def _strip_secrets(entry: dict) -> dict:
    return _scrub_mapping(dict(entry))
```
Also add, in `dashboard/lib/schemas.ts`, a server-side redactor applied after `ModuleDTO.array().safeParse` in `app/api/modules/route.ts` so defense is double-sided:
```ts
const SECRET_KEY_RE = /token|secret|api_key|apikey|password|credential|oauth/i;
function deepRedact<T>(v: T): T { /* walk & replace */ }
```

## Warnings

### WR-01: SSE proxy does not propagate upstream abort on client disconnect → engine leak

**File:** `dashboard/app/api/chat/stream/route.ts:79-103`

**Issue:** The IIFE at lines 86-97 reads from `upstream.body` and writes to the client until the upstream is done. If the browser disconnects mid-stream, the client-side `ReadableStream` is cancelled, `writer.write(value)` rejects — but the `.catch(() => {})` on the ping write swallows that and the outer loop continues reading from `upstream` forever (or until Claude finishes), holding the owner lock and wasting API budget. There is no `AbortController` signalling back to `engineFetch`. T-13-32 says interleaved turns are blocked, but a wedged lock held by a phantom disconnected client achieves the same denial-of-service against the owner.

**Fix:**
```ts
const controller = new AbortController();
// Pass signal to engineFetch init
upstream = await engineFetch("/engine/chat", { ..., signal: controller.signal });
// Propagate client-side cancellation:
req.signal.addEventListener("abort", () => {
  controller.abort();
  clearInterval(ping);
  void writer.abort().catch(() => {});
});
```
And in the forwarding IIFE, break the loop on `writer.write()` rejection.

### WR-02: `owner_lock` registry leaks an unbounded dict keyed by owner id

**File:** `bot/engine/owner_lock.py:18, 31-37`

**Issue:** `_locks: dict[str, asyncio.Lock]` grows forever. Since only the OWNER.md-validated id reaches the engine, in practice this is bounded by |owners| (≈1), but the defensive fallback at line 28 (`return session_key` when no colon) means a malformed `session_key` creates a spurious entry. A buggy caller (or a crafted loopback request from a neighbour process if loopback is ever shared) could grow `_locks` unboundedly. Also, there is no TTL or eviction, so a dangling reference to a finished lock forever pins memory.

**Fix:** Validate `session_key` format strictly (reject if not matching `^(tg|web|ops):[^:\s]{1,64}$`) and either cap the dict with `functools.lru_cache`-style eviction or attach lock lifetime to a background GC that evicts non-contended owners after N minutes.

### WR-03: `safeResolve` falls through to the lexical path when no ancestor resolves — comment is wrong

**File:** `dashboard/lib/hub-tree.server.ts:92-109`

**Issue:** The `@ts-expect-error` at line 107 claims "unreachable in practice" — but the loop at 94-103 only assigns `canonical` when `fs.realpath(cursor)` succeeds AND immediately `break`s. If the symbolic root itself fails to realpath (e.g., `HUB_ROOT_OVERRIDE` points at a deleted path), the loop walks up to `/`, then `path.dirname('/') === '/'` exits the `while` without ever assigning `canonical`. The fallback `canonical = joined` then silently allows an unresolved path through. Low likelihood, but the "unreachable" claim is factually wrong and the fallback defeats the symlink-escape guarantee on a broken root.

**Fix:**
```ts
// Early-validate the root exists BEFORE the loop; throw on missing root.
// Remove the fallback assignment — canonicalization must succeed or throw.
if (!canonical) throw new Error("path cannot be canonicalized");
```

### WR-04: Telegram widget HMAC accepts stringified numeric `id` without bounds check

**File:** `dashboard/lib/telegram-widget.server.ts:44-48, 73-74`

**Issue:** `Number(obj.id)` at line 73 accepts arbitrary huge values. While `readOwnerId()` compares as string, a caller could supply `id: "00123"` and (depending on Telegram serialization) pass the HMAC check only if the data-check-string uses the same stringification Telegram used. Telegram always sends `id` as a numeric literal; stringifying `"00123"` into the check string yields `id=00123`, which would fail the HMAC. Functional risk is low, but the code path at line 48 allows `typeof obj.id === "string"` with no regex guard, and `String(v)` at line 52 normalizes the string input identically to the numeric path. Minor hardening.

**Fix:** Reject `typeof obj.id !== "number"` outright (Telegram's widget always sends a number). If strings must be accepted, require `/^-?\d+$/` on `obj.id`.

### WR-05: `auth_date` skew tolerance is one-sided (past only)

**File:** `dashboard/lib/telegram-widget.server.ts:46`

**Issue:** The check `Math.floor(Date.now()/1000) - authDate > 86400` only rejects old timestamps. A future-dated `auth_date` (clock skew on client or a forged widget response) passes. Combined with HMAC, exploitation requires the bot token, but the asymmetry is a code smell. Reject `authDate - now > 60` as well.

**Fix:**
```ts
const now = Math.floor(Date.now() / 1000);
if (now - authDate > 86400) return null;
if (authDate - now > 60) return null; // no future timestamps
```

### WR-06: `useSSE` retry doubles turns and ignores CSRF rotation

**File:** `dashboard/app/(auth)/_lib/use-sse.ts:105-127`

**Issue:** On abnormal close, the hook retries once after exponential backoff (line 118-121). The retry reuses the SAME `ctrl` AbortController — if the user navigates or types a new message, `abortRef.current?.abort()` (line 44) aborts the prior controller, but the retry's `setTimeout` at line 118 is not cleared. If the retry fires after the user sent a new turn, it will race with the new stream and double-post. Also, if the CSRF cookie rotated (e.g., session renewal), the retry reuses the stale header from `readCsrfCookie()` called at the original send — actually this one is fine (it re-reads on retry since it's inside `attempt()`), disregard. Main bug is the orphaned setTimeout.

**Fix:**
```ts
let retryTimer: ReturnType<typeof setTimeout> | null = null;
ctrl.signal.addEventListener("abort", () => {
  if (retryTimer) clearTimeout(retryTimer);
});
// ... replace `await new Promise(r => setTimeout(r, delay))` with a cancellable variant.
```

### WR-07: `bridge_rpc` and `modules_rpc` trust `request.json()` without size limits

**File:** `bot/engine/bridge_rpc.py:74, 86`; `bot/engine/modules_rpc.py:68, 112`

**Issue:** `await request.json()` is unbounded. Even on loopback, a misbehaving upstream route handler could pass a massive body (e.g., 100 MB of module config) and OOM the engine. FastAPI does not enforce a default max body size.

**Fix:** Wrap engine reads with an explicit content-length cap:
```python
async def _read_json_bounded(req: Request, max_bytes: int = 1_048_576) -> dict:
    cl = int(req.headers.get("content-length") or 0)
    if cl > max_bytes:
        raise HTTPException(413, "payload too large")
    return await req.json()
```

## Info

### IN-01: `bridge_rpc.regen_code` is identical to `claim_code`, hides intent

**File:** `bot/engine/bridge_rpc.py:65-67`

**Issue:** `regen` aliases `claim`, so "regenerate" doesn't invalidate the old code before issuing a new one. That's fine if `generate_pairing_code` is atomic-rewrite by design, but the sharing is implicit.

**Fix:** Add a docstring noting the idempotent-replace semantic, OR have `regen` call `revoke_code` first to make intent explicit.

### IN-02: Hardcoded production origin fallback

**File:** `dashboard/lib/csrf.shared.ts:19`

**Issue:** `"https://animaya.makscee.ru"` hardcodes a user-specific host. Contributors running against their own domain will be rejected by `verifyCsrf` unless they set `NEXT_PUBLIC_ANIMAYA_PUBLIC_ORIGIN` — but no errorfail-fast if the env var is missing in production.

**Fix:** Fail-closed in production when neither env var is set:
```ts
if (process.env.NODE_ENV === "production" &&
    !process.env.NEXT_PUBLIC_ANIMAYA_PUBLIC_ORIGIN &&
    !process.env.ANIMAYA_PUBLIC_ORIGIN) {
  throw new Error("ANIMAYA_PUBLIC_ORIGIN required in production");
}
```

### IN-03: `readOwnerId` caches `null` permanently on first miss

**File:** `dashboard/lib/owner.server.ts:22-34`

**Issue:** If OWNER.md is absent at first call, `cached = null` is memoized forever (per process). Subsequent writes to OWNER.md during the same process lifetime are ignored. A `_resetOwnerCache()` test hook exists but there's no prod signal to refresh. Low impact since OWNER.md is set once at install, but a stale `null` means any later-installed OWNER.md never takes effect without a restart.

**Fix:** Cache with a short TTL (e.g., 60s) rather than indefinitely, or don't cache `null` (re-read on miss).

### IN-04: `modules_jobs._lock.locked()` check is TOCTOU

**File:** `bot/engine/modules_jobs.py:146-147, 167-168`

**Issue:** `if _lock.locked(): raise InProgressError` is checked outside the lock; two concurrent callers can both observe "unlocked" and both create tasks, which then serialize via `async with _lock` but return 200 (not 409) to one of them. The race is narrow and the subsequent `async with _lock` still serializes the actual work, but the 409 contract is not guaranteed.

**Fix:** Use a single atomic CAS via a counter or `asyncio.Semaphore(1)` with `.locked()` semantics replaced by `.acquire_nowait()` / `QueueFull` handling.

### IN-05: `deploy.sh` passes `.env` through rsync and prints smoke test with `$DASHBOARD_TOKEN`

**File:** `scripts/deploy.sh:26-30, 40`

**Issue:** `rsync -az --delete ./` will sync the local `.env` file to the LXC unless excluded (it's not in the exclude list). The smoke-test echo at line 40 references `$DASHBOARD_TOKEN` in a way that could land in shell history. Not a bug per se but low-entropy leak.

**Fix:** Add `--exclude .env` (or use a deny-list pattern) and use `'...'` single-quote echo so the variable isn't expanded into scrollback.

### IN-06: `ModuleDTO` permits `config` but has no redaction guard in the list route

**File:** `dashboard/lib/schemas.ts:82-88`; `dashboard/app/api/modules/route.ts:29-34`

**Issue:** Schema comment claims unknown fields are stripped, but `config` is declared as `ModuleConfigSchema.optional()` (arbitrary keys allowed). Callers relying on the schema for redaction are misled. See CR-02 for the stronger fix; this entry flags the docstring accuracy.

**Fix:** Update the comment at lines 75-79 of `schemas.ts` to accurately describe what Zod does ("strips only fields not declared") and delegate redaction explicitly.

---

_Reviewed: 2026-04-17T21:50:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
