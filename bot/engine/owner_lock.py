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
from contextlib import asynccontextmanager
from typing import AsyncIterator

_locks: dict[str, asyncio.Lock] = {}


def _owner_of(session_key: str) -> str:
    """Extract owner id from a session_key of form "tg:<id>" or "web:<id>".

    Returns the raw key if it contains no colon (defensive fallback).
    """
    if ":" in session_key:
        return session_key.split(":", 1)[1]
    return session_key


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
