"""Loopback HTTP smoke tests for bot.engine.http.

Covers:
- GET /engine/modules returns 200 with shape {"modules":[...]}
- Response DTOs carry no `bot_token` / `token` fields (SEC-01)
- POST to an unknown module yields 4xx
- Engine configured for loopback-only (host accessor + middleware assertions)
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bot.engine import http as engine_http


@pytest.fixture()
def tmp_hub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Minimal hub dir with empty registry so all_cards() returns []."""
    hub = tmp_path / "hub"
    hub.mkdir()
    # empty registry so all_cards() sees no installed modules
    (hub / "registry.json").write_text('{"modules": []}', encoding="utf-8")
    monkeypatch.setenv("DATA_PATH", str(hub))
    # modules root: empty dir → no available cards either
    modules_dir = tmp_path / "modules_root"
    modules_dir.mkdir()
    monkeypatch.setenv("ANIMAYA_MODULES_DIR", str(modules_dir))
    # Let the loopback-only middleware permit Starlette's "testclient" source.
    monkeypatch.setenv("ANIMAYA_ENGINE_ALLOW_TESTCLIENT", "1")
    return hub


def test_engine_bound_loopback_only() -> None:
    """`get_host` hardcodes 127.0.0.1 and HTTP module mentions loopback-only."""
    assert engine_http.get_host() == "127.0.0.1"
    src = Path("bot/engine/http.py").read_text(encoding="utf-8")
    assert "127.0.0.1" in src
    assert "loopback only" in src


def test_get_port_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANIMAYA_ENGINE_PORT", raising=False)
    assert engine_http.get_port() == 8091
    monkeypatch.setenv("ANIMAYA_ENGINE_PORT", "9999")
    assert engine_http.get_port() == 9999


def test_list_modules_shape_and_no_bot_token(tmp_hub: Path) -> None:
    client = TestClient(engine_http.app)
    r = client.get("/engine/modules")
    assert r.status_code == 200
    body = r.json()
    assert "modules" in body
    assert isinstance(body["modules"], list)
    # DTO has no secret-bearing fields
    payload = r.text
    assert "bot_token" not in payload
    assert '"token"' not in payload


def test_install_unknown_module_returns_4xx(tmp_hub: Path) -> None:
    client = TestClient(engine_http.app)
    r = client.post("/engine/modules/does-not-exist/install", json={})
    assert 400 <= r.status_code < 500


def test_non_loopback_client_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the test-client env flag, non-loopback clients are rejected."""
    monkeypatch.delenv("ANIMAYA_ENGINE_ALLOW_TESTCLIENT", raising=False)
    client = TestClient(engine_http.app)
    r = client.get("/engine/modules")
    # TestClient's synthetic host "testclient" is NOT loopback → 403.
    assert r.status_code == 403
