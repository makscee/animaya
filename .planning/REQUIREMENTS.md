# Requirements: Animaya v2

**Defined:** 2026-04-13
**Core Value:** Any user can spin up a personal AI assistant by installing Animaya on their Claude Box, then customize it module-by-module — each module is self-contained, configurable, and reversible.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Install

- [x] **INST-01**: User can install Animaya on a Claude Box via `git clone` + `setup.sh`
- [x] **INST-02**: Setup script configures Python venv, installs dependencies, creates systemd service
- [x] **INST-03**: Animaya runs as a systemd unit with auto-restart and log management
- [x] **INST-04**: Setup script sanitizes CLAUDECODE=1 env var to prevent SDK hangs

### Telegram Bridge

- [x] **TELE-01**: User can send a message via Telegram and receive a streamed Claude response
- [x] **TELE-02**: Bridge uses asyncio.create_task() for non-blocking response handling
- [x] **TELE-03**: Bridge shows typing indicator while Claude is processing
- [x] **TELE-04**: Long responses are chunked and sent as multiple Telegram messages
- [x] **TELE-05**: Bridge handles errors gracefully and notifies user of failures

### Web Dashboard

- [x] **DASH-01**: Dashboard runs on FastAPI + Jinja2 + HTMX (no npm build toolchain)
- [x] **DASH-02**: Dashboard authenticates users via Telegram Login Widget
- [x] **DASH-03**: Dashboard shows bot status and health (running state, recent activity, errors)
- [x] **DASH-04**: Dashboard displays list of available and installed modules
- [x] **DASH-05**: User can install and uninstall modules from the dashboard UI
- [x] **DASH-06**: User can configure module settings via auto-generated forms from config_schema

### Module System

- [x] **MODS-01**: Each module is a folder with a manifest.json validated by pydantic
- [x] **MODS-02**: Each module has install.sh and uninstall.sh lifecycle scripts
- [x] **MODS-03**: Module registry (registry.json) tracks installed modules and their state
- [x] **MODS-04**: CLAUDE.md assembler merges core + installed module system prompts
- [x] **MODS-05**: Uninstall leaves zero artifacts — enforced at manifest schema level
- [x] **MODS-06**: Modules communicate only through shared Hub files, no inter-module code imports

### Identity Module

- [x] **IDEN-01**: User completes onboarding flow defining who they are and who the assistant is
- [x] **IDEN-02**: Identity data is stored as markdown in Hub knowledge/identity/
- [x] **IDEN-03**: Identity is injected into system prompt via XML-delimited blocks
- [x] **IDEN-04**: User can reconfigure identity from dashboard without reinstalling

### Memory Module

- [x] **MEMO-01**: Assistant can read and write persistent memory as markdown files in Hub knowledge/memory/
- [x] **MEMO-02**: Memory files are git-versioned with full audit trail
- [x] **MEMO-03**: Core summary file provides session context (who the user is, key facts)
- [x] **MEMO-04**: Memory module injects relevant context into system prompt

### Git Versioning Module

- [x] **GITV-01**: Module auto-commits data changes in Hub knowledge/ on a configurable interval
- [x] **GITV-02**: Single-committer pattern prevents concurrent write conflicts
- [x] **GITV-03**: Commits are scoped to module subdirectories for clean history

### Telethon Test Harness

- [x] **TEST-01**: Telethon auth + session persistence — harness authenticates via MTProto and reuses session headlessly
- [x] **TEST-02**: Async test driver API — `send_to_bot`, `wait_for_reply`, `assert_contains`, `start_listening`, `Listener`, `resolve_bot_entity` exported
- [x] **TEST-03**: Smoke-test text round-trip — harness sends prompt, receives bot reply, asserts content, exits 0/1

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Voice & Media

- **VOIC-01**: User can send voice messages transcribed via Whisper API
- **VOIC-02**: User can request image generation via Gemini API

### Search

- **SRCH-01**: User can search memory via semantic/vector search
- **SRCH-02**: Search results are ranked by relevance

### Advanced Modules

- **ADVM-01**: Skill files (~skill.md) — users can teach assistant reusable procedures
- **ADVM-02**: Watchdog hot-detection of new modules in modules/ directory

### Platform Integration

- **PLAT-01**: Voidnet web UI can trigger Animaya install on a Claude Box
- **PLAT-02**: Module install/uninstall can be triggered via Voidnet API

## Out of Scope

| Feature | Reason |
|---------|--------|
| Docker-based deployment | Replaced by LXC/Claude Box model |
| Custom Spaces memory module | Replaced by Hub-style knowledge/ approach |
| Multi-user provisioning UI | Voidnet handles provisioning, not Animaya |
| Database/vector store | Markdown + git is sufficient for v1 scale |
| npm build toolchain | HTMX via CDN eliminates frontend build step |
| Inter-module code dependencies | Architectural constraint — modules share files only |
| Mobile app | Telegram is the primary mobile interface |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INST-01 | Phase 1 | Complete |
| INST-02 | Phase 1 | Complete |
| INST-03 | Phase 1 | Complete |
| INST-04 | Phase 1 | Complete |
| TELE-01 | Phase 2 | Complete |
| TELE-02 | Phase 2 | Complete |
| TELE-03 | Phase 2 | Complete |
| TELE-04 | Phase 2 | Complete |
| TELE-05 | Phase 2 | Complete |
| MODS-01 | Phase 3 | Complete |
| MODS-02 | Phase 3 | Complete |
| MODS-03 | Phase 3 | Complete |
| MODS-04 | Phase 3 | Complete |
| MODS-05 | Phase 3 | Complete |
| MODS-06 | Phase 3 | Complete |
| IDEN-01 | Phase 4 | Complete |
| IDEN-02 | Phase 4 | Complete |
| IDEN-03 | Phase 4 | Complete |
| IDEN-04 | Phase 4 | Complete |
| MEMO-01 | Phase 4 | Complete |
| MEMO-02 | Phase 4 | Complete |
| MEMO-03 | Phase 4 | Complete |
| MEMO-04 | Phase 4 | Complete |
| GITV-01 | Phase 4 | Complete |
| GITV-02 | Phase 4 | Complete |
| GITV-03 | Phase 4 | Complete |
| DASH-01 | Phase 5 | Complete |
| DASH-02 | Phase 5 | Complete |
| DASH-03 | Phase 5 | Complete |
| DASH-04 | Phase 5 | Complete |
| DASH-05 | Phase 5 | Complete |
| DASH-06 | Phase 5 | Complete |
| TEST-01 | Phase 6 | Complete |
| TEST-02 | Phase 6 | Complete |
| TEST-03 | Phase 6 | Complete |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0
- Test harness requirements (Phase 6): 3 total (TEST-01..03)

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-15 after Phase 07 gap closure — checkboxes and traceability table reconciled with VERIFICATION.md verdicts; TEST-01..03 rows inserted*
