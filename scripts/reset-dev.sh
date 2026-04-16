#!/usr/bin/env bash
# reset-dev.sh — wipe Animaya runtime state for fresh-install testing.
#
# Preserves: code (except BOOTSTRAP.md — restored from git), venv, .env
#            (tokens + SESSION_SECRET + DASHBOARD_TOKEN), systemd unit.
# Wipes: installed-module state, registry, hub knowledge dirs,
#        onboarding data, generated identity files.
# Restores: BOOTSTRAP.md from the git index (so next boot re-runs onboarding).
#
# Idempotent. Safe to re-run at will.

set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
HUB_DIR="${ANIMAYA_HUB_DIR:-$HOME/hub/knowledge}"
SERVICE="animaya.service"
export XDG_RUNTIME_DIR="/run/user/$(id -u)"

echo "[reset-dev] install_dir: $INSTALL_DIR"
echo "[reset-dev] hub_dir    : $HUB_DIR"

echo "[reset-dev] --> stopping $SERVICE"
systemctl --user stop "$SERVICE" 2>/dev/null || true

echo "[reset-dev] --> clearing Claude Code SDK session store"
rm -rf "$HOME/.claude/projects"

echo "[reset-dev] --> restoring BOOTSTRAP.md from git index"
git -C "$INSTALL_DIR" checkout -- BOOTSTRAP.md 2>/dev/null || true

echo "[reset-dev] --> clearing per-module runtime state"
find "$INSTALL_DIR/modules" -maxdepth 2 -type f \( -name state.json -o -name config.json \) -print -delete 2>/dev/null || true

echo "[reset-dev] --> clearing hub knowledge dirs"
# Default HUB_DIR=$HOME/hub/knowledge; wipes hub/knowledge/identity, hub/knowledge/memory, hub/knowledge/animaya
rm -rf "$HUB_DIR/animaya" "$HUB_DIR/identity" "$HUB_DIR/memory"

echo "[reset-dev] --> starting $SERVICE"
systemctl --user start "$SERVICE"
sleep 2
systemctl --user is-active "$SERVICE"

echo "[reset-dev] done. Bot is at first-boot state (no modules, no owner, no identity, BOOTSTRAP restored)."
