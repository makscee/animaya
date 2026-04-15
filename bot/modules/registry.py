"""Module registry (Phase 3, MODS-03).

Canonical state: ``<hub_dir>/registry.json`` where hub_dir defaults to
``~/hub/knowledge/animaya/`` (D-06). Git-versioned with Hub.

All writes are atomic (temp file + os.replace) to survive crashes mid-write.
All reads gracefully handle missing file (returns empty registry).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

REGISTRY_FILENAME = "registry.json"
EMPTY_REGISTRY: dict = {"modules": []}


# ── Low-level I/O ───────────────────────────────────────────────────
def _registry_path(hub_dir: Path) -> Path:
    return hub_dir / REGISTRY_FILENAME


def read_registry(hub_dir: Path) -> dict:
    """Read registry; return ``{"modules": []}`` if file absent.

    Args:
        hub_dir: Hub directory (e.g., ``~/hub/knowledge/animaya/``).

    Returns:
        Registry dict with ``modules`` key always present.

    Raises:
        ValueError: registry.json exists but has invalid structure.
        json.JSONDecodeError: registry.json exists but is malformed JSON.
    """
    path = _registry_path(hub_dir)
    if not path.is_file():
        return {"modules": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if "modules" not in data or not isinstance(data["modules"], list):
        raise ValueError(
            f"registry.json at {path} has invalid structure (missing 'modules' list)"
        )
    return data


def write_registry(hub_dir: Path, data: dict) -> None:
    """Write registry atomically (temp file + rename).

    Args:
        hub_dir: Hub directory. Parent dirs are auto-created.
        data: Registry dict (must have "modules" list).

    Raises:
        ValueError: data is structurally invalid.
    """
    if "modules" not in data or not isinstance(data["modules"], list):
        raise ValueError("registry data must contain a 'modules' list")
    hub_dir.mkdir(parents=True, exist_ok=True)
    target = _registry_path(hub_dir)
    # Sibling temp file (same filesystem ⇒ atomic rename via os.replace).
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=False), encoding="utf-8")
    os.replace(tmp, target)
    logger.info("Registry written: %d entries at %s", len(data["modules"]), target)


# ── Query helpers ───────────────────────────────────────────────────
def list_installed(hub_dir: Path) -> list[str]:
    """Return module names in install order (ascending installed_at).

    ISO-8601 UTC strings sort lexicographically == temporally (D-16).
    """
    reg = read_registry(hub_dir)
    entries = sorted(reg["modules"], key=lambda e: e.get("installed_at", ""))
    return [e["name"] for e in entries]


def get_entry(hub_dir: Path, name: str) -> dict | None:
    """Return registry entry by name, or None if not installed."""
    reg = read_registry(hub_dir)
    for entry in reg["modules"]:
        if entry.get("name") == name:
            return entry
    return None


# ── Mutation helpers ────────────────────────────────────────────────
def add_entry(hub_dir: Path, entry: dict) -> None:
    """Append a new entry; reject if name already present (D-14).

    Args:
        entry: Must have at least 'name', 'version', 'manifest_version',
               'installed_at', 'config', 'depends' keys (D-07 + A2).

    Raises:
        ValueError: entry missing required keys, or module already installed.
    """
    required = {"name", "version", "manifest_version", "installed_at", "config", "depends"}
    missing = required - set(entry)
    if missing:
        raise ValueError(f"registry entry missing keys: {sorted(missing)}")
    reg = read_registry(hub_dir)
    if any(e.get("name") == entry["name"] for e in reg["modules"]):
        raise ValueError(f"module {entry['name']!r} already in registry")
    reg["modules"].append(entry)
    write_registry(hub_dir, reg)


def remove_entry(hub_dir: Path, name: str) -> None:
    """Remove entry by name.

    Raises:
        KeyError: module not in registry.
    """
    reg = read_registry(hub_dir)
    before = len(reg["modules"])
    reg["modules"] = [e for e in reg["modules"] if e.get("name") != name]
    if len(reg["modules"]) == before:
        raise KeyError(f"module {name!r} not in registry")
    write_registry(hub_dir, reg)


# ── One-shot migration (Phase 8 / D-8.5) ────────────────────────────────


def _module_dir(data_path: Path, name: str) -> Path:
    """Return the on-disk module directory path for a given module name."""
    # Convention: modules live in <data_path>/../../modules/<name> relative to
    # the hub knowledge dir, OR in the animaya repo root modules/<name> dir.
    # For registry purposes, data_path is the hub_dir; on-disk module dirs live
    # in the repo root modules/ tree, three levels up from bot/modules/registry.py.
    _repo_root = Path(__file__).resolve().parent.parent.parent
    return _repo_root / "modules" / name


def migrate_bridge_rename(data_path: Path) -> bool:
    """Rename registry entry 'bridge' -> 'telegram-bridge' and on-disk dir.

    One-shot migration for Phase 8 cutover. Idempotent: subsequent calls are
    no-ops after the first successful migration.

    Args:
        data_path: Root data directory (contains registry.json, i.e. hub_dir).

    Returns:
        True if migration was performed, False if nothing to migrate.
    """
    reg = read_registry(data_path)
    migrated = False
    for entry in reg.get("modules", []):
        if entry.get("name") == "bridge":
            entry["name"] = "telegram-bridge"
            # Also set runtime_entry if missing (old entries predate the field).
            entry.setdefault("runtime_entry", "bot.modules_runtime.telegram_bridge")
            migrated = True

    if migrated:
        write_registry(data_path, reg)
        # Rename on-disk dir if present.
        old_dir = _module_dir(data_path, "bridge")
        new_dir = _module_dir(data_path, "telegram-bridge")
        if old_dir.exists() and not new_dir.exists():
            old_dir.rename(new_dir)
        logger.warning(
            "Migrated module 'bridge' -> 'telegram-bridge' (registry + on-disk)"
        )
    return migrated
