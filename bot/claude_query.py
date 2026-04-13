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

    # Phase 4 adds memory context here

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
        continue_conversation=True,
    )
