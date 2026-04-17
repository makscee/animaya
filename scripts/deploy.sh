#!/usr/bin/env bash
# Deploy Animaya to the animaya-dev LXC (container 205 on tower).
#
# Phase 13 cutover: builds the new Docker image with Bun + Next.js +
# Python engine, with --no-cache (per CLAUDE.md — never trust Docker
# build cache during debugging). Smoke command printed at the end.
#
# Prerequisites (run once on the target LXC):
#   - Docker installed
#   - .env populated with TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN,
#     AUTH_SECRET, OWNER_TELEGRAM_ID, DASHBOARD_TOKEN,
#     NEXT_PUBLIC_TELEGRAM_BOT_USERNAME
#
# Usage:
#   ./scripts/deploy.sh [lxc_host]
#   LXC_HOST defaults to "tower" (Proxmox host); container id 205.

set -euo pipefail

LXC_HOST="${1:-tower}"
LXC_ID="${LXC_ID:-205}"
REMOTE_PATH="${REMOTE_PATH:-/opt/animaya}"

echo ">> Sync source to ${LXC_HOST} LXC ${LXC_ID}:${REMOTE_PATH}"
ssh "root@${LXC_HOST}" "pct exec ${LXC_ID} -- mkdir -p ${REMOTE_PATH}"
rsync -az --delete \
  --exclude '.git' --exclude '.venv' --exclude 'node_modules' \
  --exclude '.next' --exclude '__pycache__' --exclude '.claude' \
  ./ "root@${LXC_HOST}:/tmp/animaya-sync/"
ssh "root@${LXC_HOST}" "pct push ${LXC_ID} /tmp/animaya-sync ${REMOTE_PATH} --recursive" || \
  ssh "root@${LXC_HOST}" "rsync -az --delete /tmp/animaya-sync/ /var/lib/lxc/${LXC_ID}/rootfs${REMOTE_PATH}/"

echo ">> Build image (--no-cache — per CLAUDE.md Docker-cache rule)"
ssh "root@${LXC_HOST}" "pct exec ${LXC_ID} -- bash -c 'cd ${REMOTE_PATH} && docker compose -f docker/docker-compose.yml build --no-cache'"

echo ">> Restart container"
ssh "root@${LXC_HOST}" "pct exec ${LXC_ID} -- bash -c 'cd ${REMOTE_PATH} && docker compose -f docker/docker-compose.yml up -d'"

echo ">> Deployed. Smoke test:"
echo "   curl -H \"x-dashboard-token: \$DASHBOARD_TOKEN\" https://animaya-dev.<host>/api/modules | jq '.modules'"
echo "   (should return a JSON list with no bot_token fields)"
