# Technology Stack — v2.0 Onboarding Polish & Bridge-as-Module

**Project:** Animaya v2.0 milestone
**Researched:** 2026-04-15
**Scope:** DELTA from v1.0 only. v1.0 stack is validated and locked (see git history for v1.0 STACK.md).
**Confidence:** HIGH

---

## TL;DR

**Zero new runtime dependencies required.** Every v2.0 feature (bridge install flow, owner-claim pairing, per-sender metadata, tool-use display toggle, identity editor, dashboard chat, Hub file tree) ships on the existing stack. The only additions are:

1. **Vendor htmx 2.0.8** into `bot/dashboard/static/` (one-time asset, no pip change)
2. **Stdlib modules already on Python 3.12** (`secrets`, `hmac`, `mimetypes`, `pathlib`, `asyncio`) — nothing to install

Two optional UX libraries (`Pygments`, `markdown-it-py`) are flagged LOW-priority — defer unless first-user feedback demands them.

The constraint set (no npm, LXC-native, Hub-compatible, reversible modules) is fully respected — no package managers, no binary deps, no frontend build step.

---

## Validated v1.0 Stack (Unchanged — Inherited)

All confirmed by code inspection of `bot/dashboard/`, `bot/bridge/`, `bot/modules/`, `pyproject.toml` (2026-04-15):

| Technology | Pinned | Role in v2.0 |
|------------|--------|--------------|
| Python | 3.12+ | Runtime — stdlib covers all new needs |
| FastAPI | `>=0.115.0` | Dashboard HTTP — new routes added (`/chat`, `/hub/*`, `/modules/telegram-bridge/pair`) |
| Uvicorn | `>=0.30.0` | ASGI server — no change |
| Jinja2 | `>=3.1.0` | HTML fragments — new `_fragments/*.html` for chat, tree, pairing panel |
| pydantic | `>=2.0` | Manifest validation — extended for `requires_setup`, `pre_installed` fields |
| jsonschema | `>=4.0` | Config form validation — covers bridge token, display-mode enum, non-owner toggle |
| itsdangerous | `>=2.1.0` | Session cookies — unchanged |
| python-multipart | `>=0.0.9` | HTMX form POST parsing |
| python-telegram-bot | `>=21.10` | **v2.0 pattern change:** manual `initialize()`/`start()`/`updater.start_polling()` called at module install time, not at process startup; `stop()` on uninstall. Supported in v21 per official docs. |
| claude-code-sdk | `>=0.0.25` | Chat + bridge reuse `build_options()`; sender metadata injected via `append_system_prompt` |
| httpx[socks] | `>=0.27.0` | Unchanged |

---

## v2.0 Deltas (What's New)

### 1. Frontend Asset — Vendor htmx

| Asset | Version | Where | Why |
|-------|---------|-------|-----|
| `htmx.min.js` | **2.0.8** | `bot/dashboard/static/htmx.min.js` | Current stable (Apr 2026). All new UI uses `hx-post`, `hx-swap`, `hx-trigger`. Fragment-swap pattern already established in v1.0 `module_routes.py`. |
| `htmx-ext-sse.min.js` | 2.x companion | `bot/dashboard/static/htmx-ext-sse.min.js` | Streaming chat tokens via SSE. FastAPI `StreamingResponse(media_type="text/event-stream")` → HTMX SSE extension swaps tokens into `#chat-stream`. No JS framework needed. |

**Decision: vendor, don't CDN.** LXC may be offline/air-gapped after install. Vendored assets preserve reversibility and match the existing `StaticFiles` mount pattern.

**One-time fetch (during v2.0 development, committed to repo):**
```bash
curl -fsSL https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js \
    -o bot/dashboard/static/htmx.min.js
curl -fsSL https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/ext/sse.js \
    -o bot/dashboard/static/htmx-ext-sse.min.js
```

**Reference in `base.html`:**
```html
<script src="/static/htmx.min.js"></script>
<script src="/static/htmx-ext-sse.min.js"></script>
```

### 2. Stdlib Modules (Already Shipped — No Install)

