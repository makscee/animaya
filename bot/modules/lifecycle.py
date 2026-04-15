"""Module lifecycle: install / uninstall orchestration (Phase 3, MODS-02).

Implements D-11 env injection, D-12 registry-update-after-script-success,
D-13 auto-rollback on install failure, D-14 no-reinstall, D-15 dependency
rules, and owned_paths validation (T-03-01-02 path traversal defense).
"""
from __future__ import annotations

import json
import logging
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from bot.events import emit as _emit_event
from bot.modules.assembler import assemble_claude_md
from bot.modules.manifest import ModuleManifest, validate_manifest
from bot.modules.registry import (
    add_entry,
    get_entry,
    read_registry,
    remove_entry,
)

logger = logging.getLogger(__name__)

# ── Defaults & validation ───────────────────────────────────────────
# Repo-layout default: ~/animaya/modules/  (three levels up from bot/modules/lifecycle.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODULES_ROOT: Path = _REPO_ROOT / "modules"
DEFAULT_HUB_DIR: Path = Path.home() / "hub" / "knowledge" / "animaya"

NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")


# ── Validation helpers ──────────────────────────────────────────────
def _validate_name(name: str) -> None:
    """Enforce safe module-name shape (carry-forward T-03-02-05)."""
    if not NAME_PATTERN.match(name):
        raise ValueError(
            f"invalid module name {name!r}: must match {NAME_PATTERN.pattern}"
        )


def _validate_owned_paths(owned_paths: list[str]) -> None:
    """Reject absolute paths and traversal segments (carry-forward T-03-01-02)."""
    for p in owned_paths:
        if not p:
            raise ValueError("owned_paths entries must be non-empty strings")
        if Path(p).is_absolute() or p.startswith("/"):
            raise ValueError(
                f"owned_path {p!r} must be relative to ANIMAYA_HUB_DIR, not absolute"
            )
        parts = Path(p).parts
        if ".." in parts:
            raise ValueError(f"owned_path {p!r} must not contain '..' segments")


def _resolve_owned_path(hub_dir: Path, rel: str) -> Path:
    """Resolve owned_path relative to hub_dir, with containment check."""
    hub_resolved = hub_dir.resolve()
    candidate = (hub_resolved / rel).resolve()
    # Containment: candidate must be under hub_resolved
    try:
        candidate.relative_to(hub_resolved)
    except ValueError as exc:
        raise ValueError(
            f"owned_path {rel!r} resolves outside hub_dir {hub_dir}"
        ) from exc
    return candidate


