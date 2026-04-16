---
plan_id: 260416-mme-01
name: reset accumulated buffer after tool uses so post-tool text is not duplicated
mode: quick
---

# Plan

## Bug

`bot/bridge/telegram.py::_run_claude_and_stream` (around lines 548-564) uses a
single monotonic `accumulated` string across the whole Claude turn. When the
SDK emits `Text → ToolUse → ToolUse → Text`, `_on_tool_use` correctly freezes
the prior text's status_msg and creates a new one, but `accumulated` still
holds the prior text. The next `TextBlock` appends and `_stream_text` renders
the cumulative string into the new status_msg → user sees the first text
DUPLICATED inside the second bubble before the new text.

## Fix

Two buffers:

- `accumulated` — current display buffer for the CURRENT status_msg. Reset to
  `""` after every `ToolUseBlock`.
- `full_response` — all text across the whole turn. Used by
  `_finalize_stream`, `_send_referenced_files`, memory consolidation.

Edge cases:

- If the stream ends with trailing tool uses and no post-tool text,
  `accumulated` is `""` but `full_response` may be non-empty. Currently the
  code checks `if accumulated.strip()`. Switch to `if full_response.strip()`.
  When `full_response` is non-empty but `accumulated` is empty, the last
  status_msg is a tool-indicator bubble that no longer serves a purpose →
  delete it via `_delete_status(stream_state["status_msg"])` instead of
  editing it.
- When `accumulated` is non-empty at end, call `_finalize_stream` with
  `accumulated` (edits the last status_msg to show the last chunk cleanly).
  Downstream consumers (refs, memory) always receive `full_response`.

## Tasks

### Task 1 — fix stream accumulator

- In `_run_claude_and_stream`:
  - Introduce `full_response = ""` alongside `accumulated = ""`.
  - On `TextBlock`: `accumulated += block.text; full_response += block.text`.
  - After `_on_tool_use(...)`: `accumulated = ""`.
  - Replace the `if accumulated.strip():` guard with `if full_response.strip():`.
  - Inside that guard:
    - If `accumulated.strip()`: call `_finalize_stream(stream_state, accumulated, update, chat=chat)`.
    - Else (`full_response` non-empty but `accumulated` empty): call
      `await _delete_status(stream_state["status_msg"])` — pre-tool text
      bubbles stay visible; the dangling tool-indicator is cleaned up.
  - Pass `full_response` to `_send_referenced_files` (was `accumulated`).
  - Pass `full_response` into `f"ASSISTANT: {full_response}"` for memory
    consolidation (was `accumulated`).
  - `return full_response` for callers that want the reply text (greeter).
  - `else` branch (empty `full_response`): keep existing
    `_delete_status(...)` + `return None`.

### Task 2 — tests

- `tests/test_telegram_bridge.py` (or wherever _run_claude_and_stream is
  tested — find first): add a test simulating a mixed stream (Text → Tool →
  Text). Assert second bubble contains ONLY the post-tool text, not the
  concatenation. Use existing mock patterns (fake `query` yielding
  `AssistantMessage`s).
- Add second test: trailing-tool-only stream (Text → Tool). Assert final
  status_msg was deleted, pre-tool text bubble remained, `full_response`
  returned is the pre-tool text.

## Deliverables

- Commit 1: `fix(quick-260416-mme): reset stream buffer after tool uses to avoid duplicated text`
  - Files: `bot/bridge/telegram.py`, `tests/test_telegram_bridge.py`
- ruff clean, affected pytest suites green.
