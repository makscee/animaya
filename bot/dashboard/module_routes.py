"""Module list + detail + install/uninstall + job status routes (Phase 5 DASH-04/05).

Auto-registered by :func:`bot.dashboard.app.build_app` via the
``_register_module_routes_if_available`` hook; exports a single
:func:`register(app, templates)` entry point.

Concurrency is delegated to :mod:`bot.dashboard.jobs` — a single global
:class:`asyncio.Lock` guarantees one install/uninstall at a time. On
conflict, we return HTTP 409 with the ``conflict_toast`` fragment so
HTMX swaps the message into ``#status-toast``.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.dashboard.deps import require_owner
from bot.dashboard.forms import coerce, render_fields, save_config, validate
from bot.dashboard.jobs import (
    InProgressError,
    get_job,
    start_install,
    start_uninstall,
)
from bot.dashboard.modules_view import all_cards, describe, module_dir_for
from bot.modules import get_entry
from bot.modules.manifest import validate_manifest
from bot.modules.telegram_bridge_state import redact_bridge_config

logger = logging.getLogger(__name__)


def register(app: FastAPI, templates: Jinja2Templates) -> None:
    """Attach /modules + /modules/{name} + install/uninstall + job routes."""
    hub_dir: Path = app.state.hub_dir

    def _conflict_toast(request: Request) -> HTMLResponse:
        resp = templates.TemplateResponse(
            request,
            "_fragments/conflict_toast.html",
            {
                "message": (
                    "Another module operation is in progress. "
                    "Wait for it to finish, then try again."
                ),
            },
        )
        resp.status_code = 409
        return resp

    @app.get("/modules", response_class=HTMLResponse, name="modules_list")
    async def modules_list(
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        installed, available = all_cards(hub_dir)
        return templates.TemplateResponse(
            request,
            "modules.html",
            {
                "installed": installed,
                "available": available,
                "nav_active": "modules",
            },
        )

    @app.get("/modules/{name}", response_class=HTMLResponse, name="module_detail")
    async def module_detail(
        name: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        card = describe(hub_dir, name)
        if card is None:
            raise HTTPException(
                status_code=404, detail=f"module {name!r} not found",
            )
        return templates.TemplateResponse(
            request,
            "module_detail.html",
            {"card": card, "nav_active": "modules"},
        )

    @app.post(
        "/modules/{name}/install",
        response_class=HTMLResponse,
        name="module_install",
    )
    async def install_endpoint(
        name: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        card = describe(hub_dir, name)
        if card is None:
            raise HTTPException(
                status_code=404, detail=f"module {name!r} not found",
            )
        # Phase 9: telegram-bridge requires a validated token BEFORE install.
        # Intercept the generic install button and render the token form instead.
        if name == "telegram-bridge":
            return templates.TemplateResponse(
                request,
                "_fragments/bridge_install_form.html",
                {"has_token": False, "name": name},
            )
        try:
            job = await start_install(name, module_dir_for(name), hub_dir)
        except InProgressError:
            return _conflict_toast(request)
        return templates.TemplateResponse(
            request,
            "_fragments/module_card_running.html",
            {"card": card, "job": job},
        )

    @app.post(
        "/modules/{name}/uninstall",
        response_class=HTMLResponse,
        name="module_uninstall",
    )
    async def uninstall_endpoint(
        name: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        card = describe(hub_dir, name)
        if card is None:
            raise HTTPException(
                status_code=404, detail=f"module {name!r} not found",
            )
        try:
            job = await start_uninstall(name, hub_dir, module_dir_for(name))
        except InProgressError:
            return _conflict_toast(request)
        return templates.TemplateResponse(
            request,
            "_fragments/module_card_running.html",
            {"card": card, "job": job},
        )

    @app.get(
        "/modules/{name}/config",
        response_class=HTMLResponse,
        name="module_config",
    )
    async def config_get(
        name: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        entry = get_entry(hub_dir, name)
        if entry is None:
            raise HTTPException(
                status_code=404, detail=f"module {name!r} not installed",
            )
        manifest = validate_manifest(module_dir_for(name))
        schema = manifest.config_schema
        if not schema or not schema.get("properties"):
            # telegram-bridge: no schema — render install form or "no config" msg
            if name == "telegram-bridge":
                safe_entry = redact_bridge_config(entry)
                has_token = safe_entry["config"].get("has_token", False)
                return templates.TemplateResponse(
                    request,
                    "_fragments/bridge_install_form.html",
                    {"has_token": has_token, "name": name},
                )
            return templates.TemplateResponse(
                request,
                "_fragments/config_form_saved.html",
                {
                    "name": name,
                    "fields": [],
                    "no_schema": True,
                },
            )
        # Redact token from config before passing to render_fields (T-09-01)
        raw_config = entry.get("config") or {}
        if name == "telegram-bridge":
            raw_config = redact_bridge_config({"config": raw_config})["config"]
        fields = render_fields(schema, raw_config)
        return templates.TemplateResponse(
            request,
            "_fragments/config_form.html",
            {
                "name": name,
                "fields": fields,
                "field_errors": {},
                "summary_error": None,
            },
        )

    @app.post(
        "/modules/{name}/config",
        response_class=HTMLResponse,
        name="module_config_save",
    )
    async def config_post(
        name: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        entry = get_entry(hub_dir, name)
        if entry is None:
            raise HTTPException(
                status_code=404, detail=f"module {name!r} not installed",
            )
        manifest = validate_manifest(module_dir_for(name))
        schema = manifest.config_schema or {}
        form = await request.form()
        form_data = {k: str(v) for k, v in form.multi_items()}
        payload, coerce_errors = coerce(form_data, schema)
        schema_errors = validate(payload, schema) if not coerce_errors else {}
        errors = {**coerce_errors, **schema_errors}
        if errors:
            fields = render_fields(
                schema, {**(entry.get("config") or {}), **payload},
            )
            return templates.TemplateResponse(
                request,
                "_fragments/config_form.html",
                {
                    "name": name,
                    "fields": fields,
                    "field_errors": errors,
                    "summary_error": (
                        f"Please fix {len(errors)} errors below."
                    ),
                },
            )
        save_config(hub_dir, name, payload)
        fresh = get_entry(hub_dir, name) or entry
        fields = render_fields(schema, fresh.get("config") or {})
        return templates.TemplateResponse(
            request,
            "_fragments/config_form_saved.html",
            {
                "name": name,
                "fields": fields,
                "field_errors": {},
                "summary_error": None,
            },
        )

    @app.get(
        "/modules/{name}/job/{job_id}",
        response_class=HTMLResponse,
        name="module_job_status",
    )
    async def job_status(
        name: str,
        job_id: str,
        request: Request,
        _uid: int = Depends(require_owner),
    ):
        job = get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job expired or unknown")
        card = describe(hub_dir, name)  # may be None after a successful uninstall
        if job.status == "running":
            return templates.TemplateResponse(
                request,
                "_fragments/module_card_running.html",
                {"card": card, "job": job},
            )
        if job.status == "done":
            return templates.TemplateResponse(
                request,
                "_fragments/module_card.html",
                {"card": card, "job_done": True, "job": job},
            )
        # failed
        return templates.TemplateResponse(
            request,
            "_fragments/module_card_failed.html",
            {
                "card": card,
                "job": job,
                "log_tail": job.log_lines[-50:],
            },
        )


__all__ = ["register"]
