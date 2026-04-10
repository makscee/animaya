"""Tier 1: Core memory — always injected into system prompt (~500 tokens).

Reads summaries from identity files and provides compact context.
The agent uses Read/Grep for deeper access (Tier 2 & 3).
"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def build_core_context(data_dir: Path) -> str:
    """Build Tier 1 core context for system prompt injection."""
    parts = []

    # Soul summary (first paragraph, max ~400 chars)
    soul_path = data_dir / "SOUL.md"
    if soul_path.exists():
        content = soul_path.read_text(encoding="utf-8").strip()
        lines = content.split("\n")
        summary_lines = []
        started = False
        for line in lines:
            if not started and line.strip() and not line.startswith("#"):
                started = True
            if started:
                summary_lines.append(line)
                if len("\n".join(summary_lines)) > 400:
                    break
        if summary_lines:
            parts.append("## Your Identity\n" + "\n".join(summary_lines))

    # Owner summary
    owner_path = data_dir / "OWNER.md"
    if owner_path.exists():
        content = owner_path.read_text(encoding="utf-8").strip()
        if len(content) > 500:
            content = content[:500] + "..."
        parts.append("## Owner\n" + content)

    # Recent facts (last 10 lines)
    facts_path = data_dir / "memory" / "facts.md"
    if facts_path.exists():
        content = facts_path.read_text(encoding="utf-8").strip()
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        if lines:
            parts.append("## Key Facts\n" + "\n".join(lines[-10:]))

    # Active spaces list
    spaces_dir = data_dir / "spaces"
    if spaces_dir.exists():
        space_names = [
            s.name
            for s in sorted(spaces_dir.iterdir())
            if s.is_dir() and s.name.startswith("@")
        ]
        if space_names:
            parts.append("## Your Spaces\n" + ", ".join(space_names))

    return "\n\n".join(parts) if parts else ""


def build_consolidation_prompt() -> str:
    """Build instructions for post-conversation memory consolidation."""
    return """Review this conversation and save any important new information:

1. **Facts about the owner** — preferences, routines, relationships, goals → append to /data/memory/facts.md
2. **People mentioned** — names, roles, relationships → append to /data/memory/people.md
3. **Projects/tasks** — new projects, deadlines, action items → append to /data/memory/projects.md
4. **Update OWNER.md** if you learned something significant about the owner
5. **Update active space** if conversation was about a specific topic

Rules:
- Only save NEW information not already in memory files
- Use bullet points (- item)
- Be concise — facts not narratives
- Skip greetings, small talk, and meta-conversation
- If nothing worth remembering, do nothing"""
