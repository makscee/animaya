#!/usr/bin/env bash
set -euo pipefail

# Bridge module install (Phase 3, D-02)
# Context injected by bot.modules installer (D-11):
#   ANIMAYA_MODULE_DIR  - this module's directory
#   ANIMAYA_HUB_DIR     - hub state directory
#   ANIMAYA_CONFIG_JSON - user config as JSON string

echo "[bridge] install starting"
echo "[bridge]   module_dir : ${ANIMAYA_MODULE_DIR}"
echo "[bridge]   hub_dir    : ${ANIMAYA_HUB_DIR}"
echo "[bridge]   config     : ${ANIMAYA_CONFIG_JSON}"

# Bridge code lives in bot/bridge/ (managed by the repo, not this script).
# No hub artifacts to create; nothing to install.

echo "[bridge] install complete"
exit 0
