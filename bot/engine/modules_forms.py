"""Config-form renderer + coercer + validator (Phase 5 DASH-06).

Walks a JSON Schema subset (D-11: string, integer, number, boolean,
string+enum) and produces template context for form partials, then
coerces HTML form data back to schema-typed payload and validates
via jsonschema (D-13). :func:`save_config` persists into the registry
entry and reassembles CLAUDE.md (D-14).

Supported types (D-11): ``string``, ``integer``, ``number``, ``boolean``,
and ``string`` with ``enum`` (rendered as ``<select>``). Anything else is
classified as ``unsupported`` and renders a muted notice — the rest of
the form still renders.

Annotations consumed (D-12): ``title``, ``description``, ``default``,
``minimum``, ``maximum``, ``minLength``, ``maxLength``, ``pattern``
(server-validated only), ``enum``.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import jsonschema

from bot.modules import assemble_claude_md, read_registry, write_registry

logger = logging.getLogger(__name__)

SUPPORTED_SCALARS: set[str] = {"string", "integer", "number", "boolean"}


# ── Rendering ────────────────────────────────────────────────────────
def render_fields(schema: dict | None, current: dict | None = None) -> list[dict]:
    """Return a list of field-template contexts for the given schema.

    Returns an empty list when the schema is falsy or has no ``properties``.
    Each field context carries its ``kind`` (``string``/``integer``/
    ``number``/``boolean``/``select``/``unsupported``), label, help,
    current value, and (where applicable) numeric/length bounds and
    enum options for the template to dispatch on.
    """
    if not schema or not isinstance(schema.get("properties"), dict):
        return []
    current = current or {}
    required = set(schema.get("required") or [])
    out: list[dict] = []
    for name, raw_prop in schema["properties"].items():
        prop = raw_prop or {}
        kind = _classify(prop)
        default = prop.get("default", "")
        value = current.get(name, default)
        out.append(
            {
                "name": name,
                "kind": kind,
                "label": prop.get("title", name),
                "help": prop.get("description", ""),
                "value": value,
                "min": prop.get("minimum"),
                "max": prop.get("maximum"),
                "min_length": prop.get("minLength"),
                "max_length": prop.get("maxLength"),
                "pattern": prop.get("pattern"),
                "enum": list(prop.get("enum") or []),
                "required": name in required,
                "notice": _unsupported_notice(name, kind),
            }
        )
    return out


def _classify(prop: dict) -> str:
    ptype = prop.get("type")
    if ptype == "string" and "enum" in prop:
        return "select"
    if ptype in SUPPORTED_SCALARS:
        return ptype  # "string" | "integer" | "number" | "boolean"
    return "unsupported"


def _unsupported_notice(name: str, kind: str) -> str | None:
    if kind != "unsupported":
        return None
    return f"Unsupported schema for `{name}` — edit via CLI."


# ── Coercion ─────────────────────────────────────────────────────────
def coerce(
    form_data: dict[str, Any], schema: dict | None
) -> tuple[dict, dict[str, str]]:
    """Coerce HTML form strings to schema-typed values.

    Returns ``(coerced_payload, coercion_errors)``. Coercion errors are
    per-field strings like ``"Must be a whole number"``; they run BEFORE
    jsonschema validation so we never hand jsonschema a type it doesn't
    expect (Pitfall 6). Booleans are filled in even when absent (HTML
    checkboxes omit unchecked values), so ``enabled`` always appears in
    the output with the right bool.
    """
    out: dict[str, Any] = {}
    errors: dict[str, str] = {}
    props = ((schema or {}).get("properties") or {})
    for name, raw_prop in props.items():
        prop = raw_prop or {}
        kind = _classify(prop)
        if kind == "unsupported":
            continue  # intentionally not saved
        if kind == "boolean":
            raw = form_data.get(name)
            out[name] = (
                name in form_data and raw not in ("", "off", "false", "0")
            )
            continue
        raw = form_data.get(name)
        if raw is None or raw == "":
            continue  # let schema default apply on jsonschema side
        if kind == "integer":
            try:
                out[name] = int(raw)
            except (TypeError, ValueError):
                errors[name] = "Must be a whole number"
        elif kind == "number":
            try:
                out[name] = float(raw)
            except (TypeError, ValueError):
                errors[name] = "Must be a number"
        else:  # "string" or "select"
            out[name] = str(raw)
    return out, errors


# ── Validation ───────────────────────────────────────────────────────
def validate(payload: dict, schema: dict | None) -> dict[str, str]:
    """Run jsonschema Draft 2020-12 validation; return ``{field: msg}``."""
    if not schema:
        return {}
    validator = jsonschema.Draft202012Validator(schema)
    out: dict[str, str] = {}
    for err in validator.iter_errors(payload):
        if err.absolute_path:
            key = str(list(err.absolute_path)[0])
        elif err.validator == "required":
            # For required errors the path is empty; extract the field
            # name from the message ("'x' is a required property").
            msg = err.message
            if "'" in msg:
                key = msg.split("'")[1]
            else:
                key = "(root)"
        else:
            key = "(root)"
        out.setdefault(key, err.message)
    return out


# ── Persistence ──────────────────────────────────────────────────────
def save_config(hub_dir: Path, name: str, new_config: dict) -> None:
    """Persist ``new_config`` into the registry entry and rebuild CLAUDE.md.

    Writes the registry atomically via :func:`bot.modules.write_registry`
    and then calls :func:`bot.modules.assemble_claude_md` (D-14). If
    assembly fails, the error is logged but not re-raised — the config
    is persisted regardless, and CLAUDE.md will be regenerated on the
    next startup (T-05-06-08).
    """
    data = read_registry(hub_dir)
    for entry in data["modules"]:
        if entry.get("name") == name:
            entry["config"] = dict(new_config)
            break
    else:
        raise KeyError(f"module {name!r} not installed")
    write_registry(hub_dir, data)
    try:
        assemble_claude_md(hub_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("assemble_claude_md after config save failed: %s", exc)


__all__ = [
    "render_fields",
    "coerce",
    "validate",
    "save_config",
    "SUPPORTED_SCALARS",
]
