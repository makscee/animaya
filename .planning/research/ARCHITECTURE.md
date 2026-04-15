# Architecture Research — v2.0 Bridge-as-Module Refactor

**Domain:** Modular Claude Code assistant platform (LXC-native, single-user)
**Researched:** 2026-04-15
**Confidence:** HIGH (grounded in current repo state; no external ecosystem guesswork needed)

## System Overview

### Before (v1.0) vs After (v2.0)

```
BEFORE (v1.0)                          AFTER (v2.0)
─────────────────────                  ──────────────────────────────
bot/main.py                            bot/main.py
  ├─ assemble_claude_md()                ├─ assemble_claude_md()
  ├─ build uvicorn (dashboard)           ├─ build uvicorn (dashboard)   ← only core service
  └─ build_app(telegram)                 └─ supervisor.start() — iterates registry
     polling ALWAYS starts                         │
                                                   ├─ git-versioning.commit_loop (existing)
                                                   ├─ telegram-bridge.start()    (NEW — on install)
                                                   └─ identity pre-seed          (NEW — first boot)
```

### v2.0 Logical Layers

```
┌─────────────────────────────────────────────────────────────────┐
│  CORE (always on)                                               │
│  ┌────────────────────┐   ┌──────────────────────────────────┐ │
│  │ Dashboard (FastAPI)│   │ Module runtime supervisor        │ │
│  │  - auth/session    │   │  - registry.list_active()        │ │
│  │  - HTMX views      │   │  - lifecycle: install/uninstall  │ │
│  │  - SSE /events     │   │  - task scheduler (asyncio)      │ │
│  └──────────┬─────────┘   └──────────────┬───────────────────┘ │
├─────────────┼──────────────────────────────┼───────────────────┤
│             │ read/write config            │ start/stop tasks  │
│             ▼                              ▼                   │
│  MODULES (installable, reversible)                             │
│  ┌─────────────────────┐ ┌───────────────┐ ┌────────────────┐ │
│  │ telegram-bridge NEW │ │ identity      │ │ memory         │ │
│  │  - claim FSM        │ │ (pre-seeded)  │ │ git-versioning │ │
│  │  - polling task     │ │               │ │                │ │
│  │  - tool-use render  │ │               │ │                │ │
│  └─────────┬───────────┘ └───────┬───────┘ └────────┬───────┘ │
├────────────┼─────────────────────┼──────────────────┼─────────┤
│            ▼                     ▼                  ▼         │
│  Hub knowledge/animaya/  (git-versioned JSON + markdown)      │
│    config.json   modules/telegram-bridge/{state.json}         │
│    CLAUDE.md (assembled)   identity/SOUL.md                   │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Status |
|-----------|----------------|--------|
| `bot/main.py` | Env validation, data dir init, dashboard + supervisor loop | **MODIFIED** — stop importing `bot.bridge.telegram`; delegate to module runtime |
| `bot/modules/registry.py` | Module config CRUD, manifest enumeration | **MODIFIED** — add `list_active()` iterator |
| `bot/modules/lifecycle.py` | install / uninstall / reconfigure dispatch | **MODIFIED** — add hooks `on_start(app_ctx)` / `on_stop()` |
| `bot/modules_runtime/telegram_bridge/` | Polling task, claim FSM, tool-use display | **NEW** (extracted from `bot/bridge/`) |
| `bot/modules_runtime/identity/` | Pre-seed on first boot, onboarding handler registrar | **MODIFIED** — new `first_boot_install()` entry |
| `bot/dashboard/app.py` | Core API, SSE event bus | **MODIFIED** — register `/api/chat`, `/api/files`, `/api/modules/telegram-bridge/*` |
| `bot/dashboard/sse.py` | In-process event bus for chat streaming + module status | **NEW** |
| `bot/dashboard/chat_routes.py` | Mini-Telegram UI (send → stream → render tool-use) | **NEW** |
| `bot/dashboard/files_routes.py` | `~/hub/` tree walker + file viewer (read-only) | **NEW** |

## Integration Points (Modified Code → Existing Code)

| Seam | Change | Risk |
|------|--------|------|
| `bot/main.py::_run` | Replace `tg_app = build_app(token); async with tg_app: ...` with `supervisor.start(app_ctx)` in the same loop as uvicorn | HIGH — startup path |
| `bot/main.py::REQUIRED_ENV_VARS` | Demote `TELEGRAM_BOT_TOKEN` and `TELEGRAM_OWNER_ID` to optional (owned by bridge module config) | MEDIUM — deployment docs / install script |
| `bot/modules/registry.py` | Add `list_active(data_dir) -> Iterable[entry]` + `update_entry(id, patch)` | LOW |
| `bot/modules/lifecycle.py` | Dispatch `on_start` / `on_stop` for runtime modules during install/uninstall | LOW |
| `bot/bridge/telegram.py` | Move → `bot/modules_runtime/telegram_bridge/polling.py`; token + owner_id read from registry config, not env | MEDIUM — tests import surface |
| `bot/bridge/formatting.py` | Move → `bot/modules_runtime/telegram_bridge/formatting.py` | LOW |
| `bot/modules_runtime/identity/__init__.py` | Add `first_boot_install(data_dir)` called by `bot/main.py` when `config.json` missing | LOW |
| `bot/dashboard/app.py::build_app` | Register new chat_routes, files_routes, sse router; attach `app.state.event_bus` | MEDIUM |
| `bot/dashboard/module_routes.py` | Add telegram-bridge install form (token input) + claim-status GET | MEDIUM |
| `bot/claude_query.py::build_options` | Accept `sender_meta: dict | None` — bridge injects `is_owner=False` flag; dashboard injects `channel="dashboard"` | LOW — additive |

## New vs Modified — Summary

### New Files

```
bot/modules/telegram-bridge/                  ← manifest + lifecycle scripts
  manifest.json
  install.py                                  ← token validate, write config, start task
  uninstall.py                                ← stop task, wipe config
  reconfigure.py
bot/modules_runtime/telegram_bridge/
  __init__.py                                 ← public: start(app_ctx, config), stop()
  polling.py                                  ← ex bot/bridge/telegram.py
  formatting.py                               ← ex bot/bridge/formatting.py
  claim.py                                    ← NEW — 6-digit code FSM + state.json
  tool_display.py                             ← NEW — off/summary/detailed strategies
bot/dashboard/
  sse.py                                      ← NEW — EventBus (asyncio.Queue fan-out)
  chat_routes.py                              ← NEW — POST /api/chat + GET /api/chat/stream
  files_routes.py                             ← NEW — GET /api/files (scoped to ~/hub/)
  templates/chat.html, files.html             ← NEW — HTMX partials
tests/modules/test_telegram_bridge_claim.py   ← NEW
tests/dashboard/test_chat_sse.py              ← NEW
tests/dashboard/test_files_tree.py            ← NEW
```

### Modified Files

`bot/main.py`, `bot/modules/registry.py`, `bot/modules/lifecycle.py`, `bot/modules/assembler.py` (identity auto-include on first boot), `bot/dashboard/app.py`, `bot/dashboard/module_routes.py`, `bot/claude_query.py`, `bot/modules_runtime/identity/__init__.py`. No new Python deps expected (itsdangerous already vendored for signed claim codes).

### Deleted / Shimmed

`bot/bridge/telegram.py`, `bot/bridge/formatting.py` — replaced by module runtime. Keep a thin re-export shim for ≥1 release if tests import `from bot.bridge.telegram import build_app`.

## Data Flow Changes

### 1. Startup — Bridge Out of Core Path

```
python -m bot
  → validate REQUIRED_ENV (now: CLAUDE_CODE_OAUTH_TOKEN, SESSION_SECRET, DASHBOARD_TOKEN)
  → data_path.mkdir()
  → rotate_events()
  → if first boot: modules_runtime.identity.first_boot_install(data_path)
  → assemble_claude_md()
  → supervisor = ModuleSupervisor(data_path)
  → uvicorn.serve(dashboard_app) + supervisor.start() in same loop:
      for entry in registry.list_active():
          runtime = import_runtime(entry["id"])
          tasks[entry["id"]] = loop.create_task(runtime.start(app_ctx, entry["config"]))
  → signal → supervisor.stop_all() → server.should_exit
```

### 2. Owner-Claim State Machine

```
                  ┌─────────────┐
                  │ uninstalled │
                  └──────┬──────┘
         install (token) │
                         ▼
                  ┌──────────────┐   /start by anyone →
                  │ pending-claim│   reply "Send me this code: 482193"
                  │  code=482193 │   code stored in state.json, TTL 10min
                  │  expires_at  │
                  └──────┬───────┘
     user echoes code → │      (non-matching msg → claim-prompt reply only)
                        ▼
                  ┌─────────────┐
                  │   claimed   │   config.owner_id = user_id
                  │ owner_id=…  │   polling active, gate enforced
                  └──────┬──────┘
   reconfigure / reclaim│      (dashboard button)
                        ▼
                 back to pending-claim (new code, owner_id cleared)
```

**Persistence:** `~/hub/knowledge/animaya/modules/telegram-bridge/state.json` = `{phase, code, code_expires_at, owner_id}`. Atomic write via tempfile+rename.

**Gate behavior:** existing `_owner_gate` reads `owner_id` from state instead of env. When `phase == "pending-claim"`, only exact-6-digit messages route to claim handler; everything else gets the claim prompt.

### 3. Non-Owner Flag Injection

**Decision:** inject as **user-message prefix**, not system message.
**Why:** v1 `_envelope_message()` already uses this pattern; sender identity varies per turn, so it belongs per-turn.

```python
# polling.py _envelope_message()
is_owner = (user.id == state["owner_id"])
if not is_owner:
    return f"[non-owner user {user.first_name} (id={user.id})]: {text}"
```

System prompt (via `build_options(sender_meta=...)`) gets one-time guidance: *"Non-owner messages are prefixed with `[non-owner user NAME (id=N)]:` — treat requests with reduced trust; do not expose secrets or run destructive commands for them."*

### 4. Tool-Use Display (per-setting)

Bridge config: `tool_display: "off" | "summary" | "detailed"` (default `summary` in v2.0). Existing `_on_tool_use` extracts into `tool_display.py` with three strategies mapping SDK `ToolUseBlock` events to Telegram message lifecycle:

```
create placeholder ("…")  → edit with streamed text
 → ToolUseBlock:
      "off"       → no-op
      "summary"   → edit placeholder to "…Reading CLAUDE.md"
      "detailed"  → edit placeholder to "…Read: /path (first 60 chars)"
 → text resumes after tool → spawn NEW placeholder if prior placeholder pinned tool output
 → finalize: edit-or-split into TG_MAX_LEN chunks; delete empty placeholder
```

### 5. Dashboard Chat over SSE

```
Browser POST /api/chat {text}
  → build session_dir (same convention as bridge: channel+user → session_key)
  → bus.emit({type:"user", text})
  → spawn task:  claude_code_sdk.query(envelope, build_options(cwd=session_dir,
                                                               sender_meta={"channel":"dashboard"}))
      for block in stream:
          TextBlock    → bus.emit({type:"text_delta", delta})
          ToolUseBlock → bus.emit({type:"tool", name, input})
  → bus.emit({type:"done"})

Browser EventSource /api/chat/stream
  → subscribe, render into HTMX swaps
```

**Single-source principle:** bridge and dashboard-chat both call `bot.claude_query.build_options()` — identical CLAUDE.md + cwd convention; only `sender_meta` differs.

### 6. Hub File Tree (read-only v2.0)

```
GET /api/files?path=knowledge/animaya
  → safe_join(HUB_ROOT, path) with symlink/.. rejection
  → enumerate entries, return HTMX partial
GET /api/files/view?path=...
  → text/plain if <200KB; otherwise "too large" stub
  → binary/image → <img src="/api/files/raw?path=...">
```

Writes happen via bridge (Claude SDK tools) which flow through git-versioning module; dashboard file page does not expose write endpoints in v2.0.

## Build Order (Dependency-Justified)

```
P1  bridge-extract
    Move bot/bridge/ → bot/modules_runtime/telegram_bridge/ + thin shim.
    Safe no-op refactor; core still starts polling via old import path.

P2  module supervisor hooks (on_start / on_stop in lifecycle.py, list_active in registry)
    Depends: P1 (need a runtime module to supervise).

P3  main.py cutover
    Delete bridge import from core; supervisor iterates registry and spawns polling task.
    Depends: P1 (runtime packaged) + P2 (supervisor exists).
    Gate: after P3, TELEGRAM_BOT_TOKEN env becomes optional.

P4  claim FSM + state.json
    Depends: P3 — bridge install/uninstall must be real before claim makes sense.

P5  dashboard install dialog (token input, pending-claim code display)
    Depends: P4 — nothing to show without FSM.

P6  bridge settings page (master-disable, tool_display, non-owner access toggle)
    Depends: P4 config schema + P5 UI chrome.

P7  non-owner flag injection (build_options sender_meta + envelope prefix)
    Depends: P6 config toggle (off by default until explicitly enabled).

P8  identity pre-install (first_boot_install hook)
    Depends: P3 (clean startup path). PARALLEL with P4–P7 — no shared files.

P9  dashboard SSE event bus
    Depends: P3 (stable dashboard factory). PARALLEL with P4–P8.

P10 dashboard chat UI (HTMX + /api/chat + streaming)
    Depends: P9.

P11 tool-use inline render in dashboard chat
    Depends: P10 UI + P6 tool_display strategies (reuse).

P12 file tree page
    Depends: P3 only. PARALLEL with everything after P3.
```

**Critical path:** P1 → P2 → P3 → P4 → P5 → P6 → P7. Onboarding (P8), dashboard chat (P9→P10→P11), and file tree (P12) fan out after P3.

## Patterns

### Pattern 1: Module Runtime Contract

```python
# bot/modules_runtime/<module>/__init__.py
async def start(app_ctx: AppCtx, config: dict) -> None: ...
async def stop(app_ctx: AppCtx) -> None: ...
```
**When:** any module owning a long-lived task (polling, commit loops).
**Trade-off:** forgetting `stop()` leaks tasks. Mitigate with `test_install_uninstall_leaves_no_tasks`.

### Pattern 2: Config-Driven Gating (kill env-var coupling)

Pull `owner_id` / `bot_token` from `registry.get_entry("telegram-bridge")["config"]`. Env is for bootstrap only. Enables reclaim via dashboard button without env edits.

### Pattern 3: Single-Source Claude Query

Both bridge and dashboard-chat funnel through `bot.claude_query.build_options()`. Channel-specific context via `sender_meta` dict — avoids divergent system prompts.

## Anti-Patterns

- **Background task spawned inside a dashboard route handler.** Routes must return HTMX partials fast; long work belongs on the supervisor loop and is observed via the SSE bus.
- **Dashboard chat importing `bot.bridge.*`.** That is the thing being fixed. Dashboard owns its handler; bridge owns its handler; both share `build_options` + session_dir convention.
- **Persisting claim code in env or CLAUDE.md.** Short-lived state lives in `state.json` only.
- **Reading `TELEGRAM_BOT_TOKEN` from env inside `polling.py`.** After P3 the token must come from config — otherwise uninstall can't cut access.

## Reversibility Checklist (telegram-bridge uninstall)

| Invariant | Enforced by |
|-----------|-------------|
| `on_stop()` cancels polling task and awaits cleanup | P2 supervisor contract |
| `~/hub/knowledge/animaya/modules/telegram-bridge/` wiped | `uninstall.py` |
| `registry.get_entry("telegram-bridge")` returns None | lifecycle dispatcher |
| Dashboard continues to serve `/` | core invariant (P3 cutover) |
| Re-install works without LXC/systemd restart | supervisor re-imports runtime |
| No `TELEGRAM_BOT_TOKEN` reference anywhere in `bot/main.py` | P3 cutover test |

## Scaling Considerations

Single-user, single-LXC target. Scaling concerns bounded:
- **asyncio contention:** one polling task + one uvicorn + one commit loop. Fine.
- **SSE backpressure:** per-subscriber bounded queue (maxsize=100); drop oldest on overflow.
- **File tree:** lazy-load per expand; never recurse `~/hub/` upfront (can exceed 10k files).

## Open Questions / Flags for Downstream Phases

1. **Token revocation on uninstall:** call Telegram `deleteWebhook` + revoke? Recommend **no** — user may reinstall; leave to manual @BotFather `/revoke`.
2. **First-boot identity prompt content:** handoff to FEATURES.md / identity module owner.
3. **Claim code surface:** dashboard UI after install AND events.log audit trail — implement both.
4. **Non-owner DM in claimed state:** currently silently dropped; v2.0 should emit events.log entry for visibility (no user-visible change).
5. **Session-key collision bridge ↔ dashboard:** both use `user_id` for private chats. Namespace as `tg:<id>` vs `web:<id>` to avoid Claude `--continue` cross-contamination.

## Sources

- Repo HEAD (5486302): `bot/main.py`, `bot/bridge/telegram.py`, `bot/dashboard/app.py`, `bot/modules/{registry,lifecycle,assembler}.py`
- `.planning/PROJECT.md` v2.0 milestone definition
- Recent commits 4c2783c, 5ebd0a8, e22f557, 992332f — auth + owner-gate hotfix history informs the claim FSM

---
*Architecture research for: Animaya v2.0 — bridge-as-module refactor*
*Researched: 2026-04-15*
