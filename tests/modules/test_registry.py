"""Tests for module registry read/write (Phase 3, MODS-02)."""
from __future__ import annotations

from pathlib import Path

import importlib.util

import pytest

_HAS_MODS = importlib.util.find_spec("bot.modules") is not None
pytestmark = pytest.mark.skipif(
    not _HAS_MODS, reason="bot.modules package not yet implemented"
)

if _HAS_MODS:
    import bot.modules as mods  # noqa: E402
else:
    mods = None  # type: ignore[assignment]


class TestRegistry:
    def test_read_missing_registry_returns_empty(self, tmp_hub_dir: Path) -> None:
        result = mods.read_registry(tmp_hub_dir)
        assert result == {"modules": []}

    def test_write_then_read_roundtrip(self, tmp_hub_dir: Path) -> None:
        entry = {"name": "sample", "version": "1.0.0", "installed_at": "2026-01-01T00:00:00Z"}
        mods.write_registry(tmp_hub_dir, {"modules": [entry]})
        result = mods.read_registry(tmp_hub_dir)
        assert entry in result["modules"]

    def test_atomic_write_no_partial_file(self, tmp_hub_dir: Path) -> None:
        mods.write_registry(tmp_hub_dir, {"modules": []})
        leftovers = list(tmp_hub_dir.glob("*.tmp"))
        assert leftovers == []

    def test_list_installed_returns_names(self, tmp_hub_dir: Path) -> None:
        entries = [
            {"name": "first", "version": "1.0.0", "installed_at": "2026-01-01T00:00:00Z"},
            {"name": "second", "version": "1.0.0", "installed_at": "2026-01-02T00:00:00Z"},
        ]
        mods.write_registry(tmp_hub_dir, {"modules": entries})
        names = mods.list_installed(tmp_hub_dir)
        assert names == ["first", "second"]
