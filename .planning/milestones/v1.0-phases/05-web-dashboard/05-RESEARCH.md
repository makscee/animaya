# Phase 5: Web Dashboard - Research

**Researched:** 2026-04-15
**Domain:** Server-rendered web dashboard (FastAPI + Jinja2 + HTMX) for module management
**Confidence:** HIGH (most decisions are already locked in CONTEXT.md; research role is to fill blanks the planner needs)

## Summary

Phase 5 builds a small, server-rendered HTMX dashboard on top of the Phase 3 module API. The stack is FastAPI + Jinja2 + HTMX over CDN, with `itsdangerous`-signed session cookies and Telegram Login Widget auth. There is no npm toolchain, no SSE, no SPA: HTMX fragment swaps drive every dynamic interaction (5s status polling, 1s install-job polling, form-validation re-renders).

The codebase already has FastAPI, Jinja2, itsdangerous, and pydantic in `pyproject.toml` (verified). The Phase 3 module API (`bot.modules.install/uninstall/list_installed/get_entry/read_registry/assemble_claude_md`) is the single integration surface — the dashboard is a thin UI over those functions plus a small async-job runner and a JSONL event log.

The Phase 1 install reality is confirmed: **`systemctl --user`** with unit name **`animaya`**, repo at `~/animaya`, hub at `~/hub/knowledge/animaya`. There is no Caddy/TLS in this repo — it lives at the Voidnet layer.

**Primary recommendation:** Build a single `bot/dashboard/app.py` that mounts FastAPI + Jinja2 routes + a tiny `bot/dashboard/jobs.py` (asyncio.Lock + dict[uuid, JobState]) + `bot/events.py` (JSONL append-only emitter). Render forms with a hand-rolled `bot/dashboard/forms.py` that walks `manifest.config_schema` properties; validate with the `jsonschema` library (new dep). Reuse `auth.py` only as a starting point — the Telegram Login Widget hash flow is materially different from the existing token check.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Stack & integration (carried forward):**
- Stack (DASH-01): FastAPI + Jinja2 + HTMX, no npm toolchain
- Auth mechanism (DASH-02): Telegram Login Widget
- Install API (P3 D-04): `bot.modules.install(name)` / `uninstall(name)` is the single integration surface
- Config schema source (P3 D-09): `manifest.config_schema` is a JSON Schema dict; Phase 5 renders it
- Registry location (P3 D-06): `~/hub/knowledge/animaya/registry.json`
- Assembler trigger (P3 D-18): every install/uninstall and every startup reassembles CLAUDE.md
- Install rollback (P3 D-13): install failure auto-runs `uninstall.sh` best-effort; dashboard surfaces rollback outcome
- Hub path convention (P1 D-06): module data and animaya state under `~/hub/knowledge/animaya/`
- Identity reconfigure: handled by the generic module-config form — no identity-specific code in Phase 5

**Phase 5 decisions:**
- D-01: Owner-only allowlist via `TELEGRAM_OWNER_ID` (single int or comma-separated). Verified TG ID not in allowlist → 403.
- D-02: Uvicorn binds to `127.0.0.1`. Caddy/Voidnet handles TLS. Trust `X-Forwarded-For`/`X-Forwarded-Proto`.
- D-03: `itsdangerous`-signed cookie, 30-day sliding TTL. Payload `{user_id, auth_date, hash}`. `httpOnly`, `SameSite=Lax`, `Secure`. `/logout` clears it.
- D-04: No CORS middleware (drop v1 `CORSMiddleware(allow_origins=["*"])`).
- D-05: HTMX polling, no SSE/WebSocket. Status fragments `hx-trigger="every 5s"` at idle.
- D-06: Poll escalates to `every 1s` while an install/uninstall job is `running`.
- D-07: Install/uninstall is **async with job polling**. POST returns `{job_id, status: "running"}`; UI polls `GET /modules/{name}/job/{id}` (1s) until `done|failed`.
- D-08: **Single global `asyncio.Lock`** for install/uninstall. Concurrent request → `409 Conflict` "another module operation in progress".
- D-09: Failure UI: red banner + expandable `<details>` with last ~50 lines of combined stderr/stdout. Rollback badge: `clean` or `dirty` (with leaked path list).
- D-10: Job state in-process dict keyed by `job_id` (uuid4). Finished jobs kept 10 min for log retrieval, then evicted. No persistence.
- D-11: Supported JSON Schema types: `string`, `integer`, `number`, `boolean`, `string` + `enum` (rendered as `<select>`). Unsupported types render an "edit via CLI" notice for that field; rest of form still renders.
- D-12: Annotations consumed: `title`, `description`, `default`, `minimum`/`maximum`, `minLength`/`maxLength`, `pattern` (server-only), `enum`.
- D-13: Validation server-only via `jsonschema` Python lib. Errors re-render form fragment via HTMX swap.
- D-14: Saving config = write to registry entry → call assembler → return success fragment. No module `reconfigure` hook.
- D-15: Multi-page URLs: `/`, `/login`, `/modules`, `/modules/{name}`, `/logout`. Server-rendered Jinja.
- D-16: HTMX for fragment swaps within pages only. No `hx-boost`, no SPA.
- D-17: Running state from `systemctl --user is-active animaya`. Falls back to "unknown" if systemctl absent.
- D-18: Activity + errors from unified JSONL event log at `~/hub/knowledge/animaya/events.log`. Record: `{ts, level, source, message, details?}`.
- D-19: Tail N=50 records for activity feed; filter `level == "error"` into separate "Recent errors" card.
- D-20: Event emitter `bot/events.py` with `emit(level, source, message, **details)`. Wire at: bridge message in/out, module install/uninstall/rollback, assembler rebuild, uncaught exceptions.
- D-21: `events.log` lives in Hub (git-versioned with GITV if installed). Truncate to last 10,000 lines at startup.
- D-22: **Drop v1 `bot/dashboard/app.py` entirely.** Cannibalize `auth.py` only if logic is sound.
- D-23: No `/api/chat`, no file browser, no settings page, no logs API beyond events-log tail.

