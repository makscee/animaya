"""Animaya bot — entry point (Phase 8 cutover).

Validates environment, initialises data dir, rotates events log,
assembles CLAUDE.md, then runs the dashboard and all installed modules
through the Supervisor lifecycle. The Telegram bridge is now a module
— main.py has no direct dependency on bot.bridge.telegram.

Boot order (D-8.7):
    1. Validate env (CLAUDE_CODE_OAUTH_TOKEN required; TELEGRAM_BOT_TOKEN optional)
    2. rotate_events() + assemble_claude_md()
    3. Build dashboard FastAPI app + start uvicorn as asyncio task (dashboard first)
    4. migrate_bridge_rename(data_path) — one-shot D-8.5 migration
    5. _seed_telegram_bridge_token(data_path) — D-8.4 one-shot env→config.json seed
    6. Build AppContext + Supervisor; await supervisor.start_all(ctx)
    7. Wait on stop_event
    8. Shutdown: await supervisor.stop_all() → then stop uvicorn
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import uvicorn

from bot.engine import http as engine_http
from bot.events import emit as _emit
from bot.events import rotate as rotate_events
from bot.modules.assembler import assemble_claude_md
from bot.modules.context import AppContext
from bot.modules.registry import get_entry, migrate_bridge_rename, migrate_drop_memory
from bot.modules.supervisor import Supervisor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUIRED_ENV_VARS: tuple[str, ...] = (
    "CLAUDE_CODE_OAUTH_TOKEN",
    "SESSION_SECRET",
    "DASHBOARD_TOKEN",
    # Phase 13: next-auth JWT signing secret for the new Next.js dashboard.
    # `openssl rand -base64 32`.
    "AUTH_SECRET",
)
DEFAULT_DATA_PATH = str(Path.home() / "hub" / "knowledge" / "animaya")


# ── Token seed (D-8.4) ──────────────────────────────────────────────────────

def _seed_telegram_bridge_token(data_path: Path) -> None:
    """One-shot seed: write TELEGRAM_BOT_TOKEN env into module config.json.

    Runs at boot. If telegram-bridge is installed but its config.json has no
    token, and TELEGRAM_BOT_TOKEN is set in the environment, writes the token
    into the module's config.json atomically.

    After seed (or if config already has a token), the env var is ignored on
    all subsequent boots. Never auto-installs the bridge (D-8.4).

    Security: only the config.json PATH is logged — never the token value.

    Args:
        data_path: Hub data directory (contains registry.json).
    """
    entry = get_entry(data_path, "telegram-bridge")
    if entry is None:
        return  # bridge not installed — nothing to seed

    module_dir = Path(entry["module_dir"])
    config_path = module_dir / "config.json"
    existing: dict = {}
    if config_path.exists():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = {}

    if existing.get("token"):
        return  # already has token — env ignored

    env_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not env_token:
        return  # nothing to seed

    existing["token"] = env_token
    # Atomic write: sibling tmp file + replace (matches registry.py pattern).
    tmp = config_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    tmp.replace(config_path)
    # Log PATH only — never the token value (T-08-01 info-disclosure mitigation).
    logger.warning(
        "TELEGRAM_BOT_TOKEN seeded into %s; env var is deprecated and "
        "will be ignored after config.json has a token.",
        config_path,
    )


# ── Owner seed migration (D-9.13) ───────────────────────────────────────────

def _seed_owner_from_env(hub_dir: Path) -> None:
    """One-shot migration: if TELEGRAM_OWNER_ID is set and bridge has no owner, seed it.

    Runs at boot after token seed. If TELEGRAM_OWNER_ID is present in the environment
    and the bridge module exists but has no claimed owner, writes owner_id into state.json
    so existing deployments keep working without requiring a re-claim via pairing code.
    After seed, the env var is ignored on all subsequent boots.

    Security: skips if owner already exists (T-09-13 — existing owner never overwritten).

    Args:
        hub_dir: Hub data directory (contains registry.json).
    """
    raw = os.environ.get("TELEGRAM_OWNER_ID", "").strip()
    if not raw:
        return
    try:
        owner_id = int(raw.split(",")[0].strip())
    except ValueError:
        return
    from bot.modules.registry import get_entry  # noqa: PLC0415
    from bot.modules.telegram_bridge_state import (  # noqa: PLC0415
        get_owner_id,
        read_state,
        write_state,
    )
    entry = get_entry(hub_dir, "telegram-bridge")
    if entry is None:
        return
    module_dir = Path(entry["module_dir"])
    if get_owner_id(hub_dir) is not None:
        return  # already has an owner — never overwrite
    state = read_state(module_dir)
    state["claim_status"] = "claimed"
    state["owner_id"] = owner_id
    write_state(module_dir, state)
    logger.warning(
        "TELEGRAM_OWNER_ID seeded owner_id=%d into state.json; env var is deprecated",
        owner_id,
    )


# ── Event bus wrapper ────────────────────────────────────────────────────────

def _event_bus(level: str, source: str, message: str) -> None:
    """Thin wrapper over bot.events.emit for use as AppContext.event_bus."""
    try:
        _emit(level, source, message)
    except Exception:  # noqa: BLE001
        logger.debug("event_bus emit failed (level=%s source=%s)", level, source)


# ── Next.js dashboard subprocess (Phase 13) ─────────────────────────────────

def _start_dashboard() -> subprocess.Popen | None:
    """Launch the Next.js dashboard via `bun run start` in a subprocess.

    D-02 / D-04: Next.js owns the public HTTP surface on port 8090
    (`next start -p 8090 -H 127.0.0.1`). Returns None when Bun or the
    built artifact is unavailable so local dev (before `bun run build`)
    still boots — a warning is logged.

    Environment passthrough:
        ANIMAYA_ENGINE_URL → http://127.0.0.1:${ANIMAYA_ENGINE_PORT:-8091}
            Consumed by dashboard/lib/engine.server.ts (Plan 13-02).
    """
    bun = shutil.which("bun")
    cwd = str(Path(__file__).resolve().parent.parent / "dashboard")
    if bun is None or not (Path(cwd) / ".next").is_dir():
        logger.warning("dashboard not built; skipping Next.js launch (cwd=%s)", cwd)
        return None
    env = os.environ.copy()
    engine_port = env.get("ANIMAYA_ENGINE_PORT", "8091")
    env.setdefault("ANIMAYA_ENGINE_URL", f"http://127.0.0.1:{engine_port}")
    logger.info("Starting Next.js dashboard via `bun run start` (cwd=%s)", cwd)
    return subprocess.Popen([bun, "run", "start"], cwd=cwd, env=env)


def _stop_dashboard(proc: subprocess.Popen | None) -> None:
    """Gracefully stop the Next.js subprocess; fall back to kill on timeout."""
    if proc is None or proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        logger.warning("Next.js dashboard did not terminate in 10s; killing")
        proc.kill()


# ── Main entry point ─────────────────────────────────────────────────────────

def main() -> None:
    """Entry point: validate env, init data dir, rotate events, assemble
    CLAUDE.md, then run supervisor + uvicorn in one event loop."""
    for var in REQUIRED_ENV_VARS:
        if not os.environ.get(var):
            logger.error("%s not set", var)
            sys.exit(1)

    data_path = Path(os.environ.get("DATA_PATH", DEFAULT_DATA_PATH))
    data_path.mkdir(parents=True, exist_ok=True)
    logger.info("Data path: %s", data_path)

    # Rotate events log at startup (D-21).
    try:
        rotate_events()
    except Exception:  # noqa: BLE001 — never fail startup on rotate
        logger.exception("events.log rotation failed")

    # Assemble CLAUDE.md before starting modules.
    assemble_claude_md(data_path)

    logger.info("Animaya starting dashboard + module supervisor")
    try:
        asyncio.run(_run(data_path))
    except KeyboardInterrupt:
        logger.info("Shutdown via KeyboardInterrupt")


async def _run(data_path: Path) -> None:
    """D-8.7 boot order: dashboard first, supervisor second, clean shutdown.

    Dashboard starts before supervisor so a tokenless/bridgeless boot still
    brings the dashboard up (SC#1).
    """
    # ── Step 1: Build + start engine (Python) + Next.js dashboard subprocess ──
    # Phase 13: FastAPI is demoted to a loopback-only engine (D-01/D-03/D-08).
    # Next.js owns the public HTTP surface on port 8090. The legacy
    # bot.dashboard.app.build_app is deleted (D-08 big-bang) — the engine's
    # FastAPI app carries supervisor/ctx via app.state for module lifecycle.
    engine_app = engine_http.app
    engine_host = engine_http.get_host()            # hardcoded 127.0.0.1 (T-13-31)
    engine_port = engine_http.get_port()            # ANIMAYA_ENGINE_PORT, default 8091
    config = uvicorn.Config(
        engine_http.app,
        host=engine_host,
        port=engine_port,
        proxy_headers=False,
        log_level="info",
    )
    server = uvicorn.Server(config)
    uvicorn_task = asyncio.create_task(server.serve(), name="uvicorn")
    logger.info("Engine serving at http://%s:%s (loopback only)", engine_host, engine_port)

    # Launch Next.js dashboard as a child process (D-02).
    dashboard_proc = _start_dashboard()

    # ── Step 2: One-shot migrations + token seed ──────────────────────────────
    migrate_bridge_rename(data_path)           # D-8.5: rename 'bridge' → 'telegram-bridge'
    migrate_drop_memory(data_path)             # 260416-ncp: memory folded into core
    _seed_telegram_bridge_token(data_path)     # D-8.4: env token → config.json (if needed)
    _seed_owner_from_env(data_path)            # D-9.13: one-shot owner migration from env

    # ── Step 3: Build context + start supervisor ──────────────────────────────
    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass  # Windows / constrained environments.

    ctx = AppContext(
        data_path=data_path,
        stop_event=stop_event,
        event_bus=_event_bus,
        dashboard_app=engine_app,
    )
    supervisor = Supervisor()
    engine_app.state.supervisor = supervisor
    # Expose AppContext for engine-driven install/uninstall flows that need
    # to start/stop modules at runtime (supervisor.start_module / stop_module).
    engine_app.state.ctx = ctx
    await supervisor.start_all(ctx)

    # ── Step 4: Wait for shutdown signal ─────────────────────────────────────
    await stop_event.wait()

    # ── Step 5: Shutdown — supervisor first, then engine, then Next.js ───────
    logger.info("Shutting down")
    await supervisor.stop_all()
    server.should_exit = True
    await uvicorn_task
    _stop_dashboard(dashboard_proc)


# ``assemble_claude_md`` is imported from ``bot.modules.assembler`` above.
# Re-exported here so ``from bot.main import assemble_claude_md`` keeps working
# (regression tests in tests/test_skeleton.py rely on this).
__all__ = [
    "DEFAULT_DATA_PATH",
    "REQUIRED_ENV_VARS",
    "assemble_claude_md",
    "main",
    "rotate_events",
    "_run",
    "_seed_owner_from_env",
    "_seed_telegram_bridge_token",
    "_start_dashboard",
    "_stop_dashboard",
]
