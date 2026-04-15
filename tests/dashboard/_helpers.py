"""Shared helpers for dashboard tests (Phase 5 — Plan 03+)."""
from __future__ import annotations

import hashlib
import hmac
import time
from pathlib import Path
from typing import Any


def _signed_payload(
    bot_token: str,
    *,
    id_: int = 111222333,
    auth_date: int | None = None,
    first_name: str = "Test",
    username: str | None = None,
) -> dict[str, str]:
    """Build a valid Telegram Login Widget payload (with correct HMAC hash).

    Mirrors bot.dashboard.auth.verify_telegram_payload's algorithm so tests
    can exercise the /auth/telegram callback without monkeypatching.
    """
    if auth_date is None:
        auth_date = int(time.time())
    fields: dict[str, str] = {
        "id": str(id_),
        "auth_date": str(auth_date),
        "first_name": first_name,
    }
    if username is not None:
        fields["username"] = username
    data_check = "\n".join(f"{k}={fields[k]}" for k in sorted(fields))
    secret = hashlib.sha256(bot_token.encode()).digest()
    digest = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    fields["hash"] = digest
    return fields


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
