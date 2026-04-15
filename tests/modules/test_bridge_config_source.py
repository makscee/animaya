"""BRDG-04: Telegram bridge token sourced from config.json (not env var).

All tests are xfail (strict=True) until Plan 03 refactors main.py env-var
handling to make TELEGRAM_BOT_TOKEN optional and config.json canonical.

Tests use REAL imports (no mocks for the subject under test) so they fail
until Plans 02/03 implement the required changes.
"""
from __future__ import annotations

import asyncio
import os
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.modules.context import AppContext
from bot.modules.registry import write_registry


# ── Helpers ───────────────────────────────────────────────────────────

def _make_app_ctx(data_path: Path) -> AppContext:
    return AppContext(
        data_path=data_path,
        stop_event=asyncio.Event(),
        event_bus=lambda lvl, src, msg: None,
    )


def _write_bridge_registry(hub_dir: Path, config: dict | None = None) -> None:
    write_registry(hub_dir, {"modules": [
        {
            "name": "telegram-bridge",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-01T00:00:00+00:00",
            "config": config or {},
            "depends": [],
            "module_dir": "/tmp/telegram-bridge",
            "runtime_entry": "bot.modules_runtime.telegram_bridge",
        }
    ]})


# ── Tests ─────────────────────────────────────────────────────────────

def test_telegram_bot_token_not_in_required_env_vars() -> None:
    """BRDG-04: TELEGRAM_BOT_TOKEN is NOT in main.REQUIRED_ENV_VARS after Plan 03."""
    from bot.main import REQUIRED_ENV_VARS  # noqa: PLC0415

    assert "TELEGRAM_BOT_TOKEN" not in REQUIRED_ENV_VARS, (
        "TELEGRAM_BOT_TOKEN should be optional after Plan 03 — "
        "bridge token lives in config.json, not env"
    )


async def test_boot_without_token_env_and_no_bridge_installed_succeeds(tmp_path: Path) -> None:
    """BRDG-04: main._run() exists and is async after Plan 03."""
    from bot.main import _run  # noqa: PLC0415

    import inspect  # noqa: PLC0415
    assert inspect.iscoroutinefunction(_run), "_run must be an async function"


async def test_token_seed_from_env_when_bridge_installed_without_config_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: seed_bridge_token_from_env writes env token into registry config."""
    from bot.modules.lifecycle import seed_bridge_token_from_env  # noqa: PLC0415
    from bot.modules.registry import get_entry  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir, config={})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-provided-token")

    seed_bridge_token_from_env(hub_dir)

    entry = get_entry(hub_dir, "telegram-bridge")
    assert entry is not None
    assert entry["config"].get("token") == "env-provided-token"

    # Subsequent call with different env must NOT overwrite (idempotent)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "different-token")
    seed_bridge_token_from_env(hub_dir)
    entry2 = get_entry(hub_dir, "telegram-bridge")
    assert entry2["config"].get("token") == "env-provided-token", (
        "registry token must not be overwritten once set"
    )


async def test_config_json_token_is_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: telegram_bridge.on_start uses config['token'], not env var."""
    import importlib  # noqa: PLC0415
    import inspect  # noqa: PLC0415

    mod = importlib.import_module("bot.modules_runtime.telegram_bridge")

    # Inspect the on_start source to confirm it reads from config, not os.environ
    source = inspect.getsource(mod.on_start)
    assert "config" in source and "token" in source, (
        "on_start must use config['token'], not os.environ"
    )
    assert "TELEGRAM_BOT_TOKEN" not in source, (
        "on_start must NOT read TELEGRAM_BOT_TOKEN from env"
    )


async def test_bridge_rename_migration_bridge_to_telegram_bridge(tmp_path: Path) -> None:
    """BRDG-04: Old 'bridge' registry entry migrated to 'telegram-bridge' on startup.

    Plan 02 adds migrate_registry() to bot/modules/__init__.py.
    Currently bot.modules has no migrate_registry attribute → ImportError.
    """
    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)

    write_registry(hub_dir, {"modules": [
        {
            "name": "bridge",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-01T00:00:00+00:00",
            "config": {"token": "old-token"},
            "depends": [],
            "module_dir": "/tmp/bridge",
            "runtime_entry": "bot.modules_runtime.telegram_bridge",
        }
    ]})

    # This import fails until Plan 02 adds migrate_registry to bot/modules/__init__.py
    from bot.modules import migrate_registry  # type: ignore[attr-defined]  # noqa: PLC0415

    migrate_registry(hub_dir)

    from bot.modules.registry import get_entry  # noqa: PLC0415

    old_entry = get_entry(hub_dir, "bridge")
    new_entry = get_entry(hub_dir, "telegram-bridge")

    assert old_entry is None, "Old 'bridge' entry must be removed after migration"
    assert new_entry is not None, "New 'telegram-bridge' entry must exist after migration"
    assert new_entry["config"]["token"] == "old-token"
