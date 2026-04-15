"""Tests for module install/uninstall lifecycle (Phase 3, MODS-03)."""
from __future__ import annotations

import json
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


class TestLifecycle:
    def test_install_runs_script_and_updates_registry(
        self, valid_module_dir: Path, tmp_hub_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        assert (tmp_hub_dir / ".sample-marker").exists()
        assert "sample" in mods.list_installed(tmp_hub_dir)

    def test_install_rejects_already_installed(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        with pytest.raises(Exception) as exc_info:
            mods.install(valid_module_dir, tmp_hub_dir)
        assert "already installed" in str(exc_info.value).lower()

    def test_install_failure_triggers_rollback(
        self, tmp_path: Path, tmp_hub_dir: Path
    ) -> None:
        mod_dir = tmp_path / "failing"
        mod_dir.mkdir()
        manifest = {
            "manifest_version": 1,
            "name": "failing",
            "version": "1.0.0",
            "system_prompt_path": "prompt.md",
            "owned_paths": [],
            "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
            "depends": [],
            "config_schema": None,
        }
        (mod_dir / "manifest.json").write_text(json.dumps(manifest))
        (mod_dir / "prompt.md").write_text("failing module")
        install_script = mod_dir / "install.sh"
        install_script.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 1\n")
        install_script.chmod(0o755)
        uninstall_script = mod_dir / "uninstall.sh"
        uninstall_script.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n")
        uninstall_script.chmod(0o755)

        with pytest.raises(Exception):
            mods.install(mod_dir, tmp_hub_dir)
        assert mods.list_installed(tmp_hub_dir) == []

    async def test_uninstall_removes_registry_entry(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        await mods.uninstall("sample", tmp_hub_dir, valid_module_dir)
        assert mods.list_installed(tmp_hub_dir) == []
        assert not (tmp_hub_dir / ".sample-marker").exists()

    async def test_uninstall_of_uninstalled_module_rejected(self, tmp_hub_dir: Path) -> None:
        with pytest.raises(Exception) as exc_info:
            await mods.uninstall("ghost", tmp_hub_dir, tmp_hub_dir)
        assert "not installed" in str(exc_info.value).lower()

    def test_missing_dependency_rejected(self, tmp_path: Path, tmp_hub_dir: Path) -> None:
        mod_dir = tmp_path / "needs-dep"
        mod_dir.mkdir()
        manifest = {
            "manifest_version": 1,
            "name": "needs-dep",
            "version": "1.0.0",
            "system_prompt_path": "prompt.md",
            "owned_paths": [],
            "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
            "depends": ["missing"],
            "config_schema": None,
        }
        (mod_dir / "manifest.json").write_text(json.dumps(manifest))
        (mod_dir / "prompt.md").write_text("needs-dep")
        for name in ("install.sh", "uninstall.sh"):
            path = mod_dir / name
            path.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n")
            path.chmod(0o755)

        with pytest.raises(Exception) as exc_info:
            mods.install(mod_dir, tmp_hub_dir)
        assert "missing dependency" in str(exc_info.value).lower()
