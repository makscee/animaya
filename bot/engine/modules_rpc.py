"""Engine-side modules RPC: /engine/modules + install/uninstall/config.

Thin wrapper over existing business logic in `bot.modules.*` and
`bot.engine.modules_view`. No cookies, no auth — trusts loopback.
DTOs drop any `bot_token` field (T-13-33 / SEC-01).
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from bot.engine.modules_view import all_cards, describe, module_dir_for
from bot.modules import get_entry
from bot.modules.telegram_bridge_state import redact_bridge_config

logger = logging.getLogger(__name__)

router = APIRouter()


def _hub_dir() -> Path:
    """Resolve hub/data dir from env; tests set `DATA_PATH`."""
    raw = os.environ.get(
        "DATA_PATH",
        str(Path.home() / "hub" / "knowledge" / "animaya"),
    )
    return Path(raw)


_SECRET_KEY_RE = re.compile(
    r"(token|secret|api_key|apikey|password|credential|oauth)",
    re.IGNORECASE,
)


def _scrub_mapping(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact any key that looks like a secret.

    CR-02 (Phase 13 review): the old implementation only stripped
    top-level `bot_token` / `token` and delegated the `config` sub-object
    to telegram-bridge-specific logic. Module authors adding new credential
    shapes (e.g., `google_api_key`, `auth.token`) would leak to the browser
    because `ModuleConfigSchema = z.record(z.string(), z.unknown())` does
    not strip arbitrary keys. This walker generalises to any nesting depth.
    """
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(k, str) and _SECRET_KEY_RE.search(k):
            out[k] = "[REDACTED]"
        elif isinstance(v, dict):
            out[k] = _scrub_mapping(v)
        elif isinstance(v, list):
            out[k] = [_scrub_mapping(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


def _strip_secrets(entry: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive fields from a module-entry DTO before HTTP response.

    Applies the generic key-regex scrubber at every nesting level, then
    also runs the legacy telegram-bridge redactor for any bridge-specific
    keys it knows about (belt + braces).
    """
    safe = _scrub_mapping(dict(entry))
    cfg = safe.get("config")
    if isinstance(cfg, dict):
        safe["config"] = redact_bridge_config(cfg)
    return safe


@router.get("")
async def list_modules() -> dict[str, Any]:
    hub = _hub_dir()
    installed, available = all_cards(hub)
    items = []
    for card in list(installed) + list(available):
        items.append({
            "name": card.name,
            "version": card.version,
            "description": card.description,
            "installed": card.installed,
            "has_config": card.has_config,
        })
    return {"modules": items}


@router.post("/{name}/install")
async def install_module(name: str, request: Request) -> dict[str, Any]:
    hub = _hub_dir()
    card = describe(hub, name)
    if card is None:
        raise HTTPException(status_code=404, detail=f"module {name!r} not found")
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    from bot.engine.modules_jobs import InProgressError, start_install

    try:
        job = await start_install(
            name,
            module_dir_for(name),
            hub,
            config=body.get("config") or {},
        )
    except InProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "job_id": getattr(job, "id", None)}


@router.post("/{name}/uninstall")
async def uninstall_module(name: str, request: Request) -> dict[str, Any]:
    hub = _hub_dir()
    card = describe(hub, name)
    if card is None:
        raise HTTPException(status_code=404, detail=f"module {name!r} not found")
    from bot.engine.modules_jobs import InProgressError, start_uninstall

    app_state = getattr(request.app.state, "ctx", None)
    try:
        job = await start_uninstall(
            name,
            hub,
            module_dir_for(name),
            app=request.app if app_state is not None else None,
        )
    except InProgressError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True, "job_id": getattr(job, "id", None)}


@router.put("/{name}/config")
async def update_config(name: str, request: Request) -> dict[str, Any]:
    hub = _hub_dir()
    entry = get_entry(hub, name)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"module {name!r} not installed")
    body = await request.json()
    from bot.engine.modules_forms import save_config

    save_config(hub, name, body)
    updated = get_entry(hub, name) or {}
    return {"ok": True, "config": _strip_secrets(updated)}
