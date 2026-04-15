#!/usr/bin/env bash
set -euo pipefail

# Identity module install (Phase 4, IDEN-01/02)
# Identity dir is a SIBLING of ANIMAYA_HUB_DIR (~/hub/knowledge/animaya → ~/hub/knowledge/identity)
KNOWLEDGE_DIR="$(dirname "${ANIMAYA_HUB_DIR}")"
IDENTITY_DIR="${KNOWLEDGE_DIR}/identity"
mkdir -p "${IDENTITY_DIR}"

# Placeholder content with sentinel marker — bridge detects via marker
if [ ! -f "${IDENTITY_DIR}/USER.md" ]; then
  cat > "${IDENTITY_DIR}/USER.md" <<'EOF'
<!-- animaya:placeholder -->
# User

(Pending onboarding — the user will describe themselves on first message.)
EOF
fi

if [ ! -f "${IDENTITY_DIR}/SOUL.md" ]; then
  cat > "${IDENTITY_DIR}/SOUL.md" <<'EOF'
<!-- animaya:placeholder -->
# Assistant Identity

(Pending onboarding — the user will shape the assistant's persona.)
EOF
fi

# Pending-onboarding sentinel (durable across restarts)
printf 'awaiting first user message\n' > "${IDENTITY_DIR}/.pending-onboarding"

echo "[identity] install complete; onboarding pending at ${IDENTITY_DIR}"
