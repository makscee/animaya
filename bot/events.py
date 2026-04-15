"""JSONL event log emitter for the Animaya dashboard (Phase 5).

Used by the dashboard home page activity feed and errors card. All
call sites across the bot append records here; the dashboard tails
the file for display. Leaf module — no bot.* imports — to avoid
import cycles with dashboard/bridge/modules code.

Env:
    ANIMAYA_EVENTS_LOG — path to the log file. Defaults to
    ``~/hub/knowledge/animaya/events.log``.

Concurrency:
    ``emit`` relies on POSIX ``O_APPEND`` atomicity for writes under
    PIPE_BUF (4096 bytes on Linux). JSON records are well under that.
    Bridge + modules + assembler may emit concurrently without a lock.

Rotation:
    ``rotate`` rewrites the log atomically via a sibling tempfile +
    ``os.replace``. Safe to call at startup.
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────
LEVELS: frozenset[str] = frozenset({"info", "warn", "error"})
MAX_LINES: int = 10_000
DEFAULT_LOG_PATH: Path = Path.home() / "hub" / "knowledge" / "animaya" / "events.log"


def _log_path() -> Path:
    """Resolve the log path at call time so tests can override via env var."""
    raw = os.environ.get("ANIMAYA_EVENTS_LOG")
    return Path(raw) if raw else DEFAULT_LOG_PATH


# ── Public API ───────────────────────────────────────────────────────
def emit(level: str, source: str, message: str, **details: object) -> None:
    """Append one JSON record to the events log.

    Args:
        level: one of ``info``, ``warn``, ``error``.
        source: component name (``bridge``, ``modules.install``, ``assembler`` …).
        message: human-readable short text.
        **details: optional structured payload; nested under ``details``.

    Raises:
        ValueError: ``level`` not in :data:`LEVELS`.

    Security:
        Call sites must not pass secrets (tokens, cookies, bot_token) in
        ``message`` or ``details``; the log is readable by the dashboard
        owner and is git-versioned via the GITV module when installed.
    """
    if level not in LEVELS:
        raise ValueError(f"invalid level {level!r}; expected one of {sorted(LEVELS)}")
    path = _log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, object] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "source": source,
        "message": message,
    }
    if details:
        record["details"] = details
    # json.dumps escapes embedded newlines → one physical line per record.
    line = json.dumps(record, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)


def tail(n: int = 50) -> list[dict]:
    """Return the last ``n`` parsed JSON records in chronological order.

    Corrupt / unparsable lines are skipped silently (logged at debug).
    Returns ``[]`` if the file does not exist.

    Args:
        n: maximum number of records to return (last-N window).

    Returns:
        list of parsed dicts, oldest first, length <= n.
    """
    path = _log_path()
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()[-n:]
    out: list[dict] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            logger.debug("skipping corrupt events.log line")
    return out


def rotate(max_lines: int = MAX_LINES) -> None:
    """Truncate events.log to the last ``max_lines`` lines atomically.

    Safe to call at startup. No-op when the file is missing or already
    under the cap.

    Args:
        max_lines: retain at most this many lines from the tail.
    """
    path = _log_path()
    if not path.is_file():
        return
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    if len(lines) <= max_lines:
        return
    keep = lines[-max_lines:]
    # Atomic rewrite via sibling tempfile + os.replace.
    fd, tmp = tempfile.mkstemp(prefix="events.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(keep)
        os.replace(tmp, path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise
    logger.info("events.log rotated: kept last %d lines at %s", max_lines, path)


__all__ = ["emit", "tail", "rotate", "LEVELS", "MAX_LINES", "DEFAULT_LOG_PATH"]
