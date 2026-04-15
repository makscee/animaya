"""Animaya bot — entry point.

Validates environment, creates data directory, assembles CLAUDE.md,
and starts Telegram polling via the bridge module.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from bot.modules.assembler import assemble_claude_md
from bot.modules.registry import get_entry
from bot.modules_runtime.git_versioning import HUB_ROOT, commit_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS = ("TELEGRAM_BOT_TOKEN", "CLAUDE_CODE_OAUTH_TOKEN")
DEFAULT_DATA_PATH = str(Path.home() / "hub" / "knowledge" / "animaya")


def main() -> None:
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
    # run_polling() is sync — it creates and manages its own event loop
    from bot.bridge.telegram import build_app  # noqa: PLC0415

    async def _post_init(application) -> None:
        """Spawn module-owned background tasks (runs inside the event loop)."""
        entry = get_entry(data_path, "git-versioning")
        if entry is None:
            logger.info("git-versioning not installed; skipping commit loop")
            return
        interval = (
            entry.get("config", {}).get("interval_seconds")
            if isinstance(entry.get("config"), dict)
            else None
        ) or 300
        application.create_task(
            commit_loop(interval=interval, repo_root=HUB_ROOT),
            name="git-autocommit",
        )
        logger.info(
            "git-versioning commit loop scheduled (interval=%ds, repo=%s)",
            interval,
            HUB_ROOT,
        )

    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = build_app(token, post_init=_post_init)
    logger.info("Telegram polling started")
    app.run_polling()


# ``assemble_claude_md`` is imported from ``bot.modules.assembler`` above.
# It is re-exported here so ``from bot.main import assemble_claude_md`` keeps
# working (regression tests in tests/test_skeleton.py rely on this).
__all__ = ["DEFAULT_DATA_PATH", "REQUIRED_ENV_VARS", "assemble_claude_md", "main"]