### Claude's Discretion
- Jinja template layout (base + partials structure)
- CSS framework: none / vanilla CSS / single CDN stylesheet (e.g., PicoCSS) — keep minimal
- Exact job-state-machine implementation (asyncio.Task + dict vs. tiny class)
- Where `TELEGRAM_OWNER_ID` is parsed (env loader module)
- Systemd unit name + whether to call `systemctl --user` or `systemctl` (depends on Phase 1 install — verified below as `--user` + `animaya`)
- Log rotation strategy tuning (10,000-line cap is a guideline)

### Deferred Ideas (OUT OF SCOPE)
- SSE / WebSocket
- Full JSON Schema support (nested objects, arrays, `$ref`)
- Client-side validation (HTML5 or Alpine.js)
- Job persistence across bot restarts
- Multi-user / team access
- Chat UI in dashboard
- Logs page / journalctl viewer
- Module authoring UI
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DASH-01 | Dashboard runs on FastAPI + Jinja2 + HTMX (no npm) | Standard Stack — FastAPI 0.115 already in pyproject; HTMX 1.9 via CDN; Jinja2 3.1 already present |
| DASH-02 | Authenticate via Telegram Login Widget | Auth section — `<script async src="https://telegram.org/js/telegram-widget.js?22">` widget + server-side hash verification; itsdangerous-signed cookie |
| DASH-03 | Show bot status (running/stopped, recent activity, errors) | Status section — `systemctl --user is-active animaya` shell-out + JSONL `events.log` tail |
| DASH-04 | List available + installed modules | Module discovery — diff `bot.modules.list_installed(hub_dir)` against `Path("modules/").iterdir()` filtered by valid manifest |
| DASH-05 | Install/uninstall modules from UI | Job runner — wrap `bot.modules.install/uninstall` in asyncio.Task tracked in `_jobs[job_id]` dict; HTMX polls status |
| DASH-06 | Configure module settings via auto-generated forms from `config_schema` | Form renderer — walk JSON Schema `properties`; render `<input>` per supported type per D-11; validate with `jsonschema` lib; on save, write `entry["config"]` and call `assemble_claude_md()` |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.12, type hints everywhere** — apply to all new dashboard code.
- **Ruff line-length 100**, rules E/F/I/W. New files must pass `ruff check`.
- **Package name `bot`**, full paths only, no relative imports (`from bot.dashboard.app import ...`).
- **Per-module logger:** `logger = logging.getLogger(__name__)`.
- **`Path` for filesystem paths, never string concat.**
- **Section headers** use `# ──` separator.
- **Snake_case for variables, UPPER_SNAKE_CASE for constants, `_private` prefix for module-internal.**
- **Module docstrings required**; triple-quoted with Args/Returns sections.
- **Validate required env vars at startup** (`bot/main.py`); use `sys.exit(1)` on missing required.
- **Read static config at module level**, runtime config in functions, sensible defaults.
- **GSD workflow:** all edits must go through a GSD command. Phase 5 work is `/gsd-execute-phase`.
- **Test path:** `tests/`. `pytest-asyncio` with `asyncio_mode = "auto"` is already configured.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| fastapi | >=0.115.0 (already pinned) | HTTP server, routing, dependency injection | Already in pyproject; well-documented Jinja2 + Form support `[VERIFIED: pyproject.toml]` |
| uvicorn | >=0.30.0 (already pinned) | ASGI server | Already in pyproject; bind 127.0.0.1 per D-02 `[VERIFIED: pyproject.toml]` |
| jinja2 | >=3.1.0 (already pinned) | Template rendering | Already in pyproject; FastAPI ships `fastapi.templating.Jinja2Templates` `[VERIFIED: pyproject.toml]` |
| itsdangerous | >=2.1.0 (already pinned) | Signed session cookies | Already in pyproject; `URLSafeTimedSerializer` covers 30-day sliding TTL `[VERIFIED: pyproject.toml]` |
| pydantic | >=2.0 (already pinned) | Request body validation, JobState model | Already in pyproject `[VERIFIED: pyproject.toml]` |
| python-multipart | latest | `<form>` POST body parsing in FastAPI | **Required by FastAPI for `Form(...)` deps** — not in pyproject yet `[CITED: fastapi.tiangolo.com/tutorial/request-forms]` |
| jsonschema | >=4.0 | Server-side validation of submitted config (D-13) | The reference Python implementation of JSON Schema; supports Draft 2020-12. **New dependency.** `[ASSUMED on exact version range; CITED: python-jsonschema.readthedocs.io]` |

