#!/usr/bin/env bash
# e2e-debug.sh — voidnet-signed curl client for animaya dashboard
#
# Hits the LXC dashboard directly via tailnet (http://100.101.0.7:33000) with
# voidnet HMAC headers + proper Origin + persisted cookies. Reproduces the
# same flow a browser sees when proxied through voidnet-api on mcow.
#
# Usage:
#   scripts/e2e-debug.sh <METHOD> <PATH> [JSON_BODY]
#
# Examples:
#   scripts/e2e-debug.sh GET  /api/modules
#   scripts/e2e-debug.sh GET  /api/bridge
#   scripts/e2e-debug.sh POST /api/modules/telegram-bridge/install '{}'
#   scripts/e2e-debug.sh POST /api/chat/stream '{"message":"hi"}'
#   scripts/e2e-debug.sh GET  /modules                # HTML (page SSR)
#
# Env overrides:
#   ANIMAYA_LXC_URL   default: http://100.101.0.7:33000
#   LXC_SSH_TARGET    default: root@tower
#   LXC_CTID          default: 212
#
# The script reads VOIDNET_HMAC_SECRET + OWNER_TELEGRAM_ID once from the LXC
# .env via ssh, caches them at /tmp/animaya-e2e.env, and reuses until stale.
set -euo pipefail

METHOD=${1:?"METHOD required (GET|POST|PUT|DELETE)"}
URL_PATH=${2:?"PATH required (e.g. /api/modules)"}
BODY=${3:-}

: "${ANIMAYA_LXC_URL:=http://100.101.0.7:33000}"
: "${LXC_SSH_TARGET:=root@tower}"
: "${LXC_CTID:=212}"

ENV_CACHE=/tmp/animaya-e2e.env
JAR=/tmp/animaya-e2e-jar

# Refresh env cache if older than 1h or missing.
if [[ ! -f $ENV_CACHE ]] || (( $(date +%s) - $(stat -f %m "$ENV_CACHE" 2>/dev/null || stat -c %Y "$ENV_CACHE") > 3600 )); then
  ssh "$LXC_SSH_TARGET" "pct exec $LXC_CTID -- grep -E '^(VOIDNET_HMAC_SECRET|OWNER_TELEGRAM_ID|DASHBOARD_TOKEN)=' /home/maks-test/animaya/.env" > "$ENV_CACHE"
fi
# shellcheck disable=SC1090
source "$ENV_CACHE"

USER_ID=${USER_ID:-45}
HANDLE=${HANDLE:-maks-test}
TS=$(date +%s)
MSG="${USER_ID}|${HANDLE}|${OWNER_TELEGRAM_ID}|${TS}"
SIG=$(printf '%s' "$MSG" | openssl dgst -sha256 -hmac "$VOIDNET_HMAC_SECRET" -hex | awk '{print $NF}')

# Generate a stable CSRF token per jar for the session's lifetime.
if [[ ! -f ${JAR}.csrf ]]; then
  head -c 32 /dev/urandom | xxd -p | tr -d '\n' > "${JAR}.csrf"
fi
CSRF=$(cat "${JAR}.csrf")

# Warm jar on first call so subsequent requests carry session cookie too.
if [[ ! -f $JAR ]]; then
  curl -sS -o /dev/null -c "$JAR" \
    -H "x-voidnet-user-id: ${USER_ID}" \
    -H "x-voidnet-handle: ${HANDLE}" \
    -H "x-voidnet-telegram-id: ${OWNER_TELEGRAM_ID}" \
    -H "x-voidnet-timestamp: ${TS}" \
    -H "x-voidnet-signature: ${SIG}" \
    "${ANIMAYA_LXC_URL}/" || true
fi

CURL_ARGS=(
  -sS
  -i
  -b "$JAR" -c "$JAR"
  -H "x-voidnet-user-id: ${USER_ID}"
  -H "x-voidnet-handle: ${HANDLE}"
  -H "x-voidnet-telegram-id: ${OWNER_TELEGRAM_ID}"
  -H "x-voidnet-timestamp: ${TS}"
  -H "x-voidnet-signature: ${SIG}"
  -H "origin: https://animaya.makscee.ru"
  -H "x-csrf-token: ${CSRF}"
  -X "$METHOD"
  --max-time 15
  "${ANIMAYA_LXC_URL}${URL_PATH}"
)
if [[ -n $BODY ]]; then
  CURL_ARGS+=(-H "content-type: application/json" --data-raw "$BODY")
fi

exec curl "${CURL_ARGS[@]}"
