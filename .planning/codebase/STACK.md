# Technology Stack

**Analysis Date:** 2026-04-13

## Languages

**Primary:**
- Python 3.12 - Bot core, API endpoints, features
- TypeScript 5 - Dashboard frontend (Next.js)
- JavaScript (Node.js 22) - Build tooling, Claude Code CLI

**Secondary:**
- Bash - Docker startup scripts, system commands
- Dockerfile - Container image definitions

## Runtime

**Environment:**
- Python 3.12-slim (Docker base)
- Node.js 22 (for Claude Code CLI + Next.js)
- Linux (Debian-based via `python:3.12-slim`)

**Package Manager:**
- pip - Python dependencies (`pyproject.toml`)
- npm - JavaScript dependencies (`dashboard/package-lock.json`)
- Lockfile: Both present (`package-lock.json`, implicit poetry/pip-tools behavior)

## Frameworks

**Core:**
- FastAPI 0.115.0 - REST API, dashboard backend (`bot/dashboard/app.py`)
- Uvicorn 0.30.0 - ASGI server for FastAPI
- Next.js 16.2.3 - Dashboard frontend (React SSR)
- React 19.2.4 - UI components

**Messaging:**
- python-telegram-bot 21.10+ - Telegram bot interface and handlers (`bot/bridge/telegram.py`)

**Claude Integration:**
- claude-code-sdk 0.0.25+ - Claude Code API client, streaming responses, tool execution
  - Internal modules: `_internal.client`, `_internal.message_parser` (used in `bot/bridge/telegram.py`)

**Testing:**
- pytest 8.0+ - Unit and integration test runner
- pytest-asyncio 0.23+ - Async test support (`asyncio_mode = "auto"`)

**Build/Dev:**
- Ruff 0.4.0+ - Python linting and formatting (`line-length = 100`, rules: E, F, I, W)
- Tailwind CSS 4.0 - Dashboard styling
- TypeScript 5 - Type checking for Next.js
- ESLint 9 - JavaScript linting (Next.js config)

## Key Dependencies

**Critical:**
- python-telegram-bot - Handles all Telegram message delivery, updates, and bot commands
- claude-code-sdk - Execution engine for Claude Code queries; streaming responses and tool execution
- FastAPI - Web server for dashboard and API endpoints
- httpx 0.27.0+ - Async HTTP client for external API calls (STT, embeddings, image generation)

**Infrastructure:**
- Jinja2 3.1.0 - Template rendering (used in dashboard, CLAUDE.md assembly)
- itsdangerous 2.1.0 - Secure token signing (dashboard auth)
- uvicorn - ASGI server
- Next.js - Dashboard SSR and static export

**Development:**
- pytest, pytest-asyncio - Test execution

## Configuration

**Environment:**
- `.env` file (listed in `docker/docker-compose.yml`)
- Required vars: `TELEGRAM_BOT_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`
- Optional vars: `CLAUDE_MODEL`, `DATA_PATH`, `STT_API_KEY`, `STT_BASE_URL`, `GOOGLE_API_KEY`, `EMBEDDING_API_KEY`, `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `DASHBOARD_TOKEN`, `GIT_COMMIT_INTERVAL`, `STT_MODEL`

**Build:**
- `docker/Dockerfile.bot` - Single multi-stage build combining Python + Node.js
- `docker/docker-compose.yml` - Single-bot orchestration (development/testing)
- `dashboard/tsconfig.json` - TypeScript configuration
- `.ruff.toml` in `pyproject.toml` - Linting rules

**Python:**
- `pyproject.toml` - Project metadata, dependencies, tool configs
- Requires Python >=3.12
- Test path: `tests/` directory
- No setup.py (modern pyproject.toml only)

## Platform Requirements

**Development:**
- Python 3.12+
- Node.js 22 (for npm/Next.js)
- Docker (for containerized testing/deployment)
- Git (for `git_versioning` feature)

**Production:**
- Docker runtime (mcow Voidnet infrastructure)
- Persistent volume mount at `/data` for bot state
- Caddy reverse proxy (via Voidnet, not in this repo)
- Linux kernel (3000 and 8090 ports exposed)

## Build Targets

**Bot Image:**
- Name: `animaya-bot` (docker-compose)
- Ports: 3000 (Next.js), 8090 (FastAPI)
- Volumes: `bot-data:/data` (persistent state)
- Resource limits: 2GB RAM, 1.0 CPU, 256 PID limit

**Dashboard Image:**
- Built as stage in `Dockerfile.bot`
- Next.js 16 build (`npm run build`)
- Served alongside FastAPI on port 3000

---

*Stack analysis: 2026-04-13*
