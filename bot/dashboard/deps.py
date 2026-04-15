"""FastAPI dependencies for the Animaya dashboard (Phase 5).

Central owner-only guard. Every protected route declares
``user_id: int = Depends(require_owner)`` — returns the verified
Telegram user_id or raises 302→/login (unauthenticated) or 403
(authenticated but not in TELEGRAM_OWNER_ID allowlist per D-01).
"""
from __future__ import annotations

import os
from typing import Iterable

from fastapi import Cookie, HTTPException

from bot.dashboard.auth import SESSION_COOKIE_NAME, read_session_cookie


def _owner_ids() -> set[int]:
    """Parse TELEGRAM_OWNER_ID (comma-separated) into a set of ints.

    Empty / unset env → empty set → everyone is denied (fail closed, T-05-02-06).
    """
    raw = os.environ.get("TELEGRAM_OWNER_ID", "")
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            continue
    return out


def require_owner(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> int:
    """Return verified owner user_id or redirect/forbid.

    Raises:
        HTTPException(302, Location=/login): no cookie or invalid cookie.
        HTTPException(403): cookie valid, but user_id not in TELEGRAM_OWNER_ID.
    """
    if session is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    payload = read_session_cookie(session)
    if payload is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    user_id = int(payload["user_id"])
    allowlist: Iterable[int] = _owner_ids()
    if user_id not in allowlist:
        raise HTTPException(status_code=403, detail="not an owner")
    return user_id


__all__ = ["require_owner"]
