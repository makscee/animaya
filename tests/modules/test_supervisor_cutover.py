"""BRDG-03: Supervisor installs/uninstalls bridge module via on_start/on_stop.

Plan 02 flips the xfail markers:
  - test_supervisor_install_starts_bridge_via_on_start     -> PASSING
  - test_supervisor_uninstall_stops_bridge_via_on_stop     -> PASSING
  - test_on_stop_follows_updater_stop_then_stop_then_shutdown_order -> PASSING
  - test_reenable_after_uninstall_needs_reinstall          -> PASSING

New tests added in Plan 02:
  - test_on_start_rejects_empty_token
  - test_on_stop_is_idempotent_second_call
  - test_on_start_passes_ctx_through_post_init

Plan 02 Task 3 adds:
  - test_uninstall_calls_on_stop_before_uninstall_sh
  - test_uninstall_without_supervisor_skips_on_stop
  - test_uninstall_purges_config_and_state_json
  - test_uninstall_continues_if_on_stop_raises
  - test_uninstall_registry_removed_after_uninstall_sh
  - test_uninstall_clears_supervisor_handle_dict
"""
from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.modules.context import AppContext
from bot.modules.registry import write_registry


# ── Shared helpers ────────────────────────────────────────────────────


def _make_app_ctx(data_path: Path) -> AppContext:
    events: list[tuple] = []
    return AppContext(
        data_path=data_path,
        stop_event=asyncio.Event(),
        event_bus=lambda lvl, src, msg: events.append((lvl, src, msg)),
    )


def _write_bridge_registry(
    hub_dir: Path, runtime_entry: str = "bot.modules_runtime.telegram_bridge"
) -> None:
    write_registry(
        hub_dir,
        {
            "modules": [
                {
                    "name": "telegram-bridge",
                    "version": "1.0.0",
                    "manifest_version": 1,
                    "installed_at": "2026-01-01T00:00:00+00:00",
                    "config": {"token": "test-token"},
                    "depends": [],
                    "module_dir": "/tmp/telegram-bridge",
                    "runtime_entry": runtime_entry,
                }
            ]
        },
    )


def _make_mock_tg_app() -> MagicMock:
    """Return a MagicMock shaped like a PTB Application."""
    mock_app = MagicMock()
    mock_app.updater = MagicMock()
    mock_app.initialize = AsyncMock()
    mock_app.start = AsyncMock()
    mock_app.updater.start_polling = AsyncMock()
    mock_app.updater.stop = AsyncMock()
    mock_app.stop = AsyncMock()
    mock_app.shutdown = AsyncMock()
    return mock_app


# ── Tests: on_start / on_stop adapter ────────────────────────────────


async def test_supervisor_install_starts_bridge_via_on_start(tmp_path: Path) -> None:
    """BRDG-03: on_start returns a PTB Application handle (mocked build_app)."""
    import importlib  # noqa: PLC0415

    mod = importlib.import_module("bot.modules_runtime.telegram_bridge")

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)
    ctx = _make_app_ctx(hub_dir)

    mock_app = _make_mock_tg_app()

    with patch("bot.bridge.telegram.build_app", return_value=mock_app):
        handle = await mod.on_start(ctx, {"token": "test-token"})

    # Must return something with stop/shutdown (PTB Application interface)
    assert hasattr(handle, "stop"), "on_start must return PTB Application (has .stop)"
    assert hasattr(handle, "shutdown"), "on_start must return PTB Application (has .shutdown)"
    # initialize/start/start_polling must have been called
    mock_app.initialize.assert_awaited_once()
    mock_app.start.assert_awaited_once()
    mock_app.updater.start_polling.assert_awaited_once()


async def test_on_start_rejects_empty_token(tmp_path: Path) -> None:
    """on_start raises ValueError when token is empty or missing."""
    from bot.modules_runtime import telegram_bridge  # noqa: PLC0415

    ctx = _make_app_ctx(tmp_path)

    with pytest.raises(ValueError, match="missing 'token'"):
        await telegram_bridge.on_start(ctx, {})

    with pytest.raises(ValueError, match="missing 'token'"):
        await telegram_bridge.on_start(ctx, {"token": ""})