### Supporting (CDN, no install)
| Asset | Version | Purpose |
|-------|---------|---------|
| HTMX | 1.9.x (latest stable) | Fragment swaps, polling, form posts. Single `<script>` tag. `[ASSUMED — verify latest at htmx.org before pinning]` |
| (optional) PicoCSS | 2.x | Single-file classless stylesheet; sensible defaults without classes. `[ASSUMED]` |
| Telegram Login Widget | v22 (`telegram-widget.js?22`) | Renders the "Log in with Telegram" button; injects callback / posts to redirect URL `[CITED: core.telegram.org/widgets/login]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| jsonschema | pydantic dynamic models | jsonschema is closer to the source-of-truth dict; pydantic would force schema → model translation we don't need |
| HTMX | Alpine.js / vanilla `fetch` | HTMX is lower LOC for the polling + swap pattern that Phase 5 needs almost exclusively |
| Jinja2Templates | Starlette templates directly | FastAPI's wrapper integrates with `Request` and dependency injection; we already depend on FastAPI |
| asyncio.Lock + dict | arq/dramatiq/RQ | Phase 5 explicitly chose in-process (D-08, D-10); a real queue is overkill for one-at-a-time installs |
| systemctl shell-out | dbus-python | dbus binding adds a system dep; shell-out is simpler and aligns with "fall back to unknown if absent" (D-17) |

**Installation:**
```bash
# Add to pyproject.toml [project] dependencies:
#   "python-multipart>=0.0.9",
#   "jsonschema>=4.0",
# Then:
.venv/bin/pip install -e .
```

**Version verification (planner action):** Run `python -m pip index versions jsonschema python-multipart htmx` (HTMX is JS — check htmx.org/discord/CDN for current pin) and pin to verified-current versions before writing PLANs.

## Architecture Patterns

### Recommended Project Structure
```
bot/
├── dashboard/
│   ├── __init__.py
│   ├── app.py              # FastAPI app factory + route registration
│   ├── auth.py             # Telegram Login Widget hash verification + cookie helpers (rewritten)
│   ├── deps.py             # FastAPI dependency: require_owner() → user_id or 403
│   ├── jobs.py             # JobRunner: asyncio.Lock + _jobs dict + run_install/run_uninstall
│   ├── forms.py            # Schema → form-fragment renderer + POST → dict marshaller
│   ├── modules_view.py     # Module discovery: list available + installed
│   ├── status.py           # systemctl shell-out + uptime/pid (graceful degradation)
│   └── templates/
│       ├── base.html
│       ├── partials/
│       │   ├── status.html         # 5s poll target
│       │   ├── job_status.html     # 1s poll target
│       │   ├── form_field.html     # one input per JSON Schema property
│       │   ├── form_errors.html    # validation error fragment
│       │   └── activity.html       # events.log tail render
│       ├── login.html
│       ├── home.html               # status + activity + errors
│       ├── modules_list.html
│       └── module_detail.html
├── events.py               # emit(level, source, message, **details) → JSONL append
└── main.py                 # wire dashboard alongside Telegram bot (start uvicorn in background task)
```

### Pattern 1: FastAPI + Jinja2 server-rendered routes
**What:** Each page is a route returning `templates.TemplateResponse(name, {"request": request, ...})`. Sub-fragments (status widget, job poll, form errors) are separate templates returned by HTMX-targeted endpoints.
**When to use:** Every page in this dashboard.
**Example:**
```python
# Source: fastapi.tiangolo.com/advanced/templates/  [CITED]
from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

app = FastAPI()
templates = Jinja2Templates(directory="bot/dashboard/templates")

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, user_id: int = Depends(require_owner)):
    return templates.TemplateResponse(
        "home.html",
        {"request": request, "events": tail_events(50)},
    )

@app.get("/_partials/status", response_class=HTMLResponse)
async def status_partial(request: Request, _=Depends(require_owner)):
    return templates.TemplateResponse(
        "partials/status.html",
        {"request": request, "status": get_systemctl_status()},
    )
```

### Pattern 2: HTMX polling fragment
**What:** Embed an element with `hx-get="/_partials/status" hx-trigger="every 5s" hx-swap="outerHTML"`. The endpoint returns the same fragment rerendered.
**When to use:** D-05 status panel, D-06 job-status during install.
**Example:**
```html
<!-- Source: htmx.org/docs/#polling [CITED] -->
<div id="status" hx-get="/_partials/status" hx-trigger="every 5s" hx-swap="outerHTML">
  {% include "partials/status.html" %}
</div>

<!-- Escalated polling during install (D-06): swap hx-trigger via OOB or render conditionally -->
<div id="job" hx-get="/modules/{{name}}/job/{{job_id}}"
     hx-trigger="every 1s"
     hx-swap="outerHTML">
  Status: running
</div>
```
The `job_status.html` fragment, when status is `done`/`failed`, omits the `hx-trigger` attribute — polling stops naturally.

### Pattern 3: Async job runner with a single global lock
**What:** A module-level `asyncio.Lock`, a `_jobs: dict[str, JobState]` keyed by uuid4, and an `asyncio.create_task()` that runs the install in a thread executor (because `bot.modules.install` is sync subprocess-heavy).
**When to use:** D-07, D-08, D-10.
**Example:**
```python
# bot/dashboard/jobs.py
import asyncio, uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

_lock = asyncio.Lock()
_jobs: dict[str, "JobState"] = {}

@dataclass
class JobState:
    id: str
    op: str          # "install" | "uninstall"
    module: str
    status: str      # "running" | "done" | "failed"
    started: datetime
    finished: datetime | None = None
    log_lines: list[str] = field(default_factory=list)  # capped at ~200
    error: str | None = None
    rollback: str | None = None  # "clean" | "dirty" | None
    leaked_paths: list[str] = field(default_factory=list)

async def start_install(module_name: str, module_dir: Path, hub_dir: Path) -> JobState:
    if _lock.locked():
        raise RuntimeError("another module operation in progress")
    job = JobState(id=uuid.uuid4().hex, op="install",
                   module=module_name, status="running",
                   started=datetime.now(timezone.utc))
    _jobs[job.id] = job
    asyncio.create_task(_run(job, module_dir, hub_dir))
    return job

async def _run(job, module_dir, hub_dir):
    async with _lock:
        try:
            # Install is sync + subprocess-heavy. Off-thread it.
            await asyncio.to_thread(bot.modules.install, module_dir, hub_dir)
            job.status = "done"
        except RuntimeError as exc:
            job.status = "failed"
            job.error = str(exc)
            # Inspect hub for leaked owned_paths to populate rollback badge
            job.rollback, job.leaked_paths = _check_rollback(module_dir, hub_dir)
        finally:
            job.finished = datetime.now(timezone.utc)
            _gc_old_jobs()  # evict jobs finished > 10 min ago
```

**Important:** `bot.modules.install` is synchronous (uses `subprocess.run`). Must call via `asyncio.to_thread()` — calling it directly inside an `async def` would block the event loop and freeze status polling.

### Pattern 4: JSON Schema → form fragment renderer
**What:** Recursive walk of `manifest.config_schema["properties"]`. Per-property dispatch on `type` (string/integer/number/boolean) and presence of `enum`. Annotations (`title`, `description`, `default`, min/max) become attributes/labels.
**When to use:** D-11, D-12 (DASH-06).
**Example:**
```python
# bot/dashboard/forms.py
SUPPORTED = {"string", "integer", "number", "boolean"}

