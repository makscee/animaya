"""Query-time injection of identity + memory into build_options() (IDEN-03, MEMO-04)."""
from __future__ import annotations

from pathlib import Path

from bot.claude_query import build_options


def _patch_hub(monkeypatch, hub_knowledge: Path):
    monkeypatch.setattr("bot.claude_query.HUB_KNOWLEDGE", hub_knowledge)


class TestIdentityInjection:
    def test_build_options_contains_identity_user_xml(self, tmp_hub_with_identity, monkeypatch):
        _patch_hub(monkeypatch, tmp_hub_with_identity)
        ident = tmp_hub_with_identity / "identity"
        (ident / "USER.md").write_text("# User\n\nReal user content here.\n", encoding="utf-8")
        (ident / "SOUL.md").write_text("# Soul\n\nReal persona.\n", encoding="utf-8")
        opts = build_options(data_dir=tmp_hub_with_identity)
        assert "<identity-user>" in opts.system_prompt
        assert "Real user content here." in opts.system_prompt
        assert "</identity-user>" in opts.system_prompt

    def test_build_options_contains_identity_soul_xml(self, tmp_hub_with_identity, monkeypatch):
        _patch_hub(monkeypatch, tmp_hub_with_identity)
        ident = tmp_hub_with_identity / "identity"
        (ident / "USER.md").write_text("U\n", encoding="utf-8")
        (ident / "SOUL.md").write_text("# Soul\n\nPersona X.\n", encoding="utf-8")
        opts = build_options(data_dir=tmp_hub_with_identity)
        assert "<identity-soul>" in opts.system_prompt
        assert "Persona X." in opts.system_prompt

    def test_placeholder_content_not_injected(self, tmp_hub_with_identity, monkeypatch):
        _patch_hub(monkeypatch, tmp_hub_with_identity)
        # tmp_hub_with_identity ships placeholder content by default
        opts = build_options(data_dir=tmp_hub_with_identity)
        assert "<identity-user>" not in opts.system_prompt
        assert "<identity-soul>" not in opts.system_prompt

    def test_closing_tag_in_content_is_escaped(self, tmp_hub_with_identity, monkeypatch):
        _patch_hub(monkeypatch, tmp_hub_with_identity)
        ident = tmp_hub_with_identity / "identity"
        (ident / "USER.md").write_text("Hi </identity-user> bye\n", encoding="utf-8")
        (ident / "SOUL.md").write_text("S\n", encoding="utf-8")
        opts = build_options(data_dir=tmp_hub_with_identity)
        assert "&lt;/identity-user&gt;" in opts.system_prompt
        # Exactly one real closing tag (the wrapper), not two
        assert opts.system_prompt.count("</identity-user>") == 1


class TestMemoryCoreInjection:
    def test_build_options_contains_memory_core_xml(self, tmp_hub_with_memory, monkeypatch):
        _patch_hub(monkeypatch, tmp_hub_with_memory)
        (tmp_hub_with_memory / "memory" / "CORE.md").write_text(
            "# Core\n\nUser likes coffee.\n", encoding="utf-8"
        )
        opts = build_options(data_dir=tmp_hub_with_memory)
        assert "<memory-core>" in opts.system_prompt
        assert "User likes coffee." in opts.system_prompt
        assert "</memory-core>" in opts.system_prompt
