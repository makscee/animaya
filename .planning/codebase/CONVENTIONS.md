# Coding Conventions

**Analysis Date:** 2026-04-13

## Naming Patterns

**Files:**
- Lowercase with underscores: `telegram.py`, `image_gen.py`, `git_versioning.py`
- Module files follow single responsibility: `audio.py`, `search.py`, `core.py`
- Dunder files: `__init__.py`, `__main__.py`

**Functions:**
- snake_case: `build_options()`, `transcribe()`, `build_core_context()`, `chunk_markdown()`
- Private functions prefixed with single underscore: `_get_user_lock()`, `_patch_sdk_message_parser()`, `_send_status()`
- Async functions use `async def`: `transcribe()`, `_send_status()`

**Variables:**
- snake_case for all local variables and module globals: `audio_bytes`, `filename`, `user_id`
- Constants in UPPER_SNAKE_CASE: `TG_MAX_LEN`, `STT_BASE_URL`, `STT_MODEL`, `_STREAM_MIN_INTERVAL`
- Private module-level stats dict: `_stats = {...}`

**Types:**
- Use `Path` for filesystem paths: `data_dir: Path`, `config_path: Path`
- Use `dict`, `list`, `str | None` union types (Python 3.12 syntax)
- Type hints on all function parameters and returns

## Code Style

**Formatting:**
- Ruff formatter enforced
- Line length: 100 characters (set in `pyproject.toml`)
- Target Python: 3.12+

**Linting:**
- Ruff with rules: E (errors), F (pyflakes), I (isort), W (warnings)
- Config: `[tool.ruff]` in `pyproject.toml`
- Automatic import sorting by Ruff

**Comments:**
- Use `# ──` separator for major sections: `# ── SDK compatibility patch ─────────────────────────────────────────`
- Docstrings for all public functions and modules
- Triple-quoted docstrings with Args, Returns sections

## Import Organization

**Order:**
1. Future annotations: `from __future__ import annotations`
2. Standard library: `import asyncio`, `import logging`, `import os`
3. Third-party: `import httpx`, `from telegram import Update`
4. Local: `from bot.bridge.formatting import TG_MAX_LEN`

**Path Aliases:**
- No aliases used; always use full `bot.module.submodule` paths
- Relative imports never used
- Module namespace: `bot` (e.g., `from bot.memory.core import build_core_context`)

**Docstring Examples:**

From `bot/claude_query.py`:
```python
def build_options(
    data_dir: Path | None = None,
    system_prompt_extra: str = "",
    cwd: Path | str | None = None,
):
    """Build ClaudeCodeOptions with standard configuration.

    Args:
        data_dir: Bot data directory (default: DATA_PATH env var).
        system_prompt_extra: Additional context to prepend (e.g., chat type, user info).
        cwd: Working directory for Claude (default: data_dir).

    Returns:
        ClaudeCodeOptions ready for query().
    """
```

## Error Handling

**Patterns:**
- Try-except with specific exception logging: `logger.exception("Message")` captures full traceback
- Graceful degradation: return `None` on failure (e.g., `transcribe()` returns `str | None`)
- Log errors at appropriate level: `logger.error()` for recoverable errors, `logger.exception()` for unexpected failures
- Silent catch with `suppress()` for expected failures in async contexts:

```python
from contextlib import suppress

async def _update_status(msg, text: str) -> None:
    with suppress(Exception):
        await msg.edit_text(text, parse_mode=parse_mode)
```

**Error response pattern:**
- Return error strings from utility functions: `"Error: GOOGLE_API_KEY not set"`
- Let exceptions propagate in critical paths (Claude SDK initialization, startup)
- Use `sys.exit(1)` for startup validation failures

Examples from `bot/features/audio.py`:
```python
async def transcribe(audio_bytes: bytes, filename: str = "audio.ogg") -> str | None:
    if not STT_API_KEY:
        logger.warning("STT_API_KEY not set, skipping voice transcription")
        return None
    try:
        # ... API call
    except Exception:
        logger.exception("Voice transcription failed")
        return None
```

## Logging

**Framework:** Python `logging` module

**Patterns:**
- Logger per module: `logger = logging.getLogger(__name__)`
- Configured in entry point `bot/main.py`:

```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
```

**When to log:**
- INFO: Lifecycle events (startup, shutdown, config loaded), operation counts
- WARNING: Configuration issues, missing optional dependencies
- ERROR: Recoverable failures (API timeouts, retries)
- DEBUG: Detailed tracing of SDK compatibility patches
- EXCEPTION: Use `logger.exception()` to capture full traceback

Examples:
```python
logger.info("Transcribed %d bytes -> %d chars", len(audio_bytes), len(text))
logger.warning("Could not patch SDK message parser", exc_info=True)
logger.exception("Error processing queued message for user %d", user_id)
```

## Function Design

**Size:** Keep functions under 30 lines unless linear procedural flow

**Parameters:**
- Use typed parameters with sensible defaults
- Async parameters when calling async operations: `async def transcribe(...)`
- Context managers for resource cleanup: `@asynccontextmanager async def _typing_loop(chat):`

**Return Values:**
- Explicit return types on all functions
- Return `None` for fire-and-forget operations
- Return union types for success/failure: `str | None` means success returns str, failure returns None

## Module Design

**Exports:**
- Define public API at module level
- Private functions start with `_`
- All modules have module docstring

**Barrel Files:**
- `bot/*/___init__.py` are empty (no re-exports)

**Structure Example (bot/memory/core.py):**
```python
"""Tier 1: Core memory — always injected into system prompt (~500 tokens).

[Module purpose]
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Public functions
def build_core_context(data_dir: Path) -> str:
    ...

def build_consolidation_prompt() -> str:
    ...
```

## Configuration

**Environment Variables:**
- Read at module level for static config: `STT_API_KEY = os.environ.get("STT_API_KEY", "")`
- Read in functions for runtime config: `model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")`
- Provide sensible defaults
- Validate required variables at startup (in `bot/main.py`)

**File Paths:**
- Use `Path` objects, never string concatenation
- Default to `/data` via env var: `Path(os.environ.get("DATA_PATH", "/data"))`

---

*Convention analysis: 2026-04-13*
