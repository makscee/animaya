#!/usr/bin/env bash
set -euo pipefail

# Memory module install (Phase 4, MEMO-01)
KNOWLEDGE_DIR="$(dirname "${ANIMAYA_HUB_DIR}")"
MEMORY_DIR="${KNOWLEDGE_DIR}/memory"
mkdir -p "${MEMORY_DIR}"

# CORE.md — rolling summary maintained by Haiku consolidation. Idempotent:
# do not overwrite an existing one (it may contain real consolidated content).
if [ ! -f "${MEMORY_DIR}/CORE.md" ]; then
  cat > "${MEMORY_DIR}/CORE.md" <<'EOF'
# Core Memory

(Auto-maintained by Haiku consolidation after every N user turns. Empty until first session.)
EOF
fi

if [ ! -f "${MEMORY_DIR}/README.md" ]; then
  cat > "${MEMORY_DIR}/README.md" <<'EOF'
# Memory

- `CORE.md` — rolling ~150-line summary auto-maintained by the memory module.
              Always injected into the system prompt as `<memory-core>`.
- Other files (e.g. `people.md`, `projects.md`, `preferences.md`) — topical
  memories written by the assistant on demand. Read with the Read tool when
  relevant to the current conversation.
EOF
fi

echo "[memory] install complete at ${MEMORY_DIR}"
