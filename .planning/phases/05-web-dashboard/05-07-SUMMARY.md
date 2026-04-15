---
phase: 05
plan: 07
subsystem: dashboard-wiring
tags: [dashboard, main, integration, events, deploy]
requires:
  - bot.events (Plan 05-01)
  - bot.dashboard.app.build_app (Plan 05-03)
  - bot.bridge.telegram.build_app (Phase 2)
  - bot.modules.lifecycle + assembler (Phase 3)
provides:
  - bot.main._run (async dual-task runner)
  - REQUIRED_ENV_VARS expanded to 5 entries (adds SESSION_SECRET, TELEGRAM_OWNER_ID, TELEGRAM_BOT_USERNAME)
  - Event emissions at bridge / modules.install / modules.uninstall / assembler call sites
  - events.log rotation at startup
  - README dashboard deploy + BotFather /setdomain note
affects:
  - bot/main.py
  - bot/bridge/telegram.py (4 emission sites: message received / reply sent / handler exception)
  - bot/modules/lifecycle.py (4 emission sites: install ok/fail, uninstall ok/fail)
  - bot/modules/assembler.py (1 emission site: CLAUDE.md rebuilt)
  - scripts/setup.sh (Phase 5 env hints)
  - README.md (created)
  - tests/test_skeleton.py (regression tests updated for async _run)
tech-stack:
  added: []
  patterns:
    - "Uvicorn + PTB Application coexist in one asyncio loop via uvicorn.Server.serve() as task + `async with app:` + explicit app.start / updater.start_polling"
    - "asyncio.Event as stop signal; SIGINT/SIGTERM handlers set it; finally block drains polling + stops uvicorn.Server (should_exit)"
    - "Best-effort events.emit wrapped in try/except so telemetry never crashes a user-facing code path"
    - "`host='127.0.0.1' + proxy_headers=True + forwarded_allow_ips='127.0.0.1'` — trust X-Forwarded-* only from local Caddy"
key-files:
  created:
    - tests/dashboard/test_event_emitters.py (6 tests)
    - tests/dashboard/test_main_wiring.py (6 tests)
    - README.md
  modified:
    - bot/main.py (rewritten: async _run, extended REQUIRED_ENV_VARS, rotate_events at startup, uvicorn.Config with proxy headers)
    - bot/bridge/telegram.py (3 emit call sites)
    - bot/modules/lifecycle.py (4 emit call sites — install ok/fail + uninstall ok/fail)
    - bot/modules/assembler.py (1 emit call site at rebuild)
    - scripts/setup.sh (3 env-var hints appended)
    - tests/test_skeleton.py (regression tests updated to patch async runner + stub uvicorn.Server)
    - tests/dashboard/conftest.py (added tmp_hub_dir + valid_module_dir fixtures visible in tests/dashboard/)
decisions:
  - "Emit sites chosen per plan: bridge message-received (after logging / before SDK) and reply-sent (after finalize_stream); error emitter tied to application.add_error_handler() callback so uncaught PTB exceptions hit the feed"
  - "Skipped double-emit in bridge for 'Timed out / NetworkError' transient errors to avoid log spam — matches existing _error_handler gate"
  - "Graceful shutdown order: updater.stop -> app.stop -> server.should_exit=True -> await uvicorn_task — drains polled updates first, then kills HTTP server"
  - "SIGINT/SIGTERM handlers registered via loop.add_signal_handler with NotImplementedError guard for Windows/test sandboxes"
  - "All events.emit() calls wrapped in try/except — telemetry is best-effort, must not break a successful install or a normal message turn"
  - "Did NOT add HTMX SRI hash (deferred from Plan 05-03) — Plan 05-07's scope per threat register T-05-07-03/04 is uvicorn hardening, not CDN hash review"
metrics:
  duration: "~25 min"
  tasks_completed: 3
  tests_added: 12  # 6 emitters + 6 main_wiring (incl. 3 param cases)
  tests_modified: 4  # test_skeleton regression tests
  commits: 3
  files_created: 3
  files_modified: 7
  completed: 2026-04-15
