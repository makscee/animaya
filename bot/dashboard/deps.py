"""FastAPI dependencies for the Animaya dashboard (Phase 9, Plan 03).

Central owner-only guard using state.json-backed auth.
Every protected route declares ``user_id: int = Depends(require_owner)``.

Open-bootstrap behaviour (D-9.12):
  - When no owner has claimed (state.json missing or claim_status != "claimed"),
    returns 0 to allow open access for initial setup.
  - When an owner has claimed, validates session cookie against state.json owner_id.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import Cookie, HTTPException, Request

from bot.dashboard.auth import SESSION_COOKIE_NAME, read_session_cookie
from bot.modules.telegram_bridge_state import get_owner_id as _get_owner_id


def require_owner(
    request: Request,
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> int:
    """Return verified owner user_id, or allow open access if no owner claimed.

    When no owner has claimed (state.json missing or claim_status != "claimed"),
    returns 0 to allow open access for initial setup (D-9.12).

    When an owner has claimed, validates session cookie against state.json owner_id.

    Raises:
        HTTPException(302, Location=/login): no cookie, invalid cookie, OR stale
            open-bootstrap cookie (user_id=0) after owner has claimed.
        HTTPException(403): cookie valid with user_id != 0 but does not match
            state.json owner_id (real non-owner).
    """
    hub_dir: Path = request.app.state.hub_dir
    owner_id = _get_owner_id(hub_dir)
    if owner_id is None:
        return 0  # open access -- no owner claimed yet

    if session is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    payload = read_session_cookie(session)
    if payload is None:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    user_id = int(payload["user_id"])
    if user_id == 0:
        # Stale open-bootstrap cookie (minted pre-claim). Not an attacker —
        # legitimate operator whose session predates the owner claim. Send them
        # back through /login to mint a fresh cookie bound to the real owner_id.
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    if user_id != owner_id:
        raise HTTPException(status_code=403, detail="Not the bot owner")
    return user_id


__all__ = ["require_owner"]
