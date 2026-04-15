"""Tests for bot.main refactor: uvicorn + PTB on one loop + env validation.

Plan 05-07, Task 1 (RED) / Task 3 (GREEN).
"""
from __future__ import annotations

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


_ALL_REQUIRED = (
    "TELEGRAM_BOT_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "SESSION_SECRET",
    "TELEGRAM_OWNER_ID",
    "DASHBOARD_TOKEN",
)


def _set_all_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tg-token")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "oauth-token")
    monkeypatch.setenv("SESSION_SECRET", "sess-secret")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dashboard-token")


# ── Env-var validation tests ─────────────────────────────────────────


@pytest.mark.parametrize("missing_var", [
    "SESSION_SECRET",
    "TELEGRAM_OWNER_ID",
    "DASHBOARD_TOKEN",
])
def test_main_validates_new_required_env(
    missing_var: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """main() exits 1 with the missing var name mentioned in the log when
    SESSION_SECRET, TELEGRAM_OWNER_ID, or DASHBOARD_TOKEN is absent."""
    _set_all_required(monkeypatch)
    monkeypatch.delenv(missing_var, raising=False)
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    import bot.main as main_mod

    # Ensure we detect the new env vars — this drives the REQUIRED_ENV_VARS update.
    assert missing_var in main_mod.REQUIRED_ENV_VARS, (
        f"{missing_var} must be in REQUIRED_ENV_VARS"
    )

    caplog.set_level(logging.ERROR)
    with pytest.raises(SystemExit) as exc_info:
        main_mod.main()
    assert exc_info.value.code == 1
    assert missing_var in caplog.text


def test_main_validates_session_secret(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    """Explicit test — SESSION_SECRET missing -> SystemExit(1) + SESSION_SECRET in log."""
    _set_all_required(monkeypatch)
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    monkeypatch.setenv("DATA_PATH", str(tmp_path))
    import bot.main as main_mod
    caplog.set_level(logging.ERROR)
    with pytest.raises(SystemExit) as exc_info:
        main_mod.main()
    assert exc_info.value.code == 1
    assert "SESSION_SECRET" in caplog.text


# ── Startup side-effects ─────────────────────────────────────────────


def test_main_calls_events_rotate(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """main() calls bot.events.rotate() before starting the servers."""
    _set_all_required(monkeypatch)
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    calls: list[str] = []

    import bot.events as events_mod
    import bot.main as main_mod

    original_rotate = events_mod.rotate

    def _tracked_rotate(*a, **kw):
        calls.append("rotate")
        return original_rotate(*a, **kw)

    monkeypatch.setattr(events_mod, "rotate", _tracked_rotate)
    # Ensure main's reference is refreshed too
    monkeypatch.setattr(main_mod, "rotate_events", _tracked_rotate, raising=False)

    # Short-circuit the async runner so main() doesn't actually run servers.
    async def _noop_run(*a, **kw):
        calls.append("run")

    monkeypatch.setattr(main_mod, "_run", _noop_run)

    main_mod.main()

    assert "rotate" in calls
    # rotate must happen before _run
    assert calls.index("rotate") < calls.index("run")


def test_main_spawns_uvicorn_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """_run() must schedule a uvicorn server task alongside PTB polling."""
    import asyncio

    _set_all_required(monkeypatch)
    monkeypatch.setenv("DATA_PATH", str(tmp_path))

    import bot.main as main_mod

    # Stub uvicorn.Config / Server
    class _StubServer:
        def __init__(self, config):
            self.config = config
            self.should_exit = False
            self.served = False

        async def serve(self):
            self.served = True
            # Wait until asked to stop
            while not self.should_exit:
                await asyncio.sleep(0.01)

    stub_server_instances: list[_StubServer] = []

    def _stub_server(config):
        s = _StubServer(config)
        stub_server_instances.append(s)
        return s

    monkeypatch.setattr("bot.main.uvicorn.Server", _stub_server)

    # Stub dashboard build_app
    monkeypatch.setattr("bot.main.build_dashboard_app", lambda hub_dir: MagicMock())

    # Stub PTB build_app: async-context-manager-compatible mock
    ptb_app = MagicMock()
    ptb_app.__aenter__ = AsyncMock(return_value=ptb_app)
    ptb_app.__aexit__ = AsyncMock(return_value=None)
    ptb_app.start = AsyncMock()
    ptb_app.stop = AsyncMock()
    ptb_app.updater = MagicMock()
    ptb_app.updater.start_polling = AsyncMock()
    ptb_app.updater.stop = AsyncMock()

    def _fake_build_app(token, post_init=None):
        return ptb_app

    monkeypatch.setattr("bot.bridge.telegram.build_app", _fake_build_app)

    # Trigger stop quickly after startup
    async def _trigger_stop(stop_event):
        await asyncio.sleep(0.05)
        stop_event.set()

    original_run = main_mod._run

    async def _patched_run(data_path):
        # monkey into original _run by hooking Event.wait via a task
        # We'll rely on the fact that original _run awaits stop_event.wait().
        # Use signal from stop_event captured via a side-channel:
        # simplest: override stop_event.wait using a short sleep + set.
        return await original_run(data_path)

    # Patch asyncio.Event to auto-set after tasks scheduled
    class _AutoSetEvent(asyncio.Event):
        def __init__(self):
            super().__init__()
            asyncio.get_event_loop().call_later(0.05, self.set)

    monkeypatch.setattr(main_mod.asyncio, "Event", _AutoSetEvent)

    main_mod.main()

    assert stub_server_instances, "uvicorn.Server was never instantiated"
    assert stub_server_instances[0].served, "uvicorn server.serve() was never awaited"
    ptb_app.start.assert_awaited()
    ptb_app.updater.start_polling.assert_awaited()
