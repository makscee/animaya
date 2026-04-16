# Quick Task 260416-ncp — Summary

**Task:** Fold memory module into core platform (mirror identity precedent)

## Commits

| # | Hash | What |
|---|------|------|
| 1 | `87439e2` | refactor: fold memory runtime into core (relocation + gate removal + migration fn) |
| 2 | `17a2eb7` | refactor: delete memory module dir, fold prompt into core template |
| 3 | `429c974` | test: update memory tests + boot mocks + project doc refs |

## Files

**Relocated**
- `bot/modules_runtime/memory.py` → `bot/memory/consolidation.py` (same public API;
  docstring updated — no longer calls out module isolation rules)

**Deleted**
- `modules/memory/manifest.json`
- `modules/memory/prompt.md`
- `modules/memory/install.sh`
- `modules/memory/uninstall.sh`
- `modules/memory/README.md`
- `bot/templates/modules/memory.md`

**Modified**
- `bot/claude_query.py` — verified only (`<memory-core>` injection was already
  unconditional; no change needed)
- `bot/bridge/telegram.py` — removed registry gate, call `maybe_trigger_consolidation`
  unconditionally with hardcoded defaults (150 / 10 / claude-haiku-4-5)
- `bot/modules/registry.py` — added `migrate_drop_memory(data_path) -> bool` idempotent
  migration
- `bot/modules/__init__.py` — re-export `migrate_drop_memory`; `migrate_registry` now
  runs both migrations and returns OR of their results
- `bot/main.py` — call `migrate_drop_memory(data_path)` at boot right after
  `migrate_bridge_rename`
- `bot/templates/CLAUDE.md` — merged the 3-tier memory section between Rules and
  Installed Modules (source: old `bot/templates/modules/memory.md`)
- `CLAUDE.md` + `.planning/PROJECT.md` — prose updated: identity and memory are core,
  not modules

**Tests**
- `tests/modules/test_memory.py` — rewritten: drop `TestMemoryInstall` (targeted the
  deleted install.sh), add import-surface tests, retarget `TestConsolidation` at
  `bot.memory.consolidation`
- `tests/modules/test_memory_migration.py` — new, 4 tests: entry removal, idempotency,
  no-op, warning log (mirrors `migrate_bridge_rename` test pattern)
- `tests/test_main_boot.py`, `tests/test_skeleton.py`, `tests/dashboard/test_main_wiring.py`
  — every `migrate_bridge_rename` mock paired with a sibling `migrate_drop_memory` mock;
  boot-order test now also asserts `migrate_drop_memory` is called exactly once

## Upgrade path for existing bots

A bot whose `~/hub/knowledge/animaya/registry.json` still has a `memory` entry gets
cleanly upgraded on next boot:

1. `bot/main.py` `_run()` calls `migrate_drop_memory(data_path)` (idempotent).
2. Entry removed from `registry.json`, warning logged.
3. CORE.md injection continues unchanged — it was never gated by the registry entry.
4. Consolidation continues unchanged — the telegram bridge no longer checks the
   registry either; it fires unconditionally with hardcoded defaults.

No manual steps required.

## Hardcoded defaults

The consolidation config previously read from the registry entry's `config` dict
(populated by `modules/memory/manifest.json` `config_schema`). After the fold, the
call site uses the schema defaults verbatim:

- `every_n_turns=10`
- `model="claude-haiku-4-5"`
- `max_lines=150`

See `FOLLOWUPS.md` for the item to expose these via the dashboard settings page.

## Verification

- All 345 tests in `tests/` pass.
- Ruff on touched files: clean of any regression I introduced (the one remaining
  F401/I001 in `bot/main.py:124` and the E501s in `tests/test_main_boot.py` are
  pre-existing, unrelated to this task).
- Import smoke: `from bot.memory.consolidation import maybe_trigger_consolidation;
  from bot.modules.registry import migrate_drop_memory` succeeds; the old
  `bot.modules_runtime.memory` path raises ImportError.

## Pattern consistency

Follows the identity-folding precedent. No new abstractions introduced; memory is
now structurally identical to identity: prompt lives in core template, runtime lives
under `bot/`, and a one-shot migration cleans up legacy registry entries on boot.
