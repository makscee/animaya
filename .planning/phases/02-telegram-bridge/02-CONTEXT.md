# Phase 2: Telegram Bridge - Context

**Gathered:** 2026-04-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Integrate the Telegram bridge into the Phase 1 skeleton so users can send messages via Telegram and receive streamed Claude Code responses. This phase delivers TELE-01 through TELE-05: streaming responses, async non-blocking handling, typing indicators, response chunking, and error handling.

No memory system, no modules, no dashboard — just the Telegram ↔ Claude Code pipeline.

</domain>

<decisions>
## Implementation Decisions

### V1 Code Reuse
- **D-01:** Port v1 `bot/bridge/telegram.py` with minimal adaptation rather than rewriting. The existing code is proven with streaming throttle, per-user locks, typing indicators, and chunking. Remove v1-specific module imports (memory, spaces, features) and replace with stubs or skip.
- **D-02:** Port v1 `bot/claude_query.py` as the single source of truth for ClaudeCodeOptions. Keep the full tool set (Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch) and permission mode (acceptEdits).

### Memory & Context
- **D-03:** Stub out memory system calls. `build_core_context()` should return a minimal static string for now. Phase 4 adds the real memory system.
- **D-04:** CLAUDE.md assembled by `assemble_claude_md()` from Phase 1 is the system prompt base. Claude query builder reads it and injects chat metadata.

### Session Management
- **D-05:** Use per-chat working directories under DATA_PATH for session isolation (matches v1 pattern). Each chat gets its own dir with a symlinked CLAUDE.md.
- **D-06:** Per-user asyncio locks to prevent message storms — queue overlapping requests from the same user.

### Formatting & Delivery
- **D-07:** Use v1 markdown-to-Telegram-HTML formatting from `bot/bridge/formatting.py`. Port as-is.
- **D-08:** Stream throttle: 0.5s minimum interval, 30-char minimum change threshold before updating message.
- **D-09:** Chunk responses >4096 chars into multiple Telegram messages.

### Integration with main.py
- **D-10:** Replace `asyncio.Event().wait()` blocking loop with `app.run_polling()` from python-telegram-bot. This is the only change to the Phase 1 skeleton's blocking behavior.
- **D-11:** Graceful shutdown via SIGINT/SIGTERM — stop polling, close connections.

### Claude's Discretion
- Voice transcription and image generation features are NOT in Phase 2 scope. If v1 code references them, stub the imports or skip.
- File upload handling (photos, documents) — Claude may include basic passthrough if it's simple, or defer to a later phase.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing V1 Code (primary source)
- `bot/bridge/telegram.py` — Full v1 Telegram handler with streaming, locks, chunking
- `bot/bridge/formatting.py` — Markdown to Telegram HTML converter
- `bot/claude_query.py` — ClaudeCodeOptions builder (model, tools, permissions)

### Phase 1 Foundation
- `bot/main.py` — Phase 1 skeleton (env validation, data dir, CLAUDE.md, blocking loop)
- `bot/__main__.py` — Entry point calling asyncio.run(main())
- `.planning/phases/01-install-foundation/01-CONTEXT.md` — Phase 1 decisions

### Project Architecture
- `.planning/PROJECT.md` — Core value, constraints, module architecture
- `.planning/REQUIREMENTS.md` — TELE-01 through TELE-05 acceptance criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `bot/bridge/telegram.py` — Complete Telegram handler (584 lines) with streaming, typing, locks, chunking
- `bot/bridge/formatting.py` — Markdown to Telegram HTML conversion
- `bot/claude_query.py` — Claude Code SDK options builder (69 lines)
- `bot/bridge/__init__.py` — Bridge package init

### Established Patterns
- Per-module logging: `logger = logging.getLogger(__name__)`
- Async handlers with `asyncio.create_task()` for non-blocking work
- Streaming throttle with min interval + min chars
- Per-user lock dict: `_user_locks: dict[int, asyncio.Lock]`
- Error handling: try/except with user-facing error message

### Integration Points
- `bot/main.py:main()` — Replace `asyncio.Event().wait()` with telegram app polling
- `bot/main.py` — Add imports for bridge module
- `bot/claude_query.py` — Needs adaptation: remove memory.core import, simplify system prompt

</code_context>

<specifics>
## Specific Ideas

No specific requirements — the v1 code provides the implementation reference. Adapt it to work with the Phase 1 skeleton without v1-only dependencies (memory, spaces, features modules).

</specifics>

<deferred>
## Deferred Ideas

- Voice transcription (Groq Whisper) — Phase 4 or later module
- Image generation (Gemini) — Phase 4 or later module
- File upload handling — defer unless trivial to include
- Group chat support — keep if already in v1 code, but not a Phase 2 priority

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-telegram-bridge*
*Context gathered: 2026-04-13*
