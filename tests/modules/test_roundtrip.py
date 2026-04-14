"""Tests for full install/uninstall roundtrip (Phase 3, MODS-05)."""
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


class TestRoundtrip:
    def test_install_uninstall_leaves_no_artifacts(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        assert (tmp_hub_dir / ".sample-marker").exists()
        mods.uninstall("sample", tmp_hub_dir, valid_module_dir)
        assert not (tmp_hub_dir / ".sample-marker").exists()

    def test_registry_is_empty_after_roundtrip(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        mods.uninstall("sample", tmp_hub_dir, valid_module_dir)
        assert mods.list_installed(tmp_hub_dir) == []