| Module | v2.0 Usage | Rationale |
|--------|-----------|-----------|
| `secrets` | `secrets.randbelow(900000) + 100000` → 6-digit pairing code | Cryptographically strong. Quality gate explicit: "Prefer stdlib (e.g., `secrets` for pairing codes)." |
| `hmac.compare_digest` | Constant-time pairing-code comparison in bridge DM handler | Already used in `dashboard/app.py` for token. Prevents timing attacks on 6-digit space. |
| `asyncio.Lock` / `asyncio.create_task` | Bridge install/stop lifecycle, pairing TTL cleanup | Existing `dashboard/jobs.py` uses same pattern. |
| `pathlib.Path` | Hub tree traversal (`rglob`), identity file I/O, path-traversal guard (`Path(hub_dir).resolve()` prefix check) | Pervasive in v1.0. |
| `json` | Module `config.json` storage (owner_id, token, display_mode, pending_code+expires_at) | v1.0 module format; no change. |
| `mimetypes` | `Content-Type` detection for Hub file viewer | Stdlib. |
| `time`, `datetime` | Pairing TTL (5 min), audit timestamps | Stdlib. |

### 3. Optional UX Libraries (DEFER — Not Needed for MVP)

| Library | Version | Purpose | Why Deferred |
|---------|---------|---------|--------------|
| Pygments | `>=2.17` | Syntax-highlight `.md`/`.py`/`.json` in Hub file viewer | Pure Python, safe, but plain `<pre><code>` suffices. Add only on UX feedback. |
| markdown-it-py | `>=3.0` | Rendered `.md` preview in file viewer | `bot/bridge/formatting.py` already does markdown for Telegram — could reuse if needed. |
| watchfiles | `>=0.21` | Live-reload identity editor on external file change | HTMX `hx-trigger="every 5s"` polling simpler and adequate. |

**Recommendation:** Ship v2.0 with **none** of these. Re-evaluate after first-user feedback.

If later adopted, add to `pyproject.toml` — otherwise leave `pyproject.toml` unchanged for v2.0.

---

## Alternatives Considered (and Rejected)

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Chat streaming transport | FastAPI SSE + htmx-ext-sse | WebSocket | SSE is one-way (server→client), exactly the streaming shape. HTMX has first-class SSE. WebSocket adds reconnection + upgrade complexity with no benefit. |
| Pairing state storage | Module `config.json` (`pending_code`, `expires_at` fields) | Redis / SQLite | Violates LXC-native simplicity. Single owner, single bot — no concurrency requiring a DB. Matches v1.0 module-state precedent. |
| Chat UI framework | Vanilla HTMX + Jinja fragments | Alpine.js / Vue / Svelte | "No npm" constraint. HTMX covers all interactivity. |
| Hub tree widget | Server-rendered nested `<ul>` + `hx-get` lazy-expand | jsTree / react-treeview | No JS framework dependency. Lazy-load children via HTMX on click — better perf on large Hub trees. |
| Bridge reconfigure | `application.stop()` then re-init from new `config.json` | Long-lived Application with hot-reload | PTB v21 does not guarantee safe in-flight reconfig; clean stop/start is documented-safe and symmetric with install/uninstall. |
| Pairing code RNG | `secrets.randbelow` | `random.randint` | `random` is not crypto-secure; brute-forcing a 6-digit space over Telegram DMs is feasible without rate-limiting + `secrets`. |
| Sender metadata injection | Append to Claude `system_prompt` (or `append_system_prompt`) | Custom tool / Claude tool-param | Zero SDK surface change; matches v1.0 identity-module pattern. Text is directly model-readable. |
| Telegram transport | Keep PTB 21 polling | Switch to webhooks / aiogram | Out of scope; migration is unscoped risk. Polling works on LXC without inbound firewall holes. |

---

## Installation

**No `pip install` changes required for v2.0 core.**

`pyproject.toml` stays as-is. If optional libs are later adopted, add under a new `[project.optional-dependencies] ui` section — leave core deps clean.

**One-time vendor step:** see section 1 above.

---

## Integration Points with Existing Stack

