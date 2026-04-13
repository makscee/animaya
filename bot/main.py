"""Animaya bot — entry point.

Validates environment, creates data directory, assembles CLAUDE.md,
and starts Telegram polling via the bridge module.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ("TELEGRAM_BOT_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")
DEFAULT_DATA_PATH = str(Path.home() / "hub" / "knowledge" / "animaya")


async def main() -> None:
    """Entry point: validate env, init data dir, assemble CLAUDE.md, start Telegram polling."""
    # Validate required environment variables
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            logger.error("%s not set", var)
            sys.exit(1)

    # Create data directory
    data_path = Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))
    data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Data path: %s", data_path)

    # Assemble CLAUDE.md before starting the bridge
    assemble_claude_md(data_path)

    logger.info("Animaya starting Telegram bridge")

    # Start Telegram polling — blocks until SIGINT/SIGTERM
    from bot.bridge.telegram import build_app  # noqa: PLC0415

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = build_app(token)
    logger.info("Telegram polling started")
    await app.run_polling()


def assemble_claude_md(data_path: Path) -> None:
    """Write base CLAUDE.md with empty module list.

    Phase 3 module system will extend this to merge installed module prompts.

    Args:
        data_path: Directory where CLAUDE.md will be written.

    Returns:
        None
    """
    claude_md = data_path / "CLAUDE.md"
    claude_md.write_text(
        "# Animaya\n"
        "\n"
        "You are Animaya, a personal AI assistant.\n"
        "\n"
        "<!-- module-prompts-start -->\n"
        "<!-- No modules installed -->\n"
        "<!-- module-prompts-end -->\n"
    )
    logger.info("CLAUDE.md assembled at %s (0 modules)", claude_md)
