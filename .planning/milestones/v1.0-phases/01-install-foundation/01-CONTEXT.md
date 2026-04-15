# Phase 1: Install & Foundation - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Animaya installs cleanly on an existing Claude Box (LXC with Claude Code) via `git clone` + `setup.sh` and runs as a stable systemd service. The service includes a module loader skeleton and CLAUDE.md assembler so Phase 2 can plug in the Telegram bridge directly.

</domain>

<decisions>
## Implementation Decisions

### Install Experience
- **D-01:** setup.sh checks for `.env` file — if present, validates required vars; if missing, prompts interactively for Telegram token and Claude OAuth token, then writes `.env`
- **D-02:** Python venv created in project directory (e.g., `~/animaya/.venv`) for dependency isolation from system Python and Claude Code packages
- **D-03:** setup.sh checks for Node.js availability and installs it if missing (Claude Box should have it, but script is robust)
- **D-04:** Systemd service uses a wrapper script (`run.sh`) for ExecStart — activates venv, sources env, runs bot

### Directory Layout
- **D-05:** Application code installs to `~/animaya` (no root required)
- **D-06:** Module data and Hub knowledge files live at `~/hub/knowledge/animaya/` — git-versioned with Hub, shared with other Hub agents

### Upgrade Path
- **D-07:** Updates via `git pull` + re-run `setup.sh` (idempotent — detects existing install, only updates what changed)
- **D-08:** Migration strategy (schema/config format changes between versions): Claude's discretion

### Base Behavior
- **D-09:** Freshly installed service runs module loader skeleton + CLAUDE.md assembler with empty module list. Ready for Phase 2 to plug in Telegram bridge as first module.
- **D-10:** No user-facing behavior (no CLI, no health endpoint, no network listeners) — just a running service that loads modules and assembles CLAUDE.md

### Claude's Discretion
- Migration handling approach (D-08): decide during planning whether setup.sh handles migrations inline or delegates to a separate step
- Uninstall path: decide whether `setup.sh --uninstall` belongs in Phase 1 or is deferred

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` §Core Install — INST-01 through INST-04 define acceptance criteria

### Project Context
- `.planning/PROJECT.md` — Constraints (LXC-native, no Docker, Hub-compatible), key decisions
- `.planning/ROADMAP.md` §Phase 1 — Success criteria and dependency chain

### Codebase Reference (v1, reference only)
- `scripts/deploy.sh` — Old Docker-based deploy script. Shows rsync + remote pattern but approach is replaced.
- `bot/__main__.py`, `bot/main.py` — Current entry points for reference on startup sequence
- `pyproject.toml` — Existing Python project definition and dependencies

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `pyproject.toml`: Project metadata, dependencies, ruff config already defined. Can be reused as-is for venv setup.
- `bot/main.py`: Startup sequence (env validation, data init, CLAUDE.md rebuild, service startup) — reference for new entry point design

### Established Patterns
- Env var validation at startup with `sys.exit(1)` on failure
- Logging via `logging.getLogger(__name__)` per module, configured in main
- CLAUDE.md assembly from base + module markdown files (existing pattern in dashboard/app.py `_rebuild_claude_md()`)

### Integration Points
- systemd service → run.sh → .venv/bin/python -m bot
- ~/hub/knowledge/animaya/ ← module data directory, symlinked or configured via DATA_PATH
- CLAUDE.md assembler connects core system prompt with installed module prompts

</code_context>

<specifics>
## Specific Ideas

- Claude Box already has Claude Code configured — setup.sh must not interfere with existing Claude Code installation
- CLAUDECODE=1 env var must be sanitized (INST-04) — run.sh wrapper is the natural place to unset it before launching Python
- Hub knowledge/ structure is already proven in the ecosystem — module data follows the same `knowledge/{namespace}/` pattern

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-install-foundation*
*Context gathered: 2026-04-13*
