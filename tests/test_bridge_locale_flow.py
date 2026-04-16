"""End-to-end locale plumbing test.

Verifies that the bridge reads the telegram-bridge locale from the registry
(via ``_get_bridge_locale``) and passes it to ``build_options`` at the single
call site in ``_run_claude_and_stream``.

Failure modes covered:
- Missing registry entry → ``en`` default.
- Registry ``locale="ru"`` → ``ru`` forwarded.
- Registry lookup raising → ``en`` fallback (defensive).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _write_registry(data_dir: Path, locale: str | None) -> None:
    """Write a minimal registry.json with a telegram-bridge entry."""
    data_dir.mkdir(parents=True, exist_ok=True)
    entry: dict = {"name": "telegram-bridge", "config": {}}
    if locale is not None:
        entry["config"]["locale"] = locale
    registry = {"modules": [entry]}
    (data_dir / "registry.json").write_text(json.dumps(registry))


async def _empty_async_iter(*args, **kwargs):  # pragma: no cover - trivial
    """Async generator that yields nothing (no Claude output)."""
    if False:
        yield None
    return


async def _call_run_claude(data_dir: Path, session_dir: Path):
    """Invoke ``_run_claude_and_stream`` with minimal stubs and capture build_options call."""
    from bot.bridge import telegram as tg_bridge

    chat = MagicMock()
    chat.id = 42
    chat.send_message = AsyncMock(return_value=MagicMock())
    chat.send_action = AsyncMock()

    context = MagicMock()
    context.bot = MagicMock()

    with (
        patch.dict("os.environ", {"DATA_PATH": str(data_dir)}),
        patch.object(tg_bridge, "query", _empty_async_iter),
        patch("bot.claude_query.build_options") as mock_build,
    ):
        mock_build.return_value = MagicMock()
        await tg_bridge._run_claude_and_stream(
            chat=chat,
            user_id=1,
            context=context,
            envelope="hi",
            system_context="",
            session_dir=session_dir,
        )
        return mock_build


@pytest.mark.asyncio
async def test_locale_ru_flows_from_registry_to_build_options(tmp_path: Path):
    """When registry stores locale=ru, _run_claude_and_stream passes locale='ru'."""
    data_dir = tmp_path / "data"
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)
    _write_registry(data_dir, "ru")

    mock_build = await _call_run_claude(data_dir, session_dir)

    assert mock_build.called, "build_options should have been called"
    _, kwargs = mock_build.call_args
    assert kwargs.get("locale") == "ru"


@pytest.mark.asyncio
async def test_locale_defaults_to_en_when_registry_missing_entry(tmp_path: Path):
    """Without a telegram-bridge registry entry, locale defaults to 'en'."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "registry.json").write_text(json.dumps({"modules": []}))
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)

    mock_build = await _call_run_claude(data_dir, session_dir)

    assert mock_build.called
    _, kwargs = mock_build.call_args
    assert kwargs.get("locale") == "en"


@pytest.mark.asyncio
async def test_locale_defaults_to_en_when_lookup_raises(tmp_path: Path):
    """If _get_bridge_locale raises, the bridge still runs with locale='en'."""
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    session_dir = tmp_path / "session"
    session_dir.mkdir(parents=True)

    from bot.bridge import telegram as tg_bridge

    chat = MagicMock()
    chat.id = 42
    chat.send_message = AsyncMock(return_value=MagicMock())
    chat.send_action = AsyncMock()

    context = MagicMock()
    context.bot = MagicMock()

    with (
        patch.dict("os.environ", {"DATA_PATH": str(data_dir)}),
        patch.object(tg_bridge, "query", _empty_async_iter),
        patch(
            "bot.modules.telegram_bridge_state._get_bridge_locale",
            side_effect=RuntimeError("registry unreadable"),
        ),
        patch("bot.claude_query.build_options") as mock_build,
    ):
        mock_build.return_value = MagicMock()
        await tg_bridge._run_claude_and_stream(
            chat=chat,
            user_id=1,
            context=context,
            envelope="hi",
            system_context="",
            session_dir=session_dir,
        )

    assert mock_build.called
    _, kwargs = mock_build.call_args
    assert kwargs.get("locale") == "en"
