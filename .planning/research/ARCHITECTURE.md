# Architecture Research

**Domain:** Modular AI assistant platform (LXC-native, Telegram bridge + web dashboard + plugin modules)
**Researched:** 2026-04-13
**Confidence:** HIGH for core patterns, MEDIUM for module lifecycle specifics

## Standard Architecture

### System Overview

```
Claude Box (LXC)
├── Claude Code CLI          — pre-installed, handles all AI inference
├── ~/hub/                   — Hub: git repo, knowledge/, backlog/, workspace/
│   └── knowledge/
│       └── animaya/         — Module state lives here (git-versioned markdown)
└── ~/animaya/               — Animaya install root
    ├── core/
    │   ├── main.py          — Entry point: starts bridge + dashboard
    │   ├── claude_query.py  — Claude Code SDK options builder
    │   ├── bridge/          — Telegram message handler + streaming
    │   └── dashboard/       — FastAPI web UI (port 8090)
    ├── modules/             — Installed module directories
    │   ├── identity/
    │   │   ├── manifest.json
    │   │   ├── install.sh
    │   │   ├── uninstall.sh
    │   │   └── system_prompt.md  — injected into Claude context
    │   ├── memory/
    │   └── git-versioning/
    └── config/
        ├── .env             — secrets + overrides
        └── CLAUDE.md        — assembled from core + active module prompts
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| **Telegram Bridge** | Receive messages, stream Claude responses back, handle media | Claude Code SDK, Dashboard (status) |
| **Claude Code SDK** | Run Claude with tool use, manage conversation context | CLAUDE.md (system prompt), Hub knowledge/ |
| **Web Dashboard** | Module install/uninstall/configure UI, bot status, logs | Module registry, .env, CLAUDE.md assembly |
| **Module Registry** | Track installed modules, validate manifests, run install/uninstall scripts | modules/ directory, Hub knowledge/ |
| **CLAUDE.md Assembler** | Merge core prompt + active module prompts into single CLAUDE.md | modules/*/system_prompt.md |
| **Hub knowledge/** | Git-versioned markdown state for all modules | Git (auto-commit), Claude Code (reads/writes) |

### Data Flow

```
User (Telegram)
    ↓ message
Telegram Bridge
    ↓ text + context
Claude Code SDK  ←→  CLAUDE.md (assembled system prompt)
    ↓ tool calls      ↑ rebuilt on module install/uninstall
Hub knowledge/   ←→  Module state (memory/, identity/, etc.)
    ↓ git commit
Git auto-versioning (if module installed)
    ↑ response stream
Telegram Bridge
    ↓
User (Telegram)

Dashboard (separate HTTP server)
    ↓ install request
Module Registry
    ↓ run install.sh
modules/[name]/  →  Hub knowledge/[name]/  (creates state dirs)
    ↓
CLAUDE.md Assembler  →  rebuilds CLAUDE.md
    ↓
Core restarts or hot-reloads system prompt
```

## Module System Architecture

### Manifest Pattern (manifest.json)

```json
{
  "name": "memory",
  "version": "1.0.0",
  "description": "Hub-style git-versioned memory in knowledge/",
  "provides": ["system_prompt", "knowledge_dir"],
  "knowledge_dir": "animaya/memory",
  "system_prompt": "system_prompt.md",
  "hooks": {
    "post_install": "install.sh",
    "pre_uninstall": "uninstall.sh"
  },
  "config_schema": {}
}
```

Key manifest fields:
- `provides`: what the module contributes (`system_prompt`, `knowledge_dir`, `tool`, `dashboard_page`)
- `knowledge_dir`: path under `~/hub/knowledge/` to create/manage
- `hooks`: shell scripts for lifecycle events
- `config_schema`: JSON Schema for module config (rendered as form in dashboard)

### Module Lifecycle

```
Install:
1. Dashboard validates manifest.json
2. Creates ~/hub/knowledge/[module.knowledge_dir]/ if specified
3. Runs install.sh (idempotent — can run multiple times safely)
4. Registers module in modules/registry.json
5. Triggers CLAUDE.md rebuild
6. Bridge picks up new system prompt on next conversation

Uninstall:
1. Runs uninstall.sh (cleans up state, optionally preserves Hub data)
2. Removes from registry.json
3. Triggers CLAUDE.md rebuild
4. Hub knowledge/ data optionally preserved (user choice)

