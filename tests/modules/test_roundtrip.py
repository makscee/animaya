"""End-to-end roundtrip test (Phase 3, MODS-05).

Dogfoods the full lifecycle against the real modules/telegram-bridge/ first-party
module (renamed from modules/bridge/ in Phase 8 Plan 02): install ->
CLAUDE.md contains <module name="telegram-bridge"> -> uninstall ->
CLAUDE.md empty. Also re-verifies the generic lifecycle against the
valid-module fixture to keep the Plan 00 stubs green.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_HAS_MODS = importlib.util.find_spec("bot.modules") is not None
pytestmark = pytest.mark.skipif(
    not _HAS_MODS, reason="bot.modules package not yet implemented"
)

if _HAS_MODS:
    import bot.modules as mods  # noqa: E402
else:
    mods = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MODULES_ROOT = REPO_ROOT / "modules"
BRIDGE_DIR = MODULES_ROOT / "telegram-bridge"


class TestRoundtrip:
    """Generic lifecycle roundtrip against the valid-module fixture."""

    async def test_install_uninstall_leaves_no_artifacts(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        assert (tmp_hub_dir / ".sample-marker").exists()
        await mods.uninstall("sample", tmp_hub_dir, valid_module_dir)
        assert not (tmp_hub_dir / ".sample-marker").exists()

    async def test_registry_is_empty_after_roundtrip(
        self, valid_module_dir: Path, tmp_hub_dir: Path
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        await mods.uninstall("sample", tmp_hub_dir, valid_module_dir)
        assert mods.list_installed(tmp_hub_dir) == []


class TestBridgeDogfood:
    """Install + uninstall the real first-party telegram-bridge module end-to-end.

    Uses the actual ``modules/telegram-bridge/`` directory in the repo — this is the
    Phase 8 dogfood proving the entire module system works on a real module.
    """

    async def test_bridge_install_writes_claude_md_with_module_section(
        self, tmp_hub_dir: Path
    ) -> None:
        # Install telegram-bridge
        entry = mods.install(BRIDGE_DIR, tmp_hub_dir)
        assert entry["name"] == "telegram-bridge"
        assert entry["version"] == "1.0.0"
        assert mods.get_entry(tmp_hub_dir, "telegram-bridge") is not None
        assert mods.list_installed(tmp_hub_dir) == ["telegram-bridge"]

        # Assembled CLAUDE.md should include the bridge section (D-17)
        claude_md = tmp_hub_dir / "CLAUDE.md"
        assert claude_md.is_file()
        content = claude_md.read_text(encoding="utf-8")
        assert '<module name="telegram-bridge">' in content
        assert "Telegram Bridge" in content  # from prompt.md
        assert "</module>" in content

        # Uninstall
        await mods.uninstall("telegram-bridge", tmp_hub_dir, BRIDGE_DIR)
        assert mods.get_entry(tmp_hub_dir, "telegram-bridge") is None
        assert mods.list_installed(tmp_hub_dir) == []

        # Assembled CLAUDE.md should be back to empty-modules marker (D-18)
        content_after = claude_md.read_text(encoding="utf-8")
        assert "<!-- No modules installed -->" in content_after
        assert '<module name="telegram-bridge">' not in content_after

    async def test_bridge_owned_paths_empty_means_no_hub_leakage(
        self, tmp_hub_dir: Path
    ) -> None:
        """Bridge declares owned_paths=[] so no hub-side cleanup is expected.

        MODS-05: verify uninstall leaves no unexpected files beyond the
        assembler/registry outputs that the lifecycle itself owns.
        """
        mods.install(BRIDGE_DIR, tmp_hub_dir)
        await mods.uninstall("telegram-bridge", tmp_hub_dir, BRIDGE_DIR)
        remaining = {p.name for p in tmp_hub_dir.iterdir()}
        # Only files the lifecycle itself owns may remain
        allowed = {"CLAUDE.md", "registry.json"}
        assert remaining <= allowed, f"unexpected hub files left behind: {remaining}"

    async def test_bridge_reinstall_rejected(self, tmp_hub_dir: Path) -> None:
        """D-14: reinstalling the bridge without uninstall first must fail."""
        mods.install(BRIDGE_DIR, tmp_hub_dir)
        with pytest.raises(ValueError, match="already installed"):
            mods.install(BRIDGE_DIR, tmp_hub_dir)
        # Cleanup so the fixture-scoped tmp_hub_dir is consistent
        await mods.uninstall("telegram-bridge", tmp_hub_dir, BRIDGE_DIR)
