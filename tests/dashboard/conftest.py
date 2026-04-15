"""Shared fixtures for dashboard tests (Phase 5)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pytest


@pytest.fixture
def temp_hub_dir(tmp_path: Path) -> Path:
    """Isolated hub directory with an empty registry.json seeded."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "registry.json").write_text(json.dumps({"modules": []}), encoding="utf-8")
    return hub


@pytest.fixture
def session_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set SESSION_SECRET so itsdangerous-based helpers work (test-only value)."""
    secret = "test-session-secret-do-not-use-in-prod"
    monkeypatch.setenv("SESSION_SECRET", secret)
    return secret


@pytest.fixture
def owner_id(monkeypatch: pytest.MonkeyPatch) -> int:
    """Set TELEGRAM_OWNER_ID to a known test value (test-only)."""
    monkeypatch.setenv("TELEGRAM_OWNER_ID", "111222333")
    return 111222333


@pytest.fixture
def bot_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set TELEGRAM_BOT_TOKEN to a known test value for HMAC verification (test-only)."""
    token = "123456:TEST_BOT_TOKEN"
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", token)
    return token


@pytest.fixture
def events_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ANIMAYA_EVENTS_LOG into tmp_path so tests are isolated."""
    log = tmp_path / "events.log"
    monkeypatch.setenv("ANIMAYA_EVENTS_LOG", str(log))
    return log


@pytest.fixture
def client(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Any]:
    """FastAPI TestClient bound to an app factory configured for the temp hub_dir.

    Skips cleanly with a helpful reason until Plan 03 creates `bot.dashboard.app.build_app`.
    """
    monkeypatch.setenv("ANIMAYA_HUB_DIR", str(temp_hub_dir))
    try:
        from bot.dashboard.app import build_app  # noqa: PLC0415
    except ImportError:
        pytest.skip("bot.dashboard.app.build_app not yet implemented (Plan 03)")
    from fastapi.testclient import TestClient  # noqa: PLC0415

    app = build_app(hub_dir=temp_hub_dir)
    with TestClient(app) as tc:
        yield tc
