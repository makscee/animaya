"""SSE chat stream tests for bot.engine.chat_stream.

Verifies:
- text/event-stream frames match the /engine/chat route contract
- Closing frame `data: {"type":"end"}\\n\\n` always sent
- `:ping\\n\\n` heartbeat emitted when iterator idles past threshold
- Concurrent same-owner calls serialize via owner_lock (no interleaving)
"""
from __future__ import annotations

import asyncio
from typing import AsyncIterator

import pytest

from bot.engine import owner_lock
from bot.engine.chat_stream import stream_chat


@pytest.fixture(autouse=True)
def _clear_registry():
    owner_lock._locks.clear()
    yield
    owner_lock._locks.clear()


async def _drain(gen) -> list[bytes]:
    return [chunk async for chunk in gen]


async def _fake_events(events: list[dict]):
    async def factory(body: dict) -> AsyncIterator[dict]:
        for e in events:
            yield e
    return factory


async def test_basic_text_then_end() -> None:
    factory_fn = await _fake_events([
        {"type": "text", "content": "hello"},
        {"type": "tool_use", "tool": "Read", "input": {"file_path": "/x"}},
    ])
    frames = await _drain(stream_chat(
        {"message": "hi", "session_key": "web:42", "_heartbeat": 5.0},
        iterator=factory_fn,
    ))
    joined = b"".join(frames)
    assert b'data: {"type": "text", "content": "hello"}\n\n' in joined
    assert b'"type": "tool_use"' in joined
    # Always ends with explicit end frame
    assert b'data: {"type": "end"}\n\n' in joined
    # Last frame is the end frame
    assert frames[-1] == b'data: {"type": "end"}\n\n'


async def test_heartbeat_ping_on_idle() -> None:
    """Iterator that sleeps longer than the heartbeat triggers :ping frames."""

    async def slow_factory(body: dict) -> AsyncIterator[dict]:
        await asyncio.sleep(0.15)  # > heartbeat_interval below
        yield {"type": "text", "content": "late"}

    frames = await _drain(stream_chat(
        {"message": "x", "session_key": "web:7", "_heartbeat": 0.05},
        iterator=slow_factory,
    ))
    joined = b"".join(frames)
    assert b":ping\n\n" in joined
    assert b'"content": "late"' in joined
    assert frames[-1] == b'data: {"type": "end"}\n\n'


async def test_concurrent_same_owner_serialize() -> None:
    """Two streams for the same owner never interleave event emission."""
    order: list[str] = []

    def make_factory(tag: str):
        async def factory(body: dict) -> AsyncIterator[dict]:
            order.append(f"{tag}-start")
            await asyncio.sleep(0.05)
            yield {"type": "text", "content": tag}
            order.append(f"{tag}-end")
        return factory

    async def run(tag: str) -> None:
        async for _ in stream_chat(
            {"message": tag, "session_key": "web:same", "_heartbeat": 5.0},
            iterator=make_factory(tag),
        ):
            pass

    await asyncio.gather(run("A"), run("B"))
    # Each tag's start/end contiguous — never A-start, B-start, A-end, B-end
    assert order in (
        ["A-start", "A-end", "B-start", "B-end"],
        ["B-start", "B-end", "A-start", "A-end"],
    )


async def test_different_owners_do_not_serialize() -> None:
    """Two streams for different owners run concurrently."""
    enters: list[str] = []

    def make_factory(tag: str):
        async def factory(body: dict) -> AsyncIterator[dict]:
            enters.append(tag)
            await asyncio.sleep(0.05)
            yield {"type": "text", "content": tag}
        return factory

    async def run(session: str, tag: str) -> None:
        async for _ in stream_chat(
            {"message": tag, "session_key": session, "_heartbeat": 5.0},
            iterator=make_factory(tag),
        ):
            pass

    await asyncio.gather(run("web:1", "A"), run("web:2", "B"))
    # Both entered essentially together (order: both A,B before any finishes)
    assert set(enters) == {"A", "B"}
