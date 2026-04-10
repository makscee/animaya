"""FastAPI dashboard — web UI for the bot.

Provides chat interface, file browser, settings, and health endpoint.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

app = FastAPI(title="Animaya Bot Dashboard")

_data_dir = Path(os.environ.get("DATA_PATH", "/data"))


@app.get("/health")
async def health():
    from bot.bridge.telegram import get_stats

    return JSONResponse({"status": "ok", "stats": get_stats()})


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return HTMLResponse(
        "<html><head><title>Animaya</title></head>"
        "<body><h1>Animaya Bot</h1>"
        "<p><a href='/health'>Health</a> | <a href='/files'>Files</a></p>"
        "</body></html>"
    )


@app.get("/files")
async def list_files(path: str = ""):
    """List files in the data directory."""
    target = _data_dir / path
    if not target.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="replace")
        return JSONResponse({"path": path, "content": content})
    entries = []
    for item in sorted(target.iterdir()):
        if item.name.startswith("."):
            continue
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return JSONResponse({"path": path, "entries": entries})
