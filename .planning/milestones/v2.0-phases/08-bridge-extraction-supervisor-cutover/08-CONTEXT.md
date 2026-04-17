---
phase: 8
name: Bridge Extraction & Supervisor Cutover
created: 2026-04-15
requirements: [BRDG-01, BRDG-03, BRDG-04]
depends_on: [v1.0 module system (MODS-01..06)]
---

# Phase 8 Context — Bridge Extraction & Supervisor Cutover

## Goal (from ROADMAP)

Telegram bridge starts and stops as an installable runtime module instead of hard-wired boot code, so every later phase plugs into the same lifecycle surface.

## Scope (locked)

- Introduce a **module supervisor** that dispatches runtime lifecycle hooks (`on_start` / `on_stop`) for installed modules at boot and during install/uninstall.
- Extract Telegram polling from `bot/main.py` into a runtime hooks adapter that the supervisor drives.
- Rename on-disk module `bridge` → `telegram-bridge` (with registry migration).
- Drop `TELEGRAM_BOT_TOKEN` as a required env var in `bot/main.py`; module `config.json` becomes source of truth.

**Out of scope** (deferred):
- Dashboard install dialog + `getMe` validation (Phase 9).
- Pairing-code owner claim (Phase 9).
- Master disable toggle / non-owner policy / tool-use display (Phase 10).
- Removal of `TELEGRAM_OWNER_ID` env gate (Phase 9).

## Decisions

### D-8.1 — Hook discovery via manifest `runtime_entry` field
- New optional `runtime_entry: str` on `ModuleManifest` (pydantic), e.g. `"bot.modules_runtime.telegram_bridge"`.
- Supervisor `importlib.import_module(runtime_entry)` and looks for module-level `on_start` / `on_stop` callables.
- Modules without `runtime_entry` are prompt-only (current identity, memory, git-versioning behaviour) — supervisor skips them.
- Bump `manifest_version` is **not** required (field is optional; existing manifests stay valid).

### D-8.2 — Hook contract: `async on_start(ctx, config) -> handle` / `async on_stop(handle)`
- `ctx` is a frozen dataclass `bot.modules.AppContext` with:
  - `data_path: Path`
  - `stop_event: asyncio.Event`
  - `event_bus` (the `bot.events.emit` callable or a thin wrapper)
  - `dashboard_app: FastAPI | None` (for modules that want to mount routes later; `None` if dashboard not yet built)
- `config: dict` is loaded from `modules/<name>/config.json` (empty dict if absent).
- `on_start` returns an opaque `handle` (any type) that supervisor stores in memory and passes back to `on_stop`.
- Both hooks are `async`. Synchronous modules can `async def` and do the work inline.
- **Exception policy:** if `on_start` raises, supervisor logs traceback, emits `module.errored` event, sets `registry.json` entry `state="errored"`, continues booting. Dashboard stays up. `on_stop` failures are logged but don't block uninstall script execution.

### D-8.3 — Bridge code location: keep `bot/bridge/*` + add hooks adapter
- `bot/bridge/telegram.py` and `bot/bridge/formatting.py` stay untouched (build_app, handlers, TG_MAX_LEN, md_to_html).
- New file `bot/modules_runtime/telegram_bridge.py` exports `on_start(ctx, config)` / `on_stop(handle)`:
  - `on_start`: reads `config["token"]`, calls `build_app(token, post_init=_post_init)`, enters `async with tg_app`, calls `tg_app.start()` + `tg_app.updater.start_polling()`, returns `tg_app` as the handle.
  - `on_stop(tg_app)`: runs documented order `await tg_app.updater.stop() → await tg_app.stop() → await tg_app.shutdown()`.
- Why: minimal diff, matches existing `bot/modules_runtime/{identity,memory,git_versioning}.py` pattern, keeps `modules/` directory as data-only (no Python imports under `modules/`).

### D-8.4 — Bootstrap env: one-shot seed if module installed and tokenless
- On boot, if `telegram-bridge` is in registry AND `modules/telegram-bridge/config.json` has no `token` field AND `TELEGRAM_BOT_TOKEN` env is set:
  - Write token into `config.json` atomically, log `WARN: TELEGRAM_BOT_TOKEN seeded into module config; env var is deprecated and will be ignored after config.json has a token.`
- After that, env is ignored even if set.
- `TELEGRAM_BOT_TOKEN` is **removed from `REQUIRED_ENV_VARS`** in `bot/main.py` — boot succeeds with neither env nor module installed (dashboard comes up; supervisor reports bridge "not installed").
- Never auto-installs the module. Install is explicit (dashboard in Phase 9, or manual install.sh run in Phase 8).

