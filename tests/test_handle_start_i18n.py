"""Tests for /start handler i18n: t() + get_user_lang resolution.

ANI_VDN-2 T13. Substrate scope per D4: the bot `/start` greeting only.

Acceptance matrix (verbatim from T13):
  - voidnet 200 {"language": "en"} → reply in EN
  - voidnet 200 {"language": "ru"} → reply in RU
  - voidnet 5xx + TG language_code="ru-RU" → RU fallback
  - flag off → EN regardless

We mock voidnet by monkeypatching ``bot.lang._build_client`` (same seam as
``test_lang.py``) so no network is touched and the real
``get_user_lang`` HMAC + cache + fallback chain runs end-to-end.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bot import lang as lang_mod
from bot.bridge import telegram as tg_bridge
from bot.i18n import t


# ── Test scaffolding ─────────────────────────────────────────────────


def _mock_transport(responses: list[httpx.Response]) -> httpx.MockTransport:
    """Return an httpx MockTransport that yields ``responses`` in order."""
    seen = {"n": 0}

    def handler(_request: httpx.Request) -> httpx.Response:
        idx = seen["n"]
        seen["n"] += 1
        if idx >= len(responses):
            return httpx.Response(500, json={"error": "out of mocked responses"})
        return responses[idx]

    return httpx.MockTransport(handler)


def _make_update(*, user_id: int, first_name: str, language_code: str | None):
    """Build an Update mock with .message.reply_text + .effective_user."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    user = MagicMock()
    user.id = user_id
    user.first_name = first_name
    user.username = None
    user.language_code = language_code
    update.effective_user = user
    return update


@pytest.fixture(autouse=True)
def _reset_lang_cache_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Match test_lang.py's fixture: clean cache + known HMAC env + flag on."""
    lang_mod._CACHE.clear()
    monkeypatch.setenv("VOIDNET_HMAC_SECRET", "test-secret")
    monkeypatch.setenv("VOIDNET_BASE_URL", "https://voidnet.test")
    monkeypatch.delenv("I18N_SUBSTRATE_V1", raising=False)
    yield
    lang_mod._CACHE.clear()


# ── Acceptance tests ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_replies_en_when_voidnet_returns_en(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _mock_transport(
        [httpx.Response(200, json={"id": 7, "language": "en"})]
    )
    monkeypatch.setattr(
        lang_mod, "_build_client", lambda: httpx.Client(transport=transport)
    )

    update = _make_update(user_id=7, first_name="Alice", language_code="ru-RU")
    await tg_bridge._handle_start(update, MagicMock())

    update.message.reply_text.assert_awaited_once()
    sent = update.message.reply_text.await_args.args[0]
    assert sent == t("start.greeting", "en", name="Alice")
    assert "Hello, Alice" in sent  # locks copy: voidnet wins over TG locale


@pytest.mark.asyncio
async def test_start_replies_ru_when_voidnet_returns_ru(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _mock_transport(
        [httpx.Response(200, json={"id": 9, "language": "ru"})]
    )
    monkeypatch.setattr(
        lang_mod, "_build_client", lambda: httpx.Client(transport=transport)
    )

    update = _make_update(user_id=9, first_name="Борис", language_code="en-GB")
    await tg_bridge._handle_start(update, MagicMock())

    sent = update.message.reply_text.await_args.args[0]
    assert sent == t("start.greeting", "ru", name="Борис")
    assert "Привет, Борис" in sent


@pytest.mark.asyncio
async def test_start_falls_back_to_tg_ru_on_voidnet_5xx(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transport = _mock_transport([httpx.Response(503, text="upstream down")])
    monkeypatch.setattr(
        lang_mod, "_build_client", lambda: httpx.Client(transport=transport)
    )

    update = _make_update(user_id=42, first_name="Анна", language_code="ru-RU")
    await tg_bridge._handle_start(update, MagicMock())

    sent = update.message.reply_text.await_args.args[0]
    assert sent == t("start.greeting", "ru", name="Анна")
    assert "Привет, Анна" in sent


@pytest.mark.asyncio
async def test_start_replies_en_when_flag_off_regardless_of_tg_locale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("I18N_SUBSTRATE_V1", "0")

    def must_not_call() -> httpx.Client:
        raise AssertionError("HTTP client must not be built when flag is off")

    monkeypatch.setattr(lang_mod, "_build_client", must_not_call)

    update = _make_update(user_id=1, first_name="Bob", language_code="ru-RU")
    await tg_bridge._handle_start(update, MagicMock())

    sent = update.message.reply_text.await_args.args[0]
    assert sent == t("start.greeting", "en", name="Bob")
    assert "Hello, Bob" in sent
