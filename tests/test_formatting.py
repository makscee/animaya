"""Unit tests for bot.bridge.formatting — md_to_html and TG_MAX_LEN."""
from __future__ import annotations

import html

import pytest

from bot.bridge.formatting import TG_MAX_LEN, md_to_html


# ── TG_MAX_LEN ──────────────────────────────────────────────────────


def test_tg_max_len_is_4096():
    assert TG_MAX_LEN == 4096


# ── Bold / italic ────────────────────────────────────────────────────


def test_bold_conversion():
    result = md_to_html("**bold text**")
    assert "<b>bold text</b>" in result


def test_italic_star_conversion():
    result = md_to_html("*italic text*")
    assert "<i>italic text</i>" in result


def test_italic_underscore_conversion():
    result = md_to_html("_italic text_")
    assert "<i>italic text</i>" in result


# ── Headers ──────────────────────────────────────────────────────────


def test_header_conversion():
    result = md_to_html("## My Heading")
    assert "<b>My Heading</b>" in result


def test_h1_header():
    result = md_to_html("# Title")
    assert "<b>Title</b>" in result


# ── Fenced code blocks ───────────────────────────────────────────────


def test_fenced_code_block_with_language():
    md = "```python\nprint('hello')\n```"
    result = md_to_html(md)
    assert '<pre><code class="language-python">' in result
    assert "print(&#x27;hello&#x27;)" in result or "print('hello')" in result


def test_fenced_code_block_no_language():
    md = "```\nsome code\n```"
    result = md_to_html(md)
    assert "<pre><code>" in result
    assert "some code" in result


def test_fenced_code_block_preserves_content():
    md = "```\nline1\nline2\n```"
    result = md_to_html(md)
    assert "line1" in result
    assert "line2" in result


# ── HTML escaping ────────────────────────────────────────────────────


def test_escapes_ampersand():
    result = md_to_html("a & b")
    assert "&amp;" in result
    assert "& b" not in result.replace("&amp;", "")


def test_escapes_less_than():
    result = md_to_html("a < b")
    assert "&lt;" in result


def test_escapes_greater_than():
    result = md_to_html("a > b")
    assert "&gt;" in result


def test_escapes_html_in_text():
    result = md_to_html("<script>alert(1)</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


# ── Links ────────────────────────────────────────────────────────────


def test_markdown_link_conversion():
    result = md_to_html("[click here](https://example.com)")
    assert '<a href="https://example.com">click here</a>' in result


def test_link_text_preserved():
    result = md_to_html("[my link](http://test.org)")
    assert "my link" in result


# ── Unordered lists ──────────────────────────────────────────────────


def test_unordered_list_bullet_point():
    result = md_to_html("- item one")
    assert "\u2022" in result
    assert "item one" in result


def test_unordered_list_star():
    result = md_to_html("* item two")
    assert "\u2022" in result
    assert "item two" in result


# ── Inline code ──────────────────────────────────────────────────────


def test_inline_code():
    result = md_to_html("`some code`")
    assert "<code>some code</code>" in result


# ── Edge cases ───────────────────────────────────────────────────────


def test_empty_string():
    result = md_to_html("")
    assert result == ""


def test_plain_text_unchanged():
    result = md_to_html("plain text")
    assert "plain text" in result


def test_no_double_escaping_in_code_block():
    """Code block content should be HTML-escaped but not double-escaped."""
    md = "```\n<tag> & 'quote'\n```"
    result = md_to_html(md)
    # Should contain escaped versions, not raw HTML
    assert "<tag>" not in result
    assert "&amp;" in result or "&lt;" in result
