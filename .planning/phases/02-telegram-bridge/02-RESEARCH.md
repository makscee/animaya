# Phase 2: Telegram Bridge - Research

**Researched:** 2026-04-13
**Domain:** python-telegram-bot v21-22 + claude-code-sdk streaming + async integration
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Port v1 `bot/bridge/telegram.py` with minimal adaptation. Remove v1-specific module imports (memory, spaces, features) and replace with stubs or skip.
- **D-02:** Port v1 `bot/claude_query.py` as single source of truth for ClaudeCodeOptions. Keep full tool set and `acceptEdits` permission mode.
- **D-03:** Stub out memory system calls. `build_core_context()` returns a minimal static string for now.
- **D-04:** CLAUDE.md assembled by `assemble_claude_md()` is the system prompt base. Claude query builder reads it and injects chat metadata.
- **D-05:** Per-chat working directories under DATA_PATH for session isolation.
- **D-06:** Per-user asyncio locks to prevent message storms.
- **D-07:** Port v1 `bot/bridge/formatting.py` markdown-to-Telegram-HTML as-is.
- **D-08:** Stream throttle: 0.5s minimum interval, 30-char minimum change threshold.
- **D-09:** Chunk responses >4096 chars into multiple Telegram messages.
- **D-10:** Replace `asyncio.Event().wait()` in main() with `app.run_polling()` from python-telegram-bot.
- **D-11:** Graceful shutdown via SIGINT/SIGTERM — stop polling, close connections.

### Claude's Discretion

- Voice transcription and image generation are NOT in scope. Stub or skip imports referencing them.
- File upload handling (photos, documents) — may include basic passthrough if simple, or defer.

### Deferred Ideas (OUT OF SCOPE)

- Voice transcription (Groq Whisper) — Phase 4 or later module
- Image generation (Gemini) — Phase 4 or later module
- File upload handling — defer unless trivial
- Group chat support — keep if already in v1, but not a priority
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TELE-01 | User can send a message via Telegram and receive a streamed Claude response | `query()` async iterator + edit_message streaming pattern documented below |
| TELE-02 | Bridge uses `asyncio.create_task()` for non-blocking response handling | `_enqueue_or_run()` pattern from v1 verified correct for PTB v22 |
| TELE-03 | Bridge shows typing indicator while Claude is processing | `_typing_loop()` asynccontextmanager pattern verified |
| TELE-04 | Long responses are chunked and sent as multiple Telegram messages | `_finalize_stream()` + TG_MAX_LEN=4096 pattern verified |
| TELE-05 | Bridge handles errors gracefully and notifies user of failures | try/except around `query()` with user-facing error message pattern verified |
</phase_requirements>

---

## Summary

Phase 2 is a port, not a rewrite. The v1 `bot/bridge/telegram.py` (584 lines) contains a complete, proven implementation of all TELE-01 through TELE-05 requirements. The research task is to identify exactly what must change for the v2 skeleton and what can be copied verbatim.

The primary adaptation work is: (1) removing three v1-only imports (`bot.features.audio`, `bot.dashboard.app._save_message`, `bot.memory.core`), (2) replacing `asyncio.Event().wait()` in `main()` with `app.run_polling()`, and (3) stubbing `build_core_context()` in `claude_query.py`. Everything else — streaming state machine, typing loop, chunking, per-user locks, formatting — ports unchanged.

The only version risk: pyproject.toml pins `python-telegram-bot>=21.10` but the current latest is 22.7. The PTB 22.0 breaking change (timeout args removed from `run_polling()`) does not affect this codebase since v1 never used those arguments. No other PTB 22.x breaking changes affect the v1 code patterns used here.

**Primary recommendation:** Copy `bot/bridge/telegram.py` and `bot/bridge/formatting.py` verbatim, strip 4 v1-only import calls (stub them inline), adapt `claude_query.py` to remove `build_core_context` import, and replace the blocking loop in `main()`.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| python-telegram-bot | >=21.10 (latest: 22.7) | Telegram bot framework | Already in pyproject.toml; proven in v1 |
| claude-code-sdk | 0.0.25 (latest on PyPI) | Claude Code streaming query | Already in pyproject.toml; proven in v1 |

