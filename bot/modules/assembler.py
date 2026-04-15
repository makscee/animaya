"""CLAUDE.md assembler (Phase 3, MODS-04).

Rebuilds ``CLAUDE.md`` from the core base template + installed-module prompts
at every bot startup and at the end of every install/uninstall (D-18).

Order: base template → per-module sections sorted by ``installed_at`` (D-16),
each wrapped in ``<module name="...">...</module>`` (D-17).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from bot.events import emit as _emit_event
from bot.modules.manifest import validate_manifest
from bot.modules.registry import read_registry

logger = logging.getLogger(__name__)

# Repo root: three levels up from this file (bot/modules/assembler.py)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_REPO_ROOT: Path = _REPO_ROOT
DEFAULT_MODULES_ROOT: Path = _REPO_ROOT / "modules"
DEFAULT_TEMPLATE_PATH: Path = _REPO_ROOT / "bot" / "templates" / "CLAUDE.md"

# Markers preserved from Phase 1 stub for test compatibility
MARKER_START = "<!-- module-prompts-start -->"
MARKER_END = "<!-- module-prompts-end -->"
EMPTY_MODULES_COMMENT = "<!-- No modules installed -->"


def _escape_module_content(text: str) -> str:
    """Prevent a module's prompt from closing another module's XML tag.

    Replaces ``</module>`` inside prompt content with an HTML-entity-escaped
    variant. Opening tags are left alone; only the terminator is dangerous.
    """
    return text.replace("</module>", "&lt;/module&gt;")


def _render_module_section(name: str, prompt_text: str) -> str:
    """Wrap a module prompt in its XML section (D-17)."""
    safe = _escape_module_content(prompt_text.strip())
    return f'<module name="{name}">\n{safe}\n</module>'


def _placeholder_section(name: str, comment: str) -> str:
    return f'<module name="{name}">\n<!-- {comment} -->\n</module>'


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def _resolve_module_dir(
    entry: dict, modules_root: Path
) -> Path:
    """Resolve the module directory for a registry entry.

    Preference order:
    1. entry["module_dir"] (absolute path recorded at install time) — handles
       test fixtures and non-default layouts.
    2. ``modules_root / entry["name"]`` — production default (D-19).
    """
    recorded = entry.get("module_dir")
    if recorded:
        p = Path(recorded)
        if p.is_dir():
            return p
    return modules_root / entry["name"]


def _load_prompt_for_entry(
    entry: dict, modules_root: Path
) -> tuple[str | None, str]:
    """Return (prompt_text_or_None, reason_if_none) for a registry entry.

    Degrades gracefully (D-18): any failure returns None with a reason for a
    placeholder comment rather than raising.
    """
    name = entry["name"]

    # Allow raw inline prompt for testing / lightweight entries (no module dir
    # on disk). Used by test_assembler_preserves_install_order.
    inline = entry.get("prompt")
    if isinstance(inline, str) and inline:
        return inline, ""

    module_dir = _resolve_module_dir(entry, modules_root)
    if not module_dir.is_dir():
        logger.warning("module dir missing for %s at %s", name, module_dir)
        return None, "module dir not found"

    try:
        manifest = validate_manifest(module_dir)
    except Exception as exc:  # noqa: BLE001 — assembler must not crash boot
        logger.warning("manifest invalid for %s: %s", name, exc)
        return None, "manifest invalid"

    prompt_file = module_dir / manifest.system_prompt_path
    if not prompt_file.is_file():
        logger.warning("prompt missing for %s at %s", name, prompt_file)
        return None, "prompt not found"

    return prompt_file.read_text(encoding="utf-8"), ""


def assemble_claude_md(
    hub_dir: Path,
    *,
    modules_root: Path | None = None,
    repo_root: Path | None = None,
    output_path: Path | None = None,
    template_path: Path | None = None,
) -> str:
    """Rebuild CLAUDE.md; return the written content string.

    Per D-19 the output path defaults to ``hub_dir / "CLAUDE.md"``. The
    function returns the written contents for convenience (tests assert on
    substrings of the return value).

    Args:
        hub_dir: Directory containing registry.json. Output file written here
            unless ``output_path`` overrides.
        modules_root: Directory holding module folders. Default: ``<repo>/modules``.
        repo_root: Project root (reserved for future use).
        output_path: Alternative output file path. Default: ``hub_dir / "CLAUDE.md"``.
        template_path: Base template. Default: ``bot/templates/CLAUDE.md``.

    Returns:
        The assembled CLAUDE.md content (also written to disk).
    """
    hub_dir = Path(hub_dir).resolve()
    modules_root = (modules_root or DEFAULT_MODULES_ROOT).resolve()
    template_path = (template_path or DEFAULT_TEMPLATE_PATH).resolve()
    output_path = (output_path or (hub_dir / "CLAUDE.md")).resolve()

    # 1. Base template (D-19)
    if template_path.is_file():
        base = template_path.read_text(encoding="utf-8").rstrip() + "\n"
    else:
        logger.warning("base template missing at %s — using empty", template_path)
        base = "# Animaya\n"

    # 2. Registry read (D-18 defensive: missing file → empty registry)
    try:
        registry = read_registry(hub_dir)
    except Exception as exc:  # noqa: BLE001 — never crash boot
        logger.warning("registry read failed at %s: %s", hub_dir, exc)
        registry = {"modules": []}

    entries = sorted(
        registry.get("modules", []), key=lambda e: e.get("installed_at", "")
    )

    # 3. Per-module sections (D-16 install order, D-17 XML wrap)
    sections: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if not name:
            logger.warning("registry entry missing name, skipping: %s", entry)
            continue
        prompt_text, reason = _load_prompt_for_entry(entry, modules_root)
        if prompt_text is None:
            sections.append(_placeholder_section(name, reason))
            continue
        sections.append(_render_module_section(name, prompt_text))

    # 4. Assemble body between markers
    if sections:
        body = "\n\n".join(sections)
    else:
        body = EMPTY_MODULES_COMMENT

    output = (
        f"{base}\n"
        f"{MARKER_START}\n"
        f"{body}\n"
        f"{MARKER_END}\n"
    )
    _atomic_write(output_path, output)
    logger.info(
        "CLAUDE.md assembled at %s (%d modules)", output_path, len(sections)
    )
    try:
        _emit_event(
            "info",
            "assembler",
            "CLAUDE.md rebuilt",
            modules=[e.get("name") for e in entries if e.get("name")],
        )
    except Exception:  # noqa: BLE001 — events are best-effort
        logger.debug("events.emit failed for assembler", exc_info=True)
    return output