def render_field(name: str, prop: dict, current: dict) -> dict:
    """Return template context for partials/form_field.html."""
    if "enum" in prop and prop.get("type") == "string":
        kind = "select"
    elif prop.get("type") in SUPPORTED:
        kind = prop["type"]
    else:
        kind = "unsupported"
    return {
        "name": name,
        "kind": kind,
        "label": prop.get("title", name),
        "help": prop.get("description", ""),
        "value": current.get(name, prop.get("default", "")),
        "min": prop.get("minimum"),
        "max": prop.get("maximum"),
        "min_length": prop.get("minLength"),
        "max_length": prop.get("maxLength"),
        "pattern": prop.get("pattern"),
        "enum": prop.get("enum", []),
        "required": name in (prop.get("_required_set") or set()),
    }
```

```python
# Validation on submit
import jsonschema
def validate_submission(form_dict: dict, schema: dict) -> list[str]:
    """Coerce form strings → schema types, validate, return list of error msgs."""
    coerced = _coerce_to_schema(form_dict, schema)
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(coerced), key=lambda e: e.path)
    return [f"{'/'.join(map(str, e.path)) or '(root)'}: {e.message}" for e in errors]
```

**Critical:** HTML form bodies are **always strings**. You must coerce `"42"` → `42` for `integer` properties and `"on"`/missing → `True`/`False` for `boolean` checkboxes **before** running `jsonschema` validation. This coercion table is the single most error-prone slice of the form renderer.

### Pattern 5: Telegram Login Widget hash verification
**What:** Telegram POSTs a payload `{id, first_name, last_name, username, photo_url, auth_date, hash}` to your callback URL. You verify by:
1. Build `data_check_string` from all fields except `hash`, sorted alphabetically by key, joined as `key=value\n...`.
2. `secret_key = sha256(bot_token).digest()` — note: SHA-256 of the raw bot token bytes, **not HMAC**.
3. `expected = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()`
4. `hmac.compare_digest(expected, payload["hash"])` must be true.
5. `auth_date` should be within a freshness window — Telegram recommends ~24h for the initial auth. Reject if older. `[ASSUMED on the 24h figure — verify against current docs]`
6. Verified `id` must be in the `TELEGRAM_OWNER_ID` allowlist (D-01).
7. On success, mint signed cookie via `URLSafeTimedSerializer.dumps({user_id, auth_date, hash})`. Subsequent requests verify cookie via `serializer.loads(token, max_age=30*86400)`.

**When to use:** `/login` callback handler.

```python
# Source: core.telegram.org/widgets/login (Checking authorization)  [CITED]
import hashlib, hmac, os
def verify_telegram_payload(payload: dict, bot_token: str) -> bool:
    received_hash = payload.pop("hash", None)
    if not received_hash:
        return False
    data_check_string = "\n".join(
        f"{k}={v}" for k, v in sorted(payload.items())
    )
    secret_key = hashlib.sha256(bot_token.encode()).digest()
    expected = hmac.new(secret_key, data_check_string.encode(),
                       hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received_hash)
```

### Pattern 6: JSONL event log with rotation at startup
**What:** Append-only file under hub. Each `emit()` writes one JSON object + `\n`. Read = `tail -n 50` of parsed lines. Rotate by reading all lines, keeping last 10,000, atomic-rewrite at startup.

```python
# bot/events.py
EVENTS_LOG = Path(os.environ.get("ANIMAYA_EVENTS_LOG",
                                 Path.home() / "hub/knowledge/animaya/events.log"))

def emit(level: str, source: str, message: str, **details) -> None:
    EVENTS_LOG.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level, "source": source, "message": message,
    }
    if details:
        record["details"] = details
    with EVENTS_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def tail(n: int = 50) -> list[dict]:
    if not EVENTS_LOG.is_file():
        return []
    # For 10k-line cap, simple read-all is fine; revisit if file grows.
    lines = EVENTS_LOG.read_text(encoding="utf-8").splitlines()[-n:]
    out = []
    for ln in lines:
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue  # skip corrupt line
    return out
