# Architecture

**Analysis Date:** 2026-04-13

## Pattern Overview

**Overall:** Modular AI Assistant with Multi-Interface Bridge

Animaya is a Claude Code-powered personal assistant platform with three core components: a Telegram chat bridge, a FastAPI dashboard backend, and a 3-tier memory system. Each bot instance runs isolated in Docker and manages its own data, Claude Code sessions, and configuration.

**Key Characteristics:**
- Event-driven architecture with streaming responses
- Per-user concurrency control (asyncio locks per Telegram user)
- 3-tier memory hierarchy (core summary → working files → semantic search)
- Modular features system with pluggable integration handlers
- Git-versioned persistent data with auto-commit background thread

## Layers

**Interface Layer (Bridge):**
- Purpose: Receive messages from external systems, format responses, stream back
- Location: `bot/bridge/` (`telegram.py`, `formatting.py`)
- Contains: Telegram message handlers, markdown→HTML converters, streaming throttle logic
- Depends on: Claude Code SDK, python-telegram-bot, formatting utilities
- Used by: Telegram bot polling loop in `bot/main.py`
- Pattern: Handler-based (one async handler per message type)

**Query Builder Layer:**
- Purpose: Single source of truth for constructing ClaudeCodeOptions with context
- Location: `bot/claude_query.py`
- Contains: `build_options()` that assembles system prompt, model config, working directory
- Depends on: Claude Code SDK, memory.core, config.json
- Used by: Telegram bridge and dashboard chat endpoints
- Pattern: Factory function returning configured SDK options

