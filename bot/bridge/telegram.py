"""Telegram bridge for Claude Code SDK.

Receives messages via python-telegram-bot, feeds them to Claude Code SDK,
streams responses back to Telegram with progressive text updates.
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
import time
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from pathlib import Path

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from bot.bridge.formatting import TG_MAX_LEN, md_to_html
from bot.events import emit as _emit_event
from bot.modules.registry import get_entry as _registry_get_entry
from bot.modules_runtime.identity import build_onboarding_handler
from bot.modules_runtime.memory import maybe_trigger_consolidation

logger = logging.getLogger(__name__)

_stats = {
    "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "messages_received": 0,
    "messages_sent": 0,
    "errors": 0,
}


def get_stats() -> dict:
    return {**_stats}


# ── SDK compatibility patch ─────────────────────────────────────────


def _patch_sdk_message_parser():
    """Patch claude-code-sdk to skip unknown message types instead of crashing."""
    try:
        from claude_code_sdk._internal import client as sdk_client
        from claude_code_sdk._internal import message_parser

        _original = message_parser.parse_message

        def _patched(data):
            try:
                return _original(data)
            except Exception as e:
                if "Unknown message type" in str(e):
                    logger.debug("Skipping unknown SDK message type: %s", e)
                    return None
                raise

        message_parser.parse_message = _patched
        sdk_client.parse_message = _patched
    except Exception:
        logger.warning("Could not patch SDK message parser", exc_info=True)


_patch_sdk_message_parser()

# Streaming throttle
_STREAM_MIN_INTERVAL = 0.5
_STREAM_MIN_CHARS = 30


# ── Concurrency (per-user lock) ────────────────────────────────────


def _get_user_lock(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> asyncio.Lock:
    locks = context.bot_data.setdefault("_user_locks", {})
    if user_id not in locks:
        locks[user_id] = asyncio.Lock()
    return locks[user_id]


async def _enqueue_or_run(user_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE, inner):
    lock = _get_user_lock(context, user_id)

    # Try non-blocking acquire
    acquired = False
    coro = lock.acquire()
    try:
        coro.send(None)
    except StopIteration:
        acquired = True
    else:
        coro.close()

    if acquired:
        try:
            await inner(update, context)
        finally:
            lock.release()
        return

    ack = await update.message.reply_text("\u2026Queued")
    await lock.acquire()
    try:
        with suppress(Exception):
            await ack.delete()
        await inner(update, context)
    except Exception:
        logger.exception("Error processing queued message for user %d", user_id)
    finally:
        lock.release()


# ── Status message helpers ──────────────────────────────────────────


async def _send_status(update: Update, text: str = "\u2026") -> object:
    return await update.message.reply_text(text, do_quote=True)


async def _update_status(msg, text: str, parse_mode=None) -> None:
    try:
        await msg.edit_text(text, parse_mode=parse_mode)
    except Exception:
        if parse_mode:
            with suppress(Exception):
                await msg.edit_text(text, parse_mode=None)
        # If both fail, silently ignore (streaming update, not critical)


async def _delete_status(msg) -> None:
    with suppress(Exception):
        await msg.delete()


@asynccontextmanager
async def _typing_loop(chat):
    async def _loop():
        while True:
            with suppress(Exception):
                await chat.send_action(ChatAction.TYPING)
            await asyncio.sleep(5)

    task = asyncio.create_task(_loop())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


# ── Message envelope ────────────────────────────────────────────────


def _envelope_message(update: Update, text: str) -> str:
    """Wrap message with origin metadata for the LLM."""
    chat = update.effective_chat
    user = update.effective_user
    msg = update.message

    fwd_name = None
    if msg and msg.forward_origin:
        origin = msg.forward_origin
        if hasattr(origin, "sender_user") and origin.sender_user:
            fwd_name = origin.sender_user.first_name
        elif hasattr(origin, "sender_user_name") and origin.sender_user_name:
            fwd_name = origin.sender_user_name
        elif hasattr(origin, "chat") and origin.chat:
            fwd_name = origin.chat.title or origin.chat.first_name

    reply_prefix = ""
    if msg and msg.reply_to_message:
        reply_msg = msg.reply_to_message
        quoted = reply_msg.text or reply_msg.caption or ""
        if quoted:
            if len(quoted) > 300:
                quoted = quoted[:300] + "\u2026"
            sender = reply_msg.from_user.first_name if reply_msg.from_user else ""
            reply_prefix = f"[replying to {sender}: {quoted}]\n"

    if chat.type != "private":
        sender = user.first_name if user else "Unknown"
        if fwd_name:
            return f"[{sender} forwarded from {fwd_name} in group]: {reply_prefix}{text}"
        return f"[{sender} in group]: {reply_prefix}{text}"

    if fwd_name:
        return f"[forwarded from {fwd_name}]: {reply_prefix}{text}"

    return reply_prefix + text


def _build_system_context(update: Update) -> str:
    """Build dynamic system context injected per query."""
    now = datetime.now(timezone.utc)
    chat = update.effective_chat
    user = update.effective_user
    parts = [f"Current time (UTC): {now.strftime('%Y-%m-%d %H:%M')}"]

    if chat.type != "private":
        parts.append(f"Chat type: group ({chat.title or ''})")
    else:
        parts.append("Chat type: private")

    if user:
        name = user.first_name or ""
        if user.last_name:
            name += f" {user.last_name}"
        parts.append(f"User: {name}")
        if user.username:
            parts.append(f"Username: @{user.username}")
        if user.language_code:
            parts.append(f"User language: {user.language_code}")

    thread_id = getattr(update.message, "message_thread_id", None) if update.message else None
    if thread_id:
        parts.append(f"Forum topic thread_id: {thread_id}")

    return "\n".join(parts)


# ── Streaming state ─────────────────────────────────────────────────


def _make_stream_state(status_msg, update: Update) -> dict:
    return {
        "status_msg": status_msg,
        "last_edit": 0.0,
        "last_len": 0,
        "first": True,
        "has_text": False,
        "pending_text": "",
        "update": update,
        "tools_used": [],
    }


async def _stream_text(state: dict, text: str) -> None:
    now = time.monotonic()
    text_len = len(text)
    msg = state["status_msg"]

    if not text.strip():
        return

    state["has_text"] = True
    state["pending_text"] = text

    if state["first"]:
        state["first"] = False
        state["last_edit"] = now
        state["last_len"] = text_len
        display = text[:TG_MAX_LEN]
        await _update_status(msg, md_to_html(display), parse_mode=ParseMode.HTML)
        return

    elapsed = now - state["last_edit"]
    new_chars = text_len - state["last_len"]
    if elapsed < _STREAM_MIN_INTERVAL or new_chars < _STREAM_MIN_CHARS:
        return

    state["last_edit"] = now
    state["last_len"] = text_len

    if text_len > TG_MAX_LEN - 10:
        display = "\u2026" + text[-(TG_MAX_LEN - 10):]
    else:
        display = text
    await _update_status(msg, md_to_html(display), parse_mode=ParseMode.HTML)


def _should_show_tools() -> bool:
    import json

    config_path = Path(os.environ.get("DATA_PATH", "/data")) / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            return cfg.get("show_tools", False)
        except Exception:
            pass
    return False


async def _on_tool_use(state: dict, tool_name: str, tool_input: dict | None = None) -> None:
    label = tool_name.replace("_", " ").capitalize()

    if _should_show_tools() and tool_input and isinstance(tool_input, dict):
        detail = ""
        for key in ("command", "pattern", "file_path", "query", "path", "prompt", "url"):
            if key in tool_input:
                detail = f": {str(tool_input[key])[:60]}"
                break
        state["tools_used"].append(f"{label}{detail}")
    else:
        state["tools_used"].append(label)

    if _should_show_tools():
        tools_display = "\n".join(f"\u2022 {t}" for t in state["tools_used"][-8:])
        status_text = f"\u2026{label}\n\n{tools_display}"
    else:
        status_text = f"\u2026{label}"

    if state["has_text"]:
        pending = state.get("pending_text", "")
        if pending:
            display = pending[:TG_MAX_LEN]
            await _update_status(
                state["status_msg"], md_to_html(display), parse_mode=ParseMode.HTML
            )
        new_status = await _send_status(state["update"], status_text)
        state["status_msg"] = new_status
        state["has_text"] = False
        state["first"] = True
        state["last_edit"] = 0.0
        state["last_len"] = 0
        state["pending_text"] = ""
    else:
        await _update_status(state["status_msg"], status_text)


async def _finalize_stream(state: dict, reply: str, update: Update) -> None:
    status_msg = state["status_msg"]
    formatted = md_to_html(reply)
    if len(formatted) <= TG_MAX_LEN:
        try:
            await status_msg.edit_text(formatted, parse_mode=ParseMode.HTML)
        except Exception:
            await _delete_status(status_msg)
            try:
                await update.message.reply_text(formatted, parse_mode=ParseMode.HTML, do_quote=True)
            except Exception:
                await update.message.reply_text(reply, do_quote=True)
    else:
        await _delete_status(status_msg)
        for i in range(0, len(formatted), TG_MAX_LEN):
            chunk = formatted[i : i + TG_MAX_LEN]
            try:
                await update.message.reply_text(
                    chunk, parse_mode=ParseMode.HTML, do_quote=(i == 0)
                )
            except Exception:
                await update.message.reply_text(chunk, do_quote=(i == 0))


# ── Tool formatting ─────────────────────────────────────────────────


def _format_tool(name: str, tool_input: dict | None) -> str:
    """Format a tool use into a readable string like 'Read: /data/SOUL.md'."""
    if not tool_input or not isinstance(tool_input, dict):
        return name
    for key in ("file_path", "command", "pattern", "query", "path", "url", "prompt"):
        if key in tool_input:
            val = str(tool_input[key])
            if len(val) > 80:
                val = val[:77] + "..."
            return f"{name}: {val}"
    return name


# ── File sending ────────────────────────────────────────────────────

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
_FILE_PATH_RE = re.compile(r"/data/[\w./@\-]+\.(?:png|jpg|jpeg|gif|webp|pdf|txt|mp3|mp4|csv|svg)")


async def _send_referenced_files(text: str, update: Update) -> None:
    for path_str in _FILE_PATH_RE.findall(text):
        path = Path(path_str)
        if not path.exists():
            continue
        try:
            if path.suffix.lower() in _IMAGE_EXTS:
                with open(path, "rb") as f:
                    await update.message.reply_photo(photo=f)
            else:
                with open(path, "rb") as f:
                    await update.message.reply_document(document=f)
            logger.info("Sent file: %s", path)
        except Exception:
            logger.exception("Failed to send file: %s", path)


# ── Group chat filter ───────────────────────────────────────────────


def _is_bot_addressed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    chat = update.effective_chat
    if chat.type == "private":
        return True

    msg = update.message
    if not msg:
        return False

    if msg.voice or msg.audio or msg.photo or msg.document:
        return True

    text = msg.text or msg.caption or ""
    bot_username = context.bot.username
    if bot_username and f"@{bot_username}" in text:
        return True

    if msg.reply_to_message and msg.reply_to_message.from_user:
        if msg.reply_to_message.from_user.id == context.bot.id:
            return True

    return False


# ── /start handler ──────────────────────────────────────────────────


async def _handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    await update.message.reply_text(
        "Hey! I'm your personal AI assistant powered by Claude.\n\n"
        "Just send me a message and I'll help you out. I can:\n"
        "- Answer questions and have conversations\n"
        "- Read and write files\n"
        "- Run commands and search the web\n"
        "- Help with coding and analysis\n\n"
        "Send me a message to get started!",
    )


# ── Core message handler ───────────────────────────────────────────


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_user:
        return

    if not _is_bot_addressed(update, context):
        return

    # IDEN-01 onboarding routing is owned by build_onboarding_handler() —
    # its MessageHandler entry_point with `_SentinelPresent` filter captures
    # the first text while `.pending-onboarding` exists and puts the user
    # INTO the conversation state machine, so subsequent messages flow
    # through Q1→Q2→Q3 instead of re-triggering Q1 here.

    user_id = update.effective_user.id

    async def inner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.message
        text = msg.text or msg.caption or ""

        # Voice → stub (Phase 4 adds real transcription)
        voice = msg.voice or msg.audio
        if voice:
            text = "[Voice messages not yet supported]"

        # Photo → save and reference
        data_dir = Path(os.environ.get("DATA_PATH", "/data"))
        if msg.photo:
            photo = msg.photo[-1]
            tg_file = await photo.get_file()
            raw = await tg_file.download_as_bytearray()
            uploads_dir = data_dir / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            photo_path = uploads_dir / f"{photo.file_unique_id}.jpg"
            photo_path.write_bytes(raw)
            ref = f"[User sent a photo — saved at {photo_path}. Read it to see what it contains.]"
            text = f"{ref}\n{text}" if text else ref

        # Document → save and reference
        if msg.document:
            tg_file = await msg.document.get_file()
            raw = await tg_file.download_as_bytearray()
            uploads_dir = data_dir / "uploads"
            uploads_dir.mkdir(parents=True, exist_ok=True)
            doc_name = msg.document.file_name or msg.document.file_unique_id
            doc_path = uploads_dir / doc_name
            doc_path.write_bytes(raw)
            mime = msg.document.mime_type or "unknown"
            ref = f"[User sent a file: {doc_name} ({mime}) — saved at {doc_path}. Read it.]"
            text = f"{ref}\n{text}" if text else ref

        if not text.strip():
            return

        logger.info("[chat=%s user=%s] %s", update.effective_chat.id, user_id, text[:200])
        _stats["messages_received"] += 1
        try:
            _emit_event(
                "info",
                "bridge",
                "message received",
                chat_id=update.effective_chat.id,
            )
        except Exception:  # noqa: BLE001 — events are best-effort
            logger.debug("events.emit failed for bridge received", exc_info=True)

        envelope = _envelope_message(update, text)
        system_context = _build_system_context(update)

        # Per-session cwd — Claude Code scopes --continue by cwd
        chat = update.effective_chat
        thread_id = getattr(msg, "message_thread_id", None)
        if thread_id:
            session_key = f"{chat.id}_{thread_id}"
        elif chat.type == "private":
            session_key = str(user_id)
        else:
            session_key = str(chat.id)

        session_dir = data_dir / "sessions" / session_key
        session_dir.mkdir(parents=True, exist_ok=True)

        # Symlink CLAUDE.md into session dir
        session_claude = session_dir / "CLAUDE.md"
        if not session_claude.exists():
            claude_src = data_dir / "CLAUDE.md"
            if claude_src.exists():
                with suppress(OSError):
                    session_claude.symlink_to(claude_src)

        status_msg = await _send_status(update)
        state = _make_stream_state(status_msg, update)

        async with _typing_loop(update.effective_chat):
            try:
                from claude_code_sdk import query
                from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock

                from bot.claude_query import build_options

                options = build_options(
                    data_dir=data_dir,
                    system_prompt_extra=system_context,
                    cwd=session_dir,
                )

                accumulated = ""
                tools_used: list[str] = []
                async for message in query(prompt=envelope, options=options):
                    if message is None:
                        continue
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                accumulated += block.text
                                await _stream_text(state, accumulated)
                            elif isinstance(block, ToolUseBlock):
                                tools_used.append(_format_tool(block.name, block.input))
                                await _on_tool_use(state, block.name, block.input)

                if accumulated.strip():
                    _stats["messages_sent"] += 1
                    await _finalize_stream(state, accumulated, update)
                    await _send_referenced_files(accumulated, update)
                    try:
                        _emit_event(
                            "info",
                            "bridge",
                            "reply sent",
                            chat_id=update.effective_chat.id,
                        )
                    except Exception:  # noqa: BLE001
                        logger.debug(
                            "events.emit failed for bridge reply", exc_info=True
                        )
                    # MEMO-03: post-reply consolidation trigger (fire-and-forget).
                    # Gated on memory module being installed; cadence + model from registry config.
                    try:
                        mem_entry = _registry_get_entry(data_dir, "memory")
                    except Exception:
                        mem_entry = None
                    if mem_entry is not None:
                        cfg = (
                            mem_entry.get("config", {})
                            if isinstance(mem_entry.get("config"), dict)
                            else {}
                        )
                        every_n = int(cfg.get("consolidation_every_n_turns", 10))
                        cons_model = cfg.get("consolidation_model", "claude-haiku-4-5")
                        max_lines = int(cfg.get("core_max_lines", 150))
                        maybe_trigger_consolidation(
                            chat_data=context.chat_data,
                            conversation_text=f"USER: {text}\n\nASSISTANT: {accumulated}",
                            every_n_turns=every_n,
                            model=cons_model,
                            max_lines=max_lines,
                        )
                else:
                    await _delete_status(state["status_msg"])

            except Exception:
                logger.exception("Error in Claude Code SDK")
                _stats["errors"] += 1
                await _update_status(state["status_msg"], "\u274c Error processing message")

    await _enqueue_or_run(user_id, update, context, inner)


# ── Claim handler (pairing code, group=-2) ─────────────────────────


async def _claim_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process incoming 6-digit pairing codes from Telegram to claim ownership.

    Registered at group=-2 so it runs before _owner_gate (group=-1).
    Raises ApplicationHandlerStop on successful claim to prevent further processing.
    """
    if not update.message:
        return
    text = (update.message.text or "").strip()

    # Only process if exactly 6 digits
    if not text.isdigit() or len(text) != 6:
        return

    module_dir: Path | None = context.bot_data.get("module_dir")
    if module_dir is None:
        return

    from bot.modules.telegram_bridge_state import (  # noqa: PLC0415
        read_state,
        verify_pairing_code,
        write_state,
    )

    state = read_state(module_dir)
    if state.get("claim_status") != "pending":
        return

    # Increment attempt count before verification
    state["pairing_attempts"] = state.get("pairing_attempts", 0) + 1
    write_state(module_dir, state)

    if not verify_pairing_code(text, state):
        if state["pairing_attempts"] >= 5:
            state["claim_status"] = "unclaimed"
            state["pairing_code_hash"] = None
            state["pairing_code_salt"] = None
            state["pairing_code_expires"] = None
            state["pairing_attempts"] = 0
            write_state(module_dir, state)
            await update.message.reply_text(
                "Too many incorrect attempts. Click Regenerate to get a new code."
            )
        else:
            remaining = 5 - state["pairing_attempts"]
            await update.message.reply_text(
                f"Incorrect code. {remaining} attempt(s) remaining."
            )
        return

    # Success — claim ownership
    state.update(
        {
            "claim_status": "claimed",
            "owner_id": update.effective_user.id,
            "pairing_code_hash": None,
            "pairing_code_salt": None,
            "pairing_code_expires": None,
            "pairing_attempts": 0,
        }
    )
    write_state(module_dir, state)
    await update.message.reply_text("Ownership claimed. You are the owner of this bot.")
    raise ApplicationHandlerStop


