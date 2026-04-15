"""Memory module runtime: Haiku consolidation query + post-reply trigger.

Implements MEMO-03 (consolidation) and the post-reply trigger that maintains
CORE.md. MEMO-04 (system-prompt injection) is handled in bot/claude_query.py
via _read_for_injection (added in plan 04-01). MEMO-01/02 require no runtime
code — Claude writes via built-in Write tool; git-versioning commits.

Per MODS-06: this module does NOT import bot.modules_runtime.identity or
bot.modules_runtime.git_versioning. Cross-module communication happens via
files under ~/hub/knowledge/.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths + defaults ────────────────────────────────────────────────
MEMORY_DIR: Path = Path.home() / "hub" / "knowledge" / "memory"
CORE_FILE: Path = MEMORY_DIR / "CORE.md"

CONSOLIDATION_MODEL = "claude-haiku-4-5"  # locked assumption A1
DEFAULT_CORE_MAX_LINES = 150
DEFAULT_EVERY_N_TURNS = 10


def _build_consolidation_prompt(conversation_text: str, max_lines: int) -> str:
    return (
        "You are updating the user's persistent memory based on the "
        "conversation below.\n\n"
        "CONVERSATION:\n"
        f"{conversation_text}\n\n"
        "TASK:\n"
        "1. Extract new facts about the user or their world that are worth "
        "remembering long-term.\n"
        "2. Read ~/hub/knowledge/memory/CORE.md (if it exists) — the current "
        "summary.\n"
        f"3. Write an updated CORE.md that incorporates new facts AND keeps "
        f"the total under ~{max_lines} lines. If you cannot fit, drop the "
        "least-important facts.\n"
        "4. Optionally write topical files (e.g., people.md, projects.md, "
        "preferences.md) under ~/hub/knowledge/memory/ for facts that don't "
        "belong in CORE.\n\n"
        "RULES:\n"
        "- Only new information; don't restate what's already in CORE.md.\n"
        "- Bullet style, factual, no narrative.\n"
        "- If nothing worth remembering, make no edits.\n\n"
        "Use the Read and Write tools. When done, respond with a single-line "
        'summary of what you changed (or "no changes").'
    )


async def consolidate_memory(
    conversation_text: str,
    hub_knowledge: Path | None = None,
    model: str = CONSOLIDATION_MODEL,
    max_lines: int = DEFAULT_CORE_MAX_LINES,
) -> None:
    """Run a separate SDK query with cheap model to update CORE.md.

    Uses continue_conversation=False so the main chat's --continue session is
    not polluted. Writes happen via Claude's built-in Write/Edit tools.

    Args:
        conversation_text: Recent conversation excerpt to consolidate.
        hub_knowledge: Override for ~/hub/knowledge/ (used in tests).
        model: Consolidation model (default: claude-haiku-4-5, locked A1).
        max_lines: Soft cap for CORE.md line count.
    """
    from claude_code_sdk import ClaudeCodeOptions, query
    from claude_code_sdk.types import AssistantMessage, TextBlock

    cwd = (hub_knowledge or (Path.home() / "hub" / "knowledge")).resolve()
    prompt = _build_consolidation_prompt(conversation_text, max_lines)
    options = ClaudeCodeOptions(
        model=model,
        system_prompt=(
            "You are a memory-consolidation assistant. Be terse and factual."
        ),
        cwd=str(cwd),
        allowed_tools=["Read", "Write", "Edit"],
        permission_mode="acceptEdits",
        continue_conversation=False,
    )
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        logger.info(
                            "consolidation: %s", block.text.strip()[:200]
                        )
    except Exception:
        logger.exception("consolidation query failed")


def maybe_trigger_consolidation(
    chat_data: dict,
    conversation_text: str,
    every_n_turns: int = DEFAULT_EVERY_N_TURNS,
    hub_knowledge: Path | None = None,
    model: str = CONSOLIDATION_MODEL,
    max_lines: int = DEFAULT_CORE_MAX_LINES,
) -> bool:
    """Increment chat_data turn counter; if N reached, fire-and-forget consolidate.

    Returns True if a consolidation task was scheduled, False otherwise.
    Idempotent on bad chat_data shape — defaults to 0 + 1 = 1 for first call.

    Args:
        chat_data: Telegram context.chat_data dict (mutable; turn_count tracked here).
        conversation_text: Recent exchange to pass to consolidation.
        every_n_turns: Fire consolidation every Nth turn (default 10).
        hub_knowledge: Override for ~/hub/knowledge/ (used in tests).
        model: Model override (default: CONSOLIDATION_MODEL).
        max_lines: CORE.md line cap override.

    Returns:
        True if consolidation was scheduled this call, False otherwise.
    """
    chat_data["turn_count"] = int(chat_data.get("turn_count", 0)) + 1
    if chat_data["turn_count"] % every_n_turns != 0:
        return False
    try:
        asyncio.create_task(
            consolidate_memory(
                conversation_text=conversation_text,
                hub_knowledge=hub_knowledge,
                model=model,
                max_lines=max_lines,
            ),
            name=f"memory-consolidation-turn-{chat_data['turn_count']}",
        )
    except RuntimeError:
        # No running event loop (e.g., called outside async context — tests).
        logger.warning(
            "maybe_trigger_consolidation: no running loop; skipping schedule"
        )
        return False
    logger.info(
        "scheduled memory consolidation (turn=%d)", chat_data["turn_count"]
    )
    return True
