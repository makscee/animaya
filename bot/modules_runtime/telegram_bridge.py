"""Telegram bridge runtime adapter — supervisor-driven on_start/on_stop (D-8.3)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from bot.modules.context import AppContext

logger = logging.getLogger(__name__)

# ── Module lifecycle hooks ──────────────────────────────────────────────


async def on_start(ctx: AppContext, config: dict[str, Any]) -> Any:
    """Start Telegram polling. Returns the PTB Application as the supervisor handle.

    Args:
        ctx: Supervisor-provided AppContext (data_path, stop_event, event_bus, dashboard_app).
        config: Module config loaded from modules/telegram-bridge/config.json.
                Must contain 'token' (bot token from @BotFather).

    Returns:
        The started PTB Application (used as handle for on_stop).

    Raises:
        ValueError: if config lacks a non-empty 'token' field.
    """
    token = config.get("token")
    if not token:
        raise ValueError("telegram-bridge config.json missing 'token' field")

    # Deferred import: bot.bridge.telegram must NOT appear in core boot path (BRDG-01).
    from bot.bridge.telegram import build_app  # noqa: PLC0415

    post_init = _make_post_init(ctx)
    tg_app = build_app(token, post_init=post_init)

    # Store module_dir in bot_data so claim handler can read/write state.json.
    from bot.modules.registry import get_entry  # noqa: PLC0415

    entry = get_entry(ctx.data_path, "telegram-bridge")
    if entry:
        tg_app.bot_data["module_dir"] = Path(entry["module_dir"])

    # Explicit init/shutdown (Pitfall 1) — do NOT use `async with tg_app:`.
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    logger.info("telegram-bridge polling started")
    return tg_app


async def on_stop(handle: Any) -> None:
    """Shut down Telegram polling in the documented PTB order.

    Order is critical: updater.stop() cancels the long-polling HTTP loop,
    stop() drains pending updates, shutdown() releases the httpx pool.
    The v1.0 code in bot/main.py missed shutdown() — this adapter fixes it.
    """
    # Idempotent: PTB raises if already stopped — catch and log.
    try:
        await handle.updater.stop()
    except Exception:
        logger.exception("updater.stop failed (may already be stopped)")
    try:
        await handle.stop()
    except Exception:
        logger.exception("stop failed (may already be stopped)")
    try:
        await handle.shutdown()
    except Exception:
        logger.exception("shutdown failed (may already be shut down)")
    logger.info("telegram-bridge polling stopped")


# ── Internal helpers ────────────────────────────────────────────────────


def _make_post_init(ctx: AppContext):  # type: ignore[return]
    """Build a PTB post_init callback that closes over AppContext."""

    async def _post_init(app: Any) -> None:
        # Hook for bridge-specific boot: in v1.0 this spawned git-versioning.
        # Per 08-RESEARCH.md Open Question #2: git-versioning commit loop stays
        # wired outside supervisor in Phase 8 — keep this callback minimal.
        logger.info("telegram-bridge post_init (data_path=%s)", ctx.data_path)

    return _post_init
