"""Tests for CLAUDE.md assembler (Phase 3, MODS-04)."""
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


class TestAssembler:
    def test_assembler_writes_base_only_when_empty_registry(
        self, tmp_hub_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = mods.assemble_claude_md(tmp_hub_dir)
        assert "<!-- No modules installed -->" in output

    def test_assembler_merges_installed_module_prompt(
        self,
        valid_module_dir: Path,
        tmp_hub_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mods.install(valid_module_dir, tmp_hub_dir)
        output = mods.assemble_claude_md(tmp_hub_dir)
        assert '<module name="sample">' in output
        assert "sample module" in output.lower()

    def test_assembler_preserves_install_order(
        self, tmp_path: Path, tmp_hub_dir: Path
    ) -> None:
        entries = [
            {
                "name": "alpha",
                "version": "1.0.0",
                "installed_at": "2026-01-01T00:00:00Z",
                "prompt": "alpha prompt",
            },
            {
                "name": "beta",
                "version": "1.0.0",
                "installed_at": "2026-01-02T00:00:00Z",
                "prompt": "beta prompt",
            },
        ]
        mods.write_registry(tmp_hub_dir, {"modules": entries})
        output = mods.assemble_claude_md(tmp_hub_dir)
        alpha_idx = output.find('<module name="alpha">')
        beta_idx = output.find('<module name="beta">')
        assert alpha_idx != -1 and beta_idx != -1
        assert alpha_idx < beta_idx
