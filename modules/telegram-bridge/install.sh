#!/usr/bin/env bash
set -euo pipefail

# telegram-bridge module install (Phase 8, D-8.5)
# Context injected by bot.modules installer (D-11):
#   ANIMAYA_MODULE_DIR  - this module's directory
#   ANIMAYA_HUB_DIR     - hub state directory
#   ANIMAYA_CONFIG_JSON - user config as JSON string

echo "[telegram-bridge] install starting"
echo "[telegram-bridge]   module_dir : ${ANIMAYA_MODULE_DIR}"
echo "[telegram-bridge]   hub_dir    : ${ANIMAYA_HUB_DIR}"
echo "[telegram-bridge]   config     : ${ANIMAYA_CONFIG_JSON}"

# Bridge code lives in bot/bridge/ (managed by the repo, not this script).
# No hub artifacts to create; nothing to install.

echo "[telegram-bridge] install complete"
exit 0
