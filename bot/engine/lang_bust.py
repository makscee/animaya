"""POST /internal/lang-bust — voidnet-initiated cache eviction.

ANI_VDN-2 T11. Voidnet POSTs here after a successful PATCH /api/me/language
so the bot's per-user lang cache (``bot/lang.py::_CACHE``) drops the stale
entry and the next bot reply re-fetches the new language.

Threat model
------------
The route is mounted on the loopback-only engine FastAPI app (see
``bot/engine/http.py``), so direct external callers are already rejected by
the loopback middleware. HMAC verification is layered on top so that a
compromised/curious sibling process on the same host still cannot invalidate
arbitrary user cache entries — voidnet must hold ``VOIDNET_HMAC_SECRET``.

HMAC scheme matches the outbound contract used by ``bot/lang.py`` (T10) so
both sides reuse ``canonical_string`` + ``sign_canonical`` from
``bot.lang``:

    canonical = "{user_id}|{handle}|{telegram_id_or_empty}|{timestamp}"
    signature = hex_lower(HMAC-SHA256(VOIDNET_HMAC_SECRET, canonical))

Headers required from voidnet:
    X-Voidnet-User-Id      i64 decimal, must equal body.user_id
    X-Voidnet-Handle       voidnet identity (e.g. "voidnet-api")
    X-Voidnet-Telegram-Id  optional (omit when caller has no TG identity)
    X-Voidnet-Timestamp    unix seconds, replay window ±60s
    X-Voidnet-Signature    64 lowercase hex chars

Body: ``{"user_id": <int>}``.

Responses:
    204 — signature valid, cache popped (whether or not an entry existed).
    400 — missing/invalid body fields, header/body user_id mismatch.
    401 — timestamp skew >60s, missing or bad signature, missing required
          headers.
    404 — feature flag ``i18n_substrate_v1`` is off (D7) — cache untouched.
    422 — FastAPI body-shape validation (non-int user_id, etc.).
"""
from __future__ import annotations

import hmac
import logging
import os
import time
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from bot.config import i18n_enabled
from bot.lang import HMAC_TS_SKEW_SECS, bust_cache, canonical_string, sign_canonical

log = logging.getLogger(__name__)

router = APIRouter()


class LangBustBody(BaseModel):
    """Request body for ``POST /internal/lang-bust``."""

    user_id: int = Field(..., description="Voidnet user_id whose cache to evict.")


def _voidnet_secret() -> bytes:
    return os.environ.get("VOIDNET_HMAC_SECRET", "").encode("utf-8")


def _verify(
    *,
    body_user_id: int,
    header_user_id: Optional[str],
    handle: Optional[str],
    telegram_id: Optional[str],
    timestamp: Optional[str],
    signature: Optional[str],
) -> None:
    """Raise :class:`HTTPException` on any verification failure.

    On success returns ``None``. All failure modes return 401 except for
    the body/header user_id mismatch (400) and missing body (handled by
    FastAPI as 422).
    """
    secret = _voidnet_secret()
    if not secret:
        log.warning("/internal/lang-bust: VOIDNET_HMAC_SECRET unset — refusing")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="server not configured")

    if not header_user_id or not handle or not timestamp or not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing signing headers")

    # Body/header user_id must match — prevents header-only mutation of the
    # signed identity if the body is forged separately.
    try:
        hdr_uid = int(header_user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad x-voidnet-user-id")
    if hdr_uid != body_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="x-voidnet-user-id does not match body.user_id",
        )

    # Timestamp parse + skew check.
    try:
        ts = int(timestamp)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad x-voidnet-timestamp")
    now = int(time.time())
    if abs(now - ts) > HMAC_TS_SKEW_SECS:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="timestamp skew")

    # Telegram id: empty string in canonical iff header omitted.
    tg_int: Optional[int]
    if telegram_id is None or telegram_id == "":
        tg_int = None
    else:
        try:
            tg_int = int(telegram_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="bad x-voidnet-telegram-id"
            )

    canonical = canonical_string(
        user_id=hdr_uid, handle=handle, telegram_id=tg_int, timestamp=ts
    )
    expected = sign_canonical(secret, canonical)
    if not hmac.compare_digest(expected, signature.lower()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="bad signature")


@router.post("/lang-bust", status_code=status.HTTP_204_NO_CONTENT)
async def lang_bust(
    body: LangBustBody,
    request: Request,
    x_voidnet_user_id: Optional[str] = Header(default=None, alias="x-voidnet-user-id"),
    x_voidnet_handle: Optional[str] = Header(default=None, alias="x-voidnet-handle"),
    x_voidnet_telegram_id: Optional[str] = Header(
        default=None, alias="x-voidnet-telegram-id"
    ),
    x_voidnet_timestamp: Optional[str] = Header(default=None, alias="x-voidnet-timestamp"),
    x_voidnet_signature: Optional[str] = Header(default=None, alias="x-voidnet-signature"),
) -> Response:
    """Drop the cached lang entry for ``body.user_id``.

    Returns 204 on success; 404 when feature flag is off (D7).
    """
    if not i18n_enabled():
        # Flag off — pretend the route does not exist (D7).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")

    _verify(
        body_user_id=body.user_id,
        header_user_id=x_voidnet_user_id,
        handle=x_voidnet_handle,
        telegram_id=x_voidnet_telegram_id,
        timestamp=x_voidnet_timestamp,
        signature=x_voidnet_signature,
    )

    bust_cache(body.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