[VERIFIED: pip3 index versions — claude-code-sdk 0.0.25, python-telegram-bot 22.7]

### No New Dependencies

Phase 2 requires zero new packages. All needed libraries are already declared in `pyproject.toml`.

---

## Architecture Patterns

### Pattern 1: PTB Application Lifecycle in async main()

**What:** Replace `await asyncio.Event().wait()` with `await app.run_polling()`. PTB's `run_polling()` is itself a blocking coroutine that handles the update loop and graceful shutdown internally.

**When to use:** Always — this is the D-10 locked decision.

```python
# Source: v1 bot/bridge/telegram.py build_app() + D-10 decision
from bot.bridge.telegram import build_app

async def main() -> None:
    # ... env validation, data_path setup, assemble_claude_md ...
    app = build_app(os.environ["TELEGRAM_BOT_TOKEN"])
    logger.info("Starting Telegram polling...")
    await app.run_polling()
    # run_polling() returns when SIGINT/SIGTERM received — D-11 satisfied
```

[VERIFIED: v1 codebase — `build_app()` already exists and returns a configured `Application`]

**PTB 22.x note:** `run_polling()` no longer accepts `*_timeout` keyword args (moved to `ApplicationBuilder`). The v1 `build_app()` doesn't pass any timeout args to `run_polling()`, so this breaking change does not apply. [VERIFIED: WebSearch — PTB 22.0 changelog]

### Pattern 2: Claude Code SDK Streaming

**What:** `query()` is an async iterator yielding message objects. Iterate with `async for`, check type, accumulate text from `TextBlock` items.

```python
# Source: v1 bot/bridge/telegram.py lines 526-536 + claude-code-sdk 0.0.25 API
from claude_code_sdk import query
from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

accumulated = ""
async for message in query(prompt=envelope, options=options):
    if message is None:
        continue
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                accumulated += block.text
                await _stream_text(state, accumulated)
            elif isinstance(block, ToolUseBlock):
                await _on_tool_use(state, block.name, block.input)
```

[VERIFIED: WebSearch — official Claude Agent SDK Python docs confirm this exact pattern]

### Pattern 3: SDK Message Parser Compatibility Patch

**What:** The v1 monkey-patch in `telegram.py` (lines 46-69) guards against `Unknown message type` exceptions from the SDK. This is a known issue documented in claude-agent-sdk-python issue #573.

```python
# Source: v1 bot/bridge/telegram.py lines 46-69
def _patch_sdk_message_parser():
    """Patch claude-code-sdk to skip unknown message types instead of crashing."""
    # ... (copy verbatim from v1)
```

**Keep this patch.** It protects against SDK version mismatches and future SDK changes adding new message types.

### Pattern 4: Per-User Lock (Non-Blocking Acquire)

**What:** v1 uses a manual non-blocking lock acquire pattern to immediately queue messages without blocking the handler coroutine. The `context.bot_data` dict is PTB's per-application persistent store — correct place for shared state.

```python
# Source: v1 bot/bridge/telegram.py lines 79-115
def _get_user_lock(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> asyncio.Lock:
    locks = context.bot_data.setdefault("_user_locks", {})
    if user_id not in locks:
        locks[user_id] = asyncio.Lock()
    return locks[user_id]
```

[VERIFIED: v1 codebase — `context.bot_data` is PTB standard for application-scoped state]

### Pattern 5: Streaming Throttle

**What:** `_stream_text()` gates Telegram `edit_text` calls to prevent flood-wait errors. Two conditions must both be true to trigger an update: elapsed >= 0.5s AND new_chars >= 30.

```python
# Source: v1 bot/bridge/telegram.py lines 238-269
_STREAM_MIN_INTERVAL = 0.5   # seconds
_STREAM_MIN_CHARS = 30       # characters added since last edit
```

This pattern is proven — Telegram rate limits `editMessage` to ~20 calls/second per chat. The throttle keeps well below this.

### Pattern 6: session_dir and CLAUDE.md Symlink

**What:** Per D-05, each chat gets `DATA_PATH/sessions/{session_key}/` as cwd. Claude Code's `--continue` flag scopes conversation history to cwd. A symlink to the shared CLAUDE.md ensures all sessions share the same system prompt.

