# Animaya v2

## What This Is

A modular AI assistant platform that installs on top of a Claude Box (LXC with Claude Code). Users get a Telegram bridge to Claude Code plus a web dashboard, then add capabilities through installable/uninstallable modules (identity, memory, git versioning, etc.). Part of the Voidnet ecosystem — users provision Claude Boxes through Voidnet, then install Animaya via its web interface.

## Core Value

Any user can spin up a personal AI assistant by installing Animaya on their Claude Box, then customize it module-by-module — each module is self-contained, configurable, and reversible.

## Requirements

### Validated

All v1.0 requirements satisfied as of 2026-04-15 (milestone v1.0 — Audit Gaps):

- **INST-01..04** (Phase 1): Install script + systemd service on Claude Box
- **TELE-01..05** (Phase 2): Streaming Telegram bridge with async safety
- **MODS-01..06** (Phase 3): Module system — manifest, registry, lifecycle, assembler, isolation
- **IDEN-01..04** (Phase 4): Identity module — onboarding, Hub storage, system prompt injection, reconfigure
- **MEMO-01..04** (Phase 4): Memory module — Hub markdown, git versioning, Haiku consolidation, context injection
- **GITV-01..03** (Phase 4): Git versioning module — asyncio commit loop, single-committer, scoped commits
- **DASH-01..06** (Phase 5): Web dashboard — FastAPI+HTMX, Telegram Login Widget, status, modules UI, config forms
- **TEST-01..03** (Phase 6): Telethon test harness — session persistence, driver API, smoke test

### Active

(None — planning next milestone)

### Out of Scope

- Docker-based deployment — replaced by LXC/Claude Box model
- Custom Spaces memory module — replaced by Hub-style knowledge/ approach
- Multi-user provisioning UI — v1 is deploy-for-self, Voidnet handles provisioning
- Image generation / voice transcription — can be added as modules later
- Semantic search over memory — defer to post-v1 module

## Context

- **Prior art:** Docker-based Animaya (this repo) with Spaces memory, streaming Telegram bridge, FastAPI dashboard, self-dev system. Fresh rewrite — old code is reference only.
- **Infrastructure:** Proxmox host (tower) runs LXCs. Claude Boxes are LXCs with Claude Code pre-configured. Animaya installs on top.
- **Voidnet integration:** Users buy a Claude Box through Voidnet, then install Animaya from Voidnet's web interface. Animaya itself is a Voidnet service.
- **Hub architecture:** Central git repo (~/hub) with knowledge/, backlog/, workspace/. Module data lives in Hub's knowledge/ structure — git-versioned, auditable, portable.
- **Target users:** Friends and their friends within Voidnet platform. V1 target: working on own Claude Box for daily personal use.
- **v1.0 shipped:** 2026-04-15. Full audit trail in `.planning/milestones/`.

## Constraints

- **Runtime:** Must install on existing Claude Box (LXC with Claude Code already configured)
- **No containers:** LXC-native, no Docker inside LXC
- **Modularity:** Every feature beyond core (bridge + dashboard) must be a module
- **Reversibility:** Every module must cleanly uninstall without breaking other modules
- **Hub-compatible:** Module data stored in Hub knowledge/ structure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LXC instead of Docker | Simpler, direct Proxmox integration, no nested virtualization | Validated — clean installs on Claude Box |
| Fresh rewrite over migration | Architecture change too fundamental for incremental migration | Validated — clean codebase, no Docker residue |
| Folder + manifest modules | Simple, transparent, no package manager overhead | Validated — pydantic validation, zero-artifact uninstall works |
| Hub knowledge/ for module state | Git-versioned, auditable, shared across agents, already proven | Validated — memory/identity/git-versioning all use Hub |
| Telegram as primary interface | Users already use Telegram, proven in v1 | Validated — Telethon smoke tests PASS against live bot |
| FastAPI + HTMX (no npm) | Eliminate frontend build complexity | Validated — dashboard ships with zero build toolchain |
| Port v1 bridge verbatim | Preserves proven streaming/lock/chunking logic | Validated — avoids regressions on known-working code |
| Telethon harness at hub level | Reusable across workspace agents, not tied to animaya repo | Validated — harness lives at ~/hub/telethon/ |
| Tech debt accepted at v1.0 | Nyquist partial on 3 phases + cosmetic streaming artifact | Accepted — all 27 REQ satisfied, non-blocking |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-15 after milestone v1.0 completion*
