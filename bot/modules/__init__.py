"""bot.modules — module lifecycle system (Phase 3).

Public API (added incrementally across plans):
  - Plan 01 (MODS-01): ModuleManifest, ModuleScripts, validate_manifest
  - Plan 02 (MODS-03): read_registry, write_registry, list_installed, get_entry,
                       add_entry, remove_entry
  - Plan 03 (MODS-02): install, uninstall
  - Plan 04 (MODS-04): assemble_claude_md
  - Phase 08 Plan 02 (D-8.5): migrate_registry (one-shot bridge→telegram-bridge rename)
"""
from __future__ import annotations

from pathlib import Path

from bot.modules.assembler import assemble_claude_md
from bot.modules.lifecycle import install, uninstall
from bot.modules.manifest import ModuleManifest, ModuleScripts, validate_manifest
from bot.modules.registry import (
    add_entry,
    get_entry,
    list_installed,
    migrate_bridge_rename,
    migrate_drop_memory,
    read_registry,
    remove_entry,
    write_registry,
)


def migrate_registry(data_path: Path) -> bool:
    """Run all one-shot registry migrations. Returns True if any migration happened.

    Currently includes:
    - migrate_bridge_rename: renames 'bridge' → 'telegram-bridge' (D-8.5).
    - migrate_drop_memory: drops legacy 'memory' entry (260416-ncp fold).
    """
    changed_bridge = migrate_bridge_rename(data_path)
    changed_memory = migrate_drop_memory(data_path)
    return changed_bridge or changed_memory


__all__ = [
    "ModuleManifest",
    "ModuleScripts",
    "validate_manifest",
    "read_registry",
    "write_registry",
    "list_installed",
    "get_entry",
    "add_entry",
    "remove_entry",
    "migrate_bridge_rename",
    "migrate_drop_memory",
    "migrate_registry",
    "install",
    "uninstall",
    "assemble_claude_md",
]
