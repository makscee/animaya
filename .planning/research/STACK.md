# Stack Research

**Domain:** Modular AI assistant platform — Telegram bridge + web dashboard + plugin system on LXC
**Researched:** 2026-04-13
**Confidence:** HIGH (core), MEDIUM (module system patterns)

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | Ships on modern LXC base images; type hints, async, match statements all stable. 3.12 gives noticeable perf improvement over 3.10. |
| aiogram | 3.27.0 | Telegram bridge | Fully async (asyncio + aiohttp), FSM built-in for onboarding flows, middleware system for cross-cutting concerns, webhook and polling both supported. Most actively maintained Python Telegram library in 2026. |
| claude-agent-sdk | 0.1.58 | Claude Code integration | Official Anthropic SDK. `claude-code-sdk` is deprecated — this is the successor. Bundles Claude Code CLI, exposes `query()` as async iterator for streaming. Required Python 3.10+. |
| FastAPI | 0.115.x | Web dashboard backend | ASGI, async-native, OpenAPI auto-docs, SSE support built-in. Standard choice for Python API + dashboard backends in 2026. Pairs cleanly with Jinja2 + HTMX for server-rendered UI. |
| Uvicorn | 0.44.0 | ASGI server | The standard server for FastAPI. Single-process is fine for per-user LXC deployment (one bot, one dashboard, low concurrency). |
| Jinja2 | 3.x | Dashboard templating | Bundled with FastAPI's template support. Server-side rendering avoids npm/build toolchain entirely — correct for LXC install-script target. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| HTMX | 2.x (CDN) | Dashboard interactivity | Replaces JS framework for dynamic UI — partial page updates, SSE streaming, form handling. Load from CDN, no build step. |
| Tailwind CSS | 3.x (CDN play) | Dashboard styling | Use via CDN play.min.css for zero build-step styling. Acceptable for low-traffic internal dashboard. |
| python-dotenv | 1.x | Env config | `.env` file loading for local dev and LXC deployments without systemd env injection. |
| anyio | 4.x | Async compatibility | Required by claude-agent-sdk internally; also useful for running async tasks from sync contexts during module lifecycle hooks. |
| GitPython | 3.x | Git versioning module | Programmatic git operations for the git-versioning module (auto-commit Hub knowledge/ changes). Only loaded when that module is installed. |
| pydantic | 2.x | Module manifests + config | FastAPI already depends on it. Use for parsing module `manifest.json` files — validates required fields, version constraints. |
| watchdog | 5.x | Module hot-detection | Watches `modules/` directory for install/uninstall events without polling. Use `watchfiles` (Rust-backed) as alternative if perf matters. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Ruff | Linting + formatting | Replaces flake8 + black + isort. Single tool, fast, line-length 100 (matches existing codebase convention). |
| pytest + pytest-asyncio | Testing | `asyncio_mode = "auto"` in pyproject.toml eliminates boilerplate for async test functions. |
| pyproject.toml | Project metadata + deps | PEP 621 standard. Use `[project.optional-dependencies]` for per-module dev extras if needed. |

## Installation

