"""Dashboard authentication — token-based for now.

Supports DASHBOARD_TOKEN env var for simple auth.
Telegram Login Widget auth to be added in Phase 2.
"""
from __future__ import annotations

import os
from functools import wraps

from fastapi import Request
from fastapi.responses import JSONResponse

DASHBOARD_TOKEN = os.environ.get("DASHBOARD_TOKEN", "")


def require_auth(func):
    """Decorator to require dashboard authentication."""

    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not DASHBOARD_TOKEN:
            return await func(request, *args, **kwargs)

        token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if not token:
            token = request.query_params.get("token", "")

        if token != DASHBOARD_TOKEN:
            return JSONResponse({"error": "unauthorized"}, status_code=401)

        return await func(request, *args, **kwargs)

    return wrapper
