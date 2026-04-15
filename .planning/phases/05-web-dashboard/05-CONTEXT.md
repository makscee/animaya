# Phase 5: Web Dashboard - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a browser UI — served by the bot process over FastAPI + Jinja2 + HTMX (no npm build) — that lets the owner:

1. Authenticate via Telegram Login Widget
2. See live bot status + recent activity + errors
3. Install / uninstall modules from Phase 3's `bot.modules` API
4. Configure installed modules via forms auto-generated from each module's `manifest.config_schema`

Covers requirements DASH-01 through DASH-06. Not in scope: multi-tenant UI, module authoring UI, chat UI, advanced JSON Schema features (nested objects, arrays, `$ref`).
</domain>

<carried_forward>
## Locked by Prior Phases (do not re-decide)

- **Stack** (DASH-01): FastAPI + Jinja2 + HTMX, no npm toolchain.
- **Auth mechanism** (DASH-02): Telegram Login Widget.
- **Install API** (P3 D-04): Dashboard drives installs via `bot.modules.install(name)` / `uninstall(name)` — the Python API is the single integration surface.
- **Config schema source** (P3 D-09): `manifest.config_schema` is a JSON Schema dict; Phase 3 stores it, Phase 5 renders it.
- **Registry location** (P3 D-06): `~/hub/knowledge/animaya/registry.json`.
- **Assembler trigger** (P3 D-18): Every install/uninstall and every startup reassembles CLAUDE.md. Phase 5 must invoke it after config writes.
- **Install rollback** (P3 D-13): Install failure auto-runs `uninstall.sh` best-effort + verifies `owned_paths` clean. Dashboard must surface rollback outcome.
- **Hub path convention** (P1 D-06): Module data and animaya state live under `~/hub/knowledge/animaya/`.
- **Identity reconfigure** (P4): Phase 4 covered the `/identity` Telegram flow. The "dashboard reconfigure variant" hook is the generic module-config form below — no identity-specific code in Phase 5.
</carried_forward>

<decisions>
## Implementation Decisions

### Access & Session

- **D-01:** Dashboard is **owner-only**. Env var `TELEGRAM_OWNER_ID` (single int, or comma-separated list) holds the allowed Telegram user IDs. Telegram Login Widget hash is verified server-side; if verified ID is not in the allowlist → 403.
- **D-02:** Uvicorn binds to **127.0.0.1** only. TLS + public hostname are terminated by Caddy (Voidnet infrastructure). Dashboard trusts `X-Forwarded-For` / `X-Forwarded-Proto` from the proxy.
- **D-03:** Session cookie: **signed with `itsdangerous`**, 30-day sliding TTL. Cookie payload = `{user_id, auth_date, hash}` from the Login Widget payload. Explicit `/logout` clears it. `httpOnly`, `SameSite=Lax`, `Secure` (via proxy).
- **D-04:** No CORS middleware needed — dashboard serves its own HTML. Drop the v1 `CORSMiddleware(allow_origins=["*"])` from `bot/dashboard/app.py`.

### Liveness

- **D-05:** **HTMX polling**, no SSE/WebSocket in Phase 5. Status fragments use `hx-trigger="every 5s"` at idle.
- **D-06:** Poll rate escalates to **`every 1s`** on pages where an install/uninstall job is in-flight (swap the `hx-trigger` when job state is `running`). Back to 5s once `done|failed`.

### Install / Uninstall UX

- **D-07:** Install/uninstall is **async with job polling**. `POST /modules/{name}/install` enqueues a job, returns `{job_id, status: "running"}`. UI polls `GET /modules/{name}/job/{id}` (1s) until `status in {done, failed}`.
- **D-08:** **Single global `asyncio.Lock`** around install/uninstall operations. A second request while one is running → `409 Conflict` with message `"another module operation in progress"`. No queueing.
- **D-09:** Failure UI: red banner `"Install failed: {module}"` + expandable `<details>` with the **last ~50 lines of combined stderr/stdout**. Rollback outcome rendered as a badge: `rollback: clean` (owned_paths empty) or `rollback: dirty` (leaked paths listed).
- **D-10:** Job state lives in-process in a dict keyed by `job_id` (uuid4). Finished jobs kept 10 minutes for log retrieval then evicted. No persistence across bot restarts — acceptable because installs are rare and restartable.

### Config Forms

- **D-11:** Supported JSON Schema types in Phase 5: **`string`, `integer`, `number`, `boolean`, and `string` with `enum`** (rendered as `<select>`). Any other type (`object`, `array`, `$ref`, `anyOf`, etc.) causes the form renderer to show an "unsupported schema — edit config directly via CLI" notice for that field. Rest of the form still renders.
- **D-12:** Schema annotations consumed: `title` (label), `description` (help text), `default` (pre-fill), `minimum`/`maximum` (int/number), `minLength`/`maxLength` (string), `pattern` (string — server-validated only), `enum` (select options).
- **D-13:** Validation is **server-only** via the `jsonschema` Python lib. Submit posts the form; server validates; on error, re-renders the form fragment with inline error messages via HTMX swap. No client-side JS validation.
- **D-14:** Saving config: write the new `config` dict into the module's registry entry → immediately call the assembler (P3 D-18) to rebuild CLAUDE.md → return a success fragment. No module `reconfigure` hook — keeps Phase 3 manifest contract untouched.

