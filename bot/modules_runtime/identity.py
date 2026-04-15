"""Identity module runtime: sentinel helpers, file I/O, onboarding ConversationHandler.

Implements IDEN-01 (onboarding Q&A), IDEN-02 (file location), IDEN-04
(`/identity` reconfigure). IDEN-03 (system-prompt injection) lives in
bot/claude_query.py.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

logger = logging.getLogger(__name__)

# ── Paths ───────────────────────────────────────────────────────────
IDENTITY_DIR: Path = Path.home() / "hub" / "knowledge" / "identity"
USER_FILE: Path = IDENTITY_DIR / "USER.md"
SOUL_FILE: Path = IDENTITY_DIR / "SOUL.md"
PENDING_SENTINEL: Path = IDENTITY_DIR / ".pending-onboarding"

PLACEHOLDER_MARKER = "<!-- animaya:placeholder -->"

# ── Conversation states ─────────────────────────────────────────────
Q1_USER, Q2_SOUL, Q3_ADDRESS = range(3)


# ── Pure helpers (testable without telegram) ────────────────────────
def is_identity_initialized(identity_dir: Path | None = None) -> bool:
    """True iff USER.md and SOUL.md exist AND neither contains PLACEHOLDER_MARKER."""
    d = identity_dir or IDENTITY_DIR
    user = d / "USER.md"
    soul = d / "SOUL.md"
    if not (user.is_file() and soul.is_file()):
        return False
    for f in (user, soul):
        if PLACEHOLDER_MARKER in f.read_text(encoding="utf-8"):
            return False
    return True


def mark_pending_onboarding(identity_dir: Path | None = None) -> None:
    """Create the .pending-onboarding sentinel file."""
    d = identity_dir or IDENTITY_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / ".pending-onboarding").write_text(
        "awaiting first user message\n", encoding="utf-8"
    )


def clear_pending_onboarding(identity_dir: Path | None = None) -> None:
    """Remove the .pending-onboarding sentinel file."""
    d = identity_dir or IDENTITY_DIR
    (d / ".pending-onboarding").unlink(missing_ok=True)


def _atomic_write(path: Path, content: str) -> None:
    """Write content to path atomically via a .tmp intermediate."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def write_identity_files(
    user_text: str,
    soul_text: str,
    addressing: str,
    identity_dir: Path | None = None,
) -> None:
    """Atomically write USER.md and SOUL.md from onboarding answers.

    Overwrites placeholder content. Strips leading/trailing whitespace.
    Clears the .pending-onboarding sentinel on success.

    Args:
        user_text: User's self-description (answer to Q1).
        soul_text: Desired assistant persona (answer to Q2).
        addressing: How user wants to be addressed (answer to Q3).
        identity_dir: Override for IDENTITY_DIR (used in tests).
    """
    d = identity_dir or IDENTITY_DIR
    user_md = (
        f"# User\n\n"
        f"## Self-description\n\n{user_text.strip()}\n\n"
        f"## Address as\n\n{addressing.strip()}\n"
    )
    soul_md = f"# Assistant Identity\n\n{soul_text.strip()}\n"
    _atomic_write(d / "USER.md", user_md)
    _atomic_write(d / "SOUL.md", soul_md)
    clear_pending_onboarding(d)
    logger.info("identity files written; onboarding complete")


# ── ConversationHandler (Telegram-bound) ────────────────────────────
async def onboarding_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for /identity command and sentinel-triggered first message."""
    await update.message.reply_text(
        "Let's get to know each other. First — tell me about yourself: "
        "who are you, what do you do, what matters to you?"
    )
    return Q1_USER


async def _onboarding_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["identity_user"] = update.message.text
    await update.message.reply_text(
        "Thanks. Now — what kind of assistant do you want me to be? "
        "Personality, tone, what should I prioritize?"
    )
    return Q2_SOUL


async def _onboarding_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["identity_soul"] = update.message.text
    await update.message.reply_text(
        "Last one: how should I address you? (first name, nickname, anything you like)"
    )
    return Q3_ADDRESS


async def _onboarding_q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    addressing = update.message.text or "friend"
    write_identity_files(
        user_text=context.user_data.get("identity_user", ""),
        soul_text=context.user_data.get("identity_soul", ""),
        addressing=addressing,
    )
    await update.message.reply_text(
        f"Got it — I'll remember you as {addressing}. Send me anything."
    )
    return ConversationHandler.END


async def _onboarding_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Onboarding cancelled. Send /identity to retry.")
    return ConversationHandler.END


class _SentinelPresent(filters.MessageFilter):
    """Match any message while the identity onboarding sentinel file exists."""

    def filter(self, message) -> bool:  # type: ignore[override]
        return PENDING_SENTINEL.exists()


def build_onboarding_handler() -> ConversationHandler:
    """ConversationHandler for /identity command + sentinel-triggered first message.

    Entry points:
    - `/identity` command — explicit reconfigure (IDEN-04)
    - First text message when `.pending-onboarding` sentinel exists (IDEN-01) —
      this pulls the user INTO the conversation state machine so subsequent
      messages route through the Q1/Q2/Q3 handlers instead of re-triggering Q1.
    """
    sentinel_filter = _SentinelPresent() & filters.TEXT & ~filters.COMMAND
    return ConversationHandler(
        entry_points=[
            CommandHandler("identity", onboarding_start),
            MessageHandler(sentinel_filter, onboarding_start),
        ],
        states={
            Q1_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, _onboarding_q1)],
            Q2_SOUL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _onboarding_q2)],
            Q3_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, _onboarding_q3)],
        },
        fallbacks=[CommandHandler("cancel", _onboarding_cancel)],
        name="identity_onboarding",
        persistent=False,
    )
