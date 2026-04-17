"""Shared fixtures for bot.engine tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def temp_hub_dir(tmp_path: Path) -> Path:
    """Isolated hub directory with an empty registry.json seeded."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "registry.json").write_text(json.dumps({"modules": []}), encoding="utf-8")
    return hub


@pytest.fixture
def events_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect ANIMAYA_EVENTS_LOG into tmp_path so tests are isolated."""
    log = tmp_path / "events.log"
    monkeypatch.setenv("ANIMAYA_EVENTS_LOG", str(log))
    return log
