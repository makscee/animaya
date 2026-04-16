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
    """Set required env vars (SESSION_SECRET, DASHBOARD_TOKEN) so main() passes its env-gate.
    TELEGRAM_OWNER_ID is no longer required (CLAIM-04: auth moved to state.json)."""
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
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
        # Phase 8 cutover: TELEGRAM_BOT_TOKEN is no longer required (lives in config.json).
        assert "TELEGRAM_BOT_TOKEN" not in REQUIRED_ENV_VARS, (
            "Phase 8: TELEGRAM_BOT_TOKEN is optional — token seeds from config.json"
        )
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
    """Tests for Phase 8 supervisor-driven bridge wiring in main().

    Phase 8 cutover: main.py no longer calls bot.bridge.telegram.build_app directly.
    The bridge is a module started by the Supervisor. These tests verify the
    supervisor-based boot path.
    """

    def test_main_calls_build_app_with_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase 8: main() uses Supervisor to start modules, not direct build_app calls.

        Verify that _run() completes without error (supervisor path) and does NOT
        directly call bot.bridge.telegram.build_app — the bridge adapter does that.
        """
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-bot-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

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
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
            patch("bot.main.Supervisor") as MockSupervisor,
            patch("bot.main.migrate_bridge_rename", return_value=False),
            patch("bot.main.migrate_drop_memory", return_value=False),
        ):
            mock_sup = MockSupervisor.return_value
            mock_sup.start_all = AsyncMock()
            mock_sup.stop_all = AsyncMock()
            main()

        # Supervisor is used instead of direct bridge wiring
        mock_sup.start_all.assert_called_once()

    def test_main_calls_run_polling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase 8: Supervisor.start_all is called (handles polling via module adapter)."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

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
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
            patch("bot.main.Supervisor") as MockSupervisor,
            patch("bot.main.migrate_bridge_rename", return_value=False),
            patch("bot.main.migrate_drop_memory", return_value=False),
        ):
            mock_sup = MockSupervisor.return_value
            mock_sup.start_all = AsyncMock()
            mock_sup.stop_all = AsyncMock()
            main()

        # Phase 8: supervisor.start_all handles module startup (including bridge polling)
        mock_sup.start_all.assert_called_once()

    def test_assemble_claude_md_before_build_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Phase 8: assemble_claude_md must be called before supervisor.start_all."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        _set_phase5_env(monkeypatch)

        call_order: list[str] = []

        original_assemble = assemble_claude_md

        def track_assemble(data_path: Path) -> None:
            call_order.append("assemble_claude_md")
            original_assemble(data_path)

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

        async def _track_start_all(ctx):
            call_order.append("supervisor.start_all")

        with (
            patch("bot.main.assemble_claude_md", side_effect=track_assemble),
            patch("bot.main.uvicorn.Server", _StubServer),
            patch("bot.main.build_dashboard_app", return_value=MagicMock()),
            patch("bot.main.asyncio.Event", _AutoSetEvent),
            patch("bot.main.Supervisor") as MockSupervisor,
            patch("bot.main.migrate_bridge_rename", return_value=False),
            patch("bot.main.migrate_drop_memory", return_value=False),
        ):
            mock_sup = MockSupervisor.return_value
            mock_sup.start_all = _track_start_all
            mock_sup.stop_all = AsyncMock()
            main()

        assert "assemble_claude_md" in call_order
        assert "supervisor.start_all" in call_order
        assert call_order.index("assemble_claude_md") < call_order.index("supervisor.start_all")


# ── CLAIM-04: TELEGRAM_OWNER_ID fully removed from production code ────────────


def test_no_telegram_owner_id_in_deps() -> None:
    """CLAIM-04: TELEGRAM_OWNER_ID env gate fully removed from deps.py."""
    source = Path("bot/dashboard/deps.py").read_text()
    assert "TELEGRAM_OWNER_ID" not in source


def test_no_telegram_owner_id_in_bridge() -> None:
    """CLAIM-04: TELEGRAM_OWNER_ID env gate fully removed from telegram.py."""
    source = Path("bot/bridge/telegram.py").read_text()
    assert "TELEGRAM_OWNER_ID" not in source
