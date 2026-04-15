#!/usr/bin/env bash
set -euo pipefail

# telegram-bridge module uninstall (Phase 8, D-8.5)
# Must be IDEMPOTENT (safe to run on partial/full install; RESEARCH Pitfall 3).

echo "[telegram-bridge] uninstall starting"
echo "[telegram-bridge]   hub_dir    : ${ANIMAYA_HUB_DIR}"

# No owned_paths declared -> nothing to remove.
# Code removal is repo-managed (git), not this script's concern (D-02).

echo "[telegram-bridge] uninstall complete"
exit 0
