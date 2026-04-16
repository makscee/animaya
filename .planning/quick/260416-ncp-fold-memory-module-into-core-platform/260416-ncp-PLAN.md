---
phase: quick-260416-ncp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - bot/memory/consolidation.py
  - bot/modules_runtime/memory.py
  - bot/bridge/telegram.py
  - bot/claude_query.py
  - bot/modules/registry.py
  - bot/main.py
  - bot/templates/CLAUDE.md
  - bot/templates/modules/memory.md
  - bot/dashboard/modules_view.py
  - modules/memory/manifest.json
  - modules/memory/prompt.md
  - modules/memory/install.sh
  - modules/memory/uninstall.sh
  - modules/memory/README.md
  - tests/modules/test_memory.py
  - tests/modules/test_memory_migration.py
  - CLAUDE.md
autonomous: true
requirements:
  - MEMO-03
  - MEMO-04
  - MODS-03

must_haves:
  truths:
    - "Bot injects <memory-core> into every system prompt, no registry/config check"
    - "Post-reply consolidation fires every N turns regardless of whether 'memory' is in registry"
    - "On startup, if registry.json has a stale 'memory' entry, it is silently removed and the registry file is rewritten"
    - "Dashboard Modules page no longer lists memory as a toggleable module"
    - "modules/memory/ directory no longer exists on disk"
    - "bot/templates/CLAUDE.md contains a merged Memory section describing the 3-tier memory system"
    - "Existing tests covering memory injection, consolidation runtime, and registry migration still pass"
  artifacts:
    - path: "bot/memory/consolidation.py"
      provides: "consolidate_memory + maybe_trigger_consolidation (relocated from modules_runtime)"
      contains: "def consolidate_memory"
    - path: "bot/modules_runtime/memory.py"
      provides: "deletion (file removed from repo)"
    - path: "bot/modules/registry.py"
      provides: "migrate_drop_memory idempotent migration"
      contains: "def migrate_drop_memory"
    - path: "bot/templates/CLAUDE.md"
      provides: "core Memory section merged from modules/memory.md"
      contains: "## Memory"
    - path: "modules/memory"
      provides: "MUST NOT EXIST"
  key_links:
    - from: "bot/bridge/telegram.py"
      to: "bot.memory.consolidation.maybe_trigger_consolidation"
      via: "unconditional call after reply (no registry gate)"
      pattern: "maybe_trigger_consolidation\\("
    - from: "bot/main.py _run()"
      to: "bot.modules.registry.migrate_drop_memory"
      via: "sibling call next to migrate_bridge_rename at boot"
      pattern: "migrate_drop_memory\\(data_path\\)"
    - from: "bot/claude_query.py build_options"
      to: "HUB_KNOWLEDGE/memory/CORE.md"
      via: "_read_for_injection (already unconditional, verify no regression)"
      pattern: "memory.*CORE\\.md"
---

# Quick 260416-ncp — Fold memory module into core

Fold the memory module into the core Animaya platform, mirroring how identity was
folded. Memory is no longer a user-toggleable module — persistent memory is always
on for a personal assistant. Remove the module boundary entirely: delete the
on-disk module dir, unconditionalize injection + consolidation, merge the prompt
snippet into the core template, and add an idempotent registry migration so
existing bots with "memory" installed get cleanly upgraded on next boot.

## Tasks

1. **Relocate runtime + unconditionalize consolidation + add registry migration**
   - Move `bot/modules_runtime/memory.py` → `bot/memory/consolidation.py` (same public API)
   - `bot/bridge/telegram.py`: remove `_registry_get_entry(data_dir, "memory")` gate;
     call `maybe_trigger_consolidation` unconditionally with hardcoded defaults
     (every_n_turns=10, model="claude-haiku-4-5", max_lines=150)
   - `bot/modules/registry.py`: add `migrate_drop_memory(data_path) -> bool`
     (idempotent; mirrors `migrate_bridge_rename` pattern)
   - `bot/modules/__init__.py`: re-export new helper; chain into `migrate_registry`
   - `bot/main.py _run()`: call `migrate_drop_memory(data_path)` right after
     `migrate_bridge_rename(data_path)`
   - `bot/claude_query.py`: verify only — CORE.md injection is already unconditional

2. **Fold prompt into core template, delete modules/memory/, scrub dashboard**
   - `bot/templates/CLAUDE.md`: insert `## Memory (3-tier system)` section between
     Rules and Installed Modules, sourced from `bot/templates/modules/memory.md`
   - Delete: `modules/memory/{manifest.json,prompt.md,install.sh,uninstall.sh,README.md}`
   - Delete: `bot/templates/modules/memory.md`
   - Dashboard: verify no hardcoded "memory" literal in module listing (discovery is
     filesystem-based, so removal is automatic)

3. **Update tests + project docs**
   - `tests/modules/test_memory.py`: rewrite — drop `TestMemoryInstall`; add import-
     surface tests (new path works, old path raises ImportError); retarget
     `TestConsolidation` at `bot.memory.consolidation`
   - `tests/modules/test_memory_migration.py`: new, 4 tests mirroring
     `migrate_bridge_rename` pattern (removal, idempotency, no-op, warning log)
   - Boot mocks: patch `migrate_drop_memory` wherever `migrate_bridge_rename` is
     patched (`test_main_boot.py`, `test_skeleton.py`, `test_main_wiring.py`);
     extend boot-order test to assert `migrate_drop_memory` called exactly once
   - `CLAUDE.md` + `.planning/PROJECT.md`: update prose — identity and memory are
     core, not modules
   - `FOLLOWUPS.md`: note that `core_max_lines`, `consolidation_every_n_turns`,
     `consolidation_model` are now hardcoded; expose via dashboard settings as
     followup

## Verification

- `python -m pytest tests/ -v` — all tests pass (345 total)
- `modules/memory/` and `bot/modules_runtime/memory.py` no longer exist
- `bot/templates/CLAUDE.md` contains `## Memory (3-tier system)` before `## Installed Modules`
- Seed registry with `{"name": "memory"}` + sibling entry; call `migrate_drop_memory`
  twice — first returns True and drops memory, second returns False and sibling
  survives
