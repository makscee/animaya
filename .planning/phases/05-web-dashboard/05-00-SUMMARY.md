---
phase: 05
plan: 00
subsystem: web-dashboard
tags: [web, dashboard, infrastructure, wave-0]
one_liner: "Wave 0 infrastructure: dropped v1 Next.js/FastAPI dashboard carcass, added python-multipart + jsonschema deps, stood up tests/dashboard/ test package with shared fixtures so Wave 1–3 plans have a place to land automated tests."
requires:
  - Phase 3 bot.modules API (for later plans' fixture seeding)
provides:
  - "tests/dashboard/ package with 6 reusable pytest fixtures"
  - "runtime dep: python-multipart>=0.0.9 (required by FastAPI form parsing)"
  - "runtime dep: jsonschema>=4.0 (config form server-side validation)"
  - "clean slate in bot/dashboard/ (only __init__.py remains)"
affects:
  - pyproject.toml
  - bot/dashboard/
  - tests/dashboard/
  - (removed) top-level dashboard/
tech_stack_added:
  - python-multipart (FastAPI multipart/form-data parsing)
  - jsonschema (server-side JSON Schema validation)
patterns:
  - "Fixture-based test isolation via pytest monkeypatch.setenv"
  - "Deferred import inside client fixture for greenfield collection"
key_files_created:
  - tests/dashboard/__init__.py
  - tests/dashboard/conftest.py
  - .planning/phases/05-web-dashboard/05-00-SUMMARY.md
key_files_modified:
  - pyproject.toml
key_files_deleted:
  - dashboard/ (entire Next.js v1 tree)
  - bot/dashboard/app.py (v1 FastAPI + CORS + SSE)
  - bot/dashboard/auth.py (v1 DASHBOARD_TOKEN bearer)
decisions:
  - "Installed deps into a freshly created .venv (no pre-existing venv); .venv is already in .gitignore so nothing leaks into commits"
  - "Removed jsonschema __version__ access from verify script (DeprecationWarning in 4.26); used plain import check"
metrics:
  duration_minutes: 5
  tasks_completed: 2
  files_created: 3
  files_modified: 1
  files_deleted: 2_plus_dashboard_tree
completed: 2026-04-15
---

# Phase 05 Plan 00: Wave 0 Infrastructure Summary

## One-Liner

Wave 0 infrastructure: dropped v1 Next.js/FastAPI dashboard carcass, added python-multipart + jsonschema deps, and stood up `tests/dashboard/` with shared fixtures so every subsequent plan in Phase 5 has a place to land `<automated>` verifies.

## What Was Built

### Task 1: Deps added, v1 dashboard deleted (commit `fd81c04`)

- Appended `python-multipart>=0.0.9` and `jsonschema>=4.0` to `[project] dependencies` in `pyproject.toml`.
- Removed the entire top-level `dashboard/` directory (Next.js v1 frontend — ~40+ files including `package-lock.json`, `src/`, `public/`, configs).
- Removed `bot/dashboard/app.py` (v1 FastAPI app with CORS + SSE + `/api/chat`).
- Removed `bot/dashboard/auth.py` (v1 DASHBOARD_TOKEN bearer check).
- Kept `bot/dashboard/__init__.py` as the package marker (empty, 0 bytes).
- Created `.venv` and ran `pip install -e ".[dev]"` — jsonschema 4.26.0 + python-multipart 0.0.26 installed; existing `multipart` importable; whole test suite still green (119 passed).
- Verified no Python code in `bot/` or `tests/` imports `bot.dashboard.app` or `bot.dashboard.auth` — grep returned zero hits (only planning docs reference them by name, which is expected).

### Task 2: Dashboard test package with shared fixtures (commit `147a177`)

Created `tests/dashboard/__init__.py` (empty) and `tests/dashboard/conftest.py` exporting six fixtures (Python 3.12 type hints, ruff-clean):

| Fixture | Purpose |
|---------|---------|
| `temp_hub_dir` | Isolated hub directory (`tmp_path/hub/knowledge/animaya`) with seeded empty `registry.json` |
| `session_secret` | Sets `SESSION_SECRET` env var for `itsdangerous` signer (test-only value) |
| `owner_id` | Sets `TELEGRAM_OWNER_ID=111222333` (test-only allowlist) |
| `bot_token` | Sets `TELEGRAM_BOT_TOKEN` for HMAC verification (test-only value) |
| `events_log` | Redirects `ANIMAYA_EVENTS_LOG` into tmp_path |
| `client` | FastAPI `TestClient` bound to a build_app factory; **skips cleanly with a helpful reason** until Plan 03 creates `bot.dashboard.app.build_app` |

The `client` fixture uses a deferred import inside the fixture body with an `ImportError → pytest.skip` guard so Wave 0 test collection is clean even though `build_app` doesn't yet exist.

## Deviations from Plan

### Auto-fixed Issues

None. Plan executed exactly as written.

### Observations (not deviations)

- The plan suggested using `.venv/bin/pip install -e .` "or `pip install -e .`". No pre-existing venv was present, so I created `.venv` fresh (`python3 -m venv .venv`) and used `.venv/bin/pip`. `.venv` is already gitignored; nothing leaked into the commit.
- One benign `DeprecationWarning` appeared when probing `jsonschema.__version__` during acceptance verification (jsonschema 4.26 deprecates that attribute). The warning is harmless; the `import multipart; import jsonschema` smoke check still exits 0.

## Verification Results

| Check | Result |
|-------|--------|
| `grep -q "python-multipart" pyproject.toml` | PASS |
| `grep -q "jsonschema" pyproject.toml` | PASS |
| `[ ! -d dashboard ]` | PASS |
| `[ ! -f bot/dashboard/app.py ]` | PASS |
| `[ ! -f bot/dashboard/auth.py ]` | PASS |
| `python -c "import multipart; import jsonschema"` | PASS |
| `grep -rn "bot.dashboard.app\|bot.dashboard.auth" bot/ tests/` | 0 matches |
| `tests/dashboard/__init__.py` exists, empty | PASS |
| `grep -q "def temp_hub_dir" tests/dashboard/conftest.py` | PASS |
| `grep -q "def client" tests/dashboard/conftest.py` | PASS |
| All 5 other fixtures grep-present | PASS |
| `python -m pytest tests/dashboard/ -x -q` | exit 0, 0 tests collected |
| `python -m pytest tests/ -q` | **119 passed in 1.97s** |
| `ruff check tests/dashboard/conftest.py` | "All checks passed!" |

## Deferred Issues

None.

## Threat Flags

None — no new network surface, auth paths, or trust boundaries introduced. All deps pinned per plan threat model (T-05-00-01, T-05-00-02 mitigated).

## Self-Check: PASSED

Verified artifacts on disk:
- `tests/dashboard/__init__.py` — FOUND
- `tests/dashboard/conftest.py` — FOUND (73 lines, 6 fixtures)
- `pyproject.toml` — FOUND (both deps present)
- `bot/dashboard/app.py` — ABSENT (as required)
- `bot/dashboard/auth.py` — ABSENT (as required)
- `dashboard/` — ABSENT (as required)

Verified commits on disk:
- `fd81c04` — FOUND (`chore(05-00): add python-multipart + jsonschema deps; drop v1 dashboard code`)
- `147a177` — FOUND (`test(05-00): create tests/dashboard/ package with shared fixtures`)