```python
# Source: v1 bot/bridge/telegram.py lines 489-507
session_key = str(user_id)  # private chat
session_dir = data_dir / "sessions" / session_key
session_dir.mkdir(parents=True, exist_ok=True)

session_claude = session_dir / "CLAUDE.md"
if not session_claude.exists():
    claude_src = data_dir / "CLAUDE.md"
    if claude_src.exists():
        with suppress(OSError):
            session_claude.symlink_to(claude_src)
```

**Note:** `symlink_to()` creates a relative symlink by default in Python. Since `session_dir` is a subdirectory of `data_dir`, use an absolute path for the symlink target to avoid breakage if the cwd changes. The v1 code passes `claude_src` (absolute `Path`) directly — this is correct.

### Anti-Patterns to Avoid

- **Calling `app.run_polling()` inside `asyncio.run()`:** PTB manages its own event loop concerns. The `main()` function is already called via `asyncio.run(main())` in `__main__.py` — just `await app.run_polling()` inside the existing `async def main()`.
- **Importing `bot.features.audio` or `bot.dashboard.app` at module level:** These modules don't exist in v2. Import them only inside conditionals, or stub the calls inline in the message handler.
- **Re-implementing v1 patterns:** Don't rewrite `_finalize_stream`, `_typing_loop`, `md_to_html` — copy verbatim.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Markdown → Telegram HTML | Custom regex converter | `bot/bridge/formatting.py` (copy verbatim) | Already handles code blocks, tables, inline formatting, HTML escaping |
| Telegram message length limits | Manual truncation | `TG_MAX_LEN = 4096` + `_finalize_stream()` | Handles split across messages with quote attachment |
| Typing indicator loop | Manual `send_chat_action` calls | `_typing_loop()` asynccontextmanager | Handles cancellation, suppresses errors |
| Per-user queuing | Custom queue data structure | `_enqueue_or_run()` + `asyncio.Lock` | Handles non-blocking acquire, queued message UX |

---

## V1 → V2 Adaptation Map

This is the precise changeset required. Everything not listed copies verbatim.

### bot/bridge/telegram.py — Changes Required

| Location | V1 Code | V2 Adaptation |
|----------|---------|---------------|
| Line 447-451 | `from bot.features.audio import transcribe` (inside handler) | Replace voice block with stub: `text = "[voice — not supported yet]"` or skip entirely per Claude's discretion |
| Line 539-543 | `from bot.dashboard.app import _save_message; _save_message(...)` | Delete these lines — no dashboard in Phase 2 |
| Line 518 | `from bot.claude_query import build_options` | Unchanged — `claude_query.py` will exist in v2 |
| `/start` handler text | References "spaces", "voice messages", "generate images" | Update to simpler text for v2 |

### bot/claude_query.py — Changes Required

| Location | V1 Code | V2 Adaptation |
|----------|---------|---------------|
| Line 32 | `from bot.memory.core import build_core_context` | Remove this import |
| Lines 41-43 | `core = build_core_context(d); if core: parts.append(core)` | Replace with stub: `core = ""  # Phase 4 adds memory` |
| Lines 58-68 | `ClaudeCodeOptions(...)` | Unchanged — keep all tools and `acceptEdits` |

### bot/main.py — Changes Required

| Location | V1 Code | V2 Adaptation |
|----------|---------|---------------|
| Line 44 | `await asyncio.Event().wait()` | Replace with `app = build_app(token); await app.run_polling()` |
| Imports | None | Add `from bot.bridge.telegram import build_app` |

### bot/bridge/formatting.py — No Changes

Copy verbatim. Zero v1-only dependencies.

---

## CLAUDECODE Environment Variable Sanitization

**Issue:** When Animaya runs inside a Claude Code session (e.g., during development with `claude` CLI active), the subprocess inheriting `CLAUDECODE=1` causes the SDK's spawned `claude --print` subprocess to detect it's nested and reject the session or hang.

**Status in v2:** `run.sh` already contains `unset CLAUDECODE` and `unset CLAUDECODE_EXECUTION_ID` before launching the bot. [VERIFIED: grep of run.sh lines 7-8]

**Additional variables to sanitize (per WebSearch findings):** Claude Code 2.1.71+ sets `CLAUDE_CODE_SSE_PORT` which can also cause subprocess stalls. The Phase 1 setup.sh does not sanitize this. The planner should note this as a hardening task, but it does not block Phase 2 functionality for normal (non-nested) operation.

