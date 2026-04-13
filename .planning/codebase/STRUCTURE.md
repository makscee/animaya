# Codebase Structure

**Analysis Date:** 2026-04-13

## Directory Layout

```
animaya/
├── bot/                           # Python bot package (Telegram + Claude Code SDK)
│   ├── __init__.py
│   ├── __main__.py                # Module entry point (python -m bot)
│   ├── main.py                    # Main bot process initialization
│   ├── claude_query.py            # Query builder (single source of truth for SDK options)
│   ├── bridge/                    # External service integrations
│   │   ├── __init__.py
│   │   ├── telegram.py            # Telegram message handler + streaming
│   │   └── formatting.py          # Markdown → Telegram HTML converter
│   ├── memory/                    # 3-tier memory system
│   │   ├── __init__.py
│   │   ├── core.py                # Tier 1: Core context for system prompt injection
│   │   └── search.py              # Tier 3: Semantic search with embeddings
│   ├── features/                  # Specialized integrations
│   │   ├── __init__.py
│   │   ├── audio.py               # Voice transcription (Groq Whisper)
│   │   ├── image_gen.py           # Image generation (Gemini)
│   │   ├── git_versioning.py      # Auto-commit background thread
│   │   └── self_dev.py            # bot.Dockerfile mutation interface
│   ├── dashboard/                 # FastAPI backend for Next.js frontend
│   │   ├── __init__.py
│   │   ├── app.py                 # REST API endpoints
│   │   └── auth.py                # Dashboard authentication
│   └── templates/                 # Module markdown templates
│       ├── CLAUDE.md              # Base instructions (assembled dynamically)
│       └── modules/               # Feature module documentation
│           ├── voice.md
│           ├── identity.md
│           ├── image-gen.md
│           ├── memory.md
│           ├── spaces.md
│           └── self-dev.md
├── dashboard/                     # Next.js frontend (TypeScript/React)
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── public/                    # Static assets
│   ├── src/
│   │   ├── app/                   # Next.js App Router pages
│   │   │   ├── layout.tsx         # Root layout (Sidebar + outlet)
│   │   │   ├── page.tsx           # Home page
│   │   │   ├── chat/
│   │   │   │   └── page.tsx       # Chat interface (streaming messages)
│   │   │   ├── files/
│   │   │   │   └── page.tsx       # File browser + editor
│   │   │   ├── history/
│   │   │   │   └── page.tsx       # Chat session history
│   │   │   ├── modules/
│   │   │   │   └── page.tsx       # Module marketplace + installer
│   │   │   ├── settings/
│   │   │   │   └── page.tsx       # Bot settings (model, language, etc.)
│   │   │   ├── stats/
│   │   │   │   └── page.tsx       # Usage statistics
│   │   │   └── logs/
│   │   │       └── page.tsx       # Log viewer
│   │   ├── components/
│   │   │   └── Sidebar.tsx        # Navigation sidebar
│   │   └── lib/
│   │       ├── api.ts             # API client functions
│   │       ├── types.ts           # Shared TypeScript interfaces
│   │       └── modules.ts         # Module management utilities
│   └── README.md
├── shared/                        # Python shared models
│   ├── __init__.py
│   └── models.py                  # Pydantic dataclasses (BotConfig)
├── docker/                        # Container configuration
│   ├── Dockerfile.bot             # Python 3.12 + Node.js 22 + Claude CLI
│   └── docker-compose.yml         # Single-bot deployment spec
├── scripts/                       # Deployment and utility scripts
│   └── deploy.sh
├── pyproject.toml                 # Python project config (ruff, dependencies)
├── CLAUDE.md                      # Project instructions (checked into repo)
├── PLAN.md                        # Implementation roadmap
├── ISSUES.md                      # Known issues and tracking
└── DASHBOARD.md                   # Dashboard documentation
```

## Directory Purposes

**`bot/`:**
- Purpose: Core bot application (Telegram bridge + Claude Code SDK integration)
- Contains: Message handlers, memory system, API bridge, feature modules
- Key files: `main.py` (entry), `claude_query.py` (query builder)

**`bot/bridge/`:**
- Purpose: External service adapters
- Contains: Telegram handler, message formatting logic
- Pattern: Handler-based (one async function per message type)

**`bot/memory/`:**
- Purpose: Hierarchical context and search
- Contains: Core summary builder, semantic search with embeddings
- Key files: `core.py` (Tier 1 prompt injection), `search.py` (vector search)

**`bot/features/`:**
- Purpose: Pluggable integrations and self-modification
- Contains: Voice, image, git versioning, dockerfile mutation
- Pattern: Stateless utility modules with public functions

**`bot/dashboard/`:**
- Purpose: FastAPI backend providing REST API
- Contains: Endpoints for chat, files, modules, settings, logs
- Running: Background thread on port 8090 from main.py

**`bot/templates/`:**
- Purpose: Documentation and feature specifications
- Contains: `CLAUDE.md` base + per-module markdown files
- Pattern: Dynamically assembled into /data/CLAUDE.md at runtime

**`dashboard/`:**
- Purpose: Next.js frontend web UI
- Contains: Pages (chat, files, settings, modules), components, API client
- Framework: Next.js 14+ App Router with Tailwind CSS

**`dashboard/src/app/`:**
- Purpose: Route pages in Next.js App Router
- Structure: One `page.tsx` per route, shared `layout.tsx`
- Pattern: Server/client boundary at page level

**`dashboard/src/lib/`:**
- Purpose: Utilities and types
- Key: `api.ts` (fetchJSON + typed endpoints), `types.ts` (shared interfaces)

