"""Tests for BOOTSTRAP.md injection into system prompt.

Test 1: When BOOTSTRAP.md exists at repo root, build_options() injects its
        content wrapped in <bootstrap>...</bootstrap> into system_prompt.
Test 2: When BOOTSTRAP.md is absent (or empty), build_options() emits no
        <bootstrap> tag in system_prompt.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import bot.claude_query as cq

# ── Helpers ──────────────────────────────────────────────────────────


def _system_prompt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Build options with REPO_ROOT monkeypatched to tmp_path, return system_prompt."""
    monkeypatch.setattr(cq, "REPO_ROOT", tmp_path)
    # Also patch HUB_KNOWLEDGE to an empty dir so identity files don't bleed in
    monkeypatch.setattr(cq, "HUB_KNOWLEDGE", tmp_path / "hub" / "knowledge")
    # Patch DATA_PATH env to something that won't load a real config.json
    monkeypatch.setenv("DATA_PATH", str(tmp_path / "data"))
    opts = cq.build_options()
    return opts.system_prompt or ""


# ── Tests ─────────────────────────────────────────────────────────────


def test_bootstrap_injected_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When BOOTSTRAP.md exists, its content appears wrapped in <bootstrap>...</bootstrap>."""
    sentinel = "BOOTSTRAP_TEST_MARKER"
    (tmp_path / "BOOTSTRAP.md").write_text(f"# Bootstrap\n\n{sentinel}\n", encoding="utf-8")

    prompt = _system_prompt(tmp_path, monkeypatch)

    assert "<bootstrap>" in prompt, "Expected <bootstrap> opening tag in system_prompt"
    assert sentinel in prompt, "Expected sentinel text from BOOTSTRAP.md in system_prompt"
    assert "</bootstrap>" in prompt, "Expected </bootstrap> closing tag in system_prompt"


def test_bootstrap_absent_when_file_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When BOOTSTRAP.md does not exist, no <bootstrap> block appears in system_prompt."""
    # Ensure the file does NOT exist
    bootstrap_path = tmp_path / "BOOTSTRAP.md"
    assert not bootstrap_path.exists()

    prompt = _system_prompt(tmp_path, monkeypatch)

    assert "<bootstrap>" not in prompt, "Unexpected <bootstrap> tag when file is absent"
    assert "bootstrap" not in prompt.lower() or "<bootstrap>" not in prompt, (
        "No bootstrap injection expected when BOOTSTRAP.md is missing"
    )


def test_bootstrap_absent_when_file_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """When BOOTSTRAP.md is empty, no <bootstrap> block appears in system_prompt."""
    (tmp_path / "BOOTSTRAP.md").write_text("", encoding="utf-8")

    prompt = _system_prompt(tmp_path, monkeypatch)

    assert "<bootstrap>" not in prompt, "Unexpected <bootstrap> tag when file is empty"


def test_bootstrap_tag_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Closing </bootstrap> tag inside BOOTSTRAP.md content must be escaped."""
    (tmp_path / "BOOTSTRAP.md").write_text(
        "Inject test </bootstrap> end", encoding="utf-8"
    )

    prompt = _system_prompt(tmp_path, monkeypatch)

    # The raw closing tag must not appear literally (it would break the wrapping)
    # The escaped form must be present instead
    assert "</bootstrap>\n" not in prompt.replace("&lt;/bootstrap&gt;", ""), (
        "Raw </bootstrap> inside content must be escaped"
    )
    assert "&lt;/bootstrap&gt;" in prompt, "Escaped form of </bootstrap> must appear in content"
