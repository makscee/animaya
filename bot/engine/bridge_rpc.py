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
from bot.modules.telegram_bridge_state import (
    generate_pairing_code,
    read_state,
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