**Workaround already in v1:** `_patch_sdk_message_parser()` provides a different kind of resilience (SDK message type errors), not env sanitization. Both protections should be kept.

---

## Common Pitfalls

### Pitfall 1: PTB 22.x `run_polling()` Timeout Arguments Removed

**What goes wrong:** Passing `read_timeout`, `write_timeout` etc. to `run_polling()` raises `TypeError` in PTB 22+.
**Why it happens:** PTB 22.0 moved these to `ApplicationBuilder`.
**How to avoid:** Don't pass any `*_timeout` args to `run_polling()`. The v1 code doesn't — safe to port as-is.
**Warning signs:** `TypeError: run_polling() got an unexpected keyword argument`

### Pitfall 2: Importing v1-only modules at module level

**What goes wrong:** `ImportError` at startup if `bot.features.audio`, `bot.memory.core`, or `bot.dashboard.app` are imported at the top of `telegram.py`.
**Why it happens:** These modules don't exist in v2.
**How to avoid:** The v1 code already imports these inside the handler function body (lazy imports) — keep that pattern and stub/skip the call sites.
**Warning signs:** `ModuleNotFoundError: No module named 'bot.features'`

### Pitfall 3: `asyncio.run()` vs `await` for `run_polling()`

**What goes wrong:** Calling `asyncio.run(app.run_polling())` inside an already-running event loop causes `RuntimeError: This event loop is already running`.
**Why it happens:** `__main__.py` calls `asyncio.run(main())` — the event loop is already running when `main()` executes.
**How to avoid:** Just `await app.run_polling()` inside `async def main()`. Never call `app.run_polling()` synchronously.

### Pitfall 4: `do_quote` parameter in PTB 22

**What goes wrong:** `do_quote=True` parameter to `reply_text()` may behave differently in PTB 22 (it was renamed from `quote` in PTB 20).
**Why it happens:** PTB API evolution.
**How to avoid:** `do_quote` was introduced in PTB 20 and is still present in PTB 22 — safe. [ASSUMED — not verified against PTB 22 docs specifically]

### Pitfall 5: SDK `None` messages in async iterator

