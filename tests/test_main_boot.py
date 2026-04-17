"""Boot-order and env-matrix tests for bot/main.py (Plan 08-03, BRDG-04).

Tests verify:
1. TELEGRAM_BOT_TOKEN NOT in REQUIRED_ENV_VARS
2. _run() with empty registry + no env vars + mocked uvicorn + mocked Supervisor
3. Token seed: bridge registered, no config token, env set → config.json written
4. Token seed idempotent: config.json already has token → env ignored
5. No import of bot.bridge.telegram in main.py
6. migrate_bridge_rename called during _run()
7. Dashboard uvicorn task started BEFORE supervisor.start_all
8. On stop_event, supervisor.stop_all awaited BEFORE uvicorn shutdown
"""
from __future__ import annotations

import ast
import asyncio
import json
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.main import REQUIRED_ENV_VARS, _run


# ── Test 1: TELEGRAM_BOT_TOKEN not required ───────────────────────────────────

def test_telegram_bot_token_not_in_required_env_vars() -> None:
    """BRDG-04: TELEGRAM_BOT_TOKEN must not be in REQUIRED_ENV_VARS."""
    assert "TELEGRAM_BOT_TOKEN" not in REQUIRED_ENV_VARS, (
        "TELEGRAM_BOT_TOKEN should be optional after Plan 03 — "
        "bridge token lives in config.json, not env"
    )


# ── Test 2: _run() with empty registry + no token env succeeds ───────────────

async def test_run_with_empty_registry_and_no_token_env_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: _run() with empty registry + no env vars starts dashboard without error."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth-token")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dash-token")

    # Write empty registry so no modules start
    reg_file = tmp_path / "registry.json"
    reg_file.write_text(json.dumps({"modules": []}))

    mock_server = MagicMock()
    mock_server.serve = AsyncMock(return_value=None)
    mock_server.should_exit = False

    with (
        patch("bot.main.uvicorn.Server", return_value=mock_server),
        patch("bot.main.uvicorn.Config", return_value=MagicMock()),
        patch("bot.main.rotate_events"),
        patch("bot.main.assemble_claude_md"),
        patch("bot.main.migrate_bridge_rename", return_value=False),
        patch("bot.main.migrate_drop_memory", return_value=False),
        patch("bot.main.Supervisor") as MockSupervisor,
    ):
        mock_sup_instance = MockSupervisor.return_value
        mock_sup_instance.start_all = AsyncMock()
        mock_sup_instance.stop_all = AsyncMock()

        # Pre-set stop_event so _run() exits immediately after starting
        original_event_class = asyncio.Event

        call_count = 0

        def _make_event():
            nonlocal call_count
            ev = original_event_class()
            call_count += 1
            if call_count == 1:  # first event created is stop_event
                ev.set()  # pre-set so we exit immediately
            return ev

        with patch("bot.main.asyncio.Event", side_effect=_make_event):
            await _run(tmp_path)

        # No exception = success (dashboard-only mode)
        mock_sup_instance.start_all.assert_called_once()
        mock_sup_instance.stop_all.assert_called_once()


# ── Test 3: Token seed writes env token into config.json ─────────────────────

def test_token_seed_writes_env_token_to_config_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: When bridge registered + config tokenless + env set → config.json written."""
    from bot.main import _seed_telegram_bridge_token
    from bot.modules.registry import write_registry

    hub_dir = tmp_path
    module_dir = tmp_path / "modules" / "telegram-bridge"
    module_dir.mkdir(parents=True)

    write_registry(hub_dir, {"modules": [
        {
            "name": "telegram-bridge",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-01T00:00:00+00:00",
            "config": {},
            "depends": [],
            "module_dir": str(module_dir),
            "runtime_entry": "bot.modules_runtime.telegram_bridge",
        }
    ]})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env-seeded-token")

    _seed_telegram_bridge_token(hub_dir)

    config_path = module_dir / "config.json"
    assert config_path.exists(), "config.json must be created by seed helper"
    data = json.loads(config_path.read_text())
    assert data.get("token") == "env-seeded-token"


# ── Test 4: Token seed is idempotent ─────────────────────────────────────────

def test_token_seed_idempotent_when_config_already_has_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-04: config.json already has token → env ignored (no overwrite)."""
    from bot.main import _seed_telegram_bridge_token
    from bot.modules.registry import write_registry

    hub_dir = tmp_path
    module_dir = tmp_path / "modules" / "telegram-bridge"
    module_dir.mkdir(parents=True)

    # Pre-write config.json with existing token
    config_path = module_dir / "config.json"
    config_path.write_text(json.dumps({"token": "already-stored-token"}))

    write_registry(hub_dir, {"modules": [
        {
            "name": "telegram-bridge",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-01T00:00:00+00:00",
            "config": {},
            "depends": [],
            "module_dir": str(module_dir),
            "runtime_entry": "bot.modules_runtime.telegram_bridge",
        }
    ]})

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "different-env-token")

    _seed_telegram_bridge_token(hub_dir)

    data = json.loads(config_path.read_text())
    assert data.get("token") == "already-stored-token", (
        "Existing token in config.json must NOT be overwritten by env var"
    )


