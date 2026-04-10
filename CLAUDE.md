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
