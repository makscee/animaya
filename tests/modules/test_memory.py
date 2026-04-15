"""Memory module tests (MEMO-01..04). Wave 0 stubs; bodies filled in plan 04-03."""
from __future__ import annotations

import pytest


class TestMemoryInstall:
    @pytest.mark.xfail(reason="Wave 0 stub for MEMO-01", strict=False)
    def test_install_creates_memory_dir_with_core_md(self, tmp_hub_dir):
        assert False, "implement in plan 04-03"


class TestMemoryPersist:
    @pytest.mark.xfail(reason="Wave 0 stub for MEMO-01", strict=False)
    def test_write_to_memory_facts_persists(self, tmp_hub_with_memory):
        assert False, "implement in plan 04-03"


class TestMemoryGitCommit:
    @pytest.mark.xfail(reason="Wave 0 stub for MEMO-02", strict=False)
    def test_memory_write_followed_by_commit_tick(self, tmp_hub_git_repo):
        assert False, "implement in plan 04-03"


class TestConsolidation:
    @pytest.mark.xfail(reason="Wave 0 stub for MEMO-03", strict=False)
    def test_consolidate_runs_with_haiku_model(self, tmp_hub_with_memory, fake_claude_query):
        assert False, "implement in plan 04-03"
