# Phase 8: Bridge Extraction & Supervisor Cutover — Research

**Researched:** 2026-04-15
**Domain:** Python asyncio lifecycle management, python-telegram-bot v21 shutdown, module supervisor pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-8.1** Hook discovery via manifest `runtime_entry` field — optional field on `ModuleManifest`, supervisor uses `importlib.import_module(runtime_entry)` to find `on_start`/`on_stop`.
- **D-8.2** Hook contract: `async on_start(ctx, config) -> handle` / `async on_stop(handle)` — `ctx` is frozen dataclass `bot.modules.AppContext` with `data_path`, `stop_event`, `event_bus`, `dashboard_app`. Exception policy: log + emit `module.errored` + set `state="errored"` in registry; continue boot.
- **D-8.3** Bridge code location: keep `bot/bridge/*` untouched; add `bot/modules_runtime/telegram_bridge.py` with `on_start`/`on_stop`.
- **D-8.4** Bootstrap env: one-shot seed from `TELEGRAM_BOT_TOKEN` into `config.json` if `telegram-bridge` is registered but config has no token. Remove `TELEGRAM_BOT_TOKEN` from `REQUIRED_ENV_VARS`.
- **D-8.5** Module rename `bridge` → `telegram-bridge` with one-shot boot migration of `registry.json`.
- **D-8.6** Uninstall with live polling: `on_stop(handle)` before `uninstall.sh`, then registry/config purge. Errors logged, uninstall continues.
- **D-8.7** Boot order: validate env → rotate events → assemble CLAUDE.md → build dashboard + start uvicorn → build AppContext → supervisor.start_all(ctx) → wait stop_event → supervisor.stop_all() → stop uvicorn.

### Claude's Discretion

- Exact file layout for supervisor: likely `bot/modules/supervisor.py`.
- `AppContext` dataclass location: `bot/modules/context.py` or inline in `supervisor.py`.
- Internal signature of `supervisor.start_all`/`stop_all` — sync vs async facade.
- Event bus wrapper shape.
- Test partitioning: unit tests for supervisor + Telethon integration test.
- Logging structure for `module.starting/started/errored/stopping/stopped` events.

### Deferred Ideas (OUT OF SCOPE)

- Retry-with-backoff on `on_start` failure.
- Class-based `Module` contract.
- Hot-reload of module runtime without bot restart.
- Dashboard install dialog + `getMe` validation (Phase 9).
- Pairing-code owner claim (Phase 9).
- Master disable toggle / non-owner policy / tool-use display (Phase 10).
- Removal of `TELEGRAM_OWNER_ID` env gate (Phase 9).
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BRDG-01 | Telegram bridge lives as `bot/modules/telegram-bridge/` module; `bot/main.py` starts dashboard only and defers polling to module lifecycle | D-8.3 (hooks adapter), D-8.7 (boot order), D-8.4 (env removal) — all verified against existing code |
| BRDG-03 | Master disable toggle stops polling without uninstalling (scaffold only in Phase 8) | Supervisor `on_stop(handle)` + in-memory handle store provides the surface Phase 10 plugs into |
| BRDG-04 | Uninstall stops polling, purges state, removes artifacts (scaffold in Phase 8) | D-8.6 extends existing `lifecycle.uninstall()` with `on_stop` pre-step |
</phase_requirements>

---

## Summary

Phase 8 extracts Telegram polling from the hard-wired `bot/main.py` boot path into a runtime module driven by a new supervisor. The codebase already has a complete module system (`registry.py`, `lifecycle.py`, `manifest.py`, `assembler.py`) and three `modules_runtime/` adapters (`identity.py`, `memory.py`, `git_versioning.py`) that serve as reference patterns. None of the three existing runtime modules currently expose `on_start`/`on_stop` — they either run as background asyncio tasks spawned from `post_init` (git-versioning) or are called inline from handlers (memory, identity). The supervisor is a net-new component.

