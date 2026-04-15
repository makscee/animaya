#!/usr/bin/env bash
set -euo pipefail

# Memory module uninstall (Phase 4, MODS-05)
# Removes ALL memory data. Idempotent.
KNOWLEDGE_DIR="$(dirname "${ANIMAYA_HUB_DIR}")"
MEMORY_DIR="${KNOWLEDGE_DIR}/memory"

rm -rf "${MEMORY_DIR}"
echo "[memory] uninstalled (all memory data removed at ${MEMORY_DIR})"
