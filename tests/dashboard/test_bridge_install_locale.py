"""Locale persistence through the bridge install endpoint (Phase 260416-lht, Plan 01).

Verifies:
    - POST form-urlencoded with ``locale="ru"`` persists ``config.locale == "ru"``.
    - Missing ``locale`` defaults to ``"en"``.
    - Invalid ``locale`` falls back to ``"en"`` without 4xx.
    - JSON body flow (post-install ``bridge_install_form.html`` with json-enc) accepts locale.
    - ``redact_bridge_config`` preserves ``config.locale`` while stripping the token.
    - GET /modules/telegram-bridge/config page renders the chosen locale label.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest

from bot.modules.registry import get_entry
from bot.modules.telegram_bridge_state import redact_bridge_config
from tests.dashboard._helpers import build_client, make_session_cookie

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_jobs(events_log: Path) -> Iterator[None]:  # noqa: ARG001
    """Clear dashboard.jobs state between tests."""
    try:
        from bot.dashboard import jobs as jobs_mod  # noqa: PLC0415
    except ImportError:
        yield
        return
    jobs_mod._jobs.clear()
    if jobs_mod._lock.locked():
        try:
            jobs_mod._lock.release()
        except RuntimeError:
            pass
    yield
    jobs_mod._jobs.clear()


@pytest.fixture
def auth_client(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
) -> Iterator:
    """TestClient with pre-seeded owner session cookie."""
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        tc.cookies.set("animaya_session", make_session_cookie(owner_id))
        yield tc


def _install_spy():
    """Return a (patcher_cms, captured_config) pair.

    Use as ``with _install_spy() as captured:`` — after the block exits,
    ``captured["config"]`` holds the ``config=`` kwarg seen by start_install.
    """
    captured: dict = {"config": None}

    async def _fake_start_install(name, source_dir, hub_dir, config=None):  # noqa: ARG001
        captured["config"] = config
        # Write a minimal registry entry so the route's subsequent get_entry
        # + write_state don't explode when it looks up module_dir.
        module_dir = hub_dir / "modules" / "telegram-bridge"
        module_dir.mkdir(parents=True, exist_ok=True)
        registry_path = hub_dir / "registry.json"
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            registry = {"modules": []}
        # Replace or append the telegram-bridge entry.
        registry["modules"] = [
            m for m in registry.get("modules", []) if m.get("name") != "telegram-bridge"
        ]
        registry["modules"].append(
            {
                "name": "telegram-bridge",
                "module_dir": str(module_dir),
                "config": config or {},
            }
        )
        registry_path.write_text(json.dumps(registry), encoding="utf-8")
        return SimpleNamespace(status="done", error=None)

    patcher_validate = patch(
        "bot.dashboard.bridge_routes.validate_bot_token",
        new=AsyncMock(return_value=(True, "testbot", None)),
    )
    patcher_install = patch(
        "bot.dashboard.bridge_routes.start_install",
        new=AsyncMock(side_effect=_fake_start_install),
    )
    return patcher_validate, patcher_install, captured


# ── Install persistence ───────────────────────────────────────────────────────


def test_install_persists_locale_ru(auth_client, temp_hub_dir: Path) -> None:
    """POST form with locale=ru → registry config.locale == 'ru'."""
    p_valid, p_install, captured = _install_spy()
    with p_valid, p_install:
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            data={"token": "110201543:valid_token_here", "locale": "ru"},
        )
    assert r.status_code == 200
    assert captured["config"] == {"token": "110201543:valid_token_here", "locale": "ru"}
    entry = get_entry(temp_hub_dir, "telegram-bridge")
    assert entry is not None
    assert entry["config"]["locale"] == "ru"
    assert entry["config"]["token"] == "110201543:valid_token_here"


def test_install_persists_locale_en_default(auth_client, temp_hub_dir: Path) -> None:
    """POST form without locale → defaults to 'en'."""
    p_valid, p_install, captured = _install_spy()
    with p_valid, p_install:
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            data={"token": "110201543:valid_token_here"},
        )
    assert r.status_code == 200
    assert captured["config"]["locale"] == "en"
    entry = get_entry(temp_hub_dir, "telegram-bridge")
    assert entry is not None
    assert entry["config"]["locale"] == "en"


def test_install_rejects_invalid_locale_falls_back_to_en(
    auth_client, temp_hub_dir: Path
) -> None:
    """Invalid locale → silent fallback to 'en' (no 4xx)."""
    p_valid, p_install, captured = _install_spy()
    with p_valid, p_install:
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            data={"token": "110201543:valid_token_here", "locale": "zz"},
        )
    assert r.status_code == 200
    assert captured["config"]["locale"] == "en"
    entry = get_entry(temp_hub_dir, "telegram-bridge")
    assert entry["config"]["locale"] == "en"


def test_install_accepts_json_body_with_locale(
    auth_client, temp_hub_dir: Path
) -> None:
    """JSON body (post-install json-enc flow) carries locale through."""
    p_valid, p_install, captured = _install_spy()
    with p_valid, p_install:
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            json={"token": "110201543:valid_token_here", "locale": "ru"},
        )
    assert r.status_code == 200
    assert captured["config"]["locale"] == "ru"
    entry = get_entry(temp_hub_dir, "telegram-bridge")
    assert entry["config"]["locale"] == "ru"


# ── Redaction ─────────────────────────────────────────────────────────────────


def test_redact_bridge_config_keeps_locale_visible() -> None:
    """redact_bridge_config strips token, preserves locale."""
    entry = {"config": {"token": "secret", "locale": "ru"}}
    out = redact_bridge_config(entry)
    assert out["config"]["locale"] == "ru"
    assert out["config"]["has_token"] is True
    assert "token" not in out["config"]


# ── Config page rendering ─────────────────────────────────────────────────────


def test_bridge_config_page_renders_locale(
    auth_client, temp_hub_dir: Path
) -> None:
    """GET /modules/telegram-bridge/config after a ru install shows 'Русский'."""
    # Seed a ru install end-to-end through the route so the registry entry
    # reflects a real persisted install.
    p_valid, p_install, _captured = _install_spy()
    with p_valid, p_install:
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            data={"token": "110201543:valid_token_here", "locale": "ru"},
        )
    assert r.status_code == 200

    # Provide a manifest so validate_manifest succeeds on the config GET.
    entry = get_entry(temp_hub_dir, "telegram-bridge")
    assert entry is not None
    module_dir = Path(entry["module_dir"])
    manifest = {
        "manifest_version": 1,
        "name": "telegram-bridge",
        "version": "0.1.0",
        "system_prompt_path": "prompt.md",
        "owned_paths": [],
        "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
        "depends": [],
        "config_schema": None,
    }
    (module_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (module_dir / "prompt.md").write_text("Telegram bridge module.\n", encoding="utf-8")

    resp = auth_client.get("/modules/telegram-bridge/config")
    assert resp.status_code == 200
    body = resp.text
    assert "Русский" in body