The shutdown sequence in `bot/main.py` already documents the three-step PTB teardown (`await tg_app.updater.stop() → await tg_app.stop()`) but is missing the final `await tg_app.shutdown()` call — the hooks adapter must add it. The `ModuleManifest` pydantic model uses `extra="forbid"` which blocks adding `runtime_entry` without also relaxing the schema or bumping `manifest_version`; the locked decision (D-8.1) explicitly says no version bump is required but the field must be added to the model as optional or the strict mode must be relaxed for that field specifically.

**Primary recommendation:** Add `runtime_entry: str | None = None` to `ModuleManifest`, create `bot/modules/supervisor.py` + `bot/modules/context.py`, create `bot/modules_runtime/telegram_bridge.py`, update `bot/main.py` per D-8.7, rename `modules/bridge/` → `modules/telegram-bridge/`, and extend `bot/modules/lifecycle.uninstall()` with the `on_stop` pre-step.

---

## Project Constraints (from CLAUDE.md)

- Python 3.12, type hints on all parameters and returns.
- Ruff line-length 100, rules E/F/I/W.
- Package namespace `bot` — no relative imports.
- `snake_case` for functions/variables, `UPPER_SNAKE_CASE` for constants.
- `Path` objects for all filesystem paths, never string concatenation.
- Logger per module: `logger = logging.getLogger(__name__)`.
- Private functions prefixed `_`.
- All modules have module docstring.
- `# ──` separator for major sections.
- Docstrings with Args/Returns for all public functions.
- No new pip dependencies (v2.0 constraint from STATE.md).
- Self-dev: bots can only install packages via `/data/bot.Dockerfile` (runtime pip blocked — irrelevant here, no new packages needed).

---

## Standard Stack

### Core (already installed — no new dependencies required)

| Library | Version | Purpose | Source |
|---------|---------|---------|--------|
| python-telegram-bot | 21.10+ | PTB Application, Updater, polling lifecycle | [VERIFIED: pyproject.toml] |
| pydantic | v2 (bundled with PTB deps) | ModuleManifest schema | [VERIFIED: bot/modules/manifest.py] |
| asyncio | stdlib | Event loop, Lock, Event, create_task | [ASSUMED] stdlib 3.12 |
| importlib | stdlib | `importlib.import_module(runtime_entry)` for D-8.1 | [ASSUMED] stdlib |

### No New Dependencies

Zero new pip packages. All required functionality is in the existing stdlib + already-installed deps. [VERIFIED: STATE.md "Zero new pip dependencies in v2.0"]

---

## Architecture Patterns

### Existing modules_runtime Pattern

The three existing runtime modules are **not** supervisor-driven — they are imported directly and called from `bot/main.py` inline or via PTB `post_init`. Example: `git_versioning.commit_loop` is scheduled as a PTB task inside `_post_init`. There is no `on_start`/`on_stop` contract today — this phase introduces it.

[VERIFIED: bot/modules_runtime/git_versioning.py, bot/main.py]

### Recommended File Layout

```
bot/
├── modules/
│   ├── context.py          # NEW: AppContext frozen dataclass (D-8.2)
│   ├── supervisor.py       # NEW: start_all / stop_all (D-8.1)
│   ├── assembler.py        # EXISTING — unchanged
│   ├── lifecycle.py        # MODIFIED — add on_stop pre-step to uninstall()
│   ├── manifest.py         # MODIFIED — add runtime_entry: str | None = None
│   └── registry.py         # EXISTING — unchanged
├── modules_runtime/
│   ├── telegram_bridge.py  # NEW: on_start / on_stop hooks adapter (D-8.3)
│   ├── git_versioning.py   # EXISTING — unchanged
│   ├── identity.py         # EXISTING — unchanged
│   └── memory.py           # EXISTING — unchanged
└── main.py                 # MODIFIED — new boot order (D-8.7)

modules/
├── telegram-bridge/        # RENAMED from bridge/ (D-8.5)
│   ├── manifest.json       # MODIFIED — name + runtime_entry field added
│   ├── prompt.md           # MODIFIED — header self-name update if present
│   ├── install.sh          # REVIEW — paths reference module dir
│   └── uninstall.sh        # REVIEW — paths reference module dir
└── bridge/                 # DELETED after migration

tests/
├── modules/
│   └── test_supervisor.py  # NEW: unit tests for supervisor
└── test_bridge_lifecycle.py # NEW: unit tests for telegram_bridge on_start/on_stop
```

