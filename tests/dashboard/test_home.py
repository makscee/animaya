"""Tests for home page + HTMX fragment endpoints (Phase 5 DASH-03)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.dashboard._helpers import make_session_cookie


@pytest.fixture
def auth_cookie(
    session_secret: str,  # noqa: ARG001
    owner_id: int,
) -> dict[str, str]:
    """animaya_session cookie payload for an authenticated owner."""
    return {"animaya_session": make_session_cookie(owner_id)}


@pytest.fixture
def patched_client(
    client,  # comes from conftest
    monkeypatch: pytest.MonkeyPatch,
):
    """Force 'unknown' status so tests don't depend on the host having systemctl."""
    from bot.dashboard import status

    monkeypatch.setattr(status.shutil, "which", lambda _: None)
    return client


# ── Auth ─────────────────────────────────────────────────────────────
def test_home_redirects_without_session(patched_client) -> None:
    resp = patched_client.get("/")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"


# ── Home page rendering ──────────────────────────────────────────────
def test_home_renders_status_strip(patched_client, auth_cookie) -> None:
    resp = patched_client.get("/", cookies=auth_cookie)
    assert resp.status_code == 200
    body = resp.text
    assert 'class="stats"' in body
    # 3 stat cards by label:
    assert "Bot status" in body
    assert "Modules installed" in body
    assert "Events today" in body


def test_home_htmx_trigger_present(patched_client, auth_cookie) -> None:
    resp = patched_client.get("/", cookies=auth_cookie)
    assert resp.status_code == 200
    # Three panels each declare their own polling trigger.
    assert resp.text.count('hx-trigger="every 5s"') >= 3


def test_home_activity_feed_shows_events(
    patched_client, auth_cookie, events_log: Path
) -> None:
    from bot.events import emit

    emit("info", "bridge", "hello-one")
    emit("info", "bridge", "hello-two")
    emit("info", "bridge", "hello-three")

    resp = patched_client.get("/", cookies=auth_cookie)
    assert resp.status_code == 200
    body = resp.text
    assert "hello-one" in body
    assert "hello-two" in body
    assert "hello-three" in body
    _ = events_log


def test_home_error_feed_filters_errors(
    patched_client, auth_cookie, events_log: Path
) -> None:
    from bot.events import emit

    emit("info", "bridge", "chatty-info-a")
    emit("info", "bridge", "chatty-info-b")
    emit("error", "modules.install", "BOOM-error")

    resp = patched_client.get("/", cookies=auth_cookie)
    body = resp.text

    # Activity feed contains all three (info + error).
    assert "BOOM-error" in body

    # Error feed: isolate "Recent errors" panel substring and verify.
    err_idx = body.find("Recent errors")
    assert err_idx >= 0, "Recent errors panel must be present"
    err_panel = body[err_idx:]
    assert "BOOM-error" in err_panel
    # The infos must not show up in error feed (error panel starts AFTER activity panel).
    # Use the error_feed id to bound the error panel region.
    ef_start = body.find('id="error-feed"')
    assert ef_start >= 0
    # Slice from error-feed marker to end
    ef_region = body[ef_start:]
    assert "chatty-info-a" not in ef_region
    assert "chatty-info-b" not in ef_region
    _ = events_log


def test_home_empty_activity_renders_empty_state(
    patched_client, auth_cookie, events_log: Path  # noqa: ARG001
) -> None:
    resp = patched_client.get("/", cookies=auth_cookie)
    assert resp.status_code == 200
    assert "No activity yet" in resp.text


def test_home_empty_errors_renders_empty_state(
    patched_client, auth_cookie, events_log: Path
) -> None:
    from bot.events import emit

    emit("info", "bridge", "just-info")
    resp = patched_client.get("/", cookies=auth_cookie)
    assert resp.status_code == 200
    assert "No recent errors" in resp.text
    _ = events_log


# ── Fragment endpoints ───────────────────────────────────────────────
def test_fragments_status_returns_partial_only(patched_client, auth_cookie) -> None:
    resp = patched_client.get("/fragments/status", cookies=auth_cookie)
    assert resp.status_code == 200
    body = resp.text.strip()
    assert "<html" not in body.lower()
    assert body.startswith("<div")
    assert 'class="stats"' in body
    assert 'id="status-strip"' in body


def test_fragments_activity_returns_partial(
    patched_client, auth_cookie, events_log: Path
) -> None:
    from bot.events import emit

    emit("info", "bridge", "activity-row")
    resp = patched_client.get("/fragments/activity", cookies=auth_cookie)
    assert resp.status_code == 200
    body = resp.text
    assert "<html" not in body.lower()
    assert 'class="activity-item"' in body
    assert "activity-row" in body
    _ = events_log


def test_fragments_errors_returns_partial(
    patched_client, auth_cookie, events_log: Path
) -> None:
    from bot.events import emit

    emit("info", "bridge", "filler")
    emit("error", "modules.install", "err-row")
    resp = patched_client.get("/fragments/errors", cookies=auth_cookie)
    assert resp.status_code == 200
    body = resp.text
    assert "<html" not in body.lower()
    assert "err-row" in body
    assert "filler" not in body
    _ = events_log


def test_fragments_require_owner(patched_client) -> None:
    resp = patched_client.get("/fragments/status")
    assert resp.status_code == 302
    assert resp.headers["location"] == "/login"
    resp = patched_client.get("/fragments/activity")
    assert resp.status_code == 302
    resp = patched_client.get("/fragments/errors")
    assert resp.status_code == 302
