---
phase: 02-telegram-bridge
plan: 01
subsystem: bridge
tags: [telegram, claude-sdk, streaming, formatting, tdd]
dependency_graph:
  requires: [01-01]
  provides: [bot.bridge.telegram, bot.bridge.formatting, bot.claude_query]
  affects: [bot.main]
tech_stack:
  added: []
  patterns: [per-user-asyncio-locks, streaming-throttle, tdd-red-green]
key_files:
  created:
    - tests/test_formatting.py
    - tests/test_bridge.py
  modified:
    - bot/bridge/telegram.py
    - bot/claude_query.py
decisions:
  - "Port v1 code verbatim rather than rewrite — preserves proven streaming/lock logic"
  - "TextBlock API fix: constructor takes only text= (no type= arg) in installed SDK"
  - "AssistantMessage API fix: requires model= argument in installed SDK"
metrics:
  duration: ~10min
  completed: 2026-04-13T20:21:00Z
  tasks_completed: 2
  files_changed: 4
---

# Phase 2 Plan 01: Telegram Bridge Port Summary

**One-liner:** Ported v1 Telegram bridge to v2 by removing three v1-only imports (bot.memory.core, bot.features.audio, bot.dashboard.app) and adding 37 TDD tests covering TELE-01 through TELE-05.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write tests for formatting and bridge (RED) | b2a29e2 | tests/test_formatting.py, tests/test_bridge.py |
| 2 | Port v1 modules to v2 — adapt telegram.py, claude_query.py (GREEN) | 0bd8d1e | bot/bridge/telegram.py, bot/claude_query.py |

## Verification

All success criteria met:
- 37/37 tests pass (`pytest tests/test_formatting.py tests/test_bridge.py`)
- Zero v1-only imports in telegram.py and claude_query.py
- `from bot.bridge.telegram import build_app` succeeds
- `from bot.claude_query import build_options` succeeds
- formatting.py unchanged from v1 (zero diff)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed TextBlock API mismatch in test**
- **Found during:** Task 1 verification (RED run)
- **Issue:** Test used `TextBlock(type="text", text="Hello world")` but installed `claude-code-sdk` `TextBlock.__init__` takes only `text: str`
- **Fix:** Removed `type=` kwarg from TextBlock constructor call
- **Files modified:** tests/test_bridge.py
- **Commit:** b2a29e2

**2. [Rule 1 - Bug] Fixed AssistantMessage API mismatch in test**
- **Found during:** Task 1 verification (RED run)
- **Issue:** Test used `AssistantMessage(content=[...])` but constructor requires `model: str` positional arg
- **Fix:** Added `model="claude-test"` argument
- **Files modified:** tests/test_bridge.py
- **Commit:** b2a29e2

## Known Stubs

| File | Stub | Reason |
|------|------|--------|
| bot/bridge/telegram.py:444 | `text = "[Voice messages not yet supported]"` | Voice transcription deferred to Phase 4 (Groq Whisper module) |
| bot/claude_query.py:41 | `# Phase 4 adds memory context here` | Memory system deferred to Phase 4 |

## Threat Surface Scan

No new security surface introduced beyond the plan's threat model. The three removed imports (memory, audio, dashboard) reduced the attack surface vs v1.

T-02-02 (prompt injection via envelope): mitigated as designed — envelope format makes user text boundaries clear, Claude Code safety filters handle injection.
T-02-04 (DoS via message storms): mitigated — per-user asyncio locks ported verbatim from v1.
T-02-05 (privilege escalation): mitigated — permission_mode="acceptEdits" retained in build_options.
T-02-06 (Telegram rate limits): mitigated — streaming throttle constants (0.5s/30char) unchanged.

## Self-Check: PASSED

- tests/test_formatting.py: FOUND
- tests/test_bridge.py: FOUND
- bot/bridge/telegram.py: FOUND (modified)
- bot/claude_query.py: FOUND (modified)
- Commit b2a29e2: FOUND
- Commit 0bd8d1e: FOUND