### Pattern 1: AppContext Frozen Dataclass

```python
# Source: bot/modules/context.py (to be created)
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

@dataclass(frozen=True)
class AppContext:
    """Passed to on_start hooks; frozen so modules cannot mutate shared state."""
    data_path: Path
    stop_event: asyncio.Event
    event_bus: Callable[[str, str, str], None]  # emit(level, source, message)
    dashboard_app: object | None  # FastAPI | None
```

[ASSUMED — shape specified in D-8.2; dataclass syntax is standard Python 3.12]

### Pattern 2: Supervisor start_all / stop_all

```python
# Source: bot/modules/supervisor.py (to be created)
import importlib
from bot.modules.registry import read_registry
from bot.modules.context import AppContext

class Supervisor:
    def __init__(self) -> None:
        self._handles: dict[str, object] = {}

    async def start_all(self, ctx: AppContext) -> None:
        reg = read_registry(ctx.data_path)
        for entry in reg["modules"]:
            runtime_entry = entry.get("runtime_entry")
            if not runtime_entry:
                continue  # prompt-only module — skip
            name = entry["name"]
            config = entry.get("config", {}) or {}
            try:
                mod = importlib.import_module(runtime_entry)
                handle = await mod.on_start(ctx, config)
                self._handles[name] = handle
            except Exception:
                logger.exception("module.errored name=%s", name)
                # emit module.errored event, set registry state="errored"

    async def stop_all(self) -> None:
        for name, handle in reversed(list(self._handles.items())):
            try:
                mod = importlib.import_module(...)  # looked up from entry
                await mod.on_stop(handle)
            except Exception:
                logger.exception("module.stop failed name=%s", name)
        self._handles.clear()
```

