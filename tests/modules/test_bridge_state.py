"""Unit tests for bot.modules.telegram_bridge_state (Phase 9, Plan 01)."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.modules.telegram_bridge_state import (
    read_state,
    redact_bridge_config,
    validate_bot_token,
    write_state,
)


# ── read_state / write_state ──────────────────────────────────────────────────


def test_read_state_missing_file(tmp_path: Path) -> None:
    """read_state returns {} when state.json does not exist."""
    result = read_state(tmp_path)
    assert result == {}


def test_write_and_read_state(tmp_path: Path) -> None:
    """write_state persists state dict; read_state returns it correctly."""
    state = {"claim_status": "unclaimed", "owner_id": None}
    write_state(tmp_path, state)
    result = read_state(tmp_path)
    assert result == state


def test_read_state_corrupt_file(tmp_path: Path) -> None:
    """read_state returns {} when state.json contains invalid JSON."""
    (tmp_path / "state.json").write_text("{not valid json", encoding="utf-8")
    result = read_state(tmp_path)
    assert result == {}


# ── validate_bot_token ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_validate_bot_token_valid() -> None:
    """validate_bot_token returns (True, username, None) for a valid token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": True, "result": {"username": "test_bot"}}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        ok, username, error = await validate_bot_token("valid_token")

    assert ok is True
    assert username == "test_bot"
    assert error is None


@pytest.mark.asyncio
async def test_validate_bot_token_invalid() -> None:
    """validate_bot_token returns (False, None, description) for invalid token."""
    mock_response = MagicMock()
    mock_response.json.return_value = {"ok": False, "description": "Unauthorized"}

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        ok, username, error = await validate_bot_token("bad_token")

    assert ok is False
    assert username is None
    assert error == "Unauthorized"


@pytest.mark.asyncio
async def test_validate_bot_token_network_error() -> None:
    """validate_bot_token returns (False, None, network msg) on ConnectError."""
    import httpx

    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        ok, username, error = await validate_bot_token("any_token")

    assert ok is False
    assert username is None
    assert error == "Could not reach Telegram API"


# ── redact_bridge_config ──────────────────────────────────────────────────────


def test_redact_bridge_config() -> None:
    """redact_bridge_config strips token and adds has_token=True."""
    entry = {"name": "telegram-bridge", "config": {"token": "secret123"}}
    result = redact_bridge_config(entry)
    assert "token" not in result["config"]
    assert result["config"]["has_token"] is True
    # Original is not mutated
    assert entry["config"]["token"] == "secret123"


def test_redact_bridge_config_no_token() -> None:
    """redact_bridge_config adds has_token=False when no token present."""
    entry = {"name": "telegram-bridge", "config": {}}
    result = redact_bridge_config(entry)
    assert result["config"]["has_token"] is False
    assert "token" not in result["config"]


def test_redact_bridge_config_preserves_other_fields() -> None:
    """redact_bridge_config preserves non-token fields in config and entry."""
    entry = {
        "name": "telegram-bridge",
        "config": {"token": "abc", "extra": "value"},
        "other": "data",
    }
    result = redact_bridge_config(entry)
    assert result["config"]["extra"] == "value"
    assert result["other"] == "data"
    assert "token" not in result["config"]
