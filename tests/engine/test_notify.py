"""Tests for ``POST /internal/notify`` (ANI_VDN-2 T14).

Covers the acceptance grid from the subtask spec:

* ``recipient_lang="ru"`` → renders RU template inline, no HTTP call to voidnet
* ``recipient_lang="en"`` → renders EN template inline, no HTTP call
* ``recipient_lang`` absent → falls back to ``get_user_lang`` (mocked)
* HMAC verifier failures (timestamp skew, bad sig, missing headers) and
  the feature-flag-off branch reuse the verifier from ``lang_bust.py``;
  one happy-path + one each of skew/bad-sig/flag-off keep the wiring
  honest without re-exhaustively replaying T11's test grid.

Tests run against ``bot.engine.http.app`` via FastAPI ``TestClient`` with
the loopback middleware whitelisting ``testclient`` (matches the
``test_lang_bust.py`` pattern).
"""
from __future__ import annotations

import time
from typing import Optional
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bot import lang as bot_lang
from bot.engine import http as engine_http
from bot.lang import canonical_string, sign_canonical

SECRET = "test-secret-please-ignore"
HANDLE = "voidnet-api"


@pytest.fixture(autouse=True)
def _allow_testclient_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANIMAYA_ENGINE_ALLOW_TESTCLIENT", "1")
    monkeypatch.setenv("VOIDNET_HMAC_SECRET", SECRET)
    monkeypatch.delenv("I18N_SUBSTRATE_V1", raising=False)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    bot_lang._CACHE.clear()
    yield
    bot_lang._CACHE.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(engine_http.app)


def _sign(
    *,
    user_id: int,
    handle: str = HANDLE,
    telegram_id: Optional[int] = None,
    timestamp: Optional[int] = None,
    secret: str = SECRET,
) -> dict[str, str]:
    if timestamp is None:
        timestamp = int(time.time())
    canonical = canonical_string(
        user_id=user_id, handle=handle, telegram_id=telegram_id, timestamp=timestamp
    )
    signature = sign_canonical(secret.encode("utf-8"), canonical)
    headers = {
        "x-voidnet-user-id": str(user_id),
        "x-voidnet-handle": handle,
        "x-voidnet-timestamp": str(timestamp),
        "x-voidnet-signature": signature,
    }
    if telegram_id is not None:
        headers["x-voidnet-telegram-id"] = str(telegram_id)
    return headers


# ── Inline lang resolution (T14 acceptance §3) ──────────────────────


def test_recipient_lang_ru_renders_inline_no_http_call(client: TestClient) -> None:
    """recipient_lang="ru" must render via t() in RU and bypass get_user_lang
    entirely (no cache touch, no HMAC GET to voidnet)."""
    user_id = 4242
    headers = _sign(user_id=user_id)

    # Patch get_user_lang to blow up if called — proves the inline path
    # never falls back to the cache/HTTP code path.
    with patch("bot.engine.notify.get_user_lang") as mock_gul:
        mock_gul.side_effect = AssertionError(
            "recipient_lang inline path must NOT call get_user_lang"
        )
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "notify.suspended",
                "vars": {"slug": "vpn", "reason": "недостаточно средств"},
                "recipient_lang": "ru",
            },
            headers=headers,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "ru"
    assert body["message"] == "Сервис vpn приостановлен: недостаточно средств. Пополните счёт, чтобы возобновить."
    # Cache must remain untouched — the inline path does not seed it.
    assert bot_lang._cache_get(user_id) is None


def test_recipient_lang_en_renders_inline(client: TestClient) -> None:
    user_id = 1
    headers = _sign(user_id=user_id)

    with patch("bot.engine.notify.get_user_lang") as mock_gul:
        mock_gul.side_effect = AssertionError("inline path must skip get_user_lang")
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "notify.suspended",
                "vars": {"slug": "vpn", "reason": "low credits"},
                "recipient_lang": "en",
            },
            headers=headers,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "en"
    assert body["message"] == "Service vpn suspended: low credits. Top up to reactivate."


def test_recipient_lang_uppercase_normalized(client: TestClient) -> None:
    """Voidnet may send 'RU'/'EN' through accidental upper-casing in some
    serialisers — accept and lowercase rather than fall through."""
    user_id = 99
    headers = _sign(user_id=user_id)

    with patch("bot.engine.notify.get_user_lang") as mock_gul:
        mock_gul.side_effect = AssertionError("uppercase should still be inline")
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "start.greeting",
                "vars": {"name": "Maks"},
                "recipient_lang": "RU",
            },
            headers=headers,
        )

    assert r.status_code == 200
    assert r.json()["lang"] == "ru"


