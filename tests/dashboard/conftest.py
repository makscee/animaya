"""Fixtures for dashboard auth + page tests (Phase 5)."""
from __future__ import annotations

import pytest


@pytest.fixture
def session_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Stable SESSION_SECRET for cookie signing in tests."""
    secret = "0" * 64  # 32 bytes hex
    monkeypatch.setenv("SESSION_SECRET", secret)
    return secret


@pytest.fixture
def bot_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Fake TELEGRAM_BOT_TOKEN for HMAC verification tests."""
    token = "123456:TEST-bot-token-fixture"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    return token


@pytest.fixture
def owner_id(monkeypatch: pytest.MonkeyPatch) -> int:
    """Canonical owner Telegram user_id configured via env."""
    uid = 111222333
    monkeypatch.setenv("TELEGRAM_OWNER_ID", str(uid))
    return uid
