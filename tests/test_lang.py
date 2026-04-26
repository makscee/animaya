"""Tests for bot.lang: get_user_lang() + from_bcp47() helper.

Subtask: ANI_VDN-2 T10 (HMAC voidnet GET + 60s TTL cache + TG BCP-47 fallback).

Mirrors voidnet's `voidnet_common::i18n::from_bcp47` matrix and exercises the
HMAC GET path against a mocked httpx transport so we don't hit the network.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from bot import lang as lang_mod
from bot.lang import (
    BOT_HANDLE,
    HMAC_TS_SKEW_SECS,
    canonical_string,
    from_bcp47,
    get_user_lang,
    sign_canonical,
)


# ── BCP-47 matrix (mirrors voidnet) ──────────────────────────────────


@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        ("ru", "ru"),
        ("RU", "ru"),
        ("ru-RU", "ru"),
        ("ru_RU", "en"),  # BCP-47 splits on '-' only; "ru_ru" isn't a known primary subtag
        ("en", "en"),
        ("en-GB", "en"),
        ("EN", "en"),
        ("pt-br", "en"),
        ("zh-Hans", "en"),
        ("fr", "en"),
        ("", "en"),
        (None, "en"),
        ("   ", "en"),
        ("ru-", "ru"),
        ("-ru", "en"),  # empty primary subtag
    ],
)
def test_from_bcp47_matrix(inp: Any, expected: str) -> None:
    assert from_bcp47(inp) == expected


# ── Canonical string + signature parity with voidnet's signing.rs ────


def test_canonical_string_with_telegram_id() -> None:
    s = canonical_string(user_id=42, handle="alice", telegram_id=999, timestamp=1700000000)
    assert s == "42|alice|999|1700000000"


def test_canonical_string_without_telegram_id() -> None:
    s = canonical_string(user_id=42, handle="alice", telegram_id=None, timestamp=1700000000)
    # Field is empty, delimiters remain (per integration doc + signing.rs).
    assert s == "42|alice||1700000000"


def test_sign_canonical_matches_python_hmac_sha256_hex_lower() -> None:
    secret = b"shhh"
    canonical = "42|alice||1700000000"
    expected = hmac.new(secret, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    assert expected == expected.lower()
    assert sign_canonical(secret, canonical) == expected


# ── HMAC GET — 200 happy path (En + Ru) ──────────────────────────────


def _mock_transport(responses: list[httpx.Response]) -> tuple[list[httpx.Request], httpx.MockTransport]:
    """Return a list+transport that records each outgoing request and returns
    `responses[i]` for the i-th call.
    """
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        idx = len(seen) - 1
        if idx >= len(responses):
            return httpx.Response(500, json={"error": "out of mocked responses"})
        return responses[idx]

    return seen, httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def _reset_cache_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets a clean cache + a known HMAC secret + base URL."""
    lang_mod._CACHE.clear()
    monkeypatch.setenv("VOIDNET_HMAC_SECRET", "test-secret")
    monkeypatch.setenv("VOIDNET_BASE_URL", "https://voidnet.test")
    # Default flag on (config.i18n_enabled defaults true; ensure no override).
    monkeypatch.delenv("I18N_SUBSTRATE_V1", raising=False)
    yield
    lang_mod._CACHE.clear()


def test_get_user_lang_200_en(monkeypatch: pytest.MonkeyPatch) -> None:
    seen, transport = _mock_transport(
        [httpx.Response(200, json={"id": 7, "language": "en"})]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))

    result = get_user_lang(7, tg_language_code="ru")  # cache miss, server wins over TG
    assert result == "en"
    assert len(seen) == 1
    req = seen[0]
    assert req.url.path == "/api/users/7"
    # All five headers present
    for hdr in (
        "x-voidnet-user-id",
        "x-voidnet-handle",
        "x-voidnet-timestamp",
        "x-voidnet-signature",
    ):
        assert hdr in req.headers
    assert req.headers["x-voidnet-handle"] == BOT_HANDLE
    assert req.headers["x-voidnet-user-id"] == "7"