### Page Topology

- **D-15:** **Multi-page** URL structure, server-rendered Jinja:
  - `/` — login redirect OR dashboard home (status + recent activity + errors)
  - `/login` — Telegram Login Widget
  - `/modules` — installed + available module cards
  - `/modules/{name}` — module detail + config form + install/uninstall button
  - `/logout`
- **D-16:** HTMX is used for **fragment swaps within each page** (status widget refresh, job-status polling, form submit with validation errors). Full page loads happen on navigation. No `hx-boost`, no single-page-app feel.

### Status / Activity / Errors

- **D-17:** **Running state** comes from `systemctl --user is-active animaya` (or the Phase 1 unit name). Dashboard shell-outs once per status-poll. Falls back to "unknown" if systemctl absent (dev environment).
- **D-18:** **Activity + errors** come from a **unified JSONL event log** at `~/hub/knowledge/animaya/events.log`. Each record: `{ts, level, source, message, details?}` where `level ∈ {info, warn, error}` and `source` identifies the component (e.g., `bridge`, `modules.install`, `assembler`).
- **D-19:** Dashboard reads the **tail N=50** records for the activity feed and filters `level == "error"` into a separate "Recent errors" card. Both rendered on `/`.
- **D-20:** Event emitter is a small module `bot/events.py` with `emit(level, source, message, **details)`. Phase 5 wires emitters at: message received/replied (bridge), module install/uninstall/rollback (lifecycle), CLAUDE.md rebuilt (assembler), uncaught exceptions (logging handler).
- **D-21:** `events.log` lives in the Hub (git-versioned with GITV module if installed). Rotate by truncating to last 10,000 lines at startup.

### v1 Code Reuse

- **D-22:** `bot/dashboard/app.py` (v1) is a Next.js API backend with CORS + SSE + `/api/chat` streaming. **Drop it entirely.** Start fresh with `bot/dashboard/app.py` serving Jinja pages + HTMX fragments. `bot/dashboard/auth.py` can be cannibalized for Telegram Login Widget hash verification if the logic is sound.
- **D-23:** No `/api/chat` endpoint in Phase 5 — Telegram is the chat surface. No file browser, no settings page, no logs API beyond the events-log tail used by the activity feed.

### Claude's Discretion

- Choice of Jinja template layout (base template, partials structure).
- CSS framework: none vs. vanilla CSS vs. a single CDN'd stylesheet (e.g., PicoCSS) — planner may pick. Keep it minimal.
- Exact job-state-machine implementation (asyncio.Task + dict vs. a tiny job-runner class).
- Where `TELEGRAM_OWNER_ID` is parsed (env loader module).
- Systemd unit name + whether to call `systemctl --user` or `systemctl` (depends on Phase 1 install).
- Log rotation strategy tuning (10,000-line cap is a guideline).
</decisions>

<canonical_refs>
## Canonical References

- `.planning/PROJECT.md` — project vision, core value, constraints
- `.planning/REQUIREMENTS.md` — DASH-01..06 requirement definitions
- `.planning/ROADMAP.md` — Phase 5 goal + success criteria
- `.planning/phases/01-install-foundation/01-CONTEXT.md` — D-06 (Hub path), systemd unit conventions
- `.planning/phases/03-module-system/03-CONTEXT.md` — D-04 (install API), D-06 (registry path), D-09 (config_schema), D-13 (rollback), D-18 (assembler trigger)
- `.planning/phases/04-first-party-modules/04-CONTEXT.md` — identity reconfigure context (Phase 5 variant = generic config form)
- `bot/dashboard/app.py` — v1 FastAPI code, mostly to be replaced (reference for auth.py salvage only)
- `bot/dashboard/auth.py` — v1 auth code, candidate for Telegram Login Widget hash verification
- `bot/modules/` — Phase 3 module system (registry, lifecycle, manifest, assembler) that Phase 5 wraps

No external specs/ADRs referenced.
</canonical_refs>

<deferred>
## Deferred Ideas

- **SSE / WebSocket**: reconsider if 5s polling latency becomes painful, or if we add live chat in the dashboard later.
- **Full JSON Schema support** (nested objects, arrays, `$ref`): add when a first-party module needs it.
- **Client-side validation** (HTML5 or Alpine.js): add only if server round-trip is too slow.
- **Job persistence** across bot restarts: add only if installs become long-running (> minutes).
- **Multi-user / team access**: scope of Voidnet, not Animaya Phase 5.
- **Chat UI in dashboard**: Telegram is the chat surface for v1.
- **Logs page / journalctl viewer**: events.log tail covers the common case.
- **Module authoring UI**: out of scope; modules authored in-repo.
</deferred>

<open_questions>
## Open for Research / Planning

- Exact Telegram Login Widget hash verification flow — confirm via Telegram docs (hash algorithm, `auth_date` staleness window).
- `itsdangerous` signer config: which key source (reuse `DASHBOARD_TOKEN` env or add `SESSION_SECRET`?).
- Whether `systemctl --user` or system-level systemctl matches Phase 1's install. Planner: confirm against `scripts/setup.sh` + `run.sh`.
- CSS approach: planner to pick single-file vanilla CSS or a tiny CDN framework. No npm.
- Job-log size cap: 50 lines on failure is the UI-visible budget; planner decides full in-memory buffer.
</open_questions>
