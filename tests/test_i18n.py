"""Tests for bot.i18n: t() lookup + var substitution + ru_pluralize.

Subtask: ANI_VDN-2 T9 (i18n substrate seed for animaya bot).
"""

from __future__ import annotations

import pytest

from bot.i18n import DICTS, ru_pluralize, t


# ── t() lookup ──────────────────────────────────────────────────────


def test_t_lookup_en_returns_english_string():
    out = t("start.greeting", "en", name="Maks")
    assert "Hello" in out
    assert "Maks" in out


def test_t_lookup_ru_returns_russian_string():
    out = t("start.greeting", "ru", name="Макс")
    assert "Привет" in out
    assert "Макс" in out


def test_t_var_substitution_replaces_braced_placeholders():
    # Inject a temp key so the test doesn't hard-code real seed wording.
    DICTS["en"]["__test.hello"] = "Hi {who}, you have {n} new items."
    try:
        out = t("__test.hello", "en", who="Maks", n=3)
        assert out == "Hi Maks, you have 3 new items."
    finally:
        del DICTS["en"]["__test.hello"]


def test_t_missing_var_leaves_placeholder_untouched():
    DICTS["en"]["__test.partial"] = "Hello {who}, count={n}."
    try:
        out = t("__test.partial", "en", who="Maks")
        assert out == "Hello Maks, count={n}."
    finally:
        del DICTS["en"]["__test.partial"]


def test_t_missing_key_returns_key_itself():
    out = t("definitely.not.a.real.key", "en")
    assert out == "definitely.not.a.real.key"


def test_t_missing_key_with_vars_still_returns_key():
    out = t("definitely.not.a.real.key", "ru", name="X")
    assert out == "definitely.not.a.real.key"


def test_t_unknown_lang_falls_back_to_en():
    out = t("start.greeting", "fr", name="Maks")
    # Falls back to en bucket — should contain the English greeting.
    assert "Hello" in out
    assert "Maks" in out


def test_t_lang_none_falls_back_to_en():
    out = t("start.greeting", None, name="Maks")  # type: ignore[arg-type]
    assert "Hello" in out


def test_t_uppercase_lang_normalized():
    out = t("start.greeting", "RU", name="Макс")
    assert "Привет" in out


# ── ru_pluralize ────────────────────────────────────────────────────

# Standard form set for "сообщение" (message) — picked because the three
# forms are short and visibly distinct.
ONE = "сообщение"  # one
FEW = "сообщения"  # few
MANY = "сообщений"  # many


@pytest.mark.parametrize(
    "n, expected",
    [
        (0, MANY),
        (1, ONE),
        (2, FEW),
        (3, FEW),
        (4, FEW),
        (5, MANY),
        (6, MANY),
        (10, MANY),
        (11, MANY),  # teen → many (NOT one)
        (12, MANY),  # teen → many (NOT few)
        (13, MANY),
        (14, MANY),
        (15, MANY),
        (20, MANY),
        (21, ONE),  # ends in 1, not teen → one
        (22, FEW),
        (23, FEW),
        (24, FEW),
        (25, MANY),
        (100, MANY),
        (101, ONE),
        (102, FEW),
        (104, FEW),
        (111, MANY),  # 111 % 100 == 11 → many
        (112, MANY),
        (114, MANY),
        (121, ONE),
        (122, FEW),
        (1000, MANY),
        (1001, ONE),
        (1011, MANY),
        (1021, ONE),
    ],
)
def test_ru_pluralize_buckets(n: int, expected: str):
    assert ru_pluralize(n, ONE, FEW, MANY) == expected


def test_ru_pluralize_handles_negative_via_abs():
    # Negative counts are unusual but must not crash; bucket on |n|.
    assert ru_pluralize(-1, ONE, FEW, MANY) == ONE
    assert ru_pluralize(-2, ONE, FEW, MANY) == FEW
    assert ru_pluralize(-11, ONE, FEW, MANY) == MANY


def test_ru_pluralize_accepts_int_like():
    # bool is a subclass of int — should still work.
    assert ru_pluralize(True, ONE, FEW, MANY) == ONE
    assert ru_pluralize(False, ONE, FEW, MANY) == MANY
