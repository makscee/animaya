"""Git auto-versioning for bot data.

Background thread commits changes every N minutes.
Also provides commit-on-demand for graceful shutdown.
"""
from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_COMMIT_INTERVAL = int(os.environ.get("GIT_COMMIT_INTERVAL", "300"))
_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Animaya Bot",
    "GIT_AUTHOR_EMAIL": "bot@animaya.makscee.ru",
    "GIT_COMMITTER_NAME": "Animaya Bot",
    "GIT_COMMITTER_EMAIL": "bot@animaya.makscee.ru",
}


def _run_git(data_dir: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=data_dir,
            capture_output=True,
            text=True,
            timeout=30,
            env=_GIT_ENV,
        )
        return result.stdout.strip()
    except Exception as e:
        logger.debug("Git command failed: git %s -> %s", " ".join(args), e)
        return ""


def commit_if_changed(data_dir: Path) -> bool:
    """Commit all changes if any. Returns True if committed."""
    if not (data_dir / ".git").exists():
        return False

    status = _run_git(data_dir, "status", "--porcelain")
    if not status:
        return False

    _run_git(data_dir, "add", "-A")

    diff = _run_git(data_dir, "diff", "--cached", "--stat")
    if not diff:
        return False

    timestamp = time.strftime("%Y-%m-%d %H:%M")
    _run_git(data_dir, "commit", "-m", f"auto: data update {timestamp}")
    logger.info("Auto-committed data changes at %s", timestamp)
    return True


def start_auto_commit(data_dir: Path) -> threading.Thread:
    """Start background auto-commit thread."""

    def _loop():
        logger.info("Git auto-commit started (interval: %ds, dir: %s)", _COMMIT_INTERVAL, data_dir)
        while True:
            time.sleep(_COMMIT_INTERVAL)
            try:
                commit_if_changed(data_dir)
            except Exception:
                logger.exception("Auto-commit failed")

    thread = threading.Thread(target=_loop, daemon=True, name="git-autocommit")
    thread.start()
    return thread
