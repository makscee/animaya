"""Unit tests for bot.modules.telegram_bridge_state (Phase 9, Plans 01–02)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.modules.telegram_bridge_state import (
    check_expiry,
    generate_pairing_code,
    read_state,
    redact_bridge_config,
    validate_bot_token,
    verify_pairing_code,
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


# ── Pairing code tests (Plan 02) ──────────────────────────────────────────────


def test_generate_pairing_code_hash_only(tmp_path: Path, monkeypatch) -> None:
    """generate_pairing_code stores HMAC hash only — no plaintext code on disk."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    code, state = generate_pairing_code(tmp_path)

    # Plaintext code returned as int
    assert isinstance(code, int)
    assert 100000 <= code <= 999999

    # state.json on disk must have hash but no plaintext code
    on_disk = read_state(tmp_path)
    assert "pairing_code_hash" in on_disk
    assert isinstance(on_disk["pairing_code_hash"], str)
    assert len(on_disk["pairing_code_hash"]) == 64  # SHA-256 hex digest
    assert on_disk["claim_status"] == "pending"
    # The plaintext code value should not appear as a string in the state dict values
    str_code = str(code)
    for v in on_disk.values():
        if isinstance(v, str):
            assert str_code not in v, "plaintext code found in state.json value"


def test_verify_pairing_code_success(tmp_path: Path, monkeypatch) -> None:
    """verify_pairing_code returns True for the correct plaintext code."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    code, state = generate_pairing_code(tmp_path)
    assert verify_pairing_code(str(code), state) is True


def test_verify_pairing_code_wrong_code(tmp_path: Path, monkeypatch) -> None:
    """verify_pairing_code returns False for an incorrect code."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    _code, state = generate_pairing_code(tmp_path)
    assert verify_pairing_code("000000", state) is False


def test_verify_pairing_code_expired(tmp_path: Path, monkeypatch) -> None:
    """verify_pairing_code returns False when TTL has elapsed."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    code, state = generate_pairing_code(tmp_path)
    # Backdate expiry by 1 minute
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    state["pairing_code_expires"] = past
    assert verify_pairing_code(str(code), state) is False


def test_verify_pairing_code_max_attempts(tmp_path: Path, monkeypatch) -> None:
    """verify_pairing_code returns False when attempt cap (5) is reached."""
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    code, state = generate_pairing_code(tmp_path)
    state["pairing_attempts"] = 5
    assert verify_pairing_code(str(code), state) is False


def test_check_expiry_transitions_to_unclaimed(tmp_path: Path) -> None:
    """check_expiry transitions pending state to unclaimed when TTL elapsed."""
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    state = {
        "claim_status": "pending",
        "pairing_code_hash": "abc123",
        "pairing_code_salt": "saltsalt",
        "pairing_code_expires": past,
        "pairing_attempts": 2,
    }
    result = check_expiry(state)
    assert result["claim_status"] == "unclaimed"
    assert result["pairing_code_hash"] is None
    assert result["pairing_code_salt"] is None
    assert result["pairing_code_expires"] is None
    assert result["pairing_attempts"] == 0


def test_check_expiry_no_change_when_valid(tmp_path: Path) -> None:
    """check_expiry leaves pending state unchanged when TTL has not elapsed."""
    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    state = {
        "claim_status": "pending",
        "pairing_code_hash": "abc123",
        "pairing_code_salt": "saltsalt",
        "pairing_code_expires": future,
        "pairing_attempts": 1,
    }
    result = check_expiry(state)
    assert result["claim_status"] == "pending"
    assert result["pairing_code_hash"] == "abc123"
