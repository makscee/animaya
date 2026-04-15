"""Tests for auto-generated module config forms (Plan 05-06, DASH-06)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

import pytest

from tests.dashboard._helpers import build_client, make_session_cookie


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
def auth_client(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
    modules_root: Path,  # noqa: ARG001
) -> Iterator:
    """TestClient with a pre-seeded owner session cookie."""
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        tc.cookies.set("animaya_session", make_session_cookie(owner_id))
        yield tc


# ────────────────────────────────────────────────────────────────────
# Unit tests: render_fields
# ────────────────────────────────────────────────────────────────────

def test_render_fields_string():
    from bot.dashboard.forms import render_fields
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
    from bot.dashboard.forms import render_fields
    schema = {
        "type": "object",
        "properties": {"mode": {"type": "string", "enum": ["a", "b", "c"]}},
    }
    fields = render_fields(schema)
    assert fields[0]["kind"] == "select"
    assert fields[0]["enum"] == ["a", "b", "c"]


def test_render_fields_integer_uses_min_max():
    from bot.dashboard.forms import render_fields
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
    from bot.dashboard.forms import render_fields
    schema = {"type": "object", "properties": {"ratio": {"type": "number"}}}
    assert render_fields(schema)[0]["kind"] == "number"


def test_render_fields_boolean():
    from bot.dashboard.forms import render_fields
    schema = {
        "type": "object",
        "properties": {"enabled": {"type": "boolean", "default": True}},
    }
    f = render_fields(schema)[0]
    assert f["kind"] == "boolean"
    assert f["value"] is True


def test_render_fields_unsupported_object():
    from bot.dashboard.forms import render_fields
    schema = {"type": "object", "properties": {"nested": {"type": "object"}}}
    f = render_fields(schema)[0]
    assert f["kind"] == "unsupported"
    assert f["notice"]
    assert "nested" in f["notice"]


def test_render_fields_unsupported_array():
    from bot.dashboard.forms import render_fields
    schema = {"type": "object", "properties": {"items": {"type": "array"}}}
    f = render_fields(schema)[0]
    assert f["kind"] == "unsupported"


def test_render_fields_uses_current_over_default():
    from bot.dashboard.forms import render_fields
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
    from bot.dashboard.forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    payload, errors = coerce({"age": "42"}, schema)
    assert payload == {"age": 42}
    assert errors == {}


def test_coerce_integer_empty_string_removes_key():
    from bot.dashboard.forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    payload, errors = coerce({"age": ""}, schema)
    assert "age" not in payload
    assert errors == {}


def test_coerce_boolean_missing_is_false():
    from bot.dashboard.forms import coerce
    schema = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}
    payload, _ = coerce({}, schema)
    assert payload == {"enabled": False}


def test_coerce_boolean_present_is_true():
    from bot.dashboard.forms import coerce
    schema = {"type": "object", "properties": {"enabled": {"type": "boolean"}}}
    payload, _ = coerce({"enabled": "on"}, schema)
    assert payload == {"enabled": True}


def test_coerce_integer_non_numeric_sets_error():
    from bot.dashboard.forms import coerce
    schema = {"type": "object", "properties": {"age": {"type": "integer"}}}
    _, errors = coerce({"age": "abc"}, schema)
    assert "age" in errors


# ────────────────────────────────────────────────────────────────────
# Unit tests: validate
# ────────────────────────────────────────────────────────────────────

def test_validate_happy_path():
    from bot.dashboard.forms import validate
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 10}},
    }
    assert validate({"count": 5}, schema) == {}


def test_validate_returns_field_errors():
    from bot.dashboard.forms import validate
    schema = {
        "type": "object",
        "properties": {"count": {"type": "integer", "minimum": 1, "maximum": 10}},
    }
    errors = validate({"count": 99}, schema)
    assert "count" in errors


def test_validate_missing_required_field():
    from bot.dashboard.forms import validate
    schema = {
        "type": "object",
        "required": ["x"],
        "properties": {"x": {"type": "string"}},
    }
    errors = validate({}, schema)
    assert "x" in errors


# ────────────────────────────────────────────────────────────────────
# Unit test: save_config
# ────────────────────────────────────────────────────────────────────

def test_save_config_writes_registry_and_assembler(
    temp_hub_dir: Path, modules_root: Path, monkeypatch: pytest.MonkeyPatch,
):
    from bot.dashboard import forms
    from bot.modules import install as module_install
    from bot.modules import get_entry

    _seed_module_with_schema(modules_root, "demo", DEMO_SCHEMA)
    module_install(modules_root / "demo", temp_hub_dir)

    called: list[Path] = []

    def fake_assemble(hub_dir: Path) -> str:
        called.append(hub_dir)
        return "ok"

    monkeypatch.setattr(forms, "assemble_claude_md", fake_assemble)

    forms.save_config(temp_hub_dir, "demo", {"name": "abc", "count": 7, "enabled": False, "mode": "b"})

    entry = get_entry(temp_hub_dir, "demo")
    assert entry is not None
    assert entry["config"] == {
        "name": "abc", "count": 7, "enabled": False, "mode": "b",
    }
    assert called == [temp_hub_dir]


# ────────────────────────────────────────────────────────────────────
# Integration tests: HTTP endpoints
# ────────────────────────────────────────────────────────────────────

def test_config_endpoint_requires_owner(
    temp_hub_dir: Path,
    session_secret: str,  # noqa: ARG001
    owner_id: int,  # noqa: ARG001
    bot_token: str,  # noqa: ARG001
    events_log: Path,  # noqa: ARG001
    modules_root: Path,  # noqa: ARG001
):
    _seed_module_with_schema(modules_root, "foo", DEMO_SCHEMA)
    with build_client(temp_hub_dir, follow_redirects=False) as tc:
        r = tc.get("/modules/foo/config")
        assert r.status_code in (302, 307)
        assert r.headers.get("location", "").endswith("/login")


def test_config_endpoint_renders_form_for_installed_module(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module_with_schema(modules_root, "foo", DEMO_SCHEMA)
    from bot.modules import install as module_install
    module_install(modules_root / "foo", temp_hub_dir)

    r = auth_client.get("/modules/foo/config")
    assert r.status_code == 200, r.text
    body = r.text
    assert 'hx-post="/modules/foo/config"' in body
    assert '<input type="text"' in body  # name field
    assert 'type="number"' in body  # count field
    assert 'type="checkbox"' in body  # enabled
    assert "<select" in body  # mode enum


def test_config_endpoint_shows_notice_when_no_schema(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module_with_schema(modules_root, "foo", None)
    from bot.modules import install as module_install
    module_install(modules_root / "foo", temp_hub_dir)

    r = auth_client.get("/modules/foo/config")
    assert r.status_code == 200, r.text
    assert "This module has no configuration" in r.text


def test_config_endpoint_404_for_uninstalled(
    auth_client, modules_root: Path,
):
    _seed_module_with_schema(modules_root, "foo", DEMO_SCHEMA)
    r = auth_client.get("/modules/foo/config")
    assert r.status_code == 404


def test_post_config_valid_saves_and_returns_success_fragment(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module_with_schema(modules_root, "foo", DEMO_SCHEMA)
    from bot.modules import get_entry
    from bot.modules import install as module_install
    module_install(modules_root / "foo", temp_hub_dir)

    r = auth_client.post(
        "/modules/foo/config",
        data={"name": "abc", "count": "7", "enabled": "on", "mode": "b"},
    )
    assert r.status_code == 200, r.text
    assert "Saved. CLAUDE.md rebuilt." in r.text
    entry = get_entry(temp_hub_dir, "foo")
    assert entry is not None
    assert entry["config"]["name"] == "abc"
    assert entry["config"]["count"] == 7
    assert entry["config"]["enabled"] is True
    assert entry["config"]["mode"] == "b"


def test_post_config_invalid_re_renders_with_errors(
    auth_client, modules_root: Path, temp_hub_dir: Path,
):
    _seed_module_with_schema(modules_root, "foo", DEMO_SCHEMA)
    from bot.modules import install as module_install
    module_install(modules_root / "foo", temp_hub_dir)

    # count=500 violates maximum=100
    r = auth_client.post(
        "/modules/foo/config",
        data={"name": "abc", "count": "500", "mode": "a"},
    )
    assert r.status_code == 200, r.text
    body = r.text
    assert "field-error" in body
    assert "errors below" in body
