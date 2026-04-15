"""Bridge-specific dashboard routes (Phase 9, Plan 01).

Mounts token install endpoint and claim-status stub.
Auto-registered by :func:`bot.dashboard.app.build_app` via
``_register_bridge_routes_if_available`` hook; exports a single
:func:`register(app, templates)` entry point.

Security:
    - Token is validated via Telegram getMe before any state is written (T-09-03)
    - Token value is never logged; only the bot username is logged (T-09-02)
    - Token input field uses type="password" to prevent shoulder surfing (T-09-05)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bot.dashboard.deps import require_owner
from bot.dashboard.jobs import InProgressError, start_install
from bot.modules.telegram_bridge_state import validate_bot_token, write_state

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
        body = await request.json()
        token: str = (body.get("token") or "").strip()

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

        # Enqueue install job
        try:
            await start_install("telegram-bridge", module_dir, hub_dir)
        except InProgressError:
            return HTMLResponse(
                '<div class="error" role="alert">'
                "Another module operation is in progress. Please wait and try again."
                "</div>",
                status_code=409,
            )

        return HTMLResponse(
            status_code=200,
            headers={"HX-Redirect": "/modules/telegram-bridge/config"},
        )

    @app.get(
        "/api/modules/telegram-bridge/claim-status",
        response_class=HTMLResponse,
        name="bridge_claim_status",
    )
    async def claim_status(
        request: Request,  # noqa: ARG001
        _uid: int = Depends(require_owner),
    ) -> HTMLResponse:
        """Stub: FSM claim-status endpoint (Plan 02 fills in logic)."""
        return HTMLResponse("")


__all__ = ["register"]
