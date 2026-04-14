#!/usr/bin/env bash
set -euo pipefail

# Bridge module uninstall (Phase 3, D-02)
# Must be IDEMPOTENT (safe to run on partial/full install; RESEARCH Pitfall 3).

echo "[bridge] uninstall starting"
echo "[bridge]   hub_dir    : ${ANIMAYA_HUB_DIR}"

# No owned_paths declared -> nothing to remove.
# Code removal is repo-managed (git), not this script's concern (D-02).

echo "[bridge] uninstall complete"
exit 0
