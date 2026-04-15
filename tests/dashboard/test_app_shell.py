"""App shell tests — build_app factory, static mount, home guard, logout (Plan 05-03)."""
from __future__ import annotations

from pathlib import Path

from bot.dashboard.auth import SESSION_COOKIE_NAME
from tests.dashboard._helpers import make_session_cookie


def test_build_app_returns_fastapi(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001
    bot_token: str,  # noqa: ARG001
) -> None:
    from bot.dashboard.app import build_app  # noqa: PLC0415

    app = build_app(hub_dir=temp_hub_dir)
    assert type(app).__name__ == "FastAPI"


def test_static_css_served(client) -> None:
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/css")
    assert "--accent" in r.text


def test_favicon_served(client) -> None:
    r = client.get("/static/favicon.svg")
    assert r.status_code == 200
    assert r.text.lstrip().startswith("<svg") or r.text.lstrip().startswith("<?xml")


def test_root_without_session_redirects_to_login(client) -> None:
    r = client.get("/")
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/login"


def test_root_with_non_owner_session_403(client) -> None:
    # Sign a cookie for a user that is NOT in TELEGRAM_OWNER_ID.
    cookie = make_session_cookie(user_id=999)
    client.cookies.set(SESSION_COOKIE_NAME, cookie)
    r = client.get("/")
    assert r.status_code == 403


def test_root_with_owner_session_renders_home(client, owner_id: int) -> None:
    cookie = make_session_cookie(user_id=owner_id)
    client.cookies.set(SESSION_COOKIE_NAME, cookie)
    r = client.get("/")
    assert r.status_code == 200
    # Home placeholder should mention "Dashboard" somewhere (nav or H2) and the user id.
    body = r.text
    assert "Dashboard" in body
    assert str(owner_id) in body


def test_logout_clears_cookie_and_redirects(client) -> None:
    r = client.get("/logout")
    assert r.status_code in (302, 303, 307)
    assert r.headers.get("location") == "/login"
    # Set-Cookie header should clear the animaya_session cookie.
    if hasattr(r.headers, "get_list"):
        set_cookie_headers = r.headers.get_list("set-cookie")
    else:
        set_cookie_headers = [r.headers.get("set-cookie", "")]
    joined = ";".join(set_cookie_headers).lower()
    assert SESSION_COOKIE_NAME in joined
