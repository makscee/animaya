---
plan: 05-06
phase: 05-web-dashboard
title: Auto-generated module config forms (DASH-06)
status: complete
completed: 2026-04-15
requirements: [DASH-06]
tags: [dashboard, config, forms, jsonschema]
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Plan 05-06 Summary

## Delivered

DASH-06 — auto-generated configuration forms for installed modules, driven by each module's `manifest.config_schema`:

- `GET /modules/{name}/config` renders an HTMX form built from the installed module's `config_schema`. Unknown / uninstalled modules get `404`. Modules with null schema return a "This module has no configuration" notice.
- `POST /modules/{name}/config` coerces form data per JSON Schema type, validates with `jsonschema.Draft202012Validator`, persists to the registry entry via `bot.modules.write_registry`, calls `bot.modules.assemble_claude_md`, and returns a "Saved. CLAUDE.md rebuilt." success fragment.
- `/modules/{name}` detail page lazy-loads the form via `hx-get="/modules/{name}/config"` + `hx-trigger="load"` when the module is installed and has a schema.

### Supported JSON Schema types (D-11)

| Schema | HTML input | kind |
|--------|-----------|------|
| `{type: "string"}` | `<input type="text">` | `string` |
| `{type: "string", enum: [...]}` | `<select>` | `select` |
| `{type: "integer"}` | `<input type="number" step="1">` | `integer` |
| `{type: "number"}` | `<input type="number" step="any">` | `number` |
| `{type: "boolean"}` | `<input type="checkbox">` | `boolean` |
| anything else | muted "Unsupported — edit via CLI" notice | `unsupported` |

### Annotations consumed (D-12)

`title` (label), `description` (help text), `default` (pre-fill), `minimum`/`maximum` (int/number), `minLength`/`maxLength` (string), `pattern` (server-validated only via jsonschema), `enum` (select options), `required` (propagated for template use).

### Coercion rules (pre-jsonschema)

- `integer` / `number` empty string → key dropped from payload so the schema `default` applies.
- `integer` / `number` non-numeric → `{"Must be a whole number" | "Must be a number"}` error short-circuits jsonschema for that field.
- `boolean` checkbox absent → `False`; present with any value other than `""`/`"off"`/`"false"`/`"0"` → `True`.
- `unsupported` fields are intentionally omitted from the coerced payload (never persisted).
- `string` / `select` values passed through as-is, jsonschema rejects enum mismatches.

### Validation pipeline

```
form data --> coerce() --(errors?)-> re-render with field-error + summary
                |
                no errors
                v
            validate() --(errors?)-> re-render with field-error + summary
                |
                no errors
                v
         save_config() -> write_registry -> assemble_claude_md
                |
                v
      success fragment ("Saved. CLAUDE.md rebuilt.") + fresh form
```

`save_config` wraps `assemble_claude_md` in a try/except so a downstream assembler hiccup does **not** roll back the persisted config (T-05-06-08). The next bot startup reassembles CLAUDE.md.

## Files

**Created:**
- `bot/dashboard/forms.py` — `render_fields`, `coerce`, `validate`, `save_config` helpers (187 lines)
- `bot/dashboard/templates/_fragments/form_field.html` — dispatches on `field.kind` for each supported type
- `bot/dashboard/templates/_fragments/config_form.html` — outer form with `hx-post` + submit
- `bot/dashboard/templates/_fragments/config_form_saved.html` — success + re-rendered form; also carries the "no schema" branch
- `tests/dashboard/test_config_form.py` — 23 tests covering render/coerce/validate/save + 6 HTTP endpoints

**Modified:**
- `bot/dashboard/module_routes.py` — added two routes (`config_get`, `config_post`) inside `register()`, both `Depends(require_owner)`
- `bot/dashboard/templates/module_detail.html` — replaced config placeholder block with the HTMX lazy-load + fallback notices

## Commits

- `c6679d2` test(05-06): failing tests for config form + renderer + save flow
- `1e055f8` feat(05-06): config_schema renderer + coercer + validator + save helpers
- (latest) feat(05-06): config_schema -> HTMX form with jsonschema validation + assembler rebuild

## Verification

- `tests/dashboard/test_config_form.py` — **23/23 green** (23 tests, min bar was 18)
- Dashboard suite (`tests/dashboard/`) — **97/97 green**
- Whole suite (`tests/`) — **216/216 green**
- `ruff check bot/dashboard/` — clean

## Key Decisions

- **Coerce-before-validate**: booleans always present in payload (HTML omission-implies-false); empty numeric strings dropped (so `default` applies via jsonschema); type-coercion errors short-circuit jsonschema to keep error messages on-topic.
- **Required-field extraction**: `jsonschema` reports `required` errors with an empty `absolute_path`; `validate()` parses the standard quoted field name from the message so the error lands on the right field in the form.
- **Assembler failure is non-fatal on save** (T-05-06-08): registry is the source of truth; CLAUDE.md is derivable and regenerates on startup.
- **Template lazy-load on detail page**: config form fetched via HTMX on page load rather than rendered inline server-side — keeps `/modules/{name}` responsive and lets the form fragment own its own error-state swap target.
- **Summary error text**: "Please fix N errors below." (always plural) per UI-SPEC error-state copy contract.

## Deviations

None — plan executed as written aside from two minor template refinements:
1. `config_form_saved.html` gained a `no_schema` branch so `GET /modules/{name}/config` can return the "This module has no configuration" notice through the same partial (avoided a dedicated fragment for a single line of copy).
2. `module_detail.html` branch order — plan's elif was "not installed" first; reordered to `has_config and installed` → `has_config and not installed` → default (no-schema) so the has_config modules get the lazy-load even when the plan's branch order would hit the "no configuration" default.

Both are cosmetic restructurings of the plan's template with identical rendered outputs for each branch.

## Self-Check: PASSED

- `bot/dashboard/forms.py` — FOUND
- `bot/dashboard/templates/_fragments/form_field.html` — FOUND
- `bot/dashboard/templates/_fragments/config_form.html` — FOUND
- `bot/dashboard/templates/_fragments/config_form_saved.html` — FOUND
- `tests/dashboard/test_config_form.py` — FOUND
- Commits `c6679d2`, `1e055f8` — FOUND in `git log`