requirements_satisfied: [DASH-01, DASH-03]
nyquist_compliant: true
nyquist_signed_off: 2026-04-15
nyquist_retroactive: true
---

# Phase 05 Plan 07: Final Wiring Summary

Fuse bot + dashboard into one asyncio event loop, emit events at the three natural call sites (bridge, module lifecycle, assembler), validate all five required env vars at startup, rotate events.log, and document the BotFather `/setdomain` step — the only plan that touches the live entrypoint.

## What Was Built

### 1. `bot/main.py` — rewritten

- `REQUIRED_ENV_VARS` grew from 2 → 5 (`TELEGRAM_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`, **`SESSION_SECRET`**, **`TELEGRAM_OWNER_ID`**, **`TELEGRAM_BOT_USERNAME`**). Missing any → `logger.error("%s not set", var); sys.exit(1)` with the missing var name in the log so tests can detect it via `caplog`.
- `rotate_events()` invoked at startup (D-21) — wrapped in try/except so a corrupt log does not block startup.
- `assemble_claude_md(data_path)` still called before the bridge (regression-preserved).
- New `async def _run(data_path)` replaces `app.run_polling()`:
  - Builds the PTB Application with the Phase-4 `_post_init` hook (git-versioning commit loop preserved).
  - Builds the dashboard via `build_dashboard_app(hub_dir=data_path)`.
  - Creates a `uvicorn.Config(host="127.0.0.1", port=DASHBOARD_PORT, proxy_headers=True, forwarded_allow_ips="127.0.0.1")` and a `uvicorn.Server`.
  - Spawns `asyncio.create_task(server.serve(), name="uvicorn")`.
  - Enters `async with tg_app:` + `await tg_app.start()` + `await tg_app.updater.start_polling()`.
  - Awaits an `asyncio.Event()` set by `SIGINT`/`SIGTERM` handlers.
  - Graceful shutdown: `updater.stop()` → `tg_app.stop()` → `server.should_exit = True` → `await uvicorn_task`.
- `main()` wraps `asyncio.run(_run(data_path))` and catches `KeyboardInterrupt`.

### 2. Event emitters wired

| Source | Level | Site | Message |
|--------|-------|------|---------|
| `bridge` | info | `_handle_message` after logging the turn | `"message received"` + `chat_id` detail |
| `bridge` | info | end of successful reply finalize | `"reply sent"` + `chat_id` detail |
| `bridge` | error | `_error_handler` (PTB callback) | `"handler exception: {ErrClass}"` + `error=str(err)` |
| `modules.install` | info | after `add_entry` succeeds | `"{name}@{version} installed"` |
| `modules.install` | error | before raising on `rc != 0` | `"{name} install.sh failed"` + `rc` |
| `modules.uninstall` | info | after owned-path check passes | `"{name} uninstalled"` |
| `modules.uninstall` | error | before raising on `rc != 0` | `"{name} uninstall.sh failed"` + `rc` |
| `assembler` | info | end of `assemble_claude_md` | `"CLAUDE.md rebuilt"` + `modules=[names]` |

All emit calls wrapped in `try/except` so a broken log path never breaks a successful user action (best-effort telemetry).

### 3. README + setup.sh deploy steps

- `README.md` created with env-var matrix (Phase 1/2 + Phase 5), dashboard deploy section, and the `/setdomain` BotFather walkthrough.
- `scripts/setup.sh` appended with three `echo NOTE:` hints when `SESSION_SECRET`, `TELEGRAM_OWNER_ID`, or `TELEGRAM_BOT_USERNAME` is unset during install.

### 4. Tests