# ── Application builder ─────────────────────────────────────────────


async def _error_handler(update, context):
    if "Timed out" in str(context.error) or "NetworkError" in str(context.error):
        return
    logger.warning("Telegram error: %s", context.error)
    try:
        err = context.error
        _emit_event(
            "error",
            "bridge",
            f"handler exception: {type(err).__name__}",
            error=str(err),
        )
    except Exception:  # noqa: BLE001
        logger.debug("events.emit failed for bridge error", exc_info=True)


async def _owner_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Drop updates from non-owner users when an owner has claimed the bot.

    Registered at group=-1 so it runs before any other handler. Raises
    ApplicationHandlerStop to short-circuit the handler chain.
    Reads claim_status from state.json — no env var dependency.
    """
    module_dir = context.bot_data.get("module_dir")
    if module_dir is None:
        return  # no module dir = can't check ownership, allow through
    from bot.modules.telegram_bridge_state import read_state  # noqa: PLC0415
    state = read_state(module_dir)
    if state.get("claim_status") != "claimed":
        return  # not claimed yet = allow all messages through
    owner_id = state.get("owner_id")
    if owner_id is None:
        return
    user_id = update.effective_user.id if update.effective_user else None
    if user_id != owner_id:
        raise ApplicationHandlerStop


def build_app(
    token: str,
    post_init: object | None = None,
) -> Application:
    proxy_url = os.environ.get("TELEGRAM_PROXY")
    builder = Application.builder().token(token)
    if proxy_url:
        builder = builder.proxy(proxy_url).get_updates_proxy(proxy_url)
        logger.info("Using Telegram proxy: %s", proxy_url)
    if post_init is not None:
        builder = builder.post_init(post_init)
    app = builder.build()
    app.add_handler(TypeHandler(Update, _claim_handler), group=-2)
    app.add_handler(TypeHandler(Update, _owner_gate), group=-1)
    app.add_handler(CommandHandler("start", _handle_start))
    # IDEN-04: /identity reconfigure ConversationHandler MUST be registered
    # BEFORE the catch-all MessageHandler so /identity is routed correctly
    # and Q&A state messages stay inside the conversation (Pitfall 8).
    app.add_handler(build_onboarding_handler())
    app.add_handler(
        MessageHandler(
            (filters.TEXT | filters.VOICE | filters.AUDIO | filters.PHOTO | filters.Document.ALL)
            & ~filters.COMMAND,
            _handle_message,
        )
    )
    app.add_error_handler(_error_handler)
    return app
