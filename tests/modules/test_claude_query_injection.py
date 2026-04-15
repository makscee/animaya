"""Query-time injection of identity + memory into build_options() (IDEN-03, MEMO-04)."""
from __future__ import annotations

import pytest


class TestIdentityInjection:
    @pytest.mark.xfail(reason="Wave 0 stub for IDEN-03", strict=False)
    def test_build_options_contains_identity_user_xml(self, tmp_hub_with_identity, monkeypatch):
        assert False, "implement in plan 04-01"

    @pytest.mark.xfail(reason="Wave 0 stub for IDEN-03", strict=False)
    def test_build_options_contains_identity_soul_xml(self, tmp_hub_with_identity, monkeypatch):
        assert False, "implement in plan 04-01"


class TestMemoryCoreInjection:
    @pytest.mark.xfail(reason="Wave 0 stub for MEMO-04", strict=False)
    def test_build_options_contains_memory_core_xml(self, tmp_hub_with_memory, monkeypatch):
        assert False, "implement in plan 04-03"
