---
phase: 13
plan: 04
subsystem: engine-loopback-supervisor
tags: [python, engine, loopback, sse, wave-3]
requires:
  - "13-02 auth core (dashboard/lib/engine.server.ts contract — http://127.0.0.1:8091)"
provides:
  - "bot.engine.owner_lock — per-owner asyncio.Lock registry shared by tg + web"
  - "bot.engine.http — loopback-only FastAPI app on 127.0.0.1:ANIMAYA_ENGINE_PORT"
  - "bot.engine.chat_stream — async SSE generator with 15s heartbeat + owner-lock"
  - "bot.engine.modules_rpc — /engine/modules CRUD without bot_token leak (SEC-01)"
  - "bot.engine.bridge_rpc — /engine/bridge claim/revoke/regen/toggle/policy"
  - "bot.main supervises engine (loopback) + 'bun run start' for Next.js dashboard"
affects:
  - "bot/main.py — uvicorn now hosts bot.engine.http; launches Next.js subprocess"
  - "bot/dashboard/app.py — no longer the uvicorn target (kept for AppContext dependencies; Plan 06 deletes)"
  - "CLAUDE.md — AUTH_SECRET + OWNER_TELEGRAM_ID + ANIMAYA_ENGINE_PORT env vars"
  - "tests/dashboard/test_main_wiring.py — AUTH_SECRET added to env helper"
tech-stack:
  added:
    - "bot/engine/* subpackage (loopback HTTP, owner-lock, SSE)"
    - "subprocess + shutil in bot/main.py to launch `bun run start`"
  patterns:
    - "asyncio.Lock dict keyed by owner_id (derived from session_key suffix)"
    - "asyncio.wait timeout for SSE heartbeat emission without re-entering the iterator"
    - "Env-gated TestClient allowlist (ANIMAYA_ENGINE_ALLOW_TESTCLIENT=1) for tests"
    - "DTO secret-strip (bot_token/token) at serialization boundary"
key-files:
  created:
    - bot/engine/__init__.py
    - bot/engine/owner_lock.py
    - bot/engine/http.py
    - bot/engine/chat_stream.py
    - bot/engine/modules_rpc.py
    - bot/engine/bridge_rpc.py
    - tests/engine/__init__.py
    - tests/engine/test_owner_lock.py
    - tests/engine/test_http_smoke.py
    - tests/engine/test_chat_stream.py
  modified:
    - bot/main.py
    - CLAUDE.md
    - tests/dashboard/test_main_wiring.py
decisions:
  - "Engine host hardcoded to 127.0.0.1 via get_host() — not configurable by env (T-13-31 defense-in-depth)"
  - "Owner id derived from session_key: 'tg:<id>' | 'web:<id>' — colon-prefixed convention shared with dashboard/lib/engine.server.ts"
  - "SSE heartbeat implemented via asyncio.wait (not asyncio.wait_for + shield) to avoid 'async generator already running' re-entrancy errors"
  - "Loopback middleware allows '127.0.0.1', '::1', 'localhost' only; adds 'testclient' iff ANIMAYA_ENGINE_ALLOW_TESTCLIENT=1 (tests-only)"
  - "Task 3 commit message was applied via --amend on the wip(auto) commit that captured bot/main.py + CLAUDE.md + test fixture changes (no logic loss)"
metrics:
  duration_sec: 900
  tasks: 3
  completed_date: 2026-04-17
---

# Phase 13 Plan 04: Python loopback engine + Next.js supervisor Summary

Wave 3 engine side complete: Python demoted to a loopback-only FastAPI engine (`bot/engine/*`, 127.0.0.1:${ANIMAYA_ENGINE_PORT:-8091}) with SSE chat + modules/bridge RPC matching the contract Plan 13-03 will consume. Owner-lock coordinator serializes Telegram + web turns for a single owner across both transport origins. `bot/main.py` now supervises both processes: uvicorn for the engine plus `bun run start` subprocess for the Next.js dashboard. All 13 engine tests pass, all 26 main-boot/main-wiring tests remain green, ruff clean across touched surface.

## What Was Built