# ── Test 5: No import of bot.bridge.telegram in main.py ──────────────────────

def test_no_bridge_telegram_import_in_main_py() -> None:
    """BRDG-01: bot.bridge.telegram must NOT appear in any import statement in main.py."""
    src = Path("bot/main.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        # Check 'from X import Y' statements
        if isinstance(node, ast.ImportFrom) and node.module:
            assert "bot.bridge.telegram" not in node.module, (
                f"Found forbidden import of bot.bridge.telegram in main.py: {node.module}"
            )
        # Check 'import X' statements
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "bot.bridge.telegram" not in alias.name, (
                    f"Found forbidden import alias of bot.bridge.telegram in main.py"
                )
        # Check string literals used as deferred module args (importlib.import_module("bot.bridge..."))
        # but skip docstrings (first statement of module/class/function bodies).
        if isinstance(node, (ast.Call,)):
            func = node.func
            func_name = ""
            if isinstance(func, ast.Attribute):
                func_name = func.attr
            elif isinstance(func, ast.Name):
                func_name = func.id
            if func_name in ("import_module",) and node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                    assert "bot.bridge.telegram" not in first_arg.value, (
                        "Found deferred import_module('bot.bridge.telegram') in main.py"
                    )


# ── Test 6: migrate_bridge_rename called during _run() ───────────────────────

async def test_migrate_bridge_rename_called_during_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """BRDG-01 + 260416-ncp: _run() must call both migrations at boot."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth-token")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dash-token")

    migrate_calls = []
    memory_migrate_calls = []

    def _capture_migrate(data_path):
        migrate_calls.append(data_path)
        return False

    def _capture_memory_migrate(data_path):
        memory_migrate_calls.append(data_path)
        return False

    mock_server = MagicMock()
    mock_server.serve = AsyncMock(return_value=None)

    with (
        patch("bot.main.uvicorn.Server", return_value=mock_server),
        patch("bot.main.uvicorn.Config", return_value=MagicMock()),
        patch("bot.main.rotate_events"),
        patch("bot.main.assemble_claude_md"),
        patch("bot.main.migrate_bridge_rename", side_effect=_capture_migrate),
        patch("bot.main.migrate_drop_memory", side_effect=_capture_memory_migrate),
        patch("bot.main.Supervisor") as MockSupervisor,
    ):
        mock_sup = MockSupervisor.return_value
        mock_sup.start_all = AsyncMock()
        mock_sup.stop_all = AsyncMock()

        original_event_class = asyncio.Event
        call_count = 0

        def _make_event():
            nonlocal call_count
            ev = original_event_class()
            call_count += 1
            if call_count == 1:
                ev.set()
            return ev

        with patch("bot.main.asyncio.Event", side_effect=_make_event):
            await _run(tmp_path)

    assert len(migrate_calls) == 1, "migrate_bridge_rename must be called exactly once"
    assert migrate_calls[0] == tmp_path
    assert len(memory_migrate_calls) == 1, "migrate_drop_memory must be called exactly once"
    assert memory_migrate_calls[0] == tmp_path


# ── Test 7: Dashboard uvicorn task created BEFORE supervisor.start_all ───────

async def test_dashboard_starts_before_supervisor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-8.7: asyncio.create_task(server.serve()) must be called BEFORE supervisor.start_all.

    The ordering invariant is about *task creation* (scheduling), not about when
    the coroutine body executes. We record the order of create_task vs start_all.
    """
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth-token")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dash-token")

    calls: list[str] = []

    mock_server = MagicMock()
    mock_server.serve = AsyncMock(return_value=None)

    # Intercept asyncio.create_task to record when uvicorn task is scheduled
    original_create_task = asyncio.create_task

    def _tracking_create_task(coro, *, name=None):
        if name == "uvicorn":
            calls.append("uvicorn.task_created")
        return original_create_task(coro, name=name)

    with (
        patch("bot.main.uvicorn.Server", return_value=mock_server),
        patch("bot.main.uvicorn.Config", return_value=MagicMock()),
        patch("bot.main.rotate_events"),
        patch("bot.main.assemble_claude_md"),
        patch("bot.main.migrate_bridge_rename", return_value=False),
        patch("bot.main.migrate_drop_memory", return_value=False),
        patch("bot.main.asyncio.create_task", side_effect=_tracking_create_task),
        patch("bot.main.Supervisor") as MockSupervisor,
    ):
        async def _start_all(ctx):
            calls.append("supervisor.start_all")

        mock_sup = MockSupervisor.return_value
        mock_sup.start_all = _start_all
        mock_sup.stop_all = AsyncMock()

        original_event_class = asyncio.Event
        call_count = 0

        def _make_event():
            nonlocal call_count
            ev = original_event_class()
            call_count += 1
            if call_count == 1:
                ev.set()
            return ev

        with patch("bot.main.asyncio.Event", side_effect=_make_event):
            await _run(tmp_path)

    assert "uvicorn.task_created" in calls, "uvicorn task must be created via asyncio.create_task"
    assert "supervisor.start_all" in calls, "supervisor.start_all must be called"
    assert calls.index("uvicorn.task_created") < calls.index("supervisor.start_all"), (
        "Dashboard uvicorn task must be CREATED (scheduled) BEFORE supervisor.start_all is awaited"
    )