**Memory Layer (3-Tier):**
- Purpose: Provide contextual information at different granularities
- Location: `bot/memory/`

  **Tier 1 (Core):** `bot/memory/core.py`
  - ~500 token budget for system prompt injection
  - Reads: SOUL.md (identity), OWNER.md (owner info), memory/facts.md (recent facts), spaces/ (active workspaces)
  - Used by: Query builder to enrich system prompt
  - Pattern: Summarization (SOUL truncated to 400 chars, OWNER to 500 chars)

  **Tier 2 (Working):** Filesystem directly accessible to Claude Code
  - /data/* is Claude's working directory
  - Includes: sessions/, memory/, spaces/, config files
  - Pattern: Claude reads/writes via file tools (Read, Write, Edit, Grep)

  **Tier 3 (Archive Search):** `bot/memory/search.py`
  - Semantic search via embeddings (OpenAI text-embedding-3-small by default)
  - Chunks markdown files, stores .embeddings.json sidecar files
  - CLI tool: `python -m bot.memory.search "query"`
  - Pattern: Vector similarity search over chunked documents

**Features Layer:**
- Purpose: Handle specialized integrations and self-modification
- Location: `bot/features/`
- Components:
  - `audio.py`: Voice transcription (Groq Whisper API)
  - `image_gen.py`: Image generation (Gemini API)
  - `git_versioning.py`: Auto-commit thread with interval-based polling
  - `self_dev.py`: bot.Dockerfile mutation interface (read/append/add-package)
- Used by: Main bot, dashboard modules system
- Pattern: Module with public functions, no shared state

**Dashboard API Layer:**
- Purpose: REST endpoints for Next.js frontend
- Location: `bot/dashboard/app.py`
- Endpoints: /api/modules, /api/chat, /api/files, /api/settings, /api/stats, /api/logs, /api/chat/history
- Contains: FastAPI app with CORS middleware, SSE event bus for streaming
- Depends on: FastAPI, pydantic, same memory/query layers as Telegram
- Pattern: RESTful + Server-Sent Events for streaming
- Runs on: Port 8090 in background thread from main.py

**Dashboard Frontend Layer:**
- Purpose: Web UI for chat, file management, settings, module management
- Location: `dashboard/src/`
- Framework: Next.js 14+ (App Router)
- Pages:
  - `app/page.tsx`: Home/landing
  - `app/chat/page.tsx`: Chat interface with streaming
  - `app/files/page.tsx`: File browser and editor
  - `app/history/page.tsx`: Chat history/sessions
  - `app/modules/page.tsx`: Module installation UI
  - `app/settings/page.tsx`: Bot configuration
  - `app/stats/page.tsx`: Usage statistics
  - `app/logs/page.tsx`: Log viewer
- Components: `components/Sidebar.tsx` (navigation)
- Libs: `lib/api.ts` (API client), `lib/types.ts` (shared types), `lib/modules.ts`
- Pattern: Component-based with server/client boundary at page level

**Data Persistence Layer:**
- Purpose: Durable storage of bot data and conversation context
- Location: `/data/` (Docker volume)
- Contains:
  - `CLAUDE.md`: Dynamic instructions assembled from modules
  - `SOUL.md`: Bot identity and personality
  - `OWNER.md`: Owner information
  - `config.json`: Model, features, module configuration
  - `bot.Dockerfile`: Self-modification specification
  - `memory/`: Tier 3 memory files (facts.md, people.md, projects.md)
  - `spaces/`: Knowledge workspaces (@project-name directories)
  - `sessions/`: Chat session history per session ID
  - `.git/`: Version history (if enabled)
- Pattern: Git-backed filesystem with auto-commit

## Data Flow

**User Message Flow:**

1. **Telegram → Bridge:** User sends message via Telegram
2. **Concurrency Control:** Lock acquired per user_id (prevents parallel queries)
3. **Query Assembly:** `build_options()` called with data_dir, gets core context from memory/core.py
4. **Claude SDK:** Message + system_prompt sent to Claude Code SDK via ClaudeCodeOptions
5. **Streaming:** Response streamed back from SDK in chunks
6. **Markdown Conversion:** TG HTML formatter applies Markdown→HTML conversion
7. **Throttled Updates:** Min 0.5s between updates, min 30 chars accumulated
8. **Telegram Send:** HTML message sent back, split if >4096 chars
9. **Memory Consolidation:** Post-response, bot can save new facts to memory/

**Dashboard Message Flow:**

1. **React UI:** User types in chat.tsx, calls `sendMessage(text)` via api.ts
2. **API Handler:** POST /api/chat endpoint enqueues message
3. **Streaming:** Client calls `streamChat()` which opens EventSource to /api/chat/stream
4. **SSE Events:** Server publishes "token", "tool", "done" events via _event_queues
5. **UI Update:** Chat component appends tokens in real-time

**Module Installation Flow:**

1. **Dashboard UI:** modules/page.tsx shows available modules
2. **Install Request:** POST /api/modules/{id}/install with config
3. **Config Storage:** config.json updated with module ID → config mapping
4. **CLAUDE.md Rebuild:** `_rebuild_claude_md()` assembles base + module .md files
5. **Symlinks:** Session CLAUDE.md symlinks updated to point to /data/CLAUDE.md
6. **Next Bot Run:** New instructions available to Claude

**Git Auto-Commit Flow:**

1. **Startup:** If /data/.git exists, `start_auto_commit()` spawns background thread
2. **Polling Loop:** Every GIT_COMMIT_INTERVAL (default 300s), check for changes
3. **Commit:** `git add -A` → `git commit` with timestamp message
4. **Shutdown:** SIGTERM/SIGINT triggers `commit_if_changed()` before exit

## Key Abstractions

**ClaudeCodeOptions:**
- Purpose: Configuration wrapper for Claude Code SDK queries
- Files: `bot/claude_query.py` (builder)
- Pattern: Factory function `build_options()` returns ready-to-use options
- Critical fields: model, system_prompt, cwd, allowed_tools, permission_mode

**Memory Context:**
- Purpose: Hierarchical information injection into Claude's context
- Files: `bot/memory/core.py` (builder)
- Pattern: `build_core_context()` assembles Tier 1 snippet, returns markdown string
- Pattern: `build_consolidation_prompt()` provides instructions for post-conversation memory save

**Message Streaming:**
- Purpose: Progressive token-by-token delivery to client
- Files: `bot/bridge/telegram.py` (streaming throttle), `bot/dashboard/app.py` (SSE)
- Pattern: Min interval + min chars buffering to avoid UI flicker
- Pattern: SSE for web, Telegram edit_message for mobile

**Module System:**
- Purpose: Pluggable feature installation without editing source
- Files: `bot/dashboard/app.py` (/api/modules endpoints)
- Pattern: config.json stores module ID → config mapping
- Pattern: Templates in bot/templates/modules/{id}.md assembled into CLAUDE.md at runtime
- Pattern: Module markdown documents feature availability and usage

**Self-Development:**
- Purpose: Bots can request container rebuilds without shell access
- Files: `bot/features/self_dev.py`
- Pattern: `bot.Dockerfile` file in /data/ appended with RUN commands
- Pattern: Runtime pip blocked; platform rebuilds container from dockerfile

## Entry Points

**Main Process:**
- Location: `bot/__main__.py` and `bot/main.py`
- Triggers: `python -m bot` or docker entrypoint
- Responsibilities:
  1. Validate env vars (TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN)
  2. Initialize /data directory
  3. Rebuild CLAUDE.md from modules
  4. Start git auto-commit thread (if .git exists)
  5. Start FastAPI dashboard on port 8090 (background)
  6. Start Telegram polling (blocks main thread)
  7. On SIGTERM/SIGINT: commit data and exit

**Telegram Message Handler:**
- Location: `bot/bridge/telegram.py:_handle_message()` (via @app.message_handler)
- Triggers: User sends text/voice/photo/file
- Responsibilities:
  1. Acquire per-user asyncio lock
  2. Build query options with core context
  3. Stream response from Claude SDK
  4. Format to Telegram HTML
  5. Send back in chunks

**Dashboard Chat Endpoint:**
- Location: `bot/dashboard/app.py:@app.post("/api/chat")`
- Triggers: React frontend sendMessage()
- Responsibilities:
  1. Parse request JSON
  2. Build options same as Telegram
  3. Stream to /api/chat/stream via SSE
  4. Queue events for all connected clients

**Module Installation Endpoint:**
- Location: `bot/dashboard/app.py:@app.post("/api/modules/{id}/install")`
- Triggers: Module install button in UI
- Responsibilities:
  1. Load config.json
  2. Store module ID + config
  3. Call `_rebuild_claude_md()`
  4. Update symlinks in session dirs

## Error Handling

**Strategy:** Graceful degradation with detailed logging

**Patterns:**

**SDK Compatibility:** Patch `message_parser.parse_message` to skip unknown message types instead of crashing (`bot/bridge/telegram.py` line 46-69)

**Missing Context:** If Tier 1 memory files don't exist, `build_core_context()` returns empty string — system prompt works with or without context

**API Errors:** FastAPI endpoints return 4xx/5xx with JSON error detail; frontend shows "Connection lost" on EventSource error

**Git Failures:** `_run_git()` catches exceptions, logs at DEBUG level, returns empty string — non-blocking

**Async Lock Timeout:** Per-user lock uses non-blocking acquire (line 89-98 in telegram.py) — if busy, message is queued instead of blocking

**Shutdown:** SIGTERM/SIGINT caught, `commit_if_changed()` called before exit — prevents data loss on container stop

## Cross-Cutting Concerns

**Logging:** 
- Framework: Python logging with format `%(asctime)s [%(name)s] %(levelname)s: %(message)s`
- Configured in `bot/main.py` at INFO level
- Available via dashboard /api/logs endpoint

**Validation:**
- Env vars checked at startup (TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN required)
- JSON config (config.json, .embeddings.json files) parsed with try/except, safe defaults
- Telegram message parsed with filters (text, voice, photo, document)

**Authentication:**
- Telegram: Bot token from @BotFather
- Claude Code: OAuth token from env (CLAUDE_CODE_OAUTH_TOKEN)
- Dashboard: Optional DASHBOARD_TOKEN for /api/* endpoints (auth.py)

**Data Format Consistency:**
- Memory files: Markdown with conventions (SOUL.md = identity, OWNER.md = owner, spaces with @ prefix)
- Config: JSON (config.json, .embeddings.json)
- Chat history: JSON in sessions/{session_id}
- Auto-commit messages: Timestamp format `YYYY-MM-DD HH:MM`

---

*Architecture analysis: 2026-04-13*
