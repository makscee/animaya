"""Bridge state helpers: read/write state.json, token validation, redaction (Phase 9).

Provides the data-layer primitives used by the install dialog and owner-claim FSM.
All I/O is against ``module_dir/state.json`` using an atomic tmp+replace pattern.
Token validation calls the Telegram getMe API via httpx (deferred import).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.modules.registry import get_entry

logger = logging.getLogger(__name__)


# ── State I/O ─────────────────────────────────────────────────────────────────


def read_state(module_dir: Path) -> dict:
    """Read state.json from module_dir; return empty dict on missing/corrupt file.

    Args:
        module_dir: Module data directory containing state.json.

    Returns:
        Parsed state dict, or {} if file is absent or cannot be decoded.
    """
    state_path = module_dir / "state.json"
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return {}


def write_state(module_dir: Path, state: dict) -> None:
    """Atomically write state dict to module_dir/state.json.

    Uses tmp+replace pattern to avoid partial-write corruption.

    Args:
        module_dir: Module data directory.
        state: State dict to persist.
    """
    state_path = module_dir / "state.json"
    tmp = state_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(state_path)


# ── Token validation ──────────────────────────────────────────────────────────


async def validate_bot_token(token: str) -> tuple[bool, str | None, str | None]:
    """Validate a Telegram bot token via the getMe API.

    Calls ``https://api.telegram.org/bot{token}/getMe`` with a 10-second timeout.
    Never logs the token value.

    Args:
        token: Bot token string from @BotFather.

    Returns:
        ``(True, username, None)`` on success.
        ``(False, None, error_message)`` on failure or network error.
    """
    import httpx  # deferred import to avoid import-time side effects

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            data = response.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError):
        return (False, None, "Could not reach Telegram API")

    if data.get("ok"):
        username: str | None = data.get("result", {}).get("username")
        return (True, username, None)
    else:
        error = data.get("description", "Invalid token")
        return (False, None, error)


# ── Token redaction ───────────────────────────────────────────────────────────


def redact_bridge_config(entry: dict) -> dict:
    """Return a copy of entry with the bridge token stripped from config.

    Replaces the ``config`` dict's ``token`` key with ``has_token: bool``.
    Non-secret config keys (e.g. ``locale``) are preserved verbatim so the
    config page and other UI can display them. Never mutates the input.

    Args:
        entry: Module registry entry dict (may contain config.token).

    Returns:
        Copy of entry with config.token removed and config.has_token added.
    """
    entry = dict(entry)
    config: dict = dict(entry.get("config") or {})
    has_token = bool(config.get("token"))
    config.pop("token", None)
    config["has_token"] = has_token
    entry["config"] = config
    return entry


# ── Owner ID lookup ───────────────────────────────────────────────────────────


def get_owner_id(hub_dir: Path) -> int | None:
    """Return the claimed owner's Telegram user ID, or None if not claimed.

    Reads the telegram-bridge module's state.json. Returns owner_id only when
    ``claim_status == "claimed"``.

    Args:
        hub_dir: Hub data directory (contains registry.json).

    Returns:
        Integer owner_id if bridge is claimed, else None.
    """
    entry = get_entry(hub_dir, "telegram-bridge")
    if entry is None:
        return None
    module_dir = Path(entry["module_dir"])
    state = read_state(module_dir)
    if state.get("claim_status") == "claimed":
        return state.get("owner_id")
    return None


# ── Locale lookup ────────────────────────────────────────────────────────────


def _get_bridge_locale(hub_dir: Path) -> str:
    """Return the telegram-bridge module's locale, defaulting to ``'en'``.

    Reads ``config.locale`` from the registry entry. Never raises — missing
    entry, missing config, or an unknown locale all fall back to ``'en'``.
    Kept together with other state-layer helpers since the registry read
    pattern mirrors :func:`get_owner_id`.

    Args:
        hub_dir: Hub data directory (contains registry.json).

    Returns:
        The persisted locale (``'en'`` or ``'ru'``). Always one of the known
        values — never an arbitrary string from the registry.
    """
    entry = get_entry(hub_dir, "telegram-bridge")
    if not entry:
        return "en"
    cfg = entry.get("config") or {}
    loc = cfg.get("locale", "en")
    return loc if loc in {"en", "ru"} else "en"


# ── Pairing code FSM ─────────────────────────────────────────────────────────


def generate_pairing_code(module_dir: Path) -> tuple[int, dict]:
    """Generate a 6-digit pairing code, store HMAC hash in state.json, return plaintext.

    The plaintext code is returned once for display and is NEVER written to disk.
    Only the HMAC-SHA256 digest (keyed by SESSION_SECRET + per-code salt) is persisted.

    Args:
        module_dir: Module data directory where state.json is written.

    Returns:
        ``(code, state)`` where ``code`` is the plaintext integer (100000–999999)
        and ``state`` is the written state dict (no plaintext code inside).
    """
    code = secrets.SystemRandom().randint(100000, 999999)
    salt = secrets.token_hex(16)
    key = os.environ.get("SESSION_SECRET", "").encode()
    digest = hmac.new(key, (salt + str(code)).encode(), hashlib.sha256).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    state = {
        "claim_status": "pending",
        "owner_id": None,
        "pairing_code_hash": digest,
        "pairing_code_salt": salt,
        "pairing_code_expires": expires,
        "pairing_attempts": 0,
    }
    write_state(module_dir, state)
    return code, state


def verify_pairing_code(candidate: str, state: dict) -> bool:
    """Verify a candidate 6-digit string against the stored HMAC hash.

    Checks TTL expiry and attempt cap before computing the HMAC comparison.
    Uses ``hmac.compare_digest`` to avoid timing attacks.

    Args:
        candidate: The plaintext code string submitted by the user.
        state: Current state dict (read from state.json).

    Returns:
        ``True`` if the code matches and is within TTL + attempt cap, else ``False``.
    """
    # Attempt cap
    if state.get("pairing_attempts", 0) >= 5:
        return False

    # TTL check
    expires_raw = state.get("pairing_code_expires")
    if not expires_raw:
        return False
    try:
        expires = datetime.fromisoformat(expires_raw)
    except ValueError:
        return False
    if datetime.now(timezone.utc) >= expires:
        return False

    # HMAC comparison
    key = os.environ.get("SESSION_SECRET", "").encode()
    salt = state.get("pairing_code_salt", "")
    expected = hmac.new(key, (salt + candidate).encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, state.get("pairing_code_hash", ""))


def check_expiry(state: dict) -> dict:
    """Auto-transition expired pending codes to unclaimed state.

    If the code is in ``pending`` status and the TTL has elapsed, transitions
    ``claim_status`` to ``"unclaimed"`` and clears all pairing fields.
    The caller is responsible for writing the returned state if it changed.

    Args:
        state: Current state dict (may be mutated by this function).

    Returns:
        The (possibly modified) state dict.
    """
    if state.get("claim_status") != "pending":
        return state

    expires_raw = state.get("pairing_code_expires")
    if not expires_raw:
        return state

    try:
        expires = datetime.fromisoformat(expires_raw)
    except ValueError:
        return state

    if datetime.now(timezone.utc) >= expires:
        state["claim_status"] = "unclaimed"
        state["pairing_code_hash"] = None
        state["pairing_code_salt"] = None
        state["pairing_code_expires"] = None
        state["pairing_attempts"] = 0

    return state


__all__ = [
    "_get_bridge_locale",
    "check_expiry",
    "generate_pairing_code",
    "get_owner_id",
    "read_state",
    "redact_bridge_config",
    "validate_bot_token",
    "verify_pairing_code",
    "write_state",
]
