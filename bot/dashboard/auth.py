"""Signed session cookies for the dashboard.

Env:
    SESSION_SECRET             — random 32+ hex chars; stable across restarts.
    DASHBOARD_COOKIE_SECURE    — "true"/"false"; default "true". Set "false"
                                  only for tailnet/HTTP testing where Secure
                                  cookies would be dropped by the browser.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
SESSION_COOKIE_NAME: str = "animaya_session"
SESSION_MAX_AGE_SECONDS: int = 30 * 86400  # 30-day sliding TTL
_SERIALIZER_SALT: str = "animaya-dashboard"


def _cookie_secure() -> bool:
    return os.environ.get("DASHBOARD_COOKIE_SECURE", "true").lower() != "false"


# ── Session cookie ────────────────────────────────────────────────────
def _serializer() -> URLSafeTimedSerializer:
    """Construct the URLSafeTimedSerializer. Fails closed if SESSION_SECRET is unset."""
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET env var required for dashboard session")
    return URLSafeTimedSerializer(secret, salt=_SERIALIZER_SALT)


def issue_session_cookie(user_id: int, auth_date: int = 0, hash_: str = "") -> str:
    """Mint a signed session cookie value.

    Raises:
        RuntimeError: if SESSION_SECRET is unset (fail closed).
    """
    payload: dict[str, Any] = {
        "user_id": int(user_id),
        "auth_date": int(auth_date),
        "hash": hash_,
    }
    return _serializer().dumps(payload)


def read_session_cookie(
    token: str | None, max_age: int = SESSION_MAX_AGE_SECONDS
) -> dict | None:
    """Return payload dict or None if token invalid / expired / missing."""
    if not token:
        return None
    try:
        payload = _serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    except RuntimeError:
        # SESSION_SECRET unset at verify time — treat as missing session.
        return None
    if not isinstance(payload, dict) or "user_id" not in payload:
        return None
    return payload


def clear_session_cookie_kwargs() -> dict[str, Any]:
    """Kwargs for response.delete_cookie(...) so routes stay DRY."""
    return {
        "key": SESSION_COOKIE_NAME,
        "httponly": True,
        "samesite": "lax",
        "secure": _cookie_secure(),
        "path": "/",
    }


def set_session_cookie_kwargs() -> dict[str, Any]:
    """Kwargs for response.set_cookie(...) so routes stay DRY."""
    return {
        "max_age": SESSION_MAX_AGE_SECONDS,
        "httponly": True,
        "samesite": "lax",
        "secure": _cookie_secure(),
        "path": "/",
    }


__all__ = [
    "SESSION_COOKIE_NAME",
    "SESSION_MAX_AGE_SECONDS",
    "clear_session_cookie_kwargs",
    "issue_session_cookie",
    "read_session_cookie",
    "set_session_cookie_kwargs",
]
