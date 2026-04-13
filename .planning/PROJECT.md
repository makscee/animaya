# Animaya v2

## What This Is

A modular AI assistant platform that installs on top of a Claude Box (LXC with Claude Code). Users get a Telegram bridge to Claude Code plus a web dashboard, then add capabilities through installable/uninstallable modules (identity, memory, git versioning, etc.). Part of the Voidnet ecosystem — users provision Claude Boxes through Voidnet, then install Animaya via its web interface.

## Core Value

Any user can spin up a personal AI assistant by installing Animaya on their Claude Box, then customize it module-by-module — each module is self-contained, configurable, and reversible.

## Requirements

### Validated

(None yet — fresh start, old Docker-based code is reference only)

### Active

- [ ] Telegram bridge connects to Claude Code and streams responses
- [ ] Web dashboard for bot management and module installation
- [ ] Module system with folder + manifest pattern (install/uninstall/configure)
- [ ] Identity module: onboarding flow (who is the user, who is the assistant)
- [ ] Memory module: Hub-style git-versioned markdown in knowledge/ structure
- [ ] Git versioning module: auto-commit data changes
- [ ] Install script: `git clone` + setup on existing Claude Box
- [ ] Module state stored in Hub knowledge/ directory structure
- [ ] Each module can be independently installed, configured, and uninstalled

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

## Constraints

- **Runtime:** Must install on existing Claude Box (LXC with Claude Code already configured)
- **No containers:** LXC-native, no Docker inside LXC
- **Modularity:** Every feature beyond core (bridge + dashboard) must be a module
- **Reversibility:** Every module must cleanly uninstall without breaking other modules
- **Hub-compatible:** Module data stored in Hub knowledge/ structure

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| LXC instead of Docker | Simpler, direct Proxmox integration, no nested virtualization | — Pending |
| Fresh rewrite over migration | Architecture change too fundamental for incremental migration | — Pending |
| Folder + manifest modules | Simple, transparent, no package manager overhead | — Pending |
| Hub knowledge/ for module state | Git-versioned, auditable, shared across agents, already proven | — Pending |
| Telegram as primary interface | Users already use Telegram, proven in v1 | — Pending |

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
*Last updated: 2026-04-13 after initialization*