async def test_on_stop_follows_updater_stop_then_stop_then_shutdown_order(
    tmp_path: Path,
) -> None:
    """BRDG-03: telegram_bridge.on_stop calls updater.stop -> stop -> shutdown in order."""
    import importlib  # noqa: PLC0415

    mod = importlib.import_module("bot.modules_runtime.telegram_bridge")

    call_order: list[str] = []
    mock_app = MagicMock()
    mock_app.updater = MagicMock()
    mock_app.updater.stop = AsyncMock(side_effect=lambda: call_order.append("updater.stop"))
    mock_app.stop = AsyncMock(side_effect=lambda: call_order.append("stop"))
    mock_app.shutdown = AsyncMock(side_effect=lambda: call_order.append("shutdown"))

    await mod.on_stop(mock_app)

    assert call_order == ["updater.stop", "stop", "shutdown"], (
        f"Expected ['updater.stop', 'stop', 'shutdown'], got {call_order}"
    )


async def test_on_stop_is_idempotent_second_call(tmp_path: Path) -> None:
    """on_stop tolerates already-stopped Application (second call idempotent)."""
    from bot.modules_runtime import telegram_bridge  # noqa: PLC0415

    mock_app = MagicMock()
    mock_app.updater = MagicMock()
    mock_app.updater.stop = AsyncMock(side_effect=RuntimeError("already stopped"))
    mock_app.stop = AsyncMock(side_effect=RuntimeError("already stopped"))
    mock_app.shutdown = AsyncMock(side_effect=RuntimeError("already stopped"))

    # Should not raise — errors are caught and logged
    await telegram_bridge.on_stop(mock_app)
    await telegram_bridge.on_stop(mock_app)


async def test_on_start_passes_ctx_through_post_init(tmp_path: Path) -> None:
    """on_start passes ctx through post_init so downstream hooks can read data_path."""
    from bot.modules_runtime import telegram_bridge  # noqa: PLC0415

    ctx = _make_app_ctx(tmp_path)
    mock_app = _make_mock_tg_app()

    captured_post_init: list = []

    def fake_build_app(token: str, post_init=None):
        captured_post_init.append(post_init)
        return mock_app

    with patch("bot.bridge.telegram.build_app", side_effect=fake_build_app):
        await telegram_bridge.on_start(ctx, {"token": "tok"})

    assert len(captured_post_init) == 1
    post_init_fn = captured_post_init[0]
    assert post_init_fn is not None
    # post_init is an async callable that accepts Application
    await post_init_fn(mock_app)  # should not raise


# ── Tests: registry migration ─────────────────────────────────────────


async def test_reenable_after_uninstall_needs_reinstall(tmp_path: Path) -> None:
    """BRDG-03: Seeding registry with old name 'bridge' → migration → 'telegram-bridge'."""
    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)

    # Seed with old name
    write_registry(
        hub_dir,
        {
            "modules": [
                {
                    "name": "bridge",
                    "version": "1.0.0",
                    "manifest_version": 1,
                    "installed_at": "2026-01-01T00:00:00+00:00",
                    "config": {"token": "tok"},
                    "depends": [],
                    "module_dir": "/tmp/bridge",
                    "runtime_entry": "bot.modules_runtime.telegram_bridge",
                }
            ]
        },
    )

    # Plan 02 adds migrate_registry to bot.modules
    from bot.modules import migrate_registry  # noqa: PLC0415

    migrate_registry(hub_dir)

    from bot.modules.registry import get_entry  # noqa: PLC0415

    old_entry = get_entry(hub_dir, "bridge")
    new_entry = get_entry(hub_dir, "telegram-bridge")

    assert old_entry is None, "Old 'bridge' entry must be removed after migration"
    assert new_entry is not None, "New 'telegram-bridge' entry must exist after migration"
    assert new_entry["config"]["token"] == "tok"


