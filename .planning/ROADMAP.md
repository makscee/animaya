# Roadmap: Animaya v2

## Overview

Animaya v2 is a fresh rewrite of a Docker-based personal AI assistant into an LXC-native, modular platform. The journey starts with a working install script and systemd service, adds a streaming Telegram bridge, builds the module system machinery, ships three first-party modules (identity, memory, git versioning), then wraps everything in a web dashboard for management and configuration.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Install & Foundation** - Working install script + systemd service on a Claude Box (completed 2026-04-13)
- [x] **Phase 2: Telegram Bridge** - Streaming Claude responses over Telegram with async safety (completed 2026-04-13)
- [ ] **Phase 3: Module System** - Manifest-driven module lifecycle with registry and CLAUDE.md assembler
- [ ] **Phase 4: First-Party Modules** - Identity, memory, and git-versioning modules fully operational
- [ ] **Phase 5: Web Dashboard** - FastAPI + HTMX dashboard for bot management and module configuration
- [x] **Phase 6: Telethon Test Harness** - Claude Code can drive end-to-end Telegram conversations against the deployed bot (completed 2026-04-14)
- [ ] **Phase 7: Close v1.0 Audit Gaps** - Retroactive VERIFICATION.md for phases 02/03/05, Nyquist sign-off, REQUIREMENTS.md bookkeeping

## Phase Details

### Phase 1: Install & Foundation
**Goal**: Animaya installs cleanly on an existing Claude Box and runs as a stable system service
**Depends on**: Nothing (first phase)
**Requirements**: INST-01, INST-02, INST-03, INST-04
**Success Criteria** (what must be TRUE):
  1. User runs `git clone` + `setup.sh` on a Claude Box and the service starts without manual intervention
  2. Animaya restarts automatically after a crash or reboot
  3. Logs are accessible via `journalctl` without custom tooling
  4. Claude SDK subprocess does not inherit CLAUDECODE=1 and hangs are absent
**Plans:** 2/2 plans complete
Plans:
- [x] 01-01-PLAN.md — Install scripts (setup.sh, run.sh, systemd service unit, tests)
- [x] 01-02-PLAN.md — Skeleton bot entry point (async main, CLAUDE.md assembler stub, tests)

### Phase 2: Telegram Bridge
**Goal**: Users can send messages via Telegram and receive streamed Claude Code responses reliably
**Depends on**: Phase 1
**Requirements**: TELE-01, TELE-02, TELE-03, TELE-04, TELE-05
**Success Criteria** (what must be TRUE):
  1. User sends a Telegram message and receives a Claude response (streamed, not batched)
  2. Bridge acknowledges messages immediately — no Telegram retry / duplicate response
  3. Typing indicator appears while Claude is processing
  4. Responses longer than Telegram's limit arrive as multiple sequential messages
  5. Errors surface as a user-visible Telegram message rather than silent failure
**Plans:** 2/2 plans complete
Plans:
- [x] 02-01-PLAN.md — Port v1 bridge modules (formatting, telegram, claude_query) with tests
- [x] 02-02-PLAN.md — Wire bridge into main.py and verify end-to-end

### Phase 3: Module System
**Goal**: Modules can be installed, configured, and uninstalled through a clean lifecycle contract with zero artifact leakage
**Depends on**: Phase 2
**Requirements**: MODS-01, MODS-02, MODS-03, MODS-04, MODS-05, MODS-06
**Success Criteria** (what must be TRUE):
  1. A module folder with a valid manifest.json passes pydantic validation; an invalid manifest is rejected with a clear error
  2. Running a module's install.sh and uninstall.sh leaves no stale state in the Hub or filesystem
  3. Registry tracks installed modules; querying it returns current state
  4. CLAUDE.md assembler produces a merged prompt containing core + all installed module prompts
  5. Modules interact only through shared Hub files — no cross-module code imports exist
