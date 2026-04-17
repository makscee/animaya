"""Tests for bot.engine.modules_forms — schema-driven form rendering + persist.

HTTP endpoint coverage lives in Playwright (dashboard/tests/e2e/). These
tests cover pure business logic: render_fields / coerce / validate /
save_config. Migrated from tests/dashboard/test_config_form.py during
Phase 13 Wave 5 cutover (D-08 big-bang).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


# ── Test fixtures: module dir + schema-aware seeding ─────────────────
def _seed_module_with_schema(
    modules_root: Path,
    name: str,
    config_schema: dict | None,
) -> Path:
    """Create a minimal module folder with a configurable manifest."""
    mdir = modules_root / name
    mdir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "manifest_version": 1,
        "name": name,
        "version": "0.1.0",
        "system_prompt_path": "prompt.md",
        "owned_paths": [],
        "scripts": {"install": "install.sh", "uninstall": "uninstall.sh"},
        "depends": [],
        "config_schema": config_schema,
    }
    (mdir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    install_sh = mdir / "install.sh"
    install_sh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    install_sh.chmod(0o755)
    uninstall_sh = mdir / "uninstall.sh"
    uninstall_sh.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    uninstall_sh.chmod(0o755)
    (mdir / "prompt.md").write_text(f"{name} prompt\n", encoding="utf-8")
    return mdir


DEMO_SCHEMA = {
    "type": "object",
    "required": ["name"],
    "properties": {
        "name": {"type": "string", "title": "Name", "minLength": 1, "maxLength": 20},
        "count": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
        "enabled": {"type": "boolean", "default": True},
        "mode": {"type": "string", "enum": ["a", "b", "c"], "default": "a"},
    },
}


@pytest.fixture
def modules_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "modules"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ANIMAYA_MODULES_DIR", str(root))
    return root


@pytest.fixture
def temp_hub_dir(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    hub.mkdir(parents=True, exist_ok=True)
    return hub


# ────────────────────────────────────────────────────────────────────
# Unit tests: render_fields
# ────────────────────────────────────────────────────────────────────

def test_render_fields_string():
    from bot.engine.modules_forms import render_fields
    schema = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "title": "Name",
                "default": "x",
                "minLength": 1,
                "maxLength": 20,
            },
        },
    }
    fields = render_fields(schema)
    assert len(fields) == 1
    f = fields[0]
    assert f["kind"] == "string"
    assert f["label"] == "Name"
    assert f["value"] == "x"
    assert f["min_length"] == 1
    assert f["max_length"] == 20


def test_render_fields_string_with_enum():
    from bot.engine.modules_forms import render_fields
    schema = {
        "type": "object",
        "properties": {"mode": {"type": "string", "enum": ["a", "b", "c"]}},
    }
    fields = render_fields(schema)
    assert fields[0]["kind"] == "select"
    assert fields[0]["enum"] == ["a", "b", "c"]


def test_render_fields_integer_uses_min_max():
    from bot.engine.modules_forms import render_fields
    schema = {
        "type": "object",
        "properties": {
            "count": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
    }
    f = render_fields(schema)[0]
    assert f["kind"] == "integer"
    assert f["min"] == 1
    assert f["max"] == 10
    assert f["value"] == 5


def test_render_fields_number():
    from bot.engine.modules_forms import render_fields
    schema = {"type": "object", "properties": {"ratio": {"type": "number"}}}
    assert render_fields(schema)[0]["kind"] == "number"


def test_render_fields_boolean():
    from bot.engine.modules_forms import render_fields
    schema = {
        "type": "object",
        "properties": {"enabled": {"type": "boolean", "default": True}},
    }
    f = render_fields(schema)[0]
    assert f["kind"] == "boolean"
    assert f["value"] is True


def test_render_fields_unsupported_object():
    from bot.engine.modules_forms import render_fields
    schema = {"type": "object", "properties": {"nested": {"type": "object"}}}
    f = render_fields(schema)[0]
    assert f["kind"] == "unsupported"
    assert f["notice"]
    assert "nested" in f["notice"]


def test_render_fields_unsupported_array():
    from bot.engine.modules_forms import render_fields
    schema = {"type": "object", "properties": {"items": {"type": "array"}}}
    f = render_fields(schema)[0]
    assert f["kind"] == "unsupported"


def test_render_fields_uses_current_over_default():
    from bot.engine.modules_forms import render_fields
    schema = {
        "type": "object",
        "properties": {"name": {"type": "string", "default": "x"}},
    }
    f = render_fields(schema, current={"name": "y"})[0]
    assert f["value"] == "y"


# ────────────────────────────────────────────────────────────────────
# Unit tests: coerce
# ────────────────────────────────────────────────────────────────────

def test_coerce_integer_from_string():
    from bot.engine.modules_forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    payload, errors = coerce({"age": "42"}, schema)
    assert payload == {"age": 42}
    assert errors == {}


def test_coerce_integer_empty_string_removes_key():
    from bot.engine.modules_forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    payload, errors = coerce({"age": ""}, schema)
    assert "age" not in payload
    assert errors == {}


def test_coerce_boolean_missing_is_false():
    from bot.engine.modules_forms import coerce
    schema = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}
    payload, _ = coerce({}, schema)
    assert payload == {"enabled": False}


def test_coerce_boolean_present_is_true():
    from bot.engine.modules_forms import coerce
    schema = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}
    payload, _ = coerce({"enabled": "on"}, schema)
    assert payload == {"enabled": True}


def test_coerce_integer_non_numeric_sets_error():
    from bot.engine.modules_forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    _, errors = coerce({"age": "abc"}, schema)
    assert "age" in errors


# ────────────────────────────────────────────────────────────────────
# Unit tests: validate
# ────────────────────────────────────────────────────────────────────

def test_validate_happy_path():
    from bot.engine.modules_forms import validate
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 10}},
    }
    assert validate({"count": 5}, schema) == {}


def test_validate_returns_field_errors():
    from bot.engine.modules_forms import validate
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 10}},
    }
    errors = validate({"count": 99}, schema)
    assert "count" in errors


def test_validate_missing_required_field():
    from bot.engine.modules_forms import validate
    schema = {
        "type": "object",
        "required": ["x"],
        "properties": {"x": {"type": "string"}},
    }
    errors = validate({}, schema)
    assert "x" in errors


# ────────────────────────────────────────────────────────────────────
# Integration test: save_config
# ────────────────────────────────────────────────────────────────────

def test_save_config_writes_registry_and_assembler(
    temp_hub_dir: Path, modules_root: Path, monkeypatch: pytest.MonkeyPatch,
):
    from bot.engine import modules_forms as forms
    from bot.modules import get_entry
    from bot.modules import install as module_install

    _seed_module_with_schema(modules_root, "demo", DEMO_SCHEMA)
    module_install(modules_root / "demo", temp_hub_dir)

    called: list[Path] = []

    def fake_assemble(hub_dir: Path) -> str:
        called.append(hub_dir)
        return "ok"

    monkeypatch.setattr(forms, "assemble_claude_md", fake_assemble)

    forms.save_config(
        temp_hub_dir,
        "demo",
        {"name": "abc", "count": 7, "enabled": False, "mode": "b"},
    )

    entry = get_entry(temp_hub_dir, "demo")
    assert entry is not None
    assert entry["config"] == {
        "name": "abc", "count": 7, "enabled": False, "mode": "b",
    }
    assert called == [temp_hub_dir]