# ── Script invocation (D-11) ────────────────────────────────────────
def _run_script(
    script_path: Path, module_dir: Path, hub_dir: Path, config: dict
) -> int:
    """Run a lifecycle script with injected env vars. Returns exit code."""
    if not script_path.is_file():
        raise FileNotFoundError(f"lifecycle script not found: {script_path}")
    env = os.environ.copy()
    env["ANIMAYA_MODULE_DIR"] = str(module_dir.resolve())
    env["ANIMAYA_HUB_DIR"] = str(hub_dir.resolve())
    env["ANIMAYA_CONFIG_JSON"] = json.dumps(config or {})
    logger.info("Running %s for module %s", script_path.name, module_dir.name)
    result = subprocess.run(
        ["bash", str(script_path)],
        cwd=str(module_dir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        logger.info("  stdout: %s", result.stdout.strip())
    if result.stderr:
        logger.warning("  stderr: %s", result.stderr.strip())
    return result.returncode


# ── Dependency checks (D-15) ────────────────────────────────────────
def _missing_deps(manifest: ModuleManifest, hub_dir: Path) -> list[str]:
    reg = read_registry(hub_dir)
    installed = {e["name"] for e in reg["modules"]}
    return [d for d in manifest.depends if d not in installed]


def _dependents_of(name: str, hub_dir: Path) -> list[str]:
    reg = read_registry(hub_dir)
    return [e["name"] for e in reg["modules"] if name in e.get("depends", [])]


# ── Public API ──────────────────────────────────────────────────────
def install(
    module_dir: Path,
    hub_dir: Path,
    *,
    config: dict | None = None,
) -> dict:
    """Install a module end-to-end.

    Steps: locate module_dir → load & validate manifest → name validation →
    name/folder match → owned_paths safety → D-14 re-install rejection →
    D-15 dependency check → run install.sh with env injection → on success,
    write registry entry (D-12) → on failure, auto-rollback (D-13).

    Args:
        module_dir: Directory containing manifest.json + scripts.
        hub_dir: Hub directory (e.g., ``~/hub/knowledge/animaya``).
        config: User config snapshot stored in registry entry (D-07).

    Returns:
        The registry entry written.

    Raises:
        ValueError: validation failure (name, manifest, owned_paths, deps, duplicate).
        RuntimeError: install.sh exited non-zero (rollback performed).
        FileNotFoundError: module directory or manifest missing.
    """
    module_dir = Path(module_dir).resolve()
    hub_dir = Path(hub_dir).resolve()
    config = config or {}

    if not module_dir.is_dir():
        raise FileNotFoundError(f"module directory not found: {module_dir}")

    manifest = validate_manifest(module_dir)  # raises ValidationError on bad schema
    name = manifest.name

    # T-03-02-05: name regex enforcement before any side effects
    _validate_name(name)

    # T-03-01-05: folder name must match manifest.name
    if module_dir.name != name:
        raise ValueError(
            f"manifest.name {name!r} does not match folder {module_dir.name!r}"
        )

    # T-03-01-02: owned_paths traversal defense
    _validate_owned_paths(manifest.owned_paths)

    # D-14: reject re-install
    if get_entry(hub_dir, name) is not None:
        raise ValueError(f"module {name!r} already installed")

    # D-15: missing dependencies block install
    missing = _missing_deps(manifest, hub_dir)
    if missing:
        raise ValueError(f"missing dependency for {name!r}: {missing}")

    # Ensure hub_dir exists for scripts to write into
    hub_dir.mkdir(parents=True, exist_ok=True)

    # Run install.sh
    script = module_dir / manifest.scripts.install
    rc = _run_script(script, module_dir, hub_dir, config)
    if rc != 0:
        logger.error("install.sh failed (rc=%d) for %s — rolling back", rc, name)
        try:
            _emit_event(
                "error",
                "modules.install",
                f"{name} install.sh failed",
                rc=rc,
            )
        except Exception:  # noqa: BLE001
            logger.debug("events.emit failed for modules.install error", exc_info=True)
        _rollback_after_failed_install(manifest, module_dir, hub_dir, config)
        raise RuntimeError(f"install.sh failed for module {name!r} (rc={rc})")

    # D-12: success → write registry entry
    entry = {
        "name": manifest.name,
        "version": manifest.version,
        "manifest_version": manifest.manifest_version,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "depends": list(manifest.depends),
        # Record module dir so the assembler can locate prompt.md for modules
        # installed outside DEFAULT_MODULES_ROOT (e.g., during tests).
        "module_dir": str(module_dir),
    }
    add_entry(hub_dir, entry)
    logger.info("Installed module %s@%s", manifest.name, manifest.version)
    try:
        _emit_event(
            "info",
            "modules.install",
            f"{manifest.name}@{manifest.version} installed",
        )
    except Exception:  # noqa: BLE001
        logger.debug("events.emit failed for modules.install success", exc_info=True)

    # D-18: rebuild CLAUDE.md at end of install. Failure here must not
    # undo the install; log and continue.
    try:
        assemble_claude_md(hub_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CLAUDE.md reassembly after install failed: %s", exc)

    return entry


def _rollback_after_failed_install(
    manifest: ModuleManifest, module_dir: Path, hub_dir: Path, config: dict
) -> None:
    """Best-effort rollback (D-13): run uninstall.sh, verify owned_paths absent."""
    script = module_dir / manifest.scripts.uninstall
    try:
        rc = _run_script(script, module_dir, hub_dir, config)
        if rc != 0:
            logger.warning(
                "rollback uninstall.sh exited %d for %s", rc, manifest.name
            )
    except FileNotFoundError:
        logger.warning(
            "rollback: uninstall.sh missing for %s — skipping", manifest.name
        )

    # Verify owned_paths gone (MODS-05 leakage check even on rollback path).
    # Leakage here only LOGS (best-effort per D-13); authoritative enforcement
    # lives in uninstall() which RAISES.
    leaked: list[str] = []
    for rel in manifest.owned_paths:
        try:
            if _resolve_owned_path(hub_dir, rel).exists():
                leaked.append(rel)
        except ValueError:
            # Already caught by _validate_owned_paths earlier; defensive skip.
            continue
    if leaked:
        logger.error(
            "rollback left leaked paths for %s: %s", manifest.name, leaked
        )


def uninstall(
    name: str,
    hub_dir: Path,
    module_dir: Path,
) -> None:
    """Uninstall a module end-to-end.

    Steps: name validation → registry lookup (D-14 inverse: must be installed)
    → dependents check (D-15 reverse) → run uninstall.sh with env injection →
    remove registry entry → owned_paths leakage check (MODS-05 enforcement).

    Args:
        name: Installed module name.
        hub_dir: Hub directory holding registry.json.
        module_dir: Directory containing the module's manifest.json + scripts.

    Raises:
        KeyError: module not installed.
        ValueError: name invalid or dependents still installed.
        RuntimeError: uninstall.sh failed or owned_paths remain after cleanup.
    """
    _validate_name(name)
    hub_dir = Path(hub_dir).resolve()
    module_dir = Path(module_dir).resolve()

    entry = get_entry(hub_dir, name)
    if entry is None:
        raise KeyError(f"module {name!r} not installed")

    # D-15 reverse: reject if dependents exist
    dependents = _dependents_of(name, hub_dir)
    if dependents:
        raise ValueError(
            f"cannot uninstall {name!r}: dependents still installed: {dependents}"
        )

    manifest = validate_manifest(module_dir) if module_dir.is_dir() else None

    if manifest is not None:
        script = module_dir / manifest.scripts.uninstall
        rc = _run_script(script, module_dir, hub_dir, entry.get("config", {}))
        if rc != 0:
            try:
                _emit_event(
                    "error",
                    "modules.uninstall",
                    f"{name} uninstall.sh failed",
                    rc=rc,
                )
            except Exception:  # noqa: BLE001
                logger.debug(
                    "events.emit failed for modules.uninstall error", exc_info=True
                )
            raise RuntimeError(f"uninstall.sh failed for {name!r} (rc={rc})")

    # Registry cleanup first (if leakage check fails we still want registry truth)
    remove_entry(hub_dir, name)

    # D-18: rebuild CLAUDE.md after registry change, BEFORE the leakage
    # check (so a leaking uninstall still produces a CLAUDE.md reflecting
    # registry truth). Failure here is logged, not raised.
    try:
        assemble_claude_md(hub_dir)
    except Exception as exc:  # noqa: BLE001
        logger.warning("CLAUDE.md reassembly after uninstall failed: %s", exc)

    # MODS-05 leakage check — authoritative (raises on leak)
    if manifest is not None:
        leaked: list[str] = []
        for rel in manifest.owned_paths:
            try:
                if _resolve_owned_path(hub_dir, rel).exists():
                    leaked.append(rel)
            except ValueError:
                continue
        if leaked:
            raise RuntimeError(
                f"uninstall of {name!r} left owned_paths: {leaked}"
            )
    logger.info("Uninstalled module %s", name)
    try:
        _emit_event("info", "modules.uninstall", f"{name} uninstalled")
    except Exception:  # noqa: BLE001
        logger.debug("events.emit failed for modules.uninstall success", exc_info=True)
