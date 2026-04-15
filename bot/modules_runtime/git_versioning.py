"""git-versioning runtime: asyncio commit loop + single-committer Lock.

Implements GITV-01 (interval auto-commit), GITV-02 (asyncio.Lock single
committer), GITV-03 (path-scoped `git add -- knowledge/`).

Critical invariants:
- Uses asyncio.create_subprocess_exec (NOT blocking subprocess.run) — does
  not block the event loop during git operations.
- Path-scoped git operations via `-- knowledge/` ensure only declared scope
  is touched (Pitfall: `git add -A` would pick up unrelated files).
- In-process asyncio.Lock is sufficient because the bot is the only writer
  to ~/hub/knowledge/ by design (D-12); no out-of-process committer.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────
HUB_ROOT: Path = Path.home() / "hub"
KNOWLEDGE_REL = "knowledge/"  # path-scope for git operations

# ── Single-committer lock (D-12) ─────────────────────────────────────
_COMMIT_LOCK = asyncio.Lock()


# ── git CLI helpers (non-blocking) ───────────────────────────────────
async def _run_git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    """Run `git -C repo_root *args` non-blocking. Returns (rc, stdout, stderr)."""
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Animaya Bot",
        "GIT_AUTHOR_EMAIL": "bot@animaya.local",
        "GIT_COMMITTER_NAME": "Animaya Bot",
        "GIT_COMMITTER_EMAIL": "bot@animaya.local",
    }
    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(repo_root),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=30)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise
    return proc.returncode, stdout_b.decode(errors="replace"), stderr_b.decode(errors="replace")


# ── Public API ───────────────────────────────────────────────────────
async def commit_if_changed(repo_root: Path | None = None) -> bool:
    """Commit any pending changes under `knowledge/`. Returns True if commit made.

    Skips entirely when no diff (no empty commit). Wrapped in _COMMIT_LOCK
    so concurrent calls serialize (D-12).
    """
    repo = (repo_root or HUB_ROOT).resolve()
    async with _COMMIT_LOCK:
        if not (repo / ".git").is_dir():
            logger.warning("git-versioning: %s is not a git repo; skipping", repo)
            return False

        # Path-scoped status — ONLY knowledge/ counts (GITV-03)
        rc, status, err = await _run_git(repo, "status", "--porcelain", "--", KNOWLEDGE_REL)
        if rc != 0:
            logger.error("git status failed (rc=%d): %s", rc, err.strip())
            return False
        if not status.strip():
            return False

        rc, _, err = await _run_git(repo, "add", "--", KNOWLEDGE_REL)
        if rc != 0:
            logger.error("git add failed (rc=%d): %s", rc, err.strip())
            return False

        # Confirm there is something staged for knowledge/ (defensive against
        # adds that were no-ops, e.g. only-permissions changes)
        rc, cached, err = await _run_git(
            repo, "diff", "--cached", "--name-only", "--", KNOWLEDGE_REL
        )
        if rc != 0 or not cached.strip():
            return False

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        msg = f"animaya: auto-commit {ts}"
        rc, _, err = await _run_git(repo, "commit", "-q", "-m", msg)
        if rc != 0:
            logger.error("git commit failed (rc=%d): %s", rc, err.strip())
            return False
        logger.info("committed knowledge/ changes at %s", ts)
        return True


async def commit_loop(
    interval: int = 300,
    repo_root: Path | None = None,
) -> None:
    """Background commit task. Tick every `interval` seconds; final commit on cancel."""
    repo = repo_root or HUB_ROOT
    logger.info("git auto-commit loop started (interval=%ds, repo=%s)", interval, repo)
    try:
        while True:
            await asyncio.sleep(interval)
            try:
                await commit_if_changed(repo)
            except Exception:
                logger.exception("auto-commit tick failed")
    except asyncio.CancelledError:
        logger.info("git auto-commit loop stopping; final commit attempt")
        try:
            await commit_if_changed(repo)
        except Exception:
            logger.exception("final commit failed")
        raise
