"""Tests for event emitters wired at bridge / lifecycle / assembler call sites.

Plan 05-07, Task 1 (RED). Verifies that the three natural call sites emit
JSONL records to bot.events.log when exercised.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest


def _read_events(log_path: Path) -> list[dict]:
    if not log_path.is_file():
        return []
    out: list[dict] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


# ── Assembler emitter ────────────────────────────────────────────────


def test_assembler_emits_on_rebuild(tmp_path: Path, events_log: Path) -> None:
    """assemble_claude_md should emit an info event with source=assembler."""
    import json as _json

    from bot.modules.assembler import assemble_claude_md

    hub = tmp_path / "hub"
    hub.mkdir()
    (hub / "registry.json").write_text(_json.dumps({"modules": []}), encoding="utf-8")

    assemble_claude_md(hub)

    records = _read_events(events_log)
    matches = [r for r in records if r.get("source") == "assembler"]
    assert matches, f"no assembler events in log: {records}"
    assert matches[-1]["level"] == "info"
    assert "CLAUDE.md rebuilt" in matches[-1]["message"]


# ── Lifecycle emitters ───────────────────────────────────────────────


def test_lifecycle_install_emits_success(
    valid_module_dir: Path, tmp_hub_dir: Path, events_log: Path
) -> None:
    """install() on success emits info event with source=modules.install."""
    from bot.modules import lifecycle

    lifecycle.install(valid_module_dir, tmp_hub_dir)

    records = _read_events(events_log)
    matches = [r for r in records if r.get("source") == "modules.install"]
    assert matches, f"no modules.install events: {records}"
    info = [r for r in matches if r["level"] == "info"]
    assert info, f"no info-level install event: {matches}"
    assert "sample" in info[-1]["message"]


def test_lifecycle_install_emits_failure(
    valid_module_dir: Path, tmp_hub_dir: Path, events_log: Path
) -> None:
    """install() on script failure emits error event with source=modules.install."""
    from bot.modules import lifecycle

    # Break install.sh so it exits 1
    install_sh = valid_module_dir / "install.sh"
    install_sh.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    install_sh.chmod(0o755)

    with pytest.raises(RuntimeError):
        lifecycle.install(valid_module_dir, tmp_hub_dir)

    records = _read_events(events_log)
    errors = [
        r for r in records
        if r.get("source") == "modules.install" and r.get("level") == "error"
    ]
    assert errors, f"no install error events: {records}"


def test_lifecycle_uninstall_emits_success(
    valid_module_dir: Path, tmp_hub_dir: Path, events_log: Path
) -> None:
    """uninstall() on success emits info event with source=modules.uninstall."""
    from bot.modules import lifecycle

    lifecycle.install(valid_module_dir, tmp_hub_dir)

    # Clear events_log so we only look at uninstall emissions
    events_log.write_text("", encoding="utf-8")

    lifecycle.uninstall("sample", tmp_hub_dir, valid_module_dir)

    records = _read_events(events_log)
    matches = [r for r in records if r.get("source") == "modules.uninstall"]
    assert matches, f"no modules.uninstall events: {records}"
    info = [r for r in matches if r["level"] == "info"]
    assert info, f"no info-level uninstall event: {matches}"


# ── Bridge emitters ──────────────────────────────────────────────────


def test_bridge_emits_on_message(events_log: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bridge _handle_message should emit info event with source=bridge when
    a text message comes in (before Claude SDK is invoked)."""
    import asyncio

    from bot.bridge import telegram as bridge_mod

    # Build a fake update + context
    update = MagicMock()
    update.effective_user.id = 42
    update.effective_user.first_name = "Alice"
    update.effective_user.last_name = None
    update.effective_user.username = None
    update.effective_user.language_code = "en"
    update.effective_chat.type = "private"
    update.effective_chat.id = 100
    update.effective_chat.title = None
    update.effective_chat.send_action = AsyncMock()
    update.message.text = "hello"
    update.message.caption = None
    update.message.voice = None
    update.message.audio = None
    update.message.photo = None
    update.message.document = None
    update.message.reply_to_message = None
    update.message.forward_origin = None
    update.message.message_thread_id = None
    update.message.reply_text = AsyncMock(return_value=MagicMock(
        edit_text=AsyncMock(),
        delete=AsyncMock(),
    ))

    ctx = MagicMock()
    ctx.bot.id = 999
    ctx.bot.username = "testbot"
    ctx.bot_data = {}
    ctx.chat_data = {}

    # Stub the Claude SDK query so the handler completes without network
    async def _fake_query(prompt, options):
        from types import SimpleNamespace
        from claude_code_sdk.types import AssistantMessage, TextBlock
        yield AssistantMessage(content=[TextBlock(text="hi back")])

    monkeypatch.setattr("claude_code_sdk.query", _fake_query)
    monkeypatch.setenv("DATA_PATH", str(events_log.parent / "data"))

    asyncio.run(bridge_mod._handle_message(update, ctx))

    records = _read_events(events_log)
    bridge_events = [r for r in records if r.get("source") == "bridge"]
    assert bridge_events, f"no bridge events: {records}"
    # Should have at least "message received"
    messages = [r["message"] for r in bridge_events]
    assert any("received" in m for m in messages), f"no 'received' in: {messages}"


def test_bridge_emits_error_on_handler_exception(
    events_log: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_error_handler emits an error event with source=bridge."""
    import asyncio

    from bot.bridge import telegram as bridge_mod

    ctx = MagicMock()
    ctx.error = RuntimeError("boom: something failed")

    asyncio.run(bridge_mod._error_handler(MagicMock(), ctx))

    records = _read_events(events_log)
    errors = [
        r for r in records
        if r.get("source") == "bridge" and r.get("level") == "error"
    ]
    assert errors, f"no bridge error events: {records}"
    assert "RuntimeError" in errors[-1]["message"] or "boom" in errors[-1]["message"]
