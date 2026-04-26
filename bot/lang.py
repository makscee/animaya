"""Per-user UI language resolution for the animaya bot.

ANI_VDN-2 T10. Single public entry point :func:`get_user_lang` returns the
preferred UI language (`'en'` or `'ru'`) for a voidnet user_id, with three
sources of truth in priority order:

    1. ``i18n_enabled()`` flag — when off, short-circuit to ``'en'`` and skip
       both the cache and the HTTP call (gives ops a clean kill switch).
    2. 60-second in-memory TTL cache (per ``user_id``).
    3. HMAC-signed ``GET {VOIDNET_BASE_URL}/api/users/:id`` against voidnet-api.
       On 4xx / 5xx / network error, fall back to the Telegram-supplied
       ``language_code`` parsed as BCP-47, then to ``'en'``.

The HMAC scheme is the same one voidnet-api uses for outbound dashboard
proxy requests (see ``crates/voidnet-api/src/proxy/signing.rs`` and the
contract at ``knowledge/integrations/animaya-voidnet.md``):

    canonical = "{user_id}|{handle}|{telegram_id_or_empty}|{timestamp}"
    signature = hex_lower(HMAC-SHA256(VOIDNET_HMAC_SECRET, canonical))

Headers (all required by the verifier in ``crates/voidnet-api/src/api/users.rs``):

    X-Voidnet-User-Id      — i64 decimal
    X-Voidnet-Handle       — ascii-safe handle
    X-Voidnet-Telegram-Id  — OPTIONAL (omitted iff signing identity has no TG id)
    X-Voidnet-Timestamp    — unix seconds, replay window ±60s
    X-Voidnet-Signature    — 64 lowercase hex chars

The bot signs with its own service identity — ``user_id`` is the queried
voidnet user (so the request is self-describing for log correlation),
``handle`` is the constant ``BOT_HANDLE``, and ``telegram_id`` is omitted.
This matches what ``verify_headers`` accepts (telegram_id is ``Option<i64>``).
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Optional

import httpx

from bot.config import i18n_enabled

__all__ = [
    "BOT_HANDLE",
    "HMAC_TS_SKEW_SECS",
    "TTL_SECS",
    "bust_cache",
    "canonical_string",
    "from_bcp47",
    "get_user_lang",
    "sign_canonical",
]

log = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────

#: Bot's outbound HMAC handle. Must match the voidnet handle regex
#: ``^[a-z][a-z0-9-]+$`` (validated in voidnet's verify_headers via parsing,
#: not regex — but this keeps us conservative).
BOT_HANDLE: str = "animaya-bot"

#: Replay window in seconds — must equal the verifier's window
#: (``HMAC_TS_SKEW_SECS`` in ``crates/voidnet-api/src/api/users.rs``).
HMAC_TS_SKEW_SECS: int = 60

#: In-memory cache TTL — D2 of the design spec.
TTL_SECS: int = 60

#: Languages the substrate supports. Anything else collapses to ``'en'``.
_SUPPORTED: frozenset[str] = frozenset({"en", "ru"})
_FALLBACK: str = "en"

#: ``user_id -> (language, fetched_at_unix_seconds)``.
_CACHE: dict[int, tuple[str, float]] = {}


# ── BCP-47 parsing (mirrors voidnet_common::i18n::from_bcp47) ────────


def from_bcp47(s: object) -> str:
    """Parse a BCP-47 tag's primary subtag and map to ``'en'`` or ``'ru'``.

    Lowercase, split on ``-``, take the first segment. Anything other than
    ``ru`` (incl. ``None``, empty string, whitespace, unknown subtag) →
    ``'en'``.

    Examples::

        from_bcp47("ru-RU")  -> "ru"
        from_bcp47("en-GB")  -> "en"
        from_bcp47("pt-br")  -> "en"
        from_bcp47(None)     -> "en"
    """
    if s is None:
        return _FALLBACK
    if not isinstance(s, str):
        s = str(s)
    s = s.strip().lower()
    if not s:
        return _FALLBACK
    primary = s.split("-", 1)[0]
    return primary if primary in _SUPPORTED else _FALLBACK


# ── HMAC signing (mirrors voidnet's signing.rs) ──────────────────────


def canonical_string(
    *, user_id: int, handle: str, telegram_id: Optional[int], timestamp: int
) -> str:
    """Build the canonical signing string.

    Format: ``"{user_id}|{handle}|{telegram_id_or_empty}|{timestamp}"``.
    When ``telegram_id`` is ``None`` the field is empty but the delimiters
    remain — same convention as ``proxy::signing::canonical`` on the Rust
    side.
    """
    tg = "" if telegram_id is None else str(telegram_id)
    return f"{user_id}|{handle}|{tg}|{timestamp}"


def sign_canonical(secret: bytes, canonical: str) -> str:
    """``hex_lower(HMAC-SHA256(secret, canonical))`` — 64 hex chars."""
    return hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


# ── HTTP client seam (overridable in tests) ──────────────────────────


def _build_client() -> httpx.Client:
    """Return a fresh httpx Client. Tests monkeypatch this to inject a
    ``MockTransport``; production uses default network transport with a
    short connect/read timeout so a slow voidnet doesn't stall a TG reply.
    """
    return httpx.Client(timeout=httpx.Timeout(5.0, connect=2.0))


def _voidnet_base_url() -> str:
    return os.environ.get("VOIDNET_BASE_URL", "").rstrip("/")


def _voidnet_secret() -> bytes:
    return os.environ.get("VOIDNET_HMAC_SECRET", "").encode("utf-8")


# ── Cache helpers ────────────────────────────────────────────────────


def _cache_get(user_id: int) -> Optional[str]:
    entry = _CACHE.get(user_id)
    if entry is None:
        return None
    lang, fetched_at = entry
    if (time.time() - fetched_at) > TTL_SECS:
        # Don't bother evicting — overwrite on next set.
        return None
    return lang


def _cache_set(user_id: int, lang: str) -> None:
    _CACHE[user_id] = (lang, time.time())


def bust_cache(user_id: int) -> bool:
    """Drop the cached language entry for ``user_id``.

    Called by the inbound ``POST /internal/lang-bust`` route (T11) after the
    voidnet portal records a settings change. Returns ``True`` if an entry
    was present, ``False`` otherwise (idempotent — safe to call repeatedly).
    """
    return _CACHE.pop(user_id, None) is not None


# ── HMAC GET ─────────────────────────────────────────────────────────


def _fetch_lang(user_id: int) -> Optional[str]:
    """One signed GET. Returns ``'en'`` / ``'ru'`` on success, ``None`` on
    any failure (caller falls back to TG locale)."""
    base = _voidnet_base_url()
    secret = _voidnet_secret()
    if not base or not secret:
        log.warning("get_user_lang: VOIDNET_BASE_URL or VOIDNET_HMAC_SECRET unset")
        return None

    timestamp = int(time.time())
    canonical = canonical_string(
        user_id=user_id, handle=BOT_HANDLE, telegram_id=None, timestamp=timestamp
    )
    signature = sign_canonical(secret, canonical)
    headers = {
        "x-voidnet-user-id": str(user_id),
        "x-voidnet-handle": BOT_HANDLE,
        # x-voidnet-telegram-id intentionally omitted — verifier accepts it
        # missing as long as the canonical string matches.
        "x-voidnet-timestamp": str(timestamp),
        "x-voidnet-signature": signature,
    }
    url = f"{base}/api/users/{user_id}"

    try:
        with _build_client() as client:
            resp = client.get(url, headers=headers)
    except httpx.HTTPError as exc:
        log.warning("get_user_lang: voidnet GET %s failed: %s", url, exc)
        return None

    if resp.status_code != 200:
        log.info(
            "get_user_lang: voidnet GET %s -> %s (falling back)", url, resp.status_code
        )
        return None

    try:
        body = resp.json()
    except ValueError:
        log.warning("get_user_lang: voidnet GET %s returned non-JSON body", url)
        return None

    raw = body.get("language") if isinstance(body, dict) else None
    if not isinstance(raw, str):
        return None
    # Normalize via BCP-47 parser so an unexpected value (e.g. 'fr') doesn't
    # propagate to t() and silently miss every key.
    norm = from_bcp47(raw)
    return norm


# ── Public entry point ───────────────────────────────────────────────


def get_user_lang(user_id: int, tg_language_code: Optional[str] = None) -> str:
    """Resolve preferred UI language for ``user_id``.

    Returns ``'en'`` or ``'ru'``. Never raises — falls back to ``'en'`` if
    every signal is missing.

    Resolution order (per design spec D2/D6/D7):
        1. Flag off (:func:`bot.config.i18n_enabled` returns ``False``) →
           ``'en'`` immediately. No HTTP, no cache write.
        2. Cache hit within :data:`TTL_SECS` → cached value.
        3. HMAC GET ``/api/users/:id`` against voidnet → cache + return.
        4. 4xx/5xx/network error → :func:`from_bcp47` of ``tg_language_code``.
    """
    if not i18n_enabled():
        return _FALLBACK

    cached = _cache_get(user_id)
    if cached is not None:
        return cached

    fetched = _fetch_lang(user_id)
    if fetched is not None:
        _cache_set(user_id, fetched)
        return fetched

    # Fallback chain — TG locale, then 'en'. We do NOT cache fallbacks, so
    # a future call gets another shot at voidnet.
    return from_bcp47(tg_language_code)
