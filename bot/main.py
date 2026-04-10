"""Animaya bot — entry point.

Starts the Telegram bridge connected to Claude Code SDK,
plus a FastAPI dashboard on port 8090.
"""
from __future__ import annotations

import logging
import os
import signal
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    if not os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        logger.error("CLAUDE_CODE_OAUTH_TOKEN not set")
        sys.exit(1)

    data_path = Path(os.environ.get("DATA_PATH", "/data"))
    data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Starting Animaya bot (data: %s)", data_path)

    # Git auto-versioning
    from bot.features.git_versioning import commit_if_changed, start_auto_commit

    if (data_path / ".git").exists():
        start_auto_commit(data_path)
    else:
        logger.info("No .git in data dir — auto-commit disabled")

    # Graceful shutdown: commit data before exit
    def _shutdown(signum, frame):
        logger.info("Shutdown signal received, committing data...")
        try:
            commit_if_changed(data_path)
        except Exception:
            logger.exception("Failed to commit on shutdown")
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    # Dashboard on port 8090 (background thread)
    from bot.dashboard.app import app as dashboard_app
    import threading
    import uvicorn

    def _run_dashboard():
        uvicorn.run(dashboard_app, host="0.0.0.0", port=8090, log_level="warning")

    threading.Thread(target=_run_dashboard, daemon=True).start()
    logger.info("Dashboard started on port 8090")

    # Telegram bridge (blocks on polling)
    from bot.bridge.telegram import build_app

    app = build_app(token)
    logger.info("Telegram bot starting...")
    app.run_polling(
        allowed_updates=["message", "edited_message", "callback_query", "my_chat_member"],
    )


if __name__ == "__main__":
    main()
