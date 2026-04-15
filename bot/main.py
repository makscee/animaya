"""Animaya bot — entry point (Phase 5 update).

Validates environment, initialises data dir, rotates events log,
assembles CLAUDE.md, then runs the Telegram bridge and FastAPI
dashboard in the same asyncio event loop.
"""
from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

import uvicorn

from bot.dashboard.app import build_app as build_dashboard_app
from bot.events import rotate as rotate_events
from bot.modules.assembler import assemble_claude_md
from bot.modules.registry import get_entry
from bot.modules_runtime.git_versioning import HUB_ROOT, commit_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "TELEGRAM_BOT_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "SESSION_SECRET",
    "TELEGRAM_OWNER_ID",
    "TELEGRAM_BOT_USERNAME",
)
DEFAULT_DATA_PATH = str(Path.home() / "hub" / "knowledge" / "animaya")


def main() -> None:
    """Entry point: validate env, init data dir, rotate events, assemble
    CLAUDE.md, then run uvicorn + Telegram polling in one event loop."""
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            logger.error("%s not set", var)
            sys.exit(1)

    data_path = Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))
    data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Data path: %s", data_path)

    # Rotate events log at startup (D-21).
    try:
        rotate_events()
    except Exception:  # noqa: BLE001 — never fail startup on rotate
        logger.exception("events.log rotation failed")

    # Assemble CLAUDE.md before starting the bridge.
    assemble_claude_md(data_path)

    logger.info("Animaya starting Telegram bridge + dashboard")
    try:
        asyncio.run(_run(data_path))
    except KeyboardInterrupt:
        logger.info("Shutdown via KeyboardInterrupt")


async def _run(data_path: Path) -> None:
    """Spin up uvicorn + PTB polling in the running event loop, wait for
    a stop signal, then shut both down cleanly."""
    from bot.bridge.telegram import build_app  # noqa: PLC0415

    async def _post_init(application) -> None:
        """Spawn module-owned background tasks (Phase 4 git-versioning)."""
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
    tg_app = build_app(token, post_init=_post_init)

    dashboard_app = build_dashboard_app(hub_dir=data_path)
    dashboard_host = os.environ.get("DASHBOARD_HOST", "127.0.0.1")
    config = uvicorn.Config(
        dashboard_app,
        host=dashboard_host,
        port=int(os.environ.get("DASHBOARD_PORT", "8090")),
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("DASHBOARD_FORWARDED_ALLOW_IPS", "127.0.0.1"),
        log_level="info",
    )
    server = uvicorn.Server(config)

    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass  # Windows / constrained environments.

    uvicorn_task = asyncio.create_task(server.serve(), name="uvicorn")
    logger.info("Dashboard serving at http://127.0.0.1:%s", config.port)

    async with tg_app:
        await tg_app.start()
        await tg_app.updater.start_polling()
        try:
            await stop_event.wait()
        finally:
            logger.info("Shutting down")
            await tg_app.updater.stop()
            await tg_app.stop()
            server.should_exit = True
            await uvicorn_task


# ``assemble_claude_md`` is imported from ``bot.modules.assembler`` above.
# It is re-exported here so ``from bot.main import assemble_claude_md`` keeps
# working (regression tests in tests/test_skeleton.py rely on this).
__all__ = [
    "DEFAULT_DATA_PATH",
    "REQUIRED_ENV_VARS",
    "assemble_claude_md",
    "build_dashboard_app",
    "main",
    "rotate_events",
]
