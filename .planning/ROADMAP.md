# Roadmap: Animaya v2

## Overview

Animaya v2 is a fresh rewrite of a Docker-based personal AI assistant into an LXC-native, modular platform. The journey starts with a working install script and systemd service, adds a streaming Telegram bridge, builds the module system machinery, ships three first-party modules (identity, memory, git versioning), then wraps everything in a web dashboard for management and configuration.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Install & Foundation** - Working install script + systemd service on a Claude Box (completed 2026-04-13)
- [ ] **Phase 2: Telegram Bridge** - Streaming Claude responses over Telegram with async safety
- [ ] **Phase 3: Module System** - Manifest-driven module lifecycle with registry and CLAUDE.md assembler
- [ ] **Phase 4: First-Party Modules** - Identity, memory, and git-versioning modules fully operational
- [ ] **Phase 5: Web Dashboard** - FastAPI + HTMX dashboard for bot management and module configuration

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
**Plans:** 1/2 plans executed
Plans:
- [x] 02-01-PLAN.md — Port v1 bridge modules (formatting, telegram, claude_query) with tests
- [ ] 02-02-PLAN.md — Wire bridge into main.py and verify end-to-end

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
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md &mdash; Port v1 bridge modules (formatting, telegram, claude_query) with tests
- [ ] 02-02-PLAN.md &mdash; Wire bridge into main.py and verify end-to-end

### Phase 4: First-Party Modules
**Goal**: Identity, memory, and git versioning modules are installed and enrich every Claude interaction
**Depends on**: Phase 3
**Requirements**: IDEN-01, IDEN-02, IDEN-03, IDEN-04, MEMO-01, MEMO-02, MEMO-03, MEMO-04, GITV-01, GITV-02, GITV-03
**Success Criteria** (what must be TRUE):
  1. New user completes onboarding and their identity appears in Claude's system prompt on the next message
  2. Assistant writes a memory fact; that fact persists in Hub knowledge/memory/ and appears in the next session's context
  3. Memory and identity files are git-committed on the configured interval without conflicts
  4. User reconfigures identity from the dashboard without reinstalling the module; new identity is reflected immediately
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md &mdash; Port v1 bridge modules (formatting, telegram, claude_query) with tests
- [ ] 02-02-PLAN.md &mdash; Wire bridge into main.py and verify end-to-end
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
**Plans**: 2 plans
Plans:
- [ ] 02-01-PLAN.md &mdash; Port v1 bridge modules (formatting, telegram, claude_query) with tests
- [ ] 02-02-PLAN.md &mdash; Wire bridge into main.py and verify end-to-end
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Install & Foundation | 2/2 | Complete    | 2026-04-13 |
| 2. Telegram Bridge | 1/2 | In Progress|  |
| 3. Module System | 0/TBD | Not started | - |
| 4. First-Party Modules | 0/TBD | Not started | - |
| 5. Web Dashboard | 0/TBD | Not started | - |
