---
task: 260416-lht
title: Locale at bridge creation drives BOOTSTRAP.md language
type: quick
completed: 2026-04-16
commits:
  - a8fbfd2
  - c5f790b
  - 049833d
---

# Quick Task 260416-lht: Locale at bridge creation drives BOOTSTRAP.md language

## One-liner

Locale chosen during Telegram-bridge install is persisted to the module
registry and flows through `build_options` so the BOOTSTRAP.md system prompt
is rendered in the operator's language (en or ru).

## Tasks

### Task 1 — Locale-aware BOOTSTRAP.md with substitution in `build_options`
- **Commit:** `a8fbfd2`
- **Files:**
  - `bot/claude_query.py` — added `LOCALE_SUBSTITUTIONS`, `_substitute_bootstrap`,
    `locale: str | None = None` kwarg on `build_options`, applied
    substitution to the BOOTSTRAP block.
  - `bot/templates/BOOTSTRAP.md` — placeholder hooks (`{locale}`,
    `{locale_example}`).
  - `tests/test_claude_query.py` (or the relevant locale tests) — covers
    `en`, `ru`, unknown, and `None` fallback to `en`.

### Task 2 — Locale selector in bridge install dialog + registry wiring
- **Commit:** `c5f790b`
- **Files:**
  - `bot/dashboard/bridge_routes.py` — accepts `locale` form field on
    install, validates ∈ {en, ru}, persists into module config.
  - `bot/dashboard/module_routes.py` — exposes locale label on the
    `telegram-bridge` config page.
  - `bot/dashboard/templates/_fragments/bridge_install_form.html` — locale
    `<select>` rendered in install form.
  - `bot/dashboard/templates/_fragments/bridge_install_modal.html` — modal
    variant of the same form.
  - `bot/dashboard/templates/bridge_config.html` — shows the persisted
    locale on the configured-bridge view.
  - `bot/modules/telegram_bridge_state.py` — added `_get_bridge_locale`
    helper (reads `telegram-bridge` entry via `get_entry`, defaults to `en`,
    whitelists to {en, ru}); exported from `__all__`.
  - `tests/dashboard/test_bridge_install_locale.py` (new) — 6 tests:
    default `en`, explicit `ru`, rejects unknown values, modal/form render
    selector, config page renders the chosen label.

### Task 3 — Plumb locale from bridge registry into `build_options`
- **Commit:** `049833d`
- **Files:**
  - `bot/bridge/telegram.py` — in `_run_claude_and_stream`, call
    `_get_bridge_locale(data_dir)` and pass the result as the new `locale`
    kwarg to `build_options(...)`. Defensive try/except → `en` on any
    registry read failure.
  - `tests/test_bridge_locale_flow.py` (new) — 3 tests: locale `ru` flows
    through, missing registry entry → `en`, registry lookup raising → `en`.

## Test summary

- `tests/dashboard/` — 131 passed (full dashboard suite, including 6 new
  locale tests).
- `tests/test_bridge.py` + `tests/test_bridge_locale_flow.py` — 24 passed.
- `uvx ruff check` — clean on every file touched across the three commits.

## Deviations

- **Rule 2 (defensive):** Added a `try/except` around `_get_bridge_locale`
  at the `_run_claude_and_stream` call site so a corrupt registry cannot
  break the Telegram reply path. Falls back to `en` and logs at debug.
- Task 2 ruff pass auto-fixed an `I001` import-order lint in
  `tests/dashboard/test_bridge_install_locale.py`.

## Commit hashes

| Task | Commit    | Subject                                                               |
| ---- | --------- | --------------------------------------------------------------------- |
| 1    | `a8fbfd2` | locale-aware BOOTSTRAP.md with substitution in build_options          |
| 2    | `c5f790b` | locale selector in bridge install dialog + registry wiring            |
| 3    | `049833d` | plumb locale from bridge registry into build_options                  |

## Self-Check: PASSED

- `bot/claude_query.py::build_options(locale=...)` — FOUND
- `bot/modules/telegram_bridge_state.py::_get_bridge_locale` — FOUND
- `bot/bridge/telegram.py` passes `locale=locale` into `build_options` — FOUND
- `tests/dashboard/test_bridge_install_locale.py` — FOUND (6 tests pass)
- `tests/test_bridge_locale_flow.py` — FOUND (3 tests pass)
- Commits `a8fbfd2`, `c5f790b`, `049833d` — FOUND in `git log`.