| New v2.0 Feature | Existing Hook | Added Surface |
|------------------|--------------|---------------|
| Bridge-as-module | `bot/modules/` manifest + `dashboard/module_routes.py` install flow | New `modules/telegram-bridge/` dir: `manifest.yaml` (`requires_setup: true`), `install.py`, `uninstall.py`. Bridge `Application` lifecycle moves from `bot/main.py` startup into module `install()`/`uninstall()`. |
| Token capture form | `dashboard/forms.py` coerce+validate | Module `config_schema`: `bot_token: {type: string, format: password, minLength: 20}` |
| 6-digit pairing code | `secrets` + module `config.json` | New `/modules/telegram-bridge/pair` GET (render code + `hx-trigger="load delay:2s"` poll) + internal owner-claim handled in bridge DM handler |
| Owner-claim DM handler | `bridge/telegram.py` message handler | Early-path: if `config.owner_id is None` and `text.strip() == pending_code` and `now < expires_at` → persist `owner_id`, clear `pending_code`, reply confirmation |
| Non-owner access toggle | Module `config_schema` boolean | `bridge/telegram.py` gate replaces env check with `config.get("allow_non_owner", False)` |
| Sender metadata in prompt | `claude_query.build_options()` | Append `## Sender\nuser_id={uid}\nusername={uname}\nis_owner={bool}` to `system_prompt` (or use SDK's `append_system_prompt`) |
| Tool-use display modes | Module `config_schema` enum: `temporary` (default) / `persistent` / `hidden` | `bridge/telegram.py` streaming branches on mode: temporary = edit-then-delete message on completion; persistent = separate sibling message; hidden = filter tool-use events from chunks |
| Identity editor page | `dashboard/module_routes.py::config_get` pattern | New `_fragments/identity_editor.html` with `<textarea>` + HTMX POST. Saves markdown file to Hub (not JSON config). |
| Dashboard chat | New `bot/dashboard/chat_routes.py` | `GET /chat` (page) + `POST /chat` (`StreamingResponse` SSE); reuses `build_options()` with dashboard-owner context; tool-use rendered inline as distinct fragments. |
| Hub file tree | New `bot/dashboard/hub_routes.py` | `GET /hub` (root tree page) + `GET /hub/tree?path=...` (nested `<ul>` fragment, HTMX-expand) + `GET /hub/file?path=...` (viewer). **Security:** enforce `resolved_path.is_relative_to(hub_dir.resolve())` to block path traversal. |

---

## What NOT to Add (Hard "No")

- **npm / Node / `package.json`** — violates core constraint. Vendor htmx only.
- **SQLite / Redis / Postgres** — single-owner single-process state fits JSON+lock; adding a DB fights v1.0's Hub-git-as-state model.
- **Any ORM** — no relational data in v2.0.
- **Celery / RQ / background workers** — existing `asyncio` tasks (`dashboard/jobs.py`) cover async install/stream. LXC is single-process.
- **WebSocket framework** — SSE is sufficient for chat streaming.
- **jsTree / virtualized-tree libs** — HTMX lazy-load suffices at expected Hub scale.
- **Module-system plugin framework (pluggy, stevedore)** — custom manifest system already works.
- **Webhooks / aiogram migration** — stick with PTB 21 polling.

---

## Confidence Summary

| Area | Confidence | Source |
|------|------------|--------|
| Existing deps cover all v2.0 features | HIGH | Code inspection of `bot/dashboard/`, `bot/bridge/`, `bot/modules/`, `pyproject.toml` (2026-04-15) |
| PTB v21 supports dynamic start/stop | HIGH | PTB v21.6 + v22 docs confirm `Application.initialize/start/stop` pattern |
| htmx 2.0.8 is current stable | HIGH | GitHub releases + htmx.org docs (Apr 2026) |
| SSE + HTMX for chat streaming | HIGH | htmx-ext-sse documented pattern; FastAPI `StreamingResponse` standard |
| `secrets` suitable for pairing codes | HIGH | Python stdlib security recommendation + quality gate |
| No new deps needed | HIGH | Per-feature analysis above; every integration point maps to existing import |
| Optional libs truly optional | MEDIUM | UX judgment — verify with first-user feedback |

---

## Sources

- [python-telegram-bot v21.6 Application docs](https://docs.python-telegram-bot.org/en/v21.6/telegram.ext.application.html) — `initialize`/`start`/`stop` lifecycle for dynamic bridge control
- [htmx releases](https://github.com/bigskysoftware/htmx/releases) — 2.0.8 current stable
- [htmx SSE extension](https://htmx.org/extensions/server-sent-events/) — streaming chat pattern
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse) — SSE from FastAPI
- [Python `secrets` module](https://docs.python.org/3.12/library/secrets.html) — `randbelow`, `choice`, crypto-strong RNG
- Code inspection: `bot/dashboard/app.py`, `auth.py`, `module_routes.py`, `forms.py`, `jobs.py`, `bridge/telegram.py`, `pyproject.toml` (this repo, 2026-04-15)
