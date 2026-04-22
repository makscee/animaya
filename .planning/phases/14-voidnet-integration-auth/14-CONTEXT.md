# Phase 14 — VoidNet Integration Auth

**Driver:** [voidnet](../../../voidnet) wants to host Animaya per-user as a managed service. Each user gets their own LXC+Animaya instance. Access must flow through voidnet's login (no Telegram widget double-login) and travel through voidnet-api as a reverse proxy (Animaya LXCs are NAT'd, not internet-reachable).

**Scope:** Add a first-class "voidnet-proxied" auth mode to the Next.js dashboard. Keep the existing Telegram + DASHBOARD_TOKEN paths working for standalone deploys.

**Out of scope:** Python bot changes. Bridge/module changes. DB schema changes. This is a dashboard-middleware-only phase.

## Decisions locked

- **Auth carrier:** HMAC-signed request headers injected by voidnet-api on every proxied request. No OAuth round-trip, no browser cookies involving Animaya. Keeps voidnet as the only session holder.
- **Headers** (names chosen for cross-service reuse — voidnet will inject the same set for every future service):
  - `X-Voidnet-User-Id: <i64>`
  - `X-Voidnet-Handle: <string>` (the voidnet username, 3–32 chars, `[a-z][a-z0-9-]+`)
  - `X-Voidnet-Telegram-Id: <i64>` — this is the Animaya `OWNER_TELEGRAM_ID` authority
  - `X-Voidnet-Timestamp: <unix-seconds>`
  - `X-Voidnet-Signature: <hex-hmac-sha256>`
- **Signature:** `hmac_sha256(VOIDNET_HMAC_SECRET, "{user_id}|{handle}|{telegram_id}|{timestamp}")`
- **Replay window:** 60 seconds. Reject timestamps outside ±60s.
- **Activation:** if `VOIDNET_HMAC_SECRET` env is set → voidnet mode enabled. If absent → current Telegram flow runs unchanged (backward compatible for standalone users).
- **Owner check:** validated `X-Voidnet-Telegram-Id` must equal `OWNER_TELEGRAM_ID` env. Mismatch → 403. (voidnet writes OWNER_TELEGRAM_ID at provision time so this normally matches, but we defend the invariant.)
- **Session shape:** on successful voidnet validation, synthesize a NextAuth JWT session identical to the one a Telegram login would produce for that telegram_id. Downstream code (modules, bridge UI, SSE) must not need to branch on auth source.
- **SSE/streaming:** every streamed request is a fresh POST with headers — no session persistence problem. Signature re-validated per request; timestamp bounds keep replay bounded.

## Why not OIDC / cookie-domain / dashboard_token

- **OIDC:** right long-term answer, but requires voidnet-api to stand up `/authorize` + `/token` + `/userinfo` and Animaya to run the OAuth client dance. 4× the code for 1 service. Revisit when the 3rd service appears.
- **Cookie-domain (`.makscee.ru` scope):** voidnet-api proxies everything anyway because LXCs are NAT'd — the browser never talks to Animaya directly. A shared cookie doesn't help when one side can't receive it.
- **Abusing `DASHBOARD_TOKEN`:** the existing token was designed to bypass session checks for deploy scripts; middleware strips session cookies on token use. Reusing it for interactive traffic disables NextAuth sessions in subtle ways and couples voidnet to upstream implementation details that aren't a contract.

## Required new files / changes

1. **`dashboard/lib/voidnet-auth.server.ts`** — pure signature verify + timestamp bounds + claims parsing.
2. **`dashboard/middleware.ts`** — add voidnet-auth check BEFORE existing Telegram gate. If valid → inject synthetic session claims into request context so downstream auth() / `getServerSession()` sees a real user. If headers present but signature bad → 401. If headers absent → fall through to existing logic.
3. **`dashboard/auth.config.ts`** — new `credentials` provider named `"voidnet"` or an adapter that turns voidnet claims into a NextAuth JWT. Per NextAuth v5 docs, easiest is a custom `jwt()` callback that trusts a `req.voidnet` claim injected by middleware.
4. **`dashboard/app/api/integration/v1/meta/route.ts`** — returns `{version, supported_auth_modes: ["telegram","voidnet"], dashboard_port: 8090}`. voidnet probes this before proxying to detect version mismatch.
5. **Env contract doc:** update `DASHBOARD.md` / `README.md` with the `VOIDNET_HMAC_SECRET` + `OWNER_TELEGRAM_ID` pair.

## Integration contract voidnet will implement (for reference, not this repo's work)

- voidnet sets `VOIDNET_HMAC_SECRET` in LXC `.env` at provision time (copy of the one in voidnet-api's env).
- voidnet-api proxies `animaya.makscee.ru/*` → `lxc_ip:8090/*` over Tailscale.
- voidnet-api requires portal session cookie on `animaya.makscee.ru`; unauth → 302 to voidnet login.
- voidnet-api does NOT forward the user's portal session cookie to Animaya (voidnet session cookie stays scoped to voidnet.makscee.ru).
- voidnet-api calls `GET /api/integration/v1/meta` once per LXC at first-probe and caches version; refuses proxying if incompatible.

## Open questions for the planning agent

1. How does NextAuth v5 middleware + Edge runtime handle injecting synthetic session claims? (May need to move to Node middleware.)
2. Does the existing `middleware.ts` Telegram-ID check (`OWNER_TELEGRAM_ID`) run in Edge or Node? If Edge, HMAC verification needs `crypto.subtle` not `node:crypto`.
3. Should `VOIDNET_HMAC_SECRET` rotation be supported (accept current + previous)? Recommend yes — future-proof.
4. SSE responses from `useSSE` — does the browser re-send signed headers on the fetch body upload path? (Voidnet proxy injects them; the browser never sees them, so yes automatic.)

## Success criteria

- With `VOIDNET_HMAC_SECRET` set and valid signed headers → user is auth'd without seeing the Telegram widget.
- With invalid signature / expired timestamp → 401 (not fallthrough — explicit signal that voidnet is misconfigured).
- With no voidnet headers → Telegram login works exactly as today.
- Owner Telegram ID mismatch → 403 with clear error (not silent fallback).
- `GET /api/integration/v1/meta` returns the contract shape.
- All existing dashboard tests pass.

## Followup phase (not this one)

Phase 15 will add `POST /api/integration/v1/update` — receives a webhook from voidnet's "Update Animaya" button and runs `git fetch && bun run build && systemctl --user restart`. Keeps voidnet out of the SSH-and-rebuild business; Animaya self-updates on signal.
