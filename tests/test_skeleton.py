"""Tests for bot entry point — Phase 2: Telegram bridge integration."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from bot.main import DEFAULT_DATA_PATH, REQUIRED_ENV_VARS, assemble_claude_md, main


class TestEnvValidation:
    """Tests for environment variable validation."""

    async def test_missing_telegram_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            await main()
        assert exc_info.value.code == 1

    async def test_missing_claude_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.delenv("CLAUDE_CODE_OAUTH_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            await main()
        assert exc_info.value.code == 1

    def test_required_vars_tuple(self) -> None:
        assert "TELEGRAM_BOT_TOKEN" in REQUIRED_ENV_VARS
        assert "CLAUDE_CODE_OAUTH_TOKEN" in REQUIRED_ENV_VARS


class TestDataDirectory:
    """Tests for data directory creation."""

    async def test_data_dir_created(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        data_dir = tmp_path / "test_data"
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(data_dir))
        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()
        with patch("bot.bridge.telegram.build_app", return_value=mock_app):
            await main()
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

    async def test_main_calls_build_app_with_token(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() must call build_app with the TELEGRAM_BOT_TOKEN value."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "my-bot-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()
        with patch("bot.bridge.telegram.build_app", return_value=mock_app) as mock_build:
            await main()
        mock_build.assert_called_once_with("my-bot-token")

    async def test_main_awaits_run_polling(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """main() must await app.run_polling() (not asyncio.Event().wait())."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()
        with patch("bot.bridge.telegram.build_app", return_value=mock_app):
            await main()
        mock_app.run_polling.assert_awaited_once()

    async def test_assemble_claude_md_before_build_app(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """assemble_claude_md must be called before build_app."""
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
        monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "test-oauth")
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        call_order: list[str] = []
        mock_app = MagicMock()
        mock_app.run_polling = AsyncMock()

        original_assemble = __import__("bot.main", fromlist=["assemble_claude_md"]).assemble_claude_md

        def track_assemble(data_path: Path) -> None:
            call_order.append("assemble_claude_md")
            original_assemble(data_path)

        def track_build_app(token: str) -> MagicMock:
            call_order.append("build_app")
            return mock_app

        with (
            patch("bot.main.assemble_claude_md", side_effect=track_assemble),
            patch("bot.bridge.telegram.build_app", side_effect=track_build_app),
        ):
            await main()

        assert call_order.index("assemble_claude_md") < call_order.index("build_app")
