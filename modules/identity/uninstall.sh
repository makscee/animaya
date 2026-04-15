#!/usr/bin/env bash
set -euo pipefail

# Identity module uninstall (Phase 4, MODS-05)
# Removes ~/hub/knowledge/identity/ entirely (USER.md, SOUL.md, .pending-onboarding).
# Idempotent: safe to run on partial install or twice.
KNOWLEDGE_DIR="$(dirname "${ANIMAYA_HUB_DIR}")"
IDENTITY_DIR="${KNOWLEDGE_DIR}/identity"

rm -rf "${IDENTITY_DIR}"
echo "[identity] uninstalled (identity data removed at ${IDENTITY_DIR})"