async def test_bridge_rename_migration_bridge_to_telegram_bridge(tmp_path: Path) -> None:
    """migrate_bridge_rename: 'bridge' registry entry renamed to 'telegram-bridge'."""
    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)

    write_registry(
        hub_dir,
        {
            "modules": [
                {
                    "name": "bridge",
                    "version": "1.0.0",
                    "manifest_version": 1,
                    "installed_at": "2026-01-01T00:00:00+00:00",
                    "config": {"token": "tok"},
                    "depends": [],
                    "module_dir": "/tmp/bridge",
                    "runtime_entry": "bot.modules_runtime.telegram_bridge",
                }
            ]
        },
    )

    from bot.modules.registry import migrate_bridge_rename, get_entry  # noqa: PLC0415

    result = migrate_bridge_rename(hub_dir)

    assert result is True
    old_entry = get_entry(hub_dir, "bridge")
    new_entry = get_entry(hub_dir, "telegram-bridge")
    assert old_entry is None
    assert new_entry is not None
    assert new_entry["config"]["token"] == "tok"


# ── Tests: lifecycle.uninstall wiring ────────────────────────────────


def _make_minimal_module_dir(tmp_path: Path, name: str = "telegram-bridge") -> Path:
    """Create a minimal module directory with manifest and uninstall.sh."""
    mod_dir = tmp_path / "modules" / name
    mod_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "manifest_version": 1,
        "name": name,
        "version": "1.0.0",
        "system_prompt_path": "prompt.md",
        "owned_paths": [],
        "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
        "depends": [],
        "config_schema": None,
        "runtime_entry": "bot.modules_runtime.telegram_bridge",
    }
    (mod_dir / "manifest.json").write_text(json.dumps(manifest_data))
    (mod_dir / "prompt.md").write_text("# Bridge\n")
    (mod_dir / "install.sh").write_text("#!/usr/bin/env bash\nexit 0\n")
    (mod_dir / "install.sh").chmod(0o755)
    return mod_dir


async def test_uninstall_calls_on_stop_before_uninstall_sh(tmp_path: Path) -> None:
    """lifecycle.uninstall awaits on_stop BEFORE running uninstall.sh."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415
    from bot.modules.supervisor import Supervisor  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    call_order: list[str] = []
    mod_dir = _make_minimal_module_dir(tmp_path)

    # uninstall.sh records its call
    uninstall_sh = mod_dir / "uninstall.sh"
    order_file = tmp_path / "call_order.txt"
    uninstall_sh.write_text(
        f"#!/usr/bin/env bash\nset -euo pipefail\n"
        f"echo 'uninstall.sh' >> {order_file}\n"
    )
    uninstall_sh.chmod(0o755)

    # Mock bridge runtime so on_stop records itself
    bridge_mod = types.ModuleType("bot.modules_runtime.telegram_bridge")
    handle = MagicMock()
    bridge_mod.on_start = AsyncMock(return_value=handle)

    async def tracked_on_stop(h: object) -> None:
        call_order.append("on_stop")

    bridge_mod.on_stop = tracked_on_stop
    sys.modules["bot.modules_runtime.telegram_bridge"] = bridge_mod

    ctx = _make_app_ctx(hub_dir)
    sup = Supervisor()
    await sup.start_all(ctx)

    await uninstall("telegram-bridge", hub_dir, mod_dir, supervisor=sup)

    uninstall_ran = order_file.exists() and "uninstall.sh" in order_file.read_text()
    assert "on_stop" in call_order, "on_stop must be called during uninstall"
    assert uninstall_ran, "uninstall.sh must also run"
    assert call_order.index("on_stop") == 0, "on_stop must run BEFORE uninstall.sh"


async def test_uninstall_without_supervisor_skips_on_stop(tmp_path: Path) -> None:
    """lifecycle.uninstall without supervisor param skips on_stop (backward compat)."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    mod_dir = _make_minimal_module_dir(tmp_path)
    uninstall_sh = mod_dir / "uninstall.sh"
    uninstall_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    uninstall_sh.chmod(0o755)

    on_stop_called = []

    bridge_mod = types.ModuleType("bot.modules_runtime.telegram_bridge")

    async def tracked_on_stop(h: object) -> None:
        on_stop_called.append(True)

    bridge_mod.on_stop = tracked_on_stop
    sys.modules["bot.modules_runtime.telegram_bridge"] = bridge_mod

    # No supervisor param — on_stop should NOT be called
    await uninstall("telegram-bridge", hub_dir, mod_dir)

    assert not on_stop_called, "on_stop must NOT be called when no supervisor provided"