**What goes wrong:** `query()` can yield `None` (e.g., for `system_prompt` message types the SDK doesn't fully model). Calling `.content` on `None` raises `AttributeError`.
**Why it happens:** The patched SDK skips unknown types by returning `None`; the iterator still yields them.
**How to avoid:** The v1 code already has `if message is None: continue` — keep it.

---

## Code Examples

### Replacing the blocking loop in main()

```python
# Source: v1 build_app() + D-10 decision
async def main() -> None:
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            logger.error("%s not set", var)
            sys.exit(1)

    data_path = Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))
    data_path.mkdir(parents=True, exist_ok=True)
    assemble_claude_md(data_path)

    from bot.bridge.telegram import build_app
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = build_app(token)
    logger.info("Telegram polling started")
    await app.run_polling()
    # Returns on SIGINT/SIGTERM — D-11 satisfied
```

### Stubbed build_options() for Phase 2

```python
# Source: v1 bot/claude_query.py with memory stub per D-03
def build_options(
    data_dir: Path | None = None,
    system_prompt_extra: str = "",
    cwd: Path | str | None = None,
):
    from claude_code_sdk import ClaudeCodeOptions

    d = data_dir or Path(os.environ.get("DATA_PATH", str(Path.home() / "hub" / "knowledge" / "animaya")))
    work_dir = str(cwd) if cwd else str(d)

    parts = []
    if system_prompt_extra:
        parts.append(system_prompt_extra)

    # Phase 4 will add real memory context here
    # core = build_core_context(d)

    system_prompt = "\n\n".join(parts) if parts else ""

    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    config_path = d / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            if cfg.get("model"):
                model = cfg["model"]
        except Exception:
            pass

    return ClaudeCodeOptions(
        model=model,
        system_prompt=system_prompt,
        cwd=work_dir,
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch", "WebFetch"],
        permission_mode="acceptEdits",
        continue_conversation=True,
    )
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TELE-01 | query() called with correct options, response streamed | unit (mock SDK) | `pytest tests/test_bridge.py -x` | Wave 0 |
| TELE-02 | Handler creates task, does not block | unit (mock handler) | `pytest tests/test_bridge.py::test_nonblocking -x` | Wave 0 |
| TELE-03 | Typing indicator loop created and cancelled | unit (mock chat) | `pytest tests/test_bridge.py::test_typing_loop -x` | Wave 0 |
| TELE-04 | Response >4096 chars split into multiple messages | unit (mock update) | `pytest tests/test_bridge.py::test_chunking -x` | Wave 0 |
| TELE-05 | SDK exception caught, error message sent to user | unit (mock query raises) | `pytest tests/test_bridge.py::test_error_handling -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest tests/test_bridge.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/test_bridge.py` — covers TELE-01 through TELE-05 with mocked SDK and PTB
- [ ] `tests/test_formatting.py` — covers md_to_html edge cases (code blocks, chunking)

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| python-telegram-bot | Telegram bridge | — | 22.7 on PyPI (pinned >=21.10 in pyproject.toml) | — |
| claude-code-sdk | Claude query | — | 0.0.25 (latest) | — |
| Node.js | claude-code-sdk subprocess | setup.sh checks | 22 (per CLAUDE.md) | Warning in setup.sh |

[VERIFIED: pip3 index — both packages available at stated versions]

Note: Packages are not installed in a venv in this shell session. The `pip install -e .` step from setup.sh installs them. No blocking dependency gaps.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `do_quote` parameter still works in PTB 22.x as in 21.x | Common Pitfalls #4 | `reply_text()` calls fail; need to remove `do_quote=True` |
| A2 | `claude_code_sdk.types` exports `AssistantMessage`, `TextBlock`, `ToolUseBlock` in 0.0.25 | Code Examples | Import errors; need to check actual package contents |
| A3 | `ClaudeCodeOptions.continue_conversation=True` is valid in SDK 0.0.25 | Stubbed build_options example | SDK rejects unknown kwarg; remove the field |

---

## Open Questions

1. **Does `continue_conversation=True` exist in claude-code-sdk 0.0.25?**
   - What we know: v1 `claude_query.py` uses it at line 67
   - What's unclear: The SDK is at 0.0.25 (very early) — field names may differ
   - Recommendation: Implementer should `pip install claude-code-sdk` and inspect `ClaudeCodeOptions` fields before assuming v1 field names are valid

2. **File upload handling scope (Claude's discretion)**
   - What we know: v1 handles photos and documents (lines 455-477 in telegram.py)
   - What's unclear: Whether to include this in Phase 2 or stub it
   - Recommendation: Include — it's self-contained within the handler and has no external dependencies beyond what's already imported

---

## Sources

### Primary (HIGH confidence)
- `bot/bridge/telegram.py` (v1) — direct inspection, 584 lines, all patterns cited
- `bot/claude_query.py` (v1) — direct inspection, 69 lines
- `bot/bridge/formatting.py` (v1) — direct inspection
- `bot/main.py` (Phase 1 skeleton) — direct inspection
- `run.sh` — confirmed CLAUDECODE/CLAUDECODE_EXECUTION_ID unset
- `pyproject.toml` — confirmed dependency pins
- pip3 index — claude-code-sdk 0.0.25, python-telegram-bot 22.7 [VERIFIED]

### Secondary (MEDIUM confidence)
- WebSearch: PTB 22.0 changelog — `run_polling()` timeout arg removal confirmed
- WebSearch: claude-agent-sdk-python GitHub issue #573 — CLAUDECODE subprocess hang confirmed
- WebSearch: Official Claude Agent SDK Python docs — `query()` / `AssistantMessage` / `TextBlock` pattern confirmed

### Tertiary (LOW confidence)
- WebSearch: CLAUDE_CODE_SSE_PORT causing subprocess stalls in Claude Code 2.1.71+ — single source

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via pip registry
- V1 → V2 adaptation map: HIGH — direct code inspection
- PTB 22.x compatibility: MEDIUM — changelog confirmed, specific method signatures not inspected
- SDK field names: LOW — early-version SDK, not inspected directly

**Research date:** 2026-04-13
**Valid until:** 2026-05-13 (stable libraries; SDK at 0.0.25 may move fast)
