# Dashboard

Next.js 16 (App Router) dashboard for Animaya. Runs on port 8090 behind the
Python engine's reverse proxy. Authenticates via one of three modes:
Telegram Login Widget (default), `DASHBOARD_TOKEN` header/query (ops bypass),
or voidnet HMAC-signed headers (Voidnet LXC integration).

## Environment

### Core

- `AUTH_SECRET` — NextAuth v5 JWT signing secret. Generate with
  `openssl rand -base64 32`. Required.
- `OWNER_TELEGRAM_ID` — Telegram user id of the owner. Written at LXC provision
  time from `OWNER.md` (Phase 11 contract). Every authenticated session must
  match this id; mismatch → 403. Edge middleware fails closed if unset.
- `NEXT_PUBLIC_TELEGRAM_BOT_USERNAME` — Bot username (no `@`) for the Telegram
  Login Widget on `/login`. Source: @BotFather → your bot → Bot Info.
- `DASHBOARD_TOKEN` — Optional ops bypass token. When set, requests presenting
  it via `x-dashboard-token` header or `?token=` query param skip the auth
  chain entirely (ops-only; strips any existing session cookie).
- `DASHBOARD_PORT` — Port the dashboard reports in
  `/api/integration/v1/meta` (default `8090`).

## Environment: voidnet integration

### `VOIDNET_HMAC_SECRET`

Shared secret between `voidnet-api` and this dashboard that activates
voidnet-proxied auth mode. When set, the dashboard accepts
HMAC-SHA256-signed `X-Voidnet-*` headers injected by `voidnet-api` and
synthesizes a NextAuth session without presenting the Telegram Login Widget.
The secret must match the one held by `voidnet-api` for the target LXC.
Unset or empty → voidnet mode is disabled and the standalone Telegram login
flow runs unchanged (backward compatible).

### `OWNER_TELEGRAM_ID` pairing invariant

`VOIDNET_HMAC_SECRET` always pairs with `OWNER_TELEGRAM_ID`. Every signed
voidnet request carries an `X-Voidnet-Telegram-Id` header that MUST equal
`OWNER_TELEGRAM_ID`; requests with a mismatching telegram id are rejected 403
with code `VOIDNET_OWNER_MISMATCH` — no silent fallback to the Telegram flow.
`voidnet-api` writes `OWNER_TELEGRAM_ID` at LXC provision time so the pairing
normally holds; the dashboard still defends the invariant.

### Signed request contract

- Headers: `X-Voidnet-User-Id`, `X-Voidnet-Handle` (3–32 chars,
  `^[a-z][a-z0-9-]+$`), `X-Voidnet-Telegram-Id`, `X-Voidnet-Timestamp`
  (unix seconds), `X-Voidnet-Signature` (hex HMAC-SHA256).
- Signature: `hmac_sha256(VOIDNET_HMAC_SECRET, "{user_id}|{handle}|{telegram_id}|{timestamp}")`
- Replay window: ±60 seconds.
- Error codes: `VOIDNET_SCHEMA`, `VOIDNET_STALE`, `VOIDNET_SIG_INVALID` (401) /
  `VOIDNET_OWNER_MISMATCH` (403).

See also `/api/integration/v1/meta` for the version/capabilities probe used by
`voidnet-api` to verify deployment compatibility.
