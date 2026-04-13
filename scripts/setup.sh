#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$INSTALL_DIR/.venv"
SERVICE_NAME="animaya"
SERVICE_DIR="$HOME/.config/systemd/user"
SERVICE_FILE="$SERVICE_DIR/$SERVICE_NAME.service"
DATA_DIR="$HOME/hub/knowledge/animaya"
VERSION_FILE="$HOME/.animaya-version"
CURRENT_VERSION="0.1.0"

echo "==> Installing Animaya v$CURRENT_VERSION"

# ── .env handling ──────────────────────────────────────────────────────────────
if [[ -f "$INSTALL_DIR/.env" ]]; then
    echo "--> Validating existing .env..."
    # shellcheck source=/dev/null
    source "$INSTALL_DIR/.env"
    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
        echo "ERROR: TELEGRAM_BOT_TOKEN is missing or empty in .env" >&2
        exit 1
    fi
    if [[ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ]]; then
        echo "ERROR: CLAUDE_CODE_OAUTH_TOKEN is missing or empty in .env" >&2
        exit 1
    fi
    echo "--> .env validated."
else
    echo "--> Creating .env (tokens required)..."
    read -rp "Telegram bot token: " TELEGRAM_BOT_TOKEN
    read -rs -p "Claude OAuth token: " CLAUDE_CODE_OAUTH_TOKEN
    echo ""
    cat > "$INSTALL_DIR/.env" <<EOF
TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
CLAUDE_CODE_OAUTH_TOKEN=$CLAUDE_CODE_OAUTH_TOKEN
DATA_PATH=$DATA_DIR
EOF
    chmod 600 "$INSTALL_DIR/.env"
    echo "--> .env created and secured."
fi

# ── Node.js check ──────────────────────────────────────────────────────────────
if ! command -v node &>/dev/null; then
    echo "WARNING: Node.js not found. Claude Code SDK requires Node.js. Install it before running Animaya."
fi

# ── Python venv ────────────────────────────────────────────────────────────────
echo "--> Setting up Python virtualenv..."
[[ -d "$VENV" ]] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -e "$INSTALL_DIR"
echo "--> Dependencies installed."

# ── Hub knowledge dir ──────────────────────────────────────────────────────────
echo "--> Creating data directory..."
mkdir -p "$DATA_DIR"

# ── Version migration ──────────────────────────────────────────────────────────
if [[ -f "$VERSION_FILE" ]]; then
    OLD_VERSION=$(cat "$VERSION_FILE")
    if [[ "$OLD_VERSION" != "$CURRENT_VERSION" ]]; then
        echo "--> Migrating from $OLD_VERSION to $CURRENT_VERSION..."
        # No migration steps for 0.1.0
    fi
fi
echo "$CURRENT_VERSION" > "$VERSION_FILE"

# ── Systemd service ────────────────────────────────────────────────────────────
echo "--> Installing systemd user service..."
chmod +x "$INSTALL_DIR/run.sh"
mkdir -p "$SERVICE_DIR"
sed "s|%h/animaya|$INSTALL_DIR|g" "$INSTALL_DIR/systemd/animaya.service" > "$SERVICE_FILE"

if ! systemctl --user status &>/dev/null 2>&1; then
    echo "WARNING: systemd user mode not available. You may need to install the service as a system service."
    exit 0
fi

loginctl enable-linger "$USER" 2>/dev/null || true
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME"
systemctl --user restart "$SERVICE_NAME"

echo ""
echo "Animaya installed and running. Check status: systemctl --user status animaya"
