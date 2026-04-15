"""Shared fixtures for Phase 3 module-system tests.

Provides tmp_hub_dir (pytest tmp_path mimicking ~/hub/knowledge/animaya/),
valid_module_dir (copy of the valid-module fixture), invalid_manifest_dir
(copy of the invalid-manifest fixture), and sample_manifest_dict (plain
dict matching ModuleManifest v1, for unit tests without disk I/O).

Phase 4 additions: tmp_hub_knowledge, tmp_hub_with_identity, tmp_hub_with_memory,
tmp_hub_git_repo, fake_claude_query — shared fixtures for identity/memory/git-versioning
module tests. All derive from tmp_path; fixtures never touch Path.home().
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import AsyncIterator, Callable

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


# ── Phase 4 fixtures ──────────────────────────────────────────────────────────

PLACEHOLDER_MARKER = "<!-- animaya:placeholder -->"


@pytest.fixture
def tmp_hub_knowledge(tmp_path: Path) -> Path:
    """Tmp ~/hub/knowledge/ root (parent of identity/ and memory/).

    Note: derives from tmp_path only — never touches Path.home().
    """
    kn = tmp_path / "hub" / "knowledge"
    kn.mkdir(parents=True, exist_ok=True)
    return kn


@pytest.fixture
def tmp_hub_with_identity(tmp_hub_knowledge: Path) -> Path:
    """tmp_hub_knowledge populated with placeholder identity files + sentinel.

    Note: derives from tmp_path only — never touches Path.home().
    """
    ident = tmp_hub_knowledge / "identity"
    ident.mkdir(parents=True, exist_ok=True)
    (ident / "USER.md").write_text(
        f"{PLACEHOLDER_MARKER}\n# User\n\n(Pending onboarding)\n", encoding="utf-8"
    )
    (ident / "SOUL.md").write_text(
        f"{PLACEHOLDER_MARKER}\n# Assistant Identity\n\n(Pending onboarding)\n",
        encoding="utf-8",
    )
    (ident / ".pending-onboarding").write_text("awaiting first user message\n", encoding="utf-8")
    return tmp_hub_knowledge


@pytest.fixture
def tmp_hub_with_memory(tmp_hub_knowledge: Path) -> Path:
    """tmp_hub_knowledge populated with empty CORE.md + README.md.

    Note: derives from tmp_path only — never touches Path.home().
    """
    mem = tmp_hub_knowledge / "memory"
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "CORE.md").write_text("# Core Memory\n\n(empty)\n", encoding="utf-8")
    (mem / "README.md").write_text("# Memory\n", encoding="utf-8")
    return tmp_hub_knowledge


@pytest.fixture
def tmp_hub_git_repo(tmp_path: Path) -> Path:
    """Fresh git repo at tmp_path/hub/ with knowledge/ subdir, identity configured.

    Note: derives from tmp_path only — never touches Path.home().
    """
    hub = tmp_path / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "knowledge").mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(hub), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(hub), "config", "user.name", "Animaya Bot"], check=True)
    subprocess.run(["git", "-C", str(hub), "config", "user.email", "bot@animaya.local"], check=True)
    # Initial empty commit so HEAD exists
    subprocess.run(["git", "-C", str(hub), "commit", "--allow-empty", "-m", "init", "-q"], check=True)
    return hub


class _FakeAssistantMessage:
    def __init__(self, text: str):
        from types import SimpleNamespace

        self.content = [SimpleNamespace(text=text)]


@pytest.fixture
def fake_claude_query() -> Callable[[str], AsyncIterator]:
    """Factory: returns an async-iterator yielding one AssistantMessage with given text."""

    def _factory(reply_text: str):
        async def _gen(*args, **kwargs):
            yield _FakeAssistantMessage(reply_text)

        return _gen

    return _factory
