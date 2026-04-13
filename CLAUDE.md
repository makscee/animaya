# CLAUDE.md

## Project Overview

Animaya is a personal AI assistant platform — part of Voidnet. Each user gets an isolated Claude Code-powered assistant connected to Telegram, running in a sandboxed Docker container on mcow.

## Architecture

```
mcow server (Voidnet infra)
├── Caddy (443) → animaya.makscee.ru (platform), {slug}.animaya.makscee.ru (bot dashboards)
├── Platform container (has docker.sock, manages bot lifecycle)
└── Bot containers (sandboxed, per-user)
    ├── Telegram bridge → Claude Code SDK → streaming responses
    ├── 3-tier memory (core summary / working files / archive search)
    ├── Spaces module (knowledge workspaces)
    ├── FastAPI dashboard (port 8090)
    └── Git auto-versioning of /data
```

## Key Files

```
bot/
├── main.py              — Entry point: Telegram bot + dashboard
├── claude_query.py      — Claude Code SDK options builder (single source of truth)
├── bridge/
│   ├── telegram.py      — Telegram message handler + streaming
│   └── formatting.py    — Markdown → Telegram HTML
├── memory/
│   ├── core.py          — Tier 1: core summary for system prompt
│   ├── spaces.py        — Spaces module (knowledge workspaces)
│   └── search.py        — Semantic search over memory files
├── features/
│   ├── audio.py         — Voice transcription (Groq Whisper)
│   ├── image_gen.py     — Image generation (Gemini)
│   ├── git_versioning.py — Auto-commit /data changes
│   └── self_dev.py      — bot.Dockerfile management (no runtime pip)
└── dashboard/
    ├── app.py           — FastAPI web UI
    └── auth.py          — Telegram Login Widget auth

docker/
├── Dockerfile.bot       — Bot image (Python 3.12 + Node.js 22 + Claude Code CLI)
└── docker-compose.yml   — Single-bot deployment for mcow
```

## Common Commands

```bash
# Local development
python -m bot                     # Run bot locally (needs .env)

# Docker
docker compose -f docker/docker-compose.yml up --build

# Deploy to mcow
./scripts/deploy.sh

# Tests
python -m pytest tests/ -v
```

## Environment Variables

Required:
- `TELEGRAM_BOT_TOKEN` — Telegram bot token from @BotFather
- `CLAUDE_CODE_OAUTH_TOKEN` — Claude Code OAuth token (handles all Claude API auth)

Optional:
- `CLAUDE_MODEL` — Model override (default: claude-sonnet-4-6)
- `DATA_PATH` — Data directory (default: /data)
- `STT_API_KEY` — Groq API key for voice transcription
- `STT_BASE_URL` — Whisper API URL (default: Groq)
- `GOOGLE_API_KEY` — Google API key for Gemini image generation
- `EMBEDDING_API_KEY` — API key for embeddings (semantic search)
- `EMBEDDING_BASE_URL` — Embeddings API URL (default: OpenAI)
- `DASHBOARD_TOKEN` — Dashboard auth token
- `GIT_COMMIT_INTERVAL` — Auto-commit interval in seconds (default: 300)

## Conventions

- Python 3.12, type hints everywhere
- Ruff for linting (line length 100)
- Package name: `bot` (import as `from bot.x import y`)
- Self-dev: bots can ONLY install packages by editing `/data/bot.Dockerfile`. Runtime pip is blocked.
- Bot data lives in `/data/` — persistent Docker volume with git versioning
- Spaces use `@` prefix, kebab-case: `@project-name`
- Skills use `~` prefix: `~deploy-process.md`

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Animaya v2**

A modular AI assistant platform that installs on top of a Claude Box (LXC with Claude Code). Users get a Telegram bridge to Claude Code plus a web dashboard, then add capabilities through installable/uninstallable modules (identity, memory, git versioning, etc.). Part of the Voidnet ecosystem — users provision Claude Boxes through Voidnet, then install Animaya via its web interface.

**Core Value:** Any user can spin up a personal AI assistant by installing Animaya on their Claude Box, then customize it module-by-module — each module is self-contained, configurable, and reversible.

### Constraints