### Task 1 — Owner-lock coordinator (commit `eabff0a`)

- `bot/engine/owner_lock.py` — module-level `_locks: dict[str, asyncio.Lock]` registry.
- `acquire_for_session(session_key)` — async context manager that derives `owner_id` from `"tg:<id>"` / `"web:<id>"` (splits on first `:`) and serializes all coroutines sharing that owner.
- Test coverage (4 tests, all pass):
  - Same-owner concurrent acquires serialize (no interleaving).
  - Different owners never block each other.
  - Cross-transport same owner (`tg:123` + `web:123`) does serialize.
  - Lock released on exception (context-manager semantics).

### Task 2 — Loopback FastAPI engine + SSE chat + modules/bridge RPC (commit `295825e`)

- `bot/engine/http.py` — FastAPI app with loopback-only middleware. `get_host()` returns `"127.0.0.1"` unconditionally; `get_port()` reads `ANIMAYA_ENGINE_PORT` (default 8091). Middleware rejects any `request.client.host` not in `{"127.0.0.1","::1","localhost"}` with 403 (T-13-30). Tests opt in via `ANIMAYA_ENGINE_ALLOW_TESTCLIENT=1`.
- `bot/engine/chat_stream.py` — `stream_chat(body, iterator=...)` acquires the owner lock for `body["session_key"]`, races the pluggable event iterator against a configurable heartbeat (`body["_heartbeat"]`, default 15.0s), emits `:ping\n\n` on idle, and always closes with a `data: {"type":"end"}\n\n` frame. Production iterator `_iter_sdk_events` calls `bot.claude_query.build_options` + `claude_code_sdk.query` and maps `AssistantMessage.TextBlock` / `ToolUseBlock` to the 13-04-PLAN.md event shape.
- `bot/engine/modules_rpc.py` — `APIRouter` with `GET ""`, `POST "/{name}/install"`, `POST "/{name}/uninstall"`, `PUT "/{name}/config"`. `_strip_secrets()` drops `bot_token` / `token` plus pipes module entries through `redact_bridge_config` before serialization (T-13-33 / SEC-01).
- `bot/engine/bridge_rpc.py` — `APIRouter` for pairing-code + toggle/policy verbs over `bot.modules.telegram_bridge_state`.
- Test coverage (9 tests, all pass):
  - HTTP smoke: loopback-only accessor, `get_port` default/override, modules list shape + no-`bot_token`/-`token` substring, unknown-module 4xx, non-loopback client → 403.
  - Chat stream: basic text→end frame, heartbeat `:ping` on idle, concurrent same-owner serialization, different-owner concurrency allowed.

### Task 3 — Supervisor + env contract (commit `cd075f2`, amended from wip-auto)

- `bot/main.py`:
  - Uvicorn now targets `bot.engine.http:app` on `engine_http.get_host()` (127.0.0.1) and `engine_http.get_port()`.
  - `_start_dashboard()` launches `bun run start` in `dashboard/` when `bun` is on PATH and `dashboard/.next` exists; otherwise warn-and-skip (dev-friendly).
  - `_stop_dashboard()` calls `terminate()` then `kill()` after 10s (graceful SIGTERM propagation).
  - Injects `ANIMAYA_ENGINE_URL=http://127.0.0.1:${ANIMAYA_ENGINE_PORT:-8091}` into the subprocess env.
  - Task name kept as `"uvicorn"` to preserve the existing `test_main_boot.py::test_dashboard_starts_before_supervisor` contract.
- `CLAUDE.md` env table:
  - Required: `AUTH_SECRET` (next-auth v5 JWT signing), `OWNER_TELEGRAM_ID` (middleware fail-closed gate).
  - Optional: `ANIMAYA_ENGINE_PORT` (default 8091).
- `tests/dashboard/test_main_wiring.py::_set_all_required` now sets `AUTH_SECRET` so its helper-driven tests boot past the env-gate.

## Must-Haves Verification