- `tests/dashboard/test_event_emitters.py` — 6 tests: assembler rebuild emit, install success/failure emit, uninstall success emit, bridge message-received emit (with stubbed Claude SDK), bridge error-handler emit.
- `tests/dashboard/test_main_wiring.py` — 6 tests (incl. 3 parametrized missing-var cases): env-var validation for SESSION_SECRET / TELEGRAM_OWNER_ID / TELEGRAM_BOT_USERNAME, explicit SESSION_SECRET case, `rotate_events` call ordering, uvicorn.Server.serve() scheduled alongside PTB.
- `tests/dashboard/conftest.py` — added `tmp_hub_dir` + `valid_module_dir` fixtures so the emitter tests can install a real fake module.
- `tests/test_skeleton.py` — three regression tests updated for the async-runner shape (now stub `uvicorn.Server`, `build_dashboard_app`, and an auto-set `asyncio.Event` so `main()` returns quickly).

## Env Var Matrix

| Var | Phase | Required | Purpose |
|-----|-------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | 1 | yes | PTB + Telegram Login Widget HMAC |
| `CLAUDE_CODE_OAUTH_TOKEN` | 2 | yes | Claude Code SDK auth |
| `SESSION_SECRET` | 5 | yes | itsdangerous session cookie signing |
| `TELEGRAM_OWNER_ID` | 5 | yes | Dashboard allowlist (comma-separated ints) |
| `TELEGRAM_BOT_USERNAME` | 5 | yes | Login Widget renders only when set |
| `DASHBOARD_PORT` | 5 | no (default `8090`) | uvicorn bind port on `127.0.0.1` |
| `DATA_PATH` | 1 | no | Hub root (default `~/hub/knowledge/animaya`) |
| `ANIMAYA_EVENTS_LOG` | 5 | no | Events log override for tests |

## Deploy Checklist

1. `scripts/setup.sh` (writes service unit, creates `.venv`).
2. Edit `.env`, add `SESSION_SECRET=$(openssl rand -hex 32)`, `TELEGRAM_OWNER_ID=<numeric>`, `TELEGRAM_BOT_USERNAME=<bot>` alongside Phase 1/2 tokens.
3. `systemctl --user restart animaya`.
4. Register reverse-proxy hostname in Caddy/Voidnet (TLS termination).
5. Open `@BotFather` → `/mybots` → bot → Bot Settings → Domain → paste public hostname.
6. Visit `https://your-host/login` and authenticate.

## Deviations from Plan

1. **[Rule 3 - Blocker] `tests/dashboard/` lacked `tmp_hub_dir` and `valid_module_dir` fixtures** — they live in `tests/modules/conftest.py` and aren't reachable from sibling `tests/dashboard/`. Added both to `tests/dashboard/conftest.py` (mirror of the modules fixtures, shared fixture root). Same semantics, no new test helpers introduced.
2. **[Rule 3 - Blocker] `tests/test_skeleton.py` regression tests needed adjustment** — plan line "must remain green after Plan 07's refactor" assumed no edit; in reality, three of them (`test_data_dir_created`, `test_main_calls_build_app_with_token`, `test_main_calls_run_polling`, `test_assemble_claude_md_before_build_app`) patched `app.run_polling` which no longer exists. Updated each to stub `uvicorn.Server`, `build_dashboard_app`, and an `asyncio.Event` that self-sets, so `main()` returns after confirming `updater.start_polling()` was awaited. No semantic regression — the tests still assert the same invariants (token passed, assembler runs first, data dir created).
3. **[Rule 2 - Critical] Emit wrapping** — plan specified raw `emit(...)` calls but telemetry must never break a successful install or a normal message turn (T-05-07-02 family — info disclosure if log write fails weirdly mid-tx). Wrapped each emit call in `try/except Exception: logger.debug(...)` so a bad path / quota / permission issue on `events.log` degrades gracefully. Acceptance criteria unchanged.
4. **Auth gates:** None encountered — the three env vars validated by `main()` are owner-provided config, not interactive auth.

No architectural deviations (Rule 4 not triggered).

## Threat Model — Mitigations Applied

