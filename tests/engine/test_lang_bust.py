"""Tests for ``POST /internal/lang-bust`` (ANI_VDN-2 T11).

Covers the acceptance grid from the task spec:

* valid request → 204 + cache entry popped
* timestamp skew >60s → 401, cache untouched
* bad signature → 401, cache untouched
* feature flag off → 404, cache untouched
* missing body → 422 (FastAPI body validation)
* missing signing headers → 401
* body/header user_id mismatch → 400

Tests run against ``bot.engine.http.app`` via ``TestClient`` with the
loopback middleware whitelisting ``testclient`` (matches existing
``tests/engine/test_http_smoke.py`` pattern).
"""
from __future__ import annotations

import time
from typing import Optional

import pytest
from fastapi.testclient import TestClient

from bot import lang as bot_lang
from bot.engine import http as engine_http
from bot.lang import canonical_string, sign_canonical

SECRET = "test-secret-please-ignore"
HANDLE = "voidnet-api"


@pytest.fixture(autouse=True)
def _allow_testclient_and_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loopback middleware lets the FastAPI TestClient through; HMAC secret
    is set to a known value so the verifier can re-compute signatures."""
    monkeypatch.setenv("ANIMAYA_ENGINE_ALLOW_TESTCLIENT", "1")
    monkeypatch.setenv("VOIDNET_HMAC_SECRET", SECRET)
    # Default: feature flag ON.
    monkeypatch.delenv("I18N_SUBSTRATE_V1", raising=False)


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    bot_lang._CACHE.clear()
    yield
    bot_lang._CACHE.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(engine_http.app)


def _seed_cache(user_id: int, lang: str = "ru") -> None:
    """Drop a fresh entry into the cache so we can assert it was evicted."""
    bot_lang._cache_set(user_id, lang)
    assert bot_lang._cache_get(user_id) == lang


def _sign(
    *,
    user_id: int,
    handle: str = HANDLE,
    telegram_id: Optional[int] = None,
    timestamp: Optional[int] = None,
    secret: str = SECRET,
) -> dict[str, str]:
    """Build the full header bundle for a valid lang-bust request."""
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


# ── Happy path ──────────────────────────────────────────────────────


def test_valid_bust_returns_204_and_pops_cache(client: TestClient) -> None:
    user_id = 4242
    _seed_cache(user_id, "ru")
    headers = _sign(user_id=user_id)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 204
    # Body MUST be empty for 204 (Starlette enforces).
    assert r.text == ""
    assert bot_lang._cache_get(user_id) is None


def test_valid_bust_when_no_cached_entry_still_204(client: TestClient) -> None:
    """Idempotency: bust against an empty cache is a no-op success."""
    user_id = 7777
    headers = _sign(user_id=user_id)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 204
    assert bot_lang._cache_get(user_id) is None


def test_valid_bust_with_telegram_id_header(client: TestClient) -> None:
    """Verifier must accept requests that include x-voidnet-telegram-id."""
    user_id = 11
    _seed_cache(user_id, "en")
    headers = _sign(user_id=user_id, telegram_id=999_888)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 204
    assert bot_lang._cache_get(user_id) is None


# ── Failure modes ───────────────────────────────────────────────────


def test_expired_timestamp_returns_401_and_keeps_cache(client: TestClient) -> None:
    user_id = 100
    _seed_cache(user_id, "ru")
    # 5 minutes in the past — well outside the ±60s window.
    stale = int(time.time()) - 300
    headers = _sign(user_id=user_id, timestamp=stale)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 401
    assert bot_lang._cache_get(user_id) == "ru"


def test_future_timestamp_outside_skew_returns_401(client: TestClient) -> None:
    user_id = 101
    _seed_cache(user_id, "ru")
    future = int(time.time()) + 300
    headers = _sign(user_id=user_id, timestamp=future)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 401
    assert bot_lang._cache_get(user_id) == "ru"


def test_bad_signature_returns_401_and_keeps_cache(client: TestClient) -> None:
    user_id = 200
    _seed_cache(user_id, "ru")
    headers = _sign(user_id=user_id, secret="WRONG-SECRET")

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 401
    assert bot_lang._cache_get(user_id) == "ru"


def test_missing_signature_header_returns_401(client: TestClient) -> None:
    user_id = 201
    _seed_cache(user_id, "ru")
    headers = _sign(user_id=user_id)
    del headers["x-voidnet-signature"]

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 401
    assert bot_lang._cache_get(user_id) == "ru"


def test_header_body_user_id_mismatch_returns_400(client: TestClient) -> None:
    """Header user_id must match body — guards against a mid-flight body
    swap that would still satisfy a stolen signature."""
    user_id_signed = 300
    _seed_cache(user_id_signed, "ru")
    headers = _sign(user_id=user_id_signed)

    r = client.post(
        "/internal/lang-bust", json={"user_id": user_id_signed + 1}, headers=headers
    )

    assert r.status_code == 400
    assert bot_lang._cache_get(user_id_signed) == "ru"


def test_flag_off_returns_404_and_keeps_cache(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    user_id = 400
    _seed_cache(user_id, "ru")
    monkeypatch.setenv("I18N_SUBSTRATE_V1", "0")
    headers = _sign(user_id=user_id)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 404
    assert bot_lang._cache_get(user_id) == "ru"


def test_missing_body_returns_422(client: TestClient) -> None:
    """FastAPI body validation: empty JSON is missing required ``user_id``."""
    headers = _sign(user_id=1)
    r = client.post("/internal/lang-bust", json={}, headers=headers)
    assert r.status_code == 422


def test_non_int_user_id_returns_422(client: TestClient) -> None:
    headers = _sign(user_id=1)
    r = client.post(
        "/internal/lang-bust", json={"user_id": "not-an-int"}, headers=headers
    )
    assert r.status_code == 422


def test_secret_unset_returns_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Operational guard: with no server secret configured the route refuses
    rather than silently accepting requests."""
    user_id = 500
    _seed_cache(user_id, "ru")
    monkeypatch.delenv("VOIDNET_HMAC_SECRET", raising=False)
    headers = _sign(user_id=user_id)

    r = client.post("/internal/lang-bust", json={"user_id": user_id}, headers=headers)

    assert r.status_code == 401
    assert bot_lang._cache_get(user_id) == "ru"
