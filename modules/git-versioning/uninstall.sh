#!/usr/bin/env bash
set -euo pipefail

# git-versioning uninstall (Phase 4, D-14)
# NO-OP on the filesystem: existing git history is preserved.
# The commit loop running inside the bot will stop on next bot restart
# because main.py's post_init checks the registry.
echo "[git-versioning] uninstalled — existing git history preserved at ${HOME}/hub"