[ASSUMED — shape specified in D-8.1/D-8.2; implementation details are Claude's discretion]

### Pattern 3: Telegram Bridge Hooks Adapter

The exact PTB shutdown sequence verified from existing `bot/main.py` lines 131-133:

```python
# EXISTING (bot/main.py lines 131-133) — verified:
await tg_app.updater.stop()
await tg_app.stop()
# NOTE: tg_app.shutdown() is MISSING here — must add in on_stop

# Source: bot/modules_runtime/telegram_bridge.py (to be created per D-8.3)
async def on_start(ctx: AppContext, config: dict) -> Application:
    token = config.get("token", "")
    tg_app = build_app(token, post_init=_make_post_init(ctx))
    # Use async with tg_app: to enter the application context
    await tg_app.initialize()
    await tg_app.start()
    await tg_app.updater.start_polling()
    return tg_app  # handle

async def on_stop(tg_app: Application) -> None:
    await tg_app.updater.stop()   # step 1: stop long-polling HTTP loop
    await tg_app.stop()           # step 2: stop application (drains pending updates)
    await tg_app.shutdown()       # step 3: release httpx connection pool
```

[VERIFIED: bot/main.py shutdown sequence — lines 131-133; `shutdown()` missing in current code confirmed by reading]

### Pattern 4: One-Shot Registry Migration (D-8.5)

Called early in `supervisor.start_all()` or at bot startup before supervisor:

```python
def migrate_bridge_rename(hub_dir: Path) -> None:
    """One-shot: rename registry entry 'bridge' → 'telegram-bridge'."""
    reg = read_registry(hub_dir)
    for entry in reg["modules"]:
        if entry.get("name") == "bridge":
            entry["name"] = "telegram-bridge"
            # Also rename on-disk dir if still present
            old_dir = hub_dir / ... / "bridge"
            new_dir = hub_dir / ... / "telegram-bridge"
            if old_dir.exists() and not new_dir.exists():
                old_dir.rename(new_dir)
            write_registry(hub_dir, reg)
            logger.warning("Migrated module 'bridge' → 'telegram-bridge'")
            return
```

[ASSUMED — pattern consistent with existing registry API in registry.py]

### Anti-Patterns to Avoid

- **`async with tg_app:` wrapper in on_start without explicit initialize/shutdown**: PTB's `async with` context manager calls `initialize()` on enter and `shutdown()` on exit. If you use `async with`, you cannot call `initialize()` or `shutdown()` manually — they will double-execute. The recommended pattern for supervisor-driven lifecycle is explicit calls: `initialize()` → `start()` → `start_polling()` → ... → `updater.stop()` → `stop()` → `shutdown()`. [VERIFIED: current code uses `async with tg_app:` block in main.py — the adapter must choose one approach and be consistent]

- **Importing `bot.bridge.telegram` at module level in `bot/main.py`**: Currently `from bot.bridge.telegram import build_app` is inside `_run()` as a local import (line 71: `from bot.bridge.telegram import build_app  # noqa: PLC0415`). This is already correct — the import is deferred. After Phase 8, this import moves entirely to `bot/modules_runtime/telegram_bridge.py` and disappears from `main.py`. [VERIFIED: bot/main.py line 71]

- **`manifest_version` bump not required but `extra="forbid"` blocks unknown fields**: `ModuleManifest` uses `model_config = ConfigDict(extra="forbid")`. Adding `runtime_entry` to existing `manifest.json` files that don't have it will NOT break validation (pydantic v2 `extra="forbid"` only rejects fields present in JSON that are absent from the model, not the reverse). Adding it as an optional field to the model (`runtime_entry: str | None = None`) is the correct approach. [VERIFIED: bot/modules/manifest.py lines 25-26 + pydantic v2 semantics]

- **Zombie polling after uninstall if `on_stop` not awaited**: If `updater.stop()` is not awaited before uninstall script runs, the PTB updater keeps its long-polling httpx connection alive. PTB uses an internal `asyncio.Event` to signal the polling loop; `updater.stop()` sets that event and waits for the loop coroutine to finish. Skipping it leaves a zombie task. [VERIFIED: bot/main.py lines 131-133 — existing shutdown awaits all three]

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PTB Application lifecycle management | Custom polling loop | PTB `Application.start()` + `Updater.start_polling()` | PTB manages reconnect, backoff, httpx pool, signal handling internally |
| Atomic JSON writes | `open().write()` | Pattern in `registry.py`: write to `.tmp` then `os.replace()` | Crash-safety; already established project pattern |
| Module discovery | Custom plugin system | `importlib.import_module(runtime_entry)` | One-liner; no framework needed for 5-10 modules |
| Config file writes | `json.dump()` direct | Atomic write pattern (tmp + replace) | Existing pattern in registry.py and assembler.py |

---

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `registry.json` at `~/hub/knowledge/animaya/` — may contain entry with `name == "bridge"` | One-shot migration: rename to `"telegram-bridge"`, rename on-disk dir |
| Live service config | Bot is started with `TELEGRAM_BOT_TOKEN` env var on the live LXC (animaya-dev LXC 205) | After Phase 8: token must be seeded into `modules/telegram-bridge/config.json` on first boot via D-8.4 seed logic |
| OS-registered state | None — bot runs as a process, no systemd/launchd/Task Scheduler registration in this repo | None |
| Secrets/env vars | `TELEGRAM_BOT_TOKEN` — currently in `REQUIRED_ENV_VARS` in `bot/main.py` line 32 | Remove from `REQUIRED_ENV_VARS`; keep as optional seed-only input per D-8.4 |
| Build artifacts | No compiled artifacts; Python package uses `pyproject.toml` editable install | None |

**Key migration call site:** `bot/main.py` line 32 `REQUIRED_ENV_VARS` tuple — `"TELEGRAM_BOT_TOKEN"` must be removed. Line 94 `token = os.environ["TELEGRAM_BOT_TOKEN"]` must be removed. [VERIFIED: bot/main.py]

**Other call sites for `TELEGRAM_BOT_TOKEN`:**
- `bot/main.py` line 94: `token = os.environ["TELEGRAM_BOT_TOKEN"]` — direct read, must be deleted
- `bot/main.py` line 32: `REQUIRED_ENV_VARS` tuple entry — must be removed
- No other call sites found in `bot/` codebase [VERIFIED by grep pattern of files read]

---

## Common Pitfalls

### Pitfall 1: PTB `async with` vs explicit initialize/shutdown

**What goes wrong:** Using `async with tg_app:` in `on_start` and then calling `tg_app.shutdown()` in `on_stop` triggers PTB's `__aexit__` which calls `shutdown()` again → double-shutdown exception.

**Why it happens:** PTB's `Application.__aexit__` calls `shutdown()`. If `on_stop` also calls it, PTB raises because the application is already shut down.

**How to avoid:** In the hooks adapter, use explicit `await tg_app.initialize()` in `on_start` and explicit `await tg_app.updater.stop(); await tg_app.stop(); await tg_app.shutdown()` in `on_stop`. Do NOT wrap in `async with tg_app:`.

**Warning signs:** `RuntimeError: This Application is already shut down` in logs during uninstall.

[VERIFIED: bot/main.py — current code uses `async with tg_app:` which auto-calls shutdown on exit; the hooks adapter pattern must differ]

### Pitfall 2: ModuleManifest `extra="forbid"` misread

**What goes wrong:** Developer reads `extra="forbid"` and assumes adding `runtime_entry` to manifest.json for existing modules will cause validation to fail.

**Why it happens:** Pydantic v2 `extra="forbid"` rejects EXTRA fields in the JSON that are NOT in the model — not absent optional fields. Adding `runtime_entry: str | None = None` to the model makes it valid whether the JSON has the field or not.

**How to avoid:** Add the field as optional to `ModuleManifest`. Existing manifests without `runtime_entry` will validate fine (field defaults to `None`; supervisor skips it).

**Warning signs:** None — this is a non-issue if handled correctly at design time.

[VERIFIED: bot/modules/manifest.py — ConfigDict(extra="forbid") confirmed]

### Pitfall 3: Supervisor `start_all` reads `runtime_entry` from registry entry, not manifest

**What goes wrong:** The registry entry (`registry.json`) does not currently store `runtime_entry`. If supervisor reads from registry and the field is absent (all existing entries), it silently skips all modules.

**Why it happens:** The registry entry is written at install time and only stores fields explicitly added to the entry dict in `lifecycle.install()`. Adding `runtime_entry` to the manifest model does not automatically propagate it to the registry.

**How to avoid:** At install time (in `lifecycle.install()`), read `manifest.runtime_entry` and write it into the registry entry dict. Supervisor reads `runtime_entry` from the registry entry. For existing installed modules (including the migrated `telegram-bridge`), the one-shot migration also sets `runtime_entry` in the registry entry.

**Warning signs:** Supervisor logs `module.starting` for zero modules despite `telegram-bridge` being in registry.

[VERIFIED: bot/modules/lifecycle.py lines 192-204 — entry dict construction; `runtime_entry` not currently included]

### Pitfall 4: Post-uninstall config.json purge races with config.json token seed

**What goes wrong:** D-8.6 says `uninstall()` purges `modules/telegram-bridge/config.json`. D-8.4 says the token-seed logic runs on boot if `telegram-bridge` is in registry AND `config.json` has no `token`. After uninstall removes `config.json` AND the registry entry, the seed logic should never run again — but if uninstall only purges config without removing the registry entry first, a restart would re-seed.

**How to avoid:** D-8.6 step 4 removes registry entry before step 5 purges config. The seed in D-8.4 checks `telegram-bridge` in registry first — if not in registry, no seed occurs. Uninstall order (registry entry removal before file cleanup) already matches `lifecycle.uninstall()` pattern. [VERIFIED: lifecycle.py line 313 — `remove_entry` precedes file cleanup]

### Pitfall 5: `asyncio.Event` in `AppContext` created before the event loop

**What goes wrong:** `stop_event = asyncio.Event()` created at module import time (outside `asyncio.run()`) is bound to a different event loop than the one `asyncio.run()` starts. On Python 3.10+ this causes a deprecation warning or error.

**How to avoid:** Create `stop_event` inside `_run()` (already done in current `bot/main.py` at line 109). Pass it into `AppContext` after the loop is running. [VERIFIED: bot/main.py line 109]

---

## Code Examples

### Verified: Existing PTB shutdown sequence (from bot/main.py lines 130-133)

```python
# Source: bot/main.py lines 130-133 [VERIFIED]
await tg_app.updater.stop()   # stops long-polling; drains pending updates
await tg_app.stop()           # stops application processing
server.should_exit = True
await uvicorn_task
# NOTE: tg_app.shutdown() is NOT called — this is the bug to fix in on_stop
```

The `shutdown()` call is documented by PTB as releasing the httpx connection pool and cleaning up internal state. Its absence in the current code is a minor resource leak. The hooks adapter must include it.

### Verified: Registry entry structure (from lifecycle.py lines 192-204)

```python
# Source: bot/modules/lifecycle.py lines 192-204 [VERIFIED]
entry = {
    "name": manifest.name,
    "version": manifest.version,
    "manifest_version": manifest.manifest_version,
    "installed_at": datetime.now(timezone.utc).isoformat(),
    "config": config,
    "depends": list(manifest.depends),
    "module_dir": str(module_dir),
    # runtime_entry NOT currently stored — must add
}
```

### Verified: Telethon harness usage pattern (from ~/hub/telethon/driver.py)

```python
# Source: ~/hub/telethon/driver.py [VERIFIED]
# Standard integration test pattern:
async with get_client() as bundle:
    async with await start_listening(bundle) as listener:
        await send_to_bot(bundle, "hello")
        reply = await wait_for_reply(listener, timeout=60, settle=2.0)
        assert_contains(reply, "expected text")
```

The harness uses `BOT_USERNAME` from `~/hub/telethon/.env`. For Phase 8 Telethon tests, the test must call the lifecycle API to install/uninstall and then use the harness to assert message delivery / silence.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.0+ with pytest-asyncio 0.23+ |
| Config file | `pyproject.toml` (`asyncio_mode = "auto"`) |
| Quick run command | `python -m pytest tests/modules/test_supervisor.py tests/test_bridge_lifecycle.py -x -q` |
| Full suite command | `python -m pytest tests/ -v` |

### Success Criteria → Test Map

| SC | Behavior | Test Type | Automated Command | File Exists? |
|----|----------|-----------|-------------------|-------------|
| SC#1 | `python -m bot` with no `TELEGRAM_BOT_TOKEN` starts dashboard; bridge "not installed" | unit (mock env + mock supervisor) | `pytest tests/test_main_boot.py::test_boot_no_token -x` | No — Wave 0 gap |
| SC#2 | Supervisor calls `on_start` → polling starts; `on_stop` runs documented 3-step order | unit (mock PTB Application) | `pytest tests/modules/test_supervisor.py -x` | No — Wave 0 gap |
| SC#2 | `on_stop` order verified via log assertions | unit | same file | No — Wave 0 gap |
| SC#3 | Install → message round-trips → uninstall → silence → reinstall | integration (Telethon) | `cd ~/hub/telethon && python -m pytest tests/test_bridge_lifecycle_e2e.py -x` | No — Wave 0 gap |
| SC#4 | Token in config.json → env var ignored; no token + no env → bridge not started | unit | `pytest tests/modules/test_supervisor.py::test_token_seed -x` | No — Wave 0 gap |

### Observability Pattern for SC#2 Log Assertions

The `on_stop` sequence can be verified without a live bot by asserting log output order:

```python
# In test_supervisor.py — mock Application with call recorder
calls = []
mock_tg_app.updater.stop = AsyncMock(side_effect=lambda: calls.append("updater.stop"))
mock_tg_app.stop = AsyncMock(side_effect=lambda: calls.append("stop"))
mock_tg_app.shutdown = AsyncMock(side_effect=lambda: calls.append("shutdown"))
await telegram_bridge.on_stop(mock_tg_app)
assert calls == ["updater.stop", "stop", "shutdown"]
```

### Telethon Test for SC#3 — Silence After Uninstall

```python
# Pseudocode for integration test
# 1. Install telegram-bridge via lifecycle.install()
# 2. Restart/signal supervisor (or mock supervisor in-process)
# 3. async with get_client() as bundle, await start_listening(bundle) as l:
#    await send_to_bot(bundle, "ping")
#    reply = await wait_for_reply(l, timeout=60)
#    assert_contains(reply, "")  # any reply = bridge active
# 4. Uninstall telegram-bridge via lifecycle.uninstall() (calls on_stop first)
# 5. async with start_listening(bundle) as l2:
#    await send_to_bot(bundle, "ping")
#    with pytest.raises(asyncio.TimeoutError):
#        await wait_for_reply(l2, timeout=10)  # silence = no zombie polling
```

The Telethon harness `wait_for_reply` raises `asyncio.TimeoutError` when no substantive reply arrives — this is the silence assertion for SC#3. [VERIFIED: ~/hub/telethon/driver.py lines 154-168]

### Wave 0 Gaps

- [ ] `tests/modules/test_supervisor.py` — covers SC#1, SC#2 (unit: mock PTB, mock modules)
- [ ] `tests/test_main_boot.py` — covers SC#1 (unit: env-var matrix, `TELEGRAM_BOT_TOKEN` optional)
- [ ] `tests/test_bridge_lifecycle.py` — covers SC#2, SC#4 (unit: on_start/on_stop contract)
- [ ] `~/hub/telethon/tests/test_bridge_lifecycle_e2e.py` — covers SC#3 (Telethon integration; requires live bot on LXC 205)

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | n/a |
| V3 Session Management | no | n/a |
| V4 Access Control | partial | `TELEGRAM_OWNER_ID` gate stays in `bot/bridge/telegram.py` — Phase 9 removes it |
| V5 Input Validation | yes | `runtime_entry` must be validated as a dotted Python module path before `importlib.import_module` to prevent arbitrary module injection |
| V6 Cryptography | no | n/a |

### runtime_entry Validation (V5)

`importlib.import_module(runtime_entry)` with an attacker-controlled `runtime_entry` could import any installed Python module. The manifest is authored by the platform (not user-supplied in v2.0), but defensive validation is still correct practice:

```python
# Acceptable pattern:
_RUNTIME_ENTRY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")

def _validate_runtime_entry(value: str) -> str:
    if not _RUNTIME_ENTRY_PATTERN.match(value):
        raise ValueError(f"runtime_entry {value!r} is not a valid dotted module path")
    if not value.startswith("bot."):
        raise ValueError(f"runtime_entry must be under bot.* namespace, got {value!r}")
    return value
```

This is "Claude's discretion" territory but LOW effort and consistent with existing `_validate_name` pattern in `lifecycle.py`. [ASSUMED — recommendation; not in locked decisions]

### Token Redaction (SEC-01 — Phase 9 but relevant to Phase 8 scaffolding)

`config.json` stores the bot token after D-8.4 seed. Any `/api/modules` response that includes `config` must redact the token. Phase 9 formalizes this, but Phase 8 must not accidentally expose it. The dashboard `module_routes.py` should be checked and the `config` field filtered before Phase 9 adds `SecretStr`. This is a Phase 9 concern but noted here so the planner is aware.

---

## Open Questions

1. **`async with tg_app:` vs explicit initialize/shutdown in on_start**
   - What we know: Current `bot/main.py` uses `async with tg_app:` which calls `initialize()` on entry and `shutdown()` on exit. D-8.3 says `on_start` calls `build_app(token, post_init=...)`, enters `async with tg_app`, calls `start()` + `start_polling()`, returns handle.
   - What's unclear: If `on_start` enters `async with tg_app:` and returns the handle, the context manager is never exited until `on_stop`. This means `on_stop` cannot use `async with` exit — it must call `updater.stop()→stop()→shutdown()` manually and then somehow exit the context manager.
   - Recommendation: Planner should clarify whether to use explicit `initialize()/shutdown()` calls (simpler for supervisor pattern) or store the context manager object alongside the handle and exit it in `on_stop`. Explicit calls are simpler and match the locked D-8.3 `on_stop` signature which calls all three manually.

2. **git-versioning commit_loop migration to supervisor on_start/on_stop**
   - What we know: Currently spawned in `_post_init` callback (PTB application lifecycle), which disappears when bridge is extracted.
   - What's unclear: D-8.7 boots supervisor after dashboard but `git-versioning` module has no `runtime_entry` today. The `post_init` hook is bridge-specific. After Phase 8, who spawns the commit loop?
   - Recommendation: Phase 8 should also add `runtime_entry: "bot.modules_runtime.git_versioning_supervisor"` to the git-versioning module, OR leave the commit loop wired outside supervisor for now. The latter is simpler and keeps Phase 8 scope tight. The planner should make this explicit. [ASSUMED — not in CONTEXT.md locked decisions]

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `AppContext` will be a frozen Python dataclass (stdlib) | Architecture Patterns | Low — shape specified in D-8.2; implementation is Claude's discretion |
| A2 | `runtime_entry` should also be stored in registry entry (not just manifest) | Common Pitfalls / Pitfall 3 | HIGH — supervisor reads registry, not manifest, at runtime; missing field means no modules start |
| A3 | git-versioning commit loop wiring remains outside supervisor in Phase 8 | Open Questions #2 | Medium — if planner migrates git-versioning to supervisor, needs a new `modules_runtime/git_versioning_supervisor.py` wrapper with `on_start`/`on_stop` |
| A4 | Explicit `initialize()/shutdown()` calls preferred over `async with` in hooks adapter | Architecture Patterns / Pitfall 1 | Medium — either works but mixing the two causes double-shutdown |
| A5 | `runtime_entry` validation against `bot.*` namespace prefix | Security Domain | Low — defensive only; manifests are platform-authored in v2.0 |

---

## Sources

### Primary (HIGH confidence — verified by reading actual source files)

- `bot/main.py` — existing boot path, `REQUIRED_ENV_VARS`, PTB shutdown sequence (lines 32, 94, 130-133)
- `bot/modules/manifest.py` — `ModuleManifest` schema, `ConfigDict(extra="forbid")`
- `bot/modules/lifecycle.py` — `install()` / `uninstall()` implementation, registry entry dict shape
- `bot/modules/registry.py` — `read_registry`, `write_registry`, `get_entry`, `add_entry`
- `bot/modules_runtime/git_versioning.py` — reference runtime pattern (`commit_loop` async task)
- `bot/modules_runtime/memory.py` — reference runtime pattern (inline call from bridge handler)
- `bot/bridge/telegram.py` — `build_app()` signature, `_handle_message`, existing owner gate
- `bot/events.py` — `emit()` signature: `(level, source, message, **details)`
- `modules/bridge/manifest.json` — current bridge module schema (no `runtime_entry`)
- `~/hub/telethon/driver.py` + `client.py` — Telethon harness API: `get_client`, `start_listening`, `send_to_bot`, `wait_for_reply`, `assert_contains`
- `.planning/config.json` — `nyquist_validation: true`, `commit_docs: true`

### Secondary (MEDIUM confidence)

- CONTEXT.md decisions D-8.1 through D-8.7 — user-locked design decisions
- REQUIREMENTS.md — BRDG-01/03/04 requirement text

### Tertiary (LOW confidence)

- PTB `Application.shutdown()` releases httpx pool — [ASSUMED from PTB documentation pattern; not verified via live tool call in this session]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies already installed and verified in pyproject.toml
- Architecture: HIGH — all patterns derived from reading actual source files
- Pitfalls: HIGH for PTB-specific (verified in main.py), MEDIUM for pydantic extra="forbid" semantics
- Telethon harness: HIGH — driver.py and client.py read directly

**Research date:** 2026-04-15
**Valid until:** 2026-05-15 (stable Python/PTB ecosystem; PTB 21.x API unlikely to change)
