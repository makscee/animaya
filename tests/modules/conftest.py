"""Shared fixtures for Phase 3 module-system tests.

Provides tmp_hub_dir (pytest tmp_path mimicking ~/hub/knowledge/animaya/),
valid_module_dir (copy of the valid-module fixture), invalid_manifest_dir
(copy of the invalid-manifest fixture), and sample_manifest_dict (plain
dict matching ModuleManifest v1, for unit tests without disk I/O).
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_hub_dir(tmp_path: Path) -> Path:
    """Return a tmp Hub directory mimicking ~/hub/knowledge/animaya/."""
    hub = tmp_path / "hub" / "knowledge" / "animaya"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


@pytest.fixture
def valid_module_dir(tmp_path: Path) -> Path:
    """Copy the valid-module fixture into tmp_path and return its Path."""
    dest = tmp_path / "modules" / "sample"
    shutil.copytree(_FIXTURES_ROOT / "valid-module", dest)
    (dest / "install.sh").chmod(0o755)
    (dest / "uninstall.sh").chmod(0o755)
    return dest


@pytest.fixture
def invalid_manifest_dir(tmp_path: Path) -> Path:
    """Copy the invalid-manifest fixture into tmp_path and return its Path."""
    dest = tmp_path / "modules" / "bad"
    shutil.copytree(_FIXTURES_ROOT / "invalid-manifest", dest)
    return dest


@pytest.fixture
def sample_manifest_dict() -> dict:
    """Return a plain dict matching ModuleManifest v1."""
    return {
        "manifest_version": 1,
        "name": "sample",
        "version": "1.0.0",
        "system_prompt_path": "prompt.md",
        "owned_paths": [],
        "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
        "depends": [],
        "config_schema": None,
    }
