---
plan_id: 260416-mme-01
name: reset accumulated buffer after tool uses so post-tool text is not duplicated
mode: quick
completed: 2026-04-16
commit: 22dd767
duration_minutes: 15
---

# Quick Task 260416-mme Summary

**One-liner:** Two-buffer fix (`accumulated` + `full_response`) in `_run_claude_and_stream` prevents pre-tool text from leaking into post-tool Telegram bubbles.

## What Was Done

- **`bot/bridge/telegram.py`** — Introduced `full_response = ""` alongside the existing `accumulated = ""`. On each `TextBlock` both buffers grow; after each `ToolUseBlock` only `accumulated` is reset. The final guard now checks `full_response.strip()` (not `accumulated`), with two sub-branches: non-empty `accumulated` → `_finalize_stream`; empty `accumulated` (trailing-tool edge case) → `_delete_status` on the dangling indicator bubble. `full_response` (not `accumulated`) is now passed to `_send_referenced_files` and the memory consolidation `conversation_text`. Return value is `full_response`.

- **`tests/test_telegram_bridge.py`** — Added `TestStreamBufferReset` with two tests:
  - `test_mixed_stream_no_duplication`: Text → ToolUse → Text stream; asserts final edit_text contains only "B", not "AB".
  - `test_trailing_tool_deletes_status_returns_full`: Text → ToolUse stream; asserts tool-indicator bubble is deleted and return value is "A".

## Deviations from Plan

None — plan executed exactly as written. Minor adaptations required by test harness reality:
- `AssistantMessage` requires `model` positional arg (added `model="test"`).
- `update.message.reply_text` must be `AsyncMock` (not plain `MagicMock`) because `_send_status` awaits it.
- Tool-indicator bubble created via `update.message.reply_text` (not `chat.send_message`), so delete assertion targets `reply_text.return_value.delete`.

## Files Modified

- `bot/bridge/telegram.py` — core fix (~10 lines changed in stream loop + final guard)
- `tests/test_telegram_bridge.py` — 2 new test cases + helper methods + `model="test"` fix on existing fake

## Verification

- `uvx ruff check bot/bridge/telegram.py tests/test_telegram_bridge.py` — clean
- `.venv/bin/pytest tests/test_telegram_bridge.py -v` — 10/10 passed