| Threat ID | Disposition | Where Mitigated |
|-----------|-------------|-----------------|
| T-05-07-01 (E: no SESSION_SECRET → forged sessions) | mitigated | `REQUIRED_ENV_VARS` check in `main()` — `sys.exit(1)` before any network bind. Covered by `test_main_validates_session_secret` + parametrized cases. |
| T-05-07-02 (I: bot token in logs) | mitigated | Bridge emitters use fixed strings (`"message received"` / `"reply sent"`) + only `chat_id` detail. Error emit uses `type(err).__name__` + `str(err)`. No SDK error carries the bot token. |
| T-05-07-03 (T: forwarded-IP spoofing) | mitigated | `uvicorn.Config(proxy_headers=True, forwarded_allow_ips="127.0.0.1")` — headers trusted only from local Caddy. |
| T-05-07-04 (D: public bind) | mitigated | `host="127.0.0.1"`. Never exposed. |
| T-05-07-05 (T: event-log injection) | mitigated | Inherited from Plan 05-01's `json.dumps(record)` — one physical line per record; embedded newlines escaped. No new injection surface. |
| T-05-07-06 (D: task leak on SIGTERM) | mitigated | `signal.add_signal_handler` → `stop_event.set()`; `finally` block stops updater + PTB + sets `server.should_exit` + `await uvicorn_task`. |
| T-05-07-07 (E: CSRF via hostile widget domain) | mitigated | BotFather `/setdomain` step documented in README. Telegram refuses to sign callbacks for unregistered domains. |
| T-05-07-08 (D: dep drift) | accepted | pyproject pins unchanged. |

## Deferred Items

- **HTMX SRI hash** (Plan 05-03 follow-up) — not in Plan 05-07's scope. Documented in 05-03 summary; no Plan 05-07 obligation.

## Commits

| Commit | Type | Summary |
|--------|------|---------|
| `57ff0ed` | test | Failing tests for event emitters + main wiring (RED, 12 tests) |
| `5de9dcc` | feat | Wire bot.events emitters in bridge + lifecycle + assembler (GREEN emitter suite) |
| `b7b7b15` | feat | main.py runs uvicorn + PTB in one loop; README deploy + setdomain note |

## Verification

| Check | Result |
|-------|--------|
| `.venv/bin/pytest tests/ -q` | 228 passed |
| `.venv/bin/pytest tests/dashboard/test_event_emitters.py tests/dashboard/test_main_wiring.py tests/test_skeleton.py -q` | 24 passed |
| `.venv/bin/ruff check bot/main.py bot/bridge/telegram.py bot/modules/lifecycle.py bot/modules/assembler.py bot/events.py` | clean |
| grep `setdomain` + `SESSION_SECRET` in `README.md` | 4 mentions |
| grep `SESSION_SECRET` in `scripts/setup.sh` | 2 mentions |
| `REQUIRED_ENV_VARS` length | 5 |
| `bot/main.py` contains `uvicorn.Config`, `proxy_headers=True`, `forwarded_allow_ips`, `post_init=_post_init` | all found |

Pre-existing ruff errors in `bot/features/search.py` et al. are out-of-scope (not touched by this plan).

## Self-Check: PASSED

- FOUND: `bot/main.py` (rewritten; contains `uvicorn.Server`, `rotate_events`, 5-var `REQUIRED_ENV_VARS`, `post_init=_post_init`)
- FOUND: emitter `from bot.events import emit as _emit_event` in `bot/bridge/telegram.py`, `bot/modules/lifecycle.py`, `bot/modules/assembler.py`
- FOUND: `README.md` with `/setdomain`, `SESSION_SECRET`, `TELEGRAM_OWNER_ID`, `TELEGRAM_BOT_USERNAME`
- FOUND: `scripts/setup.sh` appended block with the three Phase-5 env hints
- FOUND: `tests/dashboard/test_event_emitters.py` (6 tests, all green)
- FOUND: `tests/dashboard/test_main_wiring.py` (6 tests, all green)
- FOUND commits: `57ff0ed` (test RED), `5de9dcc` (feat emitters), `b7b7b15` (feat main + README)
- VERIFIED: full test suite 228 passed, ruff clean on modified files