Configure:
1. Dashboard renders config form from config_schema
2. Writes config values to modules/[name]/config.json
3. Module reads config at runtime (no restart needed for most modules)
```

### CLAUDE.md Assembly

The single most important integration point. Claude Code reads CLAUDE.md as its system prompt. Assembly:

```
CLAUDE.md = core/base_prompt.md
          + modules/identity/system_prompt.md   (if installed)
          + modules/memory/system_prompt.md     (if installed)
          + [other active modules in priority order]
```

Assembly runs at startup and after any module install/uninstall. Bridge restarts or sends updated context on next message.

## Patterns to Follow

### Pattern 1: Idempotent Install Scripts

install.sh must be safe to run multiple times. Use `mkdir -p`, check before creating files, never fail if already installed.

### Pattern 2: Hub-First State

All module state goes in `~/hub/knowledge/[module-name]/`. Never store state inside `~/animaya/modules/`. This keeps state git-versioned, portable, and accessible to Claude's tools.

### Pattern 3: Thin Bridge

The Telegram bridge does no business logic — it passes messages to Claude Code and streams responses back. Features come from modules injecting system prompt context, not from bridge code.

### Pattern 4: Dashboard as Control Plane

The dashboard is the only component that writes to manifest registry and triggers CLAUDE.md rebuild. Modules don't self-register — they are managed exclusively through the dashboard.

### Pattern 5: Graceful Prompt Reload

On module install/uninstall, CLAUDE.md is rebuilt immediately. The bridge uses the updated prompt on the next conversation (no full process restart required if Claude Code SDK supports prompt refresh; otherwise restart is acceptable).

## Anti-Patterns to Avoid

### Anti-Pattern 1: Module Code in Core

Do not put feature logic in bridge/ or dashboard/. Every capability beyond core messaging must be a module — injected via system_prompt.md or tool registration.

### Anti-Pattern 2: State Outside Hub

Storing module state in /tmp, in the animaya directory, or in a database outside Hub breaks git-versioning and portability. Always use ~/hub/knowledge/.

### Anti-Pattern 3: Tight Module Coupling

Modules must not call each other's code. Cross-module communication happens only through shared Hub knowledge/ files that Claude reads.

### Anti-Pattern 4: Non-Idempotent Scripts

Install/uninstall scripts that fail on re-run cause install loops. Every script must succeed even if the module is already in the target state.

## Build Order (Component Dependencies)

```
1. Core install script (git clone + env setup)
   └─ no dependencies

2. Telegram Bridge (core/)
   └─ depends on: Claude Code CLI present, .env with tokens

3. Web Dashboard (dashboard/)
   └─ depends on: Bridge running (shares process), module registry exists

4. Module Registry (config/registry.json + assembler)
   └─ depends on: Dashboard (manages it), modules/ directory

5. Identity Module
   └─ depends on: Module registry, Hub knowledge/ exists

6. Memory Module
   └─ depends on: Module registry, Hub knowledge/, Git in Hub

7. Git Versioning Module
   └─ depends on: Hub .git initialized
```

Build phases implied:
- **Phase 1:** Core install script + Bridge + Dashboard skeleton (no modules)
- **Phase 2:** Module system (manifest schema, registry, install/uninstall lifecycle, CLAUDE.md assembly)
- **Phase 3:** First-party modules (identity, memory, git-versioning)
- **Phase 4:** Module configuration UI in dashboard

## Scalability Considerations

| Concern | V1 (1 user) | Later (multi-user) |
|---------|-------------|--------------------|
| Module state isolation | Single Hub, flat knowledge/ | Per-user Hub repos |
| Module versions | Pin to Animaya version | Semver, module registry |
| Bridge processes | Single process | One process per user (Voidnet handles) |

## Sources

- Existing Animaya v1 codebase (reference implementation): `/Users/admin/hub/workspace/animaya/bot/`
- PROJECT.md architecture decisions: `.planning/PROJECT.md`
- Claude Code plugin manifest pattern: https://code.claude.com/docs/en/plugins
- Modular AI agent architecture survey: https://www.marktechpost.com/2025/11/15/comparing-the-top-5-ai-agent-architectures-in-2025-hierarchical-swarm-meta-learning-modular-evolutionary/
- Confidence: HIGH for component boundaries (derived from existing v1 + stated constraints), MEDIUM for module manifest specifics (designed to fit constraints, not copied from existing system)
