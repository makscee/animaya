"""Memory tests (MEMO-02..04) — memory is core after 260416-ncp fold."""
from __future__ import annotations

import subprocess

import pytest

from bot.memory import consolidation as mem_rt
from bot.modules_runtime.git_versioning import commit_if_changed


class TestMemoryImportSurface:
    def test_consolidation_importable_from_core_path(self):
        from bot.memory.consolidation import (  # noqa: F401,PLC0415
            consolidate_memory,
            maybe_trigger_consolidation,
        )

    def test_old_module_runtime_path_gone(self):
        with pytest.raises(ImportError):
            import bot.modules_runtime.memory  # noqa: F401,PLC0415


class TestMemoryPersist:
    def test_write_to_memory_facts_persists(self, tmp_hub_with_memory):
        mem = tmp_hub_with_memory / "memory"
        (mem / "facts.md").write_text("- The user prefers tea over coffee.\n")
        assert (mem / "facts.md").read_text().startswith("- The user")
        # Path traversal defence smoke: writing outside mem dir is detectable
        assert (mem / "facts.md").resolve().is_relative_to(mem.resolve())


class TestMemoryGitCommit:
    @pytest.mark.asyncio
    async def test_memory_write_followed_by_commit_tick(self, tmp_hub_git_repo):
        mem = tmp_hub_git_repo / "knowledge" / "memory"
        mem.mkdir(parents=True, exist_ok=True)
        (mem / "facts.md").write_text("- fact 1\n")
        made = await commit_if_changed(tmp_hub_git_repo)
        assert made is True
        log = subprocess.run(
            [
                "git",
                "-C",
                str(tmp_hub_git_repo),
                "log",
                "-1",
                "--name-only",
                "--pretty=format:",
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        assert "knowledge/memory/facts.md" in log


class TestConsolidation:
    @pytest.mark.asyncio
    async def test_consolidate_runs_with_haiku_model(
        self, tmp_hub_with_memory, monkeypatch
    ):
        captured = {}

        def fake_query(prompt, options):
            captured["prompt"] = prompt
            captured["model"] = options.model
            captured["continue_conversation"] = options.continue_conversation
            captured["cwd"] = options.cwd

            async def _gen():
                return
                yield  # pragma: no cover — never reached, just makes it an async-gen

            return _gen()

        monkeypatch.setattr("claude_code_sdk.query", fake_query)
        await mem_rt.consolidate_memory(
            conversation_text="user said hi",
            hub_knowledge=tmp_hub_with_memory,
            model="claude-haiku-4-5",
        )
        assert captured["model"] == "claude-haiku-4-5"
        assert captured["continue_conversation"] is False
        assert "user said hi" in captured["prompt"]
        assert str(tmp_hub_with_memory.resolve()) == captured["cwd"]
