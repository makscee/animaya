"""Login page + Telegram auth callback tests (Plan 05-03)."""
from __future__ import annotations

import time

import pytest

from bot.dashboard.auth import SESSION_COOKIE_NAME
from tests.dashboard._helpers import _signed_payload


@pytest.fixture
def bot_username(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "animaya_test_bot")
    return "animaya_test_bot"


def test_login_page_renders(client, bot_username: str) -> None:
    r = client.get("/login")
    assert r.status_code == 200
    assert "telegram-widget.js" in r.text
    assert "Animaya" in r.text


def test_login_page_uses_bot_username_env(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_USERNAME", "foo_bot")
    r = client.get("/login")
    assert r.status_code == 200
    assert 'data-telegram-login="foo_bot"' in r.text


def test_login_page_missing_bot_username_shows_error(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)
    r = client.get("/login")
    assert r.status_code == 200
    assert "misconfigured" in r.text.lower()


def test_auth_callback_valid_sets_cookie_and_redirects(
    client, bot_token: str, owner_id: int
) -> None:
    payload = _signed_payload(bot_token, id_=owner_id)
    r = client.post("/auth/telegram", data=payload)
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/"
    set_cookie = r.headers.get("set-cookie", "")
    assert SESSION_COOKIE_NAME in set_cookie
    low = set_cookie.lower()
    assert "httponly" in low
    assert "samesite=lax" in low
    assert "secure" in low


def test_auth_callback_invalid_hash_rejected(
    client, bot_token: str, owner_id: int
) -> None:
    payload = _signed_payload(bot_token, id_=owner_id)
    # Mutate id AFTER signing — hash becomes invalid.
    payload["id"] = str(int(payload["id"]) + 1)
    r = client.post("/auth/telegram", data=payload)
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/login?error=invalid"


def test_auth_callback_non_owner_rejected(client, bot_token: str) -> None:
    payload = _signed_payload(bot_token, id_=999888777)
    r = client.post("/auth/telegram", data=payload)
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/login?error=forbidden"


def test_auth_callback_stale_rejected(
    client, bot_token: str, owner_id: int
) -> None:
    stale_auth_date = int(time.time()) - 200_000  # > 24 h
    payload = _signed_payload(bot_token, id_=owner_id, auth_date=stale_auth_date)
    r = client.post("/auth/telegram", data=payload)
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/login?error=stale"
