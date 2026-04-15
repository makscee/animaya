---
phase: 04-first-party-modules
plan: 3
subsystem: memory-module
tags: [memory, consolidation, haiku, telegram-bridge, modules]
dependency_graph:
  requires: [04-01, 04-02]
  provides: [memory-lifecycle, consolidation-runtime, bridge-trigger]
  affects: [bot/bridge/telegram.py, bot/modules_runtime/memory.py]
tech_stack:
  added: [claude-haiku-4-5 consolidation query]
  patterns: [fire-and-forget asyncio.create_task, continue_conversation=False, idempotent shell install]
key_files:
  created:
    - modules/memory/manifest.json
    - modules/memory/install.sh
    - modules/memory/uninstall.sh
    - modules/memory/prompt.md
    - modules/memory/README.md
    - bot/modules_runtime/memory.py
  modified:
    - bot/bridge/telegram.py
    - tests/modules/test_memory.py
decisions:
  - CONSOLIDATION_MODEL = "claude-haiku-4-5" (locked A1 — hard-coded constant, overridable via registry config)
  - continue_conversation=False in consolidation query to prevent context explosion across calls (T-04-03-03)
  - Fire-and-forget via asyncio.create_task after _send_referenced_files (not during stream)
  - Gated on _registry_get_entry(data_dir, "memory") so bridge is safe when module uninstalled
  - MODS-06 invariant preserved: memory.py imports nothing from identity or git_versioning
metrics:
  duration: ~15 minutes
  completed: 2026-04-15
  tasks_completed: 3
  tasks_total: 4
  files_created: 7
  files_modified: 2
---

# Phase 4 Plan 3: Memory Module Summary

Ships the memory module: lifecycle scripts, Haiku consolidation runner, and post-reply bridge trigger that maintains `CORE.md` as a rolling ≤150-line summary.

## What Was Built

### modules/memory/ package

- **manifest.json** — Phase 3 manifest with `depends: ["identity"]` (locked A7). Config schema: `consolidation_model` (default `claude-haiku-4-5`), `core_max_lines` (default 150), `consolidation_every_n_turns` (default 10).
- **install.sh** — Creates `~/hub/knowledge/memory/CORE.md` + `README.md`. Idempotent: skips if files exist so existing consolidated content is preserved.
- **uninstall.sh** — `rm -rf` the memory dir entirely. Zero artifact leakage.
- **prompt.md** — Static module prompt injected by assembler. Tells Claude not to edit CORE.md directly; use Write/Edit for topical files only.
- **README.md** — Module documentation with config table and runtime description.

### bot/modules_runtime/memory.py

- `CONSOLIDATION_MODEL = "claude-haiku-4-5"` — locked assumption A1.
- `consolidate_memory()` — Async function running a standalone SDK query with `continue_conversation=False`. cwd set to `hub_knowledge` dir so Haiku can read/write memory files via built-in tools.
- `maybe_trigger_consolidation()` — Increments `chat_data["turn_count"]`; fires `asyncio.create_task(consolidate_memory(...))` every Nth turn. Returns `True` if scheduled, `False` otherwise. Gracefully handles no-event-loop case.
- MODS-06 compliant: zero imports from `bot.modules_runtime.identity` or `bot.modules_runtime.git_versioning`.

### bot/bridge/telegram.py

Added two imports at module level:
```python
from bot.modules.registry import get_entry as _registry_get_entry
from bot.modules_runtime.memory import maybe_trigger_consolidation
```

Post-reply trigger wired immediately after `await _send_referenced_files(accumulated, update)`:
- Calls `_registry_get_entry(data_dir, "memory")` — no-op if memory not installed.
- Reads `consolidation_every_n_turns`, `consolidation_model`, `core_max_lines` from registry config with safe defaults.
- Calls `maybe_trigger_consolidation(chat_data=context.chat_data, ...)` — fire-and-forget.

## Test Results

All 4 MEMO tests green (`tests/modules/test_memory.py`):
- **MEMO-01** (TestMemoryInstall): install.sh creates CORE.md + README.md with correct heading.
- **MEMO-01** (TestMemoryPersist): direct write to memory/facts.md persists and is path-safe.
- **MEMO-02** (TestMemoryGitCommit): real `commit_if_changed` call against tmp git repo — confirms memory files committed within one tick. No mock.
- **MEMO-03/04** (TestConsolidation): monkeypatched `claude_code_sdk.query` captures `model == "claude-haiku-4-5"`, `continue_conversation is False`, correct cwd.

Full suite: 43/43 passed, 0 xfail, ruff clean.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| `continue_conversation=False` | Prevents Haiku consolidation from polluting the main chat session (T-04-03-03) |
| fire-and-forget after `_send_referenced_files` | User gets response immediately; consolidation runs in background |
| `_registry_get_entry` gate | Bridge stays safe when memory module is uninstalled |
| `owned_paths: []` | Memory dir is sibling of ANIMAYA_HUB_DIR; cleanup via uninstall.sh (same pattern as identity) |
| CORE.md injection already handled | `_read_for_injection` in `claude_query.py` (plan 04-01) handles `<memory-core>` XML block |

## Tiered Memory Structure (D-07 resolved)

- `~/hub/knowledge/memory/CORE.md` — always-injected rolling summary, ≤150 lines (maintained by Haiku)
- `~/hub/knowledge/memory/{topic}.md` — topical files written by Claude on demand via Write tool

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all test stubs replaced with real assertions.

## Threat Surface

No new surfaces beyond plan's threat model (T-04-03-01 through T-04-03-06 all addressed in implementation).

## Manual Checkpoint (Task 4)

Task 4 is a `checkpoint:human-verify` gate requiring end-to-end smoke test of all three modules installed together. Awaiting user verification.

## Phase 4 Must-Haves Status

| # | Requirement | Status |
|---|-------------|--------|
| 1 | User completes onboarding → identity in next-message system prompt | Done (04-01) |
| 2 | Memory fact persists in Hub knowledge/memory/ + appears in next session | Done (this plan) |
| 3 | Memory + identity files git-committed on configured interval | Done (04-02 + MEMO-02 test) |
| 4 | User reconfigures identity via `/identity` without reinstalling | Done (04-01) |

## Self-Check

Commits verified:
- `37a5696` — feat(04-03): add memory module lifecycle package
- `0d06697` — feat(04-03): add memory.py consolidation runtime + MEMO tests green
- `c9484b1` — feat(04-03): wire maybe_trigger_consolidation into telegram bridge

## Self-Check: PASSED
