"""Shared Pydantic models for bot configuration."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BotConfig:
    """Per-bot configuration stored in /data/config.json."""

    model: str = "claude-sonnet-4-6"
    show_tools: bool = False
    auto_commit: bool = True
    commit_interval: int = 300