```

### Anti-Patterns to Avoid
- **Calling `bot.modules.install` directly inside `async def`** — it runs `subprocess.run` (blocking), freezing the event loop and breaking all polling. Always wrap in `asyncio.to_thread()`.
- **Trusting `request.client.host` for auth** — the bind is 127.0.0.1 + Caddy proxies; without `X-Forwarded-For` handling all clients look like `127.0.0.1`. Configure Uvicorn with `--proxy-headers --forwarded-allow-ips="127.0.0.1"` (or pass `proxy_headers=True, forwarded_allow_ips="127.0.0.1"` to `uvicorn.Server`).
- **Mounting `CORSMiddleware(allow_origins=["*"])`** — explicitly removed by D-04. The dashboard is same-origin-only.
- **Re-rendering the entire page after form submit** — D-13/D-16 require fragment swap. Return `partials/form_errors.html` or `partials/save_success.html`, not the whole page.
- **Storing the Telegram `hash` long-term** — the cookie is for session continuity, not re-verification. Do not call `verify_telegram_payload` on every request; verify the cookie via `itsdangerous` instead.
- **Polling without backoff during installs** — at 1s polling, a 30-line job log fragment is fine; do NOT push the full log every poll. Render only the **last N=50 lines** of `job.log_lines` (which is itself capped).
- **Letting `events.log` grow unbounded** — D-21 requires startup truncation to 10,000 lines. Failing to do this turns `tail()` into a multi-MB read every status poll.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON Schema validation | A custom type/range checker | `jsonschema` (Draft 2020-12) | Pattern matching, error paths, type coercion edge cases are all solved |
| Signed session cookies | Custom HMAC + base64 + TTL | `itsdangerous.URLSafeTimedSerializer` | Sliding TTL, signature, encoding handled; already a dep |
| HTML form parsing | Manual `await request.body()` parsing | `python-multipart` + FastAPI `Form(...)` deps | Multipart edge cases, encoding |
| Telegram hash verification | Custom HMAC (every line) | `hmac.compare_digest` + `hashlib.sha256` (stdlib) | The verification itself is small enough — but **always use `compare_digest`**, never `==`, for timing attack resistance |
| HTMX-style polling/swaps | Hand-coded `setInterval` + `fetch` + DOM patching | HTMX `hx-trigger` + `hx-swap` | Single line of HTML per polling target |
| Atomic file writes | Naive `open("w")` | `tempfile + os.replace` (existing pattern in `bot/modules/registry.py`) | Crash safety; reuse the helper |
| systemd querying | dbus-python bindings | `subprocess.run(["systemctl", "--user", "is-active", "animaya"])` | Already shell-out per D-17; one binary call is simpler than D-Bus session setup |

**Key insight:** The dashboard's value is in the *integration* (HTMX wiring + module API + JSON Schema rendering), not in any of those individual mechanics. Reuse stdlib + thin wrappers everywhere.

## Runtime State Inventory

> Phase 5 is **greenfield additive** for the dashboard files plus a small modification to drop v1 dashboard code (D-22). Net new code dominates; the rename/refactor inventory still applies because we're deleting the v1 `bot/dashboard/app.py`.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — Phase 5 reads `~/hub/knowledge/animaya/registry.json` (Phase 3-owned). New addition: `events.log` in same dir. | None for existing data. New file is created on first emit. |
| Live service config | systemd unit `animaya.service` already runs `python -m bot` which currently does NOT start a uvicorn server. Phase 5 adds dashboard startup inside `bot/main.py` (binds 127.0.0.1:PORT). | Update `bot/main.py` to launch uvicorn task alongside Telegram polling. No systemd unit changes needed (same process). Caddy/Voidnet handles public hostname — out of repo scope. |
| OS-registered state | None — no Task Scheduler / launchd / cron entries are added by Phase 5. | None. |
| Secrets/env vars | New required env: `TELEGRAM_OWNER_ID`. New required env: `SESSION_SECRET` (or reuse `DASHBOARD_TOKEN` — see Open Questions). Existing `DASHBOARD_TOKEN` no longer used after v1 dashboard drop. | Update `setup.sh` to prompt for `TELEGRAM_OWNER_ID` (or document in README); add `SESSION_SECRET` generation (`openssl rand -hex 32`) on first install. Document that `DASHBOARD_TOKEN` is obsolete. |
| Build artifacts / installed packages | `dashboard/` Next.js folder (from v1) is present in repo but unused after Phase 5. **Verify and delete** as part of the v1-dashboard cleanup task (D-22). | Delete `dashboard/` (Next.js source) and any `node_modules` if present. Ensure no `pyproject.toml` references remain (none expected). |

**Verified:** `bot/dashboard/app.py` and `bot/dashboard/auth.py` exist (v1, ~14k + ~1k respectively). `bot/dashboard/__init__.py` is empty. No other bot/dashboard files exist.

## Common Pitfalls

### Pitfall 1: Form coercion bug — booleans and missing fields
**What goes wrong:** A `boolean` field rendered as `<input type="checkbox" name="enabled">`. When unchecked, the browser **omits the field entirely** from the POST body. Naive `form_dict["enabled"]` raises KeyError; naive `bool(form_dict.get("enabled"))` makes "off" indistinguishable from "missing".
**Why:** HTML form spec — unchecked checkboxes are not submitted.
**How to avoid:** Coerce explicitly: `coerced[name] = name in form_dict` for booleans. For required-but-missing string fields, distinguish "" (submitted blank) from missing key.
**Warning signs:** Validation errors on freshly-saved forms; `True` values "stuck" until the page reloads from server state.

### Pitfall 2: Subprocess in async route freezes the event loop
**What goes wrong:** `await bot.modules.install(...)` — but `install()` is sync with `subprocess.run()`. Polling status from another tab returns nothing for the duration of the install (10s+).
**Why:** Sync code blocks the event loop; FastAPI cannot serve other requests.
**How to avoid:** **Always** wrap with `await asyncio.to_thread(bot.modules.install, ...)`.
**Warning signs:** Status widget freezes during installs; page hangs when clicking install.

### Pitfall 3: Telegram Login Widget redirect URL must match bot domain
**What goes wrong:** The widget refuses to render or returns auth payload to the wrong URL because the bot wasn't configured with `/setdomain` for this hostname.
**Why:** Telegram restricts Login Widget to bot-owner-confirmed domains (set via @BotFather `/setdomain`).
**How to avoid:** Document in install README: after deploy, run `/setdomain` on @BotFather pointing at the public dashboard hostname (e.g., `dashboard.animaya.example.com`). Cache miss = login button does nothing.
**Warning signs:** Login button renders but click does nothing; payload never arrives at `/login` callback.

### Pitfall 4: `X-Forwarded-For` trust without proxy-header config
**What goes wrong:** Uvicorn ignores `X-Forwarded-*` headers by default, so `request.client.host` is always 127.0.0.1 (the Caddy connection). All audit logs misattribute to localhost.
**Why:** ASGI servers won't trust forwarded headers from arbitrary upstreams; must opt in.
**How to avoid:** Start uvicorn with `proxy_headers=True, forwarded_allow_ips="127.0.0.1"`.
**Warning signs:** Activity log shows `127.0.0.1` for every event; cannot tell who connected.

### Pitfall 5: Job dict GC race — log fetched after eviction
**What goes wrong:** Install completes, user closes tab, comes back 11 min later, clicks the failed-install banner to expand the log → 404 because `_jobs[id]` was evicted.
**Why:** D-10 specifies 10-min retention.
**How to avoid:** Persist the failure log line to `events.log` as well (`source="modules.install", level="error", details={"log": [...]}`) so the activity feed retains it past eviction. Surface a graceful "log no longer available" fragment when `_jobs.get(id)` returns None.
**Warning signs:** "Internal Server Error" or empty fragment when expanding old job logs.

### Pitfall 6: `manifest.config_schema` may be `None`
**What goes wrong:** A module with no configurable settings has `config_schema: null` in its manifest. The form renderer crashes on `schema["properties"]`.
**Why:** D-09 of Phase 3 made the field `Optional[dict]`.
**How to avoid:** Branch at the top of the module-detail view: if `config_schema is None or not config_schema.get("properties")`, render "This module has no configurable settings" — skip the form entirely.
**Warning signs:** Module detail page 500s for some modules but not others.

### Pitfall 7: HTMX swap targets must exist
**What goes wrong:** Form POST returns `partials/form_errors.html` with `hx-target="#form-errors"`, but the home template never rendered a `#form-errors` element. The fragment is appended to body, breaking layout.
**Why:** HTMX requires the target element to exist before the swap.
**How to avoid:** Always include the empty target div in the initial render: `<div id="form-errors"></div>`.
**Warning signs:** Errors appear in unexpected DOM location; page layout breaks after a failed save.

