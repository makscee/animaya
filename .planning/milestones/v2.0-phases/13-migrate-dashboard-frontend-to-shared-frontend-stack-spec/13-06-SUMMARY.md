---
phase: 13
plan: 06
subsystem: dashboard-cutover
tags: [cutover, deploy, docker, bun, cleanup]
requires: [13-01, 13-02, 13-03, 13-04, 13-05]
provides: [D-01, D-02, D-04, D-08, D-09, D-11, A6]
affects: [bot/dashboard, pyproject.toml, docker/Dockerfile.bot, docker/docker-compose.yml, scripts/deploy.sh, tests/dashboard, .planning/ROADMAP.md]
tech-stack:
  added: [oven/bun:1 docker base, Next.js standalone runtime in container]
  patterns: [multi-stage build, bun install --frozen-lockfile, subprocess.Popen(next start) from main.py]
key-files:
  created:
    - bot/engine/modules_registry.py
    - bot/engine/bridge_fsm.py
    - tests/engine/ (migrated pure-logic tests)
  modified:
    - docker/Dockerfile.bot
    - docker/docker-compose.yml
    - scripts/deploy.sh
    - pyproject.toml
    - CLAUDE.md
    - .planning/ROADMAP.md
    - tests/test_skeleton.py
  deleted:
    - bot/dashboard/templates/
    - bot/dashboard/static/
    - bot/dashboard/auth.py
    - bot/dashboard/forms.py
    - bot/dashboard/app.py (FastAPI routes)
    - bot/dashboard/deps.py
    - tests/dashboard/test_http_routes*.py (HTTP-route pytest — covered by Playwright)
decisions:
  - "Bun installed via COPY --from=oven/bun:1 /usr/local/bin/bun to avoid curl|bash in runtime stage"
  - "Next.js standalone mode used so bun run start serves on 127.0.0.1:8090 without full node_modules in runtime image"
  - "deploy.sh hardcodes --no-cache per CLAUDE.md Docker rule"
  - "Phase 12 DASH-01..03 annotated as superseded-by-Phase-13 rather than deleted (D-09 reorder)"
metrics:
  duration: "~3h (across two agents + user LXC smoke)"
  completed: 2026-04-17
---

# Phase 13 Plan 06: Cutover + Cleanup Summary

Big-bang cutover (D-08): legacy Jinja/itsdangerous/FastAPI-HTTP surface deleted, Docker rebuilt around Bun + Next.js standalone, pytest dashboard suite retired/migrated, ROADMAP reordered for D-09, full green-check + LXC smoke user-approved.

## Must-Haves — Truths Verified

| Truth | Status |
|-------|--------|
| All FastAPI HTTP routes under bot/dashboard/ DELETED (D-08) | ✓ `rg 'from bot\.dashboard'` empty |
| bot/dashboard/templates/ and static/ DELETED | ✓ dirs absent |
| bot/dashboard/auth.py and forms.py DELETED | ✓ (logic migrated to dashboard/lib/*) |
| itsdangerous + jinja2 REMOVED from pyproject.toml | ✓ |
| Dockerfile has Bun install layer + bun run build | ✓ `oven/bun:1 AS dashboard-build` |
| Docker image starts both processes (engine 127.0.0.1:8091, next start -p 8090 -H 127.0.0.1) | ✓ verified on LXC 205 |
| Port 8090 serves Next.js exclusively | ✓ Playwright surface.spec.ts + curl smoke |
| Legacy pytest tests retired/migrated | ✓ see retirement list below |
| ROADMAP.md Phase 12 annotated superseded-by-Phase-13 for DASH-01..03 | ✓ commit be087f8 |
| Full suite green | ✓ pytest 251, bun test 44, bunx tsc clean, Playwright 14 (pre-merge) |

## Test Retirement List

**DELETED (HTTP-route tests — covered by Playwright):**
- `tests/dashboard/test_http_routes.py`
- `tests/dashboard/test_csrf.py`
- `tests/dashboard/test_auth_flow.py`
- `tests/dashboard/test_static_serve.py`

**MIGRATED to `tests/engine/`:**
- owner-claim FSM tests → `tests/engine/test_bridge_fsm.py`
- modules registry pure logic → `tests/engine/test_modules_registry.py`
- schema validation tests → `tests/engine/test_schemas.py`

## Post-Merge Green-Check (executor re-verification)

| Check | Result |
|-------|--------|
| `.venv/bin/python -m pytest tests/ -q` | 251 passed in 3.22s |
| `cd dashboard && bun test` | 44 pass / 0 fail (72 expect() calls) |
| `cd dashboard && bunx tsc --noEmit` | clean (exit 0, no output) |
| `docker compose build --no-cache` | green (prior, commit 0a46324) |
| Playwright E2E (14 specs) | green pre-merge (logged in 13-05 SUMMARY) |

## Checkpoint Approval

**Task 3 (checkpoint:human-verify)** — user ran manual LXC smoke on animaya-dev (LXC 205 on tower):
- Browser login via Telegram widget: ✓
- `/chat` streaming + tool-use cards: ✓
- `/modules` install/uninstall: ✓
- `/bridge` claim form: ✓
- Non-owner → `/403`: ✓
- Telethon smoke (ping): ✓
- `curl /api/modules` without token → 401: ✓

User response: **approved** → Phase 13 closed.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] Missing AUTH_SECRET in test env helper**
- **Found during:** Post-merge green-check on main
- **Issue:** `REQUIRED_ENV_VARS` in `bot/main.py` gained `AUTH_SECRET` during Phase 13, but `_set_phase5_env` in `tests/test_skeleton.py` was not updated. 4 tests in `TestDataDirectory` + `TestTelegramBridgeIntegration` hit `SystemExit(1)` on AUTH_SECRET missing.
- **Fix:** Added `monkeypatch.setenv("AUTH_SECRET", "test-auth-secret")` to helper
- **Files modified:** `tests/test_skeleton.py`
- **Commit:** 036404a
- **Verification:** `.venv/bin/python -m pytest tests/ -q` → 251 passed

## Key Commits

| Scope | Hash | Message |
|-------|------|---------|
| Task 1 | 1757030 | feat(13-06): excise legacy Jinja dashboard, migrate business logic to bot.engine |
| Task 2 | 0a46324 | feat(13-06): Docker + compose + deploy.sh for Bun + Next.js runtime |
| Task 3 pre-work | be087f8 | docs(13-06): note D-09 reorder — Phase 12 superseded by Phase 13 for DASH-01..03 |
| Merge | eed706a | Merge branch 'worktree-agent-af2221ef' |
| Post-merge fix | 036404a | fix(13-06): add AUTH_SECRET to test skeleton env helper |

## Self-Check: PASSED

- bot/engine/modules_registry.py: FOUND (via git log)
- bot/engine/bridge_fsm.py: FOUND (via git log)
- bot/dashboard/templates: MISSING (expected — deleted)
- bot/dashboard/auth.py: MISSING (expected — deleted)
- itsdangerous in pyproject.toml: MISSING (expected — removed)
- Commits 1757030, 0a46324, be087f8, eed706a, 036404a: all FOUND in git log
