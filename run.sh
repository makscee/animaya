#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── INST-04: Sanitize Claude Code env vars to prevent SDK subprocess hangs ─────
unset CLAUDECODE
unset CLAUDECODE_EXECUTION_ID

# ── Load environment ───────────────────────────────────────────────────────────
set -a
# shellcheck source=/dev/null
source "$INSTALL_DIR/.env"
set +a

# ── Activate venv and run bot ──────────────────────────────────────────────────
exec "$INSTALL_DIR/.venv/bin/python" -m bot