## Code Examples

### Wire dashboard alongside Telegram bot in `bot/main.py`
```python
# Source: uvicorn.org/#running-programmatically  [CITED]
import asyncio
import uvicorn
from bot.dashboard.app import app as dashboard_app

async def main():
    config = uvicorn.Config(
        dashboard_app,
        host="127.0.0.1",
        port=int(os.environ.get("DASHBOARD_PORT", "8090")),
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
        log_level="info",
    )
    server = uvicorn.Server(config)
    bot_task = asyncio.create_task(start_telegram_bot())
    server_task = asyncio.create_task(server.serve())
    await asyncio.gather(bot_task, server_task)
```

### Owner allowlist dependency
```python
# bot/dashboard/deps.py
import os
from fastapi import Cookie, HTTPException, Depends
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

SESSION_COOKIE = "animaya_session"
SESSION_MAX_AGE = 30 * 86400  # 30d sliding TTL handled by reissue

def _serializer() -> URLSafeTimedSerializer:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise RuntimeError("SESSION_SECRET required")
    return URLSafeTimedSerializer(secret, salt="animaya-dashboard")

def _owner_ids() -> set[int]:
    raw = os.environ.get("TELEGRAM_OWNER_ID", "")
    return {int(x.strip()) for x in raw.split(",") if x.strip()}

def require_owner(
    session: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> int:
    if not session:
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    try:
        payload = _serializer().loads(session, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired) as exc:
        raise HTTPException(status_code=302, headers={"Location": "/login"}) from exc
    user_id = int(payload["user_id"])
    if user_id not in _owner_ids():
        raise HTTPException(status_code=403, detail="not an owner")
    return user_id
```

