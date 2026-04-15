"""Telegram Login Widget verification + signed session cookies (Phase 5).

Implements CONTEXT D-01 (owner allowlist), D-02 (proxy bind), D-03
(itsdangerous-signed cookie, httpOnly+SameSite=Lax+Secure).

Env:
    TELEGRAM_BOT_TOKEN — used as HMAC secret (sha256 of token bytes).
    SESSION_SECRET     — random 32+ hex chars; stable across restarts.

Security notes:
  * Comparisons use hmac.compare_digest (timing-safe).
  * auth_date freshness window defaults to 24 h per Telegram docs.
  * Session cookies carry {user_id, auth_date, hash} only — no PII.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────
SESSION_COOKIE_NAME: str = "animaya_session"
SESSION_MAX_AGE_SECONDS: int = 30 * 86400  # 30-day sliding TTL (D-03)
AUTH_DATE_FRESHNESS_SECONDS: int = 86400  # 24 h per Telegram docs
_SERIALIZER_SALT: str = "animaya-dashboard"
_CLOCK_SKEW_TOLERANCE_SECONDS: int = 300  # reject payloads from >5 min in the future


# ── Telegram Login Widget verification ───────────────────────────────
def verify_telegram_payload(
    payload: dict[str, str],
    bot_token: str,
    *,
    freshness_seconds: int = AUTH_DATE_FRESHNESS_SECONDS,
    now: int | None = None,
) -> bool:
    """Return True iff payload hash matches and auth_date is fresh.

    Telegram documents the algorithm as:
        data_check_string = "\\n".join(f"{k}={v}" for k,v in sorted(payload_sans_hash))
        secret_key        = sha256(bot_token).digest()
        expected_hash     = HMAC-SHA256(secret_key, data_check_string).hexdigest()

    Args:
        payload: form-data-as-dict received from Telegram Login Widget, including 'hash'.
        bot_token: the same bot token used to receive Telegram updates.
        freshness_seconds: max age of `auth_date` accepted (default 24 h).
        now: optional injected clock (test hook).

    Returns:
        True only if: bot_token is non-empty, `hash` is present, HMAC matches
        (timing-safe), `auth_date` parses, and the payload is neither too old
        nor implausibly far in the future.
    """
    if not bot_token:
        logger.warning("verify_telegram_payload called with empty bot_token")
        return False
    received_hash = payload.get("hash")
    if not received_hash:
        return False

    unhashed = {k: v for k, v in payload.items() if k != "hash"}
    data_check = "\n".join(f"{k}={unhashed[k]}" for k in sorted(unhashed))
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        return False

    try:
        auth_date = int(unhashed.get("auth_date", 0))
    except (TypeError, ValueError):
        return False
    now_ts = now if now is not None else int(time.time())
    delta = now_ts - auth_date
    if delta > freshness_seconds or delta < -_CLOCK_SKEW_TOLERANCE_SECONDS:
        return False
    return True


# ── Session cookie ────────────────────────────────────────────────────
def _serializer() -> URLSafeTimedSerializer:
    """Construct the URLSafeTimedSerializer. Fails closed if SESSION_SECRET is unset."""
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET env var required for dashboard session")
    return URLSafeTimedSerializer(secret, salt=_SERIALIZER_SALT)


def issue_session_cookie(user_id: int, auth_date: int, hash_: str) -> str:
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
        "secure": True,
        "path": "/",
    }


__all__ = [
    "AUTH_DATE_FRESHNESS_SECONDS",
    "SESSION_COOKIE_NAME",
    "SESSION_MAX_AGE_SECONDS",
    "clear_session_cookie_kwargs",
    "issue_session_cookie",
    "read_session_cookie",
    "verify_telegram_payload",
]
