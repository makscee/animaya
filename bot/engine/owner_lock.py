"""Owner-lock registry.

Serializes Claude SDK turns for a single owner across BOTH transport
origins (Telegram bridge and Next.js dashboard). Session keys are
"tg:<id>" or "web:<id>"; the owner id is the suffix after the colon.

Shared singleton registry: importing this module gives you the same
asyncio.Lock instance for any given owner, whether you enter from the
Telegram bridge or from the /engine/chat HTTP route. This is how T-13-32
(interleaved tg + web turns corrupt SDK session) is mitigated.
"""
from __future__ import annotations

import asyncio
import re
from contextlib import asynccontextmanager
from typing import AsyncIterator

_locks: dict[str, asyncio.Lock] = {}

# WR-02 (Phase 13 review): strict session_key validator.
# Only three namespaces are expected to reach the engine:
#   tg:<id>    — Telegram bridge, owner id is the telegram user id
#   web:<id>   — Next.js dashboard, owner id is the session.user.id
#   ops:<tag>  — DASHBOARD_TOKEN ops caller (no owner, its own lock bucket)
# Limiting the id character class to a safe ASCII subset and capping length
# prevents a buggy or malicious caller from growing `_locks` unboundedly
# with garbage keys.
_SESSION_KEY_RE = re.compile(r"^(tg|web|ops):[A-Za-z0-9_\-]{1,64}$")


class InvalidSessionKeyError(ValueError):
    """Raised when session_key does not match the strict format."""


def _owner_of(session_key: str) -> str:
    """Extract owner id from a strict session_key.

    Raises `InvalidSessionKeyError` if the key does not match
    `^(tg|web|ops):[A-Za-z0-9_\\-]{1,64}$`.
    """
    if not isinstance(session_key, str) or not _SESSION_KEY_RE.match(session_key):
        raise InvalidSessionKeyError(f"invalid session_key: {session_key!r}")
    return session_key.split(":", 1)[1]


def _get_lock(owner: str) -> asyncio.Lock:
    """Get-or-create the singleton lock for this owner id."""
    lock = _locks.get(owner)
    if lock is None:
        lock = asyncio.Lock()
        _locks[owner] = lock
    return lock


@asynccontextmanager
async def acquire_for_session(session_key: str) -> AsyncIterator[None]:
    """Acquire the owner lock for a session_key; release on exit or exception.

    Args:
        session_key: "tg:<id>" or "web:<id>" — owner id is derived from suffix.

    Yields:
        None once the lock is held. Releases on normal exit or exception.
    """
    lock = _get_lock(_owner_of(session_key))
    await lock.acquire()
    try:
        yield
    finally:
        lock.release()