### D-8.5 — Module rename `bridge` → `telegram-bridge`
- `modules/bridge/` → `modules/telegram-bridge/`. Update `manifest.name`, `prompt.md` header if it self-names, `install.sh` / `uninstall.sh` paths.
- Update `bot/templates/modules/` if a bridge template exists (none today — templates are currently `identity.md`, `image-gen.md`, `memory.md`, `self-dev.md`, `spaces.md`, `voice.md`).
- **Registry migration:** on boot, if `registry.json` contains an entry with `name == "bridge"`, rewrite it to `name == "telegram-bridge"` and rename the on-disk dir if still present. One-shot migration; log a notice. After Phase 8 ships, `bridge` name is gone.
- Test fixtures under `tests/modules/fixtures/` are unaffected (they use synthetic names).

### D-8.6 — Uninstall with live polling: graceful `on_stop` before scripts
- `bot.modules.lifecycle.uninstall(name)` order:
  1. Look up in-memory handle for `name` from supervisor.
  2. `await on_stop(handle)` (runs updater.stop → stop → shutdown).
  3. Run `uninstall.sh` (CLAUDE.md re-assembly, owned_paths cleanup).
  4. Remove entry from `registry.json`.
  5. Purge `modules/<name>/config.json` + `modules/<name>/state.json`.
- If `on_stop` itself raises, log and continue with steps 3–5 (module must uninstall cleanly even if runtime crashed).
- Re-install from scratch works — verified by Telethon test (SC#3).

### D-8.7 — Boot order in `bot/main.py`
- New order:
  1. Validate env (reduced list — no `TELEGRAM_BOT_TOKEN`).
  2. `rotate_events()`.
  3. `assemble_claude_md(data_path)`.
  4. Build dashboard FastAPI app + start uvicorn task (dashboard up first).
  5. Build `AppContext(data_path, stop_event, event_bus, dashboard_app)`.
  6. `supervisor.start_all(ctx)` — iterates registry, starts every module with `runtime_entry`.
  7. Wait on `stop_event`.
  8. Shutdown: `supervisor.stop_all()` → stop uvicorn.
- Dashboard-first means SC#1 holds: no bridge installed → dashboard boots cleanly, bridge reported "not installed" via `/api/modules`.

## Claude's Discretion (planner owns)

- Exact file layout for supervisor: likely `bot/modules/supervisor.py` sibling to `lifecycle.py`, `registry.py`, `assembler.py`.
- `AppContext` dataclass location (probably `bot/modules/context.py` or inline in `supervisor.py`).
- Internal signature of `supervisor.start_all` / `stop_all` — sync vs async facade.
- Event bus wrapper shape (direct `bot.events.emit` reference vs a `Callable[[str, dict], None]`).
- Test partitioning: unit tests for supervisor (mock module with fake hooks) + Telethon integration test covering install→message→uninstall→silence→reinstall round-trip.
- Logging structure for `module.starting`, `module.started`, `module.errored`, `module.stopping`, `module.stopped` events.

## Specifics & References

- Existing shutdown sequence already lives in `bot/main.py` (`updater.stop → stop`). The hooks adapter just relocates those three lines plus an explicit `shutdown()` call.
- `bot/events.py` provides the JSONL event log used by the dashboard — supervisor hooks emit through it.
- Telethon harness at `~/hub/telethon/` is the canonical integration test entry point (reference memory: `reference_telethon_harness`).
- Existing `modules/bridge/manifest.json` is minimal (`owned_paths: []`, no `config_schema`) — Phase 8 will add `runtime_entry` and likely keep `config_schema` null (token validation lives in Phase 9).

## Deferred Ideas (captured, not acted on)

- Retry-with-backoff on `on_start` failure — currently log-and-continue; revisit if transient errors appear in production.
- Class-based `Module` contract with lifecycle methods — deferred; function hooks are sufficient for current module count.
- Hot-reload of module runtime without bot restart — out of scope for v2.0.

## Success Criteria — Trace to Decisions

| SC | How it's satisfied |
|----|---------------------|
| SC#1 (no token → dashboard boots, bridge "not installed") | D-8.4 drops env from required; D-8.7 starts dashboard before supervisor |
| SC#2 (on_start polling, on_stop documented order) | D-8.2 + D-8.3 `on_stop` does updater.stop → stop → shutdown |
| SC#3 (Telethon install→msg→uninstall→silence→reinstall) | D-8.6 graceful uninstall + registry purge; supervisor skips uninstalled modules |
| SC#4 (token optional; config.json canonical) | D-8.4 one-shot seed, then env ignored |

## Next Step

Run `/gsd-plan-phase 8` to produce `08-RESEARCH.md` + plans.
