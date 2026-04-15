"""Supervisor: runtime lifecycle manager for bot modules (D-8.1, D-8.2).

Iterates the registry, imports each module's runtime_entry, and invokes
on_start / on_stop callables in registration / reverse-registration order.
Exception policy: failing module is logged + emitted as module.errored;
boot continues for remaining modules (D-8.2 exception policy).
"""
from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path

from bot.modules.context import AppContext
from bot.modules.registry import read_registry

logger = logging.getLogger(__name__)


def _load_module_config(entry: dict) -> dict:
    """Load config from module_dir/config.json, fall back to registry entry."""
    module_dir = entry.get("module_dir", "")
    if module_dir:
        config_path = Path(module_dir) / "config.json"
        if config_path.is_file():
            try:
                return json.loads(config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
    return entry.get("config", {}) or {}


# ── Supervisor ────────────────────────────────────────────────────────
class Supervisor:
    """Manages runtime lifecycle (start/stop) for installed bot modules.

    Usage:
        supervisor = Supervisor()
        await supervisor.start_all(ctx)
        # ... bot running ...
        await supervisor.stop_all()
    """

    def __init__(self) -> None:
        # name → runtime handle returned by on_start
        self._handles: dict[str, object] = {}
        # name → dotted module path, needed for stop_all re-import
        self._runtime_entries: dict[str, str] = {}
        # event_bus captured from ctx during start_all, used by stop_all
        self._event_bus: object | None = None

    # ── Start ─────────────────────────────────────────────────────────
    async def start_all(self, ctx: AppContext) -> None:
        """Start all installed modules that have a runtime_entry.

        Iterates registry in installation order. Modules with runtime_entry=None
        are silently skipped (prompt-only modules). A module that raises during
        on_start is logged, emits module.errored, and does not block others.

        Args:
            ctx: Frozen AppContext shared with all modules.
        """
        self._event_bus = ctx.event_bus
        reg = read_registry(ctx.data_path)
        for entry in reg["modules"]:
            name: str = entry.get("name", "<unknown>")
            runtime_entry: str | None = entry.get("runtime_entry")

            if not runtime_entry:
                continue  # prompt-only module — skip

            ctx.event_bus("info", "supervisor", f"module.starting {name}")
            try:
                mod = importlib.import_module(runtime_entry)
                config = _load_module_config(entry)
                handle = await mod.on_start(ctx, config)
                self._handles[name] = handle
                self._runtime_entries[name] = runtime_entry
                ctx.event_bus("info", "supervisor", f"module.started {name}")
            except Exception:  # noqa: BLE001
                logger.exception("Supervisor: module %r on_start failed", name)
                ctx.event_bus("error", "supervisor", f"module.errored {name}")

    # ── Stop ──────────────────────────────────────────────────────────
    async def stop_all(self) -> None:
        """Stop all running modules in reverse registration order.

        Each module's on_stop is awaited. Failures are logged and do not
        prevent remaining modules from stopping. Clears all handle state.
        """
        _bus = self._event_bus
        for name, handle in reversed(list(self._handles.items())):
            runtime_entry = self._runtime_entries.get(name)
            logger.info("Supervisor: module.stopping %s", name)
            if _bus is not None:
                _bus("info", "supervisor", f"module.stopping {name}")
            try:
                if runtime_entry:
                    mod = importlib.import_module(runtime_entry)
                    await mod.on_stop(handle)
                logger.info("Supervisor: module.stopped %s", name)
                if _bus is not None:
                    _bus("info", "supervisor", f"module.stopped {name}")
            except Exception:  # noqa: BLE001
                logger.exception("Supervisor: module %r on_stop failed", name)

        self._handles.clear()
        self._runtime_entries.clear()

    # ── Query ─────────────────────────────────────────────────────────
    def get_handle(self, name: str) -> object | None:
        """Return the runtime handle for a running module, or None.

        Args:
            name: Module name (as stored in registry).

        Returns:
            Handle returned by on_start, or None if module not running.
        """
        return self._handles.get(name)