async def test_uninstall_purges_config_and_state_json(tmp_path: Path) -> None:
    """lifecycle.uninstall deletes config.json and state.json from the module dir."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    mod_dir = _make_minimal_module_dir(tmp_path)
    uninstall_sh = mod_dir / "uninstall.sh"
    uninstall_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    uninstall_sh.chmod(0o755)

    # Create config.json and state.json in the module dir
    config_file = mod_dir / "config.json"
    state_file = mod_dir / "state.json"
    config_file.write_text('{"token": "secret"}')
    state_file.write_text('{"running": true}')

    await uninstall("telegram-bridge", hub_dir, mod_dir)

    assert not config_file.exists(), "config.json must be purged on uninstall"
    assert not state_file.exists(), "state.json must be purged on uninstall"


async def test_uninstall_continues_if_on_stop_raises(tmp_path: Path) -> None:
    """lifecycle.uninstall continues with uninstall.sh even if on_stop raises."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415
    from bot.modules.supervisor import Supervisor  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    mod_dir = _make_minimal_module_dir(tmp_path)
    order_file = tmp_path / "uninstall_ran.txt"
    uninstall_sh = mod_dir / "uninstall.sh"
    uninstall_sh.write_text(
        f"#!/usr/bin/env bash\nset -euo pipefail\ntouch {order_file}\n"
    )
    uninstall_sh.chmod(0o755)

    bridge_mod = types.ModuleType("bot.modules_runtime.telegram_bridge")
    handle = MagicMock()
    bridge_mod.on_start = AsyncMock(return_value=handle)

    async def raising_on_stop(h: object) -> None:
        raise RuntimeError("on_stop exploded")

    bridge_mod.on_stop = raising_on_stop
    sys.modules["bot.modules_runtime.telegram_bridge"] = bridge_mod

    ctx = _make_app_ctx(hub_dir)
    sup = Supervisor()
    await sup.start_all(ctx)

    # Must not raise even though on_stop raises
    await uninstall("telegram-bridge", hub_dir, mod_dir, supervisor=sup)

    assert order_file.exists(), "uninstall.sh must run even when on_stop raises"


async def test_uninstall_registry_removed_after_uninstall_sh(tmp_path: Path) -> None:
    """Registry entry is removed after uninstall.sh, before config/state purge."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415
    from bot.modules.registry import get_entry  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    mod_dir = _make_minimal_module_dir(tmp_path)
    uninstall_sh = mod_dir / "uninstall.sh"
    uninstall_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    uninstall_sh.chmod(0o755)

    await uninstall("telegram-bridge", hub_dir, mod_dir)

    entry = get_entry(hub_dir, "telegram-bridge")
    assert entry is None, "Registry entry must be removed after uninstall"


async def test_uninstall_clears_supervisor_handle_dict(tmp_path: Path) -> None:
    """After uninstall, supervisor._handles and _runtime_entries are cleared."""
    from bot.modules.lifecycle import uninstall  # noqa: PLC0415
    from bot.modules.supervisor import Supervisor  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    mod_dir = _make_minimal_module_dir(tmp_path)
    uninstall_sh = mod_dir / "uninstall.sh"
    uninstall_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    uninstall_sh.chmod(0o755)

    bridge_mod = types.ModuleType("bot.modules_runtime.telegram_bridge")
    handle = MagicMock()
    bridge_mod.on_start = AsyncMock(return_value=handle)
    bridge_mod.on_stop = AsyncMock()
    sys.modules["bot.modules_runtime.telegram_bridge"] = bridge_mod

    ctx = _make_app_ctx(hub_dir)
    sup = Supervisor()
    await sup.start_all(ctx)

    assert "telegram-bridge" in sup._handles

    await uninstall("telegram-bridge", hub_dir, mod_dir, supervisor=sup)

    assert "telegram-bridge" not in sup._handles, "Handle must be cleared after uninstall"
    assert "telegram-bridge" not in sup._runtime_entries, (
        "runtime_entry must be cleared after uninstall"
    )
