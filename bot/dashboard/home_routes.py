"""Home page and HTMX fragment endpoints (Phase 5 DASH-03).

Registered by :func:`bot.dashboard.app.build_app` via
``_register_home_routes_if_available``. Removes the placeholder ``/``
route that build_app installs (name ``home_placeholder``) and replaces
it with the real home view.

Routes:
    GET /                     → home.html (status strip + activity + errors)
    GET /fragments/status     → _fragments/status_strip.html  (poll every 5s)
    GET /fragments/activity   → _fragments/activity_feed.html (poll every 5s)
    GET /fragments/errors     → _fragments/error_feed.html    (poll every 5s)

All routes are guarded by :func:`bot.dashboard.deps.require_owner`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.dashboard.deps import require_owner
from bot.dashboard.status import recent_stats
from bot.events import tail as events_tail

logger = logging.getLogger(__name__)

_RECENT_LIMIT = 50


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    """Install home + fragment routes; idempotent."""
    _ensure_relative_time_filter(templates)
    _remove_route(app, name="home_placeholder")

    hub_dir: Path = app.state.hub_dir

    @app.get("/", response_class=HTMLResponse, name="home")
    async def home(
        request: Request,
        user_id: int = Depends(require_owner),
    ) -> HTMLResponse:
        events = events_tail(_RECENT_LIMIT)
        errors = [e for e in events if e.get("level") == "error"]
        return templates.TemplateResponse(
            request,
            "home.html",
            {
                "stats": recent_stats(hub_dir),
                "events": events,
                "errors": errors,
                "nav_active": "home",
                "user_id": user_id,
            },
        )

    @app.get(
        "/fragments/status",
        response_class=HTMLResponse,
        name="fragments_status",
    )
    async def fragments_status(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "_fragments/status_strip.html",
            {"stats": recent_stats(hub_dir)},
        )

    @app.get(
        "/fragments/activity",
        response_class=HTMLResponse,
        name="fragments_activity",
    )
    async def fragments_activity(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "_fragments/activity_feed.html",
            {"events": events_tail(_RECENT_LIMIT)},
        )

    @app.get(
        "/fragments/errors",
        response_class=HTMLResponse,
        name="fragments_errors",
    )
    async def fragments_errors(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        all_events = events_tail(_RECENT_LIMIT)
        errors = [e for e in all_events if e.get("level") == "error"]
        return templates.TemplateResponse(
            request,
            "_fragments/error_feed.html",
            {"events": errors},
        )


# ── Helpers ─────────────────────────────────────────────────────────
def _remove_route(app: FastAPI, *, name: str) -> None:
    """Drop any route whose ``.name`` matches ``name`` (idempotent)."""
    app.router.routes = [
        r for r in app.router.routes if getattr(r, "name", None) != name
    ]


def _ensure_relative_time_filter(templates: Jinja2Templates) -> None:
    """Add the ``relative_time`` Jinja filter if absent. Idempotent."""
    env = templates.env
    if "relative_time" in env.filters:
        return

    def _rel(ts: str) -> str:
        try:
            parsed = datetime.fromisoformat(ts)
        except (TypeError, ValueError):
            return ""
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        delta_s = int((now - parsed).total_seconds())
        if delta_s < 0:
            return "just now"
        if delta_s < 60:
            return f"{delta_s}s ago"
        if delta_s < 3600:
            return f"{delta_s // 60}m ago"
        if delta_s < 86400:
            return f"{delta_s // 3600}h ago"
        return f"{delta_s // 86400}d ago"

    env.filters["relative_time"] = _rel


__all__ = ["register"]
