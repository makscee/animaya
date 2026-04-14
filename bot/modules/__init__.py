"""bot.modules — module lifecycle system (Phase 3).

Public API (added incrementally across plans):
  - validate_manifest(module_dir)        # Plan 01 (MODS-01) — this file
  - read_registry() / list_installed()   # Plan 02 (MODS-03)
  - install(name) / uninstall(name)      # Plan 03 (MODS-02)
  - assemble_claude_md(data_path)        # Plan 04 (MODS-04)
"""
from __future__ import annotations

from bot.modules.manifest import ModuleManifest, ModuleScripts, validate_manifest

__all__ = [
    "ModuleManifest",
    "ModuleScripts",
    "validate_manifest",
]
