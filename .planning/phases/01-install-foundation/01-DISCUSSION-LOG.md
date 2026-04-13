# Phase 1: Install & Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-13
**Phase:** 01-install-foundation
**Areas discussed:** Install experience, Directory layout, Upgrade path, Base behavior

---

## Install Experience

| Option | Description | Selected |
|--------|-------------|----------|
| Interactive prompts | setup.sh asks for tokens during install, writes .env | |
| Expect .env pre-made | User creates .env before running setup.sh | |
| Both paths | Checks for .env — prompts if missing, validates if present | ✓ |

**User's choice:** Both paths
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Venv (Recommended) | Creates .venv in project dir, isolates deps | ✓ |
| System Python | Install into system Python | |
| pipx / uv | Modern tool for isolated install | |

**User's choice:** Venv (Recommended)
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Assume available | Claude Box already has Node.js, just validate | |
| Install if missing | Check and install via nvm or system package | ✓ |

**User's choice:** Install if missing
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Direct venv python | ExecStart points to .venv/bin/python -m bot | |
| Wrapper script | ExecStart calls run.sh that activates venv, sets env | ✓ |

**User's choice:** Wrapper script
**Notes:** None

---

## Directory Layout

| Option | Description | Selected |
|--------|-------------|----------|
| ~/animaya | User home, no root needed | ✓ |
| /opt/animaya | System-level, requires root | |
| ~/hub/workspace/animaya | Inside Hub structure | |

**User's choice:** ~/animaya
**Notes:** User asked "which is better?" — Claude recommended ~/animaya for no-root install and clean separation from Hub data.

| Option | Description | Selected |
|--------|-------------|----------|
| ~/hub/knowledge/animaya/ | Inside Hub knowledge structure, git-versioned | ✓ |
| ~/animaya/data/ | Self-contained, own git repo | |
| You decide | Claude's discretion | |

**User's choice:** ~/hub/knowledge/animaya/
**Notes:** None

---

## Upgrade Path

| Option | Description | Selected |
|--------|-------------|----------|
| git pull + setup.sh | Idempotent re-run, detects existing install | ✓ |
| Dedicated update.sh | Separate script for migrations and updates | |
| Self-update command | Bot command triggers pull + restart | |

**User's choice:** git pull + setup.sh
**Notes:** None

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, in setup.sh | setup.sh checks version and runs migrations | |
| Separate migrate step | Separate migrate.sh for data migrations | |
| You decide | Claude's discretion | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Base Behavior

| Option | Description | Selected |
|--------|-------------|----------|
| Idle service + health | Service runs, health endpoint, no modules | |
| Minimal CLI status | Service + CLI command for health/modules/uptime | |
| Ready for bridge | Module loader + CLAUDE.md assembler, ready for Phase 2 | ✓ |

**User's choice:** Ready for bridge
**Notes:** User asked "which is better?" — Claude recommended this option because Phase 1 success criteria require the service to actually run, and setting up module loader/CLAUDE.md assembler here means Phase 2 can focus purely on the Telegram bridge.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include it | setup.sh --uninstall removes service/venv/app, keeps data | |
| Defer to later | Focus on install only | |
| You decide | Claude's discretion | ✓ |

**User's choice:** You decide
**Notes:** None

---

## Claude's Discretion

- Migration handling: inline in setup.sh vs separate step
- Uninstall path: include in Phase 1 or defer

## Deferred Ideas

None — discussion stayed within phase scope
