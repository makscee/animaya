"""Async SSE generator for /engine/chat.

Proxies the Claude Code SDK stream as text/event-stream frames matching
the route contract in 13-04-PLAN.md:

    data: {"type":"text","content":"..."}\\n\\n
    data: {"type":"tool_use","tool":"...","input":{...}}\\n\\n
    data: {"type":"tool_result","output":"..."}\\n\\n
    :ping\\n\\n           (every heartbeat_interval seconds on idle)
    data: {"type":"end"}\\n\\n

Turns are serialized per-owner via `bot.engine.owner_lock.acquire_for_session`
so a Telegram turn and a web turn for the same owner never overlap.

The stream iterator lives in `_iter_sdk_events` — pluggable for tests via
`stream_chat(body, iterator=...)`. Production path builds options via
`bot.claude_query.build_options` and calls `claude_code_sdk.query`.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Callable

from bot.engine.owner_lock import acquire_for_session

logger = logging.getLogger(__name__)

# Type for a pluggable event iterator (tests inject a fake).
EventIterator = Callable[[dict], AsyncIterator[dict]]


def _encode(event: dict) -> bytes:
    """SSE-encode a single data event."""
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode()


async def _iter_sdk_events(body: dict) -> AsyncIterator[dict]:
    """Production iterator: call Claude Code SDK and yield typed events.

    Yields dicts of shape:
        {"type":"text","content": str}
        {"type":"tool_use","tool": str,"input": dict}
        {"type":"tool_result","output": str}
    """
    from claude_code_sdk import query
    from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

    from bot.claude_query import build_options

    message = str(body.get("message", ""))
    data_dir = Path(os.environ.get("DATA_PATH", "/data"))
    options = build_options(data_dir=data_dir)

    async for sdk_msg in query(prompt=message, options=options):
        if sdk_msg is None:
            continue
        if isinstance(sdk_msg, AssistantMessage):
            for block in sdk_msg.content:
                if isinstance(block, TextBlock):
                    yield {"type": "text", "content": block.text}
                elif isinstance(block, ToolUseBlock):
                    yield {
                        "type": "tool_use",
                        "tool": block.name,
                        "input": dict(block.input or {}),
                    }


async def stream_chat(
    body: dict,
    *,
    iterator: EventIterator | None = None,
) -> AsyncIterator[bytes]:
    """Top-level SSE generator. Acquires owner-lock, streams events, emits
    heartbeats on idle, and always closes with a final `{"type":"end"}` frame.

    Args:
        body: JSON body dict with keys `message` (str) and `session_key`
            ("tg:<id>" or "web:<id>").
        iterator: optional test hook replacing the production SDK iterator.

    Yields:
        UTF-8 SSE byte frames.
    """
    session_key = str(body.get("session_key", ""))
    heartbeat_interval = float(body.get("_heartbeat", 15.0))
    iter_factory: EventIterator = iterator or _iter_sdk_events

    async with acquire_for_session(session_key):
        events = iter_factory(body).__aiter__()
        next_task: asyncio.Task | None = None
        try:
            while True:
                if next_task is None:
                    next_task = asyncio.create_task(events.__anext__())
                # Race: current pending __anext__ vs heartbeat timeout.
                done, _ = await asyncio.wait(
                    {next_task}, timeout=heartbeat_interval
                )
                if not done:
                    yield b":ping\n\n"
                    continue  # keep same next_task; do NOT restart iterator
                try:
                    event = next_task.result()
                except StopAsyncIteration:
                    next_task = None
                    break
                next_task = None
                yield _encode(event)
        except Exception:  # noqa: BLE001 — surface any error but still close cleanly
            logger.exception("stream_chat iterator error")
        finally:
            if next_task is not None and not next_task.done():
                next_task.cancel()
            yield _encode({"type": "end"})
