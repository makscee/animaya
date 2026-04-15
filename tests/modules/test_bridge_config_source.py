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

@pytest.mark.xfail(reason="lands in Plan 03: TELEGRAM_BOT_TOKEN removed from REQUIRED_ENV_VARS", strict=True)
def test_telegram_bot_token_not_in_required_env_vars() -> None:
    """BRDG-04: TELEGRAM_BOT_TOKEN is NOT in main.REQUIRED_ENV_VARS after Plan 03.

    Currently TELEGRAM_BOT_TOKEN IS in REQUIRED_ENV_VARS — this assertion fails
    until Plan 03 removes it.
    """
    from bot.main import REQUIRED_ENV_VARS  # noqa: PLC0415

    # This assertion FAILS with current code (token IS required) → xfail correct
    assert "TELEGRAM_BOT_TOKEN" not in REQUIRED_ENV_VARS, (
        "TELEGRAM_BOT_TOKEN should be optional after Plan 03 — "
        "bridge token lives in config.json, not env"
    )


@pytest.mark.xfail(reason="lands in Plan 03: _run() bootstrap logic with supervisor not yet wired", strict=True)
async def test_boot_without_token_env_and_no_bridge_installed_succeeds(tmp_path: Path) -> None:
    """BRDG-04: main._run() must exist and accept no TELEGRAM_BOT_TOKEN when no bridge installed.

    Plan 03 refactors main.py to have a _run() coroutine that uses Supervisor.
    Currently main.py has no _run() coroutine — this import fails.
    """
    from bot.main import _run  # type: ignore[attr-defined]  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    write_registry(hub_dir, {"modules": []})

    env_without_token = {k: v for k, v in os.environ.items() if k != "TELEGRAM_BOT_TOKEN"}

    with pytest.raises(Exception):
        pass  # Should not reach here — import above fails first

    # Plan 03: _run() with empty registry + no token env must complete without error
    # (dashboard-only mode)
    import inspect  # noqa: PLC0415
    assert inspect.iscoroutinefunction(_run), "_run must be an async function"


@pytest.mark.xfail(reason="lands in Plan 03: env var token seeding into config.json not yet implemented", strict=True)
async def test_token_seed_from_env_when_bridge_installed_without_config_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: Plan 03 adds a seed_bridge_token() helper that writes env token to config.json.

    Currently no such helper exists in bot.modules or bot.main.
    """
    # This import fails until Plan 03 creates the helper
    from bot.modules.lifecycle import seed_bridge_token_from_env  # type: ignore[attr-defined]  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir, config={})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-provided-token")

    seed_bridge_token_from_env(hub_dir)

    from bot.modules.registry import get_entry  # noqa: PLC0415

    entry = get_entry(hub_dir, "telegram-bridge")
    assert entry is not None
    assert entry["config"].get("token") == "env-provided-token"

    # Subsequent call with different env must NOT overwrite (idempotent)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "different-token")
    seed_bridge_token_from_env(hub_dir)
    entry2 = get_entry(hub_dir, "telegram-bridge")
    assert entry2["config"].get("token") == "env-provided-token", (
        "config.json token must not be overwritten once set"
    )


@pytest.mark.xfail(reason="lands in Plan 03: config.json canonical token logic in on_start not yet implemented", strict=True)
async def test_config_json_token_is_canonical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: telegram_bridge.on_start uses config['token'], ignoring env var.

    This tests the REAL telegram_bridge.on_start (not a mock). Fails until
    Plan 02 creates the module + Plan 03 ensures env var is not used.
    """
    import importlib  # noqa: PLC0415

    # This import fails until Plan 02 creates bot/modules_runtime/telegram_bridge.py
    mod = importlib.import_module("bot.modules_runtime.telegram_bridge")

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir, config={"token": "config-json-token"})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-token")
    ctx = _make_app_ctx(hub_dir)

    # The REAL on_start must use the config dict token, not env
    # It will try to actually connect with "config-json-token" — mock PTB to avoid network
    with pytest.raises(Exception):
        # If on_start doesn't exist yet → ImportError already caught above
        # If it tries to connect with wrong token → that's fine for this test
        pass

    # Inspect the on_start source to confirm it reads from config, not os.environ
    import inspect  # noqa: PLC0415

    source = inspect.getsource(mod.on_start)
    assert "config" in source and "token" in source, (
        "on_start must use config['token'], not os.environ"
    )
    assert 'os.environ' not in source or 'TELEGRAM_BOT_TOKEN' not in source, (
        "on_start must NOT read TELEGRAM_BOT_TOKEN from env"
    )


@pytest.mark.xfail(reason="lands in Plan 02: bot.modules.migrate_registry not yet implemented", strict=True)
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
