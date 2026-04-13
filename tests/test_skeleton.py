"""Tests for Phase 1 skeleton bot entry point."""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import patch

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
        # main() blocks forever, so run with timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(main(), timeout=0.5)
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
