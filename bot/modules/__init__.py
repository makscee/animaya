"""bot.modules — module lifecycle system (Phase 3).

Public API (added incrementally across plans):
  - Plan 01 (MODS-01): ModuleManifest, ModuleScripts, validate_manifest
  - Plan 02 (MODS-03): read_registry, write_registry, list_installed, get_entry,
                       add_entry, remove_entry
  - Plan 03 (MODS-02): install, uninstall
  - Plan 04 (MODS-04): assemble_claude_md (pending)
"""
from __future__ import annotations

from bot.modules.lifecycle import install, uninstall
from bot.modules.manifest import ModuleManifest, ModuleScripts, validate_manifest
from bot.modules.registry import (
    add_entry,
    get_entry,
    list_installed,
    read_registry,
    remove_entry,
    write_registry,
)

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
    "install",
    "uninstall",
]