| Truth | Status | Evidence |
|-------|--------|----------|
| Engine exposes FastAPI on 127.0.0.1:${ANIMAYA_ENGINE_PORT} | PASS | `bot/engine/http.py::get_host` returns `"127.0.0.1"` (hardcoded); `get_port` reads env. `grep -q '127.0.0.1' bot/engine/http.py` → match. |
| /engine/chat returns text/event-stream with tool_use + text + 15s heartbeat | PASS | `stream_chat` yields `data:` frames + `:ping\n\n` on idle + trailing `data: {"type":"end"}\n\n`; 4 chat_stream tests green. |
| Owner-lock serializes tg + web turns for same owner | PASS | `test_cross_transport_same_owner_serializes` + `test_concurrent_same_owner_serialize` both pass. |
| Engine RPCs accept only loopback-origin requests | PASS | `loopback_only` middleware; `test_non_loopback_client_rejected` asserts 403 for Starlette `"testclient"` host without the opt-in env flag. |
| bot/main.py launches BOTH processes (engine loopback + bun start) with graceful shutdown | PASS | `_run()` creates `uvicorn_task` then calls `_start_dashboard()`; shutdown awaits `supervisor.stop_all()` → uvicorn → `_stop_dashboard()`. |
| Existing bot/dashboard/* business logic reused (no duplication) | PASS | `modules_rpc` imports from `bot.dashboard.modules_view`, `bot.dashboard.jobs`, `bot.dashboard.forms`; `bridge_rpc` imports from `bot.modules.telegram_bridge_state`. |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — Bug] `stream_chat` heartbeat used `asyncio.wait_for(shield(task))` which re-entered the async iterator**

- **Found during:** Task 2 test run — `test_heartbeat_ping_on_idle` raised `RuntimeError: anext(): asynchronous generator is already running`.
- **Issue:** The original implementation created a fresh `asyncio.create_task(events.__anext__())` on every heartbeat iteration even though the previous task was still pending. Two concurrent `__anext__()` calls on the same async generator is illegal.
- **Fix:** Hold the pending task across heartbeat iterations; race it against a timeout via `asyncio.wait({task}, timeout=...)`. Only create a new task after the previous one resolves.
- **Files modified:** `bot/engine/chat_stream.py`.
- **Commit:** `295825e`.

**2. [Rule 3 — Blocking] TestClient default host `"testclient"` fails loopback middleware**

- **Found during:** Task 2 `test_list_modules_shape_and_no_bot_token` — all TestClient-driven tests returned 403.
- **Issue:** Starlette's in-process TestClient reports `request.client.host == "testclient"`, which is not in the loopback allowlist. Relaxing the middleware to allow `"testclient"` in production would defeat T-13-30.
- **Fix:** Added `ANIMAYA_ENGINE_ALLOW_TESTCLIENT` env opt-in. Tests set the flag via `monkeypatch.setenv`; production never sets it. The negative test `test_non_loopback_client_rejected` explicitly `delenv`s the flag and asserts 403 — proving the production path is still safe.
- **Files modified:** `bot/engine/http.py`, `tests/engine/test_http_smoke.py`.
- **Commit:** `295825e`.

**3. [Rule 3 — Blocking] `tests/dashboard/test_main_wiring.py` helper did not set AUTH_SECRET**

- **Found during:** Task 3 full-suite regression run — `test_main_calls_events_rotate` + `test_main_spawns_uvicorn_task` both `SystemExit(1)` on the new AUTH_SECRET gate.
- **Issue:** Adding `AUTH_SECRET` to `REQUIRED_ENV_VARS` regressed tests whose `_set_all_required` helper predates Phase 13.
- **Fix:** Appended `monkeypatch.setenv("AUTH_SECRET", "auth-secret")` to `_set_all_required` and added the literal to `_ALL_REQUIRED`. No per-test opt-out needed.
- **Files modified:** `tests/dashboard/test_main_wiring.py`.
- **Commit:** `cd075f2`.

**4. [Rule 1 — Bug] Registry fixture wrote `{}` instead of `{"modules": []}`**

- **Found during:** Task 2 smoke test — `bot.modules.registry.read_registry` validates schema and raises `ValueError` on missing `modules` list.
- **Issue:** Shortcut fixture didn't match the registry schema.
- **Fix:** Fixture now writes `'{"modules": []}'`.
- **Files modified:** `tests/engine/test_http_smoke.py`.
- **Commit:** `295825e`.

### Intentional Scope Trim

- `pyproject.toml` was **not** modified. Plan text explicitly defers dependency pruning to Plan 06. All new code uses already-installed packages (`fastapi`, `uvicorn`, `httpx`, `claude_code_sdk`).
- `bot/dashboard/app.py` was **not** deleted or demoted beyond the uvicorn repoint — it still builds an AppContext and exposes `app.state.hub_dir`/`supervisor`/`ctx` used by the module supervisor. Plan 06 (per 13-CONTEXT D-08) handles big-bang deletion of the legacy templates + routes.

## TDD Gate Compliance

Plan type is `execute`, not `tdd` (plan-level). Individual tasks marked `tdd="true"` followed RED→GREEN, though commits combined test + impl:

- Task 1: tests authored first; ran pytest (would have failed with ImportError before `owner_lock.py` landed); then committed with 4 pass green.
- Task 2: tests written against the interface first; two RED failures surfaced during GREEN (heartbeat re-entrancy + TestClient host); both fixed inline before the commit landed.
- Task 3 is `tdd="false"` — no RED gate required.

## Known Stubs

None. Every engine endpoint is wired to real business logic. `_iter_sdk_events` is live (calls `claude_code_sdk.query`); `_start_dashboard` warns-and-skips only when the Next.js artifact is absent (local dev). No placeholder returns, no hardcoded empty responses.

## Threat Flags

No new surface beyond plan's `<threat_model>`:

- T-13-30 mitigated by `loopback_only` middleware (enforced by `test_non_loopback_client_rejected`).
- T-13-31 mitigated by `get_host()` returning `"127.0.0.1"` (non-configurable); uvicorn in `bot/main.py` consumes it verbatim.
- T-13-32 mitigated by `owner_lock.acquire_for_session` (proven by concurrency tests).
- T-13-33 mitigated by `_strip_secrets` in `modules_rpc` + absence of `bot_token` field in all response models (asserted by `test_list_modules_shape_and_no_bot_token`).
- T-13-34 accepted (crash-loop resilience deferred to Plan 08 / docker-compose restart policy).

## Self-Check

Files verified (all FOUND in `bot/engine/` and `tests/engine/`):

- bot/engine/__init__.py, owner_lock.py, http.py, chat_stream.py, modules_rpc.py, bridge_rpc.py
- tests/engine/__init__.py, test_owner_lock.py, test_http_smoke.py, test_chat_stream.py
- bot/main.py modified; CLAUDE.md env table amended; tests/dashboard/test_main_wiring.py AUTH_SECRET added

Commits verified (animaya repo):

- FOUND: `eabff0a feat(13-04): add owner-lock registry for tg+web turn serialization`
- FOUND: `295825e feat(13-04): add loopback FastAPI engine with SSE chat + modules/bridge RPC`
- FOUND: `cd075f2 feat(13-04): supervise Python engine + Next.js dashboard subprocess`

Verification commands (all pass):

- `pytest tests/engine/ -v` → 13 passed
- `pytest tests/dashboard/test_main_wiring.py tests/test_main_boot.py` → 26 passed
- `ruff check bot/engine/ bot/main.py tests/engine/` → all checks passed
- `python -c 'import bot.main'` with env vars set → no errors
- `grep -q '127.0.0.1' bot/engine/http.py` → match
- `grep -q 'loopback only' bot/engine/http.py` → match
- `grep -q 'bun' bot/main.py` → match
- `grep -q 'ANIMAYA_ENGINE_PORT' bot/main.py` → match
- `grep -q 'AUTH_SECRET' CLAUDE.md` → match

## Self-Check: PASSED

## Commits

| # | Hash    | Message |
|---|---------|---------|
| 1 | eabff0a | `feat(13-04): add owner-lock registry for tg+web turn serialization` |
| 2 | 295825e | `feat(13-04): add loopback FastAPI engine with SSE chat + modules/bridge RPC` |
| 3 | cd075f2 | `feat(13-04): supervise Python engine + Next.js dashboard subprocess` |
