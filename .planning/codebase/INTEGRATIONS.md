# External Integrations

**Analysis Date:** 2026-04-13

## APIs & External Services

**Messaging:**
- Telegram Bot API - User interaction, message delivery, updates
  - SDK/Client: `python-telegram-bot` 21.10+
  - Token env var: `TELEGRAM_BOT_TOKEN`
  - Implementation: `bot/bridge/telegram.py` — handles updates, chat actions, media parsing

**Claude Integration:**
- Claude Code API (Anthropic) - AI query execution, streaming responses, tool use
  - SDK/Client: `claude-code-sdk` 0.0.25+
  - Auth: `CLAUDE_CODE_OAUTH_TOKEN` (OAuth token, handles all Claude API auth)
  - Implementation: `bot/claude_query.py` — builds options; `bot/bridge/telegram.py` — executes queries with streaming

**Voice Transcription:**
- Whisper-compatible API (default: Groq) - Audio transcription
  - Endpoint: `STT_BASE_URL` (default: `https://api.groq.com/openai/v1/audio/transcriptions`)
  - Auth: `STT_API_KEY` (Bearer token)
  - Model: `STT_MODEL` (default: `whisper-large-v3-turbo`)
  - Implementation: `bot/features/audio.py` — transcribes voice messages

**Image Generation:**
- Google Gemini API - Image synthesis from text prompts
  - Endpoint: `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`
  - Auth: `GOOGLE_API_KEY` (query param)
  - Model: `gemini-2.5-flash-image` (hardcoded)
  - Implementation: `bot/features/image_gen.py` — generates images, saves to `/data/uploads/`

**Embeddings & Semantic Search:**
- Embeddings API (default: OpenAI-compatible) - Semantic search over memory
  - Endpoint: `EMBEDDING_BASE_URL` (default: `https://api.openai.com/v1/embeddings`)
  - Auth: `EMBEDDING_API_KEY` (fallback to `LLM_API_KEY`)
  - Model: `EMBEDDING_MODEL` (default: `text-embedding-3-small`)
  - Implementation: `bot/memory/search.py` — indexes `.md` files, stores sidecar embeddings, performs vector search

## Data Storage

**Databases:**
- None (no SQL/NoSQL database)

**File Storage:**
- Local filesystem (`/data` volume in Docker)
  - Persistent across container restarts
  - Mounted in `docker/docker-compose.yml` as `bot-data`
  - Used for: bot state, memory files, spaces, uploaded media
  - Versioned via git (auto-commits enabled, see `features/git_versioning.py`)

**Caching:**
- None (in-memory only during request/bot execution)

## Authentication & Identity

**Telegram Login Widget:**
- Telegram's built-in login (Sign in with Telegram)
- Implementation: `bot/dashboard/auth.py`
- Token validation: `itsdangerous` secure signature verification
- Dashboard auth: Optional `DASHBOARD_TOKEN` env var for simple token-based access

**Claude Code OAuth:**
- OAuth token (`CLAUDE_CODE_OAUTH_TOKEN`)
- Handles all Claude API authentication (passed to SDK)
- No explicit refresh logic (SDK manages)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, DataDog, etc.)

**Logs:**
- Python logging (stdlib)
- Logged to stdout (Docker captures)
- Modules use `logging.getLogger(__name__)`
- Log level: Configurable (default: INFO)

## CI/CD & Deployment

**Hosting:**
- Docker container on mcow (Voidnet infrastructure)
- Caddy reverse proxy (external, not in repo)
- Subdomain routing: `animaya.makscee.ru` (platform), `{slug}.animaya.makscee.ru` (bot dashboards)

**CI Pipeline:**
- None (manual deployment via `./scripts/deploy.sh`)

**Container Orchestration:**
- Docker Compose (for local development)
- Docker Swarm or custom orchestration on mcow (not in repo)

## Environment Configuration

**Required env vars:**
- `TELEGRAM_BOT_TOKEN` - Telegram bot token from @BotFather
- `CLAUDE_CODE_OAUTH_TOKEN` - Claude Code OAuth token (all Claude API auth)

**Optional env vars (with defaults):**
- `CLAUDE_MODEL` - Claude model (default: `claude-sonnet-4-6`); can be overridden in `config.json`
- `DATA_PATH` - Bot data directory (default: `/data`)
- `STT_API_KEY` - Groq/Whisper API key (default: empty, disables voice transcription)
- `STT_BASE_URL` - Whisper endpoint (default: `https://api.groq.com/openai/v1`)
- `STT_MODEL` - Whisper model (default: `whisper-large-v3-turbo`)
- `GOOGLE_API_KEY` - Google Gemini API key (default: empty, disables image generation)
- `EMBEDDING_API_KEY` - Embeddings API key; falls back to `LLM_API_KEY` (default: empty, disables semantic search)
- `EMBEDDING_BASE_URL` - Embeddings endpoint (default: `https://api.openai.com/v1`)
- `EMBEDDING_MODEL` - Embeddings model (default: `text-embedding-3-small`)
- `DASHBOARD_TOKEN` - Optional dashboard auth token (default: empty, dashboard open)
- `GIT_COMMIT_INTERVAL` - Auto-commit interval in seconds (default: 300)

**Secrets location:**
- `.env` file (git-ignored; loaded by `docker-compose.yml`)
- Never committed to git (see `.gitignore`)

## Webhooks & Callbacks

**Incoming:**
- Telegram webhook - Received via `python-telegram-bot`'s polling/webhook mode
  - Endpoint: Not exposed in repo (handled by `telegram.ext.Application`)

**Outgoing:**
- None (bot sends responses to Telegram API, not webhooks)

## Optional Features (Graceful Degradation)

**Voice Transcription (`STT_API_KEY`):**
- If not set: warning logged, voice messages skipped
- Implementation: `bot/features/audio.py`

**Image Generation (`GOOGLE_API_KEY`):**
- If not set: returns error message to user
- Implementation: `bot/features/image_gen.py`

**Semantic Search (`EMBEDDING_API_KEY`):**
- If not set: raises `ValueError` on index/search attempt
- Implementation: `bot/memory/search.py`
- Mitigated by: Users can still use Claude Code's file search without embeddings

## Memory Architecture

**3-Tier Memory (per CLAUDE.md):**
1. **Core Summary** (`bot/memory/core.py`) - System prompt context (Tier 1)
2. **Working Files** (in-memory during Claude session) - Tier 2
3. **Archive Search** (`bot/memory/search.py`) - Semantic search over `.md` files (Tier 3)

**Embeddings Storage:**
- No database — sidecar `.{filename}.embeddings.json` files alongside source `.md` files
- JSON format: `{file, file_hash, model, chunks: [{text, hash, embedding}]}`
- Cached embeddings reused on re-indexing (if file hash unchanged)

---

*Integration audit: 2026-04-13*
