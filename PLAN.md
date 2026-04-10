# Animaya Rewrite Plan — Voidnet Integration

## Vision

Animaya becomes a **paid personal AI assistant service** within Voidnet. Users pay for an isolated Claude Code-powered assistant connected to Telegram. Each bot runs in a sandboxed Docker container that can only break itself, never the host.

---

## Stack Decision: Python

**Why Python over alternatives:**
- `claude-code-sdk` is Python-native — the core dependency
- AI coding agents (Claude Code, Cursor, etc.) are most productive in Python: clear semantics, excellent LSP, massive training data
- FastAPI is minimal, typed, well-documented — AI agents can modify it confidently
- V3 proved the pattern works in ~600 lines
- Solo dev + AI agents = optimize for readability and iteration speed, not runtime performance

**Why not Rust:** claude-code-sdk has no Rust bindings. Would require FFI or subprocess bridges, adding complexity that hurts AI-agent maintainability.

**Why not TypeScript:** Would work, but Python's stdlib + ecosystem is richer for the file/process/memory operations animaya needs. No clear advantage over Python here.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  mcow server (Voidnet infra)                        │
│                                                     │
│  Caddy (443) ─┬─ animaya.makscee.ru → Platform API  │
│               ├─ {slug}.animaya.makscee.ru → Bot UI  │
│               └─ voidnet.makscee.ru → Voidnet API    │
│                                                     │
│  ┌─────────────────────────────────────────┐        │
│  │  Platform Container (privileged)        │        │
│  │  - FastAPI control plane                │        │
│  │  - Bot lifecycle (Docker API)           │        │
│  │  - Billing/user management              │        │
│  │  - Admin dashboard                      │        │
│  │  - Image builder/updater                │        │
│  └──────────┬──────────────────────────────┘        │
│             │ docker.sock (only platform has this)   │
│  ┌──────────▼──────────────────────────────┐        │
│  │  Bot Container (sandboxed, per-user)    │        │
│  │  - Telegram bridge                      │        │
│  │  - Claude Code SDK                      │        │
│  │  - Memory/Spaces module                 │        │
│  │  - Dashboard (FastAPI, port 8090)       │        │
│  │  - Git auto-versioning of /data         │        │
│  │  ┌────────────────────────────────┐     │        │
│  │  │  /data (persistent volume)     │     │        │
│  │  │  ├── memory/                   │     │        │
│  │  │  ├── spaces/                   │     │        │
│  │  │  ├── sessions/                 │     │        │
│  │  │  ├── uploads/                  │     │        │
│  │  │  └── config.json               │     │        │
│  │  └────────────────────────────────┘     │        │
│  └─────────────────────────────────────────┘        │
│  (repeat per user)                                   │
└─────────────────────────────────────────────────────┘
```

---

## Isolation & Safety Model

### Bot containers are sandboxed:
- **No docker.sock** — bots cannot create/destroy containers
- **Read-only root filesystem** — only `/data` and `/tmp` are writable
- **Resource limits** — CPU (1 core), memory (2GB), disk quota via volume size
- **No host network** — bridge network only, no access to host services
- **No privileged mode** — drop all capabilities except what's needed
- **Seccomp profile** — restrict syscalls
- **PID namespace** — isolated process tree

### Bots can only break themselves:
- Claude Code runs inside the bot container, can only modify `/data`
- `pip install` is blocked at runtime (removed from PATH or aliased to error). To install packages, the bot edits `/data/bot.Dockerfile` and requests a rebuild from the platform API
- Platform rebuilds the container from `bot.Dockerfile` (extends base image), so all installs are versioned and rollbackable
- If a bot corrupts itself, platform can rollback via git or rebuild from previous image tag

### Versioning & Rollback:
1. **Code versioning** — Docker image tags. Platform pins each bot to an image version. Rolling updates with canary (update one bot, verify, then all).
2. **Data versioning** — Git auto-commit of `/data` every 5 minutes. Platform can `git revert` to any point.
3. **Config versioning** — `config.json` changes tracked in the same git repo.
4. **Snapshots** — Platform can create tarball snapshots of entire `/data` volume before risky operations.

---

## Module Structure

```
makscee/animaya/
├── platform/                    # Control plane (runs in platform container)
│   ├── main.py                 # FastAPI app entry
│   ├── bot_manager.py          # Docker container lifecycle (create/start/stop/restart/delete)
│   ├── bot_store.py            # Bot registry, config management
│   ├── billing.py              # Usage tracking, Boosty/Voidnet subscription integration
│   ├── admin_dashboard.py      # Web UI for managing bots
│   └── routes/                 # API route modules
│       ├── bots.py             # CRUD endpoints
│       ├── users.py            # User management
│       └── health.py           # Health checks
│
├── bot/                         # Bot code (runs in per-user container)
│   ├── main.py                 # Entry: starts Telegram bridge + dashboard
│   ├── claude_query.py         # claude-code-sdk options builder
│   ├── bridge/
│   │   ├── telegram.py         # Telegram message handler + streaming
│   │   └── formatting.py       # Markdown → Telegram HTML
│   ├── memory/
│   │   ├── manager.py          # 3-tier memory orchestration
│   │   ├── core.py             # Tier 1: core summary (injected into system prompt)
│   │   ├── spaces.py           # Spaces module: per-topic file collections
│   │   └── search.py           # Semantic search over memory/spaces (embeddings sidecar)
│   ├── features/
│   │   ├── audio.py            # Voice transcription (Groq Whisper)
│   │   ├── image_gen.py        # Image generation (Gemini)
│   │   ├── git_versioning.py   # Auto-commit /data changes
│   │   └── self_dev.py         # Self-modification (edits bot.Dockerfile, triggers rebuild)
│   ├── dashboard/
│   │   ├── app.py              # FastAPI web UI
│   │   ├── auth.py             # Telegram Login Widget auth
│   │   └── templates/          # Jinja2 templates
│   └── templates/
│       └── CLAUDE.md           # Bot behavior template (identity, memory, skills)
│
├── shared/                      # Shared between platform and bot
│   ├── models.py               # Pydantic models (bot config, user, etc.)
│   └── constants.py            # Shared constants
│
├── docker/
│   ├── Dockerfile.platform     # Platform container image
│   ├── Dockerfile.bot          # Bot container image (Python + Node.js + Claude Code CLI)
│   └── docker-compose.yml      # Full stack for mcow deployment
│
├── scripts/
│   ├── deploy.sh               # Deploy to mcow (build + push + restart)
│   └── dev.sh                  # Local development setup
│
├── tests/
│   ├── test_bot/               # Bot unit tests
│   ├── test_platform/          # Platform unit tests
│   └── smoke/                  # Integration smoke tests
│
├── pyproject.toml              # Dependencies + project metadata
├── CLAUDE.md                   # AI agent development guide
└── README.md                   # Project overview
```

---

## Features (ported from V3 + new)

### Core (from V3)
- [x] Telegram bridge with streaming responses (progressive message edits)
- [x] Claude Code SDK integration (claude-sonnet-4-6)
- [x] 3-tier memory system (core → files → archive search)
- [x] Spaces module (per-topic file collections with skills)
- [x] Voice transcription (Groq Whisper)
- [x] Image generation (Gemini)
- [x] Web dashboard (chat, files, settings)
- [x] Telegram Login Widget auth
- [x] Git auto-versioning of data
- [x] Self-modification (bot.Dockerfile edits → platform rebuild, no runtime pip)
- [x] Group chat support (@mention, reply-to)
- [x] File/photo/document handling
- [x] Per-session conversation isolation (cwd-based)
- [x] CLAUDE.md template for bot behavior

### New for Voidnet integration
- [ ] Platform control plane with billing hooks
- [ ] Caddy integration (auto-configure routes for new bots)
- [ ] Usage metering (API calls, tokens, storage)
- [ ] Bot health monitoring + auto-restart
- [ ] Voidnet user auth (link Telegram accounts from Voidnet DB)
- [ ] One-click bot provisioning from Voidnet portal

---

## Deployment on mcow

### Caddy config addition:
```
animaya.makscee.ru {
    reverse_proxy localhost:8070  # platform API
}