### systemctl status shell-out with graceful degradation
```python
# bot/dashboard/status.py
import shutil, subprocess

def is_running() -> str:
    """Return 'active' | 'inactive' | 'unknown'."""
    if shutil.which("systemctl") is None:
        return "unknown"
    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", "animaya"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        out = result.stdout.strip()
        return out if out in {"active", "inactive", "failed", "activating"} else "unknown"
    except (subprocess.TimeoutExpired, OSError):
        return "unknown"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Next.js SSR + REST API + SSE | FastAPI + Jinja2 + HTMX | This phase (D-22) | No npm toolchain; entire frontend deployed by deploying Python code |
| `DASHBOARD_TOKEN` bearer auth | Telegram Login Widget + signed cookie | This phase (D-02, D-03) | First-class user identity; aligns with bot ownership |
| `/api/chat` SSE streaming | Telegram-only chat | This phase (D-23) | Phase 5 surface area drops dramatically |
| `pip install <module>` | folder + manifest + lifecycle scripts | Phase 3 | No package manager dep; modules are git-friendly |

**Deprecated/outdated:**
- v1 `bot/dashboard/app.py` — entirely replaced (D-22). Salvage `auth.py` only as a starting point for the rewrite.
- `dashboard/` Next.js folder at repo root — delete in Phase 5 cleanup task.
- `DASHBOARD_TOKEN` env var — superseded by `SESSION_SECRET` + `TELEGRAM_OWNER_ID`.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `auth_date` freshness window of ~24h is acceptable for initial login | Auth pattern 5 | Too strict → users see "auth expired" for legitimate 6h-old payloads. Too lax → stale payloads accepted. **Verify against current Telegram docs before pinning.** |
| A2 | `jsonschema>=4.0` is the right pin (latest is in the 4.x line) | Standard Stack | If 5.x is current and breaks Draft202012Validator imports, planner picks wrong API surface. **Run `pip index versions jsonschema` before pinning.** |
| A3 | HTMX 1.9.x is current stable (not 2.x) | Standard Stack | HTMX 2.0 has minor API changes around `hx-on` event handling. **Check htmx.org before pinning.** |
| A4 | PicoCSS 2.x is the current major | Standard Stack | Cosmetic only; choice is also Claude's discretion. |
| A5 | `python-multipart` is not yet in pyproject | Standard Stack | If already present, no new dep needed. **Planner: grep pyproject before adding.** |
| A6 | Telegram bot already has `/setdomain` configured for the deployed hostname | Pitfall 3 | Login widget silently no-ops if not set. Document as deploy step. |
| A7 | Caddy/Voidnet sets `X-Forwarded-Proto: https` and the dashboard can trust it | D-02, Pitfall 4 | If headers absent, cookie `Secure` flag breaks login over HTTPS. Verify on first deploy. |
| A8 | `DASHBOARD_PORT` env (or fixed 8090) is free on the LXC | Code Examples | Conflict → uvicorn fails to bind. Fail-fast at startup. |
| A9 | `bot/main.py` currently runs Telegram via PTB `Application.run_polling()` and can be refactored to coexist with uvicorn in a single asyncio.gather() | Code Examples | If PTB starts its own loop, must use `Application.initialize()` + `start()` + `updater.start_polling()` pattern instead. **Planner: read current `bot/main.py` before designing the wiring task.** |

## Open Questions (RESOLVED)

1. **`SESSION_SECRET` source** — RESOLVED: introduce dedicated `SESSION_SECRET` env var (separate from `DASHBOARD_TOKEN`). `setup.sh` auto-generates via `openssl rand -hex 32` if missing. Adopted in plan 05-02.

2. **Module discovery — what counts as "available"?** — RESOLVED: available = subdirs of `modules/` with valid `manifest.json`, minus already-installed. Installed-but-external-source shown as separate section. Invalid manifests shown as disabled rows with error badge. Adopted in plan 05-05.

3. **`/setdomain` configuration** — RESOLVED: documented as manual deploy step in README (plan 05-07) and surfaced as troubleshooting note in login template (plan 05-03).

4. **PTB + uvicorn coexistence in `bot/main.py`** — RESOLVED: plan 05-07 task 1 reads current `bot/main.py` first and wires via `asyncio.gather` or PTB `post_init` hook, whichever matches the current shape.

5. **Where does `bot/events.py` live in import order?** — RESOLVED: `bot/events.py` is a leaf module importing only stdlib. AST isolation test pattern from Phase 3 enforces this in plan 05-01.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | Bot core | ✓ (project requirement) | 3.12+ | — |
| FastAPI 0.115+ | Dashboard | ✓ (in pyproject) | 0.115.0 | — |
| Jinja2 3.1+ | Templates | ✓ (in pyproject) | 3.1.0 | — |
| itsdangerous 2.1+ | Cookie signing | ✓ (in pyproject) | 2.1.0 | — |
| uvicorn 0.30+ | ASGI server | ✓ (in pyproject) | 0.30.0 | — |
| pydantic 2 | Models | ✓ (in pyproject) | 2.0+ | — |
| python-multipart | Form parsing | ✗ (not in pyproject) | — | Add to pyproject — no fallback acceptable for `Form(...)` deps |
| jsonschema | Schema validation | ✗ (not in pyproject) | — | Add to pyproject — manual validation is the don't-hand-roll trap |
| HTMX (CDN) | UI dynamics | ✓ (CDN at runtime) | 1.9.x | Vendor a copy under `bot/dashboard/static/` if offline LXC is a concern |
| systemctl | Status check | Likely ✓ on LXC | — | Graceful "unknown" fallback per D-17 |
| Telegram bot with `/setdomain` set | Login widget | Manual config | — | No fallback — login widget cannot render without it |

**Missing dependencies with no fallback:**
- `python-multipart`, `jsonschema` — must be added to `pyproject.toml`.
- `/setdomain` for the deployed hostname — must be configured on @BotFather as a deploy step.

**Missing dependencies with fallback:**
- HTMX CDN — vendor a local copy if the LXC has no outbound internet (Voidnet should — verify).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8 + pytest-asyncio (`asyncio_mode = "auto"`) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `pytest tests/dashboard/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DASH-01 | Dashboard app starts and serves `/login` | unit | `pytest tests/dashboard/test_app.py::test_login_page_renders` | ❌ Wave 0 |
| DASH-02 | Telegram Login hash verifies; bad hash rejected | unit | `pytest tests/dashboard/test_auth.py -x` | ❌ Wave 0 |
| DASH-02 | Owner allowlist 403s non-owners | unit | `pytest tests/dashboard/test_auth.py::test_non_owner_forbidden` | ❌ Wave 0 |
| DASH-03 | `tail_events()` returns last N records, missing file → empty list | unit | `pytest tests/test_events.py -x` | ❌ Wave 0 |
| DASH-03 | Status widget renders systemctl output; absent systemctl → "unknown" | unit | `pytest tests/dashboard/test_status.py` | ❌ Wave 0 |
| DASH-04 | `/modules` lists installed + available diff | unit + integration | `pytest tests/dashboard/test_modules_view.py` | ❌ Wave 0 |
| DASH-05 | `start_install` enqueues, polling reflects done/failed | async | `pytest tests/dashboard/test_jobs.py -x` | ❌ Wave 0 |
| DASH-05 | Concurrent install request returns 409 | unit | `pytest tests/dashboard/test_jobs.py::test_concurrent_returns_409` | ❌ Wave 0 |
| DASH-05 | Failed install populates rollback badge | unit | `pytest tests/dashboard/test_jobs.py::test_rollback_badge` | ❌ Wave 0 |
| DASH-06 | `render_field()` produces correct shape per JSON Schema type | unit | `pytest tests/dashboard/test_forms.py -x` | ❌ Wave 0 |
| DASH-06 | Form coercion: missing checkbox → False | unit | `pytest tests/dashboard/test_forms.py::test_boolean_unchecked` | ❌ Wave 0 |
| DASH-06 | jsonschema validation surfaces error path + message | unit | `pytest tests/dashboard/test_forms.py::test_validation_errors` | ❌ Wave 0 |
| DASH-06 | Save → registry write → assembler invoked | integration | `pytest tests/dashboard/test_config_save.py` | ❌ Wave 0 |
| Login flow | End-to-end Login Widget callback → cookie minted → owner allowed | integration | `pytest tests/dashboard/test_login_e2e.py` | ❌ Wave 0 |
| HTMX manual smoke | Click install in browser, status updates without refresh | manual | (browser session against local LXC port-forward) | n/a |

