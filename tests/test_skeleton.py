"""Tests for bot entry point — Phase 2: Telegram bridge integration.

Phase 5 (Plan 05-07) extended REQUIRED_ENV_VARS to five entries and
replaced ``app.run_polling()`` with an async ``_run()`` that runs
uvicorn + PTB polling in the same event loop. Regression tests below
set all required vars and patch the async runner.
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.main import DEFAULT_DATA_PATH, REQUIRED_ENV_VARS, assemble_claude_md, main


def _set_phase5_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set the Phase-5 required env vars (SESSION_SECRET,
    TELEGRAM_OWNER_ID, DASHBOARD_TOKEN) so main() passes its env-gate."""
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "12345")
    monkeypatch.setenv("DASHBOARD_TOKEN", "test-dashboard-token")


class TestEnvValidation:
    """Tests for environment variable validation."""

    def test_missing_telegram_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_missing_claude_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_required_vars_tuple(self) -> None:
        assert "TELEGRAM_BOT_TOKEN" in REQUIRED_ENV_VARS
        assert "CLAUDE_CODE_OAUTH_TOKEN" in REQUIRED_ENV_VARS


class TestDataDirectory:
    """Tests for data directory creation."""

    def test_data_dir_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data_dir = tmp_path / "test_data"
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(data_dir))
        _set_phase5_env(monkeypatch)

        async def _noop_run(*a, **kw):
            return None

        with patch("bot.main._run", side_effect=_noop_run):
            main()
        assert data_dir.exists()

    def test_default_data_path_value(self) -> None:
        assert DEFAULT_DATA_PATH.endswith("hub/knowledge/animaya")


class TestClaudeMdAssembler:
    """Tests for CLAUDE.md assembly."""

    def test_claude_md_written(self, tmp_path: Path) -> None:
        assemble_claude_md(tmp_path)
        assert (tmp_path / "CLAUDE.md").exists()

    def test_claude_md_header(self, tmp_path: Path) -> None:
        assemble_claude_md(tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert content.startswith("# Animaya")

    def test_claude_md_module_markers(self, tmp_path: Path) -> None:
        assemble_claude_md(tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "<!-- module-prompts-start -->" in content
        assert "<!-- module-prompts-end -->" in content

    def test_claude_md_no_modules(self, tmp_path: Path) -> None:
        assemble_claude_md(tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert "No modules installed" in content


class TestTelegramBridgeIntegration:
    """Tests for Phase 2 Telegram bridge wiring in main()."""

    def test_main_calls_build_app_with_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() must call build_app with the TELEGRAM_BOT_TOKEN value
        inside its async _run() coroutine."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-bot-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

        mock_tg_app = MagicMock()
        mock_tg_app.__aenter__ = AsyncMock(return_value=mock_tg_app)
        mock_tg_app.__aexit__ = AsyncMock(return_value=None)
        mock_tg_app.start = AsyncMock()
        mock_tg_app.stop = AsyncMock()
        mock_tg_app.updater = MagicMock()
        mock_tg_app.updater.start_polling = AsyncMock()
        mock_tg_app.updater.stop = AsyncMock()

        # Stub uvicorn.Server so serve() returns immediately.
        class _StubServer:
            def __init__(self, config):
                self.config = config
                self.should_exit = False

            async def serve(self):
                return None

        # Trigger stop_event immediately so the awaiter returns.
        import asyncio as _asyncio

        class _AutoSetEvent(_asyncio.Event):
            def __init__(self):
                super().__init__()
                self.set()

        with (
            patch("bot.bridge.telegram.build_app", return_value=mock_tg_app) as mock_build,
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
        ):
            main()

        mock_build.assert_called_once()
        args, kwargs = mock_build.call_args
        assert args == ("my-bot-token",)
        assert set(kwargs.keys()) <= {"post_init"}

    def test_main_calls_run_polling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() must start Telegram polling via app.updater.start_polling()
        (Phase 5 replaced the blocking run_polling with async start/updater)."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

        mock_tg_app = MagicMock()
        mock_tg_app.__aenter__ = AsyncMock(return_value=mock_tg_app)
        mock_tg_app.__aexit__ = AsyncMock(return_value=None)
        mock_tg_app.start = AsyncMock()
        mock_tg_app.stop = AsyncMock()
        mock_tg_app.updater = MagicMock()
        mock_tg_app.updater.start_polling = AsyncMock()
        mock_tg_app.updater.stop = AsyncMock()

        class _StubServer:
            def __init__(self, config):
                self.config = config
                self.should_exit = False

            async def serve(self):
                return None

        import asyncio as _asyncio

        class _AutoSetEvent(_asyncio.Event):
            def __init__(self):
                super().__init__()
                self.set()

        with (
            patch("bot.bridge.telegram.build_app", return_value=mock_tg_app),
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
        ):
            main()

        mock_tg_app.start.assert_awaited_once()
        mock_tg_app.updater.start_polling.assert_awaited_once()

    def test_assemble_claude_md_before_build_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """assemble_claude_md must be called before build_app."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

        call_order: list[str] = []

        original_assemble = assemble_claude_md

        def track_assemble(data_path: Path) -> None:
            call_order.append("assemble_claude_md")
            original_assemble(data_path)

        mock_tg_app = MagicMock()
        mock_tg_app.__aenter__ = AsyncMock(return_value=mock_tg_app)
        mock_tg_app.__aexit__ = AsyncMock(return_value=None)
        mock_tg_app.start = AsyncMock()
        mock_tg_app.stop = AsyncMock()
        mock_tg_app.updater = MagicMock()
        mock_tg_app.updater.start_polling = AsyncMock()
        mock_tg_app.updater.stop = AsyncMock()

        def track_build_app(token: str, **kwargs):
            call_order.append("build_app")
            return mock_tg_app

        class _StubServer:
            def __init__(self, config):
                self.config = config
                self.should_exit = False

            async def serve(self):
                return None

        import asyncio as _asyncio

        class _AutoSetEvent(_asyncio.Event):
            def __init__(self):
                super().__init__()
                self.set()

        with (
            patch("bot.main.assemble_claude_md", side_effect=track_assemble),
            patch("bot.bridge.telegram.build_app", side_effect=track_build_app),
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
        ):
            main()

        assert call_order.index("assemble_claude_md") < call_order.index("build_app")
