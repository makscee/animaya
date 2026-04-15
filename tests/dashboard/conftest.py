"""Shared fixtures for dashboard tests (Phase 5)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Iterator

import pytest

# Path to shared module fixtures (reused from tests/modules/fixtures/).
_MODULE_FIXTURES_ROOT = Path(__file__).parent.parent / "modules" / "fixtures"


@pytest.fixture
def tmp_hub_dir(tmp_path: Path) -> Path:
    """Tmp Hub directory mirroring tests/modules/conftest.py:tmp_hub_dir."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


@pytest.fixture
def valid_module_dir(tmp_path: Path) -> Path:
    """Copy of the tests/modules/fixtures/valid-module tree."""
    dest = tmp_path / "modules" / "sample"
    shutil.copytree(_MODULE_FIXTURES_ROOT / "valid-module", dest)
    (dest / "install.sh").chmod(0o755)
    (dest / "uninstall.sh").chmod(0o755)
    return dest


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
def dashboard_token(monkeypatch: pytest.MonkeyPatch) -> str:
    """Set DASHBOARD_TOKEN to a known test value."""
    token = "test-dashboard-token-abc123"
    monkeypatch.setenv("DASHBOARD_TOKEN", token)
    return token


@pytest.fixture
def client(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001
    bot_token: str,  # noqa: ARG001
    dashboard_token: str,  # noqa: ARG001
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
    # follow_redirects=False so tests can assert on 302/303 Location headers.
    with TestClient(app, follow_redirects=False) as tc:
        yield tc
