"""Claude Code SDK query builder.

Single source of truth for constructing ClaudeCodeOptions.
Used by: telegram bridge, dashboard chat.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Identity / memory injection ─────────────────────────────────────
HUB_KNOWLEDGE: Path = Path.home() / "hub" / "knowledge"
REPO_ROOT: Path = Path(__file__).resolve().parent.parent
_PLACEHOLDER_MARKER = "<!-- animaya:placeholder -->"
_MAX_INJECT_CHARS = 8_000


def _read_for_injection(p: Path) -> str:
    """Return file content if present and non-placeholder; else empty string.

    Truncates at _MAX_INJECT_CHARS to bound prompt size. Escapes any closing
    XML tags that match Animaya's injection wrappers so a malicious file
    cannot break out of its block (T-04-01-03).
    """
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8").strip()
    if not text or _PLACEHOLDER_MARKER in text:
        return ""
    if len(text) > _MAX_INJECT_CHARS:
        text = text[:_MAX_INJECT_CHARS] + "\n…[truncated]"
    # Escape closing tags for Animaya's injection wrappers
    for tag in ("identity-user", "identity-soul", "memory-core"):
        text = text.replace(f"</{tag}>", f"&lt;/{tag}&gt;")
    return text


def _read_bootstrap() -> str:
    """Return BOOTSTRAP.md content if present at repo root; else empty string.

    Applies _MAX_INJECT_CHARS truncation and escapes </bootstrap> to prevent
    prompt-injection escapes. Does NOT skip placeholder markers — the file is
    operator-authored and always intentional.
    """
    p = REPO_ROOT / "BOOTSTRAP.md"
    if not p.is_file():
        return ""
    text = p.read_text(encoding="utf-8").strip()
    if not text:
        return ""
    if len(text) > _MAX_INJECT_CHARS:
        text = text[:_MAX_INJECT_CHARS] + "\n…[truncated]"
    text = text.replace("</bootstrap>", "&lt;/bootstrap&gt;")
    return text


def build_options(
    data_dir: Path | None = None,
    system_prompt_extra: str = "",
    cwd: Path | str | None = None,
):
    """Build ClaudeCodeOptions with standard configuration.

    Args:
        data_dir: Bot data directory (default: DATA_PATH env var).
        system_prompt_extra: Additional context to prepend (e.g., chat type, user info).
        cwd: Working directory for Claude (default: data_dir).

    Returns:
        ClaudeCodeOptions ready for query().
    """
    from claude_code_sdk import ClaudeCodeOptions

    d = data_dir or Path(os.environ.get("DATA_PATH", "/data"))
    work_dir = str(cwd) if cwd else str(d)

    parts = []
    if system_prompt_extra:
        parts.append(system_prompt_extra)

    # Bootstrap injection: inject BOOTSTRAP.md when present (onboarding state)
    bootstrap = _read_bootstrap()
    in_bootstrap_mode = bool(bootstrap)
    if in_bootstrap_mode:
        logger.info(
            "BOOTSTRAP.md present — forcing fresh Claude session "
            "(continue_conversation=False)"
        )
        parts.append(f"<bootstrap>\n{bootstrap}\n</bootstrap>")

    # IDEN-03: identity injection (XML-delimited per D-03)
    user_md = _read_for_injection(HUB_KNOWLEDGE / "identity" / "USER.md")
    soul_md = _read_for_injection(HUB_KNOWLEDGE / "identity" / "SOUL.md")
    if user_md:
        parts.append(f"<identity-user>\n{user_md}\n</identity-user>")
    if soul_md:
        parts.append(f"<identity-soul>\n{soul_md}\n</identity-soul>")

    # MEMO-04: core memory injection (CORE.md is auto-maintained by Haiku
    # consolidation in plan 04-03; safe to inject early — empty string when absent).
    core_md = _read_for_injection(HUB_KNOWLEDGE / "memory" / "CORE.md")
    if core_md:
        parts.append(f"<memory-core>\n{core_md}\n</memory-core>")

    system_prompt = "\n\n".join(parts) if parts else ""

    # Model from config.json or env (default: sonnet)
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    config_path = d / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            if cfg.get("model"):
                model = cfg["model"]
        except Exception:
            pass

    return ClaudeCodeOptions(
        model=model,
        system_prompt=system_prompt,
        cwd=work_dir,
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch",
        ],
        permission_mode="acceptEdits",
        continue_conversation=not in_bootstrap_mode,
    )
