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

    yield AssistantMessage(content=[TextBlock(text="Привет! Чем занимаешься?")])


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
