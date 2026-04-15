"""Identity module tests (IDEN-01..04). Wave 0 stubs; bodies filled in plan 04-01."""
from __future__ import annotations

import pytest


class TestIdentityInstall:
    @pytest.mark.xfail(reason="Wave 0 stub for IDEN-02", strict=False)
    def test_install_creates_user_soul_sentinel(self, tmp_hub_dir):
        assert False, "implement in plan 04-01"


class TestIdentityOnboarding:
    @pytest.mark.xfail(reason="Wave 0 stub for IDEN-01", strict=False)
    def test_sentinel_present_after_install_cleared_after_qa(self, tmp_hub_with_identity):
        assert False, "implement in plan 04-01"


class TestIdentityReconfigure:
    @pytest.mark.xfail(reason="Wave 0 stub for IDEN-04", strict=False)
    def test_identity_command_reruns_onboarding(self, tmp_hub_with_identity):
        assert False, "implement in plan 04-01"