# ── Backwards-compat fallback (T14 acceptance §4) ───────────────────


def test_missing_recipient_lang_falls_back_to_get_user_lang(
    client: TestClient,
) -> None:
    """Older voidnet payloads without recipient_lang must still work — the
    handler falls back to get_user_lang(user_id)."""
    user_id = 7
    headers = _sign(user_id=user_id)

    with patch("bot.engine.notify.get_user_lang", return_value="ru") as mock_gul:
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "start.greeting",
                "vars": {"name": "Maks"},
            },
            headers=headers,
        )

    assert r.status_code == 200
    body = r.json()
    assert body["lang"] == "ru"
    assert "Привет, Maks" in body["message"]
    mock_gul.assert_called_once_with(user_id)


def test_unknown_recipient_lang_falls_back_to_get_user_lang(
    client: TestClient,
) -> None:
    """recipient_lang="fr" (or any unsupported value) must fall back rather
    than render in EN by accident — the design is "use the value or use
    the trusted resolver", never split the difference."""
    user_id = 8
    headers = _sign(user_id=user_id)

    with patch("bot.engine.notify.get_user_lang", return_value="en") as mock_gul:
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "start.greeting",
                "vars": {"name": "X"},
                "recipient_lang": "fr",
            },
            headers=headers,
        )

    assert r.status_code == 200
    assert r.json()["lang"] == "en"
    mock_gul.assert_called_once_with(user_id)


def test_null_recipient_lang_falls_back(client: TestClient) -> None:
    user_id = 9
    headers = _sign(user_id=user_id)

    with patch("bot.engine.notify.get_user_lang", return_value="en") as mock_gul:
        r = client.post(
            "/internal/notify",
            json={
                "user_id": user_id,
                "key": "start.greeting",
                "vars": {"name": "Y"},
                "recipient_lang": None,
            },
            headers=headers,
        )

    assert r.status_code == 200
    mock_gul.assert_called_once_with(user_id)


def test_missing_vars_defaults_to_empty(client: TestClient) -> None:
    """vars is optional in the request body — defaults to empty dict."""
    user_id = 10
    headers = _sign(user_id=user_id)

    r = client.post(
        "/internal/notify",
        json={
            "user_id": user_id,
            "key": "notify.suspended",
            "recipient_lang": "en",
        },
        headers=headers,
    )

    assert r.status_code == 200
    # No vars supplied → placeholders survive verbatim (SafeDict behaviour).
    assert r.json()["message"] == "Service {slug} suspended: {reason}. Top up to reactivate."


# ── Verifier wiring (sanity, not exhaustive) ────────────────────────


def test_expired_timestamp_returns_401(client: TestClient) -> None:
    user_id = 100
    stale = int(time.time()) - 300
    headers = _sign(user_id=user_id, timestamp=stale)

    r = client.post(
        "/internal/notify",
        json={
            "user_id": user_id,
            "key": "start.greeting",
            "recipient_lang": "en",
        },
        headers=headers,
    )

    assert r.status_code == 401


def test_bad_signature_returns_401(client: TestClient) -> None:
    user_id = 200
    headers = _sign(user_id=user_id, secret="WRONG")

    r = client.post(
        "/internal/notify",
        json={
            "user_id": user_id,
            "key": "start.greeting",
            "recipient_lang": "en",
        },
        headers=headers,
    )

    assert r.status_code == 401


def test_header_body_user_id_mismatch_returns_400(client: TestClient) -> None:
    headers = _sign(user_id=300)
    r = client.post(
        "/internal/notify",
        json={
            "user_id": 301,
            "key": "start.greeting",
            "recipient_lang": "en",
        },
        headers=headers,
    )
    assert r.status_code == 400


def test_flag_off_returns_404(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("I18N_SUBSTRATE_V1", "0")
    headers = _sign(user_id=400)
    r = client.post(
        "/internal/notify",
        json={
            "user_id": 400,
            "key": "start.greeting",
            "recipient_lang": "en",
        },
        headers=headers,
    )
    assert r.status_code == 404


def test_missing_key_returns_422(client: TestClient) -> None:
    headers = _sign(user_id=1)
    r = client.post(
        "/internal/notify",
        json={"user_id": 1, "recipient_lang": "en"},
        headers=headers,
    )
    assert r.status_code == 422


def test_missing_user_id_returns_422(client: TestClient) -> None:
    headers = _sign(user_id=1)
    r = client.post(
        "/internal/notify",
        json={"key": "start.greeting", "recipient_lang": "en"},
        headers=headers,
    )
    assert r.status_code == 422
