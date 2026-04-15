"""Git-versioning module tests (GITV-01..03)."""
from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from bot.modules_runtime.git_versioning import _COMMIT_LOCK, commit_if_changed


def _git_log_count(repo: Path) -> int:
    r = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(r.stdout.strip())


def _last_commit_msg(repo: Path) -> str:
    r = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--pretty=%s"],
        capture_output=True,
        text=True,
        check=True,
    )
    return r.stdout.strip()


class TestCommitLoop:
    @pytest.mark.asyncio
    async def test_commit_loop_creates_commit_after_changes(self, tmp_hub_git_repo):
        before = _git_log_count(tmp_hub_git_repo)
        (tmp_hub_git_repo / "knowledge" / "test.md").write_text("hello\n")
        made = await commit_if_changed(tmp_hub_git_repo)
        assert made is True
        after = _git_log_count(tmp_hub_git_repo)
        assert after == before + 1
        assert _last_commit_msg(tmp_hub_git_repo).startswith("animaya: auto-commit ")


class TestCommitSkipEmpty:
    @pytest.mark.asyncio
    async def test_no_diff_tick_does_not_commit(self, tmp_hub_git_repo):
        before = _git_log_count(tmp_hub_git_repo)
        made = await commit_if_changed(tmp_hub_git_repo)
        assert made is False
        assert _git_log_count(tmp_hub_git_repo) == before


class TestCommitLock:
    @pytest.mark.asyncio
    async def test_concurrent_commits_serialize(self, tmp_hub_git_repo):
        (tmp_hub_git_repo / "knowledge" / "a.md").write_text("a\n")
        t1 = asyncio.create_task(commit_if_changed(tmp_hub_git_repo))
        t2 = asyncio.create_task(commit_if_changed(tmp_hub_git_repo))
        r1, r2 = await asyncio.gather(t1, t2)
        # Exactly one of them committed (the other saw no diff after the first finished)
        assert sum([r1, r2]) == 1
        # Lock is released after both finish
        assert not _COMMIT_LOCK.locked()


class TestCommitScoping:
    @pytest.mark.asyncio
    async def test_path_scoped_add_excludes_out_of_scope(self, tmp_hub_git_repo):
        (tmp_hub_git_repo / "knowledge" / "foo.md").write_text("foo\n")
        (tmp_hub_git_repo / "unrelated.txt").write_text("unrelated\n")
        made = await commit_if_changed(tmp_hub_git_repo)
        assert made is True
        # unrelated.txt is still untracked (path-scoped add did not pick it up)
        r = subprocess.run(
            [
                "git",
                "-C",
                str(tmp_hub_git_repo),
                "ls-files",
                "--others",
                "--exclude-standard",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        assert "unrelated.txt" in r.stdout
        assert "knowledge/foo.md" not in r.stdout
