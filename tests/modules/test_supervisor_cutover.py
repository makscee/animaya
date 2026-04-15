"""BRDG-03: Supervisor installs/uninstalls bridge module via on_start/on_stop.

All tests are xfail (strict=True) until Plan 02 lands the telegram_bridge
runtime adapter and wires lifecycle.uninstall() to call supervisor.stop().
"""
from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

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


def _write_bridge_registry(hub_dir: Path, runtime_entry: str = "bot.modules_runtime.telegram_bridge") -> None:
    write_registry(hub_dir, {"modules": [
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
    ]})


# ── Tests ─────────────────────────────────────────────────────────────

@pytest.mark.xfail(reason="lands in Plan 02: telegram_bridge runtime adapter not yet created", strict=True)
async def test_supervisor_install_starts_bridge_via_on_start(tmp_path: Path) -> None:
    """BRDG-03: bot.modules_runtime.telegram_bridge.on_start must exist as a real coroutine
    (not a mock) that accepts (ctx, config) and returns a PTB Application handle."""
    # This test verifies the REAL telegram_bridge module exists and works end-to-end.
    # It imports the ACTUAL module — Plan 02 must create bot/modules_runtime/telegram_bridge.py.
    # We do NOT mock on_start here — the real module must exist.
    import importlib  # noqa: PLC0415

    # This import will fail until Plan 02 creates the module:
    mod = importlib.import_module("bot.modules_runtime.telegram_bridge")

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)
    ctx = _make_app_ctx(hub_dir)

    # The real on_start must accept (ctx, config) and return a PTB Application
    handle = await mod.on_start(ctx, {"token": "test-token"})

    # Must return something with stop/shutdown (PTB Application interface)
    assert hasattr(handle, "stop"), "on_start must return PTB Application (has .stop)"
    assert hasattr(handle, "shutdown"), "on_start must return PTB Application (has .shutdown)"


@pytest.mark.xfail(reason="lands in Plan 02: lifecycle.uninstall integration with Supervisor not yet wired", strict=True)
async def test_supervisor_uninstall_stops_bridge_via_on_stop(tmp_path: Path) -> None:
    """BRDG-03: lifecycle.uninstall calls supervisor.stop() BEFORE uninstall.sh runs.

    Plan 02 wires Supervisor into lifecycle.uninstall() so on_stop is
    invoked first. Currently lifecycle.uninstall() has no supervisor reference.
    """
    import json  # noqa: PLC0415

    from bot.modules.lifecycle import uninstall  # noqa: PLC0415

    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)
    _write_bridge_registry(hub_dir)

    call_order: list[str] = []

    # Create minimal module dir
    mod_dir = tmp_path / "modules" / "telegram-bridge"
    mod_dir.mkdir(parents=True, exist_ok=True)
    manifest_data = {
        "manifest_version": 1,
        "name": "telegram-bridge",
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
    uninstall_sh = mod_dir / "uninstall.sh"
    # uninstall.sh records its call
    uninstall_sh.write_text(
        f"#!/usr/bin/env bash\nset -euo pipefail\n"
        f"echo 'uninstall.sh ran' >> {tmp_path}/call_order.txt\n"
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

    from bot.modules.supervisor import Supervisor  # noqa: PLC0415

    ctx = _make_app_ctx(hub_dir)
    sup = Supervisor()
    await sup.start_all(ctx)

    # Plan 02: uninstall must accept supervisor and stop the module first.
    # The current signature is uninstall(name, hub_dir, module_dir) — no supervisor param.
    # This call will fail because the current uninstall() doesn't accept a supervisor arg.
    uninstall("telegram-bridge", hub_dir, mod_dir, supervisor=sup)  # type: ignore[call-arg]

    order_file = tmp_path / "call_order.txt"
    uninstall_ran = order_file.exists() and "uninstall.sh ran" in order_file.read_text()

    assert "on_stop" in call_order, "on_stop must be called during uninstall"
    assert uninstall_ran, "uninstall.sh must also run"
    assert call_order.index("on_stop") == 0, "on_stop must run BEFORE uninstall.sh"


@pytest.mark.xfail(reason="lands in Plan 02: bot.modules_runtime.telegram_bridge.on_stop not yet implemented", strict=True)
async def test_on_stop_follows_updater_stop_then_stop_then_shutdown_order(tmp_path: Path) -> None:
    """BRDG-03: telegram_bridge.on_stop calls updater.stop → stop → shutdown in order."""
    # This imports the REAL module — fails until Plan 02 creates it
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


@pytest.mark.xfail(reason="lands in Plan 02: registry migration bridge→telegram-bridge not yet implemented", strict=True)
async def test_reenable_after_uninstall_needs_reinstall(tmp_path: Path) -> None:
    """BRDG-03: Seeding registry with old name 'bridge' → migration → 'telegram-bridge'."""
    hub_dir = tmp_path / "hub" / "knowledge" / "animaya"
    hub_dir.mkdir(parents=True, exist_ok=True)

    # Seed with old name
    write_registry(hub_dir, {"modules": [
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
    ]})

    # Plan 02 adds this migration function — import will fail until then
    from bot.modules import migrate_registry  # type: ignore[attr-defined]  # noqa: PLC0415

    migrate_registry(hub_dir)

    from bot.modules.registry import get_entry  # noqa: PLC0415

    old_entry = get_entry(hub_dir, "bridge")
    new_entry = get_entry(hub_dir, "telegram-bridge")

    assert old_entry is None, "Old 'bridge' entry must be removed after migration"
    assert new_entry is not None, "New 'telegram-bridge' entry must exist after migration"
    assert new_entry["config"]["token"] == "tok"
