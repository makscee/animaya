"""FastAPI backend — API endpoints for the Next.js dashboard.

All endpoints under /api/ are called by the dashboard.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Animaya Bot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_data_dir = Path(os.environ.get("DATA_PATH", "/data"))

# SSE event bus for chat streaming
_event_queues: list[asyncio.Queue] = []


def _publish_event(event_type: str, data: dict):
    for q in _event_queues:
        try:
            q.put_nowait((event_type, data))
        except asyncio.QueueFull:
            pass


# ── Health ──────────────────────────────────────────────────────────


@app.get("/api/health")
async def health():
    from bot.bridge.telegram import get_stats
    return JSONResponse({"status": "ok", **get_stats()})


# ── Modules ─────────────────────────────────────────────────────────


def _load_config() -> dict:
    config_path = _data_dir / "config.json"
    if config_path.exists():
        return json.loads(config_path.read_text(encoding="utf-8"))
    return {}


def _save_config(config: dict):
    config_path = _data_dir / "config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


@app.get("/api/modules")
async def list_modules():
    config = _load_config()
    installed = config.get("modules", {})
    modules = []
    for mod_id in ["identity", "telegram", "memory", "spaces", "github", "voice", "image-gen", "self-dev"]:
        modules.append({
            "id": mod_id,
            "installed": mod_id in installed,
            "config": installed.get(mod_id, {}),
        })
    return {"modules": modules}


@app.post("/api/modules/{module_id}/install")
async def install_module(module_id: str, request: Request):
    body = await request.json()
    config = _load_config()
    modules = config.setdefault("modules", {})
    modules[module_id] = body

    # Module-specific install actions
    if module_id == "identity" and body.get("botName"):
        soul = f"# {body['botName']}\n\nI am {body['botName']}, a personal AI assistant.\n"
        if body.get("personality"):
            soul += f"\n## Personality\n{body['personality']}\n"
        if body.get("language"):
            soul += f"\n## Language\nI primarily communicate in {body['language']}.\n"
        if body.get("purpose"):
            soul += f"\n## Purpose\n{body['purpose']}\n"
        (_data_dir / "SOUL.md").write_text(soul, encoding="utf-8")

        if body.get("ownerName"):
            owner = f"# Owner\n\nName: {body['ownerName']}\n"
            (_data_dir / "OWNER.md").write_text(owner, encoding="utf-8")

    elif module_id == "memory":
        (_data_dir / "memory").mkdir(exist_ok=True)
        for f in ["facts.md", "people.md", "projects.md"]:
            p = _data_dir / "memory" / f
            if not p.exists():
                p.write_text(f"# {f.replace('.md', '').title()}\n\n", encoding="utf-8")

    elif module_id == "spaces":
        (_data_dir / "spaces").mkdir(exist_ok=True)

    elif module_id == "self-dev":
        dockerfile = _data_dir / "bot.Dockerfile"
        if not dockerfile.exists():
            dockerfile.write_text("# Bot customizations\n# Add RUN lines to install packages\n", encoding="utf-8")

    _save_config(config)
    return {"ok": True}


@app.post("/api/modules/{module_id}/uninstall")
async def uninstall_module(module_id: str):
    config = _load_config()
    modules = config.get("modules", {})
    modules.pop(module_id, None)
    _save_config(config)
    return {"ok": True}


# ── Chat ────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    text: str


@app.post("/api/chat")
async def chat_send(req: ChatRequest):
    asyncio.get_event_loop().create_task(_process_chat(req.text))
    return {"messageId": f"msg-{int(time.time())}"}


async def _process_chat(prompt: str):
    try:
        from claude_code_sdk import query
        from claude_code_sdk.types import AssistantMessage, TextBlock, ToolUseBlock
        from bot.claude_query import build_options

        options = build_options(data_dir=_data_dir)
        accumulated = ""

        async for message in query(prompt=prompt, options=options):
            if message is None:
                continue
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        accumulated += block.text
                        _publish_event("token", {"text": block.text})
                    elif isinstance(block, ToolUseBlock):
                        _publish_event("tool", {"name": block.name})

        _publish_event("done", {"fullText": accumulated})

    except Exception as e:
        logger.exception("Chat error")
        _publish_event("error", {"error": str(e)})


@app.get("/api/chat/stream")
async def chat_stream():
    queue: asyncio.Queue = asyncio.Queue(maxsize=100)
    _event_queues.append(queue)

    async def generate():
        try:
            while True:
                try:
                    event_type, data = await asyncio.wait_for(queue.get(), timeout=30)
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    if event_type in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            _event_queues.remove(queue)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/chat/history")
async def chat_history(session: str = ""):
    sessions_dir = _data_dir / "sessions"
    if not sessions_dir.exists():
        return {"sessions": [], "messages": []}

    if session:
        # Return placeholder — conversation history is in Claude Code's internal state
        return {"messages": []}

    sessions = []
    for d in sorted(sessions_dir.iterdir(), reverse=True):
        if d.is_dir():
            sessions.append({
                "id": d.name,
                "lastMessage": "",
                "timestamp": time.strftime("%Y-%m-%d %H:%M", time.localtime(d.stat().st_mtime)),
                "messageCount": 0,
            })
    return {"sessions": sessions}


# ── Files ───────────────────────────────────────────────────────────


@app.get("/api/files")
async def list_files(path: str = ""):
    target = _data_dir / path
    if not target.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    if not str(target.resolve()).startswith(str(_data_dir.resolve())):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content}
    entries = []
    for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name)):
        if item.name.startswith("."):
            continue
        entries.append({
            "name": item.name,
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return {"path": path, "entries": entries}


@app.get("/api/files/read")
async def read_file(path: str = ""):
    target = _data_dir / path
    if not target.exists() or target.is_dir():
        return {"content": "", "binary": False}
    if not str(target.resolve()).startswith(str(_data_dir.resolve())):
        return {"content": "", "binary": False}
    try:
        content = target.read_text(encoding="utf-8")
        return {"content": content, "binary": False}
    except UnicodeDecodeError:
        return {"content": "", "binary": True}


class FileWriteRequest(BaseModel):
    path: str
    content: str


@app.put("/api/files")
async def write_file(req: FileWriteRequest):
    target = _data_dir / req.path
    if not str(target.resolve()).startswith(str(_data_dir.resolve())):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(req.content, encoding="utf-8")
    return {"ok": True}


@app.delete("/api/files")
async def delete_file(path: str = ""):
    target = _data_dir / path
    if not str(target.resolve()).startswith(str(_data_dir.resolve())):
        return JSONResponse({"error": "forbidden"}, status_code=403)
    if target.exists():
        if target.is_dir():
            import shutil
            shutil.rmtree(target)
        else:
            target.unlink()
    return {"ok": True}


# ── Settings ────────────────────────────────────────────────────────


@app.get("/api/settings")
async def get_settings():
    config = _load_config()
    return {
        "model": config.get("model", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")),
        "mainLanguage": config.get("main_language", ""),
        "showTools": config.get("show_tools", False),
    }


class SettingsRequest(BaseModel):
    model: str = ""
    mainLanguage: str = ""
    showTools: bool = False


@app.put("/api/settings")
async def save_settings(req: SettingsRequest):
    config = _load_config()
    if req.model:
        config["model"] = req.model
    config["main_language"] = req.mainLanguage
    config["show_tools"] = req.showTools
    _save_config(config)
    return {"ok": True}


# ── Stats ───────────────────────────────────────────────────────────


@app.get("/api/stats")
async def get_stats():
    from bot.bridge.telegram import get_stats as tg_stats

    stats = tg_stats()
    config = _load_config()
    installed_modules = list(config.get("modules", {}).keys())

    file_count = sum(1 for _ in _data_dir.rglob("*") if _.is_file() and not _.name.startswith("."))
    total_size = sum(f.stat().st_size for f in _data_dir.rglob("*") if f.is_file() and not f.name.startswith("."))
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size // 1024} KB"
    else:
        size_str = f"{total_size // (1024 * 1024)} MB"

    return {
        "startedAt": stats.get("started_at", ""),
        "messagesReceived": stats.get("messages_received", 0),
        "messagesSent": stats.get("messages_sent", 0),
        "errors": stats.get("errors", 0),
        "fileCount": file_count,
        "dataSize": size_str,
        "installedModules": installed_modules,
    }


# ── Logs ────────────────────────────────────────────────────────────


@app.get("/api/logs")
async def get_logs(level: str = "", limit: int = 200):
    # Read from Python logging — for now return recent log lines
    # TODO: implement proper log capture with a memory handler
    return {"entries": []}
