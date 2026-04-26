"""Loopback-only FastAPI engine.

Bound to 127.0.0.1:${ANIMAYA_ENGINE_PORT:-8091}. Not reachable outside
the container — Next.js route handlers proxy here over localhost.
Therefore: no CSRF, no auth, no cookies. Trust = loopback.

Threat mitigations:
- T-13-30 (spoofed non-loopback caller): loopback-only middleware → 403
- T-13-31 (accidental 0.0.0.0 bind): `get_host()` returns "127.0.0.1"; callers
  pass it straight to uvicorn.
- T-13-33 (bot_token leak): handled in modules_rpc / bridge_rpc DTOs.
"""
from __future__ import annotations

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from bot.engine import bridge_rpc, lang_bust, modules_rpc
from bot.engine.chat_stream import stream_chat

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _allowed_hosts() -> frozenset[str]:
    """Runtime-resolved allowlist. Tests set `ANIMAYA_ENGINE_ALLOW_TESTCLIENT=1`
    to permit Starlette's synthetic "testclient" source host.
    """
    allow = set(_LOOPBACK_HOSTS)
    if os.environ.get("ANIMAYA_ENGINE_ALLOW_TESTCLIENT") == "1":
        allow.add("testclient")
    return frozenset(allow)

app = FastAPI(title="animaya-engine", openapi_url=None, docs_url=None, redoc_url=None)


@app.middleware("http")
async def loopback_only(request: Request, call_next):
    """Reject any request whose client.host is not loopback. 403 otherwise."""
    client_host = request.client.host if request.client else ""
    if client_host not in _allowed_hosts():
        return JSONResponse(
            status_code=403,
            content={"detail": "loopback only"},
        )
    return await call_next(request)


@app.post("/engine/chat")
async def engine_chat(req: Request) -> StreamingResponse:
    body = await req.json()
    return StreamingResponse(
        stream_chat(body),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-store",
            "X-Accel-Buffering": "no",
        },
    )


app.include_router(modules_rpc.router, prefix="/engine/modules")
app.include_router(bridge_rpc.router, prefix="/engine/bridge")
app.include_router(lang_bust.router, prefix="/internal")


def get_port() -> int:
    """Return engine port from env (default 8091)."""
    return int(os.environ.get("ANIMAYA_ENGINE_PORT", "8091"))


def get_host() -> str:
    """Engine always binds loopback. Hardcoded — not configurable by env."""
    return "127.0.0.1"
