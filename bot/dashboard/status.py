"""Bot runtime status probe for the dashboard (Phase 5 D-17 / DASH-03).

Shells out to ``systemctl --user is-active animaya``. Falls back to
``unknown`` in dev environments where ``systemctl`` is absent or the
unit is not installed — the dashboard must never crash on a missing
probe.

Env:
    ANIMAYA_SYSTEMD_UNIT (default ``animaya``) — unit name to probe.
    ANIMAYA_SYSTEMD_SCOPE (default ``--user``) — scope flag; empty
        string switches to system-level systemctl.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bot.events import tail as events_tail
from bot.modules import list_installed

logger = logging.getLogger(__name__)

# ── Config ───────────────────────────────────────────────────────────
SYSTEMD_UNIT: str = os.environ.get("ANIMAYA_SYSTEMD_UNIT", "animaya")
SYSTEMD_SCOPE: str = os.environ.get("ANIMAYA_SYSTEMD_SCOPE", "--user")

# systemctl is-active → UI label + dot class. Only keys in here are
# considered "known" states; anything else collapses to "unknown".
STATUS_LABELS: dict[str, tuple[str, str]] = {
    "active":     ("Running",  "dot-green"),
    "activating": ("Starting", "dot-warn"),
    "inactive":   ("Stopped",  "dot-red"),
    "failed":     ("Failed",   "dot-red"),
    "unknown":    ("Unknown",  "dot-gray"),
}


# ── Public API ───────────────────────────────────────────────────────
def is_running() -> str:
    """Return ``systemctl is-active`` output, or ``"unknown"`` on failure.

    Uses a 2-second timeout (T-05-04-04); a missing ``systemctl`` binary
    returns ``"unknown"`` without shell-out (T-05-04-06: list-form args,
    never ``shell=True``).
    """
    if shutil.which("systemctl") is None:
        return "unknown"
    cmd = ["systemctl"]
    if SYSTEMD_SCOPE:
        cmd.append(SYSTEMD_SCOPE)
    cmd.extend(["is-active", SYSTEMD_UNIT])
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("systemctl probe failed: %s", exc)
        return "unknown"
    out = (result.stdout or "").strip()
    return out if out in STATUS_LABELS else "unknown"


def _events_today_count() -> int:
    """Count events emitted within the last 24 hours.

    Reads up to the last 10k events (matches rotate cap from Plan 05-01).
    Malformed timestamps are skipped; function never raises.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    count = 0
    for rec in events_tail(10_000):
        ts = rec.get("ts")
        if not isinstance(ts, str):
            continue
        try:
            parsed = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            # Treat naive as UTC to avoid comparison errors.
            parsed = parsed.replace(tzinfo=timezone.utc)
        if parsed >= cutoff:
            count += 1
    return count


def recent_stats(hub_dir: Path) -> dict:
    """Bundle status + counts for the status-strip fragment.

    Returns a dict with keys: ``status``, ``status_label``, ``status_dot``,
    ``modules_installed``, ``events_today``.
    """
    status = is_running()
    label, dot = STATUS_LABELS.get(status, STATUS_LABELS["unknown"])
    return {
        "status": status,
        "status_label": label,
        "status_dot": dot,
        "modules_installed": len(list_installed(Path(hub_dir))),
        "events_today": _events_today_count(),
    }


__all__ = ["is_running", "recent_stats", "STATUS_LABELS"]
