"""Module discovery + description helpers (Phase 5 DASH-04).

Thin wrapper over :mod:`bot.modules` that distinguishes **available** modules
(manifest on disk, not in registry) from **installed** modules (registry
entry present). Keeps the route layer free of filesystem iteration and
manifest-parsing noise.

Modules are discovered from ``ANIMAYA_MODULES_DIR`` (env var) when set,
otherwise from :data:`bot.modules.lifecycle.DEFAULT_MODULES_ROOT`.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from bot.modules import get_entry, read_registry, validate_manifest
from bot.modules.lifecycle import DEFAULT_MODULES_ROOT

logger = logging.getLogger(__name__)


# ── Root resolution ──────────────────────────────────────────────────
def modules_root() -> Path:
    """Return the directory containing module folders (env-var aware)."""
    raw = os.environ.get("ANIMAYA_MODULES_DIR")
    return Path(raw).resolve() if raw else DEFAULT_MODULES_ROOT.resolve()


def module_dir_for(name: str) -> Path:
    """Return the directory for module ``name`` under :func:`modules_root`."""
    return modules_root() / name


# ── Card model ───────────────────────────────────────────────────────
@dataclass
class ModuleCard:
    """Single module, denormalised for template rendering."""

    name: str
    version: str
    description: str
    owned_paths: list[str]
    depends: list[str]
    has_config: bool
    installed: bool
    installed_at: str | None


def _describe_from_disk(module_dir: Path) -> ModuleCard | None:
    """Build a :class:`ModuleCard` from a module directory, or ``None``.

    Returns ``None`` if the manifest is missing or invalid; logs a warning
    so operators can diagnose. The dashboard is resilient to broken
    module folders (bad schema, unreadable path, etc.).
    """
    try:
        m = validate_manifest(module_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("skip module %s: %s", module_dir.name, exc)
        return None
    # Description is not a manifest field — use system_prompt_path's first
    # non-empty line as a humane fallback, truncated.
    description = ""
    prompt_path = module_dir / m.system_prompt_path
    if prompt_path.is_file():
        try:
            for line in prompt_path.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped:
                    description = stripped[:200]
                    break
        except OSError:
            pass
    return ModuleCard(
        name=m.name,
        version=m.version,
        description=description,
        owned_paths=list(m.owned_paths),
        depends=list(m.depends),
        has_config=bool(m.config_schema and m.config_schema.get("properties")),
        installed=False,
        installed_at=None,
    )


# ── Public API ───────────────────────────────────────────────────────
def all_cards(hub_dir: Path) -> tuple[list[ModuleCard], list[ModuleCard]]:
    """Return ``(installed, available)`` — installed first in registry order.

    Iterates :func:`modules_root` in sorted order (deterministic UI). Modules
    whose manifest fails validation are skipped with a warning (logged, not
    raised).
    """
    root = modules_root()
    installed_names = {e["name"] for e in read_registry(hub_dir)["modules"]}
    installed: list[ModuleCard] = []
    available: list[ModuleCard] = []
    children = sorted(root.iterdir()) if root.is_dir() else []
    for child in children:
        if not child.is_dir():
            continue
        card = _describe_from_disk(child)
        if card is None:
            continue
        if card.name in installed_names:
            entry = get_entry(hub_dir, card.name)
            card.installed = True
            card.installed_at = entry.get("installed_at") if entry else None
            installed.append(card)
        else:
            available.append(card)
    return installed, available


def describe(hub_dir: Path, name: str) -> ModuleCard | None:
    """Return a single card or ``None`` if the module isn't on disk."""
    candidate = module_dir_for(name)
    if not candidate.is_dir():
        return None
    card = _describe_from_disk(candidate)
    if card is None:
        return None
    entry = get_entry(hub_dir, name)
    if entry is not None:
        card.installed = True
        card.installed_at = entry.get("installed_at")
    return card


__all__ = [
    "ModuleCard",
    "all_cards",
    "describe",
    "module_dir_for",
    "modules_root",
]
