"""FastAPI app factory for the Animaya web dashboard (Phase 5).

Exposes ``build_app(hub_dir)`` returning a configured FastAPI instance with
``/``, ``/login``, ``/auth/telegram``, ``/logout`` and ``/static/*`` mounted.

Home (``/``) is owned by Plan 05-04 (home routes), ``/modules`` by Plan 05-05,
and config endpoints by Plan 05-06 — each registered via try/except ImportError
guards so the shell stays usable in isolation. The placeholder ``/`` route here
is overwritten when ``bot.dashboard.home_routes`` becomes available.

Module-level ``templates`` is exported for downstream plans to render fragments
without rebuilding the Jinja2Templates instance.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from bot.dashboard.auth import (
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
    clear_session_cookie_kwargs,
    issue_session_cookie,
    verify_telegram_payload,
)
from bot.dashboard.deps import _owner_ids, require_owner

logger = logging.getLogger(__name__)

# ── Module constants ─────────────────────────────────────────────────
TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


# ── App factory ──────────────────────────────────────────────────────
def build_app(hub_dir: Path) -> FastAPI:
    """Return a configured FastAPI instance for the dashboard.

    Args:
        hub_dir: path to ``~/hub/knowledge/animaya`` (or a temp dir in tests).
            Stored on ``app.state.hub_dir`` for downstream plans.

    Returns:
        FastAPI app with auth + home placeholder + static mount registered.
        OpenAPI docs are disabled (T-05-03-05).
    """
    app = FastAPI(
        title="Animaya Dashboard",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.hub_dir = Path(hub_dir).resolve()
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    _register_auth_routes(app)
    _register_home_placeholder(app)
    _register_home_routes_if_available(app)
    _register_module_routes_if_available(app)
    return app


# ── Auth routes (login / callback / logout) ──────────────────────────
def _register_auth_routes(app: FastAPI) -> None:
    @app.get("/login", response_class=HTMLResponse)
    async def login(request: Request, error: str | None = None) -> HTMLResponse:
        bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "").strip()
        # If env var is missing, override the error message so users see the
        # canonical "misconfigured" copy regardless of any ?error= query.
        effective_error = error if bot_username else "misconfigured"
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "bot_username": bot_username,
                "error": effective_error,
            },
        )

    @app.post("/auth/telegram")
    async def auth_telegram(request: Request) -> RedirectResponse:
        form = await request.form()
        # form.multi_items() returns list[tuple[str, str|UploadFile]]; cast to str.
        payload: dict[str, str] = {k: str(v) for k, v in form.multi_items()}
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not verify_telegram_payload(payload, bot_token):
            # Distinguish stale (auth_date too old) vs invalid (HMAC mismatch).
            try:
                age = int(time.time()) - int(payload.get("auth_date", 0))
            except (TypeError, ValueError):
                age = 0
            reason = "stale" if age > 86400 else "invalid"
            return RedirectResponse(f"/login?error={reason}", status_code=303)

        try:
            user_id = int(payload["id"])
        except (KeyError, TypeError, ValueError):
            return RedirectResponse("/login?error=invalid", status_code=303)

        if user_id not in _owner_ids():
            return RedirectResponse("/login?error=forbidden", status_code=303)

        try:
            auth_date = int(payload.get("auth_date", time.time()))
        except (TypeError, ValueError):
            auth_date = int(time.time())

        cookie = issue_session_cookie(
            user_id=user_id,
            auth_date=auth_date,
            hash_=payload.get("hash", ""),
        )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=cookie,
            max_age=SESSION_MAX_AGE_SECONDS,
            httponly=True,
            samesite="lax",
            secure=True,
            path="/",
        )
        return response

    @app.get("/logout")
    async def logout() -> RedirectResponse:
        resp = RedirectResponse("/login", status_code=303)
        resp.delete_cookie(**clear_session_cookie_kwargs())
        return resp


# ── Home placeholder (overwritten by Plan 05-04) ─────────────────────
def _register_home_placeholder(app: FastAPI) -> None:
    @app.get("/", response_class=HTMLResponse, name="home_placeholder")
    async def home(
        request: Request, user_id: int = Depends(require_owner)
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "_home_placeholder.html",
            {
                "user_id": user_id,
                "nav_active": "home",
            },
        )


# ── Optional plan hooks ──────────────────────────────────────────────
def _register_home_routes_if_available(app: FastAPI) -> None:
    """Plan 05-04 will provide ``home_routes.register(app, templates)``."""
    try:
        from bot.dashboard import home_routes  # noqa: PLC0415
    except ImportError:
        return
    home_routes.register(app, templates)


def _register_module_routes_if_available(app: FastAPI) -> None:
    """Plan 05-05 will provide ``module_routes.register(app, templates)``."""
    try:
        from bot.dashboard import module_routes  # noqa: PLC0415
    except ImportError:
        return
    module_routes.register(app, templates)


__all__ = ["build_app", "templates"]
