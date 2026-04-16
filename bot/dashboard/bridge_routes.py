"""Bridge-specific dashboard routes (Phase 9, Plans 01–02).

Mounts token install endpoint and pairing-code FSM endpoints.
Auto-registered by :func:`bot.dashboard.app.build_app` via
``_register_bridge_routes_if_available`` hook; exports a single
:func:`register(app, templates)` entry point.

Security:
    - Token is validated via Telegram getMe before any state is written (T-09-03)
    - Token value is never logged; only the bot username is logged (T-09-02)
    - Token input field uses type="password" to prevent shoulder surfing (T-09-05)
    - Pairing code plaintext never stored to disk; only returned once in HTTP response (T-09-08)
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.dashboard.deps import require_owner
from bot.dashboard.jobs import InProgressError, start_install
from bot.modules.telegram_bridge_state import (
    check_expiry,
    generate_pairing_code,
    read_state,
    validate_bot_token,
    write_state,
)

logger = logging.getLogger(__name__)


def register(app: FastAPI, templates: Jinja2Templates) -> None:  # noqa: ARG001
    """Attach bridge-specific routes to the dashboard app.

    Args:
        app: FastAPI application instance with app.state.hub_dir set.
        templates: Jinja2Templates instance (reserved for future fragment use).
    """

    @app.post(
        "/api/modules/telegram-bridge/install",
        response_class=HTMLResponse,
        name="bridge_install",
    )
    async def install_bridge(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Validate bot token via Telegram getMe, then install the bridge.

        On success: writes config.json, initialises state.json (unclaimed),
        enqueues install job, returns HX-Redirect to the config page.
        On failure: returns an error HTML fragment with no state written.

        Security: token value is never logged or included in responses (T-09-02).
        """
        # Accept both JSON and form-urlencoded bodies. HTMX defaults to
        # form-urlencoded; only posts JSON when the json-enc extension is
        # loaded. Parse by Content-Type so either transport works.
        content_type = request.headers.get("content-type", "")
        if "application/json" in content_type:
            body = await request.json()
            token: str = (body.get("token") or "").strip()
        else:
            form = await request.form()
            token = (form.get("token") or "").strip()

        if not token:
            return HTMLResponse(
                '<div class="error" role="alert">Token is required.</div>'
            )

        ok, username, error = await validate_bot_token(token)

        if not ok:
            if error == "Could not reach Telegram API":
                return HTMLResponse(
                    '<div class="error" role="alert">'
                    "Could not reach Telegram API. Check your connection and try again."
                    "</div>"
                )
            return HTMLResponse(
                '<div class="error" role="alert">'
                "Invalid bot token. Check the token from @BotFather and try again."
                "</div>"
            )

        # Valid token — persist config.json atomically
        hub_dir: Path = request.app.state.hub_dir
        module_dir = hub_dir / "modules" / "telegram-bridge"
        module_dir.mkdir(parents=True, exist_ok=True)

        config_path = module_dir / "config.json"
        tmp = config_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps({"token": token}, indent=2), encoding="utf-8")
        tmp.replace(config_path)

        # Log only the bot username — never the token value (D-9.16, T-09-02)
        logger.info("Bridge token validated for @%s, installing", username)

        # Initialise FSM state as unclaimed
        write_state(
            module_dir,
            {
                "claim_status": "unclaimed",
                "owner_id": None,
                "pairing_code_hash": None,
                "pairing_code_salt": None,
                "pairing_code_expires": None,
                "pairing_attempts": 0,
            },
        )

        # Enqueue install job and wait for it to finish before redirecting.
        # Without this wait, the HX-Redirect races ahead of the background
        # install task — the config page then 404s because the registry
        # entry is not yet written.
        try:
            job = await start_install("telegram-bridge", module_dir, hub_dir)
        except InProgressError:
            return HTMLResponse(
                '<div class="error" role="alert">'
                "Another module operation is in progress. Please wait and try again."
                "</div>",
                status_code=409,
            )

        # Poll job state (max ~20s). Install usually completes in well under 1s.
        for _ in range(200):
            if job.status != "running":
                break
            await asyncio.sleep(0.1)
        if job.status == "failed":
            err = (job.error or "unknown error").replace("<", "&lt;").replace(">", "&gt;")
            return HTMLResponse(
                f'<div class="error" role="alert">Install failed: {err}</div>',
                status_code=500,
            )

        return HTMLResponse(
            status_code=200,
            headers={"HX-Redirect": "/modules/telegram-bridge/config"},
        )

    def _module_dir() -> Path:
        """Return the telegram-bridge module directory from app state."""
        hub_dir: Path = app.state.hub_dir
        return hub_dir / "modules" / "telegram-bridge"

    def _ttl_context(state: dict) -> dict:
        """Compute TTL display values for a pending state dict."""
        expires = datetime.fromisoformat(state["pairing_code_expires"])
        remaining = max(0, int((expires - datetime.now(timezone.utc)).total_seconds()))
        pct = max(0, int(remaining / 600 * 100))
        minutes, seconds = divmod(remaining, 60)
        ttl_display = f"{minutes}m {seconds}s"
        attempts_remaining = max(0, 5 - state.get("pairing_attempts", 0))
        return {
            "pct": pct,
            "ttl_display": ttl_display,
            "ttl_seconds": remaining,
            "attempts_remaining": attempts_remaining,
        }

    @app.get(
        "/api/modules/telegram-bridge/claim-status",
        response_class=HTMLResponse,
        name="bridge_claim_status",
    )
    async def claim_status(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Return the appropriate pairing-code HTMX fragment for the current FSM state.

        Polls at this endpoint every 5 seconds when in pending state.
        Auto-transitions expired pending codes to unclaimed.
        Plaintext code is never returned here — only dashes (T-09-08).
        """
        module_dir = _module_dir()
        state = read_state(module_dir)
        original_status = state.get("claim_status")
        state = check_expiry(state)
        if state.get("claim_status") != original_status:
            write_state(module_dir, state)

        claim_status_value = state.get("claim_status", "unclaimed")

        if claim_status_value == "pending":
            ctx = _ttl_context(state)
            return templates.TemplateResponse(
                request,
                "_fragments/pairing_code_pending.html",
                {"code": "------", **ctx},
            )
        elif claim_status_value == "claimed":
            return templates.TemplateResponse(
                request,
                "_fragments/pairing_code_claimed.html",
                {},
            )
        else:
            return templates.TemplateResponse(
                request,
                "_fragments/pairing_code_unclaimed.html",
                {},
            )

    @app.post(
        "/api/modules/telegram-bridge/generate-code",
        response_class=HTMLResponse,
        name="bridge_generate_code",
    )
    async def generate_code(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Generate a fresh pairing code and return the pending fragment.

        The plaintext code is shown once in the HTTP response (acceptable per T-09-08).
        The code is never written to disk — only the HMAC hash is stored.
        """
        module_dir = _module_dir()
        code, _state = generate_pairing_code(module_dir)
        return templates.TemplateResponse(
            request,
            "_fragments/pairing_code_pending.html",
            {
                "code": str(code),
                "pct": 100,
                "ttl_display": "10m 0s",
                "ttl_seconds": 600,
                "attempts_remaining": 5,
            },
        )

    @app.post(
        "/api/modules/telegram-bridge/regenerate",
        response_class=HTMLResponse,
        name="bridge_regenerate",
    )
    async def regenerate_code(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Regenerate a pairing code (same as generate-code; old code is overwritten).

        The plaintext code is shown once in the HTTP response (acceptable per T-09-08).
        """
        module_dir = _module_dir()
        code, _state = generate_pairing_code(module_dir)
        return templates.TemplateResponse(
            request,
            "_fragments/pairing_code_pending.html",
            {
                "code": str(code),
                "pct": 100,
                "ttl_display": "10m 0s",
                "ttl_seconds": 600,
                "attempts_remaining": 5,
            },
        )

    @app.post(
        "/api/modules/telegram-bridge/revoke",
        response_class=HTMLResponse,
        name="bridge_revoke",
    )
    async def revoke_ownership(
        request: Request,
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Revoke ownership — transition claimed → unclaimed state.

        Only the current owner (validated via session cookie by require_owner) can revoke.
        Clears all ownership and pairing fields in state.json (T-09-12 mitigation).
        Returns the unclaimed HTMX fragment so the UI updates immediately.
        """
        module_dir = _module_dir()
        state = read_state(module_dir)
        state["claim_status"] = "unclaimed"
        state["owner_id"] = None
        state["pairing_code_hash"] = None
        state["pairing_code_salt"] = None
        state["pairing_code_expires"] = None
        state["pairing_attempts"] = 0
        write_state(module_dir, state)
        logger.info("Bridge ownership revoked — returned to unclaimed state")
        return templates.TemplateResponse(
            request,
            "_fragments/pairing_code_unclaimed.html",
            {},
        )


__all__ = ["register"]
