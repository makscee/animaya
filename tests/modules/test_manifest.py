"""Tests for module manifest validation (Phase 3, MODS-01)."""
from __future__ import annotations

from pathlib import Path

import importlib.util

import pytest

# Skip (but still collect) until bot.modules package exists (Wave 1+)
_HAS_MODS = importlib.util.find_spec("bot.modules") is not None
pytestmark = pytest.mark.skipif(
    not _HAS_MODS, reason="bot.modules package not yet implemented"
)

if _HAS_MODS:
    import bot.modules as mods  # noqa: E402
else:
    mods = None  # type: ignore[assignment]


class TestManifest:
    def test_valid_manifest_parses(self, valid_module_dir: Path) -> None:
        manifest = mods.validate_manifest(valid_module_dir)
        assert manifest.name == "sample"
        assert manifest.version == "1.0.0"
        assert manifest.manifest_version == 1

    def test_invalid_rejected(self, invalid_manifest_dir: Path) -> None:
        with pytest.raises(Exception) as exc_info:
            mods.validate_manifest(invalid_manifest_dir)
        msg = str(exc_info.value).lower()
        assert "unexpected_field" in msg or "extra" in msg

    def test_missing_required_field_rejected(
        self, tmp_path: Path, sample_manifest_dict: dict
    ) -> None:
        import json

        bad = dict(sample_manifest_dict)
        bad.pop("name")
        mod_dir = tmp_path / "incomplete"
        mod_dir.mkdir()
        (mod_dir / "manifest.json").write_text(json.dumps(bad))
        with pytest.raises(Exception):
            mods.validate_manifest(mod_dir)

    def test_semver_prefix_accepted(self, sample_manifest_dict: dict) -> None:
        manifest = mods.ModuleManifest.model_validate(sample_manifest_dict)
        assert manifest.name == "sample"
        assert manifest.version.startswith("1.")
