"""POST /internal/notify — voidnet-pushed user notification.

ANI_VDN-2 T14. Substrate-scope notification delivery: voidnet pushes a
templated message at the bot, which renders it through the i18n ``t()``
helper and (in production) hands it to the Telegram dispatcher.

Why a push (rather than a pull):

    Notifications are *triggered* by voidnet-side events (subscription
    suspension, billing receipts, language fan-out follow-ups, etc).
    Voidnet already knows the recipient's stored ``users.language`` at
    trigger time. Including it in the request body lets the bot skip an
    HMAC GET roundtrip and avoids a 60-second cache-staleness window.

Body shape (T14)::

    {
      "user_id":        <int>,        # voidnet user_id, also bound by HMAC headers
      "key":            "<i18n key>", # looked up in bot/i18n/{en,ru}.json
      "vars":           { ... },      # optional, str-keyed; empty dict if absent
      "recipient_lang": "ru" | "en"   # optional; if absent → fall back to get_user_lang
    }

Behaviour:

    - ``recipient_lang`` present and valid → render via ``t(key, recipient_lang, **vars)``
      INLINE (no cache touch, no HMAC GET).
    - ``recipient_lang`` absent or unrecognised → fall back to
      ``get_user_lang(user_id)`` (which uses cache + HMAC GET, with TG
      locale as last-resort).

The substrate goal is wiring + contract — the rendered string is returned
in the response body for now. ANI_VDN-3 will wire the dispatcher that
forwards it to the user's Telegram chat.

Threat model + HMAC scheme: identical to ``lang_bust.py`` (loopback-only
mount, body/header user_id binding, ±60s replay window). The two routes
share the verifier helper through ``bot.engine.lang_bust._verify`` to keep
the verification surface exactly one implementation.

Responses:
    200 — signature valid, message rendered. JSON body
          ``{"lang": "<resolved>", "message": "<rendered text>"}``.
    400 — header/body user_id mismatch.
    401 — timestamp skew >60s, missing/bad signature, missing required
          headers, or VOIDNET_HMAC_SECRET unset.
    404 — feature flag ``i18n_substrate_v1`` is off (D7).
    422 — FastAPI body-shape validation (missing user_id/key, etc.).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel, Field

from bot.config import i18n_enabled
from bot.engine.lang_bust import _verify
from bot.i18n import t
from bot.lang import _SUPPORTED, get_user_lang

log = logging.getLogger(__name__)

router = APIRouter()


class NotifyBody(BaseModel):
    """Request body for ``POST /internal/notify``."""

    user_id: int = Field(..., description="Voidnet user_id targeted by the notification.")
    key: str = Field(..., min_length=1, description="i18n key to render via t().")
    vars: dict[str, Any] = Field(
        default_factory=dict,
        description="Template variables substituted into the rendered string.",
    )
    recipient_lang: Optional[str] = Field(
        default=None,
        description=(
            "Pre-resolved language ('ru' | 'en'). When supplied, the bot uses it "
            "directly and skips both the cache and the HMAC GET. When absent "
            "(older voidnet payloads), the bot falls back to get_user_lang."
        ),
    )


def _resolve_lang(body: NotifyBody) -> str:
    """Decide the render language for this notification.

    1. If ``recipient_lang`` is one of the supported wire values, use it
       directly. No cache touch, no network call (T14 acceptance §3).
    2. Otherwise (absent, ``None``, empty, unrecognised value), fall
       back to ``get_user_lang(user_id)`` (T14 acceptance §4 — backwards
       compatibility with payloads that pre-date this field).
    """
    rl = body.recipient_lang
    if isinstance(rl, str) and rl.lower() in _SUPPORTED:
        return rl.lower()
    return get_user_lang(body.user_id)


@router.post("/notify", status_code=status.HTTP_200_OK)
async def notify(
    body: NotifyBody,
    x_voidnet_user_id: Optional[str] = Header(default=None, alias="x-voidnet-user-id"),
    x_voidnet_handle: Optional[str] = Header(default=None, alias="x-voidnet-handle"),
    x_voidnet_telegram_id: Optional[str] = Header(
        default=None, alias="x-voidnet-telegram-id"
    ),
    x_voidnet_timestamp: Optional[str] = Header(default=None, alias="x-voidnet-timestamp"),
    x_voidnet_signature: Optional[str] = Header(default=None, alias="x-voidnet-signature"),
) -> dict[str, str]:
    """Render a templated notification for ``body.user_id``.

    Returns the resolved language + rendered message. Substrate scope —
    actual TG dispatch lands in ANI_VDN-3.
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

    lang = _resolve_lang(body)
    message = t(body.key, lang, **body.vars)
    log.info(
        "/internal/notify user_id=%s key=%s lang=%s lang_source=%s",
        body.user_id,
        body.key,
        lang,
        "inline" if body.recipient_lang else "fallback",
    )
    return {"lang": lang, "message": message}
