"""In-process async job runner for module install/uninstall (Phase 5 DASH-05).

Single global :class:`asyncio.Lock` enforces one-at-a-time install/uninstall
semantics (Plan 05-05 D-08). A second concurrent call raises
:class:`InProgressError`; the route handler translates that to HTTP 409.

State retained in a module-level dict keyed by ``uuid4`` for 10 minutes
after completion (D-10). Blocking subprocess work (:func:`bot.modules.install`
and :func:`bot.modules.uninstall`) is dispatched via :func:`asyncio.to_thread`
to keep the event loop responsive (RESEARCH Pitfall 2).

Logs captured by attaching a module-local :class:`logging.Handler` to the
``bot.modules`` logger for the duration of each job; bounded to the last
200 records, with the last 50 surfaced in the failure fragment (D-09).

Rollback classification after a failed install: inspect
``manifest.owned_paths`` — any path still present under ``hub_dir``
=> ``rollback="dirty"`` with leaked relative paths; empty =>
``rollback="clean"``.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bot.modules as bot_modules
from bot.events import emit as events_emit
from bot.modules.lifecycle import _resolve_owned_path
from bot.modules.manifest import validate_manifest

logger = logging.getLogger(__name__)

# ── Tunables ─────────────────────────────────────────────────────────
_LOG_CAPACITY = 200
_TAIL_LINES = 50
_JOB_RETENTION = timedelta(minutes=10)

# ── Module state (process-local) ─────────────────────────────────────
_lock: asyncio.Lock = asyncio.Lock()
_jobs: dict[str, "JobState"] = {}


class InProgressError(RuntimeError):
    """Raised when install/uninstall is attempted while another is running."""


@dataclass
class JobState:
    """In-process state for a single install/uninstall job (D-10)."""

    id: str
    op: str                       # "install" | "uninstall"
    module: str
    status: str                   # "running" | "done" | "failed"
    started: datetime
    finished: datetime | None = None
    log_lines: list[str] = field(default_factory=list)
    error: str | None = None
    rollback: str | None = None    # "clean" | "dirty" | None (uninstall/ok)
    leaked_paths: list[str] = field(default_factory=list)


# ── Log capture ──────────────────────────────────────────────────────
class _JobLogHandler(logging.Handler):
    """Append formatted log records to a bounded list."""

    def __init__(self, target: list[str]) -> None:
        super().__init__(level=logging.INFO)
        self._target = target

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            self._target.append(self.format(record))
        except Exception:  # noqa: BLE001
            return
        if len(self._target) > _LOG_CAPACITY:
            del self._target[: len(self._target) - _LOG_CAPACITY]


def _install_handler(buffer: list[str]) -> logging.Handler:
    handler = _JobLogHandler(buffer)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    logging.getLogger("bot.modules").addHandler(handler)
    return handler


def _remove_handler(handler: logging.Handler) -> None:
    logging.getLogger("bot.modules").removeHandler(handler)


# ── Rollback classification ──────────────────────────────────────────
def _check_rollback(module_dir: Path, hub_dir: Path) -> tuple[str, list[str]]:
    """Classify rollback state after a failed install.

    Returns ``("clean", [])`` when no owned_paths remain, ``("dirty", [rel, …])``
    otherwise, or ``("unknown", [])`` if the manifest can't be read.
    """
    try:
        manifest = validate_manifest(module_dir)
    except Exception:  # noqa: BLE001
        return ("unknown", [])
    leaked: list[str] = []
    hub_resolved = hub_dir.resolve()
    for rel in manifest.owned_paths:
        try:
            if _resolve_owned_path(hub_resolved, rel).exists():
                leaked.append(rel)
        except ValueError:
            continue
    return ("dirty" if leaked else "clean", leaked)


# ── Retention / GC ───────────────────────────────────────────────────
def _gc() -> None:
    """Evict finished jobs older than ``_JOB_RETENTION``."""
    now = datetime.now(timezone.utc)
    stale = [
        jid for jid, j in _jobs.items()
        if j.finished is not None and (now - j.finished) > _JOB_RETENTION
    ]
    for jid in stale:
        _jobs.pop(jid, None)


def get_job(job_id: str) -> JobState | None:
    """Return the job or ``None`` if unknown/evicted. Runs GC opportunistically."""
    _gc()
    return _jobs.get(job_id)


# ── Public API: start_install / start_uninstall ──────────────────────
async def start_install(
    module_name: str,
    module_dir: Path,
    hub_dir: Path,
    *,
    config: dict | None = None,
) -> JobState:
    """Enqueue an install job. Raises :class:`InProgressError` if lock held."""
    if _lock.locked():
        raise InProgressError("another module operation in progress")
    job = JobState(
        id=uuid.uuid4().hex,
        op="install",
        module=module_name,
        status="running",
        started=datetime.now(timezone.utc),
    )
    _jobs[job.id] = job
    asyncio.create_task(_run_install(job, module_dir, hub_dir, config or {}))
    return job


async def start_uninstall(
    name: str,
    hub_dir: Path,
    module_dir: Path,
) -> JobState:
    """Enqueue an uninstall job. Raises :class:`InProgressError` if lock held."""
    if _lock.locked():
        raise InProgressError("another module operation in progress")
    job = JobState(
        id=uuid.uuid4().hex,
        op="uninstall",
        module=name,
        status="running",
        started=datetime.now(timezone.utc),
    )
    _jobs[job.id] = job
    asyncio.create_task(_run_uninstall(job, name, hub_dir, module_dir))
    return job


# ── Workers ──────────────────────────────────────────────────────────
async def _run_install(
    job: JobState,
    module_dir: Path,
    hub_dir: Path,
    config: dict,
) -> None:
    async with _lock:
        handler = _install_handler(job.log_lines)
        events_emit(
            "info", "modules.install",
            f"install started: {job.module}",
            job_id=job.id,
        )
        try:
            await asyncio.to_thread(
                bot_modules.install, module_dir, hub_dir, config=config,
            )
            job.status = "done"
            events_emit(
                "info", "modules.install",
                f"install done: {job.module}",
                job_id=job.id,
            )
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            job.rollback, job.leaked_paths = _check_rollback(module_dir, hub_dir)
            events_emit(
                "error", "modules.install",
                f"install failed: {job.module}",
                job_id=job.id,
                error=job.error,
                rollback=job.rollback,
                leaked_paths=job.leaked_paths,
                log=job.log_lines[-_TAIL_LINES:],
            )
        finally:
            _remove_handler(handler)
            job.finished = datetime.now(timezone.utc)
            _gc()


async def _run_uninstall(
    job: JobState,
    name: str,
    hub_dir: Path,
    module_dir: Path,
) -> None:
    async with _lock:
        handler = _install_handler(job.log_lines)
        events_emit(
            "info", "modules.uninstall",
            f"uninstall started: {name}",
            job_id=job.id,
        )
        try:
            await bot_modules.uninstall(name, hub_dir, module_dir)
            job.status = "done"
            events_emit(
                "info", "modules.uninstall",
                f"uninstall done: {name}",
                job_id=job.id,
            )
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = f"{type(exc).__name__}: {exc}"
            events_emit(
                "error", "modules.uninstall",
                f"uninstall failed: {name}",
                job_id=job.id,
                error=job.error,
                log=job.log_lines[-_TAIL_LINES:],
            )
        finally:
            _remove_handler(handler)
            job.finished = datetime.now(timezone.utc)
            _gc()


# ── Test hook (keeps _JOB_RETENTION rebindable) ──────────────────────
def _set_retention_for_tests(delta: timedelta) -> None:
    global _JOB_RETENTION
    _JOB_RETENTION = delta


__all__ = [
    "InProgressError",
    "JobState",
    "_set_retention_for_tests",
    "get_job",
    "start_install",
    "start_uninstall",
]