- **Runtime:** Must install on existing Claude Box (LXC with Claude Code already configured)
- **No containers:** LXC-native, no Docker inside LXC
- **Modularity:** Every feature beyond core (bridge + dashboard) must be a module
- **Reversibility:** Every module must cleanly uninstall without breaking other modules
- **Hub-compatible:** Module data stored in Hub knowledge/ structure
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12 - Bot core, API endpoints, features
- TypeScript 5 - Dashboard frontend (Next.js)
- JavaScript (Node.js 22) - Build tooling, Claude Code CLI
- Bash - Docker startup scripts, system commands
- Dockerfile - Container image definitions
## Runtime
- Python 3.12-slim (Docker base)
- Node.js 22 (for Claude Code CLI + Next.js)
- Linux (Debian-based via `python:3.12-slim`)
- pip - Python dependencies (`pyproject.toml`)
- npm - JavaScript dependencies (`dashboard/package-lock.json`)
- Lockfile: Both present (`package-lock.json`, implicit poetry/pip-tools behavior)
## Frameworks
- FastAPI 0.115.0 - REST API, dashboard backend (`bot/dashboard/app.py`)
- Uvicorn 0.30.0 - ASGI server for FastAPI
- Next.js 16.2.3 - Dashboard frontend (React SSR)
- React 19.2.4 - UI components
- python-telegram-bot 21.10+ - Telegram bot interface and handlers (`bot/bridge/telegram.py`)
- claude-code-sdk 0.0.25+ - Claude Code API client, streaming responses, tool execution
- pytest 8.0+ - Unit and integration test runner
- pytest-asyncio 0.23+ - Async test support (`asyncio_mode = "auto"`)
- Ruff 0.4.0+ - Python linting and formatting (`line-length = 100`, rules: E, F, I, W)
- Tailwind CSS 4.0 - Dashboard styling
- TypeScript 5 - Type checking for Next.js
- ESLint 9 - JavaScript linting (Next.js config)
## Key Dependencies
- python-telegram-bot - Handles all Telegram message delivery, updates, and bot commands
- claude-code-sdk - Execution engine for Claude Code queries; streaming responses and tool execution
- FastAPI - Web server for dashboard and API endpoints
- httpx 0.27.0+ - Async HTTP client for external API calls (STT, embeddings, image generation)
- Jinja2 3.1.0 - Template rendering (used in dashboard, CLAUDE.md assembly)
- itsdangerous 2.1.0 - Secure token signing (dashboard auth)
- uvicorn - ASGI server
- Next.js - Dashboard SSR and static export
- pytest, pytest-asyncio - Test execution
## Configuration
- `.env` file (listed in `docker/docker-compose.yml`)
- Required vars: `TELEGRAM_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`
- Optional vars: `CLAUDE_MODEL`, `DATA_PATH`, `STT_API_KEY`, `STT_BASE_URL`, `GOOGLE_API_KEY`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `DASHBOARD_TOKEN`, `GIT_COMMIT_INTERVAL`, `STT_MODEL`
- `docker/Dockerfile.bot` - Single multi-stage build combining Python + Node.js
- `docker/docker-compose.yml` - Single-bot orchestration (development/testing)
- `dashboard/tsconfig.json` - TypeScript configuration
- `.ruff.toml` in `pyproject.toml` - Linting rules
- `pyproject.toml` - Project metadata, dependencies, tool configs
- Requires Python >=3.12
- Test path: `tests/` directory
- No setup.py (modern pyproject.toml only)
## Platform Requirements
- Python 3.12+
- Node.js 22 (for npm/Next.js)
- Docker (for containerized testing/deployment)
- Git (for `git_versioning` feature)
- Docker runtime (mcow Voidnet infrastructure)
- Persistent volume mount at `/data` for bot state
- Caddy reverse proxy (via Voidnet, not in this repo)
- Linux kernel (3000 and 8090 ports exposed)
## Build Targets
- Name: `animaya-bot` (docker-compose)
- Ports: 3000 (Next.js), 8090 (FastAPI)
- Volumes: `bot-data:/data` (persistent state)
- Resource limits: 2GB RAM, 1.0 CPU, 256 PID limit
- Built as stage in `Dockerfile.bot`
- Next.js 16 build (`npm run build`)
- Served alongside FastAPI on port 3000
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Lowercase with underscores: `telegram.py`, `image_gen.py`, `git_versioning.py`
- Module files follow single responsibility: `audio.py`, `search.py`, `core.py`
- Dunder files: `__init__.py`, `__main__.py`
- snake_case: `build_options()`, `transcribe()`, `build_core_context()`, `chunk_markdown()`
- Private functions prefixed with single underscore: `_get_user_lock()`, `_patch_sdk_message_parser()`, `_send_status()`
- Async functions use `async def`: `transcribe()`, `_send_status()`
- snake_case for all local variables and module globals: `audio_bytes`, `filename`, `user_id`
- Constants in UPPER_SNAKE_CASE: `TG_MAX_LEN`, `STT_BASE_URL`, `STT_MODEL`, `_STREAM_MIN_INTERVAL`
- Private module-level stats dict: `_stats = {...}`
- Use `Path` for filesystem paths: `data_dir: Path`, `config_path: Path`
- Use `dict`, `list`, `str | None` union types (Python 3.12 syntax)
- Type hints on all function parameters and returns
## Code Style
- Ruff formatter enforced
- Line length: 100 characters (set in `pyproject.toml`)
- Target Python: 3.12+
- Ruff with rules: E (errors), F (pyflakes), I (isort), W (warnings)
- Config: `[tool.ruff]` in `pyproject.toml`
- Automatic import sorting by Ruff
- Use `# ──` separator for major sections: `# ── SDK compatibility patch ─────────────────────────────────────────`
- Docstrings for all public functions and modules
- Triple-quoted docstrings with Args, Returns sections
## Import Organization
- No aliases used; always use full `bot.module.submodule` paths
- Relative imports never used
- Module namespace: `bot` (e.g., `from bot.memory.core import build_core_context`)
## Error Handling
- Try-except with specific exception logging: `logger.exception("Message")` captures full traceback
- Graceful degradation: return `None` on failure (e.g., `transcribe()` returns `str | None`)
- Log errors at appropriate level: `logger.error()` for recoverable errors, `logger.exception()` for unexpected failures
- Silent catch with `suppress()` for expected failures in async contexts:
- Return error strings from utility functions: `"Error: GOOGLE_API_KEY not set"`
- Let exceptions propagate in critical paths (Claude SDK initialization, startup)
- Use `sys.exit(1)` for startup validation failures
## Logging
- Logger per module: `logger = logging.getLogger(__name__)`
- Configured in entry point `bot/main.py`:
- INFO: Lifecycle events (startup, shutdown, config loaded), operation counts
- WARNING: Configuration issues, missing optional dependencies
- ERROR: Recoverable failures (API timeouts, retries)
- DEBUG: Detailed tracing of SDK compatibility patches
- EXCEPTION: Use `logger.exception()` to capture full traceback
## Function Design
- Use typed parameters with sensible defaults
- Async parameters when calling async operations: `async def transcribe(...)`
- Context managers for resource cleanup: `@asynccontextmanager async def _typing_loop(chat):`
- Explicit return types on all functions
- Return `None` for fire-and-forget operations
- Return union types for success/failure: `str | None` means success returns str, failure returns None
## Module Design
- Define public API at module level
- Private functions start with `_`
- All modules have module docstring
- `bot/*/___init__.py` are empty (no re-exports)
## Configuration
- Read at module level for static config: `STT_API_KEY = os.environ.get("STT_API_KEY", "")`
- Read in functions for runtime config: `model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")`
- Provide sensible defaults
- Validate required variables at startup (in `bot/main.py`)
- Use `Path` objects, never string concatenation
- Default to `/data` via env var: `Path(os.environ.get("DATA_PATH", "/data"))`
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Event-driven architecture with streaming responses
- Per-user concurrency control (asyncio locks per Telegram user)
- 3-tier memory hierarchy (core summary → working files → semantic search)
- Modular features system with pluggable integration handlers
- Git-versioned persistent data with auto-commit background thread
## Layers
- Purpose: Receive messages from external systems, format responses, stream back
- Location: `bot/bridge/` (`telegram.py`, `formatting.py`)
- Contains: Telegram message handlers, markdown→HTML converters, streaming throttle logic
- Depends on: Claude Code SDK, python-telegram-bot, formatting utilities
- Used by: Telegram bot polling loop in `bot/main.py`
- Pattern: Handler-based (one async handler per message type)
- Purpose: Single source of truth for constructing ClaudeCodeOptions with context
- Location: `bot/claude_query.py`
- Contains: `build_options()` that assembles system prompt, model config, working directory
- Depends on: Claude Code SDK, memory.core, config.json
- Used by: Telegram bridge and dashboard chat endpoints
- Pattern: Factory function returning configured SDK options
- Purpose: Provide contextual information at different granularities
- Location: `bot/memory/`
- Purpose: Handle specialized integrations and self-modification
- Location: `bot/features/`
- Components:
- Used by: Main bot, dashboard modules system
- Pattern: Module with public functions, no shared state
- Purpose: REST endpoints for Next.js frontend
- Location: `bot/dashboard/app.py`
- Endpoints: /api/modules, /api/chat, /api/files, /api/settings, /api/stats, /api/logs, /api/chat/history
- Contains: FastAPI app with CORS middleware, SSE event bus for streaming
- Depends on: FastAPI, pydantic, same memory/query layers as Telegram
- Pattern: RESTful + Server-Sent Events for streaming
- Runs on: Port 8090 in background thread from main.py
- Purpose: Web UI for chat, file management, settings, module management
- Location: `dashboard/src/`
- Framework: Next.js 14+ (App Router)
- Pages:
- Components: `components/Sidebar.tsx` (navigation)
- Libs: `lib/api.ts` (API client), `lib/types.ts` (shared types), `lib/modules.ts`
- Pattern: Component-based with server/client boundary at page level
- Purpose: Durable storage of bot data and conversation context
- Location: `/data/` (Docker volume)
- Contains:
- Pattern: Git-backed filesystem with auto-commit
## Data Flow
## Key Abstractions
- Purpose: Configuration wrapper for Claude Code SDK queries
- Files: `bot/claude_query.py` (builder)
- Pattern: Factory function `build_options()` returns ready-to-use options
- Critical fields: model, system_prompt, cwd, allowed_tools, permission_mode
- Purpose: Hierarchical information injection into Claude's context
- Files: `bot/memory/core.py` (builder)
- Pattern: `build_core_context()` assembles Tier 1 snippet, returns markdown string
- Pattern: `build_consolidation_prompt()` provides instructions for post-conversation memory save
- Purpose: Progressive token-by-token delivery to client
- Files: `bot/bridge/telegram.py` (streaming throttle), `bot/dashboard/app.py` (SSE)
- Pattern: Min interval + min chars buffering to avoid UI flicker
- Pattern: SSE for web, Telegram edit_message for mobile
- Purpose: Pluggable feature installation without editing source
- Files: `bot/dashboard/app.py` (/api/modules endpoints)
- Pattern: config.json stores module ID → config mapping
- Pattern: Templates in bot/templates/modules/{id}.md assembled into CLAUDE.md at runtime
- Pattern: Module markdown documents feature availability and usage
- Purpose: Bots can request container rebuilds without shell access
- Files: `bot/features/self_dev.py`
- Pattern: `bot.Dockerfile` file in /data/ appended with RUN commands
- Pattern: Runtime pip blocked; platform rebuilds container from dockerfile
## Entry Points
- Location: `bot/__main__.py` and `bot/main.py`
- Triggers: `python -m bot` or docker entrypoint
- Responsibilities:
- Location: `bot/bridge/telegram.py:_handle_message()` (via @app.message_handler)
- Triggers: User sends text/voice/photo/file
- Responsibilities:
- Location: `bot/dashboard/app.py:@app.post("/api/chat")`
- Triggers: React frontend sendMessage()
- Responsibilities:
- Location: `bot/dashboard/app.py:@app.post("/api/modules/{id}/install")`
- Triggers: Module install button in UI
- Responsibilities:
## Error Handling
## Cross-Cutting Concerns
- Framework: Python logging with format `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- Configured in `bot/main.py` at INFO level
- Available via dashboard /api/logs endpoint
- Env vars checked at startup (TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN required)
- JSON config (config.json, .embeddings.json files) parsed with try/except, safe defaults
- Telegram message parsed with filters (text, voice, photo, document)
- Telegram: Bot token from @BotFather
- Claude Code: OAuth token from env (CLAUDE_CODE_OAUTH_TOKEN)
- Dashboard: Optional DASHBOARD_TOKEN for /api/* endpoints (auth.py)
- Memory files: Markdown with conventions (SOUL.md = identity, OWNER.md = owner, spaces with @ prefix)
- Config: JSON (config.json, .embeddings.json)
- Chat history: JSON in sessions/{session_id}
- Auto-commit messages: Timestamp format `YYYY-MM-DD HH:MM`
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, or `.github/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
