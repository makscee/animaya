# Project Research Summary

**Project:** Animaya v2 — Modular AI Assistant Platform
**Domain:** LXC-native personal AI assistant (Telegram bridge + web dashboard + installable modules)
**Researched:** 2026-04-13
**Confidence:** HIGH (core), MEDIUM (module system specifics)

## Executive Summary

Animaya v2 is a rewrite of a Docker-based personal AI assistant into an LXC-native, modular platform. The core loop — Telegram message in, Claude Code response streamed back — is proven from v1. The new architectural bet is a manifest-driven module system where capabilities (memory, identity, git-versioning) are installable folders with shell hooks, not code baked into the core. The recommended stack is Python 3.12 + aiogram 3.27 + claude-agent-sdk 0.1.58 + FastAPI + HTMX, all running as a single systemd service per LXC with no Docker, no npm build toolchain, and no databases — state lives in git-versioned markdown files in `~/hub/knowledge/`.

The biggest architectural risk is the module lifecycle contract. Modules that leave stale state after uninstall, or that couple to each other through code rather than shared Hub files, will recreate the complexity problems that made v1 hard to maintain. The uninstall contract must be enforced at the manifest schema level before any modules are built. The second major risk is the Telegram event loop: Claude responses take 30-120 seconds and must be handled with `asyncio.create_task()` and immediate acknowledgment, or the bridge will block and Telegram will retry, causing duplicate messages.

## Key Findings

### Recommended Stack

- **Python 3.12** — runtime, stable async/type hints
- **aiogram 3.27.0** — Telegram bridge, fully async, FSM built-in
- **claude-agent-sdk 0.1.58** — Claude Code integration, successor to deprecated claude-code-sdk, bundles CLI
- **FastAPI 0.115.x** — dashboard backend, async-native, SSE support
- **HTMX 2.x (CDN)** — dashboard interactivity, eliminates npm/build toolchain
- **pydantic 2.x** — module manifest validation, already a FastAPI dependency
- **watchdog 5.x** — module hot-detection, watches modules/ directory

### Expected Features

**Table stakes:** Streaming responses, persistent memory, Telegram bridge, web dashboard, identity/onboarding, module install/uninstall without breaking core

**Differentiators:** Git-versioned memory (Hub-style), markdown-file module state, reversible modules with clean uninstall, LXC-native deployment, skill files

**Defer (v2+):** Voice transcription, image generation, semantic search, Voidnet provisioning UI

### Architecture

Single Python process (bridge + dashboard co-hosted). CLAUDE.md assembler merges core + module prompts. All module state in `~/hub/knowledge/[module-name]/`. Modules communicate only through shared Hub files — no inter-module code imports.

### Critical Pitfalls

1. **Module state leaks on uninstall** — enforce "zero artifacts" contract at manifest level
2. **CLAUDECODE=1 env inheritance** — sanitize env before spawning SDK subprocess
3. **Blocking event loop** — asyncio.create_task() immediately, stream partial results
4. **Over-engineering modules early** — minimum viable manifest first
5. **Git commit conflicts** — single committer pattern with scoped subdirectories
6. **Prompt injection** — XML delimiters around user-controlled system prompt content

## Implications for Roadmap

### Phase 1: Core Install + Bridge + Dashboard Skeleton
Nothing else is buildable without a working LXC install script, streaming bridge, and skeleton dashboard.

### Phase 2: Module System Machinery
Freeze manifest contract before writing any module code. Delivers registry, CLAUDE.md assembler, lifecycle runner.

### Phase 3: First-Party Modules
Identity (onboarding), memory (Hub knowledge/), git-versioning (single committer). These define Animaya's core value.

### Phase 4: Module Configuration UI
Deferred until real modules exist so config_schema shapes are known.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All libraries verified on PyPI with 2026 releases |
| Features | HIGH | v1 prior art + clear defer list |
| Architecture | HIGH | Derived from v1 + stated constraints |
| Pitfalls | MEDIUM | CLAUDECODE=1 documented; rest from patterns |

### Gaps to Address

- Module manifest config_schema renderer: no reference implementation yet
- Prompt reload without restart: verify claude-agent-sdk supports per-invocation changes
- Claude Code CLI path on LXC: needs verification during Phase 1

---
*Research completed: 2026-04-13*
*Ready for roadmap: yes*
