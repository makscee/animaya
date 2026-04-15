"""Login flow tests — token-based auth (DASHBOARD_TOKEN).

Telegram Login Widget flow is removed. Tests cover:
- GET /login without token renders login template
- GET /login?token=correct -> 303 to / with session cookie
- GET /login?token=wrong -> 401 with error=invalid
- GET /login when DASHBOARD_TOKEN unset -> 500 with error=misconfigured
- GET /logout clears cookie and redirects to /login
"""
from __future__ import annotations

import pytest

from bot.dashboard.auth import SESSION_COOKIE_NAME


@pytest.fixture
def dashboard_token(monkeypatch: pytest.MonkeyPatch) -> str:
    token = "test-dashboard-token-abc123"
    monkeypatch.setenv("DASHBOARD_TOKEN", token)
    return token


def test_login_page_renders_without_token(client, dashboard_token: str) -> None:
    r = client.get("/login")
    assert r.status_code == 200
    assert "Animaya" in r.text


def test_login_page_no_error_by_default(client, dashboard_token: str) -> None:
    r = client.get("/login")
    assert r.status_code == 200
    # No error message when no token provided
    assert "misconfigured" not in r.text.lower()
    assert "invalid" not in r.text.lower()


def test_login_correct_token_redirects_and_sets_cookie(
    client, dashboard_token: str, owner_id: int
) -> None:
    r = client.get("/login", params={"token": dashboard_token})
    assert r.status_code == 303
    assert r.headers.get("location") == "/"
    set_cookie = r.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in set_cookie
    low = set_cookie.lower()
    assert "httponly" in low
    assert "samesite=lax" in low


def test_login_wrong_token_returns_401(
    client, dashboard_token: str, owner_id: int
) -> None:
    r = client.get("/login", params={"token": "wrong-token"})
    assert r.status_code == 401
    assert "invalid" in r.text.lower()


def test_login_missing_dashboard_token_env_returns_500(
    client, monkeypatch: pytest.MonkeyPatch, owner_id: int
) -> None:
    monkeypatch.delenv("DASHBOARD_TOKEN", raising=False)
    r = client.get("/login", params={"token": "any-token"})
    assert r.status_code == 500
    assert "misconfigured" in r.text.lower()


def test_logout_clears_cookie_and_redirects(client, dashboard_token: str) -> None:
    r = client.get("/logout")
    assert r.status_code == 303
    assert r.headers.get("location") == "/login"
    set_cookie = r.headers.get("set-cookie", "")
    # Cookie should be cleared (max-age=0 or expires in the past)
    assert SESSION_COOKIE_NAME in set_cookie
