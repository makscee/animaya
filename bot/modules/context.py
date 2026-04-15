"""AppContext: frozen context passed to module on_start hooks (D-8.2)."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from fastapi import FastAPI

# ── Type alias ───────────────────────────────────────────────────────
EventBus = Callable[[str, str, str], None]
"""Signature: emit(level: str, source: str, message: str) -> None"""


# ── AppContext ────────────────────────────────────────────────────────
@dataclass(frozen=True)
class AppContext:
    """Immutable context passed to module on_start / on_stop hooks.

    Args:
        data_path: Hub knowledge directory (e.g. ~/hub/knowledge/animaya/).
        stop_event: Asyncio event set when the platform is shutting down.
        event_bus: Callable emitting structured events (level, source, message).
        dashboard_app: FastAPI app instance, or None if dashboard not running.
    """

    data_path: Path
    stop_event: asyncio.Event
    event_bus: EventBus
    dashboard_app: FastAPI | None = field(default=None)