```bash
# Core runtime
pip install aiogram==3.27.0 claude-agent-sdk fastapi uvicorn[standard] jinja2

# Supporting
pip install python-dotenv anyio pydantic watchdog

# Git versioning module (optional, loaded by module)
pip install gitpython

# Dev
pip install ruff pytest pytest-asyncio
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| aiogram 3 | python-telegram-bot 21.x | If team is unfamiliar with asyncio and bot load is low. PTB has better beginner docs. Avoid for this project — aiogram's FSM is cleaner for onboarding flows. |
| aiogram 3 | Telethon | Only if you need user-account API (MTProto), not bot API. Not applicable here. |
| claude-agent-sdk | Direct Anthropic API (anthropic Python SDK) | If you need raw API access without Claude Code CLI (e.g., no tool use, just completions). For this project the SDK's streaming + tool use integration is required. |
| FastAPI + Jinja2 + HTMX | FastAPI + React/Vue SPA | Use SPA if dashboard becomes complex enough to warrant client-side state. For v1 (module install/uninstall, chat log view, config forms) SSR is sufficient and eliminates npm from install script. |
| FastAPI + Jinja2 + HTMX | Streamlit / Gradio | Those frameworks fight you when you need auth, custom layouts, or non-ML UI. Avoid for dashboards with auth and module management. |
| Uvicorn (single process) | Gunicorn + Uvicorn workers | Use Gunicorn only if running multi-user on shared infra. Per-user LXC model means one process is correct and simpler. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `claude-code-sdk` (PyPI) | Deprecated, unmaintained as of 2025. PyPI page redirects migration guidance to claude-agent-sdk. | `claude-agent-sdk` 0.1.58+ |
| Docker inside LXC | Project constraint: LXC-native only. Nested virtualization adds overhead and breaks the install-script model. | Native Python services managed by systemd or supervisor |
| npm / Node build toolchain in install script | Forces complex dependency on every LXC. Dashboard is internal, low-traffic. | HTMX + Tailwind via CDN, Jinja2 server-rendered templates |
| SQLite / PostgreSQL for module state | Overkill for this use case. State is human-readable config + notes. | Markdown files in Hub `knowledge/` structure, git-versioned |
| Celery / Redis task queue | Async Python handles the concurrency needs of a single-user bot natively. | `asyncio` tasks, `anyio` for cross-library compat |
| Flask | Sync by default, no native SSE, requires extensions for everything FastAPI has built-in. | FastAPI |

## Stack Patterns by Variant

**Module manifest format:**
- Use `manifest.json` (pydantic-validated) for machine-readable metadata: name, version, requires, hooks
- Use a `README.md` alongside for human-readable description
- Pattern proven by Odoo, VSCode extensions, and Ansible roles — simple, no registry needed

**Module lifecycle hooks:**
- Each module exposes optional Python entry points: `install()`, `uninstall()`, `on_message()`, `on_startup()`
- Core loads modules by scanning `modules/` directory, importing the package, calling lifecycle hooks
- No dynamic `importlib` magic needed — standard `__init__.py` with a known interface is sufficient

**Streaming Telegram responses:**
- `claude-agent-sdk` `query()` returns `AsyncIterator[Message]`
- Stream text deltas by editing the Telegram message in-place (aiogram `message.edit_text()` with rate-limit throttle)
- Buffer edits: update every ~500ms or on sentence boundary to stay under Telegram edit rate limits

**Dashboard auth for LXC:**
- Telegram Login Widget (OAuth-style) is the cleanest option — no password DB, user already has Telegram
- Falls back to static `DASHBOARD_TOKEN` env var for headless/API access

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| aiogram 3.27.0 | Python 3.10–3.13 | Do NOT use aiogram 2.x — breaking API, no longer maintained |
| claude-agent-sdk 0.1.58 | Python 3.10+ | Bundles Claude Code CLI internally — no separate CLI install needed on LXC |
| FastAPI 0.115.x | pydantic 2.x | FastAPI dropped pydantic v1 support in 0.100+. Pin pydantic>=2.0. |
| uvicorn 0.44.0 | FastAPI 0.115.x | Standard pairing, no known issues |
| HTMX 2.x | Any backend | CDN: `https://unpkg.com/htmx.org@2` — no version lock needed for internal tool |

## Sources

- [claude-agent-sdk PyPI](https://pypi.org/project/claude-agent-sdk/) — version 0.1.58, confirmed active (Apr 9, 2026 upload) — HIGH confidence
- [aiogram PyPI / docs](https://docs.aiogram.dev/) — version 3.27.0, released Apr 3, 2026 — HIGH confidence
- [FastAPI docs](https://fastapi.tiangolo.com/) + PyPI — version 0.115.x, confirmed Apr 2026 release — HIGH confidence
- [uvicorn PyPI](https://pypi.org/project/uvicorn/) — version 0.44.0 — HIGH confidence
- [FastAPI + HTMX pattern](https://testdriven.io/blog/fastapi-htmx/) — MEDIUM confidence (multiple corroborating sources, well-established pattern)
- Module manifest pattern — MEDIUM confidence (inferred from Odoo, VSCode, Ansible conventions; no single authoritative Python source for this specific folder+manifest pattern)

---
*Stack research for: Modular AI assistant platform (Telegram + Claude Code + web dashboard + plugin system)*
*Researched: 2026-04-13*
