"""i18n substrate for animaya bot.

Loads `en.json` and `ru.json` flat key/value dictionaries at import time.
Exposes:
    t(key, lang, **vars) -> str
        Lookup `key` in the dict for `lang` (falls back to `en`, then to the
        key itself). Substitutes ``{var}`` placeholders from kwargs.

    ru_pluralize(n, one, few, many) -> str
        Standard Russian plural rule (one / few / many) with the usual
        teen / unit edge cases.

Design ref: docs/superpowers/specs/2026-04-26-i18n-substrate-design.md
Substrate seed scope (D4): the bot `/start` greeting only — broader corpus
lands in ANI_VDN-3.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

__all__ = ["t", "ru_pluralize", "Lang", "DICTS"]

# Lang is a string alias for now — voidnet Rust owns the enum; bot just needs
# the wire string ("en" / "ru"). Upgrade to Enum if/when the bot grows its own
# typed Lang representation.
Lang = str

_I18N_DIR = Path(__file__).parent


def _load(lang: str) -> dict[str, str]:
    path = _I18N_DIR / f"{lang}.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


DICTS: dict[str, dict[str, str]] = {
    "en": _load("en"),
    "ru": _load("ru"),
}

_FALLBACK_LANG = "en"


def _normalize_lang(lang: Any) -> str:
    """Coerce Lang representation (str/enum-like) to a dict key."""
    if lang is None:
        return _FALLBACK_LANG
    # Enum-like with .value
    val = getattr(lang, "value", None)
    if isinstance(val, str):
        return val.lower()
    if isinstance(lang, str):
        return lang.lower()
    # Last resort: stringify
    return str(lang).lower()


def t(key: str, lang: Lang | str, **vars: Any) -> str:
    """Look up `key` in the `lang` dict; substitute ``{var}`` from kwargs.

    Resolution:
        1. dict[lang][key]
        2. dict['en'][key]  (fallback locale)
        3. key              (missing-key fallback — never raises)

    Variable substitution uses ``str.format_map`` so a missing variable
    leaves the placeholder untouched rather than raising ``KeyError``.
    """
    norm = _normalize_lang(lang)
    dct = DICTS.get(norm) or DICTS.get(_FALLBACK_LANG, {})
    template = dct.get(key)
    if template is None:
        # Try fallback locale before giving up
        template = DICTS.get(_FALLBACK_LANG, {}).get(key)
    if template is None:
        return key
    if not vars:
        return template
    try:
        return template.format_map(_SafeDict(vars))
    except (IndexError, ValueError):
        # Malformed template — return raw string rather than crash a reply.
        return template


class _SafeDict(dict):
    """``dict`` subclass that returns ``{key}`` for missing format keys."""

    def __init__(self, mapping: Mapping[str, Any]):
        super().__init__(mapping)

    def __missing__(self, key: str) -> str:  # type: ignore[override]
        return "{" + key + "}"


def ru_pluralize(n: int, one: str, few: str, many: str) -> str:
    """Pick the Russian plural form for integer `n`.

    Buckets (per the standard Slavic / CLDR rule for Russian):
        - **one**  : n % 10 == 1 and n % 100 != 11
                     (e.g. 1, 21, 31, 101, 121)
        - **few**  : n % 10 in {2, 3, 4} and n % 100 not in {12, 13, 14}
                     (e.g. 2, 3, 4, 22, 23, 24, 102)
        - **many** : everything else
                     (e.g. 0, 5..20, 25..30, 100, 111, 112, 1000)
    """
    n = abs(int(n))
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return one
    if 2 <= mod10 <= 4 and not (12 <= mod100 <= 14):
        return few
    return many
