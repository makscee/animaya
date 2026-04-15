"""Shared fixtures for dashboard-related tests (Phase 5).

Fixtures:
    events_log: points ANIMAYA_EVENTS_LOG at a per-test tmp_path file and
        yields the path, ensuring each test has an isolated events.log.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest


@pytest.fixture
def events_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isolate bot.events log output under tmp_path for the test.

    Also evicts any cached bot.events module so the next import picks up
    the env var (defensive — current implementation re-reads env per call).
    """
    path = tmp_path / "events.log"
    monkeypatch.setenv("ANIMAYA_EVENTS_LOG", str(path))
    # Evict cached module so test assertions about module-level defaults
    # are always against a fresh import if anyone imports at module scope.
    sys.modules.pop("bot.events", None)
    return path
