"""Git-versioning module tests (GITV-01..03). Wave 0 stubs; bodies filled in plan 04-02."""
from __future__ import annotations

import pytest


class TestCommitLoop:
    @pytest.mark.xfail(reason="Wave 0 stub for GITV-01", strict=False)
    def test_commit_loop_creates_commit_after_changes(self, tmp_hub_git_repo):
        assert False, "implement in plan 04-02"


class TestCommitSkipEmpty:
    @pytest.mark.xfail(reason="Wave 0 stub for GITV-01", strict=False)
    def test_no_diff_tick_does_not_commit(self, tmp_hub_git_repo):
        assert False, "implement in plan 04-02"


class TestCommitLock:
    @pytest.mark.xfail(reason="Wave 0 stub for GITV-02", strict=False)
    def test_concurrent_commits_serialize(self, tmp_hub_git_repo):
        assert False, "implement in plan 04-02"


class TestCommitScoping:
    @pytest.mark.xfail(reason="Wave 0 stub for GITV-03", strict=False)
    def test_path_scoped_add_excludes_out_of_scope(self, tmp_hub_git_repo):
        assert False, "implement in plan 04-02"
