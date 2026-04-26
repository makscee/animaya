"""Runtime configuration helpers for animaya bot.

Centralises env-driven feature gates so callers do not sprinkle
`os.environ.get(...)` checks across the codebase. Helpers are pure (no
caching) so tests can flip env values between calls.
"""

from __future__ import annotations

import os

__all__ = ["i18n_enabled"]

_I18N_FLAG_ENV = "I18N_SUBSTRATE_V1"
_OFF_VALUES = frozenset({"0", "false", "FALSE"})


def i18n_enabled() -> bool:
    """Return ``True`` when the i18n substrate (ANI_VDN-2) is active.

    Reads ``I18N_SUBSTRATE_V1``. Defaults to ``True`` when unset; treats
    ``"0"``, ``"false"``, and ``"FALSE"`` as off. Any other value (including
    unknown) keeps the flag enabled (fail-open).

    Mirrors :func:`voidnet_common::feature_flags::i18n_enabled` on the Rust
    side so both processes flip together when the env var is set in the
    shared deploy environment.
    """
    value = os.environ.get(_I18N_FLAG_ENV)
    if value is None:
        return True
    return value not in _OFF_VALUES
