---
phase: 08-bridge-extraction-supervisor-cutover
verified: 2026-04-15T00:00:00Z
status: human_needed
score: 14/15 must-haves verified
overrides_applied: 0
gaps:
  - truth: "Telethon e2e test file exists and is collectable"
    status: failed
    reason: "tests/telethon/test_bridge_lifecycle_e2e.py and tests/telethon/ directory do not exist"
    artifacts:
      - path: "tests/telethon/test_bridge_lifecycle_e2e.py"
        issue: "File and parent directory missing — Plan 03 Task 2 was not executed"
    missing:
      - "Create tests/telethon/ directory"
      - "Create tests/telethon/test_bridge_lifecycle_e2e.py with SC#3 scenario (install → roundtrip → uninstall → silence → reinstall)"
deferred:
  - truth: "BRDG-03: Master disable toggle stops polling without uninstalling (re-enable resumes)"
    addressed_in: "Phase 10"
    evidence: "REQUIREMENTS.md traceability: 'BRDG-03 | Phase 10 — Bridge Settings, Non-Owner Access & Tool-Use Display'. Plans 01-03 only laid xfail scaffolds for BRDG-03 — full implementation is Phase 10."
  - truth: "BRDG-04: Uninstall revokes owner (purge owner claim, full artifact removal)"
    addressed_in: "Phase 10"
    evidence: "REQUIREMENTS.md traceability: 'BRDG-04 | Phase 10 — Bridge Settings, Non-Owner Access & Tool-Use Display'. Phase 8 implements lifecycle.uninstall purge of config.json/state.json but owner-revoke and full artifact removal are Phase 10."
human_verification:
  - test: "Telethon smoke — install bridge module → send message → receive reply → uninstall → confirm silence → reinstall → receive reply"
    expected: "All five stages complete without error; uninstall stops polling (TimeoutError on silence check); reinstalled bridge answers"
    why_human: "Requires live animaya-dev LXC (LXC 205 on tower), real Telegram bot token, and deployed bot instance"
  - test: "Dashboard module install/uninstall via UI at animaya-dev.makscee.ru/modules"
    expected: "Bridge module shows in module list; install and uninstall buttons trigger correct lifecycle; /api/modules returns runtime_entry populated"
    why_human: "Requires live deployed instance with Caddy and running dashboard"
  - test: "Boot order on LXC — confirm log sequence: assemble_claude_md → migrate_bridge_rename (first boot only) → dashboard uvicorn → supervisor start"
    expected: "journalctl shows correct order; second boot shows no migration log (idempotent)"
    why_human: "Requires live deployment and log inspection on LXC 205"
---

# Phase 8: Bridge Extraction & Supervisor Cutover — Verification Report

