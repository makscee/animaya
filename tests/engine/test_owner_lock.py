"""Tests for bot.engine.owner_lock — per-owner asyncio.Lock registry.

Serializes Claude SDK turns for a single owner across Telegram and web
transports (session keys "tg:<id>" / "web:<id>").
"""
from __future__ import annotations

import asyncio

import pytest

from bot.engine import owner_lock


@pytest.fixture(autouse=True)
def _clear_registry():
    owner_lock._locks.clear()
    yield
    owner_lock._locks.clear()


async def test_same_owner_serializes() -> None:
    """Two concurrent acquires on the same owner serialize (second awaits first)."""
    order: list[str] = []

    async def worker(tag: str, hold: float) -> None:
        async with owner_lock.acquire_for_session("tg:owner-1"):
            order.append(f"{tag}-enter")
            await asyncio.sleep(hold)
            order.append(f"{tag}-exit")

    await asyncio.gather(worker("A", 0.05), worker("B", 0.01))
    # A fully completes before B enters (or vice-versa) — never interleaved.
    assert order in (
        ["A-enter", "A-exit", "B-enter", "B-exit"],
        ["B-enter", "B-exit", "A-enter", "A-exit"],
    )


async def test_different_owners_do_not_block() -> None:
    """Different owners never block each other — enters interleave."""
    events: list[str] = []

    async def worker(session: str, hold: float) -> None:
        async with owner_lock.acquire_for_session(session):
            events.append(f"{session}-enter")
            await asyncio.sleep(hold)
            events.append(f"{session}-exit")

    await asyncio.gather(
        worker("tg:owner-1", 0.05),
        worker("tg:owner-2", 0.05),
    )
    # Both entered before either exited.
    enters = [e for e in events if e.endswith("-enter")]
    exits = [e for e in events if e.endswith("-exit")]
    assert events.index(enters[1]) < events.index(exits[0])


async def test_cross_transport_same_owner_serializes() -> None:
    """tg:123 and web:123 share one owner — must serialize."""
    order: list[str] = []

    async def tg_worker() -> None:
        async with owner_lock.acquire_for_session("tg:123"):
            order.append("tg-enter")
            await asyncio.sleep(0.05)
            order.append("tg-exit")

    async def web_worker() -> None:
        async with owner_lock.acquire_for_session("web:123"):
            order.append("web-enter")
            await asyncio.sleep(0.01)
            order.append("web-exit")

    await asyncio.gather(tg_worker(), web_worker())
    # Never interleave; one full pair before the other.
    assert order in (
        ["tg-enter", "tg-exit", "web-enter", "web-exit"],
        ["web-enter", "web-exit", "tg-enter", "tg-exit"],
    )


async def test_lock_released_on_exception() -> None:
    """Context manager releases the lock even when the body raises."""
    with pytest.raises(RuntimeError):
        async with owner_lock.acquire_for_session("tg:boom"):
            raise RuntimeError("boom")
    # Lock must be free now — second acquire completes promptly.
    async with owner_lock.acquire_for_session("tg:boom"):
        pass
    lock = owner_lock._locks["boom"]
    assert not lock.locked()