# ── Test 8: supervisor.stop_all awaited BEFORE uvicorn shutdown ───────────────

async def test_supervisor_stop_all_before_uvicorn_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D-8.7: supervisor.stop_all must complete BEFORE server.should_exit is set."""
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth-token")
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dash-token")

    shutdown_calls: list[str] = []

    mock_server = MagicMock()
    mock_server.serve = AsyncMock(return_value=None)

    # Track when should_exit is set
    original_set = object.__setattr__

    class TrackingServer:
        def __setattr__(self, name, value):
            if name == "should_exit" and value is True:
                shutdown_calls.append("uvicorn.should_exit")
            object.__setattr__(self, name, value)

        serve = AsyncMock(return_value=None)
        should_exit = False

    tracking_server = TrackingServer()

    with (
        patch("bot.main.uvicorn.Server", return_value=tracking_server),
        patch("bot.main.uvicorn.Config", return_value=MagicMock()),
        patch("bot.main.rotate_events"),
        patch("bot.main.assemble_claude_md"),
        patch("bot.main.migrate_bridge_rename", return_value=False),
        patch("bot.main.migrate_drop_memory", return_value=False),
        patch("bot.main.Supervisor") as MockSupervisor,
    ):
        async def _stop_all():
            shutdown_calls.append("supervisor.stop_all")

        mock_sup = MockSupervisor.return_value
        mock_sup.start_all = AsyncMock()
        mock_sup.stop_all = _stop_all

        original_event_class = asyncio.Event
        call_count = 0

        def _make_event():
            nonlocal call_count
            ev = original_event_class()
            call_count += 1
            if call_count == 1:
                ev.set()
            return ev

        with patch("bot.main.asyncio.Event", side_effect=_make_event):
            await _run(tmp_path)

    assert "supervisor.stop_all" in shutdown_calls, "supervisor.stop_all must be called"
    assert "uvicorn.should_exit" in shutdown_calls, "uvicorn.should_exit must be set"
    assert shutdown_calls.index("supervisor.stop_all") < shutdown_calls.index("uvicorn.should_exit"), (
        "supervisor.stop_all must complete BEFORE uvicorn is shut down"
    )