**Phase Goal:** Telegram bridge starts and stops as an installable runtime module instead of hard-wired boot code, so every later phase plugs into the same lifecycle surface.
**Verified:** 2026-04-15
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | ModuleManifest accepts optional runtime_entry field without breaking existing manifests | VERIFIED | `bot/modules/manifest.py:76` — `runtime_entry: str | None = Field(default=None, ...)` with namespace validator |
| 2 | AppContext frozen dataclass exists with data_path, stop_event, event_bus, dashboard_app | VERIFIED | `bot/modules/context.py` — `@dataclass(frozen=True)` with all 4 fields confirmed |
| 3 | Supervisor.start_all iterates registry, calls on_start for runtime_entry modules | VERIFIED | `bot/modules/supervisor.py:50` — calls `read_registry`, imports via `importlib.import_module`, stores handles |
| 4 | Supervisor.stop_all calls on_stop in reverse registration order | VERIFIED | `bot/modules/supervisor.py:78` — `reversed(list(self._handles.items()))` |
| 5 | lifecycle.install() writes runtime_entry into registry entry | VERIFIED | `bot/modules/lifecycle.py:213` — `"runtime_entry": manifest.runtime_entry` in entry dict |
| 6 | telegram_bridge runtime adapter has on_start and on_stop | VERIFIED | `bot/modules_runtime/telegram_bridge.py:14,46` — both async functions present |
| 7 | on_stop order: updater.stop → stop → shutdown | VERIFIED | `bot/modules_runtime/telegram_bridge.py:55,59,63` — explicit three-step sequence with per-step try/except |
| 8 | modules/telegram-bridge/ exists (renamed from modules/bridge/) | VERIFIED | Directory exists with manifest.json, install.sh, uninstall.sh, prompt.md; modules/bridge/ absent |
| 9 | manifest.json declares runtime_entry: bot.modules_runtime.telegram_bridge | VERIFIED | `modules/telegram-bridge/manifest.json` — `"runtime_entry": "bot.modules_runtime.telegram_bridge"` |
| 10 | migrate_bridge_rename handles legacy registry entries | VERIFIED | `bot/modules/registry.py:141` — `def migrate_bridge_rename(data_path: Path) -> bool` |
| 11 | lifecycle.uninstall calls supervisor stop before uninstall.sh | VERIFIED | `bot/modules/lifecycle.py:349-360` — Step 1 is on_stop via supervisor handle before uninstall.sh |
| 12 | lifecycle.uninstall purges config.json and state.json | VERIFIED | `bot/modules/lifecycle.py:395-398` — explicit purge of both files |
| 13 | bot/main.py has no import of bot.bridge.telegram in core boot path | VERIFIED | grep returns no match; only deferred import inside `bot/modules_runtime/telegram_bridge.py:33` with noqa marker |
| 14 | TELEGRAM_BOT_TOKEN not in REQUIRED_ENV_VARS | VERIFIED | `REQUIRED_ENV_VARS = ("CLAUDE_CODE_OAUTH_TOKEN", "SESSION_SECRET", "TELEGRAM_OWNER_ID", "DASHBOARD_TOKEN")` — token absent |
| 15 | Telethon e2e test file (SC#3 automated smoke) exists | FAILED | `tests/telethon/` directory does not exist; `tests/telethon/test_bridge_lifecycle_e2e.py` missing |

**Score:** 14/15 truths verified

### Deferred Items

Items not yet met but explicitly addressed in later milestone phases.

| # | Item | Addressed In | Evidence |
|---|------|-------------|----------|
| 1 | BRDG-03: Master disable toggle stops polling without uninstalling | Phase 10 | REQUIREMENTS.md: "BRDG-03 \| Phase 10 — Bridge Settings, Non-Owner Access & Tool-Use Display" |
| 2 | BRDG-04: Uninstall revokes owner, removes all module artifacts | Phase 10 | REQUIREMENTS.md: "BRDG-04 \| Phase 10 — Bridge Settings, Non-Owner Access & Tool-Use Display" |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `bot/modules/context.py` | AppContext frozen dataclass | VERIFIED | `@dataclass(frozen=True)` class AppContext with 4 fields |
| `bot/modules/supervisor.py` | Supervisor with start_all/stop_all/get_handle | VERIFIED | All three methods; importlib.import_module; reversed stop order; 5 lifecycle events |
| `bot/modules/manifest.py` | runtime_entry optional field | VERIFIED | Field + field_validator with `^bot\.` namespace regex |
| `bot/modules/lifecycle.py` | install propagates runtime_entry; async uninstall with on_stop | VERIFIED | Both present; uninstall is `async def` with `supervisor: "Supervisor | None" = None` |
| `bot/modules_runtime/telegram_bridge.py` | on_start/on_stop adapter | VERIFIED | on_start validates token, deferred import, explicit PTB lifecycle; on_stop three-step |
| `modules/telegram-bridge/manifest.json` | Renamed manifest with runtime_entry | VERIFIED | name=telegram-bridge, runtime_entry=bot.modules_runtime.telegram_bridge |
| `bot/modules/registry.py` | migrate_bridge_rename helper | VERIFIED | `def migrate_bridge_rename` at line 141 |
| `bot/main.py` | Supervisor-driven _run(), no bridge import | VERIFIED | uvicorn first, then supervisor.start_all; no bot.bridge.telegram import |
| `tests/modules/test_supervisor.py` | Supervisor unit tests | VERIFIED | 9 test functions |
| `tests/modules/test_bridge_module.py` | BRDG-01 + migration tests | VERIFIED | 12 test functions |
| `tests/modules/test_supervisor_cutover.py` | BRDG-03 tests (was xfail, now green) | VERIFIED | 13 test functions, no remaining xfail markers |
| `tests/modules/test_bridge_config_source.py` | BRDG-04 env/seed tests | VERIFIED | 5 test functions, no remaining xfail markers |
| `tests/test_main_boot.py` | Boot-order + env-matrix tests | VERIFIED | 8 test functions |
| `tests/telethon/test_bridge_lifecycle_e2e.py` | SC#3 Telethon smoke | MISSING | Directory and file do not exist |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `bot/modules/supervisor.py` | `bot/modules/registry.py` | `read_registry` | WIRED | Line 50: `reg = read_registry(ctx.data_path)` |
| `bot/modules/supervisor.py` | importlib | `importlib.import_module(runtime_entry)` | WIRED | Line 60: `mod = importlib.import_module(runtime_entry)` |
| `bot/modules/lifecycle.py` | `manifest.runtime_entry` | install() copies to registry | WIRED | Line 213: `"runtime_entry": manifest.runtime_entry` |
| `bot/modules_runtime/telegram_bridge.py` | `bot.bridge.telegram.build_app` | deferred import inside on_start | WIRED | Line 33: `from bot.bridge.telegram import build_app  # noqa: PLC0415` |
| `bot/modules/lifecycle.py uninstall()` | `supervisor.get_handle + on_stop` | pre-step before uninstall.sh | WIRED | Lines 349-360: handle lookup → on_stop → continue |
| `modules/telegram-bridge/manifest.json` | `bot.modules_runtime.telegram_bridge` | runtime_entry field | WIRED | JSON field confirmed |
| `bot/main.py _run()` | `Supervisor.start_all` | `await supervisor.start_all(ctx)` | WIRED | Line 188 |
| `bot/main.py _run()` | `migrate_bridge_rename` | called at boot step 2 | WIRED | Line 165 |
| `bot/main.py token seed` | `modules/telegram-bridge/config.json` | atomic write when env set | WIRED | `_seed_telegram_bridge_token()` at line 55 |

### Boot Order Verification

Confirmed from `bot/main.py` line numbers:

1. Dashboard uvicorn task started (line 161: `asyncio.create_task(server.serve())`)
2. migrate_bridge_rename called (line 165)
3. _seed_telegram_bridge_token called (line 166)
4. AppContext built (line 181)
5. `await supervisor.start_all(ctx)` (line 188)
6. `await stop_event.wait()` (line 192)
7. `await supervisor.stop_all()` (line 195)
8. `server.should_exit = True; await uvicorn_task` (lines 196-197)

D-8.7 contract satisfied: dashboard up before supervisor; supervisor.stop_all before uvicorn teardown.

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| BRDG-01 | 08-01, 08-02, 08-03 | Bridge as runtime module; main.py defers polling | SATISFIED | Supervisor lifecycle wired; no bot.bridge.telegram import in main.py boot path; module manifest with runtime_entry |
| BRDG-03 | 08-01 (scaffold only) | Master disable toggle | DEFERRED | Phase 10 per REQUIREMENTS.md; Phase 8 only lands xfail scaffolds that are now green stubs |
| BRDG-04 | 08-01 (scaffold only) | Uninstall stops polling, purges state, revokes owner | PARTIAL | lifecycle.uninstall purges config.json/state.json (Phase 8 contribution); owner-revoke and full artifact removal deferred to Phase 10 |

### Anti-Patterns Found

| File | Pattern | Severity | Impact |
|------|---------|----------|--------|
| None found | — | — | No TODO/FIXME/placeholder/stub returns in core files |

### Human Verification Required

#### 1. Telethon Smoke — SC#3 End-to-End Bridge Lifecycle

**Test:** Run `python -m pytest tests/telethon/test_bridge_lifecycle_e2e.py -v` with `TEST_BOT_TOKEN` set (after the missing test file is created). Alternatively run manually: install bridge with test token → send "ping-phase-8" via Telegram → confirm reply → uninstall → send "silence-check" → confirm no reply (timeout) → reinstall → send again → confirm reply.
**Expected:** Bot replies within 60 seconds at each roundtrip stage; silence stage raises TimeoutError (no zombie polling after uninstall).
**Why human:** Requires live animaya-dev LXC 205 (`ssh root@tower 'pct exec 205 ...'`), real Telegram bot token, and network connectivity to Telegram.

#### 2. Live Boot Order Confirmation on animaya-dev LXC

**Test:** Deploy latest code to LXC 205, restart animaya service, tail journalctl.
**Expected:** Logs show (in order): CLAUDE.md assembly, "Migrated module 'bridge' -> 'telegram-bridge'" (first boot only), uvicorn startup, "module.starting telegram-bridge", "telegram-bridge polling started". Second restart shows no migration log.
**Why human:** Requires live deployed instance.

#### 3. Dashboard Module UI

**Test:** Open dashboard at deployed URL, navigate to modules page, install and uninstall telegram-bridge via UI buttons.
**Expected:** Module shows with runtime_entry populated in /api/modules response; install/uninstall trigger correct supervisor lifecycle.
**Why human:** Visual UI flow requiring live deployed instance.

### Gaps Summary

One gap blocks the automated SC#3 test artifact: `tests/telethon/test_bridge_lifecycle_e2e.py` was specified in Plan 03 Task 2 with detailed acceptance criteria, but neither the file nor its parent directory (`tests/telethon/`) was created. The automated test is the mechanized form of the human Telethon smoke — without it, SC#3 has no durable regression guard. The core functionality (lifecycle.install, lifecycle.uninstall with on_stop, Supervisor wiring) is all in place; the missing piece is the test file that validates the end-to-end scenario.

All other 14/15 must-haves are fully implemented and wired. The phase goal — bridge as installable module with clean lifecycle surface — is structurally achieved. The missing Telethon test file needs to be created before the phase can be fully closed.

---

_Verified: 2026-04-15_
_Verifier: Claude (gsd-verifier)_
