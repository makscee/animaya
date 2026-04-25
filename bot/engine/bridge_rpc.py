"""Engine-side Telegram bridge RPC: pairing code claim/revoke/regen + toggle + policy.

Thin wrapper over `bot.modules.telegram_bridge_state`. Response DTOs drop
any `bot_token` / `token` field (SEC-01).
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

# WR-07 (Phase 13 review): cap JSON body size even though we only listen on
# loopback. A misbehaving upstream route could otherwise OOM the engine.
_MAX_JSON_BYTES = 1_048_576  # 1 MiB


async def _read_json_bounded(request: Request) -> dict:
    cl_raw = request.headers.get("content-length") or "0"
    try:
        cl = int(cl_raw)
    except ValueError:
        cl = 0
    if cl > _MAX_JSON_BYTES:
        raise HTTPException(status_code=413, detail="payload too large")
    return await request.json()

from bot.modules import get_entry
from bot.modules.registry import read_registry, write_registry
from bot.modules.telegram_bridge_state import (
    generate_pairing_code,
    read_state,
    validate_bot_token,
    write_state,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _hub_dir() -> Path:
    raw = os.environ.get(
        "DATA_PATH",
        str(Path.home() / "hub" / "knowledge" / "animaya"),
    )
    return Path(raw)


def _bridge_module_dir(hub: Path) -> Path:
    entry = get_entry(hub, "telegram-bridge")
    if entry is None:
        raise HTTPException(status_code=404, detail="telegram-bridge not installed")
    return Path(entry["module_dir"])


@router.get("")
async def get_status() -> dict[str, Any]:
    """Return BridgeStatus shape consumed by dashboard.

    When telegram-bridge is not installed, returns a default
    `{enabled:false, policy:"owner_only", owner_id:null, claim_code_present:false}`
    with 200 so the dashboard can render the install/config UI instead of a 404.
    """
    hub = _hub_dir()
    entry = get_entry(hub, "telegram-bridge")
    if entry is None:
        return {
            "installed": False,
            "enabled": False,
            "policy": "owner_only",
            "owner_id": None,
            "claim_code_present": False,
        }
    module_dir = Path(entry["module_dir"])
    state = read_state(module_dir)
    owner_id = state.get("owner_id")
    return {
        "installed": True,
        "enabled": bool(state.get("enabled", False)),
        "policy": str(state.get("policy", "owner_only")),
        "owner_id": str(owner_id) if owner_id is not None else None,
        "claim_code_present": bool(state.get("pairing_code")),
    }


@router.post("/claim")
async def claim_code() -> dict[str, Any]:
    hub = _hub_dir()
    module_dir = _bridge_module_dir(hub)
    code, state = generate_pairing_code(module_dir)
    return {
        "code": str(code),
        "expires_at": state.get("pairing_expires_at"),
    }


@router.post("/revoke")
async def revoke_code() -> dict[str, Any]:
    hub = _hub_dir()
    module_dir = _bridge_module_dir(hub)
    state = read_state(module_dir)
    state.pop("pairing_code", None)
    state.pop("pairing_expires_at", None)
    state["claim_status"] = state.get("claim_status", "unclaimed")
    write_state(module_dir, state)
    return {"ok": True}


@router.post("/regen")
async def regen_code() -> dict[str, Any]:
    return await claim_code()


@router.put("/toggle")
async def toggle_bridge(request: Request) -> dict[str, Any]:
    hub = _hub_dir()
    module_dir = _bridge_module_dir(hub)
    body = await _read_json_bounded(request)
    enabled = bool(body.get("enabled", False))
    state = read_state(module_dir)
    state["enabled"] = enabled
    write_state(module_dir, state)
    return {"enabled": enabled}


@router.put("/policy")
async def set_policy(request: Request) -> dict[str, Any]:
    hub = _hub_dir()
    module_dir = _bridge_module_dir(hub)
    body = await _read_json_bounded(request)
    policy = str(body.get("policy", "") or "")
    if not policy:
        raise HTTPException(status_code=400, detail="policy required")
    state = read_state(module_dir)
    state["policy"] = policy
    write_state(module_dir, state)
    return {"policy": policy, "ok": True}


def _current_token(hub: Path) -> str:
    """Current bot token: registry config wins over env fallback."""
    entry = get_entry(hub, "telegram-bridge")
    if entry:
        tok = (entry.get("config") or {}).get("token") or ""
        if tok and tok != "pending":
            return str(tok)
    return os.environ.get("TELEGRAM_BOT_TOKEN", "")


@router.get("/identity")
async def get_identity() -> dict[str, Any]:
    """Call Telegram getMe with current token. Never leaks the token."""
    hub = _hub_dir()
    token = _current_token(hub)
    if not token:
        return {"ok": False, "username": None, "error": "No token configured"}
    ok, username, err = await validate_bot_token(token)
    return {"ok": ok, "username": username, "error": err}


@router.put("/token")
async def set_token(request: Request) -> dict[str, Any]:
    """Validate + persist a new bot token to registry. Reload required to take effect."""
    hub = _hub_dir()
    module_dir = _bridge_module_dir(hub)  # also 404s if not installed
    body = await _read_json_bounded(request)
    token = str(body.get("token", "") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    ok, username, err = await validate_bot_token(token)
    if not ok:
        return {"ok": False, "username": None, "error": err}
    reg = read_registry(hub)
    for entry in reg["modules"]:
        if entry.get("name") == "telegram-bridge":
            cfg = dict(entry.get("config") or {})
            cfg["token"] = token
            entry["config"] = cfg
            break
    write_registry(hub, reg)
    logger.info("telegram-bridge token updated; module_dir=%s username=%s", module_dir, username)
    return {"ok": True, "username": username, "error": None}
