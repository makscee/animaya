"""Dashboard auth — session cookie tests.

Telegram HMAC tests removed: that flow is gone (now token-based login).
Retained: session cookie round-trip, require_owner FastAPI dependency.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


# ── Stub app ──────────────────────────────────────────────────────────
def _stub_app(hub_dir: Path) -> FastAPI:
    """Tiny FastAPI app that exercises require_owner.

    Sets app.state.hub_dir so require_owner can read state.json.
    """
    from bot.dashboard.deps import require_owner

    app = FastAPI()
    app.state.hub_dir = hub_dir

    @app.get("/who")
    def who(uid: int = Depends(require_owner)) -> dict[str, int]:
        return {"user_id": uid}

    return app


# ── Session cookie round-trip ────────────────────────────────────────
def test_issue_and_read_session_round_trip(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111)
    payload = read_session_cookie(token)
    assert payload is not None
    assert payload["user_id"] == 111


def test_issue_session_with_optional_fields(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, auth_date=1700000000, hash_="abcd")
    payload = read_session_cookie(token)
    assert payload is not None
    assert payload["user_id"] == 111
    assert payload["auth_date"] == 1700000000
    assert payload["hash"] == "abcd"


def test_read_session_rejects_tampered(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, 1700000000, "abcd")
    mid = len(token) // 2
    flipped = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]
    assert read_session_cookie(flipped) is None


def test_read_session_rejects_expired(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, 1700000000, "abcd")
    time.sleep(1.01)
    assert read_session_cookie(token, max_age=0) is None


def test_read_session_rejects_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.dashboard.auth import issue_session_cookie

    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        issue_session_cookie(111, 1700000000, "abcd")


def test_set_session_cookie_kwargs_returns_expected_keys(session_secret: str) -> None:
    from bot.dashboard.auth import set_session_cookie_kwargs

    kwargs = set_session_cookie_kwargs()
    assert "max_age" in kwargs
    assert kwargs.get("httponly") is True
    assert kwargs.get("samesite") == "lax"


def test_clear_session_cookie_kwargs_returns_expected_keys(session_secret: str) -> None:
    from bot.dashboard.auth import clear_session_cookie_kwargs, SESSION_COOKIE_NAME

    kwargs = clear_session_cookie_kwargs()
    assert kwargs.get("key") == SESSION_COOKIE_NAME
    assert kwargs.get("httponly") is True
    assert kwargs.get("samesite") == "lax"


# ── require_owner FastAPI dependency ─────────────────────────────────
def test_require_owner_no_cookie_redirects(
    session_secret: str, owner_id: int, temp_hub_dir: Path
) -> None:
    """No cookie + claimed owner → redirect to /login."""
    app = _stub_app(temp_hub_dir)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_require_owner_bad_cookie_redirects(
    session_secret: str, owner_id: int, temp_hub_dir: Path
) -> None:
    """Invalid cookie value + claimed owner → redirect to /login."""
    app = _stub_app(temp_hub_dir)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": "not-a-real-token"})
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_require_owner_valid_non_owner_403(
    session_secret: str, owner_id: int, temp_hub_dir: Path
) -> None:
    """Valid cookie for wrong user_id + claimed owner → 403."""
    from bot.dashboard.auth import issue_session_cookie

    cookie = issue_session_cookie(999, 1700000000, "abcd")  # not owner_id
    app = _stub_app(temp_hub_dir)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": cookie})
    assert r.status_code == 403


def test_require_owner_valid_owner_passes(
    session_secret: str, owner_id: int, temp_hub_dir: Path
) -> None:
    """Valid cookie matching state.json owner_id → 200."""
    from bot.dashboard.auth import issue_session_cookie

    cookie = issue_session_cookie(owner_id, 1700000000, "abcd")
    app = _stub_app(temp_hub_dir)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": cookie})
    assert r.status_code == 200
    assert r.json() == {"user_id": owner_id}


def test_require_owner_open_bootstrap_no_owner(
    session_secret: str, temp_hub_dir: Path
) -> None:
    """No owner claimed (no state.json) → open access returns 0."""
    # temp_hub_dir has empty registry.json by default (no bridge entry)
    app = _stub_app(temp_hub_dir)
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who")
    assert r.status_code == 200
    assert r.json() == {"user_id": 0}
