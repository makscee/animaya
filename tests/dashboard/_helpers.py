"""Shared helpers for dashboard tests (Phase 5 — Plan 03+).

Telegram HMAC helpers (_signed_payload) are kept as stubs that raise
NotImplementedError so any leftover call sites fail loudly.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any


def login_client(client: Any, token: str) -> Any:
    """GET /login?token=<token> and attach the returned session cookie to *client*.

    Returns client with the session cookie set (or without if login failed).
    """
    r = client.get("/login", params={"token": token}, follow_redirects=False)
    set_cookie = r.headers.get("set-cookie", "")
    if "animaya_session=" in set_cookie:
        # Parse the cookie value out of the Set-Cookie header.
        for part in set_cookie.split(";"):
            part = part.strip()
            if part.startswith("animaya_session="):
                cookie_value = part[len("animaya_session="):]
                client.cookies.set("animaya_session", cookie_value)
                break
    return client


def build_client(hub_dir: Path, follow_redirects: bool = False) -> Any:
    """Spin up a TestClient for the dashboard FastAPI app."""
    from bot.dashboard.app import build_app  # noqa: PLC0415
    from fastapi.testclient import TestClient  # noqa: PLC0415

    app = build_app(hub_dir=hub_dir)
    return TestClient(app, follow_redirects=follow_redirects)


def make_session_cookie(user_id: int) -> str:
    """Return a signed animaya_session cookie value for an arbitrary user_id."""
    from bot.dashboard.auth import issue_session_cookie  # noqa: PLC0415

    return issue_session_cookie(
        user_id=user_id,
        auth_date=int(time.time()),
        hash_="test-hash",
    )


def _signed_payload(*args: Any, **kwargs: Any) -> dict[str, str]:
    """Removed: Telegram Login Widget flow is gone.

    This stub exists to produce a clear error if any test still calls it.
    """
    raise NotImplementedError(
        "_signed_payload is removed — Telegram auth flow no longer exists. "
        "Use login_client(client, token) instead."
    )
