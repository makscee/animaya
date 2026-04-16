"""FastAPI app factory for the Animaya web dashboard.

Exposes ``build_app(hub_dir)`` returning a configured FastAPI instance with
``/``, ``/login``, ``/logout`` and ``/static/*`` mounted.

Auth: token-based via ``DASHBOARD_TOKEN`` env var. ``GET /login?token=<value>``
issues a session cookie for the claimed owner_id (read from state.json) and
redirects to ``/``.
"""
from __future__ import annotations

import hmac
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
    clear_session_cookie_kwargs,
    issue_session_cookie,
    set_session_cookie_kwargs,
)
from bot.dashboard.deps import require_owner
from bot.modules.telegram_bridge_state import get_owner_id as _get_bridge_owner_id

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
    _register_bridge_routes_if_available(app)
    return app


# ── Auth routes (token login / logout) ────────────────────────────────
def _register_auth_routes(app: FastAPI) -> None:
    @app.get("/login", response_class=HTMLResponse, response_model=None)
    async def login(
        request: Request,
        token: str | None = None,
        error: str | None = None,
    ) -> HTMLResponse | RedirectResponse:
        expected = os.environ.get("DASHBOARD_TOKEN", "")
        hub_dir: Path = request.app.state.hub_dir
        owner_id = _get_bridge_owner_id(hub_dir)

        if token is not None:
            if not expected:
                return templates.TemplateResponse(
                    request, "login.html", {"error": "misconfigured"}, status_code=500
                )
            if not hmac.compare_digest(token, expected):
                return templates.TemplateResponse(
                    request, "login.html", {"error": "invalid"}, status_code=401
                )

            # Open-bootstrap (D-9.12): if no owner has claimed yet, issue a
            # session cookie with user_id=0 so the operator can reach the
            # install page. require_owner allows user_id=0 until an owner
            # claims; after claim, user_id must match owner_id.
            cookie_user_id = owner_id if owner_id is not None else 0
            cookie = issue_session_cookie(user_id=cookie_user_id, auth_date=int(time.time()))
            response = RedirectResponse("/", status_code=303)
            response.set_cookie(
                key=SESSION_COOKIE_NAME,
                value=cookie,
                **set_session_cookie_kwargs(),
            )
            return response

        return templates.TemplateResponse(request, "login.html", {"error": error})

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


def _register_bridge_routes_if_available(app: FastAPI) -> None:
    """Phase 9 bridge-specific routes: install dialog + claim-status stub."""
    try:
        from bot.dashboard import bridge_routes  # noqa: PLC0415
    except ImportError:
        return
    bridge_routes.register(app, templates)


__all__ = ["build_app", "templates"]
