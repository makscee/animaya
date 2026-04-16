"""Tests for proactive greeting wiring in bot/bridge/telegram.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import bot.bridge.telegram as tg_bridge
from bot.modules.telegram_bridge_state import read_state, write_state

# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def module_dir(tmp_path):
    (tmp_path / "state.json").write_text(
        '{"claim_status":"claimed","owner_id":42,"greeted":false}'
    )
    return tmp_path


@pytest.fixture
def chat():
    c = MagicMock()
    c.id = 42
    c.type = "private"
    c.title = None
    c.send_message = AsyncMock()
    c.send_action = AsyncMock()
    return c


@pytest.fixture
def user():
    u = MagicMock()
    u.id = 42
    u.first_name = "Alice"
    u.last_name = None
    u.username = "alice"
    u.language_code = "ru"
    return u


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.bot = MagicMock()
    ctx.bot.send_message = AsyncMock()
    ctx.bot_data = {}
    return ctx


# ── Fake query implementations ───────────────────────────────────────


async def _fake_query_success(*, prompt, options):
    from claude_code_sdk.types import AssistantMessage, TextBlock

    yield AssistantMessage(content=[TextBlock(text="Привет! Чем занимаешься?")], model="test")


async def _fake_query_raise(*, prompt, options):
    raise RuntimeError("SDK is sad")
    yield  # pragma: no cover — makes this an async generator


# ── TestProactiveGreeting ────────────────────────────────────────────


class TestProactiveGreeting:
    @pytest.mark.asyncio
    async def test_greets_on_first_claim(
        self, chat, user, context, module_dir, monkeypatch, tmp_path
    ):
        """Successful first claim triggers a greeting and sets greeted=True."""
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        monkeypatch.setattr(tg_bridge, "query", _fake_query_success, raising=False)
        await tg_bridge._claim_proactive_greet(chat, user, context, module_dir)
        assert read_state(module_dir)["greeted"] is True
        # At minimum one send_message call (initial status or fallback)
        assert chat.send_message.called or context.bot.send_message.called

    @pytest.mark.asyncio
    async def test_idempotent(self, chat, user, context, module_dir, monkeypatch, tmp_path):
        """Second invocation with greeted=True is a no-op — no messages sent."""
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        state = read_state(module_dir)
        state["greeted"] = True
        write_state(module_dir, state)
        monkeypatch.setattr(tg_bridge, "query", _fake_query_success, raising=False)
        await tg_bridge._claim_proactive_greet(chat, user, context, module_dir)
        chat.send_message.assert_not_called()
        context.bot.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_on_query_failure(
        self, chat, user, context, module_dir, monkeypatch, tmp_path
    ):
        """When query() raises, bilingual fallback is sent and greeted=True is set."""
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        monkeypatch.setattr(tg_bridge, "query", _fake_query_raise, raising=False)
        await tg_bridge._claim_proactive_greet(chat, user, context, module_dir)
        # fallback sent via context.bot.send_message
        called_args = [call.kwargs for call in context.bot.send_message.call_args_list]
        assert any("Hi / Привет" in (kw.get("text") or "") for kw in called_args)
        assert read_state(module_dir)["greeted"] is True

    @pytest.mark.asyncio
    async def test_no_ownership_claimed_plaintext(
        self, chat, user, context, module_dir, monkeypatch, tmp_path
    ):
        """The greeting path never emits a plaintext 'Ownership claimed.' message."""
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        monkeypatch.setattr(tg_bridge, "query", _fake_query_success, raising=False)
        await tg_bridge._claim_proactive_greet(chat, user, context, module_dir)
        all_calls = list(chat.send_message.call_args_list) + list(
            context.bot.send_message.call_args_list
        )
        for call in all_calls:
            text = call.kwargs.get("text") or (call.args[0] if call.args else "")
            assert "Ownership claimed" not in text

    def test_build_greet_envelope_no_lang(self):
        """Envelope without lang_code omits language hint."""
        env = tg_bridge._build_greet_envelope(None)
        assert "SYSTEM_EVENT: first_boot" in env
        assert "language" not in env.lower() or "your opener" not in env

    def test_build_greet_envelope_with_lang(self):
        """Envelope with non-en lang_code includes language preference hint."""
        env = tg_bridge._build_greet_envelope("ru")
        assert "'ru'" in env
        assert "your opener" in env

    def test_build_greet_envelope_en_no_hint(self):
        """Envelope with lang_code='en' does not add the hint (English is default)."""
        env = tg_bridge._build_greet_envelope("en")
        assert "your opener" not in env

    def test_greet_fallback_constant(self):
        """_GREET_FALLBACK contains the expected bilingual text."""
        assert "Hi / Привет" in tg_bridge._GREET_FALLBACK
        assert "Animaya" in tg_bridge._GREET_FALLBACK


# ── TestStreamBufferReset ────────────────────────────────────────────


def _make_fake_status_msg():
    """Return a minimal fake Telegram message object."""
    msg = MagicMock()
    msg.edit_text = AsyncMock()
    msg.delete = AsyncMock()
    return msg


def _make_fake_chat(status_msg):
    c = MagicMock()
    c.id = 99
    c.type = "private"
    c.title = None
    c.send_message = AsyncMock(return_value=status_msg)
    c.send_action = AsyncMock()
    return c


async def _fake_mixed_stream(*, prompt, options):
    """Text → ToolUse → Text."""
    from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

    yield AssistantMessage(content=[TextBlock(text="A")], model="test")
    yield AssistantMessage(
        content=[ToolUseBlock(id="t1", name="Write", input={"path": "x", "content": "y"})],
        model="test",
    )
    yield AssistantMessage(content=[TextBlock(text="B")], model="test")


async def _fake_trailing_tool_stream(*, prompt, options):
    """Text → ToolUse (no trailing text)."""
    from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

    yield AssistantMessage(content=[TextBlock(text="A")], model="test")
    yield AssistantMessage(
        content=[ToolUseBlock(id="t2", name="Write", input={"path": "x", "content": "y"})],
        model="test",
    )


class TestStreamBufferReset:
    """Verify that accumulated buffer resets after tool uses."""

    def _patch_infra(self, monkeypatch, tmp_path, fake_query):
        """Monkeypatch all infra that _run_claude_and_stream touches."""
        monkeypatch.setenv("DATA_PATH", str(tmp_path))
        monkeypatch.setattr(tg_bridge, "query", fake_query, raising=False)
        monkeypatch.setattr(tg_bridge, "_registry_get_entry", lambda *a, **kw: None, raising=False)
        monkeypatch.setattr(tg_bridge, "_emit_event", lambda *a, **kw: None, raising=False)
        monkeypatch.setattr(tg_bridge, "_send_referenced_files", AsyncMock(), raising=False)

        # Stub build_options and _get_bridge_locale so no real config is needed
        import bot.claude_query as cq
        import bot.modules.telegram_bridge_state as tbs

        monkeypatch.setattr(cq, "build_options", lambda **kw: MagicMock(), raising=False)
        monkeypatch.setattr(tbs, "_get_bridge_locale", lambda d: "en", raising=False)

    def _make_update(self):
        """Return a minimal fake Update with async reply_text."""
        update = MagicMock()
        update.message = MagicMock()
        update.message.text = "hi"
        update.message.caption = None
        update.message.message_id = 1
        update.message.reply_text = AsyncMock(return_value=_make_fake_status_msg())
        return update

    @pytest.mark.asyncio
    async def test_mixed_stream_no_duplication(self, monkeypatch, tmp_path):
        """Post-tool text bubble must contain ONLY the post-tool text, not the concatenation."""
        self._patch_infra(monkeypatch, tmp_path, _fake_mixed_stream)

        status_msg = _make_fake_status_msg()
        chat = _make_fake_chat(status_msg)
        update = self._make_update()
        ctx = MagicMock()
        ctx.chat_data = {}
        ctx.bot = MagicMock()

        result = await tg_bridge._run_claude_and_stream(
            chat,
            42,
            ctx,
            "hi",
            "",
            tmp_path,
            status_msg=status_msg,
            update=update,
        )

        # full_response should be "AB"
        assert result == "AB"

        # Collect all edit_text calls on the original + any new bubbles
        all_edits: list[str] = []
        for call in status_msg.edit_text.call_args_list:
            text_arg = call.args[0] if call.args else call.kwargs.get("text", "")
            all_edits.append(str(text_arg))
        for send_call in chat.send_message.call_args_list:
            nm = send_call.return_value
            if hasattr(nm, "edit_text"):
                for call in nm.edit_text.call_args_list:
                    text_arg = call.args[0] if call.args else call.kwargs.get("text", "")
                    all_edits.append(str(text_arg))

        # Final rendered text must not duplicate the pre-tool "A"
        assert all_edits, "Expected at least one edit_text call"
        last_edit = all_edits[-1]
        assert "AB" not in last_edit, f"Duplication detected in last edit: {last_edit!r}"

    @pytest.mark.asyncio
    async def test_trailing_tool_deletes_status_returns_full(self, monkeypatch, tmp_path):
        """Stream ending with a tool (no trailing text) must delete dangling status_msg
        and return the pre-tool text as full_response."""
        self._patch_infra(monkeypatch, tmp_path, _fake_trailing_tool_stream)

        status_msg = _make_fake_status_msg()
        chat = _make_fake_chat(status_msg)
        update = self._make_update()
        ctx = MagicMock()
        ctx.chat_data = {}
        ctx.bot = MagicMock()

        result = await tg_bridge._run_claude_and_stream(
            chat,
            42,
            ctx,
            "hi",
            "",
            tmp_path,
            status_msg=status_msg,
            update=update,
        )

        # full_response == "A" (pre-tool text)
        assert result == "A"

        # The tool-indicator bubble (new status_msg from _on_tool_use) must be deleted.
        # _on_tool_use creates it via update.message.reply_text; _delete_status then
        # calls .delete() on that message object.
        tool_bubble = update.message.reply_text.return_value
        assert tool_bubble.delete.called, "Expected dangling tool-indicator status_msg to be deleted"