**Plans:** 7 plans
Plans:
- [x] 03-00-PLAN.md — Wave 0 infra: add pydantic dep, tests/modules/ scaffolding, fixtures, test stubs
- [x] 03-01-PLAN.md — ModuleManifest pydantic model + validate_manifest (MODS-01)
- [x] 03-02-PLAN.md — Registry read/write/query API with atomic JSON (MODS-03)
- [x] 03-03-PLAN.md — install/uninstall lifecycle + env injection + auto-rollback + internal CLI (MODS-02)
- [x] 03-04-PLAN.md — CLAUDE.md assembler (install-order + XML wrap) + wire into main.py (MODS-04)
- [x] 03-05-PLAN.md — Bridge module dogfood + roundtrip e2e test + module authoring guide (MODS-05)
- [x] 03-06-PLAN.md — AST-based isolation test (MODS-06)

### Phase 4: First-Party Modules
**Goal**: Identity, memory, and git versioning modules are installed and enrich every Claude interaction
**Depends on**: Phase 3
**Requirements**: IDEN-01, IDEN-02, IDEN-03, IDEN-04, MEMO-01, MEMO-02, MEMO-03, MEMO-04, GITV-01, GITV-02, GITV-03
**Success Criteria** (what must be TRUE):
  1. New user completes onboarding and their identity appears in Claude's system prompt on the next message
  2. Assistant writes a memory fact; that fact persists in Hub knowledge/memory/ and appears in the next session's context
  3. Memory and identity files are git-committed on the configured interval without conflicts
  4. User reconfigures identity via the `/identity` Telegram command without reinstalling the module; new identity is reflected immediately. (Dashboard reconfigure variant is Phase 5 scope per D-04.)
**Plans:** 4 plans
Plans:
- [x] 04-00-PLAN.md — Wave 0: test infrastructure, Phase 4 fixtures, lock assumptions A1/A2/A7
- [x] 04-01-PLAN.md — Identity module: lifecycle, runtime, query-time injection, /identity ConversationHandler
- [x] 04-02-PLAN.md — Git-versioning module: asyncio commit loop, in-process Lock, post_init wiring
- [x] 04-03-PLAN.md — Memory module: Haiku consolidation, post-reply trigger, end-to-end smoke
**UI hint**: yes

### Phase 5: Web Dashboard
**Goal**: Users can view bot status, manage modules, and configure settings through a browser UI
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04, DASH-05, DASH-06
**Success Criteria** (what must be TRUE):
  1. User opens the dashboard URL, authenticates via Telegram Login Widget, and reaches the home screen
  2. Dashboard shows live bot status (running / stopped) and recent activity without a page refresh
  3. User installs a module from the UI; it appears as installed and its system prompt is active
  4. User uninstalls a module from the UI; it disappears from installed list and leaves no artifacts
  5. Module with a config_schema renders a form; user submits changes and they take effect
**Plans:** 8 plans
Plans:
- [ ] 05-00-PLAN.md — Wave 0: add python-multipart + jsonschema deps, delete v1 dashboard, create tests/dashboard/ fixtures
- [ ] 05-01-PLAN.md — bot/events.py JSONL emitter + tail + rotate (DASH-03)
- [ ] 05-02-PLAN.md — Telegram Login Widget HMAC + itsdangerous session cookie + require_owner dep (DASH-02)
- [ ] 05-03-PLAN.md — FastAPI app factory + base templates + static CSS + /login /auth/telegram /logout (DASH-01, DASH-02)
- [ ] 05-04-PLAN.md — Home page with status strip + activity feed + error feed + 5s HTMX polling (DASH-03)
- [ ] 05-05-PLAN.md — /modules browse + async install/uninstall job runner with 1s polling + 409 concurrency (DASH-04, DASH-05)
- [ ] 05-06-PLAN.md — Config form renderer: JSON Schema to HTMX form with server-side jsonschema validation (DASH-06)
- [ ] 05-07-PLAN.md — Wire uvicorn + PTB in one event loop, event emitters in bridge/modules/assembler, README deploy note (DASH-01, DASH-03)
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Install & Foundation | 2/2 | Complete    | 2026-04-13 |
| 2. Telegram Bridge | 2/2 | Complete   | 2026-04-13 |
| 3. Module System | 0/TBD | Not started | - |
| 4. First-Party Modules | 0/4 | Not started | - |
| 5. Web Dashboard | 0/TBD | Not started | - |

