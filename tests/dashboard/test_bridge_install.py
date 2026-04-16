"""Integration tests for the bridge install endpoint and token redaction (Phase 9, Plan 01).

Tests:
    - POST /api/modules/telegram-bridge/install with valid / invalid / network-error / empty token
    - Token redaction in GET /api/modules (modules list)
    - Token redaction in GET /modules/telegram-bridge/config
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator
from unittest.mock import AsyncMock, patch

import pytest

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


def _seed_bridge_module_in_registry(hub_dir: Path, *, token: str = "SECRET_TOKEN") -> Path:
    """Seed a telegram-bridge entry in registry.json with the given token.

    Returns the module_dir path.
    """
    module_dir = hub_dir / "modules" / "telegram-bridge"
    module_dir.mkdir(parents=True, exist_ok=True)

    # Write manifest so validate_manifest doesn't fail
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

    # Write config.json with token
    (module_dir / "config.json").write_text(
        json.dumps({"token": token}, indent=2), encoding="utf-8"
    )

    # Seed registry
    registry_path = hub_dir / "registry.json"
    registry = {"modules": [
        {
            "name": "telegram-bridge",
            "module_dir": str(module_dir),
            "config": {"token": token},
        }
    ]}
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    return module_dir


# ── Install endpoint tests ────────────────────────────────────────────────────


def test_install_valid_token(
    auth_client,
    temp_hub_dir: Path,
) -> None:
    """Valid token triggers install job and returns HX-Redirect header."""
    with (
        patch(
            "bot.dashboard.bridge_routes.validate_bot_token",
            new=AsyncMock(return_value=(True, "testbot", None)),
        ),
        patch(
            "bot.dashboard.bridge_routes.start_install",
            new=AsyncMock(return_value=object()),
        ),
    ):
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            json={"token": "110201543:valid_token_here"},
        )

    assert r.status_code == 200
    assert "HX-Redirect" in r.headers
    assert r.headers["HX-Redirect"] == "/modules/telegram-bridge/config"


def test_install_invalid_token(auth_client) -> None:
    """Invalid token returns an error fragment without installing."""
    with patch(
        "bot.dashboard.bridge_routes.validate_bot_token",
        new=AsyncMock(return_value=(False, None, "Unauthorized")),
    ):
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            json={"token": "bad_token"},
        )

    assert r.status_code == 200
    assert "Invalid bot token" in r.text
    assert "HX-Redirect" not in r.headers


def test_install_network_error(auth_client) -> None:
    """Network error during getMe returns a 'Could not reach Telegram API' fragment."""
    with patch(
        "bot.dashboard.bridge_routes.validate_bot_token",
        new=AsyncMock(return_value=(False, None, "Could not reach Telegram API")),
    ):
        r = auth_client.post(
            "/api/modules/telegram-bridge/install",
            json={"token": "any_token"},
        )

    assert r.status_code == 200
    assert "Could not reach Telegram API" in r.text
    assert "HX-Redirect" not in r.headers


def test_install_empty_token(auth_client) -> None:
    """Empty token returns 'Token is required' fragment immediately."""
    r = auth_client.post(
        "/api/modules/telegram-bridge/install",
        json={"token": ""},
    )
    assert r.status_code == 200
    assert "Token is required" in r.text
    assert "HX-Redirect" not in r.headers


# ── Token redaction tests ─────────────────────────────────────────────────────


def test_token_redacted_in_module_list(
    auth_client,
    temp_hub_dir: Path,
) -> None:
    """GET /modules does not expose the raw token; response contains has_token."""
    _seed_bridge_module_in_registry(temp_hub_dir, token="SUPER_SECRET_TOKEN")

    r = auth_client.get("/modules")

    assert r.status_code == 200
    assert "SUPER_SECRET_TOKEN" not in r.text
    # has_token is surfaced via template context (not always rendered literally, but
    # the raw token value must be absent from the HTML response body)


def test_token_redacted_in_module_config(
    auth_client,
    temp_hub_dir: Path,
) -> None:
    """GET /modules/telegram-bridge/config does not expose the raw token value."""
    _seed_bridge_module_in_registry(temp_hub_dir, token="MY_RAW_TOKEN_VALUE")

    r = auth_client.get("/modules/telegram-bridge/config")

    assert r.status_code == 200
    assert "MY_RAW_TOKEN_VALUE" not in r.text


# ── FSM claim-status endpoint tests (Plan 02) ─────────────────────────────────


def _seed_bridge_with_state(
    hub_dir: Path,
    *,
    state: dict,
    token: str = "SECRET_TOKEN",
) -> Path:
    """Seed bridge module in registry + write state.json."""
    from bot.modules.telegram_bridge_state import write_state  # noqa: PLC0415

    module_dir = _seed_bridge_module_in_registry(hub_dir, token=token)
    write_state(module_dir, state)
    return module_dir


def test_claim_status_unclaimed(
    auth_client,
    temp_hub_dir: Path,
) -> None:
    """GET claim-status with unclaimed state returns Generate Pairing Code button."""
    _seed_bridge_with_state(
        temp_hub_dir,
        state={"claim_status": "unclaimed", "owner_id": None},
    )

    r = auth_client.get("/api/modules/telegram-bridge/claim-status")

    assert r.status_code == 200
    assert "Generate Pairing Code" in r.text


def test_claim_status_pending(
    auth_client,
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
) -> None:
    """GET claim-status with pending state returns polling fragment."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    future = (datetime.now(timezone.utc) + timedelta(minutes=8)).isoformat()
    _seed_bridge_with_state(
        temp_hub_dir,
        state={
            "claim_status": "pending",
            "owner_id": None,
            "pairing_code_hash": "abc123",
            "pairing_code_salt": "salt",
            "pairing_code_expires": future,
            "pairing_attempts": 1,
        },
    )

    r = auth_client.get("/api/modules/telegram-bridge/claim-status")

    assert r.status_code == 200
    assert 'hx-trigger="every 5s"' in r.text
    assert "attempt(s) remaining" in r.text


