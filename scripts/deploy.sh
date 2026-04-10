#!/usr/bin/env bash
set -euo pipefail

# Deploy animaya bot to mcow
# Usage: ./scripts/deploy.sh

REMOTE="root@mcow"
REMOTE_DIR="/opt/animaya"

echo "=== Deploying Animaya to mcow ==="

# Sync source
echo ">> Syncing files..."
rsync -avz --exclude '.git' --exclude '.venv' --exclude '__pycache__' \
    --exclude 'data' --exclude '.env' --exclude '*.pyc' \
    . "$REMOTE:$REMOTE_DIR/"

# Build and restart
echo ">> Building and restarting..."
ssh "$REMOTE" "cd $REMOTE_DIR && docker compose -f docker/docker-compose.yml up --build -d"

echo ">> Checking status..."
ssh "$REMOTE" "docker ps --filter name=animaya-bot --format 'table {{.Names}}\t{{.Status}}'"

echo "=== Deploy complete ==="