### Phase 6: Telethon test harness at hub level for end-to-end Telegram bot testing from Claude Code

**Goal:** Claude Code (running at ~/hub) can drive real Telegram conversations against the deployed Animaya bot programmatically — send a message, receive the streamed reply, assert on its content — so bot behavior can be tested end-to-end without manual Telegram interaction.
**Depends on:** Phase 2
**Requirements**: TEST-01 (Telethon auth + session persistence), TEST-02 (async test driver API), TEST-03 (smoke-test text round-trip)
**Success Criteria** (what must be TRUE):
  1. Telethon client authenticates as a user account using credentials from env and persists its session file at hub level
  2. A helper API exposes `send_to_bot(text)` and `wait_for_reply(timeout)` so tests read like conversation scripts
  3. A smoke-test script sends a text message to the deployed bot and asserts it receives a non-empty streamed reply within a timeout
  4. Harness lives under ~/hub (not inside animaya repo) and points at the bot via configurable username
  5. Running the smoke test from Claude Code prints PASS/FAIL with the bot's actual response text captured
**Plans:** 1/1 plans complete
Plans:
- [x] 06-01-PLAN.md — Telethon harness at ~/hub/telethon/ (client, driver, smoke test, README) — completed 2026-04-14, smoke test PASSES against @mks_test_assistant_bot

### Phase 7: Close v1.0 Audit Gaps

**Goal:** Close all documentation/verification gaps identified by `v1.0-MILESTONE-AUDIT.md` so milestone can be archived with clean records. No new feature code — retroactive verification of already-shipped work.
**Depends on:** Phase 6
**Requirements:** TELE-01..05, MODS-01..06, DASH-01..06 (retroactive verification); TEST-01..03 (traceability insertion)
**Gap Closure:** Closes gaps from `.planning/v1.0-MILESTONE-AUDIT.md`
**Success Criteria** (what must be TRUE):
  1. `02-VERIFICATION.md`, `03-VERIFICATION.md`, `05-VERIFICATION.md` exist with all requirements SATISFIED or explicit gap acknowledgement
  2. DASH-02, DASH-04, DASH-05 verified satisfied against shipped code in Phase 5, or marked unsatisfied with evidence
  3. `02-VALIDATION.md` and `06-VALIDATION.md` retroactively created; Nyquist sign-off done for all six phases (01/02/03/04/05/06)
  4. REQUIREMENTS.md checkboxes match shipped reality for all 27+3 REQ-IDs; traceability table reflects true phase assignment and status
  5. Re-running `/gsd-audit-milestone 1.0` yields `status: passed`
**Plans:** 5 plans
Plans:
- [ ] 07-01-PLAN.md — Retroactive VERIFICATION.md for Phase 02 (TELE-01..05) via gsd-verifier agent against shipped bridge code
- [ ] 07-02-PLAN.md — Retroactive VERIFICATION.md for Phase 03 (MODS-01..06) via gsd-verifier agent against shipped module system code
- [ ] 07-03-PLAN.md — Retroactive VERIFICATION.md for Phase 05 (DASH-01..06, including unresolved DASH-02/04/05) via gsd-verifier agent against shipped dashboard code
- [ ] 07-04-PLAN.md — Missing VALIDATION.md (02, 06) + Nyquist sign-off for all phases
- [ ] 07-05-PLAN.md — REQUIREMENTS.md bookkeeping: checkboxes, traceability table, TEST-01..03 entry
