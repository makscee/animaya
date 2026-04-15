"""Bridge state helpers: read/write state.json, token validation, redaction (Phase 9).

Provides the data-layer primitives used by the install dialog and owner-claim FSM.
All I/O is against ``module_dir/state.json`` using an atomic tmp+replace pattern.
Token validation calls the Telegram getMe API via httpx (deferred import).
"""
from __future__ import annotations

import json
import logging
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
    Never mutates the input.

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


__all__ = [
    "get_owner_id",
    "read_state",
    "redact_bridge_config",
    "validate_bot_token",
    "write_state",
]
