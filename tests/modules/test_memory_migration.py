"""migrate_drop_memory tests (quick-260416-ncp — memory folded into core).

Mirrors the migrate_bridge_rename test pattern in test_bridge_module.py.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest

from bot.modules.registry import (
    get_entry,
    migrate_drop_memory,
    read_registry,
    write_registry,
)


@pytest.fixture
def tmp_hub_dir(tmp_path: Path) -> Path:
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


def _write_registry_with_memory(hub_dir: Path, extras: list[dict] | None = None) -> None:
    """Seed registry with a 'memory' entry plus optional siblings."""
    modules = [
        {
            "name": "memory",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-01T00:00:00+00:00",
            "config": {"core_max_lines": 150},
            "depends": ["identity"],
        }
    ]
    if extras:
        modules.extend(extras)
    write_registry(hub_dir, {"modules": modules})


class TestMigrateDropMemory:
    def test_removes_memory_entry(self, tmp_hub_dir: Path) -> None:
        voice = {
            "name": "voice",
            "version": "1.0.0",
            "manifest_version": 1,
            "installed_at": "2026-01-02T00:00:00+00:00",
            "config": {},
            "depends": [],
        }
        _write_registry_with_memory(tmp_hub_dir, extras=[voice])
        result = migrate_drop_memory(tmp_hub_dir)
        assert result is True
        assert get_entry(tmp_hub_dir, "memory") is None
        # Sibling preserved
        assert get_entry(tmp_hub_dir, "voice") is not None

    def test_idempotent(self, tmp_hub_dir: Path) -> None:
        _write_registry_with_memory(tmp_hub_dir)
        first = migrate_drop_memory(tmp_hub_dir)
        second = migrate_drop_memory(tmp_hub_dir)
        assert first is True
        assert second is False

    def test_noop_when_no_memory_entry(self, tmp_hub_dir: Path) -> None:
        write_registry(tmp_hub_dir, {"modules": []})
        result = migrate_drop_memory(tmp_hub_dir)
        assert result is False
        # Registry still exists and is empty
        assert read_registry(tmp_hub_dir) == {"modules": []}

    def test_logs_warning(
        self, tmp_hub_dir: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        _write_registry_with_memory(tmp_hub_dir)
        with caplog.at_level(logging.WARNING, logger="bot.modules.registry"):
            migrate_drop_memory(tmp_hub_dir)
        assert any(
            "memory" in rec.message for rec in caplog.records
        ), f"Expected warning mentioning memory, got: {[r.message for r in caplog.records]}"
