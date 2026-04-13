# Requirements: Animaya v2

**Defined:** 2026-04-13
**Core Value:** Any user can spin up a personal AI assistant by installing Animaya on their Claude Box, then customize it module-by-module — each module is self-contained, configurable, and reversible.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Core Install

- [ ] **INST-01**: User can install Animaya on a Claude Box via `git clone` + `setup.sh`
- [ ] **INST-02**: Setup script configures Python venv, installs dependencies, creates systemd service
- [ ] **INST-03**: Animaya runs as a systemd unit with auto-restart and log management
- [ ] **INST-04**: Setup script sanitizes CLAUDECODE=1 env var to prevent SDK hangs

### Telegram Bridge

- [x] **TELE-01**: User can send a message via Telegram and receive a streamed Claude response
- [x] **TELE-02**: Bridge uses asyncio.create_task() for non-blocking response handling
- [x] **TELE-03**: Bridge shows typing indicator while Claude is processing
- [x] **TELE-04**: Long responses are chunked and sent as multiple Telegram messages
- [x] **TELE-05**: Bridge handles errors gracefully and notifies user of failures

### Web Dashboard

- [ ] **DASH-01**: Dashboard runs on FastAPI + Jinja2 + HTMX (no npm build toolchain)
- [ ] **DASH-02**: Dashboard authenticates users via Telegram Login Widget
- [ ] **DASH-03**: Dashboard shows bot status and health (running state, recent activity, errors)
- [ ] **DASH-04**: Dashboard displays list of available and installed modules
- [ ] **DASH-05**: User can install and uninstall modules from the dashboard UI
- [ ] **DASH-06**: User can configure module settings via auto-generated forms from config_schema

### Module System

- [ ] **MODS-01**: Each module is a folder with a manifest.json validated by pydantic
- [ ] **MODS-02**: Each module has install.sh and uninstall.sh lifecycle scripts
- [ ] **MODS-03**: Module registry (registry.json) tracks installed modules and their state
- [ ] **MODS-04**: CLAUDE.md assembler merges core + installed module system prompts
- [ ] **MODS-05**: Uninstall leaves zero artifacts — enforced at manifest schema level
- [ ] **MODS-06**: Modules communicate only through shared Hub files, no inter-module code imports

### Identity Module

- [ ] **IDEN-01**: User completes onboarding flow defining who they are and who the assistant is
- [ ] **IDEN-02**: Identity data is stored as markdown in Hub knowledge/identity/
- [ ] **IDEN-03**: Identity is injected into system prompt via XML-delimited blocks
- [ ] **IDEN-04**: User can reconfigure identity from dashboard without reinstalling

### Memory Module

- [ ] **MEMO-01**: Assistant can read and write persistent memory as markdown files in Hub knowledge/memory/
- [ ] **MEMO-02**: Memory files are git-versioned with full audit trail
- [ ] **MEMO-03**: Core summary file provides session context (who the user is, key facts)
- [ ] **MEMO-04**: Memory module injects relevant context into system prompt

### Git Versioning Module

- [ ] **GITV-01**: Module auto-commits data changes in Hub knowledge/ on a configurable interval
- [ ] **GITV-02**: Single-committer pattern prevents concurrent write conflicts
- [ ] **GITV-03**: Commits are scoped to module subdirectories for clean history

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
| INST-01 | Phase 1 | Pending |
| INST-02 | Phase 1 | Pending |
| INST-03 | Phase 1 | Pending |
| INST-04 | Phase 1 | Pending |
| TELE-01 | Phase 2 | Complete |
| TELE-02 | Phase 2 | Complete |
| TELE-03 | Phase 2 | Complete |
| TELE-04 | Phase 2 | Complete |
| TELE-05 | Phase 2 | Complete |
| MODS-01 | Phase 3 | Pending |
| MODS-02 | Phase 3 | Pending |
| MODS-03 | Phase 3 | Pending |
| MODS-04 | Phase 3 | Pending |
| MODS-05 | Phase 3 | Pending |
| MODS-06 | Phase 3 | Pending |
| IDEN-01 | Phase 4 | Pending |
| IDEN-02 | Phase 4 | Pending |
| IDEN-03 | Phase 4 | Pending |
| IDEN-04 | Phase 4 | Pending |
| MEMO-01 | Phase 4 | Pending |
| MEMO-02 | Phase 4 | Pending |
| MEMO-03 | Phase 4 | Pending |
| MEMO-04 | Phase 4 | Pending |
| GITV-01 | Phase 4 | Pending |
| GITV-02 | Phase 4 | Pending |
| GITV-03 | Phase 4 | Pending |
| DASH-01 | Phase 5 | Pending |
| DASH-02 | Phase 5 | Pending |
| DASH-03 | Phase 5 | Pending |
| DASH-04 | Phase 5 | Pending |
| DASH-05 | Phase 5 | Pending |
| DASH-06 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 27 total
- Mapped to phases: 27
- Unmapped: 0

---
*Requirements defined: 2026-04-13*
*Last updated: 2026-04-13 after roadmap creation*