def test_claim_status_claimed(
    auth_client,
    temp_hub_dir: Path,
    owner_id: int,
) -> None:
    """GET claim-status with claimed state returns Revoke Ownership button."""
    _seed_bridge_with_state(
        temp_hub_dir,
        state={"claim_status": "claimed", "owner_id": owner_id},
    )

    r = auth_client.get("/api/modules/telegram-bridge/claim-status")

    assert r.status_code == 200
    assert "Ownership claimed" in r.text
    assert "Revoke Ownership" in r.text


def test_generate_code(
    auth_client,
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
) -> None:
    """POST generate-code returns 6-digit code and polling trigger."""
    _seed_bridge_with_state(
        temp_hub_dir,
        state={"claim_status": "unclaimed", "owner_id": None},
    )

    r = auth_client.post("/api/modules/telegram-bridge/generate-code")

    assert r.status_code == 200
    assert 'hx-trigger="every 5s"' in r.text
    # Body should contain a 6-digit code
    import re  # noqa: PLC0415

    codes = re.findall(r"\b\d{6}\b", r.text)
    assert len(codes) >= 1


def test_regenerate_code(
    auth_client,
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
) -> None:
    """POST regenerate returns a new code and polling trigger."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
    _seed_bridge_with_state(
        temp_hub_dir,
        state={
            "claim_status": "pending",
            "owner_id": None,
            "pairing_code_hash": "oldhash",
            "pairing_code_salt": "oldsalt",
            "pairing_code_expires": future,
            "pairing_attempts": 0,
        },
    )

    r = auth_client.post("/api/modules/telegram-bridge/regenerate")

    assert r.status_code == 200
    assert 'hx-trigger="every 5s"' in r.text
    import re  # noqa: PLC0415

    codes = re.findall(r"\b\d{6}\b", r.text)
    assert len(codes) >= 1


def test_claim_status_expired_transitions(
    auth_client,
    temp_hub_dir: Path,
) -> None:
    """GET claim-status with expired pending state auto-transitions to unclaimed."""
    from datetime import datetime, timedelta, timezone  # noqa: PLC0415

    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    _seed_bridge_with_state(
        temp_hub_dir,
        state={
            "claim_status": "pending",
            "owner_id": None,
            "pairing_code_hash": "abc123",
            "pairing_code_salt": "salt",
            "pairing_code_expires": past,
            "pairing_attempts": 2,
        },
    )

    r = auth_client.get("/api/modules/telegram-bridge/claim-status")

    assert r.status_code == 200
    # Should show unclaimed state (no polling trigger)
    assert "Generate Pairing Code" in r.text
    assert 'hx-trigger="every 5s"' not in r.text


# ── Plan 03: Revoke, open-bootstrap, auth gate, SEC-01 tests ─────────────────


def test_revoke_endpoint(
    auth_client,
    temp_hub_dir: Path,
    owner_id: int,
) -> None:
    """POST /revoke with claimed owner → returns unclaimed fragment, state cleared."""
    from bot.modules.telegram_bridge_state import read_state  # noqa: PLC0415

    module_dir = _seed_bridge_with_state(
        temp_hub_dir,
        state={"claim_status": "claimed", "owner_id": owner_id},
    )

    r = auth_client.post("/api/modules/telegram-bridge/revoke")

    assert r.status_code == 200
    assert "Generate Pairing Code" in r.text

    state = read_state(module_dir)
    assert state["claim_status"] == "unclaimed"
    assert state["owner_id"] is None


def test_open_bootstrap_no_owner(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
) -> None:
    """GET protected route with no owner claimed → 200 open access (D-9.12)."""
    from tests.dashboard._helpers import build_client  # noqa: PLC0415

    # temp_hub_dir has empty registry → get_owner_id returns None → open access
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        r = tc.get("/")
    assert r.status_code == 200


def test_auth_gate_with_owner_no_cookie(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001 — sets up claimed state.json
    events_log: Path,  # noqa: ARG001
) -> None:
    """GET protected route with claimed owner + no cookie → 302 redirect to /login."""
    from tests.dashboard._helpers import build_client  # noqa: PLC0415

    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        r = tc.get("/")
    assert r.status_code == 302
    assert r.headers.get("location") == "/login"


def test_auth_gate_with_owner_wrong_cookie(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001 — sets up claimed state.json
    events_log: Path,  # noqa: ARG001
) -> None:
    """GET protected route with claimed owner + wrong user_id cookie → 403."""
    from bot.dashboard.auth import SESSION_COOKIE_NAME, issue_session_cookie  # noqa: PLC0415
    from tests.dashboard._helpers import build_client  # noqa: PLC0415

    wrong_cookie = issue_session_cookie(user_id=999)
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        tc.cookies.set(SESSION_COOKIE_NAME, wrong_cookie)
        r = tc.get("/")
    assert r.status_code == 403


def test_token_not_in_logs_after_install(
    auth_client,
    temp_hub_dir: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """SEC-01: raw token value must NOT appear in any log record after install."""
    import logging  # noqa: PLC0415

    secret_token = "1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZ_secret"

    with (
        patch(
            "bot.dashboard.bridge_routes.validate_bot_token",
            new=AsyncMock(return_value=(True, "testbot", None)),
        ),
        patch(
            "bot.dashboard.bridge_routes.start_install",
            new=AsyncMock(return_value=object()),
        ),
        caplog.at_level(logging.DEBUG),
    ):
        auth_client.post(
            "/api/modules/telegram-bridge/install",
            json={"token": secret_token},
        )

    for record in caplog.records:
        assert secret_token not in record.getMessage(), (
            f"Token found in log record: {record.getMessage()}"
        )
