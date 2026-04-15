"""BRDG-01: module-first lifecycle — runtime_entry plumbing.

Tests that ModuleManifest accepts / validates runtime_entry, and that
lifecycle.install() propagates it into the registry entry.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from bot.modules.manifest import ModuleManifest
from bot.modules.lifecycle import install
from bot.modules.registry import get_entry

_FIXTURES_ROOT = Path(__file__).parent / "fixtures"


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def tmp_hub_dir(tmp_path: Path) -> Path:
    """Tmp Hub directory."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


@pytest.fixture
def bridge_module_dir(tmp_path: Path) -> Path:
    """A minimal valid module dir for bridge-module install tests."""
    dest = tmp_path / "modules" / "sample"
    src = _FIXTURES_ROOT / "valid-module"
    shutil.copytree(src, dest)
    (dest / "install.sh").chmod(0o755)
    (dest / "uninstall.sh").chmod(0o755)
    return dest


@pytest.fixture
def bridge_module_dir_with_runtime(tmp_path: Path) -> Path:
    """A minimal valid module dir whose manifest has runtime_entry set."""
    src = _FIXTURES_ROOT / "valid-module"
    dest = tmp_path / "modules" / "sample"
    shutil.copytree(src, dest)
    (dest / "install.sh").chmod(0o755)
    (dest / "uninstall.sh").chmod(0o755)
    # Overwrite manifest with runtime_entry
    manifest = json.loads((dest / "manifest.json").read_text())
    manifest["runtime_entry"] = "bot.modules_runtime.telegram_bridge"
    (dest / "manifest.json").write_text(json.dumps(manifest))
    return dest


# ── Tests ─────────────────────────────────────────────────────────────

class TestModuleManifestRuntimeEntry:
    """Test 1-3: ModuleManifest runtime_entry field validation."""

    def test_existing_manifest_without_runtime_entry_defaults_to_none(self) -> None:
        """Test 1: Existing manifests load without runtime_entry (defaults to None)."""
        m = ModuleManifest(
            name="sample",
            version="1.0.0",
            manifest_version=1,
            system_prompt_path="prompt.md",
            owned_paths=[],
        )
        assert m.runtime_entry is None

    def test_manifest_accepts_valid_runtime_entry(self) -> None:
        """Test 2: ModuleManifest accepts runtime_entry with valid bot.* dotted path."""
        m = ModuleManifest(
            name="sample",
            version="1.0.0",
            manifest_version=1,
            system_prompt_path="prompt.md",
            owned_paths=[],
            runtime_entry="bot.modules_runtime.telegram_bridge",
        )
        assert m.runtime_entry == "bot.modules_runtime.telegram_bridge"

    def test_manifest_rejects_unsafe_runtime_entry(self) -> None:
        """Test 3: ModuleManifest rejects runtime_entry not matching bot.* namespace."""
        with pytest.raises(ValidationError) as exc_info:
            ModuleManifest(
                name="sample",
                version="1.0.0",
                manifest_version=1,
                system_prompt_path="prompt.md",
                owned_paths=[],
                runtime_entry="os.system",
            )
        err_str = str(exc_info.value)
        assert "runtime_entry" in err_str or "ValidationError" in err_str


class TestRegistryRuntimeEntryPropagation:
    """Test 4-5: lifecycle.install() propagates runtime_entry into registry entry."""

    def test_install_with_runtime_entry_propagates_to_registry(
        self, bridge_module_dir_with_runtime: Path, tmp_hub_dir: Path
    ) -> None:
        """Test 4: After install() with runtime_entry, registry entry carries it."""
        install(bridge_module_dir_with_runtime, tmp_hub_dir)
        entry = get_entry(tmp_hub_dir, "sample")
        assert entry is not None
        assert "runtime_entry" in entry
        assert entry["runtime_entry"] == "bot.modules_runtime.telegram_bridge"

    def test_install_without_runtime_entry_has_none_in_registry(
        self, bridge_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        """Test 5: After install() without runtime_entry, registry entry has runtime_entry: None."""
        install(bridge_module_dir, tmp_hub_dir)
        entry = get_entry(tmp_hub_dir, "sample")
        assert entry is not None
        assert "runtime_entry" in entry
        assert entry["runtime_entry"] is None
