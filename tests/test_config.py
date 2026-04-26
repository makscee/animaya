"""Tests for ``bot.config.i18n_enabled``."""

from __future__ import annotations

import pytest

from bot.config import i18n_enabled

ENV = "I18N_SUBSTRATE_V1"


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    monkeypatch.delenv(ENV, raising=False)
    return monkeypatch


def test_defaults_true_when_unset(clean_env: pytest.MonkeyPatch) -> None:
    assert i18n_enabled() is True


def test_true_when_one(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(ENV, "1")
    assert i18n_enabled() is True


def test_true_when_true(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(ENV, "true")
    assert i18n_enabled() is True


def test_false_when_zero(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(ENV, "0")
    assert i18n_enabled() is False


def test_false_when_false_lowercase(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(ENV, "false")
    assert i18n_enabled() is False


def test_false_when_false_uppercase(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv(ENV, "FALSE")
    assert i18n_enabled() is False


def test_defaults_true_for_unknown_value(clean_env: pytest.MonkeyPatch) -> None:
    # Fail-open: unknown values keep the substrate on.
    clean_env.setenv(ENV, "maybe")
    assert i18n_enabled() is True