**`shared/`:**
- Purpose: Shared Python models
- Contains: BotConfig dataclass
- Pattern: Imported by bot and dashboard backend

**`docker/`:**
- Purpose: Container build specifications
- Contains: Multi-stage Dockerfile, docker-compose for local dev
- Pattern: bot.Dockerfile extended by user at runtime (in /data)

## Key File Locations

**Entry Points:**
- `bot/__main__.py`: Module entry point (calls bot.main.main())
- `bot/main.py`: Main function that starts Telegram polling + dashboard
- `dashboard/src/app/layout.tsx`: Root layout (renders Sidebar + outlet)
- `dashboard/src/app/page.tsx`: Home page

**Configuration:**
- `bot/claude_query.py`: Query builder (how to call Claude SDK)
- `shared/models.py`: Shared config models
- `dashboard/src/lib/types.ts`: API response types
- `pyproject.toml`: Python project manifest

**Core Logic:**
- `bot/bridge/telegram.py`: Message handler (lines 1-200+ complex concurrency)
- `bot/memory/core.py`: System prompt context builder
- `bot/dashboard/app.py`: FastAPI routes (lines 1-100+ endpoint definitions)

**Testing:**
- Not detected (no test/ directory or pytest files)

## Naming Conventions

**Files:**
- Python files: `snake_case.py` (e.g., `telegram.py`, `git_versioning.py`)
- TypeScript files: `camelCase.tsx` for React, `camelCase.ts` for utilities
- Package directories: Lowercase with underscores (e.g., `bot/`, `dashboard/`)
- Templates: `UPPERCASE.md` (SOUL.md, OWNER.md, CLAUDE.md)
- Config files: `config.json`, `*.env*`

**Directories:**
- Feature directories: Lowercase plural or singular based on scope
  - `bot/bridge/` — adapters
  - `bot/memory/` — memory system
  - `bot/features/` — feature modules
  - `bot/dashboard/` — API layer
  - `dashboard/src/` — frontend source

**Functions:**
- Python: snake_case (e.g., `build_core_context()`, `commit_if_changed()`)
- TypeScript: camelCase for functions and variables (e.g., `fetchJSON()`, `sendMessage()`)

**Classes/Types:**
- Python: PascalCase (e.g., `BotConfig`)
- TypeScript: PascalCase for interfaces and types (e.g., `Module`, `ChatMessage`)

**Environment Variables:**
- UPPERCASE_SNAKE_CASE (e.g., TELEGRAM_BOT_TOKEN, CLAUDE_CODE_OAUTH_TOKEN, DATA_PATH)

**Data Files in /data/:**
- Core memory: `SOUL.md`, `OWNER.md` (identity files)
- Memory: `/data/memory/{facts.md, people.md, projects.md}`
- Spaces: `/data/spaces/@project-name/` (kebab-case with @ prefix)
- Config: `config.json`, `bot.Dockerfile`
- Sessions: `/data/sessions/{session_id}/`

## Where to Add New Code

**New Telegram Feature:**
- Primary code: `bot/features/{feature_name}.py`
- Handler hook: Add async handler in `bot/bridge/telegram.py:build_app()`
- Documentation: `bot/templates/modules/{feature_name}.md`
- API endpoint (if dashboard UI needed): Add to `bot/dashboard/app.py`

**New Dashboard Page:**
- Page implementation: `dashboard/src/app/{route}/page.tsx`
- API client calls: Use `lib/api.ts` functions (add new if needed)
- Update Sidebar: `dashboard/src/components/Sidebar.tsx` with new link

**New Memory Feature:**
- If Tier 1 (system prompt): Modify `bot/memory/core.py:build_core_context()`
- If Tier 3 (search): Extend `bot/memory/search.py` search logic
- Add markdown files to `/data/memory/` at runtime (Claude creates them)

**New External Integration:**
- Feature module: `bot/features/{service_name}.py`
- Environment variables: Document in CLAUDE.md, add to .env.example
- Error handling: Wrap API calls with try/except, log failures

**Configuration Changes:**
- Bot config keys: Add to `shared/models.py:BotConfig`
- Dashboard settings: Add form field to `dashboard/src/app/settings/page.tsx`
- Environment config: Document in project CLAUDE.md

**Shared Utilities:**
- Python: Add functions to `shared/models.py` or create `bot/utils.py`
- TypeScript: Add to `dashboard/src/lib/` with meaningful name (lib/dates.ts, lib/validators.ts)

## Special Directories

**`/data/`:**
- Purpose: Persistent bot data (Docker volume mounted)
- Generated: Yes (created by bot at startup)
- Committed: No (volume-based, not in git)
- Contains: CLAUDE.md, SOUL.md, OWNER.md, config.json, memory/, spaces/, sessions/, .git/, bot.Dockerfile
- Git-managed: Optional (.git created by user, auto-commit if present)

**`node_modules/`:**
- Purpose: npm dependencies for dashboard
- Generated: Yes (npm install)
- Committed: No (listed in .gitignore)

**`__pycache__/`:**
- Purpose: Python bytecode cache
- Generated: Yes (Python runtime)
- Committed: No (listed in .gitignore)

**`bot/templates/modules/`:**
- Purpose: Module documentation fragments
- Generated: No (static in repo)
- Committed: Yes
- Usage: Assembled into /data/CLAUDE.md dynamically by `_rebuild_claude_md()`

**`dashboard/public/`:**
- Purpose: Static files served by Next.js
- Generated: No (static in repo)
- Committed: Yes

---

*Structure analysis: 2026-04-13*