*.animaya.makscee.ru {
    reverse_proxy localhost:8090  # per-bot dashboards (platform routes internally)
}
```

### Docker setup:
- Platform container: always running, has docker.sock
- Bot containers: created/managed by platform, one per user
- Images built locally on mcow or via GHCR
- Data volumes: `/opt/animaya/data/bots/{slug}/`

### Deployment flow:
```bash
# From dev machine:
git push origin main  # triggers CI or manual deploy

# On mcow:
cd /opt/animaya
git pull
docker compose build
docker compose up -d platform
# Platform auto-manages bot containers
```

---

## Implementation Phases

### Phase 1: Foundation (MVP)
**Goal:** Single bot working on mcow, end-to-end

1. Initialize repo with pyproject.toml, Dockerfile.bot, CLAUDE.md
2. Port `bot/` from V3: claude_query.py, telegram bridge, formatting
3. Port memory module with Spaces
4. Port audio transcription + image generation
5. Create Dockerfile.bot (Python 3.12 + Node.js 22 + Claude Code CLI)
6. Create docker-compose.yml for single-bot deployment
7. Deploy to mcow, configure Caddy
8. Verify: send Telegram message → get Claude response

### Phase 2: Dashboard & Versioning
**Goal:** Web UI + data safety

1. Port FastAPI dashboard (chat, files, settings)
2. Port Telegram Login Widget auth
3. Implement git auto-versioning
4. Add rollback capability (git revert via dashboard or CLI)
5. Add health check endpoint

### Phase 3: Platform (Multi-tenant)
**Goal:** Multiple users, each with isolated bot

1. Build platform control plane (FastAPI)
2. Bot CRUD API (create/start/stop/restart/delete)
3. Bot registry + config store
4. Docker container lifecycle management
5. Caddy auto-configuration for new bots
6. Admin dashboard
7. Resource limits + sandboxing

### Phase 4: Voidnet Integration & Billing
**Goal:** Paid service

1. Link Voidnet user accounts (shared SQLite or API)
2. Bot provisioning from Voidnet portal
3. Usage metering (token counting, storage tracking)
4. Boosty subscription integration (via Voidnet)
5. User self-service (create bot, manage subscription via Voidnet portal)

---

## Confirmed Decisions

1. **Domain**: `animaya.makscee.ru` (platform) + `{slug}.animaya.makscee.ru` (per-bot dashboards)
2. **Model**: Default `claude-sonnet-4-6`. No user model selection for now.
3. **Billing**: Within Voidnet via Boosty integration (not Stripe)
4. **Bots per user**: 1 bot per user (for now)
5. **Self-dev**: Bots can ONLY install packages via `bot.Dockerfile` — a per-bot Dockerfile that extends the base image. Runtime `pip install` is blocked. Claude Code edits `bot.Dockerfile`, platform rebuilds the container. This ensures:
   - All installs are versioned (Dockerfile is in git)
   - Rollback = rebuild from previous Dockerfile version
   - No hidden runtime state drift
   - Platform controls when rebuilds happen