### Sampling Rate
- **Per task commit:** `pytest tests/dashboard/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green + manual browser smoke (login → install → uninstall → reconfigure) before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/dashboard/__init__.py`
- [ ] `tests/dashboard/conftest.py` — fixtures: `tmp_hub`, `fake_owner_token`, `httpx.AsyncClient` against the FastAPI app, fake `manifest.config_schema` examples
- [ ] `tests/dashboard/test_auth.py` — Telegram hash verify, cookie sign/load, owner allowlist
- [ ] `tests/dashboard/test_app.py` — basic route smoke, `/login`, `/`, redirects
- [ ] `tests/dashboard/test_status.py` — systemctl shell-out + fallback
- [ ] `tests/dashboard/test_modules_view.py` — module discovery diff
- [ ] `tests/dashboard/test_jobs.py` — async job runner, lock, 409, rollback badge, GC
- [ ] `tests/dashboard/test_forms.py` — render_field shape, coercion, validation errors
- [ ] `tests/dashboard/test_config_save.py` — end-to-end save + assembler invocation
- [ ] `tests/dashboard/test_login_e2e.py` — full callback flow
- [ ] `tests/test_events.py` — emit + tail + rotate + corrupt-line skip
- [ ] Add to pyproject `[project.optional-dependencies].dev`: `httpx>=0.27` (already present for app code; reused for `AsyncClient`)
- [ ] Framework install: `pip install -e ".[dev]"` (no change — pytest already configured)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Telegram Login Widget HMAC-SHA256 (D-02); owner allowlist via `TELEGRAM_OWNER_ID` (D-01) |
| V3 Session Management | yes | `itsdangerous.URLSafeTimedSerializer`, 30-day sliding TTL, httpOnly + SameSite=Lax + Secure cookie (D-03); explicit `/logout` clears cookie |
| V4 Access Control | yes | `require_owner()` FastAPI dependency on every non-`/login` route; allowlist enforced server-side |
| V5 Input Validation | yes | `jsonschema` for config form bodies (D-13); pydantic for typed request models; `python-multipart` for form parsing |
| V6 Cryptography | partial | HMAC-SHA256 (stdlib `hmac` + `hmac.compare_digest` for timing safety); cookie signing via itsdangerous — never roll custom |
| V7 Error Handling/Logging | yes | All errors flow through `bot/events.py` JSONL log; rollback outcomes surfaced; logger.exception on uncaught |
| V11 Business Logic | yes | Single global asyncio.Lock prevents concurrent module mutations (D-08, prevents registry torn writes) |
| V12 File and Resources | yes | Phase 3 already enforces `owned_paths` traversal defense (carry-forward); Phase 5 inherits it |
| V14 Configuration | yes | `SESSION_SECRET` required at startup (`sys.exit(1)` if missing); 127.0.0.1 bind enforces proxy boundary (D-02) |

### Known Threat Patterns for FastAPI + Jinja2 + HTMX dashboard

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Telegram payload replay (old `auth_date`) | Spoofing | Reject `auth_date` older than 24h (A1); rotate session cookie on re-auth |
| Forged Telegram payload | Spoofing | HMAC verification with `compare_digest` (timing-safe); never log the bot token |
| XSS via module config field rendered without escape | Tampering | Jinja2 autoescape ON by default — never use `\| safe`; never render `manifest.description` HTML |
| XSS via JSONL `events.log` message field | Tampering | Same — autoescape covers it. Never render `details` as HTML. |
| CSRF on install/uninstall POST | Tampering | SameSite=Lax cookie blocks cross-site POST (D-03); also same-origin only (no CORS, D-04) |
| Path traversal in module name (`/modules/../etc/passwd`) | Tampering | `bot.modules._validate_name()` regex enforced server-side (Phase 3 carryforward); FastAPI path param does NOT auto-sanitize |
| Subprocess injection via env vars | Tampering | `bot.modules` already uses `subprocess.run([...])` list form, not shell strings; Phase 5 must not introduce shell=True |
| Session fixation | Spoofing | Mint fresh cookie on every Login Widget success (overwrite, don't merge) |
| Open redirect on `/login?next=...` | Tampering | If we add `?next=` (not in scope per D-15), validate against allowlist of internal paths |
| TOCTOU on module install (race with manifest edit) | Tampering | Single global lock (D-08) makes this impossible during the install window |
| Information disclosure via stack traces | Information disclosure | Ensure `app = FastAPI(debug=False)` in production; render generic 500 page |
| `events.log` unbounded growth | DoS | D-21 startup truncation to 10k lines |
| Concurrent installs corrupting registry | Tampering | Single asyncio.Lock (D-08) + atomic registry write (Phase 3 carryforward) |

## Sources

### Primary (HIGH confidence)
- `bot/dashboard/app.py`, `bot/dashboard/auth.py` — read directly to scope the rewrite
- `bot/modules/{__init__,lifecycle,manifest,registry,assembler}.py` — read directly to confirm integration surface
- `pyproject.toml` — verified current dependency pins
- `scripts/setup.sh`, `run.sh`, `systemd/animaya.service` — verified `systemctl --user` + unit name `animaya` + repo dir `~/animaya`
- `.planning/REQUIREMENTS.md`, `.planning/ROADMAP.md`, `.planning/phases/05-web-dashboard/05-CONTEXT.md` — locked decisions

### Secondary (MEDIUM confidence)
- FastAPI templating docs (training knowledge corroborated by pyproject pin) — patterns 1–2
- HTMX docs (training knowledge) — polling pattern in pattern 2
- Telegram Login Widget verification algorithm (training knowledge — WebFetch was blocked) — pattern 5

### Tertiary (LOW confidence)
- HTMX 1.9.x being current stable (assumed; **planner verifies**)
- jsonschema 4.x being current API surface (assumed; **planner verifies**)
- Telegram `auth_date` 24h staleness window (assumed; **planner/discuss-phase verifies**)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every package except `jsonschema` and `python-multipart` is already in pyproject; both are universally adopted for their roles
- Architecture: HIGH — patterns are textbook FastAPI + HTMX; all design decisions are locked in CONTEXT.md
- Pitfalls: MEDIUM-HIGH — the form-coercion, async-blocking, and proxy-headers traps are well-documented FastAPI gotchas; A1 (auth_date window) is the only assumption that needs explicit user/docs confirmation
- Security: HIGH — narrow attack surface (single-tenant, owner-allowlist, no CORS, no SPA, no client-side state)

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (30 days — stable stack, slow-moving libraries)

## RESEARCH COMPLETE
