"""Phase 5 Plan 02 — Telegram Login Widget HMAC + session cookie + require_owner.

Contract tests (RED phase). Imports from `bot.dashboard.auth` and
`bot.dashboard.deps` are expected to fail until Plan 02 Task 2 lands.
"""
from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


# ── Helpers ──────────────────────────────────────────────────────────
def _signed_payload(
    bot_token: str,
    *,
    id_: int = 111222333,
    auth_date: int | None = None,
    first_name: str = "Test",
) -> dict[str, str]:
    """Build a genuine Telegram Login Widget payload with a valid hash."""
    payload: dict[str, str] = {
        "id": str(id_),
        "first_name": first_name,
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
    }
    data_check = "\n".join(f"{k}={v}" for k, v in sorted(payload.items()))
    secret = hashlib.sha256(bot_token.encode()).digest()
    payload["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return payload


def _stub_app() -> FastAPI:
    """Tiny FastAPI app that exercises require_owner."""
    from bot.dashboard.deps import require_owner

    app = FastAPI()

    @app.get("/who")
    def who(uid: int = Depends(require_owner)) -> dict[str, int]:
        return {"user_id": uid}

    return app


# ── Telegram HMAC verification ───────────────────────────────────────
def test_verify_valid_payload(bot_token: str) -> None:
    from bot.dashboard.auth import verify_telegram_payload

    payload = _signed_payload(bot_token)
    assert verify_telegram_payload(payload, bot_token) is True


def test_verify_rejects_tampered_id(bot_token: str) -> None:
    from bot.dashboard.auth import verify_telegram_payload

    payload = _signed_payload(bot_token, id_=111222333)
    payload["id"] = "999999999"  # tamper after hash generation
    assert verify_telegram_payload(payload, bot_token) is False


def test_verify_rejects_missing_hash(bot_token: str) -> None:
    from bot.dashboard.auth import verify_telegram_payload

    payload = _signed_payload(bot_token)
    payload.pop("hash")
    assert verify_telegram_payload(payload, bot_token) is False


def test_verify_rejects_stale_auth_date(bot_token: str) -> None:
    from bot.dashboard.auth import verify_telegram_payload

    stale = int(time.time()) - 86400 - 60  # just past the 24h window
    payload = _signed_payload(bot_token, auth_date=stale)
    assert verify_telegram_payload(payload, bot_token) is False


def test_verify_uses_compare_digest(
    bot_token: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timing-safe compare must be used — not '=='."""
    import bot.dashboard.auth as auth_mod

    calls = {"n": 0}
    real_compare = hmac.compare_digest

    def spy(a: object, b: object) -> bool:
        calls["n"] += 1
        return real_compare(a, b)  # type: ignore[arg-type]

    monkeypatch.setattr(auth_mod.hmac, "compare_digest", spy)
    payload = _signed_payload(bot_token)
    auth_mod.verify_telegram_payload(payload, bot_token)
    assert calls["n"] >= 1


def test_verify_rejects_empty_bot_token(bot_token: str) -> None:
    from bot.dashboard.auth import verify_telegram_payload

    payload = _signed_payload(bot_token)
    assert verify_telegram_payload(payload, "") is False


# ── Session cookie round-trip ────────────────────────────────────────
def test_issue_and_read_session_round_trip(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, 1700000000, "abcd")
    payload = read_session_cookie(token)
    assert payload is not None
    assert payload["user_id"] == 111
    assert payload["auth_date"] == 1700000000
    assert payload["hash"] == "abcd"


def test_read_session_rejects_tampered(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, 1700000000, "abcd")
    # Flip one char somewhere in the middle.
    mid = len(token) // 2
    flipped = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1 :]
    assert read_session_cookie(flipped) is None


def test_read_session_rejects_expired(session_secret: str) -> None:
    from bot.dashboard.auth import issue_session_cookie, read_session_cookie

    token = issue_session_cookie(111, 1700000000, "abcd")
    # Force immediate expiry.
    time.sleep(1.01)
    assert read_session_cookie(token, max_age=0) is None


def test_read_session_rejects_missing_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    from bot.dashboard.auth import issue_session_cookie

    monkeypatch.delenv("SESSION_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        issue_session_cookie(111, 1700000000, "abcd")


# ── require_owner FastAPI dependency ─────────────────────────────────
def test_require_owner_no_cookie_redirects(
    session_secret: str, owner_id: int
) -> None:
    app = _stub_app()
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who")
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_require_owner_bad_cookie_redirects(
    session_secret: str, owner_id: int
) -> None:
    app = _stub_app()
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": "not-a-real-token"})
    assert r.status_code == 302
    assert r.headers["location"] == "/login"


def test_require_owner_valid_non_owner_403(
    session_secret: str, owner_id: int
) -> None:
    from bot.dashboard.auth import issue_session_cookie

    cookie = issue_session_cookie(999, 1700000000, "abcd")  # not owner_id
    app = _stub_app()
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": cookie})
    assert r.status_code == 403


def test_require_owner_valid_owner_passes(
    session_secret: str, owner_id: int
) -> None:
    from bot.dashboard.auth import issue_session_cookie

    cookie = issue_session_cookie(owner_id, 1700000000, "abcd")
    app = _stub_app()
    client = TestClient(app, follow_redirects=False)
    r = client.get("/who", cookies={"animaya_session": cookie})
    assert r.status_code == 200
    assert r.json() == {"user_id": owner_id}
