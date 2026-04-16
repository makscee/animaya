"""Tests for BOOTSTRAP.md injection into system prompt and continue_conversation flag.

Test 1: When BOOTSTRAP.md exists at repo root, build_options() injects its
        content wrapped in <bootstrap>...</bootstrap> into system_prompt.
Test 2: When BOOTSTRAP.md is absent (or empty), build_options() emits no
        <bootstrap> tag in system_prompt.
Test 5: When BOOTSTRAP.md exists (non-empty), build_options() returns
        continue_conversation=False (fresh SDK session).
Test 6: When BOOTSTRAP.md is absent, build_options() returns
        continue_conversation=True (normal resume).
Test 7: When BOOTSTRAP.md exists but is empty, build_options() returns
        continue_conversation=True (matches no-injection semantics).

Locale substitution tests (Task 1 additions):
- en/ru substitution, None→en fallback, unknown→en fallback, absent BOOTSTRAP.md is noop,
  literal braces (non-placeholder) pass through without KeyError.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import bot.claude_query as cq

# ── Helpers ──────────────────────────────────────────────────────────

_BOOTSTRAP_WITH_PLACEHOLDERS = (
    "# Bootstrap\n\n"
    "You speak in **{locale}**.\n\n"
    "{locale_example}\n\n"
    "Some other text."
)


def _system_prompt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, locale: str | None = None
) -> str:
    """Build options with REPO_ROOT monkeypatched to tmp_path, return system_prompt."""
    monkeypatch.setattr(cq, "REPO_ROOT", tmp_path)
    # Also patch HUB_KNOWLEDGE to an empty dir so identity files don't bleed in
    monkeypatch.setattr(cq, "HUB_KNOWLEDGE", tmp_path / "hub" / "knowledge")
    # Patch DATA_PATH env to something that won't load a real config.json
    monkeypatch.setenv("DATA_PATH", str(tmp_path / "data"))
    opts = cq.build_options(locale=locale)
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


# ── Helpers for continue_conversation tests ──────────────────────────


def _options(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, locale: str | None = None):
    """Build options with REPO_ROOT monkeypatched to tmp_path, return full ClaudeCodeOptions."""
    monkeypatch.setattr(cq, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(cq, "HUB_KNOWLEDGE", tmp_path / "hub" / "knowledge")
    monkeypatch.setenv("DATA_PATH", str(tmp_path / "data"))
    return cq.build_options(locale=locale)


# ── continue_conversation tests ───────────────────────────────────────


def test_continue_conversation_false_when_bootstrap_present(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When BOOTSTRAP.md exists with content, continue_conversation must be False."""
    (tmp_path / "BOOTSTRAP.md").write_text("# Bootstrap\n\nSome content.\n", encoding="utf-8")

    opts = _options(tmp_path, monkeypatch)

    assert opts.continue_conversation is False, (
        "Expected continue_conversation=False when BOOTSTRAP.md is present and non-empty"
    )


def test_continue_conversation_true_when_bootstrap_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When BOOTSTRAP.md does not exist, continue_conversation must be True."""
    assert not (tmp_path / "BOOTSTRAP.md").exists()

    opts = _options(tmp_path, monkeypatch)

    assert opts.continue_conversation is True, (
        "Expected continue_conversation=True when BOOTSTRAP.md is absent"
    )


def test_continue_conversation_true_when_bootstrap_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When BOOTSTRAP.md exists but is empty, continue_conversation must be True."""
    (tmp_path / "BOOTSTRAP.md").write_text("", encoding="utf-8")

    opts = _options(tmp_path, monkeypatch)

    assert opts.continue_conversation is True, (
        "Expected continue_conversation=True when BOOTSTRAP.md is empty (no-injection semantics)"
    )


# ── Locale substitution tests ─────────────────────────────────────────


def test_bootstrap_locale_en_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_options(locale='en') substitutes {locale} with English and includes EN example."""
    (tmp_path / "BOOTSTRAP.md").write_text(_BOOTSTRAP_WITH_PLACEHOLDERS, encoding="utf-8")
    prompt = _system_prompt(tmp_path, monkeypatch, locale="en")
    assert "English" in prompt, "Expected 'English' in system_prompt for locale='en'"
    assert "Tell me" in prompt and "who are you?" in prompt, (
        "Expected EN opener example in system_prompt"
    )
    assert "{locale}" not in prompt, "Raw {locale} placeholder must not appear in output"


def test_bootstrap_locale_ru_substitution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_options(locale='ru') substitutes {locale} with русском and includes RU example."""
    (tmp_path / "BOOTSTRAP.md").write_text(_BOOTSTRAP_WITH_PLACEHOLDERS, encoding="utf-8")
    prompt = _system_prompt(tmp_path, monkeypatch, locale="ru")
    assert "русском" in prompt, "Expected 'русском' in system_prompt for locale='ru'"
    assert "Расскажи" in prompt and "кто ты?" in prompt, (
        "Expected RU opener example in system_prompt"
    )
    assert "{locale}" not in prompt, "Raw {locale} placeholder must not appear in output"


def test_bootstrap_locale_none_defaults_to_en(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_options(locale=None) falls back to English substitution, no raw {locale} left."""
    (tmp_path / "BOOTSTRAP.md").write_text(_BOOTSTRAP_WITH_PLACEHOLDERS, encoding="utf-8")
    prompt = _system_prompt(tmp_path, monkeypatch, locale=None)
    assert "English" in prompt, "Expected English fallback for locale=None"
    assert "{locale}" not in prompt, "Raw {locale} must not appear when locale=None"


def test_bootstrap_locale_unknown_defaults_to_en(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """build_options(locale='fr') falls back to English, no raw {locale} leakage."""
    (tmp_path / "BOOTSTRAP.md").write_text(_BOOTSTRAP_WITH_PLACEHOLDERS, encoding="utf-8")
    prompt = _system_prompt(tmp_path, monkeypatch, locale="fr")
    assert "English" in prompt, "Expected English fallback for unknown locale 'fr'"
    assert "{locale}" not in prompt, "Raw {locale} must not appear for unknown locale"


def test_bootstrap_absent_locale_is_noop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When BOOTSTRAP.md is absent, build_options(locale='ru') does not crash and no <bootstrap>."""
    assert not (tmp_path / "BOOTSTRAP.md").exists()
    prompt = _system_prompt(tmp_path, monkeypatch, locale="ru")
    assert "<bootstrap>" not in prompt, "No <bootstrap> tag when BOOTSTRAP.md is absent"


def test_bootstrap_brace_preservation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Literal {foo} braces in BOOTSTRAP.md must pass through unchanged without KeyError."""
    content = "# Bootstrap\n\n{locale} is set. Also: {foo} stays.\n\n{locale_example}"
    (tmp_path / "BOOTSTRAP.md").write_text(content, encoding="utf-8")
    # Should not raise KeyError
    prompt = _system_prompt(tmp_path, monkeypatch, locale="en")
    assert "{foo}" in prompt, "Non-placeholder brace {foo} must survive substitution"
    assert "{locale}" not in prompt, "Known placeholder {locale} must be replaced"