def test_get_user_lang_200_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    _, transport = _mock_transport(
        [httpx.Response(200, json={"id": 9, "language": "ru"})]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(9) == "ru"


def test_get_user_lang_signature_matches_canonical(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outbound signature must equal hmac_sha256(secret, canonical(user_id|bot|<empty>|ts))."""
    seen, transport = _mock_transport(
        [httpx.Response(200, json={"id": 5, "language": "ru"})]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(5) == "ru"
    req = seen[0]
    ts = int(req.headers["x-voidnet-timestamp"])
    canonical = canonical_string(user_id=5, handle=BOT_HANDLE, telegram_id=None, timestamp=ts)
    expected_sig = sign_canonical(b"test-secret", canonical)
    assert req.headers["x-voidnet-signature"] == expected_sig
    # Timestamp within HMAC_TS_SKEW_SECS of "now"
    assert abs(int(time.time()) - ts) <= HMAC_TS_SKEW_SECS


# ── 4xx fallback to TG locale ─────────────────────────────────────────


def test_get_user_lang_404_falls_back_to_tg_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    _, transport = _mock_transport(
        [httpx.Response(404, json={"error": "user not found"})]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(404, tg_language_code="ru-RU") == "ru"


def test_get_user_lang_404_no_tg_locale_returns_en(monkeypatch: pytest.MonkeyPatch) -> None:
    _, transport = _mock_transport([httpx.Response(404, json={})])
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(123, tg_language_code=None) == "en"


# ── 5xx fallback ──────────────────────────────────────────────────────


def test_get_user_lang_5xx_falls_back_to_tg(monkeypatch: pytest.MonkeyPatch) -> None:
    _, transport = _mock_transport([httpx.Response(503, text="upstream down")])
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(1, tg_language_code="en-US") == "en"


def test_get_user_lang_network_error_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(_request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("dns down")

    transport = httpx.MockTransport(boom)
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(1, tg_language_code="ru") == "ru"


# ── Cache: hit within 60s, expire after 60s ──────────────────────────


def test_get_user_lang_cache_hit_within_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    seen, transport = _mock_transport(
        [
            httpx.Response(200, json={"id": 11, "language": "ru"}),
            httpx.Response(200, json={"id": 11, "language": "en"}),
        ]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))

    fake_now = [1_000_000.0]
    monkeypatch.setattr(lang_mod.time, "time", lambda: fake_now[0])

    assert get_user_lang(11) == "ru"
    fake_now[0] += 30  # within 60s TTL
    assert get_user_lang(11) == "ru"  # cached
    assert len(seen) == 1


def test_get_user_lang_cache_expires_after_ttl(monkeypatch: pytest.MonkeyPatch) -> None:
    seen, transport = _mock_transport(
        [
            httpx.Response(200, json={"id": 11, "language": "ru"}),
            httpx.Response(200, json={"id": 11, "language": "en"}),
        ]
    )
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))

    fake_now = [1_000_000.0]
    monkeypatch.setattr(lang_mod.time, "time", lambda: fake_now[0])

    assert get_user_lang(11) == "ru"
    fake_now[0] += 61  # past 60s TTL
    assert get_user_lang(11) == "en"  # re-fetched
    assert len(seen) == 2


# ── Flag off short-circuit (no HTTP call, no cache write) ─────────────


def test_get_user_lang_flag_off_returns_en_no_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("I18N_SUBSTRATE_V1", "0")

    called = {"n": 0}

    def must_not_call() -> httpx.Client:
        called["n"] += 1
        raise AssertionError("HTTP client must not be built when flag is off")

    monkeypatch.setattr(lang_mod, "_build_client", must_not_call)
    assert get_user_lang(7, tg_language_code="ru") == "en"
    assert called["n"] == 0
    # Cache must not be populated either — flipping flag back on shouldn't return stale 'en'.
    assert 7 not in lang_mod._CACHE


# ── Body without language field falls through ─────────────────────────


def test_get_user_lang_200_missing_field_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    _, transport = _mock_transport([httpx.Response(200, json={"id": 1})])
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(1, tg_language_code="ru") == "ru"


def test_get_user_lang_200_unknown_lang_normalizes_via_bcp47(monkeypatch: pytest.MonkeyPatch) -> None:
    """Server somehow returns 'fr' (shouldn't happen — voidnet stores en/ru) — bot
    must normalize to 'en' rather than echo a value the dictionaries don't know."""
    _, transport = _mock_transport([httpx.Response(200, json={"language": "fr"})])
    monkeypatch.setattr(lang_mod, "_build_client", lambda: httpx.Client(transport=transport))
    assert get_user_lang(1) == "en"
